# Terminal-Bench 2.0 首次单题结果

任务 `fix-git`，一次尝试，官方 verifier `reward = 1.0`，2 个测试全部通过。目的是把 Terminal-Bench 链路跑通，不是测能力。

## 固定设置

- 任务集：`terminal-bench@2.0` 的本地导出（89 任务），registry 指向
  `laude-institute/terminal-bench-2` commit `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`；
  单题文件 SHA-256 记录在 `artifacts/tb20-fix-git-run.json`。
- 任务声明资源：1 CPU / 2G 内存 / 10G 存储，由 Docker 在任务容器上强制
  （实测 `NanoCpus=1000000000`、`Memory=2147483648`）。
- Agent：Harbor adapter 子类 `MiniSweAgentWithMcp`，任务容器内安装 PyPI
  `mini-swe-agent==2.4.6`；模型 `deepseek/deepseek-flash`。
- 预算：1 次尝试、0 重试、1 并发、`cost_limit=1.0`、100 步、45 分钟。
- 镜像：`alexgshaw/fix-git:20251031`，linux/amd64，在 arm64 上以仿真执行。

## 结果

- reward 1.0，`test_about_file`、`test_layout_file` 通过，无异常。
- 11 次模型调用，输入 98,199 token（缓存命中 87,168），输出 4,966 token。
- 客户端估算 US$0.0049；总墙钟 166.8 s，其中 agent 执行 43.7 s、验证 10.8 s。

## 过程中修掉的两个阻塞

1. LiteLLM 在任务容器内缺 `mcp`，每次模型调用都抛
   `ModuleNotFoundError` 并重试到超时。用本地 adapter 子类补一次
   `uv tool install ... --with mcp` 解决；上游 adapter 与本地
   `mini-swe-agent/` 源码都没改。
2. 本机直连 Docker Hub 超时，改用镜像站拉取后 retag 成官方镜像名。

## 解释边界

- 一道 easy 题、一次尝试，不能代表 benchmark 表现，也不能与榜单数字比较。
- Agent 来自 PyPI，不是本地源码；要做 RSI 改进必须走自定义 adapter。
- 费用是客户端估算，未读 DeepSeek 账单。
