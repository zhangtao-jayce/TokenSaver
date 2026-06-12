# TokenSaver Schema Compatibility

## Current Schema

TokenSaver v0.6 writes new traces with `schema_version: "0.3"`.

Additive fields:

- `traffic_type`
- `caller_task_type`
- `inferred_task_type`
- tool call `status`
- deployment metadata under `metadata`

## Traffic Compatibility

Valid traffic values:

- `production_user_run`
- `smoke_test`
- `deployment_audit`

Legacy traces without `traffic_type` are read as `production_user_run`. They are never inferred as smoke traffic.

## Storage Compatibility

- `runs.jsonl` remains append-only JSONL.
- Existing traces remain readable.
- `health.json`, `deployment.json`, and `index/latest_by_route.json` are additive and can be deleted and rebuilt through later runs.
- Generic `reports/latest.md`, `briefs/latest.md`, and `panel/index.html` are production-only after the first v0.6 write.
- Smoke and deployment-audit artifacts use separate names and never replace production latest artifacts.

## Completeness Semantics

Diagnosis distinguishes:

- field absent
- field present but empty
- valid zero, `false`, or empty collection where the field contract allows it

For deployment acceptance, `quality_signals` must be a non-empty object and the final answer must be non-empty.
