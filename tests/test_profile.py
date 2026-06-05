import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tokensaver.cli import main
from tokensaver.diagnosis import diagnose_run
from tokensaver.eval import evaluate_fixtures
from tokensaver.profile import load_profile, template_profile, write_profile_template


class ProfileTests(unittest.TestCase):
    def test_write_and_load_profile_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".tokensaver" / "profile.yaml"
            write_profile_template(path, template="support-bot")

            profile = load_profile(path)
            self.assertEqual(profile["app"], "my_support_bot")
            self.assertIn("quick_question", profile["required_fields"])

    def test_domain_templates_exist_without_custom_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            for template, app in {
                "finance-assistant": "my_finance_assistant",
                "legal-assistant": "my_legal_assistant",
                "crm-agent": "my_crm_agent",
            }.items():
                path = Path(tmp) / f"{template}.yaml"
                write_profile_template(path, template=template)
                profile = load_profile(path)
                self.assertEqual(profile["app"], app)
                self.assertTrue(profile["required_fields"])

    def test_profile_budget_and_required_fields_drive_diagnosis(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.yaml"
            path.write_text(
                "\n".join(
                    [
                        "app: demo",
                        "budgets:",
                        "  quick_question:",
                        "    input_tokens: 100",
                        "    output_tokens: 50",
                        "    latency_ms: 1000",
                        "required_fields:",
                        "  quick_question:",
                        "    - conclusion",
                        "    - next_action",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            diagnosis = diagnose_run(
                {
                    "task_type": "quick_question",
                    "input_tokens": 200,
                    "output_tokens": 20,
                    "quality_signals": {"missing_required_fields": ["next_action"]},
                },
                profile=load_profile(path),
            )

            self.assertEqual(diagnosis["budget"]["input_tokens"], 100)
            self.assertIn("input_budget_exceeded", diagnosis["finding_codes"])
            self.assertIn("required_field_missing", diagnosis["finding_codes"])
            self.assertEqual(diagnosis["quality_guardrail_fields"], ["conclusion", "next_action"])

    def test_intent_patterns_are_profile_driven(self):
        run = {
            "user_message": "AVGO放量下跌原因分析",
            "task_type": "stock_agent_message",
            "route": "ticker_switch_react_agent",
        }

        default_diagnosis = diagnose_run(run)
        finance_diagnosis = diagnose_run(run, profile=template_profile("finance-assistant"))

        self.assertNotIn("task_route_mismatch", default_diagnosis["finding_codes"])
        self.assertIn("task_route_mismatch", finance_diagnosis["finding_codes"])

    def test_cli_init_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "profile.yaml"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["init-profile", "--template", "coding-agent", "--output", str(output)])

            self.assertEqual(code, 0)
            data = load_profile(output)
            self.assertEqual(data["app"], "my_coding_agent")

    def test_evaluate_fixtures_rejects_missing_required_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixtures.json"
            path.write_text(
                """[
  {
    "id": "quick_question_basic",
    "input": "Summarize status.",
    "task_type": "quick_question",
    "expected_required_fields": ["conclusion"],
    "run": {
      "task_type": "quick_question",
      "quality_signals": {
        "missing_required_fields": ["conclusion"]
      }
    }
  }
]""",
                encoding="utf-8",
            )

            result = evaluate_fixtures(path)

            self.assertEqual(result["result"], "rejected")
            self.assertEqual(result["cases"][0]["failures"], ["required_field_missing"])


if __name__ == "__main__":
    unittest.main()
