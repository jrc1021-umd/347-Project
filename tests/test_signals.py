import pandas as pd
import pytest

from src.text_signals import add_signals, cosine_similarity, keyword_balance, lm_net_tone


def test_lm_net_tone():
    assert lm_net_tone("good bad bad fine", {"good"}, {"bad"}) == pytest.approx(-0.25)


def test_keyword_balance_whole_words_only():
    assert keyword_balance("strongly worded", ["strong"], []) == 0
    assert keyword_balance("strong weak weak growth", ["strong"], ["weak"]) == pytest.approx(-25)


def test_keyword_phrase_matches():
    assert keyword_balance("elevated inflation today now", ["elevated inflation"], []) == pytest.approx(25)


def test_cosine_identical_and_disjoint():
    assert cosine_similarity("rates rose", "rates rose") == pytest.approx(1)
    assert cosine_similarity("rates rose", "jobs fell") == 0


def test_first_statement_has_no_prior():
    df = pd.DataFrame({"decision_date": ["2020-01-01", "2020-02-01"], "statement_text": ["a b", "a b"]})
    out = add_signals(df)
    assert pd.isna(out.loc[0, "cosine_prior"])
    assert out.loc[1, "cosine_prior"] == pytest.approx(1)
