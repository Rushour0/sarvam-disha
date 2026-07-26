"""Find the SNR at which the agent stops working.

A single noisy run tells you the agent failed. It does not tell you where the
cliff is, and "works in noise" is not a yes/no property — every voice stack has
an SNR below which VAD, ASR or endpointing collapses. What matters is whether
that cliff sits above or below the conditions your users actually call from.

Rough reference points for the levels swept here:

    30 dB   quiet room
    20 dB   home with a fan
    15 dB   busy household, TV on
    10 dB   shop, roadside, people talking nearby
     5 dB   loud street, market
     0 dB   noise as loud as the speaker

Runs the same scenario at each level and reports where the score falls off.

    testing/.venv/bin/python testing/noise_sweep.py m2_tuning --noise shop
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PYTHON = TESTING_DIR / ".venv" / "bin" / "python"
RUNNER = TESTING_DIR / "scenario_runner.py"
RECORDINGS_DIR = TESTING_DIR / "recordings"

DEFAULT_LEVELS = [30, 20, 15, 10, 5]


def run_level(scenario: str, noise: str, snr: int, telephony: bool) -> dict:
    command = [str(PYTHON), str(RUNNER), scenario, "--noise", noise, "--snr", str(snr)]
    if telephony:
        command.append("--telephony")

    print(f"\n=== {noise} @ {snr} dB SNR{' + telephony' if telephony else ''}")
    process = subprocess.run(
        command, cwd=str(TESTING_DIR), capture_output=True, text=True
    )
    if process.returncode != 0:
        print(f"  run failed (exit {process.returncode})")
        for line in process.stdout.strip().splitlines()[-6:]:
            print(f"    {line}")

    runs = sorted(RECORDINGS_DIR.glob(f"*_{scenario}_{noise}{snr}"))
    if not runs:
        return {"snr": snr, "passed": None, "total": None, "run_dir": None}

    run_dir = runs[-1]
    results = json.loads((run_dir / "readout.json").read_text(encoding="utf-8"))
    transcript = json.loads((run_dir / "transcript.json").read_text(encoding="utf-8"))
    agent_turns = [t for t in transcript if t["speaker"] == "agent"]
    empty = sum(1 for t in agent_turns if not t["text"].strip())

    passed = sum(1 for r in results if r["passed"])
    print(f"  {passed}/{len(results)} steps, agent turns: {len(agent_turns)}, empty: {empty}")

    return {
        "snr": snr,
        "passed": passed,
        "total": len(results),
        "agent_turns": len(agent_turns),
        "empty_replies": empty,
        "run_dir": str(run_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep SNR to find the agent's noise floor.")
    parser.add_argument("scenario")
    parser.add_argument("--noise", default="shop")
    parser.add_argument(
        "--levels",
        default=",".join(str(level) for level in DEFAULT_LEVELS),
        help="comma-separated SNR values in dB, loudest speech first",
    )
    parser.add_argument("--telephony", action="store_true")
    args = parser.parse_args()

    levels = [int(part) for part in args.levels.split(",") if part.strip()]
    rows = [run_level(args.scenario, args.noise, snr, args.telephony) for snr in levels]

    print("\n" + "=" * 60)
    print(f"NOISE SWEEP — {args.scenario}, {args.noise}")
    print("=" * 60)
    print(f"{'SNR':<8}{'score':<10}{'agent turns':<14}{'empty'}")
    print("-" * 60)
    for row in rows:
        if row["passed"] is None:
            print(f"{row['snr']:<8}{'no run':<10}")
            continue
        score = f"{row['passed']}/{row['total']}"
        print(f"{row['snr']:<8}{score:<10}{row['agent_turns']:<14}{row['empty_replies']}")

    scored = [r for r in rows if r["passed"] is not None]
    clean = [r for r in scored if r["passed"] == r["total"]]
    if clean:
        print(f"\nlowest fully-passing SNR: {min(r['snr'] for r in clean)} dB")
    else:
        print("\nno level passed fully")

    broken = [r for r in scored if r["empty_replies"] or r["agent_turns"] < r["total"]]
    if broken:
        worst = max(r["snr"] for r in broken)
        print(f"agent starts dropping turns at or below: {worst} dB")

    output = RECORDINGS_DIR / f"sweep_{args.scenario}_{args.noise}.json"
    output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nsaved: {output}")


if __name__ == "__main__":
    main()
