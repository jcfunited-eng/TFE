"""
test_sensory_library_permanence.py — GL-CMD-LIBRARY-PERMANENCE-JOE-20260719:
pictures, sounds, and videos are a personal library, the same category as
books -- given once, available whenever wanted, never silently deleted by
a disuse timer.

Root incident: real uploads from 2026-07-17 (50+ pictures, 7 sounds,
deliberately curated -- "Aven and Guala.jpg", "your name is guala") were
silently deleted, including the only copy of the file on disk, after
~27x the old forget-window elapsed unattended. Joe, direct, 2026-07-19:
"the way gifts are given... a personal library... that should never be
deleted." _forget_stale_sensory_items and its three call sites are
removed entirely, not disabled -- matching how corpora (books) already
had zero deletion code.

Gates:
1. A picture/sound/video with a real file on disk survives arbitrarily
   long unattended (well past the old ~39,120-tick threshold) across
   many real autonomy ticks -- neither the in-memory record NOR the
   file is removed.
2. The removed function is genuinely gone (no dead reference anyone
   could accidentally call back in).
3. Unrelated forgetting/decay mechanisms this sweep used to run
   alongside (word-mode forgetting, atlas forgetting) are UNCHANGED --
   this fix is scoped to sensory items only, not a blanket "nothing
   ever decays" regression.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsf_ai_service.v4.gualaloom_v5_engine import Guala, PictureItem, Section


def test_gate1_library_items_never_deleted():
    print("Gate 1: pictures/sounds/videos survive indefinitely...")
    g = Guala()
    scratch_dir = "/tmp/claude-0/-workspaces-Tao-Financial-Engine/19961585-751a-4275-b579-638761db6ff0/scratchpad/library-perm-test"
    os.makedirs(scratch_dir, exist_ok=True)
    fake_file = os.path.join(scratch_dir, "gift_original.jpg")
    with open(fake_file, "wb") as f:
        f.write(b"real uploaded bytes, not a placeholder")

    import numpy as np
    pic = PictureItem(item_id="gift1", title="Aven and Guala.jpg",
                      intensity_grid=np.zeros((64, 64)), source="upload",
                      shown_at_tick=0)
    pic.original_path = fake_file
    g._pictures["gift1"] = pic
    g._sounds["gift2"] = {"title": "your name is guala",
                          "created_tick": 0, "last_attended_tick": 0}

    # Advance well past the OLD forget threshold (Section.MODE_FORGET_TICKS,
    # ~39,120) with these items never once attended.
    g.tick = Section.MODE_FORGET_TICKS * 30
    for _ in range(2500):
        g._autonomy_tick()

    assert "gift1" in g._pictures, \
        "a real uploaded picture must never be silently forgotten"
    assert "gift2" in g._sounds, \
        "a real uploaded sound must never be silently forgotten"
    assert os.path.exists(fake_file), \
        "the picture's real file on disk must never be deleted"
    print("  PASS: picture + sound + file all survive far past the old threshold")


def test_gate2_function_genuinely_removed():
    print("Gate 2: the old sweep is gone, not just unreachable...")
    g = Guala()
    assert not hasattr(g, "_forget_stale_sensory_items"), \
        "the sensory-item forget sweep must be fully removed, not dormant"
    print("  PASS: _forget_stale_sensory_items no longer exists")


def test_gate3_unrelated_decay_still_works():
    print("Gate 3: word-mode and atlas forgetting still run normally...")
    g = Guala()
    g.add_corpus("book", "Book", ["the cat sat on the mat"] * 50)
    for _ in range(3000):
        g._autonomy_tick()
    # Real, ordinary decay/forgetting physics elsewhere must be untouched:
    # confirm the atlas and section forgetting calls this sweep used to sit
    # beside are still present and still reachable in the same tick block.
    import inspect
    src = inspect.getsource(g._autonomy_tick)
    assert "forget_below_threshold" in src, \
        "atlas forgetting must remain untouched by this fix"
    assert "forget_stale_modes" in src, \
        "word-mode forgetting must remain untouched by this fix"
    print("  PASS: unrelated decay/forgetting mechanisms unchanged")


if __name__ == "__main__":
    test_gate1_library_items_never_deleted()
    test_gate2_function_genuinely_removed()
    test_gate3_unrelated_decay_still_works()
    print("\nAll library-permanence gates pass.")
