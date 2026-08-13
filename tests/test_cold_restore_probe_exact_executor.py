"""Fresh-process proof for one raw native CURRENT organism."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import dsf_ai_service.cold_restore_probe as probe


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
STATE = b"GLORUN01-native-current-test"
STATE_SHA = hashlib.sha256(STATE).hexdigest()
GIT_SHA = "a" * 40
IMAGE = "sha256:" + "b" * 64


@dataclass
class _Observation:
    identity: str = IDENTITY
    organism_tick: int = 23_723_846
    state_bytes: int = len(STATE)
    state_sha256: str = STATE_SHA
    python_callback_count: int = 0
    joint_field_count: int = 2
    complete_neuron_count: int = 217
    developmental_resting_neuron_count: int = 196_335


class _Organism:
    def __init__(self) -> None:
        self.readiness_calls = 0
        self.save_calls = 0

    def readiness(self) -> _Observation:
        self.readiness_calls += 1
        return _Observation()

    def save(self) -> bytes:
        self.save_calls += 1
        return STATE


@dataclass
class _Pointer:
    identity: str = IDENTITY
    organism_tick: int = 23_723_846
    state_sha256: str = STATE_SHA


@dataclass
class _Restored:
    organism: _Organism = field(default_factory=_Organism)
    pointer: _Pointer = field(default_factory=_Pointer)


@dataclass
class _Admission:
    max_envelope_bytes: int = 1_000
    max_fabric_bytes: int = 900
    max_logical_peak_bytes: int = 3_000


def _arguments(**changes: object) -> SimpleNamespace:
    values = {
        "native_store_root": "/read-only/native-organism",
        "expected_identity": IDENTITY,
        "expected_tick": 23_723_846,
        "expected_state_sha256": STATE_SHA,
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_probe_cannot_import_the_retired_python_organism() -> None:
    source = Path(probe.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "guala_physical_runtime",
        "Guala(",
        "load_full_state",
        "generation_store",
        "owner",
        "exact_field_executor",
    ):
        assert forbidden not in source
    assert "restore_current_native_organism" in source
    assert "raw_glorun_current_only" in source


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("expected_state_sha256", "not-a-sha", "state SHA-256"),
        ("candidate_git_sha", "not-a-commit", "commit"),
        ("candidate_image_digest", "latest", "image digest"),
    ),
)
def test_probe_rejects_noncanonical_artifact_coordinates_before_restore(
    monkeypatch,
    field: str,
    value: str,
    message: str,
) -> None:
    monkeypatch.setattr(probe, "_arguments", lambda: _arguments(**{field: value}))
    monkeypatch.setattr(
        probe,
        "derive_native_resident_resource_admission",
        lambda _root: (_ for _ in ()).throw(AssertionError("must not derive")),
    )
    with pytest.raises(ValueError, match=message):
        probe.main()


def test_probe_reads_saves_and_reobserves_without_advancing_state(
    monkeypatch,
    capsys,
) -> None:
    restored = _Restored()
    monkeypatch.setattr(probe, "_arguments", _arguments)
    monkeypatch.setattr(
        probe,
        "derive_native_resident_resource_admission",
        lambda _root: _Admission(),
    )
    monkeypatch.setattr(
        probe,
        "restore_current_native_organism",
        lambda *_args, **_kwargs: restored,
    )

    assert probe.main() == 0
    assert restored.organism.readiness_calls == 2
    assert restored.organism.save_calls == 1
    proof = json.loads(capsys.readouterr().out)
    receipt = proof.pop("receipt_sha256")
    assert proof == {
        "baseline_observed_state_sha256": STATE_SHA,
        "baseline_observed_tick": 23_723_846,
        "candidate_git_sha": GIT_SHA,
        "candidate_image_digest": IMAGE,
        "cold_restore_exact": True,
        "complete_neuron_count": 217,
        "current_format_migration_rehearsed": False,
        "developmental_resting_neuron_count": 196_335,
        "migration_predecessor_state_sha256": None,
        "mode": "cold-restore",
        "motor_action_rehearsed": False,
        "python_callback_count": 0,
        "python_cognition_workers_started": 0,
        "raw_glorun_current_only": True,
        "resident_state_bytes": len(STATE),
        "resident_state_sha256": STATE_SHA,
        "schema": probe.PROOF_SCHEMA,
        "source_identity": IDENTITY,
        "source_advanced_after_baseline": False,
        "source_mount_read_only": True,
        "tick": 23_723_846,
    }
    assert receipt == hashlib.sha256(probe._canonical(proof)).hexdigest()


def test_probe_rejects_state_or_callback_change(monkeypatch) -> None:
    class _ChangedOrganism(_Organism):
        def readiness(self) -> _Observation:
            observed = super().readiness()
            if self.readiness_calls == 2:
                observed.state_sha256 = "f" * 64
                observed.python_callback_count = 1
            return observed

    restored = _Restored(organism=_ChangedOrganism())
    monkeypatch.setattr(probe, "_arguments", _arguments)
    monkeypatch.setattr(
        probe,
        "derive_native_resident_resource_admission",
        lambda _root: _Admission(),
    )
    monkeypatch.setattr(
        probe,
        "restore_current_native_organism",
        lambda *_args, **_kwargs: restored,
    )
    with pytest.raises(RuntimeError, match="cold restore changed"):
        probe.main()


def test_articulation_rehearsal_reads_tick_through_native_observation(
    monkeypatch,
) -> None:
    from dsf_ai_service import native_production_app

    class _ArticulatingOrganism:
        def readiness(self) -> SimpleNamespace:
            return SimpleNamespace(organism_tick=37)

        def prepare_admitted(self, _episode, _admissions) -> SimpleNamespace:
            return SimpleNamespace(
                token="heard",
                physically_transitioned_neuron_count=2,
                complete_neuron_fractal_count=1,
                externally_perturbed_body_receptor_count=1,
            )

        def commit(self, token: str) -> None:
            assert token == "heard"

    monkeypatch.setattr(
        probe,
        "exact_articulatory_unit_trajectory",
        lambda **_kwargs: (
            16_000,
            (1, -1),
            b"\x01\x00\x00\x00" * 4,
            3,
            80,
            265,
            0,
            1,
            0,
            2,
        ),
    )
    observed_prefixes: list[str] = []

    def episodes(**kwargs):
        observed_prefixes.append(kwargs["assembly_prefix"])
        return [(object(), [])]

    monkeypatch.setattr(native_production_app, "_mono_pcm_hop_episodes", episodes)
    prepared = SimpleNamespace(
        articulatory_unit_recruitments=(
            ("13" * 16, 0, 1, (("12" * 16, 12, "13" * 16, 13, 0, 1),)),
        )
    )

    proof = probe._rehearse_articulation_and_self_hearing(
        _ArticulatingOrganism(), prepared
    )

    assert observed_prefixes == ["c020-cold-self-hearing-37"]
    assert proof is not None
    assert proof["self_hearing_transitioned_neuron_count"] == 2
    assert proof["self_hearing_fractal_count"] == 1


def test_native_articulation_source_uses_one_real_interval_and_replays_exactly(
    monkeypatch,
) -> None:
    recruitment = (
        "13" * 16,
        0,
        5,
        (("12" * 16, 12, "13" * 16, 13, 0, 5),),
    )

    class _SourceOrganism:
        def __init__(self) -> None:
            self.tick = 40

        def readiness(self) -> SimpleNamespace:
            return SimpleNamespace(
                identity=IDENTITY,
                organism_tick=self.tick,
                python_callback_count=0,
                state_bytes=1_000 + self.tick,
                state_sha256=f"{self.tick:064x}",
            )

        def prepare_vestibular_trajectory(
            self, heading: int, steps: tuple[int, ...]
        ) -> SimpleNamespace:
            assert heading == 0
            assert steps == (360,)
            return SimpleNamespace(
                token="source",
                articulatory_unit_recruitments=(recruitment,),
                dsf_delivery_count=2,
                physically_transitioned_neuron_count=208,
            )

        def commit(self, token: str) -> SimpleNamespace:
            assert token == "source"
            self.tick += 1
            return self.readiness()

        def save(self) -> bytes:
            return f"successor-{self.tick}".encode("ascii")

    monkeypatch.setattr(
        probe,
        "exact_native_yaw_trajectory",
        lambda **_kwargs: (360, (360,)),
    )
    monkeypatch.setattr(
        probe,
        "restore_native_resident_organism",
        lambda **_kwargs: _SourceOrganism(),
    )

    def articulate(organism, prepared):
        assert tuple(prepared.articulatory_unit_recruitments) == (recruitment,)
        organism.tick += 4
        return {
            "layer_13_recruitment_count": 1,
            "self_hearing_hop_count": 4,
        }

    monkeypatch.setattr(
        probe,
        "_rehearse_articulation_and_self_hearing",
        articulate,
    )

    proof = probe._rehearse_native_articulation_source(b"body", {})

    assert proof["native_articulation_cold_replay_exact"] is True
    assert proof["native_articulation_source_interval_count"] == 1
    assert proof["native_articulation_source_dsf_delivery_count"] == 2
    assert proof["native_articulation_source_layer_13_recruitment_count"] == 1
    assert (
        proof["native_articulation_source_physically_transitioned_neuron_count"]
        == 208
    )


def test_episodic_relation_resolves_only_against_retained_successor() -> None:
    recalled = ("01" * 16, "02" * 16, "03" * 16)
    related = ("04" * 16, "05" * 16, "06" * 16)
    recalled_receipt = "1" * 64
    related_receipt = "2" * 64
    bond = (recalled[0], related[0], 0)

    class _EpisodicOrganism:
        committed = False

        def commit(self, token: str) -> None:
            assert token == "prepared-token"
            self.committed = True

        def observe_retained_formation_structures(self):
            assert self.committed
            return (
                (recalled_receipt, recalled, (), (), 0),
                (related_receipt, related, (), (), 0),
            )

    organism = _EpisodicOrganism()
    prepared = SimpleNamespace(
        token="prepared-token",
        organic_mosaic_relations=(
            (
                (recalled_receipt, related_receipt),
                (),
                (bond,),
                "55" * 32,
                (((recalled[0], related[0], 0, 7), (related[0], related[1], 0, 5)),),
                (
                    (
                        (recalled[0], related[0], 0, 7),
                        (related[0], related[1], 0, 5),
                        (recalled[0], related[0], 0, 9),
                        (related[0], related[1], 0, 4),
                    ),
                ),
            ),
        ),
    )
    observed = probe._commit_and_observe_episodic_relation(
        organism,
        prepared,
        recalled,
    )
    assert observed is not None
    assert observed["episodic_recalled_formation_receipt"] == recalled_receipt
    assert observed["episodic_related_formation_count"] == 2
    assert observed["episodic_relation_active_bond_count"] == 1
    assert observed["ordered_physical_path_count"] == 1
    assert observed["ordered_path_relation_count"] == 1
    assert observed["structural_relation_sha256"] == "55" * 32
