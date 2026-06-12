"""Runtime tracing SDK for Agent applications."""

from __future__ import annotations

import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable

from .diagnosis import diagnose_run
from .profile import load_profile
from .store import (
    TRAFFIC_PRODUCTION,
    LocalStore,
    normalize_traffic_type,
)
from .task_classifier import classify_task
from .tokenizer import estimate_tokens

FailureCallback = Callable[[dict[str, Any]], None]


class TokenSaver:
    """Local-first runtime tracer for an Agent application."""

    def __init__(
        self,
        *,
        app: str,
        channel: str = "unknown",
        store_dir: str | Path = ".tokensaver",
        profile_path: str | Path | None = None,
        profile: dict[str, Any] | None = None,
        failure_callback: FailureCallback | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.app = app
        self.channel = channel
        self.failure_callback = failure_callback
        self.logger = logger or logging.getLogger("tokensaver")
        self.store = LocalStore(store_dir, failure_callback=self._report_failure)
        self.profile = profile or load_profile(profile_path)

    def run(
        self,
        *,
        user_message: str,
        task_type: str | None = None,
        route: str | None = None,
        metadata: dict[str, Any] | None = None,
        traffic_type: str = TRAFFIC_PRODUCTION,
    ) -> "AgentRun":
        try:
            return AgentRun(
                tokensaver=self,
                user_message=user_message,
                task_type=task_type,
                route=route,
                metadata=metadata or {},
                traffic_type=traffic_type,
            )
        except Exception as exc:
            self._report_failure(
                {
                    "stage": "run_enter",
                    "error": str(exc),
                    "app": self.app,
                }
            )
            raise

    def mark_deployment(
        self,
        *,
        host_version: str,
        environment: str = "production",
        tokensaver_version: str | None = None,
    ) -> dict[str, Any]:
        return self.store.mark_deployment(
            host_version=host_version,
            environment=environment,
            tokensaver_version=tokensaver_version,
        )

    def health(self) -> dict[str, Any]:
        return self.store.read_health()

    def _report_failure(self, event: dict[str, Any]) -> None:
        payload = {"component": "tokensaver", **event}
        try:
            self.logger.error("TokenSaver integration failure: %s", payload)
        except Exception:
            print(f"TokenSaver integration failure: {payload}", file=sys.stderr)
        if self.failure_callback is None:
            return
        try:
            self.failure_callback(payload)
        except Exception as exc:
            try:
                self.logger.exception("TokenSaver failure callback failed: %s", exc)
            except Exception:
                print(f"TokenSaver failure callback failed: {exc}", file=sys.stderr)


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
        traffic_type: str,
    ) -> None:
        self._tokensaver = tokensaver
        self._started = time.time()
        inferred_task_type = classify_task(user_message).task_type
        self._run: dict[str, Any] = {
            "schema_version": "0.3",
            "run_id": str(uuid.uuid4()),
            "app": tokensaver.app,
            "channel": tokensaver.channel,
            "user_message": user_message,
            "caller_task_type": task_type,
            "inferred_task_type": inferred_task_type,
            "task_type": task_type or inferred_task_type,
            "route": route or "",
            "traffic_type": normalize_traffic_type(traffic_type),
            "context_items": [],
            "tool_calls": [],
            "model_calls": [],
            "budget": {},
            "quality_requirements": [],
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

    def set_budget(
        self,
        *,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        latency_ms: int | None = None,
    ) -> None:
        budget = self._run.setdefault("budget", {})
        if input_tokens is not None:
            budget["input_tokens"] = int(input_tokens)
        if output_tokens is not None:
            budget["output_tokens"] = int(output_tokens)
        if latency_ms is not None:
            budget["latency_ms"] = int(latency_ms)

    def set_quality_requirements(self, required_fields: list[str]) -> None:
        self._run["quality_requirements"] = list(required_fields)

    def add_context(self, name: str, content: str, *, kind: str = "text") -> None:
        try:
            self._run["context_items"].append(
                {
                    "name": name,
                    "kind": kind,
                    "tokens": estimate_tokens(content),
                }
            )
        except Exception as exc:
            self._trace_failure("context_trace", exc)
            raise

    def record_tool_call(
        self,
        name: str,
        *,
        input_text: str = "",
        output_text: str = "",
        latency_ms: int = 0,
        cached: bool = False,
        status: str = "ok",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self._run["tool_calls"].append(
                {
                    "name": name,
                    "input_tokens": estimate_tokens(input_text),
                    "output_tokens": estimate_tokens(output_text),
                    "latency_ms": latency_ms,
                    "cached": cached,
                    "status": status,
                    "metadata": metadata or {},
                }
            )
        except Exception as exc:
            self._trace_failure("tool_trace", exc)
            raise

    def record_model_call(
        self,
        *,
        model: str,
        input_text: str,
        output_text: str,
        latency_ms: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self._run["model_calls"].append(
                {
                    "model": model,
                    "input_tokens": estimate_tokens(input_text),
                    "output_tokens": estimate_tokens(output_text),
                    "latency_ms": latency_ms,
                    "metadata": metadata or {},
                }
            )
        except Exception as exc:
            self._trace_failure("model_trace", exc)
            raise

    def record_answer(self, answer: str) -> None:
        self._run["answer"] = answer
        self._run["answer_tokens"] = estimate_tokens(answer)

    def record_final_answer(self, answer: str, *, channel: str | None = None) -> None:
        if channel:
            self._run["channel"] = channel
        self.record_answer(answer)

    def add_quality_signal(self, name: str, value: Any = True) -> None:
        self._run["quality_signals"][name] = value

    def _trace_failure(self, stage: str, exc: Exception) -> None:
        event = {
            "stage": stage,
            "error": str(exc),
            "run_id": self._run.get("run_id"),
        }
        self._tokensaver.store.record_failure(**event)

    def finish(self) -> dict[str, Any]:
        if self.result is not None:
            return self.result

        ended = time.time()
        try:
            self._run["ended_at"] = ended
            self._run["latency_ms"] = int((ended - self._started) * 1000)
            self._run["input_tokens"] = _sum_input_tokens(self._run)
            self._run["output_tokens"] = _sum_output_tokens(self._run)
            self._run["diagnosis"] = diagnose_run(self._run, profile=self._tokensaver.profile)
            artifacts = self._tokensaver.store.save_run(self._run)
            self._run["artifacts"] = artifacts
            self.result = self._run
            return self._run
        except Exception as exc:
            self._tokensaver._report_failure(
                {
                    "stage": "finish",
                    "error": str(exc),
                    "run_id": self._run.get("run_id"),
                }
            )
            raise


def record_agent_run(
    run: dict[str, Any],
    *,
    store_dir: str | Path = ".tokensaver",
    profile_path: str | Path | None = None,
    profile: dict[str, Any] | None = None,
    failure_callback: FailureCallback | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    """Record an externally constructed run trace."""

    normalized = dict(run)
    normalized.setdefault("schema_version", "0.3")
    normalized.setdefault("run_id", str(uuid.uuid4()))
    normalized["traffic_type"] = normalize_traffic_type(normalized.get("traffic_type"))
    normalized.setdefault("context_items", [])
    normalized.setdefault("tool_calls", [])
    normalized.setdefault("model_calls", [])
    normalized.setdefault("budget", {})
    normalized.setdefault("quality_requirements", [])
    normalized.setdefault("quality_signals", {})
    normalized.setdefault("metadata", {})
    inferred_task_type = classify_task(str(normalized.get("user_message") or "")).task_type
    normalized.setdefault("inferred_task_type", inferred_task_type)
    normalized.setdefault("caller_task_type", normalized.get("task_type"))
    normalized.setdefault("task_type", inferred_task_type)
    _normalize_context_items(normalized)
    _normalize_tool_calls(normalized)
    _normalize_model_calls(normalized)
    if "answer_tokens" not in normalized and normalized.get("answer"):
        normalized["answer_tokens"] = estimate_tokens(str(normalized.get("answer") or ""))
    normalized.setdefault("input_tokens", _sum_input_tokens(normalized))
    normalized.setdefault("output_tokens", _sum_output_tokens(normalized))
    active_profile = profile or load_profile(profile_path)
    normalized["diagnosis"] = diagnose_run(normalized, profile=active_profile)
    reporter = _build_failure_reporter(failure_callback=failure_callback, logger=logger)
    artifacts = LocalStore(store_dir, failure_callback=reporter).save_run(normalized)
    normalized["artifacts"] = artifacts
    return normalized


def mark_deployment(
    *,
    host_version: str,
    environment: str = "production",
    tokensaver_version: str | None = None,
    store_dir: str | Path = ".tokensaver",
) -> dict[str, Any]:
    """Start a new local deployment acceptance cycle."""

    return LocalStore(store_dir).mark_deployment(
        host_version=host_version,
        environment=environment,
        tokensaver_version=tokensaver_version,
    )


def read_health(*, store_dir: str | Path = ".tokensaver") -> dict[str, Any]:
    """Read the local cross-run health artifact."""

    return LocalStore(store_dir).read_health()


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
        call.setdefault("latency_ms", 0)
        call.setdefault("status", "ok" if call.get("success", True) else "failed")
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


def _build_failure_reporter(
    *,
    failure_callback: FailureCallback | None,
    logger: logging.Logger | None,
) -> FailureCallback:
    active_logger = logger or logging.getLogger("tokensaver")

    def report(event: dict[str, Any]) -> None:
        try:
            active_logger.error("TokenSaver integration failure: %s", event)
        except Exception:
            print(f"TokenSaver integration failure: {event}", file=sys.stderr)
        if failure_callback is not None:
            try:
                failure_callback(event)
            except Exception as exc:
                try:
                    active_logger.exception("TokenSaver failure callback failed: %s", exc)
                except Exception:
                    print(f"TokenSaver failure callback failed: {exc}", file=sys.stderr)

    return report
