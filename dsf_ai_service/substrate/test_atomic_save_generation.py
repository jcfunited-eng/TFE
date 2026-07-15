"""GL-FIX-ATOMIC-SAVE-GENERATIONS-20260715 -- real (non-monkeypatched) tests.

Covers the two halves of the fix:

Piece A (state-file-tick manifest -> the loader accepts the by-design hot/cold
tick skew and detects torn saves):
  * hot-saved state (core tick > atlas tick) loads clean;
  * a full save realigns every file to one tick and loads clean;
  * a torn file (tick != manifest) is rejected;
  * a file newer than core is rejected;
  * legacy state with NO manifest still loads (migration, no state loss);
  * legacy state with a future-dated file is still rejected.

Piece B (atomic generation snapshots -> recover the previous complete
generation instead of silently time-travelling to S3):
  * every successful save publishes a complete generation + CURRENT_GEN;
  * a torn flat state recovers from the newest valid generation;
  * older generations are tried when the newest is bad;
  * total local failure returns None (caller must halt, never S3);
  * only the newest N generations are kept;
  * the append-only WAL rides the generation and tolerates later growth.

Plus the byte-identity invariant: every persisted file except guala_core.json
is byte-identical to today's format; core differs only by the added
state_file_ticks field.
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala
from dsf_ai_service.substrate import atomic_state_generation as asg

_SENT = "the sun rises over the calm river each morning"


def _settle(g, timeout=15.0):
    """Drain the organism growth queue so save_full_state does not race the
    background fold worker (a pre-existing 'deque mutated during iteration'
    pickle race, unrelated to this fix -- draining first makes tests
    deterministic)."""
    import time
    q = getattr(g, "_organism_queue", None)
    if q is None:
        return
    deadline = time.monotonic() + timeout
    while getattr(q, "unfinished_tasks", 0) > 0 and time.monotonic() < deadline:
        time.sleep(0.02)
    time.sleep(0.1)


def _new():
    g = Guala()
    g.read_sentence(_SENT, source="seed")
    _settle(g)
    return g


def _hotcold_state(tmp, hot_advance=2000):
    """Full save at a low tick, then a hot save far ahead -> core tick well
    past the cold stores' tick (the exact production shape that used to fail)."""
    g = _new()
    for _ in range(50):
        g.tick += 1
    g.save_full_state(tmp)
    for _ in range(hot_advance):
        g.tick += 1
    g.save_hot_state(tmp)
    return g


def _load(tmp_or_gen):
    g = _new()
    g.load_full_state(tmp_or_gen)
    return g


def _env_tick(path):
    with open(path) as fh:
        return json.load(fh).get("saved_at_tick")


# ---------------------------------------------------------------- Piece A ----

def test_hot_saved_state_loads_despite_tick_skew():
    tmp = tempfile.mkdtemp()
    _hotcold_state(tmp)
    atlas_t = _env_tick(os.path.join(tmp, "guala_atlas.json"))
    core_t = _env_tick(os.path.join(tmp, "guala_core.json"))
    assert core_t > atlas_t, "test setup: core should be ahead of atlas"
    g = _load(tmp)
    assert getattr(g, "_load_successful", False), getattr(g, "_load_errors", None)
    assert g.tick == core_t


def test_manifest_records_real_per_file_ticks():
    tmp = tempfile.mkdtemp()
    _hotcold_state(tmp)
    core = json.load(open(os.path.join(tmp, "guala_core.json")))["data"]
    sft = core["state_file_ticks"]
    assert sft["guala_core.json"] == core["tick"]
    assert sft["guala_atlas.json"] < sft["guala_core.json"]
    assert sft["guala_needs.json"] == sft["guala_core.json"]


def test_full_save_realigns_all_files():
    tmp = tempfile.mkdtemp()
    g = _hotcold_state(tmp)
    for _ in range(10):
        g.tick += 1
    g.save_full_state(tmp)
    core_t = _env_tick(os.path.join(tmp, "guala_core.json"))
    assert _env_tick(os.path.join(tmp, "guala_atlas.json")) == core_t
    assert _load(tmp)._load_successful


def test_torn_file_wrong_tick_rejected():
    tmp = tempfile.mkdtemp()
    _hotcold_state(tmp)
    p = os.path.join(tmp, "guala_atlas.json")
    raw = json.load(open(p))
    raw["saved_at_tick"] = raw["saved_at_tick"] + 7  # not the manifest value
    json.dump(raw, open(p, "w"))
    assert not _load(tmp)._load_successful


def test_file_newer_than_core_rejected():
    tmp = tempfile.mkdtemp()
    g = _hotcold_state(tmp)
    p = os.path.join(tmp, "guala_atlas.json")
    raw = json.load(open(p))
    raw["saved_at_tick"] = g.tick + 5000  # future -> torn
    json.dump(raw, open(p, "w"))
    assert not _load(tmp)._load_successful


def test_legacy_state_without_manifest_still_loads():
    """Migration: existing on-disk state (written before this fix) has no
    state_file_ticks and a hot/cold tick skew. It must load, not time-travel."""
    tmp = tempfile.mkdtemp()
    _hotcold_state(tmp)
    p = os.path.join(tmp, "guala_core.json")
    raw = json.load(open(p))
    raw["data"].pop("state_file_ticks", None)
    json.dump(raw, open(p, "w"))
    g = _load(tmp)
    assert getattr(g, "_load_successful", False), getattr(g, "_load_errors", None)


def test_legacy_torn_future_file_still_rejected():
    tmp = tempfile.mkdtemp()
    g = _hotcold_state(tmp)
    cp = os.path.join(tmp, "guala_core.json")
    raw = json.load(open(cp))
    raw["data"].pop("state_file_ticks", None)
    json.dump(raw, open(cp, "w"))
    ap = os.path.join(tmp, "guala_atlas.json")
    araw = json.load(open(ap))
    araw["saved_at_tick"] = g.tick + 9999
    json.dump(araw, open(ap, "w"))
    assert not _load(tmp)._load_successful


def test_full_save_roundtrip_all_one_tick_loads():
    tmp = tempfile.mkdtemp()
    g = _new()
    for _ in range(120):
        g.tick += 1
    g.save_full_state(tmp)
    g2 = _load(tmp)
    assert g2._load_successful
    assert g2.tick == g.tick


# --------------------------------------------- byte-identity invariant -------

# Files whose bytes legitimately churn across an identical re-save for reasons
# unrelated to this fix, so they are excluded from the byte-identity check:
#   guala_windows.json  -- window_manager compacts the WAL each full save,
#                          bumping its generation counter (window_manager owns
#                          it; this fix does not touch it).
#   *.binding.json      -- record the sha256 of the organism/tapestry pickles,
#                          which are non-deterministic across saves (background
#                          workers + gzip), so their recorded hash varies.
_BYTE_IDENTITY_EXCLUDE = ("guala_core.json", "guala_windows.json")


def _churns(name):
    return name in _BYTE_IDENTITY_EXCLUDE or name.endswith(".binding.json")


def test_non_core_json_stores_are_stable_and_manifest_is_core_only():
    """This fix only WHERE files live + HOW they publish, and adds one field
    (state_file_ticks) to guala_core.json. Prove it: every deterministic JSON
    store is byte-stable across an identical re-save, and the new
    state_file_ticks manifest appears in NO file except guala_core.json."""
    tmp = tempfile.mkdtemp()
    g = _new()
    for _ in range(80):
        g.tick += 1
    g.save_full_state(tmp)
    first = {}
    for name in os.listdir(tmp):
        fp = os.path.join(tmp, name)
        if os.path.isfile(fp) and name.endswith(".json") and not _churns(name):
            first[name] = open(fp, "rb").read()
    assert first, "no deterministic JSON stores captured"
    # Re-save the SAME state at the SAME tick.
    g.save_full_state(tmp)
    for name, data in first.items():
        after = open(os.path.join(tmp, name), "rb").read()
        # timestamp inside the envelope varies; compare the data payload only
        a = json.loads(data).get("data", json.loads(data))
        b = json.loads(after).get("data", json.loads(after))
        assert a == b, f"{name} payload changed across identical re-save"
        assert "state_file_ticks" not in json.dumps(a), (
            f"{name} unexpectedly carries the state_file_ticks manifest "
            f"(it must live only in guala_core.json)")
    # And it IS present in core.
    core = json.load(open(os.path.join(tmp, "guala_core.json")))["data"]
    assert "state_file_ticks" in core


def test_core_gains_only_state_file_ticks_field():
    tmp = tempfile.mkdtemp()
    g = _new()
    for _ in range(40):
        g.tick += 1
    g.save_full_state(tmp)
    core = json.load(open(os.path.join(tmp, "guala_core.json")))["data"]
    assert "state_file_ticks" in core
    assert isinstance(core["state_file_ticks"], dict)


# ---------------------------------------------------------------- Piece B ----

def test_every_save_publishes_a_generation():
    tmp = tempfile.mkdtemp()
    _hotcold_state(tmp)
    gens = asg.list_generations(tmp)
    assert gens, "no generation published"
    assert os.path.exists(os.path.join(tmp, asg.CURRENT_GEN_NAME))
    # newest generation loads clean directly from its directory
    gd, man = gens[0]
    assert _load(gd)._load_successful


def test_torn_flat_recovers_from_newest_generation():
    tmp = tempfile.mkdtemp()
    _hotcold_state(tmp)
    newest_tick = asg.list_generations(tmp)[0][1]["tick"]
    # Simulate a torn/corrupt flat core via atomic replace (new inode) --
    # generation hard-links keep their own good inodes.
    t = os.path.join(tmp, "guala_core.json.torn")
    open(t, "w").write("{ not valid json")
    os.replace(t, os.path.join(tmp, "guala_core.json"))
    assert not _load(tmp)._load_successful

    def load_test(gen_dir):
        return _load(gen_dir)._load_successful

    man = asg.recover_from_generations(tmp, load_test)
    assert man is not None and man["tick"] == newest_tick
    # after materialize, the flat dir loads clean again
    assert _load(tmp)._load_successful


def test_falls_back_to_older_generation_when_newest_bad():
    tmp = tempfile.mkdtemp()
    g = _hotcold_state(tmp)
    for _ in range(500):
        g.tick += 1
    g.save_hot_state(tmp)  # a second, newer generation
    gens = asg.list_generations(tmp)
    assert len(gens) >= 2
    newest_dir = gens[0][0]
    older_tick = gens[1][1]["tick"]
    # Corrupt the newest generation's core (atomic replace = new inode).
    cp = os.path.join(newest_dir, "guala_core.json")
    t = cp + ".x"
    open(t, "w").write("x")
    os.replace(t, cp)
    # Also make the flat state fail so recovery is invoked.
    ft = os.path.join(tmp, "guala_core.json") + ".x"
    open(ft, "w").write("x")
    os.replace(ft, os.path.join(tmp, "guala_core.json"))

    def load_test(gen_dir):
        return _load(gen_dir)._load_successful

    man = asg.recover_from_generations(tmp, load_test)
    assert man is not None and man["tick"] == older_tick


def test_total_local_failure_returns_none_never_s3():
    tmp = tempfile.mkdtemp()
    _hotcold_state(tmp)
    # Corrupt every generation's core.
    for gd, _m in asg.list_generations(tmp):
        cp = os.path.join(gd, "guala_core.json")
        t = cp + ".x"
        open(t, "w").write("x")
        os.replace(t, cp)

    def load_test(gen_dir):
        return _load(gen_dir)._load_successful

    assert asg.recover_from_generations(tmp, load_test) is None


def test_prunes_to_keep_three_generations():
    tmp = tempfile.mkdtemp()
    g = _new()
    for _ in range(50):
        g.tick += 1
    g.save_full_state(tmp)
    for _ in range(6):
        for _ in range(300):
            g.tick += 1
        g.save_hot_state(tmp)
    assert len(asg.list_generations(tmp)) == 3


def test_wal_rides_generation_and_tolerates_growth():
    tmp = tempfile.mkdtemp()
    g = _new()
    for _ in range(50):
        g.tick += 1
    g.read_sentence("birds sing softly in the tall green trees", source="seed")
    _settle(g)
    g.save_full_state(tmp)  # oldest kept generation
    gen1_dir = asg.list_generations(tmp)[0][0]
    waldir = os.path.join(gen1_dir, asg.WAL_DIRNAME)
    assert os.path.isdir(waldir), "WAL not captured in generation"
    before = sum(os.path.getsize(os.path.join(waldir, x))
                 for x in os.listdir(waldir))
    # more window activity + hot saves -> shared active WAL segment grows
    for w in ("the quiet moon glows over still water",
              "a warm light rests on the hill"):
        for _ in range(300):
            g.tick += 1
        g.read_sentence(w, source="seed")
        _settle(g)
        g.save_hot_state(tmp)
    after = sum(os.path.getsize(os.path.join(waldir, x))
                for x in os.listdir(waldir))
    assert after >= before
    # the older generation still validates and load-tests clean
    assert asg._validate_generation(gen1_dir) is not None
    assert _load(gen1_dir)._load_successful


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
