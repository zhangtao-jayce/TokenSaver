# TokenSaver

TokenSaver is an open-source runtime ROI diagnosis toolkit for AI Agent applications.

It helps builders trace Agent runs locally, diagnose token/context/model/tool waste, and generate repair briefs that Codex / Claude Code can use to improve the Agent application.

中文定位：

**TokenSaver 是一个帮助 Agent 应用开发者观察真实运行中的 Token ROI 问题，并把低效模式转化为 Codex / Claude Code 可执行优化任务的本地优先诊断工具。**

## Start Here: Let Your Coding Agent Do It

If you are a normal user, you do not need to manually install, inspect, or wire TokenSaver first.

Open your Agent application in Codex / Claude Code, then copy this prompt:

```text
Please integrate TokenSaver into this Agent application.

TokenSaver repository:
https://github.com/zhangtao-jayce/TokenSaver

Read:
- README.md
- docs/集成指南.md

Requirements:
1. Find the main entrypoint where this Agent handles a user message.
2. Install TokenSaver in this project if needed:
   pip install git+https://github.com/zhangtao-jayce/TokenSaver.git
3. Add Agent Runtime Trace around each user-message run.
4. Record app, channel, user_message, task_type, route, context_items, tool_calls, model_calls, answer, and quality_signals when available.
5. Keep all TokenSaver data local. Do not upload prompts, context, traces, or tool outputs.
6. Run or add a minimal demo/test message that triggers one Agent run.
7. Confirm these files exist:
   - .tokensaver/runs.jsonl
   - .tokensaver/reports/latest.md
   - .tokensaver/briefs/latest.md
   - .tokensaver/panel/index.html
8. Show me the contents of:
   - .tokensaver/reports/latest.md
   - .tokensaver/briefs/latest.md
9. Tell me the command to open or view .tokensaver/panel/index.html.
10. Add a minimal test or demo command that proves TokenSaver trace generation works.
```

That is the main deployment path. TokenSaver is designed so the coding agent can read this repository and perform the integration for you.

After integration, your coding agent should show you:

- the latest run summary
- the repair brief
- the local activity panel path
- the test or demo command it added

TokenSaver writes results locally:

```text
.tokensaver/
  runs.jsonl
  reports/latest.md
  briefs/latest.md
  panel/index.html
```

The `latest.md` report is for users. The repair brief is for Codex / Claude Code to improve the Agent app.

## Manual Commands For Coding Agents

These commands are mainly for Codex / Claude Code to use while integrating TokenSaver.

Install from GitHub:

```bash
pip install git+https://github.com/zhangtao-jayce/TokenSaver.git
```

Read generated results:

```bash
cat .tokensaver/reports/latest.md
cat .tokensaver/briefs/latest.md
python3 -m tokensaver.cli latest --kind panel
```

## Minimal Python Integration

```python
from tokensaver import TokenSaver
from tokensaver.integrations import trace_llm_call

tokensaver = TokenSaver(app="my-agent", channel="slack")

def handle_message(message: str) -> str:
    with tokensaver.run(user_message=message) as run:
        run.set_task(task_type="quick_quote_check", route="deep_research")
        run.add_context("price", "market context ...", kind="market_data")

        prompt = f"Answer: {message}"
        answer = trace_llm_call(
            run,
            model="anthropic/claude-sonnet-4-6",
            input_text=prompt,
            call=lambda: call_llm(prompt),
        )
        run.record_answer(answer)
        return answer
```

## Try TokenSaver Without Modifying Your App

Record and diagnose the example run:

```bash
cat examples/run.json | python3 -m tokensaver.cli record-run
python3 -m tokensaver.cli latest --kind summary
python3 -m tokensaver.cli latest --kind brief
python3 -m tokensaver.cli latest --kind panel
```

Run the Goldfinger-like example:

```bash
python3 examples/goldfinger_agent.py
```

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

## CLI And MCP

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

Run tests with the Python standard library:

```bash
python3 -m unittest discover -s tests
```
