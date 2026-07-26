# IDEA_SCOPE.md — Disha

> Control plane for the build. If a change does not improve the active milestone's acceptance test or the rubric strategy, it goes to the parking lot.

## 0. Scope status

| Field | Value |
|---|---|
| Event | Sarvam Epoch Buildathon, 2026-07-26, Razorpay Arena |
| Team | Solo — Rushikesh Patade |
| Build starts | 11:35 IST |
| Deployed target | 15:20 IST |
| Submission lock | 16:30 IST |
| Demo duration | 3 min (30s context, 30s pain, 2 min live) |
| Current milestone | M0 |
| Scope owner | Rushikesh |
| Last updated | 11:30 IST |

Status language: Specified → Implemented → Working locally → Verified → Demo-ready.

## 1. Idea lock

| Decision | Locked answer |
|---|---|
| One-sentence product | A voice counsellor in the student's own language that asks the questions nobody asked, opens career avenues they've never heard of, and notices when the real problem is pressure — not marks. |
| Specific user | Class 11–12 / fresh-pass student in a tier-3/4 town, speaks Hindi or Marathi (code-mixed with English), phone-first, no laptop |
| Situation and repeated job | "What should I do after 12th?" — decided today from two cousins, a WhatsApp forward, and a commission-driven agent |
| Current workaround | Commission counsellor who names colleges he's paid to name; or nobody at all |
| Hard input | A rambling, code-mixed call that opens with a borrowed aspiration, hides the five real constraints (distance, hostel, fees, family permission, scholarship risk), contradicts itself, and carries family pressure the student won't name directly |
| Final usable output / state change | (1) Spoken trade-off guidance grounded ONLY in the closed dataset, (2) a written session summary + career shortlist the student can show a parent, (3) a flag log + escalation card in a counsellor queue when distress / family pressure / choice paralysis is detected |
| Sarvam parameter | **Voice Experience** (only scored branch) |
| Additional capability | Sarvam Translate for the parent-facing summary language — load-bearing for the artifact, not scored |
| Team's unfair advantage | SIH 2022 winner on this exact problem (NaksheKadam — inspiration only, zero code reuse); production LiveKit voice tuning (barge-in, endpointing, interruptions) from real work; native Hindi + Marathi |
| Creativity thesis | Three reinforcing choices: (a) indirect elicitation — constraints surface through concrete life questions, never a form; (b) the counsellor notices wellbeing signals (distress, family pressure, choice paralysis) woven into career talk and adapts instead of pushing the script; (c) closed-list discipline — it never names a career/college/fee outside its dataset, says "not in my list", and logs every refusal |
| Delight thesis | At the student's hardest moment (pressure surfaces), the agent slows down, drops the checklist, acknowledges in their language — then the summary that reaches the parent frames the student's constraints respectfully. Honest recovery, not cheerfulness |
| Decisive demo proof | Judge (or builder) plays a student with a cousin-fed aspiration and hidden family pressure. Agent surfaces constraints without a form, flags the pressure gently mid-call (visible in the counsellor view), refuses an out-of-list college by name, and the parent summary arrives in Marathi |

### Why this idea
- **Asymmetric fit:** domain (SIH-winning career guidance) × craft (production voice turn-taking) × language (native Hindi/Marathi for live judging) — no other 4-hr team at the venue likely has all three.
- **Decisive proof:** unrehearsed judge input; refusal behaviour verifiable in ten seconds; flag appears in a second surface (counsellor queue) — a state change, not a chat reply.

## 2. User and job

> When a tier-3/4 student must choose what to do after class 12 with no trustworthy adult to ask, they need to complete one honest counselling conversation in their own language, so that they leave with 2–3 viable, affordable career avenues, a plan a parent can read, and — if they're struggling — a human counsellor alerted.

Job complete only when: (1) ≥3 of 5 constraints elicited and persisted, (2) shortlist produced strictly from the closed dataset, (3) summary artifact rendered (student + parent version), (4) any wellbeing flag logged with verbatim quote and visible in counsellor view.

## 3. Product contract

### Golden path
1. Student opens web link on phone, taps mic, speaks Hindi/Marathi (code-mixed OK).
2. Agent elicits life facts conversationally → five constraints fill a visible tracker.
3. Student names an aspiration; agent explores it + 2 adjacent avenues from dataset, as trade-offs against elicited constraints.
4. Wellbeing signals (distress / family pressure / choice paralysis) are detected → tone shift + acknowledgement + flag logged.
5. Call ends → summary page (student) + parent summary (translated) + counsellor escalation card if flagged.

### Memory boundary
- Within one call: full constraint + conversation state (this is Voice, not Memory evidence).
- Across sessions: case persisted in Mongo (EC2); reopening the link resumes the case — **this is the Memory evidence**.
- Deliberately forgotten: no audio stored; flags store quote + timestamp only.

### Human review boundary (hard rules, enforced in code)
- NEVER diagnoses, assesses, or advises on mental health. Flags and hands to a human.
- Explicit self-harm marker → immediate warm handoff message with Tele-MANAS 14416 (verify number before demo) + top-priority escalation. No career script continues.
- NEVER names a career, college, fee, or cutoff outside the dataset. "Not in my list" ≠ "no match found". Every out-of-list ask is logged.

## 4. Verified capability matrix

| Capability | API | Access | Verified |
|---|---|---|---|
| STT | Saaras v3 streaming via `livekit-plugins-sarvam` (`sarvam.STT(model="saaras:v3")`, `unknown` lang detect / `hi-IN` / `mr-IN`, codemix) | SARVAM_API_KEY | docs.livekit.io + PyPI 1.6.7 ✓ |
| TTS | Bulbul v3 via `sarvam.TTS(model="bulbul:v3")`, hi-IN/mr-IN/en-IN, chunked streaming | SARVAM_API_KEY | ✓ |
| Translate | Sarvam Translate REST (parent summary) | SARVAM_API_KEY | docs listed, exercise in M3 |
| Media | LiveKit Cloud `wss://<your-project>.livekit.cloud` | .env.local | `lk room list` ✓ |
| LLM | LiveKit Inference (gemini flash, soca pattern) | LiveKit creds | known-good pattern |
| State | Mongo on EC2 (`127.0.0.1:27018`, worker co-located; dev via SSH tunnel) | pem key | container healthy ✓ |
| Deploy | Frontend → Vercel; worker → EC2 (docker) | existing accounts | — |

**Unsupported assumptions (not on critical path):** telephony/PSTN, voice cloning, Sarvam LLM endpoint, Doc AI. Latency target ~600 ms perceived turn start (preemptive TTS); measure in M0, never claim "instant".

## 5. Rubric strategy

| Dimension | Mult | Target | Observable proof | Milestone |
|---|---:|---:|---|---|
| JTBD completion | 2.5× | L4–L5 | 3 scripted personas complete end-to-end, artifacts produced, no builder touch | M1→M4 |
| Memory & Context | 1× | L3–L4 | Constraint tracker fills from conversation; case resumes after page reload | M3 |
| Creativity | 1.5× | L4 | Elicitation-not-form + wellbeing-aware counselling + auditable refusal, reinforcing | M2 |
| Impact | 1.5× | L4 | Commission-counselling baseline story + NaksheKadam credibility; metric: % students reaching a constraint-fit shortlist vs. agent-fed default | pitch prep |
| Delight | 1× | L3–L4 | Pressure moment handled with judgment; recovery without losing progress | M2 |
| **Voice Experience** | 2.5× | L4 | Live code-mixed Hindi/Marathi, barge-in mid-sentence, correction survives, follow-ups build on answers | M0→M3 |

Evidence boundaries: in-call flow → Voice. Persisted resume → Memory. Refusal + flagging design → Creativity. Pressure-moment handling → Delight. Artifact completion → JTBD. No double-counting.

Rubric traps to avoid: avatar/polish ≠ creativity; "I understand your concern" stock empathy ≠ delight; naming many Sarvam APIs ≠ score.

## 6. Architecture (smallest)

```
Phone browser mic → LiveKit Cloud room → Python agent worker (EC2)
  ├─ sarvam.STT (saaras:v3, streaming, codemix)
  ├─ LLM (LiveKit inference) + tools:
  │    lookup_careers(closed JSON dataset) · flag_wellbeing(type, quote) · save_constraint(k,v)
  ├─ sarvam.TTS (bulbul:v3, hi-IN/mr-IN)
  └─ Mongo: cases, constraints, flags, refusal log
Next.js (Vercel): join page + live constraint tracker + summary page + counsellor queue view
```

Components: `agent/` (worker, Python) · `web/` (Next.js, from livekit agent-starter) · `api/` (tiny FastAPI on EC2 via Coolify: cases, flags, summaries, counsellor queue; Mongo behind it) · `data/career_tree.json` — **real NaksheKadam SIH-2022 career tree (423 nodes, 7 streams incl. 72 vocational paths)**, data reuse with disclosed lineage. Tree has courses/jobs/links, NO fees → agent refuses fee/cutoff specifics ("not in my list") instead of inventing them.

Live UI events (constraint tracker, flags, refusal log) stream over the LiveKit **data channel** to the web client — no DB on the live path. Persistence/resume/counsellor queue go through `api/`.

## 7. Milestones (real clock)

### M0 — 11:35–11:50 · Feasibility
Scaffold repo; SARVAM_API_KEY verified with one STT + one TTS call; voice loop hello-world locally (laptop worker + LiveKit Cloud). **Accept:** I speak Hindi, hear a Bulbul reply. **Stop:** if sarvam plugin fails by 12:00 → raw Sarvam REST STT/TTS in the worker (slower, still works).

### M1 — 11:50–12:35 · Ugly end-to-end (JTBD L3)
System prompt v1 (elicitation via life questions), save_constraint tool → Mongo, call-end summary JSON → rendered summary page. **Accept:** one Hindi call elicits ≥3 constraints and produces the summary without code edits. **Behind → cut:** summary page = raw JSON dump, still counts.

### M2 — 12:35–13:35 · Flags + closed list (Creativity/Delight core)
`data/careers.json` curated (delegate); lookup tool with refusal + log; flag_wellbeing (distress / family-pressure / choice-paralysis) → tone-shift instruction + counsellor card; self-harm hard rule. **Accept:** scripted pressure line triggers flag visible in counsellor view; out-of-list college gets "not in my list" + log entry. **Behind → cut:** counsellor view = table of flags, no styling.

### M3 — 13:35–14:35 · Deploy + Memory + parent summary
Worker dockerized → EC2 (Mongo localhost); web → Vercel; resume-case on reload; parent summary via Translate (Marathi); barge-in/endpointing tuning pass. **Accept:** golden path works on the public Vercel URL from a phone. **Behind → cut:** parent summary in same language (skip Translate); worker stays on laptop with EC2 tunnel for state.

### M4 — 14:35–15:20 · Hardening (no new features)
3 scripted personas run clean; reset script; fallback screen-recording captured; 2 timed rehearsals; submission assets. **Accept:** two consecutive timed rehearsals pass, incl. one on fallback.

Buffer 15:20–16:00. Submission ≤16:15.

## 8. Test plan
Personas (scripted before M2 ends): (1) borrowed-aspiration + hidden fee constraint, (2) family-pressure ("papa bolte hain engineering hi karna hai") → flag, (3) choice paralysis + out-of-list college ask → refusal. Failure cases: unreadable/garbled turn → ask to repeat without restart; API timeout → honest "ek second" + retry; self-harm phrase → handoff script.

## 9. Demo contract (2 min live)
0–15s: student joins on phone, speaks Marathi-mixed Hindi. 15–60s: elicitation — constraints tracker fills live; barge-in correction ("nahi, 2 lakh nahi — 1 lakh max") survives. 60–90s: pressure line → visible tone shift + flag card pops in counsellor view. 90–110s: out-of-list college → "not in my list" + refusal log. 110–120s: summary + Marathi parent note + escalation card. Claims we must NOT make: latency numbers we didn't measure, dataset provenance beyond what it is, any mental-health assessment capability.

## 10. Pre-mortem (top 3) & mitigations
1. **Latency/turn-taking sluggish on venue wifi** → preemptive TTS on, phone hotspot fallback, fallback recording.
2. **Flag detection flaky live** → flags driven by tool-call with generous scripted markers; personas rehearsed; counsellor view also shows constraint events so the surface is never empty.
3. **Elicitation prompt rambles or interrogates** → prompt reviewed against 3 personas in M2; hard cap one question per turn.

## 11. Non-goals
Telephony/PSTN · mobile app · voice cloning · real college verification/live scrapes · counsellor marketplace/login · English UI polish · analytics.

## 12. Parking lot
Doc AI marksheet upload · scholarship-eligibility mock endpoint · WhatsApp delivery of summary · multi-district datasets · Sarvam-30B as LLM · dialect expansion beyond hi/mr.

## 13. Execution split
Codex lane A: agent worker (owns `agent/`). Codex lane B: Next.js web (owns `web/`). Claude: dataset curation, integration, every verify/run/deploy gate, this file. One owner per path; golden path stays runnable after every merge.

## 14. Next single action
Rushikesh: paste SARVAM_API_KEY. (dashboard.sarvam.ai → API keys)
