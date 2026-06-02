"""Human-readable summaries and repair briefs for Agent runs."""

from __future__ import annotations

from typing import Any


def generate_run_summary(run: dict[str, Any]) -> str:
    diagnosis = run.get("diagnosis") or {}
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
    findings = diagnosis.get("findings") or []
    if findings:
        lines.extend(["", "## Findings"])
        for finding in findings:
            lines.append(
                f"- [{finding.get('severity')}] {finding.get('code')}: {finding.get('message')}"
            )
    return "\n".join(lines) + "\n"


def generate_repair_brief(run: dict[str, Any]) -> str:
    diagnosis = run.get("diagnosis") or {}
    findings = diagnosis.get("findings") or []
    app = run.get("app") or "this Agent app"
    channel = run.get("channel") or "runtime"
    task_type = run.get("task_type") or "unknown"
    route = run.get("route") or "unknown"

    lines = [
        f"# TokenSaver Repair Brief",
        "",
        f"Please optimize {app}'s {channel} Agent workflow.",
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

    if findings:
        lines.extend(["", "## Problems"])
        for finding in findings:
            lines.append(f"- {finding.get('code')}: {finding.get('message')}")

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
            "4. Add or update tests for route selection and token budgets when code changes are made.",
        ]
    )
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

