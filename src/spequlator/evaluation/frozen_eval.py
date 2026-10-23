"""H4: freeze the train-tuned settings, then run the ONE-TIME test evaluation (D-010, D-021).

  uv run spequlator eval freeze                     # pin hashes -> results/frozen/FROZEN.json
  git add results && git commit && git tag frozen-eval
  uv run spequlator eval run --split test --confirm-frozen

`eval run` refuses if any pinned artifact changed after freezing. Test signals are cached,
so re-running only re-prints the same numbers (no tuning happens on test).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd

from spequlator.datasets.codocbench import PINNED_COMMIT, verify_checksums
from spequlator.evaluation import stats
from spequlator.evaluation.calibrate import outcomes
from spequlator.evaluation.proxy_task import PAIRS, FrozenSplitError, build, cache_path
from spequlator.paths import artifacts_dir, repo_root
from spequlator.pipeline.report import Thresholds

PINNED = ("tfidf.joblib", "thresholds.json", "finetune_gate.json", "minilm-ft")
ENCODERS = ("minilm", "minilm-ft")
STRATA = ((0.0, 0.7), (0.7, 0.9), (0.9, 0.95), (0.95, 1.0001))
BASELINE = "TF-IDF delta"


class FrozenMismatch(RuntimeError):
    """Frozen settings are missing or an artifact changed after freezing."""


def results_dir() -> Path:
    env = os.environ.get("SPEQULATOR_RESULTS_DIR")
    return Path(env) if env else repo_root() / "results"


def _sha256(path: Path) -> str:
    """SHA-256 of a file, or of every file in a directory (sorted, path-tagged)."""
    h = hashlib.sha256()
    files = sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
    for f in files:
        if path.is_dir():
            h.update(str(f.relative_to(path)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root(),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return out.stdout.strip() or None


def freeze() -> Path:
    art, frozen_dir = artifacts_dir(), results_dir() / "frozen"
    missing = [name for name in PINNED if not (art / name).exists()]
    if missing:
        raise FileNotFoundError(f"cannot freeze, missing in {art}: {', '.join(missing)}")
    frozen_dir.mkdir(parents=True, exist_ok=True)
    for name in ("thresholds.json", "finetune_gate.json"):
        shutil.copy(art / name, frozen_dir / name)
    record = {
        "frozen_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "artifacts_sha256": {name: _sha256(art / name) for name in PINNED},
    }
    path = frozen_dir / "FROZEN.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path


def verify_frozen() -> dict:
    path = results_dir() / "frozen" / "FROZEN.json"
    if not path.exists():
        raise FrozenMismatch("not frozen yet: run `spequlator eval freeze` and commit first")
    record = json.loads(path.read_text(encoding="utf-8"))
    for name, sha in record["artifacts_sha256"].items():
        target = artifacts_dir() / name
        if not target.exists() or _sha256(target) != sha:
            raise FrozenMismatch(
                f"{name} changed or missing since freezing; re-freeze is a deviation"
            )
    return record


def load_frame(split: str, encoders: tuple[str, ...] = ENCODERS) -> pd.DataFrame:
    df = pd.read_parquet(cache_path(split, "base"))
    for key in encoders:
        enc = pd.read_parquet(cache_path(split, key)).drop(columns=["encoder"])
        enc = enc.rename(columns={c: c.replace("_enc_", f"_{key}_") for c in enc.columns})
        df = df.merge(enc, on="record_id", validate="one_to_one")
    return df


def signal_table(df: pd.DataFrame, th: Thresholds) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """(stale, updated) arrays per signal; higher = fits the new code better."""
    live = th.encoder or "minilm-ft"

    def cols(name: str) -> tuple[np.ndarray, np.ndarray]:
        return df[f"stale_{name}"].to_numpy(), df[f"updated_{name}"].to_numpy()

    def comb(pair: str) -> np.ndarray:
        t = df[f"{pair}_tfidf_delta"].to_numpy() / th.scale_tfidf
        e = df[f"{pair}_{live}_delta"].to_numpy() / th.scale_encoder
        return (t + e) / 2

    return {
        "TF-IDF snapshot": cols("tfidf_abs"),
        BASELINE: cols("tfidf_delta"),
        "MiniLM delta": cols("minilm_delta"),
        "MiniLM fine-tuned delta": cols("minilm-ft_delta"),
        f"Combined (TF-IDF + {live})": (comb("stale"), comb("updated")),
    }


def compute_metrics(df: pd.DataFrame, th: Thresholds, n_boot: int = stats.N_BOOT) -> dict:
    groups = df["project_key"].to_numpy()
    sig = signal_table(df, th)
    out: dict = {"n_records": len(df), "n_projects": len(np.unique(groups)), "signals": {}}

    for name, (s, u) in sig.items():
        row = {}
        for metric in ("pairwise_accuracy", "pooled_auc"):
            fn = getattr(stats, metric)
            point, lo, hi = stats.cluster_bootstrap(
                groups, lambda i, s=s, u=u, fn=fn: fn(s[i], u[i]), n_boot
            )
            row[metric] = {"value": point, "ci95": [lo, hi]}
            if name != BASELINE:
                bs, bu = sig[BASELINE]
                d, dlo, dhi = stats.cluster_bootstrap(
                    groups,
                    lambda i, s=s, u=u, fn=fn, bs=bs, bu=bu: fn(s[i], u[i]) - fn(bs[i], bu[i]),
                    n_boot,
                )
                row[f"{metric}_minus_baseline"] = {"value": d, "ci95": [dlo, dhi]}
        row["project_macro_pairwise_accuracy"] = stats.project_macro(
            groups, lambda i, s=s, u=u: stats.pairwise_accuracy(s[i], u[i])
        )
        out["signals"][name] = row

    out["rules"] = {
        r: {
            "stale_rate": float(df[f"stale_{r}"].mean()),
            "updated_rate": float(df[f"updated_{r}"].mean()),
            "lift": float(df[f"stale_{r}"].mean() / max(df[f"updated_{r}"].mean(), 1e-9)),
        }
        for r in ("r1", "r2")
    }

    live = th.encoder or "minilm-ft"
    renamed = df.rename(columns={f"{p}_{live}_delta": f"{p}_enc_delta" for p in PAIRS})
    out["decision_rule"] = {"thresholds": th.version, **outcomes(renamed, th, use_encoder=True)}

    strata = []
    for lo, hi in STRATA:
        m = ((df["doc_edit_ratio"] >= lo) & (df["doc_edit_ratio"] < hi)).to_numpy()
        entry = {"doc_edit_ratio": [lo, min(hi, 1.0)], "n": int(m.sum())}
        for name in (BASELINE, "MiniLM fine-tuned delta", f"Combined (TF-IDF + {live})"):
            s, u = sig[name]
            entry[name] = stats.pairwise_accuracy(s[m], u[m]) if m.any() else None
        strata.append(entry)
    out["strata_pairwise_accuracy"] = strata
    out["encoder_truncation_rate"] = {
        k: float(df[f"stale_{k}_truncated"].mean())
        for k in ENCODERS
        if f"stale_{k}_truncated" in df
    }
    return out


def _fmt(cell: dict) -> str:
    lo, hi = cell["ci95"]
    return f"{cell['value']:.3f} [{lo:.3f}, {hi:.3f}]"


def to_markdown(m: dict) -> str:
    lines = [
        (
            f"Test split: {m['n_records']} records, {m['n_projects']} projects. Proxy task (D-015); "
            "95% project-cluster bootstrap CIs."
        ),
        "",
        "| Signal | Pairwise acc. | Pooled AUC | AUC minus TF-IDF delta |",
        "|---|---|---|---|",
    ]
    for name, row in m["signals"].items():
        diff = row.get("pooled_auc_minus_baseline")
        lines.append(
            f"| {name} | {_fmt(row['pairwise_accuracy'])} | {_fmt(row['pooled_auc'])} | "
            f"{_fmt(diff) if diff else '-'} |"
        )
    d = m["decision_rule"]
    lines += [
        "",
        (
            f"Decision rule ({d['thresholds']}): coverage {d['coverage']:.3f}, "
            f"balanced accuracy on decided {d['balanced_accuracy_decided']:.3f}"
        ),
        "",
        "| Pair | potential_drift | no_obvious_drift | inconclusive |",
        "|---|---|---|---|",
    ]
    for p in PAIRS:
        lines.append(
            f"| {p} | {d[f'{p}_potential_drift']:.3f} | {d[f'{p}_no_obvious_drift']:.3f} | "
            f"{d[f'{p}_inconclusive']:.3f} |"
        )
    lines += ["", "| Rule | Fires on stale | Fires on updated | Lift |", "|---|---|---|---|"]
    for r, v in m["rules"].items():
        lines.append(
            f"| {r.upper()} | {v['stale_rate']:.3f} | {v['updated_rate']:.3f} | {v['lift']:.2f} |"
        )
    names = [k for k in m["strata_pairwise_accuracy"][0] if k not in ("doc_edit_ratio", "n")]
    lines += [
        "",
        "| Doc edit ratio | n | " + " | ".join(names) + " |",
        "|---" * (len(names) + 2) + "|",
    ]
    for s in m["strata_pairwise_accuracy"]:
        vals = " | ".join("-" if s[k] is None else f"{s[k]:.3f}" for k in names)
        lines.append(
            f"| {s['doc_edit_ratio'][0]:.2f}-{s['doc_edit_ratio'][1]:.2f} | {s['n']} | {vals} |"
        )
    return "\n".join(lines) + "\n"


def write_figures(m: dict, out: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out.mkdir(parents=True, exist_ok=True)
    names = list(m["signals"])
    vals = [m["signals"][n]["pooled_auc"]["value"] for n in names]
    err = np.array([[v - m["signals"][n]["pooled_auc"]["ci95"][0],
                     m["signals"][n]["pooled_auc"]["ci95"][1] - v] for n, v in zip(names, vals, strict=True)]).T  # fmt: skip
    fig, ax = plt.subplots(figsize=(7, 3.2))
    ax.barh(names, vals, xerr=err, color="#4C72B0", capsize=3)
    ax.axvline(0.5, color="grey", linestyle="--", linewidth=1)
    ax.set_xlim(0.4, 0.85)
    ax.set_xlabel("Pooled AUC on test (95% project-cluster CI); 0.5 = chance")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out / "auc_ci.png", dpi=150)
    plt.close(fig)


def run_info(frozen: dict) -> dict:
    pkgs = ("torch", "transformers", "sentence-transformers", "scikit-learn", "numpy", "pandas")
    versions = {}
    for p in pkgs:
        try:
            versions[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            versions[p] = None
    return {
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "packages": versions,
        "codocbench_commit": PINNED_COMMIT,
        "dataset_sha256": verify_checksums(),
        "frozen": frozen,
        "seeds": {"feasibility_and_finetune": 13, "bootstrap": stats.SEED},
        "n_boot": stats.N_BOOT,
    }


def run_test(confirm: bool) -> str:
    if not confirm:
        raise FrozenSplitError("the test split is opened once: pass --confirm-frozen")
    frozen = verify_frozen()
    for part in (None, *ENCODERS):
        if not cache_path("test", part or "base").exists():
            build("test", part, allow_test=True)
    th = Thresholds.load()
    m = compute_metrics(load_frame("test"), th)
    out = results_dir()
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    md = to_markdown(m)
    (out / "tables.md").write_text(md, encoding="utf-8")
    (out / "RUN_INFO.json").write_text(
        json.dumps(run_info(frozen), indent=2) + "\n", encoding="utf-8"
    )
    write_figures(m, out / "figures")
    return md
