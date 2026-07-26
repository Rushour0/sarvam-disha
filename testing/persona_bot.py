"""Persona bot: joins a LiveKit room as the student and records the call.

The bot never imports anything from agent/. It talks to the Disha worker the
same way a real caller would: over a LiveKit room.

Per turn it
  1. listens to the agent's audio until the agent goes quiet,
  2. transcribes that turn with Sarvam Saaras,
  3. asks the persona LLM what the student says next,
  4. speaks that line with Sarvam Bulbul and publishes it to the room.

Everything is written to testing/recordings/<run_id>/.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from livekit import api, rtc

import audio_impairments
import sarvam_client

TESTING_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTING_DIR.parent
PERSONA_BANK = REPO_ROOT / "personas" / "personas.json"
RECORDINGS_DIR = TESTING_DIR / "recordings"

MIX_RATE = 48_000
FRAME_MS = 20
SILENCE_RMS = 350.0
TURN_END_SILENCE_S = 1.6
AGENT_TURN_TIMEOUT_S = 45.0

LANG_TO_TTS = {
    "hi": "hi-IN",
    "mr": "mr-IN",
    "en": "en-IN",
    "hi_en_codemix": "hi-IN",
}


# --------------------------------------------------------------------------- env


def load_env() -> None:
    """Load repo env files, then pull the OpenAI key from wherever it lives.

    The key is read at runtime and never copied into this repo.
    """
    for name in (".env", ".env.local"):
        path = REPO_ROOT / name
        if path.exists():
            _merge_env_file(path, override=name == ".env.local")

    if not os.environ.get("OPENAI_API_KEY"):
        external = Path(
            os.environ.get("OPENAI_ENV_FILE", "~/gba/fabri/.env")
        ).expanduser()
        if external.exists():
            _merge_env_file(external, override=False, only={"OPENAI_API_KEY"})


def _merge_env_file(
    path: Path, *, override: bool, only: set[str] | None = None
) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if only is not None and key not in only:
            continue
        if override or key not in os.environ:
            os.environ[key] = value.strip().strip("'\"")


# ------------------------------------------------------------------- persona LLM


def load_persona(persona_id: str) -> dict:
    bank = json.loads(PERSONA_BANK.read_text(encoding="utf-8"))
    for persona in bank["personas"]:
        if persona["id"] == persona_id:
            return persona
    known = ", ".join(p["id"] for p in bank["personas"])
    raise SystemExit(f"unknown persona {persona_id!r}. known: {known}")


def persona_system_prompt(persona: dict) -> str:
    mix = ", ".join(f"{k} {int(v * 100)}%" for k, v in persona["lang"].items())
    return f"""
You are role-playing a student calling a career helpline. You are NOT an assistant.
Never counsel, never list options, never break character, never mention being an AI.

You are {persona["name"]}, age {persona["age"]}, from {persona["city"]}.
Stage: {persona["stage"]}. Marks: {persona.get("marks", "not stated")}.
Background you are living, not reciting: {persona["hidden_context"]}

Speak the way this student speaks. Language mix: {mix}. Use Roman script.
Code-switch mid-sentence the way a real Indian teenager does.

Hard rules:
- 1 to 2 short sentences per turn. Never a paragraph.
- Answer only what was asked. Do not volunteer your hidden background unless the
  counsellor asks a question that draws it out naturally.
- If you do not understand, say so the way this student would, or agree politely
  without understanding if that is in character.
- Never solve your own problem. You are confused; that is the point.
- Output only the spoken line. No stage directions, no quotes, no labels.
""".strip()


def persona_reply(persona: dict, history: list[dict[str, str]]) -> str:
    messages = [{"role": "system", "content": persona_system_prompt(persona)}, *history]
    if os.environ.get("OPENAI_API_KEY"):
        return _openai_reply(messages)
    return sarvam_client.chat(messages, max_tokens=120)


def _openai_reply(messages: list[dict[str, str]]) -> str:
    import httpx

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        json={
            "model": os.environ.get("PERSONA_MODEL", "gpt-4.1-mini"),
            "messages": messages,
            "max_tokens": 120,
            "temperature": 0.9,
        },
        timeout=90,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


# ------------------------------------------------------------------------- audio


def resample(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    if source_rate == target_rate or samples.size == 0:
        return samples.astype(np.int16)
    duration = samples.size / source_rate
    target_count = max(1, int(duration * target_rate))
    source_x = np.linspace(0.0, duration, samples.size, endpoint=False)
    target_x = np.linspace(0.0, duration, target_count, endpoint=False)
    return np.interp(target_x, source_x, samples.astype(np.float32)).astype(np.int16)


class Timeline:
    """A growable mono buffer that samples are written into by wall-clock offset."""

    def __init__(self, rate: int = MIX_RATE) -> None:
        self.rate = rate
        self._buffer = np.zeros(rate * 30, dtype=np.int32)
        self._end = 0

    def write_at(self, offset_s: float, samples: np.ndarray) -> None:
        start = max(0, int(offset_s * self.rate))
        stop = start + samples.size
        if stop > self._buffer.size:
            grow = np.zeros(max(stop - self._buffer.size, self.rate * 30), dtype=np.int32)
            self._buffer = np.concatenate([self._buffer, grow])
        self._buffer[start:stop] += samples.astype(np.int32)
        self._end = max(self._end, stop)

    def to_int16(self, length: int | None = None) -> np.ndarray:
        end = self._end if length is None else max(self._end, length)
        return np.clip(self._buffer[:end], -32768, 32767).astype(np.int16)


def write_wav(path: Path, channels: list[np.ndarray], rate: int = MIX_RATE) -> None:
    length = max((c.size for c in channels), default=0)
    padded = [np.pad(c, (0, length - c.size)) for c in channels]
    interleaved = np.stack(padded, axis=-1).reshape(-1) if len(padded) > 1 else padded[0]
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(len(padded))
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(interleaved.astype(np.int16).tobytes())


# --------------------------------------------------------------------------- run


class CallRunner:
    def __init__(
        self,
        persona: dict,
        max_turns: int,
        run_dir: Path,
        interrupt_turns: set[int] | None = None,
        impairments: dict | None = None,
    ) -> None:
        self.persona = persona
        self.max_turns = max_turns
        self.run_dir = run_dir
        self.interrupt_turns = interrupt_turns or set()
        self.impairments = impairments or {}
        self.barge_in_results: list[dict[str, object]] = []

        self.started = time.monotonic()
        self.agent_timeline = Timeline()
        self.student_timeline = Timeline()

        self.agent_chunks: list[np.ndarray] = []
        self.agent_speaking = False
        self.last_voice_at = 0.0
        self.agent_audio_seen = False

        self.transcript: list[dict[str, object]] = []
        self.events: list[dict] = []
        self.finished = asyncio.Event()

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started

    # -- capture ----------------------------------------------------------------

    async def consume_agent_track(self, track: rtc.Track) -> None:
        stream = rtc.AudioStream(track)
        async for event in stream:
            frame = event.frame
            samples = np.frombuffer(frame.data, dtype=np.int16)
            if frame.num_channels > 1:
                samples = samples.reshape(-1, frame.num_channels)[:, 0]
            at = self.elapsed
            self.agent_timeline.write_at(at, resample(samples, frame.sample_rate, MIX_RATE))

            rms = float(np.sqrt(np.mean(samples.astype(np.float32) ** 2))) if samples.size else 0.0
            if rms > SILENCE_RMS:
                self.agent_audio_seen = True
                self.agent_speaking = True
                self.last_voice_at = at
                self.agent_chunks.append(resample(samples, frame.sample_rate, 16_000))
            elif self.agent_speaking:
                self.agent_chunks.append(resample(samples, frame.sample_rate, 16_000))

    def on_data(self, packet: rtc.DataPacket) -> None:
        if packet.topic != "disha":
            return
        with contextlib.suppress(Exception):
            event = json.loads(packet.data.decode())
            event["at_s"] = round(self.elapsed, 2)
            self.events.append(event)
            print(f"  [event] {event.get('type')}")
            if event.get("type") == "summary":
                self.finished.set()

    # -- turn taking ------------------------------------------------------------

    async def wait_until_agent_speaking(self, min_speech_s: float = 1.5) -> bool:
        """Block until the agent has been talking for a while. Used to cut in."""
        deadline = self.elapsed + AGENT_TURN_TIMEOUT_S
        speech_started: float | None = None

        while self.elapsed < deadline:
            await asyncio.sleep(0.05)
            if self.agent_speaking and self.elapsed - self.last_voice_at < 0.4:
                speech_started = speech_started or self.elapsed
                if self.elapsed - speech_started >= min_speech_s:
                    return True
            else:
                speech_started = None
        return False

    async def measure_stop_latency(self, cut_in_at: float) -> float | None:
        """After cutting in, how long until the agent's audio actually stops.

        Returns seconds from the interruption to the agent's last voiced frame,
        or None if the agent was still talking when we gave up.
        """
        deadline = self.elapsed + 12.0
        while self.elapsed < deadline:
            await asyncio.sleep(0.05)
            if self.elapsed - self.last_voice_at > 0.8:
                return round(max(0.0, self.last_voice_at - cut_in_at), 2)
        return None

    async def wait_for_agent_turn(self) -> np.ndarray | None:
        """Block until the agent has spoken and then gone quiet."""
        deadline = self.elapsed + AGENT_TURN_TIMEOUT_S

        while self.elapsed < deadline:
            await asyncio.sleep(0.1)
            if self.finished.is_set():
                break
            if self.agent_speaking and self.elapsed - self.last_voice_at > TURN_END_SILENCE_S:
                break
        else:
            print("  [warn] agent turn timed out")

        if not self.agent_chunks:
            return None
        turn_audio = np.concatenate(self.agent_chunks)
        # Consume the buffer. Leaving it would make the next wait re-transcribe
        # this same audio and report it as a second, duplicate agent turn.
        self.agent_chunks.clear()
        self.agent_speaking = False
        return turn_audio

    async def speak(
        self,
        source: rtc.AudioSource,
        text: str,
        language: str,
        clip: tuple[np.ndarray, int] | None = None,
    ) -> None:
        samples, rate = clip or await asyncio.to_thread(sarvam_client.tts, text, language)

        # Degrade before publishing. The agent must hear what a student in a shop
        # or on a 2G handset actually sounds like, not studio TTS.
        if self.impairments:
            samples = audio_impairments.apply(samples, rate, self.impairments)

        # Drop anything the agent said before this line. Barge-in is enabled on
        # the agent, so its reply can start while we are still speaking; keeping
        # audio from here on is what makes that reply survive into the next turn.
        self.agent_chunks.clear()
        self.agent_speaking = False

        self.student_timeline.write_at(self.elapsed, resample(samples, rate, MIX_RATE))

        chunk = int(rate * FRAME_MS / 1000)
        for start in range(0, samples.size, chunk):
            block = samples[start : start + chunk]
            if block.size < chunk:
                block = np.pad(block, (0, chunk - block.size))
            await source.capture_frame(
                rtc.AudioFrame(
                    data=block.tobytes(),
                    sample_rate=rate,
                    num_channels=1,
                    samples_per_channel=chunk,
                )
            )

    # -- main loop --------------------------------------------------------------

    async def run(self, room: rtc.Room, source: rtc.AudioSource) -> None:
        language = LANG_TO_TTS.get(self.persona["primary_lang"], "hi-IN")
        history: list[dict[str, str]] = []

        for turn in range(1, self.max_turns + 1):
            cutting_in = turn in self.interrupt_turns

            if cutting_in:
                # Synthesise the line first. Cutting in only measures anything if
                # audio is ready to play the instant we decide to interrupt.
                line = (
                    self.persona["opening"]
                    if turn == 1
                    else await asyncio.to_thread(persona_reply, self.persona, history)
                )
                clip = await asyncio.to_thread(sarvam_client.tts, line, language)

                speaking = await self.wait_until_agent_speaking()
                agent_audio = np.concatenate(self.agent_chunks) if self.agent_chunks else None
                cut_in_at = self.elapsed
                print(f"  [barge-in] turn {turn}, agent mid-sentence={speaking}")

                play = asyncio.create_task(self.speak(source, line, language, clip=clip))
                latency = await self.measure_stop_latency(cut_in_at)
                await play
                # Discard the tail of the sentence we killed. It arrives after
                # speak() cleared the buffer and would otherwise be read as the
                # agent's reply to the interruption.
                self.agent_chunks.clear()
                self.agent_speaking = False

                print(f"  [barge-in] agent stopped after {latency}s" if latency is not None
                      else "  [barge-in] agent never stopped")
                self.barge_in_results.append(
                    {"turn": turn, "agent_was_speaking": speaking, "stop_latency_s": latency}
                )
            else:
                agent_audio = await self.wait_for_agent_turn()

            if agent_audio is not None and agent_audio.size:
                text, detected = await asyncio.to_thread(
                    sarvam_client.stt, agent_audio, 16_000
                )
                print(f"  agent [{detected}]: {text}")
                self.transcript.append(
                    {
                        "turn": turn,
                        "speaker": "agent",
                        "at_s": round(self.elapsed, 2),
                        "text": text,
                        "language": detected,
                    }
                )
                history.append({"role": "user", "content": text})

            if self.finished.is_set():
                break

            if not cutting_in:
                line = (
                    self.persona["opening"]
                    if turn == 1
                    else await asyncio.to_thread(persona_reply, self.persona, history)
                )

            print(f"  student: {line}")
            self.transcript.append(
                {
                    "turn": turn,
                    "speaker": "student",
                    "at_s": round(self.elapsed, 2),
                    "text": line,
                    "interrupted_agent": cutting_in,
                }
            )
            history.append({"role": "assistant", "content": line})

            if not cutting_in:
                await self.speak(source, line, language)

        # let any trailing agent audio land
        await asyncio.sleep(3.0)

    # -- output -----------------------------------------------------------------

    def save(self, room_name: str) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        agent = self.agent_timeline.to_int16()
        student = self.student_timeline.to_int16()

        write_wav(self.run_dir / "call.wav", [agent, student])
        write_wav(self.run_dir / "agent.wav", [agent])
        write_wav(self.run_dir / "student.wav", [student])

        (self.run_dir / "transcript.json").write_text(
            json.dumps(self.transcript, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.run_dir / "events.jsonl").write_text(
            "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in self.events),
            encoding="utf-8",
        )
        (self.run_dir / "meta.json").write_text(
            json.dumps(
                {
                    "persona_id": self.persona["id"],
                    "persona_name": self.persona["name"],
                    "room": room_name,
                    "started_utc": datetime.now(timezone.utc).isoformat(),
                    "duration_s": round(self.elapsed, 2),
                    "turns": len([t for t in self.transcript if t["speaker"] == "student"]),
                    "barge_in": self.barge_in_results,
                    "impairments": self.impairments,
                    "agent_languages": [
                        t.get("language")
                        for t in self.transcript
                        if t["speaker"] == "agent"
                    ],
                    "pass_criteria": self.persona["pass"],
                    "fail_tells": self.persona["fail"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def build_impairments(args: argparse.Namespace) -> dict:
    """Turn --noise/--snr/--telephony into an impairment spec."""
    spec: dict = {}
    if getattr(args, "noise", None):
        spec["noise"] = args.noise
        spec["snr_db"] = args.snr
    if getattr(args, "telephony", False):
        spec["telephony"] = True
        spec["bits"] = 8
    return spec


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run one persona call against Disha.")
    parser.add_argument("persona", help="persona id, e.g. p4_prachi")
    parser.add_argument("--turns", type=int, default=8)
    parser.add_argument("--agent-name", default="disha")
    parser.add_argument("--noise", help="noise kind: babble, shop, traffic, fan, wind, pink, white")
    parser.add_argument("--snr", type=float, default=15.0, help="signal-to-noise ratio in dB")
    parser.add_argument("--telephony", action="store_true", help="band-limit to 300-3400 Hz")
    parser.add_argument(
        "--interrupt-turns",
        default="",
        help="comma-separated turn numbers where the student talks over the agent, e.g. 2,4",
    )
    args = parser.parse_args()
    interrupt_turns = {
        int(part) for part in args.interrupt_turns.split(",") if part.strip()
    }
    impairments = build_impairments(args)

    load_env()
    persona = load_persona(args.persona)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    room_name = f"test-{persona['id'].replace('_', '-')}-{stamp}"
    run_dir = RECORDINGS_DIR / f"{stamp}_{persona['id']}"

    url = os.environ["LIVEKIT_URL"]
    key = os.environ["LIVEKIT_API_KEY"]
    secret = os.environ["LIVEKIT_API_SECRET"]

    print(f"persona: {persona['name']} ({persona['id']})")
    print(f"room:    {room_name}")
    print(f"audio:   {audio_impairments.describe(impairments)}")

    lkapi = api.LiveKitAPI(url=url, api_key=key, api_secret=secret)
    try:
        await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(agent_name=args.agent_name, room=room_name)
        )
        print(f"dispatched agent {args.agent_name!r}")
    finally:
        await lkapi.aclose()

    token = (
        api.AccessToken(key, secret)
        .with_identity("student")
        .with_name(persona["name"])
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )

    runner = CallRunner(persona, args.turns, run_dir, interrupt_turns, impairments)
    room = rtc.Room()
    tasks: list[asyncio.Task] = []

    @room.on("track_subscribed")
    def _on_track(track: rtc.Track, *_: object) -> None:
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print("  [rtc] agent audio track subscribed")
            tasks.append(asyncio.create_task(runner.consume_agent_track(track)))

    @room.on("data_received")
    def _on_data(packet: rtc.DataPacket) -> None:
        runner.on_data(packet)

    await room.connect(url, token)
    print("  [rtc] connected")

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

    print(f"\nrecordings: {run_dir}")
    for name in ("call.wav", "agent.wav", "student.wav", "transcript.json", "events.jsonl"):
        print(f"  {run_dir / name}")


if __name__ == "__main__":
    asyncio.run(main())
