import numpy as np
import pytest

from spequlator.evaluation.finetune import delta_auc, gate_passes, project_split


def test_project_split_is_disjoint_and_deterministic(mini_records):
    fit, dev = project_split(mini_records, n_dev=2, seed=13)
    assert len(fit) + len(dev) == len(mini_records)
    assert not {r.project_key for r in fit} & {r.project_key for r in dev}
    assert len({r.project_key for r in dev}) == 2
    _, dev2 = project_split(mini_records, n_dev=2, seed=13)
    assert [r.record_id for r in dev] == [r.record_id for r in dev2]


def test_project_split_refuses_test_records(mini_records):
    leaked = [mini_records[0].__class__(**{**mini_records[0].__dict__, "split": "test"})]
    with pytest.raises(ValueError):
        project_split(mini_records + leaked, n_dev=1, seed=13)


def test_gate():
    assert gate_passes(0.65, 0.62)
    assert gate_passes(0.62, 0.62)
    assert not gate_passes(0.60, 0.62)


class PerfectEncoder:
    """Embeds each docstring next to the code it was written for -> stale always worse."""

    name = "perfect@0"

    def __init__(self, records):
        self.vec = {}
        for i, r in enumerate(records):
            new, old = np.zeros(64), np.zeros(64)
            new[2 * i], old[2 * i + 1] = 1.0, 1.0
            self.vec.update({r.new_code: new, r.new_doc: new, r.old_code: old, r.old_doc: old})

    def encode(self, texts):
        return np.stack([self.vec[t] for t in texts]), [False] * len(texts)


def test_delta_auc_perfect_signal(mini_records):
    assert delta_auc(PerfectEncoder(mini_records), mini_records) == pytest.approx(1.0)
