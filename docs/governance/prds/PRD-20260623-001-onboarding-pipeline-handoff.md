# PRD-20260623-001：首次安装、Pipeline 与外部 Agent 交接体验

- 状态：已完成
- 日期：2026-06-23
- 需求来源：张涛基于另一位真实用户的部署复盘，明确要求按整理后的产品建议全部迭代
- 规模：中型跨模块迭代

## 问题与目标

真实用户已验证 TokenSaver 的本地 trace、ROI 诊断、report、brief 和 panel 价值，但在首次安装和非标准工作流接入阶段遇到以下摩擦：

- 产品名、PyPI 包名、import 名和 CLI 名不同，文档未统一解释。
- README 已使用 PyPI，集成指南仍把 GitHub 源码安装作为默认路径。
- Python 低于 3.10 时，pip 的报错容易被误解为包不存在。
- `doctor` 只能在安装后运行，缺少不依赖本地安装的预检入口说明。
- batch/research pipeline 和“本地脚本生成 raw、外部 Codex/Claude 完成分析”的工作流缺少一等示例及交接记录。
- `task_type_mismatch` 与“自定义 task type 没有专属预算”没有被区分。
- PATH 建议尚未提供可直接复制的 shell 命令。
- 解释器错配场景缺少安全、可审查的 runner 模板。

本次目标是降低首次成功运行和 pipeline 接入成本，同时保持 TokenSaver 的本地优先、零运行依赖和向后兼容。

## 用户场景

1. Python 新用户从 PyPI 安装，能在安装前确认版本要求并理解四种命名。
2. 系统 `python3` 过旧的用户可用 `uvx` 完成 demo/doctor，或选择明确的 Python 3.10+ 解释器。
3. batch research pipeline 能记录 source fetch、dedupe/select、model summarization 和输出文件。
4. 外部 Agent 接力工作流能记录输入产物、任务说明、预期输出和交接完成状态，即使宿主脚本没有传统 `model_call`。
5. 自定义 task type 使用默认预算时得到单独、可行动的 profile 建议，而不会与分类冲突混为一谈。

## 范围

- 统一 README 与集成指南中的 PyPI 首选、uvx 备用、GitHub 开发版安装顺序。
- 增加安装前 Python 版本检查、典型错误解释和命名映射。
- 改善 `doctor` 的 PATH 修复文案，输出精确、可复制且带 shell 转义的命令。
- 新增 `task_type_missing_budget` 诊断；保留现有 `task_type_mismatch` 语义。
- 新增 SDK 外部 Agent handoff 记录接口、schema 规范化、报告/brief 摘要和最小示例。
- 新增 research/batch pipeline 示例和测试。
- 提供 runner 脚本模板及生成说明，但不让 TokenSaver 自动修改用户 shell 配置。
- 更新公开文档、schema 兼容说明和 changelog 的 Unreleased 部分（如存在）。

## 非范围

- 不修改受控开发原则或其完整性基线。
- 不发布新版本，不创建 GitHub PR，不修改外部仓库。
- 不实现 Python 解释器下载器、环境管理器或自动修改用户 PATH。
- 不让 TokenSaver 执行外部 Agent，也不读取或上传交接文件内容。
- 不把自定义 task type 自动写入 profile；只生成确定性建议，避免静默修改用户预算策略。

## 设计方案

### 1. 安装信息架构

- 首选：`python3 -m pip install tokensaver-agent`。
- 零安装体验/预检：`uvx tokensaver-agent demo` 与 `uvx tokensaver-agent doctor`。
- 开发版：`python3 -m pip install git+https://...`。
- 文档明确：项目名 TokenSaver、distribution `tokensaver-agent`、import `tokensaver`、CLI `tokensaver`。
- 所有手工安装路径先显示 `python3 --version`，要求 3.10+。

### 2. Doctor 可行动输出

- PATH finding 保留 `python -m tokensaver.cli` fallback。
- 额外返回 POSIX shell 可复制的 `export PATH=...:$PATH` 命令。
- 使用 shell quoting 处理包含空格或特殊字符的脚本目录。
- 保持 finding code 和现有字段兼容，只增加证据/建议内容。

### 3. Task type 诊断拆分

- `task_type_mismatch` 继续只表示 caller 与 inferred classification 不一致。
- 当选中 task type 不在 profile `budgets` 且实际回落到 `default` 时，新增 `task_type_missing_budget`。
- finding 说明当前正在使用 default budget，并提供可复制的 YAML patch 示例；不自动改 profile。
- 空 profile 或显式提供 task budget 时不误报。

### 4. External Agent handoff

在单次 run 上新增 `add_handoff(...)`：

- `agent`：下游 Agent 名称，例如 `codex`。
- `mode`：默认 `external_agent_handoff`。
- `input_artifacts`：只记录路径/标识，不读取内容。
- `instruction`：可选任务说明，沿用本地 trace 数据边界。
- `expected_output`：预期输出路径/标识。
- `status`：`prepared`、`completed` 或 `failed`。
- `output_artifacts`、`metadata`：可选。

规范化后的顶层字段为 `handoffs`。旧 trace 无此字段时按空列表处理。报告和 repair brief 显示 handoff 数量、目标和状态；不把它伪装成 model call。

### 5. Pipeline 示例与 runner 模板

- 增加可离线运行的 research pipeline 示例，记录抓取、去重、选择、外部交接及输出状态。
- 增加 `run_with_tokensaver.sh.example`，通过 `TOKENSAVER_PYTHON` 显式选择解释器并使用 `exec` 运行宿主入口。
- 模板不硬编码用户机器路径，不自动写入 PATH，不代替虚拟环境。

## 数据与接口兼容性

- `handoffs` 是可选的 additive 字段；现有 schema 0.3/0.4 trace 继续可读。
- `add_handoff` 是新增 API，不改变现有 `TokenSaver.run`、tool/model/context API。
- 新 diagnosis code 是 additive；依赖固定 finding 集合的消费者应忽略未知 code。
- 不增加第三方运行依赖。

## 文件影响

预计涉及：

- `README.md`
- `docs/集成指南.md`
- `docs/schema-compatibility.md`
- `CHANGELOG.md`
- `tokensaver/runtime.py`
- `tokensaver/diagnosis.py`
- `tokensaver/install.py`
- `tokensaver/store.py`
- `tokensaver/brief.py`
- `examples/` 下新增 pipeline 与 runner 模板
- `tests/` 下新增或扩展专项测试
- `docs/governance/TEST_LOG.md`
- `docs/governance/DEVELOPMENT_LOG.md`

## 备选方案

- 自动生成并写入 runner：拒绝。解释器和宿主入口属于用户环境，自动写文件容易产生错误路径和错误权限。
- 安装包内新增 `doctor --install-check`：拒绝作为安装前方案，因为安装失败时该命令不可用；使用 `uvx` 和文档预检解决。
- 未知 task type 自动写 profile：拒绝。预算是产品策略，必须由项目所有者审查。
- 把外部 handoff 记录为 model call：拒绝。该做法会污染模型 token 和延迟统计。

## 风险与缓解

- handoff instruction 可能包含敏感内容：保持本地存储，并允许调用方省略 instruction、只记录 artifact 标识。
- 新 finding 可能增加现有报告告警数量：仅在自定义 task type 确实使用 default budget 时触发，并采用 medium severity。
- 文档命令随 shell 不同：runner 和 PATH 命令限定 POSIX shell；Windows 用户继续使用模块入口。
- 示例可能被误当生产实现：明确其为最小离线模板。

## 阶段计划

1. 建立专项测试，覆盖诊断、PATH 命令、handoff API/持久化/报告。
2. 实现 SDK、规范化、诊断和展示。
3. 增加 pipeline 示例、runner 模板和统一文档。
4. 执行专项、治理、全量、语法、示例 smoke 和 diff 检查。
5. 追加测试记录和开发记录，核对一致性。

## 成功指标

- 文档中普通用户默认安装路径不再依赖 GitHub clone。
- Python 3.10+ 要求在安装命令之前可见。
- 自定义 task type 的预算缺失与分类冲突产生不同 finding。
- 外部 handoff 不增加 `model_calls`，但能在 trace、report 和 brief 中审计。
- pipeline 示例在无网络、无外部模型调用时可生成本地 trace 和报告。

## 验收标准

1. README 和集成指南给出一致的安装优先级及命名映射。
2. 文档解释 Python 低版本的典型 pip 失败和可执行解决路径。
3. PATH finding 包含精确模块 fallback 和可复制 export 命令。
4. 未配置自定义 task type 预算时出现 `task_type_missing_budget`；显式预算时不出现。
5. caller/inferred 不一致仍独立产生 `task_type_mismatch`。
6. `add_handoff` 能持久化、规范化并展示，不污染 model call/token 统计。
7. batch/research pipeline 示例和 runner 模板存在且说明安全边界。
8. 治理原则文件及完整性基线未变化。
9. 所有测试 SOP 通过，测试记录和开发记录均已追加。

## 测试 SOP

1. 运行本次专项测试：
   `python3 -m unittest tests.test_onboarding_pipeline_handoff -v`
2. 运行既有安装、profile、runtime、panel 与生产健康回归：
   `python3 -m unittest tests.test_install tests.test_profile tests.test_runtime tests.test_panel tests.test_v06_production_health -v`
3. 运行治理完整性测试：
   `python3 -m unittest tests.test_governance -v`
4. 运行全量测试：
   `python3 -m unittest discover -s tests`
5. 运行 Python 语法检查：
   `python3 -m py_compile tokensaver/*.py tests/*.py examples/research_pipeline/*.py`
6. 在临时目录执行离线 pipeline smoke，确认生成 trace、report、brief 和 panel，且 handoff 不计入 model call。
7. 检查安装命令一致性和 GitHub 开发版标识：
   `rg -n "pip install|uvx tokensaver-agent|Python 3.10|development version|开发版" README.md docs/集成指南.md`
8. 运行补丁格式检查：
   `git diff --check`

只有以上步骤全部通过并追加真实测试记录后，才可将本次开发记录标记为成功。
