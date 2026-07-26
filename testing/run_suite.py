"""Run several scenarios and print one combined readout.

Scenarios run with limited concurrency because each one occupies a LiveKit room
and a worker job process. Two at a time keeps the suite quick without starving
the worker.

    testing/.venv/bin/python testing/run_suite.py
    testing/.venv/bin/python testing/run_suite.py m2_tuning closed_list
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PYTHON = TESTING_DIR / ".venv" / "bin" / "python"
RUNNER = TESTING_DIR / "scenario_runner.py"
SCENARIOS_DIR = TESTING_DIR / "scenarios"
RECORDINGS_DIR = TESTING_DIR / "recordings"
CONCURRENCY = 2


async def run_one(scenario_id: str, slot: asyncio.Semaphore) -> dict:
    async with slot:
        print(f"[start] {scenario_id}")
        process = await asyncio.create_subprocess_exec(
            str(PYTHON),
            str(RUNNER),
            scenario_id,
            cwd=str(TESTING_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        output = stdout.decode(errors="replace")
        print(f"[done ] {scenario_id} (exit {process.returncode})")

        newest = sorted(RECORDINGS_DIR.glob(f"*_{scenario_id}"))
        readout = newest[-1] / "readout.json" if newest else None
        results = (
            json.loads(readout.read_text(encoding="utf-8"))
            if readout and readout.exists()
            else []
        )
        return {
            "scenario": scenario_id,
            "exit_code": process.returncode,
            "results": results,
            "run_dir": str(newest[-1]) if newest else None,
            "output": output,
        }


async def main() -> None:
    requested = sys.argv[1:] or sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))
    slot = asyncio.Semaphore(CONCURRENCY)
    runs = await asyncio.gather(*(run_one(name, slot) for name in requested))

    total_pass = total_steps = 0
    print("\n" + "=" * 72)
    print("SUITE READOUT")
    print("=" * 72)

    for run in runs:
        results = run["results"]
        if not results:
            print(f"\n{run['scenario']}: NO READOUT (exit {run['exit_code']})")
            print("  last output:")
            for line in run["output"].strip().splitlines()[-8:]:
                print(f"    {line}")
            continue

        passed = sum(1 for r in results if r["passed"])
        total_pass += passed
        total_steps += len(results)
        print(f"\n{run['scenario']}: {passed}/{len(results)}")
        for result in results:
            mark = "PASS" if result["passed"] else "FAIL"
            print(f"  {mark}  {result['step']}. {result['name']}")
            for failure in result["failures"]:
                print(f"          -> {failure}")

    print("\n" + "-" * 72)
    print(f"TOTAL {total_pass}/{total_steps} steps passed")
    for run in runs:
        if run["run_dir"]:
            print(f"  {run['scenario']}: {run['run_dir']}")


if __name__ == "__main__":
    asyncio.run(main())
