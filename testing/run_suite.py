"""Run several scenarios and print one combined readout.

Scenarios run strictly one at a time because they share one LiveKit worker.

    testing/.venv/bin/python testing/run_suite.py
    testing/.venv/bin/python testing/run_suite.py m2_tuning closed_list
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

TESTING_DIR = Path(__file__).resolve().parent
PYTHON = TESTING_DIR / ".venv" / "bin" / "python"
RUNNER = TESTING_DIR / "scenario_runner.py"
SCENARIOS_DIR = TESTING_DIR / "scenarios"
RECORDINGS_DIR = TESTING_DIR / "recordings"
# Give the LiveKit worker time to release the prior room before the next scenario.
SUITE_SETTLE_S = float(os.environ.get("SUITE_SETTLE_S", "5"))


def progress_marker(phase: str, scenario_id: str, detail: str = "") -> None:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    print(f"[{timestamp}] [{phase}] {scenario_id}{detail}", flush=True)


async def run_one(scenario_id: str) -> dict:
    process = None
    output = ""
    progress_marker("start", scenario_id)
    try:
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

        if process.returncode != 0:
            return {
                "scenario": scenario_id,
                "exit_code": process.returncode,
                "results": [],
                "run_dir": None,
                "output": output,
                "error": f"runner exited {process.returncode}",
            }

        newest = sorted(RECORDINGS_DIR.glob(f"*_{scenario_id}"))
        readout = newest[-1] / "readout.json" if newest else None
        if not readout or not readout.exists():
            return {
                "scenario": scenario_id,
                "exit_code": process.returncode,
                "results": [],
                "run_dir": str(newest[-1]) if newest else None,
                "output": output,
                "error": "runner completed without a readout",
            }

        results = json.loads(readout.read_text(encoding="utf-8"))
        return {
            "scenario": scenario_id,
            "exit_code": process.returncode,
            "results": results,
            "run_dir": str(newest[-1]) if newest else None,
            "output": output,
            "error": None,
        }
    except Exception as error:
        return {
            "scenario": scenario_id,
            "exit_code": process.returncode if process else None,
            "results": [],
            "run_dir": None,
            "output": output,
            "error": f"{type(error).__name__}: {error}",
        }
    finally:
        exit_detail = f" (exit {process.returncode})" if process else " (not started)"
        progress_marker("done ", scenario_id, exit_detail)


async def main() -> None:
    requested = sys.argv[1:] or sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))
    runs = []
    for index, name in enumerate(requested):
        runs.append(await run_one(name))
        if index < len(requested) - 1:
            await asyncio.sleep(SUITE_SETTLE_S)

    total_pass = total_steps = 0
    print("\n" + "=" * 72)
    print("SUITE READOUT")
    print("=" * 72)

    for run in runs:
        results = run["results"]
        if run["error"]:
            print(f"\n{run['scenario']}: ERROR ({run['error']}; exit {run['exit_code']})")
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
