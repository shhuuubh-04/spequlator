import numpy as np
import pandas as pd

from spequlator.evaluation import calibrate as cal
from spequlator.evaluation.calibrate import MIN_COVERAGE, calibrate, outcomes
from spequlator.pipeline.report import Thresholds


def _frame(n=200, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "record_id": [f"r{i}" for i in range(n)],
            "stale_tfidf_delta": rng.normal(-0.03, 0.03, n),
            "updated_tfidf_delta": rng.normal(0.03, 0.03, n),
            "stale_enc_delta": rng.normal(-0.02, 0.02, n),
            "updated_enc_delta": rng.normal(0.02, 0.02, n),
            "stale_r1": rng.random(n) < 0.1,
            "updated_r1": rng.random(n) < 0.02,
            "stale_r2": rng.random(n) < 0.2,
            "updated_r2": rng.random(n) < 0.1,
            "stale_doc_words": 20,
            "updated_doc_words": 20,
        }
    )


def test_outcomes_rates_sum_to_one():
    out = outcomes(_frame(), Thresholds(eps=0.01), use_encoder=False)
    for pair in ("stale", "updated"):
        total = sum(
            out[f"{pair}_{k}"] for k in ("potential_drift", "no_obvious_drift", "inconclusive")
        )
        assert abs(total - 1.0) < 1e-9
    assert 0.0 <= out["coverage"] <= 1.0


def test_calibrate_respects_coverage_and_records_encoder():
    th, table = calibrate(_frame(), encoder="minilm")
    assert th.encoder == "minilm" and th.version.startswith("calibrated-train-minilm-")
    assert th.scale_tfidf > 0 and th.scale_encoder > 0
    chosen = table[table.eps == th.eps].iloc[0]
    assert chosen["coverage"] >= MIN_COVERAGE
    assert chosen["balanced_accuracy_decided"] > 0.6  # separable synthetic data


def test_calibrate_tfidf_only():
    th, _ = calibrate(_frame(), encoder=None)
    assert th.encoder is None and th.scale_encoder == 1.0


def test_unreachable_coverage_picks_most_decisive(monkeypatch):
    monkeypatch.setattr(cal, "MIN_COVERAGE", 1.01)
    th, table = cal.calibrate(_frame(), encoder="minilm")
    assert th.eps == table.loc[table["coverage"].idxmax(), "eps"]
