# TokenSaver

TokenSaver is an open-source runtime ROI diagnosis toolkit for AI Agent applications.

It records Agent runs locally, diagnoses token/context/model/tool waste with local rules, and generates repair briefs that Codex / Claude Code can use to improve the Agent application.

中文定位：

**TokenSaver 是一个面向 Agent 应用的本地运行期 ROI 诊断工具。它帮助开发者记录 Agent 真实运行过程，发现 token、上下文、工具调用、模型选择和工作流 route 的低效问题，并生成可交给 Codex / Claude Code 的优化 brief。**

## Start Here: Let Your Coding Agent Do It

If you are a normal user, you do not need to manually inspect or wire TokenSaver first.

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

## What TokenSaver Currently Does

Current implemented features:

- Agent Runtime Trace SDK
- local JSONL trace storage
- stable trace schema version field
- local run summary markdown
- local repair brief markdown
- local HTML activity panel
- rule-based ROI diagnosis
- channel/task/route-aware budget diagnosis
- ROI dimension scores for cost, latency, context precision, output density, task fit, and quality risk
- top token consumer analysis across context, tools, model calls, and final answers
- tool output governance findings for dominant outputs and raw/full payloads
- required quality field guardrails
- before/after run comparison
- local version and update checks
- update notices in generated reports, repair briefs, and the local panel
- install doctor, verify-install, and environment-specific upgrade commands
- local token estimation
- editable model pricing metadata
- CLI tools
- dependency-free MCP stdio server
- generic LLM call tracing helper
- framework-agnostic callback adapter
- Goldfinger-like example integration

Current diagnosis rules can flag:

- short task using a deep route
- context item too large
- history/log context waste for quick tasks
- output too long for task/channel
- input, output, or latency budget overage
- repeated tool call without cache
- large tool output
- dominant tool output
- raw or full-detail tool payload
- strong model used for quick task
- missing required quality fields
- sensitive realtime/action task missing obvious source attribution
- user correction signal

TokenSaver does **not** upload data by default and does **not** call an LLM by default.

## Install

Recommended in an Agent app:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade \
  git+https://github.com/zhangtao-jayce/TokenSaver.git
```

For macOS Homebrew Python temporary seed-user verification:

```bash
python3 -m pip install --user --break-system-packages --upgrade --force-reinstall \
  git+https://github.com/zhangtao-jayce/TokenSaver.git
```

For local development:

```bash
git clone https://github.com/zhangtao-jayce/TokenSaver.git
cd TokenSaver
python3 -m unittest discover -s tests
```

## Minimal Python Integration

```python
from tokensaver import TokenSaver
from tokensaver.integrations import trace_llm_call

tokensaver = TokenSaver(app="my-agent", channel="slack")

def handle_message(message: str) -> str:
    with tokensaver.run(user_message=message) as run:
        run.set_task(task_type="quick_quote_check", route="deep_research")
        run.set_budget(input_tokens=8000, output_tokens=800, latency_ms=30000)
        run.set_quality_requirements(["source", "as_of_time"])
        run.add_context("price", "market context ...", kind="market_data")

        prompt = f"Answer: {message}"
        answer = trace_llm_call(
            run,
            model="anthropic/claude-sonnet-4-6",
            input_text=prompt,
            call=lambda: call_llm(prompt),
        )
        run.record_final_answer(answer)
        return answer
```

## Read Results

After one Agent run:

```bash
cat .tokensaver/reports/latest.md
cat .tokensaver/briefs/latest.md
python3 -m tokensaver.cli latest --kind panel
```

The summary is for users. The repair brief is for Codex / Claude Code.

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

## CLI

Estimate tokens:

```bash
python3 -m tokensaver.cli estimate "TokenSaver observes Agent runtime ROI locally."
```

Check installed version and updates:

```bash
python3 -m tokensaver.cli version
python3 -m tokensaver.cli version --verbose
python3 -m tokensaver.cli check-update
python3 -m tokensaver.cli check-update --json
```

When a newer version is available, TokenSaver prints a copyable upgrade command:

```bash
python3 -m tokensaver.cli upgrade-command --commit COMMIT
python3 -m tokensaver.cli verify-install --commit COMMIT --check-project-files
python3 -m tokensaver.cli doctor
```

TokenSaver also adds an update notice to generated local artifacts when a newer version is detected. To disable automatic update checks during Agent runs:

```bash
export TOKENSAVER_CHECK_UPDATE_ON_RUN=0
```

If the `tokensaver` console script is not on `PATH`, use the stable module form:

```bash
python3 -m tokensaver.cli version
```

Plan context/model strategy for a task:

```bash
python3 -m tokensaver.cli plan "MU 刚刚为什么突然拉升，要不要减仓？" --model anthropic/claude-sonnet-4-6
```

Record and diagnose a run:

```bash
python3 -m tokensaver.cli record-run --file examples/run.json
```

Read latest artifacts:

```bash
python3 -m tokensaver.cli latest --kind run
python3 -m tokensaver.cli latest --kind summary
python3 -m tokensaver.cli latest --kind brief
python3 -m tokensaver.cli latest --kind panel
```

Inspect recorded runs:

```bash
python3 -m tokensaver.cli list --app goldfinger --channel feishu
python3 -m tokensaver.cli show latest
python3 -m tokensaver.cli report latest
python3 -m tokensaver.cli brief latest
python3 -m tokensaver.cli top-tools --last 50
```

Compare before/after optimization runs:

```bash
python3 -m tokensaver.cli compare --before RUN_ID --after RUN_ID
```

## MCP

Start the stdio MCP server:

```bash
python3 -m tokensaver.mcp_server
```

Available MCP tools:

- `tokensaver.plan_task`
- `tokensaver.estimate_tokens`
- `tokensaver.record_agent_run`
- `tokensaver.get_latest_runs`
- `tokensaver.diagnose_roi`
- `tokensaver.generate_repair_brief`
- `tokensaver.get_version`
- `tokensaver.check_update`
- `tokensaver.doctor`
- `tokensaver.verify_install`
- `tokensaver.upgrade_command`

Codex / Claude Code can use these tools to inspect a task, record Agent runs, read latest traces, diagnose ROI, generate repair briefs, and verify the TokenSaver installation environment.

## Public Docs

- [Integration Guide](docs/集成指南.md)
- [Open Source Scope](OPEN_SOURCE_SCOPE.md)
- [Version Management](VERSION.md)
- [Changelog](CHANGELOG.md)
- [Security Policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Tests

Run tests with the Python standard library:

```bash
python3 -m unittest discover -s tests
```
