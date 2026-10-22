# Spequlator — Evaluation results (template; filled at H8)

- **Run:** `results/RUN_INFO.json`. Git tag `frozen-eval`, commit `<sha>`, date `<date>`.
- **Split:** CoDocBench test (2,273 records, 103 projects), opened once.
- **Task:** stale-vs-updated proxy (D-015). These are **proxy** labels, not real-drift judgements.

## Headline (95% project-cluster bootstrap CI)

| Signal | Mode | Pairwise acc. | Pooled AUC | Δ AUC vs TF-IDF Δ (paired CI) |
|---|---|---|---|---|
| TF-IDF | snapshot | | | |
| TF-IDF | Δ | | | — |
| UniXcoder | Δ | | | |
| MiniLM (pretrained) | Δ | | | |
| MiniLM (fine-tuned, D-020) | Δ | | | |
| Combined decision rule | 3-state | n/a | n/a | n/a |

## Decision-rule outcomes

| Pair | potential_drift | no_obvious_drift | inconclusive |
|---|---|---|---|
| stale (old docstring) | | | |
| updated (new docstring) | | | |

## Rules

| Rule | Fires on stale | Fires on updated | Lift | Coverage |
|---|---|---|---|---|
| R1 parameter mismatch | | | | |
| R2 deleted-identifier mention | | | | |

## Strata by docstring edit ratio

(figure `results/figures/strata.png` and table)

## Answers

- **RQ1:**
- **RQ2:**
- **RQ3:**
- **RQ4 (manual review, n = 30 records / 60 reports):** fidelity __/2, specificity __/2, calibration __/2, κ = __ (if double-annotated)

## Worked examples

1. Success:
2. Inconclusive:
3. Failure:

## Deviations from the pre-registered plan

(none / list)

## Threats to validity

See `EXPERIMENT_PLAN.md`. Note anything new that came up here.