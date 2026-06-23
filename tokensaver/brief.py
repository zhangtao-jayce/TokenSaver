"""Human-readable summaries and repair briefs for Agent runs."""

from __future__ import annotations

from typing import Any

from .update import format_update_notice


def generate_run_summary(
    run: dict[str, Any],
    *,
    update_info: dict[str, Any] | None = None,
) -> str:
    diagnosis = run.get("diagnosis") or {}
    budget = diagnosis.get("budget") or run.get("budget") or {}
    lines = [
        f"# TokenSaver Run Summary",
        "",
        f"- app: {run.get('app', '')}",
        f"- channel: {run.get('channel', '')}",
        f"- traffic_type: {run.get('traffic_type', 'production_user_run')}",
        f"- task_type: {run.get('task_type', '')}",
        f"- route: {run.get('route', '')}",
        f"- input_tokens: {run.get('input_tokens', 0)}",
        f"- output_tokens: {run.get('output_tokens', 0)}",
        f"- latency_ms: {run.get('latency_ms', 0)}",
        f"- roi_score: {diagnosis.get('roi_score', 100)}",
        f"- status: {diagnosis.get('status', 'ok')}",
    ]
    if budget:
        lines.extend(
            [
                "",
                "## Budget",
                "",
                f"- input_tokens: {budget.get('input_tokens', '')}",
                f"- output_tokens: {budget.get('output_tokens', '')}",
                f"- latency_ms: {budget.get('latency_ms', '')}",
            ]
        )
    handoffs = list(run.get("handoffs") or [])
    if handoffs:
        lines.extend(["", "## External Agent Handoffs", ""])
        for handoff in handoffs:
            lines.append(
                "- "
                f"{handoff.get('agent', 'external_agent')}: "
                f"{handoff.get('status', 'prepared')}"
                f"; expected_output={handoff.get('expected_output') or 'unspecified'}"
            )
    token_usage = run.get("token_usage") or {}
    if token_usage:
        lines.extend(["", "## Token Breakdown", ""])
        for field in (
            "billed_model_input_tokens",
            "billed_model_output_tokens",
            "tool_payload_tokens",
            "final_answer_tokens",
            "reasoning_tokens",
            "repeated_context_tokens",
            "tool_schema_tokens",
            "source",
        ):
            lines.append(f"- {field}: {token_usage.get(field, 0)}")
    dimensions = diagnosis.get("dimensions") or {}
    if dimensions:
        lines.extend(["", "## ROI Dimensions"])
        for name, score in dimensions.items():
            lines.append(f"- {name}: {score}")
    consumers = diagnosis.get("top_token_consumers") or []
    if consumers:
        lines.extend(["", "## Top Token Consumers"])
        for item in consumers:
            lines.append(
                f"- {item.get('kind')}: {item.get('name')} ({item.get('tokens', 0)} tokens)"
            )
    latency_consumers = diagnosis.get("top_latency_consumers") or []
    if latency_consumers:
        lines.extend(["", "## Top Latency Consumers"])
        for item in latency_consumers:
            lines.append(
                f"- {item.get('kind')}: {item.get('name')} ({item.get('latency_ms', 0)}ms)"
            )
    root_causes = diagnosis.get("root_causes") or []
    if root_causes:
        lines.extend(["", "## Root Causes"])
        for item in root_causes:
            lines.append(
                f"- {item.get('code')} ({item.get('owner_area')}): {item.get('message')}"
            )
    findings = diagnosis.get("findings") or []
    if findings:
        lines.extend(["", "## Findings"])
        for finding in findings:
            lines.append(
                f"- [{finding.get('severity')}] {finding.get('code')}: {finding.get('message')}"
            )
    notice = format_update_notice(update_info)
    if notice:
        lines.extend(["", notice])
    return "\n".join(lines) + "\n"


def generate_repair_brief(
    run: dict[str, Any],
    *,
    update_info: dict[str, Any] | None = None,
) -> str:
    diagnosis = run.get("diagnosis") or {}
    findings = diagnosis.get("findings") or []
    app = run.get("app") or "this Agent app"
    channel = run.get("channel") or "runtime"
    task_type = run.get("task_type") or "unknown"
    route = run.get("route") or "unknown"
    required_fields = list(run.get("quality_requirements") or diagnosis.get("quality_guardrail_fields") or [])
    handoffs = list(run.get("handoffs") or [])

    lines = [
        f"# TokenSaver Repair Brief",
        "",
        "## Objective",
        "",
        f"Optimize {app}'s {channel} Agent workflow without losing decision-critical answer quality.",
        "",
        "## Observed Run",
        "",
        f"- task_type: {task_type}",
        f"- traffic_type: {run.get('traffic_type', 'production_user_run')}",
        f"- route: {route}",
        f"- input_tokens: {run.get('input_tokens', 0)}",
        f"- output_tokens: {run.get('output_tokens', 0)}",
        f"- latency_ms: {run.get('latency_ms', 0)}",
        f"- roi_score: {diagnosis.get('roi_score', 100)}",
    ]

    token_usage = run.get("token_usage") or {}
    if token_usage:
        lines.extend(
            [
                f"- tool_payload_tokens: {token_usage.get('tool_payload_tokens', 0)}",
                f"- final_answer_tokens: {token_usage.get('final_answer_tokens', 0)}",
                f"- repeated_context_tokens: {token_usage.get('repeated_context_tokens', 0)}",
                f"- tool_schema_tokens: {token_usage.get('tool_schema_tokens', 0)}",
                f"- token_usage_source: {token_usage.get('source', 'estimated')}",
            ]
        )

    if handoffs:
        lines.extend(["", "## External Agent Handoffs", ""])
        for handoff in handoffs:
            inputs = ", ".join(str(item) for item in handoff.get("input_artifacts") or [])
            lines.append(
                "- "
                f"agent={handoff.get('agent', 'external_agent')}; "
                f"status={handoff.get('status', 'prepared')}; "
                f"inputs={inputs or 'unspecified'}; "
                f"expected_output={handoff.get('expected_output') or 'unspecified'}"
            )

    consumers = diagnosis.get("top_token_consumers") or []
    if consumers:
        lines.extend(["", "## Evidence"])
        for item in consumers[:5]:
            lines.append(
                f"- {item.get('kind')}: {item.get('name')} used {item.get('tokens', 0)} tokens"
            )
    latency_consumers = diagnosis.get("top_latency_consumers") or []
    if latency_consumers:
        if not consumers:
            lines.extend(["", "## Evidence"])
        for item in latency_consumers[:5]:
            lines.append(
                f"- {item.get('kind')}: {item.get('name')} took {item.get('latency_ms', 0)}ms"
            )

    root_causes = diagnosis.get("root_causes") or []
    if root_causes:
        lines.extend(["", "## Root Causes"])
        for item in root_causes:
            lines.append(
                f"- {item.get('code')} ({item.get('owner_area')}): {item.get('message')}"
            )

    if findings:
        lines.extend(["", "## Problems"])
        for finding in findings:
            owner = finding.get("owner_area") or "workflow"
            lines.append(f"- {finding.get('code')} ({owner}): {finding.get('message')}")
            evidence = finding.get("evidence") or {}
            if evidence:
                lines.append(f"  Evidence: {_inline_dict(evidence)}")
            if finding.get("impact"):
                lines.append(f"  Impact: {finding.get('impact')}")

        if required_fields:
            lines.extend(["", "## Required Quality Fields"])
            for field in required_fields:
                lines.append(f"- {field}")

        lines.extend(["", "## Requested Changes"])
        for index, recommendation in enumerate(_dedupe_recommendations(findings), start=1):
            lines.append(f"{index}. {recommendation}")
    else:
        lines.extend(
            [
                "",
                "## Problems",
                "",
                "- No low-ROI pattern was detected by the current local rules.",
                "",
                "## Requested Changes",
                "",
                "1. Keep the current route, context, model, and answer budget unless new evidence appears.",
            ]
        )

    lines.extend(
        [
            "",
            "## Verification",
            "",
            "1. Run the same or equivalent Agent request again.",
            "2. Confirm TokenSaver records a new trace.",
            "3. Compare input tokens, output tokens, latency, and finding codes against this run.",
            "4. Confirm required quality fields are still present or explicitly verified.",
            "5. Add or update tests for route selection, tool payload modes, and token budgets when code changes are made.",
        ]
    )
    notice = format_update_notice(update_info)
    if notice:
        lines.extend(["", notice])
    return "\n".join(lines) + "\n"


def _dedupe_recommendations(findings: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    recommendations: list[str] = []
    for finding in findings:
        recommendation = str(finding.get("recommendation") or "").strip()
        if recommendation and recommendation not in seen:
            seen.add(recommendation)
            recommendations.append(recommendation)
    return recommendations


def _inline_dict(value: dict[str, Any]) -> str:
    parts = []
    for key, item in value.items():
        parts.append(f"{key}={item}")
    return ", ".join(parts)
