# TokenSaver 开发记录

本文件只追加历史记录。开发成功记录将在完成对应测试 SOP 后写入。

## DEV-20260622-001：建立开发治理基线

- 日期：2026-06-22
- 对应 PRD：`docs/governance/prds/PRD-20260622-001-development-governance.md`
- 对应测试记录：`TEST-20260622-001`
- 状态：成功
- 变更范围：仓库开发流程、治理文档及治理完整性测试

关键设计决策：

- 将 `DEVELOPMENT_PRINCIPLES.md` 设为唯一受控原则正文，避免规则散落后产生冲突。
- 通过根目录 `AGENTS.md` 强制后续开发代理先读取原则和流程。
- 使用 SHA-256 自动化测试保护原则正文，避免无意修改或静默漂移。
- 采用 PRD、测试记录、开发记录三类独立证据，保持决策、验证和结果可回溯。

实际变更：

- 固化开发记录、测试 SOP 与记录、PRD 先行三项原则。
- 明确只有张涛专项授权才能修改原则，并设置六项严格变更门槛。
- 创建治理流程说明、本次小 PRD、追加式日志和 3 项治理测试。
- 未修改 TokenSaver 产品逻辑、公开 API 或 trace schema。

兼容性与风险：

- 现有产品行为保持不变。
- 哈希测试提供仓库内完整性检测，但不能替代 Git 托管平台的权限控制。

验证结果：专项治理测试 3 项通过，全量测试 89 项通过，Python 语法检查和补丁检查通过。详细结果见 `TEST-20260622-001`。

## DEV-20260622-002：TokenSaver 0.7 可信优化闭环

- 日期：2026-06-22
- 对应 PRD：`docs/governance/prds/PRD-20260622-002-v0.7-trustworthy-optimization-loop.md`
- 对应测试记录：`TEST-20260622-002`
- 状态：成功
- 版本：0.7.0
- 变更范围：运行时 schema、SDK、集成适配、诊断、健康状态、存储比较、CLI、报告、测试及发布文档

关键设计决策：

- schema 0.4 将模型 token、工具载荷、最终答案、reasoning、重复上下文和工具 schema 分开，停止把工具输出及最终答案副本加入模型输出总量。
- provider usage 优先，本地估算作为 fallback，并以 `provider`、`estimated`、`mixed` 明示来源。
- health 通过 host request 与 trace started/finished 生命周期区分业务空闲和链路断裂。
- 版本比较复用 `compare` 命令，通过互斥参数保留双 run 模式；群组样本少于最低门槛时不宣称改善。
- 只比较生产流量，避免 smoke 或 deployment audit 污染版本结论。
- 不引入 pandas、scipy 或其他运行依赖，保持本地零依赖核心。

实际变更：

- 新增 schema 0.4 `token_usage` 及模型 usage、工具语义一等字段。
- OpenAI、Anthropic、LiteLLM 兼容适配器可读取常见 provider usage。
- 新增工具 surface 成本及 route tool precision 诊断。
- 新增流量感知 health 字段、请求登记 API、idle 与 broken finding。
- 新增按 host version 及 task/route/channel/app 的群组 P50/P95 比较、质量保持率和小样本状态。
- 更新摘要、README、集成指南、schema 兼容说明、版本及 changelog。
- 新增 12 项 0.7 专项测试，并更新 schema contract 测试。

兼容性与风险：

- schema 0.3 trace、现有 SDK 调用和双 run compare 保持可用。
- schema 0.3 与 0.4 的顶层 token 聚合语义不同，跨 schema 群组比较会显示警告。
- `repeated_context_tokens` 是基于已记录 context 与模型调用次数的估算，不表示供应商账单中的独立项目。
- 群组结论是保守规则判断，不等同统计显著性；小样本明确标记数据不足。

遗留事项：会话级理解、证据归因、实时 policy callback、隐私保留策略和工作流图不属于本版本，需另立 PRD。

验证结果：0.7 专项测试 12 项通过，治理测试 3 项通过，全量测试 101 项通过，CLI/API smoke、语法、补丁及版本一致性检查全部通过。详细结果见 `TEST-20260622-002`。
