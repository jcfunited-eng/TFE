from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from dsf_ai_service import native_production_app as serving


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
STATE_SHA = hashlib.sha256(b"native-state").hexdigest()


@dataclass
class _Observation:
    identity: str = IDENTITY
    organism_tick: int = 23_723_846
    fabric_bytes: int = 400
    fabric_generation: int = 13
    fabric_sha256: str = "a" * 64
    joint_field_count: int = 2
    joint_neuron_count: int = 96
    mounted_generation: int = 2
    state_bytes: int = 500
    state_sha256: str = STATE_SHA
    cognitive_mosaic_count: int = 0
    cognitive_ordinal: int = 0
    cognitive_trace_count: int = 0
    formation_activation_count: int = 0
    partial_cue_reassembly_count: int = 0
    physical_transition_claimed: bool = False
    python_callback_count: int = 0


class _Organism:
    def __init__(self) -> None:
        self.readiness_calls = 0

    def readiness(self) -> _Observation:
        self.readiness_calls += 1
        return _Observation()


@dataclass
class _Restored:
    organism: _Organism = field(default_factory=_Organism)


@dataclass
class _Admission:
    max_envelope_bytes: int = 1_000
    max_fabric_bytes: int = 900
    max_logical_peak_bytes: int = 3_000
    memory_boundary_source: str = "test"
    derivation: str = "three finite regions"


def _mount(monkeypatch) -> _Restored:
    restored = _Restored()
    monkeypatch.setattr(serving, "_restored", restored)
    monkeypatch.setattr(serving, "_admission", _Admission())
    monkeypatch.setattr(
        serving,
        "_build_identity",
        lambda: {
            "git_sha": "b" * 40,
            "image_digest": "sha256:" + "c" * 64,
            "task_definition": "dsf-ai-task:900",
        },
    )
    serving._refresh_public_observation_cache()
    return restored


def test_public_observation_is_cached_and_conditional(monkeypatch) -> None:
    restored = _mount(monkeypatch)
    assert restored.organism.readiness_calls == 1

    first = serving.native_observation()
    assert first.status_code == 200
    etag = first.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"')
    assert restored.organism.readiness_calls == 1

    unchanged = serving.native_observation(if_none_match=etag)
    assert unchanged.status_code == 304
    assert unchanged.body == b""
    assert unchanged.headers["etag"] == etag
    assert restored.organism.readiness_calls == 1

    again = serving.native_observation()
    assert again.body == first.body
    assert restored.organism.readiness_calls == 1


def test_public_observation_matches_both_browser_consumers(monkeypatch) -> None:
    _mount(monkeypatch)
    value = json.loads(serving.native_observation().body)

    assert value["schema"] == "guala.native.public_observation.v1"
    assert value["generation"] == value["organism"]["tick"]
    assert value["generation_state"] == {
        "fabric_generation": 13,
        "mounted_generation": 2,
        "organism_tick": 23_723_846,
        "state_sha256": STATE_SHA,
    }
    for name in (
        "identity",
        "organism",
        "sensory",
        "neuron_activity",
        "fractals",
        "formations",
        "recall",
        "cognitive_capital",
        "attention",
        "body",
        "autonomy",
        "articulation",
        "expression",
        "curriculum",
        "full_dsf",
        "persistence",
        "resources",
    ):
        section = value[name]
        assert isinstance(section["available"], bool)
        assert section["status"]
        assert section["reason"]

    for modality in (
        "visual",
        "auditory",
        "text",
        "touch",
        "temperature",
        "smell",
        "taste",
        "vestibular",
        "proprioception",
        "interoception",
    ):
        assert value["sensory"][modality]["available"] is False

    assert value["autonomy"]["action_observed"] is False
    assert value["fractals"]["count"] == 0
    assert value["formations"]["mosaic_count"] == 0
    assert value["full_dsf"]["fields"] == [
        "D_k",
        "M_k",
        "R_rev_k",
        "U_star_k",
        "C_k",
        "P_k",
        "B_k",
    ]
    assert value["full_dsf"]["projection"] == "none"
    assert value["observation_contract"] == {
        "cached_per_committed_generation": True,
        "cognition_authority": False,
        "declared_loss": (
            "only committed native readiness facts and explicit unavailability "
            "are projected; no neuronal field body is present"
        ),
        "read_advances_organism": False,
    }
    receipt = value.pop("snapshot_receipt_sha256")
    assert receipt == serving._receipt(value)


def test_capabilities_never_offer_an_unmounted_ingress(monkeypatch) -> None:
    _mount(monkeypatch)
    value = json.loads(serving.native_observation().body)
    assert value["capabilities"]
    for capability in value["capabilities"].values():
        assert capability["available"] is False
        assert capability["endpoint"] is None
        assert capability["status"] == "not_mounted"
        assert "not mounted" in capability["reason"]


def test_native_public_surface_contains_no_owner_or_legacy_observation_route(
    monkeypatch,
) -> None:
    _mount(monkeypatch)
    body = serving.native_observation().body.decode("ascii")
    assert "owner" not in body.lower()
    paths = {route.path for route in serving.app.routes}
    assert "/api/v1/guala/native-observation" in paths
    assert "/api/v1/gualaloom/observation" not in paths
