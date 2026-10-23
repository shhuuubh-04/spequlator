import numpy as np
import pytest

from spequlator.evaluation import proxy_task as pt


class FakeEncoder:
    name = "fake/encoder@0"

    def encode(self, texts):
        rng = np.random.default_rng(0)
        v = rng.normal(size=(len(texts), 6))
        return v / np.linalg.norm(v, axis=1, keepdims=True), [len(t) > 400 for t in texts]


def test_base_signals_columns_and_values(mini_records, small_tfidf):
    df = pt.base_signals(mini_records, small_tfidf)
    assert len(df) == len(mini_records)
    for pair in ("stale", "updated"):
        for col in ("tfidf_delta", "tfidf_abs", "r1", "r2", "doc_words"):
            assert f"{pair}_{col}" in df.columns
    lr = df.set_index("record_id").loc["8e8e00c86a25"]
    assert bool(lr["stale_r1"]) and not bool(lr["updated_r1"])
    assert lr["project_key"] == "chainer/chainer"
    assert 0.0 <= lr["doc_edit_ratio"] <= 1.0


def test_encoder_signals_shape(mini_records):
    df = pt.encoder_signals(mini_records, FakeEncoder())
    assert len(df) == len(mini_records)
    assert {"stale_enc_delta", "updated_enc_abs", "stale_enc_truncated"} <= set(df.columns)
    assert (df["encoder"] == "fake/encoder@0").all()
    assert df["stale_enc_delta"].between(-2, 2).all()


def test_test_split_is_guarded(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(tmp_path))
    with pytest.raises(pt.FrozenSplitError):
        pt.build("test")
    with pytest.raises(pt.FrozenSplitError):
        pt.main(["--split", "test"])
