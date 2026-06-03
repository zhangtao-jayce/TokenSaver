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
    owner_area: str = "workflow"
    impact: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "owner_area": self.owner_area,
            "impact": self.impact,
        }


_TASK_BUDGETS: dict[str, dict[str, int]] = {
    "quick_quote_check": {"input_tokens": 3_000, "output_tokens": 500, "latency_ms": 20_000},
    "light_qa": {"input_tokens": 3_000, "output_tokens": 500, "latency_ms": 20_000},
    "operation_confirmation": {"input_tokens": 5_000, "output_tokens": 700, "latency_ms": 30_000},
    "intraday_anomaly_attribution": {"input_tokens": 8_000, "output_tokens": 1_000, "latency_ms": 60_000},
    "realtime_analysis": {"input_tokens": 8_000, "output_tokens": 1_000, "latency_ms": 60_000},
    "position_risk_check": {"input_tokens": 8_000, "output_tokens": 1_000, "latency_ms": 60_000},
    "daily_summary": {"input_tokens": 12_000, "output_tokens": 1_500, "latency_ms": 90_000},
    "stock_agent_message": {"input_tokens": 12_000, "output_tokens": 1_500, "latency_ms": 60_000},
    "deep_stock_research": {"input_tokens": 30_000, "output_tokens": 3_000, "latency_ms": 180_000},
    "deep_analysis": {"input_tokens": 30_000, "output_tokens": 3_000, "latency_ms": 180_000},
    "system_debug": {"input_tokens": 12_000, "output_tokens": 1_500, "latency_ms": 90_000},
}

_CHANNEL_TASK_BUDGETS: dict[tuple[str, str], dict[str, int]] = {
    ("feishu", "stock_agent_message"): {
        "input_tokens": 12_000,
        "output_tokens": 1_500,
        "latency_ms": 60_000,
    },
    ("lark", "stock_agent_message"): {
        "input_tokens": 12_000,
        "output_tokens": 1_500,
        "latency_ms": 60_000,
    },
    ("slack", "stock_agent_message"): {
        "input_tokens": 12_000,
        "output_tokens": 1_500,
        "latency_ms": 60_000,
    },
    ("feishu", "quick_quote_check"): {
        "input_tokens": 8_000,
        "output_tokens": 800,
        "latency_ms": 30_000,
    },
    ("report", "deep_stock_research"): {
        "input_tokens": 60_000,
        "output_tokens": 8_000,
        "latency_ms": 300_000,
    },
    ("report", "deep_analysis"): {
        "input_tokens": 60_000,
        "output_tokens": 8_000,
        "latency_ms": 300_000,
    },
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
    answer_tokens = int(run.get("answer_tokens") or 0)
    latency_ms = int(run.get("latency_ms") or 0)
    context_items = list(run.get("context_items") or [])
    tool_calls = list(run.get("tool_calls") or [])
    model_calls = list(run.get("model_calls") or [])

    findings: list[DiagnosisFinding] = []
    budget = _resolve_budget(run, channel=channel, task_type=task_type)
    top_consumers = _top_token_consumers(run)

    if input_tokens > budget["input_tokens"]:
        findings.append(
            DiagnosisFinding(
                code="input_budget_exceeded",
                severity="high",
                message="Input tokens exceed the expected budget for this task type.",
                evidence={
                    "task_type": task_type,
                    "channel": channel,
                    "route": route,
                    "input_tokens": input_tokens,
                    "budget": budget["input_tokens"],
                },
                recommendation="Reduce injected context or route this request to a deeper task type intentionally.",
                owner_area="context/router",
                impact="High input volume increases cost, latency, and context dilution risk.",
            )
        )

    if output_tokens > budget["output_tokens"]:
        findings.append(
            DiagnosisFinding(
                code="output_budget_exceeded",
                severity="medium",
                message="Output tokens exceed the expected budget for this task type.",
                evidence={
                    "task_type": task_type,
                    "channel": channel,
                    "route": route,
                    "output_tokens": output_tokens,
                    "budget": budget["output_tokens"],
                },
                recommendation="Add channel-aware answer length limits or a concise response mode.",
                owner_area="channel",
                impact="Long answers can reduce readability and increase response cost.",
            )
        )

    if latency_ms and latency_ms > budget["latency_ms"]:
        findings.append(
            DiagnosisFinding(
                code="latency_budget_exceeded",
                severity="medium",
                message="Run latency exceeds the expected budget for this channel and task.",
                evidence={
                    "task_type": task_type,
                    "channel": channel,
                    "latency_ms": latency_ms,
                    "budget": budget["latency_ms"],
                },
                recommendation="Review slow tools, deep route selection, and model call count for this workflow.",
                owner_area="workflow",
                impact="High latency is especially costly in chat and realtime Agent workflows.",
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
                owner_area="router",
                impact="Deep workflows spend extra context and latency on requests that should be cheap.",
            )
        )

    channel_answer_tokens = answer_tokens if answer_tokens > 0 else output_tokens
    if channel in _SHORT_CHANNELS and channel_answer_tokens > 1_200:
        severity = "high" if channel_answer_tokens > 5_000 else "medium"
        findings.append(
            DiagnosisFinding(
                code="answer_too_long_for_channel",
                severity=severity,
                message="The answer is long for a short-message channel.",
                evidence={
                    "channel": channel,
                    "answer_tokens": channel_answer_tokens,
                    "warning_threshold": 1_200,
                    "medium_threshold": 2_000,
                    "high_threshold": 5_000,
                },
                recommendation="Limit default channel answers to a short summary unless the user asks to expand.",
                owner_area="channel",
                impact="Short-message channels need concise defaults with expandable details.",
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
                    owner_area="context",
                    impact="Large context items can crowd out more relevant current evidence.",
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
                    owner_area="context",
                    impact="Raw history is often low ROI for simple requests.",
                )
            )

    _add_tool_findings(findings, tool_calls, input_tokens)
    _add_model_findings(findings, model_calls, task_type)
    _add_quality_findings(findings, run, task_type)

    codes = [finding.code for finding in findings]
    dimensions = _score_dimensions(
        findings=findings,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        budget=budget,
    )
    score = _overall_score(dimensions)
    return {
        "roi_score": score,
        "dimensions": dimensions,
        "budget": budget,
        "top_token_consumers": top_consumers,
        "finding_codes": codes,
        "findings": [finding.to_dict() for finding in findings],
        "status": "ok" if not findings else "needs_attention",
    }


def _resolve_budget(run: dict[str, Any], *, channel: str, task_type: str) -> dict[str, int]:
    budget = dict(_TASK_BUDGETS.get(task_type, {
        "input_tokens": 12_000,
        "output_tokens": 1_500,
        "latency_ms": 90_000,
    }))
    budget.update(_CHANNEL_TASK_BUDGETS.get((channel, task_type), {}))
    explicit = run.get("budget") or (run.get("metadata") or {}).get("budget") or {}
    for key in ("input_tokens", "output_tokens", "latency_ms"):
        value = explicit.get(key)
        if value is not None:
            budget[key] = int(value)
    return budget


def _looks_deep_route(route: str) -> bool:
    lowered = route.lower()
    return any(word in lowered for word in _DEEP_ROUTE_WORDS)


def _is_history_or_log(label: str) -> bool:
    return any(word in label for word in ("history", "log", "conversation", "memory"))


def _add_tool_findings(
    findings: list[DiagnosisFinding],
    tool_calls: list[dict[str, Any]],
    input_tokens: int,
) -> None:
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
                    recommendation="Return structured summaries from tools instead of raw large payloads; add summary/detail/full modes where full data is only requested explicitly.",
                    owner_area="tool",
                    impact="Oversized tool payloads are a common source of input cost and context dilution.",
                )
            )
        if input_tokens > 0 and output_tokens / input_tokens >= 0.30:
            findings.append(
                DiagnosisFinding(
                    code="dominant_tool_output",
                    severity="high",
                    message="One tool dominates the run token footprint.",
                    evidence={
                        "tool": name,
                        "output_tokens": output_tokens,
                        "input_tokens": input_tokens,
                        "share_of_input": round(output_tokens / input_tokens, 3),
                    },
                    recommendation="Add tool parameters that return only the fields needed for the current task and channel.",
                    owner_area="tool",
                    impact="Dominant tool outputs usually indicate raw records, logs, or unfiltered JSON.",
                )
            )
        if _looks_raw_payload(call):
            findings.append(
                DiagnosisFinding(
                    code="raw_tool_payload",
                    severity="medium",
                    message="A tool output appears to be a raw or full-detail payload.",
                    evidence={"tool": name, "metadata": call.get("metadata") or {}},
                    recommendation="Expose a compact schema with summary fields, recent items, and an explicit full mode for audit requests.",
                    owner_area="tool/schema",
                    impact="Raw payloads make it hard for the Agent to preserve decision-relevant fields while controlling cost.",
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
                    owner_area="tool",
                    impact="Repeated calls can duplicate latency and tokens inside one run.",
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
                    owner_area="model/router",
                    impact="Strong models are often unnecessary for classification and simple replies.",
                )
            )


def _add_quality_findings(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
    task_type: str,
) -> None:
    quality = run.get("quality_signals") or {}
    required_fields = list(run.get("quality_requirements") or [])
    if quality.get("user_correction"):
        findings.append(
            DiagnosisFinding(
                code="user_correction_signal",
                severity="medium",
                message="The user corrected the answer.",
                evidence={"user_correction": True},
                recommendation="Review missing context, source attribution, or answer format for this task route.",
                owner_area="quality",
                impact="User corrections are direct evidence that cost reduction or routing may have hurt utility.",
            )
        )
    missing_fields = quality.get("missing_required_fields") or []
    if isinstance(missing_fields, dict):
        missing_fields = [field for field, present in missing_fields.items() if not present]
    if missing_fields:
        findings.append(
            DiagnosisFinding(
                code="missing_required_quality_field",
                severity="high",
                message="The answer or compact schema missed required quality fields.",
                evidence={"missing_required_fields": list(missing_fields)},
                recommendation="Restore required quality fields before further token reduction.",
                owner_area="quality/schema",
                impact="Token savings are not acceptable when required decision fields disappear.",
            )
        )
    elif required_fields and not str(run.get("answer") or "").strip():
        findings.append(
            DiagnosisFinding(
                code="quality_fields_not_verified",
                severity="low",
                message="Required quality fields were registered but no final answer was recorded for verification.",
                evidence={"required_fields": required_fields},
                recommendation="Record the final answer or explicit quality signals so TokenSaver can verify quality guardrails.",
                owner_area="quality",
                impact="Unverified quality guardrails make before/after optimization less reliable.",
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
                    owner_area="prompt",
                    impact="Realtime and action-sensitive answers need traceable current evidence.",
                )
            )


def _looks_raw_payload(call: dict[str, Any]) -> bool:
    metadata = call.get("metadata") or {}
    mode = str(metadata.get("mode") or metadata.get("detail_level") or "").lower()
    if mode in {"full", "raw", "debug"}:
        return True
    if bool(metadata.get("raw_payload")):
        return True
    record_count = metadata.get("record_count")
    if record_count is not None:
        try:
            return int(record_count) >= 50
        except (TypeError, ValueError):
            return False
    return False


def _top_token_consumers(run: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    consumers: list[dict[str, Any]] = []
    for item in run.get("context_items") or []:
        consumers.append(
            {
                "kind": "context",
                "name": item.get("name") or "unnamed",
                "tokens": int(item.get("tokens") or 0),
            }
        )
    for call in run.get("tool_calls") or []:
        consumers.append(
            {
                "kind": "tool_output",
                "name": call.get("name") or "unnamed",
                "tokens": int(call.get("output_tokens") or 0),
            }
        )
    for call in run.get("model_calls") or []:
        model = call.get("model") or "unnamed"
        consumers.append(
            {
                "kind": "model_input",
                "name": model,
                "tokens": int(call.get("input_tokens") or 0),
            }
        )
        consumers.append(
            {
                "kind": "model_output",
                "name": model,
                "tokens": int(call.get("output_tokens") or 0),
            }
        )
    if run.get("answer_tokens"):
        consumers.append(
            {
                "kind": "answer",
                "name": "final_answer",
                "tokens": int(run.get("answer_tokens") or 0),
            }
        )
    consumers.sort(key=lambda item: int(item["tokens"]), reverse=True)
    return consumers[:limit]


def _score_dimensions(
    *,
    findings: list[DiagnosisFinding],
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    budget: dict[str, int],
) -> dict[str, int]:
    dimensions = {
        "cost_efficiency": _ratio_score(input_tokens, budget["input_tokens"]),
        "latency_efficiency": _ratio_score(latency_ms, budget["latency_ms"]) if latency_ms else 100,
        "context_precision": 100,
        "output_density": _ratio_score(output_tokens, budget["output_tokens"]),
        "task_fit": 100,
        "quality_risk": 100,
    }
    code_to_dimension = {
        "input_budget_exceeded": "cost_efficiency",
        "tool_output_too_large": "context_precision",
        "dominant_tool_output": "context_precision",
        "raw_tool_payload": "context_precision",
        "context_item_too_large": "context_precision",
        "history_context_waste": "context_precision",
        "output_budget_exceeded": "output_density",
        "answer_too_long_for_channel": "output_density",
        "latency_budget_exceeded": "latency_efficiency",
        "wrong_route_for_task": "task_fit",
        "overpowered_model_for_quick_task": "task_fit",
        "missing_required_quality_field": "quality_risk",
        "quality_fields_not_verified": "quality_risk",
        "missing_source_attribution": "quality_risk",
        "user_correction_signal": "quality_risk",
    }
    for finding in findings:
        dimension = code_to_dimension.get(finding.code)
        if dimension:
            dimensions[dimension] = max(
                0,
                dimensions[dimension] - _severity_penalty(finding.severity),
            )
    return dimensions


def _ratio_score(actual: int, budget: int) -> int:
    if actual <= 0 or budget <= 0:
        return 100
    if actual <= budget:
        return 100
    overage = (actual - budget) / budget
    return max(0, int(100 - min(80, overage * 80)))


def _overall_score(dimensions: dict[str, int]) -> int:
    weights = {
        "cost_efficiency": 0.22,
        "latency_efficiency": 0.12,
        "context_precision": 0.24,
        "output_density": 0.16,
        "task_fit": 0.14,
        "quality_risk": 0.12,
    }
    return int(sum(dimensions[name] * weight for name, weight in weights.items()))


def _has_source_signal(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in ("source", "来源", "according", "as of", "截至"))


def _severity_penalty(severity: str) -> int:
    if severity == "high":
        return 25
    if severity == "medium":
        return 15
    return 5
