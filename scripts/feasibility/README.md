# Feasibility scripts (train split only)

These scripts produced the F-numbered findings in `docs/REFERENCES.md` and `docs/FEASIBILITY.md`. Each one takes the path to CoDocBench `train.jsonl` and **never** reads `test.jsonl`.

```bash
uv run python -I scripts/feasibility/stats.py   data/raw/codocbench/train.jsonl   # F1, F2
uv run python -I scripts/feasibility/stats2.py  data/raw/codocbench/train.jsonl   # F1 leakage, diff format
uv run python -I scripts/feasibility/spike.py   data/raw/codocbench/train.jsonl   # F3, F6
uv run python -I scripts/feasibility/spike3.py  data/raw/codocbench/train.jsonl   # F5 (needs docstring-parser)
uv run python -I scripts/feasibility/spike4.py  data/raw/codocbench/train.jsonl   # F4
uv run python -I scripts/feasibility/spike2.py  data/raw/codocbench/train.jsonl   # F7 (downloads models)
uv run python -I scripts/feasibility/spike5.py  data/raw/codocbench/train.jsonl   # F8
uv run python -I scripts/feasibility/spike6.py  data/raw/codocbench/train.jsonl   # F9 (fine-tune, ~6 min on 2 cores)
uv run python -I scripts/feasibility/spike7.py  data/raw/codocbench/train.jsonl   # F10
```

Environment used on 2026-10-22: Python 3.13, 2 CPU cores, 8 GB RAM, torch 2.14.1+cpu, transformers 5.20.2, sentence-transformers 6.2.0, scikit-learn 1.9.1. Seed 13.

`spike2.py` still includes the Jina model. It is expected to fail on transformers 5.x, which is finding F7.

These are throwaway research scripts, not part of the package. The production code in `src/spequlator/` re-implements the same logic with tests.