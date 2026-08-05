"""Bounded THING-grounded recurrent-q to articulatory vocal turns.

The owner retains an exact structural form and compact authenticated references
to evidence already owned by the teaching, lived-context, and articulatory
authorities.  It never duplicates the upstream sensory settlements.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryGeneratedEmission,
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.causal_thing_lived_context import (
    CausalThingLivedContextEvent,
    CausalThingLivedContextOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.lived_vocal_teaching_episode import (
    LivedVocalTeachingEpisode,
    LivedVocalTeachingEpisodeAuthority,
)
from dsf_ai_service.substrate.w1_binaural_grounding_evidence import (
    W1BinauralGroundingEvidence,
    W1BinauralGroundingEvidenceAuthority,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    PreparedW1SelfAcousticMount,
    W1ArticulatorySelfAcousticCommitUndo,
    W1SelfAcousticMount,
    W1SelfAcousticPropagationAuthority,
)


PROFILE_SCHEMA = "guala.grounded_articulatory_vocal_turn.profile.v2"
OCCURRENCE_SCHEMA = "guala.grounded_articulatory_vocal_turn.occurrence.v2"
DECISION_SCHEMA = "guala.grounded_articulatory_vocal_turn.decision.v2"
OUTPUT_SCHEMA = "guala.grounded_articulatory_vocal_turn.output.v2"
STATE_SCHEMA = "guala.grounded_articulatory_vocal_turn.state.v2"
ENVELOPE_SCHEMA = "guala.grounded_articulatory_vocal_turn.state_hmac.v2"
FORM_SCHEMA = "guala.binaural_recurrent_q_allen_graph.v1"
_OCCURRENCE_DOMAIN = b"guala-grounded-articulatory-occurrence-v2\0"
_DECISION_DOMAIN = b"guala-grounded-articulatory-decision-v2\0"
_OUTPUT_DOMAIN = b"guala-grounded-articulatory-output-v2\0"
_STATE_DOMAIN = b"guala-grounded-articulatory-state-v2\0"
_PREPARED_AUTHORITY = object()
_UNDO_AUTHORITY = object()
_HEX = frozenset("0123456789abcdef")
_ALLEN_RELATIONS = frozenset({
    "after",
    "before",
    "contains",
    "during",
    "equal",
    "finished_by",
    "finishes",
    "meets",
    "met_by",
    "overlapped_by",
    "overlaps",
    "started_by",
    "starts",
})


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _ascii(value: object, label: str, *, maximum: int = 512) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
    ):
        raise ValueError(f"grounded articulatory {label} changed")
    try:
        value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError(
            f"grounded articulatory {label} is not ASCII"
        ) from error
    return value


def _key(value: bytes | str) -> bytes:
    if isinstance(value, str):
        try:
            raw = value.encode("ascii")
        except UnicodeEncodeError as error:
            raise ValueError(
                "grounded articulatory authority key is not ASCII"
            ) from error
    else:
        raw = value
    if not isinstance(raw, bytes) or not 32 <= len(raw) <= 4_096:
        raise ValueError("grounded articulatory key boundary changed")
    return raw


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"grounded articulatory {label} changed")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"grounded articulatory {label} changed")
    return value


def _fraction(value: object, label: str) -> Fraction:
    if not isinstance(value, str) or value.count("/") != 1:
        raise ValueError(f"grounded articulatory {label} is not exact")
    numerator, denominator = value.split("/", 1)
    try:
        result = Fraction(int(numerator), int(denominator))
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError(
            f"grounded articulatory {label} is not exact"
        ) from error
    if f"{result.numerator}/{result.denominator}" != value:
        raise ValueError(f"grounded articulatory {label} is not canonical")
    return result


def _evidence_record(
    value: W1BinauralGroundingEvidence,
) -> dict[str, object]:
    return {
        **value.payload(),
        "authority_hmac_sha256": value.authority_hmac_sha256,
        "authority_receipt_sha256": value.authority_receipt_sha256,
        "episode_id": value.episode_id,
    }


def _allen(
    a_start: Fraction,
    a_end: Fraction,
    b_start: Fraction,
    b_end: Fraction,
) -> str:
    if a_end < b_start:
        return "before"
    if a_end == b_start:
        return "meets"
    if a_start < b_start < a_end < b_end:
        return "overlaps"
    if a_start == b_start and a_end < b_end:
        return "starts"
    if b_start < a_start and a_end < b_end:
        return "during"
    if b_start < a_start and a_end == b_end:
        return "finishes"
    if a_start == b_start and a_end == b_end:
        return "equal"
    inverse = {
        "before": "after",
        "meets": "met_by",
        "overlaps": "overlapped_by",
        "starts": "started_by",
        "during": "contains",
        "finishes": "finished_by",
        "equal": "equal",
    }
    return inverse[_allen(b_start, b_end, a_start, a_end)]


def _validate_form(form_json: str, maximum_bytes: int) -> str:
    _ascii(form_json, "structural form", maximum=maximum_bytes)
    try:
        form = json.loads(form_json)
    except json.JSONDecodeError as error:
        raise ValueError(
            "grounded articulatory structural form is unreadable"
        ) from error
    if (
        not isinstance(form, Mapping)
        or set(form)
        != {"nodes", "pairwise_allen_relations", "schema"}
        or form.get("schema") != FORM_SCHEMA
        or not isinstance(form.get("nodes"), list)
        or not isinstance(form.get("pairwise_allen_relations"), list)
        or _canonical(form).decode("ascii") != form_json
        or len(form_json.encode("ascii")) > maximum_bytes
    ):
        raise ValueError("grounded articulatory structural form changed")
    nodes = form["nodes"]
    for node in nodes:
        if (
            not isinstance(node, Mapping)
            or set(node) != {"ear_id", "neuron_id", "segment_index"}
            or node.get("ear_id") not in {"left", "right"}
            or isinstance(node.get("segment_index"), bool)
            or not isinstance(node.get("segment_index"), int)
            or node["segment_index"] < 0
        ):
            raise ValueError(
                "grounded articulatory structural node changed"
            )
        _ascii(node.get("neuron_id"), "neuron identity")
    expected_pairs = len(nodes) * (len(nodes) - 1) // 2
    relations = form["pairwise_allen_relations"]
    if len(relations) != expected_pairs:
        raise ValueError(
            "grounded articulatory structural relation count changed"
        )
    cursor = 0
    for left in range(len(nodes)):
        for right in range(left + 1, len(nodes)):
            relation = relations[cursor]
            cursor += 1
            if (
                not isinstance(relation, list)
                or len(relation) != 3
                or relation[0] != left
                or relation[1] != right
                or relation[2] not in _ALLEN_RELATIONS
            ):
                raise ValueError(
                    "grounded articulatory structural relation changed"
                )
    if {node["ear_id"] for node in nodes} != {"left", "right"}:
        raise ValueError("grounded articulatory form is not binaural")
    return form_json


def _structural_form(
    evidence: W1BinauralGroundingEvidence,
    maximum_bytes: int,
) -> str:
    activations: list[dict[str, object]] = []
    for activation in evidence.activations:
        activation.verify()
        record = json.loads(activation.activation_json)
        segment = record.get("segment_index")
        if (
            isinstance(segment, bool)
            or not isinstance(segment, int)
            or segment < 0
        ):
            raise ValueError(
                "grounded articulatory recurrent-q segment changed"
            )
        activations.append({
            "ear_id": activation.ear_id,
            "neuron_id": activation.neuron_id,
            "segment_index": segment,
            "_start": _fraction(
                record.get("source_time_start"), "activation start"
            ),
            "_end": _fraction(
                record.get("source_time_end"), "activation end"
            ),
        })
    activations.sort(key=lambda item: (
        item["ear_id"],
        item["neuron_id"],
        item["segment_index"],
        item["_start"],
        item["_end"],
    ))
    pair_count = len(activations) * (len(activations) - 1) // 2
    if pair_count * 8 > maximum_bytes:
        raise RuntimeError(
            "grounded articulatory structural form capacity exhausted"
        )
    nodes = [
        {
            "ear_id": item["ear_id"],
            "neuron_id": item["neuron_id"],
            "segment_index": item["segment_index"],
        }
        for item in activations
    ]
    relations: list[list[object]] = []
    cross_ear = False
    for left in range(len(activations)):
        for right in range(left + 1, len(activations)):
            relations.append([
                left,
                right,
                _allen(
                    activations[left]["_start"],
                    activations[left]["_end"],
                    activations[right]["_start"],
                    activations[right]["_end"],
                ),
            ])
            cross_ear = cross_ear or (
                activations[left]["ear_id"]
                != activations[right]["ear_id"]
            )
    if not cross_ear:
        raise ValueError(
            "grounded articulatory form lost cross-ear relation"
        )
    result = _canonical({
        "nodes": nodes,
        "pairwise_allen_relations": relations,
        "schema": FORM_SCHEMA,
    }).decode("ascii")
    return _validate_form(result, maximum_bytes)


@dataclass(frozen=True, slots=True)
class GroundedArticulatoryVocalTurnProfile:
    profile_id: str
    max_occurrences: int
    max_occurrence_bytes: int
    max_state_bytes: int
    authority_receipt_sha256: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        max_occurrences: int,
        max_occurrence_bytes: int,
        max_state_bytes: int,
    ) -> "GroundedArticulatoryVocalTurnProfile":
        provisional = cls(
            profile_id=_ascii(profile_id, "profile identity"),
            max_occurrences=_positive(
                max_occurrences, "occurrence capacity"
            ),
            max_occurrence_bytes=_positive(
                max_occurrence_bytes, "occurrence byte capacity"
            ),
            max_state_bytes=_positive(
                max_state_bytes, "state byte capacity"
            ),
            authority_receipt_sha256="0" * 64,
        )
        if provisional.max_state_bytes <= provisional.max_occurrence_bytes:
            raise ValueError(
                "grounded articulatory state cannot hold one occurrence"
            )
        return cls(
            profile_id=provisional.profile_id,
            max_occurrences=provisional.max_occurrences,
            max_occurrence_bytes=provisional.max_occurrence_bytes,
            max_state_bytes=provisional.max_state_bytes,
            authority_receipt_sha256=_digest(provisional.payload()),
        )

    def payload(self) -> dict[str, object]:
        return {
            "max_occurrence_bytes": self.max_occurrence_bytes,
            "max_occurrences": self.max_occurrences,
            "max_state_bytes": self.max_state_bytes,
            "profile_id": self.profile_id,
            "schema": PROFILE_SCHEMA,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }

    def verify(self) -> None:
        if self != GroundedArticulatoryVocalTurnProfile.create(
            profile_id=self.profile_id,
            max_occurrences=self.max_occurrences,
            max_occurrence_bytes=self.max_occurrence_bytes,
            max_state_bytes=self.max_state_bytes,
        ):
            raise ValueError(
                "grounded articulatory profile authority changed"
            )


@dataclass(frozen=True, slots=True)
class GroundedArticulatoryTeachingOccurrence:
    teaching_episode: LivedVocalTeachingEpisode
    external_form: W1BinauralGroundingEvidence
    lived_context_event: CausalThingLivedContextEvent
    articulatory_program: ArticulatoryProgram


@dataclass(frozen=True, slots=True)
class GroundedArticulatoryLearnedOccurrence:
    occurrence_id: str
    form_sha256: str
    form_json: str
    thing_id: str
    program_id: str
    teaching_episode_id: str
    teaching_episode_receipt_sha256: str
    external_source_occurrence_id: str
    external_settlement_receipt_sha256: str
    external_grounding_receipt_sha256: str
    lived_context_event_receipt_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "external_grounding_receipt_sha256": (
                self.external_grounding_receipt_sha256
            ),
            "external_settlement_receipt_sha256": (
                self.external_settlement_receipt_sha256
            ),
            "external_source_occurrence_id": (
                self.external_source_occurrence_id
            ),
            "form_json": self.form_json,
            "form_sha256": self.form_sha256,
            "lived_context_event_receipt_sha256": (
                self.lived_context_event_receipt_sha256
            ),
            "program_id": self.program_id,
            "schema": OCCURRENCE_SCHEMA,
            "teaching_episode_id": self.teaching_episode_id,
            "teaching_episode_receipt_sha256": (
                self.teaching_episode_receipt_sha256
            ),
            "thing_id": self.thing_id,
        }

    def record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
            "occurrence_id": self.occurrence_id,
        }


class GroundedArticulatoryResolutionState(str, Enum):
    UNRESOLVED = "unresolved"
    AMBIGUOUS = "ambiguous"
    PREPARED = "prepared"


@dataclass(frozen=True, slots=True)
class GroundedArticulatoryVocalTurnDecision:
    state: GroundedArticulatoryResolutionState
    reason: str
    thing_id: str
    form_sha256: str
    challenge_grounding_receipt_sha256: str
    challenge_context_event_receipt_sha256: str
    grounded_program_ids: tuple[str, ...]
    selected_program_id: str | None
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "challenge_context_event_receipt_sha256": (
                self.challenge_context_event_receipt_sha256
            ),
            "challenge_grounding_receipt_sha256": (
                self.challenge_grounding_receipt_sha256
            ),
            "form_sha256": self.form_sha256,
            "grounded_program_ids": list(self.grounded_program_ids),
            "reason": self.reason,
            "schema": DECISION_SCHEMA,
            "selected_program_id": self.selected_program_id,
            "state": self.state.value,
            "thing_id": self.thing_id,
        }


@dataclass(slots=True)
class _Phase:
    value: str


@dataclass(frozen=True, slots=True)
class PreparedGroundedArticulatoryVocalTurn:
    decision: GroundedArticulatoryVocalTurnDecision
    prepared_self_acoustic: PreparedW1SelfAcousticMount = field(repr=False)
    _phase: _Phase = field(repr=False, compare=False)
    _owner: object = field(repr=False, compare=False)
    _authority: object = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class GroundedArticulatoryVocalTurnOutput:
    decision: GroundedArticulatoryVocalTurnDecision
    emission: ArticulatoryGeneratedEmission
    self_hearing: W1SelfAcousticMount
    full_dsf_tuple_count: int
    full_dsf_custody_sha256: str
    authority_hmac_sha256: str
    authority_receipt_sha256: str


@dataclass(frozen=True, slots=True)
class GroundedArticulatoryVocalTurnUndo:
    _acoustic_undo: W1ArticulatorySelfAcousticCommitUndo = field(repr=False)
    _epoch: int = field(repr=False)
    _owner: object = field(repr=False, compare=False)
    _authority: object = field(repr=False, compare=False)


class GroundedArticulatoryVocalTurnOwner:
    """Bounded exact THING-context articulatory association authority."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        profile: GroundedArticulatoryVocalTurnProfile,
        teaching_authority: LivedVocalTeachingEpisodeAuthority,
        grounding_authority: W1BinauralGroundingEvidenceAuthority,
        lived_context_owner: CausalThingLivedContextOwner,
        articulatory_owner: ArticulatorySelfVocalMotorOwner,
        world_authority: EmbodimentWorldAuthority,
        self_acoustic_authority: W1SelfAcousticPropagationAuthority,
    ) -> None:
        profile.verify()
        self._key = _key(authority_key)
        self._profile = profile
        self._teaching = teaching_authority
        self._grounding = grounding_authority
        self._context = lived_context_owner
        self._articulatory = articulatory_owner
        self._world = world_authority
        self._acoustic = self_acoustic_authority
        self._occurrences: tuple[
            GroundedArticulatoryLearnedOccurrence, ...
        ] = ()
        self._prepared: PreparedGroundedArticulatoryVocalTurn | None = None
        self._owner = object()
        self._next_epoch = 1
        self._latest_undo_epoch: int | None = None
        self._lock = threading.RLock()

    @property
    def occurrences(
        self,
    ) -> tuple[GroundedArticulatoryLearnedOccurrence, ...]:
        with self._lock:
            return self._occurrences

    def _owned_episode(
        self, value: GroundedArticulatoryLearnedOccurrence
    ) -> LivedVocalTeachingEpisode:
        matches = tuple(
            episode
            for episode in self._teaching.episodes
            if episode.episode_id == value.teaching_episode_id
            and episode.authority_receipt_sha256
            == value.teaching_episode_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "grounded articulatory teaching reference is not owned"
            )
        self._teaching.verify(matches[0])
        return matches[0]

    def _owned_event(
        self, value: GroundedArticulatoryLearnedOccurrence
    ) -> CausalThingLivedContextEvent:
        matches = tuple(
            event
            for episode in self._context.episodes
            for event in episode.events
            if event.authority_receipt_sha256
            == value.lived_context_event_receipt_sha256
        )
        if len(matches) != 1:
            raise ValueError(
                "grounded articulatory context reference is not owned"
            )
        self._context.verify_owned_event(matches[0])
        return matches[0]

    def _verify_references(
        self, value: GroundedArticulatoryLearnedOccurrence
    ) -> None:
        episode = self._owned_episode(value)
        event = self._owned_event(value)
        programs = tuple(
            program
            for program in self._articulatory.programs
            if program.program_id == value.program_id
        )
        if len(programs) != 1:
            raise ValueError(
                "grounded articulatory program reference is not owned"
            )
        programs[0].verify()
        witness = self._teaching.witness(episode)
        external = witness.get("external_multisensory")
        auditory = witness.get("auditory_form_evidence")
        self_response = witness.get("self_vocal_response")
        acoustic = (
            self_response.get("acoustic_outcome")
            if isinstance(self_response, Mapping)
            else None
        )
        if (
            not isinstance(external, Mapping)
            or not isinstance(auditory, Mapping)
            or not isinstance(acoustic, Mapping)
            or external.get("source_occurrence_id")
            != value.external_source_occurrence_id
            or external.get("settlement_receipt_sha256")
            != value.external_settlement_receipt_sha256
            or auditory.get("authority_receipt_sha256")
            != value.external_grounding_receipt_sha256
            or acoustic.get("motor_id") != value.program_id
            or event.source_occurrence_id
            != value.external_source_occurrence_id
            or event.settlement_receipt_sha256
            != value.external_settlement_receipt_sha256
            or event.thing_route_state != "unique"
            or event.thing_ids != (value.thing_id,)
        ):
            raise ValueError(
                "grounded articulatory authority references diverged"
            )

    def _verify_learned(
        self,
        value: GroundedArticulatoryLearnedOccurrence,
        *,
        verify_references: bool = True,
    ) -> None:
        for digest, label in (
            (value.occurrence_id, "occurrence"),
            (value.form_sha256, "form"),
            (value.thing_id, "THING"),
            (value.program_id, "program"),
            (value.teaching_episode_id, "teaching episode"),
            (
                value.teaching_episode_receipt_sha256,
                "teaching episode receipt",
            ),
            (
                value.external_source_occurrence_id,
                "external occurrence",
            ),
            (
                value.external_settlement_receipt_sha256,
                "external settlement",
            ),
            (
                value.external_grounding_receipt_sha256,
                "external grounding",
            ),
            (
                value.lived_context_event_receipt_sha256,
                "lived context",
            ),
            (value.authority_hmac_sha256, "occurrence HMAC"),
            (value.authority_receipt_sha256, "occurrence authority"),
        ):
            _sha(digest, label)
        _validate_form(
            value.form_json, self._profile.max_occurrence_bytes
        )
        if hashlib.sha256(
            value.form_json.encode("ascii")
        ).hexdigest() != value.form_sha256:
            raise ValueError(
                "grounded articulatory form commitment changed"
            )
        signature = hmac.new(
            self._key,
            _OCCURRENCE_DOMAIN + _canonical(value.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            value.occurrence_id
            != _digest({
                "external_grounding_receipt_sha256": (
                    value.external_grounding_receipt_sha256
                ),
                "lived_context_event_receipt_sha256": (
                    value.lived_context_event_receipt_sha256
                ),
                "teaching_episode_receipt_sha256": (
                    value.teaching_episode_receipt_sha256
                ),
            })
            or not hmac.compare_digest(
                signature, value.authority_hmac_sha256
            )
            or value.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": signature,
                "payload": value.payload(),
            })
            or len(_canonical(value.record()))
            > self._profile.max_occurrence_bytes
        ):
            raise ValueError(
                "grounded articulatory occurrence authority changed"
            )
        if verify_references:
            self._verify_references(value)

    def _compose(
        self,
        source: GroundedArticulatoryTeachingOccurrence,
    ) -> GroundedArticulatoryLearnedOccurrence:
        if not isinstance(
            source, GroundedArticulatoryTeachingOccurrence
        ):
            raise TypeError(
                "grounded articulatory teaching occurrence is not typed"
            )
        self._teaching.verify(source.teaching_episode)
        self._grounding.verify(source.external_form)
        self._context.verify_owned_event(source.lived_context_event)
        source.articulatory_program.verify()
        if source.articulatory_program not in self._articulatory.programs:
            raise ValueError(
                "grounded articulatory program is not currently owned"
            )
        witness = self._teaching.witness(source.teaching_episode)
        external = witness.get("external_multisensory")
        auditory = witness.get("auditory_form_evidence")
        self_response = witness.get("self_vocal_response")
        event = source.lived_context_event
        acoustic = (
            self_response.get("acoustic_outcome")
            if isinstance(self_response, Mapping)
            else None
        )
        if (
            not isinstance(external, Mapping)
            or not isinstance(auditory, Mapping)
            or not isinstance(acoustic, Mapping)
            or auditory != _evidence_record(source.external_form)
            or external.get("source_occurrence_id")
            != event.source_occurrence_id
            or external.get("settlement_receipt_sha256")
            != event.settlement_receipt_sha256
            or source.external_form.causal_settlement_receipt_sha256
            != event.settlement_receipt_sha256
            or event.thing_route_state != "unique"
            or len(event.thing_ids) != 1
            or acoustic.get("motor_id")
            != source.articulatory_program.program_id
        ):
            raise ValueError(
                "grounded articulatory teaching authorities diverged"
            )
        form_json = _structural_form(
            source.external_form,
            self._profile.max_occurrence_bytes,
        )
        values = {
            "form_sha256": hashlib.sha256(
                form_json.encode("ascii")
            ).hexdigest(),
            "form_json": form_json,
            "thing_id": event.thing_ids[0],
            "program_id": source.articulatory_program.program_id,
            "teaching_episode_id": source.teaching_episode.episode_id,
            "teaching_episode_receipt_sha256": (
                source.teaching_episode.authority_receipt_sha256
            ),
            "external_source_occurrence_id": (
                event.source_occurrence_id
            ),
            "external_settlement_receipt_sha256": (
                event.settlement_receipt_sha256
            ),
            "external_grounding_receipt_sha256": (
                source.external_form.authority_receipt_sha256
            ),
            "lived_context_event_receipt_sha256": (
                event.authority_receipt_sha256
            ),
        }
        occurrence_id = _digest({
            "external_grounding_receipt_sha256": (
                values["external_grounding_receipt_sha256"]
            ),
            "lived_context_event_receipt_sha256": (
                values["lived_context_event_receipt_sha256"]
            ),
            "teaching_episode_receipt_sha256": (
                values["teaching_episode_receipt_sha256"]
            ),
        })
        provisional = GroundedArticulatoryLearnedOccurrence(
            occurrence_id=occurrence_id,
            **values,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _OCCURRENCE_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        result = GroundedArticulatoryLearnedOccurrence(
            occurrence_id=occurrence_id,
            **values,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )
        self._verify_learned(result)
        return result

    def learn(
        self,
        occurrences: tuple[
            GroundedArticulatoryTeachingOccurrence, ...
        ],
    ) -> tuple[GroundedArticulatoryLearnedOccurrence, ...]:
        if not isinstance(occurrences, tuple) or len(occurrences) < 2:
            raise ValueError(
                "grounded articulatory learning requires two occurrences"
            )
        composed = tuple(self._compose(value) for value in occurrences)
        for field_name in (
            "teaching_episode_id",
            "external_source_occurrence_id",
            "external_settlement_receipt_sha256",
            "external_grounding_receipt_sha256",
        ):
            if len({
                getattr(value, field_name) for value in composed
            }) != len(composed):
                raise ValueError(
                    "grounded articulatory teachings are not independent"
                )
        if len({
            (value.form_sha256, value.thing_id, value.program_id)
            for value in composed
        }) != 1:
            raise ValueError(
                "grounded articulatory teachings do not share one relation"
            )
        with self._lock:
            by_id = {
                value.occurrence_id: value
                for value in self._occurrences
            }
            for value in composed:
                existing = by_id.get(value.occurrence_id)
                if existing is not None and existing != value:
                    raise ValueError(
                        "grounded articulatory occurrence conflicted"
                    )
                by_id[value.occurrence_id] = value
            staged = tuple(by_id[key] for key in sorted(by_id))
            self._encoded(staged)
            self._occurrences = staged
        return composed

    def _decision(
        self,
        *,
        state: GroundedArticulatoryResolutionState,
        reason: str,
        thing_id: str,
        form_sha256: str,
        evidence: W1BinauralGroundingEvidence,
        event: CausalThingLivedContextEvent,
        programs: tuple[str, ...],
        selected: str | None,
    ) -> GroundedArticulatoryVocalTurnDecision:
        provisional = GroundedArticulatoryVocalTurnDecision(
            state=state,
            reason=_ascii(reason, "decision reason"),
            thing_id=_sha(thing_id, "decision THING"),
            form_sha256=_sha(form_sha256, "decision form"),
            challenge_grounding_receipt_sha256=_sha(
                evidence.authority_receipt_sha256,
                "challenge grounding",
            ),
            challenge_context_event_receipt_sha256=_sha(
                event.authority_receipt_sha256,
                "challenge context",
            ),
            grounded_program_ids=tuple(
                _sha(value, "grounded program") for value in programs
            ),
            selected_program_id=(
                None
                if selected is None
                else _sha(selected, "selected program")
            ),
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._key,
            _DECISION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return GroundedArticulatoryVocalTurnDecision(
            state=provisional.state,
            reason=provisional.reason,
            thing_id=provisional.thing_id,
            form_sha256=provisional.form_sha256,
            challenge_grounding_receipt_sha256=(
                provisional.challenge_grounding_receipt_sha256
            ),
            challenge_context_event_receipt_sha256=(
                provisional.challenge_context_event_receipt_sha256
            ),
            grounded_program_ids=provisional.grounded_program_ids,
            selected_program_id=provisional.selected_program_id,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def prepare_turn(
        self,
        *,
        external_form: W1BinauralGroundingEvidence,
        lived_context_event: CausalThingLivedContextEvent,
    ) -> (
        GroundedArticulatoryVocalTurnDecision
        | PreparedGroundedArticulatoryVocalTurn
    ):
        self._grounding.verify(external_form)
        self._context.verify_owned_event(lived_context_event)
        if (
            lived_context_event.thing_route_state != "unique"
            or len(lived_context_event.thing_ids) != 1
            or external_form.causal_settlement_receipt_sha256
            != lived_context_event.settlement_receipt_sha256
        ):
            raise ValueError(
                "grounded articulatory challenge crossed lived context"
            )
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "grounded articulatory turn is already prepared"
                )
            if (
                external_form.authority_receipt_sha256
                in {
                    value.external_grounding_receipt_sha256
                    for value in self._occurrences
                }
                or lived_context_event.authority_receipt_sha256
                in {
                    value.lived_context_event_receipt_sha256
                    for value in self._occurrences
                }
            ):
                raise ValueError(
                    "grounded articulatory challenge is not held out"
                )
            form_json = _structural_form(
                external_form,
                self._profile.max_occurrence_bytes,
            )
            form_sha = hashlib.sha256(
                form_json.encode("ascii")
            ).hexdigest()
            thing_id = lived_context_event.thing_ids[0]
            current_programs = {
                value.program_id for value in self._articulatory.programs
            }
            grouped: dict[str, set[str]] = {}
            for value in self._occurrences:
                if (
                    value.form_sha256 == form_sha
                    and value.thing_id == thing_id
                    and value.program_id in current_programs
                ):
                    grouped.setdefault(
                        value.program_id, set()
                    ).add(value.occurrence_id)
            programs = tuple(sorted(
                program_id
                for program_id, sources in grouped.items()
                if len(sources) >= 2
            ))
            if not programs:
                return self._decision(
                    state=GroundedArticulatoryResolutionState.UNRESOLVED,
                    reason="no_repeated_grounded_program",
                    thing_id=thing_id,
                    form_sha256=form_sha,
                    evidence=external_form,
                    event=lived_context_event,
                    programs=(),
                    selected=None,
                )
            if len(programs) != 1:
                return self._decision(
                    state=GroundedArticulatoryResolutionState.AMBIGUOUS,
                    reason="multiple_grounded_current_programs",
                    thing_id=thing_id,
                    form_sha256=form_sha,
                    evidence=external_form,
                    event=lived_context_event,
                    programs=programs,
                    selected=None,
                )
            decision = self._decision(
                state=GroundedArticulatoryResolutionState.PREPARED,
                reason="one_grounded_current_program",
                thing_id=thing_id,
                form_sha256=form_sha,
                evidence=external_form,
                event=lived_context_event,
                programs=programs,
                selected=programs[0],
            )
            before = self._world.observation_snapshot()
            synthesis = self._articulatory.synthesize(
                program_id=programs[0],
                source_time_start=Fraction(
                    before.revision * MAX_VOCAL_SAMPLE_COUNT,
                    VOCAL_SAMPLE_RATE_HZ,
                ),
            )
            prepared_emission = (
                self._articulatory.prepare_generated_emission(
                    synthesis=synthesis,
                    world_authority=self._world,
                    causal_intent_receipt_sha256=(
                        decision.authority_receipt_sha256
                    ),
                )
            )
            prepared_acoustic = self._acoustic.prepare_articulatory(
                prepared_emission,
                articulatory_owner=self._articulatory,
            )
            prepared = PreparedGroundedArticulatoryVocalTurn(
                decision=decision,
                prepared_self_acoustic=prepared_acoustic,
                _phase=_Phase("prepared"),
                _owner=self._owner,
                _authority=_PREPARED_AUTHORITY,
            )
            self._prepared = prepared
            return prepared

    @staticmethod
    def _full_field(
        mount: W1SelfAcousticMount,
    ) -> tuple[int, str]:
        records = []
        for sense in mount.causal_settlement.interpretations:
            if sense.state != "observed":
                continue
            for substream in sense.substreams:
                for field_tuple in substream.field_tuples:
                    if tuple(
                        name for name, _value in field_tuple.fields
                    ) != DSF_FIELD_ORDER:
                        raise ValueError(
                            "grounded articulatory output flattened DSF"
                        )
                    records.append({
                        "receipt": field_tuple.authority_receipt_sha256,
                        "sense": sense.sense,
                    })
        if not records:
            raise ValueError(
                "grounded articulatory output lost full field"
            )
        return len(records), _digest({
            "field_tuples": records,
            "schema": "guala.grounded_articulatory.full_dsf.v1",
        })

    def commit_prepared(
        self,
        prepared: PreparedGroundedArticulatoryVocalTurn,
    ) -> tuple[
        GroundedArticulatoryVocalTurnOutput,
        GroundedArticulatoryVocalTurnUndo,
    ]:
        with self._lock:
            if (
                not isinstance(
                    prepared,
                    PreparedGroundedArticulatoryVocalTurn,
                )
                or prepared._authority is not _PREPARED_AUTHORITY
                or prepared._owner is not self._owner
                or self._prepared is not prepared
                or prepared._phase.value != "prepared"
            ):
                raise ValueError(
                    "grounded articulatory prepared turn changed"
                )
            acoustic_undo = None
            try:
                emission, mount, acoustic_undo = (
                    self._acoustic.commit_prepared_articulatory(
                        prepared.prepared_self_acoustic
                    )
                )
                count, custody_sha = self._full_field(mount)
                payload = {
                    "decision_receipt_sha256": (
                        prepared.decision.authority_receipt_sha256
                    ),
                    "full_dsf_custody_sha256": custody_sha,
                    "full_dsf_tuple_count": count,
                    "generated_emission_receipt_sha256": (
                        emission.emission_receipt
                        .authority_receipt_sha256
                    ),
                    "program_id": emission.synthesis.program.program_id,
                    "schema": OUTPUT_SCHEMA,
                    "self_hearing_mount_receipt_sha256": (
                        mount.receipt.authority_receipt_sha256
                    ),
                }
                signature = hmac.new(
                    self._key,
                    _OUTPUT_DOMAIN + _canonical(payload),
                    hashlib.sha256,
                ).hexdigest()
                output = GroundedArticulatoryVocalTurnOutput(
                    decision=prepared.decision,
                    emission=emission,
                    self_hearing=mount,
                    full_dsf_tuple_count=count,
                    full_dsf_custody_sha256=custody_sha,
                    authority_hmac_sha256=signature,
                    authority_receipt_sha256=_digest({
                        "authority_hmac_sha256": signature,
                        "payload": payload,
                    }),
                )
            except BaseException:
                if acoustic_undo is not None:
                    self._acoustic.rollback_committed_articulatory(
                        acoustic_undo
                    )
                self._prepared = None
                prepared._phase.value = "failed"
                raise
            epoch = self._next_epoch
            self._next_epoch += 1
            self._latest_undo_epoch = epoch
            self._prepared = None
            prepared._phase.value = "committed"
            return output, GroundedArticulatoryVocalTurnUndo(
                _acoustic_undo=acoustic_undo,
                _epoch=epoch,
                _owner=self._owner,
                _authority=_UNDO_AUTHORITY,
            )

    def discard_prepared(
        self,
        prepared: PreparedGroundedArticulatoryVocalTurn,
    ) -> None:
        with self._lock:
            if (
                self._prepared is not prepared
                or prepared._owner is not self._owner
                or prepared._authority is not _PREPARED_AUTHORITY
                or prepared._phase.value != "prepared"
            ):
                raise ValueError(
                    "grounded articulatory prepared turn changed"
                )
            self._acoustic.discard_prepared_articulatory(
                prepared.prepared_self_acoustic
            )
            self._prepared = None
            prepared._phase.value = "discarded"

    def rollback_committed(
        self,
        undo: GroundedArticulatoryVocalTurnUndo,
    ) -> None:
        with self._lock:
            if (
                not isinstance(
                    undo, GroundedArticulatoryVocalTurnUndo
                )
                or undo._authority is not _UNDO_AUTHORITY
                or undo._owner is not self._owner
                or self._latest_undo_epoch != undo._epoch
                or self._prepared is not None
            ):
                raise ValueError(
                    "grounded articulatory undo is stale"
                )
            self._acoustic.rollback_committed_articulatory(
                undo._acoustic_undo
            )
            self._latest_undo_epoch = None

    def _body(
        self,
        occurrences: tuple[
            GroundedArticulatoryLearnedOccurrence, ...
        ],
    ) -> dict[str, object]:
        for value in occurrences:
            self._verify_learned(value)
        return {
            "occurrences": [value.record() for value in occurrences],
            "profile": self._profile.record(),
            "schema": STATE_SCHEMA,
        }

    def _encoded(
        self,
        occurrences: tuple[
            GroundedArticulatoryLearnedOccurrence, ...
        ],
    ) -> bytes:
        if len(occurrences) > self._profile.max_occurrences:
            raise RuntimeError(
                "grounded articulatory occurrence capacity exhausted"
            )
        body = self._body(occurrences)
        encoded = _canonical({
            "body": body,
            "schema": ENVELOPE_SCHEMA,
            "state_hmac_sha256": hmac.new(
                self._key,
                _STATE_DOMAIN + _canonical(body),
                hashlib.sha256,
            ).hexdigest(),
        })
        if len(encoded) > self._profile.max_state_bytes:
            raise RuntimeError(
                "grounded articulatory state capacity exhausted"
            )
        return encoded

    def snapshot_encoded(self) -> bytes:
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "grounded articulatory turn is prepared"
                )
            return self._encoded(self._occurrences)

    def restore_encoded(self, encoded: bytes) -> None:
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > self._profile.max_state_bytes
            or not encoded.isascii()
        ):
            raise ValueError(
                "grounded articulatory restore extent changed"
            )
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "grounded articulatory state is unreadable"
            ) from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"body", "schema", "state_hmac_sha256"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or _canonical(envelope) != encoded
        ):
            raise ValueError(
                "grounded articulatory state envelope changed"
            )
        body = envelope.get("body")
        if (
            not isinstance(body, Mapping)
            or set(body) != {"occurrences", "profile", "schema"}
            or body.get("schema") != STATE_SCHEMA
            or body.get("profile") != self._profile.record()
            or not isinstance(body.get("occurrences"), list)
        ):
            raise ValueError(
                "grounded articulatory state body changed"
            )
        expected = hmac.new(
            self._key,
            _STATE_DOMAIN + _canonical(body),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected, envelope.get("state_hmac_sha256")
        ):
            raise ValueError(
                "grounded articulatory state HMAC changed"
            )
        required = {
            "authority_hmac_sha256",
            "authority_receipt_sha256",
            "external_grounding_receipt_sha256",
            "external_settlement_receipt_sha256",
            "external_source_occurrence_id",
            "form_json",
            "form_sha256",
            "lived_context_event_receipt_sha256",
            "occurrence_id",
            "program_id",
            "schema",
            "teaching_episode_id",
            "teaching_episode_receipt_sha256",
            "thing_id",
        }
        restored = []
        for record in body["occurrences"]:
            if (
                not isinstance(record, Mapping)
                or set(record) != required
                or record.get("schema") != OCCURRENCE_SCHEMA
            ):
                raise ValueError(
                    "grounded articulatory occurrence record changed"
                )
            value = GroundedArticulatoryLearnedOccurrence(
                occurrence_id=record["occurrence_id"],
                form_sha256=record["form_sha256"],
                form_json=record["form_json"],
                thing_id=record["thing_id"],
                program_id=record["program_id"],
                teaching_episode_id=record["teaching_episode_id"],
                teaching_episode_receipt_sha256=(
                    record["teaching_episode_receipt_sha256"]
                ),
                external_source_occurrence_id=(
                    record["external_source_occurrence_id"]
                ),
                external_settlement_receipt_sha256=(
                    record["external_settlement_receipt_sha256"]
                ),
                external_grounding_receipt_sha256=(
                    record["external_grounding_receipt_sha256"]
                ),
                lived_context_event_receipt_sha256=(
                    record["lived_context_event_receipt_sha256"]
                ),
                authority_hmac_sha256=(
                    record["authority_hmac_sha256"]
                ),
                authority_receipt_sha256=(
                    record["authority_receipt_sha256"]
                ),
            )
            self._verify_learned(value)
            restored.append(value)
        if (
            len(restored) > self._profile.max_occurrences
            or len({value.occurrence_id for value in restored})
            != len(restored)
        ):
            raise ValueError(
                "grounded articulatory restored capacity changed"
            )
        staged = tuple(sorted(
            restored, key=lambda value: value.occurrence_id
        ))
        self._encoded(staged)
        with self._lock:
            if self._prepared is not None:
                raise RuntimeError(
                    "grounded articulatory turn is prepared"
                )
            self._occurrences = staged

    def status(self) -> dict[str, object]:
        with self._lock:
            encoded = self._encoded(self._occurrences)
            return {
                "full_field_authority": True,
                "max_occurrences": self._profile.max_occurrences,
                "max_state_bytes": self._profile.max_state_bytes,
                "occurrence_count": len(self._occurrences),
                "prepared": self._prepared is not None,
                "retained_pcm_bytes": 0,
                "schema": STATE_SCHEMA,
                "state_bytes": len(encoded),
            }


__all__ = (
    "GroundedArticulatoryLearnedOccurrence",
    "GroundedArticulatoryResolutionState",
    "GroundedArticulatoryTeachingOccurrence",
    "GroundedArticulatoryVocalTurnDecision",
    "GroundedArticulatoryVocalTurnOutput",
    "GroundedArticulatoryVocalTurnOwner",
    "GroundedArticulatoryVocalTurnProfile",
    "GroundedArticulatoryVocalTurnUndo",
    "PreparedGroundedArticulatoryVocalTurn",
)
