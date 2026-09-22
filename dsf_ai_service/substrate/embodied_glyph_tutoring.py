"""Receipt-owned glyph material and acoustic tutoring lesson custody.

This boundary gives a tutor two physical actuators:

* one exact, bounded 64x64 glyph-bearing material presentation; and
* one exact, bounded PCM acoustic actuation.

Neither actuator supplies identity, pronunciation, meaning, recognition, or
reward.  A lesson may be retained only after the existing audiovisual custody
proves that the exact presented frame receipts and exact emitted PCM digest
entered one settled sight+sound occurrence, the whole-organism owner proves
that same settlement, and passive learning routes it to one already-owned
causal THING.

Durable state contains the bounded glyph bitmap and receipt-only waveform
custody.  It never retains PCM.  L0-L4 remains upstream and unchanged.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import threading
import wave
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Mapping

import numpy as np

from dsf_ai_service.substrate.causal_thing_mosaic import (
    CausalThingMosaicOwner,
)
from dsf_ai_service.substrate.causal_thing_sensory_expansion import (
    RetainedAudiovisualCustody,
    RetainedAudiovisualCustodyAuthority,
)
from dsf_ai_service.substrate.experience_grown_vocal_causal_relation import (
    ExperienceGrownVocalCausalRelationOwner,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    source_evidence_sample_commitment_sha256,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PassiveThingLearningRecord,
    PassiveWholeOrganismThingLearningOwner,
)
from dsf_ai_service.substrate.visual_region_continuity import (
    CanonicalVisualFrame,
    DeterministicVisualRegionContinuityAuthority,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    ContributionState,
    MechanismAvailability,
    WholeOrganismEpisodeAuthority,
    WholeOrganismEpisodeRecord,
)


GEOMETRY_SCHEMA = "guala.embodied_glyph.geometry.v1"
PRESENTATION_SCHEMA = "guala.embodied_glyph.material_presentation.v1"
ACOUSTIC_SCHEMA = "guala.embodied_glyph.acoustic_actuation.v1"
LESSON_SCHEMA = "guala.embodied_glyph.lesson.v1"
STATE_SCHEMA = "guala.embodied_glyph.curriculum.state.v1"
ENVELOPE_SCHEMA = "guala.embodied_glyph.curriculum.state_hmac.v1"
OBSERVATION_SCHEMA = "guala.embodied_glyph.curriculum.observation.v1"

VISUAL_WIDTH = 64
VISUAL_HEIGHT = 64
PACKED_GEOMETRY_BYTES = VISUAL_WIDTH * VISUAL_HEIGHT // 8
MAX_PRESENTATION_FRAMES = 16
MAX_PCM_SAMPLES = 160_000
MAX_LESSONS = 128
MAX_STATE_BYTES = 8 * 1024 * 1024
MAX_DESIGNATION_BYTES = 128

_PRESENTATION_DOMAIN = b"guala-embodied-glyph-presentation-v1\0"
_ACOUSTIC_DOMAIN = b"guala-embodied-glyph-acoustic-v1\0"
_LESSON_DOMAIN = b"guala-embodied-glyph-lesson-v1\0"
_STATE_DOMAIN = b"guala-embodied-glyph-state-v1\0"
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


def _sha(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value.encode("utf-8")) > 256
    ):
        raise ValueError(f"{name} changed")
    return value


def _key(value: bytes | str, domain: bytes) -> bytes:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("embodied glyph authority key changed")
    return hashlib.sha256(domain + raw).digest()


def _verify_native_inputs_in_settlement(
    settlement: CausalExperienceSettlement,
    *,
    sense: str,
    native_inputs: tuple[object, ...],
) -> None:
    settlement.verify()
    interpretation = next(
        (
            value
            for value in settlement.interpretations
            if value.sense == sense
        ),
        None,
    )
    if (
        interpretation is None
        or interpretation.state != "observed"
        or len(interpretation.substreams) != len(native_inputs)
    ):
        raise ValueError(
            f"embodied glyph {sense} actuation is absent from settlement"
        )
    by_topology = {
        value.topology_index: value
        for value in interpretation.substreams
    }
    for native in native_inputs:
        component = by_topology.get(native.topology_index)
        samples = tuple(
            (
                index,
                native.source_times[index],
                Fraction.from_float(
                    float(native.normalized_signal[index])
                ),
                (
                    native.source_relevance[index]
                    if native.source_relevance is not None
                    else Fraction(1)
                ),
                native.phase_turns[index],
            )
            for index in range(len(native.normalized_signal))
        )
        if (
            component is None
            or component.sensor_id != native.sensor_id
            or component.substream_id != native.substream_id
            or component.physical_quantity != native.physical_quantity
            or component.physical_unit != native.physical_unit
            or component.source_sample_count != len(samples)
            or component.source_sample_commitment_sha256
            != source_evidence_sample_commitment_sha256(samples)
        ):
            raise ValueError(
                f"embodied glyph {sense} actuation differs from settlement"
            )


@dataclass(frozen=True, slots=True)
class ExactGlyphGeometry:
    """Exact binary material geometry; it carries no glyph identity."""

    packed_foreground_bits: bytes = field(repr=False)
    foreground_luminance: int
    background_luminance: int
    foreground_pixel_count: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        packed_foreground_bits: bytes,
        foreground_luminance: int,
        background_luminance: int,
    ) -> "ExactGlyphGeometry":
        if (
            not isinstance(packed_foreground_bits, bytes)
            or len(packed_foreground_bits) != PACKED_GEOMETRY_BYTES
        ):
            raise ValueError("glyph geometry must be one exact 64x64 bit plane")
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 255
            for value in (foreground_luminance, background_luminance)
        ) or foreground_luminance == background_luminance:
            raise ValueError("glyph material luminance boundary changed")
        unpacked = np.unpackbits(
            np.frombuffer(packed_foreground_bits, dtype=np.uint8),
            bitorder="big",
        )
        count = int(unpacked.sum())
        if not 0 < count < VISUAL_WIDTH * VISUAL_HEIGHT:
            raise ValueError("glyph material must contain foreground and background")
        payload = {
            "background_luminance": background_luminance,
            "foreground_luminance": foreground_luminance,
            "foreground_pixel_count": count,
            "height": VISUAL_HEIGHT,
            "packed_foreground_bits_base64": base64.b64encode(
                packed_foreground_bits
            ).decode("ascii"),
            "schema": GEOMETRY_SCHEMA,
            "width": VISUAL_WIDTH,
        }
        return cls(
            packed_foreground_bits=packed_foreground_bits,
            foreground_luminance=foreground_luminance,
            background_luminance=background_luminance,
            foreground_pixel_count=count,
            authority_receipt_sha256=_digest(payload),
        )

    def payload(self) -> dict[str, object]:
        return {
            "background_luminance": self.background_luminance,
            "foreground_luminance": self.foreground_luminance,
            "foreground_pixel_count": self.foreground_pixel_count,
            "height": VISUAL_HEIGHT,
            "packed_foreground_bits_base64": base64.b64encode(
                self.packed_foreground_bits
            ).decode("ascii"),
            "schema": GEOMETRY_SCHEMA,
            "width": VISUAL_WIDTH,
        }

    def verify(self) -> None:
        expected = type(self).create(
            packed_foreground_bits=self.packed_foreground_bits,
            foreground_luminance=self.foreground_luminance,
            background_luminance=self.background_luminance,
        )
        if self != expected:
            raise ValueError("glyph geometry authority changed")

    def pixels(self) -> np.ndarray:
        self.verify()
        mask = np.unpackbits(
            np.frombuffer(self.packed_foreground_bits, dtype=np.uint8),
            bitorder="big",
        ).reshape(VISUAL_HEIGHT, VISUAL_WIDTH)
        return np.where(
            mask != 0,
            self.foreground_luminance,
            self.background_luminance,
        ).astype(np.uint8)


@dataclass(frozen=True, slots=True)
class GlyphMaterialPresentation:
    material_id: str
    geometry: ExactGlyphGeometry
    source_time_ns: tuple[int, ...]
    frame_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "frame_sha256s": list(self.frame_sha256s),
            "geometry": self.geometry.payload(),
            "geometry_authority_receipt_sha256": (
                self.geometry.authority_receipt_sha256
            ),
            "material_id": self.material_id,
            "schema": PRESENTATION_SCHEMA,
            "source_time_ns": list(self.source_time_ns),
        }

    def frames(self) -> tuple[CanonicalVisualFrame, ...]:
        pixels = self.geometry.pixels()
        return tuple(
            CanonicalVisualFrame.from_uint8(source_time, pixels)
            for source_time in self.source_time_ns
        )


class GlyphBearingW1MaterialAuthority:
    """Authenticate exact presented geometry without naming its meaning."""

    def __init__(self, *, authority_key: bytes | str) -> None:
        self._key = _key(authority_key, _PRESENTATION_DOMAIN)

    def present(
        self,
        *,
        material_id: str,
        geometry: ExactGlyphGeometry,
        source_time_ns: tuple[int, ...],
    ) -> GlyphMaterialPresentation:
        if not isinstance(geometry, ExactGlyphGeometry):
            raise TypeError("glyph presentation requires typed geometry")
        geometry.verify()
        if (
            not isinstance(source_time_ns, tuple)
            or not 1 <= len(source_time_ns) <= MAX_PRESENTATION_FRAMES
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in source_time_ns
            )
            or tuple(sorted(set(source_time_ns))) != source_time_ns
        ):
            raise ValueError("glyph presentation time extent changed")
        frames = tuple(
            CanonicalVisualFrame.from_uint8(value, geometry.pixels())
            for value in source_time_ns
        )
        provisional = GlyphMaterialPresentation(
            material_id=_identifier(material_id, "glyph material id"),
            geometry=geometry,
            source_time_ns=source_time_ns,
            frame_sha256s=tuple(value.frame_sha256 for value in frames),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _PRESENTATION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = GlyphMaterialPresentation(
            material_id=provisional.material_id,
            geometry=geometry,
            source_time_ns=source_time_ns,
            frame_sha256s=provisional.frame_sha256s,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self.verify(result)
        return result

    def verify(self, value: GlyphMaterialPresentation) -> None:
        if not isinstance(value, GlyphMaterialPresentation):
            raise TypeError("glyph material presentation is not typed")
        value.geometry.verify()
        expected_frames = value.frames()
        signature = hmac.new(
            self._key,
            _PRESENTATION_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            tuple(frame.frame_sha256 for frame in expected_frames)
            != value.frame_sha256s
            or not hmac.compare_digest(
                signature,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": value.payload(),
            })
        ):
            raise ValueError("glyph material presentation authority changed")

    def verify_settlement(
        self,
        value: GlyphMaterialPresentation,
        settlement: CausalExperienceSettlement,
    ) -> None:
        """Prove the exact glyph light trajectories entered this settlement."""

        self.verify(value)
        prepared = (
            DeterministicVisualRegionContinuityAuthority
            .prepare_retinotopic_inputs(value.frames())
        )
        _verify_native_inputs_in_settlement(
            settlement,
            sense="sight",
            native_inputs=prepared.substreams,
        )


@dataclass(frozen=True, slots=True)
class TutorAcousticActuation:
    source_media_receipt_sha256: str
    source_time_start_ns: int
    sample_rate_hz: int
    sample_count: int
    channel_count: int
    sample_width_bytes: int
    wav_sha256: str
    pcm_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str
    pcm_s16le: bytes = field(repr=False, compare=False)

    def payload(self) -> dict[str, object]:
        return {
            "channel_count": self.channel_count,
            "pcm_sha256": self.pcm_sha256,
            "sample_count": self.sample_count,
            "sample_rate_hz": self.sample_rate_hz,
            "sample_width_bytes": self.sample_width_bytes,
            "schema": ACOUSTIC_SCHEMA,
            "source_media_receipt_sha256": (
                self.source_media_receipt_sha256
            ),
            "source_time_start_ns": self.source_time_start_ns,
            "wav_sha256": self.wav_sha256,
        }


class AuthenticatedTutorAcousticActuator:
    """Authenticate transient physical PCM; retain no replayable pressure."""

    def __init__(self, *, authority_key: bytes | str) -> None:
        self._key = _key(authority_key, _ACOUSTIC_DOMAIN)

    def actuate_wav(
        self,
        *,
        wav_bytes: bytes,
        source_media_receipt_sha256: str,
        source_time_start_ns: int,
    ) -> TutorAcousticActuation:
        if not isinstance(wav_bytes, bytes) or not wav_bytes:
            raise ValueError("tutor acoustic actuation requires WAV bytes")
        _sha(source_media_receipt_sha256, "tutor source media")
        if (
            isinstance(source_time_start_ns, bool)
            or not isinstance(source_time_start_ns, int)
            or source_time_start_ns < 0
        ):
            raise ValueError("tutor acoustic source time changed")
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as source:
                channel_count = source.getnchannels()
                sample_width = source.getsampwidth()
                sample_rate = source.getframerate()
                sample_count = source.getnframes()
                compression = source.getcomptype()
                pcm = source.readframes(sample_count)
                trailing = source.readframes(1)
        except (EOFError, wave.Error) as error:
            raise ValueError("tutor acoustic WAV is unreadable") from error
        if (
            channel_count != 1
            or sample_width != 2
            or sample_rate != 16_000
            or compression != "NONE"
            or not 1 <= sample_count <= MAX_PCM_SAMPLES
            or len(pcm) != sample_count * 2
            or trailing
            or not any(pcm)
        ):
            raise ValueError(
                "tutor acoustic actuation requires bounded mono 16kHz PCM16"
            )
        provisional = TutorAcousticActuation(
            source_media_receipt_sha256=source_media_receipt_sha256,
            source_time_start_ns=source_time_start_ns,
            sample_rate_hz=sample_rate,
            sample_count=sample_count,
            channel_count=channel_count,
            sample_width_bytes=sample_width,
            wav_sha256=hashlib.sha256(wav_bytes).hexdigest(),
            pcm_sha256=hashlib.sha256(pcm).hexdigest(),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
            pcm_s16le=pcm,
        )
        signature = hmac.new(
            self._key,
            _ACOUSTIC_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = TutorAcousticActuation(
            source_media_receipt_sha256=provisional.source_media_receipt_sha256,
            source_time_start_ns=provisional.source_time_start_ns,
            sample_rate_hz=provisional.sample_rate_hz,
            sample_count=provisional.sample_count,
            channel_count=provisional.channel_count,
            sample_width_bytes=provisional.sample_width_bytes,
            wav_sha256=provisional.wav_sha256,
            pcm_sha256=provisional.pcm_sha256,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
            pcm_s16le=pcm,
        )
        self.verify(result)
        return result

    def verify(self, value: TutorAcousticActuation) -> None:
        if not isinstance(value, TutorAcousticActuation):
            raise TypeError("tutor acoustic actuation is not typed")
        signature = hmac.new(
            self._key,
            _ACOUSTIC_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            len(value.pcm_s16le) != value.sample_count * 2
            or hashlib.sha256(value.pcm_s16le).hexdigest()
            != value.pcm_sha256
            or not hmac.compare_digest(
                signature,
                value.authority_hmac_sha256,
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": value.payload(),
            })
        ):
            raise ValueError("tutor acoustic actuation authority changed")

    def verify_settlement(
        self,
        value: TutorAcousticActuation,
        settlement: CausalExperienceSettlement,
    ) -> None:
        """Prove this exact PCM produced the settlement's cochlear sources."""

        self.verify(value)
        from dsf_ai_service.substrate.auditory_kernel_mount import (
            auditory_kernel_component_inputs,
        )
        from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
            transduce_auditory_full_field,
        )

        samples = (
            np.frombuffer(value.pcm_s16le, dtype="<i2")
            .astype(np.float64)
            / 32768.0
        )
        capture = transduce_auditory_full_field(
            samples,
            sample_rate_hz=value.sample_rate_hz,
        )
        native_inputs = auditory_kernel_component_inputs(
            capture,
            source_anchor=Fraction(
                value.source_time_start_ns,
                1_000_000_000,
            ),
        )
        _verify_native_inputs_in_settlement(
            settlement,
            sense="sound",
            native_inputs=native_inputs,
        )

    def status(self) -> dict[str, object]:
        return {
            "max_pcm_samples": MAX_PCM_SAMPLES,
            "retained_pcm_bytes": 0,
            "schema": "guala.embodied_glyph.acoustic_actuator.status.v1",
            "stateful": False,
            "waveform_content_authority": False,
        }


@dataclass(frozen=True, slots=True)
class EmbodiedGlyphLessonRecord:
    sequence: int
    tutor_designation: str
    material_presentation: Mapping[str, object]
    acoustic_actuation: Mapping[str, object]
    audiovisual_custody_receipt_sha256: str
    source_occurrence_id: str
    settlement_receipt_sha256: str
    whole_organism_episode_receipt_sha256: str
    whole_organism_manifest: tuple[tuple[str, str], ...]
    whole_organism_mechanisms: tuple[tuple[str, str, str], ...]
    passive_learning_receipt_sha256: str
    thing_id: str
    vocal_relation_state_sha256: str
    vocal_relation_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "acoustic_actuation": dict(self.acoustic_actuation),
            "audiovisual_custody_receipt_sha256": (
                self.audiovisual_custody_receipt_sha256
            ),
            "material_presentation": dict(self.material_presentation),
            "passive_learning_receipt_sha256": (
                self.passive_learning_receipt_sha256
            ),
            "schema": LESSON_SCHEMA,
            "sequence": self.sequence,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "source_occurrence_id": self.source_occurrence_id,
            "thing_id": self.thing_id,
            "tutor_designation": self.tutor_designation,
            "vocal_relation_state_sha256": (
                self.vocal_relation_state_sha256
            ),
            "vocal_relation_receipt_sha256s": list(
                self.vocal_relation_receipt_sha256s
            ),
            "whole_organism_episode_receipt_sha256": (
                self.whole_organism_episode_receipt_sha256
            ),
            "whole_organism_manifest": [
                list(value) for value in self.whole_organism_manifest
            ],
            "whole_organism_mechanisms": [
                list(value) for value in self.whole_organism_mechanisms
            ],
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(slots=True)
class _PreparedState:
    phase: str = "prepared"


@dataclass(frozen=True, slots=True)
class PreparedEmbodiedGlyphLesson:
    record: EmbodiedGlyphLessonRecord
    before: tuple[EmbodiedGlyphLessonRecord, ...] = field(repr=False)
    after: tuple[EmbodiedGlyphLessonRecord, ...] = field(repr=False)
    _state: _PreparedState = field(repr=False, compare=False)
    _owner_authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class EmbodiedGlyphLessonCommitUndo:
    prepared: PreparedEmbodiedGlyphLesson = field(repr=False)
    _owner_authority: object = field(repr=False, compare=False)


class EmbodiedGlyphTutoringCurriculumOwner:
    """Bounded atomic custody for physically completed glyph lessons."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        max_lessons: int = MAX_LESSONS,
        max_state_bytes: int = MAX_STATE_BYTES,
    ) -> None:
        if (
            isinstance(max_lessons, bool)
            or not isinstance(max_lessons, int)
            or not 1 <= max_lessons <= MAX_LESSONS
            or isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or not 1 <= max_state_bytes <= MAX_STATE_BYTES
        ):
            raise ValueError("embodied glyph curriculum capacity changed")
        self._lesson_key = _key(authority_key, _LESSON_DOMAIN)
        self._state_key = _key(authority_key, _STATE_DOMAIN)
        self._max_lessons = max_lessons
        self._max_state_bytes = max_state_bytes
        self._lessons: tuple[EmbodiedGlyphLessonRecord, ...] = ()
        self._prepared: PreparedEmbodiedGlyphLesson | None = None
        self._owner_authority = object()
        self._lock = threading.RLock()
        self._encoded(self._lessons)

    @property
    def lessons(self) -> tuple[EmbodiedGlyphLessonRecord, ...]:
        with self._lock:
            return self._lessons

    def _seal(
        self,
        *,
        sequence: int,
        tutor_designation: str,
        presentation: GlyphMaterialPresentation,
        actuation: TutorAcousticActuation,
        custody: RetainedAudiovisualCustody,
        whole_organism_authority: WholeOrganismEpisodeAuthority,
        episode: WholeOrganismEpisodeRecord,
        passive: PassiveThingLearningRecord,
        vocal_relation_state_sha256: str,
        relation_receipts: tuple[str, ...],
    ) -> EmbodiedGlyphLessonRecord:
        mechanisms = tuple(
            (
                value.mechanism_id,
                value.state.value,
                value.authority_receipt_sha256,
            )
            for value in episode.contributions
        )
        provisional = EmbodiedGlyphLessonRecord(
            sequence=sequence,
            tutor_designation=tutor_designation,
            material_presentation=presentation.payload() | {
                "authority_hmac_sha256": presentation.authority_hmac_sha256,
                "authority_receipt_sha256": (
                    presentation.authority_receipt_sha256
                ),
            },
            acoustic_actuation=actuation.payload() | {
                "authority_hmac_sha256": actuation.authority_hmac_sha256,
                "authority_receipt_sha256": (
                    actuation.authority_receipt_sha256
                ),
            },
            audiovisual_custody_receipt_sha256=(
                custody.authority_receipt_sha256
            ),
            source_occurrence_id=custody.source_occurrence_id,
            settlement_receipt_sha256=(
                custody.settlement.authority_receipt_sha256
            ),
            whole_organism_episode_receipt_sha256=(
                episode.authority_receipt_sha256
            ),
            whole_organism_manifest=tuple(
                (
                    value.mechanism_id,
                    value.availability.value,
                )
                for value in whole_organism_authority.manifest.mechanisms
            ),
            whole_organism_mechanisms=mechanisms,
            passive_learning_receipt_sha256=(
                passive.authority_receipt_sha256
            ),
            thing_id=passive.thing_id,
            vocal_relation_state_sha256=vocal_relation_state_sha256,
            vocal_relation_receipt_sha256s=relation_receipts,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._lesson_key,
            _LESSON_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return EmbodiedGlyphLessonRecord(
            **{
                name: getattr(provisional, name)
                for name in provisional.__dataclass_fields__
                if name not in {
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

    def _verify_record(self, value: EmbodiedGlyphLessonRecord) -> None:
        if not isinstance(value, EmbodiedGlyphLessonRecord):
            raise TypeError("embodied glyph lesson is not typed")
        if (
            isinstance(value.sequence, bool)
            or not isinstance(value.sequence, int)
            or value.sequence <= 0
            or not isinstance(value.tutor_designation, str)
            or not value.tutor_designation
            or len(value.tutor_designation.encode("utf-8"))
            > MAX_DESIGNATION_BYTES
        ):
            raise ValueError("embodied glyph lesson designation changed")
        for digest, name in (
            (
                value.audiovisual_custody_receipt_sha256,
                "lesson audiovisual custody",
            ),
            (value.source_occurrence_id, "lesson occurrence"),
            (value.settlement_receipt_sha256, "lesson settlement"),
            (
                value.whole_organism_episode_receipt_sha256,
                "lesson whole-organism episode",
            ),
            (
                value.passive_learning_receipt_sha256,
                "lesson passive learning",
            ),
            (value.thing_id, "lesson THING"),
            (
                value.vocal_relation_state_sha256,
                "lesson vocal relation state",
            ),
            (value.authority_hmac_sha256, "lesson HMAC"),
            (value.authority_receipt_sha256, "lesson authority"),
        ):
            _sha(digest, name)
        for relation in value.vocal_relation_receipt_sha256s:
            _sha(relation, "lesson vocal relation")
        if (
            not value.whole_organism_mechanisms
            or tuple(
                mechanism
                for mechanism, _availability
                in value.whole_organism_manifest
            )
            != tuple(
                mechanism
                for mechanism, _state, _receipt
                in value.whole_organism_mechanisms
            )
            or any(
                availability
                not in {
                    MechanismAvailability.AVAILABLE.value,
                    MechanismAvailability.UNAVAILABLE.value,
                }
                for _mechanism, availability
                in value.whole_organism_manifest
            )
            or any(
                state not in {
                    ContributionState.PERTURBED.value,
                    ContributionState.QUIESCENT.value,
                    ContributionState.UNAVAILABLE.value,
                }
                for _mechanism, state, _receipt
                in value.whole_organism_mechanisms
            )
        ):
            raise ValueError("embodied glyph lesson lost organism mechanisms")
        for mechanism, _state, receipt in value.whole_organism_mechanisms:
            _identifier(mechanism, "lesson mechanism")
            _sha(receipt, "lesson mechanism contribution")
        signature = hmac.new(
            self._lesson_key,
            _LESSON_DOMAIN + _canonical(value.payload()),
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
            raise ValueError("embodied glyph lesson authority changed")

    def prepare_lesson(
        self,
        *,
        tutor_designation: str,
        presentation_authority: GlyphBearingW1MaterialAuthority,
        presentation: GlyphMaterialPresentation,
        acoustic_authority: AuthenticatedTutorAcousticActuator,
        acoustic_actuation: TutorAcousticActuation,
        audiovisual_authority: RetainedAudiovisualCustodyAuthority,
        audiovisual_custody: RetainedAudiovisualCustody,
        whole_organism_authority: WholeOrganismEpisodeAuthority,
        whole_organism_episode: WholeOrganismEpisodeRecord,
        passive_owner: PassiveWholeOrganismThingLearningOwner,
        passive_record: PassiveThingLearningRecord,
        thing_owner: CausalThingMosaicOwner,
        vocal_relation_owner: ExperienceGrownVocalCausalRelationOwner,
    ) -> PreparedEmbodiedGlyphLesson:
        if not isinstance(
            presentation_authority,
            GlyphBearingW1MaterialAuthority,
        ) or not isinstance(
            acoustic_authority,
            AuthenticatedTutorAcousticActuator,
        ):
            raise TypeError("embodied glyph lesson requires both actuators")
        presentation_authority.verify(presentation)
        acoustic_authority.verify(acoustic_actuation)
        audiovisual_authority.verify_custody(audiovisual_custody)
        audiovisual_custody.settlement.verify()
        presentation_authority.verify_settlement(
            presentation,
            audiovisual_custody.settlement,
        )
        acoustic_authority.verify_settlement(
            acoustic_actuation,
            audiovisual_custody.settlement,
        )
        if (
            tuple(presentation.frame_sha256s)
            != tuple(audiovisual_custody.frame_sha256s)
            or acoustic_actuation.pcm_sha256
            != audiovisual_custody.canonical_audio_sha256
        ):
            raise ValueError(
                "glyph and acoustic actuators did not enter one AV custody"
            )
        if (
            whole_organism_episode not in whole_organism_authority.episodes
            or whole_organism_episode.settlement_authority_receipt_sha256
            != audiovisual_custody.settlement.authority_receipt_sha256
        ):
            raise ValueError(
                "glyph lesson did not enter the same whole-organism episode"
            )
        observed = {
            value.sense
            for value in audiovisual_custody.settlement.interpretations
            if value.state == "observed"
        }
        if not {"sight", "sound"}.issubset(observed):
            raise ValueError("glyph lesson requires physical sight and sound")
        if (
            passive_record not in passive_owner.records
            or passive_record.story.settlement_authority_receipt_sha256
            != audiovisual_custody.settlement.authority_receipt_sha256
            or passive_record.observed_senses != tuple(
                value.sense
                for value in audiovisual_custody.settlement.interpretations
                if value.state == "observed"
            )
        ):
            raise ValueError(
                "glyph lesson passive THING custody crossed its settlement"
            )
        if not any(
            value.thing_id == passive_record.thing_id
            for value in thing_owner.mosaics
        ):
            raise ValueError("glyph lesson THING is not owned")
        relation_receipts = tuple(
            value.authority_receipt_sha256
            for value in vocal_relation_owner.relations
            if value.thing_id == passive_record.thing_id
        )
        vocal_relation_state_sha256 = hashlib.sha256(
            vocal_relation_owner.snapshot_encoded()
        ).hexdigest()
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError("embodied glyph lesson already prepared")
            existing = next(
                (
                    value
                    for value in self._lessons
                    if value.source_occurrence_id
                    == audiovisual_custody.source_occurrence_id
                ),
                None,
            )
            if existing is not None:
                raise ValueError("embodied glyph lesson occurrence is duplicate")
            if len(self._lessons) >= self._max_lessons:
                raise RuntimeError("embodied glyph lesson capacity exhausted")
            record = self._seal(
                sequence=len(self._lessons) + 1,
                tutor_designation=tutor_designation,
                presentation=presentation,
                actuation=acoustic_actuation,
                custody=audiovisual_custody,
                whole_organism_authority=whole_organism_authority,
                episode=whole_organism_episode,
                passive=passive_record,
                vocal_relation_state_sha256=(
                    vocal_relation_state_sha256
                ),
                relation_receipts=relation_receipts,
            )
            self._verify_record(record)
            after = self._lessons + (record,)
            self._encoded(after)
            prepared = PreparedEmbodiedGlyphLesson(
                record=record,
                before=self._lessons,
                after=after,
                _state=_PreparedState(),
                _owner_authority=self._owner_authority,
            )
            self._prepared = prepared
            return prepared

    def commit_prepared(
        self,
        prepared: PreparedEmbodiedGlyphLesson,
    ) -> EmbodiedGlyphLessonCommitUndo:
        with self._lock:
            if (
                prepared is not self._prepared
                or prepared._owner_authority is not self._owner_authority
                or prepared._state.phase != "prepared"
                or self._lessons != prepared.before
            ):
                raise ValueError("embodied glyph prepared lesson changed")
            self._lessons = prepared.after
            self._prepared = None
            prepared._state.phase = "committed"
            return EmbodiedGlyphLessonCommitUndo(
                prepared=prepared,
                _owner_authority=self._owner_authority,
            )

    def rollback_committed(
        self,
        undo: EmbodiedGlyphLessonCommitUndo,
    ) -> None:
        with self._lock:
            prepared = undo.prepared
            if (
                undo._owner_authority is not self._owner_authority
                or prepared._state.phase != "committed"
                or self._lessons != prepared.after
            ):
                raise ValueError("embodied glyph rollback authority changed")
            self._lessons = prepared.before
            prepared._state.phase = "rolled_back"

    def discard_prepared(
        self,
        prepared: PreparedEmbodiedGlyphLesson,
    ) -> None:
        with self._lock:
            if (
                prepared is not self._prepared
                or prepared._state.phase != "prepared"
            ):
                raise ValueError("embodied glyph prepared lesson changed")
            self._prepared = None
            prepared._state.phase = "discarded"

    def _body(
        self,
        lessons: tuple[EmbodiedGlyphLessonRecord, ...],
    ) -> dict[str, object]:
        return {
            "lessons": [value.record() for value in lessons],
            "limits": {
                "max_lessons": self._max_lessons,
                "max_state_bytes": self._max_state_bytes,
            },
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        lessons: tuple[EmbodiedGlyphLessonRecord, ...],
    ) -> bytes:
        body = self._body(lessons)
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
            raise RuntimeError("embodied glyph curriculum state capacity exhausted")
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            return self._encoded(self._lessons)

    def observation_projection(self) -> dict[str, object]:
        with self._lock:
            latest = self._lessons[-1] if self._lessons else None
            articulation_state = (
                "perturbed"
                if latest is not None
                and latest.vocal_relation_receipt_sha256s
                else "quiescent"
            )
            manifest = (
                dict(latest.whole_organism_manifest)
                if latest is not None else {}
            )
            unavailable = sorted(
                mechanism
                for mechanism, availability in manifest.items()
                if availability
                != MechanismAvailability.AVAILABLE.value
            )
            unwired: list[str] = []
            return {
                "articulation": {
                    "relation_receipt_sha256s": (
                        list(latest.vocal_relation_receipt_sha256s)
                        if latest is not None else []
                    ),
                    "state_receipt_sha256": (
                        latest.vocal_relation_state_sha256
                        if latest is not None else None
                    ),
                    "state": articulation_state,
                    "word_authority": False,
                },
                "claims": {
                    "glyph_identity_authority": False,
                    "meaning_authority": False,
                    "reading_authority": False,
                    "spoken_form_authority": False,
                    "transcript_authority": False,
                },
                "latest_lesson": (
                    None
                    if latest is None
                    else {
                        **latest.record(),
                        "tutor_designation_authority": "display_only",
                    }
                ),
                "lesson_count": len(self._lessons),
                "max_lessons": self._max_lessons,
                "retained_pcm_bytes": 0,
                "schema": OBSERVATION_SCHEMA,
                "state_bytes": len(self._encoded(self._lessons)),
                "state_capacity_bytes": self._max_state_bytes,
                "whole_organism": {
                    "complete_wiring": latest is not None,
                    "mechanisms": (
                        [
                            {
                                "availability": manifest[mechanism],
                                "authority_receipt_sha256": receipt,
                                "mechanism_id": mechanism,
                                "state": state,
                            }
                            for mechanism, state, receipt
                            in latest.whole_organism_mechanisms
                        ]
                        if latest is not None else []
                    ),
                    "production_milestone_satisfied": latest is not None,
                    "state": (
                        "perturbed"
                        if latest is not None
                        else "quiescent"
                    ),
                    "unavailable_mechanism_ids": unavailable,
                    "unwired_mechanism_ids": unwired,
                },
            }


def _geometry_from_payload(value: object) -> ExactGlyphGeometry:
    if (
        not isinstance(value, Mapping)
        or value.get("schema") != GEOMETRY_SCHEMA
        or value.get("width") != VISUAL_WIDTH
        or value.get("height") != VISUAL_HEIGHT
    ):
        raise ValueError("restored glyph geometry changed")
    try:
        packed = base64.b64decode(
            value["packed_foreground_bits_base64"],
            validate=True,
        )
    except Exception as error:
        raise ValueError("restored glyph geometry encoding changed") from error
    result = ExactGlyphGeometry.create(
        packed_foreground_bits=packed,
        foreground_luminance=value["foreground_luminance"],
        background_luminance=value["background_luminance"],
    )
    if (
        result.foreground_pixel_count != value["foreground_pixel_count"]
    ):
        raise ValueError("restored glyph geometry content changed")
    return result


def _lesson_from_record(
    value: Mapping[str, object],
) -> EmbodiedGlyphLessonRecord:
    material = dict(value["material_presentation"])
    geometry = _geometry_from_payload(material["geometry"])
    if geometry.authority_receipt_sha256 != material[
        "geometry_authority_receipt_sha256"
    ]:
        raise ValueError("restored glyph material geometry changed")
    return EmbodiedGlyphLessonRecord(
        sequence=value["sequence"],
        tutor_designation=value["tutor_designation"],
        material_presentation=material,
        acoustic_actuation=dict(value["acoustic_actuation"]),
        audiovisual_custody_receipt_sha256=(
            value["audiovisual_custody_receipt_sha256"]
        ),
        source_occurrence_id=value["source_occurrence_id"],
        settlement_receipt_sha256=value["settlement_receipt_sha256"],
        whole_organism_episode_receipt_sha256=(
            value["whole_organism_episode_receipt_sha256"]
        ),
        whole_organism_manifest=tuple(
            tuple(item) for item in value["whole_organism_manifest"]
        ),
        whole_organism_mechanisms=tuple(
            tuple(item) for item in value["whole_organism_mechanisms"]
        ),
        passive_learning_receipt_sha256=(
            value["passive_learning_receipt_sha256"]
        ),
        thing_id=value["thing_id"],
        vocal_relation_state_sha256=(
            value["vocal_relation_state_sha256"]
        ),
        vocal_relation_receipt_sha256s=tuple(
            value["vocal_relation_receipt_sha256s"]
        ),
        authority_hmac_sha256=value["authority_hmac_sha256"],
        authority_receipt_sha256=value["authority_receipt_sha256"],
    )


def restore_embodied_glyph_tutoring_curriculum(
    encoded: bytes,
    *,
    authority_key: bytes | str,
) -> EmbodiedGlyphTutoringCurriculumOwner:
    if not isinstance(encoded, bytes) or not encoded:
        raise ValueError("embodied glyph curriculum state is absent")
    try:
        envelope = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("embodied glyph curriculum state is unreadable") from error
    if (
        not isinstance(envelope, Mapping)
        or set(envelope) != {"body", "schema", "state_hmac_sha256"}
        or envelope.get("schema") != ENVELOPE_SCHEMA
        or _canonical(envelope) != encoded
    ):
        raise ValueError("embodied glyph curriculum envelope changed")
    body = envelope["body"]
    if (
        not isinstance(body, Mapping)
        or set(body) != {"lessons", "limits", "schema"}
        or body.get("schema") != STATE_SCHEMA
        or not isinstance(body.get("lessons"), list)
        or not isinstance(body.get("limits"), Mapping)
        or set(body["limits"]) != {"max_lessons", "max_state_bytes"}
    ):
        raise ValueError("embodied glyph curriculum body changed")
    owner = EmbodiedGlyphTutoringCurriculumOwner(
        authority_key=authority_key,
        max_lessons=body["limits"]["max_lessons"],
        max_state_bytes=body["limits"]["max_state_bytes"],
    )
    expected_hmac = hmac.new(
        owner._state_key,
        _STATE_DOMAIN + _canonical(body),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(
        expected_hmac,
        envelope["state_hmac_sha256"],
    ):
        raise ValueError("embodied glyph curriculum state authority changed")
    lessons = tuple(_lesson_from_record(value) for value in body["lessons"])
    if tuple(value.sequence for value in lessons) != tuple(
        range(1, len(lessons) + 1)
    ) or len({value.source_occurrence_id for value in lessons}) != len(
        lessons
    ):
        raise ValueError("restored embodied glyph lesson order changed")
    for lesson in lessons:
        owner._verify_record(lesson)
    owner._lessons = lessons
    if owner.snapshot_encoded() != encoded:
        raise ValueError("embodied glyph cold restore changed state")
    return owner


__all__ = (
    "ACOUSTIC_SCHEMA",
    "AuthenticatedTutorAcousticActuator",
    "EmbodiedGlyphLessonCommitUndo",
    "EmbodiedGlyphLessonRecord",
    "EmbodiedGlyphTutoringCurriculumOwner",
    "ExactGlyphGeometry",
    "GEOMETRY_SCHEMA",
    "GlyphBearingW1MaterialAuthority",
    "GlyphMaterialPresentation",
    "LESSON_SCHEMA",
    "OBSERVATION_SCHEMA",
    "PRESENTATION_SCHEMA",
    "PreparedEmbodiedGlyphLesson",
    "TutorAcousticActuation",
    "restore_embodied_glyph_tutoring_curriculum",
)
