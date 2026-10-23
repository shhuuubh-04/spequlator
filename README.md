# Spequlator

Spequlator checks whether a function's documentation still matches its code, and explains why. Give it a docstring plus either the current code (**snapshot**) or the code before and after a change (**change**). It returns one of three findings, `potential_drift`, `no_obvious_drift` or `inconclusive`, together with the evidence, the signal values, what it could not check, and a suggested next step.

Findings are heuristics for review, not verdicts. Signal values measure shared words or meaning; they are not probabilities.

## How it works

| Part | What it does |
|---|---|
| TF-IDF delta | How much closer the docstring is to the new code than to the old code (identifier-aware word overlap). |
| MiniLM delta | The same comparison with sentence embeddings from `all-MiniLM-L6-v2`, fine-tuned on the CoDocBench train split (D-020). |
| Rule R1 | Parameters the docstring documents that the new signature no longer has (skipped when the function takes `**kwargs`). |
| Rule R2 | Words in the docstring that only appear in lines the change removed. |
| Decision rule | Averages the two scaled signals; a dead-band calibrated on train leaves unclear cases `inconclusive` (D-028). |

All analysis lives in `src/spequlator/`. The CLI and the local API are thin wrappers, and the web UI only displays reports. Everything runs on your own machine, CPU only.

## Setup

Needs Linux or WSL2, 8 GB RAM, [`uv`](https://docs.astral.sh/uv/), and Node.js 22 for the UI.

```bash
git clone https://github.com/shhuuubh-04/spequlator && cd spequlator
uv sync

# CoDocBench at the pinned commit (not stored in git)
git clone https://github.com/kunpai/codocbench /tmp/cdb
git -C /tmp/cdb checkout ee0256da15a07dcf265d5313fe51a269aa7268e0
mkdir -p data/raw/codocbench && cp /tmp/cdb/dataset/*.jsonl data/raw/codocbench/
uv run spequlator data verify

# Train-only artifacts: TF-IDF, signal caches, fine-tuned MiniLM, thresholds
uv run python -m spequlator.models.tfidf
uv run spequlator eval cache --split train
uv run python -m spequlator.evaluation.finetune
uv run spequlator eval calibrate --encoder minilm-ft
```

The fine-tune takes a while on CPU. Without it, `uv run spequlator analyze --no-encoder` still works with TF-IDF and the rules.

## Use it

**Command line**

```bash
# A dataset example (CoDocBench record id); --doc-version new tests the updated docstring
uv run spequlator analyze --example-id 8e8e00c86a25
uv run spequlator analyze --example-id 8e8e00c86a25 --doc-version new

# Your own files: change mode, or snapshot mode with --code-file
uv run spequlator analyze --docs-file doc.txt --old-code-file before.py --new-code-file after.py
uv run spequlator analyze --docs-file doc.txt --code-file current.py --format json
```

**Web UI** (two terminals)

```bash
uv run spequlator serve --port 8001                      # API on 127.0.0.1 only
cd frontend && echo "SPEQULATOR_API_PORT=8001" > .env.local && npm install && npm run dev
```

Then open http://localhost:5173. Use "Load dataset example", or paste your own docstring and code.

## Results

The test split was opened once, after freezing every setting (tag `frozen-eval`). The task is a **proxy**: tell the docstring the authors replaced ("stale") from the one they wrote ("updated"), for the same code change. It does not measure detection of real drift in the wild.

- Full numbers with 95% project-cluster CIs: [`docs/EVALUATION_RESULTS.md`](docs/EVALUATION_RESULTS.md), [`results/tables.md`](results/tables.md), [`results/figures/auc_ci.png`](results/figures/auc_ci.png).
- Comparing against the code change beats comparing against a snapshot of the code.
- The fine-tuned encoder alone does not beat TF-IDF; combined with TF-IDF it gives the best pairwise accuracy (the evaluation doc says whether that gain is statistically clear).
- The rules fire rarely but are much more frequent on stale docstrings, and give the most specific evidence.
- The manual review of 60 reports was **scored by an LLM, not a human** (D-029); see the evaluation doc for what it found.

## Limitations

- R1 only checks one direction: a newly added parameter that the docstring never mentions is not flagged.
- When TF-IDF and the encoder disagree, the combined score can still give a confident `no_obvious_drift`.
- Only the function and its docstring are inspected: no callers, runtime behaviour or other documentation.
- Long inputs are truncated to the encoder's token limit (the report says so).
- Python docstrings only.

## Development

```bash
uv run ruff check . && uv run ruff format --check . && uv run pytest -q
cd frontend && npm test -- --run && npm run build
```

Design and decisions: `docs/ARCHITECTURE.md`, `docs/EXPERIMENT_PLAN.md` and `decisions.json`. Demo script: `docs/DEMO.md`.

## Data and attribution

Uses **CoDocBench** by Pai, Devanbu and Ahmed, *CoDocBench: A Dataset for Code-Documentation Alignment in Software Maintenance*, MSR 2025 Data and Tool Showcase ([arXiv:2502.00519](https://arxiv.org/abs/2502.00519)), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The dataset is downloaded at a pinned commit and is not redistributed here.

Uses the `sentence-transformers/all-MiniLM-L6-v2` model (Apache 2.0) at a pinned revision.