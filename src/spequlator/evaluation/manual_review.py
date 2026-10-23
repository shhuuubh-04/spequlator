"""H8: manual review of generated reports (RQ4) and the curated demo-example list.

Sampling (after the frozen test run, D-021):
  - 30 TEST records, stratified 10/10/10 by the live rule's finding on the STALE pair
    (seed 2026); for each record, reports for both the old and the new docstring = 60 reports.
  - results/manual_review_packets.md : every report in full, for reading.
  - results/manual_review.csv        : one row per report; a PERSON fills the rubric columns.
Rubric (0-2 each): evidence_fidelity, specificity, uncertainty_calibration; plus
needs_update (yes/no/unsure). These are project annotations, not dataset ground truth.

Demo examples: seeded random TEST records filtered only for readability (short code and
docstring), never by the tool's output, plus the observe_lr train example used in tests.
"""

from __future__ import annotations

import json
import random

import pandas as pd

from spequlator.datasets.codocbench import CodocRecord, get_record, load_split, to_input
from spequlator.evaluation.frozen_eval import load_frame, results_dir
from spequlator.nlp.rules import R1Result, R2Result
from spequlator.pipeline.report import Thresholds, decide

SEED = 2026
RUBRIC = ("evidence_fidelity", "specificity", "uncertainty_calibration")
FINDINGS = ("potential_drift", "no_obvious_drift", "inconclusive")
DEMO_ANCHOR = "8e8e00c86a25"  # observe_lr (train): renamed parameters, used throughout the docs


def stale_findings(df: pd.DataFrame, th: Thresholds) -> pd.Series:
    """The live rule's finding for each record's stale pair, from cached test signals."""
    col = f"stale_{th.encoder or 'minilm-ft'}_delta"
    enc = df[col].to_numpy() if col in df.columns else [None] * len(df)
    findings = [
        decide(
            "change",
            r1=R1Result(applicable=True, fired=bool(r1)),
            r2=R2Result(applicable=True, fired=bool(r2)),
            tfidf=float(t),
            encoder=None if e is None else float(e),
            doc_words=int(w),
            th=th,
        ).finding
        for r1, r2, t, e, w in zip(
            df["stale_r1"],
            df["stale_r2"],
            df["stale_tfidf_delta"],
            enc,
            df["stale_doc_words"],
            strict=True,
        )
    ]
    return pd.Series(findings, index=df.index)


def stratified_pick(record_ids: pd.Series, findings: pd.Series, n: int, seed: int) -> list[str]:
    """n records split evenly across the 3 findings; short strata are topped up from the rest."""
    rng = random.Random(seed)
    per = n // len(FINDINGS)
    picked: list[str] = []
    for f in FINDINGS:
        pool = sorted(record_ids[findings == f])
        picked += rng.sample(pool, min(per, len(pool)))
    rest = sorted(set(record_ids) - set(picked))
    picked += rng.sample(rest, n - len(picked))
    return picked


def _context(rec: CodocRecord, max_lines: int = 25) -> str:
    diff = [ln for ln in rec.diff_code.splitlines() if ln.startswith(("- ", "+ "))][:max_lines]
    return "\n".join(diff)


def build_review(n: int = 30, seed: int = SEED) -> tuple[str, str]:
    from spequlator.models.encoder import get_encoder
    from spequlator.pipeline.analyze import analyze

    th = Thresholds.load()
    df = load_frame("test")
    ids = stratified_pick(df["record_id"], stale_findings(df, th), n, seed)
    encoder = get_encoder(th.encoder) if th.encoder else None

    rows, packets = (
        [],
        ["# Manual review packets", "", f"{n} test records x 2 docstrings, seed {seed}.", ""],
    )
    for i, rid in enumerate(ids, 1):
        rec = get_record(rid, "test")
        packets += [
            f"## {i}. {rec.project_key} :: {rec.function}  (`{rid}`)",
            "",
            "Code diff:",
            "```diff",
            _context(rec),
            "```",
            "",
        ]
        for version in ("old", "new"):
            rep = analyze(to_input(rec, version), encoder=encoder, thresholds=th)
            doc = rec.old_doc if version == "old" else rec.new_doc
            packets += [
                f"### Docstring {'before' if version == 'old' else 'after'} commit -> **{rep.finding}**",
                "```text", doc.strip(), "```",
                f"- Summary: {rep.summary}",
                *[f"- Evidence [{e.kind}]: {e.text}" + (f" | lines: {' / '.join(e.lines)}" if e.lines else "") for e in rep.evidence],
                f"- Signals: TF-IDF {rep.signals.tfidf.value:+.3f}"
                + (f", encoder {rep.signals.encoder.value:+.3f}" if rep.signals.encoder else ", encoder n/a"),
                *[f"- Uncertainty: {u}" for u in rep.uncertainties],
                f"- Next step: {rep.next_step}",
                "",
            ]  # fmt: skip
            rows.append(
                {
                    "n": i,
                    "record_id": rid,
                    "project": rec.project_key,
                    "function": rec.function,
                    "doc_version": version,
                    "finding": rep.finding,
                    "summary": rep.summary,
                    **dict.fromkeys(RUBRIC, ""),
                    "needs_update": "",
                    "notes": "",
                }
            )
    out = results_dir()
    out.mkdir(parents=True, exist_ok=True)
    csv_path, md_path = out / "manual_review.csv", out / "manual_review_packets.md"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    md_path.write_text("\n".join(packets) + "\n", encoding="utf-8")
    return str(csv_path), str(md_path)


def summarize_scores(df: pd.DataFrame) -> dict:
    """Means of the filled rubric columns overall, by docstring version and by finding."""
    scored = df.dropna(subset=list(RUBRIC))
    if scored.empty:
        raise ValueError(
            "no scored rows: fill evidence_fidelity, specificity, uncertainty_calibration (0-2)"
        )
    for k in RUBRIC:
        bad = ~scored[k].isin([0, 1, 2])
        if bad.any():
            raise ValueError(f"{k} must be 0, 1 or 2 (row n={scored.loc[bad, 'n'].iloc[0]})")

    def means(g: pd.DataFrame) -> dict[str, float]:
        return {k: round(float(g[k].mean()), 2) for k in RUBRIC}

    out = {
        "n_reports_scored": len(scored),
        "overall": means(scored),
        "by_doc_version": {v: means(g) for v, g in scored.groupby("doc_version")},
        "by_finding": {f: means(g) for f, g in scored.groupby("finding")},
    }
    nu = scored["needs_update"].astype(str).str.strip().str.lower()
    if (nu != "").any() and (nu != "nan").any():
        for v in ("old", "new"):
            sel = nu[scored["doc_version"] == v]
            out[f"needs_update_yes_rate_{v}"] = round(float((sel == "yes").mean()), 3)
    return out


def summarize(csv_name: str = "manual_review.csv") -> dict:
    path = results_dir() / csv_name
    summary = summarize_scores(pd.read_csv(path))
    (results_dir() / "manual_review_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def pick_demo(records: list[CodocRecord], n: int, seed: int) -> list[str]:
    """Readable examples only (short code/doc), chosen at random, never by outcome."""
    readable = sorted(
        (
            r
            for r in records
            if len(r.old_code) + len(r.new_code) <= 1500 and 5 <= len(r.new_doc.split()) <= 120
        ),
        key=lambda r: r.record_id,
    )
    return [r.record_id for r in random.Random(seed).sample(readable, min(n, len(readable)))]


def write_demo_examples(n: int = 11, seed: int = SEED) -> str:
    ids = [DEMO_ANCHOR, *pick_demo(load_split("test"), n, seed)]
    path = results_dir() / "demo_examples.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ids, indent=2) + "\n", encoding="utf-8")
    return str(path)
