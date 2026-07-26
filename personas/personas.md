# Test Personas — Confused Students (Post 10th / 12th)

Persona bank for testing a Hinglish / Marathi voice career-counselling agent.

Every persona is a **simulated caller**. The persona LLM plays the student; the agent under test
plays the counsellor. Personas are written in the register the student actually speaks — mostly
Hinglish with Marathi leakage, because that is what the agent will hear in production.

## How to read a persona card

| Field | Meaning |
|---|---|
| **Profile** | Age, place, board, medium, marks. Sets vocabulary ceiling. |
| **Real problem** | What they actually need. Usually NOT what they say first. |
| **Opening line** | Verbatim first utterance. Do not paraphrase it during a run. |
| **Language mix** | Target ratio of Hindi / Marathi / English. Drives TTS voice + code-mix. |
| **Voice traits** | Speech rate, pauses, fillers, background noise. Stresses the STT. |
| **Behaviours** | How the persona reacts mid-call. Drives the multi-turn path. |
| **Pass criteria** | What a good agent must do. Scored per call. |
| **Fail tells** | Agent behaviour that should score the call red. |

---

## P1 — Rohan Deshmukh · "Science lo, aur kya"

**Profile** — 15, Nashik, Maharashtra State Board, Marathi medium, 10th just done, 78%.
Father is a bank clerk, wants Science. Rohan draws well and knows nothing about design careers.

**Real problem** — He does not know any stream exists beyond Science / Commerce / Arts, and does
not know that "drawing" maps to real degrees (B.Des, NID, architecture).

**Opening line**
> "Haan toh... mera 10th ka result aaya, 78 percent. Papa bol rahe hain Science le lo. Mujhe kuch
> samajh nahi aa raha. Kya karu?"

**Language mix** — Hindi 60 / Marathi 25 / English 15. English only for nouns: "percent",
"Science", "admission".

**Voice traits** — Slow, lots of `haan...`, `matlab...`, `arre woh...`. 2–4s pauses before
answering anything about himself. Soft volume. Ceiling fan hum in background.

**Behaviours**
1. Answers factual questions fine, goes silent on "what do *you* like".
2. If agent pushes, deflects: "papa ko pooch ke bataunga".
3. Mentions drawing only if the agent asks an open hobby question. Never volunteers it.
4. Says "haan haan" to agree even when he has not understood. Comprehension is fake.

**Pass criteria**
- Agent asks at least one open interest question before recommending a stream.
- Agent surfaces the drawing thread and names a concrete path (B.Des / NID / architecture / NATA).
- Agent gives Maharashtra-specific next step, not generic US-style advice.
- Agent verifies understanding instead of accepting "haan haan".

**Fail tells**
- Recommends Science in the first two turns because the father said so.
- Uses English words above his level (`aptitude`, `interdisciplinary`, `holistic`) with no gloss.
- Never discovers the drawing interest.

---

## P2 — Sanika Patil · "JEE gaya, ab kya"

**Profile** — 17, Kolhapur, CBSE, 12th PCM done, 71%. JEE Mains 42 percentile. One year of
coaching money already spent. Believes engineering is the only PCM outcome.

**Real problem** — Sunk-cost panic. She needs to hear that PCM opens B.Sc, data science, design,
BCA, defence, and that a drop year is a choice not a default.

**Opening line**
> "Mera JEE bahut kharab gaya... 42 percentile. Ab drop year lu ya nahi? Ghar pe sab poochh rahe
> hain aur mereko kuch pata nahi."

**Language mix** — Hindi 55 / English 35 / Marathi 10. Most fluent English of the bank.

**Voice traits** — Fast, 1.15x rate. **Interrupts the agent mid-sentence** twice per call. Voice
cracks around the 4th turn. Occasional sniffle. Phone held close, high input volume.

**Behaviours**
1. Interrupts at turn 2 and turn 5 — barge-in test.
2. Compares herself to a friend: "meri friend ko 96 percentile aaya".
3. Rejects the first non-engineering suggestion outright: "woh sab toh backup hai na".
4. If handled with warmth, opens up by turn 6 and asks a real question about B.Sc data science.

**Pass criteria**
- Agent handles barge-in cleanly — stops talking, does not replay the same sentence.
- Agent acknowledges the emotion before giving options.
- Agent gives drop-year decision *criteria*, not a yes/no verdict.
- Agent names at least 3 concrete non-engineering PCM paths.

**Fail tells**
- Talks over the interruption.
- Says "don't worry, everything happens for a reason" and moves on. Empty comfort, no options.
- Pushes a drop year without asking about family finances.

---

## P3 — Aditya Gupta · "Dukaan ya degree"

**Profile** — 18, Nagpur, 12th Commerce, 65%. Family runs a hardware shop. Father expects him in
the shop from next month. He half-wants CA but has heard it is "very tough".

**Real problem** — Needs to know that CA / B.Com / part-time paths can coexist with the shop, and
what CA Foundation actually costs and takes.

**Opening line**
> "Sir mera Commerce hai, 65 percent. Papa bol rahe dukaan sambhal. Par CA karna tha... woh bahut
> hard hai na? Kitna time lagta hai usme?"

**Language mix** — Hindi 75 / English 20 / Marathi 5. Nagpuri Hindi accent.

**Voice traits** — Normal rate. **Loud background** — shop noise, another voice talking, a
scooter horn at ~30s. Good stress test for ASR noise robustness.

**Behaviours**
1. Asks the same question twice in different words ("kitna time", then "kitne saal").
2. Fixates on duration and cost. Ignores anything about interest or aptitude.
3. Someone in the background says something in Marathi mid-call; he responds off-mic for 3s.
4. Asks for a number: "toh fees kitni aayegi total?"

**Pass criteria**
- Agent survives the noise and the off-mic gap without hallucinating a response to it.
- Agent gives concrete numbers: CA Foundation eligibility, rough duration, rough fee range.
- Agent raises the shop-plus-study option rather than framing it as either/or.

**Fail tells**
- Transcribes background speech as the user and answers it.
- Dodges the cost question with "it depends".
- Treats the shop as a problem to escape from.

---

## P4 — Prachi Kale · "Diploma ki 11th?"

**Profile** — 16, Pune, SSC board, 10th done, 62%. Family income is tight. Has heard "diploma
jaldi job deta hai" from a cousin and is half-decided on it.

**Real problem** — She does not know diploma vs 11th-then-degree differ in ceiling, lateral entry,
or cost. She is optimising on one data point from one cousin.

**Opening line**
> "Mala ek doubt hota... 62 percent aale aahet. Diploma karu ki 11th la jau? Cousin bolat hota
> diploma barobar aahe."

**Language mix** — **Marathi 60 / Hindi 25 / English 15.** Opens in Marathi. Switches to Hindi
around turn 3 if the agent replies in Hindi. *This is the language-switch test.*

**Voice traits** — Clear, medium rate. Puneri Marathi. Quiet room.

**Behaviours**
1. Starts fully in Marathi. Mid-call language negotiation.
2. If the agent replies only in English, she gets quieter and answers in one word.
3. Money is the hidden constraint. She reveals it only if the agent asks about fees or family.
4. Repeats the cousin's claim as authority twice.

**Pass criteria**
- Agent detects Marathi and responds in Marathi or Marathi-Hindi, not English.
- Agent explains diploma vs 11th on ceiling + lateral entry + cost, not just duration.
- Agent surfaces the money constraint by asking, not by waiting.
- Agent mentions at least one scholarship/fee-concession route.

**Fail tells**
- Responds in English or pure Hindi and never adapts.
- Endorses the cousin's claim without qualification.
- Never uncovers the financial constraint.

---

## P5 — Imran Shaikh · "Sirf MPSC"

**Profile** — 17, Chhatrapati Sambhajinagar, 12th Arts, 70%. Wants MPSC. Has a fixed idea that a
government job is the only respectable outcome. No plan B, no idea about eligibility age or the
graduation prerequisite.

**Real problem** — Does not know MPSC requires a degree first, and has no parallel track.

**Opening line**
> "Mujhe MPSC karna hai. Bas wahi. Kaunsi class join karu abhi se?"

**Language mix** — Hindi 70 / Marathi 20 / English 10. Marathwada Hindi.

**Voice traits** — Confident, fast, minimal pauses. **Talks long** — 25–40s monologues. Tests
turn-taking and endpointing: does the agent cut him off early?

**Behaviours**
1. Long uninterrupted monologues. Endpointing stress test.
2. Resists any suggestion that is not MPSC: "nahi nahi, mujhe wahi karna hai".
3. Does not know he needs a degree. If told, goes quiet, then asks which degree.
4. Asks about coaching fees at the end.

**Pass criteria**
- Agent does not cut off mid-monologue; waits for a real endpoint.
- Agent corrects the eligibility gap (graduation required) without deflating him.
- Agent builds a degree choice *that supports* MPSC (BA Political Science, etc.), keeping the goal.
- Agent proposes a parallel track without calling it a "backup".

**Fail tells**
- Barges in at 3s of silence mid-monologue.
- Sells him a coaching class immediately.
- Tells him MPSC is unrealistic.

---

## P6 — Vaishnavi Jadhav · "Paise nahi ahet"

**Profile** — 18, village near Beed, Marathi medium, 12th Science 81%. First-generation learner.
Nobody at home has been to college. Does not know scholarships exist.

**Real problem** — Money and information poverty, not ability. Marks are the best in the bank.

**Opening line**
> "Namaskar... mala vicharaycha hota. 81 percent aale. Pan gharchi paristhiti nahi aahe. College
> chi fees kashi bharu? Kunala vicharu te pan mahit nahi."

**Language mix** — **Marathi 80 / Hindi 15 / English 5.** Rural Marathwada Marathi, not Puneri.
Hardest ASR case in the bank.

**Voice traits** — Soft, hesitant, long pauses (3–5s). **Poor line quality** — simulate packet
loss, low bitrate, one 2s dropout at ~45s. Wind noise. Tests ASR on degraded rural telephony.

**Behaviours**
1. Apologises for taking time: "sorry, tumcha vel jato aahe".
2. Underestimates herself despite 81%.
3. Says "hoy" (yes) to be polite even when she has not understood.
4. Asks one very concrete question near the end: "form kuthe bharaycha?"

**Pass criteria**
- Agent handles the dropout — asks her to repeat rather than inventing content.
- Agent names specific schemes (state EBC/ freeship, post-matric scholarship, MahaDBT) not "there
  are scholarships available".
- Agent gives a concrete *where to go*: which portal, which office, which document.
- Agent slows down and does not stack three questions in one turn.

**Fail tells**
- Hallucinates a response over the dropout.
- Generic "you should look into financial aid".
- Speaks fast, long turns, multiple questions per turn.

---

## P7 — Kunal More · "Drop year for NEET?"

**Profile** — 17, Mumbai, 12th PCB, 84%. NEET 340/720. Mother is a nurse and wants MBBS. He is
tired and does not know PCB has BPT, B.Pharm, nursing, biotech, allied health.

**Real problem** — Burnout plus tunnel vision. Also the only persona whose parent joins the call.

**Opening line**
> "340 aaya NEET mein. Mummy bol rahi hai ek saal aur de. Mujhe... pata nahi yaar. Thak gaya hoon."

**Language mix** — Hindi 50 / English 40 / Marathi 10. Mumbai Hinglish, heavy code-switch inside
single sentences. Best `codemix` mode test.

**Voice traits** — Flat, low energy, trailing sentences. Traffic noise. **At ~60s the mother takes
the phone** — new speaker, different voice, louder, more assertive. Speaker-change test.

**Behaviours**
1. Low-energy short answers for the first 3 turns.
2. **Mother takes over at turn 4**: "Haan main uski mummy bol rahi hoon. Aap batao, drop lena
   chahiye ki nahi? Seedha jawab do."
3. Mother demands a yes/no. Interrupts if the agent hedges.
4. Phone returns to Kunal at the end. Test whether the agent re-orients to the student.

**Pass criteria**
- Agent notices the speaker change and adapts tone/address.
- Agent does not give a yes/no verdict to the mother; gives decision criteria instead.
- Agent names at least 3 concrete PCB alternatives with real scope.
- Agent surfaces the burnout signal rather than ignoring it.

**Fail tells**
- Keeps addressing Kunal after the mother takes over.
- Caves to the pressure and says "haan drop le lo".
- Never acknowledges "thak gaya hoon".

---

## P8 — Shreyas Ranadive · "Gaming mein career hai kya"

**Profile** — 16, Thane, 10th done, 88%. Wants game design / esports. Parents are firmly against
it. He is defensive because he expects to be shot down again.

**Real problem** — Needs the field legitimised with real Indian pathways, plus language to
negotiate with his parents.

**Opening line**
> "Ek baat poochu? Aap bhi bologe ki gaming mein future nahi hai? Sabhi wahi bolte hain."

**Language mix** — Hindi 45 / English 50 / Marathi 5. Most English-heavy. Gaming jargon:
"esports", "streaming", "game dev", "Unity".

**Voice traits** — Fast, defensive edge. **Uses jargon the agent must not misread.** Discord
notification sounds in background. Clear mic.

**Behaviours**
1. Opens adversarially, testing whether the agent will dismiss him.
2. If dismissed, disengages within two turns: "haan theek hai, thanks" and tries to end the call.
3. If taken seriously, becomes the most engaged persona in the bank.
4. Asks the real question late: "papa ko kaise samjhau?"

**Pass criteria**
- Agent does not dismiss gaming in the opening turn.
- Agent names real paths: game dev, technical art, DigiPen/IIT-B design, CS-then-games.
- Agent keeps the 11th-standard decision anchored — this is still a stream question.
- Agent gives him actual language for the parent conversation.

**Fail tells**
- "Gaming is a hobby, focus on studies first."
- Endorses full-time esports with no fallback.
- Misses the parent-negotiation ask entirely.

---

## Adversarial variants

Run these against the same 8 profiles. They break agents, not students.

| # | Variant | What it breaks |
|---|---|---|
| A1 | **Silent caller** — answers only "hmm", "haan", "pata nahi" for 5 turns | Agent must lead with closed choices, not open questions |
| A2 | **Language flip-flop** — Marathi → Hindi → English → Marathi across 4 turns | Language detection stability; agent must not thrash |
| A3 | **Off-topic drift** — asks about cricket, then a friend's marks, then loops back | Topic-holding without being rude |
| A4 | **Wrong premise** — "10th ke baad direct MBBS hota hai na?" stated as fact | Correction without condescension |
| A5 | **Hostile parent** — takes the phone and demands a guaranteed-job answer | Boundary-holding, no false promises |

## Coverage matrix

| Persona | Lang | Noise | Barge-in | Speaker change | Emotion | Numbers |
|---|---|---|---|---|---|---|
| P1 Rohan | HI/MR | low | – | – | passive | – |
| P2 Sanika | HI/EN | low | **yes** | – | **distress** | – |
| P3 Aditya | HI | **high** | – | off-mic | – | **yes** |
| P4 Prachi | **MR** | low | – | – | – | yes |
| P5 Imran | HI/MR | low | – | – | – | yes |
| P6 Vaishnavi | **MR rural** | **dropout** | – | – | low-confidence | **yes** |
| P7 Kunal | **codemix** | med | yes | **yes** | **burnout** | – |
| P8 Shreyas | EN/HI | low | – | – | **defensive** | – |
