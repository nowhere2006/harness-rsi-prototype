# Terminal-Bench 2.0 setup

Harbor is pinned to `0.24.0` (upstream release commit
`b53b8134e1241686dca7759af188f987ecc48e8b`), with Python dependencies pinned in
`terminal-bench/requirements.lock`. The benchmark selector is the official Harbor
legacy registry entry `terminal-bench@2.0`; that entry maps the 89 tasks to
`https://github.com/laude-institute/terminal-bench-2.git` at commit
`69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`.

The task files are exported on disk at `terminal-bench/datasets/terminal-bench/`.
Runs use `--path` against that export so a registry change cannot silently swap
the task set underneath an experiment; each run records SHA-256 hashes of the
task files it used.

## Where the CPU/memory limits come from

Every task declares its own requirement in `task.toml`:

```toml
[environment]
docker_image = "alexgshaw/fix-git:20251031"
cpus = 1
memory = "2G"
storage = "10G"
```

Harbor turns those declarations into a Docker Compose override on the **task
container** (`cpus: <n>`, `mem_limit: "<mb>m"`). With the Docker backend the
`auto` policy resolves to `limit`, so `--cpus limit --memory limit` enforces the
task's own numbers.

Do **not** pass `--override-cpus` / `--override-memory-mb`: those replace the
task's declared values. 84 of the 89 tasks declare 1 CPU, but five declare 2 or
4; 18 declare 4G or 8G. Overriding silently changes both the runtime and the
comparability of the result. The synthetic local smoke task has no declared
resources, which is why `smoke` still passes explicit overrides.

Observed on a live trial of `fix-git` (declared 1 CPU / 2G):
`NanoCpus=1000000000`, `HostConfig.Memory=2147483648`.

## Agent adapter

Harbor's bundled `mini-swe-agent` adapter installs the CLI from PyPI inside the
task container (`mini-swe-agent==2.4.6`) and does not import the local
`mini-swe-agent/` checkout. Current LiteLLM needs the `mcp` package on the
chat-completion path; without it every model call raises
`ModuleNotFoundError: No module named 'mcp'` and LiteLLM retries until the trial
dies.

`terminal-bench/harbor_agents/mini_mcp.py` subclasses the upstream adapter and
adds one install step (`--with mcp`). Runs pass
`--agent harbor_agents.mini_mcp:MiniSweAgentWithMcp`. The control container
mounts this directory and gets `PYTHONPATH` from `compose.yaml`, so the class is
importable.

This file is our code and leaves the baseline `mini-swe-agent/` checkout
untouched. It is also the extension point for the RSI work: a modified agent has
to reach Terminal-Bench trials through an adapter like this one, not through
edits to the local checkout.

## Network constraint

Direct Docker Hub access is blocked on this network: `auth.docker.io` and
`registry-1.docker.io` time out. Anything that needs registry metadata fails,
including a control-image rebuild and a task-image pull.

Workaround used for the validated run: pull through a mirror and retag under the
official name, then let Harbor find the image locally.

```sh
docker pull --platform linux/amd64 dockerproxy.net/alexgshaw/fix-git:20251031
docker tag dockerproxy.net/alexgshaw/fix-git:20251031 alexgshaw/fix-git:20251031
```

`scripts/terminal-lab` therefore only builds the control image when it is
missing. Rebuilding needs registry access; do it while the network allows it.

## Commands

```sh
scripts/terminal-lab check                 # version + agent list (builds only if image missing)
scripts/terminal-lab smoke                 # synthetic task, nop agent, no model call
scripts/terminal-lab preview TASK_SLUG     # resolved JobConfig JSON, no container run
TERMINAL_BENCH_PAID_RUN=1 scripts/terminal-lab run-single TASK_SLUG
scripts/terminal-lab report JOB_NAME
```

`run-single` selects one task, one attempt, zero retries, one concurrent trial,
`deepseek/deepseek-flash`, agent CLI 2.4.6, `cost_limit=1.0`, and agent config
`step_limit=100`, `wall_time_limit_seconds=2700`. The US$1 figure is a
client-side estimate checked between requests; it depends on LiteLLM being able
to price the model's returned usage.

## Validated run

`fix-git` (difficulty `easy`, expert estimate 5 min, 1 CPU / 2G), one attempt:
reward `1.0`, both verifier tests passed, 11 model calls, 166.8 s wall time,
client-estimated US$0.0049, no exceptions. Evidence and caveats:
`artifacts/tb20-fix-git-run.json`, raw artifacts under
`terminal-bench/runs/tb20-fix-git-20261023-220312/`.

This proves the Terminal-Bench path works end to end. It is one easy task, so it
is not a benchmark score, and task selection for experiments is still open.
