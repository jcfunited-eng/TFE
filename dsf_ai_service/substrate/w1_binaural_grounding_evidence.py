"""Authenticated W1 grounding evidence from one atomic two-ear episode.

This is the binaural sibling of the older mono grounding intake.  It does not
assign meaning or produce a cue by itself.  It proves only that:

* a verified recurrent q firing was recomputed from one exact two-ear receptor
  settlement;
* the receptor settlement and the non-auditory roots came from the same
  six-sense causal settlement;
* every retained activation preserves its ear identity, exact causal span,
  and complete D/M/R/U/C/P/B occurrence records; and
* at least one non-auditory physical substream was genuinely observed.

Sound-only self hearing therefore cannot masquerade as a grounded referent.
No transcript, label, object lookup, score, vote, threshold, or reduced field
is admitted.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    GroundingRoot,
    grounding_roots_from_settlement,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AUDITORY_RECEPTOR_OCCURRENCE_SCHEMA,
    AuditoryBinauralMotifFiring,
    AuditoryMotifActivation,
    AuditoryMotifObservationState,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.w1_binaural_receptor_settlement import (
    W1BinauralReceptorSettlement,
)


W1_BINAURAL_GROUNDING_PROFILE_SCHEMA = (
    "guala.w1.binaural_grounding_evidence.profile.v1"
)
W1_BINAURAL_ACTIVATION_EVIDENCE_SCHEMA = (
    "guala.w1.binaural_grounding_activation.v1"
)
W1_BINAURAL_GROUNDING_EVIDENCE_SCHEMA = (
    "guala.w1.binaural_grounding_evidence.v1"
)
W1_BINAURAL_GROUNDING_DOMAIN = (
    b"guala-w1-binaural-grounding-evidence-v1\0"
)
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("W1 binaural grounding key must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError("W1 binaural grounding key boundary changed")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("W1 binaural grounding time must be exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{name} is not an exact fraction") from error
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not canonical")
    return result


@dataclass(frozen=True, slots=True)
class W1BinauralGroundingResourceProfile:
    profile_id: str
    max_activations: int
    max_roots: int
    max_evidence_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_activations: int,
        max_roots: int,
        max_evidence_bytes: int,
    ) -> "W1BinauralGroundingResourceProfile":
        if (
            not isinstance(profile_id, str)
            or not profile_id
            or profile_id != profile_id.strip()
            or len(profile_id.encode("utf-8")) > 512
        ):
            raise ValueError(
                "W1 binaural grounding profile identifier changed"
            )
        provisional = cls(
            profile_id=profile_id,
            max_activations=_positive(
                max_activations, "W1 grounding activation capacity"
            ),
            max_roots=_positive(
                max_roots, "W1 grounding root capacity"
            ),
            max_evidence_bytes=_positive(
                max_evidence_bytes, "W1 grounding evidence bytes"
            ),
            authority_receipt_sha256="0" * 64,
        )
        return cls(
            profile_id=provisional.profile_id,
            max_activations=provisional.max_activations,
            max_roots=provisional.max_roots,
            max_evidence_bytes=provisional.max_evidence_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_activations": self.max_activations,
            "max_evidence_bytes": self.max_evidence_bytes,
            "max_roots": self.max_roots,
            "profile_id": self.profile_id,
            "schema": W1_BINAURAL_GROUNDING_PROFILE_SCHEMA,
        }

    def verify(self) -> None:
        _positive(
            self.max_activations, "W1 grounding activation capacity"
        )
        _positive(self.max_roots, "W1 grounding root capacity")
        _positive(
            self.max_evidence_bytes, "W1 grounding evidence bytes"
        )
        _sha256(
            self.authority_receipt_sha256,
            "W1 grounding profile authority",
        )
        if self.authority_receipt_sha256 != _digest(self.payload()):
            raise ValueError("W1 binaural grounding profile changed")


def _occurrence_record(value) -> dict[str, object]:
    value.verify()
    return value.payload() | {
        "authority_receipt_sha256": value.authority_receipt_sha256
    }


def _activation_record(
    activation: AuditoryMotifActivation,
) -> dict[str, object]:
    return {
        "ear_id": activation.ear_id,
        "full_field_occurrences": [
            _occurrence_record(value)
            for value in activation.full_field_occurrences
        ],
        "neuron_id": activation.neuron_id,
        "schema": W1_BINAURAL_ACTIVATION_EVIDENCE_SCHEMA,
        "segment_index": activation.segment_index,
        "source_index_end": activation.source_index_end,
        "source_index_start": activation.source_index_start,
        "source_time_end": _fraction_text(
            activation.source_time_end
        ),
        "source_time_start": _fraction_text(
            activation.source_time_start
        ),
        "state_ordinal_end": activation.state_ordinal_end,
        "state_ordinal_start": activation.state_ordinal_start,
    }


def _validate_occurrence(value: object) -> None:
    if (
        not isinstance(value, dict)
        or value.get("schema") != AUDITORY_RECEPTOR_OCCURRENCE_SCHEMA
        or value.get("pressure_basin") != "authoritative_upper"
        or set(value) != {
            "authority_receipt_sha256",
            "causal_interval_end",
            "phase_field_receipt_sha256",
            "phase_fields",
            "pressure_basin",
            "pressure_field_receipt_sha256",
            "pressure_fields",
            "receptor",
            "schema",
            "source_index",
            "source_time",
            "winding_delta",
        }
    ):
        raise ValueError(
            "W1 binaural grounding occurrence structure changed"
        )
    for field_name in ("pressure_fields", "phase_fields"):
        fields = value.get(field_name)
        if (
            not isinstance(fields, list)
            or tuple(
                item[0]
                for item in fields
                if isinstance(item, list) and len(item) == 2
            ) != DSF_FIELD_ORDER
        ):
            raise ValueError(
                "W1 binaural grounding lost explicit DSF field order"
            )
        for expected, item in zip(
            DSF_FIELD_ORDER, fields, strict=True
        ):
            if (
                not isinstance(item, list)
                or len(item) != 2
                or item[0] != expected
            ):
                raise ValueError(
                    "W1 binaural grounding lost explicit DSF field"
                )
            _fraction(
                item[1],
                f"W1 binaural grounding {field_name} {expected}",
            )
    for field_name in (
        "authority_receipt_sha256",
        "phase_field_receipt_sha256",
        "pressure_field_receipt_sha256",
    ):
        _sha256(
            value.get(field_name),
            f"W1 binaural grounding {field_name}",
        )
    payload = {
        key: item
        for key, item in value.items()
        if key != "authority_receipt_sha256"
    }
    if _digest(payload) != value["authority_receipt_sha256"]:
        raise ValueError(
            "W1 binaural grounding occurrence authority changed"
        )


@dataclass(frozen=True, slots=True)
class W1BinauralActivationEvidence:
    ear_id: str
    neuron_id: str
    activation_json: str
    authority_receipt_sha256: str

    @classmethod
    def from_activation(
        cls,
        activation: AuditoryMotifActivation,
    ) -> "W1BinauralActivationEvidence":
        record = _activation_record(activation)
        result = cls(
            ear_id=activation.ear_id,
            neuron_id=activation.neuron_id,
            activation_json=_canonical(record).decode("utf-8"),
            authority_receipt_sha256=_digest(record),
        )
        result.verify()
        return result

    def verify(self) -> None:
        if self.ear_id not in ("left", "right"):
            raise ValueError(
                "W1 binaural grounding activation lost ear identity"
            )
        _sha256(
            self.neuron_id, "W1 binaural grounding activation neuron"
        )
        _sha256(
            self.authority_receipt_sha256,
            "W1 binaural grounding activation",
        )
        if not isinstance(self.activation_json, str):
            raise ValueError(
                "W1 binaural grounding activation is not canonical JSON"
            )
        try:
            record = json.loads(self.activation_json)
        except json.JSONDecodeError as error:
            raise ValueError(
                "W1 binaural grounding activation is unreadable"
            ) from error
        if (
            _canonical(record).decode("utf-8") != self.activation_json
            or not isinstance(record, dict)
            or set(record) != {
                "ear_id",
                "full_field_occurrences",
                "neuron_id",
                "schema",
                "segment_index",
                "source_index_end",
                "source_index_start",
                "source_time_end",
                "source_time_start",
                "state_ordinal_end",
                "state_ordinal_start",
            }
            or record.get("schema")
            != W1_BINAURAL_ACTIVATION_EVIDENCE_SCHEMA
            or record.get("ear_id") != self.ear_id
            or record.get("neuron_id") != self.neuron_id
            or not isinstance(
                record.get("full_field_occurrences"), list
            )
            or not record["full_field_occurrences"]
        ):
            raise ValueError(
                "W1 binaural grounding activation changed"
            )
        for occurrence in record["full_field_occurrences"]:
            _validate_occurrence(occurrence)
        start = _fraction(
            record.get("source_time_start"),
            "W1 binaural grounding activation start",
        )
        end = _fraction(
            record.get("source_time_end"),
            "W1 binaural grounding activation end",
        )
        if (
            end <= start
            or _digest(record) != self.authority_receipt_sha256
        ):
            raise ValueError(
                "W1 binaural grounding activation authority changed"
            )

    def record(self) -> dict[str, str]:
        self.verify()
        return {
            "activation_json": self.activation_json,
            "authority_receipt_sha256": (
                self.authority_receipt_sha256
            ),
            "ear_id": self.ear_id,
            "neuron_id": self.neuron_id,
        }


@dataclass(frozen=True, slots=True)
class W1BinauralGroundingEvidence:
    episode_id: str
    causal_settlement_receipt_sha256: str
    receptor_settlement_receipt_sha256: str
    binaural_firing_receipt_sha256: str
    activations: tuple[W1BinauralActivationEvidence, ...]
    roots: tuple[GroundingRoot, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "activations": [
                value.record() for value in self.activations
            ],
            "binaural_firing_receipt_sha256": (
                self.binaural_firing_receipt_sha256
            ),
            "causal_settlement_receipt_sha256": (
                self.causal_settlement_receipt_sha256
            ),
            "receptor_settlement_receipt_sha256": (
                self.receptor_settlement_receipt_sha256
            ),
            "roots": [value.as_record() for value in self.roots],
            "schema": W1_BINAURAL_GROUNDING_EVIDENCE_SCHEMA,
        }

    def verify(
        self,
        authority_key: bytes | str,
        profile: W1BinauralGroundingResourceProfile,
    ) -> None:
        key = _key(authority_key)
        profile.verify()
        for value, name in (
            (self.episode_id, "W1 binaural grounding episode"),
            (
                self.causal_settlement_receipt_sha256,
                "W1 binaural grounding settlement",
            ),
            (
                self.receptor_settlement_receipt_sha256,
                "W1 binaural grounding receptors",
            ),
            (
                self.binaural_firing_receipt_sha256,
                "W1 binaural grounding firing",
            ),
            (
                self.authority_hmac_sha256,
                "W1 binaural grounding HMAC",
            ),
            (
                self.authority_receipt_sha256,
                "W1 binaural grounding authority",
            ),
        ):
            _sha256(value, name)
        if (
            not self.activations
            or len(self.activations) > profile.max_activations
            or not self.roots
            or len(self.roots) > profile.max_roots
            or tuple(
                sorted(
                    self.roots,
                    key=lambda item: (
                        item.root_id, item.value_sha256
                    ),
                )
            ) != self.roots
        ):
            raise ValueError(
                "W1 binaural grounding evidence capacity changed"
            )
        for value in self.activations:
            value.verify()
        for value in self.roots:
            value.verify()
        payload = self.payload()
        signature = hmac.new(
            key,
            W1_BINAURAL_GROUNDING_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            self.episode_id != _digest({
                "binaural_firing_receipt_sha256": (
                    self.binaural_firing_receipt_sha256
                ),
                "causal_settlement_receipt_sha256": (
                    self.causal_settlement_receipt_sha256
                ),
            })
            or len(_canonical(payload)) > profile.max_evidence_bytes
            or not hmac.compare_digest(
                signature, self.authority_hmac_sha256
            )
            or self.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ):
            raise ValueError(
                "W1 binaural grounding evidence authority changed"
            )


class W1BinauralGroundingEvidenceAuthority:
    """Admit bounded full-field evidence without assigning a referent."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        resource_profile: W1BinauralGroundingResourceProfile,
    ) -> None:
        resource_profile.verify()
        self._key = _key(authority_key)
        self._profile = resource_profile

    def admit(
        self,
        *,
        settlement: CausalExperienceSettlement,
        receptor_settlement: W1BinauralReceptorSettlement,
        firing: AuditoryBinauralMotifFiring,
        motif_owner: AuditoryRecurrentMotifOwner,
    ) -> W1BinauralGroundingEvidence:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError(
                "W1 binaural grounding requires exact causal settlement"
            )
        if not isinstance(
            receptor_settlement, W1BinauralReceptorSettlement
        ):
            raise TypeError(
                "W1 binaural grounding requires two-ear receptors"
            )
        if not isinstance(firing, AuditoryBinauralMotifFiring):
            raise TypeError(
                "W1 binaural grounding requires two-ear q firing"
            )
        if not isinstance(motif_owner, AuditoryRecurrentMotifOwner):
            raise TypeError(
                "W1 binaural grounding requires recurrent q authority"
            )
        settlement.verify()
        receptor_settlement.verify()
        firing.verify()
        recomputed = motif_owner.fire_binaural(
            receptor_settlement
        )
        if recomputed != firing:
            raise ValueError(
                "W1 binaural grounding firing is not current q authority"
            )
        observed_nonauditory = tuple(
            value
            for value in settlement.interpretations
            if (
                value.sense != "sound"
                and value.state == "observed"
                and value.substreams
            )
        )
        if not observed_nonauditory:
            raise ValueError(
                "W1 binaural grounding requires observed non-auditory field"
            )
        if (
            firing.firing.state
            is not AuditoryMotifObservationState.OBSERVED
            or not firing.activations
            or receptor_settlement.upstream_w1_l5
            .upstream_causal_settlement_receipt_sha256
            != settlement.authority_receipt_sha256
            or receptor_settlement.assembly_id != settlement.assembly_id
            or firing.source_settlement_receipt_sha256
            != receptor_settlement.authority_receipt_sha256
        ):
            raise ValueError(
                "W1 binaural grounding transaction link changed"
            )
        activations = tuple(
            W1BinauralActivationEvidence.from_activation(value)
            for value in firing.activations
        )
        roots = grounding_roots_from_settlement(settlement)
        if (
            len(activations) > self._profile.max_activations
            or len(roots) > self._profile.max_roots
        ):
            raise RuntimeError(
                "W1 binaural grounding resource capacity exhausted"
            )
        payload = {
            "activations": [
                value.record() for value in activations
            ],
            "binaural_firing_receipt_sha256": (
                firing.authority_receipt_sha256
            ),
            "causal_settlement_receipt_sha256": (
                settlement.authority_receipt_sha256
            ),
            "receptor_settlement_receipt_sha256": (
                receptor_settlement.authority_receipt_sha256
            ),
            "roots": [value.as_record() for value in roots],
            "schema": W1_BINAURAL_GROUNDING_EVIDENCE_SCHEMA,
        }
        if len(_canonical(payload)) > self._profile.max_evidence_bytes:
            raise RuntimeError(
                "W1 binaural grounding byte capacity exhausted"
            )
        signature = hmac.new(
            self._key,
            W1_BINAURAL_GROUNDING_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = W1BinauralGroundingEvidence(
            episode_id=_digest({
                "binaural_firing_receipt_sha256": (
                    firing.authority_receipt_sha256
                ),
                "causal_settlement_receipt_sha256": (
                    settlement.authority_receipt_sha256
                ),
            }),
            causal_settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            receptor_settlement_receipt_sha256=(
                receptor_settlement.authority_receipt_sha256
            ),
            binaural_firing_receipt_sha256=(
                firing.authority_receipt_sha256
            ),
            activations=activations,
            roots=roots,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result.verify(self._key, self._profile)
        return result

    def verify(
        self,
        evidence: W1BinauralGroundingEvidence,
    ) -> None:
        if not isinstance(evidence, W1BinauralGroundingEvidence):
            raise TypeError("W1 binaural grounding evidence is not typed")
        evidence.verify(self._key, self._profile)


__all__ = [
    "W1BinauralActivationEvidence",
    "W1BinauralGroundingEvidence",
    "W1BinauralGroundingEvidenceAuthority",
    "W1BinauralGroundingResourceProfile",
]
