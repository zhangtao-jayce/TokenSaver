# Version Management

Current version: `0.8.0`

Release date: 2026-06-23

## Versioning Rule

TokenSaver uses semantic versioning:

```text
MAJOR.MINOR.PATCH
```

- `MAJOR`: incompatible public API or storage format changes.
- `MINOR`: new compatible features, tools, diagnosis rules, integrations, or output artifacts.
- `PATCH`: bug fixes, documentation corrections, test updates, and small compatibility improvements.

## Release Record Template

Each release should record:

- version
- release date
- release goal
- iteration summary
- added
- changed
- fixed
- removed
- verification
- compatibility notes
- known limitations

## Current Release

### 0.8.0

Release date: 2026-06-23

Release goal:

Remove first-install ambiguity and make batch pipelines with external coding-Agent handoffs observable without misreporting them as model calls.

Iteration summary:

TokenSaver 0.8.0 standardizes the PyPI/Python/CLI onboarding path, adds actionable PATH and custom task-budget diagnostics, introduces first-class external Agent handoff traces, and provides an offline research pipeline plus explicit-Python runner template.

Compatibility notes:

- `handoffs` is an optional additive schema 0.4 field; existing traces remain readable.
- `AgentRun.add_handoff` and `task_type_missing_budget` are additive public behavior.
- Handoffs do not contribute to model-call or token accounting.
- No new runtime dependency is required.

Verification:

```text
Onboarding/pipeline tests: 6 passed
Governance tests: 3 passed
Full suite: 107 passed
Python compilation, offline pipeline smoke, and diff check: passed
```

### 0.7.0

Release date: 2026-06-22

Release goal:

Build a trustworthy Agent optimization loop on explicit token semantics, traffic-aware trace health, and conservative host-version group comparison.

Iteration summary:

TokenSaver 0.7.0 introduces schema 0.4 token breakdowns, provider usage ingestion, first-class tool semantic outcomes, tool-surface cost findings, host request/trace lifecycle health, and baseline/candidate comparisons grouped by task and route.

Compatibility notes:

- Existing schema 0.3 traces remain readable.
- Existing SDK calls and two-run compare commands remain compatible.
- Schema 0.4 top-level model token totals intentionally exclude tool payloads and duplicate final answers.
- No new runtime dependency is required.

Verification:

```text
0.7 tests: 12 passed
Governance tests: 3 passed
Full suite: 101 passed
Python compile, CLI/API smoke, diff check, and version consistency: passed
```

### 0.6.2

Release date: 2026-06-12

Release goal:

Keep production health commit detection correct when legacy `tokensaver` and current `tokensaver-agent` distribution metadata coexist.

Iteration summary:

TokenSaver `0.6.2` makes PEP 610 commit detection prefer the current `tokensaver-agent` distribution while retaining compatibility with legacy installs.

Verification:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
```

Compatibility notes:

- No public API or trace schema changes.
- Legacy `tokensaver` distribution metadata remains a fallback.

### 0.6.1

Release date: 2026-06-12

Release goal:

Make TokenSaver a local production integration health and ROI diagnostic that separates real and test traffic, proves trace health, and validates the first real request after deployment.

Iteration summary:

TokenSaver `0.6.1` adds production/smoke/deployment traffic isolation, atomic cross-run health state, trace completeness findings, deployment acceptance, visible integration failure hooks, unified doctor/runtime health, production-health GUI modules, and version/traffic-isolated trend aggregation.

Verification:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli health --json
```

Expected result:

```text
Ran 85 tests
OK
```

Compatibility notes:

- New traces use schema `0.3`.
- Legacy traces without `traffic_type` are treated as production, never smoke.
- Existing `runs.jsonl` remains readable and append-only.
- Generic latest artifacts are production-only after the first v0.6 write.

### 0.6.0

Release date: 2026-06-11

Release goal:

Make TokenSaver understandable and testable within 30 seconds, while establishing measurable open-source growth loops.

Iteration summary:

TokenSaver `0.6.0` introduced the deterministic demo, benchmark artifacts, anonymous share cards, case studies, packaging metadata, CI, release automation, and repository growth metrics.

Compatibility notes:

- Existing traces remain readable.
- The demo uses deterministic synthetic fixtures.
- Core diagnosis remains local and dependency-free.

### 0.5.1

Release date: 2026-06-05

Release goal:

Make TokenSaver's local GUI immediately communicate run ROI, waste, risk, and next repair actions.

Iteration summary:

TokenSaver `0.5.1` upgrades `.tokensaver/panel/index.html` from a basic activity panel into an offline local ROI health report. The panel now emphasizes the latest run status, cost overview, risk state, Top Waste, findings with evidence, a repair brief copy CTA, and recent run trends.

Verification:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli record-run --file examples/run.json --store-dir /private/tmp/tokensaver-gui
python3 -m tokensaver.cli latest --store-dir /private/tmp/tokensaver-gui --kind panel
```

Expected result:

```text
Ran 36 tests
OK
```

Compatibility notes:

- Existing traces remain readable.
- The GUI remains a static local HTML file.
- No network, login, database, or chart dependency is required.

### 0.5.0

Release date: 2026-06-05

Release goal:

Make TokenSaver easier to integrate into real Agent applications in under 10 minutes.

Iteration summary:

TokenSaver `0.5.0` adds dependency-free integration helpers for OpenAI, Anthropic, LiteLLM, and LangChain/LangGraph-style callbacks. It also documents the standard Agent run fields and the TypeScript/Vercel AI SDK JSON import path.

Verification:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli init-profile --template coding-agent --output /private/tmp/tokensaver-profile.yaml --force
python3 -m tokensaver.cli record-run --file examples/run.json --store-dir /private/tmp/tokensaver-v05
python3 -m tokensaver.cli latest --store-dir /private/tmp/tokensaver-v05 --kind summary
python3 -m tokensaver.cli latest --store-dir /private/tmp/tokensaver-v05 --kind brief
python3 -m tokensaver.cli latest --store-dir /private/tmp/tokensaver-v05 --kind panel
```

Expected result:

```text
Ran 35 tests
OK
```

Compatibility notes:

- Existing traces remain readable.
- Core package remains dependency-free.
- New integration helpers accept SDK-compatible client objects without importing those SDKs.

Known limitations:

- Vercel AI SDK support is via documented JSON import shape, not a native npm package.
- LangChain/LangGraph support is a lightweight callback adapter, not a full framework integration package.

### 0.4.0

Release date: 2026-06-03

Release goal:

Productize TokenSaver installation, upgrade, and verification for real Agent application environments.

Iteration summary:

TokenSaver `0.4.0` adds environment-aware installation diagnostics, verbose version metadata, dependency pin scanning, install verification, upgrade command generation, a safe self-update entrypoint, and MCP tools for Agent-accessible install diagnostics.

Verification:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli version --verbose
python3 -m tokensaver.cli doctor --offline
python3 -m tokensaver.cli verify-install --version 0.4.0
python3 -m tokensaver.cli upgrade-command --commit COMMIT
```

Expected result:

```text
Ran 21 tests
OK
```

Compatibility notes:

- Existing traces remain readable.
- New installation commands are additive.
- `self-update` only prints the command unless `--execute` is explicitly passed.
- `doctor --fix-requirements` only edits dependency pins when explicitly requested.

Known limitations:

- Local commit detection is best-effort and depends on Git checkout or PEP 610 install metadata.
- `self-update --execute` still depends on the current Python environment permissions.

### 0.3.0

Release date: 2026-06-03

Release goal:

Make it easy for seed users to discover and apply TokenSaver updates from inside already-integrated Agent applications.

Iteration summary:

TokenSaver `0.3.0` adds local version reporting, GitHub update checks, generated upgrade commands, and update notices in generated reports, repair briefs, and the local panel.

Verification:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
python3 -m tokensaver.cli version
python3 -m tokensaver.cli check-update --json --timeout 0.1
```

Expected result:

```text
Ran 15 tests
OK
```

Compatibility notes:

- Existing traces remain readable.
- Network failures during update checks do not block Agent tracing.
- Automatic artifact update checks can be disabled with `TOKENSAVER_CHECK_UPDATE_ON_RUN=0`.

Known limitations:

- Update checks use public GitHub metadata from `main`.
- Projects that pin a specific commit still need an explicit upgrade command to move forward.

### 0.2.0

Release date: 2026-06-03

Release goal:

Turn TokenSaver from a token statistics tool into a stronger Agent workflow ROI diagnosis and repair-brief system.

Iteration summary:

TokenSaver `0.2.0` adds channel-aware budgets, tool output governance, quality guardrails, before/after comparison, richer reports, and expanded CLI inspection commands. This release is informed by real seed-user feedback from Goldfinger Agent usage.

Verification:

```bash
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
```

Expected result:

```text
Ran 11 tests
OK
```

Compatibility notes:

- Existing `0.1.0` traces remain readable.
- New traces include `schema_version: "0.2"`.
- Existing `record_answer()` integrations continue to work.
- New optional APIs include `set_budget()`, `set_quality_requirements()`, and `record_final_answer()`.

Known limitations:

- Diagnosis is still deterministic and rule-based.
- Token estimation is approximate.
- Quality field verification depends on the host Agent recording explicit quality signals or final answers.

### 0.1.0

Release date: 2026-06-02

Release goal:

Provide the first runnable local runtime ROI diagnosis core for AI Agent applications.

Iteration summary:

TokenSaver `0.1.0` establishes the local diagnosis loop:

```text
Trace -> Diagnose -> Summarize -> Generate Repair Brief
```

It lets users or coding agents integrate TokenSaver into an Agent app, record one run, diagnose low-ROI patterns with local rules, and read local outputs under `.tokensaver/`.

Verification:

```bash
python3 -m unittest discover -s tests
```

Expected result:

```text
Ran 8 tests
OK
```

Known limitations:

- Diagnosis is rule-based and local.
- Token estimation is approximate.
- There is no hosted dashboard.
- There is no LLM gateway.
- There is no automatic cloud upload.
- There is no automatic LLM-based quality evaluation.
