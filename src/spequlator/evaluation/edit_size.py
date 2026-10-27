"""Phase 2 run 3: the frozen test results broken down by how much the docstring changed.

Descriptive only. It re-scores the test signals already cached by `phase2 run` (no model is
trained, tuned or re-selected), groups the records by docstring edit size, and writes
results/phase2_run3/by_edit_size.{md,json}.

  uv run python -m spequlator.evaluation.edit_size

Edit size = tokens (words and punctuation marks) inserted, deleted or replaced between the
old and the new docstring. "Cosmetic" = the two differ only in letter case, punctuation or
spacing, i.e. the words are identical.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np

from spequlator.datasets.codocbench import load_split
from spequlator.evaluation import phase2, stats
from spequlator.evaluation.frozen_eval import BASELINE, results_dir, verify_frozen
from spequlator.pipeline.report import Thresholds

_TOKEN = re.compile(r"\w+|[^\w\s]")
BUCKETS = [("0-1", 0, 1), ("2-5", 2, 5), ("6-15", 6, 15), ("16+", 16, None)]
SIGNALS = [
    BASELINE,
    phase2.V1_COMBINED,
    "MiniLM fine-tuned delta (phase 2)",
    "Granite fine-tuned delta (phase 2)",
    "TF-IDF + Granite (phase 2)",
]
SHORT = {
    BASELINE: "TF-IDF",
    phase2.V1_COMBINED: "v1 system",
    "MiniLM fine-tuned delta (phase 2)": "MiniLM",
    "Granite fine-tuned delta (phase 2)": "Granite",
    "TF-IDF + Granite (phase 2)": "TF-IDF + Granite",
}


def edit_size(old: str, new: str) -> int:
    a, b = _TOKEN.findall(old), _TOKEN.findall(new)
    ops = difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()
    return sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in ops if op != "equal")


def cosmetic(old: str, new: str) -> bool:
    """True when only case, punctuation or spacing differs (the words are identical)."""

    def words(s: str) -> list[str]:
        return [t.lower() for t in _TOKEN.findall(s) if t[0].isalnum() or t[0] == "_"]

    return words(old) == words(new)


def masks(sizes: np.ndarray, cos: np.ndarray) -> list[tuple[str, np.ndarray]]:
    out = [("All records", np.ones(len(sizes), bool))]
    for label, lo, hi in BUCKETS:
        out.append((f"{label} tokens changed", (sizes >= lo) & (sizes <= (hi or sizes.max()))))
    out.append(("Cosmetic only (case, punctuation, spacing)", cos))
    return out


def breakdown(sig: dict, sizes, cos, groups, n_boot: int = stats.N_BOOT) -> list[dict]:
    rows = []
    for label, m in masks(np.asarray(sizes), np.asarray(cos, bool)):
        g = np.asarray(groups)[m]
        row = {
            "group": label,
            "n": int(m.sum()),
            "n_projects": int(len(np.unique(g))),
            "signals": {},
        }
        for name in SIGNALS:
            if name not in sig:
                continue
            s, u = sig[name][0][m], sig[name][1][m]
            row["signals"][name] = {}
            for metric in ("pairwise_accuracy", "pooled_auc"):
                fn = getattr(stats, metric)
                p, lo, hi = stats.cluster_bootstrap(
                    g, lambda i, s=s, u=u, fn=fn: fn(s[i], u[i]), n_boot
                )
                row["signals"][name][metric] = {"value": p, "ci95": [lo, hi]}
        rows.append(row)
    return rows


def to_markdown(rows: list[dict]) -> str:
    names = [n for n in SIGNALS if n in rows[0]["signals"]]
    head = "| Docstring change | Records | " + " | ".join(SHORT[n] for n in names) + " |"
    out = [
        (
            "Phase 2 run 3 test results by docstring edit size (descriptive breakdown of the "
            "frozen run; nothing was retrained or re-selected). 95% project-cluster bootstrap CIs."
        ),
    ]
    for metric, title in (
        ("pairwise_accuracy", "Pairwise accuracy: picks the right version of the same docstring"),
        ("pooled_auc", "Pooled AUC: ranks one docstring against docstrings of other functions"),
    ):
        out += ["", f"**{title}**", "", head, "|---|---|" + "---|" * len(names)]
        for r in rows:
            cells = []
            for n in names:
                c = r["signals"][n][metric]
                cells.append(f"{c['value']:.3f} [{c['ci95'][0]:.3f}, {c['ci95'][1]:.3f}]")
            share = r["n"] / rows[0]["n"]
            out.append(f"| {r['group']} | {r['n']} ({share:.0%}) | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--run-dir", type=Path, default=None, help="default: results/phase2_run3")
    a = p.parse_args(argv)
    run_dir = a.run_dir or results_dir() / "phase2_run3"
    try:
        frozen = json.loads((run_dir / "FROZEN.json").read_text(encoding="utf-8"))
        verify_frozen()
        if phase2.verify_manifest(phase2.p2_dir())["sha256"] != frozen["artifacts_sha256"]:
            raise phase2.Phase2Error(f"artifacts/phase2 does not hold the run frozen in {run_dir}")
    except (phase2.Phase2Error, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    df = phase2._test_signals()  # served from the caches written by `phase2 run`
    sig = phase2.phase2_signals(df, frozen, Thresholds.load())
    recs = {r.record_id: r for r in load_split("test")}
    ordered = [recs[i] for i in df["record_id"]]
    sizes = np.array([edit_size(r.old_doc, r.new_doc) for r in ordered])
    cos = np.array([cosmetic(r.old_doc, r.new_doc) for r in ordered])
    rows = breakdown(sig, sizes, cos, df["project_key"].to_numpy())
    (run_dir / "by_edit_size.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    md = to_markdown(rows)
    (run_dir / "by_edit_size.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
