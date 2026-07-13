"""Regression proof that attention never reinstates DeepAtlas into LivingAtlas."""

import copy
import inspect

from dsf_ai_service.substrate.deep_atlas import DeepAtlas, FORGETTING_THRESHOLD
from dsf_ai_service.v4.gualaloom_v4_uf_kernel import DSF
from dsf_ai_service.v4.gualaloom_v5_engine import Section
from dsf_ai_service.v4.gualaloom_v6_living_atlas import LivingAtlas


CHI = 17
SECTION = "subject"


def _dsf(direction):
    return DSF(
        D_k=direction,
        M_k=0.1,
        R_rev=0.0,
        U_star=0.2,
        C_k=0.8,
        P_k=0.4,
        B_k=0.9,
        S_UF=0.72,
    )


def _build_deep_cohabitant():
    section = Section(name=SECTION)
    atlas = LivingAtlas()
    committed, resident_motif, _ = section.receive(
        _dsf(0.6),
        CHI,
        "resident",
        atlas,
        familiarity=0.0,
        salience=1.0,
        dwell_ticks=4,
        engine_tick=1,
        atlas_kwargs={
            "source": "resident_source",
            "episode_ref": "resident_episode",
        },
    )
    assert committed

    resident_entry = next(
        entry
        for entry in atlas.entries[CHI]
        if entry["section"] == SECTION and entry["motif"] == resident_motif
    )
    deep_atlas = DeepAtlas()
    assert deep_atlas.promote(
        resident_entry,
        "episodic",
        tick=2,
        working_atlas=atlas,
    )
    deep_entry = next(
        entry
        for entry in deep_atlas.entries[CHI]
        if entry["section"] == SECTION and entry["motif"] == resident_motif
    )
    assert deep_entry["strength"] >= FORGETTING_THRESHOLD
    return section, atlas, deep_atlas, resident_motif


def _entries_for(atlas, motif):
    return [
        entry
        for entries in atlas.entries.values()
        for entry in entries
        if entry["section"] == SECTION and entry["motif"] == motif
    ]


def test_same_chi_deep_memory_cannot_reappear_during_receive():
    parameters = inspect.signature(Section.receive).parameters
    assert "deep_atlas" not in parameters
    assert "index_callback" not in parameters

    section, atlas, deep_atlas, resident_motif = _build_deep_cohabitant()
    deep_before = copy.deepcopy(deep_atlas.entries[CHI])
    for entries in atlas.entries.values():
        entries[:] = [
            entry
            for entry in entries
            if not (
                entry["section"] == SECTION
                and entry["motif"] == resident_motif
            )
        ]
    assert not _entries_for(atlas, resident_motif)

    committed, incoming_motif, _ = section.receive(
        _dsf(-0.4),
        CHI,
        "incoming",
        atlas,
        familiarity=0.0,
        salience=1.0,
        dwell_ticks=1,
        engine_tick=3,
        atlas_kwargs={
            "source": "incoming_source",
            "episode_ref": "incoming_episode",
        },
    )

    assert committed
    assert incoming_motif != resident_motif
    assert not _entries_for(atlas, resident_motif)
    incoming_entries = _entries_for(atlas, incoming_motif)
    assert incoming_entries
    assert all(entry["source"] == "incoming_source" for entry in incoming_entries)
    assert all(
        entry["episode_ref"] == "incoming_episode" for entry in incoming_entries
    )
    assert deep_atlas.entries[CHI] == deep_before
    assert "reinstatements_since_boot" not in deep_atlas.snapshot()
    assert "reinstatements" not in deep_atlas.to_json()


def test_same_chi_deep_memory_cannot_reinforce_a_working_entry():
    section, atlas, deep_atlas, resident_motif = _build_deep_cohabitant()
    resident_entries = _entries_for(atlas, resident_motif)
    before = {
        id(entry): (
            entry["last_tick"],
            entry["reinforcement_count"],
            entry["source"],
            entry.get("episode_ref"),
        )
        for entry in resident_entries
    }

    committed, incoming_motif, _ = section.receive(
        _dsf(-0.4),
        CHI,
        "incoming",
        atlas,
        familiarity=0.0,
        salience=1.0,
        dwell_ticks=1,
        engine_tick=3,
        atlas_kwargs={
            "source": "incoming_source",
            "episode_ref": "incoming_episode",
        },
    )

    assert committed
    assert incoming_motif != resident_motif
    for entry in resident_entries:
        assert (
            entry["last_tick"],
            entry["reinforcement_count"],
            entry["source"],
            entry.get("episode_ref"),
        ) == before[id(entry)]
    assert "reinstatements_since_boot" not in deep_atlas.snapshot()


def test_legacy_reinstatement_counter_is_ignored_and_not_saved_again():
    _, _, deep_atlas, _ = _build_deep_cohabitant()
    legacy_payload = deep_atlas.to_json()
    legacy_payload["reinstatements"] = 3_100_000

    restored = DeepAtlas()
    saved_count = restored.load_from_json(legacy_payload)

    assert saved_count == deep_atlas.live_count()
    assert restored.live_count() == deep_atlas.live_count()
    assert "reinstatements" not in restored.to_json()
    assert "reinstatements_since_boot" not in restored.snapshot()
