# Spequlator documentation pack (v1.2)

v1.2 turns the v1.1 scope into an **evidence-backed, 10-hour build plan**. Each decision cites external sources (R*) or train-split-only feasibility measurements (F*) that were run on CoDocBench before the build.

## What changed from v1.1

| File | Change |
|---|---|
| `decisions.json` | D-012 accepted. New D-015…D-024. New blocks: `dataset_freeze.codocbench` (commit, licence, SHA-256), `models`, `evaluation`, `evidence_register`. |
| `docs/10_HOUR_PLAN.md` | **Replaced.** Hour-by-hour plan, background compute, cut lines, definition of done, pyproject snippet. |
| `docs/FEASIBILITY.md` | **New.** Train-only spike results F3–F10. |
| `docs/REFERENCES.md` | **New.** Evidence register: papers, model cards, tooling docs, checksums, model revisions. |
| `docs/EVALUATION_RESULTS.md` | **New.** Template, filled in at H8. |
| `docs/EXPERIMENT_PLAN.md` | Rewritten: proxy task, RQ1–4, metrics, cluster bootstrap, pre-registered expectations. |
| `docs/ARCHITECTURE.md` | Change and snapshot modes, signals S1/S2, rules R1/R2, decision rule, module map onto `src/spequlator/`, API under `/api`. |
| `docs/DATASETS.md`, `docs/DATASET_AUDIT.md` | CoDocBench collection rule, licence, pins, field formats, v1.2 audit addendum. |
| `docs/PRD.md` | Modes, Journey B wording, FR-5/6/6b, acceptance criterion 8, risks. |
| `docs/CLI_SPEC.md` | Change-mode flags, `--doc-version`, `--no-encoder`, `data`/`eval` commands, exit codes 0/1/2/3. |
| `docs/FRONTEND_SPEC.md` | Mode toggle, before/after docstring switch, signal bars, states table. |
| `docs/TESTING_AND_QUALITY.md` | Concrete test inventory, fixtures, gates, `RUN_INFO.json`. |
| `docs/IMPLEMENTATION_PLAN.md`, `docs/STATUS.md` | Aligned to the 10-hour plan. |
| `scripts/feasibility/` | **New.** The scripts that produced F1–F10 (train split only). |

## Install into the repository

See the step-by-step instructions in the chat reply, or follow these steps:

```bash
cd ~/spequlator
git add -A && git commit -m "wip: before docs v1.2" || true      # safety point
cp docs/10_HOUR_PLAN.md /tmp/10_HOUR_PLAN.old.md                   # keep your old plan for comparison
unzip -o ~/Downloads/spequlator_docs_v1_2.zip -d /tmp/spq12
cp /tmp/spq12/spequlator_docs/decisions.json .
cp /tmp/spq12/spequlator_docs/README_DOCS.md .
cp /tmp/spq12/spequlator_docs/docs/*.md docs/
mkdir -p scripts && cp -r /tmp/spq12/spequlator_docs/scripts/feasibility scripts/
python -m json.tool decisions.json > /dev/null && git diff --stat
git add decisions.json README_DOCS.md docs scripts/feasibility
git commit -m "docs: v1.2 evidence-backed 10-hour plan (D-015..D-024)"
```

The pack does not touch `README.md`, `pyproject.toml`, `src/` or `tests/`. Those change during the build: see `10_HOUR_PLAN.md` H0 and H9.