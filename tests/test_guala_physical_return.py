"""Exact physical-medium custody, not a proof of learned speech."""

import base64
from dataclasses import replace
from fractions import Fraction
import hashlib
import hmac
import json
import struct
from types import SimpleNamespace

import pytest

from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.guala_motor_world import prepare_motor_consequence
from dsf_ai_service.guala_physical_return import PendingPhysicalReturn, RETURN_SAMPLE_BYTES
from dsf_ai_service.guala_physical_sensorium import compact_signal_body
from dsf_ai_service.guala_world_sensorium import consequence_source_times, passive_body_consequence_sensorium
from dsf_ai_service.lean_physical_loop import PASSIVE_TIMES
from dsf_ai_service.substrate import thermally_coupled_embodiment_world as coupled


IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
AXES = (
    (2, "neck_yaw", "millidegree", 0, -75000, 0, 75000),
    (8, "left_eyelid_aperture", "micrometre", 10000, 0, 10000, 12000),
    (9, "right_eyelid_aperture", "micrometre", 10000, 0, 10000, 12000),
)


def _plan(world, tick=41):
    return prepare_motor_consequence(
        world=world,
        evidence=SimpleNamespace(
            articulated_body_consequences=(), body_proprioceptive_sources=(),
            body_proprioceptive_source_extents=(), body_proprioceptive_source_admissions=(),
            root_yaw_unit_recruitments=(("01" * 16, 4, 7, "positive"),),
            root_translation_unit_recruitments=(),
            causal_transition_sha256="03" * 32, organism_tick=tick,
        ),
        predecessor_state_sha256="04" * 32,
        predecessor_body_axes=AXES, successor_body_axes=AXES,
    )


def _capture(plan, tick=41):
    after = plan.prepared_world.execution_receipt.after
    return PendingPhysicalReturn.capture(
        identity=IDENTITY, producer_tick=tick, causal_transition_sha256="03" * 32,
        world_revision=after.revision,
        world_observation_receipt_sha256=after.authority_receipt_sha256,
        sensorium=plan.sensorium, sources=plan.sources, vestibular=plan.vestibular,
    )


def test_actual_return_three_samples_preserve_all_frames_and_cold_consumption():
    world = home_world_authority(identity=IDENTITY)
    plan = _plan(world)
    pending = _capture(plan)
    times = consequence_source_times(PASSIVE_TIMES)
    full = passive_body_consequence_sensorium(
        world=world, execution=plan.prepared_world.execution_receipt,
        predecessor_body_axes=AXES, successor_body_axes=AXES, source_times=times,
    )
    rebuilt = pending.sensorium(times)
    assert len(pending.sampled_sensorium) == RETURN_SAMPLE_BYTES == 5280
    assert compact_signal_body(rebuilt, frame_count=27) == compact_signal_body(full, frame_count=27)
    middle = times.index(Fraction(1, 1000))
    assert rebuilt.displacement[3][middle] != 0
    assert rebuilt.displacement[3][middle + 1] == 0
    world.commit_prepared_action(plan.prepared_world, physical_return=pending)
    encoded = bytes(world.encoded_snapshot())
    cold = home_world_authority(identity=IDENTITY, encoded_world=encoded)
    assert bytes(cold.encoded_snapshot()) == encoded
    restored = cold.pending_physical_return
    assert restored == pending
    assert restored.sources[0].restore().as_bytes() == pending.sources[0].payload
    observed = cold.observation_snapshot()
    with pytest.raises(RuntimeError, match="current body/world"):
        restored.validate_binding(identity=IDENTITY, producer_tick=42,
                                  world_revision=observed.revision,
                                  world_receipt=observed.authority_receipt_sha256)
    cold.consume_physical_return(restored)
    assert cold.pending_physical_return is None
    assert cold.observation_snapshot().revision == observed.revision
    with pytest.raises(RuntimeError, match="custody"):
        cold.consume_physical_return(restored)


def test_return_is_replaced_atomically_and_renovation_cannot_drop_it():
    world = home_world_authority(identity=IDENTITY)
    first = _plan(world)
    pending = _capture(first)
    world.commit_prepared_action(first.prepared_world, physical_return=pending)
    with pytest.raises(RuntimeError, match="pending physical experience"):
        world.migrate_declared_home_topology()
    second = _plan(world, 42)
    successor = _capture(second, 42)
    with pytest.raises(RuntimeError, match="exact physical return"):
        world.commit_prepared_action(second.prepared_world, physical_return=successor)
    assert world.pending_physical_return is pending
    world.commit_prepared_action(second.prepared_world,
                                expected_physical_return=pending, physical_return=successor)
    assert world.pending_physical_return is successor
    with world.committed_prepared_action_rollback_transaction(second.prepared_world) as rollback:
        rollback()
    assert world.pending_physical_return is pending


def test_v2_migration_is_explicit_empty_and_keeps_the_inner_world():
    world = home_world_authority(identity=IDENTITY)
    current = json.loads(world.encoded_snapshot())
    payload = json.loads(base64.b64decode(current["payload_base64"]))
    inner = payload["world_state_base64"]
    del payload["pending_physical_return"]
    payload["schema"] = coupled.V2_COUPLED_SCHEMA
    body = coupled._canonical(payload)
    old = coupled._canonical({
        "schema": coupled.V2_COUPLED_SCHEMA,
        "payload_base64": base64.b64encode(body).decode("ascii"),
        "authority_hmac_sha256": hmac.new(world._thermal_key, coupled.V2_COUPLED_DOMAIN + body, hashlib.sha256).hexdigest(),
    })
    with pytest.raises(ValueError, match="explicit physical-return migration"):
        home_world_authority(identity=IDENTITY, encoded_world=old)
    migrated = home_world_authority(identity=IDENTITY, encoded_world=old, migrate_physical_return=True)
    after = json.loads(base64.b64decode(json.loads(migrated.encoded_snapshot())["payload_base64"]))
    assert after["world_state_base64"] == inner
    assert migrated.pending_physical_return is None
    assert after["thermal_state"] == payload["thermal_state"]


def test_changed_or_nonfinite_return_boundary_is_refused():
    world = home_world_authority(identity=IDENTITY)
    plan = _plan(world)
    pending = _capture(plan)
    with pytest.raises(ValueError, match="three sampled frames"):
        replace(pending, sampled_sensorium=pending.sampled_sensorium[:-8])
    with pytest.raises(ValueError, match="non-finite"):
        replace(pending, sampled_sensorium=struct.pack("<d", float("nan")) + pending.sampled_sensorium[8:])
    with pytest.raises(ValueError, match="physical duration"):
        replace(pending.sources[0], admissions=((True, 1000),))
    world.discard_prepared_action(plan.prepared_world)


def test_return_capacity_refuses_before_world_commit(monkeypatch):
    world = home_world_authority(identity=IDENTITY)
    before = world.observation_snapshot()
    plan = _plan(world)
    pending = _capture(plan)
    monkeypatch.setattr(coupled, "MAX_COUPLED_STATE_BYTES", 1)
    with pytest.raises(ValueError, match="declared world capacity"):
        world.commit_prepared_action(plan.prepared_world, physical_return=pending)
    assert world.pending_physical_return is None
    assert world.observation_snapshot() == before
    world.discard_prepared_action(plan.prepared_world)


def test_compact_tail_cold_custody_keeps_samples_order_and_duration():
    """Codec fixture only; not a claim that these samples were lived."""
    from dsf_ai_service.guala_physical_return import PhysicalReturnSource, MAX_PASSIVE_BODY_BYTES
    payload = b"GLBPTR01" + struct.pack("<QIBii", 40, 2, 1, 512, 513)
    # One physical axis ordinal follows the21byte fixed header.
    payload = payload[:21] + bytes([37]) + payload[21:]
    tail = PhysicalReturnSource(payload, (4, 8, 1, 2), ((1, 1000),))
    assert PhysicalReturnSource.from_record(tail.record()) == tail
    with pytest.raises(RuntimeError, match="native runtime budget"):
        tail.restore()
    with pytest.raises(ValueError, match="compact extent"):
        replace(tail, payload=payload + b"x")
    with pytest.raises(ValueError, match="physical duration"):
        replace(tail, admissions=((249, 1000),))
    oversized = tail.record()
    oversized["payload_base64"] = base64.b64encode(
        payload + bytes(MAX_PASSIVE_BODY_BYTES)
    ).decode("ascii")
    with pytest.raises(ValueError, match="exceeds its admission"):
        PhysicalReturnSource.from_record(oversized)
    world = home_world_authority(identity=IDENTITY)
    plan = _plan(world)
    pending = replace(_capture(plan), sources=(tail,) + plan.sources)
    with pytest.raises(ValueError, match="repeats or reorders"):
        replace(pending, sources=(tail, tail) + plan.sources)
    before = world.observation_snapshot()
    with pytest.raises(ValueError, match="pending producer"):
        replace(pending, producer_tick=42)
    assert world.pending_physical_return is None
    assert world.observation_snapshot() == before
    world.commit_prepared_action(plan.prepared_world, physical_return=pending)
    encoded = bytes(world.encoded_snapshot())
    cold = home_world_authority(identity=IDENTITY, encoded_world=encoded)
    assert bytes(cold.encoded_snapshot()) == encoded
    assert cold.pending_physical_return == pending
    assert cold.pending_physical_return.sources[0].payload == payload


def test_native_return_kind_bounds_refuse_oversize_or_duplicate_before_decode():
    """Boundary falsifier only; this does not assert memory or speech success."""
    world = home_world_authority(identity=IDENTITY)
    before = world.observation_snapshot()
    plan = _plan(world)
    pending = _capture(plan)
    yaw = pending.sources[0]
    assert yaw.payload.startswith(b"GLJSRC05")
    assert yaw.extents == (2, 4, 1, 2)
    with pytest.raises(ValueError, match="native source kind"):
        replace(yaw, extents=(4, 8, 1, 2))
    with pytest.raises(ValueError, match="native source kind"):
        replace(yaw, extents=(2, 4, 2, 4), admissions=((1, 1000), (1, 1000)))
    with pytest.raises(ValueError, match="kind is not mounted"):
        replace(yaw, payload=b"GLJSRC02" + yaw.payload[8:])
    with pytest.raises(ValueError, match="repeats or reorders"):
        replace(pending, sources=(yaw, yaw))
    assert world.pending_physical_return is None
    assert world.observation_snapshot() == before
    assert pending.sources == (yaw,)
    world.discard_prepared_action(plan.prepared_world)
