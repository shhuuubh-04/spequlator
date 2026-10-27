"""Phase 2 (D-032): import the Kaggle outputs, freeze, and run ONE declared test evaluation.

  uv run python -m spequlator.evaluation.phase2 import ~/Downloads/phase2_outputs.zip
  uv run python -m spequlator.evaluation.phase2 freeze
  git add results/phase2 && git commit -m "phase 2: freeze" && git tag phase2-frozen
  uv run python -m spequlator.evaluation.phase2 run --confirm-frozen

v1.0's frozen artifacts and results are never modified. The new models are compared with
v1 on the same test split; each phase-2 run is a declared reuse of it (run 1 = second use).
Run 3 has two fine-tuned bi-encoders (MiniLM, Granite Small R2) and no cross-encoder; runs 1-2
also had a cross-encoder. Whatever the manifest lists is what gets frozen and scored.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from spequlator.datasets.codocbench import load_split
from spequlator.evaluation import stats
from spequlator.evaluation.frozen_eval import (
    BASELINE,
    _sha256,
    load_frame,
    results_dir,
    signal_table,
    verify_frozen,
)
from spequlator.evaluation.proxy_task import encoder_signals
from spequlator.paths import artifacts_dir
from spequlator.pipeline.report import Thresholds

V1_COMBINED = "v1 combined (TF-IDF + MiniLM-ft)"

# artifact folder -> (manifest key of its pick, column suffix, signal name, with-TF-IDF name)
ENCODERS = {
    "minilm-ft2": (
        "best_bi",
        "ft2",
        "MiniLM fine-tuned delta (phase 2)",
        "TF-IDF + MiniLM (phase 2)",
    ),
    "granite-ft": (
        "best_granite",
        "granite",
        "Granite fine-tuned delta (phase 2)",
        "TF-IDF + Granite (phase 2)",
    ),
}
# Extra paired comparisons reported when both signals exist (a minus b).
COMPARISONS = [
    ("Granite fine-tuned delta (phase 2)", "MiniLM fine-tuned delta (phase 2)"),
    ("TF-IDF + Granite (phase 2)", "TF-IDF + MiniLM (phase 2)"),
]
ORDINAL = {1: "second", 2: "third", 3: "fourth", 4: "fifth"}


def present(manifest: dict) -> list[str]:
    """Bi-encoder artifact folders this manifest contains."""
    return [k for k in ENCODERS if k in manifest["sha256"]]


def p2_dir() -> Path:
    return artifacts_dir() / "phase2"


def out_dir() -> Path:
    return results_dir() / "phase2"


class Phase2Error(RuntimeError):
    """Missing, tampered or unfrozen phase-2 artifacts."""


def verify_manifest(root: Path) -> dict:
    manifest = json.loads((root / "phase2_manifest.json").read_text(encoding="utf-8"))
    for name, sha in manifest["sha256"].items():
        target = root / name
        if not target.exists() or _sha256(target) != sha:
            raise Phase2Error(f"{name}: missing or SHA-256 mismatch (re-download the zip)")
    return manifest


def import_outputs(zip_path: Path) -> dict:
    """Unzip into artifacts/phase2 after checking every hash in the manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)
        manifest = verify_manifest(Path(tmp))
        target = p2_dir()
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(tmp, target)
    return manifest


def _scale(values: np.ndarray) -> float:
    return float(np.std(values)) or 1.0


def freeze() -> Path:
    """Pin phase-2 artifacts and the pre-registered combination settings (train data only)."""
    verify_frozen()  # v1 artifacts must be untouched
    manifest = verify_manifest(p2_dir())
    if manifest.get("smoke"):
        raise Phase2Error("these outputs come from a smoke run; run the full notebook")
    th = Thresholds.load()
    # Combination (pre-registered): each signal / its spread on cross-fitted train rows;
    # a cross-encoder logit is centred on its train mean first (Δ signals are already
    # centred at "no change"). TF-IDF keeps v1's frozen scale.
    combine = {"scale_tfidf": th.scale_tfidf}
    for key in present(manifest):
        col = ENCODERS[key][1]
        sig = pd.read_parquet(p2_dir() / f"signals_train_{key}.parquet")
        combine[f"scale_{col}"] = _scale(np.r_[sig["stale_enc_delta"], sig["updated_enc_delta"]])
    if "ce" in manifest["sha256"]:
        ce = pd.read_parquet(p2_dir() / "signals_train_ce.parquet")
        ce_all = np.r_[ce["stale_ce"], ce["updated_ce"]]
        combine["centre_ce"], combine["scale_ce"] = float(np.mean(ce_all)), _scale(ce_all)
    record = {
        "frozen_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "run": manifest.get("run", 1),
        "manifest_sha256": _sha256(p2_dir() / "phase2_manifest.json"),
        "artifacts_sha256": manifest["sha256"],
        **{k: manifest[k] for k in ("best_bi", "best_granite", "best_ce") if k in manifest},
        "combine": combine,
    }
    out = out_dir()
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(p2_dir() / "dev_results.json", out / "dev_results.json")
    path = out / "FROZEN.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def _test_signals() -> pd.DataFrame:
    """v1 test caches plus the phase-2 models (cached under artifacts/phase2)."""
    from spequlator.models.encoder import EncoderSpec, SentenceEncoder

    manifest = json.loads((p2_dir() / "phase2_manifest.json").read_text())
    df = load_frame("test")
    recs = {r.record_id: r for r in load_split("test")}
    ordered = [recs[i] for i in df["record_id"]]
    df = df.set_index("record_id")

    for key in present(manifest):
        best_key, col = ENCODERS[key][:2]
        cache = p2_dir() / f"signals_test_{key}.parquet"
        if not cache.exists():
            print(f"encoding the test split with {key} (a few minutes on CPU)...", file=sys.stderr)
            spec = EncoderSpec(key, str(p2_dir() / key), None, int(manifest[best_key]["max_len"]))
            encoder_signals(ordered, SentenceEncoder(spec, batch_size=32)).to_parquet(cache)
        sig = pd.read_parquet(cache).set_index("record_id")
        df[f"stale_{col}"], df[f"updated_{col}"] = sig["stale_enc_delta"], sig["updated_enc_delta"]

    if "ce" not in manifest["sha256"]:
        return df.reset_index()
    from spequlator.models.cross_encoder import CrossModel, change_text

    ce_cache = p2_dir() / "signals_test_ce.parquet"
    if not ce_cache.exists():
        model = CrossModel(p2_dir() / "ce")
        sides = [change_text(r.old_code, r.new_code, model.fmt) for r in ordered]
        stale = model.score_pairs([(r.old_doc, s) for r, s in zip(ordered, sides, strict=True)])
        upd = model.score_pairs([(r.new_doc, s) for r, s in zip(ordered, sides, strict=True)])
        pd.DataFrame(
            {"record_id": [r.record_id for r in ordered], "stale_ce": stale, "updated_ce": upd}
        ).to_parquet(ce_cache)
    ce = pd.read_parquet(ce_cache).set_index("record_id")
    df["stale_ce"], df["updated_ce"] = ce["stale_ce"], ce["updated_ce"]
    return df.reset_index()


def phase2_signals(df: pd.DataFrame, frozen: dict, th: Thresholds) -> dict:
    c = frozen["combine"]
    v1 = signal_table(df, th)
    pair = ("stale", "updated")

    def t(p):
        return df[f"{p}_tfidf_delta"].to_numpy() / c["scale_tfidf"]

    def enc(col, p):
        return df[f"{p}_{col}"].to_numpy() / c[f"scale_{col}"]

    def x(p):
        return (df[f"{p}_ce"].to_numpy() - c["centre_ce"]) / c["scale_ce"]

    v1_comb = next(k for k in v1 if k.startswith("Combined"))
    out = {
        BASELINE: v1[BASELINE],
        "MiniLM fine-tuned delta (v1)": v1["MiniLM fine-tuned delta"],
        V1_COMBINED: v1[v1_comb],
    }
    cols = [v for v in ENCODERS.values() if f"scale_{v[1]}" in c]
    for _, col, name, _ in cols:
        out[name] = tuple(df[f"{p}_{col}"].to_numpy() for p in pair)
    for _, col, _, combo in cols:
        out[combo] = tuple((t(p) + enc(col, p)) / 2 for p in pair)
    if "scale_ce" in c:
        out["Cross-encoder (phase 2)"] = tuple(df[f"{p}_ce"].to_numpy() for p in pair)
        out["TF-IDF + cross-encoder"] = tuple((t(p) + x(p)) / 2 for p in pair)
        if "scale_ft2" in c:
            out["TF-IDF + MiniLM (phase 2) + cross-encoder"] = tuple(
                (t(p) + enc("ft2", p) + x(p)) / 3 for p in pair
            )
    return out


def compute(df: pd.DataFrame, sig: dict, n_boot: int = stats.N_BOOT) -> dict:
    groups = df["project_key"].to_numpy()
    out: dict = {"n_records": len(df), "n_projects": int(len(np.unique(groups))), "signals": {}}
    for name, (s, u) in sig.items():
        row = {}
        for metric in ("pairwise_accuracy", "pooled_auc"):
            fn = getattr(stats, metric)
            p, lo, hi = stats.cluster_bootstrap(
                groups, lambda i, s=s, u=u, fn=fn: fn(s[i], u[i]), n_boot
            )
            row[metric] = {"value": p, "ci95": [lo, hi]}
            for ref in (BASELINE, V1_COMBINED):
                if name == ref:
                    continue
                rs, ru = sig[ref]
                d, dlo, dhi = stats.cluster_bootstrap(
                    groups,
                    lambda i, s=s, u=u, rs=rs, ru=ru, fn=fn: fn(s[i], u[i]) - fn(rs[i], ru[i]),
                    n_boot,
                )
                key = "tfidf" if ref == BASELINE else "v1"
                row[f"{metric}_minus_{key}"] = {"value": d, "ci95": [dlo, dhi]}
        out["signals"][name] = row
    for a, b in COMPARISONS:
        if a not in sig or b not in sig:
            continue
        (s, u), (rs, ru) = sig[a], sig[b]
        row = {}
        for metric in ("pairwise_accuracy", "pooled_auc"):
            fn = getattr(stats, metric)
            d, dlo, dhi = stats.cluster_bootstrap(
                groups,
                lambda i, s=s, u=u, rs=rs, ru=ru, fn=fn: fn(s[i], u[i]) - fn(rs[i], ru[i]),
                n_boot,
            )
            row[metric] = {"value": d, "ci95": [dlo, dhi]}
        out.setdefault("comparisons", {})[f"{a} minus {b}"] = row
    return out


def _cell(c: dict | None) -> str:
    if not c:
        return "-"
    lo, hi = c["ci95"]
    return f"{c['value']:.3f} [{lo:.3f}, {hi:.3f}]"


def _dev_auc(r: dict) -> str:
    sd = r.get("pooled_auc_sd")
    return f"{r['pooled_auc']:.3f}" + (f" ± {sd:.3f}" if sd is not None else "")


def to_markdown(m: dict, dev: list[dict]) -> str:
    run = m.get("frozen", {}).get("run", 1)
    use = ORDINAL.get(run, f"{run + 1}th")
    lines = [
        (
            f"Phase 2 run {run} test (declared {use} use of the test split): "
            f"{m['n_records']} records, {m['n_projects']} projects; "
            "95% project-cluster bootstrap CIs."
        ),
        "",
        "| Signal | Pairwise acc. | Pooled AUC | PA minus v1 combined | AUC minus TF-IDF |",
        "|---|---|---|---|---|",
    ]
    for name, r in m["signals"].items():
        lines.append(
            f"| {name} | {_cell(r['pairwise_accuracy'])} | {_cell(r['pooled_auc'])} | "
            f"{_cell(r.get('pairwise_accuracy_minus_v1'))} | {_cell(r.get('pooled_auc_minus_tfidf'))} |"
        )
    if m.get("comparisons"):
        lines += ["", "| Paired difference | Pairwise acc. | Pooled AUC |", "|---|---|---|"]
        lines += [
            f"| {k} | {_cell(r['pairwise_accuracy'])} | {_cell(r['pooled_auc'])} |"
            for k, r in m["comparisons"].items()
        ]
    lines += [
        "",
        (
            "Training-split selection (held-out dev projects, from the Kaggle notebook; "
            "± = spread over seeds; single-seed rows are in dev_results.json):"
        ),
        "",
        "| Run | Family | Dev pairwise acc. | Dev AUC |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {r['name']} | {r['family']} | {r['pairwise_accuracy']:.3f} | {_dev_auc(r)} |"
        for r in dev
        if not r["family"].endswith("-run")
    ]
    return "\n".join(lines) + "\n"


def run(confirm: bool) -> str:
    if not confirm:
        raise Phase2Error("the phase-2 test run happens once: pass --confirm-frozen")
    frozen_path = out_dir() / "FROZEN.json"
    if not frozen_path.exists():
        raise Phase2Error("not frozen: run `freeze`, commit and tag phase2-frozen first")
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    verify_frozen()
    if verify_manifest(p2_dir())["sha256"] != frozen["artifacts_sha256"]:
        raise Phase2Error("phase-2 artifacts changed after freezing")
    df = _test_signals()
    m = compute(df, phase2_signals(df, frozen, Thresholds.load()))
    m["frozen"] = frozen
    out = out_dir()
    (out / "metrics.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    md = to_markdown(m, json.loads((out / "dev_results.json").read_text()))
    (out / "tables.md").write_text(md, encoding="utf-8")
    return md


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import", help="unzip and hash-check the Kaggle outputs")
    imp.add_argument("zip", type=Path)
    sub.add_parser("freeze", help="pin phase-2 artifacts and combination settings")
    r = sub.add_parser("run", help="the one phase-2 test run")
    r.add_argument("--confirm-frozen", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.cmd == "import":
            m = import_outputs(a.zip)
            print(f"imported -> {p2_dir()}")
            print(f"best MiniLM: {m['best_bi']['name']}  (dev AUC {m['best_bi']['pooled_auc']})")
            for key, label in (("best_granite", "Granite"), ("best_ce", "cross-encoder")):
                if key in m:
                    print(f"best {label}: {m[key]['name']}  (dev AUC {m[key]['pooled_auc']})")
            if m.get("smoke"):
                print("warning: these are smoke-run outputs, not the real models")
        elif a.cmd == "freeze":
            print(f"frozen -> {freeze()}")
            print("next: commit results/phase2 and tag the freeze before `run`")
        else:
            print(run(a.confirm_frozen))
    except (Phase2Error, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
