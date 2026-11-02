from pathlib import Path

import pytest

from src.config import meetings
from src.fetch_statements import parse_statement, redact_dates

HTML = (Path(__file__).parent / "fixtures" / "statement.html").read_text()


def test_statement_stops_at_vote():
    parsed = parse_statement(HTML)
    assert parsed["statement_text"].startswith("Information received")
    assert "Bernanke" not in parsed["statement_text"]
    assert "Implementation" not in parsed["statement_text"]
    assert "For release" not in parsed["statement_text"]


def test_dissent_kept_in_vote_text():
    assert "Voting against" in parse_statement(HTML)["vote_text"]


def test_missing_vote_raises():
    with pytest.raises(ValueError):
        parse_statement(HTML.replace("Voting for", "Votes for"))


@pytest.mark.parametrize("text, expected", [
    ("met in October suggests", "met in [DATE] suggests"),
    ("at least through mid-2015.", "at least through [DATE]."),
    ("through June 2015 and", "through [DATE] and"),
    ("on January 29-30.", "on [DATE]."),
    ("on December 12, 2012.", "on [DATE]."),
    ("inflation of 2 percent", "inflation of 2 percent"),
    ("the Committee may adjust", "the Committee may adjust"),
])
def test_redact_dates(text, expected):
    assert redact_dates(text) == expected


def test_calendar_counts():
    df = meetings()
    assert (df["role"] == "sample").sum() == 119
    by_year = df[df["role"] == "sample"].groupby(df["decision_date"].dt.year).size()
    assert by_year.pop(2020) == 7
    assert (by_year == 8).all()


def test_sample_decisions_are_weekdays():
    df = meetings()
    assert (df.loc[df["role"] == "sample", "decision_date"].dt.dayofweek < 5).all()


def test_year_filter_keeps_prior_statement():
    df = meetings(2023)
    assert df.iloc[0]["decision_date"].strftime("%Y-%m-%d") == "2022-12-14"
    assert len(df) == 9
