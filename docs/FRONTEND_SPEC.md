# Spequlator — Frontend specification

- **Version:** 1.2
- **Stack:** Vite + React + TypeScript, plain CSS (no UI kit), `fetch` against `/api/*` through the Vite dev proxy [R20]. Time budget: 2 hours (H6–H8).

## Design goal

A minimal analysis workspace that a first-time user understands without instructions. The emphasis is on evidence readability over dashboards.

## Layout (one page)

### Header
- **Spequlator**, with the subtitle "Understand potential gaps between code and documentation."
- A status pill fed by `/api/health`: `TF-IDF ready · Encoder ready/loading/unavailable`.

### Input workspace
- **Mode toggle:** `Compare a change` (default) / `Check a snapshot`.
- **Change mode:** three labelled text areas:
  - **Documentation**
  - **Code before**
  - **Code after**

  The code areas use a monospace font. On wide screens, Code before and Code after sit side by side.
- **Snapshot mode:** two areas, **Documentation** and **Code**.
- **Primary button:** **Analyze consistency**. It is disabled while required fields are empty or a request is in flight.
- **Secondary:** **Load dataset example**. This opens a selector of about 12 curated test-split records (chosen at H8 from a seeded sample, not cherry-picked by outcome) plus a search box. A `Docstring: before commit / after commit` switch fills Documentation with the old or new docstring. Below the panels, a collapsible block shows `diff_code` / `diff_docstring`: green `+`, red `-`, with `?` lines hidden.

### Results panel (below inputs, or right column at ≥ 1200px)
1. **Finding badge**, neutral colours: Potential drift (amber), No obvious drift (slate), Inconclusive (grey). Never red, never the word "bug".
2. **Summary sentence.**
3. **Evidence list.** Each item is tagged `Parameter check`, `Removed identifier` or `Term overlap`, shows the exact snippet or diff lines, and highlights the matched tokens in the input panels.
4. **Signals**, as two horizontal bars on a −1…+1 axis with zero marked, labelled "TF-IDF alignment shift" and "Encoder alignment shift". The caption reads: "Similarity signals, not probabilities." In snapshot mode the label is "similarity".
5. **What we can't tell**: the uncertainty list.
6. **Suggested review step.**
7. **Copy JSON** and **Download Markdown**: both are client-side and send nothing to a server.

### States
| State | Behaviour |
|---|---|
| Empty | Inline hint under each field. The Example button is highlighted. |
| Loading | Button shows a spinner and is disabled. Previous results are dimmed, not cleared. |
| Success | Results are shown and inputs preserved. Scroll to the results on narrow screens. |
| Validation error (422) | Message attached to the offending field (`error.field`). |
| Encoder unavailable | Report still shown. Banner: "Deep-learning signal unavailable — showing TF-IDF and rule evidence only." |
| API down | "Can't reach the analysis service. Start it with `uv run spequlator serve`." |
| Narrow (< 768px) | Panels stack vertically. Bars become full-width. |

## Interaction rules

- Never label a score as "confidence" or "probability of correctness".
- Visually separate **Observed** (evidence) from **Interpretation** (summary/explanation).
- No source text leaves the machine. There are no analytics and no external fonts or CDNs.

## Out of scope

Authentication, history, collaboration, deployment, IDE integration, automatic fixes.

## Acceptance checklist (verified at H9)

- [ ] A first-time user can complete a change-mode analysis from an example in 3 clicks or fewer.
- [ ] Both modes are reachable; labels are visible; the primary action is obvious.
- [ ] Results show evidence and uncertainty, and highlight matched tokens.
- [ ] Empty, loading, validation-error, encoder-unavailable and API-down states have been triggered and look right.
- [ ] The same input gives the same finding in the UI and the CLI (copy JSON → compare).
- [ ] `npm run build` passes, and a 375px-wide viewport has no horizontal scroll.