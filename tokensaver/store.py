"""Local storage for TokenSaver Agent run traces."""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .brief import generate_repair_brief, generate_run_summary
from .update import check_for_update, format_update_notice

TRAFFIC_PRODUCTION = "production_user_run"
TRAFFIC_SMOKE = "smoke_test"
TRAFFIC_DEPLOYMENT = "deployment_audit"
TRAFFIC_TYPES = {TRAFFIC_PRODUCTION, TRAFFIC_SMOKE, TRAFFIC_DEPLOYMENT}


def normalize_traffic_type(value: Any) -> str:
    aliases = {
        None: TRAFFIC_PRODUCTION,
        "": TRAFFIC_PRODUCTION,
        "real": TRAFFIC_PRODUCTION,
        "production": TRAFFIC_PRODUCTION,
        "smoke": TRAFFIC_SMOKE,
        "deployment": TRAFFIC_DEPLOYMENT,
        "audit": TRAFFIC_DEPLOYMENT,
    }
    normalized = aliases.get(value, value)
    if normalized not in TRAFFIC_TYPES:
        raise ValueError(f"Unsupported traffic_type: {value!r}")
    return str(normalized)


class LocalStore:
    """Small local JSONL store for Agent runs and latest markdown artifacts."""

    def __init__(
        self,
        root: str | Path = ".tokensaver",
        *,
        failure_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.root = Path(root)
        self.failure_callback = failure_callback
        self.runs_path = self.root / "runs.jsonl"
        self.reports_dir = self.root / "reports"
        self.briefs_dir = self.root / "briefs"
        self.panel_dir = self.root / "panel"
        self.index_dir = self.root / "index"
        self.health_path = self.root / "health.json"
        self.deployment_path = self.root / "deployment.json"
        self.latest_by_route_path = self.index_dir / "latest_by_route.json"

    def save_run(self, run: dict[str, Any]) -> dict[str, str]:
        started = time.perf_counter()
        run["traffic_type"] = normalize_traffic_type(run.get("traffic_type"))
        try:
            self._ensure_dirs()
            self._append_run(run)
            update_info = _check_update_for_artifacts()
            if update_info:
                run["tokensaver_update"] = update_info
            summary = generate_run_summary(run, update_info=update_info)
            brief = generate_repair_brief(run, update_info=update_info)
            suffix = _traffic_suffix(run["traffic_type"])
            report_path = self.reports_dir / f"latest_{suffix}.md"
            brief_path = self.briefs_dir / f"latest_{suffix}.md"
            panel_path = self.panel_dir / f"{suffix}.html"
            self._atomic_write_text(report_path, summary)
            self._atomic_write_text(brief_path, brief)
            artifacts = {
                "runs_path": str(self.runs_path),
                "report_path": str(report_path),
                "brief_path": str(brief_path),
                "panel_path": str(panel_path),
            }
            current_health = self.read_health()
            current_acceptance = current_health.get("deployment_acceptance") or {}
            preliminary_panel = self._render_panel(
                run,
                update_info=update_info,
                health=current_health,
                acceptance=current_acceptance,
            )
            self._atomic_write_text(panel_path, preliminary_panel)
            acceptance = self._evaluate_deployment_acceptance(run, artifacts)
            health = self._success_health(
                run,
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                acceptance=acceptance,
            )
            panel = self._render_panel(
                run,
                update_info=update_info,
                health=health,
                acceptance=acceptance,
            )
            self._atomic_write_text(panel_path, panel)
            if run["traffic_type"] == TRAFFIC_PRODUCTION:
                generic_report = self.reports_dir / "latest.md"
                generic_brief = self.briefs_dir / "latest.md"
                generic_panel = self.panel_dir / "index.html"
                self._atomic_write_text(generic_report, summary)
                self._atomic_write_text(generic_brief, brief)
                self._atomic_write_text(generic_panel, panel)
                artifacts.update(
                    {
                        "latest_report_path": str(generic_report),
                        "latest_brief_path": str(generic_brief),
                        "latest_panel_path": str(generic_panel),
                    }
                )
            elif not (self.panel_dir / "index.html").exists():
                self._atomic_write_text(self.panel_dir / "index.html", self._render_empty_panel(health))
            self._update_latest_by_route(run, artifacts)
            return artifacts
        except Exception as exc:
            self.record_failure(
                stage=_failure_stage(exc),
                error=str(exc),
                run_id=str(run.get("run_id") or ""),
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
            )
            raise

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
        return self.latest_run_for_traffic(TRAFFIC_PRODUCTION)

    def latest_run_for_traffic(self, traffic_type: str) -> dict[str, Any] | None:
        wanted = normalize_traffic_type(traffic_type)
        runs = self.load_runs(limit=0)
        runs = [run for run in runs if normalize_traffic_type(run.get("traffic_type")) == wanted]
        return runs[-1] if runs else None

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

    def read_latest_report(self, traffic_type: str = TRAFFIC_PRODUCTION) -> str:
        path = self.reports_dir / f"latest_{_traffic_suffix(normalize_traffic_type(traffic_type))}.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def read_latest_brief(self, traffic_type: str = TRAFFIC_PRODUCTION) -> str:
        path = self.briefs_dir / f"latest_{_traffic_suffix(normalize_traffic_type(traffic_type))}.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def read_health(self) -> dict[str, Any]:
        health = self._read_json(self.health_path, _default_health())
        health["deployment_acceptance"] = self._read_json(
            self.deployment_path,
            health.get("deployment_acceptance") or {},
        )
        return health

    def mark_deployment(
        self,
        *,
        host_version: str,
        environment: str = "production",
        tokensaver_version: str | None = None,
    ) -> dict[str, Any]:
        from . import __version__

        try:
            self._ensure_dirs()
            marker = {
                "status": "awaiting",
                "deployed_at": _utc_now(),
                "host_version": host_version,
                "tokensaver_version": tokensaver_version or __version__,
                "environment": environment,
                "missing_fields": [],
                "recommendations": [],
                "accepted_run_id": None,
            }
            self._atomic_write_json(self.deployment_path, marker)
            health = self.read_health()
            health["deployment_acceptance"] = marker
            health["updated_at"] = _utc_now()
            self._atomic_write_json(self.health_path, health)
            return marker
        except Exception as exc:
            self.record_failure(stage=_failure_stage(exc), error=str(exc))
            raise

    def record_failure(
        self,
        *,
        stage: str,
        error: str,
        run_id: str = "",
        latency_ms: float = 0,
    ) -> dict[str, Any]:
        health = self.read_health()
        health.update(
            {
                "status": "failed",
                "updated_at": _utc_now(),
                "last_failure_at": _utc_now(),
                "last_error": {"stage": stage, "message": error, "run_id": run_id},
                "failure_count": int(health.get("failure_count") or 0) + 1,
                "consecutive_failure_count": int(health.get("consecutive_failure_count") or 0) + 1,
                "last_trace_write_latency_ms": latency_ms,
            }
        )
        try:
            self._ensure_dirs()
            self._atomic_write_json(self.health_path, health)
        except OSError:
            pass
        if self.failure_callback is not None:
            try:
                self.failure_callback(
                    {"stage": stage, "error": error, "run_id": run_id, "health": health}
                )
            except Exception as exc:
                print(f"TokenSaver failure callback failed: {exc}", file=sys.stderr)
        return health

    def latest_by_route(self) -> dict[str, Any]:
        return self._read_json(self.latest_by_route_path, {})

    def trend_summary(self, *, limit: int = 100) -> list[dict[str, Any]]:
        groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
        for run in self.load_runs(limit=limit):
            metadata = run.get("metadata") or {}
            key = (
                str(run.get("app") or ""),
                str(metadata.get("host_version") or ""),
                str(metadata.get("tokensaver_version") or ""),
                str(run.get("task_type") or ""),
                str(run.get("route") or ""),
                str(run.get("channel") or ""),
                normalize_traffic_type(run.get("traffic_type")),
            )
            groups.setdefault(key, []).append(run)
        return [_trend_group(key, runs) for key, runs in groups.items()]

    def tool_governance(self, *, limit: int = 100) -> list[dict[str, Any]]:
        totals: dict[str, dict[str, Any]] = {}
        for run in self.load_runs(limit=limit):
            for call in run.get("tool_calls") or []:
                name = str(call.get("name") or "unnamed")
                item = totals.setdefault(
                    name,
                    {"tool": name, "calls": 0, "output_tokens": 0, "latency_ms": 0, "failures": 0},
                )
                item["calls"] += 1
                item["output_tokens"] += int(call.get("output_tokens") or 0)
                item["latency_ms"] += int(call.get("latency_ms") or 0)
                if str(call.get("status") or "ok") not in {"ok", "success"}:
                    item["failures"] += 1
        for item in totals.values():
            calls = max(int(item["calls"]), 1)
            item["avg_output_tokens"] = round(int(item["output_tokens"]) / calls, 2)
            item["avg_latency_ms"] = round(int(item["latency_ms"]) / calls, 2)
            item["failure_rate"] = round(int(item["failures"]) / calls, 3)
        return sorted(
            totals.values(),
            key=lambda item: (item["output_tokens"], item["latency_ms"]),
            reverse=True,
        )

    def _ensure_dirs(self) -> None:
        for path in (
            self.root,
            self.reports_dir,
            self.briefs_dir,
            self.panel_dir,
            self.index_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _append_run(self, run: dict[str, Any]) -> None:
        try:
            with self.runs_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(run, ensure_ascii=False, sort_keys=True) + "\n")
        except OSError as exc:
            _set_failure_stage(exc, "runs_write")
            raise

    def _success_health(
        self,
        run: dict[str, Any],
        *,
        latency_ms: float,
        acceptance: dict[str, Any],
    ) -> dict[str, Any]:
        health = self.read_health()
        traffic_type = normalize_traffic_type(run.get("traffic_type"))
        now = _utc_now()
        health.update(
            {
                "status": "ok",
                "updated_at": now,
                "last_success_trace_at": now,
                "last_success_run_id": run.get("run_id") or "",
                "consecutive_failure_count": 0,
                "last_trace_write_latency_ms": latency_ms,
                "deployment_acceptance": acceptance,
            }
        )
        if traffic_type == TRAFFIC_PRODUCTION:
            health["last_real_run_at"] = now
        elif traffic_type == TRAFFIC_SMOKE:
            health["last_smoke_run_at"] = now
        else:
            health["last_deployment_audit_at"] = now
        self._atomic_write_json(self.health_path, health)
        return health

    def _evaluate_deployment_acceptance(
        self,
        run: dict[str, Any],
        artifacts: dict[str, str],
    ) -> dict[str, Any]:
        marker = self._read_json(self.deployment_path, {})
        if not marker or marker.get("status") != "awaiting":
            return marker
        if normalize_traffic_type(run.get("traffic_type")) != TRAFFIC_PRODUCTION:
            return marker
        missing = deployment_acceptance_missing_fields(run, artifacts)
        marker.update(
            {
                "status": "failed" if missing else "passed",
                "checked_at": _utc_now(),
                "checked_run_id": run.get("run_id"),
                "accepted_run_id": None if missing else run.get("run_id"),
                "missing_fields": missing,
                "recommendations": [_acceptance_recommendation(item) for item in missing],
            }
        )
        self._atomic_write_json(self.deployment_path, marker)
        return marker

    def _update_latest_by_route(
        self,
        run: dict[str, Any],
        artifacts: dict[str, str],
    ) -> None:
        index = self.latest_by_route()
        key = "|".join(
            [
                str(run.get("app") or ""),
                str(run.get("channel") or ""),
                str(run.get("route") or ""),
                normalize_traffic_type(run.get("traffic_type")),
            ]
        )
        index[key] = {
            "run_id": run.get("run_id"),
            "app": run.get("app"),
            "channel": run.get("channel"),
            "route": run.get("route"),
            "traffic_type": run.get("traffic_type"),
            "ended_at": run.get("ended_at"),
            "artifacts": artifacts,
        }
        self._atomic_write_json(self.latest_by_route_path, index)

    def _atomic_write_text(self, path: Path, text: str) -> None:
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(text, encoding="utf-8")
            os.replace(temporary, path)
        except OSError as exc:
            _set_failure_stage(exc, f"artifact_write:{path.name}")
            raise
        finally:
            if temporary.exists():
                temporary.unlink()

    def _atomic_write_json(self, path: Path, value: dict[str, Any]) -> None:
        self._atomic_write_text(
            path,
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )

    @staticmethod
    def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return dict(default)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return dict(default)
        return value if isinstance(value, dict) else dict(default)

    def _render_panel(
        self,
        latest: dict[str, Any],
        *,
        update_info: dict[str, Any] | None = None,
        health: dict[str, Any] | None = None,
        acceptance: dict[str, Any] | None = None,
    ) -> str:
        runs = [
            run
            for run in self.load_runs(limit=100)
            if normalize_traffic_type(run.get("traffic_type")) == normalize_traffic_type(latest.get("traffic_type"))
        ][-20:]
        health = health or self.read_health()
        acceptance = acceptance or health.get("deployment_acceptance") or {}
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
        traffic_label = _traffic_label(normalize_traffic_type(latest.get("traffic_type")))
        health_status = str(health.get("status") or "unknown")
        acceptance_status = str(acceptance.get("status") or "not_marked")
        acceptance_details = ", ".join(str(item) for item in acceptance.get("missing_fields") or [])
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
        <span class="badge">{_esc(traffic_label)}</span>
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

    <div class="grid two">
      <section class="section">
        <h2>Production Health</h2>
        <div class="grid metrics">
          {_metric("Status", health_status)}
          {_metric("Last Real Trace", health.get("last_real_run_at") or "Never")}
          {_metric("Failures", health.get("failure_count", 0))}
          {_metric("Consecutive", health.get("consecutive_failure_count", 0))}
          {_metric("Write Latency", f"{health.get('last_trace_write_latency_ms', 0)}ms")}
        </div>
      </section>
      <section class="section">
        <h2>Deployment Acceptance</h2>
        <p><span class="badge">{_esc(acceptance_status.title())}</span></p>
        <p class="muted" style="margin-top:8px;">{_esc(acceptance_details or "No missing fields recorded.")}</p>
      </section>
    </div>

    <section class="section">
      <h2>Environment</h2>
      <p class="muted">Run <code>tokensaver health --json</code> for version, commit, Python, PATH, dependency pin, trace, and acceptance details.</p>
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

    def _render_empty_panel(self, health: dict[str, Any]) -> str:
        acceptance = health.get("deployment_acceptance") or {}
        return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TokenSaver Production Health</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f8fb;color:#18212f;margin:0}}main{{max-width:820px;margin:60px auto;padding:28px;background:#fff;border:1px solid #d8dee8;border-radius:8px}}.muted{{color:#657084}}</style></head>
<body><main>
<h1>TokenSaver Production Health</h1>
<h2>No production traffic yet</h2>
<p class="muted">Smoke and deployment audit runs are stored separately and never shown as production ROI.</p>
<p>Health status: <strong>{_esc(str(health.get("status") or "unknown"))}</strong></p>
<p>Deployment acceptance: <strong>{_esc(str(acceptance.get("status") or "not_marked"))}</strong></p>
</main></body></html>
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


def deployment_acceptance_missing_fields(
    run: dict[str, Any],
    artifacts: dict[str, str] | None = None,
) -> list[str]:
    missing: list[str] = []
    metadata = run.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    for field in ("host_version", "tokensaver_version", "environment"):
        if field not in metadata or metadata.get(field) in (None, ""):
            missing.append(f"metadata.{field}")
    if "quality_signals" not in run or not isinstance(run.get("quality_signals"), dict):
        missing.append("quality_signals")
    elif not run.get("quality_signals"):
        missing.append("quality_signals.non_empty")
    for field in ("tool_calls", "model_calls"):
        if field not in run or not isinstance(run.get(field), list):
            missing.append(field)
    if "answer" not in run or not str(run.get("answer") or "").strip():
        missing.append("final_answer")
    required_artifacts = ("runs_path", "report_path", "brief_path", "panel_path")
    for field in required_artifacts:
        value = artifacts.get(field) if artifacts else None
        if not value or not Path(value).is_file():
            missing.append(f"artifact.{field}")
    return missing


def _acceptance_recommendation(field: str) -> str:
    if field.startswith("metadata."):
        return f"Record {field} on the first production run after deployment."
    if field.startswith("artifact."):
        return f"Ensure TokenSaver can persist {field.removeprefix('artifact.')}."
    if field.startswith("quality_signals"):
        return "Record explicit quality signals for the production response."
    if field == "final_answer":
        return "Call record_final_answer() or provide a non-empty answer field."
    return f"Record a valid {field} field in the production trace."


def _default_health() -> dict[str, Any]:
    return {
        "status": "unknown",
        "updated_at": "",
        "last_success_trace_at": "",
        "last_success_run_id": "",
        "last_failure_at": "",
        "last_error": None,
        "failure_count": 0,
        "consecutive_failure_count": 0,
        "last_trace_write_latency_ms": 0,
        "last_real_run_at": "",
        "last_smoke_run_at": "",
        "last_deployment_audit_at": "",
        "deployment_acceptance": {},
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _traffic_suffix(traffic_type: str) -> str:
    return {
        TRAFFIC_PRODUCTION: "real",
        TRAFFIC_SMOKE: "smoke",
        TRAFFIC_DEPLOYMENT: "deployment",
    }[traffic_type]


def _traffic_label(traffic_type: str) -> str:
    return {
        TRAFFIC_PRODUCTION: "Real",
        TRAFFIC_SMOKE: "Smoke",
        TRAFFIC_DEPLOYMENT: "Deployment Audit",
    }[traffic_type]


def _failure_stage(exc: Exception) -> str:
    stage = getattr(exc, "tokensaver_stage", None)
    if stage:
        return str(stage)
    notes = getattr(exc, "__notes__", [])
    for note in notes:
        if str(note).startswith("tokensaver_stage="):
            return str(note).split("=", 1)[1]
    return "store_write"


def _set_failure_stage(exc: Exception, stage: str) -> None:
    try:
        setattr(exc, "tokensaver_stage", stage)
    except (AttributeError, TypeError):
        pass


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * percentile), len(ordered) - 1)
    return ordered[index]


def _trend_group(key: tuple[str, ...], runs: list[dict[str, Any]]) -> dict[str, Any]:
    input_tokens = [int(run.get("input_tokens") or 0) for run in runs]
    output_tokens = [int(run.get("output_tokens") or 0) for run in runs]
    latency = [int(run.get("latency_ms") or 0) for run in runs]
    over_budget = 0
    complete_quality = 0
    finding_counts: dict[str, int] = {}
    for run in runs:
        diagnosis = run.get("diagnosis") or {}
        budget = diagnosis.get("budget") or {}
        if (
            int(run.get("input_tokens") or 0) > int(budget.get("input_tokens") or 10**18)
            or int(run.get("output_tokens") or 0) > int(budget.get("output_tokens") or 10**18)
            or int(run.get("latency_ms") or 0) > int(budget.get("latency_ms") or 10**18)
        ):
            over_budget += 1
        if isinstance(run.get("quality_signals"), dict) and run.get("quality_signals"):
            complete_quality += 1
        for code in diagnosis.get("finding_codes") or []:
            finding_counts[str(code)] = finding_counts.get(str(code), 0) + 1
    count = len(runs)
    return {
        "app": key[0],
        "host_version": key[1],
        "tokensaver_version": key[2],
        "task_type": key[3],
        "route": key[4],
        "channel": key[5],
        "traffic_type": key[6],
        "runs": count,
        "input_tokens": {"p50": _percentile(input_tokens, 0.50), "p95": _percentile(input_tokens, 0.95)},
        "output_tokens": {"p50": _percentile(output_tokens, 0.50), "p95": _percentile(output_tokens, 0.95)},
        "latency_ms": {"p50": _percentile(latency, 0.50), "p95": _percentile(latency, 0.95)},
        "budget_exceeded_rate": round(over_budget / count, 3),
        "quality_fields_retention_rate": round(complete_quality / count, 3),
        "finding_codes": finding_counts,
    }


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
