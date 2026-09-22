"""Bounded exact whole-organism structural-state transfer authority.

This owner begins at the mounted manifest's true uncommitted zero.  It then
accepts only settled :class:`WholeOrganismEpisodeCapability` values revalidated
by the authority that owns the complete episode.

Episode provenance and structural state are deliberately separate:

* provenance authenticates where, when, and under which custody the state was
  observed; and
* structural identity retains every ordered D/M/R/U/C/P/B tuple and every
  typed mounted-mechanism state without using episode wrappers as identity.

Consequently, two distinct episodes carrying the same complete structural
state produce ``no_durable_change``.  A change to any exact field coordinate,
root topology, or mechanism state produces ``changed``.  No mechanism name is
interpreted as a cognitive form, promotion, score, or threshold.

The retained state is bounded to one current receipt and at most one in-flight
transfer.  Completed transfers are not accumulated.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.causal_thing_mosaic import FullFieldSensoryRoot
from dsf_ai_service.substrate.whole_organism_episode import (
    ContributionState,
    DownstreamAuthority,
    L6Disposition,
    MechanismAvailability,
    MechanismKind,
    MountedMechanismSpec,
    WholeOrganismEpisodeAuthority,
    WholeOrganismEpisodeCapability,
    WholeOrganismEpisodeRecord,
    WholeOrganismMechanismContribution,
)


STRUCTURAL_IDENTITY_SCHEMA = (
    "guala.whole_organism.structural_identity.v2"
)
STRUCTURAL_PROVENANCE_SCHEMA = (
    "guala.whole_organism.structural_provenance.v2"
)
STRUCTURAL_STATE_SCHEMA = (
    "guala.whole_organism.structural_state_receipt.v2"
)
TRANSFER_SCHEMA = "guala.whole_organism.structural_transfer.v2"
COMMIT_SCHEMA = "guala.whole_organism.structural_transfer_commit.v2"
OWNER_STATE_SCHEMA = (
    "guala.whole_organism.structural_perturbation_state.v2"
)
OWNER_STATE_ENVELOPE_SCHEMA = (
    "guala.whole_organism.structural_perturbation_state_hmac.v2"
)

_STRUCTURAL_STATE_DOMAIN = b"guala-whole-structural-state-v2\0"
_TRANSFER_DOMAIN = b"guala-whole-structural-transfer-v2\0"
_COMMIT_DOMAIN = b"guala-whole-structural-transfer-commit-v2\0"
_OWNER_STATE_DOMAIN = b"guala-whole-structural-owner-state-v2\0"

MAX_OWNER_STATE_BYTES = 16 * 1024 * 1024
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
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError(
            "whole-organism structural perturbation authority key is invalid"
        )
    return raw


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 identity")
    return value


def _identifier(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > 256
    ):
        raise ValueError(f"{label} is not a bounded canonical identifier")
    return value


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("whole-organism source time is not exact")
    return f"{value.numerator}/{value.denominator}"


def _verify_fraction_text(value: object, label: str) -> str:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{label} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    try:
        exact = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(f"{label} is not an exact fraction") from error
    if _fraction_text(exact) != value:
        raise ValueError(f"{label} is not canonical")
    return value


def _canonical_mapping_json(value: object, label: str) -> str:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} is not a mapping")
    try:
        encoded = _canonical(dict(value))
        decoded = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not canonical JSON") from error
    if not isinstance(decoded, dict):
        raise ValueError(f"{label} is not a canonical mapping")
    return encoded.decode("utf-8")


def _verified_mapping_json(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, str):
        raise ValueError(f"{label} is not canonical JSON text")
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is unreadable") from error
    if (
        not isinstance(decoded, dict)
        or _canonical(decoded).decode("utf-8") != value
    ):
        raise ValueError(f"{label} is not a canonical mapping")
    return decoded


def _verified_state_json(value: object, label: str) -> object:
    if not isinstance(value, str):
        raise ValueError(f"{label} is not canonical JSON text")
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is unreadable") from error
    if (
        not isinstance(decoded, (dict, list))
        or _canonical(decoded).decode("utf-8") != value
    ):
        raise ValueError(f"{label} is not canonical structured state")
    return decoded


def _root_structural_state(root: FullFieldSensoryRoot) -> dict[str, object]:
    """Return the complete non-provenance structural state of one root."""

    if not isinstance(root, FullFieldSensoryRoot):
        raise TypeError("whole-organism structural root is not typed")
    evidence = root.verified_evidence()
    raw_tuples = evidence.get("field_tuples")
    if not isinstance(raw_tuples, list) or not raw_tuples:
        raise ValueError("whole-organism root lost its full field")
    field_tuples: list[dict[str, object]] = []
    for tuple_index, item in enumerate(raw_tuples):
        if not isinstance(item, dict):
            raise ValueError("whole-organism field tuple is not a mapping")
        raw_fields = item.get("fields")
        if (
            not isinstance(raw_fields, list)
            or len(raw_fields) != len(DSF_FIELD_ORDER)
            or tuple(
                value[0]
                for value in raw_fields
                if isinstance(value, list) and len(value) == 2
            )
            != DSF_FIELD_ORDER
        ):
            raise ValueError(
                "whole-organism root flattened or reordered its DSF field"
            )
        fields: list[list[str]] = [
            [field_name, field_value]
            for field_name, field_value in raw_fields
        ]
        for name in ("source_index_start", "source_index_end", "tuple_index"):
            value = item.get(name)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(
                    f"whole-organism structural root {name} changed"
                )
        if item["tuple_index"] != tuple_index:
            raise ValueError(
                "whole-organism structural root tuple order changed"
            )
        if item["source_index_end"] < item["source_index_start"]:
            raise ValueError(
                "whole-organism structural root interval changed"
            )
        field_tuples.append({
            "fields": fields,
            "source_index_end": item["source_index_end"],
            "source_index_start": item["source_index_start"],
            "tuple_index": item["tuple_index"],
        })
    coordinates = evidence.get("coordinates")
    if (
        not isinstance(coordinates, list)
        or any(
            not isinstance(value, list)
            or len(value) != 2
            or any(not isinstance(part, str) or not part for part in value)
            for value in coordinates
        )
    ):
        raise ValueError(
            "whole-organism structural root coordinates changed"
        )
    sample_count = evidence.get("source_sample_count")
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or sample_count <= 0
    ):
        raise ValueError(
            "whole-organism structural root sample count changed"
        )
    result: dict[str, object] = {
        "boundary_state": _identifier(
            evidence.get("boundary_state"),
            "whole-organism root boundary state",
        ),
        "coordinates": coordinates,
        "field_tuples": field_tuples,
        "physical_quantity": _identifier(
            evidence.get("physical_quantity"),
            "whole-organism root physical quantity",
        ),
        "physical_unit": _identifier(
            evidence.get("physical_unit"),
            "whole-organism root physical unit",
        ),
        "physical_value_sha256": _sha(
            root.physical_value_sha256,
            "whole-organism root physical identity",
        ),
        "sense": _identifier(root.sense, "whole-organism root sense"),
        "source_sample_count": sample_count,
        "topology_index": root.topology_index,
    }
    if root.sense == "sight":
        result["source_signal_commitment_sha256"] = _sha(
            evidence.get("source_signal_commitment_sha256"),
            "whole-organism sight excitation",
        )
    return result


def _root_state_receipt(root_state: Mapping[str, object]) -> str:
    return _digest({
        "root_state": dict(root_state),
        "schema": STRUCTURAL_IDENTITY_SCHEMA,
    })


def _mechanism_zero_state(
    spec: MountedMechanismSpec,
) -> dict[str, object]:
    if spec.availability is MechanismAvailability.UNAVAILABLE:
        state = ContributionState.UNAVAILABLE
        value = {
            "unavailable_reason": spec.unavailable_reason,
            "unavailable_semantics": spec.unavailable_semantics,
        }
    else:
        state = ContributionState.QUIESCENT
        value = {
            "quiescent_semantics": spec.quiescent_semantics,
        }
    return {
        "availability": spec.availability.value,
        "kind": spec.kind.value,
        "mechanism_id": spec.mechanism_id,
        "state": state.value,
        "value": value,
    }


def _mechanism_structural_state(
    *,
    spec: MountedMechanismSpec,
    contribution: WholeOrganismMechanismContribution,
    root_states: tuple[dict[str, object], ...],
) -> dict[str, object]:
    """Extract exact current mechanism state without episode provenance."""

    if not isinstance(contribution, WholeOrganismMechanismContribution):
        raise TypeError("whole-organism mechanism contribution is not typed")
    if contribution.mechanism_id != spec.mechanism_id:
        raise ValueError("whole-organism mechanism order changed")
    evidence = _verified_mapping_json(
        contribution.semantic_evidence_json,
        "whole-organism mechanism evidence",
    )
    common = {
        "availability": spec.availability.value,
        "kind": spec.kind.value,
        "mechanism_id": spec.mechanism_id,
        "state": contribution.state.value,
    }
    if spec.availability is MechanismAvailability.UNAVAILABLE:
        if contribution.state is not ContributionState.UNAVAILABLE:
            raise ValueError(
                "unavailable mounted mechanism changed structural state"
            )
        return {
            **common,
            "value": {
                "unavailable_reason": spec.unavailable_reason,
                "unavailable_semantics": spec.unavailable_semantics,
            },
        }
    matching_roots = tuple(
        value for value in root_states
        if value["sense"] == spec.sense
    )
    if spec.kind is MechanismKind.RECEPTOR_FAMILY:
        if contribution.state is ContributionState.PERTURBED:
            if not matching_roots:
                raise ValueError(
                    "perturbed receptor lost its structural roots"
                )
            value: dict[str, object] = {
                "root_structural_state_sha256s": [
                    _root_state_receipt(root) for root in matching_roots
                ],
            }
        elif contribution.state is ContributionState.QUIESCENT:
            if matching_roots:
                raise ValueError(
                    "quiescent receptor carries structural roots"
                )
            value = {
                "quiescent_semantics": spec.quiescent_semantics,
            }
        elif contribution.state is ContributionState.UNAVAILABLE:
            if matching_roots:
                raise ValueError(
                    "unavailable receptor carries structural roots"
                )
            value = {
                "unavailable_reason": (
                    spec.unavailable_reason
                    if spec.unavailable_reason is not None
                    else spec.unavailable_semantics
                ),
                "unavailable_semantics": spec.unavailable_semantics,
            }
        else:
            raise ValueError("receptor mechanism state is not lawful")
        return {**common, "value": value}
    if spec.kind is not MechanismKind.STATEFUL:
        raise ValueError("mounted mechanism kind is unsupported")
    if contribution.state is ContributionState.QUIESCENT:
        return {
            **common,
            "value": {
                "quiescent_semantics": spec.quiescent_semantics,
            },
        }
    if contribution.state is not ContributionState.PERTURBED:
        raise ValueError(
            "available stateful mechanism supplied unavailable state"
        )
    rule = evidence.get("rule")
    extra: dict[str, object] = {}
    if rule == "authenticated_before_then_after":
        current_state = _verified_state_json(
            evidence.get("after_state_json"),
            "whole-organism mechanism after state",
        )
    elif rule == "authenticated_current_state_perturbation":
        current_state = _verified_state_json(
            evidence.get("current_state_json"),
            "whole-organism mechanism current state",
        )
    elif rule == "authenticated_recovery_with_actual_n_gate":
        current_state = _verified_state_json(
            evidence.get("stable_state_json"),
            "whole-organism mechanism recovered state",
        )
        coordinates = evidence.get("l1_n_gate_coordinates")
        if not isinstance(coordinates, list) or not coordinates:
            raise ValueError(
                "whole-organism recovered mechanism lost N_gate state"
            )
        extra["l1_n_gate_coordinates"] = [
            _verify_fraction_text(
                value,
                "whole-organism recovered mechanism N_gate",
            )
            for value in coordinates
        ]
    else:
        raise ValueError(
            "whole-organism stateful mechanism evidence is unsupported"
        )
    root_receipts = (
        [_root_state_receipt(root) for root in root_states]
        if spec.binds_full_field_roots
        else []
    )
    return {
        **common,
        "value": {
            **extra,
            "current_state": current_state,
            "root_structural_state_sha256s": root_receipts,
        },
    }


@dataclass(frozen=True, slots=True)
class WholeOrganismStructuralStateReceipt:
    """Authenticated receipt with separate provenance and structural identity."""

    manifest_authority_receipt_sha256: str
    structural_state_json: str
    structural_state_sha256: str
    provenance_json: str
    provenance_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "manifest_authority_receipt_sha256": (
                self.manifest_authority_receipt_sha256
            ),
            "provenance_json": self.provenance_json,
            "provenance_sha256": self.provenance_sha256,
            "schema": STRUCTURAL_STATE_SCHEMA,
            "structural_state_json": self.structural_state_json,
            "structural_state_sha256": self.structural_state_sha256,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class PreparedWholeOrganismStructuralTransfer:
    """The sole durable in-flight journal entry and exclusive transfer lock."""

    transfer_id: str
    before_state: WholeOrganismStructuralStateReceipt
    after_state: WholeOrganismStructuralStateReceipt
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "after_state_authority_receipt_sha256": (
                self.after_state.authority_receipt_sha256
            ),
            "before_state_authority_receipt_sha256": (
                self.before_state.authority_receipt_sha256
            ),
            "schema": TRANSFER_SCHEMA,
            "transfer_id": self.transfer_id,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "after_state": self.after_state.record(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "before_state": self.before_state.record(),
        }


@dataclass(frozen=True, slots=True)
class WholeOrganismStructuralTransferCommit:
    transfer_id: str
    before_state_authority_receipt_sha256: str
    after_state_authority_receipt_sha256: str
    before_structural_state_sha256: str
    after_structural_state_sha256: str
    disposition: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "after_state_authority_receipt_sha256": (
                self.after_state_authority_receipt_sha256
            ),
            "after_structural_state_sha256": (
                self.after_structural_state_sha256
            ),
            "before_state_authority_receipt_sha256": (
                self.before_state_authority_receipt_sha256
            ),
            "before_structural_state_sha256": (
                self.before_structural_state_sha256
            ),
            "disposition": self.disposition,
            "schema": COMMIT_SCHEMA,
            "transfer_id": self.transfer_id,
        }


@dataclass(frozen=True, slots=True)
class WholeOrganismStructuralPerturbationResolution:
    state: str
    reasons: tuple[str, ...]
    prepared: PreparedWholeOrganismStructuralTransfer | None
    commit: WholeOrganismStructuralTransferCommit | None


class WholeOrganismStructuralPerturbationOwner:
    """Own one bounded, non-prescriptive whole-organism state transfer."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        episode_authority: WholeOrganismEpisodeAuthority,
        max_state_bytes: int = 256 * 1024,
    ) -> None:
        raw_key = _key(authority_key)
        if not isinstance(
            episode_authority,
            WholeOrganismEpisodeAuthority,
        ):
            raise TypeError(
                "whole-organism episode authority is not typed"
            )
        if (
            isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or not 1 <= max_state_bytes <= MAX_OWNER_STATE_BYTES
        ):
            raise ValueError(
                "whole-organism perturbation byte capacity is invalid"
            )
        self._episode_authority = episode_authority
        self._state_key = hashlib.sha256(
            _STRUCTURAL_STATE_DOMAIN + raw_key
        ).digest()
        self._transfer_key = hashlib.sha256(
            _TRANSFER_DOMAIN + raw_key
        ).digest()
        self._commit_key = hashlib.sha256(
            _COMMIT_DOMAIN + raw_key
        ).digest()
        self._owner_state_key = hashlib.sha256(
            _OWNER_STATE_DOMAIN + raw_key
        ).digest()
        self._max_state_bytes = max_state_bytes
        self._verified_state_receipts: dict[
            str,
            tuple[
                WholeOrganismStructuralStateReceipt,
                WholeOrganismEpisodeRecord | None,
            ],
        ] = {}
        self._verified_transfer: (
            PreparedWholeOrganismStructuralTransfer | None
        ) = None
        self._lock = threading.RLock()
        self._current_state = self._seal_zero_state()
        self._in_flight: (
            PreparedWholeOrganismStructuralTransfer | None
        ) = None
        self._encoded(
            current_state=self._current_state,
            in_flight=None,
        )

    @property
    def current_state(self) -> WholeOrganismStructuralStateReceipt:
        with self._lock:
            self._verify_state_receipt(self._current_state)
            return self._current_state

    @property
    def in_flight(
        self,
    ) -> PreparedWholeOrganismStructuralTransfer | None:
        with self._lock:
            if self._in_flight is not None:
                self._verify_transfer(self._in_flight)
            return self._in_flight

    def _zero_structural_payload(self) -> dict[str, object]:
        manifest = self._episode_authority.manifest
        return {
            "manifest_authority_receipt_sha256": (
                manifest.authority_receipt_sha256
            ),
            "mechanisms": [
                _mechanism_zero_state(spec)
                for spec in manifest.mechanisms
            ],
            "roots": [],
            "schema": STRUCTURAL_IDENTITY_SCHEMA,
        }

    def _zero_provenance_payload(self) -> dict[str, object]:
        return {
            "manifest_authority_receipt_sha256": (
                self._episode_authority.manifest.authority_receipt_sha256
            ),
            "origin": "mounted_uncommitted_zero",
            "schema": STRUCTURAL_PROVENANCE_SCHEMA,
        }

    def _structural_payload_from_record(
        self,
        record: WholeOrganismEpisodeRecord,
    ) -> dict[str, object]:
        if (
            record.l6_disposition is not L6Disposition.SETTLED
            or record.l6_authority_receipt_sha256 is None
        ):
            raise PermissionError(
                "whole-organism structural state lacks settled L6 custody"
            )
        manifest = self._episode_authority.manifest
        if (
            record.manifest_receipt_sha256
            != manifest.authority_receipt_sha256
            or len(record.contributions) != len(manifest.mechanisms)
            or tuple(
                value.mechanism_id for value in record.contributions
            )
            != tuple(value.mechanism_id for value in manifest.mechanisms)
        ):
            raise PermissionError(
                "whole-organism mounted manifest custody is incomplete"
            )
        roots = tuple(
            _root_structural_state(root)
            for root in record.full_field_roots
        )
        mechanisms = tuple(
            _mechanism_structural_state(
                spec=spec,
                contribution=contribution,
                root_states=roots,
            )
            for spec, contribution in zip(
                manifest.mechanisms,
                record.contributions,
                strict=True,
            )
        )
        return {
            "manifest_authority_receipt_sha256": (
                manifest.authority_receipt_sha256
            ),
            "mechanisms": list(mechanisms),
            "roots": list(roots),
            "schema": STRUCTURAL_IDENTITY_SCHEMA,
        }

    def _provenance_payload_from_record(
        self,
        record: WholeOrganismEpisodeRecord,
    ) -> dict[str, object]:
        return {
            "chain_id": record.chain_id,
            "episode_authority_receipt_sha256": (
                record.authority_receipt_sha256
            ),
            "episode_id": record.episode_id,
            "full_field_root_receipts": [
                _digest(value.record()) for value in record.full_field_roots
            ],
            "l6_authority_receipt_sha256": (
                record.l6_authority_receipt_sha256
            ),
            "manifest_authority_receipt_sha256": (
                record.manifest_receipt_sha256
            ),
            "mechanism_contribution_receipts": [
                [
                    contribution.mechanism_id,
                    contribution.authority_receipt_sha256,
                ]
                for contribution in record.contributions
            ],
            "native_evidence_transition_receipt_sha256": _digest(
                record.native_evidence_transition.record()
            ),
            "origin": "settled_whole_organism_episode",
            "phase": record.phase.value,
            "schema": STRUCTURAL_PROVENANCE_SCHEMA,
            "settlement_authority_receipt_sha256": (
                record.settlement_authority_receipt_sha256
            ),
            "settlement_event_id": record.settlement_event_id,
            "settlement_structural_fingerprint": (
                record.settlement_structural_fingerprint
            ),
            "source_time_end": _fraction_text(record.source_time_end),
            "source_time_start": _fraction_text(record.source_time_start),
        }

    def _seal_payloads(
        self,
        *,
        structural_payload: Mapping[str, object],
        provenance_payload: Mapping[str, object],
    ) -> WholeOrganismStructuralStateReceipt:
        structural_json = _canonical_mapping_json(
            structural_payload,
            "whole-organism structural identity",
        )
        provenance_json = _canonical_mapping_json(
            provenance_payload,
            "whole-organism structural provenance",
        )
        provisional = WholeOrganismStructuralStateReceipt(
            manifest_authority_receipt_sha256=(
                self._episode_authority.manifest.authority_receipt_sha256
            ),
            structural_state_json=structural_json,
            structural_state_sha256=hashlib.sha256(
                structural_json.encode("utf-8")
            ).hexdigest(),
            provenance_json=provenance_json,
            provenance_sha256=hashlib.sha256(
                provenance_json.encode("utf-8")
            ).hexdigest(),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._state_key,
            _STRUCTURAL_STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        return WholeOrganismStructuralStateReceipt(
            manifest_authority_receipt_sha256=(
                provisional.manifest_authority_receipt_sha256
            ),
            structural_state_json=provisional.structural_state_json,
            structural_state_sha256=provisional.structural_state_sha256,
            provenance_json=provisional.provenance_json,
            provenance_sha256=provisional.provenance_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )

    def _seal_zero_state(self) -> WholeOrganismStructuralStateReceipt:
        return self._seal_payloads(
            structural_payload=self._zero_structural_payload(),
            provenance_payload=self._zero_provenance_payload(),
        )

    def _seal_state(
        self,
        record: WholeOrganismEpisodeRecord,
    ) -> WholeOrganismStructuralStateReceipt:
        return self._seal_payloads(
            structural_payload=self._structural_payload_from_record(record),
            provenance_payload=self._provenance_payload_from_record(record),
        )

    def _state_from_capability(
        self,
        capability: WholeOrganismEpisodeCapability,
    ) -> WholeOrganismStructuralStateReceipt:
        if not isinstance(
            capability,
            WholeOrganismEpisodeCapability,
        ):
            raise TypeError(
                "structural perturbation requires a typed settled "
                "whole-organism capability"
            )
        record = self._episode_authority.require(
            capability,
            DownstreamAuthority.LEARNING,
        )
        result = self._seal_state(record)
        self._verify_state_receipt(result)
        return result

    def _remember_verified_state(
        self,
        receipt: WholeOrganismStructuralStateReceipt,
        record: WholeOrganismEpisodeRecord | None,
    ) -> None:
        self._verified_state_receipts[
            receipt.authority_receipt_sha256
        ] = (receipt, record)
        while len(self._verified_state_receipts) > 2:
            oldest = next(iter(self._verified_state_receipts))
            del self._verified_state_receipts[oldest]


    def _verify_state_receipt(
        self,
        receipt: WholeOrganismStructuralStateReceipt,
    ) -> WholeOrganismEpisodeRecord | None:
        if not isinstance(
            receipt,
            WholeOrganismStructuralStateReceipt,
        ):
            raise TypeError(
                "whole-organism structural state receipt is not typed"
            )
        _sha(receipt.authority_receipt_sha256, "structural state authority")
        cached = self._verified_state_receipts.get(
            receipt.authority_receipt_sha256
        )
        if cached is not None:
            if cached[0] != receipt:
                raise PermissionError("verified structural state changed")
            return cached[1]
        manifest_receipt = (
            self._episode_authority.manifest.authority_receipt_sha256
        )
        if receipt.manifest_authority_receipt_sha256 != manifest_receipt:
            raise PermissionError(
                "whole-organism structural state crossed mounted manifest"
            )
        for value, label in (
            (
                receipt.structural_state_sha256,
                "structural state identity",
            ),
            (
                receipt.provenance_sha256,
                "structural state provenance",
            ),
            (
                receipt.authority_hmac_sha256,
                "structural state HMAC",
            ),
            (
                receipt.authority_receipt_sha256,
                "structural state authority",
            ),
        ):
            _sha(value, label)
        structural = _verified_mapping_json(
            receipt.structural_state_json,
            "whole-organism structural identity",
        )
        provenance = _verified_mapping_json(
            receipt.provenance_json,
            "whole-organism structural provenance",
        )
        if (
            structural.get("schema") != STRUCTURAL_IDENTITY_SCHEMA
            or provenance.get("schema") != STRUCTURAL_PROVENANCE_SCHEMA
            or structural.get("manifest_authority_receipt_sha256")
            != manifest_receipt
            or provenance.get("manifest_authority_receipt_sha256")
            != manifest_receipt
            or receipt.structural_state_sha256
            != hashlib.sha256(
                receipt.structural_state_json.encode("utf-8")
            ).hexdigest()
            or receipt.provenance_sha256
            != hashlib.sha256(
                receipt.provenance_json.encode("utf-8")
            ).hexdigest()
        ):
            raise PermissionError(
                "whole-organism structural identity or provenance changed"
            )
        payload = receipt.payload()
        expected_hmac = hmac.new(
            self._state_key,
            _STRUCTURAL_STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            receipt.authority_hmac_sha256 != expected_hmac
            or receipt.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise PermissionError(
                "whole-organism structural state authority changed"
            )
        origin = provenance.get("origin")
        if origin == "mounted_uncommitted_zero":
            expected = self._seal_zero_state()
            if expected != receipt:
                raise PermissionError(
                    "mounted whole-organism zero state changed"
                )
            self._remember_verified_state(receipt, None)
            return None
        if origin != "settled_whole_organism_episode":
            raise PermissionError(
                "whole-organism structural provenance origin changed"
            )
        episode_receipt = _sha(
            provenance.get("episode_authority_receipt_sha256"),
            "whole-organism provenance episode authority",
        )
        capability = self._episode_authority.capability_for(episode_receipt)
        record = self._episode_authority.require(
            capability,
            DownstreamAuthority.LEARNING,
        )
        expected = self._seal_state(record)
        if expected != receipt:
            raise PermissionError(
                "whole-organism structural state lost exact custody"
            )
        self._remember_verified_state(receipt, record)
        return record

    def _seal_transfer(
        self,
        *,
        before_state: WholeOrganismStructuralStateReceipt,
        after_state: WholeOrganismStructuralStateReceipt,
    ) -> PreparedWholeOrganismStructuralTransfer:
        self._verified_transfer = None
        transfer_id = _digest({
            "after_state_authority_receipt_sha256": (
                after_state.authority_receipt_sha256
            ),
            "before_state_authority_receipt_sha256": (
                before_state.authority_receipt_sha256
            ),
            "schema": TRANSFER_SCHEMA,
        })
        provisional = PreparedWholeOrganismStructuralTransfer(
            transfer_id=transfer_id,
            before_state=before_state,
            after_state=after_state,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._transfer_key,
            _TRANSFER_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        return PreparedWholeOrganismStructuralTransfer(
            transfer_id=transfer_id,
            before_state=before_state,
            after_state=after_state,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )

    def _verify_transfer(
        self,
        transfer: PreparedWholeOrganismStructuralTransfer,
    ) -> None:
        if not isinstance(
            transfer,
            PreparedWholeOrganismStructuralTransfer,
        ):
            raise TypeError(
                "whole-organism structural transfer lock is not typed"
            )
        _sha(transfer.authority_receipt_sha256, "structural transfer authority")
        cached_transfer = self._verified_transfer
        if cached_transfer is not None:
            if cached_transfer != transfer:
                raise PermissionError("verified structural transfer changed")
            return
        self._verify_state_receipt(transfer.before_state)
        self._verify_state_receipt(transfer.after_state)
        expected_id = _digest({
            "after_state_authority_receipt_sha256": (
                transfer.after_state.authority_receipt_sha256
            ),
            "before_state_authority_receipt_sha256": (
                transfer.before_state.authority_receipt_sha256
            ),
            "schema": TRANSFER_SCHEMA,
        })
        payload = transfer.payload()
        expected_hmac = hmac.new(
            self._transfer_key,
            _TRANSFER_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            transfer.transfer_id != expected_id
            or transfer.authority_hmac_sha256 != expected_hmac
            or transfer.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise PermissionError(
                "whole-organism structural transfer lock changed"
            )
        self._verified_transfer = transfer

    def prepare(
        self,
        capability: WholeOrganismEpisodeCapability,
    ) -> WholeOrganismStructuralPerturbationResolution:
        """Acquire the sole transfer lock without changing current state."""

        try:
            after_state = self._state_from_capability(capability)
        except (TypeError, ValueError, PermissionError) as error:
            return WholeOrganismStructuralPerturbationResolution(
                state="unresolved",
                reasons=(
                    f"settled_whole_organism_custody_missing:{error}",
                ),
                prepared=None,
                commit=None,
            )
        with self._lock:
            try:
                self._verify_state_receipt(self._current_state)
            except (TypeError, ValueError, PermissionError) as error:
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=(
                        f"current_structural_custody_missing:{error}",
                    ),
                    prepared=None,
                    commit=None,
                )
            if self._in_flight is not None:
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=("transfer_lock_unavailable",),
                    prepared=None,
                    commit=None,
                )
            prepared = self._seal_transfer(
                before_state=self._current_state,
                after_state=after_state,
            )
            try:
                self._verify_transfer(prepared)
                self._encoded(
                    current_state=self._current_state,
                    in_flight=prepared,
                )
            except (TypeError, ValueError, PermissionError) as error:
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=(
                        f"transfer_capacity_or_custody_missing:{error}",
                    ),
                    prepared=None,
                    commit=None,
                )
            self._in_flight = prepared
            return WholeOrganismStructuralPerturbationResolution(
                state="prepared",
                reasons=(),
                prepared=prepared,
                commit=None,
            )

    def _seal_commit(
        self,
        transfer: PreparedWholeOrganismStructuralTransfer,
        disposition: str,
    ) -> WholeOrganismStructuralTransferCommit:
        if disposition not in {"changed", "no_durable_change"}:
            raise ValueError(
                "whole-organism transfer disposition is invalid"
            )
        provisional = WholeOrganismStructuralTransferCommit(
            transfer_id=transfer.transfer_id,
            before_state_authority_receipt_sha256=(
                transfer.before_state.authority_receipt_sha256
            ),
            after_state_authority_receipt_sha256=(
                transfer.after_state.authority_receipt_sha256
            ),
            before_structural_state_sha256=(
                transfer.before_state.structural_state_sha256
            ),
            after_structural_state_sha256=(
                transfer.after_state.structural_state_sha256
            ),
            disposition=disposition,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = provisional.payload()
        signature = hmac.new(
            self._commit_key,
            _COMMIT_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        return WholeOrganismStructuralTransferCommit(
            transfer_id=provisional.transfer_id,
            before_state_authority_receipt_sha256=(
                provisional.before_state_authority_receipt_sha256
            ),
            after_state_authority_receipt_sha256=(
                provisional.after_state_authority_receipt_sha256
            ),
            before_structural_state_sha256=(
                provisional.before_structural_state_sha256
            ),
            after_structural_state_sha256=(
                provisional.after_structural_state_sha256
            ),
            disposition=disposition,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )

    def commit(
        self,
        transfer: object,
    ) -> WholeOrganismStructuralPerturbationResolution:
        """Commit only the currently retained authenticated transfer lock."""

        with self._lock:
            if self._in_flight is None:
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=("transfer_lock_missing",),
                    prepared=None,
                    commit=None,
                )
            if not isinstance(
                transfer,
                PreparedWholeOrganismStructuralTransfer,
            ):
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=("transfer_lock_missing",),
                    prepared=None,
                    commit=None,
                )
            try:
                self._verify_transfer(transfer)
                self._verify_transfer(self._in_flight)
            except (TypeError, ValueError, PermissionError) as error:
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=(f"transfer_custody_missing:{error}",),
                    prepared=None,
                    commit=None,
                )
            if (
                transfer.authority_receipt_sha256
                != self._in_flight.authority_receipt_sha256
                or transfer.before_state.authority_receipt_sha256
                != self._current_state.authority_receipt_sha256
            ):
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=("transfer_lock_missing",),
                    prepared=None,
                    commit=None,
                )
            disposition = (
                "no_durable_change"
                if (
                    transfer.before_state.structural_state_sha256
                    == transfer.after_state.structural_state_sha256
                )
                else "changed"
            )
            next_state = (
                self._current_state
                if disposition == "no_durable_change"
                else transfer.after_state
            )
            try:
                self._encoded(
                    current_state=next_state,
                    in_flight=None,
                )
            except (TypeError, ValueError, PermissionError) as error:
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=(
                        f"transfer_capacity_or_custody_missing:{error}",
                    ),
                    prepared=None,
                    commit=None,
                )
            commit = self._seal_commit(transfer, disposition)
            self._current_state = next_state
            self._in_flight = None
            return WholeOrganismStructuralPerturbationResolution(
                state=disposition,
                reasons=(),
                prepared=None,
                commit=commit,
            )

    def rollback(
        self,
        transfer: object,
    ) -> WholeOrganismStructuralPerturbationResolution:
        """Discard only the exact retained lock; current state is untouched."""

        with self._lock:
            if (
                self._in_flight is None
                or not isinstance(
                    transfer,
                    PreparedWholeOrganismStructuralTransfer,
                )
            ):
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=("transfer_lock_missing",),
                    prepared=None,
                    commit=None,
                )
            try:
                self._verify_transfer(transfer)
                self._verify_transfer(self._in_flight)
            except (TypeError, ValueError, PermissionError) as error:
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=(f"transfer_custody_missing:{error}",),
                    prepared=None,
                    commit=None,
                )
            if (
                transfer.authority_receipt_sha256
                != self._in_flight.authority_receipt_sha256
            ):
                return WholeOrganismStructuralPerturbationResolution(
                    state="unresolved",
                    reasons=("transfer_lock_missing",),
                    prepared=None,
                    commit=None,
                )
            self._encoded(
                current_state=self._current_state,
                in_flight=None,
            )
            self._in_flight = None
            return WholeOrganismStructuralPerturbationResolution(
                state="rolled_back",
                reasons=(),
                prepared=None,
                commit=None,
            )

    def _state_payload(
        self,
        *,
        current_state: WholeOrganismStructuralStateReceipt,
        in_flight: PreparedWholeOrganismStructuralTransfer | None,
    ) -> dict[str, object]:
        return {
            "current_state": current_state.record(),
            "in_flight_transfer": (
                None if in_flight is None else in_flight.record()
            ),
            "max_state_bytes": self._max_state_bytes,
            "schema": OWNER_STATE_SCHEMA,
        }

    def _encoded(
        self,
        *,
        current_state: WholeOrganismStructuralStateReceipt,
        in_flight: PreparedWholeOrganismStructuralTransfer | None,
    ) -> bytes:
        self._verify_state_receipt(current_state)
        if in_flight is not None:
            self._verify_transfer(in_flight)
        payload = self._state_payload(
            current_state=current_state,
            in_flight=in_flight,
        )
        signature = hmac.new(
            self._owner_state_key,
            _OWNER_STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "authority_hmac_sha256": signature,
            "payload": payload,
            "schema": OWNER_STATE_ENVELOPE_SCHEMA,
        })
        if len(encoded) > self._max_state_bytes:
            raise ValueError(
                "whole-organism perturbation state capacity full"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(
                current_state=self._current_state,
                in_flight=self._in_flight,
            )

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        episode_authority: WholeOrganismEpisodeAuthority,
        encoded: bytes,
    ) -> "WholeOrganismStructuralPerturbationOwner":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError(
                "whole-organism perturbation cold state is absent"
            )
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "whole-organism perturbation cold state is unreadable"
            ) from error
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {
                "authority_hmac_sha256",
                "payload",
                "schema",
            }
            or envelope.get("schema")
            != OWNER_STATE_ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError(
                "whole-organism perturbation cold envelope changed"
            )
        payload = envelope.get("payload")
        if (
            not isinstance(payload, dict)
            or set(payload) != {
                "current_state",
                "in_flight_transfer",
                "max_state_bytes",
                "schema",
            }
            or payload.get("schema") != OWNER_STATE_SCHEMA
        ):
            raise ValueError(
                "whole-organism perturbation cold payload changed"
            )
        current_state = cls._state_from_record(
            payload.get("current_state")
        )
        owner = cls(
            authority_key=authority_key,
            episode_authority=episode_authority,
            max_state_bytes=payload.get("max_state_bytes"),
        )
        owner._verify_state_receipt(current_state)
        raw_in_flight = payload.get("in_flight_transfer")
        in_flight = (
            None
            if raw_in_flight is None
            else cls._transfer_from_record(raw_in_flight)
        )
        expected_hmac = hmac.new(
            owner._owner_state_key,
            _OWNER_STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if envelope.get("authority_hmac_sha256") != expected_hmac:
            raise ValueError(
                "whole-organism perturbation cold state authority changed"
            )
        if in_flight is not None:
            owner._verify_transfer(in_flight)
            if (
                in_flight.before_state.authority_receipt_sha256
                != current_state.authority_receipt_sha256
            ):
                raise ValueError(
                    "cold structural transfer left its before state"
                )
        owner._current_state = current_state
        owner._in_flight = in_flight
        if owner.snapshot_encoded() != encoded:
            raise ValueError(
                "whole-organism perturbation cold round-trip changed state"
            )
        return owner

    @staticmethod
    def _state_from_record(
        raw: object,
    ) -> WholeOrganismStructuralStateReceipt:
        expected = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "manifest_authority_receipt_sha256",
            "provenance_json",
            "provenance_sha256",
            "schema",
            "structural_state_json",
            "structural_state_sha256",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != STRUCTURAL_STATE_SCHEMA
        ):
            raise ValueError(
                "cold whole-organism structural state record changed"
            )
        return WholeOrganismStructuralStateReceipt(
            manifest_authority_receipt_sha256=(
                raw["manifest_authority_receipt_sha256"]
            ),
            structural_state_json=raw["structural_state_json"],
            structural_state_sha256=raw["structural_state_sha256"],
            provenance_json=raw["provenance_json"],
            provenance_sha256=raw["provenance_sha256"],
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=(
                raw["authority_receipt_sha256"]
            ),
        )

    @classmethod
    def _transfer_from_record(
        cls,
        raw: object,
    ) -> PreparedWholeOrganismStructuralTransfer:
        expected = {
            "after_state",
            "after_state_authority_receipt_sha256",
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "before_state",
            "before_state_authority_receipt_sha256",
            "schema",
            "transfer_id",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != expected
            or raw.get("schema") != TRANSFER_SCHEMA
        ):
            raise ValueError(
                "cold whole-organism structural transfer changed"
            )
        before_state = cls._state_from_record(raw["before_state"])
        after_state = cls._state_from_record(raw["after_state"])
        if (
            raw["before_state_authority_receipt_sha256"]
            != before_state.authority_receipt_sha256
            or raw["after_state_authority_receipt_sha256"]
            != after_state.authority_receipt_sha256
        ):
            raise ValueError(
                "cold structural transfer state custody changed"
            )
        return PreparedWholeOrganismStructuralTransfer(
            transfer_id=raw["transfer_id"],
            before_state=before_state,
            after_state=after_state,
            authority_hmac_sha256=raw["authority_hmac_sha256"],
            authority_receipt_sha256=raw["authority_receipt_sha256"],
        )


__all__ = (
    "PreparedWholeOrganismStructuralTransfer",
    "WholeOrganismStructuralPerturbationOwner",
    "WholeOrganismStructuralPerturbationResolution",
    "WholeOrganismStructuralStateReceipt",
    "WholeOrganismStructuralTransferCommit",
)
