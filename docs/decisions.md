# Decisions for the team to review

## Settled by checking the source

- **Sample size is 119, not about 120.** The scheduled March 17-18, 2020 meeting was cancelled, so 2020 has 7 meetings. The final report should say 119.
- **Unscheduled meetings stay out of the sample.** The March 15, 2020 statement is kept only as the prior statement for April 2020. December 14, 2010 is kept only as the prior statement for January 2011.
- **Decision dates are not always Wednesdays.** Some fall on Tuesdays or Thursdays, so the calendar lists each date instead of assuming a weekday.
- **Rate changes take effect the next day.** The February 1, 2023 hike took effect February 2, for example, so `d_target_bp` compares the target across the day before and the day after.

- **Scoring uses a free local model instead of a paid API.** This replaces "LLM API (Claude or OpenAI)" in the proposal, so the report and AI Workflow Appendix must say so. Keep the same model for the whole study. Each score file records the model's digest, which identifies its exact version.
- **Temperature is 0.3, with a different seed for each run.** At temperature 0 the repeat-run check would prove little, because identical answers would be expected.

## Team decisions (Nov 9, 2026)

- Roles: **Shan:** benchmark signals, hand-scoring lead, AI log; **Pat:** regressions, event analysis, placebo tests; **Max:** out-of-sample test, investment rule, figures; **Jacob:** coordination, data and LLM scoring, GitHub, report assembly.
- Hand-scorers: Shan and Pat, scoring 20 statements independently.
- Hawkish shift: d_llm_tone > 0.
- Dates stay redacted in the main run.
- Keyword lists are final as of today.
- April 2020 stays in the main results; dropping it is a robustness check.
- Voting text is excluded from LLM input; dissents are kept in the dissent column.
- Prompt tone_v1 is locked for the main run; tone_v2 is the sensitivity check.
