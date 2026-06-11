"""Built-in, offline TokenSaver product demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .runtime import record_agent_run
from .store import compare_runs


def run_demo(store_dir: str | Path = ".tokensaver-demo") -> dict[str, Any]:
    """Record a deterministic before/after pair and write benchmark artifacts."""

    root = Path(store_dir)
    before = record_agent_run(_before_run(), store_dir=root)
    before_panel = (root / "panel" / "index.html").read_text(encoding="utf-8")
    after = record_agent_run(_after_run(), store_dir=root)
    comparison = compare_runs(before, after)
    (root / "panel" / "before.html").write_text(before_panel, encoding="utf-8")
    (root / "panel" / "after.html").write_text(
        (root / "panel" / "index.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    benchmark = {
        "scenario": "A short support question incorrectly routed through deep research.",
        "before_run_id": before["run_id"],
        "after_run_id": after["run_id"],
        "comparison": comparison,
        "artifacts": {
            "panel": str(root / "panel" / "index.html"),
            "before_panel": str(root / "panel" / "before.html"),
            "after_panel": str(root / "panel" / "after.html"),
            "report": str(root / "reports" / "latest.md"),
            "brief": str(root / "briefs" / "latest.md"),
            "benchmark_json": str(root / "benchmark.json"),
            "benchmark_markdown": str(root / "benchmark.md"),
        },
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "benchmark.json").write_text(
        json.dumps(benchmark, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "benchmark.md").write_text(
        render_demo_benchmark(before, after, comparison),
        encoding="utf-8",
    )
    return benchmark


def render_demo_benchmark(
    before: dict[str, Any],
    after: dict[str, Any],
    comparison: dict[str, Any],
) -> str:
    deltas = comparison["deltas"]
    return "\n".join(
        [
            "# TokenSaver Demo Benchmark",
            "",
            "A deterministic offline example showing a short support request before and after workflow repair.",
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
            *[f"- `{code}`" for code in comparison["resolved_findings"]],
            "",
            "## Result",
            "",
            f"**{str(comparison['result']).upper()}**",
            "",
            "This benchmark uses bundled fixture data. It is a product demonstration, not a claim about every Agent workload.",
            "",
        ]
    )


def _metric_row(label: str, metric: dict[str, Any], *, suffix: str = "") -> str:
    change = metric.get("delta_pct")
    change_text = "n/a" if change is None else f"{change:+.1f}%"
    return (
        f"| {label} | {metric['before']}{suffix} | {metric['after']}{suffix} "
        f"| {change_text} |"
    )


def _before_run() -> dict[str, Any]:
    return {
        "run_id": "demo-before",
        "app": "support_agent",
        "channel": "chat",
        "user_message": "What is the current status of ticket 1842?",
        "task_type": "quick_question",
        "route": "deep_research",
        "budget": {
            "input_tokens": 4_000,
            "output_tokens": 700,
            "latency_ms": 15_000,
        },
        "context_items": [
            {"name": "full_conversation_history", "kind": "history", "tokens": 9_200},
            {"name": "entire_customer_record", "kind": "crm", "tokens": 5_100},
        ],
        "tool_calls": [
            {
                "name": "search_tickets",
                "input_tokens": 120,
                "output_tokens": 2_400,
                "latency_ms": 5_800,
                "cached": False,
            },
            {
                "name": "search_tickets",
                "input_tokens": 120,
                "output_tokens": 2_400,
                "latency_ms": 5_600,
                "cached": False,
            },
        ],
        "model_calls": [
            {
                "model": "frontier-model",
                "input_tokens": 18_000,
                "output_tokens": 2_100,
                "latency_ms": 18_000,
            }
        ],
        "answer": "A long status response.",
        "answer_tokens": 500,
        "input_tokens": 32_540,
        "output_tokens": 7_400,
        "latency_ms": 31_000,
        "quality_requirements": ["conclusion", "next_action"],
        "quality_signals": {
            "conclusion": True,
            "next_action": True,
        },
    }


def _after_run() -> dict[str, Any]:
    return {
        "run_id": "demo-after",
        "app": "support_agent",
        "channel": "chat",
        "user_message": "What is the current status of ticket 1842?",
        "task_type": "quick_question",
        "route": "ticket_status",
        "budget": {
            "input_tokens": 4_000,
            "output_tokens": 700,
            "latency_ms": 15_000,
        },
        "context_items": [
            {"name": "ticket_1842", "kind": "crm", "tokens": 620},
            {"name": "recent_ticket_summary", "kind": "summary", "tokens": 310},
        ],
        "tool_calls": [
            {
                "name": "get_ticket",
                "input_tokens": 40,
                "output_tokens": 280,
                "latency_ms": 420,
                "cached": True,
            }
        ],
        "model_calls": [
            {
                "model": "small-model",
                "input_tokens": 1_450,
                "output_tokens": 210,
                "latency_ms": 1_100,
            }
        ],
        "answer": "Ticket 1842 is waiting for customer confirmation. Next action: follow up tomorrow.",
        "answer_tokens": 90,
        "input_tokens": 2_460,
        "output_tokens": 580,
        "latency_ms": 1_700,
        "quality_requirements": ["conclusion", "next_action"],
        "quality_signals": {
            "conclusion": True,
            "next_action": True,
        },
    }
