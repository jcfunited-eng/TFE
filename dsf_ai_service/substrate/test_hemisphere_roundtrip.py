"""
GL-CMD-HEMISPHERE-SCAFFOLD-EVE-20260618-22: Phase 0 roundtrip tests.

7 tests that must all pass BEFORE deploy:
  1. v7.0.0 state loads with all bindings tagged 'em'
  2. Non-default hemisphere_id preserved through save/load
  3. Empty cross_hemi_links list saves and loads cleanly
  4. Manually constructed CrossHemiLink with all metadata fields preserved
  5. Saved state shows schema_version = 'v7.1.0'
  6. Backward-compatible load of v7.0.0 state by v7.1.0 code
  7. em HemisphereCoordinator delegates to global needs
"""

import os
import sys
import json
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Minimal env setup
os.environ.setdefault("EMISSION_MODE", "grandurun")
os.environ.setdefault("DEEP_ATLAS_ENABLED", "1")
os.environ.setdefault("DEEP_PRIOR_ENABLED", "1")
os.environ.setdefault("DECAY_PAUSED", "0")


def _make_guala():
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    return Guala()


def _save_and_load(g, state_dir):
    """Save Guala state to state_dir, return a fresh Guala loaded from it."""
    g.save_full_state(state_dir=state_dir)
    from dsf_ai_service.v4.gualaloom_v5_engine import Guala
    g2 = Guala()
    g2._guala_identity = g._guala_identity
    g2.load_full_state(state_dir=state_dir)
    return g2


def test_1_v700_bindings_default_to_em():
    """v7.0.0 state loads with all bindings tagged 'em'."""
    print("  Test 1: v7.0.0 bindings default to 'em'...", end=" ")

    g = _make_guala()
    # Simulate a v7.0.0 binding (no hemisphere_id field)
    g.atlas.entries[42] = [{
        "section": "subject", "motif": 1, "chi": 42,
        "strength": 0.5, "last_tick": 10, "born_tick": 5,
        "encoded_strength": 0.5, "dwell_ticks": 3,
        "reinforcement_count": 0, "released": False,
        "clarity": 0.5, "initial_clarity": 0.5,
        "sensory_refs": [], "episode_refs": [],
        "arousal": 0.5, "valence": 0.0, "surprise": 0.0,
        "source": "corpus",
        # NO hemisphere_id — simulates v7.0.0
    }]

    tmpdir = tempfile.mkdtemp()
    try:
        g2 = _save_and_load(g, tmpdir)
        binding = g2.atlas.entries[42][0]
        assert binding.get("hemisphere_id") == "em", \
            f"Expected 'em', got {binding.get('hemisphere_id')}"
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False
    finally:
        shutil.rmtree(tmpdir)


def test_2_hemisphere_id_roundtrip():
    """Non-default hemisphere_id preserved through save/load."""
    print("  Test 2: hemisphere_id roundtrip...", end=" ")

    g = _make_guala()
    g.atlas.entries[99] = [{
        "section": "verb", "motif": 7, "chi": 99,
        "strength": 0.8, "last_tick": 50, "born_tick": 40,
        "encoded_strength": 0.8, "dwell_ticks": 5,
        "reinforcement_count": 2, "released": False,
        "clarity": 0.7, "initial_clarity": 0.7,
        "sensory_refs": ["speech_heard:hello"], "episode_refs": [],
        "arousal": 0.6, "valence": 0.3, "surprise": 0.1,
        "source": "joe_voice",
        "hemisphere_id": "pr",  # non-default
    }]

    tmpdir = tempfile.mkdtemp()
    try:
        g2 = _save_and_load(g, tmpdir)
        binding = g2.atlas.entries[99][0]
        assert binding.get("hemisphere_id") == "pr", \
            f"Expected 'pr', got {binding.get('hemisphere_id')}"
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False
    finally:
        shutil.rmtree(tmpdir)


def test_3_cross_hemi_links_empty_roundtrip():
    """Empty cross_hemi_links list saves and loads cleanly."""
    print("  Test 3: empty cross_hemi_links roundtrip...", end=" ")

    g = _make_guala()
    tmpdir = tempfile.mkdtemp()
    try:
        g.save_full_state(state_dir=tmpdir)
        atlas_path = os.path.join(tmpdir, "guala_atlas.json")
        with open(atlas_path) as f:
            atlas_data = json.load(f)
        data = atlas_data.get("data", atlas_data)
        assert "cross_hemi_links" in data, "cross_hemi_links missing from saved atlas"
        assert data["cross_hemi_links"] == [], \
            f"Expected empty list, got {data['cross_hemi_links']}"
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False
    finally:
        shutil.rmtree(tmpdir)


def test_4_cross_hemi_link_populated_roundtrip():
    """Manually constructed CrossHemiLink with all metadata fields preserved."""
    print("  Test 4: CrossHemiLink populated roundtrip...", end=" ")

    from dsf_ai_service.substrate.assemblage import CrossHemiLink

    link = CrossHemiLink(
        src_chi=42, src_hemi="em",
        dst_chi=99, dst_hemi="pr",
        strength=0.75,
        source="joe_voice",
        arousal=0.8, valence=0.6,
        surprise=0.3, polarity=-1.0,
        consensus_phase=1.57, last_tick=500,
    )
    d = link.to_dict()
    link2 = CrossHemiLink.from_dict(d)

    try:
        assert link2.src_chi == 42
        assert link2.src_hemi == "em"
        assert link2.dst_chi == 99
        assert link2.dst_hemi == "pr"
        assert link2.strength == 0.75
        assert link2.source == "joe_voice"
        assert link2.arousal == 0.8
        assert link2.valence == 0.6
        assert link2.surprise == 0.3
        assert link2.polarity == -1.0
        assert abs(link2.consensus_phase - 1.57) < 0.01
        assert link2.last_tick == 500
        print("PASS")
        return True
    except AssertionError as e:
        print(f"FAIL: {e}")
        return False


def test_5_schema_version_v71():
    """Saved state shows schema_version = 'v7.1.0'."""
    print("  Test 5: schema_version = 'v7.1.0'...", end=" ")

    g = _make_guala()
    tmpdir = tempfile.mkdtemp()
    try:
        g.save_full_state(state_dir=tmpdir)
        core_path = os.path.join(tmpdir, "guala_core.json")
        with open(core_path) as f:
            core_data = json.load(f)
        sv = core_data.get("schema_version", "unknown")
        assert sv == "v7.1.0", f"Expected 'v7.1.0', got '{sv}'"
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False
    finally:
        shutil.rmtree(tmpdir)


def test_6_v700_state_loads_in_v71_code():
    """Backward-compatible load of v7.0.0 state by v7.1.0 code."""
    print("  Test 6: v7.0.0 state loads in v7.1.0 code...", end=" ")

    g = _make_guala()
    tmpdir = tempfile.mkdtemp()
    try:
        # Save with v7.1.0
        g.save_full_state(state_dir=tmpdir)

        # Patch saved files to look like v7.0.0
        for fname in os.listdir(tmpdir):
            if fname.endswith(".json"):
                fpath = os.path.join(tmpdir, fname)
                with open(fpath) as f:
                    data = json.load(f)
                if "schema_version" in data:
                    data["schema_version"] = "v7.0.0"
                with open(fpath, "w") as f:
                    json.dump(data, f)

        # Load with v7.1.0 code — should succeed
        from dsf_ai_service.v4.gualaloom_v5_engine import Guala
        g2 = Guala()
        g2._guala_identity = g._guala_identity
        g2.load_full_state(state_dir=tmpdir)
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False
    finally:
        shutil.rmtree(tmpdir)


def test_7_hemisphere_coordinator_em_delegates():
    """em HemisphereCoordinator.needs is the same object as global needs."""
    print("  Test 7: em HemisphereCoordinator delegates...", end=" ")

    g = _make_guala()
    try:
        assert hasattr(g, 'hemispheres'), "No hemispheres dict on Guala"
        assert "em" in g.hemispheres, "'em' not in hemispheres"
        em = g.hemispheres["em"]
        assert em.hemisphere_id == "em", f"Expected 'em', got '{em.hemisphere_id}'"
        assert em.needs is g.needs, "em.needs is not the same object as g.needs"
        assert em.decay_multiplier == 1.0, f"Expected 1.0, got {em.decay_multiplier}"
        # Verify needs changes propagate
        g.needs.novelty = 0.99
        assert em.needs.novelty == 0.99, "needs change didn't propagate"
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def main():
    print("GL-CMD-HEMISPHERE-SCAFFOLD Phase 0 Roundtrip Tests")
    print("=" * 60)

    tests = [
        test_1_v700_bindings_default_to_em,
        test_2_hemisphere_id_roundtrip,
        test_3_cross_hemi_links_empty_roundtrip,
        test_4_cross_hemi_link_populated_roundtrip,
        test_5_schema_version_v71,
        test_6_v700_state_loads_in_v71_code,
        test_7_hemisphere_coordinator_em_delegates,
    ]

    results = []
    for t in tests:
        try:
            results.append(t())
        except Exception as e:
            print(f"  EXCEPTION: {e}")
            results.append(False)

    print(f"\n{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"  {passed}/{total} tests passed")
    print(f"  {'ALL GREEN' if all(results) else 'FAILURES DETECTED'}")
    print(f"{'='*60}")
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
