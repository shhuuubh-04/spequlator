"""Typed input and report schemas shared by the core, CLI and API.

See docs/ARCHITECTURE.md ("Report schema") and decisions D-003, D-015, D-016.
The finding values are reviewer-facing heuristic states, not ground-truth labels.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.2"
MAX_CHARS = 20_000  # per text field; documented limit, never silently truncated

Mode = Literal["change", "snapshot"]
Finding = Literal["potential_drift", "no_obvious_drift", "inconclusive"]
FINDINGS: tuple[str, ...] = ("potential_drift", "no_obvious_drift", "inconclusive")


class Source(BaseModel):
    """Where the analysed text came from."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["manual", "codocbench"] = "manual"
    record_id: str | None = None
    project: str | None = None
    function: str | None = None
    doc_version: Literal["old", "new"] | None = None


class AnalysisInput(BaseModel):
    """One analysis request.

    Snapshot mode: ``documentation`` + ``code``.
    Change mode (primary, D-016): ``documentation`` + ``old_code`` + ``new_code``.
    """

    model_config = ConfigDict(extra="forbid")

    documentation: str = Field(max_length=MAX_CHARS)
    code: str | None = Field(default=None, max_length=MAX_CHARS)
    old_code: str | None = Field(default=None, max_length=MAX_CHARS)
    new_code: str | None = Field(default=None, max_length=MAX_CHARS)
    source: Source = Field(default_factory=Source)

    @model_validator(mode="after")
    def _check_mode(self) -> AnalysisInput:
        if not self.documentation.strip():
            raise ValueError("documentation: must not be empty")
        has_snapshot = self.code is not None
        has_change = self.old_code is not None or self.new_code is not None
        if has_snapshot and has_change:
            raise ValueError(
                "give either 'code' (snapshot) or 'old_code' + 'new_code' (change), not both"
            )
        if has_change:
            if self.old_code is None or self.new_code is None:
                raise ValueError("change mode needs both 'old_code' and 'new_code'")
            if not self.old_code.strip():
                raise ValueError("old_code: must not be empty")
            if not self.new_code.strip():
                raise ValueError("new_code: must not be empty")
        elif has_snapshot:
            if not self.code.strip():
                raise ValueError("code: must not be empty")
        else:
            raise ValueError("missing code: give 'code' or 'old_code' + 'new_code'")
        return self

    @property
    def mode(self) -> Mode:
        return "change" if self.old_code is not None else "snapshot"

    @property
    def current_code(self) -> str:
        """The code the documentation should describe now."""
        return self.new_code if self.mode == "change" else self.code  # type: ignore[return-value]


class Evidence(BaseModel):
    """An objective, checkable observation backing the finding."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["rule_r1", "rule_r2", "diff", "term_overlap"]
    text: str
    lines: list[str] = Field(default_factory=list)


class SignalValue(BaseModel):
    """A similarity/relatedness signal (a score, not a calibrated likelihood)."""

    model_config = ConfigDict(extra="forbid")

    value: float
    kind: Literal["delta", "absolute"]


class EncoderSignal(SignalValue):
    model: str
    truncated: bool = False


class Signals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tfidf: SignalValue | None = None
    encoder: EncoderSignal | None = None


class ReportMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thresholds_version: str | None = None
    tfidf_artifact_sha256: str | None = None
    elapsed_ms: float | None = None


class Report(BaseModel):
    """Structured, evidence-grounded analysis report (FR-7)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.2"] = SCHEMA_VERSION
    mode: Mode
    source: Source = Field(default_factory=Source)
    finding: Finding
    summary: str
    observations: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    signals: Signals = Field(default_factory=Signals)
    explanation: str = ""
    uncertainties: list[str] = Field(default_factory=list)
    review_recommended: bool = True
    meta: ReportMeta = Field(default_factory=ReportMeta)
