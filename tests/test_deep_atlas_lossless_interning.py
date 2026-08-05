import copy
import json
import struct

import pytest

from dsf_ai_service.substrate.deep_atlas import DeepAtlas
from tools.migrate_deep_atlas_v2 import migrate


def _entry(section, motif, co_occurrence):
    return {
        "section": section,
        "motif": motif,
        "chi": 7,
        "strength": 0.8,
        "last_tick": 20,
        "born_tick": 10,
        "encoded_strength_at_write": 0.7,
        "dwell_at_write": 5,
        "source_path": "episodic",
        "promoted_at_tick": 10,
        "clarity": 0.6,
        "initial_clarity": 0.5,
        "arousal": 0.4,
        "valence": 0.1,
        "surprise": 0.2,
        "source": "corpus",
        "polarity": 1.0,
        "sensory_refs": ["w:tree"],
        "episode_refs": ["episode:1"],
        "co_occurrence": copy.deepcopy(co_occurrence),
    }


def _plain(mapping):
    return {
        section: dict(motifs.items())
        for section, motifs in mapping.items()
    }


def test_v3_columnar_roundtrip_is_lossless_interned_and_copy_on_write():
    shared = {
        "subject": {"1": 0.25, "2": 0.5},
        "modal_sound": {"4": 0.75},
    }
    atlas = DeepAtlas()
    atlas.tick = 20
    atlas.entries[7] = [
        _entry("subject", 1, shared),
        _entry("verb", 2, shared),
    ]

    snapshot = atlas.persistence_snapshot()
    assert snapshot["schema"] == "deep_atlas_v2"
    assert len(snapshot["co_occurrence_tables"]) == 2
    first_refs = snapshot["entries"]["7"][0]["co_occurrence_refs"]
    second_refs = snapshot["entries"]["7"][1]["co_occurrence_refs"]
    assert first_refs == second_refs
    assert "co_occurrence" not in snapshot["entries"]["7"][0]

    persisted = atlas.encode_persistence_snapshot(snapshot)
    assert persisted["schema"] == "deep_atlas_v3"
    assert persisted["columnar_bytes"] > 0
    assert persisted["columnar_payload_chunks"]
    atlas.validate_columnar_payload(persisted)

    restored = DeepAtlas()
    assert restored.load_from_json(copy.deepcopy(persisted)) == 2
    first, second = restored.entries[7]
    assert _plain(first["co_occurrence"]) == shared
    assert _plain(second["co_occurrence"]) == shared

    first_section = first["co_occurrence"].setdefault("subject", {})
    first_section["1"] = 0.9

    assert first["co_occurrence"]["subject"]["1"] == 0.9
    assert second["co_occurrence"]["subject"]["1"] == 0.25


def test_prune_releases_only_unreachable_interned_association_tables():
    shared = {"subject": {"1": 0.25, "2": 0.5}}
    atlas = DeepAtlas()
    atlas.entries[7] = [
        _entry("subject", 1, shared),
        _entry("verb", 2, shared),
    ]
    atlas.persistence_snapshot()

    assert len(atlas._co_occurrence_registry) == 1

    first, second = atlas.entries[7]
    first["co_occurrence"]["subject"]["1"] = 0.9
    second["strength"] = 0.0
    atlas.prune()

    assert atlas.live_count() == 1
    assert len(atlas._co_occurrence_registry) == 0
    assert first["co_occurrence"]["subject"]["1"] == 0.9

    atlas.persistence_snapshot()
    assert len(atlas._co_occurrence_registry) == 1
    first["strength"] = 0.0
    atlas.prune()

    assert atlas.live_count() == 0
    assert len(atlas._co_occurrence_registry) == 0


def test_v3_preserves_unsigned_64_bit_motifs_and_binary64_weights():
    motif = 2**64 - 57
    weight = 0.12345678901234568
    atlas = DeepAtlas()
    atlas.tick = 20
    atlas.entries[7] = [
        _entry("subject", 1, {"subject": {str(motif): weight}}),
    ]

    restored = DeepAtlas()
    persisted = atlas.to_json()
    assert restored.load_from_json(persisted) == 1
    actual = restored.entries[7][0]["co_occurrence"]["subject"][str(motif)]

    assert struct.pack(">d", actual) == struct.pack(">d", weight)


def test_v3_payload_corruption_fails_before_live_atlas_mutation():
    atlas = DeepAtlas()
    atlas.tick = 20
    atlas.entries[7] = [
        _entry("subject", 1, {"subject": {"1": 0.25}}),
    ]
    persisted = atlas.to_json()
    corrupted = copy.deepcopy(persisted)
    first = corrupted["columnar_payload_chunks"][0]
    corrupted["columnar_payload_chunks"][0] = (
        ("A" if first[0] != "A" else "B") + first[1:]
    )
    target = DeepAtlas()
    target.entries[99] = [
        _entry("object", 2, {"object": {"2": 0.5}}),
    ]

    with pytest.raises(ValueError, match="digest does not match"):
        target.load_from_json(corrupted)

    assert 99 in target.entries
    assert 7 not in target.entries


def test_v2_reference_failure_cannot_partially_replace_live_atlas():
    shared = {"subject": {"1": 0.25, "2": 0.5}}
    source = DeepAtlas()
    source.tick = 20
    source.entries[7] = [
        _entry("subject", 1, shared),
        _entry("verb", 2, shared),
    ]
    damaged = source.persistence_snapshot()
    damaged["entries"]["7"][1]["co_occurrence_refs"]["subject"] = "f" * 64

    target = DeepAtlas()
    target.tick = 99
    target.promotions_survival = 4
    target.promotions_episodic = 5
    target.reinstatements = 6
    target.entries[99] = [
        _entry("object", 3, {"object": {"3": 0.75}}),
    ]
    before = target.persistence_snapshot()

    with pytest.raises(ValueError, match="reference is missing"):
        target.load_from_json(damaged)

    assert target.persistence_snapshot() == before
    assert target.tick == 99
    assert target.promotions_survival == 4
    assert target.promotions_episodic == 5
    assert target.reinstatements == 6


def test_v1_load_and_v3_resave_preserve_every_association():
    legacy_entry = _entry(
        "object", 3,
        {"object": {"3": 0.4}, "modal_sight": {"9": 0.6}},
    )
    legacy = {
        "schema": "deep_atlas_v1",
        "tick": 30,
        "saved_n_entries": 1,
        "entries": {"7": [copy.deepcopy(legacy_entry)]},
        "promotions_survival": 2,
        "promotions_episodic": 3,
        "reinstatements": 4,
    }

    atlas = DeepAtlas()
    assert atlas.load_from_json(legacy) == 1
    assert _plain(atlas.entries[7][0]["co_occurrence"]) == (
        legacy_entry["co_occurrence"])

    persisted = atlas.to_json()
    assert persisted["schema"] == "deep_atlas_v3"
    restored = DeepAtlas()
    assert restored.load_from_json(copy.deepcopy(persisted)) == 1
    assert _plain(restored.entries[7][0]["co_occurrence"]) == (
        legacy_entry["co_occurrence"])
    assert restored.promotions_survival == 2
    assert restored.promotions_episodic == 3
    assert restored.reinstatements == 4


def test_streaming_v1_to_v2_migration_remains_a_valid_v3_input(tmp_path):
    shared = {"subject": {"1": 0.25, "2": 0.5}}
    first = _entry("subject", 1, shared)
    second = _entry("verb", 2, shared)
    source_payload = {
        "schema_version": "v7.4.0",
        "guala_identity": "identity-1",
        "saved_at_tick": 20,
        "saved_at_timestamp": "2026-07-20T00:00:00Z",
        "data": {
            "schema": "deep_atlas_v1",
            "tick": 20,
            "saved_n_entries": 2,
            "entries": {"7": [first, second]},
            "promotions_survival": 3,
            "promotions_episodic": 4,
            "reinstatements": 5,
        },
    }
    source = tmp_path / "v1.json"
    destination = tmp_path / "v2.json"
    source.write_text(json.dumps(source_payload))

    proof = migrate(source, destination)
    migrated = json.loads(destination.read_text())

    assert proof["entries"] == 2
    assert proof["unique_tables"] == 1
    assert migrated["guala_identity"] == "identity-1"
    assert migrated["saved_at_tick"] == 20
    assert migrated["data"]["schema"] == "deep_atlas_v2"
    atlas = DeepAtlas()
    assert atlas.load_from_json(migrated["data"]) == 2
    persisted = atlas.to_json()
    assert persisted["schema"] == "deep_atlas_v3"
    restored = DeepAtlas()
    assert restored.load_from_json(persisted) == 2
    assert _plain(restored.entries[7][0]["co_occurrence"]) == shared
    assert _plain(restored.entries[7][1]["co_occurrence"]) == shared
