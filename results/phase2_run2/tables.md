Phase 2 test run (declared third use (phase 2, run 2) of the test split): 2273 records, 103 projects; 95% project-cluster bootstrap CIs.

| Signal | Pairwise acc. | Pooled AUC | PA minus v1 combined | AUC minus TF-IDF |
|---|---|---|---|---|
| TF-IDF delta | 0.745 [0.712, 0.778] | 0.706 [0.682, 0.729] | -0.025 [-0.040, -0.014] | - |
| MiniLM fine-tuned delta (v1) | 0.713 [0.685, 0.743] | 0.660 [0.638, 0.681] | -0.056 [-0.074, -0.041] | -0.046 [-0.066, -0.032] |
| v1 combined (TF-IDF + MiniLM-ft) | 0.769 [0.735, 0.804] | 0.706 [0.683, 0.730] | - | 0.000 [-0.009, 0.009] |
| MiniLM fine-tuned delta (phase 2) | 0.735 [0.701, 0.771] | 0.694 [0.671, 0.718] | -0.034 [-0.048, -0.015] | -0.012 [-0.024, 0.001] |
| Cross-encoder (phase 2) | 0.646 [0.619, 0.680] | 0.552 [0.542, 0.562] | -0.124 [-0.164, -0.083] | -0.154 [-0.176, -0.134] |
| TF-IDF + MiniLM (phase 2) | 0.767 [0.734, 0.801] | 0.724 [0.698, 0.749] | -0.002 [-0.013, 0.008] | 0.018 [0.010, 0.026] |
| TF-IDF + cross-encoder | 0.772 [0.748, 0.795] | 0.656 [0.638, 0.677] | 0.002 [-0.022, 0.023] | -0.049 [-0.062, -0.038] |
| TF-IDF + MiniLM (phase 2) + cross-encoder | 0.798 [0.773, 0.823] | 0.702 [0.678, 0.727] | 0.029 [0.009, 0.047] | -0.004 [-0.015, 0.008] |

Training-split selection (held-out dev projects, from the Kaggle notebook):

| Run | Family | Dev pairwise acc. | Dev AUC |
|---|---|---|---|
| bi pretrained len256 | bi-encoder | 0.715 | 0.639 |
| bi pretrained len384 | bi-encoder | 0.724 | 0.645 |
| bi lr5e-05 ep3 len256 | bi-encoder | 0.747 | 0.693 |
| bi lr5e-05 ep3 len384 | bi-encoder | 0.752 | 0.696 |
| bi lr5e-05 ep5 len256 | bi-encoder | 0.745 | 0.690 |
| bi lr5e-05 ep5 len384 | bi-encoder | 0.747 | 0.693 |
| bi best, no hard negative | bi-encoder-ablation | 0.752 | 0.666 |
| bi best, batch 32 | bi-encoder-ablation | 0.754 | 0.689 |
| bi best, seed 7 | bi-encoder-ablation | 0.752 | 0.682 |
| bi best, seed 42 | bi-encoder-ablation | 0.756 | 0.686 |
| ce ms-marco-MiniLM-L6 diff | cross-encoder | 0.631 | 0.530 |
| ce ms-marco-MiniLM-L6 full | cross-encoder | 0.625 | 0.524 |
| ce all-MiniLM-L6 diff | cross-encoder | 0.593 | 0.528 |
| ce all-MiniLM-L6 full | cross-encoder | 0.590 | 0.520 |
| ce unixcoder diff (dev only) | cross-encoder-reference | 0.656 | 0.532 |
