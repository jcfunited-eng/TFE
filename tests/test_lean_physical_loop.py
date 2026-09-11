"""Input handoff only; mature speech behavior is proved through the real actor."""

from contextlib import nullcontext
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


@pytest.mark.parametrize("new_consequence", [False, True])
@pytest.mark.parametrize("physical_return", [False, True])
@pytest.mark.parametrize(
    "guided,pending,external",
    [(True, True, True), (True, False, True), (False, True, True), (False, True, False), (False, False, False)],
)
def test_primary_keeps_tutor_and_authenticated_self_hearing_together(
    monkeypatch, guided, pending, external, physical_return, new_consequence,
):
    own_pressure, own_body, tutor = b"own pressure", b"own body", b"tutor pressure"
    calls, passive_calls, bindings = [], [], []
    ready = SimpleNamespace(identity="test-identity", articulated_body_axes=(), state_sha256="d" * 64)
    runtime = SimpleNamespace(
        live_organism_tick=10,
        in_flight_acoustic_pressure_s16le=own_pressure if pending else None,
        in_flight_acoustic_body_s16le=own_body if pending else None,
        in_flight_acoustic_source_tick=9 if pending else None,
        readiness=lambda: ready,
    )

    def admitted(*args, **kwargs):
        calls.append((args, kwargs))
        runtime.live_organism_tick += 1
        runtime.in_flight_acoustic_pressure_s16le = None
        runtime.in_flight_acoustic_body_s16le = None
        runtime.in_flight_acoustic_source_tick = None
        return SimpleNamespace(
            articulated_body_consequences=(), causal_transition_sha256="a" * 64,
            dsf_delivery_count=0, physically_transitioned_neuron_count=0,
            python_callback_count=0,
        )

    runtime.advance_coexisting_admitted_interval_unsealed = admitted
    returning = SimpleNamespace(
        producer_tick=10, causal_transition_sha256="b" * 64, sources=(),
        vestibular=(0, 7), sensorium=lambda _times: Sensorium(),
        validate_binding=lambda **kw: bindings.append(kw),
    ) if physical_return else None
    world = SimpleNamespace(
        pending_physical_return=returning,
        observation_snapshot=lambda: SimpleNamespace(revision=1, authority_receipt_sha256="c" * 64),
        prepared_action_visibility_transaction=lambda _p: nullcontext(),
        commit_prepared_action=lambda _p: None,
    )

    def consume(expected):
        assert expected is returning
        world.pending_physical_return = None

    world.consume_physical_return = consume
    prepared = SimpleNamespace(execution_receipt=SimpleNamespace(
        after=SimpleNamespace(revision=2, authority_receipt_sha256="e" * 64),
    ))
    successor_return = SimpleNamespace(producer_tick=11)
    motor_plan = SimpleNamespace(
        prepared_world=prepared, sensorium=Sensorium(), sources=(), vestibular=None,
        actual_root_motion=(0, 0, 0), requested_root_motion=(0, 0, 0),
        requested_action="fixture-action", refusal_reason=None,
    )

    def commit(_prepared, **values):
        if values:
            assert values["expected_physical_return"] is returning
            assert values["physical_return"] is successor_return
            world.pending_physical_return = successor_return

    world.commit_prepared_action = commit
    monkeypatch.setattr(loop, "prepare_motor_consequence", lambda **_kw: motor_plan)
    monkeypatch.setattr(loop.PendingPhysicalReturn, "capture", lambda **_kw: successor_return)

    def prepare(_world):
        passive_calls.append(True)
        return prepared

    monkeypatch.setattr(loop, "prepare_passive_world_interval", prepare)
    monkeypatch.setattr(loop, "passive_sensorium", lambda **_kw: Sensorium())
    monkeypatch.setattr(loop, "_requires_physical_return", lambda _e: new_consequence)
    monkeypatch.setattr(loop, "lean_embodiment_observation", lambda *_a: {})

    def transduce(pressure):
        value = 1.0 if pressure == tutor else 0.25
        return loop.PASSIVE_TIMES, (value,), ((value,),), 4000

    monkeypatch.setattr(loop, "one_self_hearing_hop", transduce)
    monkeypatch.setattr(loop, "settle_physical_sensorium", lambda **kw: kw["sensorium"])
    monkeypatch.setattr(loop, "settle_projected_physical_sensorium", lambda **kw: kw["sensorium"])
    drives = ((37, 0, 1500),) if guided else None
    occurrence = (
        PhysicalOccurrence("sensory", LeanSensoryOccurrence(
            "guided-vocal-microphone" if guided else "microphone", None, tutor, drives,
        ))
        if external else PhysicalOccurrence("unattended", None)
    )
    result = loop.LeanPhysicalLoop().settle(runtime, world, occurrence)
    assert len(calls) == 1
    args, kwargs = calls[0]
    sources, admissions = args
    if physical_return:
        assert not passive_calls and len(bindings) == 1
        assert len(sources) == 1 + int(external) + int(pending)
        if external:
            assert sources[1].legacy_ears == ((1.0,),) * 2
        if pending:
            assert sources[-1].legacy_ears == ((0.25,),) * 2
        assert world.pending_physical_return is (successor_return if new_consequence else None)
    else:
        assert len(passive_calls) == 1 and not bindings
        assert len(sources) == (2 if pending and external else 1)
        assert sources[0].legacy_ears == (((1.0,),) * 2 if external else ((0.25,),) * 2 if pending else ())
    assert admissions == loop.PASSIVE_ADMISSION * len(sources)
    assert kwargs == {
        "guided_vocal_drives": drives,
        "pressure_s16le": own_pressure if pending else None,
        "body_s16le": own_body if pending else None,
        "consumed_sample_count": 4000 if pending else None,
        "vestibular_motion": (0, 7) if physical_return else None,
    }
    assert result.native_interval_count == 1
    assert result.observation["external_heard_sample_count"] == (4000 if external else 0)
    assert result.observation["self_heard_sample_count"] == (4000 if pending else 0)
    assert result.observation["external_guided_vocal_axis_count"] == (1 if guided else 0)
    assert result.observation["consumed_physical_return_tick"] == (10 if physical_return else None)
    assert result.observation["vestibular_return_consumed"] is physical_return


def test_native_explicit_pre_mutation_refusal_keeps_pending_return(monkeypatch):
    from guala_core import NativePhysicalInputRefused
    ready = SimpleNamespace(identity="fixture", articulated_body_axes=())
    pending = SimpleNamespace(
        validate_binding=lambda **_kw: None, sensorium=lambda _times: Sensorium(),
        causal_transition_sha256="a" * 64, sources=(), vestibular=None,
    )
    runtime = SimpleNamespace(
        live_organism_tick=10, readiness=lambda: ready,
        in_flight_acoustic_pressure_s16le=None,
        in_flight_acoustic_body_s16le=None, in_flight_acoustic_source_tick=None,
    )
    def refuse(*_a, **_kw):
        raise NativePhysicalInputRefused("native rejected input before taking state")
    runtime.advance_coexisting_admitted_interval_unsealed = refuse
    world = SimpleNamespace(
        pending_physical_return=pending,
        observation_snapshot=lambda: SimpleNamespace(revision=0, authority_receipt_sha256="b" * 64),
    )
    monkeypatch.setattr(loop, "settle_physical_sensorium", lambda **kw: kw["sensorium"])
    with pytest.raises(NativePhysicalInputRefused):
        loop.LeanPhysicalLoop().unattended(runtime, world)
    assert world.pending_physical_return is pending
    assert runtime.live_organism_tick == 10
