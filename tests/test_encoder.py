import numpy as np
import pytest

from spequlator.models import encoder as enc_mod
from spequlator.models.base import EncoderUnavailable
from spequlator.models.encoder import SentenceEncoder, spec_for


class FakeTokenizer:
    def __call__(self, texts, add_special_tokens=True, verbose=False):
        return {"input_ids": [[0] * (len(t.split()) + 2) for t in texts]}


class FakeST:
    calls = 0

    def __init__(self, model_id, revision=None, device="cpu", trust_remote_code=False):
        assert trust_remote_code is False  # D-018
        self.tokenizer = FakeTokenizer()
        self.max_seq_length = 0

    def encode(self, texts, **kwargs):
        FakeST.calls += 1
        rng = np.random.default_rng(len(texts))
        v = rng.normal(size=(len(texts), 8))
        return v / np.linalg.norm(v, axis=1, keepdims=True)


@pytest.fixture
def fake_st(monkeypatch):
    import sentence_transformers

    FakeST.calls = 0
    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", FakeST)
    return FakeST


def test_specs_are_pinned():
    assert spec_for("unixcoder").revision == "5604afdc964f6c53782a6813140ade5216b99006"
    assert spec_for("minilm").revision == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    assert spec_for("unixcoder").name == "microsoft/unixcoder-base@5604afd"
    assert spec_for("minilm-ft").max_seq_length == 128
    with pytest.raises(ValueError):
        spec_for("jina")


def test_encode_normalises_flags_truncation_and_caches(fake_st):
    e = SentenceEncoder(spec_for("minilm"))
    vecs, trunc = e.encode(["short text", "word " * 400, "short text"])
    assert vecs.shape == (3, 8)
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0)
    assert trunc == [False, True, False]
    assert np.allclose(vecs[0], vecs[2])  # duplicate served from cache
    e.encode(["short text"])
    assert fake_st.calls == 1  # second call fully cached


def test_load_failure_becomes_encoder_unavailable(monkeypatch):
    import sentence_transformers

    def boom(*a, **k):
        raise OSError("no internet")

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", boom)
    with pytest.raises(EncoderUnavailable, match="no internet"):
        SentenceEncoder(spec_for("unixcoder")).encode(["x"])


def test_get_encoder_is_shared(fake_st, monkeypatch):
    monkeypatch.setattr(enc_mod, "_INSTANCES", {})
    assert enc_mod.get_encoder("minilm") is enc_mod.get_encoder("minilm")


@pytest.mark.encoder
def test_real_unixcoder_if_cached(monkeypatch):
    """Slow: runs only when the pinned weights are already downloaded (START_HERE 3.4)."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    try:
        vecs, trunc = SentenceEncoder(spec_for("unixcoder")).encode(
            ["Return the sum.", "def f(a, b):\n    return a + b"]
        )
    except EncoderUnavailable as exc:
        pytest.skip(f"model not cached: {exc}")
    assert vecs.shape == (2, 768)
    assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-5)
    assert trunc == [False, False]
