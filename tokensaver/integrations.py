"""Small dependency-free integration helpers.

These helpers are intentionally generic. They give coding agents simple
patterns to wrap LLM calls or adapt framework callbacks without TokenSaver
depending on any specific Agent framework.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .runtime import AgentRun


STANDARD_RUN_FIELDS = [
    "app",
    "channel",
    "user_message",
    "task_type",
    "route",
    "context_items",
    "tool_calls",
    "model_calls",
    "answer",
    "quality_signals",
]


def trace_llm_call(
    run: AgentRun,
    *,
    model: str,
    input_text: str,
    call: Callable[[], str],
    metadata: dict[str, Any] | None = None,
) -> str:
    """Execute a text LLM call and record it on an AgentRun."""

    started = time.time()
    output_text = call()
    latency_ms = int((time.time() - started) * 1000)
    run.record_model_call(
        model=model,
        input_text=input_text,
        output_text=output_text,
        latency_ms=latency_ms,
        metadata=metadata,
    )
    return output_text


def trace_openai_chat_completion(
    run: AgentRun,
    *,
    client: Any,
    model: str,
    messages: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
    **create_kwargs: Any,
) -> Any:
    """Call ``client.chat.completions.create`` and record the model call.

    The helper accepts the OpenAI SDK shape without importing OpenAI. Tests and
    host applications can pass any compatible client object.
    """

    started = time.time()
    response = client.chat.completions.create(model=model, messages=messages, **create_kwargs)
    latency_ms = int((time.time() - started) * 1000)
    output_text = extract_response_text(response)
    run.record_model_call(
        model=model,
        input_text=messages_to_text(messages),
        output_text=output_text,
        latency_ms=latency_ms,
        metadata=_merge_metadata(metadata, {"provider": "openai", "api": "chat.completions"}),
    )
    return response


def trace_openai_response(
    run: AgentRun,
    *,
    client: Any,
    model: str,
    input: str | list[Any],
    metadata: dict[str, Any] | None = None,
    **create_kwargs: Any,
) -> Any:
    """Call ``client.responses.create`` and record the model call."""

    started = time.time()
    response = client.responses.create(model=model, input=input, **create_kwargs)
    latency_ms = int((time.time() - started) * 1000)
    run.record_model_call(
        model=model,
        input_text=_value_to_text(input),
        output_text=extract_response_text(response),
        latency_ms=latency_ms,
        metadata=_merge_metadata(metadata, {"provider": "openai", "api": "responses"}),
    )
    return response


def trace_anthropic_message(
    run: AgentRun,
    *,
    client: Any,
    model: str,
    messages: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
    **create_kwargs: Any,
) -> Any:
    """Call ``client.messages.create`` and record the model call."""

    started = time.time()
    response = client.messages.create(model=model, messages=messages, **create_kwargs)
    latency_ms = int((time.time() - started) * 1000)
    run.record_model_call(
        model=model,
        input_text=messages_to_text(messages),
        output_text=extract_response_text(response),
        latency_ms=latency_ms,
        metadata=_merge_metadata(metadata, {"provider": "anthropic", "api": "messages"}),
    )
    return response


def trace_litellm_completion(
    run: AgentRun,
    *,
    completion: Callable[..., Any],
    model: str,
    messages: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
    **completion_kwargs: Any,
) -> Any:
    """Call a LiteLLM-compatible completion function and record the model call."""

    started = time.time()
    response = completion(model=model, messages=messages, **completion_kwargs)
    latency_ms = int((time.time() - started) * 1000)
    run.record_model_call(
        model=model,
        input_text=messages_to_text(messages),
        output_text=extract_response_text(response),
        latency_ms=latency_ms,
        metadata=_merge_metadata(metadata, {"provider": "litellm", "api": "completion"}),
    )
    return response


class TokenSaverCallback:
    """Framework-agnostic callback adapter for Agent frameworks.

    Coding agents can map framework-specific events to these methods.
    """

    def __init__(self, run: AgentRun) -> None:
        self.run = run

    def on_context(self, name: str, content: str, *, kind: str = "text") -> None:
        self.run.add_context(name, content, kind=kind)

    def on_tool_end(
        self,
        name: str,
        *,
        input_text: str = "",
        output_text: str = "",
        latency_ms: int = 0,
        cached: bool = False,
    ) -> None:
        self.run.record_tool_call(
            name,
            input_text=input_text,
            output_text=output_text,
            latency_ms=latency_ms,
            cached=cached,
        )

    def on_llm_end(
        self,
        *,
        model: str,
        input_text: str,
        output_text: str,
        latency_ms: int = 0,
    ) -> None:
        self.run.record_model_call(
            model=model,
            input_text=input_text,
            output_text=output_text,
            latency_ms=latency_ms,
        )

    def on_answer(self, answer: str) -> None:
        self.run.record_answer(answer)


class LangChainTokenSaverCallback(TokenSaverCallback):
    """Dependency-free LangChain/LangGraph callback adapter.

    It implements common callback method names used by LangChain handlers while
    keeping all imports optional. LangGraph applications can attach the same
    handler to model/tool nodes.
    """

    def __init__(self, run: AgentRun) -> None:
        super().__init__(run)
        self._tool_starts: dict[str, tuple[float, str, str]] = {}
        self._llm_starts: dict[str, tuple[float, str, str]] = {}

    def on_llm_start(
        self,
        serialized: dict[str, Any] | None,
        prompts: list[str],
        *,
        run_id: Any = None,
        invocation_params: dict[str, Any] | None = None,
        **_: Any,
    ) -> None:
        key = str(run_id or len(self._llm_starts))
        model = _model_from_serialized(serialized, invocation_params)
        self._llm_starts[key] = (time.time(), model, "\n\n".join(prompts))

    def on_llm_end(self, response: Any, *, run_id: Any = None, **_: Any) -> None:
        key = str(run_id or next(reversed(self._llm_starts), "0"))
        started, model, input_text = self._llm_starts.pop(key, (time.time(), "unknown", ""))
        self.run.record_model_call(
            model=model,
            input_text=input_text,
            output_text=extract_response_text(response),
            latency_ms=int((time.time() - started) * 1000),
            metadata={"framework": "langchain"},
        )

    def on_chat_model_start(
        self,
        serialized: dict[str, Any] | None,
        messages: list[Any],
        *,
        run_id: Any = None,
        invocation_params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        prompts = [_value_to_text(message) for message in messages]
        self.on_llm_start(
            serialized,
            prompts,
            run_id=run_id,
            invocation_params=invocation_params,
            **kwargs,
        )

    def on_tool_start(
        self,
        serialized: dict[str, Any] | None,
        input_str: str,
        *,
        run_id: Any = None,
        name: str | None = None,
        **_: Any,
    ) -> None:
        tool_name = name or _name_from_serialized(serialized) or "unknown_tool"
        self._tool_starts[str(run_id or tool_name)] = (time.time(), tool_name, input_str)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: Any = None,
        name: str | None = None,
        **_: Any,
    ) -> None:
        key = str(run_id or name or "unknown_tool")
        started, started_name, input_text = self._tool_starts.pop(
            key,
            (time.time(), name or key, ""),
        )
        self.run.record_tool_call(
            name or started_name,
            input_text=input_text,
            output_text=_value_to_text(output),
            latency_ms=int((time.time() - started) * 1000),
            metadata={"framework": "langchain"},
        )


def messages_to_text(messages: list[dict[str, Any]]) -> str:
    """Convert chat messages into compact trace text."""

    parts = []
    for message in messages:
        role = message.get("role") or "message"
        content = _value_to_text(message.get("content", ""))
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


def extract_response_text(response: Any) -> str:
    """Best-effort text extraction across OpenAI, Anthropic, LiteLLM, and LC."""

    output_text = _get_attr_or_key(response, "output_text")
    if output_text:
        return str(output_text)

    content = _get_attr_or_key(response, "content")
    if content:
        return _value_to_text(content)

    choices = _get_attr_or_key(response, "choices")
    if choices:
        texts = []
        for choice in choices:
            message = _get_attr_or_key(choice, "message")
            if message is not None:
                texts.append(_value_to_text(_get_attr_or_key(message, "content") or message))
                continue
            texts.append(_value_to_text(_get_attr_or_key(choice, "text") or choice))
        return "\n".join(text for text in texts if text)

    generations = _get_attr_or_key(response, "generations")
    if generations:
        texts = []
        for group in generations:
            items = group if isinstance(group, list) else [group]
            for item in items:
                texts.append(_value_to_text(_get_attr_or_key(item, "text") or item))
        return "\n".join(text for text in texts if text)

    return _value_to_text(response)


def _merge_metadata(base: dict[str, Any] | None, extra: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base or {})
    merged.update(extra)
    return merged


def _get_attr_or_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _value_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_value_to_text(item) for item in value)
    if isinstance(value, dict):
        if "text" in value:
            return _value_to_text(value["text"])
        if "content" in value:
            return _value_to_text(value["content"])
        return " ".join(f"{key}: {_value_to_text(item)}" for key, item in value.items())
    text = _get_attr_or_key(value, "text")
    if text is not None:
        return _value_to_text(text)
    content = _get_attr_or_key(value, "content")
    if content is not None and content is not value:
        return _value_to_text(content)
    return str(value)


def _model_from_serialized(
    serialized: dict[str, Any] | None,
    invocation_params: dict[str, Any] | None,
) -> str:
    params = invocation_params or {}
    for key in ("model", "model_name", "model_id"):
        if params.get(key):
            return str(params[key])
    if serialized:
        kwargs = serialized.get("kwargs") if isinstance(serialized.get("kwargs"), dict) else {}
        for key in ("model", "model_name", "model_id"):
            if kwargs.get(key):
                return str(kwargs[key])
        name = _name_from_serialized(serialized)
        if name:
            return name
    return "unknown"


def _name_from_serialized(serialized: dict[str, Any] | None) -> str:
    if not serialized:
        return ""
    if serialized.get("name"):
        return str(serialized["name"])
    identifier = serialized.get("id")
    if isinstance(identifier, list) and identifier:
        return str(identifier[-1])
    if identifier:
        return str(identifier)
    return ""
