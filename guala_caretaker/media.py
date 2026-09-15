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
# The listening level: every recording is brought to one integrated loudness
# (EBU R128, -16 LUFS) when it is kept, as a radio's volume is set once and a
# reader speaks at one level; a quiet piano piece and a reader then sit alike at
# one metre, and the room's geometry does the rest at her ears.
LISTENING_LUFS = -16
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
    _convert(mp3_path, pcm_path)
    os.remove(mp3_path)
    with open(os.path.join(os.path.dirname(pcm_path), "LICENCE.json"), "w") as out:
        json.dump({"archive": archive, "source": f"{ARCHIVE_DOWNLOAD}{archive}", "licence": LIBRIVOX_LICENCE}, out, indent=1)
    return pcm_path


def _convert(source: str, pcm_path: str) -> None:
    """One channel, her sample rate, her grain, at the listening level."""

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", source, "-af", f"loudnorm=I={LISTENING_LUFS}:TP=-1.5:LRA=11",
                    "-ac", "1", "-ar", str(SAMPLE_RATE_HZ), "-f", "s16le", pcm_path], check=True)


# A single spoken word is too short for the integrated loudness pass (it needs
# seconds of sound and leaves a half-second word near silence); a word is kept at
# a peak level instead, the same for every word: its loudest sample at half of full
# scale, which is where a reader's own words peak at the listening level.
WORD_PEAK = 0.5


def _convert_word(source: str, pcm_path: str) -> None:
    import struct
    raw_path = pcm_path + ".raw"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", source, "-ac", "1", "-ar", str(SAMPLE_RATE_HZ), "-f", "s16le", raw_path], check=True)
    raw = open(raw_path, "rb").read(); os.remove(raw_path)
    n = len(raw) // 2
    values = struct.unpack(f"<{n}h", raw[: n * 2])
    peak = max(1, max(abs(v) for v in values))
    gain = (WORD_PEAK * 32767) / peak
    scaled = struct.pack(f"<{n}h", *(max(-32768, min(32767, int(round(v * gain)))) for v in values))
    # whole beats only: the tail is padded with silence to the beat boundary
    pad = (-len(scaled)) % BLOCK_BYTES
    with open(pcm_path, "wb") as out:
        out.write(scaled + b"\0" * pad)


def blocks(pcm_path: str) -> list[bytes]:
    """The chapter as beats of sound, whole blocks only."""

    with open(pcm_path, "rb") as source:
        raw = source.read()
    return [raw[i:i + BLOCK_BYTES] for i in range(0, len(raw) - BLOCK_BYTES + 1, BLOCK_BYTES)]


# Music: public-domain recordings kept by the Internet Archive (Musopen's
# releases: orchestral and chamber works recorded and released into the public
# domain). Some items hold their tracks as plain files, some inside one zip.
MUSIC_ITEMS = (
    ("musopen-chopin", "public domain (Musopen)"),
    ("musopen-brahms-symphony-premix", "public domain (Musopen)"),
    ("musopen-mozart-quartet-in-d-minor-k421", "public domain (Musopen)"),
    ("musopen-dvorak-quartet-in-f-major-op-51", "public domain (Musopen)"),
    ("musopen-beethoven-symphony-no-3-eroica-compressed", "public domain (Musopen)"),
)


def tracks(archive: str) -> list[dict]:
    """The sound files of one Archive item, in order: plain mp3/ogg/flac files, or,
    when the item holds one zip, the sound files inside it (named zip!member)."""

    meta = json.loads(_get(f"{ARCHIVE_METADATA}{archive}"))
    sound = [f for f in meta["files"] if f["name"].lower().endswith((".mp3", ".ogg", ".flac"))]
    if sound:
        # One file per piece: an item often holds the same piece as mp3 and ogg.
        preferred = {".mp3": 0, ".ogg": 1, ".flac": 2}
        by_stem: dict[str, dict] = {}
        for f in sorted(sound, key=lambda f: (f["name"].rsplit(".", 1)[0], preferred.get("." + f["name"].rsplit(".", 1)[-1].lower(), 9))):
            by_stem.setdefault(f["name"].rsplit(".", 1)[0], f)
        return [{"name": f["name"], "length": f.get("length"), "size": int(f.get("size") or 0)} for f in by_stem.values()]
    zips = [f for f in meta["files"] if f["name"].lower().endswith(".zip")]
    if not zips:
        return []
    zip_name = sorted(zips, key=lambda f: f["name"])[0]["name"]
    zip_path = _fetch_file(archive, zip_name)
    import zipfile
    with zipfile.ZipFile(zip_path) as z:
        members = sorted(n for n in z.namelist() if n.lower().endswith((".mp3", ".ogg", ".flac")))
    return [{"name": f"{zip_name}!{member}", "length": None, "size": 0} for member in members]


def _fetch_file(archive: str, name: str) -> str:
    path = os.path.join(LIBRARY, archive, name)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as out:
            out.write(_get(f"{ARCHIVE_DOWNLOAD}{archive}/{urllib.parse.quote(name)}", timeout=900))
    return path


def fetch_track(archive: str, name: str, licence: str) -> str:
    """One track converted to her grain of sound and kept; the path of the kept sound."""

    base = name.split("!", 1)
    pcm_path = os.path.join(LIBRARY, archive, re.sub(r"\.(mp3|ogg|flac)$", ".pcm", base[-1].replace("/", "_"), flags=re.IGNORECASE))
    if os.path.exists(pcm_path) and os.path.getsize(pcm_path) >= BLOCK_BYTES:
        return pcm_path
    os.makedirs(os.path.dirname(pcm_path), exist_ok=True)
    if len(base) == 2:
        import zipfile
        zip_path = _fetch_file(archive, base[0])
        with zipfile.ZipFile(zip_path) as z:
            source = os.path.join(LIBRARY, archive, "_member" + os.path.splitext(base[1])[1])
            with z.open(base[1]) as member, open(source, "wb") as out:
                out.write(member.read())
    else:
        source = _fetch_file(archive, base[0])
    _convert(source, pcm_path)
    if len(base) == 2 or source.lower().endswith((".mp3", ".ogg", ".flac")):
        os.remove(source)
    with open(os.path.join(os.path.dirname(pcm_path), "LICENCE.json"), "w") as out:
        json.dump({"archive": archive, "source": f"{ARCHIVE_DOWNLOAD}{archive}", "licence": licence}, out, indent=1)
    return pcm_path


# Spoken words: single English words said by people, from Wikimedia Commons
# (each file openly licensed; the licence read from the file's own record and
# kept beside the sound). The caretaker names a thing with one as it hands it.
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def commons_word(word: str, accent: str = "en-us") -> str | None:
    """One spoken word converted to her grain of sound and kept; the path, or
    None when Commons has no recording under the usual name."""

    import glob
    kept = glob.glob(os.path.join(LIBRARY, "words", f"{accent}-{word}.pcm"))
    if kept:
        return kept[0]
    title = f"File:{accent.capitalize()}-{word}.ogg"
    query = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|extmetadata", "format": "json"})
    pages = json.loads(_get(f"{COMMONS_API}?{query}"))["query"]["pages"]
    page = next(iter(pages.values()))
    info = (page.get("imageinfo") or [None])[0]
    if info is None:
        return None
    meta = info.get("extmetadata") or {}
    licence = (meta.get("LicenseShortName") or {}).get("value") or (meta.get("License") or {}).get("value") or "unknown"
    author = (meta.get("Artist") or {}).get("value") or "unknown"
    folder = os.path.join(LIBRARY, "words")
    os.makedirs(folder, exist_ok=True)
    source = os.path.join(folder, f"{accent}-{word}.ogg")
    with open(source, "wb") as out:
        out.write(_get(info["url"], timeout=300))
    pcm_path = os.path.join(folder, f"{accent}-{word}.pcm")
    _convert_word(source, pcm_path)
    os.remove(source)
    record_path = os.path.join(folder, "LICENCES.json")
    records = json.load(open(record_path)) if os.path.exists(record_path) else {}
    records[f"{accent}-{word}"] = {"title": title, "url": info["url"], "licence": licence, "author": re.sub(r"<[^>]+>", "", author)}
    json.dump(records, open(record_path, "w"), indent=1)
    return pcm_path


__all__ = ("LIBRARY", "BLOCK_BYTES", "MUSIC_ITEMS", "blocks", "chapters", "commons_word", "fetch_chapter", "fetch_track", "librivox_book", "tracks")
