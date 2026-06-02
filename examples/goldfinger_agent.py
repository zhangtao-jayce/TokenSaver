"""Minimal Goldfinger-like TokenSaver integration example."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tokensaver import TokenSaver
from tokensaver.integrations import trace_llm_call


tokensaver = TokenSaver(app="goldfinger", channel="feishu")


def handle_message(message: str) -> str:
    with tokensaver.run(user_message=message, task_type="quick_quote_check") as run:
        run.set_task(route="deep_stock_research")
        run.add_context("price", "MU current price and intraday move", kind="market_data")
        run.add_context("full_history_log", "history " * 3000, kind="history")

        prompt = f"Answer this Feishu question: {message}"
        answer = trace_llm_call(
            run,
            model="anthropic/claude-sonnet-4-6",
            input_text=prompt,
            call=lambda: "MU needs a concise answer with source attribution.",
        )
        run.record_answer(answer)
        return answer


if __name__ == "__main__":
    print(handle_message("MU 怎么了？"))
