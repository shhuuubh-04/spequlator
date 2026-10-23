import numpy as np
import pytest
from conftest import read

from spequlator.datasets.codocbench import to_input
from spequlator.models import tfidf as tfidf_mod
from spequlator.models.base import EncoderUnavailable
from spequlator.pipeline.analyze import analyze
from spequlator.pipeline.report import Thresholds
from spequlator.schemas import AnalysisInput, Report

TH = Thresholds()


def _lr(mini_records):
    return next(r for r in mini_records if r.function == "observe_lr")


def test_dataset_example_old_doc_flags_renamed_params(mini_records, small_tfidf):
    rep = analyze(to_input(_lr(mini_records), "old"), tfidf=small_tfidf, thresholds=TH)
    assert rep.finding == "potential_drift"
    r1 = [e for e in rep.evidence if e.kind == "rule_r1"]
    assert r1 and "key" in r1[0].text and "optimizer" in r1[0].text
    assert r1[0].lines[0].startswith("def observe_lr(")
    assert rep.source.doc_version == "old" and rep.source.record_id == "8e8e00c86a25"
    assert rep.review_recommended and rep.next_step


def test_dataset_example_new_doc_has_no_param_evidence(mini_records, small_tfidf):
    rep = analyze(to_input(_lr(mini_records), "new"), tfidf=small_tfidf, thresholds=TH)
    assert not [e for e in rep.evidence if e.kind == "rule_r1"]
    assert rep.finding != "potential_drift"


def test_synthetic_stale_param_change_mode(small_tfidf):
    inp = AnalysisInput(
        documentation=read("stale_param", "doc.txt"),
        old_code=read("stale_param", "old.py"),
        new_code=read("stale_param", "new.py"),
    )
    rep = analyze(inp, tfidf=small_tfidf, thresholds=TH)
    assert rep.mode == "change" and rep.finding == "potential_drift"
    assert "timeout" in rep.summary
    assert rep.signals.tfidf.kind == "delta"
    Report.model_validate_json(rep.model_dump_json())  # JSON round-trip


def test_snapshot_mode_is_honest_without_rule_evidence(small_tfidf):
    inp = AnalysisInput(documentation=read("aligned", "doc.txt"), code=read("aligned", "code.py"))
    rep = analyze(inp, tfidf=small_tfidf, thresholds=TH)
    assert rep.mode == "snapshot" and rep.finding == "inconclusive"
    assert rep.signals.tfidf.kind == "absolute"
    assert any("Snapshot mode" in u for u in rep.uncertainties)


class FakeEncoder:
    name = "fake/encoder@0"

    def __init__(self, fail: bool = False):
        self.fail = fail

    def encode(self, texts):
        if self.fail:
            raise EncoderUnavailable("weights not downloaded")
        vecs = np.eye(len(texts), 4)
        vecs[0] = vecs[1]  # doc == first code text -> positive delta in change mode
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True), [False] * len(texts)


def test_encoder_signal_and_graceful_failure(mini_records, small_tfidf):
    inp = to_input(_lr(mini_records), "new")
    ok = analyze(inp, tfidf=small_tfidf, encoder=FakeEncoder(), thresholds=TH)
    assert ok.signals.encoder is not None
    assert ok.signals.encoder.kind == "delta" and ok.signals.encoder.value == pytest.approx(1.0)
    assert ok.signals.encoder.model == "fake/encoder@0"

    degraded = analyze(inp, tfidf=small_tfidf, encoder=FakeEncoder(fail=True), thresholds=TH)
    assert degraded.signals.encoder is None
    assert any("weights not downloaded" in u for u in degraded.uncertainties)


def test_missing_artifact_is_reported(monkeypatch, tmp_path, mini_records):
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(tmp_path))
    with pytest.raises(tfidf_mod.ArtifactMissing, match="spequlator.models.tfidf"):
        analyze(to_input(_lr(mini_records), "old"), thresholds=TH)


def test_report_text_never_uses_banned_words(mini_records, small_tfidf):
    for rec in mini_records:
        for version in ("old", "new"):
            rep = analyze(to_input(rec, version), tfidf=small_tfidf, thresholds=TH)
            text = rep.model_dump_json().lower()
            for banned in ("confidence", "probability", '"bug"'):
                assert banned not in text
