"""Small dependency-free integration helpers.

These helpers are intentionally generic. They give coding agents simple
patterns to wrap LLM calls or adapt framework callbacks without TokenSaver
depending on any specific Agent framework.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .runtime import AgentRun


def trace_llm_call(
    run: AgentRun,
    *,
    model: str,
    input_text: str,
    call: Callable[[], str],
    metadata: dict[str, Any] | None = None,
) -> str:
    """Execute a text LLM call and record it on an AgentRun."""

    started = time.time()
    output_text = call()
    latency_ms = int((time.time() - started) * 1000)
    run.record_model_call(
        model=model,
        input_text=input_text,
        output_text=output_text,
        latency_ms=latency_ms,
        metadata=metadata,
    )
    return output_text


class TokenSaverCallback:
    """Framework-agnostic callback adapter for Agent frameworks.

    Coding agents can map framework-specific events to these methods.
    """

    def __init__(self, run: AgentRun) -> None:
        self.run = run

    def on_context(self, name: str, content: str, *, kind: str = "text") -> None:
        self.run.add_context(name, content, kind=kind)

    def on_tool_end(
        self,
        name: str,
        *,
        input_text: str = "",
        output_text: str = "",
        latency_ms: int = 0,
        cached: bool = False,
    ) -> None:
        self.run.record_tool_call(
            name,
            input_text=input_text,
            output_text=output_text,
            latency_ms=latency_ms,
            cached=cached,
        )

    def on_llm_end(
        self,
        *,
        model: str,
        input_text: str,
        output_text: str,
        latency_ms: int = 0,
    ) -> None:
        self.run.record_model_call(
            model=model,
            input_text=input_text,
            output_text=output_text,
            latency_ms=latency_ms,
        )

    def on_answer(self, answer: str) -> None:
        self.run.record_answer(answer)

