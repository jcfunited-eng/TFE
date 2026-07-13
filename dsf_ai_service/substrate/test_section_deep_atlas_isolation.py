"""Regression proof for the Section.receive/DeepAtlas mutation boundary.

Ordinary attention may create its own primary working-atlas binding, but it
must not reinstate a different deep-memory cohabitant at the same chi.  Deep
recall remains available only through the explicit ``DeepAtlas.reinstate``
boundary.  The proof uses the real Section, LivingAtlas, and DeepAtlas.
"""

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


def _record_count(atlas):
    return sum(len(entries) for entries in atlas.entries.values())


def _one_binding_record_count(atlas):
    """LivingAtlas preserves one binding across every address in its chi band."""

    return 2 * atlas.band + 1


def test_receive_isolated_from_deep_reinstatement_but_explicit_recall_survives(
    monkeypatch,
):
    monkeypatch.setenv("DEEP_ATLAS_ENABLED", "1")
    monkeypatch.setenv("DEEP_PRIOR_ENABLED", "1")

    parameters = inspect.signature(Section.receive).parameters
    assert "deep_atlas" not in parameters
    assert "index_callback" not in parameters

    # Remove the resident from working memory while retaining its promoted deep
    # record.  A same-chi receive may then add only its own primary commit.
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
    records_before_receive = _record_count(atlas)
    primary_record_count = _one_binding_record_count(atlas)
    reinstatements_before_receive = deep_atlas.reinstatements

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
    assert section.commits[-1]["mode"] == incoming_motif
    assert section.commits[-1]["word"] == "incoming"
    assert _record_count(atlas) == records_before_receive + primary_record_count
    assert not _entries_for(atlas, resident_motif)
    incoming_entries = _entries_for(atlas, incoming_motif)
    assert len(incoming_entries) == primary_record_count
    assert all(entry["source"] == "incoming_source" for entry in incoming_entries)
    assert all(
        entry["episode_ref"] == "incoming_episode"
        for entry in incoming_entries
    )
    assert deep_atlas.entries[CHI] == deep_before
    assert deep_atlas.reinstatements == reinstatements_before_receive

    # Deep memory remains explicitly recallable; only this named operation may
    # increment the reinstatement receipt and fund a caller-controlled write.
    recall_strength = deep_atlas.reinstate(
        CHI,
        SECTION,
        resident_motif,
        tick=4,
    )
    assert recall_strength > 0.0
    assert deep_atlas.reinstatements == reinstatements_before_receive + 1
    assert deep_atlas.entries[CHI] == deep_before

    atlas.record(
        SECTION,
        resident_motif,
        CHI,
        tick=4,
        salience=recall_strength,
        dwell_ticks=0,
        source="explicit_deep_recall",
    )
    assert _record_count(atlas) == (
        records_before_receive + 2 * primary_record_count
    )
    recalled_entries = _entries_for(atlas, resident_motif)
    assert len(recalled_entries) == primary_record_count
    assert all(
        entry["source"] == "explicit_deep_recall"
        for entry in recalled_entries
    )

    # If the cohabitant is already in working memory, an unrelated same-chi
    # receive must not refresh or reinforce it either.
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
    records_before_receive = _record_count(atlas)
    primary_record_count = _one_binding_record_count(atlas)

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
    assert _record_count(atlas) == records_before_receive + primary_record_count
    for entry in resident_entries:
        assert (
            entry["last_tick"],
            entry["reinforcement_count"],
            entry["source"],
            entry.get("episode_ref"),
        ) == before[id(entry)]
    assert deep_atlas.reinstatements == 0
