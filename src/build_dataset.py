"""Build the one-row-per-meeting analysis file.

Usage: python -m src.build_dataset [--year 2023] [--prompt-id tone_v1] [--run 1]

Timing rules, all to avoid look-ahead bias:
- Statements come out during the trading day, before the close, so the
  meeting-day move is close(t) minus close(t-1).
- Controls use data through t-1 only.
- The 5-day return starts at close(t), after the statement is public.
- Rate changes take effect the day after the decision, so DFEDTARU is compared
  across t-1 and t+1 calendar days. A same-day difference would show almost no changes.
"""
import argparse

import numpy as np
import pandas as pd

from src.config import PROCESSED, RAW
from src.score_llm import output_path
from src.text_signals import add_signals

FORWARD_DAYS = 5
PRIOR_DAYS = 5


def market_features(dates: pd.Series, spy: pd.Series, fred: pd.DataFrame) -> pd.DataFrame:
    """Compute outcomes and controls for each decision date."""
    spy = spy.sort_index().dropna()
    calendar = spy.index
    # Bond markets close on some days stocks trade, so carry a yield over one such day.
    aligned = fred.reindex(calendar.union(fred.index)).sort_index().ffill(limit=1).reindex(calendar)
    target = fred["DFEDTARU"].dropna().asfreq("D").ffill()

    rows = []
    for date in pd.to_datetime(dates):
        if date not in calendar:
            raise ValueError(f"{date.date()} is not a trading day; check the meeting calendar")
        i = calendar.get_loc(date)
        if i < PRIOR_DAYS + 1:
            raise ValueError(f"Not enough price history before {date.date()}")
        has_forward = i + FORWARD_DAYS < len(spy)
        at = lambda col, k: aligned[col].iloc[k]
        rows.append({
            "decision_date": date,
            "d2y_bp": (at("DGS2", i) - at("DGS2", i - 1)) * 100,
            "d10y_bp": (at("DGS10", i) - at("DGS10", i - 1)) * 100,
            "spy_day_ret": spy.iloc[i] / spy.iloc[i - 1] - 1,
            "spy_next5_ret": spy.iloc[i + FORWARD_DAYS] / spy.iloc[i] - 1 if has_forward else np.nan,
            "d_target_bp": (target.get(date + pd.Timedelta(days=1), np.nan)
                            - target.get(date - pd.Timedelta(days=1), np.nan)) * 100,
            "vix_prior": at("VIXCLS", i - 1),
            "spy_prior5_ret": spy.iloc[i - 1] / spy.iloc[i - 1 - PRIOR_DAYS] - 1,
            "d2y_prior5_bp": (at("DGS2", i - 1) - at("DGS2", i - 1 - PRIOR_DAYS)) * 100,
        })
    return pd.DataFrame(rows)


def build(statements, scores, spy, fred) -> pd.DataFrame:
    df = add_signals(statements)
    df = df.merge(scores[["decision_date", "score", "reason"]], on="decision_date", how="left")
    df = df.rename(columns={"score": "llm_tone", "reason": "llm_reason"})
    df["d_llm_tone"] = df["llm_tone"].diff()
    df["d_lm_net_tone"] = df["lm_net_tone"].diff()
    df["d_keyword_balance"] = df["keyword_balance"].diff()
    df["dissent"] = df["vote_text"].str.contains("Voting against", regex=False).astype(int)

    sample = df[df["role"] == "sample"].copy()
    sample["decision_date"] = pd.to_datetime(sample["decision_date"])
    features = market_features(sample["decision_date"], spy, fred)
    keep = ["decision_date", "llm_tone", "d_llm_tone", "lm_net_tone", "d_lm_net_tone",
            "keyword_balance", "d_keyword_balance", "cosine_prior", "dissent", "llm_reason"]
    return features.merge(sample[keep], on="decision_date", validate="one_to_one")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int)
    parser.add_argument("--prompt-id", default="tone_v1")
    parser.add_argument("--run", type=int, default=1)
    args = parser.parse_args()

    statements = pd.read_csv(RAW / "statements.csv", dtype={"decision_date": str})
    scores_file = output_path(args.prompt_id, args.run)
    if scores_file.exists():
        scores = pd.read_csv(scores_file, dtype={"decision_date": str})
    else:
        print(f"{scores_file.name} not found; LLM columns will be blank")
        scores = pd.DataFrame(columns=["decision_date", "score", "reason"])
    spy = pd.read_csv(RAW / "spy.csv", index_col="date", parse_dates=True).iloc[:, 0]
    fred = pd.read_csv(RAW / "fred.csv", index_col="date", parse_dates=True)

    if args.year:
        years = statements["decision_date"].str[:4].astype(int)
        keep = statements.index[years == args.year]
        statements = statements.loc[max(keep[0] - 1, 0) : keep[-1]]

    dataset = build(statements, scores, spy, fred)
    if args.year:  # the prior statement was only needed to compute changes
        dataset = dataset[dataset["decision_date"].dt.year == args.year]
    out = PROCESSED / "event_dataset.csv"
    dataset.to_csv(out, index=False)
    print(f"wrote {len(dataset)} meetings to {out}")
    print(dataset.isna().sum()[lambda s: s > 0].to_string())


if __name__ == "__main__":
    main()
