import json

import pandas as pd
import pytest

from src import score_llm

CFG = {"host": "http://x", "model": "m", "temperature": 0.3, "num_ctx": 4096, "redact_dates": True}


def body(score, done="stop"):
    return {"done_reason": done, "message": {"content": json.dumps({"score": score, "reason": "r"})}}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        if self.payload.get("error"):
            raise score_llm.requests.HTTPError(self.payload["error"])

    def json(self):
        return self.payload


def fake_post(monkeypatch, bodies):
    calls = []
    queue = list(bodies)

    def post(url, json, timeout):
        calls.append(json)
        return FakeResponse(queue.pop(0))

    monkeypatch.setattr(score_llm.requests, "post", post)
    return calls


def test_prompt_hides_dates_and_fills_statement():
    prompt = score_llm.build_prompt("tone_v1", "Met in December; low through mid-2015.")
    assert "December" not in prompt and "2015" not in prompt
    assert "{statement}" not in prompt
    assert prompt.count("[DATE]") >= 2


@pytest.mark.parametrize("prompt_id", ["tone_v1", "tone_v2"])
def test_prompts_exist_and_keep_json_braces(prompt_id):
    prompt = score_llm.build_prompt(prompt_id, "low rates")
    assert "low rates" in prompt and '{"score"' in prompt


def test_parse_valid():
    assert score_llm.parse_response(body(-2))["score"] == -2


def test_parse_rejects_off_scale():
    with pytest.raises(ValueError):
        score_llm.parse_response(body(3))


def test_parse_rejects_truncated():
    with pytest.raises(ValueError):
        score_llm.parse_response(body(1, done="length"))


def test_request_uses_schema_and_run_seed(monkeypatch):
    calls = fake_post(monkeypatch, [body(1)])
    score_llm.score_one(CFG, "p", run=2)
    assert calls[0]["format"] == score_llm.SCHEMA
    assert calls[0]["stream"] is False
    assert calls[0]["options"]["seed"] == 2000


def test_repeat_runs_use_different_seeds(monkeypatch):
    calls = fake_post(monkeypatch, [body(1), body(1)])
    score_llm.score_one(CFG, "p", run=1)
    score_llm.score_one(CFG, "p", run=2)
    assert calls[0]["options"]["seed"] != calls[1]["options"]["seed"]


def test_retries_bad_output_then_succeeds(monkeypatch):
    bad = {"done_reason": "stop", "message": {"content": "not json"}}
    calls = fake_post(monkeypatch, [bad, body(5), body(1)])
    result = score_llm.score_one(CFG, "p", run=1)
    assert result["attempts"] == 3 and len(calls) == 3


def test_gives_up_after_max_attempts(monkeypatch):
    fake_post(monkeypatch, [body(5)] * 3)
    with pytest.raises(RuntimeError):
        score_llm.score_one(CFG, "p", run=1)


def test_missing_model_gives_clear_message(monkeypatch):
    monkeypatch.setattr(score_llm.requests, "get", lambda *a, **k: FakeResponse({"models": []}))
    with pytest.raises(SystemExit, match="ollama pull m"):
        score_llm.model_digest(CFG)


def test_ollama_not_running_gives_clear_message(monkeypatch):
    def refuse(*a, **k):
        raise score_llm.requests.ConnectionError

    monkeypatch.setattr(score_llm.requests, "get", refuse)
    with pytest.raises(SystemExit, match="Ollama"):
        score_llm.model_digest(CFG)


def test_score_all_resumes(tmp_path, monkeypatch):
    out = tmp_path / "scores.csv"
    pd.DataFrame([{"decision_date": "2020-01-01", "model": "m", "digest": "d", "prompt_id": "tone_v1",
                   "run": 1, "score": 0, "reason": "saved", "attempts": 1}]).to_csv(out, index=False)
    statements = pd.DataFrame({"decision_date": ["2020-01-01", "2020-02-01"], "statement_text": ["a", "b"]})
    calls = fake_post(monkeypatch, [body(1)])
    result = score_llm.score_all(statements, CFG, "d", "tone_v1", 1, out)
    assert len(calls) == 1
    assert len(result) == 2
    assert len(pd.read_csv(out)) == 2


def test_retries_after_ollama_500(monkeypatch):
    stuck = {"error": "prediction aborted, token repeat limit reached"}
    calls = fake_post(monkeypatch, [stuck, body(0)])
    result = score_llm.score_one(CFG, "p", run=2)
    assert result["score"] == 0 and result["attempts"] == 2
    assert [c["options"]["seed"] for c in calls] == [2000, 2001]
