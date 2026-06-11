# TokenSaver Launch Kit

TokenSaver is a local-first ROI diagnosis toolkit for AI Agent applications. It finds wasted context, repeated tool calls, oversized retrieval payloads, expensive routes, and quality regression risk, then generates a repair brief for coding agents.

## Show HN

Title:

```text
Show HN: TokenSaver – Find wasted context and tool calls in AI agents locally
```

Body:

```text
I built TokenSaver after seeing simple Agent requests go through deep workflows with large conversation histories, repeated tool calls, and expensive model inputs.

TokenSaver records an Agent run locally, applies deterministic ROI checks, and generates a repair brief that Codex or Claude Code can implement. It does not upload prompts or traces and does not require an LLM for diagnosis.

The zero-setup demo:

uvx tokensaver-agent demo

The bundled deterministic example goes from 32,540 to 2,460 input tokens and from a 35 to 100 ROI score. Those are fixture results, not a universal performance claim.

The repository includes OpenAI, Anthropic, LiteLLM, and LangGraph helpers, three reproducible before/after cases, an offline HTML panel, MCP tools, and benchmark share cards.

I would especially value feedback on the diagnosis rules and which Agent frameworks should get first-class examples next.
```

## Reddit

Title:

```text
My agent used 32k input tokens for a simple status question, so I built a local tool to explain why
```

Body:

```text
TokenSaver traces route/context/tool/model usage for an AI Agent run and flags patterns such as deep routes for short tasks, repeated uncached tools, oversized RAG payloads, and ReAct context amplification.

It stays local and generates a coding-agent repair brief plus a before/after benchmark.

Try the deterministic demo:
uvx tokensaver-agent demo

GitHub: https://github.com/zhangtao-jayce/TokenSaver

The demo numbers are fixture results and are labeled as such. I am looking for real integrations and diagnosis-rule feedback.
```

## V2EX / 掘金

Title:

```text
我做了一个本地 Agent ROI 诊断工具：定位上下文、工具调用和路由浪费
```

Body:

```text
TokenSaver 不是 Prompt 压缩器，也不是云端监控平台。它旁路记录 Agent 的 route、context、tool、model、latency 和质量信号，再用本地规则找出低 ROI 模式，并生成 Codex / Claude Code 可以直接执行的修复 brief。

无需账号、默认不上传数据、诊断过程不调用 LLM：

uvx tokensaver-agent demo

仓库内提供 LangGraph 重复工具调用、OpenAI Coding Agent 上下文浪费、RAG 检索结果过长三个可复现案例。

GitHub:
https://github.com/zhangtao-jayce/TokenSaver
```

## Integration Outreach

```text
Hi, I maintain TokenSaver, a local-first Agent ROI diagnosis toolkit.

I noticed this project has a clear user-message / tool / model execution path. I would like to contribute an optional TokenSaver example that:

- keeps all traces local
- adds no required cloud service
- records route, context size, tools, model calls, latency, and quality signals
- includes a deterministic test and before/after benchmark

Would an example integration PR be useful? I will keep it isolated and dependency-optional.
```

## Launch Checklist

- Merge the release PR.
- Create the GitHub release and attach wheel/sdist.
- Publish `tokensaver-agent` to PyPI.
- Run `uvx tokensaver-agent demo` from a clean environment.
- Post Show HN, Reddit, V2EX, and 掘金 versions with the same factual claims.
- Open integration discussions before submitting changes to third-party repositories.
- Track stars, unique visitors, clones, referrers, demo issues, and integration requests weekly.
