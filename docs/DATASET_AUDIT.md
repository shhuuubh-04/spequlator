# Dataset audit log

- **Audit date:** 2026-10-22 (v1.2 addendum same day)
- **Status:** Structure/overlap audit complete. CoDocBench licence (CC BY 4.0), pinned commit and SHA-256 checksums verified. SAFA/SciCoQA licence checks remain open (not needed for the main experiment).

## CoDocBench

| Check | Result |
|---|---:|
| Combined records | 4,573 |
| Train records | 2,300 |
| Test records | 2,273 |
| Unique records by audit key | 4,573 |
| Train/test exact-key overlap | 0 |
| Unique projects | 203 |
| Train projects | 100 |
| Test projects | 103 |
| Project overlap | 0 |
| Records with two versions | 4,573 |
| `whitespace_only_code=True` | 0 |
| `whitespace_only_docstring=True` | 0 |

## SAFA artifact counts

Backend 518; Concept 12; Core 1; Design Constraint 45; Epic 38; Epic Suite 9; Feature 93; Frontend 683; Functional Constraint 34; Functional Requirement 359; Gen 584; Goal 3; NFR 6; Security Requirement 2; tim 14. Total 2,401.

## SAFA trace counts

Backend2Design Constraint 17; Backend2Functional Requirement 76; Concept2Concept 11; Concept2Functional Constraint 29; Concept2Functional Requirement 30; Design Constraint2Design Constraint 4; Design Constraint2Functional Requirement 47; Epic Suite2Core 9; Epic2Epic Suite 44; Feature2Epic 115; Feature2Feature 3; Frontend2Design Constraint 0; Frontend2Functional Requirement 24; Functional Constraint2Feature 79; Functional Requirement2Epic 4; Functional Requirement2Feature 385; Functional Requirement2Functional Requirement 70; Functional Requirement2Goal 7; Functional Requirement2NFR 20; Gen2Backend 1; Gen2Design Constraint 116; Gen2Functional Requirement 96; Goal2Epic Suite 3; NFR2Goal 6; Security Requirement2Feature 2; tim 24. Total 1,222.

Code-related links: Backend2Design Constraint 17; Backend2Functional Requirement 76; Frontend2Functional Requirement 24; Gen2Design Constraint 116; Gen2Functional Requirement 96. Total 329. All inspected links had APPROVED status. Unique named pairs 329. Code endpoints matched 329; requirement endpoints matched 203, unmatched by name 126.

## SciCoQA

Split sizes: real 92, synthetic 543, pooled 129. Unique union 738. Overlap: real/synthetic 0, pooled/real 26, pooled/synthetic 0.

Real types: Difference 48; Paper Omission 29; Code Omission 12; None 3.
Real categories: Algorithm 22; Loss 22; Training 16; Model 10; Data 10; Evaluation 9; None 3.
Real validation: Gemini True 92; GPT True 80 and False 12.
Synthetic types: Difference 424; Paper Omission 64; Code Omission 55.
Pooled types: None 103; Difference 13; Paper Omission 10; Code Omission 3.
Pooled categories: None 103; Loss 6; Training 5; Model 4; Algorithm 4; Evaluation 4; Data 3.

## CoDocBench v1.2 addendum (train split only unless noted)

| Check | Result | Source |
|---|---:|---|
| Pinned commit | `ee0256da15a07dcf265d5313fe51a269aa7268e0` | R2 |
| Licence | CC BY 4.0 (Zenodo v1.0) | R3 |
| Collection rule | Code **and** docstring changed in the same commit; one-sided changes excluded | R1 |
| `code` field contains docstring (leak) | 5 / 2,300 | F1 |
| Diff format | `difflib.ndiff` (`- `, `+ `, `  `, `? `) | F1 |
| Records with identical old/new docstring | 0 | F1 |
| Docstring edit ratio ≥ 0.95 (near-trivial) | 25.3% | F2 |
| Docstring edit ratio ≥ 0.90 | 41.7% | F2 |
| New docstring words: p50 / p90 / p99 | 42 / 162 / 549 | F1 |
| New code whitespace tokens: p50 / p90 / p99 | 47 / 176 / 396 | F1 |
| `ast.parse` succeeds on dedented new code | 100% | F5 |
| Records whose docstring documents parameters | 49.8% | F5 |
| Top-5 project share | 29.4% | F1 |

Implication: at max 512 sub-word tokens, roughly the longest 10% of code/docstrings will be truncated. Log a `truncated` flag per input and report the truncation rate.

## Pre-release checklist

- [x] CoDocBench licence (CC BY 4.0) verified.
- [x] CoDocBench commit pinned and SHA-256 checksums recorded (`REFERENCES.md`).
- [ ] SAFA / SciCoQA licence verified (only needed if they are redistributed).
- [ ] Manual-review subset IDs and seed recorded (`results/manual_review_sample.csv`, seed 2026).
- [x] Official project-level test split preserved (enforced by `tests/test_split_guard.py`).