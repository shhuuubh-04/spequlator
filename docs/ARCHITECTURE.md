# Spequlator — System architecture

- **Version:** 1.2 (supersedes 1.1)
- **Date:** 2026-10-22

## Overview

```text
 React/Vite/TS UI  ──HTTP/JSON (/api via Vite proxy [R20])──►  FastAPI adapter
                                                                   │
 Typer CLI ───────────────────────────────────────────────────────►│
                                                                   ▼
                                         spequlator.pipeline.analyze(AnalysisInput) -> Report
                                                                   │
        ┌──────────────┬───────────────┬───────────────┬───────────┴───────────┐
        ▼              ▼               ▼               ▼                       ▼
  nlp.preprocessing  nlp.rules     models.tfidf    models.encoder        pipeline.report
  (split ids,        (R1 params,   (fit on TRAIN,  (UniXcoder, lazy,     (decision rule,
   parse ndiff,       R2 deleted-   joblib)         cached, optional)     evidence,
   dedent/ast)        identifier)                                         explanation)
                                                                   ▲
                                         datasets.codocbench (read-only adapter, checksum verify)
```

**Architectural rule (unchanged):** all analysis logic lives in the Python package. The CLI and API are thin adapters. The frontend renders the report and computes nothing.

## Analysis modes (D-016)

| Mode | Inputs | Why |
|---|---|---|
| **Change mode** (primary) | `documentation`, `old_code`, `new_code` | Encoding the code change is what makes detection work. It beats looking at current code alone in the literature [R4] and in our data: TF-IDF AUC 0.724 vs 0.565 [F3, F4]. |
| **Snapshot mode** | `documentation`, `code` | Needed for quick manual checks. Absolute similarity is weak [F3, F7], so this mode relies on rule R1, and the score signals only move the finding at the extremes. It returns `inconclusive` more often, by design. |

A CoDocBench example opens in change mode. The user picks which docstring to test: **pre-commit (old)** or **post-commit (new)**. The demo then shows the same code change judged against a stale and an updated docstring side by side.

## Signals

| ID | Signal | Change mode | Snapshot mode | Evidence shown |
|---|---|---|---|---|
| S1 | TF-IDF delta-alignment | `cos(doc,new) − cos(doc,old)` | `cos(doc,code)` | Top overlapping and lost terms |
| S2 | Encoder delta-alignment | Same, using normalised embeddings. Live model: the fine-tuned MiniLM if it passes the D-020 gate (task-specific, about 10× faster than UniXcoder [F7, F9]), otherwise UniXcoder. All encoders are reported in the evaluation. | `cos(doc,code)` | — (score only) |
| R1 | Parameter mismatch | Docstring-documented parameters (`docstring_parser` [R14]) minus `ast` signature parameters of the new code [R15] | Same | Parameter names; the `def` line |
| R2 | Deleted-identifier mention | Identifier tokens in the docstring that appear in removed `ndiff` lines but **not** in the new code (adapted from OVERLAP(C, deleted) [R4]) | n/a | Tokens plus the removed diff lines |

Preprocessing details:

- Split CamelCase and snake_case and lowercase the result [R13].
- For R2, drop tokens shorter than 3 characters and English stopwords.
- Drop `? ` hint lines from ndiff.
- Dedent the code before calling `ast`.
- The TF-IDF vectorizer is fitted on **train-split** docstrings and code only (`sublinear_tf=True`, `min_df=2`) [R16] and persisted to `artifacts/tfidf.joblib`.

## Decision rule (D-017): transparent, thresholds frozen on train

```
R  = R1 fires or R2 fires                 # rule evidence
S1, S2 = delta signals; ε1, ε2 = dead-bands learned on TRAIN only (artifacts/thresholds.json)

potential_drift   if R  or (S1 < −ε1 and S2 < −ε2)
no_obvious_drift  if not R and S1 > +ε1 and S2 > +ε2      (snapshot mode: both above high quantile)
inconclusive      otherwise; also forced if doc < 5 words, encoder unavailable AND |S1| ≤ ε1,
                  or input truncated beyond 50%
```

ε is picked by a grid search on train to maximise balanced accuracy over decided cases, with coverage (share not `inconclusive`) ≥ 60%. It is then frozen before the single test run.

The finding states remain reviewer-facing heuristics, not ground truth (D-003, D-007).

## Report schema (Pydantic v2, `spequlator/schemas.py`)

```jsonc
{
  "schema_version": "1.2",
  "mode": "change" | "snapshot",
  "source": {"kind": "manual" | "codocbench", "record_id": "…", "project": "…", "doc_version": "old" | "new"},
  "finding": "potential_drift" | "no_obvious_drift" | "inconclusive",
  "summary": "one sentence, template-generated",
  "observations": ["objective facts, e.g. 'parameter `timeout` removed from signature'"],
  "evidence": [{"kind": "rule_r1"|"rule_r2"|"diff"|"term_overlap", "text": "…", "lines": ["- def f(x, timeout):"]}],
  "signals": {
    "tfidf": {"value": 0.0, "kind": "delta" | "absolute"},
    "encoder": {"value": 0.0, "kind": "delta" | "absolute", "model": "microsoft/unixcoder-base@5604afd", "truncated": false} | null
  },
  "explanation": "constrained template: evidence → possible implication",
  "uncertainties": ["…"],
  "review_recommended": true,
  "meta": {"thresholds_version": "…", "tfidf_artifact_sha256": "…", "elapsed_ms": 0}
}
```

The explanation is **template-based** (D-009): every sentence is traceable to a field in `evidence` or `signals`. No free-text generation is used.

## Module map (fits the existing `src/spequlator/` layout)

| Path | Responsibility |
|---|---|
| `schemas.py` | `AnalysisInput`, `Report`, `Evidence`, `Signals` (Pydantic) |
| `nlp/preprocessing.py` (exists, extend) | `split_identifiers`, `normalize_text`, `parse_ndiff`, `dedent_code`, length limits |
| `nlp/rules.py` | `param_mismatch()`, `deleted_identifier_mentions()` |
| `models/tfidf.py` | `fit_tfidf(train)`, `load()`, `cosine()` |
| `models/encoder.py` | Lazy singleton and LRU cache. `encode()` with normalisation, `truncated` flag, and a typed `EncoderUnavailable` error |
| `pipeline/analyze.py` | `analyze(AnalysisInput) -> Report`, the single entry point |
| `pipeline/report.py` | Decision rule, explanation templates, uncertainty list |
| `datasets/codocbench.py` | `load_split()`, `get_record(id)`, `verify_checksums()`, `to_input(record, doc_version)` |
| `evaluation/proxy_task.py` | Builds stale/updated pairs, computes all signals, caches to `artifacts/eval_cache_{split}.parquet` |
| `evaluation/stats.py` | Pairwise accuracy, AUC, project-cluster bootstrap CIs, stratification |
| `evaluation/calibrate.py` | Learns ε on train and writes `artifacts/thresholds.json` |
| `evaluation/finetune.py` | D-020 contrastive fine-tune on train triplets → `artifacts/minilm-ft/` (with `fit_split: train` metadata) |
| `evaluation/manual_review.py` | Seeded stratified sample → CSV for scoring |
| `cli.py` | Typer app (`analyze`, `data verify`, `data examples`, `eval calibrate`, `eval run`) |
| `api.py` | FastAPI app |
| `frontend/` (repo root) | Vite React TS app |
| `artifacts/` (git-ignored) | `tfidf.joblib`, `thresholds.json`, embedding caches |
| `results/` (committed) | `metrics.json`, `tables.md`, `figures/*.png`, `manual_review.csv` |

## API contract

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/api/health` | — | `{"status":"ok","tfidf":true,"encoder":"ready" or "loading" or "unavailable"}` |
| GET | `/api/examples?split=test&limit=50&q=` | — | `[{record_id, project, function, doc_edit_ratio}]` (curated demo list first) |
| GET | `/api/examples/{record_id}` | — | Old and new code, old and new doc, diffs |
| POST | `/api/analyze` | `{"documentation": str, "code": str}` (snapshot mode) or `{"documentation": str, "old_code": str, "new_code": str}` (change mode) | `Report` |
| POST | `/api/analyze/example` | `{"record_id": str, "doc_version": "old" or "new"}` | `Report` |

Limits: each text field is at most 20,000 characters, otherwise the request returns 422. Errors use the shape `{"error": {"code", "message", "field"}}` and never include stack traces.

## Runtime and failure behaviour

- The encoder loads in the background at API startup, so `/health` reports `loading`. If loading fails, the encoder is `unavailable`, the report contains `signals.encoder = null`, and an uncertainty is added. TF-IDF and the rules still run (D-019).
- Missing or empty diffs: change-based rules are skipped and the report says so. Diffs are never fabricated.
- Invalid or oversized input returns 422 from the API and exit code 2 from the CLI.
- Source text never leaves the machine. Model weights are downloaded once, pinned by revision.