"""Production exposes only authenticated AE-native carrier physics."""

from __future__ import annotations

import inspect
import json

from dsf_ai_service.substrate.live_ae_neurochemical_flow import (
    LiveAENeurochemicalFlowOwner,
)
from dsf_ai_service.substrate.unavailable_neurochemical_flow import (
    UnavailableNeurochemicalFlowOwner,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala


CORE_GUALA = Guala.__mro__[1]


def test_production_uses_the_exact_live_neurochemical_authority() -> None:
    source = inspect.getsource(CORE_GUALA)
    assert "build_live_quiescent_neurochemical_mount" not in source
    assert "LiveAENeurochemicalFlowOwner" in source


def test_ae_native_chemistry_is_typed_without_biological_claims(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "live-neurochemical-honesty-test-authority-key",
    )
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    guala = Guala()
    try:
        guala.load_full_state(str(tmp_path))
        owner = guala._whole_organism_neurochemical_owner
        assert type(owner) is LiveAENeurochemicalFlowOwner

        status = owner.status()
        assert status["available"] is True
        assert status["chemistry_authority"] is True
        assert status["conservative"] is True
        assert status["local_receptor_coupling"] == (
            "available_exact_event_state"
        )
        assert (
            guala._physical_internal_body_state.status()[
                "neurochemical_reference_count"
            ]
            == 15
        )

        envelope = json.loads(owner.snapshot_encoded())
        encoded = json.dumps(envelope, sort_keys=True)
        for invented in ("mood", "reward", "salience"):
            assert invented not in encoded
        assert {
            value.species_id for value in owner._manifest.species
        } == {
            "species:ae-excitation-carrier",
            "species:ae-recovery-carrier",
        }

        mechanism = next(
            value
            for value in guala._whole_organism_episode_authority.manifest.mechanisms
            if value.mechanism_id == "state:neurochemical-flow"
        )
        assert mechanism.availability.value == "available"
        assert mechanism.unavailable_reason is None

        observation = guala.observation_snapshot()[
            "internal_neurochemical_flow"
        ]
        assert observation["available"] is True
        assert observation["chemistry_authority"] is True
        assert observation["conservative"] is True
    finally:
        guala.shutdown()


def test_authenticated_dry_legacy_state_migrates_to_live_genesis(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        "live-neurochemical-legacy-migration-test-key",
    )
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    guala = Guala()
    try:
        guala.load_full_state(str(tmp_path))
        legacy = UnavailableNeurochemicalFlowOwner(
            authority_key=(
                guala._whole_organism_neurochemical_authority_key
            ),
            internal_body_owner=guala._physical_internal_body_state,
        ).snapshot_encoded()
        guala._restore_whole_organism_neurochemical_snapshot(legacy)
        assert type(
            guala._whole_organism_neurochemical_owner
        ) is LiveAENeurochemicalFlowOwner
        assert guala._whole_organism_neurochemical_owner.boundary is None
    finally:
        guala.shutdown()
