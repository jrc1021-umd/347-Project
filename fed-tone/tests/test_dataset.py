"""Look-ahead and timing checks on synthetic data with known answers."""
import numpy as np
import pandas as pd
import pytest

from src.build_dataset import build, market_features
from src.fetch_market import clean_prices, parse_fred_csv

DATES = pd.bdate_range("2023-01-02", periods=30)
EVENT = DATES[15]


def make_market(target_shift_days=1):
    spy = pd.Series(100 * 1.01 ** np.arange(30), index=DATES, name="SPY")
    fred = pd.DataFrame({
        "DGS2": 4 + 0.01 * np.arange(30), "DGS10": 3.5 + 0.02 * np.arange(30),
        "VIXCLS": 20.0 + np.arange(30),
    }, index=DATES)
    daily = pd.date_range(DATES[0], DATES[-1], freq="D")
    target = pd.Series(4.5, index=daily)
    target[target.index >= EVENT + pd.Timedelta(days=target_shift_days)] = 4.75
    return spy, fred.join(target.rename("DFEDTARU"), how="outer")


def test_event_outcomes():
    row = market_features(pd.Series([EVENT]), *make_market()).iloc[0]
    assert row["d2y_bp"] == pytest.approx(1)
    assert row["d10y_bp"] == pytest.approx(2)
    assert row["spy_day_ret"] == pytest.approx(0.01)
    assert row["spy_next5_ret"] == pytest.approx(1.01 ** 5 - 1)


@pytest.mark.parametrize("shift", [0, 1])
def test_target_change_found_when_effective_next_day_or_same_day(shift):
    row = market_features(pd.Series([EVENT]), *make_market(shift)).iloc[0]
    assert row["d_target_bp"] == pytest.approx(25)


def test_controls_ignore_event_day_and_later():
    spy, fred = make_market()
    base = market_features(pd.Series([EVENT]), spy, fred).iloc[0]
    spy2, fred2 = spy.copy(), fred.copy()
    spy2[spy2.index >= EVENT] *= 2
    fred2.loc[fred2.index >= EVENT, ["DGS2", "VIXCLS"]] += 5
    changed = market_features(pd.Series([EVENT]), spy2, fred2).iloc[0]
    for col in ["vix_prior", "spy_prior5_ret", "d2y_prior5_bp"]:
        assert changed[col] == pytest.approx(base[col])
    assert changed["d2y_bp"] != pytest.approx(base["d2y_bp"])


def test_forward_return_ignores_event_day_move():
    spy, fred = make_market()
    base = market_features(pd.Series([EVENT]), spy, fred).iloc[0]
    spy2 = spy.copy()
    spy2[spy2.index < EVENT] *= 0.5
    changed = market_features(pd.Series([EVENT]), spy2, fred).iloc[0]
    assert changed["spy_next5_ret"] == pytest.approx(base["spy_next5_ret"])


def test_bond_holiday_carries_prior_yield():
    spy, fred = make_market()
    fred.loc[DATES[14], "DGS2"] = np.nan
    row = market_features(pd.Series([EVENT]), spy, fred).iloc[0]
    assert row["d2y_bp"] == pytest.approx(2)


def test_non_trading_day_raises():
    spy, fred = make_market()
    with pytest.raises(ValueError):
        market_features(pd.Series([pd.Timestamp("2023-01-22")]), spy, fred)


def test_last_events_without_five_days_are_blank():
    spy, fred = make_market()
    row = market_features(pd.Series([DATES[-2]]), spy, fred).iloc[0]
    assert np.isnan(row["spy_next5_ret"])


def test_reference_row_supplies_prior_but_is_not_in_sample():
    spy, fred = make_market()
    statements = pd.DataFrame({
        "decision_date": [str(DATES[10].date()), str(EVENT.date())],
        "role": ["reference", "sample"],
        "statement_text": ["strong growth", "weak growth"],
        "vote_text": ["Voting for", "Voting for\n\nVoting against"],
    })
    scores = pd.DataFrame({"decision_date": statements["decision_date"], "score": [1, -1], "reason": ["a", "b"]})
    out = build(statements, scores, spy, fred)
    assert len(out) == 1
    assert out.loc[0, "d_llm_tone"] == -2
    assert out.loc[0, "dissent"] == 1


def test_parse_fred_handles_missing():
    s = parse_fred_csv("observation_date,DGS2\n2023-01-02,\n2023-01-03,4.4\n2023-01-04,.\n", "DGS2")
    assert s.isna().sum() == 2 and s.iloc[1] == 4.4


def test_clean_prices_handles_multiindex():
    idx = pd.date_range("2023-01-02", periods=2, name="Date")
    cols = pd.MultiIndex.from_tuples([("Close", "SPY"), ("Volume", "SPY")])
    raw = pd.DataFrame([[1.0, 5], [2.0, 6]], index=idx, columns=cols)
    assert clean_prices(raw, "SPY").tolist() == [1.0, 2.0]


def test_year_option_drops_prior_year_row(tmp_path, monkeypatch):
    from src import build_dataset as b
    dates = pd.bdate_range("2022-11-01", "2023-02-28")
    spy = pd.Series(100 + np.arange(len(dates), dtype=float), index=dates, name="SPY").rename_axis("date")
    fred = pd.DataFrame({"DGS2": 4.0, "DGS10": 3.5, "VIXCLS": 20.0, "DFEDTARU": 4.5},
                        index=pd.date_range(dates[0], dates[-1], freq="D")).rename_axis("date")
    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame({"decision_date": ["2022-12-14", "2023-02-01"], "role": "sample",
                  "statement_text": "a", "vote_text": "Voting for"}).to_csv(raw / "statements.csv", index=False)
    spy.to_csv(raw / "spy.csv")
    fred.to_csv(raw / "fred.csv")
    monkeypatch.setattr(b, "RAW", raw)
    monkeypatch.setattr(b, "PROCESSED", tmp_path)
    monkeypatch.setattr(b, "output_path", lambda *a: tmp_path / "none.csv")
    monkeypatch.setattr("sys.argv", ["x", "--year", "2023"])
    b.main()
    assert pd.read_csv(tmp_path / "event_dataset.csv")["decision_date"].tolist() == ["2023-02-01"]
