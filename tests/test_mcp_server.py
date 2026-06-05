import tempfile
import unittest
from pathlib import Path

from tokensaver.mcp_server import handle_request


class McpServerTests(unittest.TestCase):
    def test_tools_list(self):
        response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(response["id"], 1)
        names = [tool["name"] for tool in response["result"]["tools"]]
        self.assertIn("tokensaver.plan_task", names)
        self.assertIn("tokensaver.estimate_tokens", names)
        self.assertIn("tokensaver.init_profile", names)
        self.assertIn("tokensaver.eval_fixtures", names)
        self.assertIn("tokensaver.doctor", names)
        self.assertIn("tokensaver.verify_install", names)

    def test_plan_tool_call(self):
        response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "tokensaver.plan_task",
                    "arguments": {
                        "user_message": "帮我分析 MU 今天为什么突然涨，要不要减仓",
                        "model": "anthropic/claude-sonnet-4-6",
                    },
                },
            }
        )
        text = response["result"]["content"][0]["text"]
        self.assertIn("intraday_anomaly_attribution", text)
        self.assertIn("requires_realtime_data", text)

    def test_runtime_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            record_response = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "tokensaver.record_agent_run",
                        "arguments": {
                            "store_dir": tmp,
                            "run": {
                                "app": "demo_agent",
                                "channel": "chat",
                                "user_message": "Summarize current status.",
                                "task_type": "quick_question",
                                "route": "deep_research",
                                "context_items": [
                                    {
                                        "name": "full_history_log",
                                        "kind": "history",
                                        "content": "history " * 3000,
                                    }
                                ],
                            },
                        },
                    },
                }
            )
            text = record_response["result"]["content"][0]["text"]
            self.assertIn("deep_route_for_short_task", text)

            latest_response = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "tokensaver.get_latest_runs",
                        "arguments": {"store_dir": tmp, "limit": 1},
                    },
                }
            )
            self.assertIn("demo_agent", latest_response["result"]["content"][0]["text"])

            brief_response = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "tokensaver.generate_repair_brief",
                        "arguments": {"store_dir": tmp},
                    },
                }
            )
            self.assertIn("TokenSaver Repair Brief", brief_response["result"]["content"][0]["text"])

    def test_profile_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profile.yaml"
            init_response = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 8,
                    "method": "tools/call",
                    "params": {
                        "name": "tokensaver.init_profile",
                        "arguments": {
                            "template": "support-bot",
                            "output": str(profile_path),
                        },
                    },
                }
            )
            self.assertIn("my_support_bot", init_response["result"]["content"][0]["text"])
            self.assertTrue(profile_path.exists())

            fixtures_path = Path(tmp) / "fixtures.json"
            fixtures_path.write_text(
                """[
  {
    "id": "quick_question_basic",
    "input": "Summarize status.",
    "task_type": "quick_question",
    "expected_required_fields": ["answer"],
    "run": {
      "task_type": "quick_question",
      "answer": "ok",
      "answer_tokens": 1
    }
  }
]""",
                encoding="utf-8",
            )
            eval_response = handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "tools/call",
                    "params": {
                        "name": "tokensaver.eval_fixtures",
                        "arguments": {
                            "fixtures_path": str(fixtures_path),
                            "profile_path": str(profile_path),
                        },
                    },
                }
            )
            self.assertIn('"result": "accepted"', eval_response["result"]["content"][0]["text"])

    def test_install_tools(self):
        version_response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {
                    "name": "tokensaver.get_version",
                    "arguments": {"verbose": False},
                },
            }
        )
        self.assertIn("python_executable", version_response["result"]["content"][0]["text"])

        command_response = handle_request(
            {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "tools/call",
                "params": {
                    "name": "tokensaver.upgrade_command",
                    "arguments": {"commit": "abc1234"},
                },
            }
        )
        self.assertIn("@abc1234", command_response["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
