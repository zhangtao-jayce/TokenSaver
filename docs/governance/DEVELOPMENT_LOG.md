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

## DEV-20260622-003：提交并发布 TokenSaver 0.7.0

- 日期：2026-06-22
- 对应 PRD：`docs/governance/prds/PRD-20260622-003-v0.7-release.md`
- 对应测试记录：`TEST-20260622-003`
- 状态：成功
- 发布版本：0.7.0
- 变更范围：GitHub 提交、PR、CI、标签、Release、PyPI Trusted Publishing 和发行包验证

实际结果：

- 发布提交经 rebase 后通过 PR #10 合并到 `main`。
- 合并提交为 `d58842080a7acacbf025efb5eee42988d0bae45c`。
- 创建 `v0.7.0` 标签和 GitHub Release。
- GitHub CI Python 3.10–3.13 矩阵及 benchmark 全部通过。
- Trusted Publishing workflow `27958029885` 成功将 `tokensaver-agent==0.7.0` 发布到 PyPI。
- 全新虚拟环境从 PyPI 安装、版本检查和离线 demo 均通过。

发布决策与风险：

- 使用 GitHub OIDC Trusted Publishing，不在本地处理或保存 PyPI token。
- PyPI 版本不可覆盖，因此只有在 PR CI、构建和本地 wheel 验证通过后才触发正式发布。
- Actions 中 Node.js 20 弃用警告未影响本次结果，后续应单独升级相关 action 大版本并建立小 PRD。
- Goldfinger 升级必须精确 pin `tokensaver-agent==0.7.0`；如验收失败，回退到 `0.6.2`。

验证结果：完整发布 SOP 全部通过，详细证据见 `TEST-20260622-003`。

## DEV-20260623-001：首次安装、Pipeline 与外部 Agent 交接体验

- 日期：2026-06-23
- 对应 PRD：`docs/governance/prds/PRD-20260623-001-onboarding-pipeline-handoff.md`
- 对应测试记录：`TEST-20260623-001`
- 状态：成功
- 变更范围：安装引导、doctor PATH 建议、task type 预算诊断、外部 Agent handoff trace、报告/brief/panel、pipeline 示例、runner 模板、schema 文档和测试

关键设计决策：

- 普通用户安装路径统一为 PyPI，`uvx` 用于零安装 demo/doctor，GitHub 安装仅用于未发布开发版。
- 安装前诊断通过 Python 版本检查和 `uvx` 解决；不增加一个只有安装成功后才能运行的伪“安装前 doctor”。
- `task_type_mismatch` 保持 caller/inferred 分类冲突语义；新增 `task_type_missing_budget` 表示自定义任务回落到默认预算。
- 预算策略不自动写入 profile，只输出确定性、可审查的 YAML 建议。
- external Agent handoff 使用独立 `handoffs` 字段和 `add_handoff` API，不伪装成 model call，不改变 token 统计。
- runner 采用显式 Python 的模板，不自动修改 PATH、shell 配置或用户项目文件。

实际变更：

- README 与集成指南新增四层命名映射、Python 3.10+ 预检、低版本 pip 报错解释、PyPI/uvx/GitHub 安装优先级。
- doctor 的 PATH finding 新增 shell-quoted `export PATH` 命令和当前 Python 模块入口。
- 新增 `task_type_missing_budget` finding，提供实际 fallback budget 证据和 profile YAML patch。
- SDK 新增 `AgentRun.add_handoff`，支持 `prepared`、`completed`、`failed` 状态、artifact 标识、预期输出和 metadata。
- 外部 JSON trace 支持 handoff 规范化；`handoffs` 加入标准集成字段。
- run summary、repair brief 和本地 panel 显示 handoff，同时保持 model/token 统计隔离。
- 新增离线 research pipeline 示例及 `TOKENSAVER_PYTHON` runner 模板。
- 更新 schema 兼容说明、Unreleased changelog、集成字段合约和 6 项专项测试。

兼容性与风险：

- `handoffs` 和新 finding code 均为 additive；旧 schema 0.3/0.4 trace 和既有 SDK API 保持可用。
- handoff instruction 仍是本地 trace 数据，调用方可省略该字段并只记录 artifact 标识；TokenSaver 不读取或上传 artifact 文件。
- 新 finding 会使没有专属预算且没有显式 run budget 的自定义 task type 显示 medium 提示，这是预期的可观测性变化。
- runner 模板面向 POSIX shell，不承担 Python 安装和环境管理。
- 本次未修改版本号、受控开发原则或完整性基线，未执行发布和外部写入。

验证结果：专项测试 6 项、关键回归 65 项、治理测试 3 项、全量测试 107 项全部通过；语法检查、离线 pipeline smoke、安装文案检查和 `git diff --check` 通过。测试过程中的两次中间失败及处置已如实记录。详细结果见 `TEST-20260623-001`。
