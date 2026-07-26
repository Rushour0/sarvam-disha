# Session handoff — knowledge-base work

State as of 12:35 IST, 2026-07-26. Pick this up only after the golden path is demo-stable.

## Status update (2026-07-26, later session)

- Task 1 DONE — `search_handbook` tool, citation-gated instructions, `kb` data
  event, and a Sources section in the session panel. `make build` is green.
- Data repair, not in the original plan: the 26 SD SEED chunks were glyph-code
  mojibake (subsetted fonts with no ToUnicode map — pypdf and pdftotext both
  return raw codes). `scripts/decode_handbook.py` decodes them, drops the 3
  pages that stay unreadable, and is idempotent. Run it with `--from-pdf` to
  re-extract from `data/raw/` and decode from the original glyph codes. 91
  chunks total: 24 SD SEED + 65 CFA + 2 recovered cover pages.
- Task 2 DONE by a parallel session (agent `load_case_facts` + `disha.case`
  attribute from the web client).
- Qdrant IS wired, hybrid per the fabri pattern (`agent/retrieval.py`): RRF
  fusion of a Qdrant dense arm and an in-process BM25 arm. No new Python deps —
  httpx over the Qdrant REST API, BM25 written out. Degrades to BM25-only when
  Qdrant or embeddings are unavailable, so `make dev` works with nothing running.
  Collections: `disha_handbook` (91), `disha_careers` (88),
  `disha_conversation_<case>`, `disha_person_<case>`. Re-index with
  `agent/.venv/bin/python scripts/index_kb.py` (drops and rebuilds both static
  collections, so removed chunks do not linger as orphaned points).
- The career tree is now searched too, not just the handbook. It used to match
  node NAMES only, so "teacher banna hai" returned nothing even though nine
  nodes list Teacher in their `jobs` text. `build_career_documents()` indexes
  path + jobs; exact name matches still rank first.
- The vocational gap is closed. `data/pathway_tree.json` (v2) is now the single
  career source: 327 nodes — 7 streams, 240 qualifications, 70 ITI trades,
  10 Army entry routes. Built by `scripts/build_pathway_tree.py` from
  `career_tree.json` + `vocational_paths.json`, with scholarship tags attached.
- Schema is a FLAT node list with parent/child ids so a front end can render a
  tree, breadcrumb, or graph from the same file. Served at `GET /tree`;
  scholarships at `GET /scholarships`.
- `data/scholarships.json`: 41 government schemes — 31 central, 10 Maharashtra
  state — of which 9 carry a sourced amount and income ceiling; the rest are
  name+provider only. Every record carries
  `source_url` and `fetched_on`. Nothing is populated that an official page did
  not state — an invented income ceiling is worse than no answer.
- Hindi/Marathi aliases on the trades ("silai ka kaam", "sena bharti",
  "khana banane ka kaam") — without them every dataset word was English and
  the students this is for got refusals.
- `search_careers` results carry their matching `scholarships` inline, so the
  affordability answer does not depend on the model remembering a second call.

### Maharashtra coverage

The personas are Marathi-speaking students in tier-3/4 Maharashtra, and the
state schemes are the ones that actually move their decision — a hostel
allowance answers `hostel_needed` and a 100% fee waiver answers `fee_ceiling`
far more concretely than a central merit scheme does.

- Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship — 100% tuition
  and exam fees for girls, 50% for boys, income ceiling Rs. 8 lakh (DTE).
- Dr. Panjabrao Deshmukh Vasatigruh Nirvah Bhatta — hostel maintenance of
  Rs. 60,000 / 51,000 / 43,000 / 38,000 per year by location tier (DTE).
- GoI Post-Matric Scholarship (Maharashtra SC/Navbouddha) — maintenance
  Rs. 250-1,350 per month plus fees, income ceiling Rs. 2.50 lakh (SJSA).
- Seven more MahaDBT-listed schemes, name and department only.
- Vocational: DVET centralised ITI admission, NAPS and MAPS apprenticeships,
  and ITI Short Term Training (STEP) as `Vocational Education > Maharashtra
  routes > …` nodes.

Scholarship records carry a `state` field; nodes carry `state` too, so the
front end can filter and Disha can say "this is a Maharashtra scheme".

### Measured retrieval quality (2026-07-26)

Probe of 14 questions the personas would really ask plus 8 that nothing in the
dataset can answer:

    recall            14/14
    refusal-precision  8/8

Getting there needed three fixes that only showed up once scores were printed
instead of assumed:

1. **Dense search was actively harmful on careers.** Career node text is a path
   plus a few job words, so every short label embeds ~0.3 from every other one
   and the ranking inverted — "college fees nahi bhar sakti" matched
   `Defence > NCC` at 0.355 while "doctor banna hai" matched `STEM > Medicine`
   at 0.325. The floor for short-label collections is now 0.45
   (`MIN_DENSE_SCORE_SHORT_LABELS`), so BM25 carries careers and dense only
   speaks when genuinely confident. The handbook keeps 0.34 — its chunks are
   long prose, which is where embeddings actually earn their place.
2. **Dotted abbreviations were unmatchable.** "C.A. foundation" tokenised to
   ['c', 'a', 'foundation'], so a student asking about CA could never reach it.
   Both tokenisers now collapse dotted abbreviations.
3. **Coverage alone refuses answerable questions.** "CA kitna time lagta hai"
   has four terms, only one of which exists in the corpus. A document matching
   a sufficiently rare term (IDF >= 3.5) now qualifies on that alone.

Before these, the probe returned a plausible-looking career for nearly every
nonsense query — which is worse than refusing, because it makes the closed-list
rule look satisfied while feeding Disha irrelevant nodes.

### Rebuild order

    python3 scripts/build_vocational.py
    python3 scripts/build_scholarships.py
    python3 scripts/build_pathway_tree.py
    agent/.venv/bin/python scripts/index_kb.py
- Two relevance floors keep the closed-list rule intact: nearest-neighbour
  search always returns something, so the dense arm has a cosine threshold
  (0.34) and the sparse arm requires a document to cover half the query's
  distinct terms. Verified: "quantum teleportation" and "best pizza in naples"
  both return nothing and fall through to log_refusal.
- Deployment host and key path moved out of `scripts/deploy-ec2.sh` into an
  untracked `scripts/deploy.env` (see `deploy.env.example`). A `.gitignore` now
  covers that, `.env`, `.env.local`, cases, recordings, and `data/raw/`.
- UNVERIFIED: no live call has exercised `search_handbook` yet. The tool and
  ranking are smoke-tested offline only.

## What exists already

- `data/career_tree.json` — 423-node closed career tree, LIVE behind the agent's
  `search_careers` tool (`agent/disha.py`). This is the only KB the agent uses today.
- `data/handbook_chunks.json` — 91 extracted text chunks, each
  `{source, page, text≤1500}`: 26 from the SD SEED Career Handbook (30 pp),
  65 from the CFA Society India Career Guide 2022 (80 pp). Extracted with pypdf;
  quality unreviewed. Raw PDFs in `data/raw/` (excluded from EC2 rsync).
- Qdrant already running on the EC2 box (`127.0.0.1:6333`, healthy) — available
  if vector search is wanted; NOT required for v1.

## Task 1 — handbook KB into the agent (~25 min)

1. Add `search_handbook(query)` tool to `agent/disha.py`, mirroring
   `search_careers`: load `handbook_chunks.json` once, keyword/substring rank
   (reuse `_match_rank`), return top 3 `{source, page, text}`.
2. Instruction addition: Disha may use handbook facts ONLY with attribution
   ("SD SEED handbook, page N") and must treat absence as not-in-list — the
   closed-list refusal rule extends to the handbook.
3. Emit a data event `{"type":"kb","source":...,"page":...}` so the UI can show
   source traceability.
4. Optional upgrade (only if time): embed chunks into the EC2 Qdrant and swap the
   keyword rank for vector search. Needs an embedding provider — OpenAI key in
   `.env` works (`text-embedding-3-small`). Not worth it before the demo works.

## Task 2 — user knowledge base / cross-session memory (~30 min)

Goal: rubric Memory L4 = returning student resumes their case.

1. Signups already land in `localStorage["disha.signups"]` (phone). Pass the
   phone (or a generated case id) as a participant attribute `disha.case` on
   reconnect; token route already forwards arbitrary attributes.
2. Agent: on join, if `disha.case` matches an existing file in `agent/cases/`,
   load its constraint/flag events into the system prompt ("what we already
   know") and greet with a resume line instead of a fresh intro.
3. Do NOT build auth. Case id in the URL/localStorage is enough for the demo.
4. Demo proof: end a call mid-way, reload, reconnect — Disha continues without
   re-asking the saved constraints.

## Guardrails carried from IDEA_SCOPE.md

- Judges score ONE Sarvam param (Voice). KB work must never delay voice polish.
- Same evidence can't score twice: resume-across-session → Memory; handbook
  citation visible in UI → supports JTBD/trust, not Voice.
- Never let the LLM answer career facts from its own knowledge — every fact
  traces to tree, handbook chunk, or refusal.

## Next single action when resuming

Add `search_handbook` to `agent/disha.py` (Task 1 step 1) and rerun
`make build`.
