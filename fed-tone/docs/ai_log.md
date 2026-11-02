# AI log

Source material for the AI Workflow Appendix. Add an entry whenever AI affects code, analysis, or writing.

## Template

**Date / person / tool:**
**Task and prompt summary:**
**What AI produced:**
**How we checked it:**
**What we changed or rejected:**

## Entries

**Nov 1, 2026 / Jacob / Claude:** Brainstormed project ideas and drafted the proposal. Team to confirm it reviewed the final version.

**Nov 2, 2026 / Jacob / Claude:** Built the starter repository: meeting calendar, data downloads, benchmark signals, LLM scorer, dataset builder, and tests. Checked meeting dates against the Fed's calendar pages and tested the code on synthetic data with known answers. No real market data or LLM scores had been run at this point, so the team still needs to review the code and run it.

**Nov 2, 2026 / Jacob / Claude:** Replaced the paid Claude API scorer with a free local model through Ollama because the team did not want to pay for API use. The scorer was tested with simulated Ollama responses, not a real model.

**Candidate example of an AI error to verify:** The AI-drafted proposal says "about 120 events," but checking the Fed's calendar gives 119 because the March 2020 meeting was cancelled.
