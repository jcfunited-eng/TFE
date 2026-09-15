"""Her library: real recordings fetched once from open sources and kept in her
beat's grain of sound (16 kHz, one channel, 4,000 samples a beat), with the
licence of each recording written beside it.

Books come from LibriVox (public-domain readings of public-domain texts by
human volunteers, served from the Internet Archive). Nothing here is
synthesized and nothing streams from outside at beat time: a chapter is
fetched and converted before it is read to her.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIBRARY = os.path.join(HERE, "media")
USER_AGENT = "guala-caretaker/1.0 (+https://dsf-ai.com; public-domain recordings for an artificial organism's home)"
SAMPLE_RATE_HZ = 16_000
BLOCK_BYTES = 8_000          # 4,000 samples of 16-bit sound: one beat at her ears
LIBRIVOX_API = "https://librivox.org/api/feed/audiobooks/"
ARCHIVE_METADATA = "https://archive.org/metadata/"
ARCHIVE_DOWNLOAD = "https://archive.org/download/"
LIBRIVOX_LICENCE = "public domain (LibriVox: readers release their recordings into the public domain; texts are public domain)"


def _get(url: str, timeout: int = 120) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def librivox_book(title: str, language: str = "English") -> dict:
    """The first LibriVox recording of a title in a language: its Internet
    Archive identifier and the whole recording's length."""

    query = urllib.parse.quote(title)
    fields = "%7Bid,title,language,totaltimesecs,url_zip_file,url_librivox%7D"
    books = json.loads(_get(f"{LIBRIVOX_API}?format=json&limit=10&title={query}&fields={fields}"))["books"]
    book = next((b for b in books if b.get("language") == language), None) or books[0]
    match = re.search(r"compress/([^/]+)/", book["url_zip_file"])
    if match is None:
        raise ValueError("LibriVox book has no Internet Archive identifier")
    return {"id": book["id"], "title": book["title"], "language": book["language"], "seconds": int(book["totaltimesecs"]),
            "archive": match.group(1), "url": book["url_librivox"]}


def chapters(archive: str) -> list[dict]:
    """The chapter recordings of one Internet Archive item, in order (the 64 kb/s
    files when the item has them)."""

    meta = json.loads(_get(f"{ARCHIVE_METADATA}{archive}"))
    files = [f for f in meta["files"] if f["name"].lower().endswith(".mp3")]
    small = [f for f in files if "64kb" in f["name"].lower()]
    files = small or files
    files.sort(key=lambda f: f["name"])
    return [{"name": f["name"], "length": f.get("length"), "size": int(f.get("size") or 0)} for f in files]


def chapter_pcm_path(archive: str, name: str) -> str:
    return os.path.join(LIBRARY, archive, re.sub(r"\.mp3$", ".pcm", name, flags=re.IGNORECASE))


def fetch_chapter(archive: str, name: str) -> str:
    """One chapter converted to her grain of sound and kept; the path of the
    kept sound. Fetched once; a second call returns what is kept."""

    pcm_path = chapter_pcm_path(archive, name)
    if os.path.exists(pcm_path) and os.path.getsize(pcm_path) >= BLOCK_BYTES:
        return pcm_path
    os.makedirs(os.path.dirname(pcm_path), exist_ok=True)
    mp3_path = os.path.join(os.path.dirname(pcm_path), name)
    with open(mp3_path, "wb") as out:
        out.write(_get(f"{ARCHIVE_DOWNLOAD}{archive}/{urllib.parse.quote(name)}", timeout=600))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3_path, "-ac", "1", "-ar", str(SAMPLE_RATE_HZ), "-f", "s16le", pcm_path], check=True)
    os.remove(mp3_path)
    with open(os.path.join(os.path.dirname(pcm_path), "LICENCE.json"), "w") as out:
        json.dump({"archive": archive, "source": f"{ARCHIVE_DOWNLOAD}{archive}", "licence": LIBRIVOX_LICENCE}, out, indent=1)
    return pcm_path


def blocks(pcm_path: str) -> list[bytes]:
    """The chapter as beats of sound, whole blocks only."""

    with open(pcm_path, "rb") as source:
        raw = source.read()
    return [raw[i:i + BLOCK_BYTES] for i in range(0, len(raw) - BLOCK_BYTES + 1, BLOCK_BYTES)]


__all__ = ("LIBRARY", "BLOCK_BYTES", "blocks", "chapters", "fetch_chapter", "librivox_book")
