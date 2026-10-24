# TB 4.0 fast-agent 子集基线（19 题，完整版）

## 协议

- 任务集：`terminal-bench/terminal-bench@4.0.0` 本地导出，fast-agent 选定的 19 题。
- Agent：Harbor `mini-swe-agent` adapter 子类（PyPI 2.4.6 + `mcp`），模型 `deepseek/deepseek-flash`，非思考模式。
- 预算：每题 150 步 / 5400 秒 / US$2、1 次尝试、0 重试；2 并发，内存闸门 12 GiB。
- 资源：按每题 `task.toml` 声明值由 Docker 强制；Docker VM 8 核 / 16 GiB。
- 记录：`outputs/tb4-baseline/records.jsonl`；首次无效尝试单独存档在 `records-invalid-attempt1.jsonl`。

## 结果：10/19 通过，其中 4 条记录不可计入

按退出原因重新分类（依据每题轨迹的 `info.exit_status`）：

| 分类 | 题数 | 说明 |
|---|---:|---|
| 通过（Submitted + reward 1.0） | 10 | 有效 |
| 真实失败（Submitted + reward 0.0） | 5 | 有效 |
| 预算截断（LimitsExceeded，150 次调用） | 3 | 结果未知，非能力结论 |
| 环境中断（Insufficient Balance，120 次调用） | 1 | 无效 |

有效样本 **15 题，通过 10 题（67%）**。被截断的 3 题是 `cad-model`、`vllm-deepseek-streaming`、`telecom-entity-resolution`，全部在恰好 150 次调用时停止；`hof-topology-interpenetration` 在第 120 次调用时因余额耗尽中断。

| 任务 | 类别 | reward | 费用 | 耗时 | 输入 token |
|---|---|---:|---:|---:|---:|
| html-js-filter | Security | 1.0 | $0.0687 | 848 s | 3.83M |
| photonic-waveguide-routing | Software | 1.0 | $0.3097 | 2795 s | 26.4M |
| vpp-loss-divergence | ML | 1.0 | $0.0814 | 821 s | 9.29M |
| mvcc-lsm-compaction | Software | 1.0 | $0.0180 | 561 s | 0.33M |
| sound-change-cascade | Science | 1.0 | $0.2236 | 1275 s | 27.5M |
| vba-userform-port | Software | 1.0 | $0.1315 | 1093 s | 13.1M |
| atrx-vep-crispr | Science | 1.0 | $0.1255 | 934 s | 8.23M |
| fin-saccr-rwa | Operations | 1.0 | $0.1559 | 1149 s | 18.1M |
| react-lead-form | Software | 1.0 | $0.0616 | 717 s | 3.46M |
| wal-recovery-ordering | Software | 1.0 | $0.0593 | 865 s | 3.05M |
| cad-model | Hardware | 0.0 | $0.2714 | 1844 s | 31.1M |
| vllm-deepseek-streaming | ML | 0.0 | $0.1625 | 1035 s | 23.4M |
| cargo-flight-dispatch | Operations | 0.0 | $0.0645 | 621 s | 2.73M |
| production-planning | Operations | 0.0 | $0.0873 | 849 s | 2.65M |
| gsea-proteomics | Science | 0.0 | $0.0351 | 491 s | 2.30M |
| hof-topology-interpenetration | Science | 0.0 | $0.1743 | 1818 s | 19.5M |
| session-window-debug | Software | 0.0 | $0.0363 | 412 s | 1.18M |
| satb-audio-transcription | Media | 0.0 | $0.2538 | 1859 s | 26.5M |
| telecom-entity-resolution | Software | 0.0 | $0.2713 | 2474 s | 37.5M |

合计：**US$2.59**，墙钟 **6.2 小时**（2 并发），镜像拉取 11 分钟。

分类：Security 1/1、Software 5/7、Science 2/4、Operations 1/3、ML 1/2、Hardware 0/1、Media 0/1。

## 观察

- 通过组平均 $0.124/题，未通过组平均 $0.151/题。失败题更贵，说明它们不是在早期放弃，而是**跑到很晚才失败**——这正是有提升空间的位置。
- 单题成本跨度 $0.018–0.31（17 倍），由步数和上下文长度决定，不是由题目难度线性决定。`mvcc-lsm-compaction` 9 分钟 $0.018 就过了，`cad-model` 31 分钟 $0.27 仍失败。
- 输入 token 最高 3,750 万（`telecom`），缓存命中率普遍 99% 以上，这是费用能被压住的原因。
- 3 题在恰好 150 次调用处被步数上限截断，说明这个预算对最难的几题仍然偏紧；要判断它们真实能力，需要单独提高预算重跑。

## 有效性

首次运行的 5 条无效记录（3 次余额不足、2 次 `deb.debian.org` 不可达）已重跑，但重跑后仍有 4 条不可用：3 题被 150 步上限截断、1 题再次因余额耗尽中断。因此本轮不是 19 条完整基线，而是 **15 条有效 + 3 条截断 + 1 条中断**。之前的版本写成"19 条全部有效"是错的，已在核对轨迹退出状态后修正。

## 解释边界

- 有效样本的 67%（15 题）仍不能与公开的 33.8%（Artificial Analysis 用 mini-swe-agent 跑全 66 题）直接比较：任务集不同（这是 fast-agent 子集）、预算更紧（150 步 / 90 分钟 vs 官方 8 小时）、只跑 1 次而非 3 次。
- 每题只有 1 次尝试，无法区分"模型不会"与"这次没做出来"。单题结论不可靠，只有子集层面的比例有参考价值。
- 耗时是 2 并发下测的，与单跑不可比。

## 下一步：RSI 实验集

按"有没有提升空间"分三层：

| 层 | 任务 | 用途 |
|---|---|---|
| 临界通过 | photonic-waveguide-routing、sound-change-cascade、fin-saccr-rwa、vba-userform-port、atrx-vep-crispr | 慢但能过，改进应体现为更少步数/费用 |
| 高分失败 | cad-model、hof-topology-interpenetration、satb-audio-transcription、telecom-entity-resolution、vllm-deepseek-streaming | 跑很久仍失败，RSI 机制最该起作用 |
| 天花板对照 | mvcc-lsm-compaction、html-js-filter、vpp-loss-divergence | 本来就快，用来检查方法没有引入回归 |

统计功效的现实：19 题各 1 次只能做筛选。检测 +10 个点需要每组约 350 次运行；即使 8 题 × 3 次重复（24 次/组）也只能抓住 20 个点以上的大效应。下一阶段应先定 RSI 机制，再用小规模重复做方向性筛选，最终结论需要更大样本或云上全量。
