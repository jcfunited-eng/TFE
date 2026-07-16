"""World-feed adapters with explicit registration and availability truth.

Two extra text feeds for her autonomous study, using the keys that are present:
  - KHAN: Tavily web search restricted to khanacademy.org -> real article text.
  - YOUTUBE: YouTube Data API (key) search of curated child/educational queries ->
    video titles + descriptions. (Transcripts need OAuth / are IP-blocked from the
    datacenter, so this is the text ABOUT the videos, reliably available.)

Network IO lives here; feeding the substrate stays in the caller.  A feed is not
registered without its credential.  ``feed_status`` always reports why an optional
feed is disabled, so missing configuration cannot masquerade as an empty result.

REBUILD (GL-SPC-SUBSTRATE-TRUE-SINGLE-STACK-20260716-v3, Environment table):
the old behavior was 10 fixed queries per feed cycling forever — a stale
goldfish bowl.  Now each feed draws from a large rotating topic pool
(seasons, animals, places, simple science, stories, daily life, ...) via
``next_query``, which guarantees no query repeats within
WORLD_FEED_NO_REPEAT_CYCLES fetches (default 50), and every fetch is bounded
by a per-fetch byte budget (WORLD_FEED_FETCH_BYTE_BUDGET, default 64 KiB).
Feed content still enters as ordinary reading experience through the
caller's existing path; the quality gates are unchanged.
"""

import collections
import json
import os
import random
import re
import threading
import urllib.parse
import urllib.request

# ── rotating child-appropriate topic pools ──────────────────────────────────
# Age-appropriate for an early-language learner; grouped by topic set so the
# breadth is auditable.  The original 10 queries per feed are all still
# present inside their categories (continuity with what she has already
# read), but the pool is ~8x larger and rotation makes the old
# same-10-forever loop structurally impossible.

KHAN_TOPIC_SETS = {
    "animals": [
        "animals and their babies for kids", "how birds fly for children",
        "what fish eat for kids", "animal homes and habitats for kids",
        "farm animals for children", "ocean animals for kids",
        "insects and bugs for children",
        "how animals stay warm in winter for kids",
        "frogs and tadpoles for children", "big cats and small cats for kids",
    ],
    "seasons_weather": [
        "weather and seasons for kids", "why it rains for children",
        "snow and winter for kids", "spring flowers for children",
        "summer sunshine for kids", "autumn leaves for children",
        "clouds in the sky for kids", "wind and storms for children",
        "the four seasons for kids", "hot days and cold days for children",
    ],
    "places": [
        "life on a farm for kids", "the beach and the ocean for children",
        "forests and trees for kids", "rivers and lakes for children",
        "mountains for kids", "gardens and growing for children",
        "the city and the town for kids", "deserts for children",
        "ponds and puddles for kids", "islands for children",
    ],
    "simple_science": [
        "the water cycle for children", "the sun moon and stars for children",
        "day and night for kids", "plants and how they grow for kids",
        "seeds and sprouts for children", "floating and sinking for kids",
        "shadows and light for children", "magnets for kids",
        "colors of the rainbow for children", "how rain helps plants for kids",
        "rocks and soil for children", "the five senses for kids",
    ],
    "stories_language": [
        "story for young children about animals", "fairy tales for children",
        "nursery rhymes for kids", "counting stories for children",
        "picture stories for kids", "rhyming words for children",
        "the alphabet for kids", "first words for toddlers",
        "simple poems for children", "bedtime stories for kids",
    ],
    "daily_life": [
        "healthy food for children", "fruits and vegetables for kids",
        "getting dressed for children", "brushing teeth for kids",
        "helping at home for children", "bath time for kids",
        "bedtime and sleep for children",
        "breakfast lunch and dinner for kids",
        "washing hands for children", "playing outside for kids",
    ],
    "people_feelings": [
        "kindness and feelings for children", "sharing with friends for kids",
        "families for children", "community helpers for kids",
        "saying please and thank you for children", "making friends for kids",
        "feeling happy and sad for children", "taking turns for kids",
        "helping others for children", "being brave for kids",
    ],
    "numbers_shapes": [
        "counting numbers for kids", "colors and shapes for kids",
        "big and small for children", "counting to ten for kids",
        "circles squares and triangles for children", "patterns for kids",
        "more and less for children", "first second and third for kids",
        "sorting and matching for children", "counting animals for kids",
    ],
}

YOUTUBE_TOPIC_SETS = {
    "songs_words": [
        "Ms Rachel learn first words toddler", "Sesame Street learn letters",
        "learn colors for toddlers song", "counting numbers song for kids",
        "nursery rhymes for babies", "phonics songs for kids",
        "Cocomelon learning song", "abc song for toddlers",
        "old macdonald had a farm song", "wheels on the bus song for kids",
    ],
    "animals": [
        "animal sounds for children", "baby animals for toddlers",
        "farm animals video for kids", "zoo animals for children",
        "ocean animals for toddlers", "birds singing for children",
        "puppies and kittens for kids", "elephants for toddlers",
        "dinosaur songs for kids", "butterfly life cycle for children",
    ],
    "seasons_weather": [
        "seasons song for kids", "rain rain go away song",
        "snow video for toddlers", "sunny day song for children",
        "autumn leaves for kids video", "spring flowers for toddlers",
        "weather song for children", "rainbow song for kids",
        "clouds video for toddlers", "windy day for children",
    ],
    "stories": [
        "bedtime story for toddlers", "fairy tale read aloud for kids",
        "goodnight moon read aloud",
        "the very hungry caterpillar read aloud",
        "story time for preschool", "gentle stories for toddlers",
        "picture book read aloud for children",
        "three little pigs story for kids",
        "goldilocks story for children", "counting story for toddlers",
    ],
    "shapes_numbers": [
        "learn shapes for preschool", "counting to ten for toddlers",
        "shape song for kids", "number song for children",
        "big and small for toddlers", "sorting colors for kids",
        "patterns for preschool", "matching game song for toddlers",
        "five little ducks song", "ten in the bed song for kids",
    ],
    "daily_life": [
        "brush your teeth song for kids", "bath time song for toddlers",
        "getting dressed song for children", "healthy food song for kids",
        "clean up song for toddlers", "wash your hands song for children",
        "good morning song for preschool", "bedtime routine for toddlers",
        "please and thank you song for kids", "sharing song for children",
    ],
    "places": [
        "farm visit for toddlers", "beach day for children",
        "forest walk for kids", "garden for toddlers video",
        "playground song for children", "train ride for kids",
        "boat song for toddlers", "airplane video for children",
        "city sounds for kids", "camping for toddlers",
    ],
    "simple_science": [
        "day and night for kids", "the sun for toddlers",
        "moon and stars song for children",
        "plant growing time lapse for kids", "float or sink for children",
        "shadow play for toddlers", "magnet video for kids",
        "water cycle song for children", "five senses song for kids",
        "animal habitats for children",
    ],
}

# Flattened pools (kept under the original names: the feed registry and its
# callers/tests see one flat list per feed, exactly as before — just bigger).
KHAN_QUERIES = [q for _set in KHAN_TOPIC_SETS.values() for q in _set]
YOUTUBE_QUERIES = [q for _set in YOUTUBE_TOPIC_SETS.values() for q in _set]

_QUERY_POOLS = {"khan": KHAN_QUERIES, "youtube": YOUTUBE_QUERIES}

# ── rotation: no query repeats within N fetch cycles ────────────────────────
_DEFAULT_NO_REPEAT_CYCLES = 50

_rotation_lock = threading.Lock()
_rotation_recent: dict[str, collections.deque] = {}


def _no_repeat_cycles():
    """N: a query used now cannot be reused for the next N fetches."""
    try:
        n = int(os.environ.get("WORLD_FEED_NO_REPEAT_CYCLES",
                               str(_DEFAULT_NO_REPEAT_CYCLES)))
    except ValueError:
        n = _DEFAULT_NO_REPEAT_CYCLES
    return max(1, n)


def next_query(feed_name):
    """Draw the next query for ``feed_name`` from its rotating topic pool.

    Guarantee: the returned query has not been returned for this feed within
    the last N calls (N = WORLD_FEED_NO_REPEAT_CYCLES, default 50, clamped to
    pool size - 1 so a draw always exists).  Thread-safe; state is
    per-process and resets on restart, which only restarts rotation — it can
    never recreate a fixed short loop.
    """
    pool = _QUERY_POOLS.get(feed_name)
    if not pool:
        raise KeyError(f"unknown world feed: {feed_name!r}")
    window = min(_no_repeat_cycles(), len(pool) - 1)
    with _rotation_lock:
        recent = _rotation_recent.setdefault(feed_name, collections.deque())
        while len(recent) > window:  # window is env-tunable live
            recent.popleft()
        recent_set = set(recent)
        candidates = [q for q in pool if q not in recent_set]
        query = random.choice(candidates)
        recent.append(query)
        while len(recent) > window:
            recent.popleft()
    return query


def rotation_status():
    """Honest rotation/budget telemetry (no credentials, no queries leaked)."""
    with _rotation_lock:
        recently = {name: len(_rotation_recent.get(name, ()))
                    for name in _QUERY_POOLS}
    return {
        "no_repeat_cycles": _no_repeat_cycles(),
        "fetch_byte_budget": _fetch_byte_budget(),
        "pools": {name: {"pool_size": len(pool),
                         "recently_used": recently[name]}
                  for name, pool in _QUERY_POOLS.items()},
    }


# ── per-fetch byte budget ────────────────────────────────────────────────────
_DEFAULT_FETCH_BYTE_BUDGET = 65536  # 64 KiB of raw feed text per fetch


def _fetch_byte_budget():
    try:
        budget = int(os.environ.get("WORLD_FEED_FETCH_BYTE_BUDGET",
                                    str(_DEFAULT_FETCH_BYTE_BUDGET)))
    except ValueError:
        budget = _DEFAULT_FETCH_BYTE_BUDGET
    return max(1024, budget)


def _truncate_to_byte_budget(text):
    """Cap raw feed text at the per-fetch byte budget (UTF-8 safe)."""
    encoded = (text or "").encode("utf-8")
    budget = _fetch_byte_budget()
    if len(encoded) <= budget:
        return text or ""
    return encoded[:budget].decode("utf-8", "ignore")


class FeedResponseOverCap(ValueError):
    """A feed response exceeded the bounded network read cap."""


def _read_response_capped(resp):
    """Bounded network read: never pull unbounded bytes off the wire.

    The hard cap is 8x the text budget (floor 256 KiB) so a normal JSON
    envelope always fits; a response bigger than that raises
    FeedResponseOverCap and the fetch reports empty — with its own log line
    so a chronically oversize query is distinguishable from a genuinely
    empty one in telemetry (adversarial-review nit, 2026-07-16).
    """
    cap = max(8 * _fetch_byte_budget(), 262144)
    raw = resp.read(cap + 1)
    if len(raw) > cap:
        raise FeedResponseOverCap(
            f"world-feed response exceeded the network cap ({cap} bytes)")
    return raw

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
            data = json.loads(_read_response_capped(resp))
        text = " ".join((r.get("raw_content") or r.get("content") or "")
                        for r in data.get("results", []))
        return _clean_lines(_truncate_to_byte_budget(text))
    except FeedResponseOverCap as over:
        print(f"[worldfeed] khan {query!r}: response over network cap "
              f"({over}) — reported empty")
        return []
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
            data = json.loads(_read_response_capped(resp))
        chunks = []
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            chunks.append(sn.get("title", ""))
            chunks.append(sn.get("description", ""))
        text = " . ".join(c for c in chunks if c)
        return _clean_lines(_truncate_to_byte_budget(text))
    except FeedResponseOverCap as over:
        print(f"[worldfeed] youtube {query!r}: response over network cap "
              f"({over}) — reported empty")
        return []
    except Exception:
        return []


_FEED_DEFINITIONS = (
    ("khan", "TAVILY_API_KEY", KHAN_QUERIES, khan_text),
    ("youtube", "YOUTUBE_API_KEY", YOUTUBE_QUERIES, youtube_text),
)


def feed_status() -> dict[str, dict[str, object]]:
    """Report each feed's registration state without exposing credentials."""
    return {
        name: {
            "enabled": bool(os.environ.get(secret_name, "").strip()),
            "reason": (
                "configured"
                if os.environ.get(secret_name, "").strip()
                else f"disabled: {secret_name} is not configured"
            ),
        }
        for name, secret_name, _queries, _fetch in _FEED_DEFINITIONS
    }


def available_feeds() -> list[dict[str, object]]:
    """Return only feeds whose credential is configured at call time."""
    return [
        {"name": name, "queries": queries, "fetch": fetch}
        for name, secret_name, queries, fetch in _FEED_DEFINITIONS
        if os.environ.get(secret_name, "").strip()
    ]
