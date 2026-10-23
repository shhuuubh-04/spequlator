import pandas as pd
import pytest

from spequlator.evaluation.manual_review import (
    RUBRIC,
    pick_demo,
    stale_findings,
    stratified_pick,
    summarize_scores,
)
from spequlator.pipeline.report import Thresholds


def test_stratified_pick_balances_and_is_reproducible():
    ids = pd.Series([f"r{i}" for i in range(60)])
    findings = pd.Series(
        ["potential_drift"] * 40 + ["no_obvious_drift"] * 15 + ["inconclusive"] * 5
    )
    a = stratified_pick(ids, findings, n=30, seed=2026)
    assert len(a) == len(set(a)) == 30
    assert a == stratified_pick(ids, findings, n=30, seed=2026)
    by = findings.set_axis(ids).loc[a].value_counts()
    assert by["inconclusive"] == 5  # whole short stratum taken, then topped up from the rest
    assert by["no_obvious_drift"] >= 10 and by["potential_drift"] >= 10


def test_stale_findings_uses_rules_and_signals():
    df = pd.DataFrame(
        {
            "stale_r1": [True, False, False],
            "stale_r2": [False, False, False],
            "stale_tfidf_delta": [0.5, -0.5, 0.5],
            "stale_minilm-ft_delta": [0.5, -0.5, 0.5],
            "stale_doc_words": [20, 20, 20],
        }
    )
    th = Thresholds(eps=0.1, encoder="minilm-ft")
    assert list(stale_findings(df, th)) == [
        "potential_drift",
        "potential_drift",
        "no_obvious_drift",
    ]


def _scores(**over):
    base = {
        "n": [1, 1, 2, 2],
        "doc_version": ["old", "new", "old", "new"],
        "finding": ["potential_drift", "no_obvious_drift", "inconclusive", "inconclusive"],
        "evidence_fidelity": [2, 2, 1, 2],
        "specificity": [2, 1, 1, 0],
        "uncertainty_calibration": [2, 2, 1, 1],
        "needs_update": ["yes", "no", "unsure", "no"],
    }
    base.update(over)
    return pd.DataFrame(base)


def test_summarize_scores():
    s = summarize_scores(_scores())
    assert s["n_reports_scored"] == 4
    assert s["overall"]["evidence_fidelity"] == 1.75
    assert set(s["by_doc_version"]) == {"old", "new"}
    assert s["needs_update_yes_rate_old"] == 0.5


def test_summarize_rejects_out_of_range_and_empty():
    with pytest.raises(ValueError, match="0, 1 or 2"):
        summarize_scores(_scores(specificity=[3, 1, 1, 0]))
    empty = _scores(**{k: [None] * 4 for k in RUBRIC})
    with pytest.raises(ValueError, match="no scored rows"):
        summarize_scores(empty)


def test_pick_demo_is_readable_and_seeded(mini_records):
    a = pick_demo(mini_records, n=3, seed=2026)
    assert a == pick_demo(mini_records, n=3, seed=2026)
    chosen = [r for r in mini_records if r.record_id in a]
    assert all(len(r.old_code) + len(r.new_code) <= 1500 for r in chosen)
