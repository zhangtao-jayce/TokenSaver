# Security Policy

TokenSaver observes Agent runtime data, including prompts, context items, tool outputs, model calls, and final answers. The open-source core is designed to be local-first.

## Data Handling

By default, TokenSaver writes local artifacts only:

- `.tokensaver/runs.jsonl`
- `.tokensaver/reports/latest.md`
- `.tokensaver/briefs/latest.md`
- `.tokensaver/panel/index.html`

TokenSaver does not upload user data by default.

## Reporting Issues

If you find a security issue, please avoid posting sensitive data publicly. Open a minimal GitHub issue describing the problem class, or contact the maintainers through the repository's published contact channel once available.

## Sensitive Data Guidance

Do not commit generated `.tokensaver/` traces if they contain private prompts, business context, tool outputs, or user messages. The repository `.gitignore` excludes `.tokensaver/` by default.
