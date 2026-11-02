"""Shared paths and settings."""
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"


def settings() -> dict:
    return yaml.safe_load((CONFIG / "settings.yaml").read_text())


def meetings(year: int | None = None) -> pd.DataFrame:
    """Load the meeting calendar.

    With a year, also keep the statement just before it so the first
    meeting of that year still has a change in tone.
    """
    df = pd.read_csv(CONFIG / "fomc_meetings.csv", parse_dates=["decision_date"], keep_default_na=False)
    df = df.sort_values("decision_date").reset_index(drop=True)
    if year is None:
        return df
    in_year = df.index[df["decision_date"].dt.year == year]
    if len(in_year) == 0:
        raise ValueError(f"No meetings in {year}")
    return df.loc[max(in_year[0] - 1, 0) : in_year[-1]].reset_index(drop=True)
