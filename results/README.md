# Curated results

Small records kept in the repo so the claims in the README can be checked
without committing full run directories.

- `evo-harness-smoke-2tasks.md` / `.jsonl` — two-task smoke run
  (`session-window-debug`, `gsea-proteomics`). Both tasks scored `reward=0`;
  the harness grew from 0 to 840 to 1663 characters. This demonstrates the
  reflection → injection loop, not an improvement.
- `tb4-baseline-records.jsonl` — per-task Terminal-Bench 4.0 baseline attempts.
  This is a subset run with a shorter budget than the official benchmark; it is
  not a leaderboard score.

Not included: task datasets, Docker images, full trajectories, verifier logs,
virtualenvs, caches, `outputs/`, `terminal-bench/runs/`.

See `docs/experiments/results/` for the write-ups and `artifacts/` for selected
provenance JSON.
