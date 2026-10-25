# 文档导览

这个仓库记录了一条完整的实验链：搭环境 → 跑基线 → 实现一个 RSI 方法 → 得到负结果并定位原因。

## 当前有效的内容

| 文档 | 内容 |
|---|---|
| [`../README.md`](../README.md) | 总览、复现命令、两臂结果 |
| [`setup.md`](setup.md) | Terminal-Bench 2.0 的 Harbor 搭建与资源语义 |
| [`experiments/rsi-options.md`](experiments/rsi-options.md) | 三条 RSI 路线的挂载点、成本与测量设计 |
| [`experiments/results/2026-10-24-tb4-baseline-fast-agent-subset.md`](experiments/results/2026-10-24-tb4-baseline-fast-agent-subset.md) | TB4 19 题基线（含失效分类） |
| [`experiments/results/2026-10-24-evo-harness-15tasks.md`](experiments/results/2026-10-24-evo-harness-15tasks.md) | Evo-Harness 首轮：14 组配对，10 → 6 |
| [`analysis/2026-10-24-why-evo-harness-failed.md`](analysis/2026-10-24-why-evo-harness-failed.md) | 上述负结果的根因分析 |
| [`analysis/2026-10-24-reflection-and-differences.md`](analysis/2026-10-24-reflection-and-differences.md) | 与论文的流程对比（两张流程图）、九项差异、No Propose 消融、四个可解释性发现、三个前提错配 |
| [`experiments/data/`](experiments/data/) | 逐题原始记录（JSONL）与两题冒烟轨迹 |

## 历史记录（已被后续工作取代）

| 文档 | 说明 |
|---|---|
| [`experiments/results/2026-10-23-swebench-sk26323.md`](experiments/results/2026-10-23-swebench-sk26323.md) | 最早的 SWE-bench 单题跑通记录 |
| [`experiments/results/2026-10-23-terminal-bench-fix-git.md`](experiments/results/2026-10-23-terminal-bench-fix-git.md) | TB2 单题链路验证 |
| [`experiments/archive/`](experiments/archive/) | SWE-bench 时代的选题与预算草稿 |

## 没进仓库的东西

任务数据集、Docker 镜像、完整轨迹、verifier 日志、虚拟环境、`outputs/`、`terminal-bench/runs/` 都不提交。
需要时用 README 里的命令重新生成。

## 关于 API key

早期运行的轨迹里曾出现明文 key（Agent 在容器内执行 `env` 打印了环境变量）。已从本地日志中清除，
并把这些目录加入 `.gitignore`；提交前也做过扫描。**key 仍需轮换**，因为它在其他渠道暴露过。
