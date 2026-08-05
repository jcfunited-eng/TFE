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


def test_current_vocal_extension_snapshots_expose_exact_mutation_roots(
        monkeypatch) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "owner-vocal-state-key-123456789012345678901234",
    )
    guala = Guala()
    try:
        bodies = guala._bounded_owner_state_bodies()
        root_fields = {
            "owner_state/pending_body_owned_vocal_consequence.state": (
                "state_hmac_sha256"
            ),
            "owner_state/w1_companion_av_continuity.state": (
                "authority_hmac_sha256"
            ),
            "owner_state/experience_grown_vocal_causal_relation.state": (
                "state_hmac_sha256"
            ),
        }
        for relative_path, root_field in root_fields.items():
            snapshot = json.loads(bodies[relative_path])
            assert frozen_path_owner_mutation_root(
                relative_path,
                bodies[relative_path],
            ) == snapshot[root_field]

        continuity_path = "owner_state/w1_companion_av_continuity.state"
        changed = json.loads(bodies[continuity_path])
        changed["payload"]["generation"] += 1
        changed_body = json.dumps(
            changed,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        with pytest.raises(
            OwnerScopedPersistenceError,
            match="authority receipt",
        ):
            frozen_path_owner_mutation_root(
                continuity_path,
                changed_body,
            )
    finally:
        guala.shutdown()


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


def test_retired_structural_graph_is_absent_and_reflection_is_exact(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "owner-graph-runtime-key-123456789012345678901234",
    )
    guala = Guala()
    try:
        guala.save_full_state(
            tmp_path,
            publish_generation=False,
        )
        assert not (tmp_path / "guala_organism.sgr").exists()
        assert not (
            tmp_path / "guala_organism.sgr.binding.json"
        ).exists()
        reflection_path = (
            tmp_path
            / "owner_state"
            / "whole_organism_reflection_monitor.json"
        )
        persisted = decode_owner_state_bodies({
            group.relative_path: (
                tmp_path / group.relative_path
            ).read_bytes()
            for group in OWNER_STATE_GROUPS
        })
        assert reflection_path.is_file()
        assert (
            json.dumps(
                persisted["whole_organism_reflection_monitor"],
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            == guala._whole_organism_reflection_owner.snapshot_encoded()
        )
        assert not (tmp_path / "guala_tapestry.sgr").exists()
        assert not (tmp_path / "wave_atlas.npz").exists()
    finally:
        guala.shutdown()


def test_owner_bodies_are_tick_independent_and_one_mutation_is_one_path(
    monkeypatch,
) -> None:
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "owner-body-runtime-key-1234567890123456789012345",
    )
    guala = Guala()
    try:
        first_payload = guala._teaching_persistence_payload()
        first = owner_state_bodies(first_payload)
        guala.tick += 100
        assert owner_state_bodies(
            guala._teaching_persistence_payload()
        ) == first

        mutated_payload = dict(first_payload)
        mutated_payload["causal_thing_mosaic"] = {
            "body": {"mosaics": []},
            "state_hmac_sha256": "c" * 64,
        }
        mutated = owner_state_bodies(mutated_payload)
        changed = {
            path
            for path in first
            if first[path] != mutated[path]
        }
        assert changed == {
            "owner_state/causal_thing_mosaic.json"
        }
        group = next(
            value
            for value in OWNER_STATE_GROUPS
            if value.owner_id == "causal_thing_mosaic"
        )
        assert owner_state_body_mutation_root(
            group,
            mutated[group.relative_path],
        ) == "c" * 64
        assert decode_owner_state_bodies(first) == {
            key: first_payload[key]
            for group in OWNER_STATE_GROUPS
            for key in group.state_keys
        }
    finally:
        guala.shutdown()


def test_current_manifest_has_no_retired_state_paths() -> None:
    retired = Guala.RETIRED_BOOT_FILES
    assert not (set(Guala.FULL_SAVE_MANIFEST_FILES) & retired)
    assert not (set(Guala.HOT_SAVE_MANIFEST_FILES) & retired)
