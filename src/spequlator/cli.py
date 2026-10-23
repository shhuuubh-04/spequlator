"""Spequlator command-line interface (docs/CLI_SPEC.md). A thin adapter over the shared core.

Exit codes: 0 analysis done (also when the encoder is unavailable) | 1 unexpected error |
2 invalid input | 3 data or artifact error.
"""

from __future__ import annotations

import sys
import warnings
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from spequlator.datasets import codocbench as cdb
from spequlator.models.tfidf import ArtifactMissing, SplitLeakError
from spequlator.schemas import AnalysisInput, Report

warnings.filterwarnings("ignore", category=SyntaxWarning)  # invalid escapes in dataset code

app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Code-documentation drift analysis."
)
data_app = typer.Typer(no_args_is_help=True, help="Dataset utilities.")
eval_app = typer.Typer(no_args_is_help=True, help="Evaluation (train-only unless frozen).")
app.add_typer(data_app, name="data")
app.add_typer(eval_app, name="eval")


class Fmt(str, Enum):
    text = "text"
    json = "json"


class DocVersion(str, Enum):
    old = "old"
    new = "new"


class EncKey(str, Enum):
    unixcoder = "unixcoder"
    minilm = "minilm"
    minilm_ft = "minilm-ft"


def _fail(code: int, message: str) -> None:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code)


def _read(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        _fail(2, f"cannot read {path}: {exc.strerror}")
    return None


def _build_input(
    code_file, docs_file, docs_text, old_code_file, new_code_file, example_id, doc_version
):
    if example_id:
        if any([code_file, docs_file, docs_text, old_code_file, new_code_file]):
            _fail(2, "--example-id cannot be combined with file or text inputs")
        try:
            rec = cdb.get_record(example_id)
        except cdb.RecordNotFound:
            _fail(2, f"unknown example id {example_id!r}")
        return cdb.to_input(rec, doc_version.value)
    if docs_file and docs_text:
        _fail(2, "give --docs-file or --docs-text, not both")
    docs = _read(docs_file) if docs_file else docs_text
    if docs is None:
        _fail(2, "documentation is required (--docs-file or --docs-text)")
    try:
        return AnalysisInput(
            documentation=docs,
            code=_read(code_file),
            old_code=_read(old_code_file),
            new_code=_read(new_code_file),
        )
    except ValidationError as exc:
        _fail(2, "; ".join(e["msg"].removeprefix("Value error, ") for e in exc.errors()))
    return None


def render_text(rep: Report) -> str:
    label = rep.finding.replace("_", " ").upper()
    lines = [
        f"Finding:   {label}  (heuristic{' - review recommended' if rep.review_recommended else ''})",
        f"Summary:   {rep.summary}",
    ]
    if rep.evidence:
        lines.append("Evidence:")
        for e in rep.evidence:
            lines.append(f"  [{e.kind}] {e.text}")
            lines += [f"      {ln}" for ln in e.lines]
    lines.append("Signals (similarity/relatedness, not probabilities):")
    t = rep.signals.tfidf
    if t:
        lines.append(f"  TF-IDF {t.kind:<8} {t.value:+.3f}")
    enc = rep.signals.encoder
    lines.append(
        f"  Encoder {enc.kind:<7} {enc.value:+.3f}   ({enc.model})" if enc else "  Encoder  n/a"
    )
    lines.append("Uncertainty:")
    lines += [f"  - {u}" for u in rep.uncertainties]
    lines.append(f"Next step: {rep.next_step}")
    return "\n".join(lines)


@app.command()
def analyze(
    code_file: Annotated[Path | None, typer.Option(help="Snapshot mode: current code.")] = None,
    docs_file: Annotated[Path | None, typer.Option(help="Documentation file.")] = None,
    docs_text: Annotated[str | None, typer.Option(help="Documentation as text.")] = None,
    old_code_file: Annotated[Path | None, typer.Option(help="Change mode: code before.")] = None,
    new_code_file: Annotated[Path | None, typer.Option(help="Change mode: code after.")] = None,
    example_id: Annotated[
        str | None, typer.Option(help="CoDocBench record id (change mode).")
    ] = None,
    doc_version: Annotated[
        DocVersion, typer.Option(help="Which docstring to test.")
    ] = DocVersion.old,
    fmt: Annotated[Fmt, typer.Option("--format", help="Output format.")] = Fmt.text,
    no_encoder: Annotated[bool, typer.Option("--no-encoder", help="TF-IDF + rules only.")] = False,
    encoder: Annotated[EncKey | None, typer.Option(help="Override the calibrated encoder.")] = None,
    debug: Annotated[bool, typer.Option(help="Show tracebacks.")] = False,
) -> None:
    """Analyse documentation against code (snapshot), a code change, or a dataset example."""
    from spequlator.models.encoder import get_encoder
    from spequlator.pipeline.analyze import analyze as run
    from spequlator.pipeline.report import Thresholds

    inp = _build_input(
        code_file, docs_file, docs_text, old_code_file, new_code_file, example_id, doc_version
    )
    try:
        th = Thresholds.load()
        key = None if no_encoder else (encoder.value if encoder else th.encoder)
        rep = run(inp, encoder=get_encoder(key) if key else None, thresholds=th)
    except (ArtifactMissing, SplitLeakError, cdb.DataIntegrityError) as exc:
        _fail(3, str(exc))
    except Exception as exc:
        if debug:
            raise
        _fail(1, f"unexpected failure: {exc} (re-run with --debug)")
    typer.echo(rep.model_dump_json(indent=2) if fmt is Fmt.json else render_text(rep))


@data_app.command("verify")
def data_verify() -> None:
    """Check SHA-256 of the pinned CoDocBench files."""
    try:
        for name, sha in cdb.verify_checksums().items():
            typer.echo(f"ok  {name}  {sha}")
    except cdb.DataIntegrityError as exc:
        _fail(3, str(exc))


@data_app.command("examples")
def data_examples(
    split: Annotated[str, typer.Option()] = "train",
    limit: Annotated[int, typer.Option()] = 20,
) -> None:
    """List record ids (use the test split only after the frozen H4 run)."""
    if split not in cdb.SPLITS:
        _fail(2, f"split must be one of {cdb.SPLITS}")
    try:
        for rec in cdb.load_split(split)[:limit]:  # type: ignore[arg-type]
            typer.echo(f"{rec.record_id}  {rec.project_key:<40} {rec.function}")
    except cdb.DataIntegrityError as exc:
        _fail(3, str(exc))


@eval_app.command("cache")
def eval_cache(
    split: Annotated[str, typer.Option()] = "train",
    encoder: Annotated[EncKey | None, typer.Option()] = None,
    allow_test: Annotated[bool, typer.Option("--allow-test")] = False,
) -> None:
    """Cache proxy-task signals (base, or one encoder) for a split."""
    from spequlator.evaluation.proxy_task import FrozenSplitError, build

    try:
        build(split, encoder.value if encoder else None, allow_test=allow_test)
    except FrozenSplitError as exc:
        _fail(2, str(exc))
    except (ArtifactMissing, cdb.DataIntegrityError) as exc:
        _fail(3, str(exc))


@eval_app.command("calibrate")
def eval_calibrate(
    encoder: Annotated[EncKey | None, typer.Option(help="Encoder to calibrate with.")] = None,
) -> None:
    """Learn epsilon dead-bands on TRAIN signals and write artifacts/thresholds.json."""
    from spequlator.evaluation.calibrate import MIN_COVERAGE, calibrate, load_signals

    key = encoder.value if encoder else None
    try:
        df = load_signals("train", key)
    except FileNotFoundError as exc:
        _fail(
            3,
            f"{exc}. Run: uv run spequlator eval cache --split train"
            + (f" --encoder {key}" if key else ""),
        )
    th, table = calibrate(df, key)
    path = th.save()
    cols = ["eps", "coverage", "balanced_accuracy_decided",
            "stale_potential_drift", "updated_potential_drift"]  # fmt: skip
    typer.echo(table[cols].to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    row = table[table["eps"] == th.eps].iloc[0]
    typer.echo(
        f"\nchosen eps={th.eps} (scale_tfidf={th.scale_tfidf:.4f}, "
        f"scale_encoder={th.scale_encoder:.4f}) coverage={row['coverage']:.3f} "
        f"balanced_accuracy={row['balanced_accuracy_decided']:.3f} -> {path}"
    )
    if row["coverage"] < MIN_COVERAGE:
        typer.echo(f"warning: no eps reached coverage {MIN_COVERAGE:.0%}; chose the most decisive.")


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(main())
