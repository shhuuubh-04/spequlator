# Spequlator — Project status

- **Date:** 2026-10-23
- **Version:** 1.0 (git tag `v1.0`)
- **Status:** Built, evaluated once on the frozen test split, documented. Ready to demo.

## Done

| Part | Result |
|---|---|
| Data and core | CoDocBench adapter with pinned checksums; preprocessing; rules R1 and R2; report schema |
| Signals | TF-IDF and MiniLM deltas; MiniLM fine-tuned on train, gate passed (D-020); train-only calibration (D-028) |
| Interfaces | Typer CLI; local FastAPI service (127.0.0.1 only); React/Vite UI with change and snapshot modes, dataset examples; report-style results with a step-by-step calculation trace (D-030, D-031) |
| Evaluation | Settings frozen (tag `frozen-eval`); one-time test run → `results/`; RQ4 review of 60 reports (LLM-scored, D-029) |
| Docs | README, `EVALUATION_RESULTS.md` (generated from `results/`), `DEMO.md`; tag `v1.0` |

Tests: 148 Python, 7 frontend.

## Decisions taken during the build

D-025 (R2 decisive only inside the dead-band), D-026 (owner/project cluster keys), D-027 (UniXcoder dropped from the frozen run), D-028 (single combined score with one dead-band), D-029 (LLM-scored manual review), D-030 (read-only calculation trace), D-031 (report-style light UI). Details in `decisions.json`; their effect on results in `EVALUATION_RESULTS.md`.

## Known limitations

- R1 does not flag a newly added parameter that the docstring never mentions.
- Disagreeing signals can still average into a confident `no_obvious_drift`.
- The RQ4 review is LLM-scored by a single scorer; no human agreement figure.
- Results are on the CoDocBench proxy task, not real-world drift.

## Future work

1. Reverse R1 ("R1b"): new parameters missing from the docstring.
2. Return `inconclusive` when TF-IDF and the encoder point in opposite directions.
3. Drop stopwords from the "terms shared" evidence.
4. A human-annotated review with two annotators and κ.
5. UniXcoder and SciCoQA as a second dataset.

Any of these changes the frozen system, so each needs a new decision entry and a fresh frozen run on new data.

## Change control

Any scope, dataset, architecture or evaluation change must be recorded as a new decision entry in root `decisions.json` and reflected in the relevant docs **before** implementation.