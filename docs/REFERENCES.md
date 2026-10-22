# Spequlator — References and evidence register

- **Version:** 1.2
- **Date:** 2026-10-22

Every design decision in `decisions.json` (D-015 onward) cites one or more IDs below. `[F*]` IDs are this project's own feasibility measurements. They were run on the **CoDocBench train split only**, and the test split was not opened. Reproduce them with `scripts/feasibility/`.

## Dataset

| ID | Source | What we rely on it for |
|---|---|---|
| R1 | Pai, Devanbu, Ahmed. *CoDocBench: A Dataset for Code-Documentation Alignment in Software Maintenance.* MSR 2025 Data & Tool Showcase. https://arxiv.org/abs/2502.00519 (HTML: https://arxiv.org/html/2502.00519v2) | **Every record is a commit where code and docstring changed together.** Code-only and docstring-only commits were excluded, as were whitespace-only edits. Only the first of consecutive updates is kept. The test split is a random 50% of projects. The top 25 projects make up about 60% of samples. Correctness is judged by being "closer to the matching version than the other", which is the basis for our proxy task. |
| R2 | CoDocBench repository. https://github.com/kunpai/codocbench, pinned commit `ee0256da15a07dcf265d5313fe51a269aa7268e0` (2026-05-25) | File names, JSON field names, `version_data` layout, `ndiff` diff format |
| R3 | CoDocBench Zenodo archive v1.0. https://zenodo.org/records/14251623 (DOI 10.5281/zenodo.14251623) | **Licence: CC BY 4.0.** Attribution is required, and redistribution is allowed with attribution. The GitHub repo has no LICENSE file. |
| R22 | SAFA release. https://zenodo.org/records/18285767 | Supplementary, unchanged from v1.1 |
| R23 | SciCoQA. Hugging Face dataset `UKPLab/scicoqa` | Future work only, unchanged from v1.1 |

## Prior work on code–comment inconsistency

| ID | Source | What we rely on it for |
|---|---|---|
| R4 | Panthaplackel, Li, Gligoric, Mooney. *Deep Just-In-Time Inconsistency Detection Between Comments and Source Code.* AAAI 2021. https://arxiv.org/abs/2010.01625 | (a) Encoding the **code change** beats looking at the current code alone. The best "post hoc" model reached 67.2 F1, against 77.1–80.9 F1 for "just-in-time" models. (b) The **OVERLAP(C, deleted)** rule flags a comment that shares a token with deleted code. It reached 68.0 F1, a strong, explainable baseline we adopt as rule R2. (c) Corazza et al.'s TF-IDF + SVM post hoc baseline reached 54.6 F1. |
| R5 | Wen, Nagy, Bavota, Lanza. *A Large-Scale Empirical Study on Code-Comment Inconsistencies.* ICPC 2019. https://www.inf.usi.ch/faculty/lanza/PUBS/P/Wen2019a.pdf | Code and comments co-evolve in only about 7% (method comments) to 13% (class comments) of cases. Not updating a comment is **not necessarily wrong**, which justifies our `inconclusive` state and the "not a bug" wording. |
| R6 | Corazza, Maggio, Scanniello. *Coherence of comments and method implementations: a dataset and an empirical investigation.* Software Quality Journal, 2018. https://www.springerprofessional.de/en/coherence-of-comments-and-method-implementations-a-dataset-and-a/11027070 | Precedent for a TF-IDF lexical baseline for comment/code coherence |
| R13 | Dit, Guerrouj, Poshyvanyk, Antoniol. *Can Better Identifier Splitting Techniques Help Feature Location?* ICPC 2011. https://www.cs.wm.edu/~denys/pubs/ICPC2011-IdentifierSplitting.pdf | Simple CamelCase/underscore splitting is a standard, competitive preprocessing step. Better splitters were rarely significantly better, so we use simple splitting. |

## Models

| ID | Source | Facts used |
|---|---|---|
| R7 | Guo et al. *UniXcoder: Unified Cross-Modal Pre-training for Code Representation.* ACL 2022. https://aclanthology.org/2022.acl-long.499 ; card https://huggingface.co/microsoft/unixcoder-base | Apache-2.0. 12 layers, 768-dim. Examples use max_length 512 with cosine similarity of normalised embeddings. The paper's zero-shot result is code-to-code search; NL-to-code search was fine-tuned. |
| R8 | `sentence-transformers/all-MiniLM-L6-v2`. https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 | Apache-2.0. About 22.7M parameters, 384-dim. **Truncates input past 256 word pieces.** |
| R9 | `jinaai/jina-embeddings-v2-base-code`. https://huggingface.co/jinaai/jina-embeddings-v2-base-code | Apache-2.0, 161M parameters. Trained on docstring–code pairs. **Requires `trust_remote_code=True`.** |
| R10 | `Salesforce/codet5p-110m-embedding`. https://huggingface.co/Salesforce/codet5p-110m-embedding | BSD-3, 256-dim. Requires `trust_remote_code=True`. |
| R11 | `flax-sentence-embeddings/st-codesearch-distilroberta-base`. https://huggingface.co/flax-sentence-embeddings/st-codesearch-distilroberta-base | Trained on CodeSearchNet. **Max 128 tokens, and the card states no licence.** Used for comparison only, never as the default. |

## Methods, statistics and tooling

| ID | Source | Use |
|---|---|---|
| R12 | Dror, Baumer, Shlomov, Reichart. *The Hitchhiker's Guide to Testing Statistical Significance in NLP.* ACL 2018. https://aclanthology.org/P18-1128/ | Bootstrap resampling for paired metric comparisons and confidence intervals (CIs) |
| R17 | SciPy `scipy.stats.bootstrap`. https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html | Bootstrap implementation. We resample *projects* (cluster bootstrap) because of project skew [F1]. |
| R14 | `docstring_parser` (PyPI). https://pypi.org/project/docstring-parser/ | Parses reST, Google and NumPy docstring parameter sections (rule R1) |
| R15 | Python `ast`. https://docs.python.org/3.13/library/ast.html | Extracts function signatures (rule R1) |
| R16 | scikit-learn `TfidfVectorizer`. https://scikit-learn.org/0.21/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html | `sublinear_tf`, `min_df` and cosine similarity on L2-normalised rows |
| R18 | Typer testing. https://typer.tiangolo.com/tutorial/testing/ | `CliRunner` tests |
| R19 | FastAPI testing. https://fastapi.tiangolo.com/tutorial/testing/ | `TestClient` tests |
| R20 | Vite server options. https://vite.dev/config/server-options.html | `server.proxy` so the frontend calls `/api` with no CORS setup |
| R21 | uv + PyTorch guide. https://docs.astral.sh/uv/guides/integration/pytorch/ | **On Linux, PyPI `torch` installs CUDA wheels by default.** Pin the CPU index to avoid a multi-GB download. |

## Project feasibility measurements (train split only, 2026-10-22)

| ID | Finding | Script |
|---|---|---|
| F1 | Train: 2,300 records, 100 projects. The top 5 projects (core, cpython, django, ray, ccxt) make up 29.4% of records. Docstrings in `code` were removed: the new docstring's first 40 characters appear inside the new code in only 5 of 2,300 records. `diff_code` and `diff_docstring` are Python `difflib.ndiff` text (`- `, `+ `, `? ` prefixes). New docstring length: median 42 words, p90 162. New code: median 47 whitespace tokens, p90 176. | `stats.py`, `stats2.py` |
| F2 | Docstring edit size, measured as `difflib.SequenceMatcher` ratio between old and new docstring: median 0.863. **25.3% of records have ratio ≥ 0.95**, i.e. near-trivial docstring edits. | `stats.py` |
| F3 | Absolute TF-IDF similarity `cos(new_code, doc)` is a weak drift signal. It ranks the new docstring above the old one in 65.2% of records (7.4% ties), but **pooled ROC-AUC is only 0.565**. | `spike.py` |
| F4 | The **delta-alignment** signal `cos(doc, new_code) − cos(doc, old_code)` works much better. With TF-IDF, **pooled AUC is 0.724**. Δ < 0 for 61.8% of stale (old) docstrings and 28.5% of updated docstrings. | `spike4.py` |
| F5 | Rule R1 (parameter mismatch): `ast` parses 100% of new code, and 49.8% of records document parameters. A docstring naming a parameter missing from the new signature occurs in **15.3% of old docstrings and 7.4% of new docstrings**. | `spike3.py` |
| F6 | Rule R2 (deleted-identifier mention, adapted from R4's OVERLAP): fires for **27.8% of old docstrings and 17.7% of new docstrings**. | `spike.py` |
| F7 | Encoder comparison on 300 seeded train records (seed 13), CPU, absolute similarity. TF-IDF + split: pairwise 0.640, AUC 0.558. UniXcoder: pairwise 0.647, AUC 0.549, 0.195 s per text on 2 CPU cores. MiniLM (256-token truncation): pairwise 0.570, AUC 0.543, 0.026 s per text. **Jina v2 code failed to load** with `transformers` 5.x: `ImportError: find_pruneable_heads_and_indices`. | `spike2.py` |
| F8 | Delta-alignment on the 300-record sample: **TF-IDF Δ AUC 0.733** (PA 0.797), UniXcoder Δ 0.641, MiniLM Δ 0.632, st-codesearch Δ 0.635. **Pretrained encoders trail TF-IDF in Δ mode.** | `spike5.py` |
| F9 | Project-disjoint dev inside train (20 projects, 725 records): TF-IDF Δ AUC 0.693 (PA 0.760). MiniLM pretrained 0.624. **MiniLM fine-tuned 1 epoch on the other 80 projects: 0.649**, trained in 371 s on 2 cores (batch 8, 128 tokens; batch 16 ran out of memory at 8 GB). TF-IDF + fine-tuned combination: **PA 0.778**, AUC 0.692. | `spike6.py` |
| F10 | Explicit-edit variant `cos(doc, added lines) − cos(doc, removed lines)` on the same dev set: TF-IDF 0.658, MiniLM 0.595, UniXcoder 0.614. **Worse than full-code Δ**, so diff lines feed rules and evidence only. | `spike7.py` |

## Checksums (SHA-256) of CoDocBench files at commit `ee0256da`

```
c0e8563af0baf9eab4fe1341fd0bf2099ec41030fd5c2224f1c3803a712c21d4  dataset/codocbench.jsonl  (4,573 lines)
9eef860afedcbf059a4f2e408cafbaa6c61ffbf4369e687a9b45ae80f7ac7c6d  dataset/train.jsonl       (2,300 lines)
74e3da99744a43bdf1be77c57eb1069548911c30fd931a49bbc7d0d5050dcdea  dataset/test.jsonl        (2,273 lines)
```

## Model revisions to pin

```
sentence-transformers/all-MiniLM-L6-v2   1110a243fdf4706b3f48f1d95db1a4f5529b4d41
jinaai/jina-embeddings-v2-base-code      516f4baf13dec4ddddda8631e019b5737c8bc250   (not used; see F7)
microsoft/unixcoder-base                 5604afdc964f6c53782a6813140ade5216b99006   (apache-2.0)
flax-sentence-embeddings/st-codesearch-distilroberta-base  23d22ea4191fc9d006833d3b62694949f1ffebd1  (no licence stated; comparison only)
```