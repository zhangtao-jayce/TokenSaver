import os
import tempfile
import unittest

from tokensaver import TokenSaver
from tokensaver.integrations import (
    LangChainTokenSaverCallback,
    STANDARD_RUN_FIELDS,
    messages_to_text,
    trace_anthropic_message,
    trace_litellm_completion,
    trace_openai_chat_completion,
    trace_openai_response,
)


class _OpenAIChatCompletions:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return {"choices": [{"message": {"content": "chat answer"}}]}


class _OpenAIResponses:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return {"output_text": "response answer"}


class _OpenAIClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _OpenAIChatCompletions()})()
        self.responses = _OpenAIResponses()


class _AnthropicMessages:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return {"content": [{"type": "text", "text": "anthropic answer"}]}


class _AnthropicClient:
    def __init__(self):
        self.messages = _AnthropicMessages()


class IntegrationHelperTests(unittest.TestCase):
    def setUp(self):
        self._old_update_env = os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN")
        os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = "0"

    def tearDown(self):
        if self._old_update_env is None:
            os.environ.pop("TOKENSAVER_CHECK_UPDATE_ON_RUN", None)
        else:
            os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = self._old_update_env

    def test_standard_run_fields_match_v06_schema_contract(self):
        self.assertEqual(
            STANDARD_RUN_FIELDS,
            [
                "app",
                "channel",
                "user_message",
                "traffic_type",
                "task_type",
                "route",
                "metadata",
                "context_items",
                "tool_calls",
                "model_calls",
                "answer",
                "quality_signals",
            ],
        )

    def test_openai_chat_and_responses_helpers_record_model_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="demo", channel="chat", store_dir=tmp)
            client = _OpenAIClient()
            messages = [{"role": "user", "content": "hello"}]

            with ts.run(user_message="hello") as run:
                chat_response = trace_openai_chat_completion(
                    run,
                    client=client,
                    model="gpt-4.1-mini",
                    messages=messages,
                    temperature=0,
                )
                responses_response = trace_openai_response(
                    run,
                    client=client,
                    model="gpt-4.1-mini",
                    input="hello",
                )
                run.record_final_answer("done")

            self.assertEqual(chat_response["choices"][0]["message"]["content"], "chat answer")
            self.assertEqual(responses_response["output_text"], "response answer")
            calls = run.result["model_calls"]
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0]["metadata"]["provider"], "openai")
            self.assertEqual(calls[0]["metadata"]["api"], "chat.completions")
            self.assertEqual(calls[1]["metadata"]["api"], "responses")
            self.assertIn("user: hello", messages_to_text(messages))

    def test_anthropic_and_litellm_helpers_record_model_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="demo", channel="chat", store_dir=tmp)
            anthropic = _AnthropicClient()

            def completion(**kwargs):
                completion.kwargs = kwargs
                return {"choices": [{"message": {"content": "litellm answer"}}]}

            with ts.run(user_message="hello") as run:
                trace_anthropic_message(
                    run,
                    client=anthropic,
                    model="claude-sonnet-4-6",
                    messages=[{"role": "user", "content": "hello"}],
                    max_tokens=100,
                )
                trace_litellm_completion(
                    run,
                    completion=completion,
                    model="openai/gpt-4.1-mini",
                    messages=[{"role": "user", "content": "hello"}],
                )
                run.record_final_answer("done")

            calls = run.result["model_calls"]
            self.assertEqual(calls[0]["metadata"]["provider"], "anthropic")
            self.assertEqual(calls[1]["metadata"]["provider"], "litellm")
            self.assertEqual(completion.kwargs["model"], "openai/gpt-4.1-mini")

    def test_langchain_callback_records_llm_and_tool_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="demo", channel="chat", store_dir=tmp)
            with ts.run(user_message="search docs") as run:
                callback = LangChainTokenSaverCallback(run)
                callback.on_llm_start(
                    {"id": ["langchain", "chat_models", "ChatOpenAI"]},
                    ["question"],
                    run_id="llm-1",
                    invocation_params={"model_name": "gpt-4.1-mini"},
                )
                callback.on_llm_end(
                    {"generations": [[{"text": "answer"}]]},
                    run_id="llm-1",
                )
                callback.on_tool_start(
                    {"name": "search"},
                    "query",
                    run_id="tool-1",
                    name="search",
                )
                callback.on_tool_end("result text", run_id="tool-1", name="search")
                run.record_final_answer("answer")

            self.assertEqual(run.result["model_calls"][0]["model"], "gpt-4.1-mini")
            self.assertEqual(run.result["model_calls"][0]["metadata"]["framework"], "langchain")
            self.assertEqual(run.result["tool_calls"][0]["name"], "search")
            self.assertGreater(run.result["tool_calls"][0]["output_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
