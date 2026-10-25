Phase 2 test run (declared second use of the test split): 2273 records, 103 projects; 95% project-cluster bootstrap CIs.

| Signal | Pairwise acc. | Pooled AUC | PA minus v1 combined | AUC minus TF-IDF |
|---|---|---|---|---|
| TF-IDF delta | 0.745 [0.712, 0.778] | 0.706 [0.682, 0.729] | -0.025 [-0.040, -0.014] | - |
| MiniLM fine-tuned delta (v1) | 0.713 [0.685, 0.743] | 0.660 [0.638, 0.681] | -0.056 [-0.074, -0.041] | -0.046 [-0.066, -0.032] |
| v1 combined (TF-IDF + MiniLM-ft) | 0.769 [0.735, 0.804] | 0.706 [0.683, 0.730] | - | 0.000 [-0.009, 0.009] |
| MiniLM fine-tuned delta (phase 2) | 0.736 [0.702, 0.772] | 0.694 [0.671, 0.718] | -0.033 [-0.047, -0.014] | -0.012 [-0.024, 0.001] |
| Cross-encoder (phase 2) | 0.602 [0.581, 0.629] | 0.545 [0.534, 0.558] | -0.168 [-0.204, -0.132] | -0.161 [-0.183, -0.140] |
| TF-IDF + MiniLM (phase 2) | 0.769 [0.734, 0.803] | 0.724 [0.698, 0.749] | -0.001 [-0.012, 0.010] | 0.018 [0.010, 0.026] |
| TF-IDF + cross-encoder | 0.747 [0.721, 0.772] | 0.647 [0.629, 0.669] | -0.023 [-0.052, -0.000] | -0.059 [-0.073, -0.046] |
| TF-IDF + MiniLM (phase 2) + cross-encoder | 0.779 [0.755, 0.804] | 0.696 [0.673, 0.720] | 0.010 [-0.012, 0.029] | -0.010 [-0.023, 0.002] |

Training-split selection (held-out dev projects, from the Kaggle notebook):

| Run | Family | Dev pairwise acc. | Dev AUC |
|---|---|---|---|
| bi pretrained len128 | bi-encoder | 0.694 | 0.633 |
| bi pretrained len256 | bi-encoder | 0.715 | 0.639 |
| bi lr2e-05 ep1 len128 | bi-encoder | 0.712 | 0.653 |
| bi lr2e-05 ep1 len256 | bi-encoder | 0.752 | 0.670 |
| bi lr2e-05 ep3 len128 | bi-encoder | 0.712 | 0.658 |
| bi lr2e-05 ep3 len256 | bi-encoder | 0.752 | 0.683 |
| bi lr5e-05 ep1 len128 | bi-encoder | 0.714 | 0.650 |
| bi lr5e-05 ep1 len256 | bi-encoder | 0.756 | 0.673 |
| bi lr5e-05 ep3 len128 | bi-encoder | 0.694 | 0.656 |
| bi lr5e-05 ep3 len256 | bi-encoder | 0.747 | 0.693 |
| bi best, no hard negative | bi-encoder-ablation | 0.752 | 0.666 |
| bi best, batch 32 | bi-encoder-ablation | 0.754 | 0.689 |
| bi best, seed 7 | bi-encoder-ablation | 0.752 | 0.682 |
| bi best, seed 42 | bi-encoder-ablation | 0.756 | 0.686 |
| ce ms-marco-MiniLM-L6 diff | cross-encoder | 0.607 | 0.532 |
| ce ms-marco-MiniLM-L6 full | cross-encoder | 0.578 | 0.519 |
| ce all-MiniLM-L6 diff | cross-encoder | 0.578 | 0.516 |
| ce all-MiniLM-L6 full | cross-encoder | 0.617 | 0.515 |
| ce unixcoder diff (dev only) | cross-encoder-reference | 0.598 | 0.538 |
