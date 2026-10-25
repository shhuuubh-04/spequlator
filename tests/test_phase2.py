import hashlib
import json
import zipfile

import numpy as np
import pandas as pd
import pytest
from conftest import read

from spequlator.evaluation import phase2
from spequlator.models.cross_encoder import change_text, word_importance
from spequlator.pipeline.report import Thresholds
from spequlator.pipeline.trace import explain
from spequlator.schemas import AnalysisInput

TH = Thresholds()


class FakeScorer:
    """Score drops by 1 for every 'timeout' in the docstring: an easy-to-check stand-in."""

    name = "fake cross-encoder"
    fmt = "diff"
    max_len = 512

    def __init__(self):
        self.calls = 0

    def score_pairs(self, pairs):
        self.calls += 1
        return np.array([0.5 - doc.count("timeout") for doc, _ in pairs], dtype=float)


def _change():
    return AnalysisInput(
        documentation=read("stale_param", "doc.txt"),
        old_code=read("stale_param", "old.py"),
        new_code=read("stale_param", "new.py"),
    )


def test_change_text_formats():
    diff = change_text("def f(a):\n    return a\n", "def f(b):\n    return b\n", "diff")
    assert diff.startswith("CHANGED LINES:\n- def f(a):") and "+ def f(b):" in diff
    assert diff.endswith("NEW CODE:\ndef f(b):\n    return b\n")
    assert change_text("x", "y", "full") == "OLD CODE:\nx\nNEW CODE:\ny"


def test_word_importance_is_score_minus_occluded_score():
    doc = "Wait for timeout seconds; timeout is required."
    base, weights, n = word_importance(FakeScorer(), doc, "a", "b")
    assert base == pytest.approx(-1.5) and n == len(doc.split())
    by_word = {doc[w.start : w.end]: w.weight for w in weights}
    assert by_word["timeout"] == pytest.approx(-1.0)  # removing it raises the score by 1
    assert by_word["Wait"] == pytest.approx(0.0)


def test_explain_cross_score_only_then_words(small_tfidf):
    fake = FakeScorer()
    tr = explain(_change(), tfidf=small_tfidf, thresholds=TH, cross=fake).trace
    assert tr.cross is not None and tr.cross.words == [] and tr.cross.passes == 1
    assert tr.cross.lean == ("fits" if tr.cross.score >= 0 else "stale")
    tr2 = explain(_change(), tfidf=small_tfidf, thresholds=TH, cross=fake, cross_words=True).trace
    assert tr2.cross.n_words == len(tr2.cross.words) and tr2.cross.passes == tr2.cross.n_words + 1
    assert "timeout" in tr2.cross.toward_stale


def test_cross_is_absent_without_model_or_in_snapshot_mode(small_tfidf):
    assert explain(_change(), tfidf=small_tfidf, thresholds=TH).trace.cross is None
    snap = AnalysisInput(documentation=read("aligned", "doc.txt"), code=read("aligned", "code.py"))
    assert explain(snap, tfidf=small_tfidf, thresholds=TH, cross=FakeScorer()).trace.cross is None


def _fake_outputs(root):
    (root / "ce").mkdir(parents=True)
    (root / "ce" / "spequlator_ce.json").write_text('{"format": "diff"}')
    (root / "signals_train_ce.parquet").write_bytes(b"x")
    files = sorted(p for p in (root / "ce").rglob("*") if p.is_file())
    h = hashlib.sha256()
    for f in files:
        h.update(str(f.relative_to(root / "ce")).encode())
        h.update(f.read_bytes())
    manifest = {
        "smoke": False,
        "best_bi": {"name": "bi"},
        "best_ce": {"name": "ce"},
        "sha256": {
            "ce": h.hexdigest(),
            "signals_train_ce.parquet": hashlib.sha256(b"x").hexdigest(),
        },
    }
    (root / "phase2_manifest.json").write_text(json.dumps(manifest))


def _zip(src, dest):
    with zipfile.ZipFile(dest, "w") as zf:
        for p in src.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(src))
    return dest


def test_import_checks_every_hash(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    _fake_outputs(tmp_path / "good")
    m = phase2.import_outputs(_zip(tmp_path / "good", tmp_path / "good.zip"))
    assert m["best_ce"]["name"] == "ce" and (tmp_path / "artifacts/phase2/ce").is_dir()

    _fake_outputs(tmp_path / "bad")
    (tmp_path / "bad" / "ce" / "spequlator_ce.json").write_text('{"format": "full"}')
    with pytest.raises(phase2.Phase2Error):
        phase2.import_outputs(_zip(tmp_path / "bad", tmp_path / "bad.zip"))


def test_run_refuses_without_confirmation_or_freeze(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEQULATOR_RESULTS_DIR", str(tmp_path / "results"))
    with pytest.raises(phase2.Phase2Error):
        phase2.run(confirm=False)
    with pytest.raises(phase2.Phase2Error, match="not frozen"):
        phase2.run(confirm=True)


def test_metrics_on_synthetic_signals():
    rng = np.random.default_rng(0)
    n = 60
    df = pd.DataFrame(
        {"record_id": [f"r{i}" for i in range(n)], "project_key": [f"p{i % 6}" for i in range(n)]}
    )
    for name in ("tfidf_abs", "tfidf_delta", "minilm_delta", "minilm-ft_delta", "ft2", "ce"):
        df[f"stale_{name}"] = rng.normal(-0.5, 1, n)
        df[f"updated_{name}"] = rng.normal(0.5, 1, n)
    th = Thresholds(scale_tfidf=0.09, scale_encoder=0.07, encoder="minilm-ft")
    frozen = {"combine": {"scale_tfidf": 0.09, "scale_ft2": 1.0, "centre_ce": 0.0, "scale_ce": 1.0}}
    sig = phase2.phase2_signals(df, frozen, th)
    assert phase2.V1_COMBINED in sig and "TF-IDF + MiniLM (phase 2) + cross-encoder" in sig
    m = phase2.compute(df, sig, n_boot=20)
    row = m["signals"]["Cross-encoder (phase 2)"]
    assert 0.5 < row["pooled_auc"]["value"] <= 1 and "pairwise_accuracy_minus_v1" in row
    assert "pooled_auc_minus_tfidf" not in m["signals"][phase2.BASELINE]
    md = phase2.to_markdown(
        m, [{"name": "bi", "family": "bi-encoder", "pairwise_accuracy": 0.7, "pooled_auc": 0.65}]
    )
    assert "declared second use" in md and "| bi | bi-encoder |" in md