"""Transient bounded retention for live auditory causal authorities.

Continuous Krimelack recognition may join the current transport unit with the
immediately prior unit.  Its recognition receipt names both L5 experience
identities and both full-field/path receipts, but a receipt is not the
original typed authority.  Causal occurrence binding therefore requires a
small lifetime owner that retains the original:

* ``AuditoryL5Experience``;
* ``AuditoryStreamSettlementReceipt``;
* ``CausalExperienceSettlement``;
* one immutable verified Krimelack path/full-DSF exemplar.

This owner mirrors the live Krimelack stream boundary: at most one prior and
one current component for each of four streams.  A component is prepared
without mutation before recognition.  It is committed only when the returned
recognition exactly names the same current settlement and its component
receipts match that shared verified exemplar.  Discontinuity clears the
stream.  State is intentionally transient because the recognition stream is
also transient across restart.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from dsf_ai_service.substrate.auditory_krimelack_memory import (
    AuditoryKrimelackPreparedExemplar,
    AuditoryKrimelackPreparedPath,
    prepare_auditory_krimelack_path,
)
from dsf_ai_service.substrate.auditory_krimelack_stream import (
    MAX_AUDITORY_KRIMELACK_STREAM_COMPONENTS,
    AuditoryKrimelackStreamRecognition,
    AuditoryKrimelackStreamState,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Experience
from dsf_ai_service.substrate.auditory_incremental_terminal import (
    AuditoryVerifiedSettlementCapability,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_STREAM_CAPACITY,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)


AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_BUFFER_SCHEMA = (
    "guala.auditory.krimelack_causal_evidence_buffer.v2"
)
MAX_AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_COMPONENT_BYTES = (
    8 * 1024 * 1024
)
MAX_AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_BUFFER_BYTES = (
    64 * 1024 * 1024
)

def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackRetainedCausalComponent:
    auditory_l5: AuditoryL5Experience
    stream_settlement: AuditoryStreamSettlementReceipt
    causal_settlement: CausalExperienceSettlement
    prepared_path: AuditoryKrimelackPreparedPath
    path_receipt_sha256: str
    authority_bytes: int

    def verify(self) -> None:
        if not isinstance(self.auditory_l5, AuditoryL5Experience):
            raise TypeError(
                "auditory evidence buffer requires typed L5"
            )
        if not isinstance(
            self.stream_settlement,
            AuditoryStreamSettlementReceipt,
        ):
            raise TypeError(
                "auditory evidence buffer requires stream settlement"
            )
        if not isinstance(
            self.causal_settlement,
            CausalExperienceSettlement,
        ):
            raise TypeError(
                "auditory evidence buffer requires causal settlement"
            )
        self.stream_settlement.verify()
        self.causal_settlement.verify()
        if not isinstance(
            self.prepared_path,
            AuditoryKrimelackPreparedPath,
        ):
            raise TypeError(
                "auditory evidence buffer requires exact path"
            )
        self.prepared_path.verify_linkage(self.auditory_l5)
        path = self.prepared_path.path
        if (
            self.stream_settlement.assembly_id
            != self.auditory_l5.assembly_id
            or self.causal_settlement.assembly_id
            != self.auditory_l5.assembly_id
            or self.stream_settlement.source_time_start
            != self.auditory_l5.source_time_start
            or self.stream_settlement.source_time_end
            != self.auditory_l5.source_time_end
            or self.causal_settlement.source_time_start
            != self.auditory_l5.source_time_start
            or self.causal_settlement.source_time_end
            != self.auditory_l5.source_time_end
            or self.stream_settlement
            .auditory_l5_authority_receipt_sha256
            != self.auditory_l5.authority_receipt_sha256
            or self.stream_settlement
            .causal_settlement_authority_receipt_sha256
            != self.causal_settlement.authority_receipt_sha256
            or path.experience_id
            != self.auditory_l5.experience_id
            or path.l5_authority_receipt_sha256
            != self.auditory_l5.authority_receipt_sha256
        ):
            raise ValueError(
                "auditory evidence buffer authority linkage changed"
            )
        if (
            self.path_receipt_sha256
            != path.authority_receipt_sha256
            or not 1
            <= self.authority_bytes
            <= MAX_AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_COMPONENT_BYTES
        ):
            raise ValueError(
                "auditory evidence buffer path authority changed"
            )


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackPreparedCausalComponent:
    component: AuditoryKrimelackRetainedCausalComponent
    preparation_receipt_sha256: str
    _construction_authority: object

    def verify(self) -> None:
        self.component.verify()
        if self.preparation_receipt_sha256 != (
            _preparation_receipt(self.component)
        ):
            raise ValueError(
                "auditory evidence preparation receipt changed"
            )


def _preparation_receipt(
    component: AuditoryKrimelackRetainedCausalComponent,
) -> str:
    return hashlib.sha256(_canonical({
        "causal_settlement_receipt_sha256": (
            component.causal_settlement.authority_receipt_sha256
        ),
        "experience_id": component.auditory_l5.experience_id,
        "authority_bytes": component.authority_bytes,
        "path_receipt_sha256": component.path_receipt_sha256,
        "prepared_path_verification_receipt_sha256": (
            component.prepared_path.verification_receipt_sha256
        ),
        "schema": (
            "guala.auditory.krimelack_causal_evidence_preparation.v1"
        ),
        "stream_settlement_receipt_sha256": (
            component.stream_settlement.authority_receipt_sha256
        ),
    })).hexdigest()


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackLiveCausalEvidence:
    recognition: AuditoryKrimelackStreamRecognition
    prepared_exemplars: tuple[
        AuditoryKrimelackPreparedExemplar, ...
    ]
    auditory_experiences: tuple[AuditoryL5Experience, ...]
    stream_settlements: tuple[
        AuditoryStreamSettlementReceipt, ...
    ]
    causal_settlements: tuple[CausalExperienceSettlement, ...]

    def verify(self) -> None:
        self.recognition.verify()
        count = len(self.recognition.component_experience_ids)
        if (
            self.recognition.state
            is not AuditoryKrimelackStreamState.UNIQUE
            or not 1
            <= count
            <= MAX_AUDITORY_KRIMELACK_STREAM_COMPONENTS
            or len(self.prepared_exemplars) != count
            or len(self.auditory_experiences) != count
            or len(self.stream_settlements) != count
            or len(self.causal_settlements) != count
        ):
            raise ValueError(
                "auditory live causal evidence is not uniquely recognized"
            )
        for ordinal, (
            prepared_exemplar,
            experience,
            stream,
            causal,
        ) in enumerate(zip(
            self.prepared_exemplars,
            self.auditory_experiences,
            self.stream_settlements,
            self.causal_settlements,
            strict=True,
        )):
            prepared_exemplar.verify_linkage(experience)
            stream.verify()
            causal.verify()
            if (
                self.recognition.component_experience_ids[ordinal]
                != experience.experience_id
                or self.recognition.component_path_receipts[ordinal]
                != prepared_exemplar.exemplar.path
                .authority_receipt_sha256
                or self.recognition.component_full_dsf_receipts[ordinal]
                != prepared_exemplar.exemplar.full_dsf_authority
                .authority_receipt_sha256
            ):
                raise ValueError(
                    "auditory live causal evidence left recognition"
                )
        current = self.stream_settlements[-1]
        if (
            self.recognition.stream_id != current.stream_id
            or self.recognition.sequence != current.sequence
            or self.recognition.first_sample_index
            != current.first_sample_index
            or self.recognition.sample_count != current.sample_count
            or self.recognition.settlement_receipt_sha256
            != current.authority_receipt_sha256
        ):
            raise ValueError(
                "auditory live causal evidence left current settlement"
            )
        if count == 2 and not _continuous(
            self.stream_settlements[0],
            self.stream_settlements[1],
        ):
            raise ValueError(
                "auditory live causal evidence lost component continuity"
            )


def _component(
    *,
    auditory_l5: AuditoryL5Experience,
    stream_settlement: AuditoryStreamSettlementReceipt,
    causal_settlement: CausalExperienceSettlement,
    prepared_path: (
        AuditoryKrimelackPreparedPath | None
    ) = None,
    verified_capability: (
        AuditoryVerifiedSettlementCapability | None
    ) = None,
) -> AuditoryKrimelackRetainedCausalComponent:
    if not isinstance(auditory_l5, AuditoryL5Experience):
        raise TypeError(
            "auditory evidence preparation requires typed L5"
        )
    if prepared_path is None:
        prepared_path = prepare_auditory_krimelack_path(
            auditory_l5,
            verified_capability=verified_capability,
            joint_settlement=(
                stream_settlement
                if verified_capability is not None
                else None
            ),
        )
    elif verified_capability is not None:
        raise ValueError(
            "prepared path cannot be replaced by another capability"
        )
    if not isinstance(
        prepared_path,
        AuditoryKrimelackPreparedPath,
    ):
        raise TypeError(
            "auditory evidence preparation requires prepared path"
        )
    prepared_path.verify_linkage(auditory_l5)
    if not isinstance(
        stream_settlement,
        AuditoryStreamSettlementReceipt,
    ):
        raise TypeError(
            "auditory evidence preparation requires stream settlement"
        )
    stream_settlement.verify()
    if not isinstance(
        causal_settlement,
        CausalExperienceSettlement,
    ):
        raise TypeError(
            "auditory evidence preparation requires causal settlement"
        )
    verified_causal_transaction = None
    if verified_capability is None:
        causal_settlement.verify()
    else:
        verified_capability.verify_linkage(
            pcm_s16le=verified_capability.pcm_s16le,
            capture=verified_capability.capture,
            auditory_l5=auditory_l5,
            transport=verified_capability.transport,
            cochlear=verified_capability.cochlear,
            causal_settlement=causal_settlement,
            joint_settlement=stream_settlement,
        )
        verified_causal_transaction = (
            verified_capability.verified_causal_transaction
        )
        if verified_causal_transaction is None:
            causal_settlement.verify()
        else:
            verified_causal_transaction.verify_linkage(
                causal_settlement
            )
    if causal_settlement.language_events:
        raise ValueError(
            "auditory evidence buffer rejects transcript events"
        )
    if (
        stream_settlement.assembly_id != auditory_l5.assembly_id
        or causal_settlement.assembly_id != auditory_l5.assembly_id
        or stream_settlement.source_time_start
        != auditory_l5.source_time_start
        or stream_settlement.source_time_end
        != auditory_l5.source_time_end
        or causal_settlement.source_time_start
        != auditory_l5.source_time_start
        or causal_settlement.source_time_end
        != auditory_l5.source_time_end
        or stream_settlement
        .auditory_l5_authority_receipt_sha256
        != auditory_l5.authority_receipt_sha256
        or stream_settlement
        .causal_settlement_authority_receipt_sha256
        != causal_settlement.authority_receipt_sha256
    ):
        raise ValueError(
            "auditory evidence buffer authority linkage changed"
        )
    path = prepared_path.path
    causal_payload = causal_settlement.receipt_registry.resolve(
        causal_settlement.authority_receipt_sha256,
        "auditory evidence retained causal settlement",
    )
    if not causal_payload or len(causal_payload) > 2 * 1024 * 1024:
        raise RuntimeError(
            "auditory evidence causal authority exceeds its byte boundary"
        )
    causal_base64_bytes = 4 * ((len(causal_payload) + 2) // 3)
    result = AuditoryKrimelackRetainedCausalComponent(
        auditory_l5=auditory_l5,
        stream_settlement=stream_settlement,
        causal_settlement=causal_settlement,
        prepared_path=prepared_path,
        path_receipt_sha256=(
            path.authority_receipt_sha256
        ),
        authority_bytes=(
            prepared_path.encoded_bytes
            + causal_base64_bytes
            + len(_canonical({
                **stream_settlement.payload(),
                "authority_receipt_sha256": (
                    stream_settlement.authority_receipt_sha256
                ),
            }))
        ),
    )
    if not 1 <= result.authority_bytes <= (
        MAX_AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_COMPONENT_BYTES
    ):
        raise RuntimeError(
            "auditory evidence component byte capacity is full"
        )
    return result


def _continuous(
    prior: AuditoryStreamSettlementReceipt,
    current: AuditoryStreamSettlementReceipt,
) -> bool:
    return (
        current.stream_id == prior.stream_id
        and current.sequence == prior.sequence + 1
        and current.first_sample_index
        == prior.first_sample_index + prior.sample_count
        and current.prior_transport_receipt_sha256
        == prior.transport_receipt_sha256
        and current.source_time_start == prior.source_time_end
    )


class AuditoryKrimelackCausalEvidenceBufferOwner:
    """Own exact current/prior authorities for live recognition closure."""

    def __init__(
        self,
        *,
        log_event: Callable[..., None],
        stream_capacity: int = PCM_STREAM_CAPACITY,
        encoded_authority_capacity: int = (
            MAX_AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_BUFFER_BYTES
        ),
    ) -> None:
        if (
            isinstance(stream_capacity, bool)
            or not isinstance(stream_capacity, int)
            or not 1 <= stream_capacity <= PCM_STREAM_CAPACITY
            or isinstance(encoded_authority_capacity, bool)
            or not isinstance(encoded_authority_capacity, int)
            or not 1
            <= encoded_authority_capacity
            <= MAX_AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_BUFFER_BYTES
        ):
            raise ValueError(
                "auditory evidence buffer capacity is invalid"
            )
        self._log_event = log_event
        self._stream_capacity = stream_capacity
        self._encoded_authority_capacity = (
            encoded_authority_capacity
        )
        self._preparation_authority = object()
        self._lock = threading.RLock()
        self._streams: OrderedDict[
            str,
            tuple[AuditoryKrimelackRetainedCausalComponent, ...],
        ] = OrderedDict()

    def prepare(
        self,
        *,
        auditory_l5: AuditoryL5Experience,
        stream_settlement: AuditoryStreamSettlementReceipt,
        causal_settlement: CausalExperienceSettlement,
        verified_capability: (
            AuditoryVerifiedSettlementCapability | None
        ) = None,
    ) -> AuditoryKrimelackPreparedCausalComponent:
        component = _component(
            auditory_l5=auditory_l5,
            stream_settlement=stream_settlement,
            causal_settlement=causal_settlement,
            verified_capability=verified_capability,
        )
        result = AuditoryKrimelackPreparedCausalComponent(
            component=component,
            preparation_receipt_sha256=(
                _preparation_receipt(component)
            ),
            _construction_authority=self._preparation_authority,
        )
        return result

    @staticmethod
    def _recognition_components(
        *,
        recognition: AuditoryKrimelackStreamRecognition,
        retained: tuple[
            AuditoryKrimelackRetainedCausalComponent, ...
        ],
    ) -> tuple[
        AuditoryKrimelackRetainedCausalComponent, ...
    ]:
        by_id = {
            value.auditory_l5.experience_id: value
            for value in retained
        }
        try:
            selected = tuple(
                by_id[experience_id]
                for experience_id
                in recognition.component_experience_ids
            )
        except KeyError as error:
            raise ValueError(
                "auditory recognition prior typed authority is absent"
            ) from error
        if len(selected) != len(set(
            recognition.component_experience_ids
        )):
            raise ValueError(
                "auditory recognition repeats a component"
            )
        for ordinal, component in enumerate(selected):
            if (
                component.path_receipt_sha256
                != recognition.component_path_receipts[ordinal]
            ):
                raise ValueError(
                    "auditory recognition component authority changed"
                )
            if recognition.state is AuditoryKrimelackStreamState.UNIQUE:
                prepared_full = (
                    recognition.prepared_full_dsf_exemplars[ordinal]
                )
                prepared_full.verify_linkage(
                    component.auditory_l5
                )
                if (
                    prepared_full.exemplar.full_dsf_authority
                    .authority_receipt_sha256
                    != recognition.component_full_dsf_receipts[ordinal]
                ):
                    raise ValueError(
                        "auditory recognition full DSF authority changed"
                    )
        return selected

    def commit(
        self,
        *,
        prepared: AuditoryKrimelackPreparedCausalComponent,
        recognition: AuditoryKrimelackStreamRecognition,
    ) -> AuditoryKrimelackLiveCausalEvidence | None:
        if not isinstance(
            prepared,
            AuditoryKrimelackPreparedCausalComponent,
        ):
            raise TypeError(
                "auditory evidence buffer requires preparation"
            )
        if not isinstance(
            recognition,
            AuditoryKrimelackStreamRecognition,
        ):
            raise TypeError(
                "auditory evidence buffer requires recognition"
            )
        if (
            prepared._construction_authority
            is not self._preparation_authority
            or prepared.preparation_receipt_sha256
            != _preparation_receipt(prepared.component)
        ):
            raise ValueError(
                "auditory evidence preparation authority changed"
            )
        recognition.verify()
        current = prepared.component
        stream = current.stream_settlement
        if (
            recognition.stream_id != stream.stream_id
            or recognition.sequence != stream.sequence
            or recognition.first_sample_index
            != stream.first_sample_index
            or recognition.sample_count != stream.sample_count
            or recognition.settlement_receipt_sha256
            != stream.authority_receipt_sha256
            or recognition.component_experience_ids[-1]
            != current.auditory_l5.experience_id
        ):
            raise ValueError(
                "auditory evidence preparation left recognition"
            )
        with self._lock:
            prior_values = self._streams.get(stream.stream_id, ())
            prior = prior_values[-1] if prior_values else None
            continuous = (
                prior is not None
                and _continuous(
                    prior.stream_settlement,
                    stream,
                )
            )
            if recognition.state is (
                AuditoryKrimelackStreamState.DISCONTINUITY
            ):
                if stream.sequence == 0 or continuous:
                    raise ValueError(
                        "auditory evidence discontinuity changed"
                    )
                prospective = OrderedDict(self._streams)
                prospective.pop(stream.stream_id, None)
                retained = ()
                evidence = None
            else:
                if stream.sequence == 0:
                    retained = (current,)
                elif continuous:
                    retained = (prior, current)
                else:
                    raise ValueError(
                        "auditory recognition prior typed authority is absent"
                    )
                selected = self._recognition_components(
                    recognition=recognition,
                    retained=retained,
                )
                prospective = OrderedDict(self._streams)
                if (
                    stream.stream_id not in prospective
                    and len(prospective) >= self._stream_capacity
                ):
                    raise RuntimeError(
                        "auditory evidence stream capacity is full"
                    )
                prospective[stream.stream_id] = retained
                prospective.move_to_end(stream.stream_id)
                total_bytes = sum(
                    component.authority_bytes
                    for components in prospective.values()
                    for component in components
                )
                if total_bytes > self._encoded_authority_capacity:
                    raise RuntimeError(
                        "auditory evidence byte capacity is full"
                    )
                evidence = (
                    AuditoryKrimelackLiveCausalEvidence(
                        recognition=recognition,
                        prepared_exemplars=(
                            recognition
                            .prepared_full_dsf_exemplars
                        ),
                        auditory_experiences=tuple(
                            value.auditory_l5 for value in selected
                        ),
                        stream_settlements=tuple(
                            value.stream_settlement
                            for value in selected
                        ),
                        causal_settlements=tuple(
                            value.causal_settlement
                            for value in selected
                        ),
                    )
                    if recognition.state
                    is AuditoryKrimelackStreamState.UNIQUE
                    else None
                )
            self._log_event(
                "auditory_krimelack_causal_evidence_committed",
                component_count=len(retained),
                recognition_state=recognition.state.value,
                stream_id=stream.stream_id,
            )
            self._streams = prospective
        return evidence

    def close_stream(self, stream_id: str) -> bool:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError(
                "auditory evidence buffer stream id is required"
            )
        with self._lock:
            return self._streams.pop(stream_id, None) is not None

    def clear(self) -> int:
        """Discard every transient stream component across a state boundary."""
        with self._lock:
            cleared = len(self._streams)
            self._streams.clear()
            return cleared

    def status(self) -> dict[str, object]:
        with self._lock:
            components = tuple(
                value
                for retained in self._streams.values()
                for value in retained
            )
            return {
                "authority_bytes": sum(
                    value.authority_bytes for value in components
                ),
                "component_capacity_per_stream": (
                    MAX_AUDITORY_KRIMELACK_STREAM_COMPONENTS
                ),
                "retained_component_count": len(components),
                "schema": (
                    AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_BUFFER_SCHEMA
                ),
                "stream_capacity": self._stream_capacity,
                "stream_count": len(self._streams),
                "transient": True,
            }


__all__ = (
    "AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_BUFFER_SCHEMA",
    "AuditoryKrimelackCausalEvidenceBufferOwner",
    "AuditoryKrimelackLiveCausalEvidence",
    "AuditoryKrimelackPreparedCausalComponent",
    "AuditoryKrimelackRetainedCausalComponent",
    "MAX_AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_BUFFER_BYTES",
    "MAX_AUDITORY_KRIMELACK_CAUSAL_EVIDENCE_COMPONENT_BYTES",
)
