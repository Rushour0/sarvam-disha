"""Thin REST wrappers for the three Sarvam endpoints the persona bot needs.

Deliberately synchronous and dependency-light. Each call is run off the event
loop with asyncio.to_thread by the caller.
"""

from __future__ import annotations

import base64
import io
import os
import wave

import httpx
import numpy as np

API_ROOT = "https://api.sarvam.ai"
TTS_MODEL = "bulbul:v3"
STT_MODEL = "saaras:v3"
LLM_MODEL = "sarvam-105b"


def _headers() -> dict[str, str]:
    key = os.environ.get("SARVAM_API_KEY")
    if not key:
        raise RuntimeError("SARVAM_API_KEY is not set")
    return {"api-subscription-key": key}


def tts(text: str, language: str, speaker: str | None = None) -> tuple[np.ndarray, int]:
    """Synthesise speech. Returns (int16 mono samples, sample_rate)."""
    body: dict[str, object] = {
        "text": text,
        "target_language_code": language,
        "model": TTS_MODEL,
    }
    if speaker:
        body["speaker"] = speaker

    response = httpx.post(
        f"{API_ROOT}/text-to-speech", headers=_headers(), json=body, timeout=90
    )
    response.raise_for_status()
    audio_bytes = base64.b64decode(response.json()["audios"][0])

    with wave.open(io.BytesIO(audio_bytes)) as wav:
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    return np.frombuffer(frames, dtype=np.int16), rate


def stt(samples: np.ndarray, sample_rate: int) -> tuple[str, str]:
    """Transcribe int16 mono audio. Returns (transcript, detected language)."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.astype(np.int16).tobytes())
    buffer.seek(0)

    response = httpx.post(
        f"{API_ROOT}/speech-to-text",
        headers=_headers(),
        files={"file": ("turn.wav", buffer, "audio/wav")},
        data={"model": STT_MODEL, "language_code": "unknown"},
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("transcript", ""), payload.get("language_code", "unknown")


def chat(messages: list[dict[str, str]], max_tokens: int = 160) -> str:
    """One completion from the Sarvam LLM, used as the persona's brain."""
    response = httpx.post(
        f"{API_ROOT}/v1/chat/completions",
        headers={**_headers(), "Content-Type": "application/json"},
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.8,
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()
