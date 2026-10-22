# Spequlator — Start here (builder handover)

- **Handover date:** 2026-10-23
- **For:** whoever builds Spequlator from this point
- **Time to finish this guide:** about 20–30 minutes, mostly downloads

The project is fully **planned, but no application code has been written yet**. This guide gets your machine to the exact starting line. After that, follow `docs/10_HOUR_PLAN.md` from step **H0 item 5**.

---

## 1. Read these first (about 15 minutes, in this order)

1. `docs/10_HOUR_PLAN.md`: the hour-by-hour build, cut lines and definition of done. **This is your main document.**
2. `docs/ARCHITECTURE.md`: modes, signals, rules, decision rule, report schema, module map and API.
3. `docs/EXPERIMENT_PLAN.md`: the proxy task, metrics and the one-time frozen test run.
4. `decisions.json`: D-001…D-024. Every choice is already made and justified, so don't re-decide anything.
5. Skim as needed: `FEASIBILITY.md` (why the design looks like this), `REFERENCES.md` (sources, checksums, model revisions), `CLI_SPEC.md`, `FRONTEND_SPEC.md` and `TESTING_AND_QUALITY.md`.

## 2. Repository state at handover

| Item | State |
|---|---|
| Docs v1.2 (`docs/`, `decisions.json`, `README_DOCS.md`) | ✅ Done and committed |
| Feasibility scripts (`scripts/feasibility/`) | ✅ Committed (train split only, for reference) |
| `.gitignore` (data, artifacts, caches, frontend build) | ✅ Committed |
| `pyproject.toml` | ✅ Dependencies added. CPU-only torch index (D-024). Entry point `spequlator = "spequlator.cli:app"`. pytest marker and ruff config added. |
| `uv.lock` | ✅ Committed, so `uv sync` reproduces the exact environment |
| `src/spequlator/nlp/preprocessing.py` + `tests/test_preprocessing.py` | ⚠️ Early stub from before the plan. **Extend it, don't replace it** (ARCHITECTURE module map). |
| `src/spequlator/{evaluation,models,pipeline}/` | Empty folders, to be filled in |
| `src/spequlator/cli.py` | ❌ Not written yet. **`uv run spequlator` will error until H3. That's expected.** |
| Dataset files (`data/raw/codocbench/`) | ❌ Not in git (licence and size). Download them in step 3.3 below. |
| Model weights | ❌ Not in git. Download them in step 3.4 below. |

## 3. Setup (do once)

### 3.1 Prerequisites

- Linux or WSL2, at least 8 GB RAM. 8+ CPU cores recommended. No GPU needed.
- `git`, and `uv` (https://docs.astral.sh/uv/). `uv` installs the project's Python 3.13 by itself.
- Node.js (current LTS) and `npm`. These are needed only from H6 (frontend).
- Internet access to github.com, pypi.org, download.pytorch.org and huggingface.co.

> On Ubuntu, the command is `python3`, not `python`. Inside this project, always use **`uv run python`**.

### 3.2 Clone and install

```bash
git clone https://github.com/shhuuubh-04/spequlator ~/spequlator
cd ~/spequlator
uv sync
uv run python -c "import torch; print(torch.__version__)"
```

✅ This must print a version ending in **`+cpu`**. If it shows a CUDA build or starts downloading gigabytes, the CPU index in `pyproject.toml` isn't being picked up. Stop and fix that first (see `REFERENCES.md`, R21).

### 3.3 Download CoDocBench at the pinned commit and verify it

```bash
git clone https://github.com/kunpai/codocbench /tmp/cdb
git -C /tmp/cdb checkout ee0256da15a07dcf265d5313fe51a269aa7268e0
mkdir -p data/raw/codocbench && cp /tmp/cdb/dataset/*.jsonl data/raw/codocbench/
sha256sum data/raw/codocbench/*.jsonl
wc -l data/raw/codocbench/*.jsonl
```

✅ The output must match **exactly**:

```
c0e8563af0baf9eab4fe1341fd0bf2099ec41030fd5c2224f1c3803a712c21d4  data/raw/codocbench/codocbench.jsonl
74e3da99744a43bdf1be77c57eb1069548911c30fd931a49bbc7d0d5050dcdea  data/raw/codocbench/test.jsonl
9eef860afedcbf059a4f2e408cafbaa6c61ffbf4369e687a9b45ae80f7ac7c6d  data/raw/codocbench/train.jsonl
```

There should be 4,573, 2,273 and 2,300 lines respectively. The licence is CC BY 4.0: attribute it in the README.

### 3.4 Pre-download the models (run in a second terminal; leave it running)

```bash
cd ~/spequlator && uv run python -c "from sentence_transformers import SentenceTransformer as S; S('microsoft/unixcoder-base', revision='5604afdc964f6c53782a6813140ade5216b99006'); S('sentence-transformers/all-MiniLM-L6-v2', revision='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'); print('models ready')"
```

✅ It prints `models ready`. UniXcoder may warn that it is creating a model with **mean pooling**. That's expected and matches the feasibility runs.

### 3.5 Sanity check

```bash
uv run pytest -q
```

✅ The existing preprocessing tests pass.

### 3.6 Optional: reproduce one feasibility number (about 10 seconds)

```bash
uv run python -I scripts/feasibility/spike4.py data/raw/codocbench/train.jsonl
```

✅ It prints `Delta-alignment TF-IDF pooled AUC (stale=old_doc): 0.724`, matching `FEASIBILITY.md` F4. If it does, your data and environment are right.

## 4. Where to start building

Open `docs/10_HOUR_PLAN.md` and begin at **H0, item 5** (dataset adapter `datasets/codocbench.py` and its tests). Items 1–4 of H0 are covered by this guide.

The clock starts at about **0:30**, so you have about 9.5 hours for the rest.

## 5. Rules you must not break

1. **Never open `test.jsonl` for anything except the single frozen run at H4.** That means no fitting TF-IDF on it, no thresholds, no looking at examples. Choose UI examples only after H4 (D-010, D-021).
2. **All analysis logic lives in `src/spequlator/`.** The CLI and API are thin adapters, and the frontend computes nothing (D-011).
3. **Never set `trust_remote_code=True`** (D-018). Use the pinned model revisions.
4. **Proxy results are "proxy".** Never describe them as real-drift detection accuracy (D-015). Neutral finding labels; never call a result a "bug" or a "confidence".
5. **Changing a decision requires a new entry in `decisions.json` first**, including any cut made at a §4 cut line in the plan.

## 6. Known gotchas (already hit during planning)

| Symptom | Cause / fix |
|---|---|
| `bash: python: command not found` | Use `uv run python` (or `python3`) |
| `uv run spequlator` → import error | `cli.py` doesn't exist until H3. Expected. |
| `ImportError … find_pruneable_heads_and_indices` | You loaded a `trust_remote_code` model (e.g. Jina) on transformers 5.x. Use UniXcoder or MiniLM (F7). |
| Fine-tune killed or out of memory | Use batch 8 and `max_seq_length` 128 (F9). Batch 16 ran out of memory at 8 GB RAM. |
| `pyproject.toml` "duplicate key" | A TOML section or key was added twice. Keep exactly one `[project.scripts]` with one `spequlator = …` line. |
| Huge torch download | The CPU index isn't applied. See 3.2. |

## 7. Commit conventions

- Small commits per plan block, for example `feat(core): rules R1/R2 + tests`.
- Tag `frozen-eval` immediately before the H4 test run, and `v1.0` at the end.
- Never commit `data/raw/`, `artifacts/` or model weights. The `.gitignore` already covers them.
- When done, update `docs/STATUS.md` and fill in `docs/EVALUATION_RESULTS.md`.