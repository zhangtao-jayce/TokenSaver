"""Rule-based runtime ROI diagnosis for Agent runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .profile import load_profile, profile_required_fields


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


def diagnose_run(run: dict[str, Any], *, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """Diagnose one Agent run using deterministic local rules."""

    profile = profile or load_profile()
    task_type = str(run.get("task_type") or "unknown")
    route = str(run.get("route") or "")
    channel = str(run.get("channel") or "").lower()
    token_usage = run.get("token_usage") or {}
    input_tokens = int(token_usage.get("billed_model_input_tokens", run.get("input_tokens")) or 0)
    output_tokens = int(token_usage.get("billed_model_output_tokens", run.get("output_tokens")) or 0)
    answer_tokens = int(token_usage.get("final_answer_tokens", run.get("answer_tokens")) or 0)
    latency_ms = int(run.get("latency_ms") or 0)
    context_items = list(run.get("context_items") or [])
    tool_calls = list(run.get("tool_calls") or [])
    model_calls = list(run.get("model_calls") or [])
    thresholds = dict(profile.get("thresholds") or {})
    quick_tasks = {str(item) for item in profile.get("quick_tasks") or []}
    short_channels = {str(item).lower() for item in profile.get("short_channels") or []}
    sensitive_tasks = {str(item) for item in profile.get("sensitive_tasks") or []}

    findings: list[DiagnosisFinding] = []
    budget = _resolve_budget(run, channel=channel, task_type=task_type, profile=profile)
    top_consumers = _top_token_consumers(run)
    top_latency_consumers = _top_latency_consumers(run)

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

    if task_type in quick_tasks and _looks_deep_route(route, profile=profile):
        findings.append(
            DiagnosisFinding(
                code="deep_route_for_short_task",
                severity="high",
                message="A short task appears to have used a deep workflow route.",
                evidence={"task_type": task_type, "route": route},
                recommendation="Add or tighten a quick route that avoids deep research context and tools.",
                owner_area="router",
                impact="Deep workflows spend extra context and latency on requests that should be cheap.",
            )
        )

    channel_answer_tokens = answer_tokens if answer_tokens > 0 else output_tokens
    short_threshold = int(thresholds.get("short_channel_answer_tokens") or 1_200)
    short_high_threshold = int(thresholds.get("short_channel_answer_high_tokens") or 5_000)
    if channel in short_channels and channel_answer_tokens > short_threshold:
        severity = "high" if channel_answer_tokens > short_high_threshold else "medium"
        findings.append(
            DiagnosisFinding(
                code="channel_output_over_budget",
                severity=severity,
                message="The answer is long for a short-message channel.",
                evidence={
                    "channel": channel,
                    "answer_tokens": channel_answer_tokens,
                    "warning_threshold": short_threshold,
                    "high_threshold": short_high_threshold,
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
        if tokens > int(thresholds.get("large_context_item_tokens") or 8_000):
            findings.append(
                DiagnosisFinding(
                    code="oversized_context_item",
                    severity="high",
                    message="One context item is very large.",
                    evidence={"context": name, "tokens": tokens},
                    recommendation="Replace raw context with a task-specific summary or top relevant slices.",
                    owner_area="context",
                    impact="Large context items can crowd out more relevant current evidence.",
                )
            )
        if (
            task_type in quick_tasks
            and tokens > int(thresholds.get("quick_history_context_tokens") or 2_000)
            and _is_history_or_log(label)
        ):
            findings.append(
                DiagnosisFinding(
                    code="history_context_pollution",
                    severity="high",
                    message="History or log context is large for a quick task.",
                    evidence={"context": name, "tokens": tokens, "task_type": task_type},
                    recommendation="Use a rolling summary for quick tasks instead of raw history or logs.",
                    owner_area="context",
                    impact="Raw history is often low ROI for simple requests.",
            )
        )

    _add_react_context_findings(
        findings,
        run,
        budget=budget,
        profile=profile,
    )
    _add_tool_findings(findings, tool_calls, input_tokens, profile=profile)
    _add_tool_surface_findings(findings, run, profile=profile)
    _add_latency_tool_findings(
        findings,
        tool_calls,
        latency_ms=latency_ms,
        budget=budget,
        profile=profile,
    )
    _add_model_findings(findings, model_calls, task_type, quick_tasks=quick_tasks)
    _add_route_findings(findings, run, task_type=task_type, route=route, profile=profile)
    _add_quality_findings(
        findings,
        run,
        task_type,
        channel=channel,
        short_channels=short_channels,
        sensitive_tasks=sensitive_tasks,
        profile=profile,
    )
    _add_trace_completeness_findings(findings, run)
    _add_task_type_mismatch_finding(findings, run, profile=profile)
    _add_task_type_missing_budget_finding(findings, run, profile=profile)

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
        "top_latency_consumers": top_latency_consumers,
        "root_causes": _root_causes(findings),
        "quality_guardrail_fields": profile_required_fields(profile, task_type),
        "finding_codes": codes,
        "findings": [finding.to_dict() for finding in findings],
        "status": "ok" if not findings else "needs_attention",
    }


def diagnose_health(
    health: dict[str, Any],
    *,
    stale_after_seconds: int = 86_400,
) -> list[dict[str, Any]]:
    findings: list[DiagnosisFinding] = []
    untraced = int(health.get("untraced_request_count") or 0)
    traffic_aware = "last_host_request_at" in health
    if untraced > 0:
        findings.append(
            DiagnosisFinding(
                code="trace_pipeline_broken",
                severity="high",
                message="Host requests were observed without corresponding trace starts.",
                evidence={
                    "untraced_request_count": untraced,
                    "last_host_request_at": health.get("last_host_request_at"),
                    "last_trace_started_at": health.get("last_trace_started_at"),
                },
                recommendation="Verify that every host request enters TokenSaver.run() and passes the registered request_id.",
                owner_area="integration/runtime",
            )
        )
    last_real = _parse_datetime(health.get("last_real_run_at"))
    if last_real is not None:
        age_seconds = int((datetime.now(timezone.utc) - last_real).total_seconds())
        if age_seconds > stale_after_seconds and not traffic_aware:
            findings.append(
                DiagnosisFinding(
                    code="trace_stale",
                    severity="high",
                    message="The latest production trace is stale.",
                    evidence={"last_real_run_at": health.get("last_real_run_at"), "age_seconds": age_seconds},
                    recommendation="Verify that production requests still initialize and finish TokenSaver tracing.",
                    owner_area="integration/runtime",
                )
            )
        elif age_seconds > stale_after_seconds and untraced == 0:
            last_host = _parse_datetime(health.get("last_host_request_at"))
            last_finished = _parse_datetime(health.get("last_trace_finished_at"))
            if last_host is None or (last_finished is not None and last_host <= last_finished):
                findings.append(
                    DiagnosisFinding(
                        code="idle_no_traffic",
                        severity="info",
                        message="Production traces are old, but no newer host traffic is waiting to be traced.",
                        evidence={
                            "last_real_run_at": health.get("last_real_run_at"),
                            "last_host_request_at": health.get("last_host_request_at"),
                            "age_seconds": age_seconds,
                        },
                        recommendation="No tracing repair is required unless host traffic resumes without traces.",
                        owner_area="integration/runtime",
                    )
                )
    acceptance = health.get("deployment_acceptance") or {}
    if acceptance.get("status") == "awaiting":
        findings.append(
            DiagnosisFinding(
                code="no_real_run_after_deploy",
                severity="high",
                message="No production user run has passed deployment acceptance yet.",
                evidence={"deployed_at": acceptance.get("deployed_at")},
                recommendation="Send one real production request and inspect its acceptance result.",
                owner_area="deployment",
            )
        )
    if int(health.get("consecutive_failure_count") or 0) > 0:
        findings.append(
            DiagnosisFinding(
                code="trace_write_failed",
                severity="high",
                message="Recent TokenSaver trace persistence failed.",
                evidence={
                    "consecutive_failure_count": health.get("consecutive_failure_count"),
                    "last_error": health.get("last_error"),
                },
                recommendation="Fix the recorded persistence stage and confirm a successful production trace resets consecutive failures.",
                owner_area="integration/runtime",
            )
        )
    latency = float(health.get("last_trace_write_latency_ms") or 0)
    if latency > 1_000:
        findings.append(
            DiagnosisFinding(
                code="trace_write_slow",
                severity="medium",
                message="The latest trace write was slow.",
                evidence={"last_trace_write_latency_ms": latency, "threshold_ms": 1000},
                recommendation="Inspect filesystem latency and reduce synchronous artifact work on the request path.",
                owner_area="storage/runtime",
            )
        )
    return [finding.to_dict() for finding in findings]


def _add_trace_completeness_findings(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
) -> None:
    if "quality_signals" not in run:
        findings.append(_missing_finding("quality_signals_missing", "quality_signals", "absent"))
    elif not isinstance(run.get("quality_signals"), dict) or not run.get("quality_signals"):
        findings.append(_missing_finding("quality_signals_missing", "quality_signals", "empty"))

    metadata = run.get("metadata")
    missing_metadata: list[dict[str, str]] = []
    if not isinstance(metadata, dict):
        missing_metadata.append({"field": "metadata", "state": "absent_or_invalid"})
    else:
        for field in ("host_version", "tokensaver_version", "environment"):
            if field not in metadata:
                missing_metadata.append({"field": field, "state": "absent"})
            elif metadata.get(field) in (None, ""):
                missing_metadata.append({"field": field, "state": "empty"})
    if missing_metadata:
        findings.append(
            DiagnosisFinding(
                code="deployment_metadata_missing",
                severity="medium",
                message="Deployment metadata is incomplete.",
                evidence={"missing": missing_metadata},
                recommendation="Record host_version, tokensaver_version, and environment in run metadata.",
                owner_area="integration/schema",
                impact="Deployment acceptance and version regression analysis need explicit version metadata.",
            )
        )

    if "answer" not in run:
        answer_state = "absent"
    elif not str(run.get("answer") or "").strip():
        answer_state = "empty"
    else:
        answer_state = ""
    if answer_state:
        findings.append(
            DiagnosisFinding(
                code="final_answer_missing",
                severity="high",
                message="The final answer was not captured.",
                evidence={"field": "answer", "state": answer_state},
                recommendation="Call record_final_answer() or provide a non-empty answer field.",
                owner_area="integration/schema",
                impact="Answer quality cannot be verified without the final user-visible response.",
            )
        )

    incomplete_tools: list[dict[str, Any]] = []
    for index, call in enumerate(run.get("tool_calls") or []):
        missing_fields = []
        for field in ("name", "input_tokens", "output_tokens", "latency_ms", "status"):
            if field not in call:
                missing_fields.append({"field": field, "state": "absent"})
            elif field in {"name", "status"} and call.get(field) in (None, ""):
                missing_fields.append({"field": field, "state": "empty"})
        if missing_fields:
            incomplete_tools.append({"index": index, "missing": missing_fields})
    if incomplete_tools:
        findings.append(
            DiagnosisFinding(
                code="tool_metadata_incomplete",
                severity="medium",
                message="One or more tool calls lack required trace metadata.",
                evidence={"tool_calls": incomplete_tools},
                recommendation="Record tool name, input/output token counts, latency, and status for every call.",
                owner_area="integration/tooling",
                impact="Incomplete tool traces hide latency, failure, and payload-cost causes.",
            )
        )


def _missing_finding(code: str, field: str, state: str) -> DiagnosisFinding:
    return DiagnosisFinding(
        code=code,
        severity="medium",
        message=f"{field} is missing or empty.",
        evidence={"field": field, "state": state},
        recommendation=f"Record a non-empty {field} value for every production run.",
        owner_area="integration/schema",
        impact="Trace completeness is required for production health and deployment acceptance.",
    )


def _add_task_type_mismatch_finding(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
    *,
    profile: dict[str, Any],
) -> None:
    caller = run.get("caller_task_type")
    inferred = run.get("inferred_task_type")
    if not caller or not inferred or caller == inferred:
        return
    budgets = profile.get("budgets") or {}
    findings.append(
        DiagnosisFinding(
            code="task_type_mismatch",
            severity="medium",
            message="Caller and TokenSaver task classification disagree.",
            evidence={
                "caller_task_type": caller,
                "inferred_task_type": inferred,
                "selected_task_type": run.get("task_type"),
                "caller_budget": budgets.get(str(caller)),
                "inferred_budget": budgets.get(str(inferred)),
                "route": run.get("route"),
            },
            recommendation="Review the caller classification and choose the task type whose budget and route match the request.",
            owner_area="router/profile",
            impact="Classification conflicts can silently apply the wrong route and token budget.",
        )
    )


def _add_task_type_missing_budget_finding(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
    *,
    profile: dict[str, Any],
) -> None:
    task_type = str(run.get("task_type") or "unknown")
    budgets = profile.get("budgets") or {}
    explicit_budget = run.get("budget") or (run.get("metadata") or {}).get("budget") or {}
    fallback = budgets.get("default")
    if task_type in budgets or explicit_budget or not fallback:
        return
    yaml_lines = [f"{task_type}:"]
    for field in ("input_tokens", "output_tokens", "latency_ms"):
        yaml_lines.append(f"  {field}: {int(fallback.get(field) or 0)}")
    findings.append(
        DiagnosisFinding(
            code="task_type_missing_budget",
            severity="medium",
            message="This task type has no dedicated profile budget and is using the default budget.",
            evidence={
                "task_type": task_type,
                "fallback_budget": dict(fallback),
            },
            recommendation=(
                "Review the default values, then add this entry under budgets in the profile:\n"
                + "\n".join(yaml_lines)
            ),
            owner_area="router/profile",
            impact="A generic budget can hide task-specific token or latency regressions.",
        )
    )


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _resolve_budget(
    run: dict[str, Any],
    *,
    channel: str,
    task_type: str,
    profile: dict[str, Any],
) -> dict[str, int]:
    budgets = profile.get("budgets") or {}
    channel_budgets = profile.get("channel_budgets") or {}
    budget = dict(budgets.get(task_type) or budgets.get("default") or {
        "input_tokens": 12_000,
        "output_tokens": 1_500,
        "latency_ms": 90_000,
    })
    channel_budget = ((channel_budgets.get(channel) or {}).get(task_type) or {})
    budget.update(channel_budget)
    explicit = run.get("budget") or (run.get("metadata") or {}).get("budget") or {}
    for key in ("input_tokens", "output_tokens", "latency_ms"):
        value = explicit.get(key)
        if value is not None:
            budget[key] = int(value)
    return budget


def _looks_deep_route(route: str, *, profile: dict[str, Any]) -> bool:
    lowered = route.lower()
    words = profile.get("deep_route_words") or ["deep", "research", "investigate", "report"]
    return any(str(word).lower() in lowered for word in words)


def _is_history_or_log(label: str) -> bool:
    return any(word in label for word in ("history", "log", "conversation", "memory"))


def _add_react_context_findings(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
    *,
    budget: dict[str, int],
    profile: dict[str, Any],
) -> None:
    model_calls = list(run.get("model_calls") or [])
    context_items = list(run.get("context_items") or [])
    model_call_count = len(model_calls)
    if model_call_count < 3:
        return

    thresholds = dict(profile.get("thresholds") or {})
    min_repeated_tokens = int(thresholds.get("repeated_context_item_tokens") or 1_000)
    min_react_calls = int(thresholds.get("react_loop_model_calls") or 4)
    total_model_input = sum(int(call.get("input_tokens") or 0) for call in model_calls)

    repeated_contexts: list[dict[str, Any]] = []
    for item in context_items:
        tokens = int(item.get("tokens") or 0)
        if tokens < min_repeated_tokens:
            continue
        name = str(item.get("name") or "unnamed")
        repeated_contexts.append(
            {
                "context": name,
                "tokens": tokens,
                "repeated_model_calls": model_call_count,
                "estimated_total_repeated_tokens": tokens * model_call_count,
            }
        )

    for item in repeated_contexts:
        if item["estimated_total_repeated_tokens"] < int(budget["input_tokens"] * 0.5):
            continue
        findings.append(
            DiagnosisFinding(
                code="oversized_repeated_context_item",
                severity="high",
                message="A large context item appears to be replayed across multiple model calls.",
                evidence=item,
                recommendation="Split long prompts or context into route-specific profiles, and pass only summarized tool state into later model calls.",
                owner_area="context/prompt",
                impact="Repeated context can dominate input cost even when each individual model call looks moderate.",
            )
        )

    if model_call_count >= min_react_calls and repeated_contexts:
        largest = max(repeated_contexts, key=lambda item: int(item["estimated_total_repeated_tokens"]))
        first_input = int(model_calls[0].get("input_tokens") or 0)
        last_input = int(model_calls[-1].get("input_tokens") or 0)
        findings.append(
            DiagnosisFinding(
                code="react_loop_token_amplification",
                severity="high",
                message="A multi-step ReAct loop appears to replay accumulated context across model calls.",
                evidence={
                    "model_calls_count": model_call_count,
                    "first_call_input_tokens": first_input,
                    "last_call_input_tokens": last_input,
                    "total_model_input_tokens": total_model_input,
                    "largest_repeated_context": largest["context"],
                    "largest_estimated_repeated_tokens": largest["estimated_total_repeated_tokens"],
                },
                recommendation="After tool calls, replace full ReAct message history with a rolling summary and use a compact final-answer prompt.",
                owner_area="agent_loop",
                impact="ReAct loops multiply stable prompt and context costs by the number of planning steps.",
            )
        )


def _add_tool_findings(
    findings: list[DiagnosisFinding],
    tool_calls: list[dict[str, Any]],
    input_tokens: int,
    *,
    profile: dict[str, Any],
) -> None:
    thresholds = dict(profile.get("thresholds") or {})
    large_output_tokens = int(thresholds.get("large_tool_output_tokens") or 4_000)
    dominant_share = float(thresholds.get("dominant_tool_output_share") or 0.30)
    seen: dict[str, int] = {}
    for call in tool_calls:
        name = str(call.get("name") or "unnamed")
        seen[name] = seen.get(name, 0) + 1
        output_tokens = int(call.get("output_tokens") or 0)
        cached = bool(call.get("cached"))
        if output_tokens > large_output_tokens:
            findings.append(
                DiagnosisFinding(
                    code="oversized_tool_output",
                    severity="medium",
                    message="A tool returned a large output.",
                    evidence={"tool": name, "output_tokens": output_tokens},
                    recommendation="Return structured summaries from tools instead of raw large payloads; add summary/detail/full modes where full data is only requested explicitly.",
                    owner_area="tool",
                    impact="Oversized tool payloads are a common source of input cost and context dilution.",
                )
            )
        if input_tokens > 0 and output_tokens / input_tokens >= dominant_share:
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
        if _looks_raw_payload(call, profile=profile):
            findings.append(
                DiagnosisFinding(
                    code="raw_payload_in_default_path",
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
                    code="repeated_tool_call_without_cache",
                    severity="medium",
                    message="A tool was called repeatedly without cache evidence.",
                    evidence={"tool": name, "calls": seen[name]},
                    recommendation="Add a short TTL cache or reuse the previous tool result within the run.",
                    owner_area="tool",
                    impact="Repeated calls can duplicate latency and tokens inside one run.",
                )
            )


def _add_tool_surface_findings(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
    *,
    profile: dict[str, Any],
) -> None:
    thresholds = dict(profile.get("thresholds") or {})
    token_usage = run.get("token_usage") or {}
    schema_tokens = int(token_usage.get("tool_schema_tokens") or 0)
    schema_threshold = int(thresholds.get("large_tool_schema_tokens") or 4_000)
    model_calls = list(run.get("model_calls") or [])
    exposed_counts = [
        int((call.get("metadata") or {}).get("exposed_tool_count") or 0)
        for call in model_calls
    ]
    exposed_count = max(exposed_counts, default=0)
    used_count = len({str(call.get("name") or "") for call in run.get("tool_calls") or [] if call.get("name")})
    precision = round(used_count / exposed_count, 3) if exposed_count else None
    if schema_tokens >= schema_threshold:
        findings.append(
            DiagnosisFinding(
                code="oversized_tool_surface",
                severity="high",
                message="Tool schemas consume a large amount of model input context.",
                evidence={
                    "tool_schema_tokens": schema_tokens,
                    "exposed_tool_count": exposed_count or None,
                    "used_tool_count": used_count,
                    "route_tool_precision": precision,
                },
                recommendation="Expose only route-relevant tools and replace full schemas with a smaller routed tool set.",
                owner_area="tool/router",
                impact="Unused tool schemas are billed on model calls even when the tools are never invoked.",
            )
        )
    min_exposed = int(thresholds.get("large_tool_surface_count") or 10)
    min_precision = float(thresholds.get("route_tool_precision") or 0.25)
    if exposed_count >= min_exposed and precision is not None and precision < min_precision:
        findings.append(
            DiagnosisFinding(
                code="unused_tool_schema_cost",
                severity="medium",
                message="The route exposed many more tools than it used.",
                evidence={
                    "exposed_tool_count": exposed_count,
                    "used_tool_count": used_count,
                    "route_tool_precision": precision,
                    "estimated_unused_tool_schema_tokens": round(schema_tokens * (1 - precision)),
                },
                recommendation="Route first, then attach the smallest tool schema set needed by that route.",
                owner_area="tool/router",
                impact="Low tool-surface precision wastes context and can reduce tool-selection accuracy.",
            )
        )


def _add_latency_tool_findings(
    findings: list[DiagnosisFinding],
    tool_calls: list[dict[str, Any]],
    *,
    latency_ms: int,
    budget: dict[str, int],
    profile: dict[str, Any],
) -> None:
    thresholds = dict(profile.get("thresholds") or {})
    slow_tool_ms = int(thresholds.get("slow_tool_latency_ms") or 30_000)
    low_value_output_tokens = int(thresholds.get("low_value_tool_output_tokens") or 50)
    for call in tool_calls:
        name = str(call.get("name") or "unnamed")
        call_latency = int(call.get("latency_ms") or 0)
        output_tokens = int(call.get("output_tokens") or 0)
        metadata = call.get("metadata") or {}
        if call_latency >= slow_tool_ms and output_tokens <= low_value_output_tokens:
            evidence = {
                "tool": name,
                "latency_ms": call_latency,
                "output_tokens": output_tokens,
                "latency_share": round(call_latency / latency_ms, 3) if latency_ms else None,
            }
            findings.append(
                DiagnosisFinding(
                    code="expensive_low_value_tool_call",
                    severity="high",
                    message="A slow tool call returned very little usable output.",
                    evidence=evidence,
                    recommendation="Add a timeout fallback or cheaper snapshot path, and let the Agent stop deepening when the tool returns low-value output.",
                    owner_area="tool/fallback",
                    impact="Slow low-value tools dominate latency without improving the final answer enough.",
                )
            )
        success = metadata.get(
            "transport_success",
            metadata.get("success", call.get("transport_success", call.get("success"))),
        )
        semantic_success = metadata.get("semantic_success", call.get("semantic_success"))
        if semantic_success is False or (
            success is True and call_latency >= slow_tool_ms and output_tokens <= low_value_output_tokens
        ):
            findings.append(
                DiagnosisFinding(
                    code="tool_success_mismatch",
                    severity="medium",
                    message="A tool appears transport-successful but semantically low-value or failed.",
                    evidence={
                        "tool": name,
                        "success": success,
                        "semantic_success": semantic_success,
                        "latency_ms": call_latency,
                        "output_tokens": output_tokens,
                    },
                    recommendation="Trace transport_success separately from semantic_success, error_type, fallback_used, and result_quality.",
                    owner_area="tool/schema",
                    impact="A success flag that only means process completion hides tool failures from route and cache decisions.",
                )
            )
        fallback_used = bool(metadata.get("fallback_used", call.get("fallback_used", False)))
        if call_latency > int(budget["latency_ms"] * 0.5) and not fallback_used:
            findings.append(
                DiagnosisFinding(
                    code="missing_fallback_for_slow_tool",
                    severity="medium",
                    message="A slow tool consumed a large share of the latency budget without fallback evidence.",
                    evidence={
                        "tool": name,
                        "latency_ms": call_latency,
                        "budget_latency_ms": budget["latency_ms"],
                        "fallback_used": fallback_used,
                    },
                    recommendation="Define timeout thresholds and fallback behavior for this tool in the default route.",
                    owner_area="tool/fallback",
                    impact="Missing fallback paths make chat workflows wait for tools that may not return useful evidence.",
                )
            )


def _add_model_findings(
    findings: list[DiagnosisFinding],
    model_calls: list[dict[str, Any]],
    task_type: str,
    *,
    quick_tasks: set[str],
) -> None:
    if task_type not in quick_tasks:
        return
    for call in model_calls:
        model = str(call.get("model") or "").lower()
        if any(word in model for word in ("opus", "sonnet", "gpt-4.1")):
            findings.append(
                DiagnosisFinding(
                    code="strong_model_for_simple_task",
                    severity="medium",
                    message="A quick task used a strong model.",
                    evidence={"task_type": task_type, "model": call.get("model")},
                    recommendation="Use rules or a cheaper model for quick routing and short answers.",
                    owner_area="model/router",
                    impact="Strong models are often unnecessary for classification and simple replies.",
                )
            )


def _add_route_findings(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
    *,
    task_type: str,
    route: str,
    profile: dict[str, Any],
) -> None:
    message = str(run.get("user_message") or "")
    lowered = message.lower()
    intent_patterns = profile.get("intent_patterns") or {}
    if not isinstance(intent_patterns, dict):
        return
    for intent_name, pattern in intent_patterns.items():
        if not isinstance(pattern, dict):
            continue
        keywords = [str(word).lower() for word in pattern.get("keywords") or []]
        if not keywords or not any(word in lowered for word in keywords):
            continue
        expected_words = [str(word).lower() for word in pattern.get("expected_route_words") or []]
        if expected_words and any(
            word in task_type.lower() or word in route.lower() for word in expected_words
        ):
            continue
        candidates = [
            str(item)
            for item in pattern.get("expected_task_type_candidates") or [str(intent_name)]
        ]
        findings.append(
            DiagnosisFinding(
                code="task_route_mismatch",
                severity="medium",
                message="The user request matches a configured intent pattern, but the recorded task or route looks generic.",
                evidence={
                    "user_message": message,
                    "intent_pattern": str(intent_name),
                    "recorded_task_type": task_type,
                    "route": route,
                    "expected_task_type_candidates": candidates,
                },
                recommendation="Add profile intent mapping so matched requests use the intended task budget, route, prompt, and answer policy.",
                owner_area="router/profile",
                impact="A generic route can apply the wrong prompt, budget, tool set, and answer policy.",
            )
        )
        return


def _add_quality_findings(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
    task_type: str,
    *,
    channel: str,
    short_channels: set[str],
    sensitive_tasks: set[str],
    profile: dict[str, Any],
) -> None:
    quality = run.get("quality_signals") or {}
    required_fields = list(run.get("quality_requirements") or profile_required_fields(profile, task_type))
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
                code="required_field_missing",
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
                code="quality_regression_risk",
                severity="low",
                message="Required quality fields were registered but no final answer was recorded for verification.",
                evidence={"required_fields": required_fields},
                recommendation="Record the final answer or explicit quality signals so TokenSaver can verify quality guardrails.",
                owner_area="quality",
                impact="Unverified quality guardrails make before/after optimization less reliable.",
            )
        )
    _add_answer_density_findings(
        findings,
        run,
        channel=channel,
        short_channels=short_channels,
        profile=profile,
    )
    if task_type in sensitive_tasks:
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


def _add_answer_density_findings(
    findings: list[DiagnosisFinding],
    run: dict[str, Any],
    *,
    channel: str,
    short_channels: set[str],
    profile: dict[str, Any],
) -> None:
    if channel not in short_channels:
        return
    answer = str(run.get("answer") or "")
    if not answer:
        return
    thresholds = dict(profile.get("thresholds") or {})
    density_profile = profile.get("answer_density") or {}
    if not isinstance(density_profile, dict):
        density_profile = {}
    table_rows = sum(1 for line in answer.splitlines() if line.strip().startswith("|"))
    caveat_words = [str(word) for word in density_profile.get("caveat_words") or []]
    followup_words = [str(word) for word in density_profile.get("followup_words") or []]
    caveat_count = sum(answer.count(word) for word in caveat_words)
    followup_count = sum(answer.count(word) for word in followup_words)
    if (
        table_rows >= int(thresholds.get("low_density_table_rows") or 6)
        or caveat_count >= int(thresholds.get("low_density_caveat_count") or 3)
        or followup_count >= int(thresholds.get("low_density_followup_count") or 2)
    ):
        findings.append(
            DiagnosisFinding(
                code="low_density_answer_section",
                severity="medium",
                message="The final answer contains sections that are likely too low-density for a short-message channel.",
                evidence={
                    "channel": channel,
                    "table_rows": table_rows,
                    "caveat_count": caveat_count,
                    "followup_count": followup_count,
                    "answer_tokens": int(run.get("answer_tokens") or 0),
                },
                recommendation="For short-message channels, keep the default answer to conclusion, cause, action, and risk; move tables and extended evidence into an artifact.",
                owner_area="channel",
                impact="Low-density sections make chat answers hard to scan even when the total token count is near budget.",
            )
        )


def _looks_raw_payload(call: dict[str, Any], *, profile: dict[str, Any]) -> bool:
    metadata = call.get("metadata") or {}
    mode = str(metadata.get("mode") or metadata.get("detail_level") or "").lower()
    if mode in {"full", "raw", "debug"}:
        return True
    if bool(metadata.get("raw_payload")):
        return True
    record_count = metadata.get("record_count")
    if record_count is not None:
        try:
            thresholds = profile.get("thresholds") or {}
            threshold = int(thresholds.get("raw_payload_record_count") or 50)
            return int(record_count) >= threshold
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


def _top_latency_consumers(run: dict[str, Any], limit: int = 8) -> list[dict[str, Any]]:
    consumers: list[dict[str, Any]] = []
    for call in run.get("tool_calls") or []:
        consumers.append(
            {
                "kind": "tool",
                "name": call.get("name") or "unnamed",
                "latency_ms": int(call.get("latency_ms") or 0),
            }
        )
    for index, call in enumerate(run.get("model_calls") or []):
        model = call.get("model") or f"model_call_{index}"
        consumers.append(
            {
                "kind": "model",
                "name": model,
                "latency_ms": int(call.get("latency_ms") or 0),
            }
        )
    consumers.sort(key=lambda item: int(item["latency_ms"]), reverse=True)
    return [item for item in consumers[:limit] if int(item["latency_ms"]) > 0]


def _root_causes(findings: list[DiagnosisFinding], limit: int = 5) -> list[dict[str, Any]]:
    priority = {
        "react_loop_token_amplification": 0,
        "oversized_repeated_context_item": 1,
        "expensive_low_value_tool_call": 2,
        "tool_success_mismatch": 3,
        "task_route_mismatch": 4,
        "low_density_answer_section": 5,
    }
    ranked = [finding for finding in findings if finding.code in priority]
    ranked.sort(key=lambda finding: (priority[finding.code], finding.code))
    return [
        {
            "code": finding.code,
            "owner_area": finding.owner_area,
            "message": finding.message,
        }
        for finding in ranked[:limit]
    ]


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
        "oversized_tool_output": "context_precision",
        "dominant_tool_output": "context_precision",
        "raw_payload_in_default_path": "context_precision",
        "oversized_context_item": "context_precision",
        "oversized_repeated_context_item": "context_precision",
        "react_loop_token_amplification": "context_precision",
        "history_context_pollution": "context_precision",
        "expensive_low_value_tool_call": "latency_efficiency",
        "missing_fallback_for_slow_tool": "latency_efficiency",
        "output_budget_exceeded": "output_density",
        "channel_output_over_budget": "output_density",
        "low_density_answer_section": "output_density",
        "latency_budget_exceeded": "latency_efficiency",
        "deep_route_for_short_task": "task_fit",
        "task_route_mismatch": "task_fit",
        "strong_model_for_simple_task": "task_fit",
        "tool_success_mismatch": "quality_risk",
        "required_field_missing": "quality_risk",
        "quality_regression_risk": "quality_risk",
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
