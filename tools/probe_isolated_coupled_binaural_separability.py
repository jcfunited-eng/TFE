"""Full-field separability census for the isolated cochlear candidate.

Command and speaker metadata select and evaluate the corpus only.  Neither is
passed to transduction, receptor mounting, L0--L4, event-boundary derivation,
tokenization, or pair relation functions.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import wave
import zipfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

import numpy as np

from dsf_ai_service.glew_runtime.exact_field_executor import (
    start_exact_field_executor,
    stop_exact_field_executor,
)
from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    build_transaction_owned_six_sense_full_field,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.canonical_l6 import (
    canonical_l6_direction,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    COCHLEAR_CHANNEL_COUNT,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
)
from tools.isolated_coupled_binaural_cochlear_candidate import (
    COMPONENT_COUNT,
    COMPONENTS_PER_EAR,
    EAR_IDS,
    RECEPTOR_KINDS,
    CoupledBinauralCapture,
    CoupledBinauralCochlearAuthority,
)


ARCHIVE_SHA256 = (
    "49650f2341b26d886b46b3f4fb8fed59e30300b17550f1ee4a768b3106cf93a0"
)
ARCHIVE_PREFIX = "mini_speech_commands/"
COMMANDS = ("down", "go", "left", "no", "right", "stop", "up", "yes")
SPEAKERS_PER_COMMAND = 8
REFERENCE_SPEAKERS_PER_COMMAND = 5
HELD_OUT_SPEAKERS_PER_COMMAND = 3
MAX_RELATION_PAIRS = 2_016
REPORT_SCHEMA = (
    "guala.audit.isolated_coupled_binaural_separability.v1"
)
KEY = b"isolated-coupled-binaural-census-authority-key-v1"
_HEX = frozenset("0123456789abcdef")


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _root(schema: str, values: Iterable[str]) -> str:
    return _digest({
        "schema": schema,
        "sha256s": list(tuple(sorted(set(values)))),
    })


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _direction(left: Fraction, right: Fraction) -> int:
    if not isinstance(left, Fraction) or not isinstance(right, Fraction):
        raise TypeError("candidate relation requires exact Fractions")
    return (right > left) - (right < left)


def _positive_scale_ray(values: Sequence[Fraction]) -> tuple[str, ...]:
    exact = tuple(values)
    if not exact or any(not isinstance(value, Fraction) for value in exact):
        raise TypeError("candidate projective ray is not exact")
    pivot = next((value for value in exact if value != 0), None)
    if pivot is None:
        return tuple("0/1" for _value in exact)
    scale = abs(pivot)
    return tuple(
        f"{(value / scale).numerator}/{(value / scale).denominator}"
        for value in exact
    )


@dataclass(frozen=True, slots=True)
class CorpusItem:
    item_id: str
    oracle_command: str
    speaker_id: str
    archive_member: str
    pcm_sha256: str
    split: str
    ordinal: int


@dataclass(frozen=True, slots=True)
class ExactFrame:
    fields: tuple[Fraction, ...]
    tuple_receipt_sha256: str

    def verify(self) -> None:
        if (
            len(self.fields) != len(DSF_FIELD_ORDER)
            or any(not isinstance(value, Fraction) for value in self.fields)
        ):
            raise ValueError("candidate frame flattened the DSF field")
        _sha256(self.tuple_receipt_sha256, "candidate L4 tuple")


@dataclass(frozen=True, slots=True)
class CandidateComponent:
    component_id: str
    ear_id: str
    cochlear_index: int
    receptor_kind: str
    frames: tuple[ExactFrame, ...]
    basin_receipt_sha256: str

    def verify(self, frame_count: int) -> None:
        if (
            not self.component_id
            or self.ear_id not in EAR_IDS
            or not 0 <= self.cochlear_index < COCHLEAR_CHANNEL_COUNT
            or self.receptor_kind not in RECEPTOR_KINDS
            or len(self.frames) != frame_count
        ):
            raise ValueError("candidate component topology changed")
        _sha256(self.basin_receipt_sha256, "candidate L4 basin")
        for value in self.frames:
            value.verify()


@dataclass(frozen=True, slots=True)
class CandidateExperience:
    item_id: str
    capture_receipt_sha256: str
    topology_receipt_sha256: str
    joint_l4_support_root_sha256: str
    components: tuple[CandidateComponent, ...]
    event_boundary_indices: tuple[int, ...]
    event_boundary_receipt_sha256s: tuple[str, ...]
    event_boundary_root_sha256: str
    frame_count: int
    left_right_identical: bool

    def verify(self) -> None:
        for value in (
            self.capture_receipt_sha256,
            self.topology_receipt_sha256,
            self.joint_l4_support_root_sha256,
            self.event_boundary_root_sha256,
            *self.event_boundary_receipt_sha256s,
        ):
            _sha256(value, "candidate experience authority")
        if (
            len(self.components) != COMPONENT_COUNT
            or not 1 <= self.frame_count <= 800
            or not self.event_boundary_indices
            or self.event_boundary_indices[0] != 0
            or tuple(sorted(set(self.event_boundary_indices)))
            != self.event_boundary_indices
            or len(self.event_boundary_receipt_sha256s)
            != len(self.event_boundary_indices)
        ):
            raise ValueError("candidate experience boundary changed")
        for value in self.components:
            value.verify(self.frame_count)
        if self.event_boundary_root_sha256 != _root(
            "guala.audit.coupled_binaural.event_boundary_root.v1",
            self.event_boundary_receipt_sha256s,
        ):
            raise ValueError("candidate event boundary root changed")


@dataclass(frozen=True, slots=True)
class TokenSet:
    candidate_id: str
    tokens: frozenset[str]
    token_root_sha256: str
    authority_receipt_sha256: str

    def verify(self, experience: CandidateExperience) -> None:
        if not self.tokens or len(self.tokens) > 65_536:
            raise ValueError("candidate token boundary changed")
        for value in self.tokens:
            _sha256(value, "candidate token")
        if self.token_root_sha256 != _root(
            "guala.audit.coupled_binaural.token_set.v1",
            self.tokens,
        ):
            raise ValueError("candidate token root changed")
        if self.authority_receipt_sha256 != _digest({
            "candidate_id": self.candidate_id,
            "event_boundary_root_sha256": (
                experience.event_boundary_root_sha256
            ),
            "joint_l4_support_root_sha256": (
                experience.joint_l4_support_root_sha256
            ),
            "schema": (
                "guala.audit.coupled_binaural.token_authority.v1"
            ),
            "token_root_sha256": self.token_root_sha256,
        }):
            raise ValueError("candidate token authority changed")


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    candidate_id: str
    quotient_invariance: str
    quotient_loses: tuple[str, ...]
    tokenizer: Callable[[CandidateExperience], TokenSet]

    def record(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "event_gate": (
                "exact changes in complete B_k direction vector or "
                "authenticated neighbor/interaural phase-lock order"
            ),
            "full_fields_used": list(DSF_FIELD_ORDER),
            "quotient_invariance": self.quotient_invariance,
            "quotient_loses": list(self.quotient_loses),
            "relation": (
                "reciprocal canonical L6 over exact quotient-token sets"
            ),
        }


def _select_corpus(archive: zipfile.ZipFile) -> tuple[CorpusItem, ...]:
    names = set(archive.namelist())
    selected = []
    used_speakers = set()
    ordinal = 0
    for command in COMMANDS:
        prefix = f"{ARCHIVE_PREFIX}{command}/"
        by_speaker: dict[str, list[str]] = {}
        for name in sorted(
            value
            for value in names
            if value.startswith(prefix) and value.endswith(".wav")
        ):
            filename = name.rsplit("/", 1)[-1]
            if "_nohash_" not in filename:
                continue
            speaker = filename.split("_nohash_", 1)[0]
            by_speaker.setdefault(speaker, []).append(name)
        command_items = []
        for speaker in sorted(by_speaker):
            if speaker in used_speakers:
                continue
            canonical_members = tuple(
                member
                for member in by_speaker[speaker]
                if _is_canonical_wav(archive.read(member))
            )
            if not canonical_members:
                continue
            member = canonical_members[0]
            pcm_sha = hashlib.sha256(archive.read(member)).hexdigest()
            item = CorpusItem(
                item_id=_digest({
                    "archive_member_sha256": pcm_sha,
                    "ordinal": ordinal,
                    "schema": "guala.audit.full_field_corpus_item.v1",
                }),
                oracle_command=command,
                speaker_id=speaker,
                archive_member=member,
                pcm_sha256=pcm_sha,
                split=(
                    "reference"
                    if len(command_items)
                    < REFERENCE_SPEAKERS_PER_COMMAND
                    else "held_out"
                ),
                ordinal=ordinal,
            )
            command_items.append(item)
            selected.append(item)
            used_speakers.add(speaker)
            ordinal += 1
            if len(command_items) == SPEAKERS_PER_COMMAND:
                break
        if len(command_items) != SPEAKERS_PER_COMMAND:
            raise RuntimeError(
                "candidate corpus lacks globally source-disjoint speakers"
            )
    if (
        len(selected) != 64
        or len({value.speaker_id for value in selected}) != 64
    ):
        raise RuntimeError(
            "candidate corpus speaker custody is not source-disjoint"
        )
    return tuple(selected)


def _is_canonical_wav(data: bytes) -> bool:
    try:
        with wave.open(io.BytesIO(data), "rb") as source:
            return (
                source.getnchannels() == 1
                and source.getsampwidth() == 2
                and source.getframerate() == REQUIRED_SAMPLE_RATE_HZ
                and OBSERVATION_HOP_SAMPLES
                <= source.getnframes()
                <= REQUIRED_SAMPLE_RATE_HZ
                and source.getnframes() % OBSERVATION_HOP_SAMPLES == 0
                and source.getcomptype() == "NONE"
            )
    except (EOFError, wave.Error):
        return False


def _pcm_from_wav(data: bytes) -> np.ndarray:
    with wave.open(io.BytesIO(data), "rb") as source:
        frame_count = source.getnframes()
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != REQUIRED_SAMPLE_RATE_HZ
            or not OBSERVATION_HOP_SAMPLES
            <= frame_count
            <= REQUIRED_SAMPLE_RATE_HZ
            or frame_count % OBSERVATION_HOP_SAMPLES != 0
            or source.getcomptype() != "NONE"
        ):
            raise ValueError("candidate WAV left canonical PCM custody")
        pcm = source.readframes(frame_count)
    if len(pcm) != frame_count * 2:
        raise ValueError("candidate WAV PCM length changed")
    return (
        np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32_768.0
    )


def _component_metadata(
    global_index: int,
) -> tuple[str, int, str]:
    ear_index, within_ear = divmod(
        global_index, COMPONENTS_PER_EAR
    )
    cochlear_index, receptor_index = divmod(
        within_ear, len(RECEPTOR_KINDS)
    )
    return (
        EAR_IDS[ear_index],
        cochlear_index,
        RECEPTOR_KINDS[receptor_index],
    )


def _extract_ear(
    built,
    *,
    ear_id: str,
    frame_count: int,
) -> tuple[CandidateComponent, ...]:
    built.verify_construction()
    sound = next(
        value
        for value in built.boundary.boundaries
        if value.sense is PhysicalSense.SOUND
    )
    support_by_id = {
        value[2]: value
        for value in built._source_l0_l4_supports
    }
    result = []
    ear_offset = EAR_IDS.index(ear_id) * COMPONENTS_PER_EAR
    for local_index, substream in enumerate(sound.substreams):
        substream.verify(built.receipt_registry)
        global_index = ear_offset + local_index
        expected_ear, channel, kind = _component_metadata(global_index)
        if expected_ear != ear_id:
            raise RuntimeError("candidate ear extraction changed")
        support = support_by_id[substream.profile.substream_id]
        intervals = support[4]
        tuples = substream.kernel_basin.exact_dsf_field_tuples
        if len(intervals) != len(tuples):
            raise RuntimeError("candidate L4 support intervals changed")
        expanded: list[ExactFrame | None] = [None] * frame_count
        for interval, field in zip(intervals, tuples, strict=True):
            frame = ExactFrame(
                fields=field.as_tuple(),
                tuple_receipt_sha256=field.authority_receipt_sha256,
            )
            frame.verify()
            for index in range(interval[0], interval[1] + 1):
                if expanded[index] is not None:
                    raise RuntimeError("candidate L4 support overlaps")
                expanded[index] = frame
        if any(value is None for value in expanded):
            raise RuntimeError("candidate L4 support skipped a frame")
        result.append(CandidateComponent(
            component_id=substream.profile.substream_id,
            ear_id=ear_id,
            cochlear_index=channel,
            receptor_kind=kind,
            frames=tuple(
                value for value in expanded if value is not None
            ),
            basin_receipt_sha256=(
                substream.kernel_basin.authority_receipt_sha256
            ),
        ))
    return tuple(result)


def _event_boundaries(
    capture: CoupledBinauralCapture,
    components: tuple[CandidateComponent, ...],
    *,
    topology_receipt_sha256: str,
) -> tuple[tuple[int, ...], tuple[str, ...]]:
    b_index = DSF_FIELD_ORDER.index("B_k")
    phase_by_vertex = {
        f"{value.ear_id}:erb_{value.cochlear_index:02d}": (
            value.phase_lock
        )
        for value in capture.fields
    }
    topology = CoupledBinauralCochlearAuthority(
        authority_key=KEY
    ).topology
    edges = (*topology.neighbor_edges, *topology.interaural_edges)
    indices = [0]
    receipts = [_digest({
        "frame_index": 0,
        "joint_l4_witness_root_sha256": _root(
            "guala.audit.coupled_binaural.boundary_witness.v1",
            (
                value.frames[0].tuple_receipt_sha256
                for value in components
            ),
        ),
        "schema": (
            "guala.audit.coupled_binaural.event_boundary.v1"
        ),
        "state": "genesis",
        "topology_receipt_sha256": topology_receipt_sha256,
    })]
    prior_signature = None
    for frame_index in range(1, capture.frame_count):
        b_directions = tuple(
            _direction(
                value.frames[frame_index - 1].fields[b_index],
                value.frames[frame_index].fields[b_index],
            )
            for value in components
        )
        resonance_orders = tuple(
            (
                phase_by_vertex[left][frame_index]
                > phase_by_vertex[right][frame_index]
            )
            - (
                phase_by_vertex[left][frame_index]
                < phase_by_vertex[right][frame_index]
            )
            for left, right in edges
        )
        signature = (b_directions, resonance_orders)
        if signature == prior_signature:
            continue
        prior_signature = signature
        indices.append(frame_index)
        receipts.append(_digest({
            "B_k_directions": list(b_directions),
            "frame_index": frame_index,
            "joint_l4_witness_root_sha256": _root(
                "guala.audit.coupled_binaural.boundary_witness.v1",
                (
                    value.frames[
                        frame_index
                    ].tuple_receipt_sha256
                    for value in components
                ),
            ),
            "resonance_orders": list(resonance_orders),
            "schema": (
                "guala.audit.coupled_binaural.event_boundary.v1"
            ),
            "topology_receipt_sha256": topology_receipt_sha256,
        }))
    return tuple(indices), tuple(receipts)


def _mount_experience(
    *,
    item_id: str,
    signal: np.ndarray,
    authority: CoupledBinauralCochlearAuthority,
) -> CandidateExperience:
    capture = authority.transduce(
        signal,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    anchor = Fraction(0)
    components = []
    for ear_id in EAR_IDS:
        inputs = authority.mount_ear_l0_l4_inputs(
            capture,
            ear_id=ear_id,
            source_anchor=anchor,
        )
        built = build_transaction_owned_six_sense_full_field(
            assembly_id=f"coupled-binaural-{item_id}-{ear_id}",
            source_time_start=anchor,
            source_time_end=Fraction(
                len(signal), REQUIRED_SAMPLE_RATE_HZ
            ),
            observed_substreams={PhysicalSense.SOUND: inputs},
            states={
                sense: (
                    SenseBoundaryState.OBSERVED
                    if sense is PhysicalSense.SOUND
                    else SenseBoundaryState.SENSOR_UNAVAILABLE
                )
                for sense in SENSE_ORDER
            },
        )
        components.extend(_extract_ear(
            built,
            ear_id=ear_id,
            frame_count=capture.frame_count,
        ))
    mounted = tuple(components)
    boundary_indices, boundary_receipts = _event_boundaries(
        capture,
        mounted,
        topology_receipt_sha256=(
            authority.topology.authority_receipt_sha256
        ),
    )
    left = capture.fields[:COCHLEAR_CHANNEL_COUNT]
    right = capture.fields[COCHLEAR_CHANNEL_COUNT:]
    left_right_identical = all(
        (
            left_value.cochlear_index,
            left_value.centre_hz,
            left_value.erb_width_hz,
            left_value.causal_offsets_samples,
            left_value.envelope,
            left_value.phase_lock,
            left_value.onset,
            left_value.offset,
            left_value.cumulative_phase_turns,
        )
        == (
            right_value.cochlear_index,
            right_value.centre_hz,
            right_value.erb_width_hz,
            right_value.causal_offsets_samples,
            right_value.envelope,
            right_value.phase_lock,
            right_value.onset,
            right_value.offset,
            right_value.cumulative_phase_turns,
        )
        for left_value, right_value in zip(
            left, right, strict=True
        )
    )
    result = CandidateExperience(
        item_id=item_id,
        capture_receipt_sha256=capture.authority_receipt_sha256,
        topology_receipt_sha256=(
            authority.topology.authority_receipt_sha256
        ),
        joint_l4_support_root_sha256=_root(
            "guala.audit.coupled_binaural.joint_l4_support.v1",
            (value.basin_receipt_sha256 for value in mounted),
        ),
        components=mounted,
        event_boundary_indices=boundary_indices,
        event_boundary_receipt_sha256s=boundary_receipts,
        event_boundary_root_sha256=_root(
            "guala.audit.coupled_binaural.event_boundary_root.v1",
            boundary_receipts,
        ),
        frame_count=capture.frame_count,
        left_right_identical=left_right_identical,
    )
    result.verify()
    return result


def _finish_tokens(
    candidate_id: str,
    experience: CandidateExperience,
    quotients: Iterable[object],
) -> TokenSet:
    tokens = frozenset(
        _digest({
            "candidate_id": candidate_id,
            "quotient": value,
            "schema": (
                "guala.audit.coupled_binaural.structural_token.v1"
            ),
        })
        for value in quotients
    )
    token_root = _root(
        "guala.audit.coupled_binaural.token_set.v1",
        tokens,
    )
    result = TokenSet(
        candidate_id=candidate_id,
        tokens=tokens,
        token_root_sha256=token_root,
        authority_receipt_sha256=_digest({
            "candidate_id": candidate_id,
            "event_boundary_root_sha256": (
                experience.event_boundary_root_sha256
            ),
            "joint_l4_support_root_sha256": (
                experience.joint_l4_support_root_sha256
            ),
            "schema": (
                "guala.audit.coupled_binaural.token_authority.v1"
            ),
            "token_root_sha256": token_root,
        }),
    )
    result.verify(experience)
    return result


def _component_state_ray(
    experience: CandidateExperience,
) -> TokenSet:
    candidate = "event_component_state_positive_scale_ray_v1"
    return _finish_tokens(
        candidate,
        experience,
        (
            {
                "cochlear_index": component.cochlear_index,
                "ear_id": component.ear_id,
                "positive_scale_ray": list(_positive_scale_ray(
                    component.frames[frame_index].fields
                )),
                "receptor_kind": component.receptor_kind,
            }
            for component in experience.components
            for frame_index in experience.event_boundary_indices
        ),
    )


def _component_delta_ray(
    experience: CandidateExperience,
) -> TokenSet:
    candidate = "event_component_delta_ray_b_c_gate_v1"
    b_index = DSF_FIELD_ORDER.index("B_k")
    c_index = DSF_FIELD_ORDER.index("C_k")
    values = []
    for component in experience.components:
        for frame_index in experience.event_boundary_indices[1:]:
            prior = component.frames[frame_index - 1].fields
            current = component.frames[frame_index].fields
            delta = tuple(
                right - left
                for left, right in zip(prior, current, strict=True)
            )
            values.append({
                "B_k_direction": _direction(
                    prior[b_index], current[b_index]
                ),
                "C_k_direction": _direction(
                    prior[c_index], current[c_index]
                ),
                "cochlear_index": component.cochlear_index,
                "ear_id": component.ear_id,
                "positive_scale_delta_ray": list(
                    _positive_scale_ray(delta)
                ),
                "receptor_kind": component.receptor_kind,
            })
    return _finish_tokens(candidate, experience, values)


def _component_field_order(
    experience: CandidateExperience,
) -> TokenSet:
    candidate = "event_component_joint_field_order_v1"
    return _finish_tokens(
        candidate,
        experience,
        (
            {
                "cochlear_index": component.cochlear_index,
                "ear_id": component.ear_id,
                "field_order": [
                    _direction(left, right)
                    for left, right in zip(
                        component.frames[
                            frame_index - 1
                        ].fields,
                        component.frames[frame_index].fields,
                        strict=True,
                    )
                ],
                "receptor_kind": component.receptor_kind,
            }
            for component in experience.components
            for frame_index in experience.event_boundary_indices[1:]
        ),
    )


def _neighborhood(
    experience: CandidateExperience,
    *,
    projective: bool,
) -> TokenSet:
    candidate = (
        "event_cochlear_neighborhood_full_ray_order_v1"
        if projective
        else "event_cochlear_neighborhood_joint_order_v1"
    )
    values = []
    for ear_id in EAR_IDS:
        ear_offset = EAR_IDS.index(ear_id) * COMPONENTS_PER_EAR
        for receptor_index, receptor_kind in enumerate(RECEPTOR_KINDS):
            for start in range(COCHLEAR_CHANNEL_COUNT - 2):
                indices = tuple(
                    ear_offset
                    + channel * len(RECEPTOR_KINDS)
                    + receptor_index
                    for channel in range(start, start + 3)
                )
                for frame_index in experience.event_boundary_indices[1:]:
                    prior = tuple(
                        experience.components[index].frames[
                            frame_index - 1
                        ].fields
                        for index in indices
                    )
                    current = tuple(
                        experience.components[index].frames[
                            frame_index
                        ].fields
                        for index in indices
                    )
                    quotient = {
                        "cross_channel_field_orders": [
                            [
                                _direction(
                                    current[left][field_index],
                                    current[right][field_index],
                                )
                                for left, right in ((0, 1), (1, 2), (0, 2))
                            ]
                            for field_index in range(len(DSF_FIELD_ORDER))
                        ],
                        "ear_id": ear_id,
                        "neighborhood_start": start,
                        "receptor_kind": receptor_kind,
                        "temporal_field_orders": [
                            [
                                _direction(left, right)
                                for left, right in zip(
                                    prior_fields,
                                    current_fields,
                                    strict=True,
                                )
                            ]
                            for prior_fields, current_fields in zip(
                                prior, current, strict=True
                            )
                        ],
                    }
                    if projective:
                        quotient["positive_scale_state_rays"] = [
                            list(_positive_scale_ray(value))
                            for value in current
                        ]
                        quotient["positive_scale_delta_rays"] = [
                            list(_positive_scale_ray(tuple(
                                right - left
                                for left, right in zip(
                                    prior_fields,
                                    current_fields,
                                    strict=True,
                                )
                            )))
                            for prior_fields, current_fields in zip(
                                prior, current, strict=True
                            )
                        ]
                    values.append(quotient)
    return _finish_tokens(candidate, experience, values)


def _neighborhood_full(
    experience: CandidateExperience,
) -> TokenSet:
    return _neighborhood(experience, projective=True)


def _neighborhood_order(
    experience: CandidateExperience,
) -> TokenSet:
    return _neighborhood(experience, projective=False)


CANDIDATES = (
    CandidateSpec(
        candidate_id="event_component_state_positive_scale_ray_v1",
        quotient_invariance=(
            "one strictly-positive rational scale per seven-field tuple"
        ),
        quotient_loses=(
            "absolute common field scale",
            "boundary duration",
            "token multiplicity",
            "global event order",
        ),
        tokenizer=_component_state_ray,
    ),
    CandidateSpec(
        candidate_id="event_component_delta_ray_b_c_gate_v1",
        quotient_invariance=(
            "one strictly-positive rational scale per seven-field delta"
        ),
        quotient_loses=(
            "absolute common delta scale",
            "boundary duration",
            "token multiplicity",
            "global event order",
        ),
        tokenizer=_component_delta_ray,
    ),
    CandidateSpec(
        candidate_id="event_component_joint_field_order_v1",
        quotient_invariance=(
            "independent strictly-monotone transform of every DSF field"
        ),
        quotient_loses=(
            "all field magnitudes",
            "all delta ratios",
            "boundary duration",
            "token multiplicity",
            "global event order",
        ),
        tokenizer=_component_field_order,
    ),
    CandidateSpec(
        candidate_id="event_cochlear_neighborhood_full_ray_order_v1",
        quotient_invariance=(
            "positive scale per component tuple while retaining exact "
            "three-place field order"
        ),
        quotient_loses=(
            "absolute common field scale",
            "boundary duration",
            "token multiplicity",
            "global event order",
        ),
        tokenizer=_neighborhood_full,
    ),
    CandidateSpec(
        candidate_id="event_cochlear_neighborhood_joint_order_v1",
        quotient_invariance=(
            "independent monotone field transforms while retaining exact "
            "three-place temporal and cochleotopic order"
        ),
        quotient_loses=(
            "all field magnitudes",
            "all delta ratios",
            "boundary duration",
            "token multiplicity",
            "global event order",
        ),
        tokenizer=_neighborhood_order,
    ),
)


def _l6_payload(value) -> dict[str, object]:
    return {
        "dimensions": value.dimensions,
        "effective_dimensions": value.effective_dimensions,
        "knee": value.knee,
        "locked": value.locked,
        "matching_non_null": value.matching_non_null,
        "matching_quiescent": value.matching_quiescent,
    }


def _relation(
    candidate_id: str,
    left_id: str,
    right_id: str,
    left: TokenSet,
    right: TokenSet,
) -> dict[str, object]:
    intersection = left.tokens.intersection(right.tokens)
    left_l6 = canonical_l6_direction(
        dimensions=len(left.tokens),
        matching_non_null=len(intersection),
        matching_quiescent=0,
    )
    right_l6 = canonical_l6_direction(
        dimensions=len(right.tokens),
        matching_non_null=len(intersection),
        matching_quiescent=0,
    )
    payload = {
        "candidate_id": candidate_id,
        "intersection_root_sha256": _root(
            "guala.audit.coupled_binaural.intersection.v1",
            intersection,
        ),
        "left_item_id": left_id,
        "left_l6": _l6_payload(left_l6),
        "left_token_authority_receipt_sha256": (
            left.authority_receipt_sha256
        ),
        "matching_token_count": len(intersection),
        "relation_locked": left_l6.locked and right_l6.locked,
        "right_item_id": right_id,
        "right_l6": _l6_payload(right_l6),
        "right_token_authority_receipt_sha256": (
            right.authority_receipt_sha256
        ),
        "schema": (
            "guala.audit.coupled_binaural.structural_relation.v1"
        ),
    }
    return payload | {"authority_receipt_sha256": _digest(payload)}


def _matrix(
    items: tuple[CorpusItem, ...],
    tokens: Mapping[str, TokenSet],
    candidate_id: str,
) -> tuple[list[list[dict[str, object]]], dict[str, object]]:
    matrix = []
    for left in items:
        row = []
        for right in items:
            if left.item_id == right.item_id:
                value = tokens[left.item_id]
                l6 = canonical_l6_direction(
                    dimensions=len(value.tokens),
                    matching_non_null=len(value.tokens),
                    matching_quiescent=0,
                )
                row.append({
                    "authority_receipt_sha256": _digest({
                        "candidate_id": candidate_id,
                        "item_id": left.item_id,
                        "schema": (
                            "guala.audit.coupled_binaural.identity.v1"
                        ),
                        "token_root_sha256": value.token_root_sha256,
                    }),
                    "intersection_root_sha256": (
                        value.token_root_sha256
                    ),
                    "left_l6": _l6_payload(l6),
                    "matching_token_count": len(value.tokens),
                    "relation_locked": True,
                    "right_l6": _l6_payload(l6),
                })
            else:
                row.append(_relation(
                    candidate_id,
                    left.item_id,
                    right.item_id,
                    tokens[left.item_id],
                    tokens[right.item_id],
                ))
        matrix.append(row)
    index = {value.item_id: offset for offset, value in enumerate(items)}
    within_locked = 0
    within_total = 0
    cross_locked = 0
    cross_total = 0
    within_failures = []
    cross_failures = []
    for left_index, left in enumerate(items):
        for right_index in range(left_index + 1, len(items)):
            right = items[right_index]
            locked = bool(matrix[left_index][right_index]["relation_locked"])
            if left.oracle_command == right.oracle_command:
                within_total += 1
                within_locked += int(locked)
                if not locked:
                    within_failures.append([left.item_id, right.item_id])
            else:
                cross_total += 1
                cross_locked += int(locked)
                if locked:
                    cross_failures.append([left.item_id, right.item_id])
    if within_total + cross_total != MAX_RELATION_PAIRS:
        raise RuntimeError("candidate relation matrix is incomplete")
    held_out = []
    for query in items:
        if query.split != "held_out":
            continue
        same = tuple(
            value
            for value in items
            if value.split == "reference"
            and value.oracle_command == query.oracle_command
        )
        other = tuple(
            value
            for value in items
            if value.split == "reference"
            and value.oracle_command != query.oracle_command
        )
        same_locks = tuple(
            value.item_id
            for value in same
            if matrix[index[query.item_id]][index[value.item_id]][
                "relation_locked"
            ]
        )
        other_locks = tuple(
            value.item_id
            for value in other
            if matrix[index[query.item_id]][index[value.item_id]][
                "relation_locked"
            ]
        )
        held_out.append({
            "held_out_item_id": query.item_id,
            "oracle_command": query.oracle_command,
            "other_command_reference_lock_count": len(other_locks),
            "other_command_reference_locks": list(other_locks),
            "passed": (
                len(same_locks) == REFERENCE_SPEAKERS_PER_COMMAND
                and not other_locks
            ),
            "same_command_reference_lock_count": len(same_locks),
            "same_command_reference_locks": list(same_locks),
        })
    evaluation = {
        "cross_command_locked_pairs": cross_locked,
        "cross_command_pair_count": cross_total,
        "cross_pair_failure_root_sha256": _digest({
            "pairs": cross_failures,
            "schema": (
                "guala.audit.coupled_binaural.cross_failures.v1"
            ),
        }),
        "held_out_checks": held_out,
        "held_out_pass_count": sum(
            bool(value["passed"]) for value in held_out
        ),
        "held_out_total": len(held_out),
        "relation_passed": (
            within_locked == within_total
            and cross_locked == 0
            and all(value["passed"] for value in held_out)
        ),
        "within_command_locked_pairs": within_locked,
        "within_command_pair_count": within_total,
        "within_pair_failure_root_sha256": _digest({
            "pairs": within_failures,
            "schema": (
                "guala.audit.coupled_binaural.within_failures.v1"
            ),
        }),
    }
    return matrix, evaluation


def run_census(archive_path: Path) -> dict[str, object]:
    if not archive_path.is_file():
        raise FileNotFoundError(
            f"speech command archive absent: {archive_path}"
        )
    archive_digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if archive_digest != ARCHIVE_SHA256:
        raise ValueError("candidate corpus archive authority changed")
    authority = CoupledBinauralCochlearAuthority(authority_key=KEY)
    with zipfile.ZipFile(archive_path) as archive:
        items = _select_corpus(archive)
        executor = start_exact_field_executor()
        executor.assert_healthy()
        try:
            experiences = tuple(
                _mount_experience(
                    item_id=item.item_id,
                    signal=_pcm_from_wav(
                        archive.read(item.archive_member)
                    ),
                    authority=authority,
                )
                for item in items
            )
        finally:
            stop_exact_field_executor()
    tokens_by_candidate = {}
    for spec in CANDIDATES:
        values = {}
        for experience in experiences:
            token_set = spec.tokenizer(experience)
            token_set.verify(experience)
            values[experience.item_id] = token_set
        tokens_by_candidate[spec.candidate_id] = values
    candidate_reports = {}
    for spec in CANDIDATES:
        matrix, evaluation = _matrix(
            items,
            tokens_by_candidate[spec.candidate_id],
            spec.candidate_id,
        )
        candidate_reports[spec.candidate_id] = {
            "evaluation": evaluation,
            "matrix": matrix,
            "specification": spec.record(),
        }
    boundary_counts = tuple(
        len(value.event_boundary_indices) for value in experiences
    )
    frame_counts = tuple(value.frame_count for value in experiences)
    report = {
        "archive_sha256": archive_digest,
        "boundedness": {
            "component_count": COMPONENT_COUNT,
            "components_per_ear_transaction": COMPONENTS_PER_EAR,
            "ear_transaction_count_per_capture": len(EAR_IDS),
            "maximum_frame_count_per_capture": max(frame_counts),
            "maximum_input_samples_per_capture": (
                max(frame_counts) * OBSERVATION_HOP_SAMPLES
            ),
            "maximum_event_boundary_count": max(boundary_counts),
            "minimum_frame_count_per_capture": min(frame_counts),
            "minimum_input_samples_per_capture": (
                min(frame_counts) * OBSERVATION_HOP_SAMPLES
            ),
            "minimum_event_boundary_count": min(boundary_counts),
            "maximum_native_samples_per_ear_transaction": (
                COMPONENTS_PER_EAR * max(frame_counts)
            ),
            "minimum_native_samples_per_ear_transaction": (
                COMPONENTS_PER_EAR * min(frame_counts)
            ),
            "source_disjoint_capture_count": len(experiences),
        },
        "candidate_reports": candidate_reports,
        "commands": list(COMMANDS),
        "experience_records": [
            {
                "archive_member": item.archive_member,
                "capture_receipt_sha256": (
                    experience.capture_receipt_sha256
                ),
                "event_boundary_count": len(
                    experience.event_boundary_indices
                ),
                "event_boundary_root_sha256": (
                    experience.event_boundary_root_sha256
                ),
                "item_id": item.item_id,
                "joint_l4_support_root_sha256": (
                    experience.joint_l4_support_root_sha256
                ),
                "left_right_identical": (
                    experience.left_right_identical
                ),
                "oracle_command": item.oracle_command,
                "pcm_sha256": item.pcm_sha256,
                "speaker_id": item.speaker_id,
                "split": item.split,
                "token_authorities": {
                    candidate_id: {
                        "authority_receipt_sha256": (
                            values[item.item_id].authority_receipt_sha256
                        ),
                        "token_count": len(
                            values[item.item_id].tokens
                        ),
                        "token_root_sha256": (
                            values[item.item_id].token_root_sha256
                        ),
                    }
                    for candidate_id, values
                    in tokens_by_candidate.items()
                },
            }
            for item, experience in zip(
                items, experiences, strict=True
            )
        ],
        "falsifications": {
            "all_frames_became_event_boundaries": all(
                boundary_count == frame_count
                for boundary_count, frame_count in zip(
                    boundary_counts, frame_counts, strict=True
                )
            ),
            "candidate_labels_available_to_relations": False,
            "interaural_distinct_capture_count": sum(
                not value.left_right_identical
                for value in experiences
            ),
            "spatial_binaural_evidence_available": False,
            "topology_or_capture_tamper_accepted": False,
        },
        "field_order": list(DSF_FIELD_ORDER),
        "held_out_speakers_per_command": (
            HELD_OUT_SPEAKERS_PER_COMMAND
        ),
        "l0_l4_modified": False,
        "matrix_item_ids": [value.item_id for value in items],
        "mono_corpus_ear_calibration": {
            "left": {"gain": "1/1", "sample_delay": "0/1"},
            "right": {"gain": "1/1", "sample_delay": "0/1"},
        },
        "reference_speakers_per_command": (
            REFERENCE_SPEAKERS_PER_COMMAND
        ),
        "schema": REPORT_SCHEMA,
        "source_disjoint_speaker_count": 64,
        "topology": {
            "authority_receipt_sha256": (
                authority.topology.authority_receipt_sha256
            ),
            "interaural_edge_count": len(
                authority.topology.interaural_edges
            ),
            "neighbor_edge_count": len(
                authority.topology.neighbor_edges
            ),
            "vertex_count": len(authority.topology.vertex_ids),
        },
        "transduction_losses": [
            (
                "the mono corpus carries no measured interaural delay or "
                "gain, so both calibrated ears receive identical pressure "
                "and spatial binaural benefit is not evaluated"
            ),
            (
                "the 160-sample RMS envelope discards within-hop pressure "
                "order and waveform polarity"
            ),
            (
                "the phase-lock receptor retains mean unit orientation and "
                "hop-terminal cumulative phase but discards within-hop "
                "phase-lock order"
            ),
            (
                "onset and offset retain only the exact signed displacement "
                "between adjacent hop envelopes and discard intra-hop "
                "onset/offset sequence"
            ),
            (
                "passive neighbor coupling blends uncoupled individual "
                "resonator states; those independent states are not retained"
            ),
            (
                "the B/resonance boundary law retains exact B_k directions "
                "and phase-lock orders but discards their magnitudes when "
                "deciding whether a boundary changed; complete L4 fields "
                "remain retained outside that boundary quotient"
            ),
        ],
    }
    return report | {"authority_receipt_sha256": _digest(report)}


def _summary(report: dict[str, object]) -> dict[str, object]:
    return {
        "archive_sha256": report["archive_sha256"],
        "authority_receipt_sha256": (
            report["authority_receipt_sha256"]
        ),
        "boundedness": report["boundedness"],
        "candidates": {
            key: value["evaluation"]
            for key, value in report["candidate_reports"].items()
        },
        "falsifications": report["falsifications"],
        "schema": (
            "guala.audit.isolated_coupled_binaural_summary.v1"
        ),
        "source_disjoint_speaker_count": (
            report["source_disjoint_speaker_count"]
        ),
        "topology": report["topology"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = run_census(args.archive)
    if args.output is not None:
        encoded = json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ).encode("utf-8")
        args.output.write_bytes(encoded)
    emitted = _summary(report) if args.summary else report
    print(json.dumps(emitted, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
