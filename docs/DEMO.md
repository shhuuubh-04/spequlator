# Spequlator — 5-minute demo script

## Before you present (5 minutes, once)

Open two terminals in the repo:

```bash
# Terminal 1: API (wait for "Application startup complete")
uv run spequlator serve --port 8001

# Terminal 2: UI
cd frontend && npm run dev
```

1. Open http://localhost:5173. Top right should say **TF-IDF ready, encoder ready**. The encoder takes a few seconds after startup.
2. Rehearse steps 2–4 once, so the model is warm and you've seen the outputs.
3. Keep `results/figures/auc_ci.png` and `docs/EVALUATION_RESULTS.md` open in another tab.

## The script

**1. The problem (30 s)**
"Code changes, and the docstring next to it often doesn't. Spequlator reads a docstring plus the code before and after a change, and says whether the docstring still fits. It shows its evidence and every step of the calculation, and it says 'inconclusive' when it can't tell."

**2. A clear case (90 s)**
- Click **Start from a real commit**, pick `observe_lr`, keep **Docstring before the commit**, click **Check documentation**.
- **Expected:** *Potential drift*. The renamed parameters are highlighted in the docstring, with margin note 1: "Documented, but not a parameter of the code (rule R1)".
- Point at **Signals**: "Similarity scores, not probabilities. Left of the shaded band means the docstring fits the old code better."

**3. How it was computed (90 s)**
Scroll to **How it was computed**. Don't read every step; show three:
- **Step 3, tokens:** "Identifiers are split, e.g. `output_folder` becomes `output` and `folder`."
- **Step 6, TF-IDF:** "Each row is tf × idf, divided by the vector's length. The last columns multiply the two texts' weights, and the sums at the bottom are exactly the cosines. The difference is the TF-IDF signal."
- **Step 9, decide:** "The checks run in order; the first yes decides. Here R1 fired, so the rest were not reached."

**4. The fixed docstring (30 s)**
- Click **Edit inputs**, switch to **After the commit**, check again.
- **Expected:** the finding is no longer *Potential drift*. "Same code change, the docstring the authors actually wrote, so the warning goes away."

**5. Results (60 s)**
Show `results/figures/auc_ci.png` and the answers in `docs/EVALUATION_RESULTS.md`:
- The task is a **proxy**: tell the docstring the authors replaced from the one they wrote. Test split opened once, after freezing.
- Comparing against the change beats a snapshot comparison (RQ1).
- The fine-tuned encoder alone doesn't beat TF-IDF; together they give the best pairwise accuracy (RQ2).
- R1 is a strong, specific signal (4.3x more often on stale docstrings); R2 is weaker (1.9x) (RQ3).

**6. Limits and next step (30 s)**
- "The manual review of 60 reports was scored by an LLM, not a human, and we say so."
- "The biggest miss: a new parameter the docstring never mentions. Step 4 shows that direction for information, but R1 doesn't use it yet."
- "Everything runs locally on CPU; no code leaves the machine. **Print or save as PDF** gives the whole report as a document."

## If something goes wrong

| Problem | Fix |
|---|---|
| Top right says *Analysis service offline* | Terminal 1 isn't running, or the port differs from `frontend/.env.local` (`SPEQULATOR_API_PORT=8001`). |
| *encoder loading…* | Wait about 10 seconds; the page re-checks by itself. |
| Port 8001 is busy | Use another port in both `serve --port` and `.env.local`, then restart `npm run dev`. |
| An inconclusive example is wanted | `uv run spequlator analyze --example-id 7ebf17aa6bf3` (two parameters added, signals disagree). |
| Live UI fails completely | `uv run spequlator analyze --example-id 8e8e00c86a25` (add `--doc-version new` for step 4). |