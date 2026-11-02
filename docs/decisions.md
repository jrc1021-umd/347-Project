# Decisions for the team to review

## Settled by checking the source

- **Sample size is 119, not about 120.** The scheduled March 17-18, 2020 meeting was cancelled, so 2020 has 7 meetings. The final report should say 119.
- **Unscheduled meetings stay out of the sample.** The March 15, 2020 statement is kept only as the prior statement for April 2020. December 14, 2010 is kept only as the prior statement for January 2011.
- **Decision dates are not always Wednesdays.** Some fall on Tuesdays or Thursdays, so the calendar lists each date instead of assuming a weekday.
- **Rate changes take effect the next day.** The February 1, 2023 hike took effect February 2, for example, so `d_target_bp` compares the target across the day before and the day after.

- **Scoring uses a free local model instead of a paid API.** This replaces "LLM API (Claude or OpenAI)" in the proposal, so the report and AI Workflow Appendix must say so. Keep the same model for the whole study. Each score file records the model's digest, which identifies its exact version.
- **Temperature is 0.3, with a different seed for each run.** At temperature 0 the repeat-run check would prove little, because identical answers would be expected.

## Open questions

1. **Should dates stay redacted?** Removing dates limits hindsight, as the proposal promised, but it also removes forward guidance such as "at least through mid-2015," which may be real policy information. Set `redact_dates: false` in `config/settings.yaml` to compare, but save that run's scores under a different `--run` number.
2. **What about hindsight beyond dates?** The model can still infer the period from content such as the pandemic or the war in Ukraine, and it learned from later history. Name this as a limitation in the report. Dates alone cannot remove it.
3. **Does the score just repeat the rate decision?** Statements announce the decision, so tone may partly reflect it. The target-change control addresses this, but check how correlated `d_llm_tone` and `d_target_bp` are.
4. **Which prior statement should April 2020 use?** The code uses March 15, 2020. A notation-vote statement on March 23 came later, so consider dropping April 2020 as a robustness check.
5. **How is a hawkish shift defined?** The proposal does not say. The simplest rule is `d_llm_tone > 0`. Agree on it before looking at results, and use only data through 2020 if any threshold is tuned.
6. **Should voting text be scored?** It is removed from the LLM input because member names reveal the period. Dissents are kept in the `dissent` column.
7. **Is the model good enough?** Check hand-score agreement on the 20 statements before running regressions. If agreement is poor, a weak LLM result may reflect this small model, not the idea itself. Try a larger model only if the laptop can run it, then rerun every statement with that model.
8. **Are the keyword lists fair?** `config/keywords.yaml` is a starter list. Finalize it before seeing results, since editing it afterward would bias the benchmark.
