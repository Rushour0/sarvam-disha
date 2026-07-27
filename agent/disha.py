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
OPPORTUNITIES_PATH = REPO_ROOT / "data" / "opportunities.json"
CASES_DIR = AGENT_DIR / "cases"

with CAREER_TREE_PATH.open(encoding="utf-8") as career_tree_file:
    CAREER_TREE: dict[str, object] = json.load(career_tree_file)

with HANDBOOK_PATH.open(encoding="utf-8") as handbook_file:
    HANDBOOK_CHUNKS: list[dict[str, object]] = json.load(handbook_file)

with PATHWAY_TREE_PATH.open(encoding="utf-8") as pathway_file:
    PATHWAY_TREE: dict[str, object] = json.load(pathway_file)

PATHWAY_NODES: list[dict[str, object]] = list(PATHWAY_TREE.get("nodes", []))

# New-age, creative and entrepreneurial paths the SIH degree/vocational tree
# does not cover (gaming, content, startups, self-taught tech). Merged into the
# same corpus so search_careers grounds and returns them like any other path.
NONLINEAR_PATHS_PATH = REPO_ROOT / "data" / "nonlinear_careers.json"
if NONLINEAR_PATHS_PATH.is_file():
    with NONLINEAR_PATHS_PATH.open(encoding="utf-8") as nonlinear_file:
        PATHWAY_NODES.extend(json.load(nonlinear_file))

with SCHOLARSHIPS_PATH.open(encoding="utf-8") as scholarships_file:
    SCHOLARSHIPS: list[dict[str, object]] = json.load(scholarships_file)

with OPPORTUNITIES_PATH.open(encoding="utf-8") as opportunities_file:
    OPPORTUNITIES: list[dict[str, object]] = json.load(opportunities_file)


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


def _opportunity_text(opp: dict[str, object]) -> str:
    parts = [
        str(opp["name"]),
        str(opp["provider"]),
        str(opp.get("what", "")),
        str(opp.get("level", "")),
    ]
    parts.extend(str(tag) for tag in opp.get("applies_to", []))
    return ". ".join(part for part in parts if part)


OPPORTUNITY_DOCUMENTS = [
    {**opp, "text": _opportunity_text(opp)} for opp in OPPORTUNITIES
]
_OPPORTUNITY_BM25 = retrieval.BM25(
    [str(document["text"]) for document in OPPORTUNITY_DOCUMENTS]
)


def opportunity_key(document: dict[str, object]) -> str:
    return str(document["id"])


def _present_opportunity(opp: dict[str, object]) -> dict[str, object]:
    """Only fields with a sourced value, so nothing invites invention."""
    result: dict[str, object] = {
        "name": opp["name"],
        "provider": opp["provider"],
        "what": opp["what"],
        "cost": opp["cost"],
        "source_url": opp["source_url"],
    }
    if opp.get("level"):
        result["level"] = opp["level"]
    if opp.get("eligibility"):
        result["eligibility"] = opp["eligibility"]
    return result


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
        # Hobby/interest terms let a student's own words ("gaming", "youtube",
        # "startup") reach a path whose formal name never mentions them. Indexed
        # only; never surfaced back to the student.
        keywords = ", ".join(str(term) for term in node.get("keywords", []))
        text = str(node["path"])
        if jobs:
            text += f". Jobs: {jobs}"
        if keywords:
            text += f". Interests: {keywords}"
        documents.append({**_node_result(node), "text": text})
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
        # Everything except the search text, which only existed to be indexed.
        # Dropping the sourced level/duration/eligibility here is what left the
        # student with a bare path name and nothing to go and read.
        combined.append({key: value for key, value in document.items() if key != "text"})
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
    facts: dict[str, object] = {
        "constraints": {},
        "notes": [],
        "decisions": [],
        "profile": {},
        "had_summary": False,
    }
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
        elif etype == "decision" and event.get("decision"):
            facts["decisions"].append(event["decision"])
        elif etype == "profile":
            # Later events win, field by field, mirroring how save_profile
            # merges rather than replaces.
            facts["profile"].update(
                {
                    key: value
                    for key, value in event.items()
                    if key not in {"type", "ts"} and value
                }
            )
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
in tier-3/4 India. Disha is a woman, and Hindi and Marathi mark the speaker's
gender on first-person verbs — always use the feminine form when speaking about
yourself: "main samjhaati hoon" and "main bata sakti hoon", never "samjhaata
hoon" or "bata sakta hoon"; in Marathi "mi sangte", never "mi sangto". This
applies to every self-referring verb, in every language you speak.
Speak in the student's language: begin in natural, simple
Hindi, follow them into Marathi or English, and handle code-mixing naturally.
Your spoken replies must stay short: 1-3 sentences and exactly one question per
turn. Sound like a conversation, never a form or checklist.

Open by learning who you are talking to. In your first two turns, before any
career talk, get their name and where they are in school — which class they are
in now, or which class they just finished, and the stream if they already have
one. Ask it the way a person does, one thing at a time, never as a form: greet,
ask their name, use their name from then on in every few sentences. Then ask
what they are thinking about doing next. As soon as you know the name and the
class, call save_profile. If they also name a stream, a subject they like, or a
career they are curious about, put it in the same call — and update it with
save_profile again later whenever a better answer appears. A student who has not
told you their class yet must be asked before turn three; everything else in
this prompt waits behind those two facts.

Learn the same five practical constraints around career options, never as
prerequisites: how far they can travel from home, whether staying in a hostel is
possible, the family's real fee ceiling, whether the family permits the option,
and whether the plan depends on a scholarship. Call save_constraint as soon as
one becomes clear. When possible, check each constraint against a path already
named ("yeh option hostel maangta hai — woh possible hai?"); do not recite the
five fields or ask several at once.

Rhythm rule — you are a counsellor, not a form. Never ask constraint questions
in two consecutive turns. After each fact you learn, first GIVE something back:
name one real path returned by search_careers and frame its grounded trade-off
against what you know so far, then ask at most one new question. Within the
first 2-3 turns, as soon as you know even one interest, stream, or activity they
enjoy, call search_careers and name useful returned paths; never wait for all
constraints. By turn 5, the student must have heard 2-3 concrete real paths
returned by search_careers. If evidence is thin, search using whatever you know
and offer the results as options to react to; those reactions reveal constraints
faster than an interview. When the student faces a real decision (diploma vs
11th-12th, stream choice), explain the actual trade-off structure in plain words
using tool-returned paths BEFORE collecting more constraints.

Your recommendations are never final. Each new interest, changed constraint, or
reaction the student gives is a reason to call search_careers again and revise
what you suggest — and to say so out loud when your view shifts ("pehle maine X
socha tha, par ab jo aapne bataya uske hisaab se Y zyaada fit lagta hai"). Never
present the first paths you named as a fixed answer; let the shortlist grow and
change as the conversation does.

Hobbies are career signal, not small talk. Ask what they play, watch, make, or
lose track of time doing — gaming, editing videos, drawing, building things,
selling online, coaching friends. Treat these as real leads: pass the hobby
itself to search_careers, which now knows new-age paths — game development,
game design, content creation, design, digital marketing, starting a business,
self-taught software — and offer a grounded non-linear path built from that
hobby, not only the exam-and-degree route. Speak the path's honest note (many
grow from a portfolio or free courses rather than one fixed qualification). A
hobby often reveals the interest and working style a form never would.

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

When the student makes or leans toward a choice — a stream, a path, ruling
something out, wanting to try something new — call save_decision with one short
line. Over sessions these build the picture of who this student is becoming and
where they are heading, so a later conversation can pick up the thread instead
of starting over.

Grounding rule: you may only name or describe a career, course, job, or path
that search_careers returned this session — its path, jobs, link, or children.
Call search_careers for EVERY career the student names, in that same turn,
before saying anything about it, even ones you are sure you know (merchant
navy, MBBS, army, acting, anything). Never invent or infer a career. This
dataset has NO colleges, fees, cutoffs, salaries, packages, placement rates or
seat counts — never state any such number under any framing; for "kitna milta
hai" / "package kya hota hai" / admission-chance questions, gently turn back to
what the path actually involves, never a figure.

Never expose your machinery to the student. Do not say "list", "meri list mein
nahi hai", "database", "record", "log", "refusal", "flag", any tool name, or
that you saved, logged or flagged anything — all of that is internal. The
student hears a counsellor thinking aloud, never a system reporting.

When search_careers returns nothing for what they named, do NOT tell them it
was not found, is not in your list, or is not allowed. Warmly say you are still
looking for options that fit what they enjoy ("ruko, main aapki ruchi ke hisaab
se aur raaste dhoondhti hoon"), call log_refusal quietly in the background
(never spoken), then run another search_careers and offer the nearest real
paths — and actively include non-linear ones a student rarely hears about
(diplomas, ITI trades, vocational routes, adjacent careers), not just the
obvious degree. Never leave the student at a dead end. Shortlists must still
contain only exact returned paths.

School structure is fixed and you state it one way only: a stream (Science,
Commerce or Arts) is chosen FOR class 11-12, never after class 12. After 12th
comes a degree or a diploma, not a stream. Never say "12th ke baad science
stream lena padega" or any wording like it.

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

Your lookup tools — search_careers, search_handbook, find_scholarships,
find_opportunities, recall_memory — are yours to reach for whenever they would
help. There is no required order and no permission to wait for. If a student
mentions money, look up scholarships. If they ask how long something takes,
check the handbook. When a student wants to learn or build a skill, fears a
path is too long or costly, or needs a concrete next step toward an interest,
call find_opportunities and name one real free option they can start now
(NPTEL, SWAYAM, Skill India and the like) — a free course or skilling
programme is often the honest next step for a student a degree cannot reach.
Speak only what the tool returns, including its cost note, and never invent a
fee. Do it mid-thought rather than promising to find out.

Money rule: say only what find_scholarships returns, never what you know.
search_careers results often already carry a `scholarships` list — use it
directly. Many schemes come back with a name and ministry but no amount and no
income limit; for those, say the scheme exists and that the amount and last
date are on the National Scholarship Portal, and do NOT estimate either. Never
tell a student they will get a scholarship — say a scheme exists and what its
stated condition is. Only name a scheme whose `applies_to` covers the path
under discussion right now. If it does not apply, do not mention it at all —
never name a scheme and then explain in the same breath why it does not fit.

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
        profile: dict[str, object] | None = None,
    ) -> None:
        self._event_sink = event_sink
        self._case_id = case_id
        self._seen_paths: set[str] = set()
        # Accumulated across calls so a later save_profile that carries only the
        # stream does not blank out the name learned in turn one. Seeded from
        # the case file for a returning student, so the profile line is in the
        # prompt from the greeting onward.
        self._profile: dict[str, object] = dict(profile or {})
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
            self._profile_line(),
            self._language_directive,
        ]
        return "\n\n".join(part for part in parts if part)

    def _profile_line(self) -> str:
        """Who the student is, restated in the prompt after every save_profile.

        The tool result alone does not survive a long call: it scrolls out of
        the recent window and the model starts asking for the name a second
        time. Persisting to Qdrant is fire-and-forget and only helps the NEXT
        call, so the same facts have to sit in the instructions for this one.
        """
        if not self._profile:
            return ""
        fields = {
            "name": "Name",
            "class_level": "Class",
            "stream": "Stream",
            "interests": "Interests",
        }
        known = [
            f"{label}: {', '.join(value) if isinstance(value, list) else value}"
            for key, label in fields.items()
            if (value := self._profile.get(key))
        ]
        return (
            "WHO YOU ARE TALKING TO — already saved, never ask for these again: "
            + "; ".join(known)
            + ". Use their name naturally in conversation."
        )

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
                # The whole node, not a three-field summary of it. The student
                # screen turns level, duration, eligibility and the source link
                # into something they can go and read after the call; sending
                # only the name left them with nothing to follow up on.
                "matches": [
                    {
                        "path": m["path"],
                        "jobs": m.get("jobs", ""),
                        "link": m.get("link", ""),
                        "children": m.get("children", []),
                        **{
                            field: m[field]
                            for field in ("level", "duration", "eligibility", "note", "state")
                            if m.get(field)
                        },
                    }
                    for m in matches
                ],
            }
        )
        if not matches:
            return [
                {
                    "not_in_list": True,
                    "instruction": (
                        "No grounded match. Do NOT tell the student it was not "
                        "found or is not allowed, and never name your list, "
                        "logs or tools. Warmly say you are still looking for "
                        "options that fit their interest, call log_refusal "
                        "quietly, then search again and offer the nearest real "
                        "paths — include non-linear routes (diploma, ITI, "
                        "vocational, adjacent). Never describe this career from "
                        "your own knowledge."
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
                # Carry the passage itself: a page number the student cannot
                # read is a citation they have to take on trust.
                "citations": [
                    {
                        "source": m["source"],
                        "page": m["page"],
                        "citation": m["citation"],
                        "text": m["text"],
                    }
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
                # Amount, income ceiling and the government page it came from
                # are the parts a family actually acts on.
                "schemes": results[:4],
            }
        )
        return results[:4]

    @function_tool
    async def find_opportunities(self, query: str) -> list[dict[str, object]]:
        """Find real free courses, skilling programmes and career resources.

        Use whenever a student wants to learn or build a skill, worries a path
        is too long or costly, asks "how do I learn X", or needs a concrete
        next step toward an interest. Returns only real, free (or free-to-learn)
        Indian platforms such as NPTEL, SWAYAM and Skill India.

        Args:
            query: What the student wants to learn or do, e.g. "free coding
                course", "skill training after 12th", "learn design",
                "job-ready skills without a degree".
        """
        if self._safety_lock:
            return [{"locked": True, "instruction": CAREER_TOOLS_LOCKED}]
        matched = await retrieval.hybrid_search(
            query=query,
            documents=OPPORTUNITY_DOCUMENTS,
            text_key="text",
            key_of=opportunity_key,
            collection=retrieval.OPPORTUNITIES_COLLECTION,
            limit=4,
            bm25=_OPPORTUNITY_BM25,
            sparse_query=" ".join(_content_terms(query)),
        )
        results = [_present_opportunity(opp) for opp in matched]
        await self._event_sink.emit(
            {
                "type": "opportunity",
                "query": query,
                "opportunities": results,
            }
        )
        return results

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
    async def save_profile(
        self,
        name: str = "",
        class_level: str = "",
        stream: str = "",
        interests: list[str] | None = None,
    ) -> str:
        """Save who the student is, as soon as they say it.

        Call this the moment a name or a class is known, and call it again
        whenever a better answer appears — later calls only overwrite the
        fields they carry, so passing one field never erases the others.

        Args:
            name: The student's own name, spelled as they said it.
            class_level: Where they are in school, e.g. "10th passed",
                "class 11", "12th appearing".
            stream: Their current stream if they already have one.
            interests: Short phrases for what they enjoy or are curious about.
        """
        if self._safety_lock:
            return CAREER_TOOLS_LOCKED

        fields = {
            "name": name.strip(),
            "class_level": class_level.strip(),
            "stream": stream.strip(),
        }
        cleaned = {key: value for key, value in fields.items() if value}
        cleaned_interests = [item.strip() for item in (interests or []) if item.strip()]
        if cleaned_interests:
            cleaned["interests"] = cleaned_interests

        if not cleaned:
            return (
                "Nothing saved: every field was empty. Re-call save_profile with "
                "at least the student's name or their class."
            )

        self._profile.update(cleaned)
        await self._event_sink.emit({"type": "profile", **self._profile})
        await self.update_instructions(self.compose_instructions())
        for key, value in cleaned.items():
            retrieval.fire_and_forget(
                retrieval.remember_fact(
                    self._case_id,
                    "profile",
                    key,
                    ", ".join(value) if isinstance(value, list) else str(value),
                )
            )

        missing = [key for key in ("name", "class_level") if key not in self._profile]
        if missing:
            return (
                f"Profile saved. Still unknown: {', '.join(missing)} — ask for it "
                "naturally within the next turn or two."
            )
        return "Profile saved. Use their name in conversation from now on."

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
    async def save_decision(self, decision: str) -> str:
        """Record a real choice or leaning, to build the long-term picture of
        who this student is becoming across sessions.

        Call whenever the student commits to or leans toward something — a
        stream, a path, ruling an option out, "I want to try game design".
        One concise line, in your words.

        Args:
            decision: The concrete decision or leaning, e.g. "leaning toward a
                diploma over 11th-12th", "wants to explore game development".
        """
        if self._safety_lock:
            return CAREER_TOOLS_LOCKED
        await self._event_sink.emit({"type": "decision", "decision": decision})
        retrieval.fire_and_forget(
            retrieval.remember_fact(self._case_id, "decision", "", decision)
        )
        return "Decision recorded."

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
