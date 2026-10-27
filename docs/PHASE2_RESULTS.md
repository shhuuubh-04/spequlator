# Spequlator — Phase 2 results (deep-learning track)

- **Dates:** 2026-10-25 to 2026-10-27. Decisions D-032 (phase 2), D-033 (cross-encoder not served), D-034 (v2 system).
- **Question:** can a better-trained or better-chosen neural model beat word matching (TF-IDF) on the CoDocBench proxy task, and improve the system the app runs?
- **Answer:** yes, modestly and reliably. A small code-aware encoder, IBM Granite Embedding Small R2 (47M parameters), fine-tuned on the train split, is the first learned signal to match TF-IDF on its own. Combined with TF-IDF it gives the best result in the project: pooled AUC **0.734**, against 0.706 for TF-IDF and for v1. The app now runs this combination ("v2").
- **Source files:** `results/phase2_run1/`, `results/phase2_run2/`, `results/phase2_run3/` (tables, metrics, dev results, freeze records), `results/phase2_run3/by_edit_size.md`, `results/v2/`. The notebook is `notebooks/phase2_train.ipynb`; its git history holds all three pre-registered versions.

## Protocol

Same task, data and statistics as v1 (`docs/EVALUATION_RESULTS.md`): the stale-vs-updated proxy (D-015), CoDocBench at the pinned commit, 95% project-cluster bootstrap CIs (1,000 resamples, seed 2026). Pairwise accuracy (PA) asks "given the old and new docstring for the same change, which fits better?". Pooled AUC asks the harder question the app faces: judge one docstring with nothing to compare it to.

1. **Training on Kaggle (one T4 GPU), train split only.** `test.jsonl` is never copied to Kaggle. Models are selected on v1's project-held-out split: 20 dev projects (seed 13), the other train projects for fitting.
2. **Pre-registration.** Before each run, the notebook with its grid and selection rule was committed and pushed. The commit hash Kaggle ran is printed in each run's log.
3. **Import and freeze on the laptop.** `phase2 import` checks every file's SHA-256 against the notebook's manifest. `phase2 freeze` pins the hashes and the combination scales (computed from train data only), and is committed and tagged before any test number is computed.
4. **One test run per phase-2 run.** Each was a declared reuse of the test split (see "Test-split use" below).

| Run | Tag | What it tested |
|---|---|---|
| 1 | `phase2-frozen` | MiniLM grid and ablations; a cross-encoder (pointwise loss) |
| 2 | `phase2-run2-frozen` | MiniLM grid around run 1's pick; cross-encoder with a pairwise loss |
| 3 | `phase2-run3-frozen` | MiniLM vs Granite Small R2, same search, 3 seeds per setting; no cross-encoder |

## Headline: test split (2,273 records, 103 projects)

| Signal | Pairwise acc. | Pooled AUC | AUC minus TF-IDF |
|---|---|---|---|
| TF-IDF delta | 0.745 [0.712, 0.778] | 0.706 [0.682, 0.729] | — |
| v1 system (TF-IDF + MiniLM-ft) | 0.769 [0.735, 0.804] | 0.706 [0.683, 0.730] | 0.000 [−0.009, 0.009] |
| MiniLM fine-tuned (v1) | 0.713 [0.685, 0.743] | 0.660 [0.638, 0.681] | −0.046 [−0.066, −0.032] |
| MiniLM fine-tuned (run 3) | 0.740 [0.706, 0.772] | 0.696 [0.671, 0.720] | −0.010 [−0.023, 0.003] |
| **Granite fine-tuned (run 3)** | 0.748 [0.710, 0.785] | **0.717** [0.686, 0.746] | +0.011 [−0.006, 0.028] |
| TF-IDF + MiniLM (run 3) | 0.772 [0.739, 0.804] | 0.724 [0.698, 0.749] | +0.018 [0.010, 0.027] |
| **TF-IDF + Granite (run 3) = v2** | **0.776** [0.738, 0.812] | **0.734** [0.705, 0.760] | **+0.028** [0.018, 0.039] |

Paired differences on the same records (run 3):

| Comparison | Pairwise acc. | Pooled AUC |
|---|---|---|
| Granite minus MiniLM | +0.008 [−0.007, 0.028] | **+0.021 [0.012, 0.030]** |
| TF-IDF + Granite minus TF-IDF + MiniLM | +0.004 [−0.009, 0.020] | **+0.010 [0.004, 0.017]** |
| TF-IDF + Granite minus v1 system (PA) | +0.006 [−0.012, 0.023] | — |

How to read these:
- Granite's gain over MiniLM is real (the interval stays above zero) and shows in **pooled AUC**, the app's task.
- On paired accuracy, every combination sits around 0.77 and no difference between them is clear.

## Run 1: MiniLM sweep and ablations; pointwise cross-encoder

Dev AUC, single seed (13):

| MiniLM setting | Dev AUC |
|---|---|
| Pretrained, 256 tokens | 0.639 |
| v1's setting (lr 2e-5, 1 epoch, 128 tokens) | 0.653 |
| lr 2e-5, 3 epochs, 256 tokens | 0.683 |
| **lr 5e-5, 3 epochs, 256 tokens (picked)** | **0.693** |
| Same pick, 128 tokens | 0.656 |
| Pick without the hard negative (the old docstring) | 0.666 |
| Pick with batch 32 | 0.689 |
| Pick with seed 7 / seed 42 | 0.682 / 0.686 |

- **Longer inputs helped most:** 256 tokens instead of 128 gave up to +0.04.
- **Hard negatives** (training with the old docstring as the wrong answer) gave +0.027.
- **Cross-encoder:** trained to label each (docstring, code change) pair as fitting or not. Its loss stayed at ln 2 ≈ 0.693, meaning it learned nothing. Dev AUC 0.515–0.532; test 0.545.
- **Test:** tuned MiniLM 0.694 (v1's MiniLM 0.660); TF-IDF + tuned MiniLM 0.724, +0.018 [0.010, 0.026] over TF-IDF.

## Run 2: refined grid; pairwise cross-encoder

- **MiniLM:**
  - 384 tokens: 0.696 dev, within the 0.005 tie margin, so 256 stayed.
  - 5 epochs: 0.690 / 0.693, no gain over 3.
  - The pick was run 1's setting again; the hard-negative effect repeated (+0.027).
- **Cross-encoder, pairwise loss** (−log σ(score_new − score_old)):
  - The loss now fell below chance (0.81 → 0.62), and dev PA rose to 0.631. Dev AUC stayed at 0.530.
  - Test: PA 0.646, AUC 0.552.
  - TF-IDF + MiniLM + cross-encoder reached **PA 0.798, +0.029 [0.009, 0.047] over v1**, but its pooled AUC was 0.702, below TF-IDF + MiniLM.
- **Interpretation:** the cross-encoder learned to rank two versions of the same docstring. Its scores are not comparable across functions, so it cannot judge a single docstring. It is therefore not served in the app (D-033).
- **Reproducibility:** retraining MiniLM with identical settings produced bitwise-different weights (GPU non-determinism). Test results matched to within 0.002 (AUC 0.694 and 0.724 in both runs).

## Run 3: MiniLM vs Granite Small R2, 8 settings × 3 seeds

The same search for both models:
- **Settings:** setting 0 is runs 1–2's pick; settings 1–7 are drawn at random (seed 2026) from:
  - learning rate {3e-5, 5e-5, 8e-5}
  - epochs {2, 3, 4}
  - batch size {8, 16}
  - warm-up {0.05, 0.1, 0.2}
  - weight decay {0, 0.01}
  - loss scale {20, 30}
- **Fixed:** 256 tokens, hard negatives on.
- **Seeds:** each setting trained with seeds 13, 7 and 42, and compared on the **mean** dev AUC.
- **Granite:** pinned to revision 2ab6fa8, trained and saved in float32 (it ships in bfloat16).

| Setting | lr | Epochs | Batch | Warm-up | Weight decay | Scale | MiniLM dev AUC | Granite dev AUC |
|---|---|---|---|---|---|---|---|---|
| c0 (runs 1–2 pick) | 5e-5 | 3 | 8 | 0.10 | 0 | 20 | 0.687 ± 0.005 | 0.685 ± 0.003 |
| c1 | 3e-5 | 3 | 8 | 0.05 | 0.01 | 30 | 0.684 ± 0.004 | 0.712 ± 0.002 |
| c2 | 8e-5 | 3 | 8 | 0.05 | 0 | 20 | 0.689 ± 0.002 | 0.681 ± 0.004 |
| c3 | 5e-5 | 2 | 16 | 0.05 | 0.01 | 30 | 0.684 ± 0.002 | **0.712 ± 0.002 (picked)** |
| c4 | 3e-5 | 3 | 16 | 0.10 | 0.01 | 30 | 0.684 ± 0.003 | 0.711 ± 0.001 |
| c5 | 8e-5 | 4 | 8 | 0.20 | 0.01 | 20 | 0.680 ± 0.002 | 0.675 ± 0.005 |
| c6 | 8e-5 | 4 | 16 | 0.10 | 0.01 | 20 | **0.691 ± 0.005 (picked)** | 0.677 ± 0.003 |
| c7 | 8e-5 | 4 | 16 | 0.05 | 0.01 | 30 | 0.694 ± 0.003 | 0.678 ± 0.002 |
| Pretrained | — | — | — | — | — | — | 0.639 | 0.648 |

(± = standard deviation over the three seeds. Pick rule: best mean; within 0.005, fewer epochs, then the lower setting number. Under that rule c6 beats c7 for MiniLM.)

- **MiniLM has plateaued.** All eight settings fall between 0.680 and 0.694. The single-seed 0.693 quoted for runs 1–2 averages 0.687 over three seeds.
- **Granite is better, and stable.** Three different settings reach 0.711–0.712, with seed spread of 0.001–0.002. Its lead of about +0.02 over MiniLM is 4–10× the seed noise.
- **Granite needs gentle training.** Its good settings use a lower learning rate or fewer steps, plus loss scale 30. Aggressive settings (8e-5, 4 epochs) drop it to about 0.676, below MiniLM. MiniLM, a smaller model, prefers the aggressive end.
- **The search mattered.** With the old recipe (c0), Granite looks no better than MiniLM (0.685 vs 0.687). The gap only showed once both models were tuned the same way.
- **Dev predicted test.** Granite scored 0.712 on dev and 0.717 on test; its lead over MiniLM was +0.021 on dev and +0.021 on test.

## Where the errors are: results by docstring edit size

This section only describes the frozen run-3 results (`results/phase2_run3/by_edit_size.md`). Nothing was trained, tuned or chosen from it.
- **Edit size** counts the words and punctuation marks inserted, deleted or replaced between the old and new docstring.
- **Cosmetic** means the words are identical and only case, punctuation or spacing changed.

| Docstring change | Test records | PA, TF-IDF + Granite | AUC, TF-IDF | AUC, Granite | AUC, TF-IDF + Granite |
|---|---|---|---|---|---|
| 0–1 tokens | 343 (15%) | 0.688 | 0.658 | 0.628 | 0.658 |
| 2–5 tokens | 402 (18%) | 0.711 | 0.663 | 0.651 | 0.669 |
| 6–15 tokens | 543 (24%) | 0.788 | 0.683 | 0.723 | 0.729 |
| 16+ tokens | 985 (43%) | **0.826** [0.786, 0.867] | 0.749 | 0.764 | **0.783** |
| Cosmetic only | 158 (7%) | 0.484 | 0.505 | 0.507 | 0.506 |

- **Larger edits are caught more reliably.** On edits of 16+ tokens (43% of records), v2 picks the right version 83% of the time.
- **Cosmetic edits are a coin flip for every signal.** Their meaning does not change, so no similarity signal can separate them. This caps every system's overall score.
- **The two signals are strong in different places.** TF-IDF is stronger on tiny edits, where the exact changed word matters; Granite is stronger on larger rewrites. That is why combining them works. Intervals within each group overlap, so treat this as a pattern, not a tested difference.

## The v2 system (D-034)

The app and CLI now run **TF-IDF + fine-tuned Granite**.

- **Promotion:** `uv run python -m spequlator.evaluation.v2 promote` copies run 3's Granite model to `artifacts/granite-ft` (hash-checked against the freeze) and writes `artifacts/thresholds_v2.json`. A copy, the eps table and a provenance record go to `results/v2/`.
- **Scales:** exactly those frozen for run 3 (TF-IDF 0.0908, Granite 0.0359). The app's combined score is therefore the test signal above, AUC 0.734.
- **Undecided band (eps):** chosen with v1's D-028 rule (best balanced accuracy on decided cases with coverage ≥ 60%). It was chosen on train data only: the 503 cross-fitted dev-project records the Granite model did not train on.

  | eps | Train coverage | Train balanced accuracy (decided) |
  |---|---|---|
  | 0.0878 | 70.8% | 0.735 |
  | **0.1507 (chosen)** | **63.5%** | **0.756** |
  | 0.2583 | 56.0% | 0.757 |

  For comparison, v1's eps was 0.1452, chosen on all 2,300 train records.
- **Not measured:** v2's decision rule (coverage and balanced accuracy of its findings) was **not evaluated on test**; that would be a fifth use of the split. The decision-rule numbers in `EVALUATION_RESULTS.md` are v1's.
- **Unchanged:** v1's artifacts, thresholds and results. All evaluation code still uses v1. To run v1 in the app, start the server with `SPEQULATOR_SYSTEM=v1`.
- **Word heatmap:** the report's heatmap now explains Granite's score. It removes one word at a time and re-scores, taking a few seconds on a laptop CPU.

## Test-split use

| Use | Run | What changed since the previous use |
|---|---|---|
| 1st | v1 (`frozen-eval`) | — |
| 2nd | Phase 2 run 1 | new training-split experiments |
| 3rd | Phase 2 run 2 | grid refined around run 1's pick; cross-encoder loss fixed |
| 4th | Phase 2 run 3 | Granite added; seed-averaged search; cross-encoder dropped |
| (descriptive) | Edit-size breakdown | none: regrouped run-3 results, nothing selected |

Every model and setting was chosen on dev projects before its test run, by a rule committed in advance. Even so, runs 2 and 3 were designed after earlier test results were known, so their test numbers are somewhat optimistic. The strongest evidence against overfitting the test set is that Granite's dev results predicted its test results almost exactly.

## Limitations

- These are proxy-task results (D-015), not detection of real-world drift.
- About a third of test updates change five or fewer tokens, and 7% are cosmetic. No similarity-based system can reach a high overall score on this benchmark.
- v2's eps is set on 503 records (v1: 2,300). Its decision-level behaviour on test is unmeasured.
- GPU training is not bit-reproducible: retraining moves test numbers by about 0.002.
- The edit-size groups were defined after seeing the results (descriptive only).

## Reproduce

```bash
# Kaggle: notebooks/phase2_train.ipynb at the run's pre-registration commit → phase2_outputs.zip
uv run python -m spequlator.evaluation.phase2 import ~/Downloads/phase2_runN_outputs.zip
uv run python -m spequlator.evaluation.phase2 freeze      # then commit and tag
uv run python -m spequlator.evaluation.phase2 run --confirm-frozen
uv run python -m spequlator.evaluation.edit_size          # run 3 only
uv run python -m spequlator.evaluation.v2 promote         # run 3 only
```
