"""Single entry point for every interface: ``analyze(AnalysisInput) -> Report`` (FR-1, D-011)."""

from __future__ import annotations

import time

import numpy as np

from spequlator.models import tfidf as tfidf_mod
from spequlator.models.base import Encoder, EncoderUnavailable
from spequlator.models.tfidf import TfidfModel
from spequlator.nlp.preprocessing import code_diff
from spequlator.nlp.rules import R2Result, deleted_identifier_mentions, param_mismatch
from spequlator.pipeline.report import Thresholds, decide, next_step_for, summary_for
from spequlator.schemas import (
    AnalysisInput,
    EncoderSignal,
    Evidence,
    Report,
    ReportMeta,
    Signals,
    SignalValue,
)

SCOPE_NOTE = (
    "Only this function and its documentation were inspected; callers, runtime behaviour "
    "and other documentation were not."
)
SIMILARITY_NOTE = "Similarity signals measure shared words or meaning, not correctness."


def _encoder_signal(encoder: Encoder, inp: AnalysisInput) -> EncoderSignal:
    if inp.mode == "change":
        emb, trunc = encoder.encode([inp.documentation, inp.new_code, inp.old_code])
        value = float(np.dot(emb[0], emb[1]) - np.dot(emb[0], emb[2]))
        kind = "delta"
    else:
        emb, trunc = encoder.encode([inp.documentation, inp.code])
        value = float(np.dot(emb[0], emb[1]))
        kind = "absolute"
    return EncoderSignal(value=value, kind=kind, model=encoder.name, truncated=any(trunc))


def analyze(
    inp: AnalysisInput,
    *,
    tfidf: TfidfModel | None = None,
    encoder: Encoder | None = None,
    thresholds: Thresholds | None = None,
) -> Report:
    t0 = time.perf_counter()
    tfidf = tfidf or tfidf_mod.load()
    th = thresholds or Thresholds.load()
    doc, code_now = inp.documentation, inp.current_code
    observations: list[str] = []
    evidence: list[Evidence] = []
    uncertainties: list[str] = [SCOPE_NOTE, SIMILARITY_NOTE]

    # --- rules -------------------------------------------------------------------------
    r1 = param_mismatch(doc, code_now)
    r2: R2Result | None = None
    if inp.mode == "change":
        diff = code_diff(inp.old_code, inp.new_code)
        observations.append(
            f"The code change removes {len(diff.removed)} line(s) and adds {len(diff.added)}."
        )
        if not diff.changed:
            uncertainties.append("Old and new code are identical, so there is no change to check.")
        r2 = deleted_identifier_mentions(doc, inp.old_code, inp.new_code)
        s1 = SignalValue(value=tfidf.delta(doc, inp.old_code, inp.new_code), kind="delta")
    else:
        s1 = SignalValue(value=tfidf.cosine(doc, inp.code), kind="absolute")
        uncertainties.append(
            "Snapshot mode: without the code before the change, drift can only be shown "
            "by a parameter mismatch."
        )

    if r1.applicable:
        observations.append(
            f"Signature `{r1.def_line}`; documented parameters not in it: "
            f"{', '.join(r1.stale_params) or 'none'}."
        )
        if r1.stale_params and not r1.fired:
            uncertainties.append(
                "The function accepts **kwargs, so documented-but-unlisted parameters "
                f"({', '.join(r1.stale_params)}) may be valid; not treated as evidence."
            )
    if r1.fired:
        evidence.append(
            Evidence(
                kind="rule_r1",
                text=f"Documented but not in the signature: {', '.join(r1.stale_params)}",
                lines=[r1.def_line] if r1.def_line else [],
            )
        )

    # --- encoder (optional, D-019) ------------------------------------------------------
    enc: EncoderSignal | None = None
    if encoder is None:
        uncertainties.append(
            "Deep-learning signal not computed (encoder not loaded); TF-IDF and rule evidence only."
        )
    else:
        try:
            enc = _encoder_signal(encoder, inp)
            if enc.truncated:
                uncertainties.append(
                    "Some input was longer than the encoder limit and was truncated."
                )
        except EncoderUnavailable as exc:
            uncertainties.append(
                f"Deep-learning signal unavailable ({exc}); TF-IDF and rules only."
            )

    # --- decision -----------------------------------------------------------------------
    doc_words = len(doc.split())
    d = decide(
        inp.mode,
        r1=r1,
        r2=r2,
        tfidf=s1.value,
        encoder=enc.value if enc else None,
        doc_words=doc_words,
        th=th,
    )
    if r2 is not None and r2.fired:
        evidence.append(
            Evidence(
                kind="rule_r2",
                text=f"Mentioned in the docs but removed from the code: {', '.join(r2.tokens[:5])}",
                lines=[f"- {ln}" for ln in r2.lines],
            )
        )
        if not d.r2_counted and d.reason != "r1":
            uncertainties.append(
                "Removed identifiers are mentioned, but the similarity signals say the "
                "documentation fits the new code; not treated as decisive."
            )
    shared = tfidf.shared_terms(doc, code_now)
    if shared:
        evidence.append(
            Evidence(
                kind="term_overlap", text=f"Terms shared with the current code: {', '.join(shared)}"
            )
        )
    if d.reason == "short_doc":
        uncertainties.append(f"Documentation has only {doc_words} word(s).")

    signal_bits = [f"TF-IDF {s1.kind} {s1.value:+.3f}"]
    if enc:
        signal_bits.append(f"encoder {enc.kind} {enc.value:+.3f}")
    direction = " (negative = closer to the old code)" if inp.mode == "change" else ""
    explanation = (
        f"Observed: {'; '.join(e.text for e in evidence if e.kind != 'term_overlap') or 'no rule evidence'}; "
        f"{', '.join(signal_bits)}{direction}. Interpretation: {summary_for(d, r1, r2)}"
    )

    return Report(
        mode=inp.mode,
        source=inp.source,
        finding=d.finding,
        summary=summary_for(d, r1, r2),
        observations=observations,
        evidence=evidence,
        signals=Signals(tfidf=s1, encoder=enc),
        explanation=explanation,
        uncertainties=uncertainties,
        review_recommended=d.finding != "no_obvious_drift",
        next_step=next_step_for(d, r1, r2),
        meta=ReportMeta(
            thresholds_version=th.version,
            tfidf_artifact_sha256=tfidf.meta.get("sha256"),
            elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
        ),
    )
