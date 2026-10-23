import json

import numpy as np
import pandas as pd
import pytest

from spequlator.evaluation import frozen_eval as fe
from spequlator.evaluation.proxy_task import FrozenSplitError
from spequlator.pipeline.report import Thresholds


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    art, res = tmp_path / "artifacts", tmp_path / "results"
    (art / "minilm-ft").mkdir(parents=True)
    (art / "tfidf.joblib").write_bytes(b"tfidf")
    (art / "thresholds.json").write_text(json.dumps({"eps": 0.1}), encoding="utf-8")
    (art / "finetune_gate.json").write_text(json.dumps({"decision": "GO"}), encoding="utf-8")
    (art / "minilm-ft" / "model.safetensors").write_bytes(b"weights")
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(art))
    monkeypatch.setenv("SPEQULATOR_RESULTS_DIR", str(res))
    return art, res


def test_freeze_then_verify_then_detect_change(dirs):
    art, res = dirs
    path = fe.freeze()
    record = json.loads(path.read_text(encoding="utf-8"))
    assert set(record["artifacts_sha256"]) == set(fe.PINNED)
    assert (res / "frozen" / "thresholds.json").exists()
    assert fe.verify_frozen()["artifacts_sha256"] == record["artifacts_sha256"]
    (art / "minilm-ft" / "model.safetensors").write_bytes(b"retrained")
    with pytest.raises(fe.FrozenMismatch, match="minilm-ft"):
        fe.verify_frozen()


def test_freeze_requires_all_artifacts(dirs):
    art, _ = dirs
    (art / "finetune_gate.json").unlink()
    with pytest.raises(FileNotFoundError, match="finetune_gate.json"):
        fe.freeze()


def test_run_guards(dirs):
    with pytest.raises(FrozenSplitError):
        fe.run_test(confirm=False)
    with pytest.raises(fe.FrozenMismatch, match="not frozen"):
        fe.run_test(confirm=True)


def _frame(n=120, seed=1):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "record_id": [f"r{i}" for i in range(n)],
            "project_key": [f"o/p{i % 12}" for i in range(n)],
            "doc_edit_ratio": rng.random(n),
        }
    )
    for pair, shift in (("stale", -0.05), ("updated", 0.05)):
        df[f"{pair}_tfidf_abs"] = rng.random(n)
        df[f"{pair}_tfidf_delta"] = rng.normal(shift, 0.08, n)
        df[f"{pair}_r1"] = rng.random(n) < (0.1 if pair == "stale" else 0.02)
        df[f"{pair}_r2"] = rng.random(n) < (0.2 if pair == "stale" else 0.1)
        df[f"{pair}_doc_words"] = 20
        for k in fe.ENCODERS:
            df[f"{pair}_{k}_delta"] = rng.normal(shift, 0.06, n)
            df[f"{pair}_{k}_truncated"] = False
    return df


def test_compute_metrics_and_markdown():
    th = Thresholds(eps=0.1, scale_tfidf=0.08, scale_encoder=0.06, encoder="minilm-ft")
    m = fe.compute_metrics(_frame(), th, n_boot=50)
    assert m["n_records"] == 120 and m["n_projects"] == 12
    base = m["signals"][fe.BASELINE]
    assert "pooled_auc_minus_baseline" not in base
    for row in m["signals"].values():
        lo, hi = row["pooled_auc"]["ci95"]
        assert lo <= row["pooled_auc"]["value"] <= hi
    assert m["signals"]["MiniLM delta"]["pooled_auc_minus_baseline"]["ci95"][0] <= 1
    assert 0 <= m["decision_rule"]["coverage"] <= 1
    assert len(m["strata_pairwise_accuracy"]) == len(fe.STRATA)
    md = fe.to_markdown(m)
    assert "| Signal |" in md and "Decision rule" in md and "| R1 |" in md
