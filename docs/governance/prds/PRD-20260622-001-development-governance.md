# 小 PRD：建立 TokenSaver 开发治理基线

- 状态：已完成
- 日期：2026-06-22
- 需求来源：项目所有者张涛在当前会话中的直接要求
- 类型：小型流程与文档变更

## 问题与目标

当前仓库没有强制的 PRD、测试 SOP、测试记录和开发记录流程，也没有限制开发原则被随意修改。目标是建立可被后续开发代理发现、执行和自动审计的治理基线。

## 范围

- 建立受控开发原则文档。
- 建立 PRD、测试记录和开发记录规范及目录。
- 增加仓库级代理指令。
- 增加原则文档完整性自动测试。
- 记录本次变更及真实测试结果。

## 非范围

- 不修改 TokenSaver 产品运行逻辑。
- 不启动 0.7 产品功能开发。
- 不建立依赖特定托管平台权限的审批系统。

## 方案

以 `DEVELOPMENT_PRINCIPLES.md` 作为唯一受控原则正文；`AGENTS.md` 强制后续代理优先读取；以自动化测试固定原则文档 SHA-256，形成明显且可测试的变更门槛。流程说明和两份追加式日志承载操作细节与审计证据。

## 文件影响

- `AGENTS.md`
- `docs/governance/DEVELOPMENT_PRINCIPLES.md`
- `docs/governance/README.md`
- `docs/governance/prds/PRD-20260622-001-development-governance.md`
- `docs/governance/DEVELOPMENT_LOG.md`
- `docs/governance/TEST_LOG.md`
- `tests/test_governance.py`

## 风险与兼容性

- 流程增加开发前后记录成本，但这是明确要求的审计成本。
- 哈希测试不能替代代码托管权限，不过能防止原则文件被无意修改或静默漂移。
- 仅新增文档和测试，不影响现有公开 API 与 trace schema。

## 验收标准

- 三项开发原则被完整、明确记录。
- 原则变更必须具备所有者专项授权和严格流程。
- 后续代理能从仓库根目录发现强制流程。
- 自动化测试能检测原则文档变化或治理文件缺失。
- 本次测试记录和开发记录均已追加。

## 测试 SOP

1. 运行 `python3 -m unittest tests.test_governance -v`，验证治理文件、关键规则及原则文档哈希。
2. 运行 `python3 -m unittest discover -s tests`，验证新增测试与现有项目测试兼容。
3. 运行 `python3 -m py_compile tokensaver/*.py tests/*.py`，验证 Python 文件语法。
4. 检查 `git diff --check`，验证补丁不存在空白错误。
