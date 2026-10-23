"""Build tests/fixtures/codocbench_mini.jsonl from 6 hand-picked TRAIN records.

Run once after downloading CoDocBench, then commit the fixture:
    uv run python scripts/make_fixture.py

Records are copied verbatim (CC BY 4.0, Pai et al., MSR 2025). Only train.jsonl is read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from spequlator.datasets.codocbench import data_dir, make_record_id, verify_checksums

FIXTURE_IDS = {
    "8e8e00c86a25": "chainer observe_lr: params renamed; old doc names removed params (R1), Google Args",
    "b0759e4b9cdb": "datasets xPath.exists: old doc names a removed param (R1), Google Args",
    "21bbad6b09d7": "mycroft-core AudioService._restore_volume: old doc names a removed param (R1)",
    "dc8baf45e2f6": "pytorch-image-models get_pretrained_cfg_value: near-trivial doc edit (ratio >= 0.95)",
    "46d6cf9be0f2": "wttr.in translate: large doc rewrite (ratio < 0.6)",
    "fc412c0a787b": "mmdetection l1_loss: Google-style Args",
}

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "codocbench_mini.jsonl"


def main() -> int:
    verify_checksums(names=("train.jsonl",))
    wanted: dict[str, str] = {}
    with (data_dir() / "train.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            rid = make_record_id(json.loads(line))
            if rid in FIXTURE_IDS:
                wanted[rid] = line.rstrip("\n")
    missing = set(FIXTURE_IDS) - set(wanted)
    if missing:
        print(f"missing records: {sorted(missing)}", file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(wanted[i] for i in FIXTURE_IDS) + "\n", encoding="utf-8")
    print(f"wrote {len(wanted)} records to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
