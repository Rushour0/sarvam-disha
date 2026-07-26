from __future__ import annotations

import asyncio
import json
import os
import re
import time
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, TypedDict

from livekit import rtc
from livekit.agents import Agent, function_tool

import retrieval


AGENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = AGENT_DIR.parent
CAREER_TREE_PATH = REPO_ROOT / "data" / "career_tree.json"
HANDBOOK_PATH = REPO_ROOT / "data" / "handbook_chunks.json"
PATHWAY_TREE_PATH = REPO_ROOT / "data" / "pathway_tree.json"
SCHOLARSHIPS_PATH = REPO_ROOT / "data" / "scholarships.json"
CASES_DIR = AGENT_DIR / "cases"

with CAREER_TREE_PATH.open(encoding="utf-8") as career_tree_file:
    CAREER_TREE: dict[str, object] = json.load(career_tree_file)

with HANDBOOK_PATH.open(encoding="utf-8") as handbook_file:
    HANDBOOK_CHUNKS: list[dict[str, object]] = json.load(handbook_file)

with PATHWAY_TREE_PATH.open(encoding="utf-8") as pathway_file:
    PATHWAY_TREE: dict[str, object] = json.load(pathway_file)

PATHWAY_NODES: list[dict[str, object]] = list(PATHWAY_TREE.get("nodes", []))

with SCHOLARSHIPS_PATH.open(encoding="utf-8") as scholarships_file:
    SCHOLARSHIPS: list[dict[str, object]] = json.load(scholarships_file)


ConstraintName = Literal[
    "distance_from_home",
    "hostel_needed",
    "fee_ceiling",
    "family_permission",
    "scholarship_dependence",
]
WellbeingType = Literal[
    "distress",
    "family_pressure",
    "choice_paralysis",
    "self_harm",
]


class StrengthItem(TypedDict):
    label: str
    evidence_quote: str


_NON_SEARCHABLE_KEYS = frozenset({"jobs", "link"})
_WORD_RE = re.compile(r"[a-z0-9]+")
_STREAMS_NODE = CAREER_TREE.get("Streams")
STREAM_NAMES: frozenset[str] = (
    frozenset(_STREAMS_NODE) if isinstance(_STREAMS_NODE, dict) else frozenset()
)
_STREAM_NAME_BY_CASEFOLD = {
    stream_name.strip().casefold(): stream_name for stream_name in STREAM_NAMES
}


_DOTTED_RE = re.compile(r"(?<=\b[a-z])\.(?=[a-z]\b|[a-z]{2,}\b)", re.I)


def _normalise(text: str) -> str:
    """Fold to plain lowercase words, collapsing dotted abbreviations.

    "C.A." has to become "ca" and "B.Sc." "bsc", or a student who says the
    acronym never reaches the node named with the dots."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(_WORD_RE.findall(_DOTTED_RE.sub("", ascii_text).casefold()))


def _match_rank(query: str, node_name: str) -> tuple[int, int, int] | None:
    normalised_query = _normalise(query)
    normalised_name = _normalise(node_name)
    if not normalised_query or not normalised_name:
        return None

    if normalised_query == normalised_name:
        return (0, 0, len(normalised_name))
    if normalised_query in normalised_name:
        return (1, len(normalised_name) - len(normalised_query), len(normalised_name))
    if normalised_name in normalised_query:
        return (2, len(normalised_query) - len(normalised_name), len(normalised_name))

    query_words = [word for word in normalised_query.split() if len(word) >= 2]
    if query_words and all(
        any(query_word in name_word for name_word in normalised_name.split())
        for query_word in query_words
    ):
        return (3, len(normalised_name) - len(normalised_query), len(normalised_name))
    return None


def _walk_nodes(
    tree: dict[str, object],
    path: tuple[str, ...] = (),
) -> Iterator[tuple[str, dict[str, object], tuple[str, ...]]]:
    for name, node in tree.items():
        if name in _NON_SEARCHABLE_KEYS:
            continue
        node_path = (*path, name)
        if node is None:
            yield name, {}, node_path
        elif isinstance(node, dict):
            yield name, node, node_path
            yield from _walk_nodes(node, node_path)


def search_career_tree(query: str, limit: int = 5) -> list[dict[str, object]]:
    """Exact-name arm over the pathway tree. No I/O, no vectors."""
    ranked: list[tuple[tuple[int, int, int], str, str, dict[str, object]]] = []
    for node in PATHWAY_NODES:
        rank = _match_rank(query, str(node["name"]))
        if rank is not None:
            ranked.append((rank, str(node["name"]).casefold(), str(node["path"]), node))

    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    return [_node_result(node) for _, _, _, node in ranked[:limit]]


def _scholarship_text(scheme: dict[str, object]) -> str:
    parts = [
        str(scheme["name"]),
        str(scheme["provider"]),
        str(scheme.get("state") or ""),
        str(scheme.get("eligibility", "")),
    ]
    parts.extend(str(tag) for tag in scheme.get("applies_to", []))
    return ". ".join(part for part in parts if part)


SCHOLARSHIP_DOCUMENTS = [
    {**scheme, "text": _scholarship_text(scheme)} for scheme in SCHOLARSHIPS
]
_SCHOLARSHIP_BM25 = retrieval.BM25(
    [str(document["text"]) for document in SCHOLARSHIP_DOCUMENTS]
)


def scholarship_key(document: dict[str, object]) -> str:
    return str(document["id"])


def _present_scholarship(scheme: dict[str, object]) -> dict[str, object]:
    """Only fields with a sourced value, so nothing invites invention."""
    result: dict[str, object] = {
        "name": scheme["name"],
        "provider": scheme["provider"],
        "level": scheme["level"],
        "eligibility": scheme["eligibility"],
        "source_url": scheme["source_url"],
    }
    if scheme.get("amount"):
        result["amount"] = scheme["amount"]
    if scheme.get("income_ceiling"):
        result["income_ceiling"] = scheme["income_ceiling"]
    if scheme.get("state"):
        result["state"] = scheme["state"]
    return result


def scholarships_for_tags(tags: list[str], limit: int = 4) -> list[dict[str, object]]:
    """Schemes whose applies_to overlaps a node's scholarship_tags."""
    wanted = set(tags)
    if not wanted:
        return []
    matched = [
        scheme
        for scheme in SCHOLARSHIPS
        if wanted & set(str(tag) for tag in scheme.get("applies_to", []))
    ]
    # A sourced amount is more useful to a student than a bare scheme name.
    matched.sort(key=lambda scheme: (scheme.get("amount") is None, str(scheme["name"])))
    return [_present_scholarship(scheme) for scheme in matched[:limit]]


def tags_for_path(path: str) -> list[str]:
    for node in PATHWAY_NODES:
        if node["path"] == path:
            return [str(tag) for tag in node.get("scholarship_tags", [])]
    return []


_NAME_BY_ID = {node["id"]: node["name"] for node in PATHWAY_NODES}


def _node_result(node: dict[str, object]) -> dict[str, object]:
    """Shape a pathway node the way the tool contract expects it."""
    children = [
        _NAME_BY_ID[child_id]
        for child_id in list(node.get("children", []))[:8]
        if child_id in _NAME_BY_ID
    ]
    result: dict[str, object] = {
        "path": node["path"],
        "jobs": ", ".join(node.get("jobs", [])),
        "link": node.get("link", ""),
        "children": children,
    }
    # Only surface fields that carry a sourced value — an empty duration
    # invites the model to fill one in.
    for field in ("level", "duration", "eligibility", "note", "state"):
        if node.get(field):
            result[field] = node[field]

    # Attach the schemes this path is tagged for, so a career lookup already
    # carries its money answer. Waiting for a second tool call means the
    # affordability question only gets answered when the model remembers to
    # ask it, and affordability is the whole reason these students hesitate.
    schemes = scholarships_for_tags(
        [str(tag) for tag in node.get("scholarship_tags", [])], limit=2
    )
    if schemes:
        result["scholarships"] = schemes
    return result


def build_career_documents() -> list[dict[str, object]]:
    """One searchable document per pathway node.

    Node names alone are not enough to find a node: a student says "teacher
    banna hai", and the only place the word "teacher" appears is the node's
    jobs list, not its name ("Bachelor of Education (B.Ed)"). Searching the
    name plus the jobs list is what connects how a student talks about work to
    how the dataset names qualifications.
    """
    documents: list[dict[str, object]] = []
    for node in PATHWAY_NODES:
        jobs = ", ".join(node.get("jobs", []))
        documents.append(
            {
                **_node_result(node),
                "text": f"{node['path']}. Jobs: {jobs}" if jobs else str(node["path"]),
            }
        )
    return documents


CAREER_DOCUMENTS = build_career_documents()
_CAREER_BM25 = retrieval.BM25([str(document["text"]) for document in CAREER_DOCUMENTS])


def career_document_key(document: dict[str, object]) -> str:
    return str(document["path"])


_HANDBOOK_STOPWORDS = frozenset(
    """a an the of and or to in on at is are for what which how do does can i my
    me you your it its about with from please tell kya hai ke ki ka mein""".split()
)
_HANDBOOK_SNIPPET_CHARS = 420

_SHORT_SOURCE_NAMES = {
    "SD SEED Career Handbook": "SD SEED handbook",
    "CFA Society India Career Guide 2022": "CFA Society India career guide 2022",
}


def _content_terms(query: str) -> list[str]:
    """Query words worth searching on: no stopwords, nothing too short.

    Two-letter words are dropped as noise, except when the student said them in
    capitals — "CA kitna time lagta hai" is a question about Chartered
    Accountancy, and dropping "CA" left it with no content terms at all.
    """
    shouted = {word.casefold() for word in re.findall(r"\b[A-Z]{2}\b", query)}
    return [
        word
        for word in _normalise(query).split()
        if word not in _HANDBOOK_STOPWORDS and (len(word) >= 3 or word in shouted)
    ]


_handbook_terms = _content_terms


async def search_careers_ranked(query: str, limit: int = 5) -> list[dict[str, object]]:
    """Hybrid career search: exact name matches first, then RRF-fused recall.

    Exact node-name matches keep their priority — a student who says "B.Com"
    must get the B.Com node at the top, not whatever the vectors liked. Hybrid
    results fill the rest, which is what catches "teacher banna hai" landing on
    B.Ed through its jobs text.
    """
    name_matches = search_career_tree(query, limit)
    seen = {str(match["path"]) for match in name_matches}

    terms = _content_terms(query)
    fused: list[dict[str, object]] = []
    if terms:
        fused = await retrieval.hybrid_search(
            query=query,
            documents=CAREER_DOCUMENTS,
            text_key="text",
            key_of=career_document_key,
            collection=retrieval.CAREERS_COLLECTION,
            limit=limit,
            bm25=_CAREER_BM25,
            sparse_query=" ".join(terms),
            min_dense_score=retrieval.MIN_DENSE_SCORE_SHORT_LABELS,
        )

    combined = list(name_matches)
    for document in fused:
        if str(document["path"]) in seen:
            continue
        seen.add(str(document["path"]))
        combined.append(
            {
                "path": document["path"],
                "jobs": document["jobs"],
                "link": document["link"],
                "children": document["children"],
            }
        )
    return combined[:limit]


def _snippet_around(text: str, terms: list[str]) -> str:
    """Return the window of the chunk that actually answers the query."""
    lowered = text.casefold()
    positions = [lowered.find(term) for term in terms]
    hit = min((pos for pos in positions if pos >= 0), default=-1)
    if hit < 0 or len(text) <= _HANDBOOK_SNIPPET_CHARS:
        return text[:_HANDBOOK_SNIPPET_CHARS].strip()

    start = max(0, hit - _HANDBOOK_SNIPPET_CHARS // 3)
    snippet = text[start : start + _HANDBOOK_SNIPPET_CHARS].strip()
    return f"…{snippet}" if start > 0 else snippet


def handbook_chunk_key(chunk: dict[str, object]) -> str:
    """Stable id for a chunk, shared by the local copy and the Qdrant payload."""
    return f"{chunk.get('source', '')}#{chunk.get('page', 0)}"


_HANDBOOK_BM25 = retrieval.BM25([str(chunk.get("text", "")) for chunk in HANDBOOK_CHUNKS])


def _present_chunk(chunk: dict[str, object], terms: list[str]) -> dict[str, object]:
    source = str(chunk.get("source", ""))
    page = chunk.get("page", 0)
    return {
        "source": source,
        "page": page,
        "citation": f"{_SHORT_SOURCE_NAMES.get(source, source)}, page {page}",
        "text": _snippet_around(str(chunk.get("text", "")), terms),
    }


async def search_handbook_chunks(query: str, limit: int = 3) -> list[dict[str, object]]:
    """Hybrid-rank the handbook chunks: Qdrant dense + BM25, fused by RRF.

    Falls back to BM25 alone whenever Qdrant or the embedding call is
    unavailable, so a local `make dev` run needs no vector store at all.
    """
    terms = _handbook_terms(query)
    if not terms:
        return []

    matches = await retrieval.hybrid_search(
        query=query,
        documents=HANDBOOK_CHUNKS,
        text_key="text",
        key_of=handbook_chunk_key,
        collection=retrieval.HANDBOOK_COLLECTION,
        limit=limit,
        bm25=_HANDBOOK_BM25,
        sparse_query=" ".join(terms),
    )
    return [_present_chunk(chunk, terms) for chunk in matches]


def _safe_room_filename(room_name: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", room_name).strip("._")
    return safe_name or "unknown-room"


def load_case_facts(case_key: str) -> dict[str, object]:
    """Personal memory for a returning case: distilled facts only, per
    MEMORY-DESIGN.md — constraints and notes, never transcripts or flags."""
    path = CASES_DIR / f"{_safe_room_filename(case_key)}.json"
    facts: dict[str, object] = {"constraints": {}, "notes": [], "had_summary": False}
    if not path.is_file():
        return facts
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = event.get("type")
        if etype == "constraint" and "name" in event:
            facts["constraints"][event["name"]] = event.get("value", "")
        elif etype == "note" and event.get("note"):
            facts["notes"].append(event["note"])
        elif etype == "summary":
            facts["had_summary"] = True
    return facts


def _append_json_line(path: Path, event: dict[str, object]) -> None:
    line = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
    descriptor = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, line)
    finally:
        os.close(descriptor)


class EventSink:
    def __init__(self, room: rtc.Room, room_name: str) -> None:
        self._room = room
        self._path = CASES_DIR / f"{_safe_room_filename(room_name)}.json"
        self._lock = asyncio.Lock()

    async def emit(self, event: dict[str, object]) -> None:
        event = {"type": event["type"], "ts": int(time.time()), **event}
        payload = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode()

        async with self._lock:
            CASES_DIR.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(_append_json_line, self._path, event)
            await self._room.local_participant.publish_data(
                payload=payload,
                topic="disha",
                reliable=True,
            )


DISHA_INSTRUCTIONS = """
You are Disha, a warm career counsellor for class 11-12 and fresh-pass students
in tier-3/4 India. Speak in the student's language: begin in natural, simple
Hindi, follow them into Marathi or English, and handle code-mixing naturally.
Your spoken replies must stay short: 1-3 sentences and exactly one question per
turn. Sound like a conversation, never a form or checklist.

Indirectly learn five practical constraints through concrete life questions,
one at a time: how far they can travel from home, whether staying in a hostel is
possible, the family's real fee ceiling, whether the family permits the option,
and whether the plan depends on a scholarship. Call save_constraint as soon as
one becomes clear. Do not recite the five fields or ask several at once.

Rhythm rule — you are a counsellor, not a form. Never ask constraint questions
in two consecutive turns. After each fact you learn, first GIVE something back:
one concrete, grounded observation or trade-off from search_careers results
("diploma nantar lateral entry ne degree la jaata yete" style), then at most
one new question. When the student faces a real decision (diploma vs 11th-12th,
stream choice), explain the actual trade-off structure in plain words using
tool-returned paths BEFORE collecting more constraints. The student should
leave every third turn knowing something they did not know.

When the student interrupts you, their words are the priority: your next reply
must be one complete new sentence that directly answers what they just said.
Never emit a fragment or continuation of the sentence that was cut off, and
never restart your greeting. If the interruption contains a wrong premise
("10th ke baad direct MBBS hota hai na?"), your VERY FIRST word must be the
correction — "Nahi —" / "नहीं —" — followed by the correct fact from tool
results. No preamble, no source name first, no soft opener. If your earlier
point still matters, reconnect to it later in one short clause.

Numbers and names arrive garbled from speech sometimes. Repeat back every
number, class, fee amount, and institution name in your next sentence to
confirm ("gyarah-baarah class, theek?"). If a proper noun sounds unclear, ask
the student to say it again slowly instead of guessing.

Advice the student brings (cousin, WhatsApp, agent visits) is never endorsed as
correct just because someone they trust said it. Acknowledge the care behind
it, then check it against your list: "chalo dekhte hain yeh aapki situation
mein fit hota hai ya nahi" — and give your view only from tool results and the
student's saved constraints.

When the student shares a personal fact that will matter for guidance later
(father's occupation, a sibling's city, a responsibility at home, a subject
they love or fear), call remember_student with one short note. Use it
sparingly — notable facts only, never transcripts or feelings.

Closed-list rule: career exploration is allowed ONLY through search_careers.
For EVERY career the student names, you MUST call search_careers in that same
turn before saying anything about it — even careers you are certain you know
(merchant navy, MBBS, army, acting, anything). If the tool returns
not_in_list, your reply MUST BEGIN with the words "meri list mein nahi hai"
(said naturally in the student's language), then call log_refusal, then offer
the nearest option that IS in a tool result. Before naming or discussing any
career, course, job, or path, call
search_careers and use only names and facts present in that tool's returned
path, jobs, link, or children. Never invent or infer a career. This dataset
contains NO colleges, fees, cutoffs, salaries, placement rates, or seat counts
— never state any of those numbers for any career under any framing. That
includes salary questions ("kitna milta hai", "package kya hota hai") and
admission chances: the answer is always that it is not in your list, plus
log_refusal. If search_careers returns nothing for a career the student names
(merchant navy, MBBS, anything, however famous), you may NOT describe it from
your own knowledge — say it is not in your list, call log_refusal, and offer
the nearest returned path instead. Do not imply that no such option exists
outside this list. Shortlists must contain exact returned paths only.

Handbook rule: search_handbook is your only source for course durations, degree
full forms, eligibility, entrance-exam names, and study-path detail. It searches
two printed guides and returns each result with a citation. You may say a
handbook fact ONLY while naming its citation out loud in the same sentence
("SD SEED handbook, page 5, ke hisaab se B.Tech chaar saal ka hai"). Never
paraphrase a handbook fact without the citation, and never quote a citation you
did not just receive from the tool. The closed-list rule extends here: if
search_handbook returns nothing for what was asked, that fact is not in your
list — say so gently and call log_refusal. The handbook adds detail to careers
found through search_careers; it never introduces a career that search_careers
did not return. Some chunks are rough print extracts: read only the parts that
form clean sentences and skip any garbled fragment rather than speaking it.

Your four lookup tools — search_careers, search_handbook, find_scholarships,
recall_memory — are yours to reach for whenever they would help. There is no
required order and no permission to wait for. If a student mentions money, look
up scholarships. If they ask how long something takes, check the handbook. Do
it mid-thought rather than promising to find out.

Money rule: say only what find_scholarships returns, never what you know.
search_careers results often already carry a `scholarships` list — use it
directly. Many schemes come back with a name and ministry but no amount and no
income limit; for those, say the scheme exists and that the amount and last
date are on the National Scholarship Portal, and do NOT estimate either. Never
tell a student they will get a scholarship — say a scheme exists and what its
stated condition is.

Vocational paths (ITI trades, army entries) carry a `note` saying the minimum
qualification varies and must be confirmed with the ITI or the recruitment
notification. Speak that note whenever you name one, and never fill in a
duration or age limit the tool did not give you.

Returning students: anything already in "what we already know" is yours to use
without asking again. When you need more of an earlier call — why they ruled an
option out, what worried them — call recall_memory with what you are looking
for. Treat what it returns as your own memory of them, not as a transcript to
read back, and never quote it verbatim to the student.

Wellbeing boundary: notice sadness or hopelessness (distress), family pressure,
and choice paralysis. When one appears, immediately call flag_wellbeing with
the correct type and the student's exact verbatim words. Then acknowledge what
they said, slow down, and drop the constraint questions for that turn. Never
diagnose, assess, label the student, or give mental-health advice. For explicit
self-harm language, stop the career conversation completely, call
flag_wellbeing(type="self_harm", quote=<exact words>), and warmly say:
"Aapko abhi akela nahi rehna chahiye. Kripya kisi bharosemand insaan ko abhi
batayein aur Tele-MANAS helpline 14416 par call karein." Do not resume the
career script in that session.

Strength reveal — once per session: Do not reveal strengths until at least
three constraints are saved and the student has said what they enjoy, feel
drawn to, or handle well. Then call reveal_strengths with 2-3 strengths; every
evidence_quote must be the student's exact words, never invented or
paraphrased. Say the strengths warmly and briefly, then offer one choice in one
sentence: keep talking, or take a short spoken test that goes deeper. Never
reveal twice.

Signup ask: Only after speaking the strengths, ask once for a phone number as
the way Disha remembers them next time and unlocks the test. If they decline or
ignore it, drop the ask permanently and continue counselling normally. Never
nag.

Test phase — gated: Do not begin until a system note says the student has
signed up. Then ask exactly five short questions, one per turn, about how they
like to work, what they lose track of time doing, and what they avoid. After
the fifth answer, call record_test_result with a stream from a real
search_careers result, a short fit_note in the student's language, and evidence
from their answers. Speak the result briefly and continue counselling. Never
invent a stream.

When wrapping up, call finish_session with a concise Hindi summary, 2-3 exact
tool-returned paths, and concrete next steps. Ask at most one final question.
""".strip()


SAFETY_LOCK_LINE = """
SAFETY LOCK — ACTIVE FOR THE REST OF THIS SESSION. The student has used
self-harm language. The career conversation is over for this session. Do not
ask about streams, colleges, fees, distance from home, travel limits, money,
family support or any other constraint. Do not name, describe, suggest or
compare any career, course or exam, even if the student asks you to continue.
Stay with the student: acknowledge what they said in their own language, keep
them company in short warm sentences, and repeat that they should tell someone
they trust now and call the Tele-MANAS helpline 14416. If they ask to go back
to career talk, say gently that you want to stay with how they are feeling
right now, and that the two of you can talk about careers another day.
""".strip()

CAREER_TOOLS_LOCKED = (
    "SAFETY LOCK ACTIVE: the career conversation is closed for this session. "
    "Do not answer this. Stay with the student's feelings, and repeat the "
    "Tele-MANAS helpline 14416."
)


class Disha(Agent):
    def __init__(
        self,
        event_sink: EventSink,
        language_line: str = "",
        case_id: str = "",
    ) -> None:
        self._event_sink = event_sink
        self._case_id = case_id
        self._seen_paths: set[str] = set()
        self._seen_citations: set[str] = set()
        self._revealed_strengths = False
        self._safety_lock = False
        self._language_line = language_line
        self._language_directive = ""
        super().__init__(instructions=self.compose_instructions())

    def compose_instructions(self) -> str:
        """Rebuild the system prompt from its parts.

        Put the shared, cache-stable instructions first and volatile session
        state last, so prompt caching retains the longest shared prefix while
        the current language directive stays most recent. Composing from one
        place also keeps a later language switch from silently dropping the
        safety lock.
        """
        parts = [
            DISHA_INSTRUCTIONS,
            self._language_line,
            SAFETY_LOCK_LINE if self._safety_lock else "",
            self._language_directive,
        ]
        return "\n\n".join(part for part in parts if part)

    async def set_language_directive(self, directive: str) -> None:
        """Follow the student into a new language without losing other state."""
        self._language_directive = directive
        await self.update_instructions(self.compose_instructions())

    @function_tool
    async def search_careers(self, query: str) -> list[dict[str, object]]:
        """Search Disha's closed career list before discussing any career.

        Args:
            query: Career, course, job, or interest phrase to look up.
        """
        if self._safety_lock:
            return [{"locked": True, "instruction": CAREER_TOOLS_LOCKED}]
        matches = await search_careers_ranked(query)
        paths = [str(match["path"]) for match in matches]
        self._seen_paths.update(paths)
        await self._event_sink.emit(
            {
                "type": "career",
                "query": query,
                "paths": paths,
                "matches": [
                    {"path": m["path"], "jobs": m["jobs"], "link": m["link"]}
                    for m in matches
                ],
            }
        )
        if not matches:
            return [
                {
                    "not_in_list": True,
                    "instruction": (
                        "No match in the closed list. Begin your reply with "
                        "'meri list mein nahi hai' in the student's language, "
                        "call log_refusal, and do NOT describe this career "
                        "from your own knowledge."
                    ),
                }
            ]
        return matches

    @function_tool
    async def search_handbook(self, query: str) -> list[dict[str, object]]:
        """Search the two career handbooks for a fact worth quoting to the student.

        Args:
            query: The topic to look up, e.g. "B.Sc. duration" or "law entrance exam".
        """
        if self._safety_lock:
            return [{"locked": True, "instruction": CAREER_TOOLS_LOCKED}]
        matches = await search_handbook_chunks(query)
        for match in matches:
            self._seen_citations.add(str(match["citation"]))
        await self._event_sink.emit(
            {
                "type": "kb",
                "query": query,
                "citations": [
                    {"source": m["source"], "page": m["page"], "citation": m["citation"]}
                    for m in matches
                ],
            }
        )
        return matches

    @function_tool
    async def find_scholarships(self, query: str, path: str = "") -> list[dict[str, object]]:
        """Find government scholarship schemes for a student's situation or path.

        Args:
            query: What the student needs help with, e.g. "girl studying diploma",
                "SC student class 10", "ITI ki fees".
            path: Optional exact path returned by search_careers, to match schemes
                tagged for that kind of study.
        """
        by_tag = scholarships_for_tags(tags_for_path(path)) if path else []
        seen = {str(scheme["name"]) for scheme in by_tag}

        matched = await retrieval.hybrid_search(
            query=query,
            documents=SCHOLARSHIP_DOCUMENTS,
            text_key="text",
            key_of=scholarship_key,
            collection=retrieval.SCHOLARSHIPS_COLLECTION,
            limit=4,
            bm25=_SCHOLARSHIP_BM25,
            sparse_query=" ".join(_content_terms(query)),
        )

        results = list(by_tag)
        for scheme in matched:
            presented = _present_scholarship(scheme)
            if str(presented["name"]) not in seen:
                seen.add(str(presented["name"]))
                results.append(presented)

        await self._event_sink.emit(
            {
                "type": "scholarship",
                "query": query,
                "schemes": [
                    {"name": scheme["name"], "provider": scheme["provider"]}
                    for scheme in results[:4]
                ],
            }
        )
        return results[:4]

    @function_tool
    async def save_constraint(self, name: ConstraintName, value: str) -> str:
        """Save one practical constraint once the student has expressed it.

        Args:
            name: One of Disha's five supported constraint names.
            value: The student's concrete constraint in concise words.
        """
        if self._safety_lock:
            return CAREER_TOOLS_LOCKED
        await self._event_sink.emit(
            {
                "type": "constraint",
                "name": name,
                "value": value,
            }
        )
        retrieval.fire_and_forget(
            retrieval.remember_fact(self._case_id, "constraint", name, value)
        )
        return f"Saved {name}."

    @function_tool
    async def flag_wellbeing(self, type: WellbeingType, quote: str) -> str:
        """Flag a wellbeing signal for a human without diagnosing the student.

        Args:
            type: The observed signal category.
            quote: The student's exact verbatim words that triggered the flag.
        """
        await self._event_sink.emit(
            {
                "type": "flag",
                "flag_type": type,
                "quote": quote,
            }
        )
        if type == "self_harm" and not self._safety_lock:
            # Prompt wording alone did not hold: the career script resumed one
            # turn later through a constraint question. The lock also closes the
            # career tools, so it survives a later instruction rewrite.
            self._safety_lock = True
            await self.update_instructions(self.compose_instructions())
            return (
                "Flagged self_harm. SAFETY LOCK is now active for the rest of "
                "this session. Say, in the student's language: 'Aapko abhi "
                "akela nahi rehna chahiye. Kripya kisi bharosemand insaan ko "
                "abhi batayein aur Tele-MANAS helpline 14416 par call karein.' "
                "Then stay with their feelings. Ask no constraint question and "
                "name no career for the rest of this session."
            )
        return f"Flagged {type}; now slow down and acknowledge the student."

    @function_tool
    async def reveal_strengths(self, strengths: list[StrengthItem]) -> str:
        """Save evidence-bound strengths before revealing them to the student.

        Args:
            strengths: Two or three objects, each with a short strength label in
                the student's language and an evidence_quote containing the
                student's own exact verbatim words, never a paraphrase.
        """
        if self._safety_lock:
            return CAREER_TOOLS_LOCKED
        valid_strengths = [
            {
                "label": item["label"],
                "evidence_quote": item["evidence_quote"],
            }
            for item in strengths
            if item["evidence_quote"].strip()
        ]
        dropped_count = len(strengths) - len(valid_strengths)
        already_revealed = self._revealed_strengths

        if not valid_strengths:
            instruction = (
                "No strengths saved: every evidence_quote was empty or whitespace. "
                "Re-call reveal_strengths with the student's actual verbatim words."
            )
            if already_revealed:
                instruction += (
                    " Strengths were already revealed; do not repeat the reveal aloud."
                )
            return instruction

        await self._event_sink.emit(
            {
                "type": "strength",
                "strengths": valid_strengths,
            }
        )
        self._revealed_strengths = True

        instructions: list[str] = []
        if dropped_count:
            instructions.append(
                f"Saved the valid strengths, but dropped {dropped_count} item(s) "
                "because evidence_quote was empty or whitespace; re-call with the "
                "student's actual verbatim words for those items."
            )
        else:
            instructions.append("Strengths saved.")
        if already_revealed:
            instructions.append(
                "Strengths were already revealed; do not repeat the reveal aloud."
            )
        else:
            instructions.append(
                "Reveal the saved strengths warmly and briefly, then offer the "
                "choice to keep talking or take the short spoken test."
            )
        return " ".join(instructions)

    @function_tool
    async def record_test_result(
        self,
        stream: str,
        fit_note: str,
        evidence: list[str],
    ) -> str:
        """Save the result of the five-question spoken aptitude round.

        Args:
            stream: One canonical stream from a real search_careers result.
            fit_note: A short explanation of the fit in the student's language.
            evidence: The student's relevant answers from the spoken test.
        """
        if self._safety_lock:
            return CAREER_TOOLS_LOCKED
        canonical_stream = _STREAM_NAME_BY_CASEFOLD.get(stream.strip().casefold())
        if canonical_stream is None:
            valid_names = ", ".join(sorted(STREAM_NAMES))
            return (
                f"Invalid stream. Re-call record_test_result with one of: {valid_names}."
            )

        await self._event_sink.emit(
            {
                "type": "test_result",
                "stream": canonical_stream,
                "fit_note": fit_note,
                "evidence": evidence,
            }
        )
        return "Test result saved; speak it briefly and continue counselling."

    @function_tool
    async def remember_student(self, note: str) -> str:
        """Save one short notable personal fact that matters for guidance.

        Args:
            note: One concise fact, e.g. "father is a farmer near Nashik".
        """
        await self._event_sink.emit({"type": "note", "note": note})
        retrieval.fire_and_forget(
            retrieval.remember_fact(self._case_id, "note", "", note)
        )
        return "Noted."

    @function_tool
    async def recall_memory(self, query: str) -> list[dict[str, object]]:
        """Search what this returning student said or saved in earlier calls.

        Args:
            query: What you want to remember, e.g. "why she ruled out hostel".
        """
        return await retrieval.recall_case_memory(self._case_id, query)

    @function_tool
    async def log_refusal(self, asked_about: str) -> str:
        """Log an out-of-list request after telling the student it is not listed.

        Args:
            asked_about: The exact college, fee, cutoff, or absent career requested.
        """
        await self._event_sink.emit(
            {
                "type": "refusal",
                "asked_about": asked_about,
            }
        )
        return "Refusal logged."

    @function_tool
    async def finish_session(
        self,
        summary_hi: str,
        shortlist: list[str],
        next_steps: list[str],
    ) -> str:
        """Persist the final Hindi summary and closed-list shortlist.

        Args:
            summary_hi: Concise Hindi summary for the student and family.
            shortlist: Two or three exact paths returned by search_careers.
            next_steps: Concrete next actions for the student.
        """
        unknown_paths = [path for path in shortlist if path not in self._seen_paths]
        verified_shortlist = [path for path in shortlist if path in self._seen_paths]

        await self._event_sink.emit(
            {
                "type": "summary",
                "summary_hi": summary_hi,
                "shortlist": verified_shortlist,
                "next_steps": next_steps,
            }
        )
        if unknown_paths:
            return (
                "Summary saved without unverified paths. Search these first, then "
                f"retry with their exact returned paths: {unknown_paths}"
            )
        return "Session summary saved."
