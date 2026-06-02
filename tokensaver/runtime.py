"""Runtime tracing SDK for Agent applications."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from .diagnosis import diagnose_run
from .store import LocalStore
from .task_classifier import classify_task
from .tokenizer import estimate_tokens


class TokenSaver:
    """Local-first runtime tracer for an Agent application."""

    def __init__(
        self,
        *,
        app: str,
        channel: str = "unknown",
        store_dir: str | Path = ".tokensaver",
    ) -> None:
        self.app = app
        self.channel = channel
        self.store = LocalStore(store_dir)

    def run(
        self,
        *,
        user_message: str,
        task_type: str | None = None,
        route: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "AgentRun":
        return AgentRun(
            tokensaver=self,
            user_message=user_message,
            task_type=task_type,
            route=route,
            metadata=metadata or {},
        )


class AgentRun:
    """Mutable trace object for one Agent run."""

    def __init__(
        self,
        *,
        tokensaver: TokenSaver,
        user_message: str,
        task_type: str | None,
        route: str | None,
        metadata: dict[str, Any],
    ) -> None:
        self._tokensaver = tokensaver
        self._started = time.time()
        self._run: dict[str, Any] = {
            "run_id": str(uuid.uuid4()),
            "app": tokensaver.app,
            "channel": tokensaver.channel,
            "user_message": user_message,
            "task_type": task_type or classify_task(user_message).task_type,
            "route": route or "",
            "context_items": [],
            "tool_calls": [],
            "model_calls": [],
            "quality_signals": {},
            "metadata": metadata,
            "answer": "",
            "answer_tokens": 0,
            "started_at": self._started,
        }
        self.result: dict[str, Any] | None = None

    def __enter__(self) -> "AgentRun":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is not None:
            self._run["error"] = str(exc)
        self.finish()

    def set_task(self, *, task_type: str | None = None, route: str | None = None) -> None:
        if task_type:
            self._run["task_type"] = task_type
        if route:
            self._run["route"] = route

    def add_context(self, name: str, content: str, *, kind: str = "text") -> None:
        self._run["context_items"].append(
            {
                "name": name,
                "kind": kind,
                "tokens": estimate_tokens(content),
            }
        )

    def record_tool_call(
        self,
        name: str,
        *,
        input_text: str = "",
        output_text: str = "",
        latency_ms: int = 0,
        cached: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._run["tool_calls"].append(
            {
                "name": name,
                "input_tokens": estimate_tokens(input_text),
                "output_tokens": estimate_tokens(output_text),
                "latency_ms": latency_ms,
                "cached": cached,
                "metadata": metadata or {},
            }
        )

    def record_model_call(
        self,
        *,
        model: str,
        input_text: str,
        output_text: str,
        latency_ms: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._run["model_calls"].append(
            {
                "model": model,
                "input_tokens": estimate_tokens(input_text),
                "output_tokens": estimate_tokens(output_text),
                "latency_ms": latency_ms,
                "metadata": metadata or {},
            }
        )

    def record_answer(self, answer: str) -> None:
        self._run["answer"] = answer
        self._run["answer_tokens"] = estimate_tokens(answer)

    def add_quality_signal(self, name: str, value: Any = True) -> None:
        self._run["quality_signals"][name] = value

    def finish(self) -> dict[str, Any]:
        if self.result is not None:
            return self.result

        ended = time.time()
        self._run["ended_at"] = ended
        self._run["latency_ms"] = int((ended - self._started) * 1000)
        self._run["input_tokens"] = _sum_input_tokens(self._run)
        self._run["output_tokens"] = _sum_output_tokens(self._run)
        self._run["diagnosis"] = diagnose_run(self._run)
        artifacts = self._tokensaver.store.save_run(self._run)
        self._run["artifacts"] = artifacts
        self.result = self._run
        return self._run


def record_agent_run(
    run: dict[str, Any],
    *,
    store_dir: str | Path = ".tokensaver",
) -> dict[str, Any]:
    """Record an externally constructed run trace."""

    normalized = dict(run)
    normalized.setdefault("run_id", str(uuid.uuid4()))
    normalized.setdefault("context_items", [])
    normalized.setdefault("tool_calls", [])
    normalized.setdefault("model_calls", [])
    normalized.setdefault("quality_signals", {})
    normalized.setdefault("metadata", {})
    _normalize_context_items(normalized)
    _normalize_tool_calls(normalized)
    _normalize_model_calls(normalized)
    if "answer_tokens" not in normalized and normalized.get("answer"):
        normalized["answer_tokens"] = estimate_tokens(str(normalized.get("answer") or ""))
    normalized.setdefault("input_tokens", _sum_input_tokens(normalized))
    normalized.setdefault("output_tokens", _sum_output_tokens(normalized))
    normalized["diagnosis"] = diagnose_run(normalized)
    artifacts = LocalStore(store_dir).save_run(normalized)
    normalized["artifacts"] = artifacts
    return normalized


def _sum_input_tokens(run: dict[str, Any]) -> int:
    total = estimate_tokens(str(run.get("user_message") or ""))
    total += sum(int(item.get("tokens") or 0) for item in run.get("context_items") or [])
    total += sum(int(call.get("input_tokens") or 0) for call in run.get("tool_calls") or [])
    total += sum(int(call.get("input_tokens") or 0) for call in run.get("model_calls") or [])
    return total


def _sum_output_tokens(run: dict[str, Any]) -> int:
    total = int(run.get("answer_tokens") or 0)
    total += sum(int(call.get("output_tokens") or 0) for call in run.get("tool_calls") or [])
    total += sum(int(call.get("output_tokens") or 0) for call in run.get("model_calls") or [])
    return total


def _normalize_context_items(run: dict[str, Any]) -> None:
    for item in run.get("context_items") or []:
        if "tokens" not in item:
            item["tokens"] = estimate_tokens(str(item.get("content") or ""))
        item.pop("content", None)


def _normalize_tool_calls(run: dict[str, Any]) -> None:
    for call in run.get("tool_calls") or []:
        if "input_tokens" not in call:
            call["input_tokens"] = estimate_tokens(str(call.get("input_text") or ""))
        if "output_tokens" not in call:
            call["output_tokens"] = estimate_tokens(str(call.get("output_text") or ""))
        call.pop("input_text", None)
        call.pop("output_text", None)


def _normalize_model_calls(run: dict[str, Any]) -> None:
    for call in run.get("model_calls") or []:
        if "input_tokens" not in call:
            call["input_tokens"] = estimate_tokens(str(call.get("input_text") or ""))
        if "output_tokens" not in call:
            call["output_tokens"] = estimate_tokens(str(call.get("output_text") or ""))
        call.pop("input_text", None)
        call.pop("output_text", None)
