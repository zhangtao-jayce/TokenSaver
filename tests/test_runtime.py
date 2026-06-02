import json
import tempfile
import unittest
from pathlib import Path

from tokensaver import TokenSaver, record_agent_run
from tokensaver.store import LocalStore


class RuntimeTests(unittest.TestCase):
    def test_runtime_trace_writes_summary_and_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="goldfinger", channel="feishu", store_dir=tmp)
            with ts.run(user_message="MU 怎么了？", task_type="quick_quote_check") as run:
                run.set_task(route="deep_stock_research")
                run.add_context("full_history_log", "history " * 3000, kind="history")
                run.record_tool_call(
                    "price",
                    output_text="price payload " * 100,
                    latency_ms=10,
                    cached=False,
                )
                run.record_tool_call(
                    "price",
                    output_text="price payload " * 100,
                    latency_ms=10,
                    cached=False,
                )
                run.record_model_call(
                    model="anthropic/claude-sonnet-4-6",
                    input_text="prompt " * 1000,
                    output_text="answer " * 900,
                    latency_ms=50,
                )
                run.record_answer("answer " * 900)

            result = run.result
            self.assertIsNotNone(result)
            codes = result["diagnosis"]["finding_codes"]
            self.assertIn("wrong_route_for_task", codes)
            self.assertIn("history_context_waste", codes)
            self.assertIn("repeated_tool_without_cache", codes)

            store = LocalStore(tmp)
            self.assertEqual(len(store.load_runs()), 1)
            self.assertIn("TokenSaver Run Summary", store.read_latest_report())
            self.assertIn("TokenSaver Repair Brief", store.read_latest_brief())
            self.assertTrue((Path(tmp) / "panel" / "index.html").exists())

    def test_record_agent_run_normalizes_content_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorded = record_agent_run(
                {
                    "app": "demo",
                    "channel": "feishu",
                    "user_message": "quick check",
                    "task_type": "quick_quote_check",
                    "route": "deep_report",
                    "context_items": [
                        {
                            "name": "conversation_history",
                            "kind": "history",
                            "content": "history " * 3000,
                        }
                    ],
                    "model_calls": [
                        {
                            "model": "anthropic/claude-sonnet-4-6",
                            "input_text": "prompt",
                            "output_text": "answer",
                        }
                    ],
                },
                store_dir=tmp,
            )

            self.assertGreater(recorded["input_tokens"], 0)
            self.assertNotIn("content", recorded["context_items"][0])
            self.assertIn("history_context_waste", recorded["diagnosis"]["finding_codes"])
            path = Path(tmp) / "runs.jsonl"
            saved = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(saved["app"], "demo")


if __name__ == "__main__":
    unittest.main()
