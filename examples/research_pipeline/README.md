# Research Pipeline Example

This deterministic example records source fetch, dedupe/select, generated files,
quality signals, and a handoff to an external coding Agent. It does not call a
network service or count the handoff as a model call.

```bash
python3 -m examples.research_pipeline.research_pipeline \
  --store-dir /tmp/tokensaver-research-pipeline \
  --output-dir /tmp/tokensaver-research-output
```

Inspect the generated report and panel:

```bash
python3 -m tokensaver.cli latest \
  --store-dir /tmp/tokensaver-research-pipeline \
  --kind summary
python3 -m tokensaver.cli open \
  --store-dir /tmp/tokensaver-research-pipeline
```

`run_with_tokensaver.sh.example` is a reviewable template for projects whose
system `python3` differs from the Python where TokenSaver is installed. Copy it
into the host project, set `TOKENSAVER_PYTHON` to a Python 3.10+ executable, and
replace `agent.py` with the real entrypoint. It does not install Python, modify
`PATH`, or alter shell startup files.
