# TokenSaver 测试记录

本文件只追加真实测试结果。测试执行完成后再写入，不得预填成功。

## TEST-20260622-001：开发治理基线

- 日期：2026-06-22
- 对应 PRD：`PRD-20260622-001-development-governance.md`
- 环境：macOS，Python 3，仓库工作区
- 总体结果：通过

执行结果：

1. `python3 -m unittest tests.test_governance -v`
   - 结果：通过
   - 明细：运行 3 项测试，全部通过。
2. `python3 -m unittest discover -s tests`
   - 结果：通过
   - 明细：运行 89 项测试，全部通过；测试套件按预期打印一次持久化失败模拟日志，不影响测试结果。
3. `python3 -m py_compile tokensaver/*.py tests/*.py`
   - 结果：通过，退出码 0。
4. `git diff --check`
   - 结果：通过，退出码 0。

结论：本次开发满足 PRD 测试 SOP，可以进入开发记录和最终验收。

## TEST-20260623-002：TokenSaver 0.8.0 发布前本地验证

- 日期：2026-06-23
- 对应 PRD：`PRD-20260623-002-v0.8-release.md`
- 环境：macOS，Python 3.14，本地隔离构建环境与临时虚拟环境
- 阶段结果：本地发布前验证通过；GitHub CI、标签、Trusted Publishing 和 PyPI 安装待发布后验证

执行结果：

1. `python3 -m unittest tests.test_onboarding_pipeline_handoff -v`
   - 结果：通过；6 项专项测试全部通过。
2. `python3 -m unittest tests.test_governance -v`
   - 结果：通过；3 项治理测试全部通过，受控原则及完整性基线未变化。
3. `python3 -m unittest discover -s tests`
   - 结果：通过；107 项测试全部通过，离线 demo 返回 `ACCEPTED`。
4. `python3 -m py_compile tokensaver/*.py tests/*.py examples/research_pipeline/*.py`
   - 结果：通过，退出码 0。
5. `git diff --check`
   - 结果：通过，退出码 0。
6. PyPI 版本唯一性检查
   - 结果：通过；查询 `tokensaver-agent` 项目元数据，0.8.0 尚不存在。
7. `python3 -m build --outdir /tmp/tokensaver-v080-dist.ov5kLI`
   - 沙箱内首次执行因隔离构建环境无法解析 PyPI、不能获取 `setuptools>=68` 而失败。
   - 按网络策略在授权联网环境重试成功，生成 `tokensaver_agent-0.8.0.tar.gz` 和 `tokensaver_agent-0.8.0-py3-none-any.whl`。
8. wheel metadata 与版本一致性
   - 结果：通过；wheel metadata 为 `Name: tokensaver-agent`、`Version: 0.8.0`。
   - `pyproject.toml`、`tokensaver/__init__.py`、`VERSION.md` 和 `CHANGELOG.md` 均包含 0.8.0 正式版本信息。
9. 全新临时虚拟环境安装本地 wheel
   - 结果：通过；使用 `--no-index` 成功安装 `tokensaver-agent-0.8.0`。
10. 安装后验证
    - `tokensaver version`：返回 `TokenSaver 0.8.0`。
    - `tokensaver doctor --offline`：命令成功并输出可复制 PATH 修复建议。
    - `tokensaver demo`：结果 `ACCEPTED`，生成 benchmark 和 panel。

结论：0.8.0 已满足本地提交和创建发布 PR 的前置条件。GitHub CI、合并、标签、Trusted Publishing 与 PyPI 安装结果必须在实际完成后另行追加记录，不得提前标记发布成功。

## TEST-20260622-002：TokenSaver 0.7 可信优化闭环

- 日期：2026-06-22
- 对应 PRD：`PRD-20260622-002-v0.7-trustworthy-optimization-loop.md`
- 环境：macOS，Python 3，本地临时目录，禁用运行时更新检查
- 总体结果：通过

执行结果：

1. `python3 -m unittest tests.test_v07_trustworthy_loop -v`
   - 结果：通过
   - 明细：运行 12 项 0.7 专项测试，全部通过。
   - 覆盖：token 去重计量、provider usage、工具语义字段、工具 schema 成本、schema 0.3 兼容、idle/broken health、请求消解、群组分位数、小样本保护和 CLI。
2. `python3 -m unittest tests.test_governance -v`
   - 结果：通过
   - 明细：运行 3 项治理测试，原则文档内容及 SHA-256 基线未变化。
3. `python3 -m unittest discover -s tests`
   - 结果：通过
   - 明细：运行 101 项测试，全部通过。测试套件按预期打印一次持久化失败模拟日志，不影响测试结果。
4. `python3 -m py_compile tokensaver/*.py tests/*.py`
   - 结果：通过，退出码 0。
5. 临时目录 CLI/API smoke
   - 结果：通过。
   - 明细：schema 0.4 record、host request 消解、pipeline broken、旧双 run compare、版本群组 compare 均通过。
6. `git diff --check`
   - 结果：通过，退出码 0。
7. 版本一致性检查
   - 结果：通过。
   - 明细：`pyproject.toml`、`tokensaver/__init__.py`、`VERSION.md` 和 `CHANGELOG.md` 均为 0.7.0。

结论：0.7.0 满足 PRD 验收与测试 SOP，可以标记开发成功。

## TEST-20260622-003：TokenSaver 0.7.0 发布前验证

- 日期：2026-06-22
- 对应 PRD：`PRD-20260622-003-v0.7-release.md`
- 环境：macOS，Python 3，本地隔离构建环境与临时虚拟环境
- 总体结果：通过

执行结果：

1. 0.7 专项测试：12 项全部通过。
2. 治理完整性测试：3 项全部通过，受控原则未变化。
3. 全量测试：101 项全部通过；预期的持久化失败模拟日志不影响结果。
4. Python 语法与 `git diff --check`：通过。
5. `python3 -m build --outdir /private/tmp/tokensaver-v070-dist`
   - 沙箱内首次执行因隔离构建环境无法访问 PyPI 而失败，按环境网络策略在授权网络环境重试。
   - 重试成功，生成 `tokensaver_agent-0.7.0.tar.gz` 和 `tokensaver_agent-0.7.0-py3-none-any.whl`。
6. 临时虚拟环境安装本地 wheel：通过。
7. 安装后 `tokensaver version`：返回 `TokenSaver 0.7.0`。
8. 安装后离线 demo：通过，结果 `ACCEPTED`。

9. PR #10 自动 CI：通过。
   - Python 3.10、3.11、3.12、3.13 全部成功。
   - benchmark workflow 成功。
   - CI run：`27957511219`；benchmark run：`27957511217`。
10. PR 合并：通过。
    - PR：`https://github.com/zhangtao-jayce/TokenSaver/pull/10`
    - merge commit：`d58842080a7acacbf025efb5eee42988d0bae45c`
11. GitHub Release 与标签：通过。
    - `https://github.com/zhangtao-jayce/TokenSaver/releases/tag/v0.7.0`
12. Trusted Publishing：通过。
    - workflow run：`27958029885`
    - build 和 `publish-pypi` 两项 job 均成功。
    - Actions 报告 Node.js 20 action runtime 弃用警告，但 runner 自动使用 Node.js 24，未影响发布。
13. 全新临时虚拟环境从 PyPI 精确安装：通过。
    - 下载 `tokensaver_agent-0.7.0-py3-none-any.whl`。
    - `tokensaver version` 返回 `TokenSaver 0.7.0`。
    - 安装后的离线 demo 返回 `ACCEPTED`。

结论：TokenSaver 0.7.0 已通过本地、GitHub CI、构建、Trusted Publishing 和 PyPI 安装全链路验证，发布成功。

## TEST-20260623-001：首次安装、Pipeline 与外部 Agent 交接体验

- 日期：2026-06-23
- 对应 PRD：`PRD-20260623-001-onboarding-pipeline-handoff.md`
- 环境：macOS，Python 3，仓库工作区，本地临时目录，运行时更新检查关闭
- 总体结果：通过

最终执行结果：

1. `python3 -m unittest tests.test_onboarding_pipeline_handoff -v`
   - 结果：通过。
   - 明细：运行 6 项专项测试，全部通过。
   - 覆盖：PATH shell 转义、自定义 task type 预算缺失与分类冲突拆分、显式预算不误报、SDK handoff、外部 trace 规范化、非法 handoff 状态、报告/brief/panel 展示及 model/token 隔离。
   - 非法状态用例按预期触发一次本地 integration failure 日志，不影响测试结果。
2. `python3 -m unittest tests.test_install tests.test_profile tests.test_runtime tests.test_panel tests.test_v06_production_health -v`
   - 结果：通过。
   - 明细：运行 65 项关键回归测试，全部通过。
   - 既有持久化失败模拟用例按预期打印一次失败日志，不影响测试结果。
3. `python3 -m unittest tests.test_governance -v`
   - 结果：通过。
   - 明细：运行 3 项治理测试，全部通过；受控原则正文及完整性基线未变化。
4. `python3 -m unittest discover -s tests`
   - 结果：通过。
   - 明细：运行 107 项测试，全部通过；离线 demo 返回 `ACCEPTED`。
5. `python3 -m py_compile tokensaver/*.py tests/*.py examples/research_pipeline/*.py`
   - 结果：通过，退出码 0。
6. 离线 research pipeline smoke
   - 最终命令：`TOKENSAVER_CHECK_UPDATE_ON_RUN=0 python3 -m examples.research_pipeline.research_pipeline --store-dir <tmp> --output-dir <tmp>`，随后校验 JSONL 和四类 artifact。
   - 结果：通过。
   - 明细：生成 `runs.jsonl`、report、brief、panel；handoff 数量为 1，model call 数量为 0。
7. 安装文案一致性检查
   - 命令：`rg -n "pip install|uvx tokensaver-agent|Python 3.10|development version|开发版" README.md docs/集成指南.md`
   - 结果：通过。
   - 明细：README 与集成指南均以 PyPI 为普通用户主路径，安装前显示 Python 3.10+，提供 uvx 路径，并将 GitHub 标为开发版路径。
8. `git diff --check`
   - 结果：通过，退出码 0。

测试过程中发现并处置的问题：

1. 首次 pipeline smoke 使用文件路径执行示例，Python 从环境中导入了已安装的 TokenSaver 0.7.0，而不是当前工作区代码，导致 `AgentRun` 暂无 `add_handoff`。
   - 处置：仓库示例改用 `python3 -m examples.research_pipeline.research_pipeline`，确保加载当前检出代码；重试通过。
2. 首次全量测试有 1 项失败：`STANDARD_RUN_FIELDS` 已新增 `handoffs`，旧 schema 合约断言未同步。
   - 处置：更新合约测试名称和预期字段；全量重跑 107 项全部通过。

结论：本次开发满足 PRD 测试 SOP，可以进入开发记录和最终验收。
