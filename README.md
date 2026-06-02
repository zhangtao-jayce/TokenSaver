# TokenSaver

TokenSaver is an open-source sidecar for observing and optimizing AI Agent application ROI.

中文定位：

**TokenSaver 是一个帮助 Agent 应用开发者观察真实运行中的 Token ROI 问题，并把低效模式转化为 Codex / Claude Code 可执行优化任务的本地优先诊断层。**

它默认不打断用户主流程，通过低打扰的侧边面板或 MCP 工具展示 Agent 应用每次运行的 Token 成本、上下文浪费、模型策略、质量风险和优化机会；只有在高成本或高风险场景下，才建议用户采取优化动作，并生成可交给 Codex / Claude Code 的改造 brief。

## Core Idea

TokenSaver is not a simple token counter, and it is not trying to replace coding agents.

It helps users answer:

- Is this Agent application routing a user request through the right workflow?
- What context is actually needed for this Agent run?
- Which context, tool output, memory, or logs are redundant or risky?
- Is the selected model appropriate for this task type?
- How much does this Agent run cost in tokens, latency, and model spend?
- Is the result worth the token and model spend?
- What should Codex / Claude Code change in the Agent code to improve ROI?

## Product Shape

TokenSaver should work as a sidecar, not as the user's primary AI tool or primary coding agent.

Users continue using their existing workflows:

- Codex / Claude Code to build Agent applications
- Feishu / Slack / web apps to use those Agent applications
- MCP Agents, internal AI tools, business agents, and API-based LLM apps

TokenSaver observes and assists beside them:

- Runtime trace recording for Agent applications
- Token, latency, and cost estimation
- Task route and model strategy diagnosis
- Context, memory, tool output, and log redundancy detection
- Quality and risk checks
- ROI logging and regression comparison
- Codex / Claude Code optimization brief generation

## Integration Philosophy

TokenSaver's integration guide should be simple enough for a non-expert user to hand to Codex / Claude Code.

The expected user workflow is:

```text
1. User builds an Agent application with Codex / Claude Code.
2. User asks the coding agent: "Read TokenSaver's integration guide and add runtime ROI diagnosis to my Agent app."
3. The coding agent adds TokenSaver tracing around the Agent's message handling, model calls, tool calls, context injection, and final answer.
4. User keeps using the Agent normally.
5. TokenSaver records runs locally, diagnoses low-ROI patterns, and generates repair briefs for the next coding-agent iteration.
```

The first integration path should be boring and obvious:

- No gateway required.
- No cloud account required.
- No dashboard required.
- No manual architecture decision required for the first install.
- One recommended default path: Agent runtime tracing with local storage.
- Advanced forms such as wrappers, framework middleware, gateway, log import, and MCP should be optional.

## First Open-Source Direction

The initial open-source version should focus on Agent builders who use Codex / Claude Code to create applications, then discover ROI problems during real usage.

- Local-first runtime observation
- Lightweight Agent trace SDK / event format
- MCP server integration
- Local activity panel
- Model pricing table
- Token estimation
- Context waste detection
- Workflow route and risk checks
- Fixed-model optimization suggestions
- Repair brief generation for Codex / Claude Code

The first version should avoid becoming a large LLM gateway or enterprise dashboard.

## Design Principles

- Install once, work continuously.
- Do not interrupt the main workflow by default.
- Observe locally before using any LLM.
- Spend TokenSaver's own tokens only when the expected ROI is clearly positive.
- Show TokenSaver's own cost when it invokes a model.
- Keep user data local by default.
- Make optimization suggestions explainable and reversible.
- Treat token saving as a means, not the product's only goal.

## Open-Core Direction

TokenSaver uses an open-core model.

The open-source core should cover the full local diagnosis loop:

```text
Trace -> Diagnose -> Summarize -> Generate Repair Brief
```

Recommended open-source scope:

- Agent Runtime Trace SDK / event format
- Local JSONL / SQLite trace store
- Local tokenizer and token estimation
- Editable model pricing metadata
- Task type and workflow route rules
- Context, tool call, model call, and final answer recording
- Basic ROI rules engine
- Run summary generation
- Repair brief generation for Codex / Claude Code
- CLI tools
- MCP server
- Integration guide for coding agents
- Sample integrations, starting with Goldfinger-like Agent applications

Potential commercial scope later:

- Hosted dashboard
- Team workspaces
- Multi-Agent and multi-project ROI views
- Cross-device sync
- Strategy and policy center
- Enterprise permissions
- Audit reports
- Advanced model routing
- Advanced quality evaluation
- Agent version regression reports
- Private deployment support

See [TokenSaver Open Source Scope](OPEN_SOURCE_SCOPE.md) for the GitHub-facing open-source boundary.

## Current Status

This repository contains the first runnable open-source core.

The open-source core currently includes:

- Local token and cost estimation
- Rule-first task classification
- Context review and risk hints
- `tokensaver plan` CLI
- Agent Runtime Trace SDK
- Local JSONL trace store
- Rule-based ROI diagnosis
- Run summary generation
- Repair brief generation for Codex / Claude Code
- Dependency-free MCP stdio server with planning and runtime tools

See:

- [TokenSaver Open Source Scope](OPEN_SOURCE_SCOPE.md)
- [TokenSaver 集成指南](docs/集成指南.md)

## Quick Start

Current implemented features are:

- CLI token estimation
- CLI task planning
- Agent Runtime Trace SDK
- Local `.tokensaver/runs.jsonl` trace storage
- Local `.tokensaver/reports/latest.md` run summary
- Local `.tokensaver/briefs/latest.md` repair brief
- Local `.tokensaver/panel/index.html` activity panel
- MCP stdio tools for planning, recording runs, reading latest runs, ROI diagnosis, and repair brief generation
- Generic LLM call tracing helper and framework callback adapter
- Goldfinger-like example integration

Run a local task plan:

```bash
python3 -m tokensaver.cli plan "MU 刚刚为什么突然拉升，要不要减仓？" --model anthropic/claude-sonnet-4-6
```

The result is printed to stdout as JSON. Coding agents should read:

- `task_type`
- `recommended_context`
- `excluded_context`
- `model_strategy`
- `risks`
- `next_actions`

Estimate tokens:

```bash
python3 -m tokensaver.cli estimate "TokenSaver observes AI workflow ROI locally."
```

Start the MCP stdio server:

```bash
python3 -m tokensaver.mcp_server
```

When used through MCP, Codex / Claude Code should call `tokensaver.plan_task` or `tokensaver.estimate_tokens`, then summarize the returned JSON for the user.

Record and diagnose an Agent run from JSON:

```bash
cat examples/run.json | python3 -m tokensaver.cli record-run
```

Read the latest generated artifacts:

```bash
python3 -m tokensaver.cli latest --kind summary
python3 -m tokensaver.cli latest --kind brief
python3 -m tokensaver.cli latest --kind run
python3 -m tokensaver.cli latest --kind panel
```

Use the runtime SDK inside an Agent application:

```python
from tokensaver import TokenSaver

tokensaver = TokenSaver(app="goldfinger", channel="feishu")

def handle_message(message: str) -> str:
    with tokensaver.run(user_message=message, task_type="quick_quote_check") as run:
        run.set_task(route="deep_stock_research")
        run.add_context("price", "MU current price ...", kind="market_data")
        answer = "Short answer ..."
        run.record_model_call(
            model="anthropic/claude-sonnet-4-6",
            input_text="prompt ...",
            output_text=answer,
        )
        run.record_answer(answer)
        return answer
```

Run the Goldfinger-like example:

```bash
python3 examples/goldfinger_agent.py
```

Run tests with the Python standard library:

```bash
python3 -m unittest discover -s tests
```
