"""Rebuild data/handbook_chunks.json using Sarvam Docs AI (Document Digitization).

The SD SEED handbook embeds subsetted fonts with no ToUnicode map, which is why
scripts/decode_handbook.py exists: pdftotext returns glyph soup and we reverse
the cipher by hand. Docs AI reads the rendered page instead of the font tables,
so it sidesteps that whole problem — including the table rows the cipher map
never covered — and extracts the CFA guide in the same pass.

Docs AI caps a job at 10 pages, so each PDF is split into 10-page slices with
poppler (pdfseparate + pdfunite) and submitted as one job per slice; the slice
offset maps every output file back to its absolute page number.

One chunk per page, same shape as before ({source, page, text}), because the
agent's Qdrant ids are "source#page" and a different chunking would orphan the
index. Re-run scripts/index_kb.py after this to re-embed.

Run: agent/.venv/bin/python scripts/parse_handbook_docsai.py [--limit N] [--dry-run]
Needs SARVAM_API_KEY in the environment or repo .env, and the sarvamai package.
"""

from __future__ import annotations

import argparse
import html.parser
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from dotenv import dotenv_values
from sarvamai import SarvamAI

REPO_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = REPO_ROOT / "data" / "handbook_chunks.json"
RAW_DIR = REPO_ROOT / "data" / "raw"

PAGES_PER_JOB = 10  # Docs AI rejects jobs above 10 pages.

# Source names must match the existing chunks exactly: they are the first half
# of every Qdrant id and the citation the agent speaks out loud.
SOURCES = [
    ("SD SEED Career Handbook", RAW_DIR / "career_handbook_sdseed.pdf"),
    ("CFA Society India Career Guide 2022", RAW_DIR / "cfa_career_guide_2022.pdf"),
]


def load_api_key() -> str:
    values = {**dotenv_values(REPO_ROOT / ".env"), **dotenv_values(REPO_ROOT / ".env.local")}
    key = values.get("SARVAM_API_KEY") or ""
    if not key:
        sys.exit("SARVAM_API_KEY is not set in .env/.env.local")
    return key


def page_count(pdf_path: Path) -> int:
    info = subprocess.run(
        ["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True
    )
    for line in info.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[-1])
    raise RuntimeError(f"pdfinfo reported no page count for {pdf_path}")


def split_pdf(pdf_path: Path, work_dir: Path, total_pages: int) -> list[tuple[int, Path]]:
    """Split into ≤10-page slices; returns (first_absolute_page, slice_path)."""
    pages_dir = work_dir / f"{pdf_path.stem}-pages"
    pages_dir.mkdir()
    subprocess.run(
        ["pdfseparate", str(pdf_path), str(pages_dir / "page-%d.pdf")], check=True
    )

    slices: list[tuple[int, Path]] = []
    for first in range(1, total_pages + 1, PAGES_PER_JOB):
        last = min(first + PAGES_PER_JOB - 1, total_pages)
        slice_path = work_dir / f"{pdf_path.stem}-{first:03d}-{last:03d}.pdf"
        parts = [str(pages_dir / f"page-{page}.pdf") for page in range(first, last + 1)]
        if len(parts) == 1:
            Path(parts[0]).replace(slice_path)
        else:
            subprocess.run(["pdfunite", *parts, str(slice_path)], check=True)
        slices.append((first, slice_path))
    return slices


class _TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


def to_plain_text(markup: str, suffix: str) -> str:
    if suffix in {".html", ".htm", ".xml"}:
        extractor = _TextExtractor()
        extractor.feed(markup)
        markup = " ".join(extractor.parts)
    else:
        # Markdown: drop image refs and table pipes, keep the words.
        markup = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", markup)
        markup = markup.replace("|", " ").replace("#", " ")
    return re.sub(r"\s+", " ", markup).strip()


# Layout blocks that describe pictures rather than transcribe text. Captions
# stay: in these handbooks the "caption" is often the section heading itself.
_SKIP_TAGS = {"image", "logo"}
_IMAGE_PROSE_RE = re.compile(
    r"^(the (provided )?image|this image)\b", re.IGNORECASE
)


def _block_text(block: dict) -> str:
    if block.get("layout_tag") in _SKIP_TAGS:
        return ""
    text = str(block.get("text", "")).strip()
    if not text or _IMAGE_PROSE_RE.match(text):
        return ""
    if "<" in text:  # tables arrive as HTML
        text = to_plain_text(text, ".html")
    return text


def pages_from_zip(zip_path: Path, first_page: int) -> dict[int, str]:
    """Map absolute page number -> text for one job's output ZIP.

    document.md merges the whole slice, so it cannot give page numbers; the
    metadata/page_NNN.json files carry each page's layout blocks with text and
    a reading order, which is exactly the per-page granularity the agent's
    "source#page" citations need.
    """
    texts: dict[int, str] = {}
    with zipfile.ZipFile(zip_path) as archive:
        for name in sorted(archive.namelist()):
            if not (name.startswith("metadata/") and name.endswith(".json")):
                continue
            page_data = json.loads(archive.read(name))
            blocks = sorted(
                page_data.get("blocks", []), key=lambda b: b.get("reading_order", 0)
            )
            parts = [text for block in blocks if (text := _block_text(block))]
            if not parts:
                continue
            page = first_page + int(page_data.get("page_num", 0)) - 1
            texts[page] = re.sub(r"\s+", " ", " ".join(parts)).strip()
    return texts


def main() -> None:
    arg_parser = argparse.ArgumentParser(description=__doc__)
    arg_parser.add_argument("--limit", type=int, help="only parse the first N pages per PDF")
    arg_parser.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = arg_parser.parse_args()

    client = SarvamAI(api_subscription_key=load_api_key())
    chunks: list[dict] = []

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        for source, pdf_path in SOURCES:
            if not pdf_path.is_file():
                sys.exit(f"missing PDF: {pdf_path}")
            pages = page_count(pdf_path)
            if args.limit:
                pages = min(pages, args.limit)

            for first_page, slice_path in split_pdf(pdf_path, work_dir, pages):
                job = client.document_intelligence.create_job(
                    language="en-IN", output_format="md"
                )
                job.upload_file(str(slice_path))
                job.start()
                status = job.wait_until_complete(poll_interval=3.0, timeout=600)
                state = getattr(status, "job_state", "?")
                print(f"  job {source} p{first_page}+: {state}")

                zip_path = work_dir / f"{slice_path.stem}-out.zip"
                job.download_output(str(zip_path))
                for page, text in sorted(pages_from_zip(zip_path, first_page).items()):
                    if len(text) < 40:
                        # Cover pages and pure-image pages have nothing to index.
                        print(f"  skip {source} p{page}: {len(text)} chars")
                        continue
                    chunks.append({"source": source, "page": page, "text": text})
                    print(f"  ok   {source} p{page}: {len(text)} chars")

    print(f"{len(chunks)} chunks total")
    if args.dry_run:
        return

    backup = CHUNKS_PATH.with_suffix(".json.bak")
    if CHUNKS_PATH.is_file():
        backup.write_bytes(CHUNKS_PATH.read_bytes())
        print(f"previous chunks backed up to {backup.name}")
    CHUNKS_PATH.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"wrote {CHUNKS_PATH}. Now re-embed: python scripts/index_kb.py")


if __name__ == "__main__":
    main()
