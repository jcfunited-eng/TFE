"""Typed shared result for the one-way native joint-neuron fabric."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
from dsf_ai_service.glew_runtime.native_materialized_fabric import (
    ImmutableMaterializedFabricTransition,
)


MATERIALIZED_FABRIC_SCHEMA = (
    "guala.native.owner_free_materialized_fabric.v4"
)
MATERIALIZED_FABRIC_REFERENCE_SCHEMA = (
    "guala.owner_free.materialized_fabric.reference.v4"
)
LEGACY_MATERIALIZED_FABRIC_REFERENCE_SCHEMA = (
    "guala.owner_free.materialized_fabric.reference.v2"
)
PRIOR_MATERIALIZED_FABRIC_REFERENCE_SCHEMA = (
    "guala.owner_free.materialized_fabric.reference.v3"
)
MATERIALIZED_FABRIC_PERSISTENCE_SCHEMA = (
    "guala.native.materialized_fabric.persistence.v1"
)
MATERIALIZED_FABRIC_PERSISTENCE_KEYS = frozenset({
    "reference",
    "schema",
    "state_base64",
    "state_sha256",
})
MATERIALIZED_FABRIC_REFERENCE_KEYS = frozenset({
    "byte_count",
    "episode_relation_candidate_sha256",
    "evidence_count",
    "joint_field_count",
    "joint_neuron_count",
    "joint_transition_sha256",
    "materialized_body_count",
    "materialized_neuron_count",
    "mosaic_count",
    "mosaic_sha256",
    "outcome",
    "recurrent_fractal_count",
    "schema",
    "state_sha256",
    "transitioned_fractal_count",
})
PRIOR_MATERIALIZED_FABRIC_REFERENCE_KEYS = (
    MATERIALIZED_FABRIC_REFERENCE_KEYS
    - {"episode_relation_candidate_sha256"}
)
LEGACY_MATERIALIZED_FABRIC_REFERENCE_KEYS = frozenset({
    "byte_count",
    "evidence_count",
    "materialized_body_count",
    "materialized_neuron_count",
    "mosaic_count",
    "mosaic_sha256",
    "outcome",
    "schema",
    "state_sha256",
})
MATERIALIZED_FABRIC_OUTCOMES = frozenset({
    "joint_field_not_reached",
    "joint_neuronal_state_restored",
    "joint_neuronal_fractals_transitioned",
})
_HEX = frozenset("0123456789abcdef")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} is not a canonical SHA-256")
    return value


def _nonnegative(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} is not a nonnegative integer")
    return value


def extract_authenticated_predecessor_fabric_bytes(value: object) -> bytes:
    """Extract only authenticated native bytes from a predecessor record.

    This boundary is intentionally weaker than current-state restoration only
    in one respect: predecessor mosaic/neuron/body claims are neither parsed
    nor accepted. They are discarded. Exact record shape, canonical bytes,
    byte count, and both SHA-256 roots must still agree before the native
    one-way decoder receives the state.
    """
    if (
        not isinstance(value, dict)
        or set(value) != MATERIALIZED_FABRIC_PERSISTENCE_KEYS
        or value.get("schema") != MATERIALIZED_FABRIC_PERSISTENCE_SCHEMA
    ):
        raise ValueError("predecessor fabric persistence surface changed")
    reference = value.get("reference")
    if not isinstance(reference, dict):
        raise ValueError("predecessor fabric reference surface changed")
    schema = reference.get("schema")
    expected_keys = {
        LEGACY_MATERIALIZED_FABRIC_REFERENCE_SCHEMA: (
            LEGACY_MATERIALIZED_FABRIC_REFERENCE_KEYS
        ),
        PRIOR_MATERIALIZED_FABRIC_REFERENCE_SCHEMA: (
            PRIOR_MATERIALIZED_FABRIC_REFERENCE_KEYS
        ),
        MATERIALIZED_FABRIC_REFERENCE_SCHEMA: (
            MATERIALIZED_FABRIC_REFERENCE_KEYS
        ),
    }.get(schema)
    if expected_keys is None or set(reference) != expected_keys:
        raise ValueError("predecessor fabric reference schema changed")
    state_sha256 = _require_sha256(
        reference.get("state_sha256"),
        "predecessor materialized fabric state",
    )
    byte_count = _nonnegative(
        reference.get("byte_count"),
        "predecessor materialized fabric byte count",
    )
    if byte_count == 0:
        raise ValueError("predecessor materialized fabric state is empty")
    encoded = value.get("state_base64")
    if not isinstance(encoded, str) or not encoded:
        raise ValueError("predecessor fabric persistence bytes are absent")
    try:
        state_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, base64.binascii.Error) as error:
        raise ValueError(
            "predecessor fabric persistence bytes are invalid"
        ) from error
    if base64.b64encode(state_bytes).decode("ascii") != encoded:
        raise ValueError(
            "predecessor fabric persistence encoding is not canonical"
        )
    if (
        len(state_bytes) != byte_count
        or _sha256(state_bytes) != state_sha256
        or value.get("state_sha256") != state_sha256
    ):
        raise ValueError("predecessor fabric bytes changed their custody")
    return state_bytes


@dataclass(frozen=True, slots=True)
class MaterializedFabricReference:
    state_sha256: str
    byte_count: int
    outcome: str
    mosaic_sha256: str | None
    mosaic_count: int
    materialized_neuron_count: int
    materialized_body_count: int
    evidence_count: int
    joint_field_count: int = 0
    joint_neuron_count: int = 0
    transitioned_fractal_count: int = 0
    recurrent_fractal_count: int = 0
    joint_transition_sha256: str | None = None
    episode_relation_candidate_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_sha256(self.state_sha256, "materialized fabric state")
        _nonnegative(self.byte_count, "materialized fabric byte count")
        if self.byte_count == 0:
            raise ValueError("materialized fabric state is empty")
        if self.outcome not in MATERIALIZED_FABRIC_OUTCOMES:
            raise ValueError("materialized fabric outcome changed")
        if self.mosaic_sha256 is not None:
            raise ValueError(
                "evidence-only native fabric cannot claim a mosaic"
            )
        for value, label in (
            (self.mosaic_count, "mosaic count"),
            (self.materialized_neuron_count, "materialized neuron count"),
            (self.materialized_body_count, "materialized body count"),
            (self.evidence_count, "materialized evidence count"),
            (self.joint_field_count, "joint field count"),
            (self.joint_neuron_count, "joint neuron count"),
            (
                self.transitioned_fractal_count,
                "transitioned neuronal fractal count",
            ),
            (
                self.recurrent_fractal_count,
                "recurrent neuronal fractal count",
            ),
        ):
            _nonnegative(value, label)
        if self.recurrent_fractal_count > self.transitioned_fractal_count:
            raise ValueError("joint recurrence exceeds transitioned fractals")
        if self.transitioned_fractal_count > self.joint_neuron_count:
            raise ValueError("joint transition exceeds mounted neurons")
        if self.joint_field_count == 0:
            if (
                self.transitioned_fractal_count != 0
                or self.recurrent_fractal_count != 0
                or self.joint_transition_sha256 is not None
            ):
                raise ValueError("empty joint field reports a transition")
        elif self.joint_transition_sha256 is None:
            raise ValueError("mounted joint field lacks its transition receipt")
        if self.joint_transition_sha256 is not None:
            _require_sha256(
                self.joint_transition_sha256,
                "joint neuronal transition",
            )
        if self.episode_relation_candidate_sha256 is not None:
            _require_sha256(
                self.episode_relation_candidate_sha256,
                "cross-clock episode relation candidate",
            )
            if self.joint_field_count < 2:
                raise ValueError(
                    "episode relation candidate lacks two exact-clock fields"
                )
        if (
            self.mosaic_count != 0
            or self.materialized_neuron_count != 0
            or self.materialized_body_count != 0
        ):
            raise ValueError(
                "evidence-only native fabric cannot materialize legacy "
                "mosaics, neurons, or bodies"
            )

    def record(self) -> dict[str, str | int | None]:
        return {
            "byte_count": self.byte_count,
            "evidence_count": self.evidence_count,
            "episode_relation_candidate_sha256": (
                self.episode_relation_candidate_sha256
            ),
            "joint_field_count": self.joint_field_count,
            "joint_neuron_count": self.joint_neuron_count,
            "joint_transition_sha256": self.joint_transition_sha256,
            "materialized_body_count": self.materialized_body_count,
            "materialized_neuron_count": self.materialized_neuron_count,
            "mosaic_count": self.mosaic_count,
            "mosaic_sha256": self.mosaic_sha256,
            "outcome": self.outcome,
            "recurrent_fractal_count": self.recurrent_fractal_count,
            "schema": MATERIALIZED_FABRIC_REFERENCE_SCHEMA,
            "state_sha256": self.state_sha256,
            "transitioned_fractal_count": (
                self.transitioned_fractal_count
            ),
        }

    @classmethod
    def from_record(cls, value: object) -> "MaterializedFabricReference":
        if not isinstance(value, dict):
            raise ValueError("materialized fabric reference surface changed")
        legacy = (
            set(value) == LEGACY_MATERIALIZED_FABRIC_REFERENCE_KEYS
            and value.get("schema")
            == LEGACY_MATERIALIZED_FABRIC_REFERENCE_SCHEMA
        )
        current = (
            set(value) == MATERIALIZED_FABRIC_REFERENCE_KEYS
            and value.get("schema") == MATERIALIZED_FABRIC_REFERENCE_SCHEMA
        )
        prior = (
            set(value) == PRIOR_MATERIALIZED_FABRIC_REFERENCE_KEYS
            and value.get("schema")
            == PRIOR_MATERIALIZED_FABRIC_REFERENCE_SCHEMA
        )
        if not legacy and not prior and not current:
            raise ValueError("materialized fabric reference schema changed")
        return cls(
            state_sha256=value["state_sha256"],
            byte_count=value["byte_count"],
            outcome=value["outcome"],
            mosaic_sha256=value["mosaic_sha256"],
            mosaic_count=value["mosaic_count"],
            materialized_neuron_count=value["materialized_neuron_count"],
            materialized_body_count=value["materialized_body_count"],
            evidence_count=value["evidence_count"],
            joint_field_count=(
                value["joint_field_count"] if current or prior else 0
            ),
            joint_neuron_count=(
                value["joint_neuron_count"] if current or prior else 0
            ),
            transitioned_fractal_count=(
                value["transitioned_fractal_count"]
                if current or prior else 0
            ),
            recurrent_fractal_count=(
                value["recurrent_fractal_count"]
                if current or prior else 0
            ),
            joint_transition_sha256=(
                value["joint_transition_sha256"]
                if current or prior else None
            ),
            episode_relation_candidate_sha256=(
                value["episode_relation_candidate_sha256"]
                if current else None
            ),
        )


@dataclass(frozen=True, slots=True)
class VerifiedMaterializedFabricTransition:
    reference: MaterializedFabricReference
    state_bytes: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.reference, MaterializedFabricReference):
            raise TypeError("materialized fabric reference is not typed")
        if not isinstance(self.state_bytes, bytes):
            raise TypeError("materialized fabric state must be immutable bytes")
        if (
            len(self.state_bytes) != self.reference.byte_count
            or _sha256(self.state_bytes) != self.reference.state_sha256
        ):
            raise ValueError(
                "materialized fabric bytes changed their reference"
            )

    @classmethod
    def from_native(
        cls,
        value: ImmutableMaterializedFabricTransition,
    ) -> "VerifiedMaterializedFabricTransition":
        if not isinstance(value, ImmutableMaterializedFabricTransition):
            raise TypeError("materialized fabric transition is not native")
        if value.schema != MATERIALIZED_FABRIC_SCHEMA:
            raise ValueError("native materialized fabric schema changed")
        if value.python_callback_count != 0:
            raise ValueError(
                "native materialized fabric called back into Python"
            )
        state_bytes = bytes(value.as_bytes())
        reference = MaterializedFabricReference(
            state_sha256=value.state_sha256,
            byte_count=len(state_bytes),
            outcome=value.outcome,
            mosaic_sha256=value.mosaic_sha256,
            mosaic_count=value.mosaic_count,
            materialized_neuron_count=value.materialized_neuron_count,
            materialized_body_count=value.materialized_body_count,
            evidence_count=value.evidence_count,
            joint_field_count=value.joint_field_count,
            joint_neuron_count=value.joint_neuron_count,
            transitioned_fractal_count=(
                value.transitioned_fractal_count
            ),
            recurrent_fractal_count=value.recurrent_fractal_count,
            joint_transition_sha256=value.joint_transition_sha256,
            episode_relation_candidate_sha256=(
                value.episode_relation_candidate_sha256
            ),
        )
        return cls(reference=reference, state_bytes=state_bytes)

    def content_payload(self) -> tuple[str, bytes]:
        return self.reference.state_sha256, self.state_bytes

    def persistence_record(self) -> dict[str, object]:
        return {
            "reference": self.reference.record(),
            "schema": MATERIALIZED_FABRIC_PERSISTENCE_SCHEMA,
            "state_base64": base64.b64encode(self.state_bytes).decode("ascii"),
            "state_sha256": self.reference.state_sha256,
        }

    @classmethod
    def from_persistence_record(
        cls,
        value: object,
    ) -> "VerifiedMaterializedFabricTransition":
        if (
            not isinstance(value, dict)
            or set(value) != MATERIALIZED_FABRIC_PERSISTENCE_KEYS
            or value.get("schema") != MATERIALIZED_FABRIC_PERSISTENCE_SCHEMA
        ):
            raise ValueError("materialized fabric persistence surface changed")
        reference = MaterializedFabricReference.from_record(value["reference"])
        encoded = value["state_base64"]
        if not isinstance(encoded, str) or not encoded:
            raise ValueError("materialized fabric persistence bytes are absent")
        try:
            state_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as error:
            raise ValueError(
                "materialized fabric persistence bytes are invalid"
            ) from error
        if base64.b64encode(state_bytes).decode("ascii") != encoded:
            raise ValueError(
                "materialized fabric persistence encoding is not canonical"
            )
        if value["state_sha256"] != reference.state_sha256:
            raise ValueError(
                "materialized fabric persistence root changed"
            )
        return cls(reference=reference, state_bytes=state_bytes)


__all__ = (
    "MATERIALIZED_FABRIC_OUTCOMES",
    "MATERIALIZED_FABRIC_REFERENCE_KEYS",
    "MATERIALIZED_FABRIC_REFERENCE_SCHEMA",
    "MATERIALIZED_FABRIC_PERSISTENCE_KEYS",
    "MATERIALIZED_FABRIC_PERSISTENCE_SCHEMA",
    "MATERIALIZED_FABRIC_SCHEMA",
    "MaterializedFabricReference",
    "VerifiedMaterializedFabricTransition",
    "extract_authenticated_predecessor_fabric_bytes",
)
