"""Context review and risk heuristics."""

from __future__ import annotations

from dataclasses import dataclass

from .tokenizer import estimate_tokens


@dataclass(frozen=True)
class ContextItem:
    name: str
    content: str
    kind: str = "text"


@dataclass(frozen=True)
class ContextReview:
    total_tokens: int
    recommended_context: list[str]
    excluded_context: list[str]
    risks: list[str]
    observations: list[str]


_TASK_CONTEXT_HINTS: dict[str, set[str]] = {
    "light_qa": {"state", "summary", "positions", "watchlist"},
    "realtime_analysis": {"price", "news", "technical", "calendar", "summary"},
    "intraday_anomaly_attribution": {
        "price",
        "sector",
        "news",
        "technical",
        "positions",
        "summary",
    },
    "multi_object_comparison": {"summary", "score", "price", "technical", "peers"},
    "operation_confirmation": {"payload", "positions", "risk", "summary"},
    "code_analysis": {"diff", "error", "stack", "file", "test", "summary"},
    "writing_generation": {"brief", "source", "outline", "style", "summary"},
    "high_risk_document_review": {"source", "contract", "policy", "risk", "summary"},
    "deep_analysis": {"summary", "source", "data", "report", "tool"},
}


def review_context(
    *,
    task_type: str,
    context_items: list[ContextItem],
    max_context_tokens: int = 12_000,
) -> ContextReview:
    total_tokens = sum(estimate_tokens(item.content) for item in context_items)
    hints = _TASK_CONTEXT_HINTS.get(task_type, set())

    recommended: list[str] = []
    excluded: list[str] = []
    risks: list[str] = []
    observations: list[str] = []

    for item in context_items:
        label = f"{item.kind}:{item.name}".lower()
        item_tokens = estimate_tokens(item.content)
        relevant = any(hint in label for hint in hints)

        if relevant or item_tokens < 800:
            recommended.append(item.name)
        else:
            excluded.append(item.name)

        if item_tokens > 8_000:
            risks.append(f"context_too_large:{item.name}")
        if "history" in label and task_type in {
            "realtime_analysis",
            "intraday_anomaly_attribution",
            "operation_confirmation",
        }:
            risks.append(f"history_contamination_possible:{item.name}")

    if total_tokens > max_context_tokens:
        risks.append("context_budget_exceeded")
        observations.append(
            f"Context estimate {total_tokens} tokens exceeds budget {max_context_tokens}."
        )
    if not context_items:
        observations.append("No structured context items were provided.")

    return ContextReview(
        total_tokens=total_tokens,
        recommended_context=recommended,
        excluded_context=excluded,
        risks=sorted(set(risks)),
        observations=observations,
    )

