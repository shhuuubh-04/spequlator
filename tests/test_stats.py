import numpy as np
import pytest

from spequlator.evaluation import stats


def test_pairwise_accuracy_counts_ties_as_half():
    assert stats.pairwise_accuracy([0.0, 0.0, 0.0], [1.0, 0.0, -1.0]) == pytest.approx(0.5)
    assert stats.pairwise_accuracy([0.0, 0.0], [1.0, 1.0]) == 1.0


def test_pooled_auc_direction():
    assert stats.pooled_auc([-1.0, -2.0], [1.0, 2.0]) == 1.0  # stale lower = good
    assert stats.pooled_auc([1.0, 2.0], [-1.0, -2.0]) == 0.0


def test_cluster_bootstrap_reproducible_and_brackets_point():
    rng = np.random.default_rng(0)
    groups = np.repeat(np.arange(10), 20)
    s, u = rng.normal(-0.2, 1, 200), rng.normal(0.2, 1, 200)

    def metric(i):
        return stats.pairwise_accuracy(s[i], u[i])

    a = stats.cluster_bootstrap(groups, metric, n_boot=200)
    b = stats.cluster_bootstrap(groups, metric, n_boot=200)
    assert a == b
    point, lo, hi = a
    assert lo <= point <= hi


def test_paired_difference_of_identical_signals_is_zero():
    groups = np.repeat(np.arange(5), 4)
    x = np.linspace(-1, 1, 20)

    def diff(i):
        return stats.pooled_auc(x[i], -x[i]) - stats.pooled_auc(x[i], -x[i])

    assert stats.cluster_bootstrap(groups, diff, n_boot=50) == (0.0, 0.0, 0.0)


def test_project_macro_weights_projects_equally():
    groups = np.array(["a"] * 9 + ["b"])
    s = np.zeros(10)
    u = np.array([1.0] * 9 + [-1.0])
    assert stats.project_macro(groups, lambda i: stats.pairwise_accuracy(s[i], u[i])) == 0.5
