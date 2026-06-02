# TokenSaver Open Source Scope

TokenSaver is open source.

This repository currently provides the local runtime diagnosis loop:

```text
Trace -> Diagnose -> Summarize -> Generate Repair Brief
```

## Included In This Repository

- Agent Runtime Trace SDK
- Local JSONL trace store
- Local token estimation
- Editable model pricing metadata
- Basic task type and workflow route rules
- Context item recording
- Tool call recording
- Model call recording
- Final answer recording
- Rule-based ROI diagnosis
- Run summary generation
- Repair brief generation for Codex / Claude Code
- Local HTML activity panel
- Generic LLM call tracing helper
- Framework-agnostic callback adapter
- CLI tools
- MCP stdio server
- Integration guide for coding agents
- Goldfinger-like example integration
- Example Agent run JSON
- Tests

## Not Included

The current repository does not provide:

- hosted cloud dashboard
- full LLM gateway
- automatic proxying of all model traffic
- default upload of prompts, context, traces, or tool results
- team permission management
- enterprise audit workflows
- cross-device sync
- managed billing or quota controls
- automatic LLM-based evaluation

## Data Boundary

By default, TokenSaver writes local artifacts only:

```text
.tokensaver/runs.jsonl
.tokensaver/reports/latest.md
.tokensaver/briefs/latest.md
.tokensaver/panel/index.html
```

TokenSaver does not upload user data by default and does not call an LLM by default.
