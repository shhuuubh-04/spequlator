"""Transparent decision rule (D-017) and template-based report text (D-009).

Every sentence produced here is traceable to a rule result or a signal value.
Findings are reviewer-facing heuristic states, never ground truth (D-003, D-007).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from spequlator.nlp.rules import R1Result, R2Result
from spequlator.paths import artifacts_dir
from spequlator.schemas import Finding, Mode

THRESHOLDS_NAME = "thresholds.json"


@dataclass(frozen=True)
class Thresholds:
    """Dead-bands for delta signals. Learned on TRAIN only and frozen before the test run.

    Default eps_tfidf=0.01 is provisional: on the train split (TF-IDF + rules, no encoder)
    it leaves ~33% inconclusive and keeps coverage >= 60%. `eval calibrate` (H3) replaces it.
    """

    version: str = "default-train-provisional-2026-10-23"
    eps_tfidf: float = 0.01
    eps_encoder: float = 0.0
    min_doc_words: int = 5
    snapshot_low: float | None = (
        None  # snapshot similarity is weak (F3): unset = no score-only finding
    )
    snapshot_high: float | None = None

    @classmethod
    def load(cls, path: Path | None = None) -> Thresholds:
        path = path or artifacts_dir() / THRESHOLDS_NAME
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, path: Path | None = None) -> Path:
        path = path or artifacts_dir() / THRESHOLDS_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        return path


@dataclass(frozen=True)
class Decision:
    finding: Finding
    reason: str  # machine-readable key used to pick the summary template
    r2_counted: bool = False


def decide(
    mode: Mode,
    *,
    r1: R1Result,
    r2: R2Result | None,
    tfidf: float,
    encoder: float | None,
    doc_words: int,
    th: Thresholds,
) -> Decision:
    """Apply the D-017 rule. ``tfidf``/``encoder`` are deltas (change) or cosines (snapshot)."""
    if r1.fired:
        return Decision("potential_drift", "r1")
    if doc_words < th.min_doc_words:
        return Decision("inconclusive", "short_doc")

    if mode == "snapshot":
        if th.snapshot_low is not None and tfidf < th.snapshot_low:
            return Decision("potential_drift", "snapshot_low")
        if th.snapshot_high is not None and tfidf > th.snapshot_high:
            return Decision("no_obvious_drift", "snapshot_high")
        return Decision("inconclusive", "snapshot_no_rule")

    signals = [(tfidf, th.eps_tfidf)] + ([(encoder, th.eps_encoder)] if encoder is not None else [])
    all_neg = all(v < -eps for v, eps in signals)
    all_pos = all(v > eps for v, eps in signals)
    any_pos = any(v > eps for v, eps in signals)

    # R2 counts unless a signal clearly says the doc fits the NEW code (train: cuts false flags).
    if r2 is not None and r2.fired and not any_pos:
        return Decision("potential_drift", "r2", r2_counted=True)
    if all_neg:
        return Decision("potential_drift", "signals_negative")
    if all_pos:
        return Decision("no_obvious_drift", "signals_positive")
    if len(signals) > 1 and any_pos and any(v < -eps for v, eps in signals):
        return Decision("inconclusive", "signals_disagree")
    return Decision("inconclusive", "signals_weak")


def _ticks(names: list[str]) -> str:
    return ", ".join(f"`{n}`" for n in names)


def summary_for(d: Decision, r1: R1Result, r2: R2Result | None) -> str:
    if d.reason == "r1":
        return (
            f"The documentation describes parameter(s) {_ticks(r1.stale_params)} "
            "that the current code does not have."
        )
    if d.reason == "r2" and r2 is not None:
        return f"The documentation mentions {_ticks(r2.tokens[:5])}, which this change removed from the code."
    return {
        "signals_negative": "The documentation matches the old code better than the new code.",
        "signals_positive": "No sign of drift: the documentation fits the new code at least as well as the old code.",
        "signals_disagree": "The comparison signals disagree, so no finding is made.",
        "signals_weak": "The change does not clearly move the documentation's fit either way.",
        "short_doc": "The documentation is too short to compare reliably.",
        "snapshot_no_rule": (
            "No parameter mismatch found. A single code snapshot cannot show drift reliably; "
            "provide the code before and after the change."
        ),
        "snapshot_low": "The documentation shares unusually little with the code.",
        "snapshot_high": "The documentation shares a lot with the code.",
    }[d.reason]


def next_step_for(d: Decision, r1: R1Result, r2: R2Result | None) -> str:
    if d.reason == "r1":
        return f"Update the parameter list: remove or rename {_ticks(r1.stale_params)} to match the signature."
    if d.reason == "r2" and r2 is not None:
        return (
            f"Check whether statements about {_ticks(r2.tokens[:3])} still hold after the change."
        )
    if d.finding == "potential_drift":
        return "Re-read the documentation against the new code and update the parts that describe old behaviour."
    if d.finding == "no_obvious_drift":
        return "No action suggested; a quick skim is still worthwhile for behavioural changes."
    if d.reason == "snapshot_no_rule":
        return "Re-run in change mode (code before and after) for a drift check."
    return "Review manually: compare the documentation with the code diff."
