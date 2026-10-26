Phase 2 run 3 test (declared fourth use of the test split): 2273 records, 103 projects; 95% project-cluster bootstrap CIs.

| Signal | Pairwise acc. | Pooled AUC | PA minus v1 combined | AUC minus TF-IDF |
|---|---|---|---|---|
| TF-IDF delta | 0.745 [0.712, 0.778] | 0.706 [0.682, 0.729] | -0.025 [-0.040, -0.014] | - |
| MiniLM fine-tuned delta (v1) | 0.713 [0.685, 0.743] | 0.660 [0.638, 0.681] | -0.056 [-0.074, -0.041] | -0.046 [-0.066, -0.032] |
| v1 combined (TF-IDF + MiniLM-ft) | 0.769 [0.735, 0.804] | 0.706 [0.683, 0.730] | - | 0.000 [-0.009, 0.009] |
| MiniLM fine-tuned delta (phase 2) | 0.740 [0.706, 0.772] | 0.696 [0.671, 0.720] | -0.029 [-0.049, -0.012] | -0.010 [-0.023, 0.003] |
| Granite fine-tuned delta (phase 2) | 0.748 [0.710, 0.785] | 0.717 [0.686, 0.746] | -0.022 [-0.044, 0.002] | 0.011 [-0.006, 0.028] |
| TF-IDF + MiniLM (phase 2) | 0.772 [0.739, 0.804] | 0.724 [0.698, 0.749] | 0.003 [-0.012, 0.014] | 0.018 [0.010, 0.027] |
| TF-IDF + Granite (phase 2) | 0.776 [0.738, 0.812] | 0.734 [0.705, 0.760] | 0.006 [-0.012, 0.023] | 0.028 [0.018, 0.039] |

| Paired difference | Pairwise acc. | Pooled AUC |
|---|---|---|
| Granite fine-tuned delta (phase 2) minus MiniLM fine-tuned delta (phase 2) | 0.008 [-0.007, 0.028] | 0.021 [0.012, 0.030] |
| TF-IDF + Granite (phase 2) minus TF-IDF + MiniLM (phase 2) | 0.004 [-0.009, 0.020] | 0.010 [0.004, 0.017] |

Training-split selection (held-out dev projects, from the Kaggle notebook; ± = spread over seeds; single-seed rows are in dev_results.json):

| Run | Family | Dev pairwise acc. | Dev AUC |
|---|---|---|---|
| minilm pretrained | minilm-pretrained | 0.715 | 0.639 |
| minilm c0 (mean of 3 seeds) | minilm-mean | 0.751 | 0.687 ± 0.005 |
| minilm c1 (mean of 3 seeds) | minilm-mean | 0.747 | 0.684 ± 0.004 |
| minilm c2 (mean of 3 seeds) | minilm-mean | 0.735 | 0.689 ± 0.002 |
| minilm c3 (mean of 3 seeds) | minilm-mean | 0.750 | 0.684 ± 0.002 |
| minilm c4 (mean of 3 seeds) | minilm-mean | 0.747 | 0.684 ± 0.003 |
| minilm c5 (mean of 3 seeds) | minilm-mean | 0.733 | 0.680 ± 0.002 |
| minilm c6 (mean of 3 seeds) | minilm-mean | 0.749 | 0.691 ± 0.005 |
| minilm c7 (mean of 3 seeds) | minilm-mean | 0.754 | 0.694 ± 0.003 |
| granite pretrained | granite-pretrained | 0.761 | 0.648 |
| granite c0 (mean of 3 seeds) | granite-mean | 0.710 | 0.685 ± 0.003 |
| granite c1 (mean of 3 seeds) | granite-mean | 0.746 | 0.712 ± 0.002 |
| granite c2 (mean of 3 seeds) | granite-mean | 0.712 | 0.681 ± 0.004 |
| granite c3 (mean of 3 seeds) | granite-mean | 0.756 | 0.712 ± 0.002 |
| granite c4 (mean of 3 seeds) | granite-mean | 0.760 | 0.711 ± 0.001 |
| granite c5 (mean of 3 seeds) | granite-mean | 0.705 | 0.675 ± 0.005 |
| granite c6 (mean of 3 seeds) | granite-mean | 0.714 | 0.677 ± 0.003 |
| granite c7 (mean of 3 seeds) | granite-mean | 0.714 | 0.678 ± 0.002 |
