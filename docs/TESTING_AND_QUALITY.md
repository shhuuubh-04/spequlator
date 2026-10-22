# Spequlator — Testing and quality plan

- **Version:** 1.2
- **Target:** at least 30 fast tests (< 20 s total, no model download) plus 2 slow tests marked `@pytest.mark.encoder`.

## Fixtures (`tests/fixtures/`)

- `codocbench_mini.jsonl`: 6 hand-picked **train** records (CC BY 4.0, attributed in the fixture README). Include one with a removed parameter, one with near-trivial docstring edits and one with Google-style `Args:`.
- `stale_param/{old.py,new.py,doc.txt}`: synthetic. The docstring names `timeout`, which is removed from the new code.
- `aligned/{code.py,doc.txt}`: synthetic. The docstring matches the code.

## Unit tests

| File | Cases |
|---|---|
| `test_preprocessing.py` (exists, extend) | `getHTTPResponse_code` becomes `get http response code`. `parse_ndiff` separates `-`/`+` lines and ignores `? `. Dedenting nested methods works. Empty input raises. |
| `test_rules.py` | R1 handles reST `:param x:`, Google `Args:` and NumPy styles. `self`/`cls` are ignored. `*args`/`**kwargs` names are handled. R2 ignores stopwords and tokens shorter than 3 characters, and does not fire when the token survives in the new code. |
| `test_tfidf.py` | Fitting is deterministic. Cosine of identical texts is 1.0, of disjoint texts 0.0. Empty documents give 0 without NaN. |
| `test_encoder.py` | Uses a fake encoder: output is normalised, truncation flag set past the limit, `EncoderUnavailable` gives a report with `encoder=null`. Includes one `@encoder`-marked real-model smoke test. |
| `test_report.py` | Decision-rule truth table (8 cases). Every evidence item is referenced in the explanation. Finding is always one of 3 values. No "confidence" or "probability" wording. |
| `test_codocbench.py` | Loads the mini fixture. Record ID is stable. A malformed JSONL line gives a clear error. A checksum mismatch raises `DataIntegrityError`. |
| `test_split_guard.py` | The TF-IDF artifact metadata says `fit_split == "train"`. `eval run --split test` refuses without frozen thresholds. Manual-review IDs are all in the test split and none are in train. |
| `test_stats.py` | Pairwise accuracy treats ties as 0.5. Bootstrap is reproducible with a fixed seed. The CI contains the point estimate. |

## Integration tests

- `test_cli.py`: see `CLI_SPEC.md` (8 cases) [R18].
- `test_api.py` uses FastAPI `TestClient` [R19]:
  - `/api/health` returns 200.
  - `/api/analyze` returns 200 in snapshot mode and 200 in change mode.
  - It returns 422 when `code` is empty and 422 when the input is too large.
  - `/api/analyze/example` returns 404 for an unknown ID.
  - The response validates against the `Report` schema.
  - The CLI and API give the **same JSON** for the same input. This is the shared-core check (FR-1).
- Frontend: one Vitest + Testing Library test that submits the form with `fetch` mocked, renders the finding and evidence, and renders the error state. If time runs out, replace it with a scripted manual check recorded in `docs/DEMO.md`.

## Quality gates (run in this order before the demo, at H9)

```bash
uv run ruff check . && uv run ruff format --check .
uv run pytest -q -m "not encoder"
uv run pytest -q -m encoder              # requires model cache
python -m json.tool decisions.json > /dev/null
uv run spequlator data verify
uv run spequlator analyze --old-code-file tests/fixtures/stale_param/old.py --new-code-file tests/fixtures/stale_param/new.py --docs-file tests/fixtures/stale_param/doc.txt
uv run uvicorn spequlator.api:app --port 8000 &  curl -s localhost:8000/api/health
cd frontend && npm run build && npm test -- --run
```

## Reproducibility record (`results/RUN_INFO.json`, written by `eval run`)

This file records:

- Python version and `uv.lock` hash
- `torch`, `transformers`, `sentence-transformers` and `scikit-learn` versions
- CoDocBench commit and file SHA-256 values
- Model ID and revision
- `max_seq_length`
- TF-IDF parameters and artifact SHA-256
- `thresholds.json` content
- Seeds (13 feasibility, 2026 evaluation)
- Timestamp and machine CPU/GPU

## Privacy and safety

- Pasted code is processed locally only. The API binds to `127.0.0.1` by default.
- Logs never contain request bodies. Only lengths and timings are logged.
- `trust_remote_code` is **never** enabled. UniXcoder does not need it (D-018).