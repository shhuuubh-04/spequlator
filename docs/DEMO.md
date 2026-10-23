# Spequlator — 5-minute demo script

## Before you present (5 minutes, once)

Open two terminals in the repo:

```bash
# Terminal 1: API (wait for "Application startup complete")
uv run spequlator serve --port 8001

# Terminal 2: UI
cd frontend && npm run dev
```

1. Open http://localhost:5173. The status pill should say **TF-IDF ready · Encoder ready**. The encoder takes a few seconds after startup.
2. Rehearse steps 2 and 4 below once, so the model is warm and you've seen the outputs.
3. Keep `results/figures/auc_ci.png` and `docs/EVALUATION_RESULTS.md` open in another tab.

## The script

**1. The problem (30 s)**
"Code changes, and the docstring next to it often doesn't. Spequlator reads a docstring plus the code before and after a change, and tells you whether the docstring still fits, with the evidence. It says 'inconclusive' when it can't tell, instead of guessing."

**2. A clear case (60 s)**
- Click **Load dataset example** and pick `observe_lr`.
- Leave **Docstring before commit** selected and click **Analyze consistency**.
- **Expected:** *Potential drift*. R1 evidence lists the documented parameters that the new signature no longer has, with the `def observe_lr(` line.
- Point at the signal bars: "These are similarity scores, not probabilities."

**3. The same function, fixed docstring (30 s)**
- Switch to **after commit** and analyse again.
- **Expected:** the finding is no longer *Potential drift*. "Same code change, the docstring the authors actually wrote, so the warning goes away."

**4. An honest uncertain case (45 s)**
- In terminal 2 (or a third terminal), run:

  ```bash
  uv run spequlator analyze --example-id 7ebf17aa6bf3
  ```

- **Expected:** *Inconclusive*, "the comparison signals disagree", with the next step "Review manually". "Two parameters were added and not documented. The tool doesn't pretend to know."

**5. Results (60 s)**
Show `results/figures/auc_ci.png` and the answers in `docs/EVALUATION_RESULTS.md`:
- The task is a **proxy**: tell the docstring the authors replaced from the one they wrote. Test split opened once, after freezing.
- Comparing against the change beats a snapshot comparison (RQ1).
- The fine-tuned encoder alone doesn't beat TF-IDF; together they give the best pairwise accuracy (RQ2).
- The rules are rare but precise (RQ3).

**6. Limits and next step (45 s)**
- "The manual review of 60 reports was scored by an LLM, not a human, and we say so."
- "The biggest miss: a new parameter the docstring never mentions. R1 only checks one direction. A reverse check is the next rule to add."
- "Everything runs locally on CPU; no code leaves the machine."

## If something goes wrong

| Problem | Fix |
|---|---|
| UI says *Service offline* | Terminal 1 isn't running, or the port differs from `frontend/.env.local` (`SPEQULATOR_API_PORT=8001`). |
| Encoder shows *loading…* | Wait about 10 seconds; the UI re-checks by itself. |
| Port 8001 is busy | Use another port in both `serve --port` and `.env.local`, then restart `npm run dev`. |
| Live UI fails completely | Run steps 2–4 in the terminal with `uv run spequlator analyze --example-id 8e8e00c86a25` (add `--doc-version new` for step 3). |