# RSI 机制选型备忘（基于 19 题基线）

## 一个决定实现方式的硬约束

Harbor 在每个任务容器里用 `uv tool install mini-swe-agent==2.4.6` 装 Agent，**不引用本地源码**。所以任何 RSI 改动都进不去，除非走下面两条路之一：

1. **`agent_class` 注入**（推荐）：mini 的 `get_agent_class()` 接受任意 dotted path（`agents/__init__.py:14`），我们的 Harbor adapter 已经会往容器里写配置文件，同一个机制可以多写一个 Python 模块 + 设 `PYTHONPATH` + 在 `-c` 里指定 `agent.agent_class=rsi_agent.XxxAgent`。
2. **打包 wheel**：把改过的源码打成 wheel，adapter 改成 `uv tool install <wheel>`。改动更彻底，但每次迭代都要重建镜像。

路径 1 的代价是只能在 `DefaultAgent` 之上覆写方法；这对下面三种机制都够用。

## 第二个约束：Agent 看不到官方评分

TB4 的 verifier 是**独立容器**、在 Agent 结束后才跑。Agent 在轨迹里拿不到 `FAIL_TO_PASS`/`PASS_TO_PASS` 这种官方信号。

这意味着"自我改进"的反馈只能来自 Agent 自己能观测到的东西：它自己跑的测试、命令退出码、diff 是否应用成功、以及自洽性检查。任何依赖官方 reward 回灌的设计在这个 benchmark 上做不到。

## 三种机制

### A. 单轨迹内反思重试（intra-episode）

| | |
|---|---|
| 挂载点 | 覆写 `step()`（`agents/default.py:126`）或 `run()`（`:88`） |
| 机制 | 连续 k 步无文件变更 / 同一命令重复失败 → 注入"你刚才做了什么、为什么失败、换个策略"的提示；或在 `LimitsExceeded` 前触发一次「总结 + 重开」 |
| 需要改动 | 一个 `ReflectiveAgent(DefaultAgent)`，约 100–150 行 |
| 反馈信号 | 自跑测试、退出码、diff 是否产生 |
| 预期作用面 | 高分失败题（cad、hof、satb、telecom），它们跑到很晚才失败，说明有搜索但没收敛 |
| 风险 | 反思提示会增加上下文，单题费用可能涨 20–50%；对小任务可能变差 |
| 实现成本 | 低（无跨任务状态，复用现有 runner） |

### B. 跨任务记忆（inter-task memory）

| | |
|---|---|
| 挂载点 | adapter 启动时写 `memory.json` 进容器 + 在 system prompt 追加检索到的条目；任务结束回写 |
| 机制 | 把"某类任务的有效策略/踩过的坑"沉淀成条目，按类别检索注入 |
| 需要改动 | adapter 侧文件注入（约 60 行）+ 一个 `MemoryAgent`（检索/写回，约 150 行）+ 固定的任务执行顺序 |
| 反馈信号 | 自跑测试 + 任务完成后的自评 |
| 预期作用面 | 同类别连续任务（Software 7 题、Operations 3 题）；对孤立任务无效 |
| 风险 | 记忆污染会让后续任务变差；顺序敏感，需要按类别排序跑 |
| 实现成本 | 中（要改 Harbor adapter 与 runner 的调度） |

### C. 上下文内自训练（in-context self-training）

| | |
|---|---|
| 挂载点 | 离线：用已有轨迹蒸馏成 skill 清单；在线：同 B 的注入路径 |
| 机制 | 把成功轨迹/失败教训压缩成可复用技能条目，作为 system prompt 的一部分 |
| 需要改动 | 蒸馏脚本（离线，不占 API 预算可离线跑）+ B 的注入路径 |
| 预期作用面 | 全局，但效果依赖蒸馏质量 |
| 风险 | 本质是"手写 prompt 工程"的自动化版本，容易变成过拟合开发集 |
| 实现成本 | 中高（多一个离线环节） |

## 推荐顺序

**先 A，再 B。** 理由：

- A 不需要跨任务状态，可以先在 5 道高分失败题上做**单变量对照**：同一任务、同一预算、开/关反思，比较 resolved、步数、费用。
- A 的负结果也有信息量：如果反思对"跑到很晚才失败"的题都没用，说明瓶颈不在策略搜索，而在模型能力或任务信息不足，那 B/C 的收益也会有限。
- B 依赖 A 先证明"Agent 能从自身信号里学到东西"，否则记忆里存什么都是猜。

## 测量设计（无论选哪个）

- **配对设计**：同一题、同一预算，baseline 与 RSI 各跑 3 次，比较 resolved 率与单题费用。
- **主指标**：resolved（二分类）+ 达到目标所需步数/费用（连续量，功效更高）。
- **样本量现实**：19 题各 1 次只能筛选；3 次重复后每组 24–57 次运行，只能抓 20 个点以上的效应。想验证 10 个点需要约 350 次/组。
- **防回归**：必须带 3 道天花板题（mvcc、html-js-filter、vpp），确认改动没把本来能过的题弄坏。

## 待定

选 A / B / C 中的一个先做，或者告诉我你更倾向的机制形态（例如"反思但不重试"、"只记忆失败模式"），我据此把 `ReflectiveAgent` 的实现和 5 题对照实验配好。

## 注入路径验证（2026-10-24）

在控制容器内实测：把一个 `ReflectiveAgent(DefaultAgent)` 放到 `PYTHONPATH` 下，调用
`get_agent_class("rsi_agent.ReflectiveAgent")` 能正确加载，MRO 显示父类为
`DefaultAgent`。说明 config 里的 `agent.agent_class` 这条路可用。

剩余未验证的一环：任务容器里 mini 是 `uv tool install` 装出来的，模块需要放进该
工具环境的 site-packages（或给 mini 进程设 `PYTHONPATH`）。这属于打包细节，实现时
在 adapter 的 `install()` 里补一步即可，不需要改 Harbor。
