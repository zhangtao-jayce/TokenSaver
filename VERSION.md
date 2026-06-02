# Version Management

Current version: `0.1.0`

Release date: 2026-06-02

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
