# Hinglish / Marathi Voice Agent Test Harness — MVP

Persona-driven testing for a career-counselling voice agent aimed at Indian students who have just
finished 10th or 12th standard. Language target: Hinglish with Marathi code-switching.

## What exists right now

```
personas/personas.md     8 persona cards + 5 adversarial variants + coverage matrix
personas/personas.json   the same bank, machine-readable, keyed by id
```

Nothing is wired to an API yet. This is the test-input layer only.

## Why not Coval

Coval, Hamming and Cekura are the established voice-agent simulation platforms. They are built for
English. Their transcription and LLM-judge layers score Marathi and heavy Hinglish code-mix
unreliably, which produces noisy pass/fail results on exactly the calls that matter most here.

Sarvam gives the Indic pieces — Saaras v3 ASR (22 languages, code-mix output mode), Bulbul v3 TTS
(35+ voices, 11 languages) and Sarvam-M for the persona and judge roles. It does not ship a
simulation, regression or scorecard product. That layer is the thing to build.

## MVP scope

Text-only first. Audio second. Do not build both at once.

**Stage 1 — text loop (no audio).** Persona LLM plays the student from a card in `personas.json`;
the agent under test replies; an LLM judge scores the transcript against that persona's `pass` and
`fail` lists. Catches roughly 70% of agent failures — wrong recommendations, missed hidden context,
condescension, dodged questions — at a fraction of the cost and latency of a real call.

**Stage 2 — audio loop.** Wrap Stage 1 with Bulbul TTS on the persona side and Saaras ASR on the
capture side, then replay the audio through the agent. This is what surfaces the failures Stage 1
cannot see: barge-in handling, endpointing on long monologues, speaker changes, dropout recovery,
and ASR breakage on rural Marathi.

The `stress` field on each persona marks which stage a given failure mode belongs to. Anything in
the audio column of the coverage matrix in `personas.md` is Stage 2 only.

## Scoring

Per call, per persona: count of `pass` criteria met, count of `fail` tells triggered. A call is
green only when every `pass` item is met and no `fail` tell fires. Track the two counts separately
over time — pass-rate and fail-rate move independently and averaging them hides regressions.

## Adding a persona

Add the card to `personas.md` first, then mirror it into `personas.json` under the same `id`. Keep
`opening` verbatim across both files; runs are not comparable if the first utterance drifts.
