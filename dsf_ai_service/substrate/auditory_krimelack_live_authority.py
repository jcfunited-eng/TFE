"""Live bounded authority for substrate-true auditory kind observation.

This is the engine-facing replacement boundary for the legacy whole-capture
classifier. It owns one ``AuditoryKrimelackStreamOwner`` and exposes only:

* tutor designation of an already observed physical kind;
* isolated or continuous kind observation;
* bounded exact persistence of learned kinds;
* truthful status suitable for the observational UI.

It does not create word meaning, infer a speaker, inspect a transcript, query
Atlas, use chi as identity, or release a causal action. A unique auditory kind
is a perceived form only. Later causal association must independently bind
that occurrence to experience and action.
"""

from __future__ import annotations

import base64
import hashlib
import json
import threading
from dataclasses import dataclass

from dsf_ai_service.glew_runtime.model import sha256_digest
from dsf_ai_service.substrate.auditory_krimelack_memory import (
    MAX_AUDITORY_KRIMELACK_MEMORY_BYTES,
    AuditoryKrimelackPreparedExemplar,
    AuditoryKrimelackPreparedPath,
    AuditoryKrimelackRecognitionState,
)
from dsf_ai_service.substrate.auditory_krimelack_stream import (
    AUDITORY_KRIMELACK_STREAM_OPERATOR,
    AuditoryKrimelackStreamOwner,
    AuditoryKrimelackStreamRecognition,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Experience
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.auditory_tutor_authority import (
    AuditoryTutorAuthority,
    canonical_tutor_label,
)


AUDITORY_KRIMELACK_LIVE_AUTHORITY_SCHEMA = (
    "guala.auditory.krimelack_live_authority.v1"
)
AUDITORY_KRIMELACK_LIVE_PERSISTENCE_SCHEMA = (
    "guala.auditory.krimelack_live_persistence.v2"
)
AUDITORY_KRIMELACK_TEACHING_SCHEMA = (
    "guala.auditory.krimelack_teaching.v1"
)
AUDITORY_KRIMELACK_KIND_NAME = "spoken_form"
MAX_AUDITORY_KRIMELACK_LIVE_PERSISTENCE_BYTES = 64 * 1024 * 1024
AUDITORY_KRIMELACK_LIVE_ENVELOPE_RESERVE_BYTES = 4096
MAX_AUDITORY_KRIMELACK_LIVE_MEMORY_PAYLOAD_BYTES = (
    MAX_AUDITORY_KRIMELACK_LIVE_PERSISTENCE_BYTES
    - AUDITORY_KRIMELACK_LIVE_ENVELOPE_RESERVE_BYTES
)


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


@dataclass(frozen=True, slots=True)
class AuditoryKrimelackTeaching:
    experience_id: str
    kind_id: str
    tutor_label: str
    reinforcement_count: int
    exemplar_count: int
    kind_authority_receipt_sha256: str
    recognition_authority_receipt_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "exemplar_count": self.exemplar_count,
            "experience_id": self.experience_id,
            "kind": AUDITORY_KRIMELACK_KIND_NAME,
            "kind_authority_receipt_sha256": (
                self.kind_authority_receipt_sha256
            ),
            "kind_id": self.kind_id,
            "recognition_authority_receipt_sha256": (
                self.recognition_authority_receipt_sha256
            ),
            "reinforcement_count": self.reinforcement_count,
            "schema": AUDITORY_KRIMELACK_TEACHING_SCHEMA,
            "tutor_label": self.tutor_label,
        }

    def verify(self) -> None:
        for value, name in (
            (self.experience_id, "experience"),
            (self.kind_id, "kind"),
            (
                self.kind_authority_receipt_sha256,
                "kind authority",
            ),
            (
                self.recognition_authority_receipt_sha256,
                "recognition authority",
            ),
            (self.authority_receipt_sha256, "teaching authority"),
        ):
            sha256_digest(
                value,
                f"auditory Krimelack teaching {name}",
            )
        if (
            canonical_tutor_label(self.tutor_label)
            != self.tutor_label
            or isinstance(self.reinforcement_count, bool)
            or not isinstance(self.reinforcement_count, int)
            or self.reinforcement_count <= 0
            or isinstance(self.exemplar_count, bool)
            or not isinstance(self.exemplar_count, int)
            or self.exemplar_count <= 0
            or self.exemplar_count > self.reinforcement_count
            or _digest(self.payload()) != self.authority_receipt_sha256
        ):
            raise ValueError(
                "auditory Krimelack teaching authority changed"
            )


class AuditoryKrimelackLiveAuthority:
    """One engine-facing serial owner for learned auditory form kinds."""

    def __init__(
        self,
        *,
        log_event,
        tutor_authority: AuditoryTutorAuthority | None = None,
        **boundaries,
    ) -> None:
        requested_memory_bytes = boundaries.pop(
            "max_encoded_bytes",
            MAX_AUDITORY_KRIMELACK_LIVE_MEMORY_PAYLOAD_BYTES,
        )
        if (
            isinstance(requested_memory_bytes, bool)
            or not isinstance(requested_memory_bytes, int)
            or not 1
            <= requested_memory_bytes
            <= MAX_AUDITORY_KRIMELACK_LIVE_MEMORY_PAYLOAD_BYTES
            or requested_memory_bytes
            > MAX_AUDITORY_KRIMELACK_MEMORY_BYTES
        ):
            raise ValueError(
                "auditory live memory leaves no persistence envelope reserve"
            )
        self._owner = AuditoryKrimelackStreamOwner(
            log_event=log_event,
            tutor_authority=tutor_authority,
            max_encoded_bytes=requested_memory_bytes,
            **boundaries,
        )
        self._latest_lock = threading.RLock()
        self._latest_stream_recognition: (
            AuditoryKrimelackStreamRecognition | None
        ) = None
        self._latest_isolated_recognition = None

    def issue_tutor_authority(
        self,
        *,
        experience_id: str,
        kind: str,
        tutor_label: str,
    ) -> dict[str, object] | None:
        if kind != AUDITORY_KRIMELACK_KIND_NAME:
            raise ValueError(
                "auditory Krimelack live authority accepts spoken_form only"
            )
        return self._owner.issue_tutor_authority(
            experience_id=experience_id,
            tutor_label=tutor_label,
        )

    def teach(
        self,
        experience: AuditoryL5Experience,
        *,
        kind: str,
        tutor_label: str,
        authority_receipt: object | None = None,
    ) -> AuditoryKrimelackTeaching:
        if kind != AUDITORY_KRIMELACK_KIND_NAME:
            raise ValueError(
                "auditory Krimelack live authority accepts spoken_form only"
            )
        learned = self._owner.teach(
            experience,
            tutor_label=tutor_label,
            authority_receipt=authority_receipt,
        )
        recognition = self._owner.recognize(experience)
        if (
            recognition.state
            is not AuditoryKrimelackRecognitionState.UNIQUE
            or recognition.selected_kind_id != learned.kind_id
            or recognition.tutor_label != learned.tutor_label
        ):
            raise RuntimeError(
                "taught auditory kind did not reciprocally recognize itself"
            )
        provisional = AuditoryKrimelackTeaching(
            experience_id=experience.experience_id,
            kind_id=learned.kind_id,
            tutor_label=learned.tutor_label,
            reinforcement_count=learned.reinforcement_count,
            exemplar_count=len(learned.exemplars),
            kind_authority_receipt_sha256=(
                learned.authority_receipt_sha256
            ),
            recognition_authority_receipt_sha256=(
                recognition.authority_receipt_sha256
            ),
            authority_receipt_sha256="",
        )
        result = AuditoryKrimelackTeaching(
            experience_id=provisional.experience_id,
            kind_id=provisional.kind_id,
            tutor_label=provisional.tutor_label,
            reinforcement_count=provisional.reinforcement_count,
            exemplar_count=provisional.exemplar_count,
            kind_authority_receipt_sha256=(
                provisional.kind_authority_receipt_sha256
            ),
            recognition_authority_receipt_sha256=(
                provisional.recognition_authority_receipt_sha256
            ),
            authority_receipt_sha256=_digest(
                provisional.payload()
            ),
        )
        result.verify()
        with self._latest_lock:
            self._latest_isolated_recognition = recognition
        return result

    def recognize_isolated(
        self,
        experience: AuditoryL5Experience,
    ):
        """Observe one explicit physical utterance without teaching it."""

        recognition = self._owner.recognize(experience)
        recognition.verify()
        with self._latest_lock:
            self._latest_isolated_recognition = recognition
        return recognition

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
        recognition = self._owner.advance(
            experience,
            settlement,
            prepared_path=prepared_path,
            prepared_exemplar=prepared_exemplar,
        )
        recognition.verify()
        with self._latest_lock:
            self._latest_stream_recognition = recognition
        return recognition

    def close_stream(self, stream_id: str) -> bool:
        return self._owner.close_stream(stream_id)

    def encoded_snapshot(self) -> dict[str, object]:
        """Persist the canonical memory object once, never double-base64."""

        encoded_memory = self._owner.encoded_snapshot()
        text = encoded_memory["payload_base64"]
        try:
            raw_memory = base64.b64decode(text, validate=True)
            memory = json.loads(raw_memory)
        except Exception as error:
            raise RuntimeError(
                "auditory live owner produced unreadable memory"
            ) from error
        if (
            base64.b64encode(raw_memory).decode("ascii") != text
            or hashlib.sha256(raw_memory).hexdigest()
            != encoded_memory["sha256"]
            or _canonical(memory) != raw_memory
        ):
            raise RuntimeError(
                "auditory live owner produced noncanonical memory"
            )
        payload = {
            "memory": memory,
            "memory_sha256": hashlib.sha256(raw_memory).hexdigest(),
            "schema": AUDITORY_KRIMELACK_LIVE_PERSISTENCE_SCHEMA,
        }
        result = {
            **payload,
            "sha256": _digest(payload),
        }
        if len(_canonical(result)) > (
            MAX_AUDITORY_KRIMELACK_LIVE_PERSISTENCE_BYTES
        ):
            raise RuntimeError(
                "auditory live persistence exceeds its byte boundary"
            )
        return result

    def restore_encoded(self, envelope: object) -> None:
        if (
            not isinstance(envelope, dict)
            or set(envelope)
            != {"memory", "memory_sha256", "schema", "sha256"}
            or envelope.get("schema")
            != AUDITORY_KRIMELACK_LIVE_PERSISTENCE_SCHEMA
            or not isinstance(envelope.get("memory"), dict)
            or len(_canonical(envelope))
            > MAX_AUDITORY_KRIMELACK_LIVE_PERSISTENCE_BYTES
        ):
            raise ValueError(
                "auditory Krimelack live persistence changed"
            )
        payload = {
            "memory": envelope["memory"],
            "memory_sha256": envelope.get("memory_sha256"),
            "schema": envelope["schema"],
        }
        raw_memory = _canonical(envelope["memory"])
        if (
            envelope.get("memory_sha256")
            != hashlib.sha256(raw_memory).hexdigest()
            or envelope.get("sha256") != _digest(payload)
        ):
            raise ValueError(
                "auditory Krimelack live persistence changed"
            )
        self._owner.restore_encoded({
            "payload_base64": base64.b64encode(
                raw_memory
            ).decode("ascii"),
            "sha256": hashlib.sha256(raw_memory).hexdigest(),
        })
        with self._latest_lock:
            self._latest_stream_recognition = None
            self._latest_isolated_recognition = None

    def status(self) -> dict[str, object]:
        memory = self._owner.status()
        stream = self._owner.stream_status()
        with self._latest_lock:
            latest_stream = self._latest_stream_recognition
            latest_isolated = self._latest_isolated_recognition
        if latest_stream is not None:
            latest = {
                "candidate_kind_ids": list(
                    latest_stream.candidate_kind_ids
                ),
                "candidate_labels": list(
                    latest_stream.candidate_labels
                ),
                "component_count": len(
                    latest_stream.component_path_receipts
                ),
                "experience_id": (
                    latest_stream.component_experience_ids[-1]
                ),
                "kind": AUDITORY_KRIMELACK_KIND_NAME,
                "recognition_authority_receipt_sha256": (
                    latest_stream.authority_receipt_sha256
                ),
                "selected_kind_id": latest_stream.selected_kind_id,
                "state": latest_stream.state.value,
                "tutor_label": latest_stream.tutor_label,
                "work_cells": latest_stream.work_cells,
            }
        elif latest_isolated is not None:
            latest = {
                "candidate_kind_ids": list(
                    latest_isolated.candidate_kind_ids
                ),
                "candidate_labels": list(
                    latest_isolated.candidate_labels
                ),
                "component_count": 1,
                "experience_id": latest_isolated.experience_id,
                "kind": AUDITORY_KRIMELACK_KIND_NAME,
                "recognition_authority_receipt_sha256": (
                    latest_isolated.authority_receipt_sha256
                ),
                "selected_kind_id": (
                    latest_isolated.selected_kind_id
                ),
                "state": latest_isolated.state.value,
                "tutor_label": latest_isolated.tutor_label,
                "work_cells": latest_isolated.work_cells,
            }
        else:
            latest = None
        return {
            "active": True,
            "causal_action_authority": False,
            "kind_memory": memory,
            "latest_recognition": latest,
            "meaning_authority": False,
            "mechanism": AUDITORY_KRIMELACK_STREAM_OPERATOR,
            "persistence_schema": (
                AUDITORY_KRIMELACK_LIVE_PERSISTENCE_SCHEMA
            ),
            "schema": AUDITORY_KRIMELACK_LIVE_AUTHORITY_SCHEMA,
            "stream": stream,
            "transcript_authority": False,
        }

    def assert_pristine(self) -> None:
        status = self.status()
        if (
            status["kind_memory"]["kind_count"]
            or status["kind_memory"]["exemplar_count"]
            or status["stream"]["active_streams"]
            or status["latest_recognition"] is not None
        ):
            raise ValueError(
                "auditory Krimelack live authority is not pristine"
            )


__all__ = (
    "AUDITORY_KRIMELACK_KIND_NAME",
    "AUDITORY_KRIMELACK_LIVE_AUTHORITY_SCHEMA",
    "AUDITORY_KRIMELACK_LIVE_ENVELOPE_RESERVE_BYTES",
    "AUDITORY_KRIMELACK_LIVE_PERSISTENCE_SCHEMA",
    "AUDITORY_KRIMELACK_TEACHING_SCHEMA",
    "MAX_AUDITORY_KRIMELACK_LIVE_MEMORY_PAYLOAD_BYTES",
    "MAX_AUDITORY_KRIMELACK_LIVE_PERSISTENCE_BYTES",
    "AuditoryKrimelackLiveAuthority",
    "AuditoryKrimelackTeaching",
)
