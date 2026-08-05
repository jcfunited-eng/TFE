"""Exact causal occurrence for one uniquely heard Krimelack kind.

This module closes the gap between auditory form recognition and causal
experience without turning tutor text into meaning.  One occurrence binds:

* the unique structural kind selected by the Krimelack relation;
* each real auditory L5 component and its complete compact L0--L4 DSF field;
* each joint PCM/cochlear/L5/causal stream settlement;
* each complete six-sense causal settlement.

The occurrence contains no transcript, Unicode scalar sequence, tutor label,
speaker identity, action, or routing chi.  Chi may remain inside the witnessed
causal settlement as routing provenance, but it does not enter the occurrence
association identity.  The full seven-field structure is retained and
reverified; no score or compatibility vector is used.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_krimelack_kind import (
    mount_auditory_krimelack_path,
)
from dsf_ai_service.substrate.auditory_krimelack_stream import (
    AuditoryKrimelackStreamRecognition,
    AuditoryKrimelackStreamState,
)
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    mount_auditory_l4_causal_support,
)
from dsf_ai_service.substrate.auditory_krimelack_memory import (
    AuditoryKrimelackPreparedExemplar,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Experience
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AUDITORY_STREAM_SETTLEMENT_SCHEMA,
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.causal_deliberation import (
    DeliberationWitness,
)
from dsf_ai_service.substrate.compact_auditory_field_authority import (
    MAX_COMPACT_AUDITORY_FIELD_BYTES,
    CompactAuditoryFieldAuthority,
    compact_auditory_field_from_l5,
    decode_compact_auditory_field,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


AUDITORY_KRIMELACK_CAUSAL_COMPONENT_SCHEMA = (
    "guala.auditory.krimelack_causal_component.v1"
)
AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_SCHEMA = (
    "guala.auditory.krimelack_causal_occurrence.v1"
)
AUDITORY_KRIMELACK_CAUSAL_ASSOCIATION_SCHEMA = (
    "guala.auditory.krimelack_causal_association.v1"
)
MAX_AUDITORY_KRIMELACK_CAUSAL_COMPONENTS = 2
MAX_AUDITORY_KRIMELACK_CAUSAL_SETTLEMENT_BYTES = 2 * 1024 * 1024
MAX_AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_BYTES = 8 * 1024 * 1024


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


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("auditory causal occurrence time must be exact")
    return f"{value.numerator}/{value.denominator}"


def _fraction(value: object, name: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"{name} is not an exact fraction")
    numerator, denominator = value.split("/", 1)
    if (
        not numerator
        or not denominator
        or not numerator.lstrip("-").isdigit()
        or not denominator.isdigit()
        or int(denominator) <= 0
    ):
        raise ValueError(f"{name} is not an exact fraction")
    result = Fraction(int(numerator), int(denominator))
    if _fraction_text(result) != value:
        raise ValueError(f"{name} is not canonical")
    return result


def _stream_record(
    value: AuditoryStreamSettlementReceipt,
) -> dict[str, object]:
    value.verify()
    return {
        **value.payload(),
        "authority_receipt_sha256": value.authority_receipt_sha256,
    }


def _stream_from_record(
    value: object,
) -> AuditoryStreamSettlementReceipt:
    expected = {
        "assembly_id",
        "auditory_l5_authority_receipt_sha256",
        "authority_receipt_sha256",
        "causal_settlement_authority_receipt_sha256",
        "cochlear_receipt_sha256",
        "first_sample_index",
        "prior_cochlear_state_receipt_sha256",
        "prior_transport_receipt_sha256",
        "sample_count",
        "sample_rate_hz",
        "schema",
        "sequence",
        "source_time_end",
        "source_time_start",
        "stream_id",
        "transport_receipt_sha256",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected
        or value.get("schema") != AUDITORY_STREAM_SETTLEMENT_SCHEMA
    ):
        raise ValueError("auditory causal stream settlement fields changed")
    result = AuditoryStreamSettlementReceipt(
        stream_id=value.get("stream_id"),
        sequence=value.get("sequence"),
        first_sample_index=value.get("first_sample_index"),
        sample_count=value.get("sample_count"),
        source_time_start=_fraction(
            value.get("source_time_start"),
            "auditory causal stream start",
        ),
        source_time_end=_fraction(
            value.get("source_time_end"),
            "auditory causal stream end",
        ),
        assembly_id=value.get("assembly_id"),
        transport_receipt_sha256=value.get(
            "transport_receipt_sha256"
        ),
        prior_transport_receipt_sha256=value.get(
            "prior_transport_receipt_sha256"
        ),
        cochlear_receipt_sha256=value.get("cochlear_receipt_sha256"),
        prior_cochlear_state_receipt_sha256=value.get(
            "prior_cochlear_state_receipt_sha256"
        ),
        auditory_l5_authority_receipt_sha256=value.get(
            "auditory_l5_authority_receipt_sha256"
        ),
        causal_settlement_authority_receipt_sha256=value.get(
            "causal_settlement_authority_receipt_sha256"
        ),
        authority_receipt_sha256=value.get(
            "authority_receipt_sha256"
        ),
    )
    result.verify()
    if _stream_record(result) != dict(value):
        raise ValueError(
            "auditory causal stream settlement is not canonical"
        )
    return result


def _causal_witness_from_record(value: object) -> DeliberationWitness:
    expected = {
        "event_id",
        "schema",
        "settlement_payload_base64",
        "settlement_receipt_sha256",
        "structural_fingerprint",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError("auditory causal full-field witness fields changed")
    result = DeliberationWitness(
        event_id=value.get("event_id"),
        settlement_receipt_sha256=value.get(
            "settlement_receipt_sha256"
        ),
        structural_fingerprint=value.get("structural_fingerprint"),
        settlement_payload_base64=value.get(
            "settlement_payload_base64"
        ),
    )
    result.verify(
        max_bytes=MAX_AUDITORY_KRIMELACK_CAUSAL_SETTLEMENT_BYTES
    )
    if result.as_record() != dict(value):
        raise ValueError(
            "auditory causal full-field witness is not canonical"
        )
    return result


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackCausalComponent:
    ordinal: int
    path_authority_receipt_sha256: str
    full_dsf_authority: CompactAuditoryFieldAuthority
    stream_settlement: AuditoryStreamSettlementReceipt
    causal_witness: DeliberationWitness
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        encoded_field = self.full_dsf_authority.encoded()
        return {
            "causal_witness": self.causal_witness.as_record(),
            "full_dsf_authority_base64": base64.b64encode(
                encoded_field
            ).decode("ascii"),
            "ordinal": self.ordinal,
            "path_authority_receipt_sha256": (
                self.path_authority_receipt_sha256
            ),
            "schema": AUDITORY_KRIMELACK_CAUSAL_COMPONENT_SCHEMA,
            "stream_settlement": _stream_record(
                self.stream_settlement
            ),
        }

    def verify(self, *, expected_ordinal: int) -> None:
        if (
            isinstance(self.ordinal, bool)
            or not isinstance(self.ordinal, int)
            or self.ordinal != expected_ordinal
        ):
            raise ValueError(
                "auditory causal component order changed"
            )
        sha256_digest(
            self.path_authority_receipt_sha256,
            "auditory causal component path",
        )
        sha256_digest(
            self.authority_receipt_sha256,
            "auditory causal component authority",
        )
        self.full_dsf_authority.verify()
        self.stream_settlement.verify()
        self.causal_witness.verify(
            max_bytes=(
                MAX_AUDITORY_KRIMELACK_CAUSAL_SETTLEMENT_BYTES
            )
        )
        field = self.full_dsf_authority
        stream = self.stream_settlement
        causal = self.causal_witness
        if (
            field.source_field_authority_receipt_sha256
            != stream.auditory_l5_authority_receipt_sha256
            or field.assembly_id != stream.assembly_id
            or field.source_time_start != stream.source_time_start
            or field.source_time_end != stream.source_time_end
            or causal.settlement_receipt_sha256
            != stream.causal_settlement_authority_receipt_sha256
            or _digest(self.payload())
            != self.authority_receipt_sha256
        ):
            raise ValueError(
                "auditory causal component left its exact full field"
            )

    def as_record(self) -> dict[str, object]:
        self.verify(expected_ordinal=self.ordinal)
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    @classmethod
    def from_record(
        cls,
        value: object,
        *,
        expected_ordinal: int,
    ) -> "AuditoryKrimelackCausalComponent":
        expected = {
            "authority_receipt_sha256",
            "causal_witness",
            "full_dsf_authority_base64",
            "ordinal",
            "path_authority_receipt_sha256",
            "schema",
            "stream_settlement",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema")
            != AUDITORY_KRIMELACK_CAUSAL_COMPONENT_SCHEMA
        ):
            raise ValueError(
                "auditory causal component record fields changed"
            )
        encoded = value.get("full_dsf_authority_base64")
        if not isinstance(encoded, str) or not encoded:
            raise ValueError(
                "auditory causal component full DSF field is absent"
            )
        try:
            decoded = base64.b64decode(encoded, validate=True)
        except Exception as error:
            raise ValueError(
                "auditory causal component full DSF field is unreadable"
            ) from error
        if (
            len(decoded) > MAX_COMPACT_AUDITORY_FIELD_BYTES
            or base64.b64encode(decoded).decode("ascii") != encoded
        ):
            raise ValueError(
                "auditory causal component full DSF field changed"
            )
        result = cls(
            ordinal=value.get("ordinal"),
            path_authority_receipt_sha256=value.get(
                "path_authority_receipt_sha256"
            ),
            full_dsf_authority=decode_compact_auditory_field(decoded),
            stream_settlement=_stream_from_record(
                value.get("stream_settlement")
            ),
            causal_witness=_causal_witness_from_record(
                value.get("causal_witness")
            ),
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        result.verify(expected_ordinal=expected_ordinal)
        if result.as_record() != dict(value):
            raise ValueError(
                "auditory causal component record is not canonical"
            )
        return result


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackCausalOccurrence:
    occurrence_id: str
    association_id: str
    kind_id: str
    recognition_authority_receipt_sha256: str
    components: tuple[AuditoryKrimelackCausalComponent, ...]
    authority_receipt_sha256: str

    @property
    def source_time_start(self) -> Fraction:
        return self.components[0].stream_settlement.source_time_start

    @property
    def source_time_end(self) -> Fraction:
        return self.components[-1].stream_settlement.source_time_end

    def association_payload(self) -> dict[str, object]:
        return {
            "causal_structural_fingerprints": [
                value.causal_witness.structural_fingerprint
                for value in self.components
            ],
            "full_dsf_structural_fingerprints": [
                value.full_dsf_authority.structural_fingerprint
                for value in self.components
            ],
            "kind_id": self.kind_id,
            "schema": AUDITORY_KRIMELACK_CAUSAL_ASSOCIATION_SCHEMA,
        }

    def payload(self) -> dict[str, object]:
        return {
            "association_id": self.association_id,
            "component_authority_receipts": [
                value.authority_receipt_sha256
                for value in self.components
            ],
            "kind_id": self.kind_id,
            "recognition_authority_receipt_sha256": (
                self.recognition_authority_receipt_sha256
            ),
            "schema": AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_SCHEMA,
            "source_time_end": _fraction_text(self.source_time_end),
            "source_time_start": _fraction_text(self.source_time_start),
        }

    def verify(self) -> None:
        for value, name in (
            (self.occurrence_id, "occurrence"),
            (self.association_id, "association"),
            (self.kind_id, "kind"),
            (
                self.recognition_authority_receipt_sha256,
                "recognition",
            ),
            (self.authority_receipt_sha256, "authority"),
        ):
            sha256_digest(value, f"auditory causal {name}")
        if (
            not isinstance(self.components, tuple)
            or not 1
            <= len(self.components)
            <= MAX_AUDITORY_KRIMELACK_CAUSAL_COMPONENTS
        ):
            raise ValueError(
                "auditory causal occurrence component boundary changed"
            )
        for ordinal, component in enumerate(self.components):
            component.verify(expected_ordinal=ordinal)
            if ordinal:
                prior = self.components[ordinal - 1].stream_settlement
                current = component.stream_settlement
                if (
                    current.stream_id != prior.stream_id
                    or current.sequence != prior.sequence + 1
                    or current.first_sample_index
                    != prior.first_sample_index + prior.sample_count
                    or current.prior_transport_receipt_sha256
                    != prior.transport_receipt_sha256
                    or current.source_time_start != prior.source_time_end
                ):
                    raise ValueError(
                        "auditory causal occurrence is not continuous"
                    )
        if (
            self.association_id
            != _digest(self.association_payload())
            or self.authority_receipt_sha256
            != _digest(self.payload())
            or self.occurrence_id != self.authority_receipt_sha256
        ):
            raise ValueError(
                "auditory causal occurrence authority changed"
            )
        encoded = _canonical(self.as_record(verify=False))
        if len(encoded) > MAX_AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_BYTES:
            raise RuntimeError(
                "auditory causal occurrence exceeds its byte boundary"
            )

    def as_record(self, *, verify: bool = True) -> dict[str, object]:
        if verify:
            self.verify()
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "components": [
                value.as_record() for value in self.components
            ],
            "occurrence_id": self.occurrence_id,
        }

    @classmethod
    def from_record(
        cls,
        value: object,
    ) -> "AuditoryKrimelackCausalOccurrence":
        expected = {
            "association_id",
            "authority_receipt_sha256",
            "component_authority_receipts",
            "components",
            "kind_id",
            "occurrence_id",
            "recognition_authority_receipt_sha256",
            "schema",
            "source_time_end",
            "source_time_start",
        }
        if (
            not isinstance(value, Mapping)
            or set(value) != expected
            or value.get("schema")
            != AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_SCHEMA
            or not isinstance(value.get("components"), list)
            or not isinstance(
                value.get("component_authority_receipts"), list
            )
            or len(_canonical(value))
            > MAX_AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_BYTES
        ):
            raise ValueError(
                "auditory causal occurrence record fields changed"
            )
        components = tuple(
            AuditoryKrimelackCausalComponent.from_record(
                item,
                expected_ordinal=ordinal,
            )
            for ordinal, item in enumerate(value["components"])
        )
        result = cls(
            occurrence_id=value.get("occurrence_id"),
            association_id=value.get("association_id"),
            kind_id=value.get("kind_id"),
            recognition_authority_receipt_sha256=value.get(
                "recognition_authority_receipt_sha256"
            ),
            components=components,
            authority_receipt_sha256=value.get(
                "authority_receipt_sha256"
            ),
        )
        if (
            list(value["component_authority_receipts"])
            != [
                item.authority_receipt_sha256 for item in components
            ]
            or _fraction(
                value.get("source_time_start"),
                "auditory causal occurrence start",
            )
            != result.source_time_start
            or _fraction(
                value.get("source_time_end"),
                "auditory causal occurrence end",
            )
            != result.source_time_end
        ):
            raise ValueError(
                "auditory causal occurrence component links changed"
            )
        result.verify()
        if result.as_record() != dict(value):
            raise ValueError(
                "auditory causal occurrence record is not canonical"
            )
        return result


def _causal_component(
    *,
    ordinal: int,
    experience: AuditoryL5Experience,
    stream: AuditoryStreamSettlementReceipt,
    causal: CausalExperienceSettlement,
    expected_path_receipt: str,
    expected_full_dsf_receipt: str,
    prepared_exemplar: (
        AuditoryKrimelackPreparedExemplar | None
    ) = None,
) -> AuditoryKrimelackCausalComponent:
    stream.verify()
    causal.verify()
    if causal.language_events:
        raise ValueError(
            "auditory Krimelack causal occurrence rejects transcript events"
        )
    if prepared_exemplar is None:
        # Isolated callers retain the complete original verification path.
        experience.verify()
        path = mount_auditory_krimelack_path(experience)
        support = mount_auditory_l4_causal_support(experience)
        full_dsf = compact_auditory_field_from_l5(
            experience,
            support,
        )
    else:
        if not isinstance(
            prepared_exemplar,
            AuditoryKrimelackPreparedExemplar,
        ):
            raise TypeError(
                "auditory causal occurrence requires prepared exemplar"
            )
        prepared_exemplar.verify_linkage(experience)
        path = prepared_exemplar.exemplar.path
        full_dsf = (
            prepared_exemplar.exemplar.full_dsf_authority
        )
    causal_witness = DeliberationWitness.from_settlement(
        causal,
        max_bytes=MAX_AUDITORY_KRIMELACK_CAUSAL_SETTLEMENT_BYTES,
    )
    if (
        path.authority_receipt_sha256 != expected_path_receipt
        or full_dsf.authority_receipt_sha256
        != expected_full_dsf_receipt
        or stream.auditory_l5_authority_receipt_sha256
        != experience.authority_receipt_sha256
        or stream.causal_settlement_authority_receipt_sha256
        != causal.authority_receipt_sha256
        or stream.assembly_id != experience.assembly_id
        or stream.assembly_id != causal.assembly_id
        or stream.source_time_start != experience.source_time_start
        or stream.source_time_end != experience.source_time_end
        or stream.source_time_start != causal.source_time_start
        or stream.source_time_end != causal.source_time_end
    ):
        raise ValueError(
            "auditory recognition component left its live causal settlement"
        )
    provisional = AuditoryKrimelackCausalComponent(
        ordinal=ordinal,
        path_authority_receipt_sha256=path.authority_receipt_sha256,
        full_dsf_authority=full_dsf,
        stream_settlement=stream,
        causal_witness=causal_witness,
        authority_receipt_sha256="0" * 64,
    )
    result = AuditoryKrimelackCausalComponent(
        ordinal=provisional.ordinal,
        path_authority_receipt_sha256=(
            provisional.path_authority_receipt_sha256
        ),
        full_dsf_authority=provisional.full_dsf_authority,
        stream_settlement=provisional.stream_settlement,
        causal_witness=provisional.causal_witness,
        authority_receipt_sha256=_digest(provisional.payload()),
    )
    result.verify(expected_ordinal=ordinal)
    return result


def bind_auditory_krimelack_causal_occurrence(
    *,
    recognition: AuditoryKrimelackStreamRecognition,
    auditory_experiences: tuple[AuditoryL5Experience, ...],
    stream_settlements: tuple[
        AuditoryStreamSettlementReceipt, ...
    ],
    causal_settlements: tuple[CausalExperienceSettlement, ...],
    prepared_exemplars: (
        tuple[AuditoryKrimelackPreparedExemplar, ...] | None
    ) = None,
) -> AuditoryKrimelackCausalOccurrence:
    """Bind one unique heard form to its exact lived full-field occurrence."""

    if not isinstance(
        recognition,
        AuditoryKrimelackStreamRecognition,
    ):
        raise TypeError(
            "auditory causal occurrence requires typed recognition"
        )
    recognition.verify()
    if (
        recognition.state is not AuditoryKrimelackStreamState.UNIQUE
        or recognition.selected_kind_id is None
    ):
        raise ValueError(
            "auditory causal occurrence requires unique recognition"
        )
    count = len(recognition.component_experience_ids)
    if (
        not 1 <= count <= MAX_AUDITORY_KRIMELACK_CAUSAL_COMPONENTS
        or not isinstance(auditory_experiences, tuple)
        or not isinstance(stream_settlements, tuple)
        or not isinstance(causal_settlements, tuple)
        or len(auditory_experiences) != count
        or len(stream_settlements) != count
        or len(causal_settlements) != count
        or (
            prepared_exemplars is not None
            and (
                not isinstance(prepared_exemplars, tuple)
                or len(prepared_exemplars) != count
            )
        )
    ):
        raise ValueError(
            "auditory causal occurrence evidence cardinality changed"
        )
    components = tuple(
        _causal_component(
            ordinal=ordinal,
            experience=experience,
            stream=stream,
            causal=causal,
            expected_path_receipt=(
                recognition.component_path_receipts[ordinal]
            ),
            expected_full_dsf_receipt=(
                recognition.component_full_dsf_receipts[ordinal]
            ),
            prepared_exemplar=prepared_exemplar,
        )
        for ordinal, (
            experience,
            stream,
            causal,
            prepared_exemplar,
        ) in enumerate(zip(
            auditory_experiences,
            stream_settlements,
            causal_settlements,
            (
                prepared_exemplars
                if prepared_exemplars is not None
                else (None,) * count
            ),
            strict=True,
        ))
    )
    last_stream = components[-1].stream_settlement
    if (
        tuple(
            value.full_dsf_authority.experience_id
            for value in components
        )
        != recognition.component_experience_ids
        or recognition.stream_id != last_stream.stream_id
        or recognition.sequence != last_stream.sequence
        or recognition.first_sample_index
        != last_stream.first_sample_index
        or recognition.sample_count != last_stream.sample_count
        or recognition.settlement_receipt_sha256
        != last_stream.authority_receipt_sha256
    ):
        raise ValueError(
            "auditory recognition left its continuous causal occurrence"
        )
    association_payload = {
        "causal_structural_fingerprints": [
            value.causal_witness.structural_fingerprint
            for value in components
        ],
        "full_dsf_structural_fingerprints": [
            value.full_dsf_authority.structural_fingerprint
            for value in components
        ],
        "kind_id": recognition.selected_kind_id,
        "schema": AUDITORY_KRIMELACK_CAUSAL_ASSOCIATION_SCHEMA,
    }
    association_id = _digest(association_payload)
    provisional = AuditoryKrimelackCausalOccurrence(
        occurrence_id="0" * 64,
        association_id=association_id,
        kind_id=recognition.selected_kind_id,
        recognition_authority_receipt_sha256=(
            recognition.authority_receipt_sha256
        ),
        components=components,
        authority_receipt_sha256="0" * 64,
    )
    authority = _digest(provisional.payload())
    result = AuditoryKrimelackCausalOccurrence(
        occurrence_id=authority,
        association_id=provisional.association_id,
        kind_id=provisional.kind_id,
        recognition_authority_receipt_sha256=(
            provisional.recognition_authority_receipt_sha256
        ),
        components=provisional.components,
        authority_receipt_sha256=authority,
    )
    result.verify()
    return result


__all__ = (
    "AUDITORY_KRIMELACK_CAUSAL_ASSOCIATION_SCHEMA",
    "AUDITORY_KRIMELACK_CAUSAL_COMPONENT_SCHEMA",
    "AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_SCHEMA",
    "MAX_AUDITORY_KRIMELACK_CAUSAL_COMPONENTS",
    "MAX_AUDITORY_KRIMELACK_CAUSAL_OCCURRENCE_BYTES",
    "AuditoryKrimelackCausalComponent",
    "AuditoryKrimelackCausalOccurrence",
    "bind_auditory_krimelack_causal_occurrence",
)
