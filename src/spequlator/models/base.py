"""Interfaces shared by the pipeline and the encoder implementations (H2)."""

from __future__ import annotations

from typing import Protocol

import numpy as np


class EncoderUnavailable(RuntimeError):
    """The transformer encoder could not be loaded or run (D-019: degrade, don't fail)."""


class Encoder(Protocol):
    """A sentence encoder returning L2-normalised embeddings."""

    name: str  # e.g. "microsoft/unixcoder-base@5604afd"

    def encode(self, texts: list[str]) -> tuple[np.ndarray, list[bool]]:
        """Return (embeddings with unit-norm rows, per-text truncation flags)."""
        ...
