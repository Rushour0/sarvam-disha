"""Run a scripted scenario against Disha and print a pass/fail readout.

Unlike persona_bot.py, the student's lines are fixed. That is the point: a
scripted probe is reproducible, so a change to the agent's prompt shows up as a
change in the readout rather than as a differently-worded conversation.

    testing/.venv/bin/python testing/scenario_runner.py m2_tuning
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from livekit import api, rtc

import sarvam_client
import audio_impairments
from persona_bot import (
    RECORDINGS_DIR,
    TESTING_DIR,
    CallRunner,
    build_impairments,
    load_env,
)

SCENARIOS_DIR = TESTING_DIR / "scenarios"


def load_scenario(scenario_id: str) -> dict:
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.exists():
        known = ", ".join(p.stem for p in SCENARIOS_DIR.glob("*.json"))
        raise SystemExit(f"unknown scenario {scenario_id!r}. known: {known}")
    return json.loads(path.read_text(encoding="utf-8"))


class ScenarioRunner(CallRunner):
    """CallRunner with fixed lines and per-step expectation checks."""

    def __init__(
        self, scenario: dict, run_dir: Path, impairments: dict | None = None
    ) -> None:
        steps = scenario["steps"]
        interrupts = {step["n"] for step in steps if step.get("interrupt")}
        fake_persona = {
            "id": scenario["id"],
            "name": scenario["title"],
            "opening": steps[0]["text"],
            "pass": [f"step {s['n']}: {s['name']}" for s in steps],
            "fail": [],
        }
        super().__init__(
            fake_persona,
            len(steps),
            run_dir,
            interrupts,
            impairments or scenario.get("impairments"),
        )
        self.scenario = scenario
        self.results: list[dict[str, object]] = []

    def discard_interrupted_tail(
        self, tail_chunk_count: int, tail_last_voice_at: float
    ) -> None:
        """Remove audio from the just-interrupted agent turn.

        ``measure_stop_latency()`` has observed 0.8 seconds of silence when this
        is called, so chunks present at that point are only the interrupted turn's
        tail. A genuine reply can still start while the student's clip finishes;
        retain only chunks that arrived after that boundary in that case.
        """
        if self.last_voice_at > tail_last_voice_at:
            del self.agent_chunks[:tail_chunk_count]
            return

        self.agent_chunks.clear()
        self.agent_speaking = False

    async def run(self, room: rtc.Room, source: rtc.AudioSource) -> None:
        for step in self.scenario["steps"]:
            number = step["n"]
            language = step.get("language", "hi-IN")
            print(f"\n[step {number}] {step['name']}")

            events_before = len(self.events)

            if step.get("interrupt"):
                clip = await asyncio.to_thread(
                    sarvam_client.tts, step["text"], language
                )
                speaking = await self.wait_until_agent_speaking()
                agent_audio = (
                    np.concatenate(self.agent_chunks) if self.agent_chunks else None
                )
                cut_in_at = self.elapsed
                play = asyncio.create_task(
                    self.speak(source, step["text"], language, clip=clip)
                )
                latency = await self.measure_stop_latency(cut_in_at)
                tail_chunk_count = len(self.agent_chunks)
                tail_last_voice_at = self.last_voice_at
                await play
                # speak() cleared the buffer before the cut-in, but the agent
                # keeps talking through the 1.0-1.8s stop-latency window and that
                # dying audio lands in the buffer afterwards. Without this second
                # clear, wait_for_agent_turn returns the tail of the killed
                # sentence as "the reply" and every later reply is attributed to
                # the wrong step. Preserve only a genuine reply that began after
                # measure_stop_latency() established the stopped-audio boundary.
                self.discard_interrupted_tail(tail_chunk_count, tail_last_voice_at)
                self.barge_in_results.append(
                    {"turn": number, "agent_was_speaking": speaking, "stop_latency_s": latency}
                )
                print(f"  agent was mid-sentence: {speaking}, stopped after: {latency}s")
            else:
                # Wait for the agent to finish whatever it is saying, then probe.
                # The audio it produced there belongs to the previous step and has
                # already been transcribed, so it is not read again here.
                await self.wait_for_agent_turn()
                await self.speak(source, step["text"], language)
                latency = None
                speaking = None

            print(f"  student says: {step['text']}")
            self.transcript.append(
                {
                    "turn": number,
                    "speaker": "student",
                    "at_s": round(self.elapsed, 2),
                    "text": step["text"],
                    "scripted": True,
                }
            )

            # Give the agent time to answer this step before the next probe.
            reply_audio = await self.wait_for_agent_turn()
            reply_text = ""
            detected = ""
            if reply_audio is not None and reply_audio.size:
                reply_text, detected = await asyncio.to_thread(
                    sarvam_client.stt, reply_audio, 16_000
                )
                print(f"  agent replies [{detected}]: {reply_text}")
                self.transcript.append(
                    {
                        "turn": number,
                        "speaker": "agent",
                        "at_s": round(self.elapsed, 2),
                        "text": reply_text,
                        "language": detected,
                        "is_reply_to_step": number,
                    }
                )

            self.results.append(
                self.check(
                    step, reply_text, self.events[events_before:], latency, detected
                )
            )

    @staticmethod
    def check(
        step: dict,
        reply: str,
        new_events: list[dict],
        latency: float | None,
        reply_language: str = "",
    ) -> dict[str, object]:
        expect = step.get("expect", {})
        failures: list[str] = []

        wanted_language = expect.get("reply_language")
        if wanted_language and not reply_language.startswith(wanted_language):
            failures.append(
                f"replied in {reply_language or 'nothing'}, expected {wanted_language}"
            )

        banned_type = expect.get("no_event_type")
        if banned_type:
            banned_types = (
                [banned_type] if isinstance(banned_type, str) else list(banned_type)
            )
            for name in banned_types:
                if any(e.get("type") == name for e in new_events):
                    failures.append(f"emitted a {name} event but should not have")

        banned = expect.get("reply_contains_none")
        if banned:
            hits = [n for n in banned if n.lower() in reply.lower()]
            if hits:
                failures.append(f"reply mentioned forbidden terms {hits}")

        limit = expect.get("barge_in_stop_latency_under_s")
        if limit is not None:
            if latency is None:
                failures.append("agent never stopped after the interruption")
            elif latency > limit:
                failures.append(f"stop latency {latency}s exceeded {limit}s")

        wanted_type = expect.get("event_type")
        if wanted_type:
            matching = [e for e in new_events if e.get("type") == wanted_type]
            if not matching:
                seen = sorted({str(e.get("type")) for e in new_events}) or ["none"]
                failures.append(
                    f"no {wanted_type} event; saw {', '.join(seen)}"
                )
            else:
                names = expect.get("any_of_names")
                if names and not any(e.get("name") in names for e in matching):
                    got = [str(e.get("name")) for e in matching]
                    failures.append(f"constraint name {got} not in {names}")

                flag_type = expect.get("flag_type")
                if flag_type and not any(
                    e.get("flag_type") == flag_type for e in matching
                ):
                    got = [str(e.get("flag_type")) for e in matching]
                    failures.append(f"flag_type {got} != {flag_type!r}")

        needles = expect.get("reply_contains_any")
        if needles and not any(n.lower() in reply.lower() for n in needles):
            failures.append(f"reply contained none of {needles}")

        return {
            "step": step["n"],
            "name": step["name"],
            "passed": not failures,
            "failures": failures,
            "agent_reply": reply,
            "events": new_events,
            "stop_latency_s": latency,
        }

    def readout(self) -> str:
        lines = [
            "",
            "=" * 68,
            f"READOUT — {self.scenario['title']}",
            "=" * 68,
        ]
        for result in self.results:
            mark = "PASS" if result["passed"] else "FAIL"
            lines.append(f"{mark}  step {result['step']}: {result['name']}")
            for failure in result["failures"]:
                lines.append(f"        -> {failure}")
        passed = sum(1 for r in self.results if r["passed"])
        lines.append("-" * 68)
        lines.append(f"{passed}/{len(self.results)} steps passed")
        return "\n".join(lines)

    def save(self, room_name: str) -> None:
        super().save(room_name)
        (self.run_dir / "readout.json").write_text(
            json.dumps(self.results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.run_dir / "readout.txt").write_text(self.readout(), encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run a scripted scenario against Disha.")
    parser.add_argument("scenario", help="scenario id, e.g. m2_tuning")
    parser.add_argument("--agent-name", default="disha")
    parser.add_argument("--noise", help="noise kind: babble, shop, traffic, fan, wind, pink, white")
    parser.add_argument("--snr", type=float, default=15.0, help="signal-to-noise ratio in dB")
    parser.add_argument("--telephony", action="store_true", help="band-limit to 300-3400 Hz")
    args = parser.parse_args()
    impairments = build_impairments(args)

    load_env()
    scenario = load_scenario(args.scenario)

    import os

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    room_name = f"scn-{scenario['id'].replace('_', '-')}-{stamp}"
    suffix = f"_{args.noise}{int(args.snr)}" if args.noise else ""
    run_dir = RECORDINGS_DIR / f"{stamp}_{scenario['id']}{suffix}"

    url = os.environ["LIVEKIT_URL"]
    key = os.environ["LIVEKIT_API_KEY"]
    secret = os.environ["LIVEKIT_API_SECRET"]

    print(f"scenario: {scenario['title']}")
    print(f"room:     {room_name}")
    print(f"audio:    {audio_impairments.describe(impairments or scenario.get('impairments'))}")

    lkapi = api.LiveKitAPI(url=url, api_key=key, api_secret=secret)
    try:
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(agent_name=args.agent_name, room=room_name)
        )
    finally:
        await lkapi.aclose()

    token = (
        api.AccessToken(key, secret)
        .with_identity("student")
        .with_name("Scenario student")
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )

    runner = ScenarioRunner(scenario, run_dir, impairments or None)
    room = rtc.Room()
    tasks: list[asyncio.Task] = []

    @room.on("track_subscribed")
    def _on_track(track: rtc.Track, *_: object) -> None:
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            tasks.append(asyncio.create_task(runner.consume_agent_track(track)))

    @room.on("data_received")
    def _on_data(packet: rtc.DataPacket) -> None:
        runner.on_data(packet)

    await room.connect(url, token)
    source = rtc.AudioSource(22_050, 1)
    track = rtc.LocalAudioTrack.create_audio_track("student-mic", source)
    await room.local_participant.publish_track(
        track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    )

    try:
        await runner.run(room, source)
    finally:
        for task in tasks:
            task.cancel()
        await room.disconnect()
        runner.save(room_name)

    print(runner.readout())
    print(f"\nrecording: {run_dir}")


if __name__ == "__main__":
    asyncio.run(main())
