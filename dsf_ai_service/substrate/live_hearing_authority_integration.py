"""Truthful integration boundary for current and exact room hearing.

This module does not claim that the exact binaural coordinator is wired into
the production app.  It provides two bounded mechanisms:

* a source-backed audit of the current browser/app/engine cutover; and
* an engine-independent integration view over typed room-hearing outcomes.

The view can expose the two complete, independently mounted auditory fields
from an authenticated W1 capture. It cannot turn mono PCM, browser-declared
channels, model output, or a component label into room hearing, cognition,
lexical meaning, or production-live authority.

No DSF field is evaluated or reduced here.  Successful W1 outcomes retain the
complete authoritative fields inside their typed occurrences.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from enum import Enum

from dsf_ai_service.substrate.binaural_room_hearing_coordinator import (
    BINAURAL_ROOM_HEARING_OUTCOME_SCHEMA,
    BinauralRoomHearingCoordinator,
    BinauralRoomHearingOutcome,
    BinauralRoomHearingState,
)
from dsf_ai_service.substrate.browser_binaural_pcm_stream import (
    AcceptedBrowserBinauralPCMChunk,
)
from dsf_ai_service.substrate.truthful_loom_observation_projection import (
    LoomRuntimeComponentEvidence,
    TruthfulLoomObservationProjection,
    TruthfulLoomObservationProjector,
)
from dsf_ai_service.substrate.w1_authenticated_multi_emitter_capture import (
    W1AuthenticatedMultiEmitterBinauralCapture,
)


LIVE_HEARING_SOURCE_AUDIT_SCHEMA = (
    "guala.live_hearing_source_audit.v2"
)
LIVE_HEARING_INTEGRATION_SCHEMA = (
    "guala.live_hearing_authority_integration.v1"
)
LIVE_HEARING_INTEGRATION_DOMAIN = (
    b"guala-live-hearing-authority-integration-v1\0"
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


def _source_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


@dataclass(frozen=True, slots=True)
class LiveHearingSourceAudit:
    app_source_sha256: str
    browser_source_sha256: str
    engine_source_sha256: str
    browser_channel_average_present: bool
    app_mono_pcm_registry_present: bool
    app_binaural_pcm_registry_present: bool
    app_exact_room_coordinator_present: bool
    engine_recurrent_q_authority_present: bool
    engine_exact_room_coordinator_present: bool
    exact_room_hearing_source_cutover_present: bool
    live_runtime_receipt_observed: bool
    report_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "app_binaural_pcm_registry_present": (
                self.app_binaural_pcm_registry_present
            ),
            "app_exact_room_coordinator_present": (
                self.app_exact_room_coordinator_present
            ),
            "app_mono_pcm_registry_present": (
                self.app_mono_pcm_registry_present
            ),
            "app_source_sha256": self.app_source_sha256,
            "browser_channel_average_present": (
                self.browser_channel_average_present
            ),
            "browser_source_sha256": self.browser_source_sha256,
            "engine_exact_room_coordinator_present": (
                self.engine_exact_room_coordinator_present
            ),
            "engine_recurrent_q_authority_present": (
                self.engine_recurrent_q_authority_present
            ),
            "engine_source_sha256": self.engine_source_sha256,
            "exact_room_hearing_source_cutover_present": (
                self.exact_room_hearing_source_cutover_present
            ),
            "live_runtime_receipt_observed": (
                self.live_runtime_receipt_observed
            ),
            "schema": LIVE_HEARING_SOURCE_AUDIT_SCHEMA,
        }

    def verify(self) -> None:
        for value, name in (
            (self.app_source_sha256, "audited app source"),
            (self.browser_source_sha256, "audited browser source"),
            (self.engine_source_sha256, "audited engine source"),
        ):
            _sha256(value, name)
        facts = (
            self.browser_channel_average_present,
            self.app_mono_pcm_registry_present,
            self.app_binaural_pcm_registry_present,
            self.app_exact_room_coordinator_present,
            self.engine_recurrent_q_authority_present,
            self.engine_exact_room_coordinator_present,
            self.exact_room_hearing_source_cutover_present,
            self.live_runtime_receipt_observed,
        )
        if any(not isinstance(value, bool) for value in facts):
            raise TypeError("live hearing audit facts must be boolean")
        expected_cutover = (
            not self.browser_channel_average_present
            and self.app_binaural_pcm_registry_present
            and self.app_exact_room_coordinator_present
            and self.engine_exact_room_coordinator_present
        )
        if self.exact_room_hearing_source_cutover_present != expected_cutover:
            raise ValueError("live hearing source cutover claim changed")
        if self.live_runtime_receipt_observed:
            raise ValueError(
                "static source audit cannot claim a live runtime receipt"
            )
        if _digest(self.payload()) != self.report_sha256:
            raise ValueError("live hearing source audit changed")


def audit_live_hearing_sources(
    *,
    app_source: str,
    browser_source: str,
    engine_source: str,
) -> LiveHearingSourceAudit:
    """Audit exact production source markers without inferring runtime proof."""

    for value, name in (
        (app_source, "app source"),
        (browser_source, "browser source"),
        (engine_source, "engine source"),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be non-empty text")
    facts = {
        "browser_channel_average_present": (
            "sample/=channels.length;" in browser_source
        ),
        "app_mono_pcm_registry_present": (
            "AuditoryPCMStreamRegistry" in app_source
        ),
        "app_binaural_pcm_registry_present": (
            "BrowserBinauralPCMStreamRegistry" in app_source
        ),
        "app_exact_room_coordinator_present": (
            "BinauralRoomHearingCoordinator" in app_source
            and ".hear_authenticated_w1_capture(" in app_source
        ),
        "engine_recurrent_q_authority_present": (
            '"active_hearing_authority": "auditory_recurrent_motif"'
            in engine_source
            and "AuditoryQProcessOwner" in engine_source
        ),
        "engine_exact_room_coordinator_present": (
            "BinauralRoomHearingCoordinator" in engine_source
            and ".hear_authenticated_w1_capture(" in engine_source
        ),
    }
    cutover = (
        not facts["browser_channel_average_present"]
        and facts["app_binaural_pcm_registry_present"]
        and facts["app_exact_room_coordinator_present"]
        and facts["engine_exact_room_coordinator_present"]
    )
    draft = LiveHearingSourceAudit(
        app_source_sha256=_source_digest(app_source),
        browser_source_sha256=_source_digest(browser_source),
        engine_source_sha256=_source_digest(engine_source),
        **facts,
        exact_room_hearing_source_cutover_present=cutover,
        live_runtime_receipt_observed=False,
        report_sha256="0" * 64,
    )
    result = LiveHearingSourceAudit(
        app_source_sha256=draft.app_source_sha256,
        browser_source_sha256=draft.browser_source_sha256,
        engine_source_sha256=draft.engine_source_sha256,
        browser_channel_average_present=(
            draft.browser_channel_average_present
        ),
        app_mono_pcm_registry_present=(
            draft.app_mono_pcm_registry_present
        ),
        app_binaural_pcm_registry_present=(
            draft.app_binaural_pcm_registry_present
        ),
        app_exact_room_coordinator_present=(
            draft.app_exact_room_coordinator_present
        ),
        engine_recurrent_q_authority_present=(
            draft.engine_recurrent_q_authority_present
        ),
        engine_exact_room_coordinator_present=(
            draft.engine_exact_room_coordinator_present
        ),
        exact_room_hearing_source_cutover_present=(
            draft.exact_room_hearing_source_cutover_present
        ),
        live_runtime_receipt_observed=False,
        report_sha256=_digest(draft.payload()),
    )
    result.verify()
    return result


class LiveHearingEvidenceRoute(str, Enum):
    AUTHENTICATED_W1_ROOM = "authenticated_w1_room"
    BROWSER_BINAURAL_UNPROVEN = "browser_binaural_unproven"
    MONO_PRESSURE = "mono_pressure"


@dataclass(frozen=True, slots=True)
class LiveHearingAuthorityView:
    route: LiveHearingEvidenceRoute
    room_outcome: BinauralRoomHearingOutcome
    loom_projection: TruthfulLoomObservationProjection
    room_hearing_authority: bool
    full_field_occurrence_receipt_sha256s: tuple[str, ...]
    production_live_wired: bool
    cognition_authority: bool
    meaning_authority: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "cognition_authority": self.cognition_authority,
            "full_field_occurrence_receipt_sha256s": list(
                self.full_field_occurrence_receipt_sha256s
            ),
            "loom_projection_authority_receipt_sha256": (
                self.loom_projection.authority_receipt_sha256
            ),
            "meaning_authority": self.meaning_authority,
            "production_live_wired": self.production_live_wired,
            "room_hearing_authority": self.room_hearing_authority,
            "room_outcome_authority_receipt_sha256": (
                self.room_outcome.authority_receipt_sha256
            ),
            "route": self.route.value,
            "schema": LIVE_HEARING_INTEGRATION_SCHEMA,
        }

    def verify(
        self,
        *,
        authority_key: bytes | str,
        room_authority_key: bytes | str,
        loom_authority_key: bytes | str,
    ) -> None:
        key = _key(authority_key, "live hearing integration key")
        self.room_outcome.verify(room_authority_key)
        self.loom_projection.verify(loom_authority_key)
        if (
            not isinstance(self.route, LiveHearingEvidenceRoute)
            or self.production_live_wired is not False
            or self.cognition_authority is not False
            or self.meaning_authority is not False
        ):
            raise ValueError("live hearing integration authority changed")
        expected_room_authority = (
            self.route is LiveHearingEvidenceRoute.AUTHENTICATED_W1_ROOM
            and self.room_outcome.state
            is BinauralRoomHearingState.SEPARATED_OCCURRENCES
        )
        expected_receipts = tuple(
            value.authority_receipt_sha256
            for value in self.room_outcome.occurrences
        )
        if (
            self.room_hearing_authority != expected_room_authority
            or self.full_field_occurrence_receipt_sha256s
            != expected_receipts
            or (not expected_room_authority and expected_receipts)
        ):
            raise ValueError(
                "live hearing view released unsupported room authority"
            )
        component_receipts = {
            value.get("runtime_authority_receipt_sha256")
            for value in self.loom_projection.runtime_components
            if value.get("wired") is True
        }
        if self.room_outcome.authority_receipt_sha256 not in component_receipts:
            raise ValueError(
                "live hearing outcome is absent from truthful projection"
            )
        expected_hmac = hmac.new(
            key,
            LIVE_HEARING_INTEGRATION_DOMAIN
            + _canonical(self.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected_hmac,
                self.authority_hmac_sha256,
            )
            or self.authority_receipt_sha256 != _digest({
                "authority_hmac_sha256": expected_hmac,
                "payload": self.payload(),
            })
        ):
            raise ValueError("live hearing integration receipt changed")


class LiveHearingAuthorityIntegrator:
    """Expose verified room outcomes without claiming production cutover."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        room_authority_key: bytes | str,
        w1_capture_authority_key: bytes | str,
        loom_authority_key: bytes | str,
    ) -> None:
        self._key = _key(authority_key, "live hearing integration key")
        self._room_key = _key(
            room_authority_key,
            "live hearing room authority key",
        )
        self._loom_key = _key(
            loom_authority_key,
            "live hearing Loom authority key",
        )
        self._room = BinauralRoomHearingCoordinator(
            authority_key=self._room_key,
            w1_capture_authority_key=w1_capture_authority_key,
        )
        self._loom = TruthfulLoomObservationProjector(
            authority_key=self._loom_key,
        )

    def _view(
        self,
        *,
        route: LiveHearingEvidenceRoute,
        outcome: BinauralRoomHearingOutcome,
        browser_chunk: AcceptedBrowserBinauralPCMChunk | None = None,
    ) -> LiveHearingAuthorityView:
        outcome.verify(self._room_key)
        projection = self._loom.project(
            browser_binaural_chunk=browser_chunk,
            runtime_components=(
                LoomRuntimeComponentEvidence(
                    component_id=(
                        "engine-independent-exact-room-hearing"
                    ),
                    contract_schema=(
                        BINAURAL_ROOM_HEARING_OUTCOME_SCHEMA
                    ),
                    wired=True,
                    runtime_authority_receipt_sha256=(
                        outcome.authority_receipt_sha256
                    ),
                ),
            ),
        )
        room_authority = (
            route is LiveHearingEvidenceRoute.AUTHENTICATED_W1_ROOM
            and outcome.state
            is BinauralRoomHearingState.SEPARATED_OCCURRENCES
        )
        occurrence_receipts = tuple(
            value.authority_receipt_sha256
            for value in outcome.occurrences
        )
        draft = LiveHearingAuthorityView(
            route=route,
            room_outcome=outcome,
            loom_projection=projection,
            room_hearing_authority=room_authority,
            full_field_occurrence_receipt_sha256s=occurrence_receipts,
            production_live_wired=False,
            cognition_authority=False,
            meaning_authority=False,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        payload = draft.payload()
        signature = hmac.new(
            self._key,
            LIVE_HEARING_INTEGRATION_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        result = LiveHearingAuthorityView(
            route=draft.route,
            room_outcome=draft.room_outcome,
            loom_projection=draft.loom_projection,
            room_hearing_authority=draft.room_hearing_authority,
            full_field_occurrence_receipt_sha256s=(
                draft.full_field_occurrence_receipt_sha256s
            ),
            production_live_wired=False,
            cognition_authority=False,
            meaning_authority=False,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": payload,
            }),
        )
        result.verify(
            authority_key=self._key,
            room_authority_key=self._room_key,
            loom_authority_key=self._loom_key,
        )
        return result

    def hear_authenticated_w1_room(
        self,
        capture: W1AuthenticatedMultiEmitterBinauralCapture,
    ) -> LiveHearingAuthorityView:
        return self._view(
            route=LiveHearingEvidenceRoute.AUTHENTICATED_W1_ROOM,
            outcome=self._room.hear_authenticated_w1_capture(capture),
        )

    def hear_browser_binaural(
        self,
        accepted: AcceptedBrowserBinauralPCMChunk,
    ) -> LiveHearingAuthorityView:
        return self._view(
            route=(
                LiveHearingEvidenceRoute.BROWSER_BINAURAL_UNPROVEN
            ),
            outcome=self._room.hear_browser_transport(accepted),
            browser_chunk=accepted,
        )

    def hear_mono(
        self,
        pcm_s16le: bytes,
    ) -> LiveHearingAuthorityView:
        return self._view(
            route=LiveHearingEvidenceRoute.MONO_PRESSURE,
            outcome=self._room.hear_mono_pcm(pcm_s16le),
        )


__all__ = [
    "LIVE_HEARING_INTEGRATION_SCHEMA",
    "LIVE_HEARING_SOURCE_AUDIT_SCHEMA",
    "LiveHearingAuthorityIntegrator",
    "LiveHearingAuthorityView",
    "LiveHearingEvidenceRoute",
    "LiveHearingSourceAudit",
    "audit_live_hearing_sources",
]
