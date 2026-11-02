"""Download FOMC statements from federalreserve.gov.

Usage: python -m src.fetch_statements [--year 2023]
"""
import argparse
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.config import RAW, meetings

URL = "https://www.federalreserve.gov/newsevents/pressreleases/monetary{date}a.htm"
HEADERS = {"User-Agent": "BMGT347 student research project"}

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_DATE_PATTERNS = [
    rf"\b(?:{MONTHS})\s+\d{{1,2}},\s+(?:19|20)\d{{2}}\b",      # January 25, 2012
    rf"\b(?:{MONTHS})\s+\d{{1,2}}(?:-\d{{1,2}})?\b",            # January 25
    rf"\b(?:early|mid|late|middle of|end of)[- ](?:19|20)\d{{2}}\b",  # mid-2015
    rf"\b(?:{MONTHS})\s+(?:19|20)\d{{2}}\b",                     # June 2015
    r"\b(?:19|20)\d{2}\b",                                       # 2015
    rf"\b(?:{MONTHS})\b",                                        # met in December
]


def parse_statement(html: str) -> dict:
    """Split a press release into the statement and the vote paragraph(s).

    Checked against the layout of all 121 statement pages used in this study:
    each has one body column, and the policy text always ends at "Voting for".
    """
    soup = BeautifulSoup(html, "lxml")
    article = soup.find(id="article")
    if article is None:
        raise ValueError("No #article element on page")
    bodies = [
        d for d in article.find_all("div", recursive=False)
        if "col-sm-8" in d.get("class", []) and "heading" not in d.get("class", [])
    ]
    if len(bodies) != 1:
        raise ValueError(f"Expected 1 body column, found {len(bodies)}")

    paragraphs = [" ".join(p.get_text(" ", strip=True).split()) for p in bodies[0].find_all("p")]
    paragraphs = [p for p in paragraphs if p]
    cut = next((i for i, p in enumerate(paragraphs) if p.startswith("Voting for")), None)
    if cut is None:
        raise ValueError("No 'Voting for' paragraph found")

    votes = [paragraphs[cut]]
    for p in paragraphs[cut + 1 :]:
        if p.startswith("Voting against"):
            votes.append(p)

    return {"statement_text": "\n\n".join(paragraphs[:cut]), "vote_text": "\n\n".join(votes)}


def redact_dates(text: str) -> str:
    """Replace dates with [DATE] so the LLM gets fewer hints about the period."""
    for pattern in _DATE_PATTERNS:
        text = re.sub(pattern, "[DATE]", text)
    return text


def main(year: int | None = None) -> None:
    rows = []
    for m in meetings(year).itertuples():
        date = m.decision_date.strftime("%Y%m%d")
        url = URL.format(date=date)
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        rows.append({
            "decision_date": m.decision_date.date().isoformat(),
            "role": m.role,
            "url": url,
            **parse_statement(response.text),
        })
        print(f"fetched {date}")
        time.sleep(0.5)
    out = RAW / "statements.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"wrote {len(rows)} statements to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int)
    main(parser.parse_args().year)
