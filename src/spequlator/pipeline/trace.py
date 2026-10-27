"""Read-only pipeline trace for the UI's "How it was computed" section (D-030).

``explain()`` runs ``analyze()`` unchanged, then recomputes every intermediate value with the
same functions and checks that each recomputed number equals the report's. It cannot change a
finding: if the trace and the report ever disagree, ``explain()`` raises instead of guessing.

The TF-IDF step is rebuilt by hand from the trained vocabulary and idf values
(tf = 1 + ln(count), weight = tf x idf, unit weight = weight / ||v||) and checked against
scikit-learn's own ``transform`` to 1e-9.
"""

from __future__ import annotations

import difflib
import math
import re
from collections import Counter
from itertools import pairwise
from typing import Literal

import numpy as np
from pydantic import BaseModel

from spequlator.models import tfidf as tfidf_mod
from spequlator.models.base import Encoder
from spequlator.models.tfidf import TfidfModel
from spequlator.nlp.preprocessing import STOPWORDS, code_diff, content_tokens, split_identifiers
from spequlator.nlp.rules import (
    R1Result,
    R2Result,
    deleted_identifier_mentions,
    documented_params,
    param_mismatch,
    parse_signature,
)
from spequlator.pipeline.analyze import analyze
from spequlator.pipeline.report import Decision, Thresholds, decide, next_step_for, summary_for
from spequlator.schemas import AnalysisInput, Report

TOL = 1e-9
ENC_TOL = 1e-5  # float32 model output shown in float64
TOKEN_PREVIEW = 160
PIECE_PREVIEW = 40
VECTOR_HEAD = 8
PRODUCT_HEAD = 6

_SEG = re.compile(r"[A-Za-z0-9]+")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]+")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class TraceMismatch(RuntimeError):
    """The recomputed trace disagrees with the report (should never happen)."""


# ---- models (all additive; the Report schema is unchanged) ------------------------------
class TextStat(BaseModel):
    key: str
    label: str
    chars: int
    words: int
    lines: int


class Note(BaseModel):
    n: int
    kind: Literal["r1", "r2"]
    text: str


class Span(BaseModel):
    start: int
    end: int
    note: int


class DiffLine(BaseModel):
    sign: Literal["-", "+"]
    text: str
    spans: list[Span] = []


class Token(BaseModel):
    t: str
    vocab: bool  # in the TF-IDF vocabulary (fitted on train, min_df)
    content: bool  # counts for rule R2 (length >= 3, not a stopword)


class TokenStep(BaseModel):
    key: str
    label: str
    n_tokens: int
    n_vocab: int
    n_content: int
    splits: list[tuple[str, list[str]]]  # identifier -> its parts (examples)
    tokens: list[Token]  # first TOKEN_PREVIEW tokens
    more: int  # tokens not shown


class R1Step(BaseModel):
    applicable: bool
    def_line: str
    signature: list[str]
    has_kwargs: bool
    documented: list[str]
    stale: list[str]  # documented - signature (used)
    undocumented: list[str]  # signature - documented (shown only; not used, see R1 limits)
    fired: bool


class R2Step(BaseModel):
    applicable: bool
    removed: list[str]  # content tokens in removed lines
    still_present: list[str]  # removed tokens that also occur in the new code
    gone: list[str]  # removed - new code
    doc: list[str]  # content tokens in the documentation
    hits: list[str]  # doc & gone
    lines: list[str]
    fired: bool


class TermRow(BaseModel):
    term: str
    df: int
    idf: float
    count: dict[str, int]
    tf: dict[str, float]
    weight: dict[str, float]
    unit: dict[str, float]
    contrib: dict[str, float]  # unit[doc] * unit[other]


class VecStat(BaseModel):
    key: str
    label: str
    n_terms: int
    out_of_vocab: int
    sum_sq: float
    norm: float


class TfidfStep(BaseModel):
    n_train_texts: int
    vocab_size: int
    min_df: int
    vectors: list[VecStat]
    rows: list[TermRow]  # every documentation term in the vocabulary
    cos: dict[str, float]
    delta: float | None


class EncText(BaseModel):
    key: str
    label: str
    n_tokens: int | None
    truncated: bool
    pieces: list[str]
    head: list[float]
    norm: float


class EncoderStep(BaseModel):
    status: Literal["ok", "off", "unavailable"]
    model: str = ""
    max_seq_length: int | None = None
    dim: int | None = None
    texts: list[EncText] = []
    products: dict[str, list[float]] = {}
    cos: dict[str, float] = {}
    delta: float | None = None


class CombineStep(BaseModel):
    tfidf: float
    encoder: float | None
    scale_tfidf: float
    scale_encoder: float
    parts: list[float]
    z: float
    eps: float


class Check(BaseModel):
    key: str
    question: str
    detail: str
    result: Literal["yes", "no", "not reached"]
    outcome: str


class DecisionStep(BaseModel):
    checks: list[Check]
    reason: str
    finding: str


class TextStep(BaseModel):
    reason: str
    summary: str
    next_step: str


class Constants(BaseModel):
    thresholds_version: str
    eps: float
    scale_tfidf: float
    scale_encoder: float
    min_doc_words: int
    encoder_key: str | None


class WordWeight(BaseModel):
    start: int
    end: int
    weight: float  # Δ with the word minus Δ without it; > 0 = pushed toward "fits the new code"


class WordsStep(BaseModel):
    """Which docstring words moved the encoder's meaning score (occlusion, on request)."""

    model: str
    delta: float  # the encoder Δ for the full docstring (same as the report's signal)
    words: list[WordWeight]
    n_words: int
    passes: int  # encoder passes over docstring variants (code embeddings are reused)
    toward_stale: list[str]
    toward_fits: list[str]


class Trace(BaseModel):
    trace_version: Literal["1"] = "1"
    mode: str
    inputs: list[TextStat]
    documentation: str  # the text that doc_spans point into
    doc_spans: list[Span]
    notes: list[Note]
    diff: list[DiffLine] | None
    tokens: list[TokenStep]
    r1: R1Step
    r2: R2Step | None
    tfidf: TfidfStep
    encoder: EncoderStep
    combine: CombineStep | None
    decision: DecisionStep
    text: TextStep
    constants: Constants
    words: WordsStep | None = None


class Explained(BaseModel):
    report: Report
    trace: Trace


# ---- helpers ----------------------------------------------------------------------------
def token_spans(text: str) -> list[tuple[int, int, str]]:
    """``split_identifiers`` with character positions (same tokens, same order)."""
    out: list[tuple[int, int, str]] = []
    for m in _SEG.finditer(text):
        s, base = m.group(), m.start()
        cuts = [0]
        for i in range(1, len(s)):
            a, b, nxt = s[i - 1], s[i], s[i + 1] if i + 1 < len(s) else ""
            camel = (a.islower() or a.isdigit()) and b.isupper()
            acronym = a.isupper() and b.isupper() and nxt.islower()
            if camel or acronym:
                cuts.append(i)
        cuts.append(len(s))
        for x, y in pairwise(cuts):
            for w in _WORD.finditer(s[x:y]):
                out.append((base + x + w.start(), base + x + w.end(), w.group().lower()))
    return out


def _f(v: float, digits: int = 3) -> str:
    """Signed number with a true minus sign, for sentences shown to people."""
    return f"{v:+.{digits}f}".replace("-", "\u2212")


def _check(cond: bool, what: str) -> None:
    if not cond:
        raise TraceMismatch(f"trace disagrees with the report: {what}")


def _stat(key: str, label: str, text: str) -> TextStat:
    return TextStat(
        key=key, label=label, chars=len(text), words=len(text.split()), lines=len(text.splitlines())
    )


def _texts(inp: AnalysisInput) -> list[tuple[str, str, str]]:
    if inp.mode == "change":
        return [
            ("doc", "Documentation", inp.documentation),
            ("new", "Code after", inp.new_code or ""),
            ("old", "Code before", inp.old_code or ""),
        ]
    return [("doc", "Documentation", inp.documentation), ("code", "Code", inp.code or "")]


def _token_step(key: str, label: str, text: str, vocab: dict) -> TokenStep:
    toks = split_identifiers(text)
    flags = [Token(t=t, vocab=t in vocab, content=len(t) >= 3 and t not in STOPWORDS) for t in toks]
    splits: list[tuple[str, list[str]]] = []
    for ident in dict.fromkeys(_IDENT.findall(text)):
        parts = split_identifiers(ident)
        if len(parts) >= 2:
            splits.append((ident, parts))
        if len(splits) >= 6:
            break
    return TokenStep(
        key=key,
        label=label,
        n_tokens=len(toks),
        n_vocab=sum(f.vocab for f in flags),
        n_content=sum(f.content for f in flags),
        splits=splits,
        tokens=flags[:TOKEN_PREVIEW],
        more=max(0, len(flags) - TOKEN_PREVIEW),
    )


def _tfidf_step(model: TfidfModel, texts: list[tuple[str, str, str]]) -> TfidfStep:
    vec = model.vectorizer
    _check(vec.norm == "l2" and vec.smooth_idf and vec.use_idf, "unexpected TF-IDF settings")
    vocab, idf = vec.vocabulary_, vec.idf_
    n = int(model.meta.get("n_texts") or 0)
    sublinear = bool(vec.sublinear_tf)

    def tf_of(c: int) -> float:
        return 1.0 + math.log(c) if sublinear else float(c)

    counts, weights, units, vstats = {}, {}, {}, []
    sk = vec.transform([t for _, _, t in texts]).tocsr()
    for row, (key, label, text) in enumerate(texts):
        toks = split_identifiers(text)
        c = Counter(t for t in toks if t in vocab)
        w = {t: tf_of(k) * float(idf[vocab[t]]) for t, k in c.items()}
        sum_sq = sum(x * x for x in w.values())
        norm = math.sqrt(sum_sq)
        u = {t: x / norm for t, x in w.items()} if norm else {}
        # Cross-check the hand computation against scikit-learn's own vector.
        ref = {int(j): float(v) for j, v in zip(sk[row].indices, sk[row].data, strict=True)}
        _check(len(u) == len(ref), f"TF-IDF term count for {key}")
        for t, x in u.items():
            _check(abs(x - ref.get(vocab[t], math.inf)) < TOL, f"TF-IDF weight of {t!r} in {key}")
        counts[key], weights[key], units[key] = c, w, u
        vstats.append(
            VecStat(
                key=key,
                label=label,
                n_terms=len(w),
                out_of_vocab=len(toks) - sum(c.values()),
                sum_sq=sum_sq,
                norm=norm,
            )
        )

    others = [k for k, _, _ in texts if k != "doc"]
    rows = []
    for t in units["doc"]:
        i = float(idf[vocab[t]])
        df = round((1 + n) / math.exp(i - 1) - 1) if n else 0
        rows.append(
            TermRow(
                term=t,
                df=df,
                idf=i,
                count={k: counts[k].get(t, 0) for k, _, _ in texts},
                tf={k: tf_of(counts[k][t]) if t in counts[k] else 0.0 for k, _, _ in texts},
                weight={k: weights[k].get(t, 0.0) for k, _, _ in texts},
                unit={k: units[k].get(t, 0.0) for k, _, _ in texts},
                contrib={o: units["doc"][t] * units[o].get(t, 0.0) for o in others},
            )
        )
    rows.sort(key=lambda r: (-max(abs(v) for v in r.contrib.values()), -r.unit["doc"], r.term))
    cos = {o: sum(r.contrib[o] for r in rows) for o in others}
    delta = cos["new"] - cos["old"] if "new" in cos else None
    return TfidfStep(
        n_train_texts=n,
        vocab_size=len(vocab),
        min_df=int(vec.min_df),
        vectors=vstats,
        rows=rows,
        cos=cos,
        delta=delta,
    )


def _encoder_step(
    encoder: Encoder | None, report: Report, texts: list[tuple[str, str, str]]
) -> EncoderStep:
    sig = report.signals.encoder
    if sig is None:
        return EncoderStep(status="off" if encoder is None else "unavailable")
    assert encoder is not None
    emb, trunc = encoder.encode([t for _, _, t in texts])  # same order as analyze()
    keys = [k for k, _, _ in texts]
    # Same arithmetic as analyze() (the model returns float32), so the check can be exact.
    same = (
        float(np.dot(emb[0], emb[1]) - np.dot(emb[0], emb[2]))
        if len(keys) == 3
        else float(np.dot(emb[0], emb[1]))
    )
    _check(abs(same - sig.value) < TOL, "encoder signal")
    emb = np.asarray(emb, dtype=float)
    cos = {k: float(np.dot(emb[0], emb[i])) for i, k in enumerate(keys) if i > 0}
    delta = cos["new"] - cos["old"] if "new" in cos else None
    _check(
        abs((delta if delta is not None else cos["code"]) - sig.value) < ENC_TOL, "encoder display"
    )

    tok = getattr(getattr(encoder, "_model", None), "tokenizer", None)
    spec = getattr(encoder, "spec", None)
    out = []
    for i, (key, label, text) in enumerate(texts):
        n_tok, pieces = None, []
        if tok is not None:
            try:
                n_tok = len(tok([text], add_special_tokens=True, verbose=False)["input_ids"][0])
                if hasattr(tok, "tokenize"):
                    pieces = [_piece(str(p)) for p in tok.tokenize(text)[:PIECE_PREVIEW]]
            except Exception:  # noqa: BLE001 - display-only detail; the signal is already checked
                n_tok, pieces = None, []
        out.append(
            EncText(
                key=key,
                label=label,
                n_tokens=n_tok,
                truncated=bool(trunc[i]),
                pieces=pieces,
                head=[float(x) for x in emb[i][:VECTOR_HEAD]],
                norm=float(np.linalg.norm(emb[i])),
            )
        )
    products = {
        k: [float(x) for x in (emb[0] * emb[i])[:PRODUCT_HEAD]] for i, k in enumerate(keys) if i > 0
    }
    return EncoderStep(
        status="ok",
        model=sig.model,
        max_seq_length=getattr(spec, "max_seq_length", None),
        dim=int(emb.shape[1]),
        texts=out,
        products=products,
        cos=cos,
        delta=delta,
    )


def _r1_step(doc: str, code: str, r1: R1Result) -> R1Step:
    sig = parse_signature(code)
    return R1Step(
        applicable=r1.applicable,
        def_line=r1.def_line,
        signature=sorted(sig.params) if sig else [],
        has_kwargs=bool(sig and sig.has_var_keyword),
        documented=sorted(documented_params(doc)),
        stale=r1.stale_params,
        undocumented=r1.undocumented_params,
        fired=r1.fired,
    )


def _r2_step(inp: AnalysisInput, r2: R2Result) -> R2Step:
    diff = code_diff(inp.old_code or "", inp.new_code or "")
    removed = content_tokens("\n".join(diff.removed))
    new = content_tokens(inp.new_code or "")
    gone = removed - new
    doc = content_tokens(inp.documentation)
    hits = sorted(doc & gone)
    _check(hits == r2.tokens, "R2 tokens")
    return R2Step(
        applicable=r2.applicable,
        removed=sorted(removed),
        still_present=sorted(removed & new),
        gone=sorted(gone),
        doc=sorted(doc),
        hits=hits,
        lines=r2.lines,
        fired=r2.fired,
    )


def _join(text: str, spans: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """Join marks with the same note that are separated only by "_" or nothing."""
    out: list[tuple[int, int, int]] = []
    for a, b, n in sorted(spans):
        if out and out[-1][2] == n and text[out[-1][1] : a] in ("", "_"):
            out[-1] = (out[-1][0], b, n)
        else:
            out.append((a, b, n))
    return out


def _merge(spans: list[tuple[int, int, int]]) -> list[Span]:
    """Drop spans overlapping an earlier one (R1 marks are added first, so they win)."""
    kept: list[tuple[int, int, int]] = []
    for s in spans:
        if all(s[1] <= k[0] or s[0] >= k[1] for k in kept):
            kept.append(s)
    return [Span(start=a, end=b, note=n) for a, b, n in sorted(kept)]


def _marks(
    inp: AnalysisInput, r1: R1Result, r2: R2Result | None, d: Decision
) -> tuple[list[Note], list[Span], list[DiffLine] | None]:
    notes: list[Note] = []
    doc_spans: list[tuple[int, int, int]] = []
    doc = inp.documentation
    if r1.fired:
        n = len(notes) + 1
        notes.append(
            Note(n=n, kind="r1", text="Documented, but not a parameter of the code (rule R1).")
        )
        for p in r1.stale_params:
            pat = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(p)}(?![A-Za-z0-9_])")
            doc_spans += [(m.start(), m.end(), n) for m in pat.finditer(doc)]
    r2_note = 0
    if r2 is not None and r2.fired:
        r2_note = len(notes) + 1
        decisive = d.r2_counted or d.reason == "r1"
        notes.append(
            Note(
                n=r2_note,
                kind="r2",
                text="Appears only in lines this change removed (rule R2)"
                + (
                    "."
                    if decisive
                    else "; not decisive here, the signals say the text fits the new code."
                ),
            )
        )
        hits = set(r2.tokens)
        doc_spans += _join(doc, [(a, b, r2_note) for a, b, t in token_spans(doc) if t in hits])

    lines = None
    if inp.mode == "change":
        lines = []
        hits = set(r2.tokens) if r2 is not None and r2.fired else set()
        for raw in difflib.ndiff(
            (inp.old_code or "").splitlines(), (inp.new_code or "").splitlines()
        ):
            sign, text = raw[:2], raw[2:]
            if sign not in ("- ", "+ ") or not text.strip():
                continue
            spans = []
            if sign == "- " and hits:
                spans = _merge(
                    _join(text, [(a, b, r2_note) for a, b, t in token_spans(text) if t in hits])
                )
            lines.append(DiffLine(sign=sign[0], text=text.rstrip(), spans=spans))  # type: ignore[arg-type]
        diff = code_diff(inp.old_code or "", inp.new_code or "")
        _check(sum(ln.sign == "-" for ln in lines) == len(diff.removed), "diff lines")
    return notes, _merge(doc_spans), lines


def _decision_step(
    inp: AnalysisInput,
    r1: R1Result,
    r2: R2Result | None,
    s1: float,
    enc: float | None,
    doc_words: int,
    th: Thresholds,
    d: Decision,
) -> DecisionStep:
    if r1.fired:
        r1_detail = "Documented but not in the signature: " + ", ".join(r1.stale_params)
    elif r1.stale_params:
        r1_detail = (
            "Missing parameters found, but the function takes **kwargs, so they may be valid"
        )
    elif r1.applicable:
        r1_detail = "Every documented parameter is in the signature"
    else:
        r1_detail = "Not applicable: no signature found, or the docstring lists no parameters"
    specs: list[tuple[str, str, str, bool, str]] = [
        ("r1", "Does rule R1 fire?", r1_detail, r1.fired, "potential_drift"),
        (
            "short_doc",
            f"Is the documentation shorter than {th.min_doc_words} words?",
            f"{doc_words} words",
            doc_words < th.min_doc_words,
            "inconclusive",
        ),
    ]
    if inp.mode == "snapshot":
        lo, hi = th.snapshot_low, th.snapshot_high
        specs += [
            (
                "snapshot_low",
                "Is the similarity below the snapshot threshold?",
                "No threshold is set (snapshot similarity is weak)"
                if lo is None
                else f"{_f(s1)} vs {_f(lo)}",
                lo is not None and s1 < lo,
                "potential_drift",
            ),
            (
                "snapshot_high",
                "Is the similarity above the snapshot threshold?",
                "No threshold is set" if hi is None else f"{_f(s1)} vs {_f(hi)}",
                hi is not None and s1 > hi,
                "no_obvious_drift",
            ),
            (
                "snapshot_no_rule",
                "Otherwise",
                "One snapshot cannot show drift without a rule",
                True,
                "inconclusive",
            ),
        ]
    else:
        z = th.combined(s1, enc)
        fired = bool(r2 and r2.fired)
        specs += [
            (
                "r2",
                "Does rule R2 fire, with the combined score at or below +eps?",
                f"R2 {'fired' if fired else 'did not fire'}; z = {_f(z)}, +eps = {_f(th.eps, 4)}",
                fired and z <= th.eps,
                "potential_drift",
            ),
            (
                "signals_negative",
                "Is the combined score below \u2212eps?",
                f"z = {_f(z)}, \u2212eps = {_f(-th.eps, 4)}",
                z < -th.eps,
                "potential_drift",
            ),
            (
                "signals_positive",
                "Is the combined score above +eps?",
                f"z = {_f(z)}, +eps = {_f(th.eps, 4)}",
                z > th.eps,
                "no_obvious_drift",
            ),
            (
                "signals_disagree",
                "Do TF-IDF and the encoder point in opposite directions?",
                "No encoder signal" if enc is None else f"TF-IDF {_f(s1)}, encoder {_f(enc)}",
                enc is not None and s1 * enc < 0,
                "inconclusive",
            ),
            (
                "signals_weak",
                "Otherwise",
                "The combined score sits inside the undecided band",
                True,
                "inconclusive",
            ),
        ]
    checks, chosen = [], None
    for key, question, detail, cond, outcome in specs:
        if chosen is not None:
            result = "not reached"
        elif cond:
            result, chosen = "yes", key
        else:
            result = "no"
        checks.append(
            Check(key=key, question=question, detail=detail, result=result, outcome=outcome)
        )  # type: ignore[arg-type]
    _check(chosen == d.reason, f"decision branch {chosen} vs {d.reason}")
    return DecisionStep(checks=checks, reason=d.reason, finding=d.finding)


def explain(
    inp: AnalysisInput,
    *,
    tfidf: TfidfModel | None = None,
    encoder: Encoder | None = None,
    thresholds: Thresholds | None = None,
    words: bool = False,
) -> Explained:
    """``analyze()`` plus a step-by-step trace whose numbers are checked against the report.

    ``words=True`` adds the word-importance step (one encoder pass per docstring word).
    """
    model = tfidf or tfidf_mod.load()
    th = thresholds or Thresholds.load()
    report = analyze(inp, tfidf=model, encoder=encoder, thresholds=th)
    change = inp.mode == "change"
    doc, code_now = inp.documentation, inp.current_code or ""
    texts = _texts(inp)
    vocab = model.vectorizer.vocabulary_

    r1 = param_mismatch(doc, code_now)
    r2 = (
        deleted_identifier_mentions(doc, inp.old_code or "", inp.new_code or "") if change else None
    )
    tf = _tfidf_step(model, texts)
    _check(report.signals.tfidf is not None, "TF-IDF signal present")
    s1 = report.signals.tfidf.value  # type: ignore[union-attr]
    _check(abs((tf.delta if change else tf.cos["code"]) - s1) < TOL, "TF-IDF signal")
    enc_step = _encoder_step(encoder, report, texts)
    enc = report.signals.encoder.value if report.signals.encoder else None

    doc_words = len(doc.split())
    d = decide(inp.mode, r1=r1, r2=r2, tfidf=s1, encoder=enc, doc_words=doc_words, th=th)
    _check(d.finding == report.finding, "finding")
    summary = summary_for(d, r1, r2)
    _check(summary == report.summary, "summary")

    combine = None
    if change:
        parts = [s1 / th.scale_tfidf] + ([enc / th.scale_encoder] if enc is not None else [])
        combine = CombineStep(
            tfidf=s1,
            encoder=enc,
            scale_tfidf=th.scale_tfidf,
            scale_encoder=th.scale_encoder,
            parts=parts,
            z=th.combined(s1, enc),
            eps=th.eps,
        )
    notes, doc_spans, diff_lines = _marks(inp, r1, r2, d)
    order = ["doc", "old", "new"] if change else ["doc", "code"]
    by_key = {k: (k, label, t) for k, label, t in texts}

    trace = Trace(
        mode=inp.mode,
        inputs=[_stat(*by_key[k]) for k in order],
        documentation=doc,
        doc_spans=doc_spans,
        notes=notes,
        diff=diff_lines,
        tokens=[_token_step(*by_key[k], vocab) for k in order],
        r1=_r1_step(doc, code_now, r1),
        r2=_r2_step(inp, r2) if r2 is not None else None,
        tfidf=tf,
        encoder=enc_step,
        combine=combine,
        decision=_decision_step(inp, r1, r2, s1, enc, doc_words, th, d),
        text=TextStep(reason=d.reason, summary=summary, next_step=next_step_for(d, r1, r2)),
        constants=Constants(
            thresholds_version=th.version,
            eps=th.eps,
            scale_tfidf=th.scale_tfidf,
            scale_encoder=th.scale_encoder,
            min_doc_words=th.min_doc_words,
            encoder_key=th.encoder,
        ),
    )
    if words and change and report.signals.encoder is not None and encoder is not None:
        trace.words = _words_step(encoder, inp, report.signals.encoder.model)
    return Explained(report=report, trace=trace)


_DOC_WORD = re.compile(r"\S+")  # whitespace-separated words, as a reader sees them
MAX_WORDS = 80


def _piece(p: str) -> str:
    """Readable sub-word token: byte-level BPE markers (Granite) become · (new word) and ↵."""
    return p.replace("Ġ", "·").replace("Ċ", "↵").replace("ĉ", "⇥")


def _words_step(encoder: Encoder, inp: AnalysisInput, model: str) -> WordsStep:
    """Occlusion on the encoder Δ: drop each word, re-encode the docstring, compare Δ."""
    doc, new, old = inp.documentation, inp.new_code or "", inp.old_code or ""
    found = list(_DOC_WORD.finditer(doc))[:MAX_WORDS]
    variants = [doc] + [doc[: m.start()] + doc[m.end() :] for m in found]
    emb, _ = encoder.encode([*variants, new, old])
    emb = np.asarray(emb, dtype=float)
    d, n, o = emb[:-2], emb[-2], emb[-1]
    delta = d @ n - d @ o
    base = float(delta[0])
    weights = [
        WordWeight(start=m.start(), end=m.end(), weight=base - float(x))
        for m, x in zip(found, delta[1:], strict=True)
    ]
    ranked = sorted(weights, key=lambda w: w.weight)

    def names(ws: list[WordWeight]) -> list[str]:
        return list(dict.fromkeys(doc[w.start : w.end].strip(".,:;()`'\"") for w in ws))[:5]

    return WordsStep(
        model=model,
        delta=base,
        words=weights,
        n_words=len(found),
        passes=len(variants),
        toward_stale=names([w for w in ranked if w.weight < 0]),
        toward_fits=names([w for w in reversed(ranked) if w.weight > 0]),
    )
