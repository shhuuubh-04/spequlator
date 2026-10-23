"""D-020: contrastive fine-tuning of MiniLM on CoDocBench TRAIN triplets, with a go/no-go gate.

Triplet = (anchor: new code, positive: new docstring, hard negative: old docstring),
MultipleNegativesRankingLoss, 1 epoch, batch 8, lr 2e-5, max 128 tokens, seed 13 (F9).

Steps (all inside the train split; the test split is never read):
  1. Split train by owner/project: 20 dev projects held out (D-026), the rest fit.
  2. Fine-tune a dev model on the fit projects -> artifacts/minilm-ft-dev.
  3. Gate: dev delta-AUC of the fine-tuned model >= pretrained MiniLM (same 128 tokens).
  4. Write the dev model's signals for the dev projects to
     artifacts/signals_train_minilm-ft.parquet (cross-fitted: never in-sample), so
     `spequlator eval calibrate --encoder minilm-ft` tunes epsilon on unseen projects.
  5. GO: fine-tune the final model on ALL train projects -> artifacts/minilm-ft.
Result summary: artifacts/finetune_gate.json.  Run:  uv run python -m spequlator.evaluation.finetune
"""

from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

from spequlator.datasets.codocbench import CodocRecord, load_split
from spequlator.evaluation.proxy_task import cache_path, encoder_signals
from spequlator.models.base import Encoder
from spequlator.models.encoder import EncoderSpec, SentenceEncoder, spec_for
from spequlator.paths import artifacts_dir


@dataclass(frozen=True)
class FinetuneConfig:
    base_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    base_revision: str = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    epochs: int = 1
    batch_size: int = 8  # batch 16 ran out of memory at 8 GB RAM (F9)
    learning_rate: float = 2e-5
    warmup_ratio: float = 0.1
    max_seq_length: int = 128
    seed: int = 13
    n_dev_projects: int = 20


def project_split(
    records: list[CodocRecord], n_dev: int, seed: int
) -> tuple[list[CodocRecord], list[CodocRecord]]:
    """Deterministic owner/project-disjoint split of TRAIN records into (fit, dev)."""
    if {r.split for r in records} != {"train"}:
        raise ValueError("fine-tuning uses the train split only (D-010)")
    projects = sorted({r.project_key for r in records})
    dev_keys = set(random.Random(seed).sample(projects, n_dev))
    fit = [r for r in records if r.project_key not in dev_keys]
    dev = [r for r in records if r.project_key in dev_keys]
    return fit, dev


def delta_auc(encoder: Encoder, records: list[CodocRecord]) -> float:
    """Pooled ROC-AUC of the encoder delta signal: stale (old doc) is the positive class."""
    df = encoder_signals(records, encoder)
    y = np.r_[np.ones(len(df)), np.zeros(len(df))]
    return float(roc_auc_score(y, np.r_[-df["stale_enc_delta"], -df["updated_enc_delta"]]))


def train(records: list[CodocRecord], out_dir: Path, cfg: FinetuneConfig) -> Path:
    """Fine-tune MiniLM on (new code, new doc, old doc) triplets and save it with metadata."""
    from datasets import Dataset
    from sentence_transformers import (
        SentenceTransformer,
        SentenceTransformerTrainer,
        SentenceTransformerTrainingArguments,
        losses,
    )
    from sentence_transformers.training_args import BatchSamplers

    model = SentenceTransformer(cfg.base_model, revision=cfg.base_revision, device="cpu")
    model.max_seq_length = cfg.max_seq_length
    data = Dataset.from_dict(
        {
            "anchor": [r.new_code for r in records],
            "positive": [r.new_doc for r in records],
            "negative": [r.old_doc for r in records],
        }
    )
    args = SentenceTransformerTrainingArguments(
        output_dir=str(out_dir.parent / f".{out_dir.name}-trainer"),
        num_train_epochs=cfg.epochs,
        per_device_train_batch_size=cfg.batch_size,
        learning_rate=cfg.learning_rate,
        warmup_steps=cfg.warmup_ratio,  # a float < 1 is a ratio in transformers 5.x
        seed=cfg.seed,
        batch_sampler=BatchSamplers.NO_DUPLICATES,
        save_strategy="no",
        logging_steps=50,
        report_to="none",
        use_cpu=True,
    )
    SentenceTransformerTrainer(
        model=model,
        args=args,
        train_dataset=data,
        loss=losses.MultipleNegativesRankingLoss(model),
    ).train()
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save(str(out_dir))
    meta = {"fit_split": "train", "n_triplets": len(records), "config": asdict(cfg)}
    (out_dir / "spequlator_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return out_dir


def gate_passes(finetuned_auc: float, pretrained_auc: float) -> bool:
    """D-020 go/no-go: keep the fine-tuned encoder only if it is at least as good on dev."""
    return finetuned_auc >= pretrained_auc


def run(cfg: FinetuneConfig | None = None) -> dict:
    cfg = cfg or FinetuneConfig()
    art = artifacts_dir()
    records = load_split("train")
    fit, dev = project_split(records, cfg.n_dev_projects, cfg.seed)
    print(f"fit records={len(fit)}  dev records={len(dev)} ({cfg.n_dev_projects} projects)")

    t0 = time.perf_counter()
    dev_dir = train(fit, art / "minilm-ft-dev", cfg)
    dev_train_s = time.perf_counter() - t0

    pretrained = SentenceEncoder(
        EncoderSpec("minilm", cfg.base_model, cfg.base_revision, cfg.max_seq_length)
    )
    finetuned = SentenceEncoder(
        EncoderSpec("minilm-ft-dev", str(dev_dir), None, cfg.max_seq_length)
    )
    auc_pre, auc_ft = delta_auc(pretrained, dev), delta_auc(finetuned, dev)
    go = gate_passes(auc_ft, auc_pre)
    print(
        f"dev delta-AUC  pretrained={auc_pre:.3f}  fine-tuned={auc_ft:.3f}  -> {'GO' if go else 'NO-GO'}"
    )

    # Cross-fitted calibration signals: dev projects scored by a model that never saw them.
    xfit = encoder_signals(dev, finetuned)
    xfit["encoder"] = spec_for("minilm-ft").name
    xfit.to_parquet(cache_path("train", "minilm-ft"), index=False)

    result = {
        "decision": "GO" if go else "NO-GO",
        "dev_projects": cfg.n_dev_projects,
        "dev_records": len(dev),
        "dev_auc_pretrained": round(auc_pre, 4),
        "dev_auc_finetuned": round(auc_ft, 4),
        "dev_train_seconds": round(dev_train_s),
        "calibration_rows": "dev projects only, cross-fitted",
        "config": asdict(cfg),
    }
    if go:
        t1 = time.perf_counter()
        train(records, art / "minilm-ft", cfg)
        result["final_train_seconds"] = round(time.perf_counter() - t1)
        print(f"final model -> {art / 'minilm-ft'}")
    (art / "finetune_gate.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
