"""World-feed rotation + per-fetch byte budget (spec v3, Environment REBUILD).

The old behavior — the same 10 queries per feed cycling forever — is replaced
by large rotating topic pools with a no-repeat window and a per-fetch byte
budget.  These tests prove:

  - the pools are meaningfully larger than the old fixed 10 and contain the
    original 10 queries (continuity with what she has already read);
  - no query repeats within N cycles (default 50; env-tunable), for every
    registered feed, including YouTube when its key exists;
  - the per-fetch byte budget is enforced on real fetch plumbing (fake HTTP
    response, real khan_text/youtube_text code path) and the quality gate
    (_clean_lines boilerplate/prose filter) still runs;
  - the substrate_runner loop draws queries through the rotation (never a
    fixed index) and still alternates across every available feed.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dsf_ai_service.loom_model import world_feeds  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_rotation(monkeypatch):
    """Isolate rotation state and budget env per test."""
    monkeypatch.setattr(world_feeds, "_rotation_recent", {})
    monkeypatch.delenv("WORLD_FEED_NO_REPEAT_CYCLES", raising=False)
    monkeypatch.delenv("WORLD_FEED_FETCH_BYTE_BUDGET", raising=False)


# ── pools: large, unique, age-appropriate continuity ─────────────────────────

_ORIGINAL_KHAN = [
    "story for young children about animals", "counting numbers for kids",
    "the water cycle for children", "colors and shapes for kids",
    "kindness and feelings for children", "plants and how they grow for kids",
    "the sun moon and stars for children", "community helpers for kids",
    "healthy food for children", "weather and seasons for kids",
]
_ORIGINAL_YOUTUBE = [
    "Ms Rachel learn first words toddler", "Sesame Street learn letters",
    "learn colors for toddlers song", "counting numbers song for kids",
    "animal sounds for children", "nursery rhymes for babies",
    "learn shapes for preschool", "bedtime story for toddlers",
    "Cocomelon learning song", "phonics songs for kids",
]


@pytest.mark.parametrize("pool,originals", [
    (world_feeds.KHAN_QUERIES, _ORIGINAL_KHAN),
    (world_feeds.YOUTUBE_QUERIES, _ORIGINAL_YOUTUBE),
])
def test_pools_are_large_unique_and_keep_the_original_queries(pool, originals):
    assert len(pool) >= 60, "pool must be meaningfully larger than the old 10"
    assert len(set(pool)) == len(pool), "no duplicate queries within a feed"
    for query in originals:
        assert query in pool, f"original query dropped: {query!r}"
    # Larger than the default no-repeat window, so a draw always exists.
    assert len(pool) > world_feeds._DEFAULT_NO_REPEAT_CYCLES


def test_default_no_repeat_window_makes_the_old_10_cycle_impossible():
    assert world_feeds._no_repeat_cycles() >= 50


# ── rotation: no repeat within N cycles ──────────────────────────────────────

def _assert_min_repeat_gap(draws, window):
    last_seen = {}
    for i, query in enumerate(draws):
        if query in last_seen:
            gap = i - last_seen[query]
            assert gap > window, (
                f"query {query!r} repeated after {gap} draws "
                f"(window={window})")
        last_seen[query] = i


@pytest.mark.parametrize("feed_name", ["khan", "youtube"])
def test_no_query_repeats_within_default_window(feed_name):
    window = world_feeds._no_repeat_cycles()
    pool_size = len(world_feeds._QUERY_POOLS[feed_name])
    draws = [world_feeds.next_query(feed_name)
             for _ in range(pool_size * 3)]
    _assert_min_repeat_gap(draws, min(window, pool_size - 1))
    # Rotation actually rotates: far more distinct queries than the old 10.
    assert len(set(draws)) > 10


def test_no_repeat_window_is_env_tunable(monkeypatch):
    monkeypatch.setenv("WORLD_FEED_NO_REPEAT_CYCLES", "5")
    draws = [world_feeds.next_query("khan") for _ in range(200)]
    _assert_min_repeat_gap(draws, 5)


def test_window_larger_than_pool_is_clamped_and_never_deadlocks(monkeypatch):
    monkeypatch.setenv("WORLD_FEED_NO_REPEAT_CYCLES", "100000")
    pool_size = len(world_feeds.KHAN_QUERIES)
    draws = [world_feeds.next_query("khan") for _ in range(pool_size * 2)]
    _assert_min_repeat_gap(draws, pool_size - 1)


def test_unknown_feed_fails_loudly():
    with pytest.raises(KeyError, match="unknown world feed"):
        world_feeds.next_query("invented_feed")


def test_rotation_status_reports_pools_window_and_budget():
    world_feeds.next_query("khan")
    status = world_feeds.rotation_status()
    assert status["no_repeat_cycles"] == world_feeds._no_repeat_cycles()
    assert status["fetch_byte_budget"] == world_feeds._fetch_byte_budget()
    assert status["pools"]["khan"]["pool_size"] == len(
        world_feeds.KHAN_QUERIES)
    assert status["pools"]["khan"]["recently_used"] == 1
    assert status["pools"]["youtube"]["recently_used"] == 0


# ── per-fetch byte budget ────────────────────────────────────────────────────

def test_truncation_enforces_the_budget_and_is_utf8_safe(monkeypatch):
    monkeypatch.setenv("WORLD_FEED_FETCH_BYTE_BUDGET", "2048")
    text = ("La lluvia cae y el jardín crece. " * 400)  # multibyte chars
    out = world_feeds._truncate_to_byte_budget(text)
    assert len(out.encode("utf-8")) <= 2048
    assert out == text[:len(out)], "truncation only, never mangled text"


def test_budget_has_a_sane_default_and_floor(monkeypatch):
    assert world_feeds._fetch_byte_budget() == 65536
    monkeypatch.setenv("WORLD_FEED_FETCH_BYTE_BUDGET", "12")
    assert world_feeds._fetch_byte_budget() == 1024, "floor holds"
    monkeypatch.setenv("WORLD_FEED_FETCH_BYTE_BUDGET", "not-a-number")
    assert world_feeds._fetch_byte_budget() == 65536


class _FakeResponse:
    def __init__(self, body):
        self._body = body
        self.read_caps = []

    def read(self, amt=None):
        self.read_caps.append(amt)
        if amt is None:
            return self._body
        chunk, self._body = self._body[:amt], self._body[amt:]
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_khan_fetch_respects_budget_through_the_real_code_path(monkeypatch):
    monkeypatch.setenv("WORLD_FEED_FETCH_BYTE_BUDGET", "4096")
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    sentence = "The little frog jumped over the shining river stones. "
    body = json.dumps(
        {"results": [{"raw_content": sentence * 4000}]}).encode()
    fake = _FakeResponse(body)
    monkeypatch.setattr(world_feeds.urllib.request, "urlopen",
                        lambda req, timeout=0: fake)

    lines = world_feeds.khan_text("ponds and puddles for kids")

    assert lines, "clean prose within budget must survive"
    total = len(" ".join(lines).encode("utf-8"))
    assert total <= 4096, f"fed text exceeded the byte budget ({total})"
    assert fake.read_caps and fake.read_caps[0] is not None, (
        "the network read itself must be capped, not just the parsed text")


def test_khan_fetch_rejects_a_response_over_the_network_cap(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "k")
    cap = max(8 * world_feeds._fetch_byte_budget(), 262144)
    fake = _FakeResponse(b"x" * (cap + 10))
    monkeypatch.setattr(world_feeds.urllib.request, "urlopen",
                        lambda req, timeout=0: fake)
    assert world_feeds.khan_text("anything") == []


def test_youtube_fetch_respects_budget_and_quality_gate(monkeypatch):
    monkeypatch.setenv("WORLD_FEED_FETCH_BYTE_BUDGET", "2048")
    monkeypatch.setenv("YOUTUBE_API_KEY", "k")
    items = [{"snippet": {
        "title": "The gentle cow sings a quiet song at the red barn.",
        "description": "Subscribe now! " +
                       "A soft story about a duck who learns to share. " * 40,
    }} for _ in range(30)]
    fake = _FakeResponse(json.dumps({"items": items}).encode())
    monkeypatch.setattr(world_feeds.urllib.request, "urlopen",
                        lambda req, timeout=0: fake)

    lines = world_feeds.youtube_text("counting story for toddlers")

    assert lines
    assert len(" ".join(lines).encode("utf-8")) <= 2048
    assert not any("Subscribe" in line for line in lines), (
        "the existing boilerplate quality gate must keep running")


# ── the runner draws through rotation and alternates all feeds ───────────────

def test_runner_uses_rotation_and_alternates_available_feeds(monkeypatch):
    from dsf_ai_service import substrate_runner

    seen = []

    def _fake_fetch(query, timeout=25):
        return []  # "empty" short-circuits before any substrate touch

    monkeypatch.setenv("TAVILY_API_KEY", "k")
    monkeypatch.setenv("YOUTUBE_API_KEY", "k")  # YouTube participates
    monkeypatch.setattr(world_feeds, "khan_text", _fake_fetch)
    monkeypatch.setattr(world_feeds, "youtube_text", _fake_fetch)
    monkeypatch.setattr(
        substrate_runner, "_WORLD_FEED_STATE",
        {"feed_idx": 0, "last_status": {}})

    real_next_query = world_feeds.next_query

    def _recording_next_query(feed_name):
        query = real_next_query(feed_name)
        seen.append((feed_name, query))
        return query

    monkeypatch.setattr(world_feeds, "next_query", _recording_next_query)

    results = [substrate_runner._world_feed_once() for _ in range(40)]

    assert all(r["state"] == "empty" for r in results)
    feed_names = [name for name, _ in seen]
    assert set(feed_names) == {"khan", "youtube"}, (
        "every keyed feed participates in rotation")
    assert feed_names[:4] == ["khan", "youtube", "khan", "youtube"]
    for feed_name in ("khan", "youtube"):
        draws = [q for name, q in seen if name == feed_name]
        _assert_min_repeat_gap(
            draws, min(world_feeds._no_repeat_cycles(),
                       len(world_feeds._QUERY_POOLS[feed_name]) - 1))
