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
    required_fields = list(run.get("quality_requirements") or [])

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
        f"- route: {route}",
        f"- input_tokens: {run.get('input_tokens', 0)}",
        f"- output_tokens: {run.get('output_tokens', 0)}",
        f"- latency_ms: {run.get('latency_ms', 0)}",
        f"- roi_score: {diagnosis.get('roi_score', 100)}",
    ]

    consumers = diagnosis.get("top_token_consumers") or []
    if consumers:
        lines.extend(["", "## Evidence"])
        for item in consumers[:5]:
            lines.append(
                f"- {item.get('kind')}: {item.get('name')} used {item.get('tokens', 0)} tokens"
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
