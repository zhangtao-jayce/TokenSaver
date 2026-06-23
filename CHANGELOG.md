# Changelog

All notable changes to TokenSaver are recorded here.

## 0.8.0 - 2026-06-23

### Added

- First-class external Agent handoff tracing for batch and research pipelines.
- `task_type_missing_budget` diagnosis with a reviewable profile budget patch.
- Offline research pipeline example and explicit-Python runner template.

### Changed

- Installation guidance now consistently prefers PyPI, checks Python 3.10+
  before install, and reserves GitHub installation for development versions.
- Doctor PATH findings include a copyable, shell-quoted export command.
- Reports, repair briefs, and the local panel expose handoff activity without
  counting it as model usage.

## 0.7.0 - 2026-06-22

### Added

- Schema 0.4 `token_usage` breakdown for billed model, tool payload, final answer, reasoning, repeated context, and tool schema tokens.
- Provider usage normalization for OpenAI-, Anthropic-, and LiteLLM-compatible responses.
- First-class tool transport/semantic outcome fields.
- `oversized_tool_surface` and `unused_tool_schema_cost` findings.
- Host request and trace lifecycle health with `idle_no_traffic` and `trace_pipeline_broken` diagnoses.
- Baseline/candidate host-version comparison grouped by task, route, channel, or app.
- Conservative insufficient-sample reporting and cross-schema compatibility warnings.

### Changed

- New SDK traces use schema 0.4.
- New SDK `input_tokens` and `output_tokens` represent model totals and no longer add tool payloads or a duplicate final answer.
- Run summaries expose the token breakdown.

### Compatibility

- Schema 0.3 traces and existing two-run comparisons remain supported.
- No new runtime dependency was added.

### Verification

- 12 TokenSaver 0.7 tests passed.
- 3 governance tests passed.
- 101 full-suite tests passed.
- Python compilation, CLI/API smoke, diff check, and version consistency passed.

## 0.6.2 - 2026-06-12

### Fixed

- Prefer the current `tokensaver-agent` PEP 610 installation metadata when a legacy
  `tokensaver` distribution remains installed, preventing false project pin mismatch
  findings in production health checks.

### Verification

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
```

## 0.6.1 - 2026-06-12

### Release Goal

Add local production integration health to the v0.6 release line.

### Added

- Production, smoke-test, and deployment-audit traffic types.
- Production-only generic latest artifacts plus per-traffic reports, briefs, and panels.
- Atomic `.tokensaver/health.json`, deployment marker, and latest-by-route index.
- Deployment acceptance for the first real request after a release.
- Trace completeness findings and caller/inferred task classification conflicts.
- Logging and failure callback interfaces with health failure persistence.
- Unified `tokensaver health`, doctor runtime state, and production-health GUI cards.
- MCP tools for health, traffic latest, and deployment markers.
- Cross-run version/traffic trend aggregation and long-term tool governance.
- 45 Goldfinger-like v0.6 production health tests.

### Changed

- New traces use schema `0.3`; legacy traces without traffic type remain production-compatible.
- Smoke and deployment audit runs no longer replace production ROI.

### Verification

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli demo --store-dir /private/tmp/tokensaver-demo
python3 -m tokensaver.cli health --store-dir /private/tmp/tokensaver-v06 --json
python3 -m pip wheel . --no-deps -w /private/tmp/tokensaver-wheel
```

Test result:

```text
Ran 85 tests
OK
```

## 0.6.0 - 2026-06-11

### Release Goal

Make TokenSaver understandable and testable within 30 seconds, while establishing measurable open-source growth loops.

### Added

- `tokensaver demo` deterministic offline before/after product demo.
- Demo benchmark artifacts in Markdown and JSON.
- `tokensaver benchmark` for arbitrary before/after run files.
- `tokensaver open` for opening an existing panel or generating the offline demo.
- Anonymous SVG benchmark share cards.
- Three deterministic Agent ROI case studies.
- Pull request benchmark comments.
- GitHub Actions CI across Python 3.10-3.13.
- Tagged-release distribution build workflow.
- Weekly repository traffic and growth metric snapshots.
- Bug, integration, case-study, and pull request templates.
- Python package build metadata and explicit package discovery.

### Changed

- Reworked the README around immediate value, proof, privacy, and integration.
- Added project URLs, package classifiers, and SPDX license metadata.
- Documented demo fixture limitations next to benchmark results.

### Verification

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli demo --store-dir /private/tmp/tokensaver-demo
python3 -m pip wheel . --no-deps -w /private/tmp/tokensaver-wheel
```

## 0.5.1 - 2026-06-05

### Release Goal

Make the local GUI useful to ordinary users before they read JSONL or Markdown artifacts.

### Iteration Summary

This release follows the GUI-priority iteration guide. The generated `.tokensaver/panel/index.html` is now a static local ROI health report focused on whether the latest run was wasteful, where the waste came from, how severe it is, and what to repair next.

### Added

- Local ROI report layout for `.tokensaver/panel/index.html`.
- Risk state labels:
  - `Healthy`
  - `Optimizable`
  - `High Cost`
  - `Quality Risk`
- Cost overview cards:
  - input tokens
  - output tokens
  - latency
  - model calls
  - tool calls
- Top Waste section:
  - largest context item
  - largest tool output
  - largest model input
  - longest answer
  - slowest tool
- Finding cards with severity, code, evidence, recommendation, and impact.
- Repair brief preview with `Copy Full Brief` button.
- Recent runs table with simple local trend summary.
- Panel GUI test coverage.

### Changed

- The panel now reads like a local health report instead of a plain activity table.
- README and integration guide now document the offline GUI modules.

### Verification

Commands:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli record-run --file examples/run.json --store-dir /private/tmp/tokensaver-gui
python3 -m tokensaver.cli latest --store-dir /private/tmp/tokensaver-gui --kind panel
```

Test result:

```text
Ran 36 tests
OK
```

### Compatibility Notes

- Python `>=3.10`.
- No runtime third-party Python dependency is required.
- Existing traces remain readable.
- The GUI remains a local static HTML artifact and does not upload trace data.

## 0.5.0 - 2026-06-05

### Release Goal

Make real Agent application integration faster and more explicit.

### Iteration Summary

This release implements the v0.5 integration experience from the iteration guide. TokenSaver now ships dependency-free helpers for common SDK and framework shapes while keeping local-first tracing and JSONL artifacts unchanged.

### Added

- Standard Agent run field contract:
  - `app`
  - `channel`
  - `user_message`
  - `task_type`
  - `route`
  - `context_items`
  - `tool_calls`
  - `model_calls`
  - `answer`
  - `quality_signals`
- OpenAI helpers:
  - `trace_openai_chat_completion`
  - `trace_openai_response`
- Anthropic helper:
  - `trace_anthropic_message`
- LiteLLM helper:
  - `trace_litellm_completion`
- LangChain/LangGraph-style callback adapter:
  - `LangChainTokenSaverCallback`
- Vercel AI SDK / TypeScript JSON import documentation.
- Integration helper tests with fake SDK clients.

### Changed

- README minimal API now uses the OpenAI chat helper as the primary integration example.
- Integration guide now includes concrete OpenAI, Anthropic, LiteLLM, LangChain/LangGraph, and TypeScript JSON import examples.

### Verification

Commands:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli init-profile --template coding-agent --output /private/tmp/tokensaver-profile.yaml --force
python3 -m tokensaver.cli record-run --file examples/run.json --store-dir /private/tmp/tokensaver-v05
python3 -m tokensaver.cli latest --store-dir /private/tmp/tokensaver-v05 --kind summary
python3 -m tokensaver.cli latest --store-dir /private/tmp/tokensaver-v05 --kind brief
python3 -m tokensaver.cli latest --store-dir /private/tmp/tokensaver-v05 --kind panel
```

Test result:

```text
Ran 35 tests
OK
```

### Compatibility Notes

- Python `>=3.10`.
- No runtime third-party Python dependency is required by the core package.
- Existing traces remain readable.
- New SDK helpers return the original provider response object.

## 0.4.0 - 2026-06-03

### Release Goal

Productize TokenSaver installation, upgrade, and verification for seed users running real Agent applications.

### Iteration Summary

This release turns install and upgrade troubleshooting into first-class TokenSaver diagnostics. TokenSaver now explains which Python environment is active, where the package is installed, whether CLI scripts are on PATH, whether Homebrew/PEP 668 may affect installation, whether project dependency files pin an older commit, and which upgrade command fits the current environment.

### Added

- Verbose version inspection:
  - `tokensaver version --verbose`
  - `python3 -m tokensaver.cli version --verbose --json`
- Structured install doctor:
  - `tokensaver doctor`
  - `tokensaver doctor --offline`
  - `tokensaver doctor --fix-requirements`
- Install verification:
  - `tokensaver verify-install --version VERSION`
  - `tokensaver verify-install --commit COMMIT`
  - `tokensaver verify-install --check-project-files`
- Environment-aware upgrade command generation:
  - `tokensaver upgrade-command --commit COMMIT`
- Safe self-update entrypoint:
  - `tokensaver self-update --commit COMMIT`
  - `tokensaver self-update --commit COMMIT --execute`
- Project dependency pin scanning for:
  - `requirements.txt`
  - `pyproject.toml`
  - `poetry.lock`
  - `uv.lock`
  - `Pipfile.lock`
- Explicit dependency pin fixer for GitHub TokenSaver URLs in:
  - `requirements.txt`
  - `pyproject.toml`
- Local commit detection from Git checkout or PEP 610 `direct_url.json`.
- MCP tools:
  - `tokensaver.get_version`
  - `tokensaver.check_update`
  - `tokensaver.doctor`
  - `tokensaver.verify_install`
  - `tokensaver.upgrade_command`

### Changed

- Install and upgrade docs now prefer `python3 -m pip` and project virtual environments over bare `pip`.
- `check-update` now reports `cannot_check_remote`, `reason`, `local_commit`, and `local_installation_ok`.
- Upgrade commands now use the active Python interpreter.
- Integration guide now documents install diagnostics and MCP install tools.

### Fixed

- Network failures during update checks are classified instead of shown only as raw Python exceptions.
- PATH and externally managed Python conditions are diagnosed with actionable next steps.

### Verification

Commands:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli version --verbose --json
python3 -m tokensaver.cli doctor --offline --json
python3 -m tokensaver.cli verify-install --version 0.4.0 --json
python3 -m tokensaver.cli upgrade-command --commit abc1234
```

Test result:

```text
Ran 21 tests
OK
```

### Compatibility Notes

- Python `>=3.10`.
- No runtime third-party Python dependency is required by the core package.
- Existing traces remain readable.
- `self-update` does not modify the environment unless `--execute` is passed.

## 0.3.0 - 2026-06-03

### Release Goal

Help seed users discover and apply TokenSaver updates from inside already-integrated Agent applications.

### Iteration Summary

This release adds update awareness to TokenSaver. Users can check the installed version, compare it with GitHub `main`, get a copyable upgrade command, and see update notices in generated local artifacts when a newer version is available.

### Added

- Version inspection CLI:
  - `tokensaver version`
  - `python3 -m tokensaver.cli version`
- Update check CLI:
  - `tokensaver check-update`
  - `python3 -m tokensaver.cli check-update`
- Machine-readable update output:
  - `tokensaver version --json`
  - `tokensaver check-update --json`
- Public GitHub version metadata checks using `pyproject.toml` on `main`.
- Best-effort latest commit detection for pinned install commands.
- Copyable upgrade command generation.
- Update notices in generated artifacts when a newer version is available:
  - `.tokensaver/reports/latest.md`
  - `.tokensaver/briefs/latest.md`
  - `.tokensaver/panel/index.html`
- Environment switch to disable automatic artifact update checks:
  - `TOKENSAVER_CHECK_UPDATE_ON_RUN=0`

### Changed

- Generated artifacts can now include TokenSaver update metadata when available.
- Version information is defined before package runtime imports to avoid circular import issues.

### Fixed

- Update checks fail gracefully when network access is unavailable.
- Agent tracing is not blocked by update-check failures.

### Verification

Commands:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli version
python3 -m tokensaver.cli check-update --json --timeout 0.1
```

Test result:

```text
Ran 15 tests
OK
```

### Compatibility Notes

- Python `>=3.10`.
- No runtime third-party Python dependency is required by the core package.
- Existing traces remain readable.
- Data remains local; update checks fetch only public version metadata.

## 0.2.0 - 2026-06-03

### Release Goal

Upgrade TokenSaver into a more actionable Agent workflow ROI diagnosis and repair-brief system.

### Iteration Summary

This release incorporates seed-user feedback from Goldfinger Agent usage. TokenSaver now diagnoses whether Agent costs, latency, context, tool outputs, route choices, and channel-specific answers are aligned with the task. It also generates more actionable repair briefs for coding agents.

### Added

- Trace schema version field:
  - `schema_version: "0.2"`
- Runtime APIs:
  - `set_budget(input_tokens=..., output_tokens=..., latency_ms=...)`
  - `set_quality_requirements([...])`
  - `record_final_answer(...)`
- Channel/task-aware budget diagnosis.
- Latency budget diagnosis.
- ROI dimension scores:
  - `cost_efficiency`
  - `latency_efficiency`
  - `context_precision`
  - `output_density`
  - `task_fit`
  - `quality_risk`
- Top token consumer analysis across context, tools, model calls, and final answers.
- Tool output governance findings:
  - `dominant_tool_output`
  - `raw_tool_payload`
- Quality guardrail findings:
  - `missing_required_quality_field`
  - `quality_fields_not_verified`
- Before/after run comparison.
- Expanded CLI commands:
  - `list`
  - `show`
  - `report`
  - `brief`
  - `compare`
  - `top-tools`
- Local panel sections for ROI dimensions and top token consumers.
- Goldfinger-like tests for tool output governance and quality guardrails.

### Changed

- Repair briefs now include Objective, Evidence, Problems, Required Quality Fields, Requested Changes, and Verification sections.
- Run summaries now include budget, ROI dimensions, and top token consumers.
- Short-channel answer length diagnosis now uses final answer tokens when available.
- Tool output recommendations now prefer summary/detail/full modes instead of raw large payloads.

### Fixed

- Preserved backward compatibility with `record_answer()`.
- Existing `0.1.0` traces remain readable by the local store and CLI.

### Verification

Commands:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli record-run --file examples/run.json --store-dir /private/tmp/tokensaver-smoke
python3 -m tokensaver.cli list --store-dir /private/tmp/tokensaver-smoke --limit 5
python3 -m tokensaver.cli report latest --store-dir /private/tmp/tokensaver-smoke
python3 -m tokensaver.cli top-tools --store-dir /private/tmp/tokensaver-smoke --last 5
```

Test result:

```text
Ran 11 tests
OK
```

### Compatibility Notes

- Python `>=3.10`.
- No runtime third-party Python dependency is required by the core package.
- New APIs are optional and additive.
- Data is stored locally by default.

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
