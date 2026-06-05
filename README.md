# TokenSaver

TokenSaver is a local-first ROI diagnosis toolkit for AI Agent applications.

It records real Agent runs, diagnoses token/context/tool/model/route waste with local rules, and generates repair briefs that coding agents can use to improve the host Agent application.

中文定位：TokenSaver 是面向 Agent 应用的本地运行期 ROI 诊断工具，帮助开发者发现 token、上下文、工具输出、模型选择和工作流 route 的低效问题，并生成可执行的优化 brief。

TokenSaver does not upload prompts, traces, tool outputs, or user data by default. It does not call an LLM by default.

## Quick Start

Recommended installation inside an Agent project:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade \
  git+https://github.com/zhangtao-jayce/TokenSaver.git
```

For macOS Homebrew Python temporary verification:

```bash
python3 -m pip install --user --break-system-packages --upgrade --force-reinstall \
  git+https://github.com/zhangtao-jayce/TokenSaver.git
```

Verify the install:

```bash
python3 -m tokensaver.cli version --verbose
python3 -m tokensaver.cli doctor
```

Create a project profile:

```bash
python3 -m tokensaver.cli init-profile --template coding-agent
python3 -m tokensaver.cli doctor --profile .tokensaver/profile.yaml
```

If the `tokensaver` console script is not on `PATH`, use the stable module form:

```bash
python3 -m tokensaver.cli ...
```

## Let Your Coding Agent Integrate It

Copy this into Codex / Claude Code inside your Agent app repository:

```text
Please integrate TokenSaver into this Agent application.

Repository:
https://github.com/zhangtao-jayce/TokenSaver

Requirements:
1. Find the main entrypoint where this Agent handles a user message.
2. Install TokenSaver with python -m pip if needed.
3. Add a TokenSaver runtime trace around each user-message run.
4. Record app, channel, user_message, task_type, route, context_items, tool_calls, model_calls, final answer, and quality signals when available.
5. Keep TokenSaver data local.
6. Run a minimal demo/test message and confirm these files exist:
   - .tokensaver/runs.jsonl
   - .tokensaver/reports/latest.md
   - .tokensaver/briefs/latest.md
   - .tokensaver/panel/index.html
7. Show the latest report and repair brief.
8. Add or document a minimal command that proves trace generation works.
```

## Minimal Python API

```python
from tokensaver import TokenSaver
from tokensaver.integrations import trace_llm_call

tokensaver = TokenSaver(app="my-agent", channel="slack")

def handle_message(message: str) -> str:
    with tokensaver.run(user_message=message) as run:
        run.set_task(task_type="quick_question", route="deep_research")
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

## Outputs

After one run, TokenSaver writes:

```text
.tokensaver/
  runs.jsonl
  reports/latest.md
  briefs/latest.md
  panel/index.html
```

Read the latest artifacts:

```bash
python3 -m tokensaver.cli latest --kind summary
python3 -m tokensaver.cli latest --kind brief
python3 -m tokensaver.cli latest --kind panel
```

## Core Features

- Local Agent runtime tracing and JSONL storage.
- Profile-driven ROI diagnosis for task/channel/route budget, context precision, tool output size, repeated tools, model choice, latency, and quality guardrails.
- Top token consumer analysis and before/after run comparison.
- Repair brief generation for coding agents.
- Local activity panel.
- Install and upgrade diagnostics: `version --verbose`, `doctor`, `verify-install`, `upgrade-command`.
- Dependency-free MCP stdio server.

## Useful CLI

```bash
# Diagnose install and environment
python3 -m tokensaver.cli version --verbose
python3 -m tokensaver.cli doctor
python3 -m tokensaver.cli init-profile --template coding-agent
python3 -m tokensaver.cli doctor --profile .tokensaver/profile.yaml
python3 -m tokensaver.cli check-update
python3 -m tokensaver.cli upgrade-command --commit COMMIT
python3 -m tokensaver.cli verify-install --commit COMMIT --check-project-files

# Record and inspect runs
python3 -m tokensaver.cli record-run --file examples/run.json --profile .tokensaver/profile.yaml
python3 -m tokensaver.cli list --limit 20
python3 -m tokensaver.cli report latest --profile .tokensaver/profile.yaml
python3 -m tokensaver.cli brief latest --profile .tokensaver/profile.yaml
python3 -m tokensaver.cli top-tools --last 50
python3 -m tokensaver.cli compare --before RUN_ID --after RUN_ID --profile .tokensaver/profile.yaml
python3 -m tokensaver.cli eval examples/agent_cases.json --profile .tokensaver/profile.yaml
```

## Profiles

Profiles keep project-specific budgets and quality guardrails out of TokenSaver code:

```yaml
app: my_agent
channel: chat
budgets:
  quick_question:
    input_tokens: 3000
    output_tokens: 500
    latency_ms: 20000
required_fields:
  quick_question:
    - conclusion
    - next_action
```

Fixture evals can check optimization guardrails:

```json
[
  {
    "id": "quick_question_basic",
    "input": "Summarize the current status.",
    "task_type": "quick_question",
    "expected_required_fields": ["conclusion", "next_action"],
    "max_output_tokens": 1200
  }
]
```

Built-in templates:

- `chatbot`
- `coding-agent`
- `crm-agent`
- `finance-assistant`
- `legal-assistant`
- `research-agent`
- `support-bot`

## MCP

Start the stdio MCP server:

```bash
python3 -m tokensaver.mcp_server
```

Main MCP tools:

- `tokensaver.plan_task`
- `tokensaver.record_agent_run`
- `tokensaver.init_profile`
- `tokensaver.eval_fixtures`
- `tokensaver.diagnose_roi`
- `tokensaver.generate_repair_brief`
- `tokensaver.get_version`
- `tokensaver.check_update`
- `tokensaver.doctor`
- `tokensaver.verify_install`
- `tokensaver.upgrade_command`

## Development

```bash
git clone https://github.com/zhangtao-jayce/TokenSaver.git
cd TokenSaver
python3 -m unittest discover -s tests
python3 -m py_compile tokensaver/*.py
```

## Docs

- [Integration Guide](docs/集成指南.md)
- [Open Source Scope](OPEN_SOURCE_SCOPE.md)
- [Version Management](VERSION.md)
- [Changelog](CHANGELOG.md)
- [Security Policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## Compatibility Notes

TokenSaver normalizes older finding codes when comparing historical runs:

- `wrong_route_for_task` -> `deep_route_for_short_task`
- `tool_output_too_large` -> `oversized_tool_output`
- `raw_tool_payload` -> `raw_payload_in_default_path`
- `repeated_tool_without_cache` -> `repeated_tool_call_without_cache`
- `context_item_too_large` -> `oversized_context_item`
- `history_context_waste` -> `history_context_pollution`
- `answer_too_long_for_channel` -> `channel_output_over_budget`
- `overpowered_model_for_quick_task` -> `strong_model_for_simple_task`
- `missing_required_quality_field` -> `required_field_missing`
- `quality_fields_not_verified` -> `quality_regression_risk`

Deferred roadmap items:

- Optional full YAML support through PyYAML or another parser.
- More domain templates such as finance, legal, and CRM after quality expectations are defined.
- Eval execution against a live host Agent entrypoint.
- Automatic profile inference and optimization PR generation.
