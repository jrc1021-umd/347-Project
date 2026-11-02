"""Score statement tone with a free local model through Ollama.

Ollama must be running and the model downloaded (see README). No API key is used.

Usage:
  python -m src.score_llm --year 2023 --dry-run     # shows a prompt, scores nothing
  python -m src.score_llm --year 2023               # scores one year
  python -m src.score_llm                           # scores every statement
  python -m src.score_llm --prompt-id tone_v1 --run 2   # repeat-run check
  python -m src.score_llm --prompt-id tone_v2           # reworded-prompt check

Finished rows are saved after each call, so an interrupted run can be restarted.
Each run number uses its own random seed, and the model's digest is saved with
every score so the exact model version is on record.
"""
import argparse
import json
from pathlib import Path

import pandas as pd
import requests

from src.config import CONFIG, PROCESSED, RAW, settings
from src.fetch_statements import redact_dates

VALID_SCORES = {-2, -1, 0, 1, 2}
MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 600
SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer", "enum": sorted(VALID_SCORES)},
        "reason": {"type": "string"},
    },
    "required": ["score", "reason"],
}


def build_prompt(prompt_id: str, statement: str, redact: bool = True) -> str:
    template = (CONFIG / "prompts" / f"{prompt_id}.txt").read_text()
    text = redact_dates(statement) if redact else statement
    return template.replace("{statement}", text)


def parse_response(body: dict) -> dict:
    """Pull the score from an Ollama response and reject anything off the scale."""
    if body.get("done_reason") == "length":
        raise ValueError("Response was cut off")
    result = json.loads(body["message"]["content"])
    score = result["score"]
    if isinstance(score, bool) or score not in VALID_SCORES:
        raise ValueError(f"Score off the scale: {score}")
    return {"score": int(score), "reason": str(result["reason"])}


def model_digest(cfg: dict) -> str:
    """Return the digest of the installed model, with clear errors for setup problems."""
    try:
        response = requests.get(f"{cfg['host']}/api/tags", timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        raise SystemExit("Could not reach Ollama. Open the Ollama app and try again.") from error
    for model in response.json().get("models", []):
        if model["name"] == cfg["model"]:
            return model["digest"]
    raise SystemExit(f"Model not installed. Run: ollama pull {cfg['model']}")


def score_one(cfg: dict, prompt: str, run: int) -> dict:
    """Call the model, retrying with a new fixed seed if the output is unusable."""
    error = None
    for attempt in range(MAX_ATTEMPTS):
        response = requests.post(
            f"{cfg['host']}/api/chat",
            json={
                "model": cfg["model"],
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "format": SCHEMA,
                "options": {
                    "temperature": cfg["temperature"],
                    "num_ctx": cfg["num_ctx"],
                    "seed": run * 1000 + attempt,
                },
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        try:
            return {**parse_response(response.json()), "attempts": attempt + 1}
        except (ValueError, KeyError, TypeError) as caught:
            error = caught
    raise RuntimeError(f"No usable score after {MAX_ATTEMPTS} attempts: {error}")


def output_path(prompt_id: str, run: int) -> Path:
    return PROCESSED / f"llm_scores_{prompt_id}_run{run}.csv"


def score_all(statements, cfg, digest, prompt_id, run, out) -> pd.DataFrame:
    """Score each statement in its own call, skipping rows already saved."""
    done = pd.read_csv(out, dtype={"decision_date": str}) if out.exists() else pd.DataFrame()
    finished = set(done["decision_date"]) if len(done) else set()
    rows = done.to_dict("records")
    for row in statements.itertuples():
        if row.decision_date in finished:
            continue
        prompt = build_prompt(prompt_id, row.statement_text, cfg["redact_dates"])
        result = score_one(cfg, prompt, run)
        rows.append({
            "decision_date": row.decision_date, "model": cfg["model"], "digest": digest,
            "prompt_id": prompt_id, "run": run, **result,
        })
        pd.DataFrame(rows).to_csv(out, index=False)
        print(f"{row.decision_date}: {result['score']:+d}")
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int)
    parser.add_argument("--prompt-id")
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = settings()["llm"]
    prompt_id = args.prompt_id or cfg["prompt_id"]
    statements = pd.read_csv(RAW / "statements.csv", dtype={"decision_date": str})
    if args.year:
        keep = statements.index[statements["decision_date"].str[:4] == str(args.year)]
        statements = statements.loc[max(keep[0] - 1, statements.index[0]) : keep[-1]]

    if args.dry_run:
        print(build_prompt(prompt_id, statements.iloc[0]["statement_text"], cfg["redact_dates"]))
        print(f"\nDry run only. Would score {len(statements)} statements with {cfg['model']}.")
        return

    out = output_path(prompt_id, args.run)
    score_all(statements, cfg, model_digest(cfg), prompt_id, args.run, out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
