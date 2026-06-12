import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tokensaver import TokenSaver, mark_deployment, read_health, record_agent_run
from tokensaver.cli import main
from tokensaver.diagnosis import diagnose_health, diagnose_run
from tokensaver.install import doctor
from tokensaver.store import (
    TRAFFIC_DEPLOYMENT,
    TRAFFIC_PRODUCTION,
    TRAFFIC_SMOKE,
    LocalStore,
    normalize_traffic_type,
)


def goldfinger_run(**overrides):
    run = {
        "run_id": "goldfinger-real-1",
        "app": "goldfinger",
        "channel": "feishu",
        "user_message": "检查 WDC 持仓和下一步计划",
        "caller_task_type": "stock_agent_message",
        "inferred_task_type": "stock_agent_message",
        "task_type": "stock_agent_message",
        "route": "position_review",
        "traffic_type": TRAFFIC_PRODUCTION,
        "metadata": {
            "host_version": "goldfinger-2.4.0",
            "tokensaver_version": "0.6.1",
            "environment": "production",
        },
        "context_items": [{"name": "position", "kind": "portfolio", "tokens": 120}],
        "tool_calls": [
            {
                "name": "price",
                "input_tokens": 10,
                "output_tokens": 20,
                "latency_ms": 12,
                "status": "ok",
            }
        ],
        "model_calls": [
            {
                "model": "small-model",
                "input_tokens": 200,
                "output_tokens": 80,
                "latency_ms": 100,
            }
        ],
        "quality_requirements": ["conclusion", "next_action"],
        "quality_signals": {"conclusion": True, "next_action": True},
        "answer": "结论：继续持有。下一步：观察风险位。",
        "answer_tokens": 30,
        "input_tokens": 330,
        "output_tokens": 130,
        "latency_ms": 150,
    }
    run.update(overrides)
    return run


class TrafficTests(unittest.TestCase):
    def setUp(self):
        self.old_update = os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN")
        os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = "0"

    def tearDown(self):
        if self.old_update is None:
            os.environ.pop("TOKENSAVER_CHECK_UPDATE_ON_RUN", None)
        else:
            os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = self.old_update

    def test_01_real_generates_latest_real(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(), store_dir=tmp)
            self.assertTrue((Path(tmp) / "reports" / "latest_real.md").exists())

    def test_02_smoke_generates_latest_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(traffic_type=TRAFFIC_SMOKE), store_dir=tmp)
            self.assertTrue((Path(tmp) / "reports" / "latest_smoke.md").exists())

    def test_03_smoke_does_not_overwrite_latest_real(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(run_id="real", answer="real answer"), store_dir=tmp)
            before = (Path(tmp) / "reports" / "latest.md").read_text()
            record_agent_run(
                goldfinger_run(run_id="smoke", traffic_type=TRAFFIC_SMOKE, answer="smoke answer"),
                store_dir=tmp,
            )
            self.assertEqual(before, (Path(tmp) / "reports" / "latest.md").read_text())

    def test_04_no_real_keeps_generic_latest_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(traffic_type=TRAFFIC_SMOKE), store_dir=tmp)
            self.assertFalse((Path(tmp) / "reports" / "latest.md").exists())

    def test_05_deployment_audit_is_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(traffic_type=TRAFFIC_DEPLOYMENT), store_dir=tmp)
            self.assertTrue((Path(tmp) / "reports" / "latest_deployment.md").exists())

    def test_06_latest_by_route_separates_traffic(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(run_id="real"), store_dir=tmp)
            record_agent_run(goldfinger_run(run_id="smoke", traffic_type=TRAFFIC_SMOKE), store_dir=tmp)
            index = LocalStore(tmp).latest_by_route()
            self.assertEqual(len(index), 2)

    def test_07_legacy_traffic_defaults_to_real(self):
        self.assertEqual(normalize_traffic_type(None), TRAFFIC_PRODUCTION)

    def test_08_cli_latest_selects_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(run_id="smoke", traffic_type=TRAFFIC_SMOKE), store_dir=tmp)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                main(["latest", "--store-dir", tmp, "--kind", "run", "--traffic", "smoke"])
            self.assertEqual(json.loads(output.getvalue())["run_id"], "smoke")


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.old_update = os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN")
        os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = "0"

    def tearDown(self):
        if self.old_update is None:
            os.environ.pop("TOKENSAVER_CHECK_UPDATE_ON_RUN", None)
        else:
            os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = self.old_update

    def test_09_success_updates_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(), store_dir=tmp)
            health = read_health(store_dir=tmp)
            self.assertEqual(health["last_success_run_id"], "goldfinger-real-1")

    def test_10_failure_increments_total_and_consecutive(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalStore(tmp)
            store.record_failure(stage="runs_write", error="denied")
            health = store.read_health()
            self.assertEqual(health["failure_count"], 1)
            self.assertEqual(health["consecutive_failure_count"], 1)

    def test_11_success_resets_only_consecutive(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalStore(tmp)
            store.record_failure(stage="runs_write", error="denied")
            record_agent_run(goldfinger_run(), store_dir=tmp)
            health = store.read_health()
            self.assertEqual(health["failure_count"], 1)
            self.assertEqual(health["consecutive_failure_count"], 0)

    def test_12_write_latency_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(), store_dir=tmp)
            self.assertGreaterEqual(read_health(store_dir=tmp)["last_trace_write_latency_ms"], 0)

    def test_13_stale_real_trace_finding(self):
        old = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        codes = [item["code"] for item in diagnose_health({"last_real_run_at": old})]
        self.assertIn("trace_stale", codes)

    def test_14_awaiting_deployment_finding(self):
        codes = [
            item["code"]
            for item in diagnose_health({"deployment_acceptance": {"status": "awaiting"}})
        ]
        self.assertIn("no_real_run_after_deploy", codes)

    def test_15_trace_write_failed_finding(self):
        codes = [item["code"] for item in diagnose_health({"consecutive_failure_count": 2})]
        self.assertIn("trace_write_failed", codes)

    def test_16_trace_write_slow_finding(self):
        codes = [item["code"] for item in diagnose_health({"last_trace_write_latency_ms": 1500})]
        self.assertIn("trace_write_slow", codes)

    def test_17_health_atomic_write_leaves_no_temp_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            LocalStore(tmp).record_failure(stage="test", error="test")
            self.assertFalse(list(Path(tmp).glob("*.tmp")))


class CompletenessTests(unittest.TestCase):
    def test_18_quality_signals_absent(self):
        run = goldfinger_run()
        run.pop("quality_signals")
        finding = _finding(diagnose_run(run), "quality_signals_missing")
        self.assertEqual(finding["evidence"]["state"], "absent")

    def test_19_quality_signals_empty(self):
        finding = _finding(
            diagnose_run(goldfinger_run(quality_signals={})),
            "quality_signals_missing",
        )
        self.assertEqual(finding["evidence"]["state"], "empty")

    def test_20_deployment_metadata_missing(self):
        codes = diagnose_run(goldfinger_run(metadata={}))["finding_codes"]
        self.assertIn("deployment_metadata_missing", codes)

    def test_21_final_answer_absent(self):
        run = goldfinger_run()
        run.pop("answer")
        finding = _finding(diagnose_run(run), "final_answer_missing")
        self.assertEqual(finding["evidence"]["state"], "absent")

    def test_22_final_answer_empty(self):
        finding = _finding(diagnose_run(goldfinger_run(answer="")), "final_answer_missing")
        self.assertEqual(finding["evidence"]["state"], "empty")

    def test_23_tool_metadata_incomplete(self):
        run = goldfinger_run(tool_calls=[{"name": "price"}])
        codes = diagnose_run(run)["finding_codes"]
        self.assertIn("tool_metadata_incomplete", codes)

    def test_24_zero_tool_values_are_not_missing(self):
        run = goldfinger_run(
            tool_calls=[
                {
                    "name": "cache",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "latency_ms": 0,
                    "status": "ok",
                }
            ]
        )
        self.assertNotIn("tool_metadata_incomplete", diagnose_run(run)["finding_codes"])

    def test_25_task_type_mismatch(self):
        run = goldfinger_run(caller_task_type="quick_question")
        self.assertIn("task_type_mismatch", diagnose_run(run)["finding_codes"])


class AcceptanceFailureAndGuiTests(unittest.TestCase):
    def setUp(self):
        self.old_update = os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN")
        os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = "0"

    def tearDown(self):
        if self.old_update is None:
            os.environ.pop("TOKENSAVER_CHECK_UPDATE_ON_RUN", None)
        else:
            os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = self.old_update

    def test_26_marker_starts_awaiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = mark_deployment(host_version="2.4.0", store_dir=tmp)
            self.assertEqual(marker["status"], "awaiting")

    def test_27_smoke_cannot_pass_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_deployment(host_version="2.4.0", store_dir=tmp)
            record_agent_run(goldfinger_run(traffic_type=TRAFFIC_SMOKE), store_dir=tmp)
            self.assertEqual(read_health(store_dir=tmp)["deployment_acceptance"]["status"], "awaiting")

    def test_28_deployment_audit_cannot_pass_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_deployment(host_version="2.4.0", store_dir=tmp)
            record_agent_run(goldfinger_run(traffic_type=TRAFFIC_DEPLOYMENT), store_dir=tmp)
            self.assertEqual(read_health(store_dir=tmp)["deployment_acceptance"]["status"], "awaiting")

    def test_29_complete_real_passes_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_deployment(host_version="2.4.0", store_dir=tmp)
            record_agent_run(goldfinger_run(), store_dir=tmp)
            self.assertEqual(read_health(store_dir=tmp)["deployment_acceptance"]["status"], "passed")

    def test_30_incomplete_real_fails_with_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_deployment(host_version="2.4.0", store_dir=tmp)
            record_agent_run(goldfinger_run(metadata={}, answer="", quality_signals={}), store_dir=tmp)
            acceptance = read_health(store_dir=tmp)["deployment_acceptance"]
            self.assertEqual(acceptance["status"], "failed")
            self.assertIn("final_answer", acceptance["missing_fields"])

    def test_31_new_deployment_resets_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_deployment(host_version="2.4.0", store_dir=tmp)
            record_agent_run(goldfinger_run(), store_dir=tmp)
            marker = mark_deployment(host_version="2.5.0", store_dir=tmp)
            self.assertEqual(marker["status"], "awaiting")

    def test_32_failure_hook_receives_runs_write_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            events = []
            Path(tmp, "runs.jsonl").mkdir()
            with self.assertRaises(OSError):
                record_agent_run(goldfinger_run(), store_dir=tmp, failure_callback=events.append)
            self.assertTrue(events)
            self.assertIn("runs_write", events[-1]["stage"])

    def test_33_doctor_preserves_runtime_and_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            LocalStore(Path(tmp) / ".tokensaver").record_failure(stage="finish", error="boom")
            with mock.patch("tokensaver.install._pip_available", return_value=False):
                result = doctor(project_dir=tmp, check_remote=False)
            categories = {item["category"] for item in result["findings"]}
            self.assertIn("runtime", categories)
            self.assertIn("environment", categories)

    def test_34_gui_defaults_to_real(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(answer="real content"), store_dir=tmp)
            record_agent_run(
                goldfinger_run(traffic_type=TRAFFIC_SMOKE, answer="smoke content"),
                store_dir=tmp,
            )
            html = (Path(tmp) / "panel" / "index.html").read_text()
            self.assertIn("Real", html)
            self.assertNotIn("smoke content", html)

    def test_35_gui_empty_state_without_real(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(traffic_type=TRAFFIC_SMOKE), store_dir=tmp)
            html = (Path(tmp) / "panel" / "index.html").read_text()
            self.assertIn("No production traffic yet", html)

    def test_36_panel_renders_health_acceptance_and_traffic(self):
        with tempfile.TemporaryDirectory() as tmp:
            mark_deployment(host_version="2.4.0", store_dir=tmp)
            record_agent_run(goldfinger_run(), store_dir=tmp)
            html = (Path(tmp) / "panel" / "index.html").read_text()
            self.assertIn("Production Health", html)
            self.assertIn("Deployment Acceptance", html)
            self.assertIn("Environment", html)

    def test_37_cli_health_json_has_required_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(), store_dir=tmp)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(
                    ["health", "--store-dir", tmp, "--project-dir", tmp, "--json"]
                )
            result = json.loads(output.getvalue())
            self.assertIn(code, (0, 1))
            self.assertIn("runtime", result)
            self.assertIn("environment", result)
            self.assertIn("deployment_acceptance", result)

    def test_38_trends_isolate_versions_and_traffic(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(goldfinger_run(), store_dir=tmp)
            record_agent_run(
                goldfinger_run(
                    run_id="smoke",
                    traffic_type=TRAFFIC_SMOKE,
                    metadata={
                        "host_version": "goldfinger-2.5.0",
                        "tokensaver_version": "0.6.1",
                        "environment": "staging",
                    },
                ),
                store_dir=tmp,
            )
            self.assertEqual(len(LocalStore(tmp).trend_summary()), 2)

    def test_39_tool_governance_aggregates_cost_latency_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = goldfinger_run()
            run["tool_calls"][0]["status"] = "failed"
            record_agent_run(run, store_dir=tmp)
            item = LocalStore(tmp).tool_governance()[0]
            self.assertEqual(item["failure_rate"], 1.0)
            self.assertGreater(item["avg_output_tokens"], 0)

    def test_40_report_write_failure_is_visible(self):
        self._assert_artifact_failure_visible("latest_real.md")

    def test_41_brief_write_failure_is_visible(self):
        self._assert_artifact_failure_visible("latest_real.md", directory="briefs")

    def test_42_panel_write_failure_is_visible(self):
        self._assert_artifact_failure_visible("real.html")

    def test_43_health_write_failure_is_visible(self):
        self._assert_artifact_failure_visible("health.json")

    def test_44_index_write_failure_is_visible(self):
        self._assert_artifact_failure_visible("latest_by_route.json")

    def test_45_failure_callback_error_has_stderr_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalStore(tmp, failure_callback=lambda _event: 1 / 0)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                store.record_failure(stage="test", error="boom")
            self.assertIn("failure callback failed", stderr.getvalue())

    def _assert_artifact_failure_visible(self, filename, directory=None):
        with tempfile.TemporaryDirectory() as tmp:
            events = []
            store = LocalStore(tmp, failure_callback=events.append)
            original = LocalStore._atomic_write_text

            def fail_selected(active_store, path, text):
                if path.name == filename and (directory is None or path.parent.name == directory):
                    error = OSError(f"cannot write {path.name}")
                    error.tokensaver_stage = f"artifact_write:{path.name}"
                    raise error
                return original(active_store, path, text)

            with mock.patch.object(LocalStore, "_atomic_write_text", new=fail_selected):
                with self.assertRaises(OSError):
                    store.save_run(goldfinger_run())
            self.assertTrue(events)
            self.assertEqual(events[-1]["stage"], f"artifact_write:{filename}")


def _finding(diagnosis, code):
    return next(item for item in diagnosis["findings"] if item["code"] == code)


if __name__ == "__main__":
    unittest.main()
