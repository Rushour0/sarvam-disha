"""Embed the handbook chunks into Qdrant so the dense arm of hybrid search works.

Run once after changing data/handbook_chunks.json. Safe to re-run: point ids are
derived from source+page, so re-indexing updates in place.

Qdrant is expected on 127.0.0.1:6333, which is where the worker finds it when
running on the same host. From a laptop, port-forward to the deployment host
first (connection details live in your local shell config, not in this repo) or
point QDRANT_URL somewhere else.

Run: agent/.venv/bin/python scripts/index_kb.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "agent"))

load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(REPO_ROOT / ".env.local", override=True)

import retrieval  # noqa: E402  - needs the .env loaded and agent/ on the path
from disha import (  # noqa: E402
    CAREER_DOCUMENTS,
    DYNAMIC_DOCUMENTS,
    OPPORTUNITY_DOCUMENTS,
    SCHOLARSHIP_DOCUMENTS,
    career_document_key,
    dynamic_key,
    handbook_chunk_key,
    opportunity_key,
    scholarship_key,
)

CHUNKS_PATH = REPO_ROOT / "data" / "handbook_chunks.json"
BATCH_SIZE = 32


async def index(
    collection: str,
    documents: list[dict],
    key_of,
    payload_of,
    reset: bool = False,
) -> bool:
    """Embed and upsert one collection in batches. Ids are derived from the
    document key, so re-running updates in place instead of duplicating.

    `reset` drops the collection first — needed whenever chunks are removed or
    re-derived, since an upsert alone leaves the old points orphaned in place.
    """
    print(f"indexing {len(documents)} documents into {collection}")
    if reset:
        await retrieval.drop_collection(collection)
    if not await retrieval.ensure_collection(collection):
        print(f"Qdrant unreachable at {retrieval.QDRANT_URL} — nothing indexed")
        return False

    done = 0
    for start in range(0, len(documents), BATCH_SIZE):
        batch = documents[start : start + BATCH_SIZE]
        vectors = await retrieval.embed([payload_of(document)["text"] for document in batch])
        if not vectors:
            print("embedding call failed — check OPENAI_API_KEY")
            return False

        points = [
            {
                "id": retrieval.point_id(f"{collection}:{key_of(document)}"),
                "vector": vector,
                "payload": {"key": key_of(document), **payload_of(document)},
            }
            for document, vector in zip(batch, vectors)
        ]
        if not await retrieval.upsert(collection, points):
            print("upsert failed")
            return False

        done += len(points)
        print(f"  {done}/{len(documents)}")
    return True


async def main() -> int:
    chunks: list[dict] = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    handbook_ok = await index(
        retrieval.HANDBOOK_COLLECTION,
        chunks,
        handbook_chunk_key,
        lambda chunk: {
            "kind": "handbook",
            "source": chunk.get("source", ""),
            "page": chunk.get("page", 0),
            "text": str(chunk.get("text", ""))[:1500],
        },
        reset=True,
    )
    if not handbook_ok:
        return 1

    careers_ok = await index(
        retrieval.CAREERS_COLLECTION,
        CAREER_DOCUMENTS,
        career_document_key,
        lambda document: {
            "kind": "career",
            "path": document["path"],
            "jobs": document["jobs"],
            "text": str(document["text"]),
        },
        reset=True,
    )
    if not careers_ok:
        return 1

    scholarships_ok = await index(
        retrieval.SCHOLARSHIPS_COLLECTION,
        SCHOLARSHIP_DOCUMENTS,
        scholarship_key,
        lambda scheme: {
            "kind": "scholarship",
            "name": scheme["name"],
            "provider": scheme["provider"],
            "applies_to": scheme["applies_to"],
            "text": str(scheme["text"]),
        },
        reset=True,
    )
    if not scholarships_ok:
        return 1

    opportunities_ok = await index(
        retrieval.OPPORTUNITIES_COLLECTION,
        OPPORTUNITY_DOCUMENTS,
        opportunity_key,
        lambda opp: {
            "kind": "opportunity",
            "name": opp["name"],
            "provider": opp["provider"],
            "applies_to": opp["applies_to"],
            "text": str(opp["text"]),
        },
        reset=True,
    )
    if not opportunities_ok:
        return 1

    dynamic_ok = await index(
        retrieval.DYNAMIC_COLLECTION,
        DYNAMIC_DOCUMENTS,
        dynamic_key,
        lambda record: {
            "kind": str(record.get("kind", "dynamic")),
            "name": str(record.get("name", "")),
            "source": str(record.get("source", "")),
            "source_url": str(record.get("source_url", "")),
            "text": str(record.get("text", "")),
        },
        reset=True,
    )
    if not dynamic_ok:
        return 1

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
