"""LLM-as-judge over a finished run.

Deterministic assertions in scenario_runner.py cover things with a crisp
definition: did a refusal event fire, did the agent stop within 1.5s, what
language did it reply in. They cannot score "did it acknowledge the emotion
before giving options" or "did it treat the shop as a problem to escape from".

That is what this does. It reads a run directory, sends the transcript plus the
persona's pass criteria and fail tells to a judge model, and asks for a verdict
per criterion with the quote that justifies it. Quotes are required so a verdict
can be checked against the transcript instead of taken on trust.

    testing/.venv/bin/python testing/judge.py recordings/20260726-120316_p4_prachi
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx

from persona_bot import load_env

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "kind": {"type": "string", "enum": ["pass_criterion", "fail_tell"]},
                    "met": {"type": "boolean"},
                    "evidence": {
                        "type": "string",
                        "description": "Verbatim quote from the transcript, or empty if none exists.",
                    },
                    "reasoning": {"type": "string"},
                },
                "required": ["criterion", "kind", "met", "evidence", "reasoning"],
                "additionalProperties": False,
            },
        },
        "overall": {"type": "string"},
    },
    "required": ["verdicts", "overall"],
    "additionalProperties": False,
}

JUDGE_SYSTEM = """
You are grading a career-counselling voice agent that talks to Indian students in
Hindi, Marathi and code-mixed Hinglish. You are given the full transcript of one
call, a list of pass criteria, and a list of fail tells.

For each pass criterion decide whether the agent met it. For each fail tell
decide whether the agent triggered it. `met` means "the criterion was satisfied"
for a pass criterion, and "this bad behaviour occurred" for a fail tell.

Rules:
- Judge only what is in the transcript. Do not assume the agent did something off-transcript.
- Every verdict needs a verbatim quote in `evidence`. If no quote supports it, set
  `met` to false for a pass criterion and leave `evidence` empty.
- A criterion that was never reached because the call ended early is not met.
- Be strict. Asking a question about a topic is not the same as explaining it.
- The transcript comes from speech recognition, so expect transcription noise.
  Judge the intent, not the spelling.
""".strip()


def build_prompt(meta: dict, transcript: list[dict]) -> str:
    lines = [f"{turn['speaker'].upper()}: {turn['text']}" for turn in transcript]
    return json.dumps(
        {
            "persona": meta.get("persona_name"),
            "pass_criteria": meta.get("pass_criteria", []),
            "fail_tells": meta.get("fail_tells", []),
            "transcript": lines,
        },
        ensure_ascii=False,
        indent=2,
    )


def judge(run_dir: Path, model: str) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    transcript = json.loads((run_dir / "transcript.json").read_text(encoding="utf-8"))

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": build_prompt(meta, transcript)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "verdicts",
                    "schema": JUDGE_SCHEMA,
                    "strict": True,
                },
            },
            "temperature": 0,
        },
        timeout=180,
    )
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])


def render(run_dir: Path, result: dict) -> str:
    lines = ["", "=" * 72, f"JUDGE — {run_dir.name}", "=" * 72]
    for kind, header in (
        ("pass_criterion", "PASS CRITERIA"),
        ("fail_tell", "FAIL TELLS"),
    ):
        verdicts = [v for v in result["verdicts"] if v["kind"] == kind]
        if not verdicts:
            continue
        lines.append(f"\n{header}")
        for verdict in verdicts:
            good = verdict["met"] if kind == "pass_criterion" else not verdict["met"]
            lines.append(f"  {'PASS' if good else 'FAIL'}  {verdict['criterion']}")
            if verdict["evidence"]:
                lines.append(f"          \"{verdict['evidence'][:150]}\"")
            else:
                lines.append(f"          {verdict['reasoning'][:150]}")
    lines.append("\n" + "-" * 72)
    lines.append(result["overall"])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-judge a finished run.")
    parser.add_argument("run_dir", help="path to a testing/recordings/<run> directory")
    parser.add_argument("--model", default=os.environ.get("JUDGE_MODEL", "gpt-4.1"))
    args = parser.parse_args()

    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not found; judge needs it")

    run_dir = Path(args.run_dir).resolve()
    result = judge(run_dir, args.model)
    output = render(run_dir, result)

    (run_dir / "judge.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "judge.txt").write_text(output, encoding="utf-8")
    print(output)
    print(f"\nsaved: {run_dir / 'judge.json'}")


if __name__ == "__main__":
    main()
