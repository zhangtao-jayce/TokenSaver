import unittest

from tokensaver.planner import plan_task
from tokensaver.task_classifier import classify_task
from tokensaver.tokenizer import estimate_tokens


class PlannerTests(unittest.TestCase):
    def test_estimate_tokens_handles_mixed_text(self):
        self.assertGreater(estimate_tokens("hello world"), 0)
        self.assertGreaterEqual(estimate_tokens("帮我分析 MU 今天为什么突然涨"), 8)

    def test_classifies_intraday_trade_question(self):
        result = classify_task("MU 刚刚为什么突然拉升，要不要减仓？")
        self.assertEqual(result.task_type, "intraday_anomaly_attribution")
        self.assertGreater(result.confidence, 0.8)

    def test_plan_task_flags_realtime_context_risk(self):
        plan = plan_task(
            user_message="MU 刚刚为什么突然拉升，要不要减仓？",
            model="anthropic/claude-sonnet-4-6",
            context_items=[
                {
                    "name": "conversation_history",
                    "kind": "history",
                    "content": "上一轮 SNDK 分析摘要 " * 200,
                },
                {
                    "name": "current_price",
                    "kind": "price",
                    "content": "MU current price 123.45, SOXX +1.2%",
                },
            ],
        )

        data = plan.to_dict()
        self.assertEqual(data["task_type"], "intraday_anomaly_attribution")
        self.assertEqual(data["mode"], "multi_model_suggested")
        self.assertIsNotNone(data["estimated_cost_usd"])
        self.assertIn("requires_realtime_data", data["risks"])
        self.assertTrue(
            any(risk.startswith("history_contamination_possible") for risk in data["risks"])
        )
        self.assertIn("current_price", data["recommended_context"])


if __name__ == "__main__":
    unittest.main()

