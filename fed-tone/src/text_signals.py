"""Benchmark text signals: dictionary tone, keyword balance, and similarity."""
import glob
import re
from collections import Counter

import numpy as np
import pandas as pd
import yaml

from src.config import CONFIG, ROOT, settings


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def load_lm_dictionary() -> tuple[set, set] | None:
    """Return (positive, negative) words, or None if the file is not there yet."""
    pattern = str(ROOT / settings()["text"]["lm_dictionary_glob"])
    files = glob.glob(pattern)
    if not files:
        print("Loughran-McDonald dictionary not found; lm_net_tone will be blank (see README)")
        return None
    df = pd.read_csv(files[0], keep_default_na=False, usecols=["Word", "Positive", "Negative"])
    words = df["Word"].str.lower()
    return set(words[df["Positive"] != 0]), set(words[df["Negative"] != 0])


def lm_net_tone(text: str, positive: set, negative: set) -> float:
    """(positive - negative) / total words."""
    words = tokens(text)
    pos = sum(w in positive for w in words)
    neg = sum(w in negative for w in words)
    return (pos - neg) / len(words) if words else np.nan


def keyword_balance(text: str, hawkish: list[str], dovish: list[str]) -> float:
    """(hawkish phrases - dovish phrases) per 100 words, matching whole words only."""
    lowered = " ".join(tokens(text))
    count = lambda terms: sum(len(re.findall(rf"\b{re.escape(t)}\b", lowered)) for t in terms)
    n_words = len(lowered.split())
    return 100 * (count(hawkish) - count(dovish)) / n_words if n_words else np.nan


def cosine_similarity(a: str, b: str) -> float:
    """Word-count cosine similarity. Uses only the two texts, so no later data leaks in."""
    ca, cb = Counter(tokens(a)), Counter(tokens(b))
    dot = sum(ca[w] * cb[w] for w in ca.keys() & cb.keys())
    norm = np.sqrt(sum(v * v for v in ca.values())) * np.sqrt(sum(v * v for v in cb.values()))
    return dot / norm if norm else np.nan


def add_signals(statements: pd.DataFrame) -> pd.DataFrame:
    """Add benchmark signals. Rows must include each sample meeting's prior statement."""
    df = statements.sort_values("decision_date").reset_index(drop=True).copy()
    keywords = yaml.safe_load((CONFIG / "keywords.yaml").read_text())
    df["keyword_balance"] = [
        keyword_balance(t, keywords["hawkish"], keywords["dovish"]) for t in df["statement_text"]
    ]
    dictionary = load_lm_dictionary()
    df["lm_net_tone"] = (
        [lm_net_tone(t, *dictionary) for t in df["statement_text"]] if dictionary else np.nan
    )
    previous = df["statement_text"].shift(1)
    df["cosine_prior"] = [
        np.nan if pd.isna(p) else cosine_similarity(t, p)
        for t, p in zip(df["statement_text"], previous)
    ]
    return df
