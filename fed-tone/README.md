# Reading the Fed

BMGT347 final project. Does the hawkish or dovish tone of FOMC statements, measured with an LLM, explain Treasury and stock market moves beyond the rate decision and a traditional dictionary measure?

## Setup

Requires Python 3.10 or newer.

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
```

LLM scoring runs free on your own computer through Ollama, with no API key or account:

1. Install Ollama from https://ollama.com/download and open it.
2. Download the model, about 3 GB: `ollama pull gemma3:4b`

Only the person running the scoring needs Ollama. Commit the score files so everyone else can use them.

For the dictionary benchmark, download the Loughran-McDonald Master Dictionary CSV from https://sraf.nd.edu/loughranmcdonald-master-dictionary/ and save it in `data/raw/`. Keep the name starting with `Loughran-McDonald`. Without it, the pipeline still runs and `lm_net_tone` stays blank.

## Run the 2023 prototype

```
python -m src.fetch_statements --year 2023
python -m src.fetch_market
python -m src.score_llm --year 2023 --dry-run
python -m src.score_llm --year 2023
python -m src.build_dataset --year 2023
```

Read the dry-run prompt before scoring. The output is `data/processed/event_dataset.csv`, with one row per meeting.

## Run the full sample

```
python -m src.fetch_statements
python -m src.score_llm
python -m src.score_llm --prompt-id tone_v1 --run 2
python -m src.score_llm --prompt-id tone_v2
python -m src.build_dataset
```

Delete the 2023 score file first, so the whole sample comes from one run. Plug in your laptop and expect each scoring pass to take a while. If it stops, run the same command again and it will continue. The last two scoring commands are the repeat-run and reworded-prompt checks.

## Status

| Piece | Status |
| --- | --- |
| Meeting calendar, verified against the Fed site | Done |
| Statement, FRED, and SPY download | Written, needs its first real run |
| Dictionary, keyword, and similarity signals | Written, keyword lists need team review |
| LLM scoring with a local model | Written, needs its first real run |
| Event dataset with look-ahead tests | Written, tested on synthetic data |
| Hand-score validation | Not started |
| Regressions, event analysis, placebo tests | Not started |
| Out-of-sample test and investment rule | Not started |

## Dataset columns

| Column | Meaning |
| --- | --- |
| `d2y_bp`, `d10y_bp` | Meeting-day yield change, in basis points |
| `spy_day_ret` | SPY return, prior close to meeting-day close |
| `spy_next5_ret` | SPY return, meeting-day close to 5 trading days later |
| `d_target_bp` | Change in the federal funds target upper limit, in basis points |
| `vix_prior`, `spy_prior5_ret`, `d2y_prior5_bp` | Controls, using data through the day before the meeting |
| `llm_tone`, `d_llm_tone` | LLM score and its change from the prior statement |
| `lm_net_tone`, `d_lm_net_tone` | Dictionary tone and its change |
| `keyword_balance`, `d_keyword_balance` | Hawkish minus dovish phrases per 100 words, and its change |
| `cosine_prior` | Similarity to the prior statement |
| `dissent` | 1 if any member voted against the action |

See `docs/decisions.md` for choices the team should review, and log AI use in `docs/ai_log.md`.
