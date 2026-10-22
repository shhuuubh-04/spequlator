# Spequlator — CLI specification

- **Version:** 1.2
- **Framework:** Typer. Tests use `typer.testing.CliRunner` [R18].
- **Entry point:** `[project.scripts] spequlator = "spequlator.cli:app"`. Run it with `uv run spequlator …`.

## Commands (implement exactly these; document nothing else)

```bash
# Snapshot mode
spequlator analyze --code-file f.py --docs-file doc.txt
spequlator analyze --code-file f.py --docs-text "Returns active users."

# Change mode (primary)
spequlator analyze --old-code-file old.py --new-code-file new.py --docs-file doc.txt

# Dataset example (change mode); --doc-version picks which docstring is tested
spequlator analyze --example-id 3f9a1c2b7d10 --doc-version old

# Any of the above with machine-readable output
spequlator analyze ... --format json
spequlator analyze ... --no-encoder        # TF-IDF + rules only (fast, offline)

# Data and evaluation
spequlator data verify                      # SHA-256 check of data/raw/codocbench/*.jsonl
spequlator data examples --split test --limit 20
spequlator eval calibrate                   # TRAIN only → artifacts/thresholds.json
spequlator eval run --split test --confirm-frozen   # one-shot frozen test run → results/
spequlator eval review-sample --n 30 --seed 2026
```

## Human-readable output (Rich or plain text)

```
Finding:   POTENTIAL DRIFT  (heuristic — review recommended)
Summary:   The docstring documents parameter `timeout`, which no longer exists in the new code.
Evidence:
  [R1] documented but not in signature: timeout
  [R2] docstring mentions `retry_count`, removed in: - for i in range(retry_count):
Signals (similarity/relatedness, not probabilities):
  TF-IDF delta     -0.084
  Encoder delta    -0.031   (microsoft/unixcoder-base@5604afd)
Uncertainty:
  - Diff shows only this function; callers and runtime behaviour not inspected.
Next step:  Check whether `timeout` handling moved elsewhere; update :param: list.
```

JSON output is exactly the `Report` schema in `ARCHITECTURE.md`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Analysis completed. A missing encoder still exits 0, with `signals.encoder = null` and a warning. |
| 2 | Invalid input: missing pair, empty text, too large, unknown `--example-id`, or conflicting flags |
| 3 | Data or artifact error: checksum mismatch, missing `tfidf.joblib` or `thresholds.json` |
| 1 | Unexpected runtime failure. A one-line message is printed; `--debug` shows the traceback. |

`eval run --split test` refuses to run without `--confirm-frozen`, and also refuses if `artifacts/thresholds.json` is missing. This protects the held-out split (D-010).

## Validation

- Exactly one input form is allowed: snapshot pair, change triple, or `--example-id`.
- Empty or whitespace-only text is rejected.
- Each input is limited to 20,000 characters. Nothing is silently truncated: the encoder truncation is reported in `signals.encoder.truncated`.

## Tests (`tests/test_cli.py`)

1. `--help` lists the commands.
2. Snapshot mode on fixture files: exit 0, finding is one of the 3 states.
3. Change mode with a fixture whose old doc names a removed parameter: `potential_drift` with R1 evidence.
4. `--format json` output parses and validates against `Report`.
5. Missing `--docs-file`: exit 2.
6. Unknown example ID: exit 2.
7. `--no-encoder` gives `signals.encoder == null`, exit 0.
8. `eval run --split test` without `--confirm-frozen`: exit 2.