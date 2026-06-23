# TokenSaver Schema Compatibility

## Current Schema

TokenSaver v0.7 writes new SDK traces with `schema_version: "0.4"`.

Additive fields:

- `request_id`
- `token_usage`
- model call `reasoning_tokens`, `tool_schema_tokens`, and `usage_source`
- tool call `transport_success`, `semantic_success`, `result_quality`, `error_type`, and `fallback_used`
- optional top-level `handoffs` for external Agent handoff records

`token_usage` separates:

- billed model input and output
- tool payload and tool schema tokens
- final-answer tokens
- provider-reported reasoning tokens
- estimated repeated-context tokens

For schema 0.4 SDK traces, top-level `input_tokens` and `output_tokens` mean model input and model output totals. They do not add tool payloads or a duplicate final answer. Schema 0.3 traces retain their recorded historical values.

Externally supplied traces without `schema_version` continue to default to schema 0.3 so TokenSaver does not silently reinterpret historical aggregation semantics.

`handoffs` is additive and defaults to an empty list. A handoff records an
external Agent, artifact identifiers, expected output, status, and optional
metadata. It is not a `model_call` and does not change token accounting.

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

## Health Compatibility

Schema 0.7 runtime health adds host-request and trace start/finish timestamps plus an untraced-request count. Old health documents without traffic-aware fields retain legacy `trace_stale` behavior. New health documents distinguish `idle_no_traffic` from `trace_pipeline_broken`.

## Cross-Schema Comparison

Version-group comparison reports the schema distribution for each version. When schema 0.3 and 0.4 are mixed, output includes a compatibility warning because the historical top-level token aggregation semantics differ.

## Completeness Semantics

Diagnosis distinguishes:

- field absent
- field present but empty
- valid zero, `false`, or empty collection where the field contract allows it

For deployment acceptance, `quality_signals` must be a non-empty object and the final answer must be non-empty.
