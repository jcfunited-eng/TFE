"""
gutenberg_adapter.py — Fetch and parse a Project Gutenberg text into
corpus lines for GualaLoom.

Responsibilities:
  1. Download raw UTF-8 text from a Gutenberg URL.
  2. Strip the Gutenberg header and footer (between START/END markers).
  3. Split body text into sentence-level lines using the same pattern
     already used for PDF corpora in substrate_runner (split on newline,
     then split lines > 200 chars on '. ').
  4. Filter out illustration notes and blank lines.

Returns a list of clean sentence strings ready to be registered as a
corpus and fed through read_sentence().

Does NOT touch the substrate. Network IO stays here; substrate IO stays
in the caller.
"""

import re
import urllib.request


_GUTENBERG_START = re.compile(r"\*{3}\s*START OF", re.IGNORECASE)
_GUTENBERG_END   = re.compile(r"\*{3}\s*END OF",   re.IGNORECASE)

# Illustration notes that appear in Gutenberg plain-text editions
_ILLUSTRATION    = re.compile(r"^\[Illustration[^\]]*\]", re.IGNORECASE)


def fetch_and_parse(url: str) -> tuple:
    """Download a Gutenberg text and return (lines, metadata).

    lines    : list[str] — clean sentence-level strings, ready for
               read_sentence().
    metadata : dict — {n_raw_lines, n_sentences, encoding_used}
    """
    req = urllib.request.Request(url, headers={"User-Agent": "GualaLoom/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_bytes = resp.read()

    # Try UTF-8, fall back to latin-1 (most Gutenberg files are one of these)
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            raw_text = raw_bytes.decode(enc)
            encoding_used = enc
            break
        except UnicodeDecodeError:
            continue
    else:
        raw_text = raw_bytes.decode("latin-1", errors="replace")
        encoding_used = "latin-1-replace"

    # Strip Gutenberg header and footer
    body = _strip_gutenberg(raw_text)

    # Split to sentence-level lines (reuses existing corpus split pattern)
    lines = _split_to_sentences(body)

    metadata = {
        "n_raw_lines": len(raw_text.splitlines()),
        "n_sentences": len(lines),
        "encoding_used": encoding_used,
    }
    return lines, metadata


def _strip_gutenberg(text: str) -> str:
    """Return only the text between Gutenberg START and END markers."""
    lines = text.splitlines()
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if start_idx is None and _GUTENBERG_START.search(line):
            start_idx = i + 1   # content starts after the marker line
        elif start_idx is not None and _GUTENBERG_END.search(line):
            end_idx = i
            break
    if start_idx is None:
        # No markers found — use the whole text (graceful fallback)
        return text
    body_lines = lines[start_idx:end_idx] if end_idx else lines[start_idx:]
    return "\n".join(body_lines)


def _split_to_sentences(text: str) -> list:
    """Split body text to sentence-level lines.

    Mirrors the PDF-path split in substrate_runner (lines 694-702):
      - split on newline
      - for lines > 200 chars: split on '. ' boundary
      - strip blanks, illustration notes, and short artefacts
    """
    raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
    sentences = []
    for line in raw_lines:
        # Skip illustration notes
        if _ILLUSTRATION.match(line):
            continue
        # Skip very short lines that are likely chapter headings / page refs
        if len(line) < 4:
            continue
        if len(line) > 200:
            # Same heuristic as substrate_runner: split on '. '
            for part in line.replace(". ", ".\n").split("\n"):
                part = part.strip()
                if part and len(part) >= 4:
                    sentences.append(part)
        else:
            sentences.append(line)
    return sentences
