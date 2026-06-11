"""Before/after benchmark and share-card generation."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from .diagnosis import diagnose_run
from .store import compare_runs


def benchmark_runs(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    output_dir: str | Path,
    title: str = "TokenSaver Agent ROI Benchmark",
) -> dict[str, Any]:
    """Diagnose, compare, and write shareable benchmark artifacts."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    diagnosed_before = _ensure_diagnosis(before)
    diagnosed_after = _ensure_diagnosis(after)
    comparison = compare_runs(diagnosed_before, diagnosed_after)
    result = {
        "title": title,
        "before": diagnosed_before,
        "after": diagnosed_after,
        "comparison": comparison,
        "artifacts": {
            "json": str(root / "benchmark.json"),
            "markdown": str(root / "benchmark.md"),
            "share_card": str(root / "share-card.svg"),
        },
    }
    (root / "benchmark.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "benchmark.md").write_text(
        render_benchmark_markdown(title, diagnosed_before, diagnosed_after, comparison),
        encoding="utf-8",
    )
    (root / "share-card.svg").write_text(
        render_share_card(title, comparison),
        encoding="utf-8",
    )
    return result


def render_benchmark_markdown(
    title: str,
    before: dict[str, Any],
    after: dict[str, Any],
    comparison: dict[str, Any],
) -> str:
    deltas = comparison["deltas"]
    return "\n".join(
        [
            f"# {title}",
            "",
            "| Metric | Before | After | Change |",
            "| --- | ---: | ---: | ---: |",
            _metric_row("Input tokens", deltas["input_tokens"]),
            _metric_row("Output tokens", deltas["output_tokens"]),
            _metric_row("Latency", deltas["latency_ms"], suffix="ms"),
            (
                f"| ROI score | {(before.get('diagnosis') or {}).get('roi_score', 100)} "
                f"| {(after.get('diagnosis') or {}).get('roi_score', 100)} "
                f"| {comparison['roi_score']['delta']:+d} |"
            ),
            "",
            "## Resolved Findings",
            "",
            *([f"- `{code}`" for code in comparison["resolved_findings"]] or ["- None"]),
            "",
            "## New Findings",
            "",
            *([f"- `{code}`" for code in comparison["new_findings"]] or ["- None"]),
            "",
            "## Quality Check",
            "",
            f"- Result: **{str(comparison['result']).upper()}**",
            f"- Quality blockers: {', '.join(comparison['quality_blockers']) or 'none'}",
            "",
        ]
    )


def render_share_card(title: str, comparison: dict[str, Any]) -> str:
    deltas = comparison["deltas"]
    input_change = _pct(deltas["input_tokens"].get("delta_pct"))
    output_change = _pct(deltas["output_tokens"].get("delta_pct"))
    latency_change = _pct(deltas["latency_ms"].get("delta_pct"))
    roi = comparison["roi_score"]
    safe_title = html.escape(title)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#f4f7fb"/>
  <rect x="54" y="54" width="1092" height="522" rx="24" fill="#ffffff" stroke="#d8dee8" stroke-width="2"/>
  <text x="96" y="125" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#2457a6">TokenSaver</text>
  <text x="96" y="178" font-family="Arial, sans-serif" font-size="38" font-weight="700" fill="#18212f">{safe_title}</text>
  {_card_metric(96, "Input tokens", input_change)}
  {_card_metric(380, "Output tokens", output_change)}
  {_card_metric(664, "Latency", latency_change)}
  <rect x="948" y="242" width="150" height="150" rx="75" fill="#eef5ff" stroke="#bdd4fb" stroke-width="10"/>
  <text x="1023" y="310" text-anchor="middle" font-family="Arial, sans-serif" font-size="22" fill="#657084">ROI</text>
  <text x="1023" y="355" text-anchor="middle" font-family="Arial, sans-serif" font-size="38" font-weight="700" fill="#2457a6">{roi['before']}→{roi['after']}</text>
  <text x="96" y="500" font-family="Arial, sans-serif" font-size="24" fill="#16794a">Local-first · No required LLM · Quality blockers checked</text>
  <text x="96" y="540" font-family="Arial, sans-serif" font-size="20" fill="#657084">github.com/zhangtao-jayce/TokenSaver</text>
</svg>
"""


def _ensure_diagnosis(run: dict[str, Any]) -> dict[str, Any]:
    value = dict(run)
    if not isinstance(value.get("diagnosis"), dict):
        value["diagnosis"] = diagnose_run(value)
    return value


def _metric_row(label: str, metric: dict[str, Any], *, suffix: str = "") -> str:
    return (
        f"| {label} | {metric['before']}{suffix} | {metric['after']}{suffix} "
        f"| {_pct(metric.get('delta_pct'))} |"
    )


def _pct(value: Any) -> str:
    return "n/a" if value is None else f"{float(value):+.1f}%"


def _card_metric(x: int, label: str, value: str) -> str:
    return f"""
  <text x="{x}" y="275" font-family="Arial, sans-serif" font-size="20" fill="#657084">{html.escape(label)}</text>
  <text x="{x}" y="345" font-family="Arial, sans-serif" font-size="48" font-weight="700" fill="#18212f">{html.escape(value)}</text>"""
