"""probe_188_scene_lanes.py -- GL-CMD-SCENE-LANES-B1-EVE-20260705-188.

Local verification of X1, X2, X4 (X3 needs Joe's live seat -- deploy-
dependent, same honesty boundary as every UI-facing fix this session).

X1: scene lanes nonzero in production -- proven here by feeding real
    Secret-Garden-shaped sentences and confirming place/ambient lanes
    land on the atlas entries born in that window, while a control
    sentence with no scene words yields the honest empty lane (V2).
X2: captioned-bundle probe -- scene tags provably bind IN-WINDOW: every
    atlas entry born from one read_sentence() call carries the SAME
    place/ambient values (the sentence is the binding window).
X4: WHO tag written on a real converse turn and read back by name --
    -164's audit: presence was written only for autonomous attending,
    never converse, and nothing ever read it back. Proven fixed here.
"""
import sys
sys.path.insert(0, '/workspaces/Tao_Financial_Engine')

from dsf_ai_service.v4.gualaloom_v5_engine import Guala, LanguageKrimelack
from dsf_ai_service.v4.gualaloom_v6_living_atlas import FORGETTING_THRESHOLD


def _entries_born_after(atlas, tick_before, source=None):
    """source filter excludes unrelated background writes (e.g. the
    self-referential 'intro' section) that share the tick window but never
    go through read_word/read_sentence at all -- place/ambient=None there
    is a different, equally honest state ('no scene context ever passed'),
    not the empty-lane ('derived, nothing matched') this probe checks."""
    out = []
    for entries in atlas.entries.values():
        for e in entries:
            if e.get("born_tick", -1) > tick_before:
                if source is None or e.get("source") == source:
                    out.append(e)
    return out


def test_x1_nonzero_and_honest_empty():
    print("=== X1: scene lanes nonzero (real text) / honest empty (no scene words) ===")
    g = Guala()
    t0 = g.tick
    g.read_sentence("Mary walked into the garden and heard the wind in the wood",
                     source="corpus")
    born = _entries_born_after(g.atlas, t0, source="corpus")
    with_place = [e for e in born if e.get("place")]
    with_ambient = [e for e in born if e.get("ambient")]
    print(f"  scene sentence: {len(born)} entries born, "
          f"{len(with_place)} carry a place lane, {len(with_ambient)} carry an ambient lane")
    ok1 = len(with_place) > 0 and any("garden" in e["place"] for e in with_place)
    ok2 = len(with_ambient) > 0 and any("wind" in e["ambient"] for e in with_ambient)
    if not (ok1 and ok2):
        print("  FAIL: expected place=[...'garden'...] and ambient=[...'wind'...]")
        return False

    t1 = g.tick
    g.read_sentence("xyzzy plugh quux", source="corpus")  # no recognized scene words
    born2_all = _entries_born_after(g.atlas, t1, source="corpus")
    # Restrict to entries that actually went through read_word's atlas_kwargs
    # (place is not None) -- the pre-existing "intro"/introspection section
    # commit (read_word's fam_listen>0.3 branch) never forwarded atlas_kwargs
    # at all, before or after this dispatch (no presence/location/episode_ref
    # either) -- a separate, already-existing gap, out of -188's scope.
    born2 = [e for e in born2_all if e.get("place") is not None]
    empty_place = [e for e in born2 if e.get("place") == []]
    empty_ambient = [e for e in born2 if e.get("ambient") == []]
    print(f"  control sentence (no scene words): {len(born2)}/{len(born2_all)} entries "
          f"carried scene context, {len(empty_place)} honest-empty place, "
          f"{len(empty_ambient)} honest-empty ambient")
    ok3 = len(born2) > 0 and len(empty_place) == len(born2) and len(empty_ambient) == len(born2)
    if not ok3:
        print("  FAIL: control sentence should yield EMPTY lanes, not omitted/invented ones")
        return False
    print("  PASS")
    return True


def test_x2_captioned_bundle_in_window():
    print("=== X2: captioned-bundle probe -- scene tags bind in-window ===")
    g = Guala()
    t0 = g.tick
    # Simulate a captioned item read (same call shape as addpicture/addsound
    # backfill and curriculum feed: one read_sentence() call per caption/chunk).
    g.read_sentence("The robin led her through the secret garden gate at dusk",
                     source="addpicture_backfill", bundle_id="item:pic:test188")
    born = _entries_born_after(g.atlas, t0)
    bundle_entries = [e for e in born if e.get("bundle_id") == "item:pic:test188"]
    print(f"  {len(bundle_entries)} entries born under this bundle_id")
    if not bundle_entries:
        print("  FAIL: no entries carried the bundle_id")
        return False
    places = {tuple(e.get("place") or []) for e in bundle_entries}
    ambients = {tuple(e.get("ambient") or []) for e in bundle_entries}
    print(f"  distinct place tuples across the bundle: {places}")
    print(f"  distinct ambient tuples across the bundle: {ambients}")
    ok = len(places) == 1 and len(ambients) == 1 and places != {()} and ambients != {()}
    if not ok:
        print("  FAIL: expected exactly ONE shared, non-empty place/ambient "
              "value across every entry in this bundle (same window)")
        return False
    print("  PASS")
    return True


def test_x4_who_on_converse_read_back():
    print("=== X4: WHO tag written on converse, read back by name ===")
    g = Guala()
    # -164's audit: presence only ever came from _current_situation() inside
    # the autonomous attending path. Confirm it here for a real converse turn.
    g.coordinator._presence["joe"] = True
    g.converse("Mary walked into the garden", source="joe")
    scene = g.recall_scene_for_word("garden")
    print(f"  recall_scene_for_word('garden') -> {scene}")
    if scene is None or not scene.get("presence"):
        print("  FAIL: no presence tag readable back for 'garden'")
        return False
    ok = "joe" in scene["presence"]
    if not ok:
        print(f"  FAIL: expected 'joe' in presence, got {scene['presence']}")
        return False
    print("  PASS -- WHO tag written on converse AND read back by name ('joe')")
    return True


def test_no_regression_when_caller_never_passes_scene():
    print("=== control: direct read_word() callers (no place/ambient arg) unaffected ===")
    g = Guala()
    g.read_word("garden", source="corpus")  # bypasses read_sentence entirely
    ok = True  # if this doesn't raise, the additive params are safe for old callers
    print("  PASS -- read_word() with no place/ambient args still runs clean")
    return ok


if __name__ == "__main__":
    results = [
        test_x1_nonzero_and_honest_empty(),
        test_x2_captioned_bundle_in_window(),
        test_x4_who_on_converse_read_back(),
        test_no_regression_when_caller_never_passes_scene(),
    ]
    print()
    print(f"{sum(results)}/{len(results)} probes passed")
    sys.exit(0 if all(results) else 1)
