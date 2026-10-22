# Spequlator — Implementation plan

- **Version:** 1.2
- The detailed, time-boxed schedule is in **`10_HOUR_PLAN.md`**. This file keeps the phase view and priorities.

| Phase | Plan hours | Exit condition |
|---|---|---|
| 0 · Setup and data pins | H0 (0:00–0:45) | Checksums verified; dataset adapter tested |
| 1 · Shared core | H1 (0:45–2:15) | `analyze()` returns a valid `Report`; rules and TF-IDF tested |
| 2 · Encoder and caches | H2 (2:15–3:00) | Encoder wrapper with fallback; train cache running |
| 3 · CLI, calibration, fine-tune | H3 (3:00–4:00) | CLI tests green; `thresholds.json` from train; fine-tune go/no-go decided |
| 4 · Frozen evaluation | H4 (4:00–5:00) | `frozen-eval` tag; one test run; `results/` written |
| 5 · API | H5 (5:00–6:00) | API tests and CLI/API parity green |
| 6 · Frontend | H6–H8 (6:00–8:00) | A user can finish both modes and an example in the UI |
| 7 · Manual review and write-up | H8 (8:00–9:00) | `manual_review.csv` scored; `EVALUATION_RESULTS.md` filled |
| 8 · Hardening and demo | H9 (9:00–10:00) | Quality gates pass from a fresh clone; `v1.0` tag |

## Priority if the schedule tightens (unchanged order, now with explicit cut lines)

1. Shared core and unit tests
2. CLI
3. Frozen evaluation (TF-IDF, rules, pretrained encoder)
4. API and minimal frontend
5. Fine-tuned encoder (D-020 gate)
6. Manual review and write-up
7. Visual polish and export

The cut-line table is in `10_HOUR_PLAN.md` §4. Removing the frontend or CLI still requires a new decision entry.