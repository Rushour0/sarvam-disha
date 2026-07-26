"""Build real multi-speaker Indic babble with Bulbul, and cache it.

The synthetic babble in audio_impairments.py is amplitude-modulated filtered
noise. It has roughly the right spectrum and roughly the right syllable rate,
and it is fine as a control. It is not what defeats a speech system in the real
world.

What defeats a VAD is other people talking: real formants, real consonant
bursts, real pauses, in the same language as the target speaker. A VAD trained
to find speech finds it, because it is speech. Synthetic babble is a texture; a
crowd is a competitor.

Sarvam already ships 44 voices, so the crowd can be generated rather than
sourced. Each layer is a different speaker saying a different Hindi or Marathi
sentence, started at a random offset and mixed. The result is cached as .npy
because it costs one TTS call per speaker to build.

    testing/.venv/bin/python testing/babble_bed.py --speakers 8 --seconds 30
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import sarvam_client
from persona_bot import load_env

CACHE_DIR = Path(__file__).resolve().parent / "cache"

# Ordinary conversation, nothing career-related. If the babble said career words
# the agent's ASR could pick them up and the test would be measuring the wrong
# thing entirely.
BABBLE_LINES_HI = [
    "Arre suno, kal shaam ko market jaana hai kya, bahut bheed hoti hai",
    "Mummy ne bola tha ki dahi le aana, par main bhool gaya",
    "Yaar wo picture dekhi thi tumne, mujhe to bilkul samajh nahi aayi",
    "Kitne baje nikalna hai, train chhoot jayegi warna",
    "Paisa toh maine de diya tha usko, ab wo mana kar raha hai",
    "Barish itni tez aa rahi hai ki chhata bhi kaam nahi kar raha",
    "Chai peene chalein, saamne wali dukaan achhi hai",
]
BABBLE_LINES_MR = [
    "Aare aikalas ka, udya sakali lavkar nighaycha aahe amhala",
    "Tyala mi sangitla hota pan to aikat nahi kadhich",
    "Bhaji khup mahag zali aahe ya varshi, kay karnar",
    "Ghari pohochayla kiti vel lagel tula, saang na",
    "To manus roj ithe yeto ani tasach nighun jato",
]

SPEAKERS = [
    "anushka", "abhilash", "manisha", "vidya", "arya", "karun", "hitesh",
    "aditya", "ritu", "priya", "neha", "rahul", "pooja", "rohan", "simran",
    "kavya", "amit", "dev", "ishita", "shreya", "varun", "tanya", "tarun",
]


def _cache_key(speakers: int, seconds: float, language: str, seed: int) -> Path:
    raw = f"{speakers}|{seconds}|{language}|{seed}".encode()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    return CACHE_DIR / f"babble_{language}_{speakers}spk_{int(seconds)}s_{digest}.npy"


def build(
    speakers: int = 8,
    seconds: float = 30.0,
    language: str = "hi-IN",
    seed: int = 11,
    rate: int = 22_050,
) -> tuple[np.ndarray, int]:
    """Generate (or load) a babble bed. Returns (float64 in [-1, 1], rate)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_key(speakers, seconds, language, seed)
    if path.exists():
        return np.load(path), rate

    rng = np.random.default_rng(seed)
    lines = BABBLE_LINES_MR if language.startswith("mr") else BABBLE_LINES_HI
    total = int(seconds * rate)
    bed = np.zeros(total, dtype=np.float64)

    chosen = rng.choice(SPEAKERS, size=min(speakers, len(SPEAKERS)), replace=False)
    for index, speaker in enumerate(chosen):
        text = lines[index % len(lines)]
        try:
            samples, source_rate = sarvam_client.tts(text, language, speaker=str(speaker))
        except Exception as error:  # one bad voice should not kill the bed
            print(f"  skip {speaker}: {error}")
            continue

        voice = samples.astype(np.float64)
        peak = np.max(np.abs(voice))
        if peak:
            voice /= peak

        # Tile the voice across the bed at random offsets so speakers overlap
        # irregularly, the way a room does, instead of all starting together.
        position = int(rng.random() * rate)
        while position < total:
            end = min(total, position + voice.size)
            bed[position:end] += voice[: end - position] * rng.uniform(0.5, 1.0)
            position = end + int(rng.uniform(0.1, 1.2) * rate)

        print(f"  layered {speaker}: {voice.size / source_rate:.1f}s")

    peak = np.max(np.abs(bed))
    if peak:
        bed /= peak
    np.save(path, bed)
    print(f"cached: {path.name}")
    return bed, rate


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Bulbul babble bed.")
    parser.add_argument("--speakers", type=int, default=8)
    parser.add_argument("--seconds", type=float, default=30.0)
    parser.add_argument("--language", default="hi-IN")
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()

    load_env()
    bed, rate = build(args.speakers, args.seconds, args.language, args.seed)
    print(json.dumps({"samples": int(bed.size), "rate": rate, "seconds": bed.size / rate}))


if __name__ == "__main__":
    main()
