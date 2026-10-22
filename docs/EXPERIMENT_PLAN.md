# Spequlator — Experiment plan

- **Version:** 1.2 (supersedes 1.1)
- **Date:** 2026-10-22
- **Status:** Pre-registered. Hypotheses and expected ranges are fixed from train-only feasibility runs (`FEASIBILITY.md`) **before** the test split is opened.

## Research questions

- **RQ1 (change vs snapshot):** Does change-aware delta-alignment detect stale documentation better than snapshot similarity?
- **RQ2 (classical vs deep):** Do transformer signals (pretrained, and fine-tuned on train) beat a TF-IDF baseline on CoDocBench's project-disjoint test split? Do they add complementary information when combined?
- **RQ3 (explainable rules):** How often do rules R1 and R2 fire on stale vs updated documentation, and what lift do they provide?
- **RQ4 (report quality):** Are the generated reports faithful to the evidence, specific, and appropriately uncertain (manual rubric)?

The experiment does **not** claim five-class classification, real-drift detection rates, or software-correctness proof (D-003, D-007).

## Proxy task (D-015)

For each CoDocBench record *i* with old/new code (c⁰, c¹) and old/new docstring (d⁰, d¹):

| Pair | Docstring | Code context | Proxy label |
|---|---|---|---|
| stale | d⁰ | c⁰ → c¹ | 1 (should be flagged) |
| updated | d¹ | c⁰ → c¹ | 0 (should not be flagged) |

Justification: CoDocBench records are commits in which the developer changed both code and docstring [R1]. So d⁰ is a docstring the developer judged to need updating for c¹. This mirrors CoDocBench's own "closer to the matching version" criterion [R1].

Caveat: near-trivial docstring edits (25.3% of train [F2]) make d⁰ effectively acceptable. They are reported as a separate stratum, and the headline numbers are given both with and without them.

## Signals compared

| Signal | Snapshot form | Change form (Δ) |
|---|---|---|
| TF-IDF (identifier-split, `sublinear_tf`, `min_df=2`, fit on train) [R13, R16] | cos(d, c¹) | cos(d, c¹) − cos(d, c⁰) |
| UniXcoder pretrained, mean-pooled, normalised, max 512 tokens [R7] | same | same |
| MiniLM pretrained (all-MiniLM-L6-v2) [R8] | same | same |
| MiniLM fine-tuned on train triplets (c¹, d¹, d⁰) with MultipleNegativesRankingLoss (D-020) | same | same |
| R1 parameter mismatch [R14, R15] | binary | binary |
| R2 deleted-identifier mention [R4] | — | binary |
| Combined decision rule (D-017) | 3-state | 3-state |

## Protocol

1. **Train only:** fit TF-IDF; fine-tune MiniLM (on a project-disjoint 80/20 split of train to pick epochs; final model trained on all of train); grid-search dead-bands ε; compute train/dev metrics. Commit `artifacts/thresholds.json` and model hashes, then tag `frozen-eval`.
2. **Test, once:** `spequlator eval run --split test --confirm-frozen`. Any later change is reported as a post-hoc deviation in `EVALUATION_RESULTS.md`.
3. Seeds: 13 for feasibility and fine-tuning, 2026 for bootstrap and review sampling.

## Metrics

- **Pairwise accuracy (PA):** share of records where the signal rates d¹ above d⁰. Ties count 0.5; chance is 0.5. This is the per-function view.
- **Pooled ROC-AUC:** stale vs updated pairs pooled, with score = −signal. This is the "global threshold" view the tool actually uses.
- **Decision-rule outcomes:** for stale and updated pairs separately, the % `potential_drift` / `no_obvious_drift` / `inconclusive`. Also coverage (1 − inconclusive) and proxy precision on decided cases.
- **Rule lift:** firing rate on stale ÷ firing rate on updated, plus coverage.
- **Uncertainty:** 95% CIs from a **project-cluster bootstrap** (1,000 resamples) [R12, R17]. Projects are resampled because the top 5 projects make up 29% of records [F1]. **Paired** bootstrap CIs are given for the differences (encoder − TF-IDF), (Δ − absolute) and (combined − TF-IDF). A difference is called significant only if its 95% CI excludes 0.
- **Strata:** docstring edit ratio bins [0, 0.7), [0.7, 0.9), [0.9, 0.95), [0.95, 1]. Project-macro averages.
- **Operational:** encoder truncation rate, p50/p95 latency per analysis on CPU.

## Pre-registered expectations (from train-only feasibility, `FEASIBILITY.md`)

| Hypothesis | Train evidence | Expected on test |
|---|---|---|
| H1: Δ > snapshot for TF-IDF | AUC 0.724 vs 0.565 (full train) [F3, F4] | Δ AUC ≈ 0.68–0.75; paired CI excludes 0 |
| H2: pretrained encoders Δ ≤ TF-IDF Δ | 300-record sample: UniXcoder 0.641, MiniLM 0.632 vs TF-IDF 0.733 [F8] | Encoder AUC below TF-IDF. Report as a finding: docstring updates are often lexical (renamed or removed identifiers). |
| H3: fine-tuning improves the encoder, and combining it with TF-IDF helps | Dev (20 held-out train projects): MiniLM 0.624 → 0.649 AUC after fine-tuning; TF-IDF + fine-tuned PA 0.778 vs 0.760 for TF-IDF alone [F9] | Fine-tuned > pretrained MiniLM; combination PA ≥ TF-IDF. The paired CI may include 0, which is reported as such. |
| H4: rules have high lift and low coverage | R1 15.3% vs 7.4% (2.1×); R2 27.8% vs 17.7% (1.6×) [F5, F6] | Similar lifts; together they cover ≈ 35–45% of stale pairs |

Results contradicting these expectations are reported as they are.

## Manual review (RQ4)

- Sample 30 test records (seed 2026), stratified 10/10/10 by the tool's finding on the **stale** pair. For each, review the report for both d⁰ and d¹ (60 reports, about 45 minutes).
- Rubric, 0–2 each:
  - **Evidence fidelity:** every evidence item is literally present in the input.
  - **Specificity:** names concrete identifiers or lines.
  - **Uncertainty calibration:** caveats match the evidence strength.
- Add one binary judgement: *"Would a reviewer agree the docstring needs an update?"* These are project-created exploratory annotations, not dataset ground truth. If a second person is available, double-annotate 15 reports and report Cohen's κ.

## Threats to validity

- Proxy labels ≠ real drift: no observed un-updated docstrings exist in CoDocBench [R1].
- Not updating a comment is not necessarily wrong [R5].
- Diffs show one function, not the whole repository.
- Python only. Projects are skewed toward a few large ones [R1, F1].
- Truncation of long functions at 512 tokens (about the longest 10%) [F1].
- Manual review is single-annotator unless κ is reported.

## Outputs

`results/metrics.json`, `results/tables.md`, `results/figures/auc_ci.png`, `results/figures/strata.png`, `results/manual_review.csv`, `results/RUN_INFO.json`, and `docs/EVALUATION_RESULTS.md`.