"""Bounded exact coordinator for separated room-hearing occurrences.

Successful coordination has one currently admitted route:

1. verify an authenticated W1 two-emitter binaural capture;
2. mount the actual left/right mixture through complete auditory L0--L4/L5;
3. invoke exact path-conditioned source separation;
4. mount each recovered pressure cause independently through complete
   auditory L0--L4/L5;
5. emit exactly two anonymous, authority-receipted auditory occurrences.

The browser route is present only as a truthful refusal boundary.  The current
dual-channel browser transport proves two discrete byte lineages and one
sample clock, but explicitly does not prove two physical microphones.
Therefore it cannot enter cognition here.  Mono pressure, unattributed
binaural pressure, unknown acoustic paths, and blind-separation requests also
produce typed no-release outcomes.

No transcript, token, label, chi, source identity, probability, tolerance,
learned classifier, or reduced DSF projection participates.  Every successful
occurrence retains the complete explicit D_k, M_k, R_rev_k, U_star_k, C_k,
P_k, and B_k fields.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    AcceptedBrowserBinauralPCMChunk,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    REQUIRED_SAMPLE_RATE_HZ,
)
from dsf_ai_service.substrate.w1_authenticated_multi_emitter_capture import (
    W1AuthenticatedMultiEmitterBinauralCapture,
    W1MultiEmitterCaptureState,
    mount_authenticated_multi_emitter_binaural_l5,
    separate_authenticated_multi_emitter_capture,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Experience,
)
from dsf_ai_service.substrate.w1_exact_binaural_source_separation import (
    ExactBinauralSeparationState,
    ExactSeparatedAuditoryField,
    mount_exact_separated_auditory_fields,
)


BINAURAL_ROOM_HEARING_OCCURRENCE_SCHEMA = (
    "guala.binaural_room_hearing_occurrence.v1"
)
BINAURAL_ROOM_HEARING_OUTCOME_SCHEMA = (
    "guala.binaural_room_hearing_outcome.v1"
)
BINAURAL_ROOM_HEARING_DOMAIN = (
    b"guala-binaural-room-hearing-coordinator-v1\0"
)
BINAURAL_ROOM_OCCURRENCE_DOMAIN = (
    b"guala-binaural-room-hearing-occurrence-v1\0"
)
ROOM_HEARING_SOURCE_COUNT = 2


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


def _key(value: bytes | str, name: str) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError(f"{name} must be bytes or text")
    if not 32 <= len(result) <= 4_096:
        raise ValueError(f"{name} is outside its exact boundary")
    return result


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


class BinauralRoomHearingState(str, Enum):
    SEPARATED_OCCURRENCES = "separated_occurrences"
    REFUSED_UNPROVEN_BROWSER_HARDWARE = (
        "refused_unproven_browser_hardware"
    )
    REFUSED_MONO = "refused_mono"
    REFUSED_UNKNOWN_PATHS = "refused_unknown_paths"
    REFUSED_BLIND_SEPARATION = "refused_blind_separation"
    INDETERMINATE_PHYSICAL_SEPARATION = (
        "indeterminate_physical_separation"
    )


_STATE_REASON = {
    BinauralRoomHearingState.SEPARATED_OCCURRENCES: (
        "authenticated_two_ear_field_yielded_two_exact_path_occurrences"
    ),
    BinauralRoomHearingState.REFUSED_UNPROVEN_BROWSER_HARDWARE: (
        "discrete_browser_bytes_do_not_prove_two_physical_microphones"
    ),
    BinauralRoomHearingState.REFUSED_MONO: (
        "one_pressure_channel_cannot_become_binaural_room_hearing"
    ),
    BinauralRoomHearingState.REFUSED_UNKNOWN_PATHS: (
        "binaural_pressure_without_authenticated_paths_cannot_be_separated"
    ),
    BinauralRoomHearingState.REFUSED_BLIND_SEPARATION: (
        "blind_source_separation_is_not_an_admitted_deterministic_operation"
    ),
    BinauralRoomHearingState.INDETERMINATE_PHYSICAL_SEPARATION: (
        "authenticated_physical_evidence_did_not_yield_one_exact_source_pair"
    ),
}


@dataclass(frozen=True, slots=True)
class BinauralRoomAuditoryOccurrence:
    source_ordinal: int
    upstream_capture_receipt_sha256: str
    separation_receipt_sha256: str
    separated_field: ExactSeparatedAuditoryField
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def authority_payload(self) -> dict[str, object]:
        return {
            "auditory_l5_authority_receipt_sha256": (
                self.separated_field
                .auditory_l5.authority_receipt_sha256
            ),
            "schema": BINAURAL_ROOM_HEARING_OCCURRENCE_SCHEMA,
            "separated_field_authority_receipt_sha256": (
                self.separated_field.authority_receipt_sha256
            ),
            "separation_receipt_sha256": (
                self.separation_receipt_sha256
            ),
            "source_ordinal": self.source_ordinal,
            "upstream_capture_receipt_sha256": (
                self.upstream_capture_receipt_sha256
            ),
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(
            authority_key,
            "binaural room occurrence authority key",
        )
        self.separated_field.verify()
        if (
            isinstance(self.source_ordinal, bool)
            or not isinstance(self.source_ordinal, int)
            or not 0 <= self.source_ordinal < ROOM_HEARING_SOURCE_COUNT
            or self.source_ordinal
            != self.separated_field.source_ordinal
        ):
            raise ValueError("binaural room occurrence ordinal changed")
        _sha256(
            self.upstream_capture_receipt_sha256,
            "binaural room upstream capture",
        )
        _sha256(
            self.separation_receipt_sha256,
            "binaural room exact separation",
        )
        for channel in self.separated_field.auditory_l5.channels:
            for component in (
                channel.pressure,
                channel.carrier_phase_advance,
            ):
                if any(
                    tuple(name for name, _value in field_tuple.fields)
                    != DSF_FIELD_ORDER
                    for field_tuple in component.l4_field_tuples
                ):
                    raise ValueError(
                        "binaural room occurrence lost explicit DSF fields"
                    )
        payload = self.authority_payload()
        expected_hmac = hmac.new(
            key,
            BINAURAL_ROOM_OCCURRENCE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError(
                "binaural room occurrence authority changed"
            )


@dataclass(frozen=True, slots=True)
class BinauralRoomHearingOutcome:
    state: BinauralRoomHearingState
    reason: str
    evidence_kind: str
    evidence_receipt_sha256: str
    mixture_auditory_l5: W1BinauralAuditoryL5Experience | None
    separation_receipt_sha256: str | None
    occurrences: tuple[BinauralRoomAuditoryOccurrence, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def authority_payload(self) -> dict[str, object]:
        return {
            "evidence_kind": self.evidence_kind,
            "evidence_receipt_sha256": self.evidence_receipt_sha256,
            "mixture_auditory_l5_authority_receipt_sha256": (
                self.mixture_auditory_l5.authority_receipt_sha256
                if self.mixture_auditory_l5 is not None else None
            ),
            "occurrence_authority_receipt_sha256s": [
                value.authority_receipt_sha256
                for value in self.occurrences
            ],
            "reason": self.reason,
            "schema": BINAURAL_ROOM_HEARING_OUTCOME_SCHEMA,
            "separation_receipt_sha256": (
                self.separation_receipt_sha256
            ),
            "state": self.state.value,
        }

    def verify(self, authority_key: bytes | str) -> None:
        key = _key(
            authority_key,
            "binaural room hearing authority key",
        )
        if (
            not isinstance(self.state, BinauralRoomHearingState)
            or self.reason != _STATE_REASON[self.state]
            or self.evidence_kind not in (
                "authenticated_w1_multi_emitter",
                "browser_discrete_transport",
                "mono_pressure",
                "unattributed_binaural_pressure",
            )
        ):
            raise ValueError("binaural room hearing state changed")
        _sha256(
            self.evidence_receipt_sha256,
            "binaural room evidence",
        )
        if (
            self.state
            is BinauralRoomHearingState.SEPARATED_OCCURRENCES
        ):
            if (
                self.evidence_kind
                != "authenticated_w1_multi_emitter"
                or self.mixture_auditory_l5 is None
                or self.separation_receipt_sha256 is None
                or len(self.occurrences) != ROOM_HEARING_SOURCE_COUNT
                or tuple(
                    value.source_ordinal
                    for value in self.occurrences
                )
                != tuple(range(ROOM_HEARING_SOURCE_COUNT))
            ):
                raise ValueError(
                    "successful binaural room hearing is incomplete"
                )
            self.mixture_auditory_l5.verify()
            _sha256(
                self.separation_receipt_sha256,
                "binaural room separation",
            )
            for value in self.occurrences:
                value.verify(key)
                if (
                    value.upstream_capture_receipt_sha256
                    != self.evidence_receipt_sha256
                    or value.separation_receipt_sha256
                    != self.separation_receipt_sha256
                ):
                    raise ValueError(
                        "binaural room occurrence left its evidence"
                    )
        elif (
            self.mixture_auditory_l5 is not None
            or self.separation_receipt_sha256 is not None
            or self.occurrences
        ):
            raise ValueError(
                "refused binaural room evidence released cognition"
            )
        payload = self.authority_payload()
        expected_hmac = hmac.new(
            key,
            BINAURAL_ROOM_HEARING_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ):
            raise ValueError(
                "binaural room hearing authority changed"
            )


class BinauralRoomHearingCoordinator:
    """Bounded no-history owner of exact room-hearing outcomes."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        w1_capture_authority_key: bytes | str,
    ) -> None:
        self._key = _key(
            authority_key,
            "binaural room hearing authority key",
        )
        self._w1_capture_key = _key(
            w1_capture_authority_key,
            "W1 multi-emitter capture authority key",
        )
        self._lock = threading.RLock()
        self._separated = 0
        self._refused = 0
        self._indeterminate = 0

    def _outcome(
        self,
        *,
        state: BinauralRoomHearingState,
        evidence_kind: str,
        evidence_receipt_sha256: str,
        mixture_auditory_l5: (
            W1BinauralAuditoryL5Experience | None
        ) = None,
        separation_receipt_sha256: str | None = None,
        occurrences: tuple[
            BinauralRoomAuditoryOccurrence, ...
        ] = (),
    ) -> BinauralRoomHearingOutcome:
        draft = BinauralRoomHearingOutcome(
            state=state,
            reason=_STATE_REASON[state],
            evidence_kind=evidence_kind,
            evidence_receipt_sha256=evidence_receipt_sha256,
            mixture_auditory_l5=mixture_auditory_l5,
            separation_receipt_sha256=separation_receipt_sha256,
            occurrences=occurrences,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = draft.authority_payload()
        signature = hmac.new(
            self._key,
            BINAURAL_ROOM_HEARING_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = BinauralRoomHearingOutcome(
            state=draft.state,
            reason=draft.reason,
            evidence_kind=draft.evidence_kind,
            evidence_receipt_sha256=(
                draft.evidence_receipt_sha256
            ),
            mixture_auditory_l5=draft.mixture_auditory_l5,
            separation_receipt_sha256=(
                draft.separation_receipt_sha256
            ),
            occurrences=draft.occurrences,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result.verify(self._key)
        with self._lock:
            if (
                state
                is BinauralRoomHearingState.SEPARATED_OCCURRENCES
            ):
                self._separated += 1
            elif (
                state
                is BinauralRoomHearingState
                .INDETERMINATE_PHYSICAL_SEPARATION
            ):
                self._indeterminate += 1
            else:
                self._refused += 1
        return result

    def hear_authenticated_w1_capture(
        self,
        capture: W1AuthenticatedMultiEmitterBinauralCapture,
    ) -> BinauralRoomHearingOutcome:
        capture.verify(self._w1_capture_key)
        if capture.state is not W1MultiEmitterCaptureState.CAPTURED:
            return self._outcome(
                state=(
                    BinauralRoomHearingState
                    .INDETERMINATE_PHYSICAL_SEPARATION
                ),
                evidence_kind="authenticated_w1_multi_emitter",
                evidence_receipt_sha256=(
                    capture.authority_receipt_sha256
                ),
            )
        mixture = mount_authenticated_multi_emitter_binaural_l5(
            capture,
            authority_key=self._w1_capture_key,
        )
        separation = separate_authenticated_multi_emitter_capture(
            capture,
            authority_key=self._w1_capture_key,
        )
        if (
            separation.state
            is not ExactBinauralSeparationState.SEPARATED
        ):
            return self._outcome(
                state=(
                    BinauralRoomHearingState
                    .INDETERMINATE_PHYSICAL_SEPARATION
                ),
                evidence_kind="authenticated_w1_multi_emitter",
                evidence_receipt_sha256=(
                    capture.authority_receipt_sha256
                ),
            )
        separated_fields = mount_exact_separated_auditory_fields(
            separation,
            source_time_start=Fraction(
                capture.source_sample_start,
                REQUIRED_SAMPLE_RATE_HZ,
            ),
        )
        if len(separated_fields) != ROOM_HEARING_SOURCE_COUNT:
            raise RuntimeError(
                "exact room hearing released the wrong occurrence count"
            )
        occurrences = []
        for field in separated_fields:
            payload = {
                "auditory_l5_authority_receipt_sha256": (
                    field.auditory_l5.authority_receipt_sha256
                ),
                "schema": BINAURAL_ROOM_HEARING_OCCURRENCE_SCHEMA,
                "separated_field_authority_receipt_sha256": (
                    field.authority_receipt_sha256
                ),
                "separation_receipt_sha256": (
                    separation.authority_receipt_sha256
                ),
                "source_ordinal": field.source_ordinal,
                "upstream_capture_receipt_sha256": (
                    capture.authority_receipt_sha256
                ),
            }
            signature = hmac.new(
                self._key,
                BINAURAL_ROOM_OCCURRENCE_DOMAIN + _canonical(payload),
                hashlib.sha256,
            ).hexdigest()
            occurrence = BinauralRoomAuditoryOccurrence(
                source_ordinal=field.source_ordinal,
                upstream_capture_receipt_sha256=(
                    capture.authority_receipt_sha256
                ),
                separation_receipt_sha256=(
                    separation.authority_receipt_sha256
                ),
                separated_field=field,
                authority_hmac_sha256=signature,
                authority_receipt_sha256=_digest({
                    "authority_hmac_sha256": signature,
                    "payload": payload,
                }),
            )
            occurrence.verify(self._key)
            occurrences.append(occurrence)
        return self._outcome(
            state=BinauralRoomHearingState.SEPARATED_OCCURRENCES,
            evidence_kind="authenticated_w1_multi_emitter",
            evidence_receipt_sha256=(
                capture.authority_receipt_sha256
            ),
            mixture_auditory_l5=mixture,
            separation_receipt_sha256=(
                separation.authority_receipt_sha256
            ),
            occurrences=tuple(occurrences),
        )

    def hear_browser_transport(
        self,
        accepted: AcceptedBrowserBinauralPCMChunk,
    ) -> BinauralRoomHearingOutcome:
        accepted.verify()
        if (
            accepted.receipt.binaural_hardware_authority_proven
            or accepted.lineage.binaural_hardware_authority_proven
        ):
            raise ValueError(
                "unsupported browser receipt claimed hardware authority"
            )
        return self._outcome(
            state=(
                BinauralRoomHearingState
                .REFUSED_UNPROVEN_BROWSER_HARDWARE
            ),
            evidence_kind="browser_discrete_transport",
            evidence_receipt_sha256=accepted.receipt.receipt_sha256,
        )

    def hear_mono_pcm(
        self,
        pcm_s16le: bytes,
    ) -> BinauralRoomHearingOutcome:
        if (
            not isinstance(pcm_s16le, bytes)
            or not pcm_s16le
            or len(pcm_s16le) % 2
        ):
            raise ValueError(
                "room-hearing mono pressure must be signed PCM16"
            )
        return self._outcome(
            state=BinauralRoomHearingState.REFUSED_MONO,
            evidence_kind="mono_pressure",
            evidence_receipt_sha256=hashlib.sha256(
                pcm_s16le
            ).hexdigest(),
        )

    def hear_unattributed_binaural_pcm(
        self,
        *,
        left_pcm_s16le: bytes,
        right_pcm_s16le: bytes,
        request_blind_separation: bool,
    ) -> BinauralRoomHearingOutcome:
        if not isinstance(request_blind_separation, bool):
            raise TypeError(
                "blind-separation request flag must be boolean"
            )
        for value in (left_pcm_s16le, right_pcm_s16le):
            if (
                not isinstance(value, bytes)
                or not value
                or len(value) % 2
            ):
                raise ValueError(
                    "unattributed binaural pressure must be signed PCM16"
                )
        if len(left_pcm_s16le) != len(right_pcm_s16le):
            raise ValueError(
                "unattributed binaural channels left their shared clock"
            )
        evidence_receipt = _digest({
            "left_pcm_sha256": hashlib.sha256(
                left_pcm_s16le
            ).hexdigest(),
            "right_pcm_sha256": hashlib.sha256(
                right_pcm_s16le
            ).hexdigest(),
            "sample_count": len(left_pcm_s16le) // 2,
        })
        return self._outcome(
            state=(
                BinauralRoomHearingState.REFUSED_BLIND_SEPARATION
                if request_blind_separation
                else BinauralRoomHearingState.REFUSED_UNKNOWN_PATHS
            ),
            evidence_kind="unattributed_binaural_pressure",
            evidence_receipt_sha256=evidence_receipt,
        )

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "indeterminate": self._indeterminate,
                "max_occurrences_per_outcome": (
                    ROOM_HEARING_SOURCE_COUNT
                ),
                "refused": self._refused,
                "retained_raw_media_bytes": 0,
                "schema": (
                    "guala.binaural_room_hearing_coordinator_status.v1"
                ),
                "separated": self._separated,
            }


__all__ = [
    "BINAURAL_ROOM_HEARING_OCCURRENCE_SCHEMA",
    "BINAURAL_ROOM_HEARING_OUTCOME_SCHEMA",
    "BinauralRoomAuditoryOccurrence",
    "BinauralRoomHearingCoordinator",
    "BinauralRoomHearingOutcome",
    "BinauralRoomHearingState",
    "ROOM_HEARING_SOURCE_COUNT",
]
