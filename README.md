# Disha — a voice career counsellor for tier-3/4 India

> A voice counsellor in the student's own language that asks the questions nobody
> asked, opens career avenues they've never heard of, and notices when the real
> problem is pressure — not marks.

Built solo in about four hours at the **Sarvam Epoch Buildathon** (26 Jul 2026).

**[▶ Read the build story](https://sarvam-blog.pages.dev/) · [▣ The build deck](https://sarvam-blog.pages.dev/deck/)**

---

## The problem

A student in a tier-3 or tier-4 town finishes 10th or 12th and has to decide what
to do next — often from two cousins, a WhatsApp forward, and a commission agent
who names the colleges he's paid to name. They're phone-first, have no laptop, and
speak Hindi or Marathi mixed with English. There is rarely a trustworthy adult to ask.

A form captures the answer. A good counsellor discovers the *reason* — the fee
ceiling, the parent who won't allow a hostel, the two-hour travel limit, the dream
borrowed from someone else. That discovery only happens in conversation, and it has
to happen in the language the student actually thinks in.

## What Disha does

The student opens a link on their phone, taps once, and talks. No app, no login.
Disha holds one honest counselling conversation — one question at a time, never a
form — and by the end the student walks away with:

1. **2–3 real, affordable career avenues**, grounded in a closed dataset and framed
   as trade-offs against their actual constraints.
2. **A written summary** they can keep — plus a **parent-facing version** so the
   family can read the plan too.
3. **A human counsellor alerted** with an escalation card if the conversation
   surfaces distress, family pressure, or choice paralysis.

### What a single call quietly captures

| Listens for | Produces — and refuses to invent |
| --- | --- |
| Profile — name, class, stream, interests | A shortlist of **exact** dataset paths only |
| Five constraints — travel, hostel, fee ceiling, family permission, scholarship dependence | Government scholarships that actually fit the path |
| Wellbeing signals — distress, family pressure, choice paralysis, self-harm | Handbook facts spoken **only** with a page citation |
| Notable life facts worth remembering | Every out-of-list ask logged and auditable |
| Evidence-bound strengths (in the student's own words) | Student + parent summaries, counsellor escalation card |

This is not "ask AI anything." Every layer has a job, a boundary, and an observable
outcome.

## Built on Sarvam

Disha is India-first because the voice stack is. Sarvam handled the parts that
usually eat the first hours of a voice build:

- **Saaras v3 (STT)** — runs on auto-detect, so it *understands* Hindi, Marathi,
  English and code-mixing without the student ever adapting to the machine.
- **Bulbul v3 (TTS)** — a voice with a personality people trust: Indian names sound
  right, English words inside Hindi keep their rhythm, and the tone can slow down
  when the moment calls for it.
- **Docs AI (Document Digitization)** — used offline to digitize two printed career
  handbooks (one shipped scrambled, subsetted fonts) into clean, page-cited chunks
  the agent can quote instead of inventing.
- **Sarvam Translate** — renders the parent-facing summary in the family's language.

## Safety and honesty are enforced, not requested

- **Closed-list discipline.** Disha only discusses careers, courses, and scholarships
  that a lookup tool actually returns. Anything absent gets an honest *"meri list mein
  nahi hai"* and a logged refusal — never a confident hallucination. No colleges,
  fees, cutoffs, or salaries, ever.
- **A safety stop that lives in code, not the prompt.** When a student uses self-harm
  language, Disha gives the **Tele-MANAS helpline (14416)**, stays with them, and a
  hard lock closes the career tools for the rest of the session — because the model,
  told in plain words to stop, resumed the career script one turn later. Instructions
  are a request; the tools are the rule.
- **It never diagnoses.** Wellbeing signals are flagged with the student's verbatim
  words and handed to a human. That's the whole boundary.
- **A test harness that grades honestly.** Sarvam's own models were used to test the
  Sarvam agent — a persona bot speaks through Bulbul, replies come back through
  Saaras, and every step is scored twice (assertions *and* an LLM judge), passing
  only if both agree. Assertions alone said 14/22 healthy; only 8/22 survived a
  reader. It caught a hardcoded-language bug that would otherwise have shipped.
  See [`testing/REPORT.md`](testing/REPORT.md).

## Where it grows

The four-hour build is one honest call plus resume-on-return. The product it points
at is bigger:

- **A counsellor that grows with the person** — from a first vague call, to a deeper
  push after an aptitude test, to the long arc past 12th into degrees and first jobs.
  Conversations and person-facts are stored separately, so it recalls the *student*,
  not a transcript, and the questions evolve as they do.
- **Live, never-stale data** — cron / loop-engineering agents that keep the career
  paths and scholarship schemes current, so grounded advice stays accurate without
  ever loosening the closed-list rule.

## How it's put together

```
Phone browser mic → LiveKit Cloud room → Python agent worker
  ├─ Sarvam Saaras v3 (STT, auto-detect, code-mix)
  ├─ LLM + tools: search_careers · search_handbook · find_scholarships
  │               save_constraint · save_profile · flag_wellbeing · … (12 total)
  ├─ Sarvam Bulbul v3 (TTS)
  └─ grounded, closed knowledge base (Qdrant retrieval)
Next.js web app → join page · live constraint tracker · summaries · counsellor queue
```

Live UI events (constraint tracker, flags, refusals) stream over the LiveKit data
channel — no database on the live path. Persistence, case resume, and the counsellor
queue go through a small case API.

**Grounded on real data:** 327 career pathways · 41 government scholarships · 2
printed handbooks. The career tree descends from **NaksheKadam**, a SIH-2022-winning
project on this exact problem — data reuse with disclosed lineage, zero code reuse.

## Repository map

| Path | What it is |
| --- | --- |
| `agent/` | The LiveKit voice worker — Disha's system prompt, tools, and safety lock |
| `web/` | Next.js app: join page, live tracker, summaries, counsellor view |
| `api/` | Small case API: cases, flags, summaries, counsellor queue |
| `data/` | The closed knowledge base — career tree, scholarships, handbook chunks |
| `scripts/` | Data builders and the Sarvam Docs AI handbook ingestion |
| `testing/` | The Sarvam-tests-Sarvam evaluation harness and its report |
| `sarvam-blog/` | The build story and the deck (deployed to Cloudflare Pages) |
| `personas/` | Persona bank used to drive the test harness |
| `DEPLOY.md` | How the worker, API, and web app are deployed |

## A note on scope

Disha is a career-guidance tool. It does **not** diagnose, assess, or advise on
mental health — it notices signals, gives a helpline, and hands to a human. It never
states fees, cutoffs, or salaries, and refuses anything outside its dataset by design.
