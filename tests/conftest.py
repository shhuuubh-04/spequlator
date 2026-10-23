from pathlib import Path

import pytest

from spequlator.datasets.codocbench import iter_jsonl
from spequlator.models import tfidf as tfidf_mod

FIXTURES = Path(__file__).parent / "fixtures"


def read(*parts: str) -> str:
    return (FIXTURES.joinpath(*parts)).read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def mini_records():
    return list(iter_jsonl(FIXTURES / "codocbench_mini.jsonl", "train"))


@pytest.fixture(scope="session")
def small_tfidf(mini_records):
    """Tiny train-only vectorizer: fixture records + synthetic fixtures (min_df=1)."""
    texts = [t for r in mini_records for t in (r.old_doc, r.new_doc, r.old_code, r.new_code)]
    texts += [read("stale_param", f) for f in ("old.py", "new.py", "doc.txt")]
    texts += [read("aligned", f) for f in ("code.py", "doc.txt")]
    return tfidf_mod.fit(texts, fit_split="train", min_df=1)
