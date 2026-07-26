"""Merge every career source into data/pathway_tree.json — one schema, one file.

Disha had three disconnected shapes: a nested degree tree, a flat vocational
list, and a scholarship list keyed by nothing. That works for one keyword search
and nothing else — a front end cannot render it, and a node cannot say what it
leads to or what pays for it.

This produces a FLAT node list with parent/child ids. Flat is deliberate:
  - a front end can build the tree, a breadcrumb, or a graph from the same file
  - retrieval indexes one document per node without walking anything
  - ids are stable slugs, so a shortlist saved today still resolves next month

Schema (data/pathway_tree.json):
  version, generated_on, sources[], nodes[]

  node = {
    id            stable slug, unique
    parent_id     null for the seven stream roots
    name          display label
    path          human-readable "A > B > C", kept for spoken shortlists
    depth         0 for streams, 1.. below
    kind          stream | qualification | trade | entry_route | job_track
    level         after-8th | after-10th | after-12th | after-graduation | null
    duration      null unless an official source states it
    eligibility   null unless an official source states it
    note          caveat to speak alongside the node, or null
    state         null unless the node only exists in one state
    jobs          list of job titles this node leads to
    scholarship_tags  tags matched against data/scholarships.json applies_to
    children      list of child ids
    source_id     which entry in sources[] this node came from
    link          external URL from the original dataset, or ""
  }

Run: python3 scripts/build_pathway_tree.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CAREER_TREE_PATH = REPO_ROOT / "data" / "career_tree.json"
VOCATIONAL_PATH = REPO_ROOT / "data" / "vocational_paths.json"
SCHOLARSHIPS_PATH = REPO_ROOT / "data" / "scholarships.json"
OUTPUT_PATH = REPO_ROOT / "data" / "pathway_tree.json"

GENERATED_ON = "2026-07-26"
NON_NODE_KEYS = frozenset({"jobs", "link"})

SOURCES = [
    {
        "id": "career_tree",
        "title": "Disha curated career tree",
        "url": "",
        "fetched_on": "2026-07-25",
    },
    {
        "id": "bharat_skills",
        "title": "Bharat Skills — Craftsmen Training Scheme trade list (DGT/NCVT)",
        "url": "https://bharatskills.gov.in/Home/CTS",
        "fetched_on": "2026-07-26",
    },
    {
        "id": "dvet",
        "title": "Directorate of Vocational Education and Training, Maharashtra",
        "url": "https://dvet.gov.in/",
        "fetched_on": "2026-07-26",
    },
    {
        "id": "join_indian_army",
        "title": "Join Indian Army — entry schemes",
        "url": "https://joinindianarmy.nic.in/",
        "fetched_on": "2026-07-26",
    },
]

# Which scholarship tags apply to a whole stream. Node-level tags are added on
# top of these; a diploma under STEM picks up both "technical" and "vocational".
STREAM_TAGS = {
    "STEM": ["higher-ed", "technical"],
    "Commerce and Management": ["higher-ed"],
    "Creative and Argumentative Studies": ["higher-ed"],
    "Civil Services": ["higher-ed"],
    "Defence": ["defence-family"],
    "Vocational Education": ["vocational"],
    "Jobs after 10th": ["school"],
}

# Level is inferred from the stream and node shape, never from a guess about a
# specific qualification. Anything unclear stays null.
STREAM_LEVEL = {
    "Jobs after 10th": "after-10th",
    "Vocational Education": "after-10th",
}


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")
    return cleaned or "node"


def split_jobs(raw: object) -> list[str]:
    """The source stores jobs as one comma-separated string per node."""
    text = str(raw or "").strip()
    if not text:
        return []
    parts = [part.strip(" .;") for part in re.split(r"[,/]| and ", text)]
    return [part for part in parts if len(part) > 1]


class TreeBuilder:
    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}

    def add(
        self,
        *,
        name: str,
        parent_id: str | None,
        path: str,
        kind: str,
        source_id: str,
        level: str | None = None,
        duration: str | None = None,
        eligibility: str | None = None,
        note: str | None = None,
        state: str | None = None,
        jobs: list[str] | None = None,
        scholarship_tags: list[str] | None = None,
        link: str = "",
    ) -> str:
        node_id = slugify(path)
        # Two different branches can hold the same qualification (B.Arch sits
        # under both STEM and Commerce). They are separate nodes because their
        # entry route differs, so the id is derived from the full path.
        if node_id in self.nodes:
            return node_id

        self.nodes[node_id] = {
            "id": node_id,
            "parent_id": parent_id,
            "name": name,
            "path": path,
            "depth": path.count(" > "),
            "kind": kind,
            "level": level,
            "duration": duration,
            "eligibility": eligibility,
            "note": note,
            "state": state,
            "jobs": jobs or [],
            "scholarship_tags": sorted(set(scholarship_tags or [])),
            "children": [],
            "source_id": source_id,
            "link": link,
        }
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id]["children"].append(node_id)
        return node_id


def walk_career_tree(builder: TreeBuilder) -> None:
    tree = json.loads(CAREER_TREE_PATH.read_text(encoding="utf-8"))
    streams = tree.get("Streams")
    if not isinstance(streams, dict):
        raise SystemExit("career_tree.json has no Streams object")

    def recurse(node: dict, path_parts: tuple[str, ...], parent_id: str | None) -> None:
        for name, child in node.items():
            if name in NON_NODE_KEYS:
                continue
            child = child if isinstance(child, dict) else {}
            parts = (*path_parts, name)
            stream = parts[0]
            path = " > ".join(parts)
            node_id = builder.add(
                name=name,
                parent_id=parent_id,
                path=path,
                kind="stream" if len(parts) == 1 else "qualification",
                source_id="career_tree",
                level=STREAM_LEVEL.get(stream, "after-12th" if len(parts) > 1 else None),
                jobs=split_jobs(child.get("jobs")),
                scholarship_tags=STREAM_TAGS.get(stream, []),
                link=str(child.get("link", "")),
            )
            recurse(child, parts, node_id)

    recurse(streams, (), None)


def attach_vocational(builder: TreeBuilder) -> None:
    records = json.loads(VOCATIONAL_PATH.read_text(encoding="utf-8"))

    for record in records:
        parts = record["path"].split(" > ")
        parent_id: str | None = None
        # Create the intermediate grouping levels ("Vocational Education >
        # ITI (Engineering trades)") once, then hang the leaf off them.
        for index in range(1, len(parts)):
            group_path = " > ".join(parts[:index])
            stream = parts[0]
            parent_id = builder.add(
                name=parts[index - 1],
                parent_id=parent_id,
                path=group_path,
                kind="stream" if index == 1 else "qualification",
                source_id=record.get("source_id", "bharat_skills"),
                level=STREAM_LEVEL.get(stream),
                scholarship_tags=STREAM_TAGS.get(stream, []),
            )

        category = record["category"]
        is_army = category == "Defence entry route"
        is_state_route = category == "State route"
        builder.add(
            name=record["name"],
            parent_id=parent_id,
            path=record["path"],
            kind="entry_route" if (is_army or is_state_route) else "trade",
            source_id=(
                "join_indian_army" if is_army else "dvet" if is_state_route else "bharat_skills"
            ),
            state=record.get("state"),
            level="after-10th",
            duration=record.get("duration"),
            eligibility=record.get("eligibility"),
            note=record.get("eligibility_note"),
            jobs=split_jobs(record.get("jobs")),
            scholarship_tags=(
                ["defence-family"]
                if is_army
                else ["vocational", "maharashtra"]
                if is_state_route
                else ["vocational"]
            ),
            link=record.get("source_url", ""),
        )


def main() -> None:
    builder = TreeBuilder()
    walk_career_tree(builder)
    attach_vocational(builder)

    scholarships = json.loads(SCHOLARSHIPS_PATH.read_text(encoding="utf-8"))
    tag_counts: dict[str, int] = {}
    for scheme in scholarships:
        for tag in scheme["applies_to"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    nodes = list(builder.nodes.values())
    payload = {
        "version": 2,
        "generated_on": GENERATED_ON,
        "sources": SOURCES,
        "scholarship_tags": sorted(tag_counts),
        "nodes": nodes,
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    kinds: dict[str, int] = {}
    for node in nodes:
        kinds[node["kind"]] = kinds.get(node["kind"], 0) + 1
    roots = [node["name"] for node in nodes if node["parent_id"] is None]

    print(f"wrote {len(nodes)} nodes to {OUTPUT_PATH}")
    print(f"  kinds: {kinds}")
    print(f"  roots: {roots}")
    print(f"  scholarship tags in use: {tag_counts}")


if __name__ == "__main__":
    main()
