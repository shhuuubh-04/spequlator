"""FastAPI adapter over the shared core (FR-9, D-011, D-022). No analysis logic lives here.

Run:  uv run spequlator serve        (binds 127.0.0.1:8000; the Vite dev server proxies /api)
Errors always have the shape {"error": {"code", "message", "field"}} and never a traceback.
"""

from __future__ import annotations

import json
import threading
import warnings
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from spequlator.datasets import codocbench as cdb
from spequlator.models import tfidf as tfidf_mod
from spequlator.models.base import EncoderUnavailable
from spequlator.pipeline.report import Thresholds
from spequlator.pipeline.trace import Explained
from spequlator.schemas import MAX_CHARS, AnalysisInput, Report

warnings.filterwarnings("ignore", category=SyntaxWarning)  # invalid escapes in dataset code

FIELDS = ("documentation", "code", "old_code", "new_code")

# ---- encoder state: warmed in the background so the server starts instantly ----------
_state: dict = {"encoder": None, "encoder_status": "disabled", "encoder_name": None}


def _warm_encoder(key: str) -> None:
    from spequlator.models.encoder import get_encoder

    try:
        enc = get_encoder(key)
        enc.encode(["warm-up"])
        _state.update(encoder=enc, encoder_status="ready", encoder_name=enc.name)
    except EncoderUnavailable:
        _state.update(encoder=None, encoder_status="unavailable")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    key = Thresholds.load().encoder
    if key:
        _state.update(encoder_status="loading")
        threading.Thread(target=_warm_encoder, args=(key,), daemon=True).start()
    yield


app = FastAPI(title="Spequlator API", version="1.2", lifespan=lifespan)


def _error(status: int, code: str, message: str, field: str | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message, "field": field}}
    )


def _validation_response(errors: list[dict]) -> JSONResponse:
    first = errors[0] if errors else {"msg": "invalid input", "loc": ()}
    msg = str(first.get("msg", "invalid input")).removeprefix("Value error, ")
    loc = [str(x) for x in first.get("loc", ()) if str(x) not in ("body", "query", "path")]
    field = loc[-1] if loc else next((f for f in FIELDS if msg.startswith(f"{f}:")), None)
    if field is None and "code" in msg:
        field = "code"
    return _error(422, "invalid_input", msg, field)


@app.exception_handler(RequestValidationError)
async def _on_request_validation(_req: Request, exc: RequestValidationError) -> JSONResponse:
    return _validation_response(list(exc.errors()))


@app.exception_handler(ValidationError)
async def _on_validation(_req: Request, exc: ValidationError) -> JSONResponse:
    return _validation_response(exc.errors())


@app.exception_handler(tfidf_mod.ArtifactMissing)
async def _on_artifact(_req: Request, exc: Exception) -> JSONResponse:
    return _error(503, "artifact_missing", str(exc))


@app.exception_handler(cdb.DataIntegrityError)
async def _on_data(_req: Request, exc: Exception) -> JSONResponse:
    return _error(503, "data_unavailable", str(exc))


@app.exception_handler(Exception)
async def _on_unexpected(_req: Request, exc: Exception) -> JSONResponse:
    return _error(500, "internal_error", f"unexpected failure ({type(exc).__name__})")


# ---- request models ---------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documentation: str = Field(max_length=MAX_CHARS)
    code: str | None = Field(default=None, max_length=MAX_CHARS)
    old_code: str | None = Field(default=None, max_length=MAX_CHARS)
    new_code: str | None = Field(default=None, max_length=MAX_CHARS)
    use_encoder: bool = True


class ExampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    doc_version: Literal["old", "new"] = "old"
    use_encoder: bool = True


def _run(inp: AnalysisInput, use_encoder: bool) -> Report:
    from spequlator.pipeline.analyze import analyze

    encoder = _state["encoder"] if use_encoder else None
    report = analyze(inp, encoder=encoder, thresholds=Thresholds.load())
    if use_encoder and encoder is None and _state["encoder_status"] == "loading":
        report.uncertainties.append("The deep-learning model is still loading; try again shortly.")
    return report


def _explain(inp: AnalysisInput, use_encoder: bool) -> Explained:
    """Report plus the read-only step-by-step trace for the UI (D-030)."""
    from spequlator.pipeline.trace import explain

    encoder = _state["encoder"] if use_encoder else None
    ex = explain(inp, encoder=encoder, thresholds=Thresholds.load())
    if use_encoder and encoder is None and _state["encoder_status"] == "loading":
        ex.report.uncertainties.append(
            "The deep-learning model is still loading; try again shortly."
        )
    return ex


def _diff_lines(diff: str) -> list[str]:
    return [ln for ln in diff.splitlines() if not ln.startswith("? ")]


# ---- routes -------------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    try:
        tfidf_ok = bool(tfidf_mod.load())
    except (tfidf_mod.ArtifactMissing, tfidf_mod.SplitLeakError):
        tfidf_ok = False
    th = Thresholds.load()
    return {
        "status": "ok" if tfidf_ok else "degraded",
        "tfidf": tfidf_ok,
        "encoder": _state["encoder_status"],
        "encoder_name": _state["encoder_name"],
        "thresholds": th.version,
    }


@app.get("/api/examples")
def examples(
    split: Literal["train", "test"] = "train",
    limit: int = Query(50, ge=1, le=500),
    q: str = "",
) -> list[dict]:
    """Curated demo examples (results/demo_examples.json) when present, else a split listing."""
    from spequlator.evaluation.frozen_eval import results_dir

    curated = results_dir() / "demo_examples.json"
    if curated.exists():
        ids = json.loads(curated.read_text(encoding="utf-8"))
        records = [cdb.get_record(i) for i in ids]
    else:
        records = cdb.load_split(split)
    needle = q.lower().strip()
    out = []
    for r in records:
        if needle and needle not in f"{r.project_key} {r.function}".lower():
            continue
        out.append({"record_id": r.record_id, "project": r.project_key, "function": r.function})
        if len(out) >= limit:
            break
    return out


@app.get("/api/examples/{record_id}")
def example(record_id: str):
    try:
        r = cdb.get_record(record_id)
    except cdb.RecordNotFound:
        return _error(404, "not_found", f"unknown example id {record_id!r}", "record_id")
    return {
        "record_id": r.record_id,
        "project": r.project_key,
        "function": r.function,
        "file_path": r.file_path,
        "old_code": r.old_code,
        "new_code": r.new_code,
        "old_doc": r.old_doc,
        "new_doc": r.new_doc,
        "diff_code": _diff_lines(r.diff_code),
        "diff_docstring": _diff_lines(r.diff_docstring),
    }


@app.post("/api/analyze", response_model=Report)
def analyze_text(req: AnalyzeRequest) -> Report:
    inp = AnalysisInput(**req.model_dump(include=set(FIELDS)))
    return _run(inp, req.use_encoder)


@app.post("/api/analyze/example", response_model=Report)
def analyze_example(req: ExampleRequest):
    try:
        r = cdb.get_record(req.record_id)
    except cdb.RecordNotFound:
        return _error(404, "not_found", f"unknown example id {req.record_id!r}", "record_id")
    return _run(cdb.to_input(r, req.doc_version), req.use_encoder)


@app.post("/api/explain", response_model=Explained)
def explain_text(req: AnalyzeRequest) -> Explained:
    inp = AnalysisInput(**req.model_dump(include=set(FIELDS)))
    return _explain(inp, req.use_encoder)


@app.post("/api/explain/example", response_model=Explained)
def explain_example(req: ExampleRequest):
    try:
        r = cdb.get_record(req.record_id)
    except cdb.RecordNotFound:
        return _error(404, "not_found", f"unknown example id {req.record_id!r}", "record_id")
    return _explain(cdb.to_input(r, req.doc_version), req.use_encoder)
