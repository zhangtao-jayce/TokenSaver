# Reproducible Agent ROI Case Studies

These cases use deterministic synthetic traces. They are designed to reproduce diagnosis and comparison behavior without API keys, private data, or model calls.

## Run All Three

```bash
tokensaver benchmark \
  --before-file examples/case-studies/langgraph-repeated-tools/before.json \
  --after-file examples/case-studies/langgraph-repeated-tools/after.json \
  --output-dir .tokensaver-cases/langgraph \
  --title "LangGraph repeated tool calls"

tokensaver benchmark \
  --before-file examples/case-studies/openai-context-waste/before.json \
  --after-file examples/case-studies/openai-context-waste/after.json \
  --output-dir .tokensaver-cases/openai \
  --title "OpenAI coding agent context waste"

tokensaver benchmark \
  --before-file examples/case-studies/rag-oversized-retrieval/before.json \
  --after-file examples/case-studies/rag-oversized-retrieval/after.json \
  --output-dir .tokensaver-cases/rag \
  --title "RAG oversized retrieval payload"
```

Each command writes:

```text
benchmark.json
benchmark.md
share-card.svg
```

The quality requirements and signals remain present in both sides of every comparison. This lets TokenSaver reduce cost and latency without treating missing quality checks as a successful optimization.
