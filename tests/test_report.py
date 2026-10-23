import pytest

from spequlator.nlp.rules import R1Result, R2Result
from spequlator.pipeline.report import Thresholds, decide, next_step_for, summary_for

TH = Thresholds(eps=0.01)
NO_R1 = R1Result(applicable=True, fired=False)
R1_FIRED = R1Result(applicable=True, fired=True, stale_params=["timeout"], def_line="def f(x):")
NO_R2 = R2Result(applicable=True, fired=False)
R2_FIRED = R2Result(applicable=True, fired=True, tokens=["cache"], lines=["use_cache()"])


def _d(mode="change", r1=NO_R1, r2=NO_R2, tfidf=0.0, encoder=None, words=20, th=TH):
    return decide(mode, r1=r1, r2=r2, tfidf=tfidf, encoder=encoder, doc_words=words, th=th)


@pytest.mark.parametrize(
    ("kwargs", "finding", "reason"),
    [
        ({"r1": R1_FIRED, "tfidf": 0.5, "encoder": 0.5}, "potential_drift", "r1"),
        ({"words": 3, "tfidf": -0.5}, "inconclusive", "short_doc"),
        ({"r2": R2_FIRED, "tfidf": 0.0}, "potential_drift", "r2"),
        ({"r2": R2_FIRED, "tfidf": 0.2}, "no_obvious_drift", "signals_positive"),  # R2 outweighed
        ({"tfidf": -0.2, "encoder": -0.2}, "potential_drift", "signals_negative"),
        ({"tfidf": 0.2, "encoder": 0.2}, "no_obvious_drift", "signals_positive"),
        ({"tfidf": 0.2, "encoder": -0.2}, "inconclusive", "signals_disagree"),
        ({"tfidf": 0.005}, "inconclusive", "signals_weak"),
        ({"tfidf": -0.2}, "potential_drift", "signals_negative"),  # encoder unavailable
        ({"mode": "snapshot", "r2": None, "tfidf": 0.9}, "inconclusive", "snapshot_no_rule"),
        ({"tfidf": 0.05, "encoder": -0.01}, "no_obvious_drift", "signals_positive"),  # no veto
    ],
)
def test_decision_truth_table(kwargs, finding, reason):
    d = _d(**kwargs)
    assert (d.finding, d.reason) == (finding, reason)


def test_snapshot_thresholds_when_configured():
    th = Thresholds(snapshot_low=0.05, snapshot_high=0.6)
    assert _d(mode="snapshot", r2=None, tfidf=0.01, th=th).finding == "potential_drift"
    assert _d(mode="snapshot", r2=None, tfidf=0.9, th=th).finding == "no_obvious_drift"


def test_thresholds_roundtrip_and_default(tmp_path):
    assert Thresholds.load(tmp_path / "none.json") == Thresholds()
    th = Thresholds(version="calibrated-test", eps=0.5, scale_tfidf=0.04, encoder="minilm")
    assert Thresholds.load(th.save(tmp_path / "t.json")) == th


@pytest.mark.parametrize(
    "reason",
    ["r1", "r2", "signals_negative", "signals_positive", "signals_disagree", "signals_weak",
     "short_doc", "snapshot_no_rule", "snapshot_low", "snapshot_high"],
)  # fmt: skip
def test_text_templates_exist_and_use_neutral_language(reason):
    finding = "potential_drift" if reason in {"r1", "r2", "signals_negative"} else "inconclusive"
    from spequlator.pipeline.report import Decision

    d = Decision(finding, reason)
    text = (summary_for(d, R1_FIRED, R2_FIRED) + " " + next_step_for(d, R1_FIRED, R2_FIRED)).lower()
    assert text.strip()
    for banned in ("bug", "confidence", "probability", "definitely"):
        assert banned not in text


def test_combined_score_uses_train_scales():
    th = Thresholds(eps=1.0, scale_tfidf=0.05, scale_encoder=0.02)
    assert th.combined(-0.06, -0.03) == pytest.approx(-1.35)
    assert _d(tfidf=-0.06, encoder=-0.03, th=th).finding == "potential_drift"
    assert _d(tfidf=-0.06, encoder=0.03, th=th).reason == "signals_disagree"
