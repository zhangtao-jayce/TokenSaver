# Contributing to TokenSaver

TokenSaver is a local-first runtime ROI diagnosis toolkit for AI Agent applications.

Contributions are welcome in the open-source core:

- Runtime trace SDK improvements
- Local storage and report generation
- Rule-based ROI diagnosis
- Repair brief generation
- CLI and MCP tools
- Sample Agent integrations
- Tests and documentation

## Development

Run tests with the Python standard library:

```bash
python3 -m unittest discover -s tests
```

Run a demo trace:

```bash
python3 -m tokensaver.cli record-run --file examples/run.json
python3 -m tokensaver.cli latest --kind summary
python3 -m tokensaver.cli latest --kind brief
```

## Local-First Rule

Open-source TokenSaver must stay local-first by default:

- Do not upload prompts, context, traces, or tool results by default.
- Do not add a required cloud dependency for the core diagnosis loop.
- Do not call an LLM unless the user explicitly wires that behavior.

## Private Planning Docs

Internal planning documents are kept out of the public repository. Public docs should focus on usage, integration, and open-source scope.
