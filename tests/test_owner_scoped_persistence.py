"""Exact owner/role proofs for the current physical runtime generation."""

from __future__ import annotations

import json

import pytest

from dsf_ai_service.substrate.owner_scoped_persistence import (
    OWNER_STATE_GROUPS,
    OwnerScopedPersistenceError,
    census_generation_path_ownership,
    decode_owner_state_bodies,
    frozen_path_owner_mutation_root,
    issue_owner_state_snapshot_receipt,
    owner_state_bodies,
    owner_state_body_mutation_root,
    ownership_for_path,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala


KEY = b"owner-scoped-persistence-test-authority"


def _current_paths() -> tuple[str, ...]:
    return tuple(sorted({
        *Guala.FULL_SAVE_MANIFEST_FILES,
        Guala.IDENTITY_FILE,
    }))


def test_every_current_path_has_declared_ownership() -> None:
    paths = _current_paths()
    census = census_generation_path_ownership(paths)
    assert set(census) == set(paths)
    assert all(record.owner_ids for record in census.values())
    assert {
        group.relative_path for group in OWNER_STATE_GROUPS
    } < set(paths)


def test_current_vocal_extension_paths_have_exact_single_owners() -> None:
    expected = {
        "owner_state/pending_body_owned_vocal_consequence.state": (
            "pending_body_owned_vocal_consequence",
        ),
        "owner_state/w1_companion_av_continuity.state": (
            "w1_anonymous_audiovisual_continuity",
        ),
        "owner_state/experience_grown_vocal_causal_relation.state": (
            "experience_grown_vocal_causal_relation",
        ),
    }
    assert {
        relative_path: ownership_for_path(relative_path).owner_ids
        for relative_path in expected
    } == expected


def test_unknown_path_and_cross_owner_receipt_fail_closed() -> None:
    with pytest.raises(
        OwnerScopedPersistenceError,
        match="0 owners",
    ):
        ownership_for_path("unknown_state.bin")

    with pytest.raises(
        OwnerScopedPersistenceError,
        match="cannot issue one owner snapshot receipt",
    ):
        issue_owner_state_snapshot_receipt(
            identity="guala-owner-census",
            relative_path="guala_organism.sgr",
            body_sha256="a" * 64,
            body_bytes=31,
            mutation_root_sha256="b" * 64,
            frozen_tick=7,
            authority_key=KEY,
        )


def test_retired_structural_graph_is_absent_after_full_save(
    tmp_path,
    monkeypatch,
) -> None:
    """Anti-resurrection guard: a full save never recreates retired state."""
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "owner-graph-runtime-key-123456789012345678901234",
    )
    guala = Guala()
    try:
        guala.load_full_state(str(tmp_path))
        guala.save_full_state(
            tmp_path,
            publish_generation=False,
        )
        assert not (tmp_path / "guala_organism.sgr").exists()
        assert not (
            tmp_path / "guala_organism.sgr.binding.json"
        ).exists()
        assert not (tmp_path / "guala_tapestry.sgr").exists()
        assert not (tmp_path / "wave_atlas.npz").exists()
    finally:
        guala.shutdown()


def test_current_manifest_has_no_retired_state_paths() -> None:
    retired = Guala.RETIRED_BOOT_FILES
    assert not (set(Guala.FULL_SAVE_MANIFEST_FILES) & retired)
    assert not (set(Guala.HOT_SAVE_MANIFEST_FILES) & retired)
