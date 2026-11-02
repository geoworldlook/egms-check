# Changelog

Versions follow semantic versioning (major.minor.patch). Before 1.0.0 the project had no version numbers; the main
steps are listed at the end with their dates and commits.

## 1.0.0 — 2026-11-02

First version in the GeoWorldLook project standard (decision D-095, `docs/plans/Plan_v3_produkt.md`). Methods,
thresholds and results are unchanged.

- **One command set:** package `egmscheck` with `python -m egmscheck run | publish | selftest | settings` (also
  `approvals` and `test`). It calls the same `step_0N` modules as the Colab notebooks, with the same parser as
  `python step_09_local.py …`, which still works. No weekly job: EGMS is updated once a year.
- **Published results:** `python -m egmscheck publish` copies a fixed set of result files from the data folder to
  `docs/showcase/` (verdicts, levelling tables, 7 figures) and writes `egmscheck_results.json`: all rules in one file,
  read from the result files, with the task, time and code commit of each result (also mapped to the history after
  D-094). A missing required file stops the publication; a file from an older publication that is no longer produced
  is removed. It commits only `docs/showcase/` and pushes with the system Git, without login windows; `--no-git`
  copies only. First publication: the run of 2026-10-15 (code `06eeefc`).
- **CI:** GitHub Actions runs ruff and the offline tests of all modules on every push and pull request
  (`.github/workflows/selftest.yml`, Python 3.12). The selftest now also covers the reference-table check (`step_00`)
  and the publication.
- `pyproject.toml` (package, dependencies, optional `stage-b`, ruff settings). `environment.yml` without `git`: the
  system Git is used (the conda-forge git opens a login window on push). Code clean-up for ruff: unused imports and
  variables removed, one statement per line, `def` instead of assigned `lambda`; no change in behaviour.
- README as a product card (problem, user, solution, evidence, status, limits, next), with both experiments, the
  repeat on the 2020–2024 release, negative and inconclusive results, and data citations with DOIs.
- Docs (in Polish): `docs/STAN_I_PLAN.md`, `docs/evidence/karta_wynikow.md`, `docs/plans/Plan_v3_produkt.md`;
  `docs/ARCHITEKTURA.md` describes the real code; plans v1–v2, migration notes and hand-over notes moved to
  `docs/archive/` (`git mv`). The Geobasis NRW format description (PDF from another publisher) is no longer copied:
  link and SHA-256 in `docs/evidence/zrodla/README.md`. A local path in `docs/URUCHOMIENIE_LOKALNE.md` replaced with
  a generic one.

## Repository history — 2026-11-02

Rewritten (D-094): two private .docx documents removed from all commits. Commit order, dates, messages, code and
results are unchanged; commit IDs changed. Details and the old-to-new commit map: `docs/evidence/historia_git.md`.

## Before 1.0.0 (no version numbers)

| Date | What | Commits |
|---|---|---|
| 2026-10-09 | plan, literature review, reference tables from publications, consistency check (`step_00`) | `8fb67aa` … `6612e1c` |
| 2026-10-10 | experiment 1: EGMS L2b 2019–2023 vs 35 GNSS stations in Groningen, rules fixed before computing; verdict PARTIAL | `5e0fd2d` … `0513709` |
| 2026-10-11 | modules for the 2020–2024 release: area search, L3, ground data, monitoring, ASF HyP3 + MintPy (stage B, offline tests only); controller with `CHECK_CONFIG`, `run_task` and registry | `69fd3bc` … `c849509` |
| 2026-10-12 | author approvals; NRW levelling reader; second release (2019–2023, L3 vertical) for the levelling comparison; repeat in Groningen on 2020–2024 | `790445e` … `454c4fe` |
| 2026-10-13 | experiment 2 write-up: relative variant against levelling-stable benchmarks; Even et al. 2024 checked in full text | `f5367d5` … `3d56dc9` |
| 2026-10-15 | EGMS uncertainty bands on the levelling figures; showcase notebooks; last full run (`06eeefc`) | `4cbe27c` … `06eeefc` |
| 2026-10-18 | merged to `main`, repository renamed to `egms-check`; English showcase notebooks | `0d3e576` … `cf8e04a` |
| 2026-10-24 | local runs on your own computer (`step_09_local.py`) | `2004af0` |
