# Harness RSI Prototype

A minimal, reproducible harness for studying **failure-driven harness updates** on
agent benchmarks. It runs a frozen coding agent on Terminal-Bench / SWE-bench,
reflects on failed trajectories, and injects the distilled lessons into later
tasks.

> **Status: minimal prototype, not a reproduction of Evo-Harness.**
> The current implementation covers only *execution reflection + cross-task
> injection*. The paper's evolver (`Add / Merge / Revise / Skip`), structured
> skill entries, top-*b* selection, and general/topic skill levels are **not**
> implemented. No improvement claim is made.

## At a glance

| What | Result | Scope |
| --- | --- | --- |
| SWE-bench Verified, `scikit-learn__scikit-learn-26323` | official `resolved=true`; 1 FAIL_TO_PASS + 188 PASS_TO_PASS | one task, one attempt |
| Terminal-Bench 2.0, `fix-git` | official `reward=1.0`; 2 tests passed | one task, one attempt |
| Terminal-Bench 4.0 subset baseline | 19-task subset selected; ledger caveats documented | not a leaderboard score |
| Evo prototype, 2-task smoke | both tasks `reward=0`; harness grew 0 → 840 → 1663 chars | mechanism only |
| Evo prototype, 15-task sequential run | started; no aggregate result yet | no result yet |

Details and caveats: [`docs/experiments/results/`](docs/experiments/results/) and
[`results/`](results/).

## What is in this repository

This repo contains **our own code, configuration, documentation and curated
results**. It deliberately does **not** bundle upstream code, benchmark data,
Docker images or run artifacts.

| Included | Not included — download / generate yourself |
| --- | --- |
| `scripts/` — evaluation runners, Evo prototype, comparison tool | `mini-swe-agent/` upstream checkout (clone at the pinned commit) |
| `terminal-bench/` — control container, Harbor adapter, pinned requirements | Terminal-Bench task datasets (`harbor dataset download`) |
| `configs/` — model pricing, SWE-bench overrides | Docker images (pulled on demand) |
| `docs/` — experiment notes, result write-ups, RSI option memo | Python virtualenvs, caches, `outputs/`, `runs/` |
| `results/` — small curated records | `.env` with API keys |
| selected `artifacts/` — provenance JSON only | full trajectories and job logs |

## Two execution paths

The repo uses two different agent execution paths. This matters for any change
to the agent or harness.

- **SWE-bench path.** The agent process runs in the control container
  (`mini-extra swebench`). The task container only provides the execution
  environment. The local `mini-swe-agent/` checkout is used, so local source
  changes take effect.
- **Terminal-Bench path.** Harbor installs a pinned `mini-swe-agent==2.4.6`
  **inside each task container** and runs it there. The local checkout is not
  used. Agent changes must go through a Harbor adapter; task images stay
  agent-agnostic so the same task can be used with different agents.

`terminal-bench/harbor_agents/mini_mcp.py` is an example adapter extension: it
subclasses Harbor's mini-swe-agent adapter and adds one dependency to the
container-side install. It is our code and leaves the upstream baseline
untouched. It is also the extension point for future RSI work.

## Evo-Harness prototype

The prototype is a sequential, task-level version of the paper's loop:

```
task k arrives
  -> harness.md is appended to the task instruction
  -> frozen agent runs; official verifier scores the attempt
  -> if reward == 0:
       verifier output + last 8 commands
         -> reflection model writes at most 2 lessons
         -> lessons are appended to harness.md (4000-char cap)
  -> task k+1 starts with the updated harness
```

Implementation: [`scripts/evo-harness`](scripts/evo-harness).

- learns **only from failures** (successful runs do not produce lessons);
- lessons use `TRIGGER / ACTION / WHY` and are written as free text;
- the harness is injected through Harbor's `--extra-instruction-path`, which
  appends the file to the task instruction;
- every task records `reward`, `cost_usd`, `wall_sec`, `harness_chars` and the
  generated lesson in `outputs/evo-harness/records.jsonl`;
- `scripts/compare-arms` joins the baseline and Evo records per task.

**Not implemented:** evolver edits, structured skill entries
(`lesson / trigger / evidence / scope_hint`), top-*b* selection, general vs
topic skills, batch-level cross-task compilation, full-context reflection, and
multiple repeats or randomized task orders.

## Quickstart

### 0. Prerequisites

- macOS or Linux, Docker Desktop / Docker Engine
- Python 3.11+ for the SWE-bench control container; Python 3.13 for the
  Terminal-Bench control venv
- `git`, ~20 GiB free disk, and a DeepSeek API key
- Docker Hub access (or a mirror; see the network note in
  [`docs/terminal-bench.md`](docs/terminal-bench.md))

### 1. Clone this repo and the upstream agent

```bash
git clone https://github.com/nowhere2006/harness-rsi-prototype.git
cd harness-rsi-prototype

git clone https://github.com/SWE-agent/mini-swe-agent.git mini-swe-agent
cd mini-swe-agent
git checkout 04d809ceab9df28f9adaed044884180159172930
cd ..
```

The upstream checkout is not committed to this repo.

### 2. Configure

```bash
cp .env.example .env
# edit .env: DEEPSEEK_API_KEY=...
chmod 600 .env
mkdir -p outputs artifacts .cache
```

`.env` is git-ignored. Task containers do not receive the key or the Docker
socket.

### 3. SWE-bench path

```bash
./scripts/lab build
./scripts/lab up
./scripts/lab smoke          # deterministic, no API calls
./scripts/lab live-smoke     # small paid model call
./scripts/lab swebench-one scikit-learn__scikit-learn-26323 baseline-sk26323
```

`preds.json` and a patch are not a benchmark score: run the official SWE-bench
evaluator to obtain `resolved`.

### 4. Terminal-Bench path

```bash
cd terminal-bench
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.lock

# Inspect the pinned registry selectors before downloading.
.venv/bin/harbor dataset list --legacy
.venv/bin/harbor dataset download terminal-bench@2.0 -o datasets
.venv/bin/harbor dataset download terminal-bench@4.0.0 -o datasets-tb4

cd ..
./scripts/terminal-lab check
TERMINAL_BENCH_PAID_RUN=1 ./scripts/terminal-lab run-single fix-git
```

Datasets are downloaded, not committed. The exact registry commit and task-set
scope are documented in [`docs/terminal-bench.md`](docs/terminal-bench.md) and
[`terminal-bench/VALIDATION.md`](terminal-bench/VALIDATION.md).

### 5. Evo-Harness prototype

```bash
# Two-task smoke example (paid; calls the DeepSeek API)
./scripts/evo-harness session-window-debug gsea-proteomics

# Full 15-task sequential run (paid; long-running)
./scripts/evo-harness

# Baseline arm for the same subset (paid; requires the TB4 dataset)
scripts/tb4-baseline

# Paired comparison
./scripts/compare-arms
```

The prototype writes `terminal-bench/harness/harness.md` and
`outputs/evo-harness/records.jsonl`. Both are git-ignored.

## Results and evidence

- [SWE-bench single task](docs/experiments/results/2026-10-23-swebench-sk26323.md)
- [Terminal-Bench 2.0 fix-git](docs/experiments/results/2026-10-23-terminal-bench-fix-git.md)
- [Terminal-Bench 4.0 baseline subset](docs/experiments/results/2026-10-24-tb4-baseline-fast-agent-subset.md)
- [Evo smoke records](results/evo-harness-smoke-2tasks.md)
- `artifacts/` — selected provenance JSON (no logs or trajectories)

The SWE-bench and Terminal-Bench 2.0 results are **single-task verifications**,
not benchmark scores. The Terminal-Bench 4.0 subset uses a shorter budget than
the official run and must not be compared with public leaderboard numbers.

## Limitations

- **Not a paper reproduction.** Only failure reflection and injection are
  implemented; the evolver and structured skill representation are missing.
- **Order-dependent by construction.** The harness at task *k* depends on the
  prefix of tasks seen. This run uses one fixed order, with no repeats, no
  randomized orders, and no held-out split, so mechanism and task order are
  confounded.
- **Narrow reflection context.** Only verifier output and the last 8 commands
  are used, not the full trajectory or patch.
- **Task-specific leakage risk.** A lesson can encode dataset-specific details;
  the GSEA smoke lesson is an example.
- **Cost accounting is incomplete.** Task costs are recorded; reflection API
  cost is not included in the comparison.
- **One attempt per task.** No variance estimate or significance claim.
- **Hardware/network caveats.** The local run uses an ARM host with x86 task
  images under emulation; wall-clock numbers are not comparable across setups.
- **Costs are client-side estimates**, not DeepSeek bills.

## Repository layout

```
.
├── configs/                  # model pricing, SWE-bench overrides
├── docs/                     # experiment notes and result write-ups
├── scripts/                  # runners, Evo prototype, comparison
├── terminal-bench/           # Harbor control image, adapter, smoke task
├── results/                  # small curated records
├── artifacts/                # selected provenance JSON
├── Dockerfile, compose.yaml  # SWE-bench control container
└── .env.example
```

## References

- Evo-Harness: *Context-to-Harness Skill Compilation for Self-Evolving Agents*,
  Wei et al., EMNLP 2026 Main, [arXiv:2608.15071](https://arxiv.org/abs/2608.15071).
  This repository is an independent minimal prototype; it is not affiliated with
  the authors or the official `a-evolve` code.
- [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)
- [Harbor](https://github.com/laude-institute/harbor) and
  [Terminal-Bench](https://github.com/laude-institute/terminal-bench)
- [SWE-bench](https://github.com/swe-bench/SWE-bench)
