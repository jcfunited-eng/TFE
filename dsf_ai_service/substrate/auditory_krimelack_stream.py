"""Continuous Krimelack kind observation over exact auditory settlements.

Transport units are not word boundaries.  This owner first evaluates the
current auditory L5 experience.  If it is unknown and the immediately prior
unit has proven PCM, cochlear, L5, and causal-settlement continuity, the owner
also evaluates their ordered Krimelack path composition.

The composition contains no fabricated combined L5 field.  Each component is
retained as a verified ``AuditoryKrimelackExemplar`` with its complete compact
L0--L4 DSF authority.  Only the ordered balanced-ternary motifs are composed
for the auditory L5 relation.  Labels designate already learned kinds and
never enter this relation.

All live stream state is transient and bounded to one prior component per
stream.  A restart or discontinuity closes that composition authority.
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum

from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_krimelack_kind import (
    AuditoryComponentPaths,
    AuditoryKrimelackPath,
    _component_paths_relation,
    _relation_from_component_locks,
)
from dsf_ai_service.substrate.auditory_krimelack_memory import (
    MAX_AUDITORY_KRIMELACK_RECOGNITION_WORK_CELLS,
    AuditoryKrimelackExemplar,
    AuditoryKrimelackKind,
    AuditoryKrimelackMemoryOwner,
    AuditoryKrimelackPreparedExemplar,
    AuditoryKrimelackPreparedPath,
    finalize_auditory_krimelack_exemplar,
    prepare_auditory_krimelack_path,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Experience
from dsf_ai_service.substrate.auditory_pcm_stream import (
    PCM_STREAM_CAPACITY,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
AUDITORY_KRIMELACK_STREAM_RECOGNITION_SCHEMA = (
    "guala.auditory.krimelack_stream_recognition.v2"
)
AUDITORY_KRIMELACK_STREAM_OPERATOR = (
    "continuous_component_hierarchical_reciprocal_l6_v1"
)
MAX_AUDITORY_KRIMELACK_STREAM_COMPONENTS = 2


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


class AuditoryKrimelackStreamState(str, Enum):
    UNKNOWN = "unknown"
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"
    INDETERMINATE_RESOURCE = "indeterminate_resource"
    DISCONTINUITY = "discontinuity"


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackStreamRecognition:
    state: AuditoryKrimelackStreamState
    stream_id: str
    sequence: int
    first_sample_index: int
    sample_count: int
    component_experience_ids: tuple[str, ...]
    component_path_receipts: tuple[str, ...]
    component_full_dsf_receipts: tuple[str, ...]
    full_dsf_mount_state: str
    candidate_kind_ids: tuple[str, ...]
    candidate_labels: tuple[str, ...]
    selected_kind_id: str | None
    tutor_label: str | None
    work_cells: int
    settlement_receipt_sha256: str
    authority_receipt_sha256: str
    prepared_full_dsf_exemplars: tuple[
        AuditoryKrimelackPreparedExemplar, ...
    ] = field(default=(), compare=False, repr=False)

    def payload(self) -> dict[str, object]:
        return {
            "candidate_kind_ids": list(self.candidate_kind_ids),
            "candidate_labels": list(self.candidate_labels),
            "component_experience_ids": list(
                self.component_experience_ids
            ),
            "component_full_dsf_receipts": list(
                self.component_full_dsf_receipts
            ),
            "component_path_receipts": list(
                self.component_path_receipts
            ),
            "full_dsf_mount_state": self.full_dsf_mount_state,
            "first_sample_index": self.first_sample_index,
            "operator": AUDITORY_KRIMELACK_STREAM_OPERATOR,
            "sample_count": self.sample_count,
            "schema": AUDITORY_KRIMELACK_STREAM_RECOGNITION_SCHEMA,
            "selected_kind_id": self.selected_kind_id,
            "sequence": self.sequence,
            "settlement_receipt_sha256": (
                self.settlement_receipt_sha256
            ),
            "state": self.state.value,
            "stream_id": self.stream_id,
            "tutor_label": self.tutor_label,
            "work_cells": self.work_cells,
        }

    def verify(self) -> None:
        if (
            not isinstance(self.stream_id, str)
            or not self.stream_id
            or isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
            or isinstance(self.first_sample_index, bool)
            or not isinstance(self.first_sample_index, int)
            or self.first_sample_index < 0
            or isinstance(self.sample_count, bool)
            or not isinstance(self.sample_count, int)
            or self.sample_count <= 0
            or not 0
            <= self.work_cells
            <= MAX_AUDITORY_KRIMELACK_RECOGNITION_WORK_CELLS
            or not 1
            <= len(self.component_experience_ids)
            <= MAX_AUDITORY_KRIMELACK_STREAM_COMPONENTS
            or len(self.component_experience_ids)
            != len(self.component_path_receipts)
            or tuple(sorted(self.candidate_kind_ids))
            != self.candidate_kind_ids
            or len(self.candidate_kind_ids)
            != len(self.candidate_labels)
        ):
            raise ValueError(
                "auditory Krimelack stream recognition boundary changed"
            )
        for values, name in (
            (
                self.component_experience_ids,
                "component experience",
            ),
            (self.component_path_receipts, "component path"),
            (
                self.component_full_dsf_receipts,
                "component full DSF",
            ),
            (
                (self.settlement_receipt_sha256,),
                "settlement",
            ),
            (
                (self.authority_receipt_sha256,),
                "authority",
            ),
        ):
            for value in values:
                sha256_digest(
                    value,
                    f"auditory Krimelack stream {name}",
                )
        if self.state is AuditoryKrimelackStreamState.UNIQUE:
            if (
                len(self.candidate_kind_ids) != 1
                or self.selected_kind_id
                != self.candidate_kind_ids[0]
                or self.tutor_label != self.candidate_labels[0]
                or self.full_dsf_mount_state != "mounted_unique"
                or len(self.component_full_dsf_receipts)
                != len(self.component_experience_ids)
                or len(self.prepared_full_dsf_exemplars)
                != len(self.component_experience_ids)
            ):
                raise ValueError(
                    "unique auditory stream recognition changed"
                )
        elif self.state is AuditoryKrimelackStreamState.AMBIGUOUS:
            if (
                len(self.candidate_kind_ids) < 2
                or self.selected_kind_id is not None
                or self.tutor_label is not None
                or self.full_dsf_mount_state != "absent_non_unique"
                or self.component_full_dsf_receipts
                or self.prepared_full_dsf_exemplars
            ):
                raise ValueError(
                    "ambiguous auditory stream recognition changed"
                )
        elif (
            self.candidate_kind_ids
            or self.selected_kind_id is not None
            or self.tutor_label is not None
            or self.full_dsf_mount_state != "absent_non_unique"
            or self.component_full_dsf_receipts
            or self.prepared_full_dsf_exemplars
        ):
            raise ValueError(
                "non-unique auditory stream recognition released a kind"
            )
        if self.state is AuditoryKrimelackStreamState.UNIQUE:
            for ordinal, prepared in enumerate(
                self.prepared_full_dsf_exemplars
            ):
                if not isinstance(
                    prepared,
                    AuditoryKrimelackPreparedExemplar,
                ):
                    raise TypeError(
                        "unique auditory stream full DSF is not prepared"
                    )
                if (
                    prepared.exemplar.path.authority_receipt_sha256
                    != self.component_path_receipts[ordinal]
                    or prepared.exemplar.full_dsf_authority
                    .authority_receipt_sha256
                    != self.component_full_dsf_receipts[ordinal]
                ):
                    raise ValueError(
                        "unique auditory stream full DSF linkage changed"
                    )
        if (
            self.state
            in {
                AuditoryKrimelackStreamState
                .INDETERMINATE_RESOURCE,
                AuditoryKrimelackStreamState.DISCONTINUITY,
            }
            and self.work_cells != 0
        ):
            raise ValueError(
                "failed auditory stream recognition retained partial work"
            )
        if _digest(self.payload()) != self.authority_receipt_sha256:
            raise ValueError(
                "auditory Krimelack stream recognition receipt changed"
            )


@dataclass(frozen=True, slots=True)
class _PriorComponent:
    experience: AuditoryL5Experience
    path: AuditoryKrimelackPath
    prepared_path: AuditoryKrimelackPreparedPath | None
    prepared_exemplar: AuditoryKrimelackPreparedExemplar | None
    encoded_bytes: int
    settlement: AuditoryStreamSettlementReceipt


class AuditoryKrimelackStreamOwner(AuditoryKrimelackMemoryOwner):
    """Bounded learned memory plus one prior full-field unit per stream."""

    def __init__(
        self,
        *,
        log_event,
        stream_capacity: int = PCM_STREAM_CAPACITY,
        **memory_boundaries,
    ) -> None:
        super().__init__(
            log_event=log_event,
            **memory_boundaries,
        )
        if (
            isinstance(stream_capacity, bool)
            or not isinstance(stream_capacity, int)
            or not 1 <= stream_capacity <= PCM_STREAM_CAPACITY
        ):
            raise ValueError(
                "auditory Krimelack stream capacity is invalid"
            )
        self._stream_capacity = stream_capacity
        self._stream_lock = threading.RLock()
        self._streams: OrderedDict[str, _PriorComponent] = (
            OrderedDict()
        )
        self._stream_resource_exhaustions = 0
        self._stream_discontinuities = 0

    @staticmethod
    def _verify_linkage(
        experience: AuditoryL5Experience,
        settlement: AuditoryStreamSettlementReceipt,
        *,
        verify_experience: bool = True,
    ) -> None:
        if not isinstance(experience, AuditoryL5Experience):
            raise TypeError(
                "auditory Krimelack stream requires auditory L5"
            )
        if not isinstance(
            settlement,
            AuditoryStreamSettlementReceipt,
        ):
            raise TypeError(
                "auditory Krimelack stream requires joint settlement"
            )
        if verify_experience:
            experience.verify()
        settlement.verify()
        if (
            settlement.assembly_id != experience.assembly_id
            or settlement.auditory_l5_authority_receipt_sha256
            != experience.authority_receipt_sha256
            or settlement.source_time_start
            != experience.source_time_start
            or settlement.source_time_end != experience.source_time_end
        ):
            raise ValueError(
                "auditory Krimelack stream left its full-field settlement"
            )

    @staticmethod
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

    def _work_for_component_paths(
        self,
        component_paths: AuditoryComponentPaths,
    ) -> int:
        return sum(
            sum(
                len(query_component) * len(exemplar_component)
                for query_component, exemplar_component in zip(
                    component_paths,
                    exemplar.path.component_paths,
                    strict=True,
                )
            )
            for kind in self._kinds.values()
            for exemplar in kind.exemplars
        )

    @staticmethod
    def _kind_locks_component_paths(
        kind: AuditoryKrimelackKind,
        component_paths: AuditoryComponentPaths,
    ) -> bool:
        for exemplar in kind.exemplars:
            if _component_paths_relation(
                exemplar.path.component_paths,
                component_paths,
            ).locked:
                return True
        return False

    def _matched_for_component_paths(
        self,
        component_paths: AuditoryComponentPaths,
    ) -> tuple[AuditoryKrimelackKind, ...]:
        return tuple(sorted(
            (
                kind
                for kind in self._kinds.values()
                if self._kind_locks_component_paths(
                    kind,
                    component_paths,
                )
            ),
            key=lambda value: value.kind_id,
        ))

    @staticmethod
    def _kind_locks_composition(
        kind: AuditoryKrimelackKind,
        *,
        prior: AuditoryComponentPaths,
        current: AuditoryComponentPaths,
        composite: AuditoryComponentPaths,
    ) -> bool:
        for exemplar in kind.exemplars:
            reference = exemplar.path.component_paths
            composite_relation = _component_paths_relation(
                reference,
                composite,
            )
            prior_relation = _component_paths_relation(
                reference,
                prior,
            )
            current_relation = _component_paths_relation(
                reference,
                current,
            )
            locks = tuple(
                (
                    composite_relation.component_locks[index]
                    if index % 2 == 0
                    else (
                        composite_relation.component_locks[index]
                        or prior_relation.component_locks[index]
                        or current_relation.component_locks[index]
                    )
                )
                for index in range(len(reference))
            )
            relation = _relation_from_component_locks(
                locks,
                work_cells=(
                    composite_relation.work_cells
                    + prior_relation.work_cells
                    + current_relation.work_cells
                ),
            )
            if relation.locked:
                return True
        return False

    def _matched_for_composition(
        self,
        *,
        prior: AuditoryComponentPaths,
        current: AuditoryComponentPaths,
        composite: AuditoryComponentPaths,
    ) -> tuple[AuditoryKrimelackKind, ...]:
        return tuple(sorted(
            (
                kind
                for kind in self._kinds.values()
                if self._kind_locks_composition(
                    kind,
                    prior=prior,
                    current=current,
                    composite=composite,
                )
            ),
            key=lambda value: value.kind_id,
        ))

    @staticmethod
    def _state_for(
        matched: tuple[AuditoryKrimelackKind, ...],
    ) -> AuditoryKrimelackStreamState:
        return (
            AuditoryKrimelackStreamState.UNKNOWN
            if not matched
            else AuditoryKrimelackStreamState.UNIQUE
            if len(matched) == 1
            else AuditoryKrimelackStreamState.AMBIGUOUS
        )

    @staticmethod
    def _recognition(
        *,
        state: AuditoryKrimelackStreamState,
        settlement: AuditoryStreamSettlementReceipt,
        components: tuple[_PriorComponent, ...],
        matched: tuple[AuditoryKrimelackKind, ...] = (),
        work_cells: int,
    ) -> AuditoryKrimelackStreamRecognition:
        kind_ids = tuple(value.kind_id for value in matched)
        labels = tuple(value.tutor_label for value in matched)
        selected = (
            kind_ids[0]
            if state is AuditoryKrimelackStreamState.UNIQUE
            else None
        )
        label = (
            labels[0]
            if state is AuditoryKrimelackStreamState.UNIQUE
            else None
        )
        prepared_full_dsf_exemplars = ()
        if state is AuditoryKrimelackStreamState.UNIQUE:
            prepared_full_dsf_exemplars = tuple(
                (
                    value.prepared_exemplar
                    if value.prepared_exemplar is not None
                    else finalize_auditory_krimelack_exemplar(
                        value.experience,
                        value.prepared_path,
                    )
                    if value.prepared_path is not None
                    else None
                )
                for value in components
            )
            if any(
                value is None
                for value in prepared_full_dsf_exemplars
            ):
                raise RuntimeError(
                    "unique auditory stream lost retained full-field path"
                )
        provisional = AuditoryKrimelackStreamRecognition(
            state=state,
            stream_id=settlement.stream_id,
            sequence=settlement.sequence,
            first_sample_index=settlement.first_sample_index,
            sample_count=settlement.sample_count,
            component_experience_ids=tuple(
                value.experience.experience_id for value in components
            ),
            component_path_receipts=tuple(
                value.path.authority_receipt_sha256
                for value in components
            ),
            component_full_dsf_receipts=tuple(
                value.exemplar.full_dsf_authority
                .authority_receipt_sha256
                for value in prepared_full_dsf_exemplars
            ),
            full_dsf_mount_state=(
                "mounted_unique"
                if state is AuditoryKrimelackStreamState.UNIQUE
                else "absent_non_unique"
            ),
            candidate_kind_ids=kind_ids,
            candidate_labels=labels,
            selected_kind_id=selected,
            tutor_label=label,
            work_cells=work_cells,
            settlement_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            authority_receipt_sha256="",
            prepared_full_dsf_exemplars=(
                prepared_full_dsf_exemplars
            ),
        )
        result = AuditoryKrimelackStreamRecognition(
            state=provisional.state,
            stream_id=provisional.stream_id,
            sequence=provisional.sequence,
            first_sample_index=provisional.first_sample_index,
            sample_count=provisional.sample_count,
            component_experience_ids=(
                provisional.component_experience_ids
            ),
            component_path_receipts=(
                provisional.component_path_receipts
            ),
            component_full_dsf_receipts=(
                provisional.component_full_dsf_receipts
            ),
            full_dsf_mount_state=provisional.full_dsf_mount_state,
            candidate_kind_ids=provisional.candidate_kind_ids,
            candidate_labels=provisional.candidate_labels,
            selected_kind_id=provisional.selected_kind_id,
            tutor_label=provisional.tutor_label,
            work_cells=provisional.work_cells,
            settlement_receipt_sha256=(
                provisional.settlement_receipt_sha256
            ),
            authority_receipt_sha256=_digest(
                provisional.payload()
            ),
            prepared_full_dsf_exemplars=(
                prepared_full_dsf_exemplars
            ),
        )
        result.verify()
        return result

    def advance(
        self,
        experience: AuditoryL5Experience,
        settlement: AuditoryStreamSettlementReceipt,
        *,
        prepared_path: (
            AuditoryKrimelackPreparedPath | None
        ) = None,
        prepared_exemplar: (
            AuditoryKrimelackPreparedExemplar | None
        ) = None,
    ) -> AuditoryKrimelackStreamRecognition:
        """Evaluate one unit, then one exact two-unit composition if needed."""

        if (
            prepared_path is not None
            and prepared_exemplar is not None
        ):
            raise ValueError(
                "auditory stream received two prepared authorities"
            )
        if prepared_path is None and prepared_exemplar is None:
            prepared_path = prepare_auditory_krimelack_path(
                experience
            )
        if prepared_path is not None:
            if not isinstance(
                prepared_path,
                AuditoryKrimelackPreparedPath,
            ):
                raise TypeError(
                    "auditory stream requires prepared exact path"
                )
            prepared_path.verify_linkage(experience)
            current_path = prepared_path.path
            current_encoded_bytes = prepared_path.encoded_bytes
        else:
            if not isinstance(
                prepared_exemplar,
                AuditoryKrimelackPreparedExemplar,
            ):
                raise TypeError(
                    "auditory stream requires prepared exact exemplar"
                )
            prepared_exemplar.verify_linkage(experience)
            current_path = prepared_exemplar.exemplar.path
            current_encoded_bytes = (
                prepared_exemplar.full_dsf_encoded_bytes
            )
        self._verify_linkage(
            experience,
            settlement,
            verify_experience=False,
        )
        current = _PriorComponent(
            experience=experience,
            path=current_path,
            prepared_path=prepared_path,
            prepared_exemplar=prepared_exemplar,
            encoded_bytes=current_encoded_bytes,
            settlement=settlement,
        )
        with self._stream_lock:
            prior = self._streams.get(settlement.stream_id)
            if settlement.sequence == 0:
                prior = None
            elif prior is None or not self._continuous(
                prior.settlement,
                settlement,
            ):
                self._streams.pop(settlement.stream_id, None)
                self._stream_discontinuities += 1
                return self._recognition(
                    state=AuditoryKrimelackStreamState.DISCONTINUITY,
                    settlement=settlement,
                    components=(current,),
                    work_cells=0,
                )
            elif settlement.stream_id in self._streams:
                self._streams.move_to_end(settlement.stream_id)
            if (
                prior is None
                and settlement.stream_id not in self._streams
                and len(self._streams) >= self._stream_capacity
            ):
                raise RuntimeError(
                    "auditory Krimelack stream capacity is full"
                )

            with self._lock:
                current_work = self._work_for_component_paths(
                    current.path.component_paths
                )
                direct_allowed = experience.event_boundary == "utterance"
                if direct_allowed and current_work > self._max_work:
                    self._resource_exhaustions += 1
                    self._stream_resource_exhaustions += 1
                    result = self._recognition(
                        state=(
                            AuditoryKrimelackStreamState
                            .INDETERMINATE_RESOURCE
                        ),
                        settlement=settlement,
                        components=(current,),
                        work_cells=0,
                    )
                else:
                    matched = (
                        self._matched_for_component_paths(
                            current.path.component_paths
                        )
                        if direct_allowed else ()
                    )
                    state = self._state_for(matched)
                    components = (current,)
                    admitted_work = current_work if direct_allowed else 0
                    if (
                        state is AuditoryKrimelackStreamState.UNKNOWN
                        and prior is not None
                    ):
                        components = (prior, current)
                        composite_component_paths = tuple(
                            (
                                *prior_component,
                                *current_component,
                            )
                            for (
                                prior_component,
                                current_component,
                            ) in zip(
                                prior.path.component_paths,
                                current.path.component_paths,
                                strict=True,
                            )
                        )
                        composite_work = (
                            self._work_for_component_paths(
                                composite_component_paths
                            )
                        )
                        prior_work = self._work_for_component_paths(
                            prior.path.component_paths
                        )
                        composition_work = (
                            prior_work + current_work + composite_work
                        )
                        if (
                            composition_work > self._max_work
                        ):
                            self._resource_exhaustions += 1
                            self._stream_resource_exhaustions += 1
                            state = (
                                AuditoryKrimelackStreamState
                                .INDETERMINATE_RESOURCE
                            )
                            matched = ()
                            admitted_work = 0
                        else:
                            matched = self._matched_for_composition(
                                prior=(
                                    prior.path.component_paths
                                ),
                                current=current.path.component_paths,
                                composite=composite_component_paths,
                            )
                            state = self._state_for(matched)
                            admitted_work = composition_work
                    result = self._recognition(
                        state=state,
                        settlement=settlement,
                        components=components,
                        matched=matched,
                        work_cells=admitted_work,
                    )
            self._streams[settlement.stream_id] = current
            self._streams.move_to_end(settlement.stream_id)
        self._log_event(
            "auditory_krimelack_stream_observed",
            component_count=len(result.component_path_receipts),
            sequence=result.sequence,
            state=result.state.value,
            stream_id=result.stream_id,
            work_cells=result.work_cells,
        )
        return result

    def close_stream(self, stream_id: str) -> bool:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError(
                "auditory Krimelack stream id is required"
            )
        with self._stream_lock:
            return self._streams.pop(stream_id, None) is not None

    def stream_status(self) -> dict[str, int | str]:
        with self._stream_lock:
            retained = tuple(self._streams.values())
            return {
                "active_streams": len(retained),
                "component_capacity_per_stream": (
                    MAX_AUDITORY_KRIMELACK_STREAM_COMPONENTS
                ),
                "retained_component_count": len(retained),
                "retained_full_dsf_bytes": sum(
                    (
                        value.prepared_exemplar
                        .full_dsf_encoded_bytes
                        if value.prepared_exemplar is not None
                        else 0
                    )
                    for value in retained
                ),
                "retained_path_bytes": sum(
                    value.encoded_bytes for value in retained
                ),
                "schema": "guala.auditory.krimelack_stream.status.v2",
                "stream_capacity": self._stream_capacity,
                "stream_discontinuities": self._stream_discontinuities,
                "stream_resource_exhaustions": (
                    self._stream_resource_exhaustions
                ),
            }


__all__ = (
    "AUDITORY_KRIMELACK_STREAM_OPERATOR",
    "AUDITORY_KRIMELACK_STREAM_RECOGNITION_SCHEMA",
    "MAX_AUDITORY_KRIMELACK_STREAM_COMPONENTS",
    "AuditoryKrimelackStreamOwner",
    "AuditoryKrimelackStreamRecognition",
    "AuditoryKrimelackStreamState",
)
