"""v2 system (D-034): TF-IDF + Granite, promoted from the frozen phase-2 run 3.

  uv run python -m spequlator.evaluation.v2 promote

Copies run 3's fine-tuned Granite model to artifacts/granite-ft and writes
artifacts/thresholds_v2.json:

- the TF-IDF and Granite scales exactly as frozen for run 3, so the app's combined score is
  the "TF-IDF + Granite (phase 2)" signal tested there (pooled AUC 0.734);
- a dead-band eps chosen with the D-028 rule on the TRAIN split only: the cross-fitted
  dev-project scores from the run-3 notebook (503 records). The test split is not read.

The app and CLI analyse with v2 once artifacts/thresholds_v2.json exists; set
SPEQULATOR_SYSTEM=v1 to run the frozen v1 system. v1 artifacts and results are unchanged.
A copy of the settings is written to results/v2/ so it can be committed.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from spequlator.evaluation import phase2
from spequlator.evaluation.calibrate import choose_eps
from spequlator.evaluation.frozen_eval import _sha256, results_dir
from spequlator.evaluation.proxy_task import PAIRS, cache_path
from spequlator.paths import artifacts_dir
from spequlator.pipeline.report import THRESHOLDS_V2_NAME, Thresholds

RUN_DIR = "phase2_run3"
MODEL = "granite-ft"


def calibration_frame() -> pd.DataFrame:
    """Train rule/TF-IDF signals joined with run 3's cross-fitted Granite scores."""
    base = pd.read_parquet(cache_path("train", "base"))
    sig = pd.read_parquet(phase2.p2_dir() / f"signals_train_{MODEL}.parquet")
    keep = ["record_id", *[f"{p}_enc_delta" for p in PAIRS]]
    return base.merge(sig[keep], on="record_id", validate="one_to_one")


def promote(run_dir: Path | None = None) -> dict:
    run_dir = run_dir or results_dir() / RUN_DIR
    frozen = json.loads((run_dir / "FROZEN.json").read_text(encoding="utf-8"))
    if frozen.get("run") != 3 or "scale_granite" not in frozen["combine"]:
        raise phase2.Phase2Error(f"{run_dir} is not the frozen phase-2 run 3 with Granite")
    manifest = phase2.verify_manifest(phase2.p2_dir())
    if manifest["sha256"] != frozen["artifacts_sha256"]:
        raise phase2.Phase2Error("artifacts/phase2 does not hold the frozen run 3")

    dest = artifacts_dir() / MODEL
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(phase2.p2_dir() / MODEL, dest)
    if _sha256(dest) != manifest["sha256"][MODEL]:
        raise phase2.Phase2Error(f"the copy in {dest} does not match the frozen hash")

    df = calibration_frame()
    v1 = Thresholds.load()
    c = frozen["combine"]
    base = replace(
        v1, encoder=MODEL, scale_tfidf=c["scale_tfidf"], scale_encoder=c["scale_granite"]
    )
    chosen, table = choose_eps(df, base)
    chosen = replace(chosen, version=f"v2-tfidf-granite-train-{date.today().isoformat()}")
    chosen.save(artifacts_dir() / THRESHOLDS_V2_NAME)

    out = results_dir() / "v2"
    out.mkdir(parents=True, exist_ok=True)
    chosen.save(out / THRESHOLDS_V2_NAME)
    table.to_csv(out / "eps_table.csv", index=False)
    pick = table[table["eps"] == chosen.eps].iloc[0]
    record = {
        "promoted_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "decision": "D-034",
        "source": f"results/{run_dir.name}/FROZEN.json",
        "source_manifest_sha256": frozen["manifest_sha256"],
        "model": MODEL,
        "model_sha256": manifest["sha256"][MODEL],
        "model_pick": frozen.get("best_granite", {}).get("name"),
        "calibration_records": len(df),
        "calibration_data": "cross-fitted dev-project scores from the run-3 notebook (train only)",
        "train_coverage": float(pick["coverage"]),
        "train_balanced_accuracy_decided": float(pick["balanced_accuracy_decided"]),
        "v1_thresholds_version": v1.version,
        "thresholds": asdict(chosen),
    }
    (out / "PROMOTED.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("promote", help="copy the run-3 Granite model and write thresholds_v2.json")
    p.parse_args(argv)
    try:
        r = promote()
    except (phase2.Phase2Error, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    th = r["thresholds"]
    print(f"model    -> {artifacts_dir() / MODEL}  ({r['model_pick']})")
    print(f"settings -> {artifacts_dir() / THRESHOLDS_V2_NAME}  ({th['version']})")
    print(
        f"scales: TF-IDF {th['scale_tfidf']:.4f}, Granite {th['scale_encoder']:.4f}; "
        f"eps {th['eps']:.4f} on {r['calibration_records']} train records "
        f"(coverage {r['train_coverage']:.1%}, balanced accuracy {r['train_balanced_accuracy_decided']:.3f})"
    )
    print("record   -> results/v2/ (commit it); restart the server to load Granite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
