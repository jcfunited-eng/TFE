from __future__ import annotations

from pathlib import Path

import pytest

from dsf_ai_service.v4.guala_physical_runtime_core import (
    Guala,
    _build_live_whole_organism_episode_authority,
)


def test_legacy_whole_organism_builder_cannot_be_resurrected() -> None:
    with pytest.raises(
        RuntimeError,
        match="legacy Python whole-organism episode graph is permanently retired",
    ):
        _build_live_whole_organism_episode_authority("retired")


def test_legacy_owner_observation_cannot_receive_a_settlement() -> None:
    organism = object.__new__(Guala)
    with pytest.raises(
        RuntimeError,
        match="legacy owner-scoped whole-organism cognition is permanently retired",
    ):
        organism._observe_whole_organism_settlement(None)


def test_runtime_initializes_no_legacy_whole_organism_authority() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "dsf_ai_service/v4/guala_physical_runtime_core.py"
    ).read_text(encoding="utf-8")
    for field in (
        "_whole_organism_episode_authority",
        "_whole_organism_recovery_owner",
        "_whole_organism_structural_owner",
    ):
        assert f"self.{field} = None" in source
        assert f"self.{field} = _build" not in source


def test_embodied_action_refuses_before_mutation_admission() -> None:
    organism = object.__new__(Guala)
    with pytest.raises(
        RuntimeError,
        match="native embodied action settlement is not yet mounted",
    ):
        organism.durably_experience_embodied_action(
            tutor_id="joe",
            nonce="bounded-canonical-nonce",
            port_id="W1",
            command_payload=b"command",
            state_dir="/not-used",
        )

    source = (
        Path(__file__).resolve().parents[1]
        / "dsf_ai_service/v4/guala_physical_runtime_core.py"
    ).read_text(encoding="utf-8")
    start = source.index("    def durably_experience_embodied_action(")
    assert source.rfind("@_engine_mutation_entry", 0, start) < (
        source.rfind("\n    def ", 0, start)
    )
