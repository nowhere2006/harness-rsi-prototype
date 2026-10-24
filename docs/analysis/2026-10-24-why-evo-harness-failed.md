# 为什么第一版 Evo-Harness 会失败

对 `docs/experiments/results/2026-10-24-evo-harness-15tasks.md` 中 14 组配对结果的根因分析。

## 结论

这一版实现不是"效果不显著"，而是**只往坏的方向偏**：

| | 基线 | Evo |
|---|---:|---:|
| 有效配对 | 14 | 14 |
| 通过 | 10 | 6 |
| 翻盘 | — | **0** |
| 退步 | — | **4** |

基线通过的 10 题里丢掉了 4 题，基线失败的 4 题一题也没救回来。

## 四层原因

### 1. 反思产出的是"这次为什么错"，不是"下次该怎么做"

最终的 harness 内容是这样：

```
## From production-planning
TRIGGER: When writing DB-gateway SQL for planning/orders with freeze windows.
ACTION: Compute freeze_hours explicitly from horizon_start to horizon_end ...
WHY: test_freeze_h FAILED while run_id and dispatch_freeze passed
```

```
## From vba-userform-port
TRIGGER: Building a FastAPI backend with pinned requirements.txt for a verifier.
ACTION: Pin versions known to resolve together (e.g. constrain pydantic<2.10) ...
WHY: Verifier log shows a long dependency-resolution crawl (pydantic 2.14.1)
```

这些是对**某一次失败的具体诊断**：某个字段算错、某个依赖拉取太慢。对当前题有用，对下一题几乎为零——下一题既没有 `freeze_hours` 字段，也不用 FastAPI。

根子在于反思 prompt 只写了"对未来这类任务有帮助"，却没有给出"这类任务"的定义。模型只看得到一道题的失败轨迹，最合理的推断就是解释这次为什么错。**它产出的是调试日志，不是技能。**

### 2. 无条件全局注入

harness 从 765 字符涨到 3975 字符，每次都整段注入下一题。于是：

- `wal-recovery-ordering`（WAL 顺序恢复）拿到"用 `html.parser` 过滤 XSS"和"审查 MVCC 的 GC 逻辑"
- `vba-userform-port`（VBA 界面移植）拿到同一批数据库/HTML 经验

对无关任务来说这不是"没帮助"，而是**主动干扰**：占上下文、暗示错误的工具选择、甚至与任务要求冲突。四次退步中三次发生在 harness 已积累 1.5K–3.2K 字符之后；只有 `html-js-filter` 是在 harness 为空时退步的，那属于纯方差。

### 3. 注入位置把"建议"变成了"要求"

harness 被拼在**任务说明**末尾（`--extra-instruction-path`）。模型读到的结构是"任务：…… 然后 ACTION: 用 html.parser"——这会把这些当成任务的额外约束，而不是背景知识。论文里 harness 是 Agent 的运行时状态（system 层），不是题面的一部分。

### 4. 淘汰策略污染了实验

超过 4000 字符时丢弃**最旧的段落**，这个规则与"有没有用"无关。结果：

- 同一道题在不同时刻看到的 harness 是不同版本
- 可能有用的一般性经验（例如"复现工具精确版本与默认参数"）被更早的无用条目挤掉

这叫**处理不一致**：变量在任务流中间变了，前后不可比。

## 两个放大因素

**n=1 的方差。** `html-js-filter` 在 harness 完全为空、配置与基线一致的情况下也翻转了。单次尝试的噪声足以改变一道题的结果。严格的统计结论需要每题 3 次以上重复。

**任务顺序按专家耗时而非类别。** 15 题横跨 HTML 安全 → ML → 数据库 → VBA → 生物信息 → 运营。跨域迁移是技能复用里最难的情形，而论文采用 topic 级适配，把同类任务放在一起，让 topic skill 有机会生效。

## 一句话根因

> 把"失败反思"直接当成了"技能编译"，缺少 **scope（经验属于哪类任务）、selection（只注入相关的）、placement（放 system 层而非题面）** 三个必要环节。

论文的 Evo-Harness 恰恰把这三件事拆成独立组件（general skill / topic skill / harness 更新器）。这一版把它们全省了，退化成"全局追加反射日志"。

还有数据层面的不匹配：论文在 TerminalBench2 上验证，那里的失败多是"流程没走对"，反思能提炼可复用的操作序列；TB4 的失败更多是"这个任务独有的 bug 没找到"，反思只能产出实例级诊断。**方法假设与任务特性不匹配**，这一点在选 benchmark 时就该预判。

## 修复优先级

1. **加 scope 字段**，按 `task.toml` 的 category 过滤注入（Software 只读 Software）
2. **改注入位置**：system prompt，而不是任务说明
3. **按 scope 分桶、去重、按有用性淘汰**，而不是丢最旧
4. **加接受门槛**：新经验先在 1–2 道留出题上验证有效再写入 harness（GEPA 的 minibatch 验收思路）
5. **每题 3 次重复**，配对比较，把方差和效应分开

前两步各几十行，改完值得重跑同一组 15 题。在那之前，只能说"这一版实现无效"，不能说"Evo-Harness 在 TB4 上无效"。
