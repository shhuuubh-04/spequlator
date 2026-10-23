import math

import joblib
import pytest

from spequlator.models import tfidf as tfidf_mod


def test_fit_is_deterministic(mini_records):
    texts = [r.new_doc for r in mini_records] + [r.new_code for r in mini_records]
    a = tfidf_mod.fit(texts, fit_split="train", min_df=1)
    b = tfidf_mod.fit(texts, fit_split="train", min_df=1)
    assert a.vectorizer.vocabulary_ == b.vectorizer.vocabulary_
    assert a.meta["fit_split"] == "train"


def test_cosine_bounds_and_empty_text(small_tfidf):
    assert small_tfidf.cosine(
        "optimizer learning rate", "optimizer learning rate"
    ) == pytest.approx(1.0)
    assert small_tfidf.cosine("optimizer", "scores average") == 0.0
    value = small_tfidf.cosine("", "def f(): pass")
    assert value == 0.0 and not math.isnan(value)


def test_delta_sign(small_tfidf):
    old = "def f(timeout):\n    return wait(timeout)\n"
    new = "def f(retries):\n    return retry(retries)\n"
    assert small_tfidf.delta("Retry the call several times (retries).", old, new) > 0
    assert small_tfidf.delta("Wait until the timeout expires.", old, new) < 0


def test_fit_on_records_refuses_test_split(mini_records):
    leaked = [
        *mini_records[:2],
        mini_records[2].__class__(**{**mini_records[2].__dict__, "split": "test"}),
    ]
    with pytest.raises(tfidf_mod.SplitLeakError):
        tfidf_mod.fit_on_records(leaked)


def test_save_load_roundtrip_and_guards(tmp_path, small_tfidf):
    path = tfidf_mod.save(small_tfidf, tmp_path / "tfidf.joblib")
    loaded = tfidf_mod.load(path)
    assert loaded.meta["fit_split"] == "train" and len(loaded.meta["sha256"]) == 64
    assert loaded.cosine("optimizer", "optimizer") == pytest.approx(1.0)

    bad = tmp_path / "bad.joblib"
    joblib.dump({"vectorizer": small_tfidf.vectorizer, "meta": {"fit_split": "test"}}, bad)
    with pytest.raises(tfidf_mod.SplitLeakError):
        tfidf_mod.load(bad)
    with pytest.raises(tfidf_mod.ArtifactMissing):
        tfidf_mod.load(tmp_path / "missing.joblib")
