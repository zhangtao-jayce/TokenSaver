"""Rule-first task classification."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskClassification:
    task_type: str
    confidence: float
    reasons: list[str]


_REALTIME_WORDS = (
    "现在", "刚刚", "盘中", "突然", "拉升", "跳水", "涨", "跌",
    "today", "now", "intraday", "spike", "dump", "move",
)
_TRADE_WORDS = (
    "减仓", "加仓", "买", "卖", "持仓", "候选池", "watchlist",
    "position", "buy", "sell", "trim", "add",
)
_COMPARE_WORDS = ("对比", "比较", "vs", " versus ", "哪个好", "谁更")
_CODE_WORDS = (
    "bug", "报错", "修复", "代码", "diff", "stack trace", "test",
    "function", "class", "文件",
)
_WRITING_WORDS = ("写", "润色", "总结", "报告", "文案", "outline", "draft")
_LEGAL_WORDS = ("合同", "条款", "法务", "合规", "liability", "contract")


def classify_task(user_message: str) -> TaskClassification:
    text = (user_message or "").strip()
    lowered = text.lower()
    reasons: list[str] = []

    def has_any(words: tuple[str, ...]) -> bool:
        return any(word.lower() in lowered for word in words)

    realtime = has_any(_REALTIME_WORDS)
    trade = has_any(_TRADE_WORDS)
    compare = has_any(_COMPARE_WORDS) or len(_extract_ticker_like(text)) > 1
    code = has_any(_CODE_WORDS)
    writing = has_any(_WRITING_WORDS)
    legal = has_any(_LEGAL_WORDS)

    if realtime and trade:
        reasons.append("Contains realtime market/action wording.")
        return TaskClassification("intraday_anomaly_attribution", 0.86, reasons)
    if trade:
        reasons.append("Contains operation or portfolio wording.")
        return TaskClassification("operation_confirmation", 0.78, reasons)
    if compare:
        reasons.append("Contains comparison wording or multiple symbols.")
        return TaskClassification("multi_object_comparison", 0.74, reasons)
    if realtime:
        reasons.append("Contains realtime or time-sensitive wording.")
        return TaskClassification("realtime_analysis", 0.72, reasons)
    if code:
        reasons.append("Contains coding/debugging wording.")
        return TaskClassification("code_analysis", 0.72, reasons)
    if legal:
        reasons.append("Contains legal/compliance wording.")
        return TaskClassification("high_risk_document_review", 0.68, reasons)
    if writing:
        reasons.append("Contains writing/summarization wording.")
        return TaskClassification("writing_generation", 0.66, reasons)

    if len(text) < 120:
        reasons.append("Short request with no high-risk trigger.")
        return TaskClassification("light_qa", 0.62, reasons)

    reasons.append("Long request without a stronger specialized trigger.")
    return TaskClassification("deep_analysis", 0.56, reasons)


def _extract_ticker_like(text: str) -> list[str]:
    import re

    return re.findall(r"(?<![A-Z])([A-Z]{2,5})(?![A-Z])", text)

