# Spequlator — Dataset decisions and handling

- **Version:** 1.2 (supersedes 1.1)
- **Status:** Dataset roles frozen. CoDocBench pinned and checksummed.
- **Date:** 2026-10-22

## Decision summary

| Dataset | Role | Main implementation | Must not infer |
|---|---|---|---|
| CoDocBench | Primary | Yes | Version pairs are not verified five-class consistency labels. The dataset has **no** code-only (real drift) commits [R1]. |
| SAFA | Supplementary traceability data | No, not in primary experiment | An approved link is not proof of full compliance, and an absent link is not proof of absence |
| SciCoQA | Future research only | No | Scientific paper discrepancy types cannot be silently mapped to software-docstring consistency |

## CoDocBench

### What it is (sourced)

- Python functions from about 200 popular GitHub projects. Each record holds **two versions** of one function, where the developer changed **both the code and the docstring in the same commit**. Commits that changed only one of them were excluded, as were whitespace-only edits [R1].
- Split: train 2,300 / test 2,273 records, a random 50% of projects each, with zero project overlap [R1, DATASET_AUDIT].
- Licence: **CC BY 4.0** (Zenodo v1.0) [R3]. Attribute in README and in any redistributed subset.
- Pinned source: `github.com/kunpai/codocbench` @ `ee0256da15a07dcf265d5313fe51a269aa7268e0` [R2]. SHA-256 checksums are in `REFERENCES.md`.

### Fields used

`owner`, `project`, `file_path`, `function`, `version_data[0|1]` → {`docstring`, `code`, `commit_sha`, `commit_date_time`, `commit_message`, `docstring_lines`, `code_lines`}, `diff_code`, `diff_docstring`.

- `code` has the docstring removed: only 5 of 2,300 train records leak it [F1]. This matters because a leaked docstring would make similarity scores trivially high.
- `diff_*` are `difflib.ndiff` strings. Lines start with `"- "` (removed), `"+ "` (added), `"  "` (unchanged) or `"? "` (intraline hints, which must be ignored) [F1].
- `version_data[0]` is the pre-change version and `version_data[1]` the post-change version. The two have different `commit_sha` values.

### What this means for Spequlator

Because every record is a *coordinated* update, CoDocBench cannot supply examples of real drift. It does give a clean, label-free **counterfactual**, and the project uses it as a **proxy task** (decision D-015):

- **Stale pair:** old docstring checked against the code change (old code → new code). This simulates a developer who changed the code and forgot the docs. We know the old docstring needed updating, because the developer updated it in the same commit [R1].
- **Updated pair:** new docstring checked against the same code change.

A good signal should rate the stale pair as less aligned with the new code than the updated pair. This mirrors CoDocBench's own evaluation idea: an output is correct when it is "closer to its matching reference than to the other version" [R1].

**Caveats that must appear in every results table:**

1. These are **proxy** labels taken from the dataset's structure. They are not human drift judgements.
2. 25.3% of records have near-trivial docstring edits (SequenceMatcher ratio ≥ 0.95) [F2]. For these, the stale docstring is almost certainly still acceptable. Report them in a separate stratum.
3. Some old docstrings may have been only cosmetically outdated. Wen et al. show that not updating a comment is not necessarily wrong [R5].

### Handling rules

- Keep raw files in `data/raw/codocbench/` (git-ignored). Verify the SHA-256 checksums on load (`spequlator data verify`).
- Never fit TF-IDF vocabulary/IDF, choose thresholds, or select manual-review examples using `test.jsonl` until the frozen evaluation run (H4).
- The record ID is `sha1(owner/project/file_path::function::v0_sha::v1_sha)[:12]`. The audit key matches v1.1.
- Large-scale skew: the top 5 projects make up 29.4% of train records [F1]. Report project-macro averages and use a project-cluster bootstrap [R12, R17].

## SAFA and SciCoQA

Unchanged from v1.1. See `DATASET_AUDIT.md`. Neither is loaded by the application or the main experiment.

## Freeze and release rules

1. Do not merge these datasets for the main experiment.
2. Do not generate *drift* labels from similarity scores, change flags or link absence. The D-015 proxy labels come from the dataset's construction (old vs new version), are named "proxy" everywhere, and are not presented as drift ground truth.
3. Keep data files out of the application source tree.
4. Attribute CoDocBench under CC BY 4.0 when redistributing any subset (for example, the demo example file).
5. Record exact revisions, SHA-256 checksums, subset IDs and random seeds (seeds: 13 = feasibility, 2026 = bootstrap/manual-review sampling).
6. Any change to dataset role or split policy must be recorded in root `decisions.json`.