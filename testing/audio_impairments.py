"""Degrade student audio the way a real call degrades it.

Bulbul returns clean 22 kHz studio speech. Nothing a student actually calls from
sounds like that: they are in a shop, on a road, on a 2G handset, behind a fan.
Testing only with clean audio measures the agent's behaviour in a room it will
never be in.

Everything here is generated, so there are no fixture files to ship and the
impairments are reproducible from a seed.

Ordering matters and is fixed in `apply()`: additive noise first, then the
telephony band-limit, then codec-style quantisation, then dropouts. That is the
order the real path applies them — the room adds noise before the microphone,
the network band-limits after, and packets are lost last.
"""

from __future__ import annotations

import numpy as np

TELEPHONY_LOW_HZ = 300.0
TELEPHONY_HIGH_HZ = 3400.0


def _rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))


def _rng(seed: int | None) -> np.random.Generator:
    return np.random.default_rng(seed)


# ----------------------------------------------------------------- noise sources


def white_noise(count: int, rng: np.random.Generator) -> np.ndarray:
    return rng.standard_normal(count)


def pink_noise(count: int, rng: np.random.Generator) -> np.ndarray:
    """1/f noise. Closer than white to fans, traffic hum and general room tone."""
    spectrum = np.fft.rfft(rng.standard_normal(count))
    frequencies = np.arange(spectrum.size)
    frequencies[0] = 1
    spectrum /= np.sqrt(frequencies)
    shaped = np.fft.irfft(spectrum, n=count)
    peak = np.max(np.abs(shaped))
    return shaped / peak if peak else shaped


def babble(count: int, rate: int, rng: np.random.Generator) -> np.ndarray:
    """Approximate competing conversation: several amplitude-modulated bands.

    Not real speech, but it puts energy in the speech band with syllable-rate
    modulation, which is what actually defeats a VAD. A fan is easy to gate out;
    people talking nearby is not.
    """
    total = np.zeros(count)
    time = np.arange(count) / rate
    for centre_hz, syllable_hz in ((350, 4.1), (800, 3.3), (1600, 5.2), (2600, 2.7)):
        carrier = pink_noise(count, rng)
        band = _bandpass(carrier, rate, centre_hz * 0.6, centre_hz * 1.6)
        envelope = 0.5 + 0.5 * np.sin(2 * np.pi * syllable_hz * time + rng.random() * 6.28)
        total += band * envelope
    peak = np.max(np.abs(total))
    return total / peak if peak else total


def traffic(count: int, rate: int, rng: np.random.Generator) -> np.ndarray:
    """Low-frequency rumble with occasional horn-like transients."""
    base = _bandpass(pink_noise(count, rng), rate, 40.0, 900.0)
    time = np.arange(count) / rate
    for _ in range(max(1, count // (rate * 6))):
        start = rng.random() * max(0.01, time[-1] - 0.6)
        window = (time > start) & (time < start + 0.45)
        horn = np.sin(2 * np.pi * rng.uniform(380, 520) * time) * window
        base += horn * 0.35
    peak = np.max(np.abs(base))
    return base / peak if peak else base


def club(count: int, rate: int, rng: np.random.Generator) -> np.ndarray:
    """Bass-heavy music bed plus a dense crowd.

    The hard part of a club for a voice stack is not loudness, it is the kick:
    periodic high-energy low-frequency transients that push an input AGC down
    and drag a VAD's noise floor estimate up between them, so quiet speech falls
    under the gate. The bass line and crowd sit on top of that.
    """
    time = np.arange(count) / rate
    bpm = 124.0
    beat_hz = bpm / 60.0

    # Kick: decaying sine with a downward pitch sweep, retriggered every beat.
    phase = (time * beat_hz) % 1.0
    envelope = np.exp(-phase * 18.0)
    sweep = 55.0 + 45.0 * np.exp(-phase * 25.0)
    kick = np.sin(2 * np.pi * sweep * time) * envelope

    # Bass line: one note every two beats, low and sustained.
    note_index = (time * beat_hz / 2).astype(int)
    scale = np.array([49.0, 55.0, 58.0, 65.0])
    bass_hz = scale[note_index % scale.size]
    bass = 0.6 * np.sin(2 * np.pi * np.cumsum(bass_hz) / rate)

    # Hats and music wash, band-limited so it does not simply mask everything.
    wash = _bandpass(pink_noise(count, rng), rate, 2000.0, 9000.0) * 0.25
    hats = wash * (0.4 + 0.6 * (((time * beat_hz * 2) % 1.0) < 0.12))

    crowd = babble(count, rate, rng) * 0.5

    total = kick * 1.0 + bass + hats + crowd
    peak = np.max(np.abs(total))
    return total / peak if peak else total


def speech_band_mask(count: int, rate: int, rng: np.random.Generator) -> np.ndarray:
    """Noise concentrated exactly where speech carries meaning.

    Broadband noise is inefficient at hiding speech: most of its energy lands
    where there is nothing to hide. This shapes the masker to the region that
    actually carries intelligibility, so a given SNR does far more damage. It is
    the worst realistic case rather than a specific environment — use it to find
    the floor, not to imitate a room.
    """
    shaped = _bandpass(pink_noise(count, rng), rate, 300.0, 3400.0)
    # Emphasise the 1-3 kHz consonant region, where intelligibility lives.
    consonants = _bandpass(pink_noise(count, rng), rate, 1000.0, 3000.0)
    total = shaped + 1.4 * consonants
    peak = np.max(np.abs(total))
    return total / peak if peak else total


NOISE_SOURCES = {
    "club": lambda n, rate, rng: club(n, rate, rng),
    "speech_band": lambda n, rate, rng: speech_band_mask(n, rate, rng),
    "white": lambda n, rate, rng: white_noise(n, rng),
    "pink": lambda n, rate, rng: pink_noise(n, rng),
    "fan": lambda n, rate, rng: _bandpass(pink_noise(n, rng), rate, 60.0, 700.0),
    "babble": lambda n, rate, rng: babble(n, rate, rng),
    "shop": lambda n, rate, rng: 0.7 * babble(n, rate, rng) + 0.3 * traffic(n, rate, rng),
    "traffic": lambda n, rate, rng: traffic(n, rate, rng),
    "wind": lambda n, rate, rng: _bandpass(pink_noise(n, rng), rate, 20.0, 400.0),
}


# ---------------------------------------------------------------------- filters


def _bandpass(samples: np.ndarray, rate: int, low_hz: float, high_hz: float) -> np.ndarray:
    """Zero-phase brick-wall bandpass in the frequency domain.

    Not how a real filter behaves, but it needs no scipy and the artefacts are
    irrelevant next to the impairment being simulated.
    """
    if samples.size == 0:
        return samples
    spectrum = np.fft.rfft(samples)
    frequencies = np.fft.rfftfreq(samples.size, d=1.0 / rate)
    spectrum[(frequencies < low_hz) | (frequencies > high_hz)] = 0
    return np.fft.irfft(spectrum, n=samples.size)


def telephony_band(samples: np.ndarray, rate: int) -> np.ndarray:
    """Restrict to the 300-3400 Hz band a narrowband phone call survives in."""
    return _bandpass(samples, rate, TELEPHONY_LOW_HZ, TELEPHONY_HIGH_HZ)


def reverb(
    samples: np.ndarray,
    rate: int,
    rt60: float = 0.6,
    wet: float = 0.4,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Diffuse the voice by convolving with a synthetic room response.

    This is the "phone held away from the face in a hard room" case. Reverb does
    not make speech quieter, it smears each phoneme across the ones after it, so
    energy-based VADs still fire but the ASR degrades and endpointing gets late
    because the tail of every word keeps the signal above the gate.

    rt60 is the time in seconds for the tail to decay by 60 dB. Roughly: 0.3 a
    furnished room, 0.6 a bare room or shop, 1.2 a stairwell or hall.
    """
    if samples.size == 0 or rt60 <= 0:
        return samples

    rng = rng or _rng(None)
    length = max(1, int(rt60 * rate))
    time = np.arange(length) / rate
    # Exponentially decaying noise is a crude but serviceable room response.
    impulse = rng.standard_normal(length) * np.exp(-6.9 * time / rt60)
    # Sparse early reflections give the tail some structure instead of a wash.
    for delay_s, gain in ((0.011, 0.7), (0.019, 0.5), (0.031, 0.35), (0.047, 0.25)):
        index = int(delay_s * rate)
        if index < length:
            impulse[index] += gain
    impulse /= np.sqrt(np.sum(impulse**2)) or 1.0

    wet_signal = np.convolve(samples.astype(np.float64), impulse, mode="full")[
        : samples.size
    ]
    dry_peak = np.max(np.abs(samples)) or 1.0
    wet_peak = np.max(np.abs(wet_signal)) or 1.0
    wet_signal *= dry_peak / wet_peak

    return (1.0 - wet) * samples.astype(np.float64) + wet * wet_signal


# ------------------------------------------------------------------ impairments


def _bulbul_bed(
    count: int, rate: int, kind: str, rng: np.random.Generator
) -> np.ndarray:
    """Real multi-speaker Indic babble, generated by Bulbul and cached.

    `kind` is "bulbul" or "bulbul:mr-IN". Falls back to synthetic babble if the
    bed cannot be built, so an offline machine still runs — with a warning,
    because silently substituting a weaker masker would make a run look better
    than the conditions it claims to test.
    """
    language = kind.split(":", 1)[1] if ":" in kind else "hi-IN"
    try:
        import babble_bed

        seconds = max(20.0, count / rate + 5.0)
        bed, bed_rate = babble_bed.build(
            speakers=8, seconds=seconds, language=language, seed=int(rng.integers(1e6))
        )
    except Exception as error:
        print(f"  [warn] bulbul babble unavailable ({error}); using synthetic babble")
        return babble(count, rate, rng)

    if bed_rate != rate and bed.size:
        duration = bed.size / bed_rate
        source_x = np.linspace(0.0, duration, bed.size, endpoint=False)
        target_x = np.linspace(0.0, duration, int(duration * rate), endpoint=False)
        bed = np.interp(target_x, source_x, bed)

    if bed.size < count:
        bed = np.tile(bed, int(np.ceil(count / max(1, bed.size))))
    offset = int(rng.integers(0, max(1, bed.size - count)))
    return bed[offset : offset + count]


def add_noise(
    speech: np.ndarray,
    rate: int,
    kind: str = "babble",
    snr_db: float = 15.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Mix noise in at a calibrated signal-to-noise ratio.

    SNR is computed against the speech-active portion only. Measuring against
    the whole clip would let leading and trailing silence drag the reference
    down and quietly make the mix easier than the number claims.
    """
    if kind not in NOISE_SOURCES and not kind.startswith("bulbul"):
        raise ValueError(f"unknown noise {kind!r}; have {sorted(NOISE_SOURCES)}")

    rng = rng or _rng(None)
    speech = speech.astype(np.float64)
    active = speech[np.abs(speech) > (np.max(np.abs(speech)) * 0.05)]
    speech_rms = _rms(active if active.size else speech)
    if speech_rms == 0:
        return speech

    if kind.startswith("bulbul"):
        noise = _bulbul_bed(speech.size, rate, kind, rng)
    else:
        noise = NOISE_SOURCES[kind](speech.size, rate, rng)
    noise_rms = _rms(noise)
    if noise_rms == 0:
        return speech

    target_noise_rms = speech_rms / (10.0 ** (snr_db / 20.0))
    return speech + noise * (target_noise_rms / noise_rms)


def quantise(samples: np.ndarray, bits: int = 8) -> np.ndarray:
    """Crude codec-style quantisation, standing in for a low-bitrate leg."""
    peak = np.max(np.abs(samples))
    if peak == 0:
        return samples
    levels = 2 ** (bits - 1)
    return np.round(samples / peak * levels) / levels * peak


def dropouts(
    samples: np.ndarray,
    rate: int,
    spans: list[tuple[float, float]],
) -> np.ndarray:
    """Zero out (start_seconds, length_seconds) spans — a dead line, not silence."""
    output = samples.copy()
    for start_s, length_s in spans:
        start = int(start_s * rate)
        stop = min(output.size, start + int(length_s * rate))
        if start < output.size:
            output[start:stop] = 0.0
    return output


def packet_loss(
    samples: np.ndarray,
    rate: int,
    loss_rate: float = 0.02,
    packet_ms: int = 20,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Randomly drop fixed-size packets, the way a bad mobile leg does."""
    rng = rng or _rng(None)
    output = samples.copy()
    packet = max(1, int(rate * packet_ms / 1000))
    for start in range(0, output.size, packet):
        if rng.random() < loss_rate:
            output[start : start + packet] = 0.0
    return output


# ------------------------------------------------------------------------ entry


def apply(samples: np.ndarray, rate: int, spec: dict | None) -> np.ndarray:
    """Apply an impairment spec to int16 mono speech, returning int16 mono.

    Spec keys, all optional:
        noise        one of NOISE_SOURCES
        snr_db       signal-to-noise ratio for that noise, default 15
        telephony    bool, band-limit to 300-3400 Hz
        bits         quantisation depth, e.g. 8
        dropouts     [[start_s, length_s], ...]
        packet_loss  fraction, e.g. 0.03
        gain_db      overall level change, applied last
        seed         int, for reproducibility
    """
    if not spec:
        return samples.astype(np.int16)

    rng = _rng(spec.get("seed"))
    audio = samples.astype(np.float64)

    # Reverb first: the room smears the voice before any of it reaches a mic,
    # and before the room's own noise is added to it.
    if spec.get("reverb"):
        reverb_spec = spec["reverb"]
        if isinstance(reverb_spec, (int, float)):
            reverb_spec = {"rt60": float(reverb_spec)}
        audio = reverb(
            audio,
            rate,
            float(reverb_spec.get("rt60", 0.6)),
            float(reverb_spec.get("wet", 0.4)),
            rng,
        )

    if spec.get("noise"):
        audio = add_noise(
            audio, rate, spec["noise"], float(spec.get("snr_db", 15.0)), rng
        )
    if spec.get("telephony"):
        audio = telephony_band(audio, rate)
    if spec.get("bits"):
        audio = quantise(audio, int(spec["bits"]))
    if spec.get("packet_loss"):
        audio = packet_loss(audio, rate, float(spec["packet_loss"]), rng=rng)
    if spec.get("dropouts"):
        audio = dropouts(audio, rate, [tuple(d) for d in spec["dropouts"]])
    if spec.get("gain_db"):
        audio = audio * (10.0 ** (float(spec["gain_db"]) / 20.0))

    # Scale down rather than clip. At low SNR the speech-plus-noise sum exceeds
    # full scale, and clipping would add harmonic distortion on top of the noise
    # — so the run would be harsher than the SNR it claims to be testing.
    # Scaling preserves the ratio, which is the thing being measured.
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 32767.0:
        audio = audio * (32767.0 / peak)

    return np.clip(audio, -32768, 32767).astype(np.int16)


def describe(spec: dict | None) -> str:
    if not spec:
        return "clean"
    parts = []
    if spec.get("noise"):
        parts.append(f"{spec['noise']}@{spec.get('snr_db', 15)}dB")
    if spec.get("telephony"):
        parts.append("telephony")
    if spec.get("bits"):
        parts.append(f"{spec['bits']}bit")
    if spec.get("packet_loss"):
        parts.append(f"loss={spec['packet_loss']}")
    if spec.get("dropouts"):
        parts.append(f"dropouts={len(spec['dropouts'])}")
    return ", ".join(parts) or "clean"
