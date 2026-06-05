"""Profile loading and templates for TokenSaver diagnostics."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_PROFILE: dict[str, Any] = {
    "app": "agent",
    "channel": "runtime",
    "budgets": {
        "default": {"input_tokens": 12000, "output_tokens": 1500, "latency_ms": 90000},
        "quick_question": {"input_tokens": 3000, "output_tokens": 500, "latency_ms": 20000},
        "quick_quote_check": {"input_tokens": 3000, "output_tokens": 500, "latency_ms": 20000},
        "light_qa": {"input_tokens": 3000, "output_tokens": 500, "latency_ms": 20000},
        "operation_confirmation": {"input_tokens": 5000, "output_tokens": 700, "latency_ms": 30000},
        "deep_research": {"input_tokens": 30000, "output_tokens": 3000, "latency_ms": 180000},
        "deep_analysis": {"input_tokens": 30000, "output_tokens": 3000, "latency_ms": 180000},
        "system_debug": {"input_tokens": 12000, "output_tokens": 1500, "latency_ms": 90000},
    },
    "channel_budgets": {
        "chat": {
            "quick_question": {"input_tokens": 3000, "output_tokens": 500, "latency_ms": 20000},
        },
        "slack": {
            "quick_question": {"input_tokens": 8000, "output_tokens": 800, "latency_ms": 30000},
        },
        "lark": {
            "quick_question": {"input_tokens": 8000, "output_tokens": 800, "latency_ms": 30000},
        },
        "feishu": {
            "quick_question": {"input_tokens": 8000, "output_tokens": 800, "latency_ms": 30000},
        },
        "wechat": {
            "quick_question": {"input_tokens": 8000, "output_tokens": 800, "latency_ms": 30000},
        },
        "report": {
            "deep_research": {"input_tokens": 60000, "output_tokens": 8000, "latency_ms": 300000},
            "deep_analysis": {"input_tokens": 60000, "output_tokens": 8000, "latency_ms": 300000},
        },
    },
    "short_channels": ["chat", "slack", "lark", "feishu", "wechat"],
    "quick_tasks": ["quick_question", "quick_quote_check", "light_qa"],
    "sensitive_tasks": ["operation_confirmation"],
    "deep_route_words": ["deep", "research", "investigate", "report"],
    "required_fields": {},
    "tool_policies": {},
    "intent_patterns": {},
    "answer_density": {
        "caveat_words": ["unavailable", "not available"],
        "followup_words": ["follow up"],
    },
    "thresholds": {
        "large_context_item_tokens": 8000,
        "quick_history_context_tokens": 2000,
        "large_tool_output_tokens": 4000,
        "dominant_tool_output_share": 0.30,
        "short_channel_answer_tokens": 1200,
        "short_channel_answer_high_tokens": 5000,
        "raw_payload_record_count": 50,
    },
}


PROFILE_TEMPLATES: dict[str, dict[str, Any]] = {
    "chatbot": {
        "app": "my_chatbot",
        "channel": "chat",
        "required_fields": {
            "quick_question": ["answer", "next_action"],
        },
    },
    "coding-agent": {
        "app": "my_coding_agent",
        "channel": "cli",
        "budgets": {
            "small_code_change": {"input_tokens": 12000, "output_tokens": 1800, "latency_ms": 90000},
            "code_review": {"input_tokens": 30000, "output_tokens": 3500, "latency_ms": 180000},
        },
        "quick_tasks": ["quick_question", "light_qa", "small_code_change"],
        "required_fields": {
            "small_code_change": ["summary", "tests"],
            "code_review": ["findings", "risk"],
        },
        "tool_policies": {
            "read_file": {"default_mode": "targeted"},
            "search": {"max_output_tokens": 6000},
        },
    },
    "support-bot": {
        "app": "my_support_bot",
        "channel": "chat",
        "required_fields": {
            "quick_question": ["answer", "resolution_step"],
            "operation_confirmation": ["confirmation", "next_action"],
        },
    },
    "research-agent": {
        "app": "my_research_agent",
        "channel": "report",
        "required_fields": {
            "deep_research": ["conclusion", "evidence", "limitations"],
        },
    },
    "finance-assistant": {
        "app": "my_finance_assistant",
        "channel": "chat",
        "budgets": {
            "realtime_analysis": {"input_tokens": 12000, "output_tokens": 1500, "latency_ms": 60000},
            "deep_research": {"input_tokens": 50000, "output_tokens": 5000, "latency_ms": 180000},
        },
        "sensitive_tasks": ["operation_confirmation", "realtime_analysis"],
        "intent_patterns": {
            "market_move_explanation": {
                "keywords": [
                    "放量",
                    "下跌",
                    "上涨",
                    "突然涨",
                    "突然跌",
                    "异动",
                    "原因分析",
                    "why is",
                    "why did",
                    "move",
                    "drop",
                    "rally",
                    "selloff",
                ],
                "expected_route_words": ["intraday", "anomaly", "realtime", "market_move", "market"],
                "expected_task_type_candidates": [
                    "intraday_anomaly",
                    "market_move_explanation",
                    "realtime_analysis",
                ],
            },
        },
        "answer_density": {
            "caveat_words": ["待核验", "数据缺口", "无法确认", "unavailable", "not available"],
            "followup_words": ["可继续追问", "继续追问", "follow up"],
        },
        "required_fields": {
            "quick_question": ["conclusion", "evidence", "risk"],
            "realtime_analysis": ["conclusion", "evidence", "as_of_time", "risk"],
            "deep_research": ["conclusion", "evidence", "risk", "limitations"],
        },
    },
    "legal-assistant": {
        "app": "my_legal_assistant",
        "channel": "chat",
        "budgets": {
            "document_review": {"input_tokens": 40000, "output_tokens": 4000, "latency_ms": 180000},
        },
        "sensitive_tasks": ["operation_confirmation", "document_review"],
        "required_fields": {
            "quick_question": ["conclusion", "basis", "risk"],
            "document_review": ["issue", "basis", "risk", "next_action"],
        },
    },
    "crm-agent": {
        "app": "my_crm_agent",
        "channel": "chat",
        "budgets": {
            "account_summary": {"input_tokens": 16000, "output_tokens": 1800, "latency_ms": 90000},
            "operation_confirmation": {"input_tokens": 5000, "output_tokens": 700, "latency_ms": 30000},
        },
        "required_fields": {
            "account_summary": ["summary", "recent_activity", "next_action"],
            "operation_confirmation": ["confirmation", "record_id", "next_action"],
        },
        "tool_policies": {
            "read_customer_records": {"default_mode": "summary", "allow_full_when_user_asks": True},
            "search_crm": {"max_output_tokens": 6000},
        },
    },
}


def load_profile(path: str | Path | None = None) -> dict[str, Any]:
    """Return a merged profile, using defaults when no path is supplied."""

    profile = deepcopy(DEFAULT_PROFILE)
    if not path:
        return profile
    loaded = _read_profile_file(Path(path))
    _deep_merge(profile, loaded)
    return profile


def template_profile(name: str) -> dict[str, Any]:
    if name not in PROFILE_TEMPLATES:
        choices = ", ".join(sorted(PROFILE_TEMPLATES))
        raise ValueError(f"Unknown profile template {name!r}. Choices: {choices}")
    profile = deepcopy(DEFAULT_PROFILE)
    _deep_merge(profile, PROFILE_TEMPLATES[name])
    return profile


def write_profile_template(path: str | Path, *, template: str = "chatbot") -> dict[str, Any]:
    profile = template_profile(template)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dump_profile(profile), encoding="utf-8")
    return profile


def dump_profile(profile: dict[str, Any]) -> str:
    return _dump_yaml(profile).rstrip() + "\n"


def profile_required_fields(profile: dict[str, Any], task_type: str) -> list[str]:
    required = profile.get("required_fields") or {}
    if isinstance(required, list):
        return [str(item) for item in required]
    if isinstance(required, dict):
        fields = required.get(task_type) or required.get("default") or []
        if isinstance(fields, list):
            return [str(item) for item in fields]
    return []


def _read_profile_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        value = json.loads(text)
    else:
        value = _parse_yaml_subset(text)
    if not isinstance(value, dict):
        raise ValueError(f"Profile must be an object: {path}")
    return value


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = deepcopy(value)


def _parse_yaml_subset(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    lines = text.splitlines()
    for index, raw in enumerate(lines):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if stripped.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError(f"YAML list item has non-list parent: {raw}")
            parent.append(_parse_scalar(stripped[2:].strip()))
            continue
        key, sep, value = stripped.partition(":")
        if not sep:
            raise ValueError(f"Unsupported profile YAML line: {raw}")
        key = key.strip()
        value = value.strip()
        if value:
            parent[key] = _parse_scalar(value)
            continue
        container: Any = _next_container(lines, index)
        parent[key] = container
        stack.append((indent, container))
    return root


def _next_container(lines: list[str], index: int) -> Any:
    current = lines[index]
    current_indent = len(current) - len(current.lstrip(" "))
    for raw in lines[index + 1:]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent <= current_indent:
            return {}
        return [] if raw.strip().startswith("- ") else {}
    return {}


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        return json.loads(value.replace("'", '"'))
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    return value


def _dump_yaml(value: Any, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.append(_dump_yaml(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {_format_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        return "\n".join(f"{prefix}- {_format_scalar(item)}" for item in value)
    return f"{prefix}{_format_scalar(value)}"


def _format_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if not text or any(char in text for char in ":#[]{}") or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    return text
