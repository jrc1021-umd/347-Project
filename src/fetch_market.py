"""Download FRED series and SPY prices.

Usage: python -m src.fetch_market
"""
import io

import pandas as pd
import requests

from src.config import RAW, settings

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def parse_fred_csv(text: str, series: str) -> pd.Series:
    """Parse a FRED CSV, turning blanks and '.' into missing values."""
    df = pd.read_csv(io.StringIO(text), na_values=["."])
    df.columns = ["date", series]
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[series].astype(float)


def clean_prices(raw: pd.DataFrame, ticker: str) -> pd.Series:
    """Return adjusted closes, whichever column layout yfinance used."""
    frame = raw.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    close = frame["Close"].dropna().astype(float).rename(ticker)
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    close.index.name = "date"
    return close


def main() -> None:
    import yfinance as yf

    cfg = settings()["market"]
    start, end = cfg["download_start"], cfg["download_end"]
    fred = []
    for series in cfg["fred_series"]:
        response = requests.get(
            FRED_URL, params={"id": series, "cosd": start, "coed": end}, timeout=60
        )
        response.raise_for_status()
        fred.append(parse_fred_csv(response.text, series))
        print(f"fetched {series}")
    pd.concat(fred, axis=1).to_csv(RAW / "fred.csv")

    ticker = cfg["equity_ticker"]
    prices = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if prices.empty:
        raise RuntimeError("yfinance returned no data; try again in a few minutes")
    clean_prices(prices, ticker).to_csv(RAW / "spy.csv")
    print("wrote fred.csv and spy.csv")


if __name__ == "__main__":
    main()
