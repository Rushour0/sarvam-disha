from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    NOT_GIVEN,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
)
from livekit.plugins import openai as openai_plugin
from livekit.plugins import sarvam, silero

try:
    from livekit.plugins import noise_cancellation
except ImportError:  # plugin is optional; the agent must still start without it
    noise_cancellation = None

import retrieval
from disha import Disha, EventSink, load_case_facts


REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(REPO_ROOT / ".env.local", override=True)


# How long the student must be silent before the agent treats their turn as over.
# Lowered to 0.3 earlier today for latency; that made the agent start talking over
# students who paused mid-sentence, which is common in code-mixed Hindi/Marathi.
# Back to the framework default. Costs ~200ms per turn; talking over a student in
# front of an audience costs more. Sweep 0.4-0.7 if it still cuts people off.
DISHA_ENDPOINT_MIN_DELAY = float(os.environ.get("DISHA_ENDPOINT_MIN_DELAY", "0.5"))  # Sweep: 0.4-0.7 s.
DISHA_ENDPOINT_MAX_DELAY = float(os.environ.get("DISHA_ENDPOINT_MAX_DELAY", "2.5"))  # Sweep: 1.5-3.0 s.
DISHA_PREEMPTIVE_TTS = os.environ.get("DISHA_PREEMPTIVE_TTS", "true").lower() in {"1", "true", "yes"}  # Sweep: on/off.
# Raised above the framework default (0.5) deliberately: the venue is noisy and
# babble was cutting the agent off mid-sentence. min_words is NOT a usable filter
# here — its gate reads the interim transcript, and Sarvam STT emits none, so any
# min_words > 0 defers barge-in to the final transcript. Duration is the only
# noise filter that works on this stack. Sweep 0.5-0.9 against babble/shop noise.
DISHA_INTERRUPT_MIN_DURATION = float(os.environ.get("DISHA_INTERRUPT_MIN_DURATION", "0.7"))  # Sweep: 0.5-0.9 s.
# Keep at 0. See the min_duration note above: raising this silently disables
# VAD-driven barge-in on Sarvam STT rather than merely filtering short ones.
DISHA_INTERRUPT_MIN_WORDS = int(os.environ.get("DISHA_INTERRUPT_MIN_WORDS", "0"))  # Keep 0 on Sarvam STT.
DISHA_TTS_MIN_BUFFER = int(os.environ.get("DISHA_TTS_MIN_BUFFER", "30"))  # Sweep: 30-100 chars.
DISHA_TTS_MAX_CHUNK = int(os.environ.get("DISHA_TTS_MAX_CHUNK", "150"))  # Sweep: 50-300 chars.
DISHA_TTS_SPEAKER = os.environ.get("DISHA_TTS_SPEAKER", "pooja")  # bulbul:v3 female voice.


def build_llm():
    """DISHA_LLM controls the brain: "openai/<model>" uses the OpenAI key from
    .env; any other string is passed to LiveKit Inference as-is."""
    choice = os.environ.get("DISHA_LLM", "openai/gpt-4.1-mini")
    if choice.startswith("openai/") and os.environ.get("OPENAI_API_KEY"):
        return openai_plugin.LLM(model=choice.removeprefix("openai/"))
    return choice


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


server = AgentServer(setup_fnc=prewarm)


LANGS = {
    "hi": {
        "tts": "hi-IN",
        "line": "The student chose Hindi as the starting language. Begin in natural, simple Hindi, but students freely mix Hindi, Marathi and English — always mirror the exact mix the student uses, never force them back to one language.",
        "greet": (
            "Hindi mein ek chhota, garamjoshi bhara parichay do. Career ka naam "
            "liye bina poochho ki student aaj kis baat ko samajhne aaya hai. Sirf ek sawal."
        ),
    },
    "en": {
        "tts": "en-IN",
        "line": "The student chose English as the starting language. Begin in simple, warm Indian English, but students freely mix English with Hindi or Marathi — always mirror the exact mix the student uses, never force them back to one language.",
        "greet": (
            "Give a short, warm introduction in English. Without naming any career, "
            "ask what the student came to figure out today. One question only."
        ),
    },
    "mr": {
        "tts": "mr-IN",
        "line": "The student chose Marathi as the starting language. Begin in natural, simple Marathi, but students freely mix Marathi, Hindi and English — always mirror the exact mix the student uses, never force them back to one language.",
        "greet": (
            "Marathi madhye ek chhota, prem bharlela parichay dya. Career cha ullekha "
            "na karta vichara ki vidyarthi aaj kay samjun ghyayla aala aahe. Fakta ek prashna."
        ),
    },
    "ta": {
        "tts": "ta-IN",
        "line": "The student chose Tamil as the starting language. Begin in natural, simple Tamil, but students freely mix Tamil and English — always mirror the exact mix the student uses, never force them back to one language.",
        "greet": (
            "Give a short, warm introduction in simple Tamil. Without naming any career, "
            "ask what the student came to understand today. One question only."
        ),
    },
}


@server.rtc_session(agent_name="disha")
async def entrypoint(ctx: JobContext) -> None:
    participant = await ctx.wait_for_participant()
    attrs = participant.attributes or {}
    lang_code = attrs.get("disha.lang", "hi")
    lang = LANGS.get(lang_code, LANGS["hi"])

    # Case-keyed persistence: a returning device resumes its case instead of
    # starting a fresh room-keyed file.
    case_key = attrs.get("disha.case", "") or ctx.job.room.name
    event_sink = EventSink(ctx.room, case_key)
    facts = load_case_facts(case_key)

    known_line = ""
    greet = lang["greet"]
    constraints = facts["constraints"]
    notes = facts["notes"]
    profile = facts["profile"]
    if constraints or notes or profile:
        parts = [
            f"{k}: {', '.join(v) if isinstance(v, list) else v}"
            for k, v in profile.items()
        ]
        parts += [f"{k}: {v}" for k, v in constraints.items()]
        parts += list(notes)
        known_line = (
            "Returning student. Personal memory already saved — do NOT re-ask "
            "these, build on them: " + "; ".join(parts)
        )
        greet = (
            "The student has spoken with you before. In their chosen starting "
            "language, greet them back warmly by name if you know it, in one "
            "short sentence, mention "
            "ONE thing you remember about their situation, and ask what has "
            "changed or what they want to continue with. One question only."
        )

    tts = sarvam.TTS(
        model="bulbul:v3",
        # Disha is a woman; bulbul:v3 defaults to the male voice "shubh" when
        # no speaker is given, so it must be named explicitly.
        speaker=DISHA_TTS_SPEAKER,
        target_language_code=lang["tts"],
        min_buffer_size=DISHA_TTS_MIN_BUFFER,
        max_chunk_length=DISHA_TTS_MAX_CHUNK,
    )
    # Prewarm per session so the connection is not shared across worker jobs.
    tts.prewarm()

    session = AgentSession(
        stt=sarvam.STT(model="saaras:v3", language="unknown"),
        llm=build_llm(),
        tts=tts,
        vad=ctx.proc.userdata["vad"],
        turn_handling={
            # Sarvam STT emits no interim transcripts, so keep VAD turn detection.
            "turn_detection": "vad",
            "endpointing": {
                "mode": "fixed",
                "min_delay": DISHA_ENDPOINT_MIN_DELAY,
                "max_delay": DISHA_ENDPOINT_MAX_DELAY,
            },
            "interruption": {
                "enabled": True,
                "min_duration": DISHA_INTERRUPT_MIN_DURATION,
                "min_words": DISHA_INTERRUPT_MIN_WORDS,
            },
            "preemptive_generation": {
                "enabled": True,
                "preemptive_tts": DISHA_PREEMPTIVE_TTS,
            },
        },
    )

    if os.environ.get("DISHA_LOG_METRICS"):
        from livekit.agents.metrics import log_metrics

        @session.on("metrics_collected")
        def _on_metrics_collected(ev) -> None:
            log_metrics(ev.metrics)

    language_line = lang["line"] if not known_line else f"{lang['line']}\n\n{known_line}"
    disha_agent = Disha(
        event_sink,
        language_line=language_line,
        case_id=case_key,
        profile=profile,
    )

    # Bulbul v3 output languages the TTS may follow the student into.
    followable = {"hi-IN", "en-IN", "mr-IN", "ta-IN", "bn-IN", "gu-IN", "kn-IN",
                  "ml-IN", "od-IN", "pa-IN", "te-IN"}
    lang_names = {
        "hi-IN": "Hindi", "en-IN": "Indian English", "mr-IN": "Marathi",
        "ta-IN": "Tamil", "bn-IN": "Bengali", "gu-IN": "Gujarati",
        "kn-IN": "Kannada", "ml-IN": "Malayalam", "od-IN": "Odia",
        "pa-IN": "Punjabi", "te-IN": "Telugu",
    }
    lang_state = {"current": lang["tts"], "pending": None, "first": True}

    async def _follow_language(code: str) -> None:
        # The reply language is decided by the LLM's text, not the TTS voice —
        # update both, or a Marathi student keeps getting Hindi sentences.
        session.tts.update_options(target_language_code=code)
        name = lang_names.get(code, code)
        directive = (
            f"LANGUAGE NOW: the student is speaking {name}. Write every reply "
            f"in {name} from this point, mirroring their exact mix. Do not "
            "return to your earlier language unless the student does."
        )
        # Routed through the agent so a language switch recomposes the prompt
        # instead of overwriting it — otherwise it would drop an active safety
        # lock set earlier in the session.
        await disha_agent.set_language_directive(directive)
        await event_sink.emit({"type": "language", "lang": code})

    @session.on("user_input_transcribed")
    def _on_transcribed(ev) -> None:
        if not ev.is_final or not ev.transcript:
            return
        detected = (ev.language or "").strip()
        asyncio.create_task(
            event_sink.emit(
                {"type": "utterance", "role": "student", "text": ev.transcript,
                 "lang": detected}
            )
        )
        retrieval.fire_and_forget(
            retrieval.remember_utterance(case_key, "student", ev.transcript, detected)
        )
        # Follow the student's language. The FIRST user turn switches
        # immediately (the chip was only a guess about how they'd open);
        # after that, two-turn hysteresis so a single misdetection
        # (e.g. gu-IN on Marathi audio) never flips the voice mid-call.
        first_turn = lang_state["first"]
        lang_state["first"] = False
        if detected in followable and detected != lang_state["current"]:
            if first_turn or lang_state["pending"] == detected:
                lang_state["current"] = detected
                lang_state["pending"] = None
                asyncio.create_task(_follow_language(detected))
            else:
                lang_state["pending"] = detected
        else:
            lang_state["pending"] = None

    @session.on("conversation_item_added")
    def _on_item(ev) -> None:
        item = ev.item
        if getattr(item, "role", None) == "assistant":
            text = getattr(item, "text_content", None) or ""
            if text:
                asyncio.create_task(
                    event_sink.emit(
                        {"type": "utterance", "role": "disha", "text": text,
                         "lang": lang_state["current"]}
                    )
                )
                retrieval.fire_and_forget(
                    retrieval.remember_utterance(
                        case_key, "disha", text, lang_state["current"]
                    )
                )

    signup_state = {"received": False}
    session_started = asyncio.Event()

    async def _begin_unlocked_test() -> None:
        await session_started.wait()
        session.generate_reply(
            instructions=(
                "SYSTEM NOTE: The student has just signed up. The spoken test is "
                "now unlocked. Begin the five-question round now, asking exactly "
                "one short question per turn."
            )
        )

    @ctx.room.on("data_received")
    def _on_data_received(packet: rtc.DataPacket) -> None:
        try:
            if packet.topic != "disha.client":
                return
            payload = json.loads(packet.data)
        except (AttributeError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return

        if (
            not isinstance(payload, dict)
            or payload.get("type") != "signup"
            or signup_state["received"]
        ):
            return

        signup_state["received"] = True
        asyncio.create_task(_begin_unlocked_test())

    # Background Voice Cancellation. Browser noiseSuppression only removes
    # stationary noise (fan, hum); it cannot remove other people talking, and
    # babble in the speech band is what was falsely triggering barge-in and
    # cutting the agent off mid-sentence. BVC is a per-frame filter on the
    # inbound audio, so its cost is constant and does not grow with utterance
    # length. Set DISHA_BVC=0 to fall back to browser-only suppression.
    room_options = NOT_GIVEN
    if noise_cancellation is not None and os.environ.get("DISHA_BVC", "1") != "0":
        room_options = room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        )

    await session.start(
        room=ctx.room,
        agent=disha_agent,
        room_options=room_options,
    )
    session_started.set()
    if not signup_state["received"]:
        session.generate_reply(instructions=greet)


if __name__ == "__main__":
    cli.run_app(server)
