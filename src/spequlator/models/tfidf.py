"""TF-IDF baseline signal (S1).

Change mode:   delta = cos(doc, new_code) - cos(doc, old_code)   (D-016; train AUC 0.724, F4)
Snapshot mode: cos(doc, code)                                     (weak; train AUC 0.565, F3)

The vectorizer is fitted on the CoDocBench TRAIN split only (D-010) and saved with metadata
so the split guard can check it. Build it with:  uv run python -m spequlator.models.tfidf
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer

from spequlator.nlp.preprocessing import split_identifiers
from spequlator.paths import artifacts_dir

ARTIFACT_NAME = "tfidf.joblib"
PARAMS = {"sublinear_tf": True, "min_df": 2}


class ArtifactMissing(FileNotFoundError):
    """A required generated artifact has not been built yet."""


class SplitLeakError(RuntimeError):
    """Something other than the train split was used for fitting."""


@dataclass
class TfidfModel:
    vectorizer: TfidfVectorizer
    meta: dict = field(default_factory=dict)

    def _vec(self, texts: list[str]):
        return self.vectorizer.transform(texts)  # rows are L2-normalised

    def cosine(self, a: str, b: str) -> float:
        m = self._vec([a, b])
        return float(m[0].multiply(m[1]).sum())

    def delta(self, doc: str, old_code: str, new_code: str) -> float:
        """Positive: doc fits the new code better. Negative: doc still fits the old code better."""
        m = self._vec([doc, new_code, old_code])
        return float(m[0].multiply(m[1]).sum() - m[0].multiply(m[2]).sum())

    def shared_terms(self, a: str, b: str, k: int = 5) -> list[str]:
        """Up to k terms present in both texts, highest combined TF-IDF weight first."""
        m = self._vec([a, b])
        both = m[0].multiply(m[1]).toarray().ravel()
        idx = [i for i in np.argsort(-both) if both[i] > 0][:k]
        vocab = self.vectorizer.get_feature_names_out()
        return [str(vocab[i]) for i in idx]


def fit(texts: Iterable[str], *, fit_split: str, min_df: int = PARAMS["min_df"]) -> TfidfModel:
    vec = TfidfVectorizer(
        tokenizer=split_identifiers,
        lowercase=False,
        token_pattern=None,
        sublinear_tf=PARAMS["sublinear_tf"],
        min_df=min_df,
    )
    texts = list(texts)
    vec.fit(texts)
    meta = {
        "fit_split": fit_split,
        "n_texts": len(texts),
        "vocab_size": len(vec.vocabulary_),
        "params": {**PARAMS, "min_df": min_df},
        "sklearn": sklearn.__version__,
    }
    return TfidfModel(vec, meta)


def fit_on_records(records) -> TfidfModel:
    """Fit on docstrings and code of both versions. Refuses anything but train records."""
    records = list(records)
    splits = {r.split for r in records}
    if splits != {"train"}:
        raise SplitLeakError(f"TF-IDF must be fitted on the train split only, got {sorted(splits)}")
    texts = [t for r in records for t in (r.old_doc, r.new_doc, r.old_code, r.new_code)]
    return fit(texts, fit_split="train")


def save(model: TfidfModel, path: Path | None = None) -> Path:
    path = path or artifacts_dir() / ARTIFACT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": model.vectorizer, "meta": model.meta}, path)
    return path


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path | None = None) -> TfidfModel:
    """Load the train-fitted vectorizer (cached per resolved path)."""
    return _load_cached((path or artifacts_dir() / ARTIFACT_NAME).resolve())


@lru_cache(maxsize=4)
def _load_cached(path: Path) -> TfidfModel:
    if not path.exists():
        raise ArtifactMissing(
            f"{path} not found. Build it with: uv run python -m spequlator.models.tfidf"
        )
    blob = joblib.load(path)
    meta = {**blob["meta"], "sha256": sha256_of(path)}
    if meta.get("fit_split") != "train":
        raise SplitLeakError(f"{path} was not fitted on the train split (D-010)")
    return TfidfModel(blob["vectorizer"], meta)


def main() -> int:
    from spequlator.datasets.codocbench import load_split, verify_checksums

    verify_checksums(names=("train.jsonl",))
    model = fit_on_records(load_split("train"))
    path = save(model)
    print(f"saved {path}  vocab={model.meta['vocab_size']}  texts={model.meta['n_texts']}")
    print(f"sha256 {sha256_of(path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
