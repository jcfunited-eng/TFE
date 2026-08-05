"""Typed physical boundary for one embodied reading lesson.

The controller presents exact material light and exact tutor pressure through
the already-mounted W1 sight and sound entry points.  It closes one shared
causal window and returns the typed arguments required by
``Guala.admit_embodied_glyph_lesson``.

The tutor designation is retained only as display provenance.  It is never
placed in the physical context, never supplied to a sensory authority, and
never interpreted as identity, pronunciation, recognition, or meaning.

Controller state is a bounded receipt index.  PCM is transient call custody:
it is required by the existing acoustic settlement verifier, but no PCM bytes
are stored in a controller record, observation, or cold-restorable snapshot.
L0--L4 remains entirely upstream and unchanged.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable

from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    RetainedAudiovisualCustody,
    RetainedAudiovisualCustodyAuthority,
)
from dsf_ai_service.substrate.embodied_glyph_tutoring import (
    AuthenticatedTutorAcousticActuator,
    GlyphBearingW1MaterialAuthority,
    GlyphMaterialPresentation,
    TutorAcousticActuation,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PassiveThingLearningRecord,
    PassiveWholeOrganismThingLearningOwner,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    WholeOrganismEpisodeAuthority,
    WholeOrganismEpisodeRecord,
)


RECORD_SCHEMA = "guala.embodied_reading.physical_lesson_boundary.v1"
STATE_SCHEMA = "guala.embodied_reading.physical_lesson_boundary.state.v1"
ENVELOPE_SCHEMA = (
    "guala.embodied_reading.physical_lesson_boundary.state_hmac.v1"
)
OBSERVATION_SCHEMA = (
    "guala.embodied_reading.physical_lesson_boundary.observation.v1"
)

MAX_BOUNDARY_RECORDS = 128
MAX_BOUNDARY_STATE_BYTES = 2 * 1024 * 1024
MAX_CONTEXT_ID_BYTES = 256
MAX_DESIGNATION_BYTES = 128

_RECORD_DOMAIN = b"guala-embodied-reading-physical-record-v1\0"
_STATE_DOMAIN = b"guala-embodied-reading-physical-state-v1\0"
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


def _key(value: bytes | str, domain: bytes) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("embodied reading boundary key changed")
    return hashlib.sha256(domain + raw).digest()


def _identifier(value: object, name: str, maximum_bytes: int) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > maximum_bytes
    ):
        raise ValueError(f"{name} changed")
    return value


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _positive_bounded(
    value: object,
    name: str,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise ValueError(f"{name} changed")
    return value


@runtime_checkable
class _WindowManagerBoundary(Protocol):
    @property
    def active_context_id(self) -> str | None:
        ...

    def begin_context(
        self,
        context_id: str,
        trigger_reason: str = "input",
        *,
        context_detail: Mapping[str, object] | None = None,
    ) -> str:
        ...

    def end_context(
        self,
        context_id: str,
        reason: str = "context_complete",
        *,
        return_settlement: bool = False,
    ) -> object:
        ...

    def discard_unsettled_context(
        self,
        context_id: str,
        reason: str = "context_failed",
    ) -> str | None:
        ...


@runtime_checkable
class EmbodiedReadingPhysicalRuntime(Protocol):
    """Minimum existing W1 surface used by the isolated controller."""

    window_manager: _WindowManagerBoundary
    _retained_audiovisual_custody: RetainedAudiovisualCustodyAuthority
    _whole_organism_episode_authority: WholeOrganismEpisodeAuthority
    _passive_whole_organism_thing_learning: (
        PassiveWholeOrganismThingLearningOwner
    )

    def process_live_visual_region_sequence(
        self,
        frames: object,
        *,
        source_time_start_ns: int,
        source_time_end_ns: int,
    ) -> object:
        ...

    def process_sound_frame(
        self,
        audio_bytes: bytes,
        source: str = "mic:live",
        source_anchor_ns: int | None = None,
        source_time_end_ns: int | None = None,
        auditory_event_boundary: str = "ambient",
    ) -> object:
        ...


@dataclass(frozen=True, slots=True)
class EmbodiedReadingBoundaryRecord:
    sequence: int
    context_id: str
    tutor_designation: str
    material_id: str
    geometry_authority_receipt_sha256: str
    presentation_authority_receipt_sha256: str
    acoustic_authority_receipt_sha256: str
    pcm_sha256: str
    source_time_start_ns: int
    source_time_end_ns: int
    settlement_authority_receipt_sha256: str
    audiovisual_custody_receipt_sha256: str
    whole_organism_episode_receipt_sha256: str
    passive_learning_receipt_sha256: str
    thing_id: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "acoustic_authority_receipt_sha256": (
                self.acoustic_authority_receipt_sha256
            ),
            "audiovisual_custody_receipt_sha256": (
                self.audiovisual_custody_receipt_sha256
            ),
            "context_id": self.context_id,
            "geometry_authority_receipt_sha256": (
                self.geometry_authority_receipt_sha256
            ),
            "material_id": self.material_id,
            "passive_learning_receipt_sha256": (
                self.passive_learning_receipt_sha256
            ),
            "pcm_sha256": self.pcm_sha256,
            "presentation_authority_receipt_sha256": (
                self.presentation_authority_receipt_sha256
            ),
            "schema": RECORD_SCHEMA,
            "sequence": self.sequence,
            "settlement_authority_receipt_sha256": (
                self.settlement_authority_receipt_sha256
            ),
            "source_time_end_ns": self.source_time_end_ns,
            "source_time_start_ns": self.source_time_start_ns,
            "thing_id": self.thing_id,
            "tutor_designation": self.tutor_designation,
            "whole_organism_episode_receipt_sha256": (
                self.whole_organism_episode_receipt_sha256
            ),
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class EmbodiedGlyphLessonAdmissionInputs:
    """Transient typed bridge into ``Guala.admit_embodied_glyph_lesson``."""

    boundary_record: EmbodiedReadingBoundaryRecord
    tutor_designation: str
    presentation_authority: GlyphBearingW1MaterialAuthority = field(
        repr=False,
        compare=False,
    )
    presentation: GlyphMaterialPresentation = field(repr=False)
    acoustic_authority: AuthenticatedTutorAcousticActuator = field(
        repr=False,
        compare=False,
    )
    acoustic_actuation: TutorAcousticActuation = field(
        repr=False,
        compare=False,
    )
    audiovisual_authority: RetainedAudiovisualCustodyAuthority = field(
        repr=False,
        compare=False,
    )
    audiovisual_custody: RetainedAudiovisualCustody = field(repr=False)
    whole_organism_episode: WholeOrganismEpisodeRecord = field(repr=False)
    passive_record: PassiveThingLearningRecord = field(repr=False)

    def admission_arguments(self) -> dict[str, object]:
        """Return the exact existing runtime admission signature."""

        return {
            "acoustic_actuation": self.acoustic_actuation,
            "acoustic_authority": self.acoustic_authority,
            "audiovisual_authority": self.audiovisual_authority,
            "audiovisual_custody": self.audiovisual_custody,
            "passive_record": self.passive_record,
            "presentation": self.presentation,
            "presentation_authority": self.presentation_authority,
            "tutor_designation": self.tutor_designation,
            "whole_organism_episode": self.whole_organism_episode,
        }


class EmbodiedReadingLessonController:
    """Bounded receipt owner and physical W1 lesson conductor."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        max_records: int = MAX_BOUNDARY_RECORDS,
        max_state_bytes: int = MAX_BOUNDARY_STATE_BYTES,
    ) -> None:
        self._record_key = _key(authority_key, _RECORD_DOMAIN)
        self._state_key = _key(authority_key, _STATE_DOMAIN)
        self._max_records = _positive_bounded(
            max_records,
            "embodied reading boundary record capacity",
            MAX_BOUNDARY_RECORDS,
        )
        self._max_state_bytes = _positive_bounded(
            max_state_bytes,
            "embodied reading boundary byte capacity",
            MAX_BOUNDARY_STATE_BYTES,
        )
        self._records: tuple[EmbodiedReadingBoundaryRecord, ...] = ()
        self._lock = threading.RLock()
        self._encoded(self._records)

    @property
    def records(self) -> tuple[EmbodiedReadingBoundaryRecord, ...]:
        with self._lock:
            return self._records

    def _seal(
        self,
        *,
        sequence: int,
        context_id: str,
        tutor_designation: str,
        presentation: GlyphMaterialPresentation,
        actuation: TutorAcousticActuation,
        source_time_end_ns: int,
        settlement: CausalExperienceSettlement,
        custody: RetainedAudiovisualCustody,
        episode: WholeOrganismEpisodeRecord,
        passive: PassiveThingLearningRecord,
    ) -> EmbodiedReadingBoundaryRecord:
        provisional = EmbodiedReadingBoundaryRecord(
            sequence=sequence,
            context_id=context_id,
            tutor_designation=tutor_designation,
            material_id=presentation.material_id,
            geometry_authority_receipt_sha256=(
                presentation.geometry.authority_receipt_sha256
            ),
            presentation_authority_receipt_sha256=(
                presentation.authority_receipt_sha256
            ),
            acoustic_authority_receipt_sha256=(
                actuation.authority_receipt_sha256
            ),
            pcm_sha256=actuation.pcm_sha256,
            source_time_start_ns=actuation.source_time_start_ns,
            source_time_end_ns=source_time_end_ns,
            settlement_authority_receipt_sha256=(
                settlement.authority_receipt_sha256
            ),
            audiovisual_custody_receipt_sha256=(
                custody.authority_receipt_sha256
            ),
            whole_organism_episode_receipt_sha256=(
                episode.authority_receipt_sha256
            ),
            passive_learning_receipt_sha256=(
                passive.authority_receipt_sha256
            ),
            thing_id=passive.thing_id,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._record_key,
            _RECORD_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = EmbodiedReadingBoundaryRecord(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name
                not in {
                    "authority_hmac_sha256",
                    "authority_receipt_sha256",
                }
            },
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self._verify_record(result)
        return result

    def _verify_record(
        self,
        value: EmbodiedReadingBoundaryRecord,
    ) -> None:
        if not isinstance(value, EmbodiedReadingBoundaryRecord):
            raise TypeError("embodied reading boundary record is not typed")
        if (
            isinstance(value.sequence, bool)
            or not isinstance(value.sequence, int)
            or value.sequence <= 0
            or isinstance(value.source_time_start_ns, bool)
            or not isinstance(value.source_time_start_ns, int)
            or value.source_time_start_ns < 0
            or isinstance(value.source_time_end_ns, bool)
            or not isinstance(value.source_time_end_ns, int)
            or value.source_time_end_ns <= value.source_time_start_ns
        ):
            raise ValueError("embodied reading boundary extent changed")
        _identifier(
            value.context_id,
            "embodied reading context",
            MAX_CONTEXT_ID_BYTES,
        )
        _identifier(
            value.tutor_designation,
            "tutor designation",
            MAX_DESIGNATION_BYTES,
        )
        _identifier(value.material_id, "glyph material id", 256)
        for digest, name in (
            (
                value.geometry_authority_receipt_sha256,
                "glyph geometry",
            ),
            (
                value.presentation_authority_receipt_sha256,
                "glyph presentation",
            ),
            (
                value.acoustic_authority_receipt_sha256,
                "tutor acoustic actuation",
            ),
            (value.pcm_sha256, "tutor PCM"),
            (
                value.settlement_authority_receipt_sha256,
                "whole-organism settlement",
            ),
            (
                value.audiovisual_custody_receipt_sha256,
                "audiovisual custody",
            ),
            (
                value.whole_organism_episode_receipt_sha256,
                "whole-organism episode",
            ),
            (
                value.passive_learning_receipt_sha256,
                "passive learning",
            ),
            (value.thing_id, "causal THING"),
            (value.authority_hmac_sha256, "boundary HMAC"),
            (value.authority_receipt_sha256, "boundary authority"),
        ):
            _sha(digest, name)
        signature = hmac.new(
            self._record_key,
            _RECORD_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                signature,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": value.payload(),
            })
        ):
            raise ValueError("embodied reading boundary authority changed")

    def conduct_lesson(
        self,
        *,
        runtime: EmbodiedReadingPhysicalRuntime,
        context_id: str,
        tutor_designation: str,
        presentation_authority: GlyphBearingW1MaterialAuthority,
        presentation: GlyphMaterialPresentation,
        acoustic_authority: AuthenticatedTutorAcousticActuator,
        acoustic_actuation: TutorAcousticActuation,
        wav_bytes: bytes,
    ) -> EmbodiedGlyphLessonAdmissionInputs:
        """Conduct one exact sight+sound occurrence and index its receipts."""

        if not isinstance(runtime, EmbodiedReadingPhysicalRuntime):
            raise TypeError(
                "embodied reading lesson requires the physical W1 runtime"
            )
        context_id = _identifier(
            context_id,
            "embodied reading context",
            MAX_CONTEXT_ID_BYTES,
        )
        tutor_designation = _identifier(
            tutor_designation,
            "tutor designation",
            MAX_DESIGNATION_BYTES,
        )
        if not isinstance(
            presentation_authority,
            GlyphBearingW1MaterialAuthority,
        ) or not isinstance(
            acoustic_authority,
            AuthenticatedTutorAcousticActuator,
        ):
            raise TypeError(
                "embodied reading lesson requires typed material and acoustic "
                "authorities"
            )
        presentation_authority.verify(presentation)
        acoustic_authority.verify(acoustic_actuation)
        if (
            not isinstance(wav_bytes, bytes)
            or hashlib.sha256(wav_bytes).hexdigest()
            != acoustic_actuation.wav_sha256
        ):
            raise ValueError(
                "embodied reading WAV differs from its acoustic actuation"
            )
        replay = acoustic_authority.actuate_wav(
            wav_bytes=wav_bytes,
            source_media_receipt_sha256=(
                acoustic_actuation.source_media_receipt_sha256
            ),
            source_time_start_ns=(
                acoustic_actuation.source_time_start_ns
            ),
        )
        if replay != acoustic_actuation:
            raise ValueError(
                "embodied reading WAV changed its authenticated PCM"
            )
        audio_duration_ns = (
            acoustic_actuation.sample_count * 1_000_000_000
            + acoustic_actuation.sample_rate_hz
            - 1
        ) // acoustic_actuation.sample_rate_hz
        source_time_start_ns = acoustic_actuation.source_time_start_ns
        source_time_end_ns = max(
            presentation.source_time_ns[-1],
            source_time_start_ns + audio_duration_ns,
        )
        if presentation.source_time_ns[0] < source_time_start_ns:
            raise ValueError(
                "glyph presentation precedes the tutor acoustic occurrence"
            )

        audiovisual_authority = runtime._retained_audiovisual_custody
        whole_organism_authority = (
            runtime._whole_organism_episode_authority
        )
        passive_owner = runtime._passive_whole_organism_thing_learning
        if (
            not isinstance(
                audiovisual_authority,
                RetainedAudiovisualCustodyAuthority,
            )
            or not isinstance(
                whole_organism_authority,
                WholeOrganismEpisodeAuthority,
            )
            or not isinstance(
                passive_owner,
                PassiveWholeOrganismThingLearningOwner,
            )
        ):
            raise RuntimeError(
                "embodied reading whole-organism owners are not mounted"
            )
        if runtime.window_manager.active_context_id is not None:
            raise RuntimeError(
                "embodied reading requires an unambiguous physical context"
            )

        with self._lock:
            if len(self._records) >= self._max_records:
                raise RuntimeError(
                    "embodied reading boundary capacity exhausted"
                )
            if any(value.context_id == context_id for value in self._records):
                raise ValueError(
                    "embodied reading context was already conducted"
                )
            capacity_probe = EmbodiedReadingBoundaryRecord(
                sequence=len(self._records) + 1,
                context_id=context_id,
                tutor_designation=tutor_designation,
                material_id=presentation.material_id,
                geometry_authority_receipt_sha256="0" * 64,
                presentation_authority_receipt_sha256="0" * 64,
                acoustic_authority_receipt_sha256="0" * 64,
                pcm_sha256="0" * 64,
                source_time_start_ns=source_time_start_ns,
                source_time_end_ns=source_time_end_ns,
                settlement_authority_receipt_sha256="0" * 64,
                audiovisual_custody_receipt_sha256="0" * 64,
                whole_organism_episode_receipt_sha256="0" * 64,
                passive_learning_receipt_sha256="0" * 64,
                thing_id="0" * 64,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            # Every receipt/HMAC has the same fixed encoded width.  This
            # exact preflight proves byte capacity before any lived physical
            # event is opened, so capacity refusal cannot strand an episode.
            self._encoded(self._records + (capacity_probe,))
            opened = False
            settlement: CausalExperienceSettlement | None = None
            try:
                runtime.window_manager.begin_context(
                    context_id,
                    "embodied_reading_material_acoustic_lesson",
                    context_detail={
                        "acoustic_actuation_authority_receipt_sha256": (
                            acoustic_actuation.authority_receipt_sha256
                        ),
                        "experience_origin": (
                            "embodied_reading_material_acoustic_lesson"
                        ),
                        "geometry_authority_receipt_sha256": (
                            presentation.geometry
                            .authority_receipt_sha256
                        ),
                        "presentation_authority_receipt_sha256": (
                            presentation.authority_receipt_sha256
                        ),
                        "sensor_unavailable": [
                            "touch",
                            "smell",
                            "taste",
                            "body",
                        ],
                        "source_time_end_ns": source_time_end_ns,
                        "source_time_start_ns": source_time_start_ns,
                    },
                )
                opened = True
                runtime.process_live_visual_region_sequence(
                    presentation.frames(),
                    source_time_start_ns=source_time_start_ns,
                    source_time_end_ns=source_time_end_ns,
                )
                runtime.process_sound_frame(
                    wav_bytes,
                    source="tutor:physical-acoustic-actuator",
                    source_anchor_ns=source_time_start_ns,
                    source_time_end_ns=(
                        source_time_start_ns + audio_duration_ns
                    ),
                    auditory_event_boundary="ambient",
                )
                result = runtime.window_manager.end_context(
                    context_id,
                    "embodied_reading_material_acoustic_lesson_complete",
                    return_settlement=True,
                )
                opened = False
                if (
                    not isinstance(result, tuple)
                    or len(result) != 2
                    or not isinstance(
                        result[1],
                        CausalExperienceSettlement,
                    )
                ):
                    raise RuntimeError(
                        "embodied reading context did not return its settlement"
                    )
                settlement = result[1]
                settlement.verify()
            except Exception:
                if opened:
                    runtime.window_manager.discard_unsettled_context(
                        context_id,
                        "embodied_reading_material_acoustic_lesson_failed",
                    )
                raise

            observed = {
                value.sense
                for value in settlement.interpretations
                if value.state == "observed"
            }
            if observed != {"sight", "sound"}:
                raise ValueError(
                    "embodied reading settlement is not exact sight and sound"
                )
            presentation_authority.verify_settlement(
                presentation,
                settlement,
            )
            acoustic_authority.verify_settlement(
                acoustic_actuation,
                settlement,
            )
            custody = audiovisual_authority.admit(
                settlement=settlement,
                frame_sha256s=presentation.frame_sha256s,
                canonical_audio_sha256=acoustic_actuation.pcm_sha256,
            )
            episodes = tuple(
                value
                for value in whole_organism_authority.episodes
                if value.settlement_authority_receipt_sha256
                == settlement.authority_receipt_sha256
            )
            passive_records = tuple(
                value
                for value in passive_owner.records
                if value.story.settlement_authority_receipt_sha256
                == settlement.authority_receipt_sha256
            )
            if len(episodes) != 1 or len(passive_records) != 1:
                raise RuntimeError(
                    "embodied reading settlement lacks one whole-organism "
                    "episode and one passive THING record"
                )
            episode = episodes[0]
            passive = passive_records[0]
            record = self._seal(
                sequence=len(self._records) + 1,
                context_id=context_id,
                tutor_designation=tutor_designation,
                presentation=presentation,
                actuation=acoustic_actuation,
                source_time_end_ns=source_time_end_ns,
                settlement=settlement,
                custody=custody,
                episode=episode,
                passive=passive,
            )
            after = self._records + (record,)
            self._encoded(after)
            self._records = after
            return EmbodiedGlyphLessonAdmissionInputs(
                boundary_record=record,
                tutor_designation=tutor_designation,
                presentation_authority=presentation_authority,
                presentation=presentation,
                acoustic_authority=acoustic_authority,
                acoustic_actuation=acoustic_actuation,
                audiovisual_authority=audiovisual_authority,
                audiovisual_custody=custody,
                whole_organism_episode=episode,
                passive_record=passive,
            )

    def _body(
        self,
        records: tuple[EmbodiedReadingBoundaryRecord, ...],
    ) -> dict[str, object]:
        return {
            "limits": {
                "max_records": self._max_records,
                "max_state_bytes": self._max_state_bytes,
            },
            "records": [value.record() for value in records],
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        records: tuple[EmbodiedReadingBoundaryRecord, ...],
    ) -> bytes:
        body = self._body(records)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._state_key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._max_state_bytes:
            raise RuntimeError(
                "embodied reading boundary byte capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._records)

    def observation_projection(self) -> dict[str, object]:
        with self._lock:
            latest = self._records[-1] if self._records else None
            return {
                "claims": {
                    "glyph_identity_authority": False,
                    "meaning_authority": False,
                    "pronunciation_authority": False,
                    "reading_authority": False,
                    "recognition_authority": False,
                    "tutor_designation_authority": False,
                },
                "latest_boundary": (
                    latest.record() if latest is not None else None
                ),
                "max_records": self._max_records,
                "max_state_bytes": self._max_state_bytes,
                "record_count": len(self._records),
                "retained_pcm_bytes": 0,
                "schema": OBSERVATION_SCHEMA,
                "state_bytes": len(self._encoded(self._records)),
            }


def _record_from_mapping(
    value: object,
) -> EmbodiedReadingBoundaryRecord:
    if not isinstance(value, Mapping):
        raise ValueError("restored embodied reading boundary record changed")
    expected = {
        "acoustic_authority_receipt_sha256",
        "authority_hmac_sha256",
        "authority_receipt_sha256",
        "audiovisual_custody_receipt_sha256",
        "context_id",
        "geometry_authority_receipt_sha256",
        "material_id",
        "passive_learning_receipt_sha256",
        "pcm_sha256",
        "presentation_authority_receipt_sha256",
        "schema",
        "sequence",
        "settlement_authority_receipt_sha256",
        "source_time_end_ns",
        "source_time_start_ns",
        "thing_id",
        "tutor_designation",
        "whole_organism_episode_receipt_sha256",
    }
    if set(value) != expected or value.get("schema") != RECORD_SCHEMA:
        raise ValueError("restored embodied reading boundary record changed")
    return EmbodiedReadingBoundaryRecord(
        sequence=value["sequence"],
        context_id=value["context_id"],
        tutor_designation=value["tutor_designation"],
        material_id=value["material_id"],
        geometry_authority_receipt_sha256=(
            value["geometry_authority_receipt_sha256"]
        ),
        presentation_authority_receipt_sha256=(
            value["presentation_authority_receipt_sha256"]
        ),
        acoustic_authority_receipt_sha256=(
            value["acoustic_authority_receipt_sha256"]
        ),
        pcm_sha256=value["pcm_sha256"],
        source_time_start_ns=value["source_time_start_ns"],
        source_time_end_ns=value["source_time_end_ns"],
        settlement_authority_receipt_sha256=(
            value["settlement_authority_receipt_sha256"]
        ),
        audiovisual_custody_receipt_sha256=(
            value["audiovisual_custody_receipt_sha256"]
        ),
        whole_organism_episode_receipt_sha256=(
            value["whole_organism_episode_receipt_sha256"]
        ),
        passive_learning_receipt_sha256=(
            value["passive_learning_receipt_sha256"]
        ),
        thing_id=value["thing_id"],
        authority_hmac_sha256=value["authority_hmac_sha256"],
        authority_receipt_sha256=value["authority_receipt_sha256"],
    )


def restore_embodied_reading_lesson_controller(
    encoded: bytes,
    *,
    authority_key: bytes | str,
) -> EmbodiedReadingLessonController:
    if not isinstance(encoded, bytes) or not encoded:
        raise ValueError("embodied reading boundary state is absent")
    try:
        envelope = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(
            "embodied reading boundary state is unreadable"
        ) from error
    if (
        not isinstance(envelope, Mapping)
        or set(envelope) != {"body", "schema", "state_hmac_sha256"}
        or envelope.get("schema") != ENVELOPE_SCHEMA
        or _canonical(envelope) != encoded
    ):
        raise ValueError("embodied reading boundary envelope changed")
    body = envelope["body"]
    if (
        not isinstance(body, Mapping)
        or set(body) != {"limits", "records", "schema"}
        or body.get("schema") != STATE_SCHEMA
        or not isinstance(body.get("records"), list)
        or not isinstance(body.get("limits"), Mapping)
        or set(body["limits"]) != {"max_records", "max_state_bytes"}
    ):
        raise ValueError("embodied reading boundary body changed")
    owner = EmbodiedReadingLessonController(
        authority_key=authority_key,
        max_records=body["limits"]["max_records"],
        max_state_bytes=body["limits"]["max_state_bytes"],
    )
    expected = hmac.new(
        owner._state_key,
        _STATE_DOMAIN + _canonical(body),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, envelope["state_hmac_sha256"]):
        raise ValueError("embodied reading boundary state authority changed")
    records = tuple(_record_from_mapping(value) for value in body["records"])
    if (
        len(records) > owner._max_records
        or tuple(value.sequence for value in records)
        != tuple(range(1, len(records) + 1))
        or len({value.context_id for value in records}) != len(records)
    ):
        raise ValueError("restored embodied reading boundary order changed")
    for record in records:
        owner._verify_record(record)
    owner._records = records
    if owner.snapshot_encoded() != encoded:
        raise ValueError("embodied reading boundary cold restore changed state")
    return owner


__all__ = (
    "EmbodiedGlyphLessonAdmissionInputs",
    "EmbodiedReadingBoundaryRecord",
    "EmbodiedReadingLessonController",
    "EmbodiedReadingPhysicalRuntime",
    "ENVELOPE_SCHEMA",
    "MAX_BOUNDARY_RECORDS",
    "MAX_BOUNDARY_STATE_BYTES",
    "OBSERVATION_SCHEMA",
    "RECORD_SCHEMA",
    "STATE_SCHEMA",
    "restore_embodied_reading_lesson_controller",
)
