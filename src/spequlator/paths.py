"""Repository-relative locations for generated artifacts."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Repo root for an editable install (uv default); falls back to the working directory."""
    root = Path(__file__).resolve().parents[2]  # src/spequlator/paths.py -> repo
    return root if (root / "pyproject.toml").exists() else Path.cwd()


def artifacts_dir() -> Path:
    """Generated, git-ignored artifacts: $SPEQULATOR_ARTIFACTS_DIR or <repo>/artifacts."""
    env = os.environ.get("SPEQULATOR_ARTIFACTS_DIR")
    return Path(env) if env else repo_root() / "artifacts"
