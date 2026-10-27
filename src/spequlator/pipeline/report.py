"""Transparent decision rule (D-017, D-025, D-028) and template-based report text (D-009).

Every sentence produced here is traceable to a rule result or a signal value.
Findings are reviewer-facing heuristic states, never ground truth (D-003, D-007).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from spequlator.nlp.rules import R1Result, R2Result
from spequlator.paths import artifacts_dir
from spequlator.schemas import Finding, Mode

THRESHOLDS_NAME = "thresholds.json"
THRESHOLDS_V2_NAME = "thresholds_v2.json"  # v2: TF-IDF + Granite (D-034)


@dataclass(frozen=True)
class Thresholds:
    """Decision-rule settings. Learned on TRAIN only and frozen before the test run (D-021).

    Delta signals are combined into one score: the mean of each available signal divided
    by its train-split spread (``scale_*``, a z-score without centring), D-028. One dead-band
    ``eps`` on that score separates potential_drift / inconclusive / no_obvious_drift.
    Defaults (scale 1.0, eps 0.01) reproduce the provisional TF-IDF-only rule (D-025).
    """

    version: str = "default-train-provisional-2026-10-23"
    eps: float = 0.01
    scale_tfidf: float = 1.0
    scale_encoder: float = 1.0
    encoder: str | None = None  # encoder key the settings were calibrated for
    min_doc_words: int = 5
    snapshot_low: float | None = None  # snapshot similarity is weak (F3): unset = no finding
    snapshot_high: float | None = None

    def combined(self, tfidf: float, encoder: float | None) -> float:
        parts = [tfidf / self.scale_tfidf]
        if encoder is not None:
            parts.append(encoder / self.scale_encoder)
        return sum(parts) / len(parts)

    @classmethod
    def active(cls) -> Thresholds:
        """Settings the app and CLI analyse with: v2 (TF-IDF + Granite, D-034) once promoted.

        Falls back to the frozen v1 settings when artifacts/thresholds_v2.json is absent or
        SPEQULATOR_SYSTEM=v1. Evaluation code always uses load(), i.e. v1.
        """
        v2 = artifacts_dir() / THRESHOLDS_V2_NAME
        if os.environ.get("SPEQULATOR_SYSTEM", "").strip().lower() != "v1" and v2.exists():
            return cls.load(v2)
        return cls.load()

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
    """Apply the D-017/D-028 rule. ``tfidf``/``encoder`` are deltas (change) or cosines (snapshot)."""
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

    z = th.combined(tfidf, encoder)
    # R2 counts unless the combined signal clearly says the doc fits the NEW code (D-025).
    if r2 is not None and r2.fired and z <= th.eps:
        return Decision("potential_drift", "r2", r2_counted=True)
    if z < -th.eps:
        return Decision("potential_drift", "signals_negative")
    if z > th.eps:
        return Decision("no_obvious_drift", "signals_positive")
    if encoder is not None and tfidf * encoder < 0:
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
