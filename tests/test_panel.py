import os
import tempfile
import unittest
from pathlib import Path

from tokensaver.runtime import record_agent_run


class PanelGuiTests(unittest.TestCase):
    def setUp(self):
        self._old_update_env = os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN")
        os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = "0"

    def tearDown(self):
        if self._old_update_env is None:
            os.environ.pop("TOKENSAVER_CHECK_UPDATE_ON_RUN", None)
        else:
            os.environ["TOKENSAVER_CHECK_UPDATE_ON_RUN"] = self._old_update_env

    def test_panel_renders_local_health_report_with_repair_cta(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_agent_run(
                {
                    "app": "demo_agent",
                    "channel": "chat",
                    "user_message": "Summarize status.",
                    "task_type": "quick_question",
                    "route": "deep_research",
                    "context_items": [
                        {
                            "name": "full_history_log",
                            "kind": "history",
                            "content": "history " * 4000,
                        }
                    ],
                    "tool_calls": [
                        {
                            "name": "search",
                            "output_text": "payload " * 700,
                            "latency_ms": 2500,
                            "cached": False,
                        },
                        {
                            "name": "search",
                            "output_text": "payload",
                            "latency_ms": 100,
                            "cached": False,
                        },
                    ],
                    "model_calls": [
                        {
                            "model": "anthropic/claude-sonnet-4-6",
                            "input_text": "prompt " * 2000,
                            "output_text": "answer " * 120,
                            "latency_ms": 800,
                        }
                    ],
                    "answer": "answer " * 120,
                    "latency_ms": 3400,
                },
                store_dir=tmp,
            )

            html = (Path(tmp) / "panel" / "index.html").read_text(encoding="utf-8")
            self.assertIn("TokenSaver Local ROI Report", html)
            self.assertIn("All data stays local", html)
            self.assertIn("Cost Overview", html)
            self.assertIn("Top Waste", html)
            self.assertIn("Largest Context", html)
            self.assertIn("Largest Tool Output", html)
            self.assertIn("Slowest Tool", html)
            self.assertIn("Findings", html)
            self.assertIn("deep_route_for_short_task", html)
            self.assertIn("Repair Brief", html)
            self.assertIn("Copy Full Brief", html)
            self.assertIn("Most Important Next Steps", html)
            self.assertIn("Recent Runs", html)
            self.assertIn("Most common findings", html)
            self.assertIn("function copyBrief()", html)


if __name__ == "__main__":
    unittest.main()
