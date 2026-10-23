import json

import pytest
from pydantic import ValidationError

from spequlator.schemas import FINDINGS, MAX_CHARS, AnalysisInput, Evidence, Report


def test_snapshot_mode():
    inp = AnalysisInput(documentation="Returns users.", code="def f(): pass")
    assert inp.mode == "snapshot"
    assert inp.current_code == "def f(): pass"


def test_change_mode():
    inp = AnalysisInput(documentation="Doc.", old_code="def f(a): pass", new_code="def f(b): pass")
    assert inp.mode == "change"
    assert inp.current_code == "def f(b): pass"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"documentation": "", "code": "x"},
        {"documentation": "   \n", "code": "x"},
        {"documentation": "Doc."},  # no code at all
        {"documentation": "Doc.", "code": "  "},
        {"documentation": "Doc.", "old_code": "x"},  # change mode missing new_code
        {"documentation": "Doc.", "old_code": "x", "new_code": " "},
        {"documentation": "Doc.", "code": "x", "old_code": "x", "new_code": "y"},  # both modes
        {"documentation": "Doc.", "code": "x", "surprise": 1},  # unknown field
    ],
)
def test_invalid_inputs_rejected(kwargs):
    with pytest.raises(ValidationError):
        AnalysisInput(**kwargs)


def test_oversized_input_rejected_not_truncated():
    with pytest.raises(ValidationError):
        AnalysisInput(documentation="Doc.", code="x" * (MAX_CHARS + 1))


def test_report_roundtrip_and_allowed_findings():
    rep = Report(
        mode="change",
        finding="potential_drift",
        summary="s",
        evidence=[Evidence(kind="rule_r1", text="documented but not in signature: key")],
    )
    again = Report.model_validate_json(rep.model_dump_json())
    assert again == rep
    assert again.schema_version == "1.2"
    assert set(FINDINGS) == {"potential_drift", "no_obvious_drift", "inconclusive"}
    with pytest.raises(ValidationError):
        Report(mode="change", finding="bug", summary="s")


def test_schema_never_mentions_confidence_or_probability():
    schema = json.dumps(Report.model_json_schema()).lower()
    assert "confidence" not in schema
    assert "probability" not in schema
