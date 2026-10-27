# Spequlator — Project status

- **Date:** 2026-10-27
- **Version:** 2.0: the app runs v2, TF-IDF + fine-tuned Granite (D-034). v1 is frozen and unchanged (tag `v1.0`).
- **Status:** v1 built, evaluated on the frozen test split, documented. Phase 2 (three pre-registered training runs) is complete and documented in `PHASE2_RESULTS.md`. Ready to demo.

## Done

| Part | Result |
|---|---|
| Data and core | CoDocBench adapter with pinned checksums; preprocessing; rules R1 and R2; report schema |
| Signals | TF-IDF and MiniLM deltas; MiniLM fine-tuned on train, gate passed (D-020); train-only calibration (D-028) |
| Interfaces | Typer CLI; local FastAPI service (127.0.0.1 only); React/Vite UI with change and snapshot modes, dataset examples; report-style results with a step-by-step calculation trace (D-030, D-031) |
| Evaluation | Settings frozen (tag `frozen-eval`); one-time test run → `results/`; RQ4 review of 60 reports (LLM-scored, D-029) |
| Docs | README, `EVALUATION_RESULTS.md` (generated from `results/`), `DEMO.md`; tag `v1.0` |
| Phase 2 (D-032) | Three pre-registered Kaggle runs (tags `phase2-frozen`, `phase2-run2-frozen`, `phase2-run3-frozen`). Results: MiniLM plateaus at about 0.69 dev AUC; the cross-encoder ranks two versions but cannot judge one (D-033); Granite Small R2 beats MiniLM on test by +0.021 AUC [0.012, 0.030]; edit-size breakdown |
| v2 system (D-034) | TF-IDF + Granite in the app and CLI; test pooled AUC 0.734 vs 0.706 (TF-IDF and v1); eps set on train; `SPEQULATOR_SYSTEM=v1` switches back; word heatmap explains Granite's score |

Tests: 165 Python, 8 frontend.

## Decisions taken during the build

D-025 (R2 decisive only inside the dead-band), D-026 (owner/project cluster keys), D-027 (UniXcoder dropped from the frozen run), D-028 (single combined score with one dead-band), D-029 (LLM-scored manual review), D-030 (read-only calculation trace), D-031 (report-style light UI), D-032 (phase 2 training runs), D-033 (cross-encoder not served; encoder word heatmap), D-034 (v2: TF-IDF + Granite). Details in `decisions.json`; their effect on results in `EVALUATION_RESULTS.md`.

## Known limitations

- R1 does not flag a newly added parameter that the docstring never mentions.
- Disagreeing signals can still average into a confident `no_obvious_drift`.
- The RQ4 review is LLM-scored by a single scorer; no human agreement figure.
- Results are on the CoDocBench proxy task, not real-world drift.
- v2's decision rule (coverage, balanced accuracy of findings) was not measured on test; the test split has already been used four times (declared in `PHASE2_RESULTS.md`).
- About a third of CoDocBench updates change five or fewer tokens, and 7% are cosmetic; no similarity signal can separate those.

## Future work

1. Reverse R1 ("R1b"): new parameters missing from the docstring.
2. Return `inconclusive` when TF-IDF and the encoder point in opposite directions.
3. Drop stopwords from the "terms shared" evidence.
4. A human-annotated review with two annotators and κ.
5. UniXcoder and SciCoQA as a second dataset.
6. Evaluate v2's decision rule on new data, since the CoDocBench test split is used up.

Any of these changes the frozen system, so each needs a new decision entry and a fresh frozen run on new data.

## Change control

Any scope, dataset, architecture or evaluation change must be recorded as a new decision entry in root `decisions.json` and reflected in the relevant docs **before** implementation.