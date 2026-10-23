"""Learn the decision-rule dead-bands (epsilon) on the TRAIN split only (D-017, D-021).

Objective: maximise balanced accuracy over *decided* cases (stale -> potential_drift,
updated -> no_obvious_drift) subject to coverage (share not inconclusive) >= 60%.
Grids are quantiles of |delta| so TF-IDF and encoder scales are handled alike.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd

from spequlator.evaluation.proxy_task import PAIRS, cache_path
from spequlator.nlp.rules import R1Result, R2Result
from spequlator.pipeline.report import Thresholds, decide

MIN_COVERAGE = 0.60
QUANTILES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)


def load_signals(split: str, encoder: str | None) -> pd.DataFrame:
    base = pd.read_parquet(cache_path(split, "base"))
    if encoder is None:
        return base
    enc = pd.read_parquet(cache_path(split, encoder))
    return base.merge(enc.drop(columns=["encoder"]), on="record_id", validate="one_to_one")


def outcomes(df: pd.DataFrame, th: Thresholds, use_encoder: bool) -> dict[str, float]:
    """Finding rates for stale/updated pairs plus coverage and balanced accuracy."""
    counts = {p: {"potential_drift": 0, "no_obvious_drift": 0, "inconclusive": 0} for p in PAIRS}
    for row in df.itertuples(index=False):
        for pair in PAIRS:
            d = decide(
                "change",
                r1=R1Result(applicable=True, fired=bool(getattr(row, f"{pair}_r1"))),
                r2=R2Result(applicable=True, fired=bool(getattr(row, f"{pair}_r2"))),
                tfidf=float(getattr(row, f"{pair}_tfidf_delta")),
                encoder=float(getattr(row, f"{pair}_enc_delta")) if use_encoder else None,
                doc_words=int(getattr(row, f"{pair}_doc_words")),
                th=th,
            )
            counts[pair][d.finding] += 1
    n = len(df)
    s, u = counts["stale"], counts["updated"]
    s_dec = s["potential_drift"] + s["no_obvious_drift"]
    u_dec = u["potential_drift"] + u["no_obvious_drift"]
    bal = 0.5 * (
        (s["potential_drift"] / s_dec if s_dec else 0.0)
        + (u["no_obvious_drift"] / u_dec if u_dec else 0.0)
    )
    out = {f"{p}_{k}": v / n for p in PAIRS for k, v in counts[p].items()}
    out["coverage"] = (s_dec + u_dec) / (2 * n)
    out["balanced_accuracy_decided"] = bal
    return out


def _grid(values: pd.Series) -> list[float]:
    return sorted({round(float(np.quantile(values.abs(), q)), 4) for q in QUANTILES})


def calibrate(df: pd.DataFrame, encoder: str | None) -> tuple[Thresholds, pd.DataFrame]:
    use_enc = encoder is not None
    t_grid = _grid(pd.concat([df["stale_tfidf_delta"], df["updated_tfidf_delta"]]))
    e_grid = (
        _grid(pd.concat([df["stale_enc_delta"], df["updated_enc_delta"]])) if use_enc else [0.0]
    )
    base = Thresholds(encoder=encoder)
    rows = []
    for et, ee in itertools.product(t_grid, e_grid):
        th = replace(base, eps_tfidf=et, eps_encoder=ee)
        rows.append({"eps_tfidf": et, "eps_encoder": ee, **outcomes(df, th, use_enc)})
    table = pd.DataFrame(rows)
    ok = table[table["coverage"] >= MIN_COVERAGE]
    best = (
        (ok if len(ok) else table)
        .sort_values(["balanced_accuracy_decided", "coverage"], ascending=False)
        .iloc[0]
    )
    chosen = replace(
        base,
        version=f"calibrated-train-{encoder or 'tfidf'}-{date.today().isoformat()}",
        eps_tfidf=float(best["eps_tfidf"]),
        eps_encoder=float(best["eps_encoder"]),
    )
    return chosen, table
