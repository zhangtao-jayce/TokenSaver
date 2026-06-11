"""Built-in, offline TokenSaver product demo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .benchmark import benchmark_runs
from .runtime import record_agent_run


def run_demo(store_dir: str | Path = ".tokensaver-demo") -> dict[str, Any]:
    """Record a deterministic before/after pair and write benchmark artifacts."""

    root = Path(store_dir)
    before = record_agent_run(_before_run(), store_dir=root)
    before_panel = (root / "panel" / "index.html").read_text(encoding="utf-8")
    after = record_agent_run(_after_run(), store_dir=root)
    benchmark_result = benchmark_runs(
        before,
        after,
        output_dir=root,
        title="TokenSaver Demo Benchmark",
    )
    comparison = benchmark_result["comparison"]
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
            "benchmark_json": benchmark_result["artifacts"]["json"],
            "benchmark_markdown": benchmark_result["artifacts"]["markdown"],
            "share_card": benchmark_result["artifacts"]["share_card"],
        },
    }
    return benchmark


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
