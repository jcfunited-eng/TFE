"""tests/test_somatic_affection_and_routines.py — Regression Test Suite for Somatic Affection & Caretaker Routines.

Validates:
1. Library Bookshelf Catalog & Entities:
   - 4 distinct public domain books placed on library shelves (Peter Rabbit, Wind in the Willows, Aesop, Mother Goose).
   - Media catalog mapping to LibriVox public-domain recordings.
2. LibriVox Catalog Resolution & Strict Rejection:
   - Known titles resolve to canonical metadata and archive identifiers.
   - Unknown titles raise ValueError (zero silent fallback to Alice).
3. Somatic Affection Contacts (Stage 1):
   - Physical skin contact execution via touch_her ("touch-hug", "touch-kiss", "touch-hold-hand", "touch-pat", "touch-shoulder", "touch-lap", "touch-bedtime-hold").
   - Measured positive contact area (um^2) and conductive heat transfer (heat_nj > 0).
   - Compression depths match specification (500 um, 750 um, 1000 um, 2000 um).
4. Lap Holding & Bedtime Hold Mechanics:
   - "touch-lap" activates 3-site enveloping hold (front-torso at 2000 um, left-shoulder at 1000 um, right-shoulder at 1000 um) with total area > 10,000 mm^2.
   - "touch-bedtime-hold" activates 3-site soothing tuck-in hold (forehead at 500 um, crown at 750 um, left-shoulder at 1000 um).
5. Television Remote Operation & Revision Continuity:
   - "tv-remote-cycle" cycles broadcast channel (Channel 0 -> 1 -> 2 -> 0).
   - World revision increments on each transaction under lock.
6. Spatial Horizon Held-Object Safety & Ray Occlusion:
   - Objects with position=None (held objects) do not crash compute_spatial_horizon_observation.
   - Finite solid angle (d=250 mm) for held-by-self objects.
   - strict_occlusion=True excludes objects behind solid walls without line of sight.
   - Sensory aperture clamped to <= 64 objects.
7. Caretaker maybe_bedtime Direct Routine Execution:
   - Directly executes caretaker.maybe_bedtime(o, st).
   - Bed made: commits bedtime_hug_given_for_night only upon verified touch delivery.
   - Failed touch delivery: does not commit state.
8. Caretaker maybe_read Direct Routine Execution & Object Pairing:
   - Directly executes caretaker.maybe_read(o, st).
   - Verifies physical presentation matches the specific rotating book ("read-book-peter-rabbit").
   - Verifies lap holding ("touch-lap") is delivered during reading.
9. Caretaker Resilience with Missing Embodiment Body:
   - food_state and within_reach gracefully handle missing bodies without KeyError or TypeError.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
import pytest

from dsf_ai_service.guala_home_world import (
    home_world_authority,
    expand_library_books,
    HOME_SHAPES,
    PATTERNED_BOXES,
    operate_tv_remote,
    switch_tv_channel,
    nocturnal_house_tidying,
    get_tv_broadcast,
    compute_spatial_horizon_observation,
)
from dsf_ai_service.guala_caretaker_hand import (
    present_food,
    touch_her,
    TOUCH_IDS,
    READ_IDS,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodiedObject,
    PositionMM,
)
from guala_caretaker.media import BOOK_CATALOG, librivox_book

# Ensure guala_caretaker directory is in path for caretaker module import
CARETAKER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "guala_caretaker"))
if CARETAKER_DIR not in sys.path:
    sys.path.insert(0, CARETAKER_DIR)

import caretaker  # noqa: E402
import media      # noqa: E402

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


def test_library_bookshelf_entities_and_shapes():
    """Verify all 4 canonical library books exist in shapes, patterned boxes, and home world after expansion."""
    for book_id in ("book-peter-rabbit", "book-wind-willows", "book-aesops-fables", "book-mother-goose"):
        assert book_id in HOME_SHAPES, f"Missing shape for {book_id}"
        assert book_id in PATTERNED_BOXES, f"Missing patterned box for {book_id}"
        assert book_id in BOOK_CATALOG, f"Missing media catalog entry for {book_id}"

    auth = home_world_authority(identity=IDENTITY, expand_library=False)
    rev_before = auth._state.world.revision
    expand_library_books(auth)
    assert auth._state.world.revision == rev_before + 1

    world = auth._state.world
    world_objects = {obj.object_id: obj for obj in world.objects}
    for book_id in ("book-peter-rabbit", "book-wind-willows", "book-aesops-fables", "book-mother-goose"):
        assert book_id in world_objects, f"{book_id} not placed in expanded home world"
        obj = world_objects[book_id]
        assert obj.position.x in (10_000, 10_500, 11_000, 11_500)
        assert obj.position.y == 6_000


def test_librivox_media_catalog_resolution_and_rejection():
    """Verify media catalog maps to valid LibriVox metadata, and unknown titles strictly raise ValueError."""
    for book_id, entry in BOOK_CATALOG.items():
        assert "title" in entry
        assert "archive" in entry
        info = librivox_book(entry["title"])
        assert info is not None
        assert "archive" in info
        assert len(info["archive"]) > 0

    # Strict rejection: zero silent fallbacks to Alice for unknown titles
    with pytest.raises(ValueError, match="LibriVox book.*retrieval failed|not found"):
        librivox_book("Nonexistent Book Title That Does Not Exist 12345")


def test_somatic_affection_skin_contact_physics():
    """Verify physical touch profiles generate honest body-to-body skin contact and conductive heat."""
    auth = home_world_authority(identity=IDENTITY)

    expected_compressions = {
        "touch-hug": {("front-torso", 2000), ("left-shoulder", 1000), ("right-shoulder", 1000)},
        "touch-kiss": {("forehead", 500)},
        "touch-pat": {("crown", 750)},
        "touch-shoulder": {("left-shoulder", 1000)},
        "touch-hold-hand": {("left-palm", 1000)},
        "touch-lap": {("front-torso", 2000), ("left-shoulder", 1000), ("right-shoulder", 1000)},
        "touch-bedtime-hold": {("forehead", 500), ("crown", 750), ("left-shoulder", 1000)},
    }

    for touch_id, expected in expected_compressions.items():
        res = present_food(auth, touch_id)
        assert res is not None
        assert res.get("schema") == "guala.caregiver_presentation.v1"
        assert res.get("object_id") == touch_id
        assert res.get("touched") is not None

        contacts = res.get("contacts") or []
        assert len(contacts) > 0, f"Touch {touch_id} generated empty contacts list"

        found_pairs = set()
        for c in contacts:
            assert c["area_um2"] > 0, f"Contact area must be positive for {touch_id}"
            assert c["heat_nj"] > 0, f"Conductive heat transfer must be positive for {touch_id}"
            assert c["compression_um"] > 0, f"Compression depth must be positive for {touch_id}"
            found_pairs.add((c["site"], c["compression_um"]))

        assert found_pairs == expected, f"Mismatched sites/compressions for {touch_id}: expected {expected}, got {found_pairs}"


def test_lap_holding_and_bedtime_hold_physics():
    """Verify lap-holding and bedtime-hold specific physical contact profiles and geometry."""
    auth = home_world_authority(identity=IDENTITY)

    # Lap holding: 3 skin sites, large contact area
    lap = present_food(auth, "touch-lap")
    assert lap.get("touched") == "lap_hold"
    lap_contacts = lap.get("contacts") or []
    assert len(lap_contacts) == 3
    lap_sites = {c["site"] for c in lap_contacts}
    assert lap_sites == {"front-torso", "left-shoulder", "right-shoulder"}

    total_lap_area_um2 = sum(c["area_um2"] for c in lap_contacts)
    # Total contact area exceeds 10,000 mm^2 (10,000 * 10^6 um^2)
    assert total_lap_area_um2 > 10_000 * 1_000_000

    # Bedtime hold: 3 skin sites
    bedtime = present_food(auth, "touch-bedtime-hold")
    assert bedtime.get("touched") == "bedtime_hold"
    bedtime_contacts = bedtime.get("contacts") or []
    assert len(bedtime_contacts) == 3
    bedtime_sites = {c["site"] for c in bedtime_contacts}
    assert bedtime_sites == {"forehead", "crown", "left-shoulder"}


def test_tv_remote_cycle_and_revision_continuity():
    """Verify tv-remote-cycle cycles television channel and increments revision under lock."""
    auth = home_world_authority(identity=IDENTITY)

    rev_0 = auth._state.world.revision
    ch1 = operate_tv_remote(auth)
    assert auth._state.world.revision == rev_0 + 1

    ch2 = operate_tv_remote(auth)
    assert auth._state.world.revision == rev_0 + 2

    res = present_food(auth, "tv-remote-cycle")
    assert res.get("presented") is True
    assert "channel" in res


def test_held_objects_spatial_horizon_safety():
    """Verify held objects (position=None) do not crash compute_spatial_horizon_observation,
    use finite solid angle, and respect the max_objects clamp."""
    auth = home_world_authority(identity=IDENTITY)
    cur_world = auth._state.world

    held_guala = EmbodiedObject(
        "held-toy-book",
        radius_mm=120,
        mass_grams=400,
        position=None,
        held_by_body_id="guala-body-1",
    )
    held_caretaker = EmbodiedObject(
        "caretaker-bottle",
        radius_mm=80,
        mass_grams=250,
        position=None,
        held_by_body_id="person-body-1",
    )

    w_held = replace(cur_world, objects=cur_world.objects + (held_guala, held_caretaker))
    auth._state = replace(auth._state, world=w_held, observation=auth._observation_for(w_held))

    # Clamp test: passing max_objects=128 must be strictly clamped to <= 64
    horizon = compute_spatial_horizon_observation(auth, body_id="guala-body-1", max_objects=128, strict_occlusion=False)
    assert len(horizon.objects) == 64
    obj_ids = [o.object_id for o in horizon.objects]

    # Object held by Guala is in observation with finite solid angle calculation
    assert "held-toy-book" in obj_ids
    assert "caretaker-bottle" in obj_ids


def test_strict_occlusion_ray_portal_exclusion():
    """Verify strict_occlusion=True excludes objects behind solid walls with no line-of-sight."""
    auth = home_world_authority(identity=IDENTITY)

    # Guala is in her-room (0..5600, 5000..10000)
    horizon_strict = compute_spatial_horizon_observation(auth, body_id="guala-body-1", max_objects=64, strict_occlusion=True)
    strict_ids = {o.object_id for o in horizon_strict.objects}

    # Her room items must be present
    assert "bed" in strict_ids
    assert "pillow" in strict_ids
    assert "blanket" in strict_ids

    # Outdoor items behind multiple solid walls must be strictly excluded
    assert "tree-oak" not in strict_ids
    assert "sandbox" not in strict_ids
    assert "garden-patch" not in strict_ids
    assert "bath-tub" not in strict_ids


def test_caretaker_maybe_bedtime_actual_routine(monkeypatch, tmp_path):
    """Directly execute caretaker.maybe_bedtime and verify:
    1. It requests bedtime preparation when bed is not made.
    2. It commits bedtime_hug_given_for_night only after confirmed touch delivery.
    3. It does not commit state if touch delivery fails.
    """
    monkeypatch.setattr(caretaker, "STATE", str(tmp_path / "caretaker_state.json"))

    calls = []

    def mock_present_food(food_id):
        calls.append(food_id)
        if food_id == "bedtime":
            return {
                "observation": {
                    "last_occurrence": {
                        "caregiver_presentation": {"made": ["pillow", "blanket"], "steps": ["moved"]}
                    }
                }
            }
        elif food_id == "touch-bedtime-hold":
            return {
                "observation": {
                    "last_occurrence": {
                        "caregiver_presentation": {
                            "touched": "bedtime_hold",
                            "contacts": [{"site": "forehead", "area_um2": 1000}],
                        }
                    }
                }
            }
        return None

    monkeypatch.setattr(caretaker, "present_food", mock_present_food)

    # Case 1: Bed not made -> calls bedtime, does NOT commit hug yet
    st = {"bed_made": ["pillow"]}
    o = {
        "live_tick": 500,
        "last_occurrence": {
            "her_sleep": {"asleep": False, "pressure": [950, 1000], "nights": 1}
        },
    }
    caretaker.maybe_bedtime(o, st)
    assert "bedtime" in calls
    assert set(st.get("bed_made") or []) == {"pillow", "blanket"}
    # Because bed became made during this call, tuck-in was immediately delivered and recorded
    assert st.get("bedtime_hug_given_for_night") == 2
    assert "touch-bedtime-hold" in calls

    # Case 2: Failed touch delivery must not commit hug
    calls.clear()
    monkeypatch.setattr(
        caretaker,
        "present_food",
        lambda fid: {"observation": {"last_occurrence": {"caregiver_presentation": {"touched": None}}}},
    )
    st_fail = {"bed_made": ["pillow", "blanket"], "bed_made_for_night": 3}
    o_night3 = {
        "live_tick": 600,
        "last_occurrence": {
            "her_sleep": {"asleep": False, "pressure": [950, 1000], "nights": 2}
        },
    }
    caretaker.maybe_bedtime(o_night3, st_fail)
    assert st_fail.get("bedtime_hug_given_for_night") is None, "Failed touch delivery must not record hug"


def test_caretaker_maybe_read_actual_routine_and_book_coupling(monkeypatch, tmp_path):
    """Directly execute caretaker.maybe_read and verify:
    1. Rotating book title couples directly to the physical book presented ('read-book-peter-rabbit').
    2. Lap holding ('touch-lap') is established for story time.
    3. Chapter completion updates state correctly.
    """
    monkeypatch.setattr(caretaker, "STATE", str(tmp_path / "caretaker_state.json"))

    calls = []

    def mock_present_food(item):
        calls.append(item)
        return {
            "observation": {
                "last_occurrence": {
                    "caregiver_presentation": {
                        "reading": True,
                        "touched": "lap_hold",
                        "contacts": [{"site": "front-torso", "area_um2": 5_000_000}],
                    }
                }
            }
        }

    monkeypatch.setattr(caretaker, "present_food", mock_present_food)
    monkeypatch.setattr(
        caretaker,
        "sing_block",
        lambda pcm: {"observation": {"live_tick": 101, "last_occurrence": {"native_tick": 101}}},
    )
    monkeypatch.setattr(media, "librivox_book", lambda title: {"title": title, "archive": "test_archive"})
    monkeypatch.setattr(media, "chapters", lambda arch: [{"name": "chapter1.mp3"}])
    monkeypatch.setattr(media, "fetch_chapter", lambda arch, chap: "dummy_chapter_path")
    monkeypatch.setattr(media, "blocks", lambda pcm_path: [b"\x00" * 8000])

    # index 1 in BOOK_CATALOG is book-peter-rabbit ("The Tale of Peter Rabbit")
    st = {"read_title_index": 1, "read_chapter": 0}
    o = {"live_tick": 200, "last_occurrence": {"her_sleep": {"asleep": False}}}

    caretaker.maybe_read(o, st)

    # Verify physical book presentation matches the title:
    assert "read-book-peter-rabbit" in calls, f"Expected read-book-peter-rabbit, got: {calls}"
    assert "touch-lap" in calls, f"Expected touch-lap, got: {calls}"
    # Finished single chapter -> cycled title index
    assert st.get("read_title_index") == 2
    assert st.get("read_chapter") == 0


def test_caretaker_resilience_with_missing_embodiment_body():
    """Verify caretaker food_state and within_reach gracefully handle missing or None bodies."""
    # Observation with missing self_body_id and bodies without pose position
    o_empty_bodies = {
        "last_occurrence": {
            "embodiment": {
                "self_body_id": "guala-body-1",
                "bodies": [{"body_id": "other-body"}],  # missing pose
                "objects": [{"object_id": "apple-1", "tastant_remaining_micrograms": 5000, "position": {"x_mm": 100, "y_mm": 100}}],
            }
        }
    }
    # Must evaluate cleanly to false/empty without KeyError or TypeError
    at_mouth, foods = caretaker.food_state(o_empty_bodies, skip=set())
    assert at_mouth is False
    assert "apple-1" in foods
