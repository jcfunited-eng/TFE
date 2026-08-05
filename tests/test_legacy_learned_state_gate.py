from __future__ import annotations

import base64
import gzip
import hashlib
import hmac
import json
import uuid

import pytest

from dsf_ai_service.substrate.legacy_learned_state_gate import (
    DIRECT,
    ESCROW,
    UNRESOLVED,
    LegacyLearnedStateGateError,
    LegacyLearnedStateUnresolved,
    build_legacy_learned_state_plan,
    verify_legacy_learned_state_plan,
)
from dsf_ai_service.substrate.owner_scoped_persistence import (
    decode_owner_state_bodies,
)
from dsf_ai_service.v4.guala_physical_runtime import Guala


AUTHORITY = b"legacy-learned-state-gate-test-authority"


@pytest.fixture(autouse=True)
def _physical_runtime_environment(monkeypatch):
    monkeypatch.setenv("EVENT_DRIVEN_SUBSTRATE", "0")
    monkeypatch.setenv(
        "GUALA_CAUSAL_ACTION_KEY",
        AUTHORITY.decode("ascii"),
    )


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _legacy_envelope(identity: str, tick: int, data: dict) -> bytes:
    return _canonical({
        "data": data,
        "guala_identity": identity,
        "saved_at_tick": tick,
        "saved_at_timestamp": "2026-07-28T00:00:00Z",
        "schema_version": "v7.4.0",
    })


def _legacy_anonymous_av_genesis(runtime) -> dict[str, object]:
    payload = {
        "generation": 0,
        "latest": None,
        "schema": (
            "guala.w1.anonymous_audiovisual_continuity.snapshot.v1"
        ),
        "settled": 0,
        "transition_capacity": 64,
        "transitions": [],
    }
    signature = hmac.new(
        runtime._w1_anonymous_av_continuity_owner._key,
        b"guala.w1.anonymous_audiovisual_continuity.snapshot.v1\0"
        + _canonical(payload),
        hashlib.sha256,
    ).hexdigest()
    return {
        "authority_hmac_sha256": signature,
        "authority_receipt_sha256": hashlib.sha256(_canonical({
            "authority_hmac_sha256": signature,
            "payload": payload,
        })).hexdigest(),
        "payload": payload,
    }


def _retired_auditory_reciprocity() -> dict[str, object]:
    payload = json.dumps(
        {
            "branch_capacity_per_class": 4,
            "class_capacity_per_kind": 64,
            "classes": [],
            "schema": "guala.auditory.causal_path.v5",
            "source_continuity": (
                "unavailable_without_receipted_stream_authority"
            ),
            "tutor_authority_required": True,
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return {
        "encoding": "gzip+base64",
        "payload": base64.b64encode(
            gzip.compress(payload, compresslevel=6, mtime=0)
        ).decode("ascii"),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "schema": "guala.auditory.causal_path.gzip.v5",
    }


def _retired_causal_action() -> dict[str, object]:
    payload = _canonical({
        "action_capacity": 64,
        "bindings": [],
        "encoded_byte_capacity": 16 * 1024 * 1024,
        "scalar_capacity": 512,
        "schema": "guala.causal_action.state.v1",
        "transient_capacity": 4,
        "witness_capacity": 128,
        "witnesses": [],
    })
    return {
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "schema": "guala.causal_action.hmac.v1",
        "state_hmac_sha256": hmac.new(
            AUTHORITY,
            b"guala-causal-action-state-v1\0" + payload,
            hashlib.sha256,
        ).hexdigest(),
    }


def _resign_retired_causal_action(
    state: dict[str, object],
) -> dict[str, object]:
    payload = _canonical(state)
    return {
        "payload_base64": base64.b64encode(payload).decode("ascii"),
        "schema": "guala.causal_action.hmac.v1",
        "state_hmac_sha256": hmac.new(
            AUTHORITY,
            b"guala-causal-action-state-v1\0" + payload,
            hashlib.sha256,
        ).hexdigest(),
    }


def _retired_auditory_v4_archive() -> dict[str, object]:
    payload = json.dumps(
        {
            "branch_capacity_per_class": 4,
            "class_capacity_per_kind": 64,
            "classes": [],
            "schema": "guala.auditory.causal_path.v4",
            "source_continuity": (
                "unavailable_without_receipted_stream_authority"
            ),
            "tutor_authority_required": True,
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    reciprocity = {
        "encoding": "gzip+base64",
        "payload": base64.b64encode(
            gzip.compress(payload, compresslevel=6, mtime=0)
        ).decode("ascii"),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "schema": "guala.auditory.causal_path.gzip.v4",
    }
    action = {
        "payload_base64": "e30=",
        "schema": "guala.causal_action.hmac.v1",
        "state_hmac_sha256": "a" * 64,
    }
    terminal = {
        "schema": "guala.auditory.incremental_terminal.v2",
    }
    return {
        "auditory_reciprocity_v4": reciprocity,
        "auditory_reciprocity_v4_canonical_sha256": (
            hashlib.sha256(_canonical(reciprocity)).hexdigest()
        ),
        "quarantined_causal_action": action,
        "quarantined_causal_action_canonical_sha256": (
            hashlib.sha256(_canonical(action)).hexdigest()
        ),
        "quarantined_latest_auditory_causal_event": terminal,
        (
            "quarantined_latest_auditory_causal_event_"
            "canonical_sha256"
        ): hashlib.sha256(_canonical(terminal)).hexdigest(),
        "schema": "guala.auditory.persistence_archive.v1",
    }


def _source(tmp_path, runtime, *, unresolved=False):
    identity_root = tmp_path / "identity-source"
    runtime._generate_genesis_identity(str(identity_root))
    identity = runtime._guala_identity
    assert identity == str(uuid.UUID(identity))
    tick = 91
    current_bodies = runtime._bounded_owner_state_bodies()
    genesis = decode_owner_state_bodies(
        {
            path: body
            for path, body in current_bodies.items()
            if path.endswith(".json")
        }
    )
    teaching = {
        "auditory_token_bindings": {},
        "causal_action_cycle": genesis["causal_action_cycle"],
        "causal_action_cycle_pending_review": (
            genesis["causal_action_cycle_pending_review"]
        ),
    }
    if unresolved:
        teaching["unmapped_learned_custody"] = {
            "possibly_physical_evidence": "no direct current owner"
        }
    (tmp_path / "guala_teaching.json").write_bytes(
        _legacy_envelope(identity, tick, teaching)
    )
    (tmp_path / "guala_sounds.json").write_bytes(
        _legacy_envelope(identity, tick, {
            "named-profile": {"raw_signal": [1, 2, 3]},
        })
    )
    sound = tmp_path / "sounds" / "legacy.audio"
    sound.parent.mkdir()
    sound.write_bytes(b"\x00\x01\x02\x03")
    return identity, tick


def test_gate_seals_retired_auditory_reciprocity_without_activation(
    tmp_path,
):
    runtime = Guala()
    try:
        identity_root = tmp_path / "identity-source"
        runtime._generate_genesis_identity(str(identity_root))
        identity = runtime._guala_identity
        tick = 23
        (tmp_path / "guala_teaching.json").write_bytes(
            _legacy_envelope(
                identity,
                tick,
                {
                    "auditory_reciprocity": (
                        _retired_auditory_reciprocity()
                    ),
                },
            )
        )

        plan = build_legacy_learned_state_plan(
            tmp_path,
            identity=identity,
            tick=tick,
            authority_key=AUTHORITY,
            max_sealed_escrow_bytes=1024 * 1024,
            runtime=runtime,
        )

        assert plan.cutover_allowed is True
        member = next(
            value
            for value in plan.body["members"]
            if value["member"] == "auditory_reciprocity"
        )
        assert member["category"] == ESCROW
        assert member["target_path"] is None
        assert member["custody_evidence"][
            "mechanism_active_in_current_runtime"
        ] is False
        assert member["custody_evidence"]["single_sense_authority"] is True
        assert member["custody_evidence"]["class_count"] == 0
        assert "sealed non-active custody" in member["reason"]

        tampered = _retired_auditory_reciprocity()
        tampered["payload_sha256"] = "0" * 64
        (tmp_path / "guala_teaching.json").write_bytes(
            _legacy_envelope(
                identity,
                tick,
                {"auditory_reciprocity": tampered},
            )
        )
        with pytest.raises(
            LegacyLearnedStateGateError,
            match="integrity changed",
        ):
            build_legacy_learned_state_plan(
                tmp_path,
                identity=identity,
                tick=tick,
                authority_key=AUTHORITY,
                max_sealed_escrow_bytes=1024 * 1024,
                runtime=runtime,
            )
    finally:
        runtime.strict_shutdown(timeout=30.0)


def test_gate_seals_retired_causal_action_with_exact_cold_inactivity(
    tmp_path,
):
    runtime = Guala()
    cold = None
    try:
        identity_root = tmp_path / "identity-source"
        runtime._generate_genesis_identity(str(identity_root))
        identity = runtime._guala_identity
        tick = 27
        retired = _retired_causal_action()
        source_body = _legacy_envelope(
            identity,
            tick,
            {"causal_action": retired},
        )
        (tmp_path / "guala_teaching.json").write_bytes(source_body)
        hot_cycle_before = runtime._causal_action_cycle.encoded_snapshot()

        plan = build_legacy_learned_state_plan(
            tmp_path,
            identity=identity,
            tick=tick,
            authority_key=AUTHORITY,
            max_sealed_escrow_bytes=len(source_body),
            runtime=runtime,
        )

        assert plan.cutover_allowed is True
        assert plan.direct_owner_bodies == {}
        assert runtime._causal_action_cycle.encoded_snapshot() == (
            hot_cycle_before
        )
        assert not hasattr(runtime, "_causal_action_owner")
        member = next(
            value
            for value in plan.body["members"]
            if value["member"] == "causal_action"
        )
        assert member["category"] == ESCROW
        assert member["target_owner_id"] is None
        assert member["target_path"] is None
        assert member["accounted_bytes"] == len(_canonical({
            "causal_action": retired,
        }))
        evidence = member["custody_evidence"]
        assert evidence == {
            "action_capacity": 64,
            "auditory_class_authority": True,
            "binding_count": 0,
            "decoded_payload_bytes": len(base64.b64decode(
                retired["payload_base64"]
            )),
            "encoded_byte_capacity": 16 * 1024 * 1024,
            "encoded_payload_bytes": len(
                retired["payload_base64"].encode("ascii")
            ),
            "mechanism_active_in_current_runtime": False,
            "payload_sha256": hashlib.sha256(base64.b64decode(
                retired["payload_base64"]
            )).hexdigest(),
            "scalar_capacity_per_binding": 512,
            "state_hmac_sha256": retired["state_hmac_sha256"],
            "transient_capacity": 4,
            "unicode_action_authority": True,
            "unicode_scalar_count": 0,
            "witness_capacity": 128,
            "witness_count": 0,
        }
        assert plan.body["category_bytes"] == {
            DIRECT: 0,
            ESCROW: len(source_body),
            UNRESOLVED: 0,
        }
        assert sum(
            record["accounted_bytes"]
            for record in plan.body["members"]
        ) == len(source_body)

        runtime.strict_shutdown(timeout=30.0)
        runtime = None
        cold = Guala()
        cold_cycle_before = cold._causal_action_cycle.encoded_snapshot()
        cold_plan = build_legacy_learned_state_plan(
            tmp_path,
            identity=identity,
            tick=tick,
            authority_key=AUTHORITY,
            max_sealed_escrow_bytes=len(source_body),
            runtime=cold,
        )
        assert cold_plan.record() == plan.record()
        assert cold._causal_action_cycle.encoded_snapshot() == (
            cold_cycle_before
        )
        assert not hasattr(cold, "_causal_action_owner")
    finally:
        if runtime is not None:
            runtime.strict_shutdown(timeout=30.0)
        if cold is not None:
            cold.strict_shutdown(timeout=30.0)


def test_gate_rejects_causal_action_hmac_schema_and_capacity_changes(
    tmp_path,
):
    runtime = Guala()
    try:
        identity_root = tmp_path / "identity-source"
        runtime._generate_genesis_identity(str(identity_root))
        identity = runtime._guala_identity
        tick = 28

        changed_hmac = _retired_causal_action()
        changed_hmac["state_hmac_sha256"] = "0" * 64
        (tmp_path / "guala_teaching.json").write_bytes(
            _legacy_envelope(
                identity,
                tick,
                {"causal_action": changed_hmac},
            )
        )
        with pytest.raises(
            LegacyLearnedStateGateError,
            match="state HMAC changed",
        ):
            build_legacy_learned_state_plan(
                tmp_path,
                identity=identity,
                tick=tick,
                authority_key=AUTHORITY,
                max_sealed_escrow_bytes=1024 * 1024,
                runtime=runtime,
            )

        changed_schema = json.loads(base64.b64decode(
            _retired_causal_action()["payload_base64"]
        ))
        changed_schema["schema"] = "guala.causal_action.state.v2"
        (tmp_path / "guala_teaching.json").write_bytes(
            _legacy_envelope(
                identity,
                tick,
                {
                    "causal_action": _resign_retired_causal_action(
                        changed_schema
                    ),
                },
            )
        )
        with pytest.raises(
            LegacyLearnedStateGateError,
            match="state schema changed",
        ):
            build_legacy_learned_state_plan(
                tmp_path,
                identity=identity,
                tick=tick,
                authority_key=AUTHORITY,
                max_sealed_escrow_bytes=1024 * 1024,
                runtime=runtime,
            )

        changed_capacity = json.loads(base64.b64decode(
            _retired_causal_action()["payload_base64"]
        ))
        changed_capacity["action_capacity"] = 63
        (tmp_path / "guala_teaching.json").write_bytes(
            _legacy_envelope(
                identity,
                tick,
                {
                    "causal_action": _resign_retired_causal_action(
                        changed_capacity
                    ),
                },
            )
        )
        with pytest.raises(
            LegacyLearnedStateGateError,
            match="state capacities changed",
        ):
            build_legacy_learned_state_plan(
                tmp_path,
                identity=identity,
                tick=tick,
                authority_key=AUTHORITY,
                max_sealed_escrow_bytes=1024 * 1024,
                runtime=runtime,
            )
    finally:
        runtime.strict_shutdown(timeout=30.0)


def test_gate_seals_explicit_auditory_v4_quarantine_without_detaching_it(
    tmp_path,
):
    runtime = Guala()
    try:
        identity_root = tmp_path / "identity-source"
        runtime._generate_genesis_identity(str(identity_root))
        identity = runtime._guala_identity
        tick = 29
        archive = _retired_auditory_v4_archive()
        (tmp_path / "guala_teaching.json").write_bytes(
            _legacy_envelope(
                identity,
                tick,
                {"auditory_v4_archive": archive},
            )
        )

        plan = build_legacy_learned_state_plan(
            tmp_path,
            identity=identity,
            tick=tick,
            authority_key=AUTHORITY,
            max_sealed_escrow_bytes=1024 * 1024,
            runtime=runtime,
        )

        assert plan.cutover_allowed is True
        member = next(
            value
            for value in plan.body["members"]
            if value["member"] == "auditory_v4_archive"
        )
        assert member["category"] == ESCROW
        assert member["target_path"] is None
        evidence = member["custody_evidence"]
        assert evidence["causal_dependents_detachable"] is False
        assert evidence["mechanism_active_in_current_runtime"] is False
        assert evidence["migration_to_current_recurrent_motif"] == (
            "unavailable"
        )
        assert "explicit quarantine" in member["reason"]

        damaged = _retired_auditory_v4_archive()
        damaged["quarantined_causal_action"]["payload_base64"] = "e30=AA"
        (tmp_path / "guala_teaching.json").write_bytes(
            _legacy_envelope(
                identity,
                tick,
                {"auditory_v4_archive": damaged},
            )
        )
        with pytest.raises(
            LegacyLearnedStateGateError,
            match="quarantined_causal_action digest changed",
        ):
            build_legacy_learned_state_plan(
                tmp_path,
                identity=identity,
                tick=tick,
                authority_key=AUTHORITY,
                max_sealed_escrow_bytes=1024 * 1024,
                runtime=runtime,
            )
    finally:
        runtime.strict_shutdown(timeout=30.0)


