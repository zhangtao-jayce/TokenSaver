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
                run.set_budget(input_tokens=2500, output_tokens=450, latency_ms=1000)
                run.set_quality_requirements(["current_shares", "entry_plan"])
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
                run.record_final_answer("answer " * 900)

            result = run.result
            self.assertIsNotNone(result)
            codes = result["diagnosis"]["finding_codes"]
            self.assertIn("wrong_route_for_task", codes)
            self.assertIn("history_context_waste", codes)
            self.assertIn("repeated_tool_without_cache", codes)
            self.assertIn("dimensions", result["diagnosis"])
            self.assertIn("top_token_consumers", result["diagnosis"])
            self.assertEqual(result["diagnosis"]["budget"]["input_tokens"], 2500)

            store = LocalStore(tmp)
            self.assertEqual(len(store.load_runs()), 1)
            self.assertIn("TokenSaver Run Summary", store.read_latest_report())
            self.assertIn("ROI Dimensions", store.read_latest_report())
            self.assertIn("TokenSaver Repair Brief", store.read_latest_brief())
            self.assertIn("Required Quality Fields", store.read_latest_brief())
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

    def test_goldfinger_like_tool_governance_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorded = record_agent_run(
                {
                    "app": "goldfinger",
                    "channel": "feishu",
                    "user_message": "复盘",
                    "task_type": "stock_agent_message",
                    "route": "goldfinger_react_agent",
                    "tool_calls": [
                        {
                            "name": "read_positions",
                            "input_text": "{}",
                            "output_text": "position_log " * 9000,
                            "metadata": {
                                "mode": "full",
                                "record_count": 120,
                            },
                        }
                    ],
                    "quality_requirements": [
                        "current_shares",
                        "current_avg_cost",
                        "entry_plan",
                        "risk_management",
                    ],
                    "quality_signals": {
                        "missing_required_fields": {"entry_plan": False}
                    },
                    "answer": "当前持仓状态。",
                    "answer_tokens": 50,
                    "latency_ms": 70_000,
                },
                store_dir=tmp,
            )

            codes = recorded["diagnosis"]["finding_codes"]
            self.assertIn("tool_output_too_large", codes)
            self.assertIn("dominant_tool_output", codes)
            self.assertIn("raw_tool_payload", codes)
            self.assertIn("missing_required_quality_field", codes)
            self.assertIn("latency_budget_exceeded", codes)
            self.assertEqual(
                recorded["diagnosis"]["top_token_consumers"][0]["name"],
                "read_positions",
            )

    def test_compare_runs_reports_deltas_and_resolved_findings(self):
        before = {
            "run_id": "before",
            "input_tokens": 36000,
            "output_tokens": 21000,
            "latency_ms": 100000,
            "diagnosis": {
                "roi_score": 40,
                "finding_codes": ["tool_output_too_large", "answer_too_long_for_channel"],
            },
        }
        after = {
            "run_id": "after",
            "input_tokens": 8000,
            "output_tokens": 900,
            "latency_ms": 30000,
            "diagnosis": {"roi_score": 86, "finding_codes": []},
        }

        from tokensaver.store import compare_runs

        comparison = compare_runs(before, after)
        self.assertEqual(comparison["deltas"]["input_tokens"]["delta"], -28000)
        self.assertEqual(comparison["roi_score"]["delta"], 46)
        self.assertIn("tool_output_too_large", comparison["resolved_findings"])


if __name__ == "__main__":
    unittest.main()
