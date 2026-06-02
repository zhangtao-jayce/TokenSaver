"""High-level task planning API."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .context_review import ContextItem, review_context
from .models import estimate_cost_usd
from .task_classifier import classify_task
from .tokenizer import estimate_tokens


@dataclass(frozen=True)
class TaskPlan:
    task_type: str
    confidence: float
    mode: str
    input_tokens_estimate: int
    context_tokens_estimate: int
    estimated_cost_usd: float | None
    recommended_context: list[str]
    excluded_context: list[str]
    model_strategy: dict[str, str]
    risks: list[str]
    observations: list[str]
    next_actions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def plan_task(
    *,
    user_message: str,
    model: str | None = None,
    output_tokens_estimate: int = 1_000,
    context_items: list[dict[str, str]] | None = None,
    preferred_mode: str = "suggest",
    max_context_tokens: int = 12_000,
) -> TaskPlan:
    classification = classify_task(user_message)
    items = [
        ContextItem(
            name=item.get("name", "unnamed"),
            content=item.get("content", ""),
            kind=item.get("kind", "text"),
        )
        for item in (context_items or [])
    ]
    review = review_context(
        task_type=classification.task_type,
        context_items=items,
        max_context_tokens=max_context_tokens,
    )

    input_tokens = estimate_tokens(user_message)
    total_input_tokens = input_tokens + review.total_tokens
    estimated_cost = estimate_cost_usd(
        model=model,
        input_tokens=total_input_tokens,
        output_tokens=output_tokens_estimate,
    )

    risks = list(review.risks)
    risks.extend(_task_risks(classification.task_type))

    return TaskPlan(
        task_type=classification.task_type,
        confidence=classification.confidence,
        mode=_choose_mode(classification.task_type, preferred_mode),
        input_tokens_estimate=input_tokens,
        context_tokens_estimate=review.total_tokens,
        estimated_cost_usd=estimated_cost,
        recommended_context=review.recommended_context,
        excluded_context=review.excluded_context,
        model_strategy=_model_strategy(classification.task_type),
        risks=sorted(set(risks)),
        observations=classification.reasons + review.observations,
        next_actions=_next_actions(classification.task_type, bool(risks)),
    )


def _choose_mode(task_type: str, preferred_mode: str) -> str:
    if preferred_mode in {"fixed_model", "multi_model", "observe_only"}:
        return preferred_mode
    if task_type in {
        "light_qa",
        "operation_confirmation",
        "writing_generation",
    }:
        return "fixed_model_optimization"
    return "multi_model_suggested"


def _model_strategy(task_type: str) -> dict[str, str]:
    if task_type == "light_qa":
        return {"observe": "rules", "final": "current_model"}
    if task_type == "operation_confirmation":
        return {"validate": "rules", "final": "current_model", "confirm": "human"}
    if task_type in {"intraday_anomaly_attribution", "deep_analysis"}:
        return {
            "classify": "rules_or_cheap_model",
            "final_reasoning": "strong_model",
            "fact_check": "rules",
        }
    if task_type == "code_analysis":
        return {
            "select_context": "rules_or_embedding",
            "final_reasoning": "current_or_strong_model",
            "verify": "tests",
        }
    return {"classify": "rules", "final": "current_model"}


def _task_risks(task_type: str) -> list[str]:
    if task_type == "intraday_anomaly_attribution":
        return [
            "requires_realtime_data",
            "requires_source_attribution",
            "do_not_rely_only_on_history",
        ]
    if task_type == "operation_confirmation":
        return ["requires_human_confirmation"]
    if task_type == "high_risk_document_review":
        return ["high_stakes_review", "requires_human_review"]
    return []


def _next_actions(task_type: str, has_risks: bool) -> list[str]:
    actions = ["show_sidecar_summary"]
    if has_risks:
        actions.append("surface_non_blocking_risk_badge")
    if task_type in {"deep_analysis", "intraday_anomaly_attribution", "code_analysis"}:
        actions.append("review_context_before_send")
    return actions

