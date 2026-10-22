# Spequlator — Feasibility study (train split only)

- **Date:** 2026-10-22
- **Purpose:** fix design choices and pre-register expectations *before* the build, without touching `test.jsonl`.
- **Environment:** 2 CPU cores, 8 GB RAM, no GPU. Python 3.13, torch 2.14.1+cpu, transformers 5.20.2, sentence-transformers 6.2.0, scikit-learn 1.9.1.
- **Scripts:** `scripts/feasibility/`. Seed 13 throughout.

## Setup

Proxy task (D-015): for each record, the **stale** pair is the old docstring against the code change, and the **updated** pair is the new docstring against the same change.

- **Pairwise accuracy (PA):** how often the signal rates the updated docstring above the stale one. Ties count 0.5; chance is 0.5.
- **AUC:** pooled ROC-AUC with stale as the positive class. It shows whether *one global threshold* separates the two.

Three evaluation sets were used:

- **Full train:** 2,300 records.
- **Sample:** 300 random train records.
- **Dev:** 725 records from 20 train projects held out of the fine-tuning set (project-disjoint, like the real split).

## Results

| ID | Signal | Set | PA | AUC | Notes |
|---|---|---|---|---|---|
| F3 | TF-IDF snapshot `cos(new code, doc)` | full train | 0.652 (+7.4% ties) | 0.565 | Weak global threshold |
| F4 | **TF-IDF Δ** `cos(doc,new) − cos(doc,old)` | full train | 0.704 (+12.2% ties) | **0.724** | Δ < 0 for 61.8% of stale vs 28.5% of updated |
| F7 | TF-IDF snapshot, identifier split | sample | 0.640 | 0.558 | Without split: 0.643 / 0.560, essentially equal [R13] |
| F7 | UniXcoder snapshot (512) | sample | 0.647 | 0.549 | 0.195 s per text |
| F7 | MiniLM snapshot (256) | sample | 0.570 | 0.543 | 0.026 s per text |
| F7 | Jina v2 code | — | — | — | **Failed to load** on transformers 5.x (`trust_remote_code`) |
| F8 | **TF-IDF Δ** | sample | 0.797 | **0.733** | |
| F8 | UniXcoder Δ (512) | sample | 0.738 | 0.641 | |
| F8 | MiniLM Δ (256) | sample | 0.708 | 0.632 | |
| F8 | st-codesearch-distilroberta Δ (128) | sample | 0.682 | 0.635 | No licence; not used |
| F9 | **TF-IDF Δ** | dev | 0.760 | **0.693** | |
| F9 | MiniLM Δ, pretrained (128) | dev | 0.672 | 0.624 | |
| F9 | MiniLM Δ, **fine-tuned** 1 epoch (128) | dev | 0.690 | 0.649 | +0.025 AUC over pretrained. Training took 371 s on 2 cores, 1.8 GB RSS. Batch 16 ran out of memory at 8 GB RAM, so use batch 8. |
| F9 | TF-IDF Δ + fine-tuned Δ (z-score average) | dev | **0.778** | 0.692 | Best PA; AUC equal to TF-IDF |
| F10 | TF-IDF explicit-edit `cos(doc,+lines) − cos(doc,−lines)` | dev | 0.746 | 0.658 | Worse than full-code Δ |
| F10 | MiniLM explicit-edit (128) | dev | 0.694 | 0.595 | |
| F10 | UniXcoder explicit-edit (256) | dev | 0.697 | 0.614 | |
| F5 | R1 parameter mismatch | full train | fires 15.3% stale / 7.4% updated | — | Lift 2.1×; `ast` parses 100%; 49.8% of records document parameters |
| F6 | R2 deleted-identifier mention | full train | fires 27.8% stale / 17.7% updated | — | Lift 1.6× |

## What this changes in the plan

1. **Change mode is primary.** Δ beats snapshot for every signal: TF-IDF AUC 0.724 vs 0.565. This matches the just-in-time finding in prior work [R4].
2. **Full-code Δ, not diff-lines-only.** Unlike Panthaplackel et al.'s learned edit encoders [R4], simple similarity on added/removed lines is weaker here (F10). Diff lines are used for rule R2 and for showing evidence.
3. **The honest expectation for RQ2 is that zero-shot encoders lose to TF-IDF.** A likely reason is that docstring updates in CoDocBench are often lexical: renamed or removed parameters and identifiers. Fine-tuning narrows the gap (F9), and combining it with TF-IDF gives the best pairwise accuracy. The plan therefore treats deep learning as a fine-tuned, complementary signal (D-020) and reports the comparison with paired CIs.
4. **Rules are worth their 20 minutes.** They have a clear lift and give exact, human-checkable evidence (F5, F6).
5. **Ops:** no `trust_remote_code` (F7); CPU torch index [R21]; fine-tune with batch 8, max 128 tokens (F9); UniXcoder at 256 tokens on small machines.

## Caveats

- The sample (n = 300) and dev (n = 725, 20 projects) sets are small. Their CIs are wide (roughly ±0.03–0.05 AUC), so they are used for **design and pre-registration only**, never as reported results.
- MiniLM was evaluated at 128 tokens in F9 but at 256 in F8, which explains the small differences between rows.
- All figures are proxy-task numbers (D-015), not real-drift detection rates.