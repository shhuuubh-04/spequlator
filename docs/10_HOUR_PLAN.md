# Spequlator — 10-hour end-to-end plan

- **Version:** 1.2 (replaces any earlier `10_HOUR_PLAN.md`)
- **Date:** 2026-10-22
- **Budget:** 600 minutes of focused work by one developer. Heavy compute runs **in the background while you code**: that overlap is what makes 10 hours enough.
- **Evidence:** every decision cites `REFERENCES.md` (R*) or train-only feasibility runs (F*, `FEASIBILITY.md`).

---

## 0. What we are building, in one paragraph

Spequlator takes documentation plus a **code change** (before → after) and reports whether the documentation still describes the old code. It combines four signals:

- A **TF-IDF delta-alignment** baseline.
- A **transformer delta-alignment** signal: pretrained UniXcoder, plus a MiniLM fine-tuned on CoDocBench train.
- Two **explainable rules:** a parameter mismatch, and a docstring mentioning identifiers deleted from the code.

It returns `potential_drift`, `no_obvious_drift` or `inconclusive`, together with the evidence lines and the uncertainties. The same Python core runs behind a Typer CLI and a FastAPI + React UI.

It is evaluated on CoDocBench's project-disjoint test split. The evaluation uses a **stale-vs-updated proxy task**: for each function, the old docstring stands in for "forgotten docs" and the developer's new docstring for "updated docs". It reports cluster-bootstrap confidence intervals and a 30-record manual review.

## 1. Why this design is strong (the evidence)

| Choice | Evidence |
|---|---|
| Change-aware (Δ) scoring on full old/new code is primary | Encoding code edits beats looking at current code alone: 77–81 vs 67 F1 [R4]. On our train data, TF-IDF Δ has AUC **0.724** vs **0.565** for snapshot similarity [F3, F4]. Similarity on diff lines alone is weaker (0.658) [F10]. |
| Proxy task instead of invented labels | CoDocBench keeps only commits where code **and** docstring changed [R1], so it has no real-drift labels, but old vs new versions give a clean counterfactual. This mirrors the dataset's own "closer to matching version" metric [R1]. |
| Explainable rules | OVERLAP(C, deleted) reaches 68 F1 in the literature [R4]. Our parameter rule fires 2.1× more on stale docs (15.3% vs 7.4%) [F5]. Our deleted-identifier rule fires 1.6× more (27.8% vs 17.7%) [F6]. |
| TF-IDF with identifier splitting | A standard, competitive preprocessing step [R13]. A TF-IDF baseline is precedent in the comment-coherence literature [R4, R6]. |
| UniXcoder (pretrained DL signal) | Apache-2.0, no `trust_remote_code` [R7]. In the snapshot setting it was the best of the encoders tested [F7]. Jina's code model **failed to load** on `transformers` 5.x [F7]. |
| Fine-tuned MiniLM (trained DL signal) | Pretrained encoders trail TF-IDF in Δ mode: AUC 0.632–0.641 vs 0.733 [F8]. One epoch on train triplets lifts MiniLM from 0.624 to 0.649 on held-out projects, and combined with TF-IDF it gives the best pairwise accuracy (0.778) [F9]. It trains in about 6 minutes on 2 CPU cores. |
| Inconclusive state and neutral language | Only 7–13% of code changes come with comment updates, and an un-updated comment isn't necessarily wrong [R5]. |
| Project-cluster bootstrap | The top 5 projects make up 29% of records [F1]. Bootstrap is the recommended way to get CIs for NLP metrics [R12, R17]. |
| CPU-only torch index | On Linux, PyPI `torch` pulls multi-GB CUDA wheels by default [R21]. |

## 2. Fixed decisions (recorded in `decisions.json`)

- D-015: proxy task.
- D-016: change and snapshot modes.
- D-017: rules plus a transparent decision rule with ε frozen on train.
- D-018: UniXcoder pinned, no remote code.
- D-019: degrade to TF-IDF and rules if the encoder is unavailable.
- D-020: fine-tuned MiniLM, behind a go/no-go gate.
- D-021: project-cluster bootstrap, single frozen test run.
- D-022: Vite proxy and localhost-only serving.
- D-012 changes from *proposed* to **accepted**.

## 3. Hour-by-hour plan

Times are elapsed from start. ⏳ marks background compute that starts at that point and is used later.

### H0 — 0:00–0:45 · Setup, data pins, dataset adapter (45 min)

1. Apply this docs pack and commit it (`docs: v1.2 evidence-backed plan`).
2. Add the dependencies:

   ```bash
   uv add typer fastapi "uvicorn[standard]" pydantic scikit-learn numpy scipy pandas pyarrow \
          sentence-transformers torch docstring-parser joblib rich matplotlib
   uv add --dev pytest ruff httpx
   ```

   Then add the CPU torch index to `pyproject.toml` before running `uv sync` [R21]. Use the snippet in §6.
3. Fetch the data at the pinned commit:

   ```bash
   git clone https://github.com/kunpai/codocbench /tmp/cdb && git -C /tmp/cdb checkout ee0256da15a07dcf265d5313fe51a269aa7268e0
   mkdir -p data/raw/codocbench && cp /tmp/cdb/dataset/*.jsonl data/raw/codocbench/
   sha256sum data/raw/codocbench/*.jsonl   # must match REFERENCES.md
   ```

4. ⏳ Pre-download the models at their pinned revisions, in the background:

   ```bash
   uv run python -c "from sentence_transformers import SentenceTransformer as S; S('microsoft/unixcoder-base', revision='5604afdc964f6c53782a6813140ade5216b99006'); S('sentence-transformers/all-MiniLM-L6-v2', revision='1110a243fdf4706b3f48f1d95db1a4f5529b4d41')"
   ```

5. Write `datasets/codocbench.py`: load, record ID, `verify_checksums`, `to_input(record, doc_version)`. Write `tests/test_codocbench.py` and the `tests/fixtures/codocbench_mini.jsonl` fixture (6 train records).

**Exit check:** `uv run pytest -q` is green, and the checksums match.

### H1 — 0:45–2:15 · Shared core (90 min)

| Min | Task | File |
|---|---|---|
| 0:45–1:00 | Pydantic `AnalysisInput` (snapshot or change, 20k-character limits) and the `Report` schema | `schemas.py` |
| 1:00–1:20 | Extend preprocessing: `split_identifiers`, `parse_ndiff` (drop `? ` lines), `dedent_code`, stopwords | `nlp/preprocessing.py` |
| 1:20–1:40 | Rules R1 (`ast` signature vs `docstring_parser` params; ignore `self`/`cls`) and R2 (removed-line tokens minus new-code tokens, ∩ docstring tokens, length ≥ 3) | `nlp/rules.py` |
| 1:40–1:55 | TF-IDF: fit on train (docstrings and code of both versions), persist with metadata `{fit_split: "train", sha256}` | `models/tfidf.py` |
| 1:55–2:15 | Decision rule (ε = 0 placeholder), evidence assembly, template explanations, uncertainties; `analyze()` | `pipeline/report.py`, `pipeline/analyze.py` |

Tests written alongside: `test_preprocessing`, `test_rules`, `test_tfidf`, `test_report` (decision truth table).

**Exit check:** about 20 tests pass, and `analyze()` on the `stale_param` fixture returns `potential_drift` with R1 evidence.

### H2 — 2:15–3:00 · Encoder and background caching (45 min)

1. `models/encoder.py`:
   - Lazy singleton, `revision` pinned, `normalize_embeddings=True`.
   - `max_seq_length` 512, or 256 if the machine has fewer than 8 cores (log which).
   - `truncated` flag set from tokenizer length.
   - `EncoderUnavailable` raised and caught in `analyze` (D-019).
   - In-memory LRU cache keyed by text hash.
2. `evaluation/proxy_task.py`: for a split, compute all signals for the stale and updated pairs and write `artifacts/eval_cache_{split}.parquet`.
3. ⏳ Start `uv run spequlator eval cache --split train` in the background. It embeds 4 texts per record. At 0.2 s per text on 2 cores [F7] that is about 30 minutes on 2 cores and about 8–10 minutes on 8 cores.
4. Start the CLI skeleton while it runs.

### H3 — 3:00–4:00 · CLI, calibration, fine-tune (60 min)

1. Finish the Typer CLI (`analyze`, `data verify`, `data examples`, `eval calibrate|cache|run|review-sample`) and `tests/test_cli.py` (8 cases, `CliRunner` [R18]).
2. `eval calibrate` (train only):
   - Grid-search ε for TF-IDF and the encoder (maximise balanced accuracy, coverage ≥ 60%).
   - Write `artifacts/thresholds.json`.
   - Print the train table.
3. ⏳ **D-020 fine-tune** (`evaluation/finetune.py`):
   - Model: MiniLM.
   - Data: (anchor c¹, positive d¹, hard negative d⁰).
   - Loss: MultipleNegativesRankingLoss.
   - Settings: 1 epoch, batch 8, lr 2e-5, `max_seq_length` 128, seed 13.
   - Steps: first on a project-disjoint 80/20 split of train, then on all of train.
   - Output: `artifacts/minilm-ft/`.
   - **Go/no-go gate (decide by 4:00):** keep it as a reported signal if dev Δ-AUC is ≥ the pretrained MiniLM's. Otherwise report it as a negative result. In both cases the plan continues unchanged.

### H4 — 4:00–5:00 · Freeze, then run the test once (60 min)

1. Commit `thresholds.json` plus the hashes of `tfidf.joblib` and `minilm-ft`, then `git tag frozen-eval`.
2. ⏳ `uv run spequlator eval run --split test --confirm-frozen`. This:
   - caches the test signals;
   - computes PA, AUC, decision outcomes, rule lift, strata and project-macro scores;
   - runs a 1,000-resample project-cluster bootstrap with paired difference CIs;
   - writes `results/metrics.json`, `tables.md`, `figures/*.png` and `RUN_INFO.json`.
3. While it runs, start the API (H5).

### H5 — 5:00–6:00 · FastAPI (60 min)

- `api.py` with `/api/health`, `/api/examples`, `/api/examples/{id}`, `/api/analyze` and `/api/analyze/example`.
- Warm the encoder in the background at startup. Return a uniform error JSON, with no stack traces.
- Add `spequlator serve` (uvicorn on `127.0.0.1:8000`).
- `tests/test_api.py` (`TestClient` [R19]), including the **CLI == API parity** test.

### H6 — 6:00–8:00 · Frontend (120 min)

| Min | Task |
|---|---|
| 6:00–6:15 | `npm create vite@latest frontend -- --template react-ts`; `server.proxy['/api'] = 'http://127.0.0.1:8000'` [R20] |
| 6:15–7:00 | Mode toggle, labelled panels, Analyze button, validation, example picker with the before/after docstring switch, diff block |
| 7:00–7:40 | Results: finding badge, summary, evidence list with token highlighting, two signal bars, uncertainties, Copy JSON / Download Markdown |
| 7:40–8:00 | Loading, error, encoder-unavailable and API-down states; < 768px stacking; `npm run build`; one Vitest test |

### H8 — 8:00–9:00 · Manual review and results write-up (60 min)

1. `eval review-sample --n 30 --seed 2026` → `results/manual_review.csv` (stratified 10/10/10; reports for d⁰ and d¹).
2. Score with the rubric (about 45 minutes).
3. Fill in `EVALUATION_RESULTS.md`: headline table with CIs, RQ1–RQ4 answers, strata figure, three worked examples (one success, one inconclusive, one failure), deviations and threats.
4. Pick 12 curated UI examples from the seeded test sample (no cherry-picking by outcome; record the IDs).

### H9 — 9:00–9:40 · Hardening and docs (40 min)

- Run every quality gate in `TESTING_AND_QUALITY.md`.
- Write README sections: what it is, quickstart (`uv sync` → `data` → `serve` → `npm run dev`), CLI examples, results summary, limitations, CoDocBench CC BY 4.0 attribution.
- Write `docs/DEMO.md`, a 5-minute script: stale vs updated docstring on the same example, then a manual paste, then a CLI JSON run, then the results table.

### H9:40–10:00 · Buffer, then tag `v1.0` (20 min)

## 4. Cut lines (decide at the checkpoint; never improvise)

| Checkpoint | If behind… | Cut |
|---|---|---|
| 3:15 | Encoder wrapper not working | Live UI/CLI uses `--no-encoder`. The encoder is still evaluated offline from the cache. |
| 4:00 | Fine-tune not finished | Report pretrained encoders only. Fine-tuning becomes future work (record it in `decisions.json`). |
| 5:45 | API incomplete | Keep only `/health` and `/analyze`. Examples are served from the static `frontend/public/examples.json`. |
| 7:30 | Frontend behind | Drop token highlighting and export. Keep the states. |
| 8:30 | Review behind | 20 records instead of 30. |
| **Never cut** | — | Split guard, frozen-threshold rule, core tests, CI reporting, the caveat language |

## 5. Definition of done (maps to PRD §10)

- [ ] `spequlator analyze` works in snapshot, change and example modes; JSON output validates.
- [ ] The UI completes both modes and a dataset example; all states are handled.
- [ ] One core: the CLI/API parity test passes.
- [ ] TF-IDF, UniXcoder and (if gated in) fine-tuned MiniLM signals all reported, with paired CIs vs TF-IDF.
- [ ] Reports show evidence and uncertainty; the manual review has been scored.
- [ ] At least 30 fast tests are green; ruff is clean.
- [ ] `RUN_INFO.json` is complete: revisions, checksums, seeds, versions.
- [ ] A fresh clone plus the README quickstart works.

## 6. `pyproject.toml` additions

```toml
[project.scripts]
spequlator = "spequlator.cli:app"

[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = [{ index = "pytorch-cpu" }]

[tool.pytest.ini_options]
markers = ["encoder: needs downloaded transformer weights (slow)"]

[tool.ruff]
line-length = 100
```

`.gitignore` additions: `data/raw/`, `data/processed/`, `artifacts/`, `frontend/node_modules/`, `frontend/dist/`, `__pycache__/`.

## 7. Compute budget (measured on 2 CPU cores, 7 GB RAM [F7, F9])

| Job | Size | Estimate (2 cores) | When |
|---|---|---|---|
| TF-IDF fit + all TF-IDF signals | 4,573 records | < 1 min | H1 |
| UniXcoder embeddings, train | 9,200 texts × 0.2 s | about 30 min | ⏳ H2 |
| UniXcoder embeddings, test | 9,092 texts | about 30 min | ⏳ H4 |
| MiniLM base embeddings, both splits | 18k texts × 0.02 s | about 6 min | ⏳ H2 |
| MiniLM fine-tune, 1 epoch, 1,575 dev-split triplets, then 2,300 final | batch 8, 128 tokens | 6.2 min measured (dev run), about 9 min for full train; 1.8 GB RAM | ⏳ H3 |
| Bootstrap, 1,000 × 7 signals | — | < 2 min | H4 |

A GPU or a machine with more cores shortens all of these. Nothing in the plan requires a GPU.