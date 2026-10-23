import json
import shutil

import pytest
from conftest import FIXTURES
from typer.testing import CliRunner

from spequlator.cli import app
from spequlator.models import tfidf as tfidf_mod
from spequlator.schemas import Report

runner = CliRunner()
SP = FIXTURES / "stale_param"
AL = FIXTURES / "aligned"


@pytest.fixture
def env(tmp_path, monkeypatch, small_tfidf):
    """Isolated artifacts (small train-fitted TF-IDF) and a fixture-only dataset folder."""
    art, data = tmp_path / "artifacts", tmp_path / "data"
    data.mkdir()
    tfidf_mod.save(small_tfidf, art / "tfidf.joblib")
    shutil.copy(FIXTURES / "codocbench_mini.jsonl", data / "train.jsonl")
    (data / "test.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(art))
    monkeypatch.setenv("SPEQULATOR_DATA_DIR", str(data))
    return tmp_path


def test_help_lists_commands():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    for cmd in ("analyze", "data", "eval"):
        assert cmd in res.output


def test_change_mode_json_flags_stale_param(env):
    args = ["analyze", "--old-code-file", str(SP / "old.py"), "--new-code-file", str(SP / "new.py")]
    res = runner.invoke(app, [*args, "--docs-file", str(SP / "doc.txt"), "--format", "json"])
    assert res.exit_code == 0, res.output
    rep = Report.model_validate(json.loads(res.output))
    assert rep.finding == "potential_drift" and rep.signals.encoder is None


def test_snapshot_mode_text_output(env):
    res = runner.invoke(
        app, ["analyze", "--code-file", str(AL / "code.py"), "--docs-file", str(AL / "doc.txt")]
    )
    assert res.exit_code == 0, res.output
    assert "Finding:" in res.output and "not probabilities" in res.output


def test_example_id(env):
    res = runner.invoke(app, ["analyze", "--example-id", "8e8e00c86a25", "--format", "json"])
    assert res.exit_code == 0, res.output
    assert json.loads(res.output)["finding"] == "potential_drift"


@pytest.mark.parametrize(
    "args",
    [
        ["analyze", "--code-file", str(AL / "code.py")],  # no documentation
        ["analyze", "--docs-text", "Doc text here.", "--old-code-file", str(SP / "old.py")],
        ["analyze", "--example-id", "000000000000"],
        ["analyze", "--example-id", "8e8e00c86a25", "--docs-text", "x"],
        ["analyze", "--docs-text", "Doc.", "--code-file", "missing.py"],
    ],
)
def test_invalid_input_exit_2(env, args):
    assert runner.invoke(app, args).exit_code == 2


def test_missing_artifact_exit_3(env, monkeypatch, tmp_path):
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(tmp_path / "empty"))
    res = runner.invoke(
        app, ["analyze", "--code-file", str(AL / "code.py"), "--docs-file", str(AL / "doc.txt")]
    )
    assert res.exit_code == 3


def test_eval_cache_refuses_test_split(env):
    assert runner.invoke(app, ["eval", "cache", "--split", "test"]).exit_code == 2


def test_data_examples_lists_fixture(env):
    res = runner.invoke(app, ["data", "examples", "--limit", "3"])
    assert res.exit_code == 0 and len(res.output.strip().splitlines()) == 3
