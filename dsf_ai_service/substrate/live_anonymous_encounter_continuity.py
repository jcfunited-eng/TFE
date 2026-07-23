"""Bounded continuity for one live, anonymous audiovisual encounter.

This authority joins three already-authenticated facts from one causal window:
the complete visual L5 region settlement, the continuous auditory settlement,
and their shared six-sense assembly.  It may establish continuity of a visible
encounter.  It cannot establish that a visible region produced the sound.

The microphone is monaural, so ``acoustic_source`` is deliberately always
``unknown``.  Microphone stream ids, client source strings, chi routes, Atlas
addresses, and acoustic resemblance never become agent identity here.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.visual_region_continuity import (
    DeterministicVisualRegionContinuityAuthority,
    VisualL5Settlement,
)


LIVE_ANONYMOUS_ENCOUNTER_SCHEMA = (
    "guala.live_anonymous_encounter_continuity.v1"
)
LIVE_ANONYMOUS_ENCOUNTER_STATE_SCHEMA = (
    "guala.live_anonymous_encounter_continuity.state.v1"
)
MAX_LIVE_ANONYMOUS_ENCOUNTER_STATE_BYTES = 128 * 1024


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} is not a lowercase SHA-256 digest")
    return value


def _key_bytes(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise TypeError("live encounter authority key must be bytes or text")
    if not result:
        raise ValueError("live encounter authority key cannot be empty")
    return hashlib.sha256(
        b"guala-live-anonymous-encounter-key-v1\0" + result
    ).digest()


def _hmac(key: bytes, domain: bytes, payload: object) -> str:
    return hmac.new(
        key,
        domain + b"\0" + _canonical_bytes(payload),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class LiveAnonymousEncounterObservation:
    assembly_id: str
    acquisition_stream_id: str
    sequence: int
    first_sample_index: int
    sample_count: int
    source_time_start: str
    source_time_end: str
    state: str
    reason: str
    acoustic_source: str
    current_visual_lineage_receipt_sha256s: tuple[str, ...]
    candidate_visual_lineage_receipt_sha256s: tuple[str, ...]
    continuing_visual_lineage_receipt_sha256: str | None
    visual_l5_authority_receipt_sha256: str
    auditory_stream_settlement_authority_receipt_sha256: str
    transport_receipt_sha256: str
    cochlear_receipt_sha256: str
    causal_settlement_authority_receipt_sha256: str
    prior_encounter_authority_receipt_sha256: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "acquisition_stream_id": self.acquisition_stream_id,
            "acoustic_source": self.acoustic_source,
            "assembly_id": self.assembly_id,
            "auditory_stream_settlement_authority_receipt_sha256": (
                self.auditory_stream_settlement_authority_receipt_sha256
            ),
            "candidate_visual_lineage_receipt_sha256s": list(
                self.candidate_visual_lineage_receipt_sha256s
            ),
            "current_visual_lineage_receipt_sha256s": list(
                self.current_visual_lineage_receipt_sha256s
            ),
            "causal_settlement_authority_receipt_sha256": (
                self.causal_settlement_authority_receipt_sha256
            ),
            "cochlear_receipt_sha256": self.cochlear_receipt_sha256,
            "continuing_visual_lineage_receipt_sha256": (
                self.continuing_visual_lineage_receipt_sha256
            ),
            "first_sample_index": self.first_sample_index,
            "reason": self.reason,
            "sample_count": self.sample_count,
            "schema": LIVE_ANONYMOUS_ENCOUNTER_SCHEMA,
            "sequence": self.sequence,
            "source_time_end": self.source_time_end,
            "source_time_start": self.source_time_start,
            "prior_encounter_authority_receipt_sha256": (
                self.prior_encounter_authority_receipt_sha256
            ),
            "transport_receipt_sha256": self.transport_receipt_sha256,
            "state": self.state,
            "visual_l5_authority_receipt_sha256": (
                self.visual_l5_authority_receipt_sha256
            ),
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class LiveAnonymousEncounterContinuityAuthority:
    """Capacity-one owner of authenticated live encounter continuity."""

    def __init__(
        self,
        *,
        authority_key: object,
        visual_authority: DeterministicVisualRegionContinuityAuthority,
    ) -> None:
        if not isinstance(
            visual_authority, DeterministicVisualRegionContinuityAuthority
        ):
            raise TypeError("live encounter requires the visual L5 authority")
        self._key = _key_bytes(authority_key)
        self._visual_authority = visual_authority
        self._latest: LiveAnonymousEncounterObservation | None = None
        self._inactive_restored_record: dict[str, object] | None = None

    def _seal(
        self, payload: Mapping[str, object]
    ) -> LiveAnonymousEncounterObservation:
        signature = _hmac(
            self._key, b"guala-live-anonymous-encounter-observation-v1", payload
        )
        receipt = hashlib.sha256(
            b"guala-live-anonymous-encounter-receipt-v1\0"
            + _canonical_bytes({
                "authority_hmac_sha256": signature,
                "payload": payload,
            })
        ).hexdigest()
        return LiveAnonymousEncounterObservation(
            assembly_id=str(payload["assembly_id"]),
            acquisition_stream_id=str(payload["acquisition_stream_id"]),
            sequence=int(payload["sequence"]),
            first_sample_index=int(payload["first_sample_index"]),
            sample_count=int(payload["sample_count"]),
            source_time_start=str(payload["source_time_start"]),
            source_time_end=str(payload["source_time_end"]),
            state=str(payload["state"]),
            reason=str(payload["reason"]),
            acoustic_source=str(payload["acoustic_source"]),
            current_visual_lineage_receipt_sha256s=tuple(
                str(value)
                for value in payload[
                    "current_visual_lineage_receipt_sha256s"
                ]
            ),
            candidate_visual_lineage_receipt_sha256s=tuple(
                str(value)
                for value in payload[
                    "candidate_visual_lineage_receipt_sha256s"
                ]
            ),
            continuing_visual_lineage_receipt_sha256=(
                str(payload["continuing_visual_lineage_receipt_sha256"])
                if payload["continuing_visual_lineage_receipt_sha256"]
                is not None
                else None
            ),
            visual_l5_authority_receipt_sha256=str(
                payload["visual_l5_authority_receipt_sha256"]
            ),
            auditory_stream_settlement_authority_receipt_sha256=str(
                payload[
                    "auditory_stream_settlement_authority_receipt_sha256"
                ]
            ),
            transport_receipt_sha256=str(
                payload["transport_receipt_sha256"]
            ),
            cochlear_receipt_sha256=str(
                payload["cochlear_receipt_sha256"]
            ),
            causal_settlement_authority_receipt_sha256=str(
                payload["causal_settlement_authority_receipt_sha256"]
            ),
            prior_encounter_authority_receipt_sha256=(
                str(payload["prior_encounter_authority_receipt_sha256"])
                if payload["prior_encounter_authority_receipt_sha256"]
                is not None
                else None
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=receipt,
        )

    @staticmethod
    def _observation_from_record(
        latest: Mapping[str, object],
    ) -> LiveAnonymousEncounterObservation:
        return LiveAnonymousEncounterObservation(
            assembly_id=str(latest.get("assembly_id", "")),
            acquisition_stream_id=str(
                latest.get("acquisition_stream_id", "")
            ),
            sequence=latest.get("sequence", -1),
            first_sample_index=latest.get("first_sample_index", -1),
            sample_count=latest.get("sample_count", 0),
            source_time_start=str(latest.get("source_time_start", "")),
            source_time_end=str(latest.get("source_time_end", "")),
            state=str(latest.get("state", "")),
            reason=str(latest.get("reason", "")),
            acoustic_source=str(latest.get("acoustic_source", "")),
            current_visual_lineage_receipt_sha256s=tuple(
                latest.get("current_visual_lineage_receipt_sha256s", ())
            ),
            candidate_visual_lineage_receipt_sha256s=tuple(
                latest.get("candidate_visual_lineage_receipt_sha256s", ())
            ),
            continuing_visual_lineage_receipt_sha256=latest.get(
                "continuing_visual_lineage_receipt_sha256"
            ),
            visual_l5_authority_receipt_sha256=str(
                latest.get("visual_l5_authority_receipt_sha256", "")
            ),
            auditory_stream_settlement_authority_receipt_sha256=str(
                latest.get(
                    "auditory_stream_settlement_authority_receipt_sha256", ""
                )
            ),
            transport_receipt_sha256=str(
                latest.get("transport_receipt_sha256", "")
            ),
            cochlear_receipt_sha256=str(
                latest.get("cochlear_receipt_sha256", "")
            ),
            causal_settlement_authority_receipt_sha256=str(
                latest.get("causal_settlement_authority_receipt_sha256", "")
            ),
            prior_encounter_authority_receipt_sha256=latest.get(
                "prior_encounter_authority_receipt_sha256"
            ),
            authority_hmac_sha256=str(
                latest.get("authority_hmac_sha256", "")
            ),
            authority_receipt_sha256=str(
                latest.get("authority_receipt_sha256", "")
            ),
        )

    def verify(self, value: LiveAnonymousEncounterObservation) -> None:
        if not isinstance(value, LiveAnonymousEncounterObservation):
            raise TypeError("live encounter observation is not typed")
        if not isinstance(value.assembly_id, str) or not value.assembly_id:
            raise ValueError("live encounter assembly id is absent")
        if (
            not isinstance(value.acquisition_stream_id, str)
            or not value.acquisition_stream_id
        ):
            raise ValueError("live encounter acquisition stream is absent")
        if (
            isinstance(value.sequence, bool)
            or not isinstance(value.sequence, int)
            or value.sequence < 0
            or isinstance(value.first_sample_index, bool)
            or not isinstance(value.first_sample_index, int)
            or value.first_sample_index < 0
            or isinstance(value.sample_count, bool)
            or not isinstance(value.sample_count, int)
            or value.sample_count <= 0
        ):
            raise ValueError("live encounter acquisition extent changed")
        try:
            source_start = Fraction(value.source_time_start)
            source_end = Fraction(value.source_time_end)
        except Exception as error:
            raise ValueError("live encounter source interval changed") from error
        if (
            value.source_time_start
            != f"{source_start.numerator}/{source_start.denominator}"
            or value.source_time_end
            != f"{source_end.numerator}/{source_end.denominator}"
            or source_end <= source_start
        ):
            raise ValueError("live encounter source interval changed")
        if value.state not in {"unique", "ambiguous", "unknown"}:
            raise ValueError("live encounter state changed")
        if value.acoustic_source != "unknown":
            raise ValueError("monaural live encounter claimed an acoustic source")
        candidates = value.candidate_visual_lineage_receipt_sha256s
        current_lineages = value.current_visual_lineage_receipt_sha256s
        if current_lineages != tuple(sorted(set(current_lineages))):
            raise ValueError("live encounter visual lineages changed order")
        for lineage in current_lineages:
            _sha256(lineage, "live encounter current visual lineage")
        if candidates != tuple(sorted(set(candidates))):
            raise ValueError("live encounter candidates changed order")
        for candidate in candidates:
            _sha256(candidate, "live encounter visual lineage")
            if candidate not in current_lineages:
                raise ValueError(
                    "live encounter candidate is absent from current vision"
                )
        if value.state == "unique":
            if (
                len(candidates) != 1
                or value.continuing_visual_lineage_receipt_sha256
                != candidates[0]
                or value.reason != "one_continuing_visual_lineage"
                or value.prior_encounter_authority_receipt_sha256 is None
            ):
                raise ValueError("unique live encounter has no unique lineage")
        elif value.state == "ambiguous":
            if (
                len(candidates) < 2
                or value.continuing_visual_lineage_receipt_sha256 is not None
                or value.reason != "multiple_continuing_visual_lineages"
                or value.prior_encounter_authority_receipt_sha256 is None
            ):
                raise ValueError("ambiguous live encounter changed candidates")
        else:
            if (
                candidates
                or value.continuing_visual_lineage_receipt_sha256 is not None
                or value.reason not in {
                    "no_continuing_visual_lineage",
                    "no_prior_adjacent_audiovisual_encounter",
                }
                or (
                    value.reason == "no_prior_adjacent_audiovisual_encounter"
                    and value.prior_encounter_authority_receipt_sha256
                    is not None
                )
            ):
                raise ValueError("unknown live encounter claimed continuity")
        for digest, label in (
            (value.visual_l5_authority_receipt_sha256, "visual L5 receipt"),
            (
                value.auditory_stream_settlement_authority_receipt_sha256,
                "auditory stream settlement receipt",
            ),
            (
                value.causal_settlement_authority_receipt_sha256,
                "causal settlement receipt",
            ),
            (value.transport_receipt_sha256, "transport receipt"),
            (value.cochlear_receipt_sha256, "cochlear receipt"),
        ):
            _sha256(digest, f"live encounter {label}")
        if value.prior_encounter_authority_receipt_sha256 is not None:
            _sha256(
                value.prior_encounter_authority_receipt_sha256,
                "live encounter prior encounter receipt",
            )
        payload = value.payload()
        expected_hmac = _hmac(
            self._key, b"guala-live-anonymous-encounter-observation-v1", payload
        )
        if not hmac.compare_digest(expected_hmac, value.authority_hmac_sha256):
            raise ValueError("live encounter authority HMAC changed")
        expected_receipt = hashlib.sha256(
            b"guala-live-anonymous-encounter-receipt-v1\0"
            + _canonical_bytes({
                "authority_hmac_sha256": expected_hmac,
                "payload": payload,
            })
        ).hexdigest()
        if not hmac.compare_digest(expected_receipt, value.authority_receipt_sha256):
            raise ValueError("live encounter authority receipt changed")

    def prepare(
        self,
        *,
        visual: VisualL5Settlement,
        auditory: AuditoryStreamSettlementReceipt,
        causal_settlement: CausalExperienceSettlement,
    ) -> LiveAnonymousEncounterObservation:
        self._visual_authority.verify_settlement(visual)
        auditory.verify()
        if not isinstance(causal_settlement, CausalExperienceSettlement):
            raise TypeError("live encounter requires a typed causal settlement")
        causal_settlement.verify()
        if not (
            visual.assembly_id
            == auditory.assembly_id
            == causal_settlement.assembly_id
        ):
            raise ValueError("live audiovisual encounter crossed causal assemblies")
        if (
            visual.full_field_receipt_sha256
            != causal_settlement.assembly_receipt_sha256
            or auditory.causal_settlement_authority_receipt_sha256
            != causal_settlement.authority_receipt_sha256
            or auditory.source_time_start
            != causal_settlement.source_time_start
            or auditory.source_time_end != causal_settlement.source_time_end
        ):
            raise ValueError(
                "live audiovisual encounter crossed causal receipt authorities"
            )
        prior = self._latest
        adjacent = bool(
            prior is not None
            and auditory.stream_id == prior.acquisition_stream_id
            and auditory.sequence == prior.sequence + 1
            and auditory.first_sample_index
            == prior.first_sample_index + prior.sample_count
            and auditory.source_time_start == Fraction(prior.source_time_end)
            and auditory.prior_transport_receipt_sha256
            == prior.transport_receipt_sha256
            and auditory.prior_cochlear_state_receipt_sha256
            == prior.cochlear_receipt_sha256
        )
        current_lineages = tuple(sorted({
            region.lineage_receipt_sha256
            for region in visual.regions
            if region.lineage_receipt_sha256 is not None
        }))
        candidates = (
            tuple(sorted({
                region.lineage_receipt_sha256
                for region in visual.regions
                if region.continuity == "unique"
                and region.lineage_receipt_sha256 is not None
                and region.lineage_receipt_sha256
                in prior.current_visual_lineage_receipt_sha256s
            }))
            if adjacent and prior is not None
            else ()
        )
        if len(candidates) == 1:
            state = "unique"
            reason = "one_continuing_visual_lineage"
            continuing = candidates[0]
        elif len(candidates) > 1:
            state = "ambiguous"
            reason = "multiple_continuing_visual_lineages"
            continuing = None
        else:
            state = "unknown"
            reason = (
                "no_continuing_visual_lineage"
                if adjacent
                else "no_prior_adjacent_audiovisual_encounter"
            )
            continuing = None
        payload = {
            "acquisition_stream_id": auditory.stream_id,
            "acoustic_source": "unknown",
            "assembly_id": auditory.assembly_id,
            "auditory_stream_settlement_authority_receipt_sha256": (
                auditory.authority_receipt_sha256
            ),
            "candidate_visual_lineage_receipt_sha256s": list(candidates),
            "current_visual_lineage_receipt_sha256s": list(
                current_lineages
            ),
            "causal_settlement_authority_receipt_sha256": (
                auditory.causal_settlement_authority_receipt_sha256
            ),
            "cochlear_receipt_sha256": auditory.cochlear_receipt_sha256,
            "continuing_visual_lineage_receipt_sha256": continuing,
            "first_sample_index": auditory.first_sample_index,
            "reason": reason,
            "sample_count": auditory.sample_count,
            "schema": LIVE_ANONYMOUS_ENCOUNTER_SCHEMA,
            "sequence": auditory.sequence,
            "source_time_end": (
                f"{auditory.source_time_end.numerator}/"
                f"{auditory.source_time_end.denominator}"
            ),
            "source_time_start": (
                f"{auditory.source_time_start.numerator}/"
                f"{auditory.source_time_start.denominator}"
            ),
            "prior_encounter_authority_receipt_sha256": (
                prior.authority_receipt_sha256 if adjacent else None
            ),
            "transport_receipt_sha256": auditory.transport_receipt_sha256,
            "state": state,
            "visual_l5_authority_receipt_sha256": (
                visual.authority_receipt_sha256
            ),
        }
        observed = self._seal(payload)
        self.verify(observed)
        return observed

    def commit(
        self, observed: LiveAnonymousEncounterObservation
    ) -> LiveAnonymousEncounterObservation:
        self.verify(observed)
        expected_prior = observed.prior_encounter_authority_receipt_sha256
        if expected_prior is not None and (
            self._latest is None
            or self._latest.authority_receipt_sha256 != expected_prior
        ):
            raise RuntimeError("live encounter ancestry changed before commit")
        self._latest = observed
        self._inactive_restored_record = None
        return observed

    def observe(
        self,
        *,
        visual: VisualL5Settlement,
        auditory: AuditoryStreamSettlementReceipt,
        causal_settlement: CausalExperienceSettlement,
    ) -> LiveAnonymousEncounterObservation:
        return self.commit(self.prepare(
            visual=visual,
            auditory=auditory,
            causal_settlement=causal_settlement,
        ))

    def clear_live_continuity(self) -> None:
        self._latest = None

    def clear_stream(self, stream_id: object) -> bool:
        if not isinstance(stream_id, str) or not stream_id:
            raise ValueError("live encounter stream id is required")
        if (
            self._latest is None
            or self._latest.acquisition_stream_id != stream_id
        ):
            return False
        self._latest = None
        return True

    def snapshot_encoded(self) -> bytes:
        payload = {
            "latest": (
                self._latest.as_record()
                if self._latest is not None
                else self._inactive_restored_record
            ),
            "live": self._latest is not None,
            "schema": LIVE_ANONYMOUS_ENCOUNTER_STATE_SCHEMA,
        }
        envelope = {
            "payload": payload,
            "state_hmac_sha256": _hmac(
                self._key, b"guala-live-anonymous-encounter-state-v1", payload
            ),
        }
        encoded = _canonical_bytes(envelope)
        if len(encoded) > MAX_LIVE_ANONYMOUS_ENCOUNTER_STATE_BYTES:
            raise RuntimeError("live encounter state exceeded its boundary")
        return encoded

    def restore_encoded(self, encoded: object) -> None:
        if not isinstance(encoded, (bytes, bytearray, memoryview)):
            raise TypeError("live encounter state must be encoded bytes")
        raw = bytes(encoded)
        if not raw or len(raw) > MAX_LIVE_ANONYMOUS_ENCOUNTER_STATE_BYTES:
            raise ValueError("live encounter state exceeded its boundary")
        try:
            envelope = json.loads(raw)
        except Exception as error:
            raise ValueError("live encounter state is unreadable") from error
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {"payload", "state_hmac_sha256"}
            or not isinstance(envelope["payload"], dict)
            or set(envelope["payload"]) != {"latest", "live", "schema"}
            or envelope["payload"]["schema"]
            != LIVE_ANONYMOUS_ENCOUNTER_STATE_SCHEMA
            or not isinstance(envelope["payload"]["live"], bool)
            or (
                envelope["payload"]["live"]
                and envelope["payload"]["latest"] is None
            )
        ):
            raise ValueError("live encounter state changed shape")
        expected = _hmac(
            self._key,
            b"guala-live-anonymous-encounter-state-v1",
            envelope["payload"],
        )
        if not hmac.compare_digest(
            expected, str(envelope["state_hmac_sha256"])
        ):
            raise ValueError("live encounter state authority changed")
        latest = envelope["payload"]["latest"]
        mounted = None
        if latest is not None:
            if not isinstance(latest, dict):
                raise ValueError("live encounter latest record changed")
            mounted = self._observation_from_record(latest)
            if mounted.as_record() != latest:
                raise ValueError("live encounter latest record changed")
            self.verify(mounted)
        self._latest = None
        self._inactive_restored_record = latest

    def rollback_encoded(self, encoded: object) -> None:
        """Restore an in-process transaction, retaining its live status."""
        try:
            restore_live = bool(json.loads(bytes(encoded))["payload"]["live"])
        except Exception as error:
            raise ValueError("live encounter rollback state is unreadable") from error
        self.restore_encoded(encoded)
        if restore_live and self._inactive_restored_record is not None:
            mounted = self._observation_from_record(
                self._inactive_restored_record
            )
            self.verify(mounted)
            self._latest = mounted
            self._inactive_restored_record = None

    def status(self) -> dict[str, object]:
        latest = self._latest.as_record() if self._latest is not None else None
        return {
            "acoustic_source": "unknown",
            "active": self._latest is not None,
            "latest": latest,
            "mechanism": "exact_causal_audiovisual_encounter_continuity",
            "persistence": "capacity_one_inactive_after_restart",
            "reason": (
                self._latest.reason
                if self._latest is not None
                else "no_live_continuity_after_gap_or_restart"
            ),
            "schema": "guala.live_anonymous_encounter_continuity.status.v1",
            "source_attribution": (
                "unavailable_without_physical_acoustic_source_correspondence"
            ),
            "state": (
                self._latest.state if self._latest is not None else "unknown"
            ),
            "state_bytes": len(self.snapshot_encoded()),
            "state_capacity_bytes": MAX_LIVE_ANONYMOUS_ENCOUNTER_STATE_BYTES,
        }


__all__ = (
    "LIVE_ANONYMOUS_ENCOUNTER_SCHEMA",
    "LIVE_ANONYMOUS_ENCOUNTER_STATE_SCHEMA",
    "LiveAnonymousEncounterContinuityAuthority",
    "LiveAnonymousEncounterObservation",
    "MAX_LIVE_ANONYMOUS_ENCOUNTER_STATE_BYTES",
)
