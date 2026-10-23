Test split: 2273 records, 103 projects. Proxy task (D-015); 95% project-cluster bootstrap CIs.

| Signal | Pairwise acc. | Pooled AUC | AUC minus TF-IDF delta |
|---|---|---|---|
| TF-IDF snapshot | 0.676 [0.650, 0.704] | 0.564 [0.555, 0.575] | -0.142 [-0.161, -0.122] |
| TF-IDF delta | 0.745 [0.712, 0.778] | 0.706 [0.682, 0.729] | - |
| MiniLM delta | 0.712 [0.683, 0.743] | 0.636 [0.617, 0.657] | -0.070 [-0.085, -0.055] |
| MiniLM fine-tuned delta | 0.713 [0.685, 0.743] | 0.660 [0.638, 0.681] | -0.046 [-0.066, -0.032] |
| Combined (TF-IDF + minilm-ft) | 0.769 [0.735, 0.804] | 0.706 [0.683, 0.730] | 0.000 [-0.009, 0.009] |

Decision rule (calibrated-train-minilm-ft-2026-10-23): coverage 0.622, balanced accuracy on decided 0.720

| Pair | potential_drift | no_obvious_drift | inconclusive |
|---|---|---|---|
| stale | 0.465 | 0.161 | 0.374 |
| updated | 0.187 | 0.430 | 0.383 |

| Rule | Fires on stale | Fires on updated | Lift |
|---|---|---|---|
| R1 | 0.107 | 0.025 | 4.28 |
| R2 | 0.223 | 0.119 | 1.88 |

| Doc edit ratio | n | TF-IDF delta | MiniLM fine-tuned delta | Combined (TF-IDF + minilm-ft) |
|---|---|---|---|---|
| 0.00-0.70 | 620 | 0.731 | 0.738 | 0.770 |
| 0.70-0.90 | 688 | 0.802 | 0.752 | 0.802 |
| 0.90-0.95 | 333 | 0.743 | 0.709 | 0.790 |
| 0.95-1.00 | 632 | 0.696 | 0.649 | 0.723 |
