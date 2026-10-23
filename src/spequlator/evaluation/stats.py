"""Proxy-task metrics and project-cluster bootstrap (D-021; Dror et al. 2018, R12; SciPy R17).

Signals follow one convention: higher = the documentation fits the NEW code better.
  pairwise accuracy: share of records where updated > stale (ties count 0.5; chance 0.5)
  pooled AUC: stale is the positive class, score = -signal (one global threshold view)
Bootstrap resamples whole projects (owner/project, D-026) because a few projects dominate.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from sklearn.metrics import roc_auc_score

N_BOOT = 1000
SEED = 2026


def pairwise_accuracy(stale: np.ndarray, updated: np.ndarray) -> float:
    stale, updated = np.asarray(stale, float), np.asarray(updated, float)
    return float(np.mean(updated > stale) + 0.5 * np.mean(updated == stale))


def pooled_auc(stale: np.ndarray, updated: np.ndarray) -> float:
    stale, updated = np.asarray(stale, float), np.asarray(updated, float)
    y = np.r_[np.ones(len(stale)), np.zeros(len(updated))]
    return float(roc_auc_score(y, -np.r_[stale, updated]))


def cluster_bootstrap(
    groups: np.ndarray,
    metric: Callable[[np.ndarray], float],
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[float, float, float]:
    """Point estimate and 95% percentile CI, resampling whole groups with replacement.

    ``metric`` receives row indices. For a paired comparison, pass a metric that returns
    ``a(idx) - b(idx)`` so both signals see the same resample.
    """
    groups = np.asarray(groups)
    members = [np.flatnonzero(groups == g) for g in np.unique(groups)]
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(members), len(members))
        values.append(metric(np.concatenate([members[k] for k in pick])))
    lo, hi = np.percentile(values, [2.5, 97.5])
    return float(metric(np.arange(len(groups)))), float(lo), float(hi)


def project_macro(groups: np.ndarray, metric: Callable[[np.ndarray], float]) -> float:
    """Unweighted mean of the metric over projects (each project counts once)."""
    groups = np.asarray(groups)
    return float(np.mean([metric(np.flatnonzero(groups == g)) for g in np.unique(groups)]))
