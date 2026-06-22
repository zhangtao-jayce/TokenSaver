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
        request_id: str | None = None,
    ) -> "AgentRun":
        try:
            return AgentRun(
                tokensaver=self,
                user_message=user_message,
                task_type=task_type,
                route=route,
                metadata=metadata or {},
                traffic_type=traffic_type,
                request_id=request_id,
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

    def record_host_request(self, *, request_id: str | None = None) -> str:
        """Register a host request before tracing starts.

        Hosts that can observe their request entrypoint should call this before
        creating an AgentRun. Passing the returned id to ``run`` lets health
        distinguish idle traffic from an untraced request.
        """

        active_request_id = request_id or str(uuid.uuid4())
        self.store.record_host_request(active_request_id)
        return active_request_id

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
        request_id: str | None,
    ) -> None:
        self._tokensaver = tokensaver
        self._started = time.time()
        inferred_task_type = classify_task(user_message).task_type
        self._run: dict[str, Any] = {
            "schema_version": "0.4",
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
            "request_id": request_id or "",
        }
        self.result: dict[str, Any] | None = None
        self._tokensaver.store.record_trace_started(
            run_id=str(self._run["run_id"]),
            request_id=request_id,
        )

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
        transport_success: bool | None = None,
        semantic_success: bool | None = None,
        result_quality: str | float | None = None,
        error_type: str | None = None,
        fallback_used: bool = False,
    ) -> None:
        try:
            call = {
                    "name": name,
                    "input_tokens": estimate_tokens(input_text),
                    "output_tokens": estimate_tokens(output_text),
                    "latency_ms": latency_ms,
                    "cached": cached,
                    "status": status,
                    "metadata": metadata or {},
                    "fallback_used": bool(fallback_used),
                }
            if transport_success is not None:
                call["transport_success"] = bool(transport_success)
            if semantic_success is not None:
                call["semantic_success"] = bool(semantic_success)
            if result_quality is not None:
                call["result_quality"] = result_quality
            if error_type:
                call["error_type"] = error_type
            self._run["tool_calls"].append(call)
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
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        reasoning_tokens: int = 0,
        tool_schema_tokens: int = 0,
        usage_source: str | None = None,
    ) -> None:
        try:
            measured_input = int(input_tokens) if input_tokens is not None else estimate_tokens(input_text)
            measured_output = int(output_tokens) if output_tokens is not None else estimate_tokens(output_text)
            self._run["model_calls"].append(
                {
                    "model": model,
                    "input_tokens": measured_input,
                    "output_tokens": measured_output,
                    "reasoning_tokens": int(reasoning_tokens),
                    "tool_schema_tokens": int(tool_schema_tokens),
                    "usage_source": usage_source or (
                        "provider"
                        if input_tokens is not None and output_tokens is not None
                        else "estimated"
                        if input_tokens is None and output_tokens is None
                        else "mixed"
                    ),
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
            self._run["token_usage"] = _build_token_usage(self._run)
            self._run["diagnosis"] = diagnose_run(self._run, profile=self._tokensaver.profile)
            artifacts = self._tokensaver.store.save_run(self._run)
            self._run["artifacts"] = artifacts
            self.result = self._run
            self._tokensaver.store.record_trace_finished(
                run_id=str(self._run.get("run_id") or ""),
                request_id=str(self._run.get("request_id") or "") or None,
            )
            return self._run
        except Exception as exc:
            try:
                self._tokensaver.store.record_trace_finished(
                    run_id=str(self._run.get("run_id") or ""),
                    request_id=str(self._run.get("request_id") or "") or None,
                )
            except Exception:
                pass
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
    supplied_usage = normalized.get("token_usage") or {}
    if "input_tokens" not in normalized and "billed_model_input_tokens" in supplied_usage:
        normalized["input_tokens"] = int(supplied_usage.get("billed_model_input_tokens") or 0)
    if "output_tokens" not in normalized and "billed_model_output_tokens" in supplied_usage:
        normalized["output_tokens"] = int(supplied_usage.get("billed_model_output_tokens") or 0)
    if "answer_tokens" not in normalized and "final_answer_tokens" in supplied_usage:
        normalized["answer_tokens"] = int(supplied_usage.get("final_answer_tokens") or 0)
    if "answer_tokens" not in normalized and normalized.get("answer"):
        normalized["answer_tokens"] = estimate_tokens(str(normalized.get("answer") or ""))
    normalized.setdefault("input_tokens", _sum_input_tokens(normalized))
    normalized.setdefault("output_tokens", _sum_output_tokens(normalized))
    normalized.setdefault("token_usage", _build_token_usage(normalized))
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
    model_calls = run.get("model_calls") or []
    if model_calls:
        return sum(int(call.get("input_tokens") or 0) for call in model_calls)
    total = estimate_tokens(str(run.get("user_message") or ""))
    total += sum(int(item.get("tokens") or 0) for item in run.get("context_items") or [])
    return total


def _sum_output_tokens(run: dict[str, Any]) -> int:
    model_calls = run.get("model_calls") or []
    if model_calls:
        return sum(int(call.get("output_tokens") or 0) for call in model_calls)
    return int(run.get("answer_tokens") or 0)


def _build_token_usage(run: dict[str, Any]) -> dict[str, Any]:
    model_calls = list(run.get("model_calls") or [])
    sources = {str(call.get("usage_source") or "estimated") for call in model_calls}
    if not sources:
        source = "estimated"
    elif sources == {"provider"}:
        source = "provider"
    elif len(sources) == 1:
        source = next(iter(sources))
    else:
        source = "mixed"
    model_call_count = len(model_calls)
    repeated_context = sum(
        int(item.get("tokens") or 0) * max(model_call_count - 1, 0)
        for item in run.get("context_items") or []
        if int(item.get("tokens") or 0) > 0
    )
    return {
        "billed_model_input_tokens": (
            sum(int(call.get("input_tokens") or 0) for call in model_calls)
            if model_calls
            else int(run.get("input_tokens") or 0)
        ),
        "billed_model_output_tokens": (
            sum(int(call.get("output_tokens") or 0) for call in model_calls)
            if model_calls
            else int(run.get("output_tokens") or 0)
        ),
        "tool_payload_tokens": sum(
            int(call.get("input_tokens") or 0) + int(call.get("output_tokens") or 0)
            for call in run.get("tool_calls") or []
        ),
        "final_answer_tokens": int(run.get("answer_tokens") or 0),
        "reasoning_tokens": sum(int(call.get("reasoning_tokens") or 0) for call in model_calls),
        "repeated_context_tokens": repeated_context,
        "tool_schema_tokens": sum(int(call.get("tool_schema_tokens") or 0) for call in model_calls),
        "source": source,
    }


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
