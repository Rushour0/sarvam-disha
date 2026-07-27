"""Nightly refresh of Disha's dynamic, externally-sourced records.

Fetches each configured source, normalises every record to a FLEXIBLE shape and
merges it into data/dynamic/<source>.json. The shape has a small fixed core:

    id, name, source, source_url, fetched_on, kind

plus an open passthrough of every other field the source returned. Unknown
fields are never dropped, and the search text Disha indexes is built from all
string / list-of-string values, so a new field an upstream source adds becomes
searchable with no code change here or in the agent.

Merge is by `id`: existing curated entries (anything already in the file that a
run does not re-fetch) are preserved, matched records are updated only when
their content actually changed, and an unchanged record keeps its old
`fetched_on` so the nightly commit stays a minimal diff rather than rewriting
every row's date.

Key: DATA_GOV_API_KEY from the environment, or from .env / .env.local (loaded
the same way scripts/index_kb.py loads them). In CI it comes from the repo
secret; locally it comes from .env.local.

Run: agent/.venv/bin/python scripts/refresh_data.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
DYNAMIC_DIR = REPO_ROOT / "data" / "dynamic"

load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(REPO_ROOT / ".env.local", override=True)

API_KEY = os.environ.get("DATA_GOV_API_KEY", "").strip()

# data.gov.in record endpoint. Discovery (which resource ids to use) was done
# out of band; only vetted per-record, student-actionable resources are wired
# here. Statistics-only resources (beneficiary counts, vacancy counts) are
# deliberately excluded — they have no entity a student can act on.
RESOURCE_URL = "https://api.data.gov.in/resource/{index_name}"
PAGE_SIZE = 100
HTTP_TIMEOUT = 30.0
# data.gov.in tarpits the default python-httpx User-Agent (the connection opens
# but the read never completes); any ordinary UA gets an instant 200. Identify
# ourselves plainly rather than spoofing a browser.
USER_AGENT = "disha-data-refresh/1.0 (+https://github.com/rushour0/sarvam)"

# Keys that are plumbing, not searchable content. Kept in sync with the loader
# in agent/disha.py (_DYNAMIC_NON_SEARCHABLE_KEYS) so text built here matches
# what the agent would build if it had to rebuild it.
_NON_SEARCHABLE_KEYS = frozenset({"id", "source", "source_url", "fetched_on", "text"})

# ---------------------------------------------------------------------------
# Source configuration
# ---------------------------------------------------------------------------
#
# Each source maps one data.gov.in resource to Disha's flexible record. Only
# `source`, `kind`, `index_name`, `name_field` and `source_url` are required;
# `id_field` picks a stable natural key (falling back to a content hash) and
# `max_records` optionally caps the fetch (a cap is always logged, never
# silent). data.gov.in resources carry no per-record link, so `source_url` is
# the resource's catalog page — the honest place each record came from.
SOURCES: list[dict[str, object]] = [
    {
        # 518 polytechnic colleges with full postal addresses. A student can
        # find and apply to the nearest one.
        "source": "polytechnics_tn",
        "kind": "institute",
        "index_name": "91aa3e10-a2d3-474c-8b13-a2fea964e4d3",
        "name_field": "institution_name",
        "id_field": "institution_code",
        "source_url": (
            "https://www.data.gov.in/resource/"
            "91aa3e10-a2d3-474c-8b13-a2fea964e4d3"
        ),
    },
    {
        # 36 MeitY-backed technology incubation centres, nationwide, with the
        # sector each supports. Actionable for a student founder.
        "source": "incubators",
        "kind": "incubator",
        "index_name": "8432c971-2b1a-4a21-a898-8e8a914ce45b",
        "name_field": "name_of_the_center",
        "id_field": "sno",
        "source_url": (
            "https://www.data.gov.in/resource/"
            "8432c971-2b1a-4a21-a898-8e8a914ce45b"
        ),
    },
]


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return cleaned or "x"


def build_search_text(record: dict[str, object]) -> str:
    """Search text from every string / list-of-string value in the record."""
    parts: list[str] = []
    for key, value in record.items():
        if key in _NON_SEARCHABLE_KEYS:
            continue
        if isinstance(value, str):
            if value:
                parts.append(value)
        elif isinstance(value, list):
            parts.extend(
                str(item) for item in value if isinstance(item, str) and item
            )
    return ". ".join(parts)


def normalize(
    record: dict[str, object], source_cfg: dict[str, object], fetched_on: str
) -> dict[str, object]:
    """Map one upstream record to the flexible core-plus-passthrough shape."""
    source = str(source_cfg["source"])
    name = str(record.get(str(source_cfg["name_field"]), "")).strip()

    id_field = source_cfg.get("id_field")
    raw_id = record.get(str(id_field)) if id_field else None
    if raw_id in (None, ""):
        # Never drop a row for want of a natural key: hash the record instead.
        digest = hashlib.sha1(
            json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        raw_id = digest[:12]
    record_id = f"{source}-{_slug(str(raw_id))}"

    core = {
        "id": record_id,
        "name": name,
        "source": source,
        "source_url": str(source_cfg["source_url"]),
        "fetched_on": fetched_on,
        "kind": str(source_cfg["kind"]),
    }
    # Passthrough every upstream field that does not collide with a core key,
    # then let core win. Nothing from the source is dropped.
    passthrough = {key: value for key, value in record.items() if key not in core}
    merged: dict[str, object] = {**passthrough, **core}
    merged["text"] = build_search_text(merged)
    return merged


def fetch_records(
    source_cfg: dict[str, object], api_key: str
) -> tuple[list[dict[str, object]], object]:
    """Page through a resource. Returns (records, reported_total)."""
    index_name = str(source_cfg["index_name"])
    url = RESOURCE_URL.format(index_name=index_name)
    max_records = source_cfg.get("max_records")

    records: list[dict[str, object]] = []
    total: object = None
    offset = 0
    with httpx.Client(
        timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT}
    ) as client:
        while True:
            response = client.get(
                url,
                params={
                    "api-key": api_key,
                    "format": "json",
                    "limit": PAGE_SIZE,
                    "offset": offset,
                },
            )
            response.raise_for_status()
            payload = response.json()
            if total is None:
                total = payload.get("total")
            batch = payload.get("records") or []
            if not batch:
                break
            records.extend(item for item in batch if isinstance(item, dict))
            offset += len(batch)

            if isinstance(max_records, int) and len(records) >= max_records:
                records = records[:max_records]
                print(
                    f"  [{source_cfg['source']}] capped at {max_records} "
                    f"records (total {total} available)"
                )
                break
            if isinstance(total, int) and offset >= total:
                break
            if len(batch) < PAGE_SIZE:
                break
    return records, total


def _content(record: dict[str, object]) -> dict[str, object]:
    """Comparable view: drop only the volatile fetch date."""
    return {key: value for key, value in record.items() if key != "fetched_on"}


def merge(source: str, fetched: list[dict[str, object]]) -> tuple[int, int, int, int]:
    """Merge into data/dynamic/<source>.json. Returns counts.

    (added, updated, unchanged, preserved). `preserved` counts existing entries
    the fetch did not touch — curated or from a row that dropped out upstream —
    which are kept, never deleted.
    """
    path = DYNAMIC_DIR / f"{source}.json"
    existing: list[dict[str, object]] = []
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, list):
            existing = [item for item in loaded if isinstance(item, dict)]

    by_id = {str(item["id"]): item for item in existing if item.get("id")}
    result_by_id = dict(by_id)  # start from existing, so curated entries survive

    added = updated = unchanged = 0
    fetched_ids: set[str] = set()
    for record in fetched:
        record_id = str(record["id"])
        fetched_ids.add(record_id)
        old = by_id.get(record_id)
        if old is None:
            result_by_id[record_id] = record
            added += 1
        elif _content(old) != _content(record):
            result_by_id[record_id] = record
            updated += 1
        else:
            # Content identical: keep the old row (and its fetched_on) so the
            # nightly commit does not churn every date.
            result_by_id[record_id] = old
            unchanged += 1

    preserved = sum(1 for record_id in by_id if record_id not in fetched_ids)

    ordered = [result_by_id[key] for key in sorted(result_by_id)]
    path.write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return added, updated, unchanged, preserved


def main() -> int:
    if not API_KEY:
        print("DATA_GOV_API_KEY not set (env or .env.local) — nothing to do")
        return 1

    DYNAMIC_DIR.mkdir(parents=True, exist_ok=True)
    fetched_on = dt.date.today().isoformat()
    exit_code = 0

    for source_cfg in SOURCES:
        source = str(source_cfg["source"])
        try:
            raw, total = fetch_records(source_cfg, API_KEY)
        except Exception as error:  # noqa: BLE001 - one bad source must not sink the rest
            print(f"[{source}] fetch failed: {error}")
            exit_code = 1
            continue

        normalized = [
            normalize(record, source_cfg, fetched_on)
            for record in raw
            if isinstance(record, dict)
        ]
        # Dedupe within the batch by id (last occurrence wins).
        deduped: dict[str, dict[str, object]] = {}
        for record in normalized:
            deduped[str(record["id"])] = record
        records = list(deduped.values())

        added, updated, unchanged, preserved = merge(source, records)
        print(
            f"[{source}] fetched {len(raw)} rows (total {total}); "
            f"added {added}, updated {updated}, unchanged {unchanged}, "
            f"preserved {preserved} -> data/dynamic/{source}.json"
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
