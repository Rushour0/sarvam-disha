"""Combined scoring: deterministic assertions AND an LLM judge, per step.

The two layers catch different things and neither is sufficient alone.

Deterministic assertions are exact and free. They answer "did a refusal event
fire", "did the agent stop within 1.5s", "what language code came back". They
cannot tell you whether the agent was condescending, whether it actually
explained something or just asked another question, or whether it endorsed a bad
source. They also fail silently when the assertion itself is too loose — a step
asserting only `no_event_type: career` passed while the agent resumed the career
script through a constraint question instead.

The judge covers exactly that gap, and has the opposite weakness: it is
persuadable, and it cannot see events at all.

So a step passes only when both layers pass. Disagreements are printed, because
a disagreement usually means the assertion is wrong rather than the agent.

This runs offline against a saved run directory, so re-scoring is cheap and does
not need a live worker.

    testing/.venv/bin/python testing/score.py recordings/20260726-123821_m2_tuning
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx

from persona_bot import load_env

TESTING_DIR = Path(__file__).resolve().parent
SCENARIOS_DIR = TESTING_DIR / "scenarios"

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "criterion": {"type": "string"},
                    "met": {"type": "boolean"},
                    "evidence": {"type": "string"},
                    "reasoning": {"type": "string"},
                },
                "required": ["criterion", "met", "evidence", "reasoning"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}

JUDGE_SYSTEM = """
You are grading one turn of a career-counselling voice agent that talks to Indian
students in Hindi, Marathi and code-mixed Hinglish.

You get the student's line, the agent's reply, and a list of criteria. For each
criterion say whether the agent met it.

Rules:
- Judge only the agent reply given. Do not assume anything happened off-transcript.
- Quote the agent verbatim in `evidence`. If nothing supports the criterion,
  set met to false and leave evidence empty.
- An empty or fragmentary agent reply meets nothing.
- Asking a question about a topic is NOT the same as explaining it.
- The reply comes from speech recognition, so ignore transcription noise and
  judge intent. Devanagari numerals spelled out as words still count as numbers.
- For language criteria, judge the language the agent actually spoke in.
""".strip()


def judge_step(step: dict, reply: str, model: str) -> list[dict]:
    criteria = step.get("judge") or []
    if not criteria:
        return []

    payload = {
        "student_said": step["text"],
        "agent_replied": reply,
        "criteria": criteria,
    }
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "verdicts", "schema": VERDICT_SCHEMA, "strict": True},
            },
            "temperature": 0,
        },
        timeout=180,
    )
    response.raise_for_status()
    return json.loads(response.json()["choices"][0]["message"]["content"])["verdicts"]


def score_run(run_dir: Path, model: str) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    results = json.loads((run_dir / "readout.json").read_text(encoding="utf-8"))
    scenario_id = meta["persona_id"]
    scenario = json.loads(
        (SCENARIOS_DIR / f"{scenario_id}.json").read_text(encoding="utf-8")
    )
    steps = {step["n"]: step for step in scenario["steps"]}

    scored = []
    for result in results:
        step = steps.get(result["step"], {})
        verdicts = judge_step(step, result.get("agent_reply", ""), model)
        judge_pass = all(v["met"] for v in verdicts) if verdicts else None
        det_pass = result["passed"]

        scored.append(
            {
                "step": result["step"],
                "name": result["name"],
                "deterministic_pass": det_pass,
                "judge_pass": judge_pass,
                "combined_pass": det_pass and (judge_pass is not False),
                "disagreement": judge_pass is not None and judge_pass != det_pass,
                "deterministic_failures": result["failures"],
                "judge_verdicts": verdicts,
                "agent_reply": result.get("agent_reply", ""),
            }
        )

    return {"scenario": scenario_id, "title": scenario["title"], "steps": scored}


def render(report: dict) -> str:
    lines = [
        "",
        "=" * 76,
        f"COMBINED SCORE — {report['title']}",
        "=" * 76,
        f"{'':4}{'step':<34}{'assert':<10}{'judge':<10}{'combined'}",
        "-" * 76,
    ]

    def mark(value: bool | None) -> str:
        if value is None:
            return "n/a"
        return "PASS" if value else "FAIL"

    for step in report["steps"]:
        lines.append(
            f"{step['step']:<4}{step['name'][:32]:<34}"
            f"{mark(step['deterministic_pass']):<10}"
            f"{mark(step['judge_pass']):<10}"
            f"{mark(step['combined_pass'])}"
        )

    disagreements = [s for s in report["steps"] if s["disagreement"]]
    if disagreements:
        lines.append("\nDISAGREEMENTS — usually the assertion is wrong, not the agent")
        for step in disagreements:
            side = "assertion passed, judge failed" if step["deterministic_pass"] else (
                "assertion failed, judge passed"
            )
            lines.append(f"  step {step['step']} ({step['name']}): {side}")
            for verdict in step["judge_verdicts"]:
                if not verdict["met"]:
                    lines.append(f"      judge: {verdict['criterion']}")
                    detail = verdict["evidence"] or verdict["reasoning"]
                    lines.append(f"             {detail[:130]}")

    lines.append("\nJUDGE DETAIL")
    for step in report["steps"]:
        failed = [v for v in step["judge_verdicts"] if not v["met"]]
        if not failed:
            continue
        lines.append(f"  step {step['step']}: {step['name']}")
        for verdict in failed:
            lines.append(f"    - {verdict['criterion']}")
            lines.append(f"      {(verdict['reasoning'] or '')[:140]}")

    combined = sum(1 for s in report["steps"] if s["combined_pass"])
    det = sum(1 for s in report["steps"] if s["deterministic_pass"])
    total = len(report["steps"])
    lines.append("\n" + "-" * 76)
    lines.append(f"assertions only: {det}/{total}    combined: {combined}/{total}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a run with assertions + LLM judge.")
    parser.add_argument("run_dirs", nargs="+", help="one or more recordings/<run> directories")
    parser.add_argument("--model", default=os.environ.get("JUDGE_MODEL", "gpt-4.1"))
    args = parser.parse_args()

    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY not found; the judge needs it")

    grand_combined = grand_total = 0
    for raw in args.run_dirs:
        run_dir = Path(raw).resolve()
        report = score_run(run_dir, args.model)
        output = render(report)
        (run_dir / "score.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (run_dir / "score.txt").write_text(output, encoding="utf-8")
        print(output)
        grand_combined += sum(1 for s in report["steps"] if s["combined_pass"])
        grand_total += len(report["steps"])

    if len(args.run_dirs) > 1:
        print("\n" + "=" * 76)
        print(f"ALL SCENARIOS — combined {grand_combined}/{grand_total}")


if __name__ == "__main__":
    main()
