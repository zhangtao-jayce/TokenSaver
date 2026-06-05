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
        diagnosis = latest.get("diagnosis") or {}
        findings = list(diagnosis.get("findings") or [])
        brief = generate_repair_brief(latest, update_info=update_info)
        roi_score = int(diagnosis.get("roi_score") or 100)
        status = str(diagnosis.get("status") or "ok")
        risk = _risk_state(latest)
        update_notice = _render_update_notice(update_info)
        rows = "\n".join(_run_row(run) for run in reversed(runs))
        top_waste = "".join(_top_waste_item(item) for item in _top_waste(latest))
        finding_cards = "".join(_finding_card(item) for item in findings[:8])
        recommendations = "".join(
            f"<li>{_esc(text)}</li>" for text in _top_recommendations(findings, limit=5)
        )
        dimensions = "".join(
            f'<div class="dimension"><span>{_esc(str(name))}</span><strong>{_esc(str(score))}</strong></div>'
            for name, score in (diagnosis.get("dimensions") or {}).items()
        )
        trend = _trend_summary(runs)
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TokenSaver Local ROI Report</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #18212f;
      --muted: #657084;
      --line: #d8dee8;
      --surface: #ffffff;
      --soft: #f6f8fb;
      --good: #16794a;
      --warn: #a05a00;
      --bad: #b42318;
      --blue: #2457a6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--soft);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    header {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 20px;
      align-items: end;
      padding: 10px 0 22px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; line-height: 1.1; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 19px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 6px; font-size: 15px; letter-spacing: 0; }}
    p {{ margin: 0; }}
    button {{
      border: 1px solid #173f7a;
      background: var(--blue);
      color: white;
      border-radius: 6px;
      padding: 10px 14px;
      font: inherit;
      cursor: pointer;
    }}
    button:focus {{ outline: 3px solid #b9d2ff; outline-offset: 2px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 9px 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    textarea {{
      width: 100%;
      min-height: 220px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      font: 13px ui-monospace, SFMono-Regular, Menlo, monospace;
      color: var(--ink);
      background: #fbfcfe;
      resize: vertical;
    }}
    .muted {{ color: var(--muted); }}
    .local {{ color: var(--good); font-weight: 700; }}
    .grid {{ display: grid; gap: 16px; }}
    .two {{ grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr); }}
    .metrics {{ grid-template-columns: repeat(5, minmax(130px, 1fr)); }}
    .section {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin-top: 18px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 150px minmax(0, 1fr);
      gap: 18px;
      align-items: center;
    }}
    .score {{
      width: 132px;
      height: 132px;
      display: grid;
      place-items: center;
      border-radius: 50%;
      border: 10px solid #c9ddff;
      background: #f8fbff;
      color: var(--blue);
      font-size: 40px;
      font-weight: 800;
    }}
    .badge {{
      display: inline-block;
      border-radius: 999px;
      padding: 4px 9px;
      font-size: 12px;
      font-weight: 700;
      margin-right: 6px;
      border: 1px solid var(--line);
      background: #f8fafc;
    }}
    .risk-ok {{ color: var(--good); border-color: #a9d6be; background: #f2fbf6; }}
    .risk-optimize {{ color: var(--warn); border-color: #e4c27f; background: #fff8e8; }}
    .risk-high {{ color: var(--bad); border-color: #f2afa8; background: #fff3f1; }}
    .metric {{
      border-left: 4px solid #88a9db;
      padding: 10px 10px 10px 12px;
      background: #fbfcfe;
      min-width: 0;
    }}
    .metric span, .dimension span {{ display: block; color: var(--muted); font-size: 12px; }}
    .metric strong {{ display: block; margin-top: 2px; font-size: 23px; overflow-wrap: anywhere; }}
    .dimension {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      border-bottom: 1px solid var(--line);
      padding: 8px 0;
    }}
    .waste, .finding {{
      border: 1px solid var(--line);
      border-left-width: 4px;
      border-radius: 6px;
      padding: 12px;
      margin-top: 10px;
      background: #fbfcfe;
    }}
    .waste {{ border-left-color: #7a8ca6; }}
    .finding.low {{ border-left-color: #6aa57a; }}
    .finding.medium {{ border-left-color: #d0973e; }}
    .finding.high {{ border-left-color: #c4554d; }}
    .finding.critical {{ border-left-color: #8f1f17; }}
    .finding code {{ font-size: 12px; color: #334155; }}
    .finding dl {{ margin: 8px 0 0; }}
    .finding dt {{ color: var(--muted); font-size: 12px; font-weight: 700; }}
    .finding dd {{ margin: 2px 0 8px; }}
    .brief-actions {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }}
    .copy-status {{ color: var(--good); min-height: 1.4em; }}
    @media (max-width: 860px) {{
      main {{ padding: 18px; }}
      header, .two, .hero {{ grid-template-columns: 1fr; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .score {{ width: 112px; height: 112px; font-size: 34px; }}
    }}
    @media (max-width: 520px) {{
      .metrics {{ grid-template-columns: 1fr; }}
      th, td {{ padding: 8px 4px; font-size: 13px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>TokenSaver Local ROI Report</h1>
        <p class="muted">A local health report for the latest Agent run. <span class="local">All data stays local.</span></p>
      </div>
      <div>
        <span class="badge {_esc(risk['class'])}">{_esc(risk['label'])}</span>
        <span class="badge">{_esc(status)}</span>
      </div>
    </header>
    {update_notice}

    <section class="section hero">
      <div class="score">{_esc(str(roi_score))}</div>
      <div>
        <h2>Latest Run</h2>
        <p>
          <strong>{_esc(str(latest.get("app", "")))}</strong>
          <span class="muted"> / {_esc(str(latest.get("channel", "")))} / {_esc(str(latest.get("task_type", "")))} / {_esc(str(latest.get("route", "")))}</span>
        </p>
        <p class="muted" style="margin-top:8px;">{_esc(risk['explanation'])}</p>
      </div>
    </section>

    <section class="section">
      <h2>Cost Overview</h2>
      <div class="grid metrics">
        {_metric("Input Tokens", latest.get("input_tokens", 0))}
        {_metric("Output Tokens", latest.get("output_tokens", 0))}
        {_metric("Latency", f"{int(latest.get('latency_ms') or 0)}ms")}
        {_metric("Model Calls", len(latest.get("model_calls") or []))}
        {_metric("Tool Calls", len(latest.get("tool_calls") or []))}
      </div>
    </section>

    <div class="grid two">
      <section class="section">
        <h2>Top Waste</h2>
        {top_waste or '<p class="muted">No obvious token or latency waste recorded.</p>'}
      </section>
      <section class="section">
        <h2>ROI Dimensions</h2>
        {dimensions or '<p class="muted">No dimension scores available.</p>'}
      </section>
    </div>

    <section class="section">
      <h2>Findings</h2>
      {finding_cards or '<p class="muted">No low-ROI pattern detected by the current local rules.</p>'}
    </section>

    <section class="section">
      <h2>Repair Brief</h2>
      <div class="brief-actions">
        <button type="button" onclick="copyBrief()">Copy Full Brief</button>
        <span class="copy-status" id="copyStatus"></span>
        <span class="muted">Open latest brief at <code>briefs/latest.md</code></span>
      </div>
      <h3>Most Important Next Steps</h3>
      <ol>{recommendations or '<li>Keep the current design unless new evidence appears.</li>'}</ol>
      <textarea id="briefText" readonly>{_esc(brief)}</textarea>
    </section>

    <section class="section">
      <h2>Recent Runs</h2>
      <p class="muted">{_esc(trend)}</p>
      <table>
        <thead><tr><th>App</th><th>Time</th><th>Task</th><th>Route</th><th>Input</th><th>Latency</th><th>ROI</th><th>Status</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
  </main>
  <script>
    function copyBrief() {{
      var text = document.getElementById('briefText');
      text.focus();
      text.select();
      var done = function() {{
        document.getElementById('copyStatus').textContent = 'Brief copied';
      }};
      if (navigator.clipboard && window.isSecureContext) {{
        navigator.clipboard.writeText(text.value).then(done).catch(function() {{
          document.execCommand('copy');
          done();
        }});
      }} else {{
        document.execCommand('copy');
        done();
      }}
    }}
  </script>
</body>
</html>
"""


def _run_row(run: dict[str, Any]) -> str:
    diagnosis = run.get("diagnosis") or {}
    return (
        "<tr>"
        f"<td>{_esc(str(run.get('app', '')))}</td>"
        f"<td>{_esc(_format_time(run.get('started_at') or run.get('ended_at')))}</td>"
        f"<td>{_esc(str(run.get('task_type', '')))}</td>"
        f"<td>{_esc(str(run.get('route', '')))}</td>"
        f"<td>{_esc(str(run.get('input_tokens', 0)))}</td>"
        f"<td>{_esc(str(run.get('latency_ms', 0)))}ms</td>"
        f"<td>{_esc(str(diagnosis.get('roi_score', 100)))}</td>"
        f"<td>{_esc(str(diagnosis.get('status', 'ok')))}</td>"
        "</tr>"
    )


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{_esc(label)}</span>"
        f"<strong>{_esc(str(value))}</strong>"
        "</div>"
    )


def _risk_state(run: dict[str, Any]) -> dict[str, str]:
    diagnosis = run.get("diagnosis") or {}
    findings = diagnosis.get("findings") or []
    codes = set(diagnosis.get("finding_codes") or [])
    severities = {str(item.get("severity") or "").lower() for item in findings if isinstance(item, dict)}
    roi_score = int(diagnosis.get("roi_score") or 100)
    quality_codes = {
        "required_field_missing",
        "quality_regression_risk",
        "missing_source_for_sensitive_task",
        "missing_human_review_for_high_risk_task",
    }
    if codes & quality_codes or "critical" in severities:
        return {
            "label": "Quality Risk",
            "class": "risk-high",
            "explanation": "This run may have quality or safety gaps. Keep guardrails before optimizing cost.",
        }
    if roi_score < 55 or "high" in severities:
        return {
            "label": "High Cost",
            "class": "risk-high",
            "explanation": "This run has high-severity waste or a low ROI score. Review Top Waste and copy the brief.",
        }
    if roi_score < 85 or findings:
        return {
            "label": "Optimizable",
            "class": "risk-optimize",
            "explanation": "This run works, but local rules found route, context, tool, model, or channel waste.",
        }
    return {
        "label": "Healthy",
        "class": "risk-ok",
        "explanation": "No major low-ROI pattern was detected. Keep the current design unless new evidence appears.",
    }


def _top_waste(run: dict[str, Any]) -> list[dict[str, Any]]:
    diagnosis = run.get("diagnosis") or {}
    consumers = list(diagnosis.get("top_token_consumers") or [])
    latency = list(diagnosis.get("top_latency_consumers") or [])
    items: list[dict[str, Any]] = []
    categories = [
        ("Largest Context", lambda item: item.get("kind") == "context"),
        ("Largest Tool Output", lambda item: item.get("kind") == "tool_output"),
        ("Largest Model Input", lambda item: item.get("kind") == "model_input"),
        ("Longest Answer", lambda item: item.get("kind") == "answer"),
    ]
    for label, predicate in categories:
        match = next((item for item in consumers if predicate(item)), None)
        if match:
            items.append(
                {
                    "label": label,
                    "name": match.get("name"),
                    "value": f"{int(match.get('tokens') or 0)} tokens",
                }
            )
    slow_tool = next((item for item in latency if item.get("kind") == "tool"), None)
    if slow_tool:
        items.append(
            {
                "label": "Slowest Tool",
                "name": slow_tool.get("name"),
                "value": f"{int(slow_tool.get('latency_ms') or 0)}ms",
            }
        )
    return items[:5]


def _top_waste_item(item: dict[str, Any]) -> str:
    return (
        '<div class="waste">'
        f"<h3>{_esc(str(item.get('label', 'Waste')))}</h3>"
        f"<p><strong>{_esc(str(item.get('name', 'unknown')))}</strong></p>"
        f"<p class=\"muted\">{_esc(str(item.get('value', '')))}</p>"
        "</div>"
    )


def _finding_card(finding: dict[str, Any]) -> str:
    severity = str(finding.get("severity") or "low").lower()
    evidence = finding.get("evidence") or {}
    evidence_text = _inline_evidence(evidence) if isinstance(evidence, dict) else str(evidence)
    return (
        f'<article class="finding {_esc(severity)}">'
        f"<h3>{_esc(str(finding.get('message') or 'Finding'))}</h3>"
        f"<p><span class=\"badge\">{_esc(severity)}</span> <code>{_esc(str(finding.get('code') or ''))}</code></p>"
        "<dl>"
        f"<dt>Evidence</dt><dd>{_esc(evidence_text or 'No structured evidence recorded.')}</dd>"
        f"<dt>Recommendation</dt><dd>{_esc(str(finding.get('recommendation') or 'Review this workflow.'))}</dd>"
        f"<dt>Impact</dt><dd>{_esc(str(finding.get('impact') or 'May reduce Agent ROI.'))}</dd>"
        "</dl>"
        "</article>"
    )


def _top_recommendations(findings: list[dict[str, Any]], *, limit: int) -> list[str]:
    seen: set[str] = set()
    recommendations: list[str] = []
    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_findings = sorted(
        findings,
        key=lambda item: severity_rank.get(str(item.get("severity") or "").lower(), 9),
    )
    for finding in sorted_findings:
        recommendation = str(finding.get("recommendation") or "").strip()
        if not recommendation or recommendation in seen:
            continue
        seen.add(recommendation)
        recommendations.append(recommendation)
        if len(recommendations) >= limit:
            break
    return recommendations


def _trend_summary(runs: list[dict[str, Any]]) -> str:
    if not runs:
        return "No recent runs recorded yet."
    count = len(runs)
    avg_input = round(sum(int(run.get("input_tokens") or 0) for run in runs) / count)
    avg_latency = round(sum(int(run.get("latency_ms") or 0) for run in runs) / count)
    common = _most_common_codes(runs, limit=3)
    suffix = f" Most common findings: {', '.join(common)}." if common else ""
    return f"Last {count} runs average {avg_input} input tokens and {avg_latency}ms latency.{suffix}"


def _most_common_codes(runs: list[dict[str, Any]], *, limit: int) -> list[str]:
    counts: dict[str, int] = {}
    for run in runs:
        codes = (run.get("diagnosis") or {}).get("finding_codes") or []
        for code in codes:
            normalized = normalize_finding_code(str(code))
            counts[normalized] = counts.get(normalized, 0) + 1
    return [
        code
        for code, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _inline_evidence(value: dict[str, Any]) -> str:
    return ", ".join(f"{key}={item}" for key, item in value.items())


def _format_time(value: Any) -> str:
    if not value:
        return ""
    try:
        import datetime as _datetime

        return _datetime.datetime.fromtimestamp(float(value)).strftime("%Y-%m-%d %H:%M")
    except (OSError, OverflowError, TypeError, ValueError):
        return str(value)


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
