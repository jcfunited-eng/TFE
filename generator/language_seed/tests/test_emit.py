import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from generator.language_seed import emit as emit_mod
from generator.language_seed import config


def _good_entry(word, chi):
    return emit_mod.build_vocabulary_entry(
        word, chi, "rich", {"visual": chi}, (0.1, 0.5, 0.5, "nrc_vad"))


def test_validate_passes_clean_seed():
    entries = [_good_entry("dog", 10), _good_entry("cat", 20)]
    seed = emit_mod.assemble(entries, [], [])
    errors = emit_mod.validate(seed)
    assert errors == [], errors


def test_validate_catches_duplicate_chi():
    entries = [_good_entry("dog", 10), _good_entry("cat", 10)]
    seed = emit_mod.assemble(entries, [], [])
    errors = emit_mod.validate(seed)
    assert any("collision" in e for e in errors)


def test_validate_catches_out_of_range_chi():
    entries = [_good_entry("dog", config.CHI_MAX + 1)]
    seed = emit_mod.assemble(entries, [], [])
    errors = emit_mod.validate(seed)
    assert any("out of range" in e for e in errors)


def test_validate_catches_dangling_grounding_ref():
    entry = _good_entry("dog", 10)
    entry["grounding"]["visual"] = 999999999  # nonexistent chi
    seed = emit_mod.assemble([entry], [], [])
    errors = emit_mod.validate(seed)
    assert any("does not reference a seeded entry" in e or "out of range" in e for e in errors)


def test_validate_catches_dangling_semantic_net_edge():
    entries = [_good_entry("dog", 10)]
    net = {"center_chi": 10, "related_chis": [{"chi": 99999, "strength": 0.5}],
           "applies_to_hemispheres": ["sf"]}
    seed = emit_mod.assemble(entries, [], [net])
    errors = emit_mod.validate(seed)
    assert any("does not reference a seeded entry" in e for e in errors)


def test_validate_catches_bad_affect_range():
    entry = _good_entry("dog", 10)
    entry["affect"]["valence"] = 5.0
    seed = emit_mod.assemble([entry], [], [])
    errors = emit_mod.validate(seed)
    assert any("valence" in e for e in errors)


def test_validate_catches_coupling_weight_out_of_range():
    pattern = {"pattern_id": "p1", "chi_sequence": [10], "hemisphere": "sf",
               "coupling_weights": {"n1": 99.0}}
    entries = [_good_entry("dog", 10)]
    seed = emit_mod.assemble(entries, [pattern], [])
    errors = emit_mod.validate(seed)
    assert any("outside J range" in e for e in errors)


def test_validate_accepts_cross_file_reference_via_additional_valid_chis():
    entries = [_good_entry("puppy", 20)]
    net = {"center_chi": 20, "related_chis": [{"chi": 10, "strength": 0.5}],
           "applies_to_hemispheres": ["sf"]}
    seed = emit_mod.assemble(entries, [], [net])
    errors_without = emit_mod.validate(seed)
    assert any("does not reference a seeded entry" in e for e in errors_without)
    errors_with = emit_mod.validate(seed, additional_valid_chis={10})
    assert errors_with == []


def test_emit_raises_on_integrity_failure(tmp_path=None):
    import tempfile
    entries = [_good_entry("dog", 10), _good_entry("cat", 10)]
    seed = emit_mod.assemble(entries, [], [])
    path = os.path.join(tempfile.mkdtemp(), "bad.seed.json")
    try:
        emit_mod.emit(seed, path)
        assert False, "expected SeedIntegrityError"
    except emit_mod.SeedIntegrityError:
        pass
    assert not os.path.exists(path)


if __name__ == "__main__":
    test_validate_passes_clean_seed()
    test_validate_catches_duplicate_chi()
    test_validate_catches_out_of_range_chi()
    test_validate_catches_dangling_grounding_ref()
    test_validate_catches_dangling_semantic_net_edge()
    test_validate_catches_bad_affect_range()
    test_validate_catches_coupling_weight_out_of_range()
    test_validate_accepts_cross_file_reference_via_additional_valid_chis()
    test_emit_raises_on_integrity_failure()
    print("ALL PASS: test_emit")
