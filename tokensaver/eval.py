"""Fixture evaluation for TokenSaver profiles and recorded runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .diagnosis import diagnose_run
from .profile import load_profile


def evaluate_fixtures(
    fixtures_path: str | Path,
    *,
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    profile = load_profile(profile_path)
    fixtures = json.loads(Path(fixtures_path).read_text(encoding="utf-8"))
    if not isinstance(fixtures, list):
        raise ValueError("Expected fixtures JSON to be an array.")

    cases = [_evaluate_case(item, profile=profile) for item in fixtures]
    failed = [case for case in cases if case["result"] != "accepted"]
    return {
        "result": "accepted" if not failed else "rejected",
        "total": len(cases),
        "accepted": len(cases) - len(failed),
        "rejected": len(failed),
        "cases": cases,
    }


def _evaluate_case(fixture: Any, *, profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(fixture, dict):
        raise ValueError("Each fixture must be an object.")
    run = dict(fixture.get("run") or {})
    run.setdefault("user_message", fixture.get("input") or "")
    run.setdefault("task_type", fixture.get("task_type") or "unknown")
    if fixture.get("expected_required_fields") and not run.get("quality_requirements"):
        run["quality_requirements"] = list(fixture.get("expected_required_fields") or [])

    diagnosis = diagnose_run(run, profile=profile)
    codes = set(diagnosis.get("finding_codes") or [])
    failures: list[str] = []

    max_output_tokens = fixture.get("max_output_tokens")
    if max_output_tokens is not None:
        actual_output = int(run.get("output_tokens") or run.get("answer_tokens") or 0)
        if actual_output > int(max_output_tokens):
            failures.append("output_tokens_over_fixture_limit")

    if "required_field_missing" in codes:
        failures.append("required_field_missing")
    if "quality_regression_risk" in codes:
        failures.append("quality_regression_risk")

    return {
        "id": fixture.get("id") or run.get("run_id") or "unnamed",
        "task_type": run.get("task_type"),
        "result": "accepted" if not failures else "rejected",
        "failures": failures,
        "roi_score": diagnosis.get("roi_score", 100),
        "finding_codes": diagnosis.get("finding_codes", []),
    }
