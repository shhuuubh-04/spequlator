"""Learn the decision-rule dead-bands (epsilon) on the TRAIN split only (D-017, D-021).

Signals are put on a common scale (divided by their train standard deviation) and averaged
into one score (D-028). The dead-band eps on that score is chosen to maximise balanced
accuracy over *decided* cases (stale -> potential_drift, updated -> no_obvious_drift)
subject to coverage (share not inconclusive) >= 60%. If no eps reaches 60%, the eps with
the highest coverage is chosen and flagged, never a less decisive one.
"""

from __future__ import annotations

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


def calibrate(df: pd.DataFrame, encoder: str | None) -> tuple[Thresholds, pd.DataFrame]:
    use_enc = encoder is not None
    t_all = pd.concat([df["stale_tfidf_delta"], df["updated_tfidf_delta"]])
    scale_t = float(t_all.std()) or 1.0
    scale_e = 1.0
    if use_enc:
        scale_e = float(pd.concat([df["stale_enc_delta"], df["updated_enc_delta"]]).std()) or 1.0
    base = Thresholds(encoder=encoder, scale_tfidf=scale_t, scale_encoder=scale_e)
    z = [
        base.combined(t, e if use_enc else None)
        for pair in PAIRS
        for t, e in zip(
            df[f"{pair}_tfidf_delta"],
            df[f"{pair}_enc_delta"] if use_enc else [None] * len(df),
            strict=True,
        )
    ]
    grid = sorted({round(float(np.quantile(np.abs(z), q)), 4) for q in QUANTILES})
    table = pd.DataFrame(
        [{"eps": eps, **outcomes(df, replace(base, eps=eps), use_enc)} for eps in grid]
    )
    ok = table[table["coverage"] >= MIN_COVERAGE]
    if len(ok):
        best = ok.sort_values(["balanced_accuracy_decided", "coverage"], ascending=False).iloc[0]
    else:  # constraint unreachable: be as decisive as possible, and say so
        best = table.sort_values("coverage", ascending=False).iloc[0]
    chosen = replace(
        base,
        version=f"calibrated-train-{encoder or 'tfidf'}-{date.today().isoformat()}",
        eps=float(best["eps"]),
    )
    return chosen, table
