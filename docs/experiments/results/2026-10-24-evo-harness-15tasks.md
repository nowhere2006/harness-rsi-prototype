# Evo-Harness 首轮实现：15 题顺序实验（负结果）

对照的是同一天、同预算的 TB4 fast-agent 子集基线。结论先说：**这一版实现让通过数从 10 降到 6，没有任何一题翻盘。**

## 实现

- 顺序跑 15 题（外部顺序固定，按专家耗时升序）。
- 每题把当前 `harness.md` 通过 Harbor 的 `--extra-instruction-path` 追加到任务说明后面。
- 任务失败后，把 verifier 输出 + 最后 8 条命令交给反思模型，产出至多 2 条 `TRIGGER / ACTION / WHY`，追加进 harness。
- harness 上限 4000 字符，超出时丢弃最旧的段落。
- 反思调用：`deepseek-flash`、关闭思考模式、最多 800 token。
- 运行预算与基线完全一致：150 步 / 90 分钟 / US$2、一次尝试。

## 结果

| 任务 | 基线 | Evo | 进入时的 harness |
|---|---:|---:|---:|
| photonic-waveguide-routing | 1 | 1 | 0 |
| html-js-filter | 1 | **0** | 0 |
| vpp-loss-divergence | 1 | 1 | 765 |
| cargo-flight-dispatch | 0 | 0 | 765 |
| mvcc-lsm-compaction | 1 | **0** | 1576 |
| production-planning | 0 | 0 | 2356 |
| sound-change-cascade | 1 | 1 | 3164 |
| gsea-proteomics | 0 | 0 | 3164 |
| vba-userform-port | 1 | **0** | 3249 |
| react-lead-form | 1 | 1 | 3248 |
| wal-recovery-ordering | 1 | **0** | 3248 |
| atrx-vep-crispr | 1 | 1 | 3259 |
| fin-saccr-rwa | 1 | 1 | 3259 |
| satb-audio-transcription | 0 | 0 | 3259 |
| session-window-debug | 0 | 无效 | 3975 |

**14 组有效对照：基线 10 题通过，Evo 6 题通过；翻盘 0 题，退步 4 题。** 本臂花费 US$1.73。

`session-window-debug` 因 `deb.debian.org` 仓库签名错误在 Agent 安装阶段失败，没有产生模型调用，已排除。

## 诊断

**1. 至少一次退步是纯噪声。** `html-js-filter` 在 harness 为空（0 字符）时也退步了——配置、预算、harness 都与基线一致，结果却相反。这说明单次尝试的方差足以翻转一道题，n=1 的对照不能当结论。

**2. 剩下的三次退步都发生在 harness 已经开始内容之后**（1576 / 3249 / 3248 字符），且内容与当前任务无关：

- 给 `wal-recovery-ordering`（WAL 顺序恢复）注入的却是"用 `html.parser` 过滤 XSS"和"审查 MVCC 的 GC 逻辑"
- 给 `vba-userform-port`（VBA 界面移植）注入的也是同一批数据库/HTML 经验

**3. 注入位置放错了。** harness 被追加到任务说明末尾，读起来像"额外要求"，而不是背景知识。模型会把无关的技能条目当成任务约束。

**4. 没有分域、没有去重、没有稳定版本。** 论文里的 harness 分为 general 和 topic 两类，只注入与当前任务相关的部分；我的实现在全局累积、超过 4000 字符就丢最旧的段落，导致同一题在不同时刻看到的 harness 是不同版本。

## 与原论文的差距

Evo-Harness 的核心是 **context-to-harness skill compilation**：把单次执行编译成可复用的技能，并按 general / topic 分层，只让相关条目影响后续任务。我这一版只做了"失败 → 写一条经验 → 全量注入"，缺了分域与筛选这一步，所以效果从"迁移"退化成"干扰"。

## 如果要继续修

1. 按 `task.toml` 的 category 分域，只注入同域条目（Software 只读 Software）
2. 把 harness 注入到 system prompt，而不是任务说明
3. 去重 + 每条经验带 `scope` 字段，检索时按 scope 过滤
4. 每题至少 3 次重复，用配对比较把方差和效应分开
5. 用一个明确的后置任务集评估，不要在训练流上评估

## 边界

单次尝试、单一顺序、单一模型（`deepseek-flash` 非思考模式）、15 题子集。这不是对 Evo-Harness 方法的否证，只说明这一版实现无效，并定位了原因。
