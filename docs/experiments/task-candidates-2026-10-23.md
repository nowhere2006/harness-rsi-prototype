# SWE-bench 首轮候选任务（2026-10-23）

本次只完成预算调整、验证和候选筛选。没有运行正式解题、生成预测或执行 grader。

使用官方 Verified/test 数据中的题面与 difficulty 字段。三题均标为 `15 min - 1 hour`，代表工程师修复耗时估计；DeepSeek 的实际难度和成功率未知。

首选 `scikit-learn__scikit-learn-26323`。以下适合度判断是根据题面作出的推断。

- **scikit-learn__scikit-learn-26323**（首选）：ColumnTransformer 的输出设置没有覆盖 remainder 中的估计器。复现输入小；需要检查复合组件的参数传递、输出类型及兼容性；适合观察定位、修改、测试全过程。
- **pytest-dev__pytest-7571**（备选）：caplog 在测试结束后未恢复日志等级。两个测试即可描述故障；涉及 fixture 生命周期和状态恢复，适合作为范围较小的首轮任务。
- **sympy__sympy-13031**（备选）：空维度矩阵的 hstack / vstack 拼接形状回归。预期输出明确；主要考察零行零列边界条件，题面易理解。

Verified 可用于熟悉任务、轨迹与评分链路。OpenAI 在 2026-02-23 的官方分析指出污染和测试缺陷，并停止报告该分数；此处不声称所选题未被 DeepSeek 训练数据覆盖，也不把少量手选任务当作研究效果结论。

后续用户已明确选择 Terminal-Bench **2.0**，准备环境按这个版本固定。此前发布页查询到的 v4.0.0 只属于历史背景，不作为本项目运行版本。Harbor 官方支持 mini-swe-agent 集成；实际迁移时仍应固定数据集、适配器与 Agent 版本并单独设置预算。

详细题面、基线 commit、数据集 fingerprint 与来源链接见 `artifacts/task-shortlist.json`。

官方来源：

- https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified
- https://openai.com/index/introducing-swe-bench-verified/
- https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- https://github.com/harbor-framework/terminal-bench/releases
- https://docs.harborframework.com/agents/pre-integrated-agents
