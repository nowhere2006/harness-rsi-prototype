# Terminal-Bench setup validation

Validated 2026-10-23 (Asia/Shanghai).

## Components and pinned versions

- Harbor CLI: `0.24.0`; upstream release source commit:
  `b53b8134e1241686dca7759af188f987ecc48e8b`.
- Harbor Python dependencies: exact versions in `requirements.lock`; file SHA-256:
  `83ff8619f439b61c8a7b8d7b1d6dc83eb1353609083c2d3d0082694a6c78d678`.
- Terminal-Bench selector: official Harbor legacy registry entry
  `terminal-bench@2.0`, 89 tasks. The current registry maps those tasks to
  `https://github.com/laude-institute/terminal-bench-2.git` commit
  `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`.
- Docker control image: `harness-rsi-terminal-bench:harbor-0.24.0`, 189 MB;
  Python base resolved to
  `python:3.13-slim@sha256:57b29a7c050c4e679e4bea572e14b3965cf4b5839de2da49d55e49ffc4024f39`.
  It contains Docker CLI and Debian Docker Compose `2.26.1-4`.
- The adapter list includes Harbor's built-in `mini-swe-agent` adapter. Harbor
  installs the task-side CLI using the version option, which is pinned to
  `2.4.6` by the real-run entry point.

## Checks completed

- `harbor --version` returned `0.24.0` in the isolated Python environment and
  the Compose control image.
- `harbor agent list` in the control image included both `mini-swe-agent` and
  `nop`.
- The control image used the mounted Docker socket to build, start, verify, and
  clean up an isolated local task environment.
- `harbor dataset list --legacy` resolved `terminal-bench` version `2.0` with
  89 tasks. This fetched registry metadata only; official task files, reference
  solutions, and task images were not downloaded.
- `harbor run --print-config` resolved one selected 2.0 task, one attempt,
  `n_concurrent_trials=1`, zero automatic retries, `mini-swe-agent`, model
  `deepseek/deepseek-flash`, adapter version `2.4.6`, `cost_limit=1.0`,
  100 agent steps, 2,700 seconds wall time, and Docker policy `limit` with
  1 CPU/2,048 MB.
- Local no-cost smoke passed with reward `1.0`, one trial, zero exceptions. It
  used the synthetic `local/terminal-bench-smoke` task and `nop` agent, so it is
  only a Harbor/Docker lifecycle check and not an official benchmark result.
  Result: `runs/local-terminal-smoke-20261023213743/result.json`.
- The root `.env` is referenced by Compose with the relative `../.env` path.
  Secret values were not displayed or copied.
- No paid model request or official Terminal-Bench trial was made.

## Local resource state after preparation

- Available disk: 29 GiB, above the requested 20 GiB floor.
- Isolated host Python environment: 333 MB.
- Harbor result files: 248 KB; Harbor cache currently empty.
- No Docker pruning was performed because the Docker engine also contains the
  user's existing images, volumes, and build cache.

The US$1 cost limit is submitted to the adapter and depends on reported model
usage being available to Mini-SWE-Agent's cost tracker. The 100-step and
45-minute limits are configured separately in Mini-SWE-Agent's `agent` config.
The model connection itself remains unverified until an explicitly authorized
paid call is made. The local mini-SWE-Agent 2.4.6 source checkout
(`04d809ceab9df28f9adaed044884180159172930`) is not imported by Harbor: the
Harbor adapter is separate code that installs its own task-side package.

## Correction: resource overrides (2026-10-23, later)

The earlier check above recorded `Docker policy limit with 1 CPU/2,048 MB` as if
it were the benchmark's setting. It was a command-line override. Harbor reads
`cpus`, `memory` and `storage` from each task's `task.toml` and enforces them on
the task container; `--override-cpus` / `--override-memory-mb` replace those
values, which changes the declared environment (5 tasks use 2-4 CPUs, 18 use
4-8G). The official-task launch path no longer passes overrides; only the
synthetic local smoke task, which declares nothing, does.

## Paid single-task validation (2026-10-23)

First attempt, `fix-git`, failed before any model call: LiteLLM raised
`ModuleNotFoundError: No module named 'mcp'` because the bundled adapter installs
the CLI without that dependency. Fixed with a local adapter subclass
(`terminal-bench/harbor_agents/mini_mcp.py`) that adds `--with mcp`; the upstream
adapter and the local mini-swe-agent checkout are unchanged.

Second attempt passed end to end:

- Task set: local export of `terminal-bench@2.0` (89 tasks), registry commit
  `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`; task files hashed per run.
- Task: `fix-git`, difficulty `easy`, declared 1 CPU / 2G / 10G.
- Result: reward `1.0`, 2/2 verifier tests, 11 model calls, 166.8 s wall clock,
  US$0.0049 client estimate, 0 exceptions, no retries.
- Resource enforcement observed live: `NanoCpus=1000000000`,
  `HostConfig.Memory=2147483648`, matching `task.toml`.
- Docker Hub was unreachable (`auth.docker.io`, `registry-1.docker.io` time out).
  The task image was pulled through `dockerproxy.net` with
  `--platform linux/amd64` and retagged to `alexgshaw/fix-git:20251031`; the
  control image was reused instead of rebuilt.

Evidence: `artifacts/tb20-fix-git-run.json`,
`artifacts/tb20-preview-fix-git.json`, `terminal-bench/runs/tb20-fix-git-20261023-220312/`.

Boundaries: one easy task, one attempt, agent installed from PyPI rather than the
local checkout, amd64 image under emulation on arm64. Not a benchmark score.
