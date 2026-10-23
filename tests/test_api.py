import json
import shutil

import pytest
from conftest import FIXTURES, read
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from spequlator.api import app
from spequlator.cli import app as cli_app
from spequlator.models import tfidf as tfidf_mod
from spequlator.schemas import MAX_CHARS, Report

SP = FIXTURES / "stale_param"


@pytest.fixture
def client(tmp_path, monkeypatch, small_tfidf):
    art, data = tmp_path / "artifacts", tmp_path / "data"
    data.mkdir()
    tfidf_mod.save(small_tfidf, art / "tfidf.joblib")
    shutil.copy(FIXTURES / "codocbench_mini.jsonl", data / "train.jsonl")
    (data / "test.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(art))
    monkeypatch.setenv("SPEQULATOR_DATA_DIR", str(data))
    monkeypatch.setenv("SPEQULATOR_RESULTS_DIR", str(tmp_path / "results"))
    with TestClient(app) as c:
        yield c


CHANGE = {
    "documentation": read("stale_param", "doc.txt"),
    "old_code": read("stale_param", "old.py"),
    "new_code": read("stale_param", "new.py"),
}


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["tfidf"] is True
    assert body["encoder"] == "disabled"  # default thresholds name no encoder


def test_analyze_change_mode(client):
    res = client.post("/api/analyze", json=CHANGE)
    assert res.status_code == 200
    rep = Report.model_validate(res.json())
    assert rep.mode == "change" and rep.finding == "potential_drift"


def test_analyze_snapshot_mode(client):
    payload = {"documentation": read("aligned", "doc.txt"), "code": read("aligned", "code.py")}
    res = client.post("/api/analyze", json=payload)
    assert res.status_code == 200 and res.json()["mode"] == "snapshot"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"documentation": "Doc text.", "code": "   "}, "code"),
        ({"documentation": "", "code": "def f(): pass"}, "documentation"),
        ({"documentation": "Doc.", "code": "x" * (MAX_CHARS + 1)}, "code"),
        ({"documentation": "Doc.", "old_code": "def f(): pass"}, None),
    ],
)
def test_validation_errors_are_uniform(client, payload, field):
    res = client.post("/api/analyze", json=payload)
    assert res.status_code == 422
    err = res.json()["error"]
    assert err["code"] == "invalid_input" and err["message"]
    if field:
        assert err["field"] == field
    assert "Traceback" not in res.text


def test_examples_and_example_detail(client):
    items = client.get("/api/examples", params={"limit": 3}).json()
    assert len(items) == 3 and {"record_id", "project", "function"} <= set(items[0])
    detail = client.get("/api/examples/8e8e00c86a25").json()
    assert detail["function"] == "observe_lr"
    assert not any(ln.startswith("? ") for ln in detail["diff_code"])
    assert client.get("/api/examples/000000000000").status_code == 404


def test_analyze_example(client):
    res = client.post(
        "/api/analyze/example", json={"record_id": "8e8e00c86a25", "doc_version": "old"}
    )
    assert res.status_code == 200 and res.json()["finding"] == "potential_drift"
    bad = client.post("/api/analyze/example", json={"record_id": "nope", "doc_version": "old"})
    assert bad.status_code == 404 and bad.json()["error"]["field"] == "record_id"


def test_cli_and_api_give_the_same_report(client):
    """FR-1: one shared core. Same input -> same JSON (ignoring timing)."""
    args = ["analyze", "--old-code-file", str(SP / "old.py"), "--new-code-file", str(SP / "new.py")]
    cli = CliRunner().invoke(
        cli_app, [*args, "--docs-file", str(SP / "doc.txt"), "--format", "json", "--no-encoder"]
    )
    api = client.post("/api/analyze", json={**CHANGE, "use_encoder": False}).json()
    a, b = json.loads(cli.output), api
    for rep in (a, b):
        rep["meta"].pop("elapsed_ms")
    assert a == b
