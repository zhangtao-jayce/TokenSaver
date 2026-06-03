# Version Management

Current version: `0.4.0`

Release date: 2026-06-03

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
