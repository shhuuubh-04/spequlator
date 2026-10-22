# Spequlator — Product Requirements Document

- **Version:** 1.2 (supersedes 1.1)
- **Project type:** Academic minor project, 10-hour build (see `10_HOUR_PLAN.md`)
- **Status:** Scope frozen, evidence-backed (see `REFERENCES.md`, `FEASIBILITY.md`); implementation pending
- **Date:** 2026-10-22

## 1. Product summary

Spequlator is a code–documentation consistency analysis and explanation system. It compares documentation with code and, preferably, with a **code change** (before → after). Its job is to flag documentation that still describes the old behaviour. Change-aware analysis is the primary mode: both the literature [R4] and our feasibility data [F3, F4] show it is much stronger than inspecting a single snapshot. It explains its findings with visible evidence and explicit uncertainty.

The complete project includes a Python analysis core, developer CLI, FastAPI backend, and interactive web frontend.

## 2. Problem statement

Documentation can become stale or describe behaviour differently from the implementation. Code and comments co-evolve in only about 7–13% of code changes [R5], and not every un-updated comment is wrong [R5]. A reviewer must inspect code and documentation changes manually to understand whether a change warrants a documentation update. Spequlator helps reviewers identify candidate inconsistencies and understand why they may matter.

## 3. Target users

- Developers reviewing code/docstring changes.
- Students demonstrating NLP and deep-learning methods on software artifacts.
- Reviewers investigating potential documentation drift.

## 4. Project goals

1. Accept code and documentation as direct user input.
2. Load and inspect selected versioned examples from CoDocBench.
3. Compare code and documentation using a classical NLP baseline (TF-IDF), pretrained transformer representations, a lightly fine-tuned transformer encoder (D-020), and two explainable rules.
4. Generate a structured report grounded in the supplied evidence.
5. Offer equivalent core analysis through a CLI and a web frontend.
6. Evaluate the comparison methods on CoDocBench's project-disjoint test split using the stale-vs-updated proxy task (D-015), with project-cluster bootstrap CIs, and manually review a sample of 30 reports.
7. Provide automated tests, reproducible setup, and project documentation.

## 5. Non-goals

- A verified five-class supervised classifier.
- Proof of program correctness or full static analysis.
- Automatic source-code modification.
- Training a generative model from scratch or fine-tuning a generator.
- Mixing CoDocBench, SAFA, and SciCoQA into one dataset.
- Production-scale multi-user hosting, authentication, or collaboration features.

## 6. Main user journeys

### Journey A — Manual analysis
1. User opens the frontend.
2. User pastes documentation plus either **code before and after** (change mode, recommended) or a single code snippet (snapshot mode).
3. User selects Analyze.
4. UI validates required input and shows loading/error states.
5. Results display the extracted inputs, TF-IDF signal, transformer signal, evidence-based interpretation, and limitations.

### Journey B — Dataset example
1. User selects a CoDocBench example (test split, curated list).
2. UI fills Code before / Code after and shows the diffs.
3. User chooses **Docstring: before commit** (simulates forgotten docs) or **after commit** (developer's update), then runs analysis.
4. Results show change evidence. For the old docstring the tool should usually lean toward `potential_drift`, and for the new one toward `no_obvious_drift`, but it is allowed to say `inconclusive`. CoDocBench contains only coordinated updates [R1], so the 'before' docstring is a simulated stale case, not observed drift.

### Journey C — CLI
1. Developer runs a documented CLI command against input files or a selected dataset record.
2. CLI returns a readable report and optionally JSON output.
3. CLI exit codes distinguish successful analysis from invalid input or runtime failure.

## 7. Functional requirements

- **FR-1 Shared core:** Analysis logic is implemented once in the Python package.
- **FR-2 Manual input:** Accept code and documentation text from the UI and CLI.
- **FR-3 Dataset access:** Load selected CoDocBench records through a dataset adapter.
- **FR-4 Change display:** Display `diff_code` and `diff_docstring` when available.
- **FR-5 Baseline:** Calculate a TF-IDF signal: delta-alignment in change mode, cosine in snapshot mode (vectorizer fit on train only).
- **FR-6 Neural representation:** Calculate the same signal with a transformer encoder: pretrained UniXcoder, and a MiniLM fine-tuned on the train split (D-018, D-020).
- **FR-6b Rules:** R1 parameter mismatch and R2 deleted-identifier mention, each with exact evidence (D-017).
- **FR-7 Explanation:** Produce a structured report with observations, evidence, possible implication, and uncertainty.
- **FR-8 CLI:** Expose analysis via a documented command-line interface.
- **FR-9 API:** Expose validated request/response endpoints for the frontend.
- **FR-10 Frontend:** Provide a simple input workflow, example selection, results view, loading state, and error state.
- **FR-11 Evaluation:** Preserve the official project-disjoint split and document manual review.
- **FR-12 Reproducibility:** Record model identifier, preprocessing, dataset revision, split, and sampling details.
- **FR-13 Tests:** Test core functions and key CLI/API paths.

## 8. Non-functional requirements

- Setup should be documented for Linux and, where practical, other common developer platforms.
- The frontend should remain usable on laptop-sized screens and adapt to narrow screens.
- User-provided source text should not be sent to third-party services by default.
- Large inputs should have documented limits.
- Errors must be actionable; stack traces should not be shown in normal UI.
- The frontend and CLI must use the same core analysis functions.
- Dataset files should not be committed blindly; check license, size, and redistribution restrictions.

## 9. Output contract

The analysis report should include:
- input/source identifier and available provenance
- documentation text or relevant excerpt
- code text or relevant excerpt
- code-change and documentation-change evidence when available
- TF-IDF signal
- transformer signal
- mode: `change` or `snapshot`
- finding: `potential_drift`, `no_obvious_drift`, or `inconclusive`
- evidence supporting the finding
- uncertainty/limitations
- recommended human review action

These three report findings are explanatory review states, not the original five-class labels and not ground-truth labels from CoDocBench.

## 10. Acceptance criteria

The project is complete when:
1. The frontend accepts manual input and displays analysis results.
2. The frontend can analyze at least a selected CoDocBench example.
3. The CLI can analyze inputs and emit readable output; JSON output is preferred.
4. CLI and API use the same Python analysis core.
5. TF-IDF and pretrained transformer comparison signals are implemented and their differences explained.
6. Reports show evidence and state uncertainty.
7. Automated tests cover preprocessing/core behavior and at least one CLI and API path.
8. The evaluation uses the official project-disjoint split. Thresholds are frozen on train before a single test run. The evaluation reports pairwise accuracy and AUC with 95% project-cluster bootstrap CIs, stratified by docstring edit size, and includes a 30-record manual review using the rubric.
9. Dataset roles, provenance, limitations, setup, architecture, and known gaps are documented.
10. A new developer can run the project by following the README/setup documentation.

## 11. Risks

- Similarity is mistaken for correctness.
- Dataset diffs are mistaken for ground-truth discrepancies.
- Frontend and CLI drift into separate implementations.
- Model downloads or hardware limitations block the demo. On Linux, PyPI `torch` pulls multi-GB CUDA wheels [R21], and `trust_remote_code` models can break on new `transformers` releases [F7]. Mitigated by the CPU index, pinned revisions and `--no-encoder`.
- The deep-learning signal underperforms TF-IDF: observed for pretrained encoders in delta mode [F8]. This is reported honestly as a finding, not hidden.
- Time is spent polishing UI before the core and evaluation work.

Mitigations: evidence-first reporting, shared core, graceful model-loading errors, simple UI, and a staged implementation plan.

## 12. Success definition

A successful minor project demonstrates a usable frontend and CLI backed by a shared NLP/deep-learning analysis pipeline, a reproducible dataset experiment, tests, and an honest discussion of limitations.