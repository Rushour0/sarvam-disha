"""Hybrid retrieval for Disha: RRF fusion of Qdrant dense search and BM25.

Ported from the approach in fabri (`src/fabri/orchestrator/retrieval.py`): run a
dense arm and a sparse arm independently, then fuse by Reciprocal Rank Fusion so
neither signal has to be score-normalised against the other. Dense search alone
misses exact tokens a student says out loud ("B.Tech", "NEET", a college name);
BM25 alone misses paraphrase ("kitne saal ka hai" vs "duration"). Fusion covers
both, and agreement between the arms naturally floats to the top.

Everything degrades: if Qdrant is unreachable or the embedding call fails, the
dense arm returns nothing and callers still get BM25 results. A voice call must
never fail because a vector store is down.

Collections follow the fabri per-scope convention:
  disha_handbook                  — the two career handbooks, shared
  disha_conversation_<case_id>    — verbatim utterances for one case
  disha_person_<case_id>          — distilled personal facts for one case

Conversation and personal memory stay in separate collections on purpose; see
MEMORY-DESIGN.md for why mixing them is how a voice agent leaks one student's
life into another's call.
"""

from __future__ import annotations

import asyncio
import logging
import math
import os
import re
import time
import uuid
from collections import Counter

import httpx


logger = logging.getLogger("disha.retrieval")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333").rstrip("/")
EMBED_MODEL = os.environ.get("DISHA_EMBED_MODEL", "text-embedding-3-small")
EMBED_DIM = int(os.environ.get("DISHA_EMBED_DIM", "1536"))
HANDBOOK_COLLECTION = "disha_handbook"
CAREERS_COLLECTION = "disha_careers"
SCHOLARSHIPS_COLLECTION = "disha_scholarships"
OPPORTUNITIES_COLLECTION = "disha_opportunities"
# Nightly-refreshed external records (data/dynamic/*.json). One shared
# collection across all dynamic sources: the flexible schema means new sources
# just add rows, never a new collection to wire up.
DYNAMIC_COLLECTION = "disha_dynamic"

_QDRANT_TIMEOUT = float(os.environ.get("QDRANT_TIMEOUT", "3.0"))
_RRF_K = 20  # fabri's value: two short pools, so the web-scale 60 flattens rank

# Nearest-neighbour search always returns *something*, which would quietly break
# Disha's closed-list refusal: ask about a career the handbooks never mention and
# the dense arm still hands back its three least-unrelated pages. Cosine
# similarity below this is treated as "no match" so the refusal path survives.
_MIN_DENSE_SCORE = float(os.environ.get("DISHA_MIN_DENSE_SCORE", "0.34"))

# Short-label corpora need a much higher floor. A career node's text is a path
# plus a few job words, and embeddings of short label strings all sit ~0.3 from
# each other, so the ranking inverts: "college fees nahi bhar sakti" scored
# Defence > NCC at 0.355 while "doctor banna hai" scored STEM > Medicine at
# 0.325. Measured, not assumed. Above this floor dense still contributes; below
# it BM25 carries the query, which is where the real signal was all along.
MIN_DENSE_SCORE_SHORT_LABELS = float(
    os.environ.get("DISHA_MIN_DENSE_SCORE_LABELS", "0.45")
)

# IDF at or above this means the term appears in only a few percent of the
# corpus — discriminative enough that one match is real evidence.
_RARE_TERM_IDF = float(os.environ.get("DISHA_RARE_TERM_IDF", "3.5"))

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_UUID_NAMESPACE = uuid.UUID("6f5c1c2e-0f5e-4c6a-9f9a-0c9f2b8b7c11")

# One warning per process per subsystem, so a down Qdrant does not spam the log.
_warned: set[str] = set()


def _warn_once(key: str, message: str) -> None:
    if key not in _warned:
        _warned.add(key)
        logger.warning(message)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value).strip("_")
    return cleaned or "unknown"


def conversation_collection(case_id: str) -> str:
    return f"disha_conversation_{_slug(case_id)}"


def person_collection(case_id: str) -> str:
    return f"disha_person_{_slug(case_id)}"


def point_id(key: str) -> str:
    """Stable id so re-indexing the same fact updates instead of duplicating."""
    return str(uuid.uuid5(_UUID_NAMESPACE, key))


# ---------------------------------------------------------------------------
# Sparse arm: BM25
# ---------------------------------------------------------------------------


_DOTTED_RE = re.compile(r"(?<=\b[a-z])\.(?=[a-z]\b|[a-z]{2,}\b)", re.I)


def tokenize(text: str) -> list[str]:
    """Tokenize, collapsing dotted abbreviations first.

    Without this, "C.A. foundation" becomes ['c', 'a', 'foundation'] and a
    student asking about "CA" can never match the node that answers them. The
    same collapse runs on the query side, so "B.Sc" and "BSc" agree.
    """
    return _TOKEN_RE.findall(_DOTTED_RE.sub("", text).casefold())


class BM25:
    """Textbook BM25 over a small in-memory corpus.

    Written out rather than pulled in as a dependency: the corpora here are
    tens to hundreds of short documents, and the EC2 worker installs its
    packages from a fixed list in scripts/deploy-ec2.sh.
    """

    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._docs = [tokenize(document) for document in documents]
        self._lengths = [len(doc) for doc in self._docs]
        self._avg_length = (sum(self._lengths) / len(self._docs)) if self._docs else 0.0
        self._frequencies = [Counter(doc) for doc in self._docs]

        document_frequency: Counter[str] = Counter()
        for doc in self._docs:
            document_frequency.update(set(doc))
        total = len(self._docs)
        self._idf = {
            term: math.log(1 + (total - count + 0.5) / (count + 0.5))
            for term, count in document_frequency.items()
        }

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        if not self._docs or not terms:
            return [0.0] * len(self._docs)

        out: list[float] = []
        for index, frequencies in enumerate(self._frequencies):
            length = self._lengths[index] or 1
            score = 0.0
            for term in terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self._k1 * (
                    1 - self._b + self._b * length / (self._avg_length or 1)
                )
                score += self._idf.get(term, 0.0) * frequency * (self._k1 + 1) / denominator
            out.append(score)
        return out

    def top(self, query: str, limit: int, min_coverage: float = 0.5) -> list[tuple[int, float]]:
        """Rank documents, keeping only those that cover enough of the query.

        Score alone is not a usable relevance floor: an off-topic question
        ("best pizza in Naples") still scores against every document that
        happens to contain "best". Requiring a document to match a share of the
        query's distinct terms is what lets an unanswerable question return
        nothing, which is what Disha's refusal rule depends on.
        """
        terms = set(tokenize(query))
        if not terms:
            return []
        needed = max(1, math.ceil(len(terms) * min_coverage))

        # A rare term is evidence on its own. "CA kitna time lagta hai" has four
        # terms but only "ca" exists in the corpus, so a coverage rule alone
        # refuses a question the dataset can answer. Terms this discriminative
        # appear in a handful of documents, so matching one is not a coincidence
        # the way matching "best" or "career" is.
        rare = {term for term in terms if self._idf.get(term, 0.0) >= _RARE_TERM_IDF}

        ranked: list[tuple[int, float]] = []
        for index, score in enumerate(self.scores(query)):
            if score <= 0:
                continue
            frequencies = self._frequencies[index]
            covered = sum(term in frequencies for term in terms)
            if covered >= needed or any(term in frequencies for term in rare):
                ranked.append((index, score))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked[:limit]


def rrf_fuse(
    dense_keys: list[str],
    sparse_keys: list[str],
    k: int = _RRF_K,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion: score = Σ 1/(k + rank). Ordinal ranks only."""
    scores: dict[str, float] = {}
    for rank, key in enumerate(dense_keys, start=1):
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    for rank, key in enumerate(sparse_keys, start=1):
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


# ---------------------------------------------------------------------------
# Dense arm: embeddings + Qdrant REST
# ---------------------------------------------------------------------------


async def embed(texts: list[str]) -> list[list[float]]:
    """Embed texts, or return [] if no key is configured or the call fails."""
    if not texts or not os.environ.get("OPENAI_API_KEY"):
        return []

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI()
        response = await client.embeddings.create(model=EMBED_MODEL, input=texts)
        return [item.embedding for item in response.data]
    except Exception as error:  # noqa: BLE001 - retrieval must never break a call
        _warn_once("embed", f"embeddings unavailable, falling back to BM25 only: {error}")
        return []


async def _qdrant(method: str, path: str, payload: dict | None = None) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=_QDRANT_TIMEOUT) as client:
            response = await client.request(method, f"{QDRANT_URL}{path}", json=payload)
            if response.status_code >= 400:
                logger.debug("qdrant %s %s -> %s", method, path, response.text[:200])
                return None
            return response.json()
    except Exception as error:  # noqa: BLE001
        _warn_once("qdrant", f"Qdrant unavailable at {QDRANT_URL}, BM25 only: {error}")
        return None


async def ensure_collection(name: str) -> bool:
    """Create the collection if missing. Returns False when Qdrant is down."""
    existing = await _qdrant("GET", f"/collections/{name}")
    if existing is not None:
        return True

    created = await _qdrant(
        "PUT",
        f"/collections/{name}",
        {"vectors": {"size": EMBED_DIM, "distance": "Cosine"}},
    )
    return created is not None


async def drop_collection(name: str) -> None:
    """Delete a collection so it can be rebuilt from scratch."""
    await _qdrant("DELETE", f"/collections/{name}")


async def upsert(name: str, points: list[dict]) -> bool:
    if not points:
        return True
    if not await ensure_collection(name):
        return False
    result = await _qdrant("PUT", f"/collections/{name}/points?wait=false", {"points": points})
    return result is not None


async def dense_search(
    name: str,
    vector: list[float],
    limit: int,
    min_score: float = _MIN_DENSE_SCORE,
) -> list[dict]:
    """Return matching payloads, best first. Empty list when Qdrant is down.

    `min_score` is enforced server-side so an unrelated query returns nothing
    rather than its nearest neighbours.
    """
    if not vector:
        return []
    result = await _qdrant(
        "POST",
        f"/collections/{name}/points/search",
        {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
            "score_threshold": min_score,
        },
    )
    if not result:
        return []
    return [hit.get("payload") or {} for hit in result.get("result", [])]


# ---------------------------------------------------------------------------
# Write paths
# ---------------------------------------------------------------------------


async def remember_utterance(case_id: str, role: str, text: str, lang: str = "") -> None:
    """Index one verbatim utterance into the case's conversation collection."""
    text = text.strip()
    if not case_id or len(text) < 8:
        return

    vectors = await embed([text])
    if not vectors:
        return

    stamp = int(time.time() * 1000)
    await upsert(
        conversation_collection(case_id),
        [
            {
                "id": point_id(f"{case_id}:utterance:{stamp}:{role}"),
                "vector": vectors[0],
                "payload": {
                    "kind": "utterance",
                    "case": case_id,
                    "role": role,
                    "lang": lang,
                    "ts": stamp // 1000,
                    "text": text,
                },
            }
        ],
    )


async def remember_fact(case_id: str, kind: str, label: str, text: str) -> None:
    """Index one distilled personal fact into the case's person collection.

    `kind` is "constraint" or "note"; `label` is the constraint name, so a
    constraint that changes overwrites its earlier value instead of stacking.
    """
    text = text.strip()
    if not case_id or not text:
        return

    vectors = await embed([f"{label}: {text}" if label else text])
    if not vectors:
        return

    await upsert(
        person_collection(case_id),
        [
            {
                "id": point_id(f"{case_id}:{kind}:{label or text}"),
                "vector": vectors[0],
                "payload": {
                    "kind": kind,
                    "case": case_id,
                    "label": label,
                    "ts": int(time.time()),
                    "text": text,
                },
            }
        ],
    )


def fire_and_forget(coroutine) -> None:
    """Run an indexing coroutine without letting it block or break the call."""

    async def guarded() -> None:
        try:
            await coroutine
        except Exception as error:  # noqa: BLE001
            logger.debug("background indexing failed: %s", error)

    try:
        asyncio.get_running_loop().create_task(guarded())
    except RuntimeError:
        coroutine.close()


# ---------------------------------------------------------------------------
# Read path
# ---------------------------------------------------------------------------


async def hybrid_search(
    query: str,
    documents: list[dict],
    text_key: str,
    key_of,
    collection: str,
    limit: int,
    dense_pool: int = 10,
    bm25: BM25 | None = None,
    sparse_query: str = "",
    min_dense_score: float = _MIN_DENSE_SCORE,
) -> list[dict]:
    """Fuse a Qdrant search over `collection` with BM25 over `documents`.

    `documents` is the authoritative local copy; Qdrant hits are matched back to
    it through `key_of`, so a stale or partial index can never introduce a
    document the caller does not already hold. That keeps the closed-list
    guarantee intact even while the index is being rebuilt.
    """
    if not query or not documents:
        return []

    by_key = {key_of(document): document for document in documents}
    ranker = bm25 or BM25([str(document.get(text_key, "")) for document in documents])
    sparse_keys = [
        key_of(documents[index])
        for index, _ in ranker.top(sparse_query or query, dense_pool)
    ]

    dense_keys: list[str] = []
    vectors = await embed([query])
    if vectors:
        for payload in await dense_search(collection, vectors[0], dense_pool, min_dense_score):
            key = str(payload.get("key", ""))
            if key in by_key:
                dense_keys.append(key)

    fused = rrf_fuse(dense_keys, sparse_keys)
    return [by_key[key] for key, _ in fused[:limit] if key in by_key]


async def recall_case_memory(case_id: str, query: str, limit: int = 4) -> list[dict]:
    """Semantic recall across a returning student's own case, dense-only.

    There is no local corpus to run BM25 against here — the case file is read
    separately for exact facts — so this arm is purely the vector index, and
    returns nothing when Qdrant or embeddings are unavailable.
    """
    if not case_id or not query:
        return []

    vectors = await embed([query])
    if not vectors:
        return []

    # Looser floor than the handbook's: this only searches the student's own
    # case, so there is no closed-list to protect, and a Hinglish utterance
    # matched against an English query sits well below the handbook threshold.
    person, conversation = await asyncio.gather(
        dense_search(person_collection(case_id), vectors[0], limit, min_score=0.22),
        dense_search(conversation_collection(case_id), vectors[0], limit, min_score=0.22),
    )
    return [payload for payload in [*person, *conversation] if payload.get("text")]
