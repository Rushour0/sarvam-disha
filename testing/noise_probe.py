"""Measure how far audio can be degraded before ASR breaks — no agent needed.

A full scenario run costs a LiveKit room, a worker job, an LLM and several
minutes. That is a slow way to discover that 5 dB club noise is simply
unintelligible. This runs the cheap half of the loop offline:

    Bulbul speaks a line  ->  degrade it  ->  Saaras transcribes it

If Saaras cannot read the audio, the agent has no chance, and the conditions
are not worth a live run. If Saaras reads it perfectly and the agent still
fails, the problem is in the agent's VAD, endpointing or turn logic rather than
in the audio.

That separation is the point. Without it, a failed noisy call has three possible
causes and no way to tell them apart.

    testing/.venv/bin/python testing/noise_probe.py --noise club --levels 20,15,10,5
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import numpy as np

import audio_impairments
import sarvam_client
from persona_bot import load_env

RECORDINGS_DIR = Path(__file__).resolve().parent / "recordings"

PROBE_LINES = [
    ("hi-IN", "Mera barvi ho gaya hai, ab mujhe samajh nahi aa raha aage kya karu"),
    ("hi-IN", "Ghar se zyada door nahi ja sakta aur fees bhi zyada nahi de sakte"),
    ("mr-IN", "Mala thoda margdarshan hava hota, mi ata baravi zali aahe"),
]


def _normalise(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"\w+", text, flags=re.UNICODE)


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Levenshtein distance over words, divided by reference length."""
    ref, hyp = _normalise(reference), _normalise(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0

    previous = list(range(len(hyp) + 1))
    for i, ref_word in enumerate(ref, start=1):
        current = [i]
        for j, hyp_word in enumerate(hyp, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (ref_word != hyp_word),
                )
            )
        previous = current
    return previous[-1] / len(ref)


def probe_level(spec: dict, label: str) -> dict:
    """Run every probe line through one impairment spec."""
    rates: list[float] = []
    samples_out = []

    for language, line in PROBE_LINES:
        clean, rate = sarvam_client.tts(line, language)
        clean_text, _ = sarvam_client.stt(clean, rate)

        degraded = audio_impairments.apply(clean, rate, spec)
        degraded_text, detected = sarvam_client.stt(degraded, rate)

        # Score against what Saaras heard in the clean case, not the written
        # line. TTS and ASR both have their own quirks and this isolates the
        # damage done by the impairment rather than the round trip.
        rate_value = word_error_rate(clean_text, degraded_text)
        rates.append(rate_value)
        samples_out.append(
            {
                "language": language,
                "clean": clean_text,
                "degraded": degraded_text,
                "detected": detected,
                "wer": round(rate_value, 3),
            }
        )
        print(f"  [{language}] WER {rate_value:.0%}  {degraded_text[:70]}")

    mean = float(np.mean(rates)) if rates else 1.0
    print(f"  {label}: mean WER {mean:.0%}")
    return {"label": label, "spec": spec, "mean_wer": round(mean, 3), "lines": samples_out}


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline ASR degradation probe.")
    parser.add_argument("--noise", default="club")
    parser.add_argument("--levels", default="25,20,15,10,5")
    parser.add_argument("--telephony", action="store_true")
    parser.add_argument("--reverb", type=float, default=0.0, help="rt60 in seconds")
    args = parser.parse_args()

    load_env()
    levels = [int(part) for part in args.levels.split(",") if part.strip()]

    results = [probe_level({}, "clean")]
    for snr in levels:
        spec: dict = {"noise": args.noise, "snr_db": snr, "seed": 5}
        if args.telephony:
            spec["telephony"] = True
            spec["bits"] = 8
        if args.reverb:
            spec["reverb"] = {"rt60": args.reverb, "wet": 0.45}
        print(f"\n=== {args.noise} @ {snr} dB")
        results.append(probe_level(spec, f"{args.noise}@{snr}dB"))

    print("\n" + "=" * 58)
    print(f"ASR DEGRADATION — {args.noise}")
    print("=" * 58)
    print(f"{'condition':<24}{'mean WER':<12}verdict")
    print("-" * 58)
    for row in results:
        wer = row["mean_wer"]
        if wer <= 0.15:
            verdict = "usable"
        elif wer <= 0.40:
            verdict = "degraded"
        else:
            verdict = "unintelligible"
        print(f"{row['label']:<24}{wer:<12.0%}{verdict}")

    usable = [r for r in results if r["mean_wer"] <= 0.15 and r["label"] != "clean"]
    if usable:
        floor = min(int(r["label"].split("@")[1].rstrip("dB")) for r in usable)
        print(f"\nASR still usable down to: {floor} dB SNR")
        print("Below that, a failed call is an audio problem, not an agent problem.")
    else:
        print("\nNo tested level kept ASR usable.")

    output = RECORDINGS_DIR / f"probe_{args.noise}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
