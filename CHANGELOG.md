# Changelog

All notable changes to TokenSaver are recorded here.

## 0.1.0 - 2026-06-02

### Release Goal

Ship the first runnable open-source core for local Agent runtime ROI diagnosis.

### Iteration Summary

This release provides a local-first runtime tracing and diagnosis loop for AI Agent applications:

```text
Trace -> Diagnose -> Summarize -> Generate Repair Brief
```

Users can ask Codex / Claude Code to integrate TokenSaver into an Agent app. TokenSaver records Agent runs locally, diagnoses low-ROI patterns with deterministic rules, and writes local summaries and repair briefs.

### Added

- Agent Runtime Trace SDK:
  - `TokenSaver(app=..., channel=...)`
  - `tokensaver.run(...)`
  - context recording
  - tool call recording
  - model call recording
  - final answer recording
  - quality signal recording
- Local JSONL trace store:
  - `.tokensaver/runs.jsonl`
- Local report artifacts:
  - `.tokensaver/reports/latest.md`
  - `.tokensaver/briefs/latest.md`
  - `.tokensaver/panel/index.html`
- Rule-based ROI diagnosis:
  - wrong route for short task
  - input/output budget exceeded
  - large context item
  - history/log waste for quick tasks
  - repeated tool call without cache
  - large tool output
  - strong model used for quick task
  - sensitive realtime/action task missing obvious source attribution
  - user correction signal
- Repair brief generation for Codex / Claude Code.
- Local token estimation.
- Editable model pricing metadata.
- CLI tools:
  - `estimate`
  - `plan`
  - `record-run`
  - `latest`
  - `diagnose-run`
  - `repair-brief`
- Dependency-free MCP stdio server.
- MCP tools:
  - `tokensaver.plan_task`
  - `tokensaver.estimate_tokens`
  - `tokensaver.record_agent_run`
  - `tokensaver.get_latest_runs`
  - `tokensaver.diagnose_roi`
  - `tokensaver.generate_repair_brief`
- Generic LLM call tracing helper:
  - `trace_llm_call`
- Framework-agnostic callback adapter:
  - `TokenSaverCallback`
- Goldfinger-like example:
  - `examples/goldfinger_agent.py`
  - `examples/run.json`
- Public documentation:
  - `README.md`
  - `docs/集成指南.md`
  - `OPEN_SOURCE_SCOPE.md`
  - `SECURITY.md`
  - `CONTRIBUTING.md`
  - `VERSION.md`

### Changed

- Public README was simplified to match the actual implemented service.
- Public docs now emphasize coding-agent-first installation and integration.
- Private planning documents are excluded from the public repository.

### Fixed

- Ensured generated `.tokensaver/` artifacts are ignored by Git.
- Ensured private planning docs are ignored by Git.
- Verified direct example execution with `python3 examples/goldfinger_agent.py`.

### Removed

- Removed public claims about features not implemented in the current repository, including hosted dashboards, gateways, enterprise controls, and roadmap-style commercial features.

### Verification

Commands:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py examples/goldfinger_agent.py
python3 -m tokensaver.cli record-run --file examples/run.json
python3 -m tokensaver.cli latest --kind summary
python3 -m tokensaver.cli latest --kind brief
python3 examples/goldfinger_agent.py
```

Test result:

```text
Ran 8 tests
OK
```

### Compatibility Notes

- Python `>=3.10`.
- No runtime third-party Python dependency is required by the core package.
- Data is stored locally by default.

### Known Limitations

- Token estimation is approximate.
- Diagnosis is deterministic and rule-based.
- No hosted dashboard is included.
- No full model gateway is included.
- No automatic LLM-based quality evaluation is included.
