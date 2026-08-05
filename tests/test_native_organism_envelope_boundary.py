from __future__ import annotations

import base64
import hashlib

import pytest

from dsf_ai_service.substrate import native_organism_envelope_boundary as boundary


class _Observation:
    def __init__(self, state: bytes) -> None:
        self._state = state
        self.state_bytes = len(state)
        self.state_sha256 = hashlib.sha256(state).hexdigest()

    def as_bytes(self) -> bytes:
        return self._state


class _StructuralImpostor:
    def __init__(self, state: bytes) -> None:
        self._state = state
        self.state_bytes = len(state)
        self.state_sha256 = hashlib.sha256(state).hexdigest()

    def as_bytes(self) -> bytes:
        return self._state


class _NativeModule:
    NativeOrganismRuntimeTransition = _Observation


def _record(state: bytes) -> dict[str, object]:
    return {
        "byte_count": len(state),
        "schema": boundary.PERSISTENCE_SCHEMA,
        "state_base64": base64.b64encode(state).decode("ascii"),
        "state_sha256": hashlib.sha256(state).hexdigest(),
    }


def _admit_test_native_type(monkeypatch) -> None:
    monkeypatch.setattr(boundary, "_native_core", lambda: _NativeModule())


def test_current_envelope_round_trip_derives_observation_from_native_restore(
    monkeypatch,
) -> None:
    state = b"GLORUN01-current-native-organism"
    calls: list[dict[str, object]] = []
    _admit_test_native_type(monkeypatch)

    def restore(**values):
        calls.append(values)
        return _Observation(values["current_envelope"])

    monkeypatch.setattr(boundary, "restore_native_organism", restore)
    verified = boundary.VerifiedNativeOrganismEnvelope.from_persistence_record(
        _record(state),
        max_envelope_bytes=1_000,
        max_fabric_bytes=900,
        max_logical_peak_bytes=3_000,
    )

    encoded_bytes = len(_record(state)["state_base64"])
    reserved_copy_bytes = encoded_bytes + (2 * len(state))
    assert verified.state_bytes == state
    assert verified.persistence_record() == _record(state)
    assert calls == [{
        "current_envelope": state,
        "max_envelope_bytes": 1_000,
        "max_fabric_bytes": 900,
        "max_logical_peak_bytes": 3_000 - reserved_copy_bytes,
    }]


@pytest.mark.parametrize(
    "state",
    (
        b"GLMFAB04-not-an-organism-envelope",
        b"GLMFAB03-legacy-predecessor",
        b"GLJNFT03-inner-state",
    ),
)
def test_persistence_refuses_inner_or_legacy_state_before_native_restore(
    monkeypatch,
    state: bytes,
) -> None:
    _admit_test_native_type(monkeypatch)
    called = False

    def restore(**_values):
        nonlocal called
        called = True
        raise AssertionError("inner state reached native restore")

    monkeypatch.setattr(boundary, "restore_native_organism", restore)
    with pytest.raises(ValueError, match="not current GLORUN01"):
        boundary.VerifiedNativeOrganismEnvelope.from_persistence_record(
            _record(state),
            max_envelope_bytes=1_000,
            max_fabric_bytes=900,
            max_logical_peak_bytes=3_000,
        )
    assert not called


def test_persistence_refuses_tampered_bytes_before_native_restore(
    monkeypatch,
) -> None:
    state = b"GLORUN01-current-native-organism"
    record = _record(state)
    record["state_sha256"] = "0" * 64
    called = False

    def restore(**_values):
        nonlocal called
        called = True
        raise AssertionError("tampered state reached native restore")

    monkeypatch.setattr(boundary, "restore_native_organism", restore)
    with pytest.raises(ValueError, match="custody changed"):
        boundary.VerifiedNativeOrganismEnvelope.from_persistence_record(
            record,
            max_envelope_bytes=1_000,
            max_fabric_bytes=900,
            max_logical_peak_bytes=3_000,
        )
    assert not called


def test_oversized_record_refuses_without_base64_decode(monkeypatch) -> None:
    state = b"GLORUN01" + (b"x" * 1_001)
    record = _record(state)
    decoded = False

    def forbidden_decode(*_args, **_kwargs):
        nonlocal decoded
        decoded = True
        raise AssertionError("oversized state was decoded")

    monkeypatch.setattr(boundary.base64, "b64decode", forbidden_decode)
    with pytest.raises(ValueError, match="exceeds its envelope boundary"):
        boundary.VerifiedNativeOrganismEnvelope.from_persistence_record(
            record,
            max_envelope_bytes=1_000,
            max_fabric_bytes=900,
            max_logical_peak_bytes=3_001,
        )
    assert not decoded


def test_noncanonical_encoded_length_refuses_without_base64_decode(
    monkeypatch,
) -> None:
    state = b"GLORUN01-current"
    record = _record(state)
    record["state_base64"] = str(record["state_base64"]) + "AAAA"
    decoded = False

    def forbidden_decode(*_args, **_kwargs):
        nonlocal decoded
        decoded = True
        raise AssertionError("noncanonical state was decoded")

    monkeypatch.setattr(boundary.base64, "b64decode", forbidden_decode)
    with pytest.raises(ValueError, match="encoded length is not canonical"):
        boundary.VerifiedNativeOrganismEnvelope.from_persistence_record(
            record,
            max_envelope_bytes=1_000,
            max_fabric_bytes=900,
            max_logical_peak_bytes=3_000,
        )
    assert not decoded


def test_infrastructure_copy_peak_refuses_without_base64_decode(
    monkeypatch,
) -> None:
    state = b"GLORUN01" + (b"x" * 892)
    record = _record(state)
    decoded = False

    def forbidden_decode(*_args, **_kwargs):
        nonlocal decoded
        decoded = True
        raise AssertionError("unadmitted infrastructure copies were decoded")

    monkeypatch.setattr(boundary.base64, "b64decode", forbidden_decode)
    with pytest.raises(ValueError, match="copies exceed the admitted logical peak"):
        boundary.VerifiedNativeOrganismEnvelope.from_persistence_record(
            record,
            max_envelope_bytes=1_000,
            max_fabric_bytes=900,
            max_logical_peak_bytes=3_001,
        )
    assert not decoded


def test_verified_envelope_construction_is_factory_only() -> None:
    state = b"GLORUN01-current"
    with pytest.raises(TypeError, match="construction is factory-only"):
        boundary.VerifiedNativeOrganismEnvelope(
            state_bytes=state,
            observation=_Observation(state),
        )


def test_from_native_refuses_structural_impostor(monkeypatch) -> None:
    state = b"GLORUN01-current"
    _admit_test_native_type(monkeypatch)
    with pytest.raises(TypeError, match="concrete native result"):
        boundary.VerifiedNativeOrganismEnvelope.from_native(
            _StructuralImpostor(state)
        )


def test_persistence_receipt_is_recomputed_from_immutable_state(
    monkeypatch,
) -> None:
    state = b"GLORUN01-current"
    _admit_test_native_type(monkeypatch)
    observation = _Observation(state)
    verified = boundary.VerifiedNativeOrganismEnvelope.from_native(observation)
    observation.state_sha256 = "0" * 64

    assert verified.persistence_record()["state_sha256"] == hashlib.sha256(
        state
    ).hexdigest()
