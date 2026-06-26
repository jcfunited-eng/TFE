"""world_feeds.py — Guala reads beyond her books: Khan Academy + YouTube.

Two extra text feeds for her autonomous study, using the keys that are present:
  - KHAN: Tavily web search restricted to khanacademy.org -> real article text.
  - YOUTUBE: YouTube Data API (key) search of curated child/educational queries ->
    video titles + descriptions. (Transcripts need OAuth / are IP-blocked from the
    datacenter, so this is the text ABOUT the videos, reliably available.)

Network IO lives here; feeding the substrate stays in the caller. Key-optional and
fully exception-walled: any miss returns [] so her study loop just moves on. Content
is lightly cleaned (drop boilerplate/URLs); her clean-token gate does the rest.
"""

import json
import os
import re
import urllib.parse
import urllib.request

# rotating child-appropriate topics so she reads broadly, not the same page
KHAN_QUERIES = [
    "story for young children about animals", "counting numbers for kids",
    "the water cycle for children", "colors and shapes for kids",
    "kindness and feelings for children", "plants and how they grow for kids",
    "the sun moon and stars for children", "community helpers for kids",
    "healthy food for children", "weather and seasons for kids",
]
YOUTUBE_QUERIES = [
    "Ms Rachel learn first words toddler", "Sesame Street learn letters",
    "learn colors for toddlers song", "counting numbers song for kids",
    "animal sounds for children", "nursery rhymes for babies",
    "learn shapes for preschool", "bedtime story for toddlers",
    "Cocomelon learning song", "phonics songs for kids",
]

_BOILERPLATE = re.compile(
    r"subscribe|copyright|all rights reserved|cookie|privacy policy|terms of|"
    r"sign in|log in|click here|http\S+|www\.\S+|\bvideo\b.*\bdownload\b|"
    r"\bno ads\b|\bads\b|\bsponsored\b|\baffiliate\b|\bpromo\b|\bdiscount\b|"
    r"\bcheckout\b|\badd to cart\b|\bfree trial\b|\bsign up\b|\bcreate account\b|"
    r"\bwatch now\b|\bstream now\b|\bdownload now\b|\bget it now\b|"
    r"\bpatreon\b|\bmerch\b|\bnotification bell\b|\blike and subscribe\b",
    re.IGNORECASE)


def _clean_lines(text, max_lines=80):
    """Split to sentence-ish lines, drop boilerplate/URLs/very short bits."""
    out = []
    for raw in re.split(r"(?<=[.!?])\s+|\n+", text or ""):
        s = raw.strip()
        if len(s) < 12 or len(s) > 240:
            continue
        if _BOILERPLATE.search(s):
            continue
        # must look like prose (has letters and a couple words)
        if len(s.split()) < 3 or not re.search(r"[A-Za-z]", s):
            continue
        out.append(s)
        if len(out) >= max_lines:
            break
    return out


def khan_text(query, timeout=25):
    """Tavily search of Khan Academy for `query` -> list of clean sentences. []."""
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        return []
    try:
        body = json.dumps({
            "api_key": key, "query": query, "max_results": 3,
            "include_domains": ["khanacademy.org"], "include_raw_content": True,
        }).encode()
        req = urllib.request.Request(
            "https://api.tavily.com/search", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        text = " ".join((r.get("raw_content") or r.get("content") or "")
                        for r in data.get("results", []))
        return _clean_lines(text)
    except Exception:
        return []


def youtube_text(query, timeout=25):
    """YouTube Data API search -> titles + descriptions as clean sentences. []."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        return []
    try:
        params = urllib.parse.urlencode({
            "part": "snippet", "q": query, "type": "video", "maxResults": 6,
            "safeSearch": "strict", "videoEmbeddable": "true", "key": key,
        })
        url = "https://www.googleapis.com/youtube/v3/search?" + params
        req = urllib.request.Request(url, headers={"User-Agent": "GualaLoom/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        chunks = []
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            chunks.append(sn.get("title", ""))
            chunks.append(sn.get("description", ""))
        return _clean_lines(" . ".join(c for c in chunks if c))
    except Exception:
        return []


# the feeds, named, with their rotating query lists — for round-robin study
FEEDS = [
    {"name": "khan", "queries": KHAN_QUERIES, "fetch": khan_text},
    {"name": "youtube", "queries": YOUTUBE_QUERIES, "fetch": youtube_text},
]
