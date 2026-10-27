import json

import numpy as np
import pandas as pd
import pytest

from spequlator.evaluation import phase2, v2
from spequlator.evaluation.calibrate import calibrate, choose_eps
from spequlator.evaluation.frozen_eval import _sha256
from spequlator.models.encoder import spec_for
from spequlator.pipeline.report import Thresholds


def _train_frame(n=120, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "record_id": [f"r{i}" for i in range(n)],
            "stale_tfidf_delta": rng.normal(-0.03, 0.03, n),
            "updated_tfidf_delta": rng.normal(0.03, 0.03, n),
            "stale_r1": rng.random(n) < 0.1,
            "updated_r1": rng.random(n) < 0.02,
            "stale_r2": rng.random(n) < 0.2,
            "updated_r2": rng.random(n) < 0.1,
            "stale_doc_words": 20,
            "updated_doc_words": 20,
        }
    )


def test_active_uses_v2_unless_v1_is_asked_for(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(tmp_path))
    monkeypatch.delenv("SPEQULATOR_SYSTEM", raising=False)
    Thresholds(version="v1-test").save()
    assert Thresholds.active().version == "v1-test"
    Thresholds(version="v2-test", encoder="granite-ft").save(tmp_path / "thresholds_v2.json")
    assert Thresholds.active().encoder == "granite-ft"
    assert Thresholds.load().version == "v1-test"  # evaluation code keeps v1
    monkeypatch.setenv("SPEQULATOR_SYSTEM", "v1")
    assert Thresholds.active().version == "v1-test"


def test_granite_spec():
    spec = spec_for("granite-ft")
    assert spec.max_seq_length == 256 and spec.model_id.endswith("granite-ft")
    assert spec.name.startswith("granite-ft (")


def test_choose_eps_is_the_calibrate_rule():
    df = _train_frame()
    rng = np.random.default_rng(1)
    df["stale_enc_delta"] = rng.normal(-0.02, 0.02, len(df))
    df["updated_enc_delta"] = rng.normal(0.02, 0.02, len(df))
    th, _ = calibrate(df, encoder="minilm")
    same, _ = choose_eps(
        df, Thresholds(encoder="minilm", scale_tfidf=th.scale_tfidf, scale_encoder=th.scale_encoder)
    )
    assert same.eps == th.eps


def _fake_run3(tmp_path, monkeypatch):
    art, res = tmp_path / "artifacts", tmp_path / "results"
    monkeypatch.setenv("SPEQULATOR_ARTIFACTS_DIR", str(art))
    monkeypatch.setenv("SPEQULATOR_RESULTS_DIR", str(res))
    p2 = art / "phase2"
    (p2 / "granite-ft").mkdir(parents=True)
    (p2 / "granite-ft" / "model.safetensors").write_bytes(b"weights")
    df = _train_frame()
    df.to_parquet(art / "signals_train_base.parquet")
    rng = np.random.default_rng(2)
    dev = df.iloc[:60]
    pd.DataFrame(
        {
            "record_id": dev["record_id"],
            "stale_enc_delta": rng.normal(-0.02, 0.02, len(dev)),
            "updated_enc_delta": rng.normal(0.02, 0.02, len(dev)),
            "encoder": "granite-ft",
        }
    ).to_parquet(p2 / "signals_train_granite-ft.parquet")
    sha = {
        "granite-ft": _sha256(p2 / "granite-ft"),
        "signals_train_granite-ft.parquet": _sha256(p2 / "signals_train_granite-ft.parquet"),
    }
    (p2 / "phase2_manifest.json").write_text(json.dumps({"run": 3, "sha256": sha}))
    Thresholds(version="v1-test", encoder="minilm-ft", eps=0.15, scale_tfidf=0.09).save()
    run = res / "phase2_run3"
    run.mkdir(parents=True)
    frozen = {
        "run": 3,
        "manifest_sha256": "m",
        "artifacts_sha256": sha,
        "best_granite": {"name": "granite c3 (mean of 3 seeds)"},
        "combine": {"scale_tfidf": 0.09, "scale_ft2": 0.05, "scale_granite": 0.04},
    }
    (run / "FROZEN.json").write_text(json.dumps(frozen))
    return art, res


def test_promote_writes_v2_settings_from_the_frozen_run(tmp_path, monkeypatch):
    monkeypatch.delenv("SPEQULATOR_SYSTEM", raising=False)
    art, res = _fake_run3(tmp_path, monkeypatch)
    r = v2.promote()
    th = Thresholds.active()
    assert th.encoder == "granite-ft" and th.version.startswith("v2-tfidf-granite-train-")
    assert th.scale_tfidf == 0.09 and th.scale_encoder == 0.04 and th.min_doc_words == 5
    assert r["calibration_records"] == 60 and (art / "granite-ft" / "model.safetensors").exists()
    assert (res / "v2" / "PROMOTED.json").exists() and (res / "v2" / "eps_table.csv").exists()
    assert Thresholds.load().version == "v1-test"  # v1 untouched


def test_promote_refuses_changed_artifacts(tmp_path, monkeypatch):
    art, _ = _fake_run3(tmp_path, monkeypatch)
    (art / "phase2" / "granite-ft" / "model.safetensors").write_bytes(b"other")
    with pytest.raises(phase2.Phase2Error):
        v2.promote()
