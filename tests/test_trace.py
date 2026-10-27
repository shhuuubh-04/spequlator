import random

import numpy as np
import pytest
from conftest import read

from spequlator.datasets.codocbench import to_input
from spequlator.nlp.preprocessing import split_identifiers
from spequlator.pipeline.analyze import analyze
from spequlator.pipeline.report import Thresholds
from spequlator.pipeline.trace import Explained, explain, token_spans
from spequlator.schemas import AnalysisInput

TH = Thresholds()
CAL = Thresholds(eps=0.15, scale_tfidf=0.09, scale_encoder=0.07, encoder="minilm-ft")


class FakeEncoder:
    name = "fake/encoder@0"

    def encode(self, texts):
        rng = np.random.default_rng(sum(len(t) for t in texts) % 997)
        v = rng.normal(size=(len(texts), 16))
        return v / np.linalg.norm(v, axis=1, keepdims=True), [False] * len(texts)


def _change():
    return AnalysisInput(
        documentation=read("stale_param", "doc.txt"),
        old_code=read("stale_param", "old.py"),
        new_code=read("stale_param", "new.py"),
    )


def _lr(mini_records, version="old"):
    return to_input(next(r for r in mini_records if r.function == "observe_lr"), version)


@pytest.mark.parametrize(
    "text",
    ["getHTTPResponse_code(x)", "ABcDEf aBCDef x509 2fa _priv__name", "def f(self, timeout=30):"],
)
def test_token_spans_match_split_identifiers(text):
    assert [t for _, _, t in token_spans(text)] == split_identifiers(text)
    for a, b, t in token_spans(text):
        assert text[a:b].lower() == t


def test_token_spans_random_strings():
    rng = random.Random(7)
    alphabet = "aAbBzZ09_ .(xY"
    for _ in range(500):
        s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 30)))
        assert [t for _, _, t in token_spans(s)] == split_identifiers(s), s


def test_explain_leaves_the_report_unchanged(small_tfidf):
    ex = explain(_change(), tfidf=small_tfidf, encoder=FakeEncoder(), thresholds=CAL)
    plain = analyze(_change(), tfidf=small_tfidf, encoder=FakeEncoder(), thresholds=CAL)
    a, b = ex.report.model_dump(), plain.model_dump()
    a["meta"].pop("elapsed_ms"), b["meta"].pop("elapsed_ms")
    assert a == b
    Explained.model_validate_json(ex.model_dump_json())  # JSON round-trip


def test_tfidf_worked_numbers_add_up(small_tfidf):
    tr = explain(_change(), tfidf=small_tfidf, thresholds=TH).trace
    t = tr.tfidf
    for o in ("new", "old"):
        assert sum(r.contrib[o] for r in t.rows) == pytest.approx(t.cos[o], abs=1e-12)
    assert t.delta == pytest.approx(t.cos["new"] - t.cos["old"])
    for v in t.vectors:
        assert v.norm == pytest.approx(v.sum_sq**0.5)
    for r in t.rows:
        assert r.weight["doc"] == pytest.approx(r.tf["doc"] * r.idf)
        assert r.unit["doc"] == pytest.approx(r.weight["doc"] / t.vectors[0].norm)


def test_decision_walk_has_one_yes_and_matches_finding(small_tfidf):
    ex = explain(_change(), tfidf=small_tfidf, encoder=FakeEncoder(), thresholds=CAL)
    checks = ex.trace.decision.checks
    yes = [c for c in checks if c.result == "yes"]
    assert len(yes) == 1 and yes[0].key == ex.trace.decision.reason
    after = checks[checks.index(yes[0]) + 1 :]
    assert all(c.result == "not reached" for c in after)
    assert yes[0].outcome == ex.report.finding
    assert ex.trace.text.summary == ex.report.summary


def test_r1_marks_point_at_stale_parameters(mini_records, small_tfidf):
    inp = _lr(mini_records)
    tr = explain(inp, tfidf=small_tfidf, thresholds=TH).trace
    assert tr.r1.fired and tr.r1.stale
    note = next(n for n in tr.notes if n.kind == "r1")
    marked = {inp.documentation[s.start : s.end] for s in tr.doc_spans if s.note == note.n}
    assert marked == set(tr.r1.stale)
    assert set(tr.r1.stale) == set(tr.r1.documented) - set(tr.r1.signature)


def test_encoder_step_and_combined_score(small_tfidf):
    ex = explain(_change(), tfidf=small_tfidf, encoder=FakeEncoder(), thresholds=CAL)
    e, c = ex.trace.encoder, ex.trace.combine
    assert e.status == "ok" and e.dim == 16 and len(e.texts) == 3
    assert e.delta == pytest.approx(ex.report.signals.encoder.value)
    assert sum(e.products["new"]) != 0 and len(e.products["new"]) == 6
    assert c.z == pytest.approx(CAL.combined(c.tfidf, c.encoder))
    assert c.parts == pytest.approx([c.tfidf / 0.09, c.encoder / 0.07])


def test_encoder_off_and_snapshot_mode(small_tfidf):
    inp = AnalysisInput(documentation=read("aligned", "doc.txt"), code=read("aligned", "code.py"))
    tr = explain(inp, tfidf=small_tfidf, thresholds=TH).trace
    assert tr.encoder.status == "off"
    assert tr.diff is None and tr.r2 is None and tr.combine is None
    assert set(tr.tfidf.cos) == {"code"} and tr.tfidf.delta is None
    assert tr.decision.reason == "snapshot_no_rule"
    assert [s.key for s in tr.inputs] == ["doc", "code"]


def test_diff_lines_carry_r2_marks(small_tfidf):
    inp = AnalysisInput(
        documentation="Fetch the page and retry with backoff_factor between attempts.",
        old_code="def fetch(url):\n    backoff_factor = 2\n    return get(url)\n",
        new_code="def fetch(url):\n    return get(url)\n",
    )
    tr = explain(inp, tfidf=small_tfidf, thresholds=TH).trace
    assert tr.r2 and tr.r2.fired and {"backoff", "factor"} <= set(tr.r2.hits)
    removed = [ln for ln in tr.diff if ln.sign == "-"]
    assert removed and any(ln.spans for ln in removed)
    assert any(n.kind == "r2" for n in tr.notes)


def test_api_explain_endpoints(tmp_path, monkeypatch, small_tfidf):
    import shutil

    from conftest import FIXTURES
    from fastapi.testclient import TestClient

    from spequlator.api import app
    from spequlator.models import tfidf as tfidf_mod

    art, data = tmp_path / "artifacts", tmp_path / "data"
    data.mkdir()
    tfidf_mod.save(small_tfidf, art / "tfidf.joblib")
    shutil.copy(FIXTURES / "codocbench_mini.jsonl", data / "train.jsonl")
    (data / "test.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(art))
    monkeypatch.setenv("SPEQULATOR_DATA_DIR", str(data))
    monkeypatch.setenv("SPEQULATOR_RESULTS_DIR", str(tmp_path / "results"))
    with TestClient(app) as c:
        body = c.post(
            "/api/explain",
            json=_change().model_dump(include={"documentation", "old_code", "new_code"}),
        ).json()
        assert (
            body["report"]["finding"] == "potential_drift"
            and body["trace"]["decision"]["reason"] == "r1"
        )
        ex = c.post("/api/explain/example", json={"record_id": "8e8e00c86a25"}).json()
        assert ex["report"]["source"]["function"] == "observe_lr" and ex["trace"]["notes"]
        assert c.post("/api/explain/example", json={"record_id": "nope"}).status_code == 404


class Float32Encoder(FakeEncoder):
    """Like the real model: float32 vectors (the trace once failed on these)."""

    def encode(self, texts):
        v, t = super().encode(texts)
        return v.astype(np.float32), t


def test_float32_encoder_output_does_not_break_the_trace(small_tfidf):
    ex = explain(_change(), tfidf=small_tfidf, encoder=Float32Encoder(), thresholds=CAL)
    assert ex.trace.encoder.status == "ok"
    assert ex.trace.encoder.delta == pytest.approx(ex.report.signals.encoder.value, abs=1e-5)


class WordEncoder:
    """Bag-of-words vectors: one dimension per vocabulary word, so occlusion is checkable."""

    name = "bag-of-words test encoder"
    VOCAB = ("timeout", "retries", "session", "users", "fetch")

    def encode(self, texts):
        v = np.array([[t.lower().count(w) + 0.01 for w in self.VOCAB] for t in texts], dtype=float)
        return v / np.linalg.norm(v, axis=1, keepdims=True), [False] * len(texts)


def test_word_importance_only_when_asked(small_tfidf):
    plain = explain(_change(), tfidf=small_tfidf, encoder=WordEncoder(), thresholds=CAL)
    assert plain.trace.words is None
    ex = explain(_change(), tfidf=small_tfidf, encoder=WordEncoder(), thresholds=CAL, words=True)
    w = ex.trace.words
    assert w is not None and w.delta == pytest.approx(ex.report.signals.encoder.value, abs=1e-6)
    assert w.n_words == len(w.words) and w.passes == w.n_words + 1
    doc = _change().documentation
    by_word = {}
    for x in w.words:
        by_word.setdefault(doc[x.start : x.end].strip(".:"), []).append(x.weight)
    assert "timeout" in w.toward_stale  # the renamed-away parameter pulls toward the old code
    assert all(abs(v) < 1e-9 for v in by_word["active"])  # not in the toy vocabulary: no effect


def test_word_importance_needs_an_encoder_and_change_mode(small_tfidf):
    assert explain(_change(), tfidf=small_tfidf, thresholds=CAL, words=True).trace.words is None
    snap = AnalysisInput(documentation=read("aligned", "doc.txt"), code=read("aligned", "code.py"))
    tr = explain(snap, tfidf=small_tfidf, encoder=WordEncoder(), thresholds=CAL, words=True).trace
    assert tr.words is None


def test_bpe_pieces_are_shown_readably():
    from spequlator.pipeline.trace import _piece

    assert _piece("Ġsteps") == "·steps" and _piece("Ċ") == "↵" and _piece("##ing") == "##ing"
