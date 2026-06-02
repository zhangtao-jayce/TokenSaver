"""Local storage for TokenSaver Agent run traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .brief import generate_repair_brief, generate_run_summary


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

        summary = generate_run_summary(run)
        brief = generate_repair_brief(run)
        report_path = self.reports_dir / "latest.md"
        brief_path = self.briefs_dir / "latest.md"
        report_path.write_text(summary, encoding="utf-8")
        brief_path.write_text(brief, encoding="utf-8")
        panel_path = self.panel_dir / "index.html"
        panel_path.write_text(self._render_panel(run), encoding="utf-8")
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

    def read_latest_report(self) -> str:
        path = self.reports_dir / "latest.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def read_latest_brief(self) -> str:
        path = self.briefs_dir / "latest.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _render_panel(self, latest: dict[str, Any]) -> str:
        runs = self.load_runs(limit=20)
        rows = "\n".join(_run_row(run) for run in reversed(runs))
        diagnosis = latest.get("diagnosis") or {}
        findings = "".join(
            f"<li><strong>{_esc(str(item.get('code')))}</strong>: {_esc(str(item.get('message')))}</li>"
            for item in diagnosis.get("findings") or []
        )
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
  <div class="score">{_esc(str(diagnosis.get("roi_score", 100)))}</div>
  <p>{_esc(str(latest.get("app", "")))} / {_esc(str(latest.get("channel", "")))} / {_esc(str(latest.get("task_type", "")))}</p>
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
