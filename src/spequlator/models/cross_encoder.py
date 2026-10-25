"""Phase-2 cross-encoder (D-032): reads the docstring and the code change together.

Trained on Kaggle (notebooks/phase2_train.ipynb) on the CoDocBench train split to output a
logit: higher = the docstring fits the change, lower = it looks stale. The logit is a model
score, not a probability. ``word_importance`` explains one score by occlusion: drop each
docstring word, re-score, and record how much the score moved.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from spequlator.models.base import EncoderUnavailable
from spequlator.nlp.preprocessing import code_diff
from spequlator.paths import artifacts_dir

_WORDISH = re.compile(r"\S+")


def change_text(old_code: str, new_code: str, fmt: str) -> str:
    """The code side of the pair. Must match the notebook's ``change_text`` exactly."""
    if fmt == "full":
        return f"OLD CODE:\n{old_code}\nNEW CODE:\n{new_code}"
    d = code_diff(old_code, new_code)
    lines = [f"- {x}" for x in d.removed] + [f"+ {x}" for x in d.added]
    return "CHANGED LINES:\n" + "\n".join(lines) + f"\nNEW CODE:\n{new_code}"


class PairScorer(Protocol):
    name: str
    fmt: str

    def score_pairs(self, pairs: list[tuple[str, str]]) -> np.ndarray: ...


@dataclass
class WordWeight:
    start: int
    end: int
    weight: float  # base score minus score without this word: > 0 helped "fits", < 0 "stale"


def score(model: PairScorer, doc: str, old_code: str, new_code: str) -> float:
    return float(model.score_pairs([(doc, change_text(old_code, new_code, model.fmt))])[0])


def word_importance(
    model: PairScorer, doc: str, old_code: str, new_code: str, max_words: int = 80
) -> tuple[float, list[WordWeight], int]:
    """Occlusion: one extra pass per word (first ``max_words`` words). Returns (score, weights, n)."""
    side = change_text(old_code, new_code, model.fmt)
    words = list(_WORDISH.finditer(doc))[:max_words]
    variants = [doc] + [doc[: m.start()] + doc[m.end() :] for m in words]
    scores = model.score_pairs([(v, side) for v in variants])
    base = float(scores[0])
    weights = [
        WordWeight(m.start(), m.end(), base - float(s))
        for m, s in zip(words, scores[1:], strict=True)
    ]
    return base, weights, len(words)


class CrossModel:
    """Lazy wrapper around the fine-tuned Hugging Face sequence-classification model."""

    def __init__(self, path: Path | None = None, *, device: str = "cpu", batch_size: int = 16):
        self.path = path or artifacts_dir() / "phase2" / "ce"
        meta_file = self.path / "spequlator_ce.json"
        if not meta_file.exists():
            raise EncoderUnavailable(f"no phase-2 cross-encoder at {self.path}")
        self.meta = json.loads(meta_file.read_text(encoding="utf-8"))
        self.fmt = self.meta.get("format", "diff")
        self.max_len = int(self.meta.get("max_len", 512))
        base = self.meta.get("base", "").split("/")[-1]
        self.name = f"cross-encoder ({base}, fine-tuned on CoDocBench train, D-032)"
        self.device, self.batch_size = device, batch_size
        self._tok = self._model = None

    def load(self) -> CrossModel:
        if self._model is not None:
            return self
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            self._tok = AutoTokenizer.from_pretrained(self.path)
            self._model = AutoModelForSequenceClassification.from_pretrained(self.path)
            self._model.to(self.device).eval()
            self._torch = torch
        except Exception as exc:  # degrade like the encoder (D-019)
            raise EncoderUnavailable(f"could not load {self.path}: {exc}") from exc
        return self

    def score_pairs(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        self.load()
        out = []
        with self._torch.no_grad():
            for i in range(0, len(pairs), self.batch_size):
                chunk = pairs[i : i + self.batch_size]
                enc = self._tok(
                    [a for a, _ in chunk],
                    [b for _, b in chunk],
                    truncation="longest_first",
                    max_length=self.max_len,
                    padding=True,
                    return_tensors="pt",
                ).to(self.device)
                out.append(self._model(**enc).logits.squeeze(-1).float().cpu().numpy())
        return np.concatenate(out) if out else np.zeros(0)


_INSTANCE: dict[str, CrossModel] = {}


def get_cross_model() -> CrossModel:
    """Shared instance; raises EncoderUnavailable when phase 2 has not been imported."""
    if "ce" not in _INSTANCE:
        _INSTANCE["ce"] = CrossModel()
    return _INSTANCE["ce"].load()
