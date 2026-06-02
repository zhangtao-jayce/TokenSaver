"""Rule-based runtime ROI diagnosis for Agent runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiagnosisFinding:
    code: str
    severity: str
    message: str
    evidence: dict[str, Any]
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
        }


_TASK_BUDGETS: dict[str, dict[str, int]] = {
    "quick_quote_check": {"input": 3_000, "output": 500},
    "light_qa": {"input": 3_000, "output": 500},
    "operation_confirmation": {"input": 5_000, "output": 700},
    "intraday_anomaly_attribution": {"input": 8_000, "output": 1_000},
    "realtime_analysis": {"input": 8_000, "output": 1_000},
    "position_risk_check": {"input": 8_000, "output": 1_000},
    "daily_summary": {"input": 12_000, "output": 1_500},
    "deep_stock_research": {"input": 30_000, "output": 3_000},
    "deep_analysis": {"input": 30_000, "output": 3_000},
    "system_debug": {"input": 12_000, "output": 1_500},
}

_SHORT_CHANNELS = {"feishu", "slack", "wechat", "lark"}
_DEEP_ROUTE_WORDS = ("deep", "research", "maestro", "investigate", "report")
_QUICK_TASKS = {"quick_quote_check", "light_qa"}
_SENSITIVE_TASKS = {
    "intraday_anomaly_attribution",
    "realtime_analysis",
    "position_risk_check",
    "operation_confirmation",
}


def diagnose_run(run: dict[str, Any]) -> dict[str, Any]:
    """Diagnose one Agent run using deterministic local rules."""

    task_type = str(run.get("task_type") or "unknown")
    route = str(run.get("route") or "")
    channel = str(run.get("channel") or "").lower()
    input_tokens = int(run.get("input_tokens") or 0)
    output_tokens = int(run.get("output_tokens") or 0)
    context_items = list(run.get("context_items") or [])
    tool_calls = list(run.get("tool_calls") or [])
    model_calls = list(run.get("model_calls") or [])

    findings: list[DiagnosisFinding] = []
    budget = _TASK_BUDGETS.get(task_type, {"input": 12_000, "output": 1_500})

    if input_tokens > budget["input"]:
        findings.append(
            DiagnosisFinding(
                code="input_budget_exceeded",
                severity="high",
                message="Input tokens exceed the expected budget for this task type.",
                evidence={
                    "task_type": task_type,
                    "input_tokens": input_tokens,
                    "budget": budget["input"],
                },
                recommendation="Reduce injected context or route this request to a deeper task type intentionally.",
            )
        )

    if output_tokens > budget["output"]:
        findings.append(
            DiagnosisFinding(
                code="output_budget_exceeded",
                severity="medium",
                message="Output tokens exceed the expected budget for this task type.",
                evidence={
                    "task_type": task_type,
                    "output_tokens": output_tokens,
                    "budget": budget["output"],
                },
                recommendation="Add channel-aware answer length limits or a concise response mode.",
            )
        )

    if task_type in _QUICK_TASKS and _looks_deep_route(route):
        findings.append(
            DiagnosisFinding(
                code="wrong_route_for_task",
                severity="high",
                message="A short task appears to have used a deep workflow route.",
                evidence={"task_type": task_type, "route": route},
                recommendation="Add or tighten a quick route that avoids deep research context and tools.",
            )
        )

    if channel in _SHORT_CHANNELS and output_tokens > 700:
        findings.append(
            DiagnosisFinding(
                code="answer_too_long_for_channel",
                severity="medium",
                message="The answer is long for a short-message channel.",
                evidence={"channel": channel, "output_tokens": output_tokens},
                recommendation="Limit default channel answers to a short summary unless the user asks to expand.",
            )
        )

    for item in context_items:
        name = str(item.get("name") or "unnamed")
        kind = str(item.get("kind") or "").lower()
        tokens = int(item.get("tokens") or 0)
        label = f"{name} {kind}".lower()
        if tokens > 8_000:
            findings.append(
                DiagnosisFinding(
                    code="context_item_too_large",
                    severity="high",
                    message="One context item is very large.",
                    evidence={"context": name, "tokens": tokens},
                    recommendation="Replace raw context with a task-specific summary or top relevant slices.",
                )
            )
        if task_type in _QUICK_TASKS and tokens > 2_000 and _is_history_or_log(label):
            findings.append(
                DiagnosisFinding(
                    code="history_context_waste",
                    severity="high",
                    message="History or log context is large for a quick task.",
                    evidence={"context": name, "tokens": tokens, "task_type": task_type},
                    recommendation="Use a rolling summary for quick tasks instead of raw history or logs.",
                )
            )

    _add_tool_findings(findings, tool_calls)
    _add_model_findings(findings, model_calls, task_type)
    _add_quality_findings(findings, run, task_type)

    codes = [finding.code for finding in findings]
    score = max(0, 100 - sum(_severity_penalty(f.severity) for f in findings))
    return {
        "roi_score": score,
        "finding_codes": codes,
        "findings": [finding.to_dict() for finding in findings],
        "status": "ok" if not findings else "needs_attention",
    }


def _looks_deep_route(route: str) -> bool:
    lowered = route.lower()
    return any(word in lowered for word in _DEEP_ROUTE_WORDS)


def _is_history_or_log(label: str) -> bool:
    return any(word in label for word in ("history", "log", "conversation", "memory"))


def _add_tool_findings(findings: list[DiagnosisFinding], tool_calls: list[dict[str, Any]]) -> None:
    seen: dict[str, int] = {}
    for call in tool_calls:
        name = str(call.get("name") or "unnamed")
        seen[name] = seen.get(name, 0) + 1
        output_tokens = int(call.get("output_tokens") or 0)
        cached = bool(call.get("cached"))
        if output_tokens > 4_000:
            findings.append(
                DiagnosisFinding(
                    code="tool_output_too_large",
                    severity="medium",
                    message="A tool returned a large output.",
                    evidence={"tool": name, "output_tokens": output_tokens},
                    recommendation="Return structured summaries from tools instead of raw large payloads.",
                )
            )
        if seen[name] > 1 and not cached:
            findings.append(
                DiagnosisFinding(
                    code="repeated_tool_without_cache",
                    severity="medium",
                    message="A tool was called repeatedly without cache evidence.",
                    evidence={"tool": name, "calls": seen[name]},
                    recommendation="Add a short TTL cache or reuse the previous tool result within the run.",
                )
            )


def _add_model_findings(
    findings: list[DiagnosisFinding],
    model_calls: list[dict[str, Any]],
    task_type: str,
) -> None:
    if task_type not in _QUICK_TASKS:
        return
    for call in model_calls:
        model = str(call.get("model") or "").lower()
        if any(word in model for word in ("opus", "sonnet", "gpt-4.1")):
            findings.append(
                DiagnosisFinding(
                    code="overpowered_model_for_quick_task",
                    severity="medium",
                    message="A quick task used a strong model.",
                    evidence={"task_type": task_type, "model": call.get("model")},
                    recommendation="Use rules or a cheaper model for quick routing and short answers.",
                )
            )


def _add_quality_findings(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
    task_type: str,
) -> None:
    quality = run.get("quality_signals") or {}
    if quality.get("user_correction"):
        findings.append(
            DiagnosisFinding(
                code="user_correction_signal",
                severity="medium",
                message="The user corrected the answer.",
                evidence={"user_correction": True},
                recommendation="Review missing context, source attribution, or answer format for this task route.",
            )
        )
    if task_type in _SENSITIVE_TASKS:
        evidence = str(run.get("answer") or "") + " " + str(run.get("metadata") or {})
        if not _has_source_signal(evidence):
            findings.append(
                DiagnosisFinding(
                    code="missing_source_attribution",
                    severity="medium",
                    message="A sensitive or realtime task lacks obvious source attribution.",
                    evidence={"task_type": task_type},
                    recommendation="Include source/time attribution for realtime or action-sensitive answers.",
                )
            )


def _has_source_signal(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ("source", "来源", "according", "as of", "截至"))


def _severity_penalty(severity: str) -> int:
    if severity == "high":
        return 25
    if severity == "medium":
        return 15
    return 5

