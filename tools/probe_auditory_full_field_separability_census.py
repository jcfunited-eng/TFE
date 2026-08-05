"""Read-only full-field auditory separability census.

This probe never teaches a label, forms a word identity, or mutates the live
hearing runtime.  It reads the verified mini Speech Commands archive, selects
globally source-disjoint speakers, mounts the complete frozen L0--L4 auditory
field, and evaluates exact structural quotients pairwise.  Command directory
names are withheld from every relation function and are used only after the
complete matrices exist to audit within-command lock and cross-command
rejection.

Every candidate starts from all explicit D_k/M_k/R_rev_k/U_star_k/C_k/P_k/B_k
Fractions on all thirty-two pressure/phase component paths.  Quotients and
their losses are declared in CANDIDATE_SPECS.  Exact positive-scale rays,
temporal order types, cochlear-neighborhood order, and exact C_k/B_k gate
transitions are deterministic equivalence classes; none uses a score,
tolerance, fitted constant, time alignment, transcript, q identity, Krimelack
trit, Unicode, or ML.

The output contains complete pair matrices, canonical L6 directions, token and
intersection roots, complete L4 support roots, and tuple-authority roots.  A
candidate passes only if every held-out speaker locks to every same-command
reference and rejects every other-command reference.
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
from dsf_ai_service.substrate.auditory_kernel_mount import (
    AUDITORY_KERNEL_COMPONENT_COUNT,
    auditory_kernel_component_inputs,
)
from dsf_ai_service.substrate.auditory_l4_causal_support import (
    AuditoryL4ExperienceSupport,
    mount_auditory_l4_causal_support,
)
from dsf_ai_service.substrate.auditory_l5 import AuditoryL5Owner
from dsf_ai_service.substrate.canonical_l6 import (
    L6Direction,
    canonical_l6_direction,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    COCHLEAR_CHANNEL_COUNT,
    OBSERVATION_HOP_SAMPLES,
    REQUIRED_SAMPLE_RATE_HZ,
    transduce_auditory_full_field,
)


ARCHIVE_SHA256 = (
    "49650f2341b26d886b46b3f4fb8fed59e30300b17550f1ee4a768b3106cf93a0"
)
ARCHIVE_PREFIX = "mini_speech_commands/"
COMMANDS = ("down", "go", "left", "no", "right", "stop", "up", "yes")
SPEAKERS_PER_COMMAND = 8
REFERENCE_SPEAKERS_PER_COMMAND = 5
HELD_OUT_SPEAKERS_PER_COMMAND = 3
MAX_OBSERVATIONS = 100
MAX_TOKENS_PER_CANDIDATE_EXPERIENCE = 16_384
MAX_RELATION_PAIRS = (
    len(COMMANDS)
    * SPEAKERS_PER_COMMAND
    * (len(COMMANDS) * SPEAKERS_PER_COMMAND - 1)
    // 2
)
REPORT_SCHEMA = "guala.audit.full_field_separability_census.v1"
TOKEN_SCHEMA = "guala.audit.full_field_structural_token.v1"
RELATION_SCHEMA = "guala.audit.full_field_structural_relation.v1"
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


def _fraction_text(value: Fraction) -> str:
    if not isinstance(value, Fraction):
        raise TypeError("full-field census value is not exact")
    return f"{value.numerator}/{value.denominator}"


def _direction(left: Fraction, right: Fraction) -> int:
    if not isinstance(left, Fraction) or not isinstance(right, Fraction):
        raise TypeError("full-field census relation is not exact")
    return (right > left) - (right < left)


def _positive_scale_ray(values: Sequence[Fraction]) -> tuple[str, ...]:
    """Exact quotient by one common strictly-positive rational scale."""

    exact = tuple(values)
    if not exact or any(not isinstance(value, Fraction) for value in exact):
        raise TypeError("projective full-field ray requires exact Fractions")
    pivot = next((value for value in exact if value != 0), None)
    if pivot is None:
        return tuple("0/1" for _value in exact)
    magnitude = abs(pivot)
    return tuple(_fraction_text(value / magnitude) for value in exact)


def _l6_payload(value: L6Direction) -> dict[str, object]:
    return {
        "dimensions": value.dimensions,
        "effective_dimensions": value.effective_dimensions,
        "knee": value.knee,
        "locked": value.locked,
        "matching_non_null": value.matching_non_null,
        "matching_quiescent": value.matching_quiescent,
    }


def _root(schema: str, values: Iterable[str]) -> str:
    ordered = tuple(sorted(set(values)))
    return _digest({"schema": schema, "sha256s": list(ordered)})


def _sha(value: str, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{name} is not a lowercase SHA-256 digest")
    return value


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
    tuple_integrity_sha256: str
    l4_tuple_authority_sha256: str

    def verify(self) -> None:
        if (
            len(self.fields) != len(DSF_FIELD_ORDER)
            or any(not isinstance(value, Fraction) for value in self.fields)
        ):
            raise ValueError("full-field frame lost an explicit DSF field")
        _sha(self.tuple_integrity_sha256, "tuple support integrity")
        _sha(self.l4_tuple_authority_sha256, "L4 tuple authority")


@dataclass(frozen=True, slots=True)
class FullFieldExperience:
    item: CorpusItem
    l4_support_integrity_sha256: str
    component_integrity_sha256s: tuple[str, ...]
    tuple_authority_root_sha256: str
    tuple_support_root_sha256: str
    frames_by_component: tuple[tuple[ExactFrame, ...], ...]

    @property
    def observation_count(self) -> int:
        return len(self.frames_by_component[0])

    def verify(self) -> None:
        _sha(self.l4_support_integrity_sha256, "L4 support integrity")
        _sha(self.tuple_authority_root_sha256, "L4 tuple authority root")
        _sha(self.tuple_support_root_sha256, "tuple support root")
        if (
            len(self.frames_by_component) != AUDITORY_KERNEL_COMPONENT_COUNT
            or len(self.component_integrity_sha256s)
            != AUDITORY_KERNEL_COMPONENT_COUNT
            or not 1 <= self.observation_count <= MAX_OBSERVATIONS
            or any(
                len(component) != self.observation_count
                for component in self.frames_by_component
            )
        ):
            raise ValueError("full-field experience lost auditory topology")
        for value in self.component_integrity_sha256s:
            _sha(value, "component support integrity")
        for component in self.frames_by_component:
            for frame in component:
                frame.verify()


@dataclass(frozen=True, slots=True)
class StructuralTokenSet:
    candidate_id: str
    token_sha256s: frozenset[str]
    token_witness_roots: tuple[tuple[str, str], ...]
    token_set_root_sha256: str
    quotient_receipt_sha256: str

    def verify(self, experience: FullFieldExperience) -> None:
        if (
            not self.candidate_id
            or not self.token_sha256s
            or len(self.token_sha256s)
            > MAX_TOKENS_PER_CANDIDATE_EXPERIENCE
            or tuple(value for value, _root_value in self.token_witness_roots)
            != tuple(sorted(self.token_sha256s))
        ):
            raise ValueError("full-field candidate token boundary changed")
        for token, witness in self.token_witness_roots:
            _sha(token, "candidate token")
            _sha(witness, "candidate token witness")
        expected_root = _root(
            "guala.audit.full_field_token_set.v1",
            self.token_sha256s,
        )
        if expected_root != self.token_set_root_sha256:
            raise ValueError("candidate token set root changed")
        expected_receipt = _digest({
            "candidate_id": self.candidate_id,
            "full_field_support_integrity_sha256": (
                experience.l4_support_integrity_sha256
            ),
            "schema": "guala.audit.full_field_quotient.v1",
            "token_set_root_sha256": self.token_set_root_sha256,
            "token_witness_roots": [
                [token, witness]
                for token, witness in self.token_witness_roots
            ],
        })
        if expected_receipt != self.quotient_receipt_sha256:
            raise ValueError("candidate quotient receipt changed")


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    candidate_id: str
    relation: str
    quotient_invariance: str
    quotient_loses: tuple[str, ...]
    tokenizer: Callable[[FullFieldExperience], StructuralTokenSet]

    def record(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "full_fields_used": list(DSF_FIELD_ORDER),
            "pressure_and_phase_used": True,
            "quotient_invariance": self.quotient_invariance,
            "quotient_loses": list(self.quotient_loses),
            "relation": self.relation,
        }


def _frames_from_support(
    item: CorpusItem,
    support: AuditoryL4ExperienceSupport,
) -> FullFieldExperience:
    component_frames: list[tuple[ExactFrame, ...]] = []
    tuple_authorities = []
    tuple_supports = []
    component_integrities = []
    observation_count: int | None = None
    for component in support.components:
        component_integrities.append(component.integrity_receipt_sha256)
        expanded: list[ExactFrame | None] = [
            None
        ] * (component.tuples[-1].source_index_end + 1)
        for value in component.tuples:
            fields = tuple(field for _name, field in value.fields)
            frame = ExactFrame(
                fields=fields,
                tuple_integrity_sha256=value.integrity_receipt_sha256,
                l4_tuple_authority_sha256=(
                    value.l4_tuple_authority_receipt_sha256
                ),
            )
            frame.verify()
            tuple_authorities.append(frame.l4_tuple_authority_sha256)
            tuple_supports.append(frame.tuple_integrity_sha256)
            for index in range(
                value.source_index_start,
                value.source_index_end + 1,
            ):
                if expanded[index] is not None:
                    raise ValueError("L4 tuple support overlaps itself")
                expanded[index] = frame
        if any(value is None for value in expanded):
            raise ValueError("L4 tuple support skipped an observation")
        mounted = tuple(value for value in expanded if value is not None)
        if observation_count is None:
            observation_count = len(mounted)
        elif len(mounted) != observation_count:
            raise ValueError("auditory components lost their common grid")
        component_frames.append(mounted)
    result = FullFieldExperience(
        item=item,
        l4_support_integrity_sha256=support.integrity_receipt_sha256,
        component_integrity_sha256s=tuple(component_integrities),
        tuple_authority_root_sha256=_root(
            "guala.audit.l4_tuple_authority_root.v1",
            tuple_authorities,
        ),
        tuple_support_root_sha256=_root(
            "guala.audit.l4_tuple_support_root.v1",
            tuple_supports,
        ),
        frames_by_component=tuple(component_frames),
    )
    result.verify()
    return result


def _token(
    *,
    candidate_id: str,
    quotient: object,
    witness_sha256s: Iterable[str],
) -> tuple[str, str]:
    witnesses = tuple(sorted(set(witness_sha256s)))
    if not witnesses:
        raise ValueError("structural quotient lacks full-field witnesses")
    for value in witnesses:
        _sha(value, "structural quotient witness")
    token = _digest({
        "candidate_id": candidate_id,
        "quotient": quotient,
        "schema": TOKEN_SCHEMA,
    })
    witness_root = _digest({
        "candidate_token_sha256": token,
        "schema": "guala.audit.full_field_token_witness.v1",
        "tuple_support_integrity_sha256s": list(witnesses),
    })
    return token, witness_root


def _finish_tokens(
    candidate_id: str,
    experience: FullFieldExperience,
    values: Iterable[tuple[str, str]],
) -> StructuralTokenSet:
    mounted: dict[str, set[str]] = {}
    for token, witness in values:
        mounted.setdefault(token, set()).add(witness)
    if not mounted:
        raise ValueError(f"{candidate_id} produced no structural tokens")
    witness_pairs = tuple(
        (
            token,
            _root(
                "guala.audit.full_field_token_witness_set.v1",
                witnesses,
            ),
        )
        for token, witnesses in sorted(mounted.items())
    )
    token_values = frozenset(mounted)
    token_root = _root(
        "guala.audit.full_field_token_set.v1",
        token_values,
    )
    receipt = _digest({
        "candidate_id": candidate_id,
        "full_field_support_integrity_sha256": (
            experience.l4_support_integrity_sha256
        ),
        "schema": "guala.audit.full_field_quotient.v1",
        "token_set_root_sha256": token_root,
        "token_witness_roots": [
            [token, witness] for token, witness in witness_pairs
        ],
    })
    result = StructuralTokenSet(
        candidate_id=candidate_id,
        token_sha256s=token_values,
        token_witness_roots=witness_pairs,
        token_set_root_sha256=token_root,
        quotient_receipt_sha256=receipt,
    )
    result.verify(experience)
    return result


def _component_state_ray(
    experience: FullFieldExperience,
) -> StructuralTokenSet:
    candidate = "component_state_positive_scale_ray_v1"
    values = []
    for topology_index, frames in enumerate(
        experience.frames_by_component
    ):
        prior_quotient = None
        for frame in frames:
            quotient = {
                "positive_scale_ray": list(
                    _positive_scale_ray(frame.fields)
                ),
                "topology_index": topology_index,
            }
            if quotient == prior_quotient:
                continue
            prior_quotient = quotient
            values.append(_token(
                candidate_id=candidate,
                quotient=quotient,
                witness_sha256s=(frame.tuple_integrity_sha256,),
            ))
    return _finish_tokens(candidate, experience, values)


def _component_delta_gate(
    experience: FullFieldExperience,
) -> StructuralTokenSet:
    candidate = "component_full_delta_ray_b_c_gate_v1"
    values = []
    b_index = DSF_FIELD_ORDER.index("B_k")
    c_index = DSF_FIELD_ORDER.index("C_k")
    for topology_index, frames in enumerate(
        experience.frames_by_component
    ):
        prior_gate: tuple[int, int] | None = None
        prior_frame = frames[0]
        for frame in frames[1:]:
            deltas = tuple(
                right - left
                for left, right in zip(
                    prior_frame.fields,
                    frame.fields,
                    strict=True,
                )
            )
            gate = (
                _direction(
                    prior_frame.fields[b_index],
                    frame.fields[b_index],
                ),
                _direction(
                    prior_frame.fields[c_index],
                    frame.fields[c_index],
                ),
            )
            if gate != prior_gate:
                values.append(_token(
                    candidate_id=candidate,
                    quotient={
                        "B_k_direction": gate[0],
                        "C_k_direction": gate[1],
                        "positive_scale_delta_ray": list(
                            _positive_scale_ray(deltas)
                        ),
                        "topology_index": topology_index,
                    },
                    witness_sha256s=(
                        prior_frame.tuple_integrity_sha256,
                        frame.tuple_integrity_sha256,
                    ),
                ))
            prior_gate = gate
            prior_frame = frame
    return _finish_tokens(candidate, experience, values)


def _component_temporal_order_gate(
    experience: FullFieldExperience,
) -> StructuralTokenSet:
    candidate = "component_joint_field_order_b_c_gate_v1"
    values = []
    b_index = DSF_FIELD_ORDER.index("B_k")
    c_index = DSF_FIELD_ORDER.index("C_k")
    for topology_index, frames in enumerate(
        experience.frames_by_component
    ):
        prior_order = None
        prior_frame = frames[0]
        for frame in frames[1:]:
            order = tuple(
                _direction(left, right)
                for left, right in zip(
                    prior_frame.fields,
                    frame.fields,
                    strict=True,
                )
            )
            gate = (order[b_index], order[c_index])
            quotient = {
                "B_k_direction": gate[0],
                "C_k_direction": gate[1],
                "field_order": list(order),
                "topology_index": topology_index,
            }
            if quotient != prior_order:
                values.append(_token(
                    candidate_id=candidate,
                    quotient=quotient,
                    witness_sha256s=(
                        prior_frame.tuple_integrity_sha256,
                        frame.tuple_integrity_sha256,
                    ),
                ))
            prior_order = quotient
            prior_frame = frame
    return _finish_tokens(candidate, experience, values)


def _neighborhood_tokens(
    experience: FullFieldExperience,
    *,
    projective: bool,
) -> StructuralTokenSet:
    candidate = (
        "cochlear_neighborhood_full_ray_order_gate_v1"
        if projective
        else "cochlear_neighborhood_joint_order_gate_v1"
    )
    values = []
    b_index = DSF_FIELD_ORDER.index("B_k")
    c_index = DSF_FIELD_ORDER.index("C_k")
    frame_count = experience.observation_count
    for component_parity, component_kind in (
        (0, "pressure"),
        (1, "phase"),
    ):
        for neighborhood_start in range(COCHLEAR_CHANNEL_COUNT - 2):
            component_indices = tuple(
                channel * 2 + component_parity
                for channel in range(
                    neighborhood_start,
                    neighborhood_start + 3,
                )
            )
            prior_quotient = None
            for frame_index in range(1, frame_count):
                prior_frames = tuple(
                    experience.frames_by_component[index][frame_index - 1]
                    for index in component_indices
                )
                current_frames = tuple(
                    experience.frames_by_component[index][frame_index]
                    for index in component_indices
                )
                temporal_orders = tuple(
                    tuple(
                        _direction(left, right)
                        for left, right in zip(
                            prior.fields,
                            current.fields,
                            strict=True,
                        )
                    )
                    for prior, current in zip(
                        prior_frames,
                        current_frames,
                        strict=True,
                    )
                )
                cross_channel_orders = tuple(
                    tuple(
                        _direction(
                            current_frames[left].fields[field_index],
                            current_frames[right].fields[field_index],
                        )
                        for left, right in ((0, 1), (1, 2), (0, 2))
                    )
                    for field_index in range(len(DSF_FIELD_ORDER))
                )
                gate_directions = tuple(
                    (order[b_index], order[c_index])
                    for order in temporal_orders
                )
                quotient: dict[str, object] = {
                    "component_kind": component_kind,
                    "cross_channel_field_orders": [
                        list(value) for value in cross_channel_orders
                    ],
                    "gate_directions_B_k_C_k": [
                        list(value) for value in gate_directions
                    ],
                    "neighborhood_start": neighborhood_start,
                    "temporal_field_orders": [
                        list(value) for value in temporal_orders
                    ],
                }
                if projective:
                    quotient["positive_scale_state_rays"] = [
                        list(_positive_scale_ray(frame.fields))
                        for frame in current_frames
                    ]
                    quotient["positive_scale_delta_rays"] = [
                        list(_positive_scale_ray(tuple(
                            right - left
                            for left, right in zip(
                                prior.fields,
                                current.fields,
                                strict=True,
                            )
                        )))
                        for prior, current in zip(
                            prior_frames,
                            current_frames,
                            strict=True,
                        )
                    ]
                if quotient == prior_quotient:
                    continue
                prior_quotient = quotient
                values.append(_token(
                    candidate_id=candidate,
                    quotient=quotient,
                    witness_sha256s=tuple(
                        value.tuple_integrity_sha256
                        for value in (*prior_frames, *current_frames)
                    ),
                ))
    return _finish_tokens(candidate, experience, values)


def _neighborhood_ray_gate(
    experience: FullFieldExperience,
) -> StructuralTokenSet:
    return _neighborhood_tokens(experience, projective=True)


def _neighborhood_order_gate(
    experience: FullFieldExperience,
) -> StructuralTokenSet:
    return _neighborhood_tokens(experience, projective=False)


CANDIDATE_SPECS = (
    CandidateSpec(
        candidate_id="component_state_positive_scale_ray_v1",
        relation="reciprocal canonical L6 over exact quotient-token sets",
        quotient_invariance=(
            "one strictly-positive rational scale per seven-field tuple"
        ),
        quotient_loses=(
            "absolute common field scale",
            "token multiplicity",
            "global token order",
        ),
        tokenizer=_component_state_ray,
    ),
    CandidateSpec(
        candidate_id="component_full_delta_ray_b_c_gate_v1",
        relation="reciprocal canonical L6 over exact quotient-token sets",
        quotient_invariance=(
            "one strictly-positive rational scale per seven-field causal "
            "delta; exact C_k/B_k direction changes gate emission"
        ),
        quotient_loses=(
            "absolute common causal-delta scale",
            "unchanged intervals between exact C_k/B_k gate transitions",
            "token multiplicity",
            "global token order",
        ),
        tokenizer=_component_delta_gate,
    ),
    CandidateSpec(
        candidate_id="component_joint_field_order_b_c_gate_v1",
        relation="reciprocal canonical L6 over exact quotient-token sets",
        quotient_invariance=(
            "independent strictly-monotone transform of each field over "
            "adjacent causal observations"
        ),
        quotient_loses=(
            "all field magnitudes",
            "causal-delta ratios",
            "token multiplicity",
            "global token order",
        ),
        tokenizer=_component_temporal_order_gate,
    ),
    CandidateSpec(
        candidate_id="cochlear_neighborhood_full_ray_order_gate_v1",
        relation="reciprocal canonical L6 over exact quotient-token sets",
        quotient_invariance=(
            "positive common scale within each component field tuple while "
            "retaining three-channel same-field order and exact C_k/B_k gates"
        ),
        quotient_loses=(
            "absolute common scale inside each component tuple",
            "token multiplicity",
            "global neighborhood-token order",
        ),
        tokenizer=_neighborhood_ray_gate,
    ),
    CandidateSpec(
        candidate_id="cochlear_neighborhood_joint_order_gate_v1",
        relation="reciprocal canonical L6 over exact quotient-token sets",
        quotient_invariance=(
            "independent monotone field transforms while retaining joint "
            "three-channel temporal order and exact C_k/B_k gates"
        ),
        quotient_loses=(
            "all field magnitudes",
            "all causal-delta ratios",
            "token multiplicity",
            "global neighborhood-token order",
        ),
        tokenizer=_neighborhood_order_gate,
    ),
)


def _relation(
    candidate_id: str,
    left_item_id: str,
    right_item_id: str,
    left: StructuralTokenSet,
    right: StructuralTokenSet,
) -> dict[str, object]:
    if left.candidate_id != candidate_id or right.candidate_id != candidate_id:
        raise ValueError("candidate relation crossed quotient authorities")
    intersection = left.token_sha256s.intersection(right.token_sha256s)
    matching = len(intersection)
    left_l6 = canonical_l6_direction(
        dimensions=len(left.token_sha256s),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    right_l6 = canonical_l6_direction(
        dimensions=len(right.token_sha256s),
        matching_non_null=matching,
        matching_quiescent=0,
    )
    payload = {
        "candidate_id": candidate_id,
        "intersection_root_sha256": _root(
            "guala.audit.full_field_intersection.v1",
            intersection,
        ),
        "left_item_id": left_item_id,
        "left_l6": _l6_payload(left_l6),
        "left_quotient_receipt_sha256": left.quotient_receipt_sha256,
        "matching_token_count": matching,
        "relation_locked": left_l6.locked and right_l6.locked,
        "right_item_id": right_item_id,
        "right_l6": _l6_payload(right_l6),
        "right_quotient_receipt_sha256": right.quotient_receipt_sha256,
        "schema": RELATION_SCHEMA,
    }
    return payload | {"authority_receipt_sha256": _digest(payload)}


def _select_corpus(archive: zipfile.ZipFile) -> tuple[CorpusItem, ...]:
    names = set(archive.namelist())
    selected: list[CorpusItem] = []
    used_speakers: set[str] = set()
    ordinal = 0
    for command in COMMANDS:
        prefix = f"{ARCHIVE_PREFIX}{command}/"
        by_speaker: dict[str, list[str]] = {}
        for name in sorted(
            value for value in names
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
            member = None
            wav_data = None
            for candidate in by_speaker[speaker]:
                candidate_data = archive.read(candidate)
                with wave.open(
                    io.BytesIO(candidate_data),
                    "rb",
                ) as source:
                    if (
                        source.getnchannels() == 1
                        and source.getsampwidth() == 2
                        and source.getframerate()
                        == REQUIRED_SAMPLE_RATE_HZ
                        and OBSERVATION_HOP_SAMPLES
                        <= source.getnframes()
                        <= REQUIRED_SAMPLE_RATE_HZ
                        and source.getnframes()
                        % OBSERVATION_HOP_SAMPLES
                        == 0
                        and source.getcomptype() == "NONE"
                    ):
                        member = candidate
                        wav_data = candidate_data
                        break
            if member is None or wav_data is None:
                continue
            pcm_sha = hashlib.sha256(wav_data).hexdigest()
            split = (
                "reference"
                if len(command_items) < REFERENCE_SPEAKERS_PER_COMMAND
                else "held_out"
            )
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
                split=split,
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
                f"corpus lacks {SPEAKERS_PER_COMMAND} globally "
                f"source-disjoint {command} speakers"
            )
    if (
        len(selected) != len(COMMANDS) * SPEAKERS_PER_COMMAND
        or len({value.speaker_id for value in selected}) != len(selected)
    ):
        raise RuntimeError("corpus speaker custody is not source-disjoint")
    return tuple(selected)


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
            raise ValueError("speech command WAV left canonical PCM custody")
        pcm = source.readframes(frame_count)
    if len(pcm) != frame_count * 2:
        raise ValueError("speech command WAV PCM length changed")
    return np.frombuffer(pcm, dtype="<i2").astype(np.float64) / 32_768.0


def _mount_experience(
    *,
    item: CorpusItem,
    wav_data: bytes,
    l5_owner: AuditoryL5Owner,
) -> FullFieldExperience:
    signal = _pcm_from_wav(wav_data)
    capture = transduce_auditory_full_field(
        signal,
        sample_rate_hz=REQUIRED_SAMPLE_RATE_HZ,
    )
    anchor = Fraction(item.ordinal * 2)
    components = auditory_kernel_component_inputs(
        capture,
        source_anchor=anchor,
    )
    built = build_transaction_owned_six_sense_full_field(
        assembly_id=f"full-field-census-{item.item_id}",
        source_time_start=anchor,
        source_time_end=anchor + Fraction(
            len(signal),
            REQUIRED_SAMPLE_RATE_HZ,
        ),
        observed_substreams={PhysicalSense.SOUND: components},
        states={
            sense: (
                SenseBoundaryState.OBSERVED
                if sense is PhysicalSense.SOUND
                else SenseBoundaryState.SENSOR_UNAVAILABLE
            )
            for sense in SENSE_ORDER
        },
    )
    experience = l5_owner.settle(built, event_boundary="ambient")
    if experience is None:
        raise RuntimeError("full-field census did not reach auditory L5")
    support = mount_auditory_l4_causal_support(experience)
    support.verify(experience)
    return _frames_from_support(item, support)


def _matrix_and_evaluation(
    *,
    items: tuple[CorpusItem, ...],
    token_sets: Mapping[str, StructuralTokenSet],
    candidate_id: str,
) -> tuple[list[list[dict[str, object]]], dict[str, object]]:
    matrix: list[list[dict[str, object]]] = []
    pair_count = 0
    for left in items:
        row = []
        for right in items:
            if left.item_id == right.item_id:
                tokens = token_sets[left.item_id]
                direction = canonical_l6_direction(
                    dimensions=len(tokens.token_sha256s),
                    matching_non_null=len(tokens.token_sha256s),
                    matching_quiescent=0,
                )
                row.append({
                    "authority_receipt_sha256": _digest({
                        "candidate_id": candidate_id,
                        "item_id": left.item_id,
                        "schema": "guala.audit.full_field_identity.v1",
                        "token_set_root_sha256": (
                            tokens.token_set_root_sha256
                        ),
                    }),
                    "intersection_root_sha256": (
                        tokens.token_set_root_sha256
                    ),
                    "left_l6": _l6_payload(direction),
                    "matching_token_count": len(tokens.token_sha256s),
                    "relation_locked": True,
                    "right_l6": _l6_payload(direction),
                })
            else:
                row.append(_relation(
                    candidate_id,
                    left.item_id,
                    right.item_id,
                    token_sets[left.item_id],
                    token_sets[right.item_id],
                ))
                if left.ordinal < right.ordinal:
                    pair_count += 1
        matrix.append(row)
    if pair_count != MAX_RELATION_PAIRS:
        raise RuntimeError("full-field relation matrix is incomplete")

    item_index = {
        value.item_id: index for index, value in enumerate(items)
    }
    held_out_checks = []
    within_pair_failures = []
    cross_pair_failures = []
    within_locked = 0
    within_total = 0
    cross_locked = 0
    cross_total = 0
    for left_index, left in enumerate(items):
        for right_index in range(left_index + 1, len(items)):
            right = items[right_index]
            locked = bool(
                matrix[left_index][right_index]["relation_locked"]
            )
            if left.oracle_command == right.oracle_command:
                within_total += 1
                within_locked += int(locked)
                if not locked:
                    within_pair_failures.append(
                        [left.item_id, right.item_id]
                    )
            else:
                cross_total += 1
                cross_locked += int(locked)
                if locked:
                    cross_pair_failures.append(
                        [left.item_id, right.item_id]
                    )
    for query in items:
        if query.split != "held_out":
            continue
        same_references = tuple(
            value for value in items
            if (
                value.split == "reference"
                and value.oracle_command == query.oracle_command
            )
        )
        other_references = tuple(
            value for value in items
            if (
                value.split == "reference"
                and value.oracle_command != query.oracle_command
            )
        )
        same_locked = tuple(
            value.item_id for value in same_references
            if matrix[item_index[query.item_id]][
                item_index[value.item_id]
            ]["relation_locked"]
        )
        other_locked = tuple(
            value.item_id for value in other_references
            if matrix[item_index[query.item_id]][
                item_index[value.item_id]
            ]["relation_locked"]
        )
        held_out_checks.append({
            "held_out_item_id": query.item_id,
            "oracle_command": query.oracle_command,
            "other_command_reference_lock_count": len(other_locked),
            "other_command_reference_locks": list(other_locked),
            "passed": (
                len(same_locked) == REFERENCE_SPEAKERS_PER_COMMAND
                and not other_locked
            ),
            "same_command_reference_lock_count": len(same_locked),
            "same_command_reference_locks": list(same_locked),
        })
    evaluation = {
        "cross_command_locked_pairs": cross_locked,
        "cross_command_pair_count": cross_total,
        "cross_pair_failure_root_sha256": _digest({
            "pairs": cross_pair_failures,
            "schema": "guala.audit.cross_pair_failures.v1",
        }),
        "held_out_checks": held_out_checks,
        "held_out_pass_count": sum(
            bool(value["passed"]) for value in held_out_checks
        ),
        "held_out_total": len(held_out_checks),
        "relation_passed": (
            within_locked == within_total
            and cross_locked == 0
            and all(value["passed"] for value in held_out_checks)
        ),
        "within_command_locked_pairs": within_locked,
        "within_command_pair_count": within_total,
        "within_pair_failure_root_sha256": _digest({
            "pairs": within_pair_failures,
            "schema": "guala.audit.within_pair_failures.v1",
        }),
    }
    return matrix, evaluation


def _experience_record(
    experience: FullFieldExperience,
    token_sets: Mapping[str, StructuralTokenSet],
) -> dict[str, object]:
    return {
        "archive_member": experience.item.archive_member,
        "candidate_quotients": {
            candidate_id: {
                "quotient_receipt_sha256": value.quotient_receipt_sha256,
                "token_count": len(value.token_sha256s),
                "token_set_root_sha256": value.token_set_root_sha256,
                "token_witness_catalog_root_sha256": _digest({
                    "schema": (
                        "guala.audit.full_field_token_witness_catalog.v1"
                    ),
                    "token_witness_roots": [
                        [token, witness]
                        for token, witness in value.token_witness_roots
                    ],
                }),
            }
            for candidate_id, value in sorted(token_sets.items())
        },
        "component_support_integrity_sha256s": list(
            experience.component_integrity_sha256s
        ),
        "full_field_support_integrity_sha256": (
            experience.l4_support_integrity_sha256
        ),
        "item_id": experience.item.item_id,
        "observation_count": experience.observation_count,
        "oracle_command": experience.item.oracle_command,
        "pcm_sha256": experience.item.pcm_sha256,
        "speaker_id": experience.item.speaker_id,
        "split": experience.item.split,
        "tuple_authority_root_sha256": (
            experience.tuple_authority_root_sha256
        ),
        "tuple_support_root_sha256": experience.tuple_support_root_sha256,
    }


def run_census(archive_path: Path) -> dict[str, object]:
    if not archive_path.is_file():
        raise FileNotFoundError(f"speech command archive absent: {archive_path}")
    archive_digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if archive_digest != ARCHIVE_SHA256:
        raise ValueError("speech command archive authority changed")
    with zipfile.ZipFile(archive_path) as archive:
        items = _select_corpus(archive)
        executor = start_exact_field_executor()
        executor.assert_healthy()
        l5_owner = AuditoryL5Owner(
            log_event=lambda *_args, **_kwargs: None
        )
        try:
            experiences = tuple(
                _mount_experience(
                    item=item,
                    wav_data=archive.read(item.archive_member),
                    l5_owner=l5_owner,
                )
                for item in items
            )
        finally:
            stop_exact_field_executor()
    tokens_by_candidate: dict[
        str, dict[str, StructuralTokenSet]
    ] = {}
    for spec in CANDIDATE_SPECS:
        mounted = {}
        for experience in experiences:
            result = spec.tokenizer(experience)
            if result.candidate_id != spec.candidate_id:
                raise ValueError("candidate tokenizer changed its identity")
            result.verify(experience)
            mounted[experience.item.item_id] = result
        tokens_by_candidate[spec.candidate_id] = mounted

    candidate_reports = {}
    for spec in CANDIDATE_SPECS:
        matrix, evaluation = _matrix_and_evaluation(
            items=items,
            token_sets=tokens_by_candidate[spec.candidate_id],
            candidate_id=spec.candidate_id,
        )
        candidate_reports[spec.candidate_id] = {
            "evaluation": evaluation,
            "matrix": matrix,
            "specification": spec.record(),
        }
    report = {
        "archive_sha256": archive_digest,
        "candidate_reports": candidate_reports,
        "commands": list(COMMANDS),
        "experience_records": [
            _experience_record(
                experience,
                {
                    candidate_id: values[experience.item.item_id]
                    for candidate_id, values
                    in tokens_by_candidate.items()
                },
            )
            for experience in experiences
        ],
        "field_order": list(DSF_FIELD_ORDER),
        "held_out_speakers_per_command": (
            HELD_OUT_SPEAKERS_PER_COMMAND
        ),
        "labels_used_by_relations": False,
        "l0_l4_modified": False,
        "matrix_item_ids": [value.item_id for value in items],
        "pressure_and_phase_component_count": (
            AUDITORY_KERNEL_COMPONENT_COUNT
        ),
        "reference_speakers_per_command": (
            REFERENCE_SPEAKERS_PER_COMMAND
        ),
        "schema": REPORT_SCHEMA,
        "source_disjoint_speaker_count": len({
            value.speaker_id for value in items
        }),
    }
    return report | {
        "authority_receipt_sha256": _digest(report),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive",
        type=Path,
        required=True,
        help="verified mini_speech_commands.zip",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="emit evaluations and authority roots without matrices",
    )
    args = parser.parse_args()
    report = run_census(args.archive)
    if args.summary:
        report = {
            "archive_sha256": report["archive_sha256"],
            "authority_receipt_sha256": (
                report["authority_receipt_sha256"]
            ),
            "candidates": {
                candidate_id: value["evaluation"]
                for candidate_id, value
                in report["candidate_reports"].items()
            },
            "schema": "guala.audit.full_field_separability_summary.v1",
            "source_disjoint_speaker_count": (
                report["source_disjoint_speaker_count"]
            ),
        }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
