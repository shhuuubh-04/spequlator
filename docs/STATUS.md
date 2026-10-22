# Spequlator — Project status

- **Date:** 2026-10-22
- **Version:** 1.2
- **Status:** Scope frozen and evidence-backed; ready to start the 10-hour build

## Frozen direction

- Code–documentation consistency analysis and explanation system, **change-aware first** (D-016).
- Interfaces: Typer CLI and React/Vite/TS frontend over one Python core via FastAPI (D-011, D-012 accepted).
- Primary dataset: CoDocBench, pinned and checksummed, CC BY 4.0 (D-023). SAFA is supplementary; SciCoQA is future work.
- Evaluation: stale-vs-updated proxy task (D-015), project-cluster bootstrap, one frozen test run (D-021).
- Signals:
  - TF-IDF delta-alignment (baseline)
  - UniXcoder (pretrained, D-018)
  - MiniLM fine-tuned on train (D-020, gated)
  - Rules R1 and R2 (D-017)
- Reports show evidence and uncertainty and may return `inconclusive`.

## Completed

- Dataset structure, overlap and traceability audits (v1.1).
- CoDocBench collection rule confirmed from the paper [R1], plus licence [R3], pinned commit and checksums.
- Train-only feasibility runs F1–F9: signal comparison, rules, encoder load and timing, fine-tune feasibility.
- Decisions D-015 to D-024 recorded; all docs updated to v1.2.

## Outstanding (the 10-hour build)

- Everything in `10_HOUR_PLAN.md` H0–H9.

## Change control

Any scope, dataset, architecture or evaluation change must be recorded as a new decision entry in root `decisions.json` and reflected in the relevant docs **before** implementation. This includes changes made at a cut line.