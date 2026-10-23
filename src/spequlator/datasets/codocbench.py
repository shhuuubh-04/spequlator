"""Read-only adapter for CoDocBench.

Dataset: Pai, Devanbu, Ahmed. "CoDocBench: A Dataset for Code-Documentation Alignment
in Software Maintenance", MSR 2025. Licence CC BY 4.0 (Zenodo 10.5281/zenodo.14251623).
Pinned at github.com/kunpai/codocbench @ ee0256da15a07dcf265d5313fe51a269aa7268e0 (D-023).

Every record is a commit where code AND docstring changed together, so the pre-commit
docstring is a *simulated* stale case for the proxy task (D-015) -- not observed drift.
Raw files are never modified.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

from spequlator.schemas import AnalysisInput, Source

Split = Literal["train", "test"]
SPLITS: tuple[Split, ...] = ("train", "test")
PINNED_COMMIT = "ee0256da15a07dcf265d5313fe51a269aa7268e0"
EXPECTED_SHA256: dict[str, str] = {
    "codocbench.jsonl": "c0e8563af0baf9eab4fe1341fd0bf2099ec41030fd5c2224f1c3803a712c21d4",
    "train.jsonl": "9eef860afedcbf059a4f2e408cafbaa6c61ffbf4369e687a9b45ae80f7ac7c6d",
    "test.jsonl": "74e3da99744a43bdf1be77c57eb1069548911c30fd931a49bbc7d0d5050dcdea",
}
EXPECTED_COUNTS: dict[str, int] = {
    "codocbench.jsonl": 4573,
    "train.jsonl": 2300,
    "test.jsonl": 2273,
}

_REQUIRED_TOP = (
    "owner",
    "project",
    "file_path",
    "function",
    "version_data",
    "diff_code",
    "diff_docstring",
)
_REQUIRED_VERSION = ("docstring", "code", "commit_sha")


class DataIntegrityError(RuntimeError):
    """Dataset files are missing, altered or malformed."""


class RecordNotFound(KeyError):
    """No record with the requested ID exists in the searched split(s)."""


@dataclass(frozen=True)
class CodocRecord:
    record_id: str
    split: str
    owner: str
    project: str
    file_path: str
    function: str
    old_code: str
    new_code: str
    old_doc: str
    new_doc: str
    diff_code: str
    diff_docstring: str
    old_commit: str
    new_commit: str

    @property
    def project_key(self) -> str:
        """Use this (not ``project``) for grouping: different owners reuse repo names,
        e.g. TheAlgorithms/Python (train) vs Yonv1943/Python (test)."""
        return f"{self.owner}/{self.project}"


def data_dir() -> Path:
    """Dataset folder: $SPEQULATOR_DATA_DIR, else <repo>/data/raw/codocbench, else ./data/..."""
    env = os.environ.get("SPEQULATOR_DATA_DIR")
    if env:
        return Path(env)
    repo_dir = Path(__file__).resolve().parents[3] / "data" / "raw" / "codocbench"
    if repo_dir.exists():  # editable install (uv default)
        return repo_dir
    return Path.cwd() / "data" / "raw" / "codocbench"  # non-editable install: run from repo root


def make_record_id(raw: dict) -> str:
    """Stable 12-hex ID from the v1.1 audit key (owner, project, file, function, commits)."""
    v0, v1 = raw["version_data"][0], raw["version_data"][1]
    key = f"{raw['owner']}/{raw['project']}/{raw['file_path']}::{raw['function']}::{v0['commit_sha']}::{v1['commit_sha']}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def parse_record(raw: dict, split: str) -> CodocRecord:
    """Validate one raw JSON object and convert it to a CodocRecord."""
    missing = [k for k in _REQUIRED_TOP if k not in raw]
    if missing:
        raise ValueError(f"missing field(s): {', '.join(missing)}")
    versions = raw["version_data"]
    if not isinstance(versions, list) or len(versions) != 2:
        raise ValueError("version_data must be a list of exactly 2 versions")
    for i, v in enumerate(versions):
        miss = [k for k in _REQUIRED_VERSION if k not in v]
        if miss:
            raise ValueError(f"version_data[{i}] missing field(s): {', '.join(miss)}")
    v0, v1 = versions
    return CodocRecord(
        record_id=make_record_id(raw),
        split=split,
        owner=str(raw["owner"]),
        project=str(raw["project"]),
        file_path=str(raw["file_path"]),
        function=str(raw["function"]),
        old_code=str(v0["code"]),
        new_code=str(v1["code"]),
        old_doc=str(v0["docstring"]),
        new_doc=str(v1["docstring"]),
        diff_code=str(raw["diff_code"] or ""),
        diff_docstring=str(raw["diff_docstring"] or ""),
        old_commit=str(v0["commit_sha"]),
        new_commit=str(v1["commit_sha"]),
    )


def iter_jsonl(path: Path, split: str) -> Iterator[CodocRecord]:
    """Yield records from a JSONL file, failing loudly on the first bad line."""
    if not path.exists():
        raise DataIntegrityError(
            f"{path} not found. Download CoDocBench first (docs/START_HERE.md, step 3.3)."
        )
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                yield parse_record(raw, split)
            except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
                raise DataIntegrityError(f"{path.name} line {lineno}: {exc}") from exc


def load_split(split: Split, directory: Path | None = None) -> list[CodocRecord]:
    if split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}, got {split!r}")
    return list(iter_jsonl((directory or data_dir()) / f"{split}.jsonl", split))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_checksums(
    directory: Path | None = None, names: tuple[str, ...] | None = None
) -> dict[str, str]:
    """Check SHA-256 of the pinned files. Returns {name: sha}; raises on any mismatch."""
    directory = directory or data_dir()
    results: dict[str, str] = {}
    for name in names or tuple(EXPECTED_SHA256):
        path = directory / name
        if not path.exists():
            raise DataIntegrityError(f"{path} not found (docs/START_HERE.md, step 3.3).")
        actual = sha256_file(path)
        if actual != EXPECTED_SHA256[name]:
            raise DataIntegrityError(
                f"{name}: SHA-256 {actual} does not match pinned {EXPECTED_SHA256[name]} "
                f"(expected commit {PINNED_COMMIT})."
            )
        results[name] = actual
    return results


@lru_cache(maxsize=4)
def _index(split: str, directory: str) -> dict[str, CodocRecord]:
    return {r.record_id: r for r in load_split(split, Path(directory))}  # type: ignore[arg-type]


def get_record(
    record_id: str, split: Split | None = None, directory: Path | None = None
) -> CodocRecord:
    """Look up one record by ID (searching test then train when split is None)."""
    d = str(directory or data_dir())
    for s in (split,) if split else ("test", "train"):
        rec = _index(s, d).get(record_id)
        if rec is not None:
            return rec
    raise RecordNotFound(record_id)


def to_input(record: CodocRecord, doc_version: Literal["old", "new"]) -> AnalysisInput:
    """Change-mode input: the chosen docstring checked against old -> new code (D-015/D-016)."""
    if doc_version not in ("old", "new"):
        raise ValueError("doc_version must be 'old' or 'new'")
    return AnalysisInput(
        documentation=record.old_doc if doc_version == "old" else record.new_doc,
        old_code=record.old_code,
        new_code=record.new_code,
        source=Source(
            kind="codocbench",
            record_id=record.record_id,
            project=record.project,
            function=record.function,
            doc_version=doc_version,
        ),
    )
