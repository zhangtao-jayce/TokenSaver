"""Local storage for TokenSaver Agent run traces."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .brief import generate_repair_brief, generate_run_summary
from .update import check_for_update, format_update_notice


class LocalStore:
    """Small local JSONL store for Agent runs and latest markdown artifacts."""

    def __init__(self, root: str | Path = ".tokensaver") -> None:
        self.root = Path(root)
        self.runs_path = self.root / "runs.jsonl"
        self.reports_dir = self.root / "reports"
        self.briefs_dir = self.root / "briefs"
        self.panel_dir = self.root / "panel"

    def save_run(self, run: dict[str, Any]) -> dict[str, str]:
        self.root.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.briefs_dir.mkdir(parents=True, exist_ok=True)
        self.panel_dir.mkdir(parents=True, exist_ok=True)

        with self.runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(run, ensure_ascii=False, sort_keys=True) + "\n")

        update_info = _check_update_for_artifacts()
        if update_info:
            run["tokensaver_update"] = update_info

        summary = generate_run_summary(run, update_info=update_info)
        brief = generate_repair_brief(run, update_info=update_info)
        report_path = self.reports_dir / "latest.md"
        brief_path = self.briefs_dir / "latest.md"
        report_path.write_text(summary, encoding="utf-8")
        brief_path.write_text(brief, encoding="utf-8")
        panel_path = self.panel_dir / "index.html"
        panel_path.write_text(self._render_panel(run, update_info=update_info), encoding="utf-8")
        return {
            "runs_path": str(self.runs_path),
            "report_path": str(report_path),
            "brief_path": str(brief_path),
            "panel_path": str(panel_path),
        }

    def load_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.runs_path.exists():
            return []
        lines = self.runs_path.read_text(encoding="utf-8").splitlines()
        selected = lines[-limit:] if limit > 0 else lines
        runs: list[dict[str, Any]] = []
        for line in selected:
            if not line.strip():
                continue
            runs.append(json.loads(line))
        return runs

    def latest_run(self) -> dict[str, Any] | None:
        runs = self.load_runs(limit=1)
        return runs[0] if runs else None

    def find_run(self, run_id: str) -> dict[str, Any] | None:
        for run in self.load_runs(limit=0):
            if str(run.get("run_id")) == run_id:
                return run
        return None

    def compare_runs(self, before_id: str, after_id: str) -> dict[str, Any]:
        before = self.find_run(before_id)
        after = self.find_run(after_id)
        if before is None:
            raise ValueError(f"Run not found: {before_id}")
        if after is None:
            raise ValueError(f"Run not found: {after_id}")
        return compare_runs(before, after)

    def read_latest_report(self) -> str:
        path = self.reports_dir / "latest.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def read_latest_brief(self) -> str:
        path = self.briefs_dir / "latest.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _render_panel(
        self,
        latest: dict[str, Any],
        *,
        update_info: dict[str, Any] | None = None,
    ) -> str:
        runs = self.load_runs(limit=20)
        rows = "\n".join(_run_row(run) for run in reversed(runs))
        diagnosis = latest.get("diagnosis") or {}
        findings = "".join(
            f"<li><strong>{_esc(str(item.get('code')))}</strong>: {_esc(str(item.get('message')))}</li>"
            for item in diagnosis.get("findings") or []
        )
        consumers = "".join(
            f"<li><strong>{_esc(str(item.get('kind')))}</strong> {_esc(str(item.get('name')))}: {_esc(str(item.get('tokens')))} tokens</li>"
            for item in diagnosis.get("top_token_consumers") or []
        )
        dimensions = "".join(
            f"<li><strong>{_esc(str(name))}</strong>: {_esc(str(score))}</li>"
            for name, score in (diagnosis.get("dimensions") or {}).items()
        )
        update_notice = _render_update_notice(update_info)
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>TokenSaver Activity Panel</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 32px; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 16px; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 8px; text-align: left; }}
    .score {{ font-size: 40px; font-weight: 700; }}
    .muted {{ color: #6b7280; }}
  </style>
</head>
<body>
  <h1>TokenSaver Activity Panel</h1>
  <p class="muted">Local-only summary generated from the latest Agent run.</p>
  {update_notice}
  <div class="score">{_esc(str(diagnosis.get("roi_score", 100)))}</div>
  <p>{_esc(str(latest.get("app", "")))} / {_esc(str(latest.get("channel", "")))} / {_esc(str(latest.get("task_type", "")))}</p>
  <h2>ROI Dimensions</h2>
  <ul>{dimensions or "<li>No dimension scores available.</li>"}</ul>
  <h2>Top Token Consumers</h2>
  <ul>{consumers or "<li>No token consumers recorded.</li>"}</ul>
  <h2>Latest Findings</h2>
  <ul>{findings or "<li>No low-ROI pattern detected.</li>"}</ul>
  <h2>Recent Runs</h2>
  <table>
    <thead><tr><th>App</th><th>Task</th><th>Route</th><th>Input</th><th>Output</th><th>ROI</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""


def _run_row(run: dict[str, Any]) -> str:
    diagnosis = run.get("diagnosis") or {}
    return (
        "<tr>"
        f"<td>{_esc(str(run.get('app', '')))}</td>"
        f"<td>{_esc(str(run.get('task_type', '')))}</td>"
        f"<td>{_esc(str(run.get('route', '')))}</td>"
        f"<td>{_esc(str(run.get('input_tokens', 0)))}</td>"
        f"<td>{_esc(str(run.get('output_tokens', 0)))}</td>"
        f"<td>{_esc(str(diagnosis.get('roi_score', 100)))}</td>"
        f"<td>{_esc(str(diagnosis.get('status', 'ok')))}</td>"
        "</tr>"
    )


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _check_update_for_artifacts() -> dict[str, Any] | None:
    if os.environ.get("TOKENSAVER_CHECK_UPDATE_ON_RUN", "1") == "0":
        return None
    info = check_for_update(timeout=0.35)
    if info.status != "update_available":
        return None
    return info.to_dict()


def _render_update_notice(update_info: dict[str, Any] | None) -> str:
    notice = format_update_notice(update_info)
    if not notice:
        return ""
    latest = update_info.get("latest_version", "latest") if update_info else "latest"
    command = update_info.get("upgrade_command", "") if update_info else ""
    return (
        '<section style="border:1px solid #f59e0b; background:#fffbeb; padding:12px; margin:16px 0;">'
        f"<strong>TokenSaver update available: {_esc(str(latest))}</strong>"
        f"<pre>{_esc(str(command))}</pre>"
        "</section>"
    )


def compare_runs(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_codes = _normalized_finding_codes(before)
    after_codes = _normalized_finding_codes(after)
    fields = ("input_tokens", "output_tokens", "latency_ms", "answer_tokens")
    deltas = {}
    for field in fields:
        before_value = int(before.get(field) or 0)
        after_value = int(after.get(field) or 0)
        deltas[field] = {
            "before": before_value,
            "after": after_value,
            "delta": after_value - before_value,
            "delta_pct": _pct_delta(before_value, after_value),
        }
    before_score = int((before.get("diagnosis") or {}).get("roi_score", 100))
    after_score = int((after.get("diagnosis") or {}).get("roi_score", 100))
    quality_blockers = sorted(
        code for code in after_codes if code in {"required_field_missing", "quality_regression_risk"}
    )
    accepted = after_score >= before_score and not quality_blockers
    return {
        "before_run_id": before.get("run_id"),
        "after_run_id": after.get("run_id"),
        "deltas": deltas,
        "roi_score": {
            "before": before_score,
            "after": after_score,
            "delta": after_score - before_score,
        },
        "resolved_findings": sorted(before_codes - after_codes),
        "new_findings": sorted(after_codes - before_codes),
        "unchanged_findings": sorted(before_codes & after_codes),
        "result": "accepted" if accepted else "rejected",
        "quality_blockers": quality_blockers,
    }


def _pct_delta(before: int, after: int) -> float | None:
    if before == 0:
        return None
    return round((after - before) / before * 100, 2)


_FINDING_CODE_ALIASES = {
    "wrong_route_for_task": "deep_route_for_short_task",
    "tool_output_too_large": "oversized_tool_output",
    "raw_tool_payload": "raw_payload_in_default_path",
    "repeated_tool_without_cache": "repeated_tool_call_without_cache",
    "context_item_too_large": "oversized_context_item",
    "history_context_waste": "history_context_pollution",
    "answer_too_long_for_channel": "channel_output_over_budget",
    "overpowered_model_for_quick_task": "strong_model_for_simple_task",
    "missing_required_quality_field": "required_field_missing",
    "quality_fields_not_verified": "quality_regression_risk",
}


def normalize_finding_code(code: str) -> str:
    return _FINDING_CODE_ALIASES.get(code, code)


def _normalized_finding_codes(run: dict[str, Any]) -> set[str]:
    codes = (run.get("diagnosis") or {}).get("finding_codes") or []
    return {normalize_finding_code(str(code)) for code in codes}
