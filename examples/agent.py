"""Minimal generic TokenSaver integration example."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tokensaver import TokenSaver
from tokensaver.integrations import trace_llm_call


tokensaver = TokenSaver(app="my_agent", channel="chat")


def handle_message(message: str) -> str:
    with tokensaver.run(user_message=message, task_type="quick_question") as run:
        run.set_task(route="deep_research")
        run.add_context("conversation_history", "history " * 3000, kind="history")
        run.add_context("records", "current records relevant to the request", kind="tool_result")

        prompt = f"Answer this request: {message}"
        answer = trace_llm_call(
            run,
            model="anthropic/claude-sonnet-4-6",
            input_text=prompt,
            call=lambda: "Current status needs a concise answer with evidence and next action.",
        )
        run.record_answer(answer)
        return answer


if __name__ == "__main__":
    print(handle_message("Summarize the current status."))
