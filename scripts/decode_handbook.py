"""Repair the SD SEED handbook chunks in data/handbook_chunks.json.

The SD SEED Career Handbook PDF embeds subsetted fonts with no usable ToUnicode
map, so both pypdf and pdftotext return raw glyph codes instead of characters.
The result is text like "DYZci^[n^c\\ i]Z <ei^ijYZ" for "Identifying the
Aptitude". The glyph codes are laid out in a predictable order, so the cipher is
a fixed per-range offset plus a handful of ligature and punctuation glyphs.

This script decodes those chunks in place, then drops any chunk that still does
not read as English (a few table rows use a second, differently-ordered font
subset that this map does not cover). Chunks from the CFA guide extract cleanly
and are passed through untouched.

Run: python3 scripts/decode_handbook.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = REPO_ROOT / "data" / "handbook_chunks.json"
GARBLED_SOURCE = "SD SEED Career Handbook"

# Glyphs that fall outside the plain letter ranges below.
GLYPH_OVERRIDES = {
    "#": " ",
    "p": "’",  # right single quote
    "q": "fi",
    "r": "–",  # en dash
    "s": "•",  # bullet separator
    "t": "–",
    "u": "ff",
    "v": "ffi",
    "w": "ffl",
}

# A short list is enough to tell decoded English from a still-ciphered string.
COMMON_WORDS = frozenset(
    """the of and to in a for is are you your with on at as be can will
    or from that this it after school career courses course college student
    students exam exams job jobs eligibility duration years class stream
    science commerce arts engineering medical degree diploma admission""".split()
)

_WORD_RE = re.compile(r"[a-z]+")
_LETTER_RUN_RE = re.compile(r"[A-Za-z]+")


def decode_glyphs(text: str) -> str:
    """Map raw glyph codes back to characters using the font's layout order."""
    out: list[str] = []
    for char in text:
        override = GLYPH_OVERRIDES.get(char)
        if override is not None:
            out.append(override)
            continue

        code = ord(char)
        if 60 <= code <= 85:  # '<'..'U'  ->  'A'..'Z'
            out.append(chr(code + 5))
        elif 86 <= code <= 111:  # 'V'..'o'  ->  'a'..'z'
            out.append(chr(code + 11))
        elif 33 <= code <= 59:  # digits and punctuation
            out.append(chr(code + 1))
        else:
            out.append(char)
    return "".join(out)


def english_ratio(text: str) -> float:
    """Share of words in the text that are recognisably common English."""
    words = _WORD_RE.findall(text.casefold())
    if not words:
        return 0.0
    return sum(word in COMMON_WORDS for word in words) / len(words)


def decode_heading_glyphs(text: str) -> str:
    """Second font subset, used by the handbook's headings and table rows."""
    out: list[str] = []
    for char in text:
        code = ord(char)
        if 87 <= code <= 90:  # 'W'..'Z'  ->  'a'..'d'
            out.append(chr(code + 10))
        elif 97 <= code <= 118:  # 'a'..'v'  ->  'e'..'z'
            out.append(chr(code + 4))
        elif char == ":":
            out.append("A")
        elif 65 <= code <= 86:  # 'A'..'V'  ->  'C'..'X'
            out.append(chr(code + 2))
        else:
            out.append(char)
    return "".join(out)


def load_dictionary() -> frozenset[str]:
    """System word list, used only to tell real words from ciphered ones."""
    for path in (Path("/usr/share/dict/words"), Path("/usr/dict/words")):
        if path.is_file():
            return frozenset(
                word.strip().casefold() for word in path.read_text(errors="ignore").splitlines()
            )
    return frozenset()


DICTIONARY = load_dictionary()


# /usr/share/dict/words carries base forms only — "align" but not "aligning",
# "aspect" but not "aspects". Without this, the gate deletes ordinary English.
_SUFFIXES = ("s", "es", "ed", "ing", "ly", "er", "est", "ies", "ment", "ness", "tion")


def _in_dictionary(word: str) -> bool:
    word = word.casefold()
    if word in DICTIONARY:
        return True
    for suffix in _SUFFIXES:
        if not word.endswith(suffix):
            continue
        stem = word[: -len(suffix)]
        if len(stem) < 3:
            continue
        # "aligning" -> "align"; "aspects" -> "aspect"; "carries" -> "carry";
        # "running" -> "run" (the doubled consonant goes too).
        if stem in DICTIONARY or f"{stem}e" in DICTIONARY:
            return True
        if stem.endswith("i") and f"{stem[:-1]}y" in DICTIONARY:
            return True
        if len(stem) > 3 and stem[-1] == stem[-2] and stem[:-1] in DICTIONARY:
            return True
    return False


def _is_english_token(token: str) -> bool:
    runs = [run for run in _LETTER_RUN_RE.findall(token) if len(run) > 1]
    return bool(runs) and all(_in_dictionary(run) for run in runs)


def repair_token(token: str) -> str | None:
    """Return the readable form of a token, or None if it is unsalvageable.

    Most tokens already decoded correctly. The rest either belong to the second
    font subset (recoverable) or to a heading subset this script does not model
    (dropped, so the agent never reads glyph soup aloud).
    """
    if not _LETTER_RUN_RE.search(token):
        return token  # pure numbers, punctuation, bullets

    # Letters welded to a colon or a digit are always a mis-decoded glyph run.
    if re.search(r"[A-Za-z][:0-9]|[:0-9][A-Za-z]", token):
        return None
    if _is_english_token(token):
        return token
    if "." in token or "/" in token or "@" in token:
        return token  # abbreviations, URLs, B.Sc., www.aipmt.nic.in

    # Retrying two-letter runs causes dictionary collisions (the correct
    # "B.Sc." comes back as the wrong "D.Ug."), so require a longer run.
    runs = _LETTER_RUN_RE.findall(token)
    all_caps = token.upper() == token
    if (
        not all_caps  # never rewrite an acronym: BMC must not become DOE
        and all(len(run) >= 2 for run in runs)
        and any(len(run) >= 3 for run in runs)
    ):
        retried = decode_heading_glyphs(token)
        if _is_english_token(retried):
            return retried

    letters = "".join(runs)
    has_vowel = any(vowel in letters.casefold() for vowel in "aeiou")
    if letters.isupper() and len(letters) <= 4:
        return token  # acronym: BBA, LLB, CWA, NEET
    if len(letters) >= 3 and letters[:1].isupper() and letters[1:].islower() and has_vowel:
        return token  # proper noun the dictionary does not carry
    return None


def tidy(text: str) -> str:
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def strip_gibberish(text: str) -> str:
    repaired = (repair_token(token) for token in text.split())
    return " ".join(token for token in repaired if token is not None)


def extract_sd_seed_pages(pdf_path: Path, max_chars: int) -> list[dict]:
    """Re-extract one raw chunk per page with pdftotext.

    Used by --from-pdf, so a decoding fix can be applied to the original glyph
    codes instead of to text an earlier, worse pass already damaged.
    """
    import subprocess

    page_count = int(
        subprocess.run(
            ["pdfinfo", str(pdf_path)], capture_output=True, text=True, check=True
        )
        .stdout.split("Pages:")[1]
        .split()[0]
    )

    chunks: list[dict] = []
    for page in range(1, page_count + 1):
        result = subprocess.run(
            ["pdftotext", "-f", str(page), "-l", str(page), str(pdf_path), "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        text = " ".join(result.stdout.split())
        if len(text) < 40:
            continue
        chunks.append({"source": GARBLED_SOURCE, "page": page, "text": text[:max_chars]})
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--repair-only",
        action="store_true",
        help="Skip glyph decoding; only re-run token repair on already-decoded text.",
    )
    parser.add_argument(
        "--min-ratio",
        type=float,
        default=0.09,
        help="Minimum common-English word ratio for a decoded chunk to be kept.",
    )
    parser.add_argument(
        "--from-pdf",
        action="store_true",
        help="Re-extract the SD SEED pages from data/raw/ before decoding.",
    )
    args = parser.parse_args()

    chunks: list[dict] = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    if args.from_pdf:
        pdf_path = REPO_ROOT / "data" / "raw" / "career_handbook_sdseed.pdf"
        if not pdf_path.is_file():
            raise SystemExit(f"missing {pdf_path} — raw PDFs are not deployed")
        fresh = extract_sd_seed_pages(pdf_path, max_chars=1500)
        print(f"re-extracted {len(fresh)} raw pages from {pdf_path.name}")
        others = [chunk for chunk in chunks if chunk.get("source") != GARBLED_SOURCE]
        chunks = fresh + others

    kept: list[dict] = []
    decoded_count = 0
    dropped: list[tuple[int, float]] = []

    for chunk in chunks:
        if chunk.get("source") != GARBLED_SOURCE:
            chunk["text"] = tidy(chunk["text"])
            kept.append(chunk)
            continue

        already_decoded = english_ratio(chunk["text"]) >= args.min_ratio
        if already_decoded and not args.repair_only:
            # Decoding twice would re-cipher it.
            kept.append(chunk)
            continue

        source_text = chunk["text"] if already_decoded else decode_glyphs(chunk["text"])
        decoded = tidy(strip_gibberish(source_text))
        ratio = english_ratio(decoded)
        if ratio < args.min_ratio or len(decoded) < 120:
            dropped.append((chunk.get("page", -1), ratio))
            continue

        chunk["text"] = decoded
        decoded_count += 1
        kept.append(chunk)

    print(f"decoded {decoded_count} SD SEED chunks, dropped {len(dropped)}")
    for page, ratio in dropped:
        print(f"  dropped page {page} (english ratio {ratio:.3f})")
    print(f"total chunks: {len(chunks)} -> {len(kept)}")

    if args.dry_run:
        sample = next((c for c in kept if c["source"] == GARBLED_SOURCE), None)
        if sample:
            print("\nsample:\n" + sample["text"][:600])
        return

    CHUNKS_PATH.write_text(
        json.dumps(kept, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {CHUNKS_PATH}")


if __name__ == "__main__":
    main()
