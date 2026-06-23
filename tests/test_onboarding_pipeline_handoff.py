import json
import os
import tempfile
import unittest
from pathlib import Path

from tokensaver import TokenSaver, record_agent_run
from tokensaver.diagnosis import diagnose_run
from tokensaver.install import path_export_command
from tokensaver.profile import template_profile
from tokensaver.store import LocalStore


class OnboardingPipelineHandoffTests(unittest.TestCase):
    def setUp(self):
        self._old_update_env = os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN")
        os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = "0"

    def tearDown(self):
        if self._old_update_env is None:
            os.environ.pop("TOKENSAVER_CHECK_UPDATE_ON_RUN", None)
        else:
            os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = self._old_update_env

    def test_path_export_command_is_copyable_and_shell_quoted(self):
        command = path_export_command("/tmp/Token Saver/bin")

        self.assertEqual(command, "export PATH='/tmp/Token Saver/bin':\"$PATH\"")

    def test_custom_task_type_missing_budget_is_distinct_from_mismatch(self):
        profile = template_profile("research-agent")
        diagnosis = diagnose_run(
            {
                "app": "daily_news",
                "channel": "cli",
                "user_message": "Build today's research digest",
                "caller_task_type": "daily_research",
                "inferred_task_type": "daily_research",
                "task_type": "daily_research",
                "route": "batch",
                "input_tokens": 10,
                "output_tokens": 10,
            },
            profile=profile,
        )

        self.assertIn("task_type_missing_budget", diagnosis["finding_codes"])
        self.assertNotIn("task_type_mismatch", diagnosis["finding_codes"])
        finding = next(
            item for item in diagnosis["findings"] if item["code"] == "task_type_missing_budget"
        )
        self.assertEqual(finding["evidence"]["fallback_budget"], profile["budgets"]["default"])
        self.assertIn("daily_research:", finding["recommendation"])

    def test_explicit_profile_budget_avoids_missing_budget_finding(self):
        profile = template_profile("research-agent")
        profile["budgets"]["daily_research"] = {
            "input_tokens": 20_000,
            "output_tokens": 2_000,
            "latency_ms": 120_000,
        }

        diagnosis = diagnose_run(
            {
                "app": "daily_news",
                "channel": "cli",
                "user_message": "Build today's research digest",
                "caller_task_type": "daily_research",
                "inferred_task_type": "daily_research",
                "task_type": "daily_research",
                "route": "batch",
                "input_tokens": 10,
                "output_tokens": 10,
            },
            profile=profile,
        )

        self.assertNotIn("task_type_missing_budget", diagnosis["finding_codes"])

    def test_sdk_handoff_is_persisted_and_does_not_create_model_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="daily_news", channel="cli", store_dir=tmp)
            with ts.run(
                user_message="Prepare today's digest",
                task_type="daily_research",
                route="batch",
            ) as run:
                run.record_tool_call("rss_fetch", output_text="three items")
                run.add_handoff(
                    agent="codex",
                    input_artifacts=["output/raw.md", "output/filter_task.md"],
                    instruction="Analyze the selected items.",
                    expected_output="output/processed.md",
                    status="prepared",
                    metadata={"item_count": 3},
                )
                run.record_final_answer("Raw digest prepared for Codex.")

            result = run.result
            self.assertIsNotNone(result)
            self.assertEqual(len(result["handoffs"]), 1)
            self.assertEqual(result["handoffs"][0]["mode"], "external_agent_handoff")
            self.assertEqual(result["model_calls"], [])
            self.assertEqual(result["token_usage"]["source"], "estimated")

            store = LocalStore(tmp)
            saved = store.load_runs()[0]
            self.assertEqual(saved["handoffs"][0]["expected_output"], "output/processed.md")
            self.assertIn("External Agent Handoffs", store.read_latest_report())
            self.assertIn("codex", store.read_latest_report())
            self.assertIn("External Agent Handoffs", store.read_latest_brief())
            panel = (Path(tmp) / "panel" / "index.html").read_text(encoding="utf-8")
            self.assertIn("Handoffs", panel)

    def test_external_run_handoffs_are_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorded = record_agent_run(
                {
                    "app": "pipeline",
                    "channel": "cli",
                    "user_message": "Prepare handoff",
                    "task_type": "daily_research",
                    "handoffs": [
                        {
                            "agent": "claude",
                            "input_artifacts": "raw.md",
                            "output_artifacts": ["processed.md"],
                            "status": "completed",
                        }
                    ],
                },
                store_dir=tmp,
            )

            handoff = recorded["handoffs"][0]
            self.assertEqual(handoff["mode"], "external_agent_handoff")
            self.assertEqual(handoff["input_artifacts"], ["raw.md"])
            self.assertEqual(handoff["output_artifacts"], ["processed.md"])
            self.assertEqual(recorded["model_calls"], [])
            saved = json.loads((Path(tmp) / "runs.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(saved["handoffs"], recorded["handoffs"])

    def test_handoff_rejects_unsupported_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            ts = TokenSaver(app="pipeline", store_dir=tmp)
            with self.assertRaises(ValueError):
                with ts.run(user_message="Prepare handoff") as run:
                    run.add_handoff(agent="codex", status="running")


if __name__ == "__main__":
    unittest.main()
