"""Primary-call translation only; native/mature behavior is proved separately."""

from dataclasses import dataclass
from fractions import Fraction
from types import SimpleNamespace

import pytest

from dsf_ai_service import lean_physical_loop as loop
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence


@dataclass(frozen=True)
class Sensorium:
    retina: tuple = ((Fraction(0),) * len(loop.PASSIVE_TIMES),)
    legacy_ears: tuple = ()
    cochleae: tuple = ()


@pytest.mark.parametrize(
    "guided,pending,external",
    [(True, True, True), (True, False, True), (False, True, True), (False, True, False)],
)
def test_primary_keeps_tutor_and_authenticated_self_hearing_together(
    monkeypatch, guided, pending, external,
):
    own_pressure, own_body, tutor = b"own pressure", b"own body", b"tutor pressure"
    calls = []
    projections = []
    ready = SimpleNamespace(identity="test-identity", articulated_body_axes=())
    runtime = SimpleNamespace(
        live_organism_tick=10,
        in_flight_acoustic_pressure_s16le=own_pressure if pending else None,
        in_flight_acoustic_body_s16le=own_body if pending else None,
        in_flight_acoustic_source_tick=9 if pending else None,
        readiness=lambda: ready,
    )

    def admitted(kind, *args, **kwargs):
        calls.append((kind, args, kwargs))
        runtime.live_organism_tick += 1
        runtime.in_flight_acoustic_pressure_s16le = None
        runtime.in_flight_acoustic_body_s16le = None
        runtime.in_flight_acoustic_source_tick = None
        return SimpleNamespace(
            articulated_body_consequences=(),
            causal_transition_sha256="a" * 64,
            dsf_delivery_count=0,
            physically_transitioned_neuron_count=0,
            python_callback_count=0,
        )

    runtime.advance_guided_vocal_interval_unsealed = (
        lambda *a, **k: admitted("guided", *a, **k)
    )
    runtime.advance_in_flight_self_hearing_unsealed = (
        lambda *a, **k: admitted("self", *a, **k)
    )
    world = SimpleNamespace(
        encoded_snapshot=lambda: b"world predecessor",
        observation_snapshot=lambda: SimpleNamespace(revision=1),
    )
    prepared = SimpleNamespace(
        execution_receipt=SimpleNamespace(after=object()),
    )
    monkeypatch.setattr(loop, "prepare_passive_world_interval", lambda _w: prepared)
    monkeypatch.setattr(loop, "passive_sensorium", lambda **_kw: Sensorium())
    monkeypatch.setattr(loop, "_commit_prepared", lambda _w, _p: None)
    monkeypatch.setattr(loop, "_requires_physical_return", lambda _e: False)
    monkeypatch.setattr(loop, "lean_embodiment_observation", lambda *_a: {})

    def transduce(pressure):
        value = 1.0 if pressure == tutor else 0.25
        return loop.PASSIVE_TIMES, (value,), ((value,),), 4_000

    monkeypatch.setattr(loop, "one_self_hearing_hop", transduce)
    monkeypatch.setattr(
        loop, "settle_physical_sensorium", lambda **kw: kw["sensorium"],
    )

    def projected(**kw):
        projections.append(kw["senses"])
        return kw["sensorium"]

    monkeypatch.setattr(loop, "settle_projected_physical_sensorium", projected)
    drives = ((37, 0, 1_500),) if guided else None
    occurrence = (
        PhysicalOccurrence(
            "sensory",
            LeanSensoryOccurrence(
                "guided-vocal-microphone" if guided else "microphone",
                None, tutor, drives,
            ),
        )
        if external else PhysicalOccurrence("unattended", None)
    )
    result = loop.LeanPhysicalLoop().settle(runtime, world, occurrence)
    assert len(calls) == 1
    kind, args, kwargs = calls[0]
    sources, admissions = args[:2]
    assert len(sources) == (2 if pending and external else 1)
    assert admissions == loop.PASSIVE_ADMISSION * len(sources)
    assert sources[0].legacy_ears == (((1.0,),) * 2 if external else ((0.25,),) * 2)
    assert projections == ([(loop.PhysicalSense.SOUND,)] if pending and external else [])
    if pending and external:
        assert sources[1].legacy_ears == ((0.25,),) * 2
    if guided:
        assert kind == "guided" and args[2] == drives
        assert kwargs == {
            "pressure_s16le": own_pressure if pending else None,
            "body_s16le": own_body if pending else None,
            "consumed_sample_count": 4_000 if pending else None,
        }
    else:
        assert kind == "self"
        assert args[2:] == (own_pressure, own_body, external, 4_000)
    assert result.native_interval_count == 1
    assert result.observation["external_heard_sample_count"] == (4_000 if external else 0)
    assert result.observation["self_heard_sample_count"] == (4_000 if pending else 0)
    assert result.observation["external_guided_vocal_axis_count"] == (1 if guided else 0)
