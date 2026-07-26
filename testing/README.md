# testing/ — persona call harness

Drives real LiveKit calls against the Disha worker using the persona bank in `personas/`, and
saves the audio.

Nothing here imports from `agent/`, `api/`, `web/` or `data/`. The bot joins the room as an
ordinary participant named `student`, exactly the way a real caller would, so the agent under test
is unmodified and unaware it is being tested.

## Layout

```
testing/
  persona_bot.py      one call, one persona, start to finish
  sarvam_client.py    REST wrappers for Bulbul TTS, Saaras STT, Sarvam chat
  .venv/              isolated; agent/.venv is never touched
  recordings/<run>/   output, one directory per call
```

## Run a call

The Disha worker must already be running (`./scripts/dev.sh` or `make dev-agent`). Check first —
two registered workers will both accept dispatch and you will not know which one answered:

```
ps -eo pid,etime,command | grep "main.py dev" | grep -v grep
```

Then:

```
testing/.venv/bin/python testing/persona_bot.py p4_prachi --turns 6
```

Persona ids: `p1_rohan`, `p2_sanika`, `p3_aditya`, `p4_prachi`, `p5_imran`, `p6_vaishnavi`,
`p7_kunal`, `p8_shreyas`.

## Run a scripted scenario

A scenario is a fixed list of student lines, each declaring what the agent is expected to do. The
runner checks those expectations and prints a pass/fail readout, so a prompt change shows up as a
changed score instead of a differently-worded conversation to read by hand.

```
testing/.venv/bin/python testing/scenario_runner.py m2_tuning
```

Scenarios live in `testing/scenarios/*.json`. A step can assert any of:

| Expectation | Meaning |
|---|---|
| `barge_in_stop_latency_under_s` | Student talks over the agent; agent must stop within N seconds |
| `event_type` | Agent must emit this event on the `disha` topic (`constraint`, `refusal`, `flag`, `career`, `summary`) |
| `any_of_names` | For `constraint`, which constraint names count |
| `flag_type` | For `flag`, which wellbeing type is expected |
| `reply_contains_any` | The agent's spoken reply must contain one of these substrings |

Output adds `readout.txt` and `readout.json` to the run directory.

## Output per run

| File | What it is |
|---|---|
| `call.wav` | Stereo. Left = agent, right = student. This is the listenable recording. |
| `agent.wav` | Agent only, mono. |
| `student.wav` | Persona only, mono. |
| `transcript.json` | Every turn with speaker, wall-clock offset, text, detected language. |
| `events.jsonl` | Everything the agent published on the `disha` data topic — constraints, career searches, wellbeing flags, refusals, the final summary. |
| `meta.json` | Run metadata plus that persona's `pass` criteria and `fail` tells, for scoring. |

Both tracks are written into a shared wall-clock timeline at 48 kHz, so overlaps in `call.wav` are
real overlaps. If the agent talks over the student, you hear it.

## How a turn works

1. Listen to the agent's track until it has spoken and then stayed below the RMS threshold for
   `TURN_END_SILENCE_S` (1.6s).
2. Transcribe that turn with Saaras v3, language `unknown` so detection is not forced.
3. Ask the persona LLM for the next student line, given the persona card and the conversation.
   Turn 1 is always the card's verbatim `opening` so runs stay comparable.
4. Speak it with Bulbul v3 and publish it to the room.

The agent has barge-in enabled with `min_words: 0`, so its reply often starts while the student is
still speaking. The buffer is therefore cleared when the student *starts* a line, not after it
ends — clearing after would discard the agent's reply and stall the call.

## Persona brain

Uses `OPENAI_API_KEY` if present, otherwise falls back to Sarvam's chat model. The key is read at
runtime from `~/gba/fabri/.env` (override with `OPENAI_ENV_FILE`) and is deliberately never copied
into this repo. Model defaults to `gpt-4.1-mini`; override with `PERSONA_MODEL`.

## Noisy conditions

Bulbul returns clean studio speech. No student calls from a studio. Until the harness degrades its
own audio, the noisy path is simply untested — the agent looks fine because it is being handed
audio it will never receive.

```
testing/.venv/bin/python testing/scenario_runner.py m2_tuning --noise shop --snr 10
testing/.venv/bin/python testing/persona_bot.py p3_aditya --noise shop --snr 10 --telephony
```

Noise kinds: `babble`, `shop`, `traffic`, `fan`, `wind`, `pink`, `white`. `babble` and `shop` are
the ones that matter — a fan is easy to gate out, people talking nearby is not, because it puts
modulated energy in the speech band where a VAD cannot distinguish it from the speaker.

`--telephony` band-limits to 300–3400 Hz and quantises to 8 bit, standing in for a narrowband
mobile leg.

SNR is calibrated against the speech-active portion only, so leading and trailing silence cannot
quietly make a mix easier than its label claims. Rough anchors: 30 dB quiet room, 20 dB fan on,
15 dB TV in the background, 10 dB shop or roadside, 5 dB loud street.

### Finding the cliff

"Works in noise" is not a yes/no property. Every voice stack has an SNR below which VAD, ASR or
endpointing collapses; what matters is whether that point sits above or below where users call
from. The sweep runs one scenario at descending SNR and reports where it breaks.

```
testing/.venv/bin/python testing/noise_sweep.py m2_tuning --noise shop
```

It reports steps passed, agent turns produced, and empty replies per level. Empty replies and
missing turns are the tell that the agent's VAD is being defeated rather than its reasoning.

Impairments are also settable per scenario via an `"impairments"` key, or per persona from the
`audio` field on the persona card.

## Combined scoring — assertions plus judge

Every scenario step carries both an `expect` block (deterministic) and a `judge` list (natural
language). `score.py` runs both and passes a step only if neither layer fails it.

```
testing/.venv/bin/python testing/score.py recordings/20260726-123821_m2_tuning
testing/.venv/bin/python testing/score.py recordings/*_m2_tuning recordings/*_closed_list
```

This runs offline against saved runs, so re-scoring costs one API call per step and does not need a
live worker. Output is a table plus a disagreement section:

```
    step                              assert    judge     combined
1   mid-sentence barge-in             PASS      FAIL      FAIL
2   constraint in Marathi-mixed Hind  PASS      FAIL      FAIL
3   out-of-list fee question          PASS      PASS      PASS
4   family pressure line              PASS      PASS      PASS
```

Disagreements matter more than the total. Every disagreement in the first full run was the
assertion being too generous, not the judge inventing a fault — which is the signal that an
assertion needs tightening. Writes `score.txt` and `score.json` into the run directory.

## LLM judge (persona runs)

Deterministic assertions cover anything with a crisp definition. They cannot score "did it
acknowledge the emotion before giving options" or "did it endorse a bad source". That is what the
judge is for.

```
testing/.venv/bin/python testing/judge.py recordings/20260726-120316_p4_prachi
```

It reads `meta.json` for the persona's pass criteria and fail tells, sends them with the transcript
to a judge model, and writes `judge.txt` and `judge.json` into the run directory. Every verdict must
carry a verbatim quote from the transcript, so verdicts can be checked rather than trusted. Model
defaults to `gpt-4.1`; override with `JUDGE_MODEL`.

## Findings

`REPORT.md` in this directory is the write-up of the 2026-07-26 run, including what the harness
found, what it got wrong about itself, and the limits of the numbers.

## Known limits

- One call at a time. No batch runner, no regression comparison across runs.
- Silence detection is a fixed RMS threshold, not a VAD. Very quiet agent audio could read as
  silence and end a turn early.
- The persona speaks scripted-then-generated lines at natural gaps. It does not deliberately
  interrupt, so P2's and P7's barge-in behaviours are described in the persona bank but not yet
  driven by the bot.
- Audio impairments in the persona cards — P6's line dropout, P3's shop noise — are not injected
  yet. The cards specify them; the bot does not apply them.
