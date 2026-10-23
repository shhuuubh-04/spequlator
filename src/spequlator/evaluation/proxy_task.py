"""Stale-vs-updated proxy task signals, cached per split (D-015).

For every CoDocBench record, the SAME code change (old -> new) is scored against:
  stale   = the old docstring (simulates forgotten docs)
  updated = the developer's new docstring
These are proxy labels from the dataset's construction, never real-drift ground truth.

Usage (background job while you code, docs/10_HOUR_PLAN.md H2):
  uv run python -m spequlator.evaluation.proxy_task --split train
  uv run python -m spequlator.evaluation.proxy_task --split train --encoder unixcoder
The test split is refused unless --allow-test is given (only at the frozen H4 run).
"""

from __future__ import annotations

import argparse
import difflib
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from spequlator.datasets.codocbench import CodocRecord, load_split
from spequlator.models import tfidf as tfidf_mod
from spequlator.models.base import Encoder
from spequlator.nlp.rules import deleted_identifier_mentions, param_mismatch
from spequlator.paths import artifacts_dir

PAIRS = ("stale", "updated")


class FrozenSplitError(RuntimeError):
    """The held-out test split may only be scored in the frozen evaluation run (D-010, D-021)."""


def cache_path(split: str, part: str) -> Path:
    return artifacts_dir() / f"signals_{split}_{part}.parquet"


def _doc(rec: CodocRecord, pair: str) -> str:
    return rec.old_doc if pair == "stale" else rec.new_doc


def base_signals(records: list[CodocRecord], tfidf: tfidf_mod.TfidfModel) -> pd.DataFrame:
    """TF-IDF + rule signals for both pairs of every record."""
    rows = []
    for rec in records:
        row = {
            "record_id": rec.record_id,
            "split": rec.split,
            "project_key": rec.project_key,
            "doc_edit_ratio": difflib.SequenceMatcher(None, rec.old_doc, rec.new_doc).ratio(),
        }
        for pair in PAIRS:
            doc = _doc(rec, pair)
            row[f"{pair}_tfidf_delta"] = tfidf.delta(doc, rec.old_code, rec.new_code)
            row[f"{pair}_tfidf_abs"] = tfidf.cosine(doc, rec.new_code)
            row[f"{pair}_r1"] = param_mismatch(doc, rec.new_code).fired
            row[f"{pair}_r2"] = deleted_identifier_mentions(doc, rec.old_code, rec.new_code).fired
            row[f"{pair}_doc_words"] = len(doc.split())
        rows.append(row)
    return pd.DataFrame(rows)


def encoder_signals(records: list[CodocRecord], encoder: Encoder) -> pd.DataFrame:
    """Encoder delta/absolute signals; each distinct text is embedded once."""
    texts = list(
        dict.fromkeys(t for r in records for t in (r.old_doc, r.new_doc, r.old_code, r.new_code))
    )
    emb, trunc = encoder.encode(texts)
    index = {t: i for i, t in enumerate(texts)}
    rows = []
    for rec in records:
        nc, oc = emb[index[rec.new_code]], emb[index[rec.old_code]]
        row = {"record_id": rec.record_id, "encoder": encoder.name}
        for pair in PAIRS:
            doc = _doc(rec, pair)
            d = emb[index[doc]]
            row[f"{pair}_enc_delta"] = float(np.dot(d, nc) - np.dot(d, oc))
            row[f"{pair}_enc_abs"] = float(np.dot(d, nc))
            row[f"{pair}_enc_truncated"] = bool(
                trunc[index[doc]] or trunc[index[rec.new_code]] or trunc[index[rec.old_code]]
            )
        rows.append(row)
    return pd.DataFrame(rows)


def build(split: str, encoder_key: str | None = None, *, allow_test: bool = False) -> Path:
    if split == "test" and not allow_test:
        raise FrozenSplitError(
            "Refusing to score the test split. It is opened once, at the frozen H4 run "
            "(pass --allow-test only there)."
        )
    records = load_split(split)  # type: ignore[arg-type]
    t0 = time.perf_counter()
    if encoder_key is None:
        frame, out = base_signals(records, tfidf_mod.load()), cache_path(split, "base")
    else:
        from spequlator.models.encoder import get_encoder

        enc = get_encoder(encoder_key).load()
        frame, out = encoder_signals(records, enc), cache_path(split, encoder_key)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, index=False)
    print(f"wrote {out}  rows={len(frame)}  seconds={time.perf_counter() - t0:.0f}")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--split", choices=("train", "test"), required=True)
    p.add_argument("--encoder", choices=("unixcoder", "minilm", "minilm-ft"), default=None)
    p.add_argument("--allow-test", action="store_true")
    args = p.parse_args(argv)
    build(args.split, args.encoder, allow_test=args.allow_test)
    return 0


if __name__ == "__main__":
    sys.exit(main())
