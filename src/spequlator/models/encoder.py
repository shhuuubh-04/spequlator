"""Transformer encoder signal (S2) with pinned revisions and graceful failure.

- UniXcoder: pretrained deep-learning signal (D-018). Apache-2.0, no remote code.
- MiniLM: base for the fine-tuned encoder (D-020); "minilm-ft" loads artifacts/minilm-ft.
- ``trust_remote_code`` is never enabled (D-018; Jina failed to load on transformers 5.x, F7).
- Any load/run failure raises EncoderUnavailable so analysis can continue (D-019).
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

import numpy as np

from spequlator.models.base import EncoderUnavailable
from spequlator.paths import artifacts_dir


@dataclass(frozen=True)
class EncoderSpec:
    key: str
    model_id: str  # Hugging Face id, or a local path for fine-tuned models
    revision: str | None
    max_seq_length: int

    @property
    def name(self) -> str:
        return f"{self.model_id}@{self.revision[:7]}" if self.revision else self.model_id


def _default_seq_len() -> int:
    """512 tokens on >= 8 cores, 256 otherwise (docs/10_HOUR_PLAN.md H2)."""
    return 512 if (os.cpu_count() or 1) >= 8 else 256


def spec_for(key: str) -> EncoderSpec:
    if key == "unixcoder":
        return EncoderSpec(
            "unixcoder",
            "microsoft/unixcoder-base",
            "5604afdc964f6c53782a6813140ade5216b99006",
            _default_seq_len(),
        )
    if key == "minilm":
        return EncoderSpec(
            "minilm",
            "sentence-transformers/all-MiniLM-L6-v2",
            "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
            256,  # model limit (R8)
        )
    if key == "minilm-ft":
        return EncoderSpec("minilm-ft", str(artifacts_dir() / "minilm-ft"), None, 128)
    raise ValueError(f"unknown encoder {key!r}; choose unixcoder, minilm or minilm-ft")


ENCODER_KEYS = ("unixcoder", "minilm", "minilm-ft")


class SentenceEncoder:
    """Lazy-loading sentence-transformers wrapper implementing the ``Encoder`` protocol."""

    def __init__(self, spec: EncoderSpec, *, device: str = "cpu", batch_size: int = 16):
        self.spec = spec
        self.name = spec.name
        self.device = device
        self.batch_size = batch_size
        self._model = None
        self._cache: dict[str, tuple[np.ndarray, bool]] = {}

    def load(self) -> SentenceEncoder:
        if self._model is not None:
            return self
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                self.spec.model_id,
                revision=self.spec.revision,
                device=self.device,
                trust_remote_code=False,
            )
            model.max_seq_length = self.spec.max_seq_length
        except Exception as exc:
            raise EncoderUnavailable(f"could not load {self.name}: {exc}") from exc
        self._model = model
        return self

    def _truncated(self, texts: list[str]) -> list[bool]:
        tok = self._model.tokenizer
        lengths = [
            len(ids) for ids in tok(texts, add_special_tokens=True, verbose=False)["input_ids"]
        ]
        return [n > self.spec.max_seq_length for n in lengths]

    def encode(self, texts: list[str]) -> tuple[np.ndarray, list[bool]]:
        """Unit-norm embeddings plus truncation flags; repeated texts are served from cache."""
        self.load()
        keys = [hashlib.sha1(t.encode("utf-8")).hexdigest() for t in texts]
        todo = list(
            dict.fromkeys(i for i, k in zip(texts, keys, strict=True) if k not in self._cache)
        )
        if todo:
            try:
                emb = self._model.encode(
                    todo,
                    batch_size=self.batch_size,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                trunc = self._truncated(todo)
            except Exception as exc:
                raise EncoderUnavailable(f"{self.name} failed while encoding: {exc}") from exc
            for text, vec, flag in zip(todo, emb, trunc, strict=True):
                self._cache[hashlib.sha1(text.encode("utf-8")).hexdigest()] = (vec, flag)
        vecs = np.stack([self._cache[k][0] for k in keys])
        return vecs, [self._cache[k][1] for k in keys]


_INSTANCES: dict[str, SentenceEncoder] = {}


def get_encoder(key: str = "unixcoder") -> SentenceEncoder:
    """Shared, lazily loaded encoder instance (one per key per process)."""
    if key not in _INSTANCES:
        _INSTANCES[key] = SentenceEncoder(spec_for(key))
    return _INSTANCES[key]
