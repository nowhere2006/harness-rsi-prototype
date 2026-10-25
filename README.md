# Harness RSI 本地实验环境

> 2026-10-24 状态：评测管线可用（Harbor + mini-swe-agent + Terminal-Bench 4.0），Evo-Harness 首版已实现并跑完 15 题，结果为负（10 → 6）。失败原因已定位到论文的三个前提，见下方日志与反思。论文的 evolver、结构化 skill 与 top-b selection 未实现。

本仓库记录一条完整的实验链：搭环境 → 跑基线 → 实现一个自改进方法 → 得到负结果并定位原因。部署、链路跑通、基线可信、论文复现是四个不同的证据层级，本仓库目前停在第三层，并对第四层的差距做了具体分析。

## 实验日志

| 日期 | 做了什么 | 结果 | 记录 |
|---|---|---|---|
| 10-23 | 部署 mini-swe-agent + Docker + SWE-bench | 单题 resolved，189 个测试通过 | [报告](docs/experiments/results/2026-10-23-swebench-sk26323.md) |
| 10-23 | Terminal-Bench 2.0 链路验证 | `fix-git` reward 1.0 | [报告](docs/experiments/results/2026-10-23-terminal-bench-fix-git.md) |
| 10-24 | TB4 fast-agent 子集 19 题基线 | 15 题有效，10 题通过（67%） | [报告](docs/experiments/results/2026-10-24-tb4-baseline-fast-agent-subset.md) |
| 10-24 | Evo-Harness 首版实现 + 15 题顺序实验 | **10 → 6，0 翻盘 4 退步** | [报告](docs/experiments/results/2026-10-24-evo-harness-15tasks.md) |
| 10-24 | 根因分析 + 与论文逐项对比 | 三个前提不满足，非实现 bug | [分析](docs/analysis/2026-10-24-why-evo-harness-failed.md) · [对比](docs/analysis/2026-10-24-reflection-and-differences.md) |

一句话结论：**管线可用，基线干净；方法首版无效，原因是批级更新、solver 能力、任务类型三个前提同时不满足。**

## 反思：和论文差在哪

这一版实现不是论文的复现，而是它最小骨架的一次实现。差别集中在三个结构性组件：

- **缺 scope**：没有"经验属于哪类任务"的标注，所以选择性注入做不到，跨域经验变成了干扰
- **缺验收**：失败就写入，没有"这条经验是否真的有用"的门槛
- **缺可分离的评估**：每题 1 次，方差足以翻转结果

另一层原因是 benchmark 错配：论文在 TerminalBench2 上验证（短任务、流程类失败多），我们在 TB4 上跑（长程任务、实例级 bug 多），反思能提炼的东西天然不同。TB2 和 TB4 的任务集、超时（30 分钟 vs 8 小时）、验证方式（同容器 vs 独立 verifier）都不同，分数不可比。

完整对比（含两张流程图、九项逐项差异、No Propose 消融、四个可解释性发现、改进优先级）：[反思与流程对比](docs/analysis/2026-10-24-reflection-and-differences.md)。

## 仓库导览

- 结论与两臂对比：本文件
- 全部文档索引：[docs/README.md](docs/README.md)
- 负结果根因：[为什么第一版 Evo-Harness 会失败](docs/analysis/2026-10-24-why-evo-harness-failed.md)
- 与论文的差异：[反思与流程对比](docs/analysis/2026-10-24-reflection-and-differences.md)
- 逐题原始记录：`docs/experiments/data/`

## 当前结构

- `mini-swe-agent/`：官方源码独立 Git 仓库，以可编辑方式安装到容器；部署配置放在外层，便于保持上游基线。
- `Dockerfile`、`compose.yaml`：Python 3.11 控制容器及 Docker CLI；包含 SWE-bench 5.0.2。
- `requirements.lock`：已安装并验证的 120 个 Python 依赖版本；Dockerfile 同时固定基础镜像摘要。
- `configs/local-swebench.yaml`：与上游 `swebench.yaml` 合并的本机覆盖配置。
- `.env`：仅本机保存的 API key，权限 600，不进镜像、不进入版本控制。`.env.example` 不含密钥。
- `outputs/`：轨迹、补丁、验证报告；`.cache/`：Hugging Face 等缓存。
- `artifacts/`：安装快照、镜像与版本信息、部署验收记录。

## 日常命令

在本目录打开终端：

```bash
./scripts/lab status
./scripts/lab up
./scripts/lab smoke        # 确定性流程验证，不调用 API
./scripts/lab live-smoke   # DeepSeek 修复小样例，会产生少量 API 费用
./scripts/lab verify-task  # 检查一个官方任务镜像，不调用模型或 grader
./scripts/lab shell
./scripts/lab down
```

修改上游 Python 文件后，可编辑安装会直接生效。新增依赖或变更 Dockerfile 后使用 `./scripts/lab build` 重建。

## 资源与架构

本次机器：Apple M4、24 GiB 内存、10 核。Docker VM 配置为 6 核、12 GiB；控制容器上限 2 核、3 GiB；每个任务上限 2 核、6 GiB，单并发。任务容器按需创建、结束删除，控制容器保持运行以便调试。

控制容器使用 ARM64 原生 Python。mini-swe-agent 的默认 SWE-bench 任务镜像为 x86_64，本地覆盖配置显式指定 `linux/amd64`。这依赖 Docker 的跨架构执行能力，不能据此推断所有任务兼容或得到与 x86 服务器完全一致的耗时。

本机已启动并验证官方 `sympy__sympy-20590` 任务镜像：x86_64、Python 3.9.20、SymPy 1.7.1，可执行符号运算。数据集基线为 `cffd4e0f86fefd4802349a9f9b19ed70934ea354`；镜像 HEAD 是附加的 `SWE-bench` 准备提交 `5efaed257c694e4452b4c8361aae1cd9cdefd6d1`。直接比较提交中的源码 blob，确认内容相同，差异仅为 1758 个文件从 100644 到 100755 的权限变化；工作树干净。完整记录在 `artifacts/swebench-task-environment.json`。此验证没有生成该题补丁或执行官方评分。

控制容器通过宿主 Docker socket 管理任务容器，适用于这台机器上的可信单用户开发。它具备 Docker 管理权限；任务容器本身不挂载该 socket，也不接收模型 API key。这里的容器划分用于环境复现和任务执行，不构成针对控制程序的宿主安全边界。

开始部署时宿主机约有 53 GiB 空闲磁盘，低于 SWE-bench 对完整本地评测建议的 120 GB。单个镜像的大小随仓库变化；本环境先按单实例使用，启动前要求至少 20 GiB 余量，此检查并不保证整个运行期间不会耗尽空间。不自动清理其他 Docker 项目的容器、镜像、卷或缓存。

## DeepSeek 接入与费用

请求使用 `https://api.deepseek.com`、`deepseek-flash`，LiteLLM 侧名称为 `deepseek/deepseek-flash`。当前官方说明该别名由 DeepSeek-V4.1-Flash-1017 提供，服务端可能更新，研究运行应保存响应中的模型标识和时间。

当前配置使用非思考模式验证工具调用链；这只是部署起点，不代表某篇论文的模型或推理设置。开始正式对照实验前，应固定模型、思考模式、token 限制、任务划分和预算。

本地价格注册表采用 2026-10-23 官方美元峰值价，输入 cache miss $0.30 / 百万 tokens、cache hit $0.006 / 百万 tokens、输出 $1.20 / 百万 tokens。因此报告中的金额是峰值价估算，不能替代 DeepSeek 账单。每实例配置 100 步、约 $1 估算费用和 45 分钟上限，任务容器保留 60 分钟以留出余量；费用与时间上限在请求之间检查，正在进行的请求仍可能超出。外层每进程调用限制为 110 次、费用限制为 $1；这不是跨进程或账户级的累计预算。单任务入口保持 1 个 worker，每次独立运行算一次尝试；当前没有自动从头重跑机制。基础 live smoke 更小：8 步、约 $0.10、5 分钟。

2026-10-23 的真实接入验证通过：DeepSeek Flash 在独立任务容器中修复 `add(a,b)` 的故障样例，保持测试文件不变，使测试从失败变为通过，并导出补丁；3 次模型调用、峰值价估算 $0.00022122。记录位于 `outputs/deepseek-smoke/report.json`、`trajectory.json` 和 `patch.diff`。这是部署验证，不是 SWE-bench 解题成绩。

## 单个 SWE-bench 任务

2026-10-23 已应用 100 步、US$1 估算阈值、45 分钟预算，容器内有效值见 `artifacts/budget-validation.json`。首轮候选与筛选边界见 [任务候选说明](docs/experiments/archive/2026-10-23-swebench-task-candidates.md)；首选为 `scikit-learn__scikit-learn-26323`。

用户随后授权的首轮正式运行现已完成：`scikit-learn__scikit-learn-26323` 单次尝试通过官方评分，189 个相关测试全部通过。结果见 [实验结果记录](docs/experiments/results/2026-10-23-swebench-sk26323.md)（完整报告与轨迹在本地 `outputs/`，不提交）。这是一道选定任务的结果，不是整套 benchmark 成绩。

生成补丁示例（调用 API、下载对应任务镜像）：

```bash
./scripts/lab swebench-one sympy__sympy-20590 baseline-sympy-20590
```

这会使用 Verified/test 子集、精确 instance ID、1 个 worker，保存 `outputs/baseline-sympy-20590/preds.json` 和该实例轨迹。`preds.json` 中有补丁、Agent 主动提交都不等于测试通过；需要另外运行 SWE-bench evaluator，才能报告 resolved。

SWE-bench 5.x 使用任务仓库定义评测。在本机 ARM 上运行官方评测还需要配置 `swe-bench-tasks` 和本地 Buildx；整批构建可能超过当前磁盘容量。先在容器内查看实际安装版本的参数：

```bash
docker compose exec agent swebench --help
docker compose exec agent swebench eval --help
```

为后续论文复现，先保留原版 mini-swe-agent baseline，再在实验分支加入论文方法，并使用相同任务、模型和预算比较 resolved、费用和耗时。当前 SWE-bench 路径本身只验证部署；Evo-Harness 最小原型（仅失败反思 + 注入）见 `scripts/evo-harness`，evolver 与结构化 skill 未实现。

## Terminal-Bench 4.0 baseline

Harbor 0.24.0 驱动 `terminal-bench/terminal-bench@4.0.0`（66 题，每题独立 verifier 容器，官方超时 8 小时）。任务文件导出在 `terminal-bench/datasets-tb4/`，运行入口是 `scripts/terminal-lab`（自定义 adapter 子类补齐 `mcp` 依赖）。

2026-10-23 夜完成 fast-agent 选定的 19 题基线：**10 题通过，5 题真实失败，3 题在 150 步上限处被截断，1 题因余额耗尽中断**（有效样本 15 题中通过 10 题）。US$2.59，6.2 小时（2 并发）。预算为每题 150 步 / 90 分钟 / US$2、一次尝试、不重试；Docker VM 8 核 / 16 GiB，任务资源按各题 `task.toml` 声明值由 Docker 强制。

```bash
TB_DATASET="$PWD/terminal-bench/datasets-tb4/terminal-bench" \
TB_STEP_LIMIT=150 TB_WALL_SECONDS=5400 TB_COST_LIMIT=2.0 \
scripts/tb4-baseline            # 断点续跑，已记录的题自动跳过
scripts/tb4-summarize           # 逐题与分类汇总
```

结果与边界：[基线报告](docs/experiments/results/2026-10-24-tb4-baseline-fast-agent-subset.md)；可复现信息（版本、预算、逐题 task 文件哈希、job ID）：`artifacts/tb4-baseline-provenance.json`。有效样本的 67% 同样不能与公开的 33.8% 比较——任务集、预算（150 步 / 90 分钟 vs 官方 8 小时）、重复次数都不同。

RSI 机制的三条候选路线、实现挂载点与测量设计见 [机制选型备忘](docs/experiments/rsi-options.md)。

## Evo-Harness 原型（负结果）

按论文的"单次执行 → 技能编译 → 在线累积"思路实现了一个最小原型：每题失败后把 verifier 输出交给反思模型，产出 `TRIGGER / ACTION / WHY` 条目，追加进 harness，下一题通过 `--extra-instruction-path` 注入。

```bash
scripts/evo-harness              # 顺序跑 15 题（结果写入 outputs/evo-harness/）
scripts/compare-arms             # 与基线配对比较
```

**结果：14 组有效对照，基线通过 10 题、本方法通过 6 题，翻盘 0 题、退步 4 题。** 其中 `html-js-filter` 在 harness 为空时也退步，说明单次尝试的方差本身就足以翻转结果；其余退步都发生在 harness 已累积内容之后，而注入的经验与当前任务无关（例如给 WAL 恢复题注入 HTML 过滤经验）。

诊断：缺少论文里的 general / topic 分域与筛选，把"迁移"做成了"干扰"；注入位置在任务说明而非 system prompt。详见 [Evo-Harness 首轮实验](docs/experiments/results/2026-10-24-evo-harness-15tasks.md) 与 [根因分析](docs/analysis/2026-10-24-why-evo-harness-failed.md)。

## 官方来源

- [mini-swe-agent 源码安装](https://mini-swe-agent.com/latest/quickstart/)
- [mini-swe-agent SWE-bench 推理与评测](https://mini-swe-agent.com/latest/usage/swebench/)
- [SWE-bench 官方仓库与 ARM 说明](https://github.com/swe-bench/SWE-bench)
- [SWE-bench Docker 资源要求](https://www.swebench.com/SWE-bench/guides/docker_setup/)
- [DeepSeek 模型与价格](https://api-docs.deepseek.com/quick_start/pricing/)
- [DeepSeek 思考模式与工具调用](https://api-docs.deepseek.com/guides/thinking_mode/)
