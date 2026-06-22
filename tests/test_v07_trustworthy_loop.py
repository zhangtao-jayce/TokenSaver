import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone

from tokensaver import TokenSaver
from tokensaver.cli import main
from tokensaver.diagnosis import diagnose_health, diagnose_run
from tokensaver.integrations import extract_token_usage
from tokensaver.runtime import record_agent_run
from tokensaver.store import LocalStore, compare_run_groups


def _version_run(version: str, run_id: str, value: int, *, schema: str = "0.4") -> dict:
    return {
        "schema_version": schema,
        "run_id": run_id,
        "app": "agent",
        "channel": "chat",
        "task_type": "deep_analysis",
        "route": "research",
        "input_tokens": value,
        "output_tokens": value // 10,
        "latency_ms": value * 2,
        "answer_tokens": value // 20,
        "token_usage": {
            "billed_model_input_tokens": value,
            "billed_model_output_tokens": value // 10,
            "final_answer_tokens": value // 20,
        },
        "tool_calls": [{"name": "search"}],
        "quality_signals": {"verified": True},
        "metadata": {"host_version": version},
    }


class TrustworthyTokenAccountingTests(unittest.TestCase):
    def setUp(self):
        self._old_update_env = os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN")
        os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = "0"

    def tearDown(self):
        if self._old_update_env is None:
            os.environ.pop("TOKENSAVER_CHECK_UPDATE_ON_RUN", None)
        else:
            os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = self._old_update_env

    def test_model_output_does_not_double_count_tool_or_final_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="agent", store_dir=tmp)
            with ts.run(user_message="analyze") as run:
                run.record_model_call(
                    model="model",
                    input_text="ignored",
                    output_text="ignored",
                    input_tokens=100,
                    output_tokens=20,
                    reasoning_tokens=5,
                    tool_schema_tokens=40,
                )
                run.record_tool_call("search", input_text="a b c d", output_text="e f g h")
                run.record_final_answer("same final model answer")

            result = run.result
            self.assertEqual(result["schema_version"], "0.4")
            self.assertEqual(result["input_tokens"], 100)
            self.assertEqual(result["output_tokens"], 20)
            self.assertEqual(result["token_usage"]["billed_model_output_tokens"], 20)
            self.assertGreater(result["token_usage"]["tool_payload_tokens"], 0)
            self.assertGreater(result["token_usage"]["final_answer_tokens"], 0)
            self.assertEqual(result["token_usage"]["reasoning_tokens"], 5)
            self.assertEqual(result["token_usage"]["tool_schema_tokens"], 40)
            self.assertEqual(result["token_usage"]["source"], "provider")

    def test_provider_usage_normalization(self):
        usage = extract_token_usage(
            {
                "usage": {
                    "prompt_tokens": 123,
                    "completion_tokens": 45,
                    "completion_tokens_details": {"reasoning_tokens": 9},
                }
            }
        )
        self.assertEqual(
            usage,
            {
                "input_tokens": 123,
                "output_tokens": 45,
                "reasoning_tokens": 9,
                "usage_source": "provider",
            },
        )

    def test_tool_semantics_are_first_class_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="agent", store_dir=tmp)
            with ts.run(user_message="query") as run:
                run.record_tool_call(
                    "market_data",
                    transport_success=True,
                    semantic_success=False,
                    result_quality="unusable",
                    error_type="upstream_unavailable",
                    fallback_used=True,
                )
                run.record_final_answer("fallback")
            call = run.result["tool_calls"][0]
            self.assertTrue(call["transport_success"])
            self.assertFalse(call["semantic_success"])
            self.assertEqual(call["error_type"], "upstream_unavailable")
            self.assertIn("tool_success_mismatch", run.result["diagnosis"]["finding_codes"])

    def test_tool_surface_cost_findings(self):
        run = _version_run("A", "surface", 1000)
        run["model_calls"] = [
            {
                "input_tokens": 1000,
                "output_tokens": 100,
                "tool_schema_tokens": 5000,
                "metadata": {"exposed_tool_count": 37},
            }
        ]
        run["token_usage"]["tool_schema_tokens"] = 5000
        codes = diagnose_run(run)["finding_codes"]
        self.assertIn("oversized_tool_surface", codes)
        self.assertIn("unused_tool_schema_cost", codes)

    def test_schema_03_external_trace_remains_recordable(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = record_agent_run(
                {
                    "schema_version": "0.3",
                    "run_id": "legacy",
                    "user_message": "legacy",
                    "input_tokens": 50,
                    "output_tokens": 10,
                    "answer_tokens": 5,
                },
                store_dir=tmp,
            )
            self.assertEqual(result["schema_version"], "0.3")
            self.assertEqual(result["token_usage"]["billed_model_output_tokens"], 10)

    def test_schema_04_external_trace_uses_semantic_token_totals(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = record_agent_run(
                {
                    "schema_version": "0.4",
                    "run_id": "external-v04",
                    "user_message": "external",
                    "token_usage": {
                        "billed_model_input_tokens": 70,
                        "billed_model_output_tokens": 12,
                        "final_answer_tokens": 4,
                        "source": "provider",
                    },
                },
                store_dir=tmp,
            )
            self.assertEqual(result["input_tokens"], 70)
            self.assertEqual(result["output_tokens"], 12)
            self.assertEqual(result["answer_tokens"], 4)


class TrafficAwareHealthTests(unittest.TestCase):
    def test_idle_without_new_host_traffic_is_not_high_risk(self):
        old = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        findings = diagnose_health(
            {
                "last_real_run_at": old,
                "last_host_request_at": old,
                "last_trace_finished_at": old,
                "untraced_request_count": 0,
            }
        )
        codes = [item["code"] for item in findings]
        self.assertIn("idle_no_traffic", codes)
        self.assertNotIn("trace_stale", codes)

    def test_untraced_host_request_is_pipeline_broken(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="agent", store_dir=tmp)
            ts.record_host_request(request_id="request-1")
            health = ts.health()
            self.assertEqual(health["untraced_request_count"], 1)
            self.assertIn("trace_pipeline_broken", [item["code"] for item in diagnose_health(health)])

    def test_registered_request_is_reconciled_by_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="agent", store_dir=tmp)
            request_id = ts.record_host_request(request_id="request-1")
            with ts.run(user_message="hello", request_id=request_id) as run:
                run.record_final_answer("hello")
            health = ts.health()
            self.assertEqual(health["untraced_request_count"], 0)
            self.assertTrue(health["last_trace_started_at"])
            self.assertTrue(health["last_trace_finished_at"])


class VersionGroupComparisonTests(unittest.TestCase):
    def test_version_groups_report_percentiles_and_improvement(self):
        runs = []
        for index, value in enumerate((1000, 1100, 1200)):
            runs.append(_version_run("A", f"a-{index}", value))
        for index, value in enumerate((500, 550, 600)):
            runs.append(_version_run("B", f"b-{index}", value))
        result = compare_run_groups(runs, baseline="A", candidate="B")
        self.assertEqual(result["baseline_runs"], 3)
        self.assertEqual(result["candidate_runs"], 3)
        self.assertEqual(result["groups"][0]["baseline"]["input_tokens"]["p50"], 1100)
        self.assertEqual(result["groups"][0]["candidate"]["input_tokens"]["p95"], 600)
        self.assertEqual(result["groups"][0]["conclusion"], "improved")

    def test_small_groups_do_not_claim_improvement(self):
        result = compare_run_groups(
            [_version_run("A", "a", 1000), _version_run("B", "b", 500)],
            baseline="A",
            candidate="B",
        )
        self.assertEqual(result["groups"][0]["sample_status"], "insufficient_data")
        self.assertEqual(result["groups"][0]["conclusion"], "insufficient_data")

    def test_compare_cli_supports_host_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalStore(tmp)
            for index, value in enumerate((1000, 1100, 1200)):
                store.save_run(_version_run("A", f"a-{index}", value))
            for index, value in enumerate((500, 550, 600)):
                store.save_run(_version_run("B", f"b-{index}", value))
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(
                    [
                        "compare",
                        "--store-dir",
                        tmp,
                        "--baseline",
                        "A",
                        "--candidate",
                        "B",
                        "--group-by",
                        "task_type,route",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["groups"][0]["conclusion"], "improved")


if __name__ == "__main__":
    unittest.main()
