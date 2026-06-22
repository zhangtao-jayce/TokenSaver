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
