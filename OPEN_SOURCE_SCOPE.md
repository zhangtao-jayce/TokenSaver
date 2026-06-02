# TokenSaver Open Source Scope

TokenSaver uses an open-core model.

The open-source core is designed for individual builders and small teams who use Codex, Claude Code, or similar coding agents to build AI Agent applications, then want to observe and improve those applications during real usage.

## Open Source Mission

TokenSaver's open-source core should make it easy to answer:

- What did this Agent run actually do?
- Which workflow route did it take?
- How many tokens did it spend?
- Which context items, tool results, logs, or memories were injected?
- Which model calls were made?
- Was the result worth the token, latency, and model cost?
- What should Codex / Claude Code change next to improve ROI?

The open-source version should be local-first, transparent, and simple enough for a user to hand the integration guide to a coding agent.

## Included In The Open Source Core

The open-source core should include:

- Agent Runtime Trace SDK / event format
- Local JSONL or SQLite trace store
- Local token estimation
- Editable model pricing metadata
- Basic task type and workflow route rules
- Context item recording
- Tool call recording
- Model call recording
- Final answer recording
- Basic ROI rules engine
- Run summary generation
- Repair brief generation for Codex / Claude Code
- Local HTML activity panel
- Generic LLM call tracing helper
- Framework callback adapter
- CLI tools
- MCP server
- Integration guide for coding agents
- Sample integrations, starting with Goldfinger-like Agent applications
- Basic tests and demo traces
- Example Agent run JSON

## Default User Experience

The default first-time integration path is:

```text
Agent Runtime Trace + Local Store + Rules Diagnosis + Repair Brief
```

Users should not need to understand gateways, middleware, callbacks, or dashboards before using TokenSaver.

They should be able to tell Codex / Claude Code:

```text
Read TokenSaver's integration guide and add runtime ROI diagnosis to this Agent app.
```

The coding agent should then add tracing around:

- User message handling
- Task type and route selection
- Context injection
- Tool calls
- Model calls
- Final answer generation
- Quality signals such as follow-up, correction, rating, or handoff

## Not Included In The First Open Source Scope

The first open-source scope should avoid:

- Hosted cloud dashboard
- Full LLM gateway
- Automatic proxying of all model traffic
- Default upload of prompts, context, traces, or tool results
- Team permission management
- Enterprise audit workflows
- Cross-device sync
- Complex policy center
- Large-scale billing and quota management

These are useful capabilities, but they should not complicate the first local integration.

## Commercial / Enterprise Scope

Commercial features can include:

- Hosted dashboard
- Team workspaces
- Multi-Agent and multi-project ROI views
- Cross-device sync
- Enterprise permissions
- Audit reports
- Strategy and policy center
- Advanced model routing
- Advanced quality evaluation
- Regression reports across Agent versions
- Private deployment support
- Deep integrations with Feishu, Slack, GitHub, Jira, and internal tools
- Team workflow for tracking Codex / Claude Code optimization briefs

## Boundary Principle

Open source should cover the full local diagnosis loop:

```text
Trace -> Diagnose -> Summarize -> Generate Repair Brief
```

Commercial features should focus on team-scale coordination, hosted analysis, governance, and advanced optimization workflows.
