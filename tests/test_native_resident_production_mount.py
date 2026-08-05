"""Production mounts only the native resident organism and truthful transport."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

import pytest

from dsf_ai_service import native_production_app as production
from dsf_ai_service.glew_runtime.native_resident_organism import (
    create_native_resident_organism,
)


ROOT = Path(__file__).resolve().parents[1]
IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"


@dataclass
class _Observation:
    identity: str = IDENTITY
    organism_tick: int = 0
    fabric_bytes: int = 0
    fabric_generation: int = 0
    fabric_sha256: str = "0" * 64
    joint_field_count: int = 0
    joint_neuron_count: int = 0
    mounted_generation: int = 0
    state_bytes: int = 1
    state_sha256: str = "a" * 64
    cognitive_mosaic_count: int = 0
    cognitive_ordinal: int = 0
    cognitive_trace_count: int = 0
    formation_activation_count: int = 0
    partial_cue_reassembly_count: int = 0
    physical_transition_claimed: bool = False
    python_callback_count: int = 0


class _Organism:
    def __init__(self, observation: _Observation | None = None) -> None:
        self.observation = observation or _Observation()

    def readiness(self) -> _Observation:
        return self.observation


@dataclass
class _Restored:
    organism: _Organism = field(default_factory=_Organism)


@dataclass
class _Admission:
    max_envelope_bytes: int = 1_000
    max_fabric_bytes: int = 900
    max_logical_peak_bytes: int = 3_000
    memory_boundary_source: str = "test"
    derivation: str = "finite native test regions"


def _release_files() -> set[str]:
    manifest = json.loads(
        (ROOT / "deploy" / "guala_release_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        path
        for category in manifest["categories"]
        for path in category["files"]
    }


def test_release_cannot_boot_the_retired_python_organism() -> None:
    files = _release_files()
    assert "dsf_ai_service/native_production_app.py" in files
    assert "dsf_ai_service/v4/guala_physical_runtime.py" not in files
    assert "dsf_ai_service/substrate_runner.py" not in files
    source = (ROOT / "dsf_ai_service" / "native_production_app.py").read_text(
        encoding="utf-8"
    )
    assert "guala_physical_runtime" not in source
    assert "process_sound_frame" not in source


def test_native_genesis_is_empty_physical_state_not_synthetic_cognition() -> None:
    organism = create_native_resident_organism(
        organism_identity=IDENTITY,
        organism_tick=0,
        max_envelope_bytes=67_108_864,
        max_fabric_bytes=67_108_000,
        max_logical_peak_bytes=536_870_912,
    )
    observed = organism.readiness()
    body = organism.save()
    assert body.startswith(b"GLORUN01")
    assert observed.identity == IDENTITY
    assert observed.organism_tick == 0
    assert observed.joint_field_count == 0
    assert observed.joint_neuron_count == 0
    assert observed.cognitive_trace_count == 0
    assert observed.cognitive_mosaic_count == 0
    assert observed.formation_activation_count == 0
    assert observed.partial_cue_reassembly_count == 0
    assert observed.python_callback_count == 0


@pytest.mark.asyncio
async def test_unmounted_browser_senses_fail_without_touching_organism(
    monkeypatch,
) -> None:
    organism = _Organism()
    monkeypatch.setattr(production, "_restored", _Restored(organism))
    monkeypatch.setattr(production, "_admission", _Admission())
    before = organism.readiness()
    sight = await production.sight_frame(None)
    sound = await production.sound_frame(None)
    after = organism.readiness()
    assert sight.status_code == 503
    assert sound.status_code == 503
    assert before == after
    assert b"not mounted" in sight.body
    assert b"not mounted" in sound.body


def test_startup_rejects_retired_cognition_counters(monkeypatch) -> None:
    changed = _Observation(cognitive_trace_count=1)
    monkeypatch.setattr(
        production,
        "derive_native_resident_resource_admission",
        lambda _root: _Admission(),
    )
    monkeypatch.setattr(
        production,
        "restore_current_native_organism",
        lambda *_args, **_kwargs: _Restored(_Organism(changed)),
    )
    with pytest.raises(RuntimeError, match="retired cognitive counters"):
        production._startup()
    assert production._restored is None
    assert production._admission is None
