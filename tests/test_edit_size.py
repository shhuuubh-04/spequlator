import numpy as np

from spequlator.evaluation import edit_size as es
from spequlator.evaluation.frozen_eval import BASELINE


def test_edit_size_counts_changed_tokens():
    assert es.edit_size("Send an email.", "Send an email.") == 0
    assert es.edit_size("Send an email.", "Send a message.") == 2
    assert es.edit_size("Retry 3 times", "Retry 3 times, then fail") == 3


def test_cosmetic_ignores_case_punctuation_spacing_but_not_identifiers():
    assert es.cosmetic("Return the  value", "return the value.")
    assert not es.cosmetic("Uses email_to.", "Uses email_from.")


def test_breakdown_groups_and_markdown():
    rng = np.random.default_rng(0)
    n = 80
    sizes = np.array([0, 3, 9, 20] * 20)
    cos = sizes == 0
    groups = np.array([f"p{i % 8}" for i in range(n)])
    sig = {BASELINE: (rng.normal(-1, 1, n), rng.normal(1, 1, n))}
    rows = es.breakdown(sig, sizes, cos, groups, n_boot=20)
    assert [r["n"] for r in rows] == [80, 20, 20, 20, 20, 20]
    md = es.to_markdown(rows)
    assert "| 16+ tokens changed | 20 (25%) |" in md and "TF-IDF" in md
