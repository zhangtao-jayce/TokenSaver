import json
import os
import tempfile
import unittest
from pathlib import Path

from tokensaver import TokenSaver, record_agent_run
from tokensaver.profile import template_profile
from tokensaver.store import LocalStore


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self._old_update_env = os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN")
        os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = "0"

    def tearDown(self):
        if self._old_update_env is None:
            os.environ.pop("TOKENSAVER_CHECK_UPDATE_ON_RUN", None)
        else:
            os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = self._old_update_env

    def test_runtime_trace_writes_summary_and_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="demo_agent", channel="chat", store_dir=tmp)
            with ts.run(user_message="Summarize current status.", task_type="quick_question") as run:
                run.set_task(route="deep_research")
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
            self.assertIn("deep_route_for_short_task", codes)
            self.assertIn("history_context_pollution", codes)
            self.assertIn("repeated_tool_call_without_cache", codes)
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
                    "task_type": "quick_question",
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
            self.assertIn("history_context_pollution", recorded["diagnosis"]["finding_codes"])
            path = Path(tmp) / "runs.jsonl"
            saved = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(saved["app"], "demo")

    def test_tool_governance_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorded = record_agent_run(
                {
                    "app": "demo_agent",
                    "channel": "feishu",
                    "user_message": "复盘",
                    "task_type": "quick_question",
                    "route": "default_agent",
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
            self.assertIn("oversized_tool_output", codes)
            self.assertIn("dominant_tool_output", codes)
            self.assertIn("raw_payload_in_default_path", codes)
            self.assertIn("required_field_missing", codes)
            self.assertEqual(
                recorded["diagnosis"]["top_token_consumers"][0]["name"],
                "read_positions",
            )

    def test_root_cause_diagnosis_for_react_loop_and_slow_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            answer = "\n".join(
                [
                    "| 项目 | 判断 |",
                    "| --- | --- |",
                    "| 放量 | 待核验 |",
                    "| 跌幅 | 待核验 |",
                    "| 新闻 | 数据缺口 |",
                    "| 持仓 | 数据缺口 |",
                    "可继续追问：要不要减仓",
                    "可继续追问：风险位在哪里",
                ]
            )
            recorded = record_agent_run(
                {
                    "app": "goldfinger",
                    "channel": "feishu",
                    "user_message": "AVGO放量下跌原因分析",
                    "task_type": "stock_agent_message",
                    "route": "ticker_switch_react_agent",
                    "budget": {
                        "input_tokens": 12000,
                        "output_tokens": 1500,
                        "latency_ms": 60000,
                    },
                    "context_items": [
                        {
                            "name": "system_prompt",
                            "kind": "system_prompt",
                            "tokens": 4798,
                        }
                    ],
                    "model_calls": [
                        {"model": "gpt", "input_tokens": 4974, "output_tokens": 0, "latency_ms": 2867},
                        {"model": "gpt", "input_tokens": 5724, "output_tokens": 23, "latency_ms": 2552},
                        {"model": "gpt", "input_tokens": 5907, "output_tokens": 12, "latency_ms": 2845},
                        {"model": "gpt", "input_tokens": 6325, "output_tokens": 0, "latency_ms": 1631},
                        {"model": "gpt", "input_tokens": 6423, "output_tokens": 896, "latency_ms": 31595},
                    ],
                    "tool_calls": [
                        {
                            "name": "maestro",
                            "latency_ms": 120093,
                            "output_tokens": 9,
                            "success": True,
                        },
                        {
                            "name": "goldscope_investigate",
                            "latency_ms": 9758,
                            "output_tokens": 311,
                        },
                        {
                            "name": "goldscope_investigate",
                            "latency_ms": 0,
                            "output_tokens": 20,
                            "cached": False,
                        },
                    ],
                    "answer": answer,
                    "answer_tokens": 999,
                    "latency_ms": 171757,
                },
                store_dir=tmp,
                profile=template_profile("finance-assistant"),
            )

            codes = recorded["diagnosis"]["finding_codes"]
            self.assertIn("react_loop_token_amplification", codes)
            self.assertIn("oversized_repeated_context_item", codes)
            self.assertIn("expensive_low_value_tool_call", codes)
            self.assertIn("tool_success_mismatch", codes)
            self.assertIn("missing_fallback_for_slow_tool", codes)
            self.assertIn("task_route_mismatch", codes)
            self.assertIn("low_density_answer_section", codes)
            self.assertEqual(
                recorded["diagnosis"]["top_latency_consumers"][0]["name"],
                "maestro",
            )

            store = LocalStore(tmp)
            self.assertIn("Root Causes", store.read_latest_report())
            self.assertIn("Top Latency Consumers", store.read_latest_report())
            self.assertIn("Root Causes", store.read_latest_brief())

    def test_compare_runs_reports_deltas_and_resolved_findings(self):
        before = {
            "run_id": "before",
            "input_tokens": 36000,
            "output_tokens": 21000,
            "latency_ms": 100000,
            "diagnosis": {
                "roi_score": 40,
                "finding_codes": ["oversized_tool_output", "channel_output_over_budget"],
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
        self.assertIn("oversized_tool_output", comparison["resolved_findings"])
        self.assertEqual(comparison["result"], "accepted")

    def test_compare_runs_normalizes_legacy_finding_codes(self):
        before = {
            "run_id": "before",
            "input_tokens": 1000,
            "output_tokens": 1000,
            "diagnosis": {
                "roi_score": 40,
                "finding_codes": ["tool_output_too_large", "wrong_route_for_task"],
            },
        }
        after = {
            "run_id": "after",
            "input_tokens": 800,
            "output_tokens": 800,
            "diagnosis": {"roi_score": 80, "finding_codes": ["deep_route_for_short_task"]},
        }

        from tokensaver.store import compare_runs

        comparison = compare_runs(before, after)
        self.assertIn("oversized_tool_output", comparison["resolved_findings"])
        self.assertIn("deep_route_for_short_task", comparison["unchanged_findings"])

    def test_compare_runs_rejects_quality_regression(self):
        before = {
            "run_id": "before",
            "input_tokens": 36000,
            "output_tokens": 21000,
            "latency_ms": 100000,
            "diagnosis": {"roi_score": 40, "finding_codes": ["oversized_tool_output"]},
        }
        after = {
            "run_id": "after",
            "input_tokens": 8000,
            "output_tokens": 900,
            "latency_ms": 30000,
            "diagnosis": {"roi_score": 86, "finding_codes": ["required_field_missing"]},
        }

        from tokensaver.store import compare_runs

        comparison = compare_runs(before, after)
        self.assertEqual(comparison["result"], "rejected")
        self.assertIn("required_field_missing", comparison["quality_blockers"])


if __name__ == "__main__":
    unittest.main()
