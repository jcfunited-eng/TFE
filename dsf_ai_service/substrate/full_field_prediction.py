"""Bounded deterministic prediction over authenticated full-field episodes.

This authority predicts an explicit next six-sense field, optional exact
auditory-token sequence, and optional W1 geometry.  Nothing is learned from
mere temporal adjacency: callers must open one context and explicitly advance
it.  Passive and exact action-conditioned transitions occupy disjoint
namespaces.

Every retained episode carries the complete causal settlement witness.  Field
comparison is path-wise and exact.  Missing observation is reported as
``unknown_unobserved``; it is never filled by a route, source label, text
recognizer, or inferred identity.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Mapping, Sequence

from dsf_ai_service.glew_runtime.model import receipt_sha256
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import SENSE_ORDER
from dsf_ai_service.substrate.auditory_batch_causal_intake import (
    AuditoryBatchCausalIntakeAuthority,
    AuditoryBatchCausalIntakeReceipt,
)
from dsf_ai_service.substrate.auditory_token_sequence import (
    AuditoryTokenSequenceAuthority,
    AuditoryTokenSequenceReceipt,
)
from dsf_ai_service.substrate.auditory_pcm_stream import (
    AuditoryPCMContinuityReceipt,
)
from dsf_ai_service.substrate.auditory_stream_settlement import (
    AuditoryStreamSettlementReceipt,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AUDITORY_CHANNELS,
    COCHLEAR_ORDER,
    OBSERVATION_HOP_SAMPLES,
)
from dsf_ai_service.substrate.causal_action_cycle import (
    DEFAULT_MAX_COMMAND_BYTES,
    DEFAULT_MAX_SPEECH_SCALARS,
    ActionIntent,
    CausalActionCycle,
)
from dsf_ai_service.substrate.causal_language_construction import (
    CausalLanguageConstructionAuthority,
    CausalLanguageEpisode,
)
from dsf_ai_service.substrate.embodiment_sensory_outcome import (
    EmbodimentSensoryOutcomeAuthority,
    OutcomeObservationReceipt,
)
from dsf_ai_service.substrate.embodiment_world import (
    ActionExecutionReceipt,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.w1_audiovisual_physical_evidence import (
    W1AudiovisualPhysicalEvidenceAuthority,
    W1PhysicalEvidenceReceipt,
)
from dsf_ai_service.substrate.w1_anonymous_audiovisual_continuity import (
    W1AnonymousAudiovisualContinuityExperience,
    W1AnonymousAudiovisualContinuityOwner,
)
from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
    AuditoryGammatoneContinuationReceipt,
)


EPISODE_SCHEMA = "guala.full_field_prediction.episode.v1"
TRANSITION_SCHEMA = "guala.full_field_prediction.transition.v1"
RELATION_SCHEMA = "guala.full_field_prediction.relation.v1"
ATTEMPT_SCHEMA = "guala.full_field_prediction.attempt.v1"
RESOLUTION_SCHEMA = "guala.full_field_prediction.resolution.v1"
STATE_SCHEMA = "guala.full_field_prediction.state.v1"
ENVELOPE_SCHEMA = "guala.full_field_prediction.state.hmac.v1"

EPISODE_DOMAIN = b"guala-full-field-prediction-episode-v1\0"
TRANSITION_DOMAIN = b"guala-full-field-prediction-transition-v1\0"
RELATION_DOMAIN = b"guala-full-field-prediction-relation-v1\0"
ATTEMPT_DOMAIN = b"guala-full-field-prediction-attempt-v1\0"
RESOLUTION_DOMAIN = b"guala-full-field-prediction-resolution-v1\0"
STATE_DOMAIN = b"guala-full-field-prediction-state-v1\0"

DEFAULT_PASSIVE_RELATION_CAPACITY = 32
DEFAULT_ACTION_RELATION_CAPACITY = 32
DEFAULT_EPISODE_CAPACITY = 132
DEFAULT_MAX_WITNESS_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_ENCODED_STATE_BYTES = 32 * 1024 * 1024

_OBSERVED = "observed"
_UNAVAILABLE_STATES = {
    "sensor_unavailable",
    "not_observed",
    "unavailable",
    "absent",
}


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


def _key(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError("full-field prediction key must be bytes or text")
    if not 32 <= len(result) <= 4096:
        raise ValueError("full-field prediction key has an invalid boundary")
    return result


def _positive_capacity(value: object, name: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise ValueError(f"{name} is outside its exact boundary")
    return value


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _sign(key: bytes, domain: bytes, payload: Mapping[str, object]) -> str:
    return hmac.new(key, domain + _canonical(payload), hashlib.sha256).hexdigest()


def _settlement_witness(
    settlement: CausalExperienceSettlement, *, max_bytes: int
) -> dict[str, object]:
    if not isinstance(settlement, CausalExperienceSettlement):
        raise TypeError("full-field prediction requires a causal settlement")
    settlement.verify()
    payload = settlement.receipt_registry.resolve(
        settlement.authority_receipt_sha256,
        "full-field prediction settlement",
    )
    if not payload or len(payload) > max_bytes:
        raise RuntimeError("full-field prediction witness exceeds its byte boundary")
    if receipt_sha256(payload) != settlement.authority_receipt_sha256:
        raise ValueError("full-field prediction settlement receipt changed")
    try:
        witness = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("full-field prediction settlement is invalid") from error
    if not isinstance(witness, dict) or _canonical(witness) != payload:
        raise ValueError("full-field prediction settlement is not canonical")
    _full_field_structure(witness)
    return witness


def _full_field_structure(witness: Mapping[str, object]) -> dict[str, object]:
    """Return explicit physical structure without bookkeeping identities."""

    raw = witness.get("interpretations")
    expected_senses = tuple(item.value for item in SENSE_ORDER)
    if (
        not isinstance(raw, list)
        or len(raw) != len(expected_senses)
        or any(not isinstance(item, Mapping) for item in raw)
        or tuple(item.get("sense") for item in raw) != expected_senses
    ):
        raise ValueError("prediction witness lost canonical six-sense structure")
    senses = []
    required_fields = {
        "D_k",
        "M_k",
        "R_rev_k",
        "U_star_k",
        "C_k",
        "P_k",
        "B_k",
    }
    for sense in raw:
        substreams = sense.get("substreams")
        if not isinstance(substreams, list):
            raise ValueError("prediction witness substreams changed")
        physical = []
        for substream in substreams:
            if not isinstance(substream, Mapping):
                raise ValueError("prediction witness substream changed")
            tuples = substream.get("field_tuples")
            if not isinstance(tuples, list):
                raise ValueError("prediction witness field tuples changed")
            exact_tuples = []
            for field_tuple in tuples:
                if not isinstance(field_tuple, Mapping):
                    raise ValueError("prediction witness DSF tuple changed")
                fields = field_tuple.get("fields")
                if (
                    not isinstance(fields, list)
                    or {value[0] for value in fields if isinstance(value, list)}
                    != required_fields
                ):
                    raise ValueError("prediction witness lost explicit DSF fields")
                exact_tuples.append({
                    "fields": fields,
                    "tuple_index": field_tuple.get("tuple_index"),
                })
            physical.append({
                "coordinates": substream.get("coordinates"),
                "field_tuples": exact_tuples,
                "physical_quantity": substream.get("physical_quantity"),
                "physical_unit": substream.get("physical_unit"),
                "sensor_id": substream.get("sensor_id"),
                "substream_id": substream.get("substream_id"),
                "topology_index": substream.get("topology_index"),
            })
        senses.append({
            "sense": sense.get("sense"),
            "state": sense.get("state"),
            "substreams": physical,
        })
    return {"interpretations": senses}


def _auditory_structure(record: Mapping[str, object]) -> dict[str, object]:
    occurrences = record.get("occurrences")
    if not isinstance(occurrences, list):
        raise ValueError("auditory prediction sequence changed")
    return {
        "occurrences": [
            {
                "classification_state": item.get("classification_state"),
                "ordinal": item.get("ordinal"),
                "structural_fingerprint": item.get("structural_fingerprint"),
                "token_candidates": item.get("token_candidates"),
            }
            for item in occurrences
            if isinstance(item, Mapping)
        ]
    }


def _w1_geometry(observation_record: Mapping[str, object]) -> dict[str, object]:
    expected = {
        "bodies",
        "objects",
        "portals",
        "regions",
        "room_bounds",
        "room_id",
        "self_body_id",
    }
    if any(key not in observation_record for key in expected):
        raise ValueError("W1 prediction attachment lost exact geometry")
    return {key: observation_record[key] for key in sorted(expected)}


def _episode_structure(
    witness: Mapping[str, object],
    auditory: Mapping[str, object] | None,
    w1: Mapping[str, object] | None,
) -> dict[str, object]:
    return {
        "auditory": (
            _auditory_structure(auditory["sequence"])
            if auditory is not None and auditory.get("sequence") is not None
            else None
        ),
        "full_field": _full_field_structure(witness),
        "schema": "guala.full_field_prediction.episode_structure.v1",
        "w1_geometry": (
            _w1_geometry(w1["observation"]) if w1 is not None else None
        ),
    }


@dataclass(frozen=True, slots=True)
class PredictiveEpisodeReceipt:
    episode_id: str
    structure_id: str
    settlement_receipt_sha256: str
    settlement_witness: Mapping[str, object]
    auditory_attachment: Mapping[str, object] | None
    w1_attachment: Mapping[str, object] | None
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "auditory_attachment": (
                dict(self.auditory_attachment)
                if self.auditory_attachment is not None
                else None
            ),
            "schema": EPISODE_SCHEMA,
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "settlement_witness": dict(self.settlement_witness),
            "structure_id": self.structure_id,
            "w1_attachment": (
                dict(self.w1_attachment)
                if self.w1_attachment is not None
                else None
            ),
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "episode_id": self.episode_id,
        }


@dataclass(frozen=True, slots=True)
class PredictionTransitionEvidence:
    transition_id: str
    mode: str
    context_episode_id: str
    target_episode_id: str
    action_intent_record: Mapping[str, object] | None
    closure_record: Mapping[str, object] | None
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_intent_record": (
                dict(self.action_intent_record)
                if self.action_intent_record is not None
                else None
            ),
            "closure_record": (
                dict(self.closure_record)
                if self.closure_record is not None
                else None
            ),
            "context_episode_id": self.context_episode_id,
            "mode": self.mode,
            "schema": TRANSITION_SCHEMA,
            "target_episode_id": self.target_episode_id,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "transition_id": self.transition_id,
        }


@dataclass(frozen=True, slots=True)
class PredictionRelation:
    relation_id: str
    mode: str
    context_structure_id: str
    target_structure_id: str
    action_receipt_sha256: str | None
    latest_evidence: PredictionTransitionEvidence
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_receipt_sha256": self.action_receipt_sha256,
            "context_structure_id": self.context_structure_id,
            "latest_evidence": self.latest_evidence.as_record(),
            "mode": self.mode,
            "relation_id": self.relation_id,
            "schema": RELATION_SCHEMA,
            "target_structure_id": self.target_structure_id,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
        }


@dataclass(frozen=True, slots=True)
class FullFieldPredictionAttempt:
    attempt_id: str
    mode: str
    context_episode_id: str
    context_structure_id: str
    action_intent_record: Mapping[str, object] | None
    status: str
    candidates: tuple[Mapping[str, object], ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "action_intent_record": (
                dict(self.action_intent_record)
                if self.action_intent_record is not None
                else None
            ),
            "candidates": [dict(value) for value in self.candidates],
            "context_episode_id": self.context_episode_id,
            "context_structure_id": self.context_structure_id,
            "mode": self.mode,
            "schema": ATTEMPT_SCHEMA,
            "status": self.status,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "attempt_id": self.attempt_id,
            "authority_hmac_sha256": self.authority_hmac_sha256,
        }


@dataclass(frozen=True, slots=True)
class ExactFieldOutcome:
    path: str
    state: str
    expected: object
    actual: object

    def as_record(self) -> dict[str, object]:
        return {
            "actual": self.actual,
            "expected": self.expected,
            "path": self.path,
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class FullFieldPredictionResolution:
    resolution_id: str
    attempt_record: Mapping[str, object]
    actual_episode_record: Mapping[str, object]
    verification: str
    matching_candidate_episode_ids: tuple[str, ...]
    candidate_outcomes: tuple[Mapping[str, object], ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "actual_episode_record": dict(self.actual_episode_record),
            "attempt_record": dict(self.attempt_record),
            "candidate_outcomes": [dict(value) for value in self.candidate_outcomes],
            "matching_candidate_episode_ids": list(
                self.matching_candidate_episode_ids
            ),
            "schema": RESOLUTION_SCHEMA,
            "verification": self.verification,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "resolution_id": self.resolution_id,
        }


@dataclass(frozen=True, slots=True)
class FullFieldPredictionStep:
    resolution: FullFieldPredictionResolution
    transition: PredictionTransitionEvidence
    relation: PredictionRelation
    next_prediction: FullFieldPredictionAttempt


def _flatten(value: object, path: str) -> dict[str, object]:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key in sorted(value):
            result.update(_flatten(value[key], f"{path}/{key}"))
        return result
    if isinstance(value, list):
        result = {}
        for index, item in enumerate(value):
            result.update(_flatten(item, f"{path}/{index}"))
        if not value:
            result[path] = []
        return result
    return {path: value}


def _sense_map(structure: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    full_field = structure.get("full_field")
    if not isinstance(full_field, Mapping):
        raise ValueError("prediction structure lost full field")
    senses = full_field.get("interpretations")
    if not isinstance(senses, list):
        raise ValueError("prediction structure lost senses")
    return {
        str(item["sense"]): item
        for item in senses
        if isinstance(item, Mapping) and "sense" in item
    }


def _compare_structures(
    expected: Mapping[str, object], actual: Mapping[str, object]
) -> tuple[ExactFieldOutcome, ...]:
    outcomes: list[ExactFieldOutcome] = []
    expected_senses = _sense_map(expected)
    actual_senses = _sense_map(actual)
    for sense in (item.value for item in SENSE_ORDER):
        left = expected_senses[sense]
        right = actual_senses[sense]
        left_state = left.get("state")
        right_state = right.get("state")
        if left_state == _OBSERVED and right_state in _UNAVAILABLE_STATES:
            outcomes.append(ExactFieldOutcome(
                f"/full_field/interpretations/{sense}",
                "unknown_unobserved",
                left,
                right,
            ))
            continue
        left_paths = _flatten(left, f"/full_field/interpretations/{sense}")
        right_paths = _flatten(right, f"/full_field/interpretations/{sense}")
        for path in sorted(set(left_paths) | set(right_paths)):
            before = left_paths.get(path)
            after = right_paths.get(path)
            outcomes.append(ExactFieldOutcome(
                path,
                "exact" if before == after else "mismatch",
                before,
                after,
            ))
    left_auditory = expected.get("auditory")
    right_auditory = actual.get("auditory")
    if left_auditory is not None and right_auditory is None:
        outcomes.append(ExactFieldOutcome(
            "/auditory", "unknown_unobserved", left_auditory, None
        ))
    elif isinstance(left_auditory, Mapping) and isinstance(
        right_auditory, Mapping
    ):
        left_occurrences = left_auditory.get("occurrences")
        right_occurrences = right_auditory.get("occurrences")
        if (
            not isinstance(left_occurrences, list)
            or not isinstance(right_occurrences, list)
            or len(left_occurrences) != len(right_occurrences)
        ):
            outcomes.append(ExactFieldOutcome(
                "/auditory/occurrences",
                "mismatch",
                left_occurrences,
                right_occurrences,
            ))
        else:
            for index, (left, right) in enumerate(
                zip(left_occurrences, right_occurrences, strict=True)
            ):
                path = f"/auditory/occurrences/{index}"
                if (
                    isinstance(left, Mapping)
                    and isinstance(right, Mapping)
                    and left.get("classification_state") == "unique"
                    and right.get("classification_state") == "unknown"
                ):
                    outcomes.append(ExactFieldOutcome(
                        path, "unknown_unobserved", left, right
                    ))
                    continue
                if (
                    isinstance(left, Mapping)
                    and isinstance(right, Mapping)
                    and left.get("classification_state") == "unique"
                    and right.get("classification_state") == "ambiguous"
                ):
                    outcomes.append(ExactFieldOutcome(
                        path, "ambiguous", left, right
                    ))
                    continue
                left_paths = _flatten(left, path)
                right_paths = _flatten(right, path)
                for item_path in sorted(set(left_paths) | set(right_paths)):
                    before = left_paths.get(item_path)
                    after = right_paths.get(item_path)
                    outcomes.append(ExactFieldOutcome(
                        item_path,
                        "exact" if before == after else "mismatch",
                        before,
                        after,
                    ))
    elif left_auditory != right_auditory:
        outcomes.append(ExactFieldOutcome(
            "/auditory", "mismatch", left_auditory, right_auditory
        ))

    for attachment in ("w1_geometry",):
        left = expected.get(attachment)
        right = actual.get(attachment)
        if left is not None and right is None:
            outcomes.append(ExactFieldOutcome(
                f"/{attachment}", "unknown_unobserved", left, None
            ))
            continue
        left_paths = _flatten(left, f"/{attachment}")
        right_paths = _flatten(right, f"/{attachment}")
        for path in sorted(set(left_paths) | set(right_paths)):
            before = left_paths.get(path)
            after = right_paths.get(path)
            outcomes.append(ExactFieldOutcome(
                path,
                "exact" if before == after else "mismatch",
                before,
                after,
            ))
    return tuple(outcomes)


def _overall(outcomes: Sequence[ExactFieldOutcome]) -> str:
    if any(value.state == "mismatch" for value in outcomes):
        return "mismatch"
    if any(value.state == "ambiguous" for value in outcomes):
        return "ambiguous"
    if any(value.state == "unknown_unobserved" for value in outcomes):
        return "unknown"
    return "exact"


class FullFieldPredictionAuthority:
    """Serial bounded owner of explicit full-field transition evidence."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        passive_relation_capacity: int = DEFAULT_PASSIVE_RELATION_CAPACITY,
        action_relation_capacity: int = DEFAULT_ACTION_RELATION_CAPACITY,
        episode_capacity: int = DEFAULT_EPISODE_CAPACITY,
        max_witness_bytes: int = DEFAULT_MAX_WITNESS_BYTES,
        max_encoded_state_bytes: int = DEFAULT_MAX_ENCODED_STATE_BYTES,
    ) -> None:
        self._key = hashlib.sha256(_key(authority_key)).digest()
        self._passive_capacity = _positive_capacity(
            passive_relation_capacity,
            "passive relation capacity",
            DEFAULT_PASSIVE_RELATION_CAPACITY,
        )
        self._action_capacity = _positive_capacity(
            action_relation_capacity,
            "action relation capacity",
            DEFAULT_ACTION_RELATION_CAPACITY,
        )
        self._episode_capacity = _positive_capacity(
            episode_capacity, "episode capacity", DEFAULT_EPISODE_CAPACITY
        )
        self._max_witness_bytes = _positive_capacity(
            max_witness_bytes, "witness byte boundary", DEFAULT_MAX_WITNESS_BYTES
        )
        self._max_encoded_state_bytes = _positive_capacity(
            max_encoded_state_bytes,
            "encoded state byte boundary",
            DEFAULT_MAX_ENCODED_STATE_BYTES,
        )
        self._episodes: dict[str, PredictiveEpisodeReceipt] = {}
        self._relations: dict[str, PredictionRelation] = {}
        self._current_episode_id: str | None = None
        self._armed_intent: ActionIntent | None = None
        self._pending: FullFieldPredictionAttempt | None = None
        self._latest_resolution: FullFieldPredictionResolution | None = None
        self._lock = threading.RLock()

    def _referenced_episode_ids_locked(self) -> set[str]:
        required: set[str] = set()
        if self._current_episode_id is not None:
            required.add(self._current_episode_id)
        for relation in self._relations.values():
            required.add(relation.latest_evidence.context_episode_id)
            required.add(relation.latest_evidence.target_episode_id)
        if self._pending is not None:
            required.add(self._pending.context_episode_id)
            for record in self._pending.candidates:
                episode_id = record.get("episode_id")
                if isinstance(episode_id, str):
                    required.add(episode_id)
        if self._latest_resolution is not None:
            actual_id = self._latest_resolution.actual_episode_record.get(
                "episode_id"
            )
            if isinstance(actual_id, str):
                required.add(actual_id)
            attempt = self._latest_resolution.attempt_record
            context_id = attempt.get("context_episode_id")
            if isinstance(context_id, str):
                required.add(context_id)
            for record in attempt.get("candidates", ()):
                if isinstance(record, Mapping):
                    episode_id = record.get("episode_id")
                    if isinstance(episode_id, str):
                        required.add(episode_id)
        return required

    def _compact_unreferenced_episodes_locked(
        self, *, retain: tuple[str, ...] = ()
    ) -> int:
        """Discard only witnesses with no live or learned reference."""
        required = self._referenced_episode_ids_locked()
        required.update(retain)
        removable = tuple(
            key for key in sorted(self._episodes) if key not in required
        )
        for key in removable:
            del self._episodes[key]
        return len(removable)

    def compact_unreferenced_episodes(self) -> int:
        """Release experience witnesses with no live or learned reference.

        Prediction relations retain their authenticated context and target
        witnesses.  Merely having been experienced is not a reason to keep a
        second lifetime index of the full causal settlement.
        """
        with self._lock:
            with self._atomic():
                return self._compact_unreferenced_episodes_locked()

    def _verify_episode(self, episode: PredictiveEpisodeReceipt) -> None:
        if not isinstance(episode, PredictiveEpisodeReceipt):
            raise TypeError("prediction episode is not typed")
        payload = episode.payload()
        _sha256(episode.episode_id, "prediction episode")
        _sha256(episode.structure_id, "prediction structure")
        if receipt_sha256(_canonical(episode.settlement_witness)) != _sha256(
            episode.settlement_receipt_sha256, "prediction settlement"
        ):
            raise ValueError("prediction episode settlement witness changed")
        structure = _episode_structure(
            episode.settlement_witness,
            episode.auditory_attachment,
            episode.w1_attachment,
        )
        if (
            episode.structure_id != _digest(structure)
            or episode.episode_id != _digest(payload)
            or not hmac.compare_digest(
                episode.authority_hmac_sha256,
                _sign(self._key, EPISODE_DOMAIN, payload),
            )
        ):
            raise ValueError("prediction episode authority changed")
        if len(_canonical(payload)) > self._max_witness_bytes:
            raise ValueError("prediction episode witness exceeds its byte boundary")

    @staticmethod
    def _verify_language_episode(
        authority: CausalLanguageConstructionAuthority,
        episode: CausalLanguageEpisode,
    ) -> None:
        if not isinstance(authority, CausalLanguageConstructionAuthority):
            raise TypeError("auditory attachment requires language authority")
        if not isinstance(episode, CausalLanguageEpisode):
            raise TypeError("auditory attachment language episode is not typed")
        if authority.verify_episode_record(episode.as_record()) != episode:
            raise ValueError("auditory language episode authority changed")

    @staticmethod
    def _verify_binaural_cochlear_topology(
        settlement: CausalExperienceSettlement,
    ) -> None:
        sound = next(
            (
                item for item in settlement.interpretations
                if item.sense == "sound"
            ),
            None,
        )
        if sound is None or sound.state != "observed" or len(sound.substreams) != 64:
            raise ValueError(
                "W1 acoustic prediction requires two complete cochleae"
            )
        coordinate_axes = (
            "acoustic-receptor",
            "cochlear-channel",
            "kernel-component",
            "centre-hz",
            "erb-width-hz",
            "gammatone-order",
            "observation-hop-samples",
        )
        for topology_index, substream in enumerate(sound.substreams):
            ear = "left" if topology_index < 32 else "right"
            local_index = topology_index % 32
            channel_index = local_index // 2
            pressure = local_index % 2 == 0
            channel = AUDITORY_CHANNELS[channel_index]
            component = (
                "pressure-envelope"
                if pressure else "carrier-phase-advance"
            )
            expected_coordinates = (
                ("acoustic-receptor", ear),
                ("cochlear-channel", channel.name),
                ("kernel-component", component),
                ("centre-hz", str(channel.centre_hz)),
                ("erb-width-hz", str(channel.erb_width_hz)),
                ("gammatone-order", str(COCHLEAR_ORDER)),
                (
                    "observation-hop-samples",
                    str(OBSERVATION_HOP_SAMPLES),
                ),
            )
            expected_suffix = (
                "pressure" if pressure else "phase_advance"
            )
            expected_quantity = (
                "cochlear-pressure-envelope"
                if pressure
                else "cochlear-carrier-phase-advance"
            )
            expected_unit = (
                "full-scale-pressure"
                if pressure
                else "nyquist-fraction-per-observation-hop"
            )
            if (
                substream.topology_index != topology_index
                or tuple(axis for axis, _value in substream.coordinates)
                != coordinate_axes
                or substream.coordinates != expected_coordinates
                or substream.sensor_id
                != f"W1-calibrated-{ear}-cochlear-field"
                or substream.substream_id
                != f"{ear}-{channel.name}_{expected_suffix}"
                or substream.physical_quantity != expected_quantity
                or substream.physical_unit != expected_unit
            ):
                raise ValueError(
                    "W1 acoustic prediction cochlear topology changed"
                )

    @staticmethod
    def _verify_w1(
        *,
        settlement: CausalExperienceSettlement,
        world_authority: EmbodimentWorldAuthority,
        sensory_authority: (
            EmbodimentSensoryOutcomeAuthority
            | W1AudiovisualPhysicalEvidenceAuthority
        ),
        observation: ObservationSnapshot,
        outcome_receipt: (
            OutcomeObservationReceipt | W1PhysicalEvidenceReceipt
        ),
        execution_receipt: ActionExecutionReceipt | None,
    ) -> None:
        if not isinstance(world_authority, EmbodimentWorldAuthority):
            raise TypeError("W1 attachment requires world authority")
        if not isinstance(sensory_authority, (
            EmbodimentSensoryOutcomeAuthority,
            W1AudiovisualPhysicalEvidenceAuthority,
        )):
            raise TypeError("W1 attachment requires sensory authority")
        if not isinstance(observation, ObservationSnapshot):
            raise TypeError("W1 attachment observation is not typed")
        if execution_receipt is None:
            if world_authority.observation_snapshot() != observation:
                raise ValueError("passive W1 observation is not the current world state")
        else:
            world_authority.verify_execution_receipt(execution_receipt)
            if execution_receipt.after != observation:
                raise ValueError("W1 execution does not end at attached observation")
        if isinstance(
            sensory_authority, W1AudiovisualPhysicalEvidenceAuthority
        ):
            if not isinstance(outcome_receipt, W1PhysicalEvidenceReceipt):
                raise TypeError(
                    "anonymous W1 attachment requires physical evidence receipt"
                )
            sensory_authority.verify_evidence_receipt(outcome_receipt)
            expected_execution = (
                execution_receipt.authority_receipt_sha256
                if execution_receipt is not None else None
            )
            if (
                outcome_receipt.world_execution_receipt_sha256
                != expected_execution
                or outcome_receipt.world_observation_after_receipt_sha256
                != observation.authority_receipt_sha256
                or (
                    execution_receipt is not None
                    and outcome_receipt
                    .world_observation_before_receipt_sha256
                    != execution_receipt.before.authority_receipt_sha256
                )
                or (
                    execution_receipt is None
                    and outcome_receipt
                    .world_observation_before_receipt_sha256
                    != observation.authority_receipt_sha256
                )
                or outcome_receipt.causal_settlement_receipt_sha256
                != settlement.authority_receipt_sha256
            ):
                raise ValueError(
                    "anonymous W1 receipt is not a reproducible physical boundary"
                )
            acoustic = bool(
                outcome_receipt.acoustic_emission_receipt_sha256s
            )
            if acoustic:
                if (
                    execution_receipt is None
                    or not outcome_receipt.binaural_commitment
                ):
                    raise ValueError(
                        "anonymous W1 acoustic receipt lost its physical cause"
                    )
                FullFieldPredictionAuthority._verify_binaural_cochlear_topology(
                    settlement
                )
                # Raw pressure is deliberately transient.  The evidence
                # authority has already signed its exact emission receipts,
                # binaural commitment, full-field settlement, and world
                # execution as one boundary.  Reconstructing discarded PCM
                # here would require retaining the sensory firehose.
                return
            if outcome_receipt.binaural_commitment:
                raise ValueError(
                    "anonymous W1 nonacoustic receipt carries sound state"
                )
            reproduced_mount = (
                sensory_authority.mount_authenticated_action_outcome(
                    execution_receipt, commit=False
                )
                if execution_receipt is not None
                else sensory_authority.mount_current_observation(commit=False)
            )
            reproduced = reproduced_mount.causal_settlement
            if reproduced is None:
                raise ValueError("anonymous W1 field could not be reproduced")
        else:
            if not isinstance(outcome_receipt, OutcomeObservationReceipt):
                raise TypeError(
                    "legacy W1 attachment requires geometry outcome receipt"
                )
            sensory_authority.verify_outcome_observation_receipt(
                outcome_receipt
            )
            if (
                outcome_receipt.world_observation_receipt_sha256
                != observation.authority_receipt_sha256
                or outcome_receipt.world_revision != observation.revision
                or outcome_receipt.execution_receipt_sha256
                != (
                    execution_receipt.authority_receipt_sha256
                    if execution_receipt is not None
                    else None
                )
            ):
                raise ValueError("W1 outcome receipt names another observation")
            reproduced_outcome = sensory_authority.transduce(
                observation,
                causal_owner=ExactCausalExperienceOwner(
                    on_settlement=lambda _value: None,
                    log_event=lambda *_args, **_kwargs: None,
                ),
                execution_receipt=execution_receipt,
                commit=False,
            )
            reproduced = reproduced_outcome.causal_settlement
        # Re-run the canonical stateless transducer.  This proves the supplied
        # full field is the physical field produced by this exact geometry.
        if (
            reproduced.structural_fingerprint
            != settlement.structural_fingerprint
        ):
            raise ValueError("W1 geometry does not produce attached causal field")

    def admit_episode(
        self,
        settlement: CausalExperienceSettlement,
        *,
        intake_authority: AuditoryBatchCausalIntakeAuthority | None = None,
        intake: AuditoryBatchCausalIntakeReceipt | None = None,
        token_authority: AuditoryTokenSequenceAuthority | None = None,
        token_sequence: AuditoryTokenSequenceReceipt | None = None,
        language_authority: CausalLanguageConstructionAuthority | None = None,
        language_episode: CausalLanguageEpisode | None = None,
        world_authority: EmbodimentWorldAuthority | None = None,
        sensory_authority: (
            EmbodimentSensoryOutcomeAuthority
            | W1AudiovisualPhysicalEvidenceAuthority
            | None
        ) = None,
        observation: ObservationSnapshot | None = None,
        outcome_receipt: (
            OutcomeObservationReceipt | W1PhysicalEvidenceReceipt | None
        ) = None,
        execution_receipt: ActionExecutionReceipt | None = None,
        continuity_authority: (
            W1AnonymousAudiovisualContinuityOwner | None
        ) = None,
        continuity_experience: (
            W1AnonymousAudiovisualContinuityExperience | None
        ) = None,
        auditory_transport: AuditoryPCMContinuityReceipt | None = None,
        auditory_cochlear: (
            AuditoryGammatoneContinuationReceipt | None
        ) = None,
        auditory_stream_settlement: (
            AuditoryStreamSettlementReceipt | None
        ) = None,
    ) -> PredictiveEpisodeReceipt:
        witness = _settlement_witness(
            settlement, max_bytes=self._max_witness_bytes
        )
        auditory_values = (
            intake_authority,
            intake,
            token_authority,
            token_sequence,
        )
        auditory = None
        if any(value is not None for value in auditory_values):
            if not all(value is not None for value in auditory_values):
                raise ValueError("auditory prediction attachment is incomplete")
            token_authority.verify_sequence(token_sequence)
            intake_authority.verify_for_episode(
                intake=intake,
                sequence=token_sequence,
                settlement=settlement,
            )
            if (language_authority is None) != (language_episode is None):
                raise ValueError("language prediction attachment is incomplete")
            if language_episode is not None:
                self._verify_language_episode(language_authority, language_episode)
                if (
                    language_episode.sequence_id != token_sequence.sequence_id
                    or language_episode.settlement_receipt_sha256
                    != settlement.authority_receipt_sha256
                    or language_episode.causal_intake_id != intake.intake_id
                ):
                    raise ValueError("language prediction episode names another intake")
            auditory = {
                "causal_intake": intake.as_record(),
                "language_episode": (
                    language_episode.as_record()
                    if language_episode is not None
                    else None
                ),
                "sequence": token_sequence.as_record(),
            }
        elif language_authority is not None or language_episode is not None:
            raise ValueError("language episode requires authenticated auditory intake")

        stream_values = (
            auditory_transport,
            auditory_cochlear,
            auditory_stream_settlement,
        )
        if any(value is not None for value in stream_values):
            if not all(value is not None for value in stream_values):
                raise ValueError(
                    "continuous auditory prediction authority is incomplete"
                )
            auditory_transport.verify()
            auditory_cochlear.verify()
            auditory_stream_settlement.verify()
            if (
                auditory_cochlear.stream_id != auditory_transport.stream_id
                or auditory_cochlear.sequence != auditory_transport.sequence
                or auditory_cochlear.first_sample_index
                != auditory_transport.first_sample_index
                or auditory_cochlear.sample_count
                != auditory_transport.sample_count
                or auditory_cochlear.transport_receipt_sha256
                != auditory_transport.receipt_sha256
                or auditory_stream_settlement.transport_receipt_sha256
                != auditory_transport.receipt_sha256
                or auditory_stream_settlement.cochlear_receipt_sha256
                != auditory_cochlear.receipt_sha256
                or auditory_stream_settlement
                .causal_settlement_authority_receipt_sha256
                != settlement.authority_receipt_sha256
                or auditory_stream_settlement.source_time_start
                != settlement.source_time_start
                or auditory_stream_settlement.source_time_end
                != settlement.source_time_end
            ):
                raise ValueError(
                    "continuous auditory authority names another experience"
                )
            if auditory is None:
                auditory = {}
            auditory["continuous_stream"] = {
                "cochlear_prior_state_receipt_sha256": (
                    auditory_cochlear.prior_state_receipt_sha256
                ),
                "cochlear_receipt_sha256": auditory_cochlear.receipt_sha256,
                "first_sample_index": auditory_transport.first_sample_index,
                "joint_settlement_receipt_sha256": (
                    auditory_stream_settlement.authority_receipt_sha256
                ),
                "prior_transport_receipt_sha256": (
                    auditory_transport.prior_receipt_sha256
                ),
                "sample_count": auditory_transport.sample_count,
                "sequence": auditory_transport.sequence,
                "source_epoch_start_ns": (
                    auditory_transport.source_epoch_start_ns
                ),
                "source_time_end": str(
                    auditory_stream_settlement.source_time_end
                ),
                "source_time_start": str(
                    auditory_stream_settlement.source_time_start
                ),
                "stream_id": auditory_transport.stream_id,
                "transport_receipt_sha256": (
                    auditory_transport.receipt_sha256
                ),
            }

        w1_values = (
            world_authority,
            sensory_authority,
            observation,
            outcome_receipt,
        )
        w1 = None
        if any(value is not None for value in w1_values) or execution_receipt is not None:
            if not all(value is not None for value in w1_values):
                raise ValueError("W1 prediction attachment is incomplete")
            self._verify_w1(
                settlement=settlement,
                world_authority=world_authority,
                sensory_authority=sensory_authority,
                observation=observation,
                outcome_receipt=outcome_receipt,
                execution_receipt=execution_receipt,
            )
            w1 = {
                "execution": (
                    execution_receipt.as_record()
                    if execution_receipt is not None
                    else None
                ),
                "observation": observation.as_record(),
                "outcome_observation": outcome_receipt.as_record(),
            }
        continuity_values = (
            continuity_authority,
            continuity_experience,
        )
        if any(value is not None for value in continuity_values):
            if not all(value is not None for value in continuity_values):
                raise ValueError(
                    "audiovisual prediction continuity is incomplete"
                )
            if (
                w1 is None
                or not isinstance(
                    sensory_authority,
                    W1AudiovisualPhysicalEvidenceAuthority,
                )
                or not isinstance(
                    outcome_receipt,
                    W1PhysicalEvidenceReceipt,
                )
            ):
                raise ValueError(
                    "audiovisual prediction continuity lacks W1 evidence"
                )
            continuity_authority.verify_experience(
                continuity_experience
            )
            if (
                continuity_experience
                .physical_evidence_receipt_sha256
                != outcome_receipt.authority_receipt_sha256
                or continuity_experience
                .world_observation_before_receipt_sha256
                != outcome_receipt
                .world_observation_before_receipt_sha256
                or continuity_experience
                .world_observation_after_receipt_sha256
                != outcome_receipt
                .world_observation_after_receipt_sha256
            ):
                raise ValueError(
                    "audiovisual prediction continuity names another boundary"
                )
            w1["anonymous_audiovisual_continuity"] = {
                "authority_receipt_sha256": (
                    continuity_experience.authority_receipt_sha256
                ),
                "prior_continuity_receipt_sha256": (
                    continuity_experience
                    .prior_continuity_receipt_sha256
                ),
                "schema": (
                    "guala.full_field_prediction."
                    "anonymous_audiovisual_continuity.v1"
                ),
                "world_observation_after_receipt_sha256": (
                    continuity_experience
                    .world_observation_after_receipt_sha256
                ),
                "world_observation_before_receipt_sha256": (
                    continuity_experience
                    .world_observation_before_receipt_sha256
                ),
            }
        structure_id = _digest(_episode_structure(witness, auditory, w1))
        payload = {
            "auditory_attachment": auditory,
            "schema": EPISODE_SCHEMA,
            "settlement_receipt_sha256": settlement.authority_receipt_sha256,
            "settlement_witness": witness,
            "structure_id": structure_id,
            "w1_attachment": w1,
        }
        if len(_canonical(payload)) > self._max_witness_bytes:
            raise RuntimeError(
                "full-field prediction witness exceeds its byte boundary"
            )
        episode = PredictiveEpisodeReceipt(
            episode_id=_digest(payload),
            structure_id=structure_id,
            settlement_receipt_sha256=settlement.authority_receipt_sha256,
            settlement_witness=witness,
            auditory_attachment=auditory,
            w1_attachment=w1,
            authority_hmac_sha256=_sign(self._key, EPISODE_DOMAIN, payload),
        )
        self._verify_episode(episode)
        with self._lock:
            existing = self._episodes.get(episode.episode_id)
            if existing is not None:
                if existing != episode:
                    raise ValueError("prediction episode identity was offered differently")
                return existing
            with self._atomic():
                if len(self._episodes) >= self._episode_capacity:
                    self._compact_unreferenced_episodes_locked()
                if len(self._episodes) >= self._episode_capacity:
                    raise RuntimeError("prediction_capacity_full")
                self._episodes[episode.episode_id] = episode
                try:
                    self._encoded_locked()
                except RuntimeError as error:
                    if str(error) != "prediction_capacity_full":
                        raise
                    self._compact_unreferenced_episodes_locked(
                        retain=(episode.episode_id,)
                    )
                    self._encoded_locked()
        return episode

    def is_exact_passive_continuation(
        self,
        context: PredictiveEpisodeReceipt,
        actual: PredictiveEpisodeReceipt,
    ) -> bool:
        """Prove one passive edge from authenticated physical continuity."""
        self._verify_episode(context)
        self._verify_episode(actual)
        left_w1 = context.w1_attachment
        right_w1 = actual.w1_attachment
        left = (
            left_w1.get("anonymous_audiovisual_continuity")
            if isinstance(left_w1, Mapping) else None
        )
        right = (
            right_w1.get("anonymous_audiovisual_continuity")
            if isinstance(right_w1, Mapping) else None
        )
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            w1_continuous = False
        else:
            w1_continuous = (
                right.get("prior_continuity_receipt_sha256")
                == left.get("authority_receipt_sha256")
                and right.get(
                    "world_observation_before_receipt_sha256"
                )
                == left.get("world_observation_after_receipt_sha256")
            )
        if w1_continuous:
            return True
        left_auditory = context.auditory_attachment
        right_auditory = actual.auditory_attachment
        if not isinstance(left_auditory, Mapping) or not isinstance(
            right_auditory, Mapping
        ):
            return False
        left_stream = left_auditory.get("continuous_stream")
        right_stream = right_auditory.get("continuous_stream")
        if not isinstance(left_stream, Mapping) or not isinstance(
            right_stream, Mapping
        ):
            return False
        return (
            right_stream.get("stream_id") == left_stream.get("stream_id")
            and right_stream.get("source_epoch_start_ns")
            == left_stream.get("source_epoch_start_ns")
            and right_stream.get("sequence")
            == left_stream.get("sequence") + 1
            and right_stream.get("first_sample_index")
            == left_stream.get("first_sample_index")
            + left_stream.get("sample_count")
            and right_stream.get("prior_transport_receipt_sha256")
            == left_stream.get("transport_receipt_sha256")
            and right_stream.get("cochlear_prior_state_receipt_sha256")
            == left_stream.get("cochlear_receipt_sha256")
            and right_stream.get("source_time_start")
            == left_stream.get("source_time_end")
        )

    def _relation_candidates_locked(
        self,
        *,
        context_structure_id: str,
        mode: str,
        action_receipt_sha256: str | None,
    ) -> tuple[PredictiveEpisodeReceipt, ...]:
        target_ids = sorted({
            relation.target_structure_id
            for relation in self._relations.values()
            if (
                relation.context_structure_id == context_structure_id
                and relation.mode == mode
                and relation.action_receipt_sha256 == action_receipt_sha256
            )
        })
        result = []
        for structure_id in target_ids:
            candidates = sorted(
                (
                    episode for episode in self._episodes.values()
                    if episode.structure_id == structure_id
                ),
                key=lambda value: value.episode_id,
            )
            if not candidates:
                raise ValueError("prediction relation lost target episode")
            result.append(candidates[-1])
        return tuple(result)

    def _issue_locked(
        self,
        context: PredictiveEpisodeReceipt,
        *,
        mode: str,
        intent: ActionIntent | None,
    ) -> FullFieldPredictionAttempt:
        candidates = self._relation_candidates_locked(
            context_structure_id=context.structure_id,
            mode=mode,
            action_receipt_sha256=(
                intent.action.authority_receipt_sha256 if intent is not None else None
            ),
        )
        status = (
            "unknown"
            if not candidates
            else "predicted"
            if len(candidates) == 1
            else "ambiguous"
        )
        payload = {
            "action_intent_record": intent.as_record() if intent is not None else None,
            "candidates": [value.as_record() for value in candidates],
            "context_episode_id": context.episode_id,
            "context_structure_id": context.structure_id,
            "mode": mode,
            "schema": ATTEMPT_SCHEMA,
            "status": status,
        }
        return FullFieldPredictionAttempt(
            attempt_id=_digest(payload),
            mode=mode,
            context_episode_id=context.episode_id,
            context_structure_id=context.structure_id,
            action_intent_record=(
                intent.as_record() if intent is not None else None
            ),
            status=status,
            candidates=tuple(value.as_record() for value in candidates),
            authority_hmac_sha256=_sign(self._key, ATTEMPT_DOMAIN, payload),
        )

    def open_context(
        self, episode: PredictiveEpisodeReceipt
    ) -> FullFieldPredictionAttempt:
        self._verify_episode(episode)
        with self._lock:
            if self._current_episode_id is not None or self._pending is not None:
                raise ValueError("full-field prediction context is already active")
            if self._episodes.get(episode.episode_id) != episode:
                raise ValueError("full-field prediction episode is not retained")
            with self._atomic():
                self._current_episode_id = episode.episode_id
                self._armed_intent = None
                self._pending = self._issue_locked(
                    episode, mode="passive", intent=None
                )
            return self._pending

    def condition_on_action(
        self, *, intent: ActionIntent, action_cycle: CausalActionCycle
    ) -> FullFieldPredictionAttempt:
        if not isinstance(action_cycle, CausalActionCycle):
            raise TypeError("action prediction requires causal action authority")
        if not action_cycle.verify_live_intent(intent):
            raise ValueError("action prediction intent is not live and authenticated")
        intent.action.verify(
            max_scalars=DEFAULT_MAX_SPEECH_SCALARS,
            max_command_bytes=DEFAULT_MAX_COMMAND_BYTES,
        )
        with self._lock:
            if self._current_episode_id is None or self._pending is None:
                raise ValueError("action prediction requires an active context")
            context = self._episodes[self._current_episode_id]
            if (
                intent.trigger_settlement_receipt_sha256
                != context.settlement_receipt_sha256
                or intent.trigger_structural_fingerprint
                != context.settlement_witness.get("structural_fingerprint")
            ):
                raise ValueError("action prediction intent names another context")
            with self._atomic():
                self._armed_intent = intent
                self._pending = self._issue_locked(
                    context, mode="action_conditioned", intent=intent
                )
            return self._pending

    @staticmethod
    def _verified_closure(
        *,
        action_cycle: CausalActionCycle,
        closure_record: Mapping[str, object],
        intent: ActionIntent,
        context: PredictiveEpisodeReceipt,
        actual: PredictiveEpisodeReceipt,
    ) -> Mapping[str, object]:
        if not isinstance(action_cycle, CausalActionCycle):
            raise TypeError("action outcome requires causal action authority")
        if not isinstance(closure_record, Mapping):
            raise TypeError("action outcome closure record is not an object")
        expected_fields = {
            "authority_hmac_sha256",
            "execution",
            "feedback",
            "intent",
            "outcome",
            "schema",
        }
        if set(closure_record) != expected_fields:
            raise ValueError("action outcome closure fields changed")
        closure_payload = {
            key: closure_record[key]
            for key in ("execution", "feedback", "intent", "outcome", "schema")
        }
        closure_receipt = _digest({
            "authority_hmac_sha256": closure_record["authority_hmac_sha256"],
            "payload": closure_payload,
        })
        evidence = action_cycle.verified_relation_evidence()
        matching = [
            item for item in evidence
            if (
                item.binding_id == intent.binding_id
                and item.action == intent.action
                and item.latest_closure_receipt_sha256 == closure_receipt
                and item.outcome_witness is not None
                and item.outcome_witness.settlement_receipt_sha256
                == actual.settlement_receipt_sha256
            )
        ]
        if len(matching) != 1:
            raise ValueError("action outcome closure is not retained and authenticated")
        item = matching[0]
        intent_record = closure_record.get("intent")
        execution_record = closure_record.get("execution")
        outcome_record = closure_record.get("outcome")
        if (
            intent_record != intent.as_record()
            or not isinstance(execution_record, Mapping)
            or execution_record.get("disposition") != "executed"
            or not isinstance(outcome_record, Mapping)
            or outcome_record.get("outcome_settlement_receipt_sha256")
            != actual.settlement_receipt_sha256
            or intent.trigger_settlement_receipt_sha256
            != context.settlement_receipt_sha256
        ):
            raise ValueError("action outcome closure names another transition")
        return {
            "action": item.action.as_record(),
            "binding_id": item.binding_id,
            "closure_receipt_sha256": closure_receipt,
            "outcome_settlement_receipt_sha256": (
                item.outcome_witness.settlement_receipt_sha256
            ),
            "schema": "guala.full_field_prediction.verified_action_closure.v1",
            "status": item.status,
            "trigger_settlement_receipt_sha256": (
                intent.trigger_settlement_receipt_sha256
            ),
        }

    def _resolve_locked(
        self,
        attempt: FullFieldPredictionAttempt,
        actual: PredictiveEpisodeReceipt,
    ) -> FullFieldPredictionResolution:
        actual_structure = _episode_structure(
            actual.settlement_witness,
            actual.auditory_attachment,
            actual.w1_attachment,
        )
        candidate_outcomes = []
        exact_ids = []
        for record in attempt.candidates:
            candidate = self._episode_from_record(record)
            outcomes = _compare_structures(
                _episode_structure(
                    candidate.settlement_witness,
                    candidate.auditory_attachment,
                    candidate.w1_attachment,
                ),
                actual_structure,
            )
            state = _overall(outcomes)
            if state == "exact":
                exact_ids.append(candidate.episode_id)
            candidate_outcomes.append({
                "candidate_episode_id": candidate.episode_id,
                "field_outcomes": [value.as_record() for value in outcomes],
                "state": state,
            })
        if attempt.status == "unknown":
            verification = "unknown_observed"
        elif attempt.status == "predicted":
            state = candidate_outcomes[0]["state"]
            verification = {
                "exact": "predicted_exact",
                "mismatch": "predicted_mismatch",
                "unknown": "predicted_unknown_unobserved",
                "ambiguous": "predicted_ambiguous",
            }[state]
        else:
            verification = (
                "ambiguous_candidate_observed"
                if exact_ids
                else "ambiguous_novel_observed"
            )
        payload = {
            "actual_episode_record": actual.as_record(),
            "attempt_record": attempt.as_record(),
            "candidate_outcomes": candidate_outcomes,
            "matching_candidate_episode_ids": exact_ids,
            "schema": RESOLUTION_SCHEMA,
            "verification": verification,
        }
        return FullFieldPredictionResolution(
            resolution_id=_digest(payload),
            attempt_record=attempt.as_record(),
            actual_episode_record=actual.as_record(),
            verification=verification,
            matching_candidate_episode_ids=tuple(exact_ids),
            candidate_outcomes=tuple(candidate_outcomes),
            authority_hmac_sha256=_sign(
                self._key, RESOLUTION_DOMAIN, payload
            ),
        )

    def _transition_locked(
        self,
        *,
        context: PredictiveEpisodeReceipt,
        actual: PredictiveEpisodeReceipt,
        intent: ActionIntent | None,
        closure_record: Mapping[str, object] | None,
    ) -> PredictionTransitionEvidence:
        mode = "action_conditioned" if intent is not None else "passive"
        payload = {
            "action_intent_record": intent.as_record() if intent is not None else None,
            "closure_record": (
                dict(closure_record) if closure_record is not None else None
            ),
            "context_episode_id": context.episode_id,
            "mode": mode,
            "schema": TRANSITION_SCHEMA,
            "target_episode_id": actual.episode_id,
        }
        return PredictionTransitionEvidence(
            transition_id=_digest(payload),
            mode=mode,
            context_episode_id=context.episode_id,
            target_episode_id=actual.episode_id,
            action_intent_record=(
                intent.as_record() if intent is not None else None
            ),
            closure_record=(
                dict(closure_record) if closure_record is not None else None
            ),
            authority_hmac_sha256=_sign(
                self._key, TRANSITION_DOMAIN, payload
            ),
        )

    def _relation_locked(
        self,
        *,
        context: PredictiveEpisodeReceipt,
        actual: PredictiveEpisodeReceipt,
        transition: PredictionTransitionEvidence,
        intent: ActionIntent | None,
    ) -> PredictionRelation:
        action_receipt = (
            intent.action.authority_receipt_sha256 if intent is not None else None
        )
        identity = {
            "action_receipt_sha256": action_receipt,
            "context_structure_id": context.structure_id,
            "mode": transition.mode,
            "schema": "guala.full_field_prediction.relation_identity.v1",
            "target_structure_id": actual.structure_id,
        }
        relation_id = _digest(identity)
        payload = {
            **identity,
            "latest_evidence": transition.as_record(),
            "relation_id": relation_id,
            "schema": RELATION_SCHEMA,
        }
        return PredictionRelation(
            relation_id=relation_id,
            mode=transition.mode,
            context_structure_id=context.structure_id,
            target_structure_id=actual.structure_id,
            action_receipt_sha256=action_receipt,
            latest_evidence=transition,
            authority_hmac_sha256=_sign(self._key, RELATION_DOMAIN, payload),
        )

    def observe_next(
        self,
        actual: PredictiveEpisodeReceipt,
        *,
        action_cycle: CausalActionCycle | None = None,
        closure_record: Mapping[str, object] | None = None,
    ) -> FullFieldPredictionStep:
        self._verify_episode(actual)
        with self._lock:
            if self._current_episode_id is None or self._pending is None:
                raise ValueError("full-field prediction context is not active")
            if self._episodes.get(actual.episode_id) != actual:
                raise ValueError("actual prediction episode is not retained")
            if (
                self._current_episode_id == actual.episode_id
                and self._latest_resolution is not None
                and self._latest_resolution.actual_episode_record
                == actual.as_record()
            ):
                prior_attempt = self._latest_resolution.attempt_record
                transition = next(
                    (
                        relation.latest_evidence
                        for relation in self._relations.values()
                        if (
                            relation.latest_evidence.context_episode_id
                            == prior_attempt.get("context_episode_id")
                            and relation.latest_evidence.target_episode_id
                            == actual.episode_id
                            and relation.latest_evidence.mode
                            == prior_attempt.get("mode")
                            and relation.latest_evidence.action_intent_record
                            == prior_attempt.get("action_intent_record")
                        )
                    ),
                    None,
                )
                if transition is None:
                    raise ValueError("idempotent prediction step lost transition")
                relation = next(
                    value
                    for value in self._relations.values()
                    if value.latest_evidence == transition
                )
                return FullFieldPredictionStep(
                    resolution=self._latest_resolution,
                    transition=transition,
                    relation=relation,
                    next_prediction=self._pending,
                )
            context = self._episodes[self._current_episode_id]
            intent = self._armed_intent
            verified_closure_record = None
            if intent is None:
                if action_cycle is not None or closure_record is not None:
                    raise ValueError("passive prediction cannot accept action closure")
            else:
                if action_cycle is None or closure_record is None:
                    raise ValueError("action_outcome_unavailable")
                verified_closure_record = self._verified_closure(
                    action_cycle=action_cycle,
                    closure_record=closure_record,
                    intent=intent,
                    context=context,
                    actual=actual,
                )
            resolution = self._resolve_locked(self._pending, actual)
            transition = self._transition_locked(
                context=context,
                actual=actual,
                intent=intent,
                closure_record=verified_closure_record,
            )
            relation = self._relation_locked(
                context=context,
                actual=actual,
                transition=transition,
                intent=intent,
            )
            with self._atomic():
                if relation.relation_id not in self._relations:
                    count = sum(
                        value.mode == relation.mode
                        for value in self._relations.values()
                    )
                    capacity = (
                        self._action_capacity
                        if relation.mode == "action_conditioned"
                        else self._passive_capacity
                    )
                    if count >= capacity:
                        raise RuntimeError("prediction_capacity_full")
                self._relations[relation.relation_id] = relation
                self._latest_resolution = resolution
                self._current_episode_id = actual.episode_id
                self._armed_intent = None
                self._pending = self._issue_locked(
                    actual, mode="passive", intent=None
                )
            return FullFieldPredictionStep(
                resolution=resolution,
                transition=transition,
                relation=relation,
                next_prediction=self._pending,
            )

    def stop_context(self) -> None:
        with self._lock:
            with self._atomic():
                self._current_episode_id = None
                self._armed_intent = None
                self._pending = None

    def current_attempt(self) -> FullFieldPredictionAttempt | None:
        with self._lock:
            return self._pending

    def current_episode(self) -> PredictiveEpisodeReceipt | None:
        """Return the authenticated active episode without changing state."""
        with self._lock:
            if self._current_episode_id is None:
                return None
            episode = self._episodes.get(self._current_episode_id)
            if episode is None:
                raise ValueError("prediction active episode is missing")
            self._verify_episode(episode)
            return episode

    def cancel_conditioned_action(
        self, intent_receipt_sha256: object
    ) -> FullFieldPredictionAttempt:
        """Return an unexecuted exact action context to passive prediction."""
        receipt = _sha256(
            intent_receipt_sha256, "cancelled prediction intent"
        )
        with self._lock:
            if (
                self._current_episode_id is None
                or self._pending is None
                or self._armed_intent is None
                or self._armed_intent.authority_receipt_sha256 != receipt
                or self._pending.mode != "action_conditioned"
            ):
                raise ValueError(
                    "prediction has no matching conditioned action"
                )
            context = self._episodes[self._current_episode_id]
            with self._atomic():
                self._armed_intent = None
                self._pending = self._issue_locked(
                    context, mode="passive", intent=None
                )
            return self._pending

    def replace_current_episode(
        self, episode: PredictiveEpisodeReceipt
    ) -> FullFieldPredictionAttempt:
        """Replace one active receipt with richer proof of the same event.

        This is attachment completion, not a temporal transition.  It is
        permitted only before an action is conditioned and only when the
        immutable causal-settlement receipt is identical.
        """
        self._verify_episode(episode)
        with self._lock:
            if self._current_episode_id is None or self._pending is None:
                raise ValueError("full-field prediction context is not active")
            if self._armed_intent is not None:
                raise ValueError(
                    "conditioned prediction cannot replace its context"
                )
            if self._episodes.get(episode.episode_id) != episode:
                raise ValueError("replacement prediction episode is not retained")
            current = self._episodes[self._current_episode_id]
            if (
                current.settlement_receipt_sha256
                != episode.settlement_receipt_sha256
            ):
                raise ValueError(
                    "replacement prediction episode names another event"
                )
            with self._atomic():
                self._current_episode_id = episode.episode_id
                self._pending = self._issue_locked(
                    episode, mode="passive", intent=None
                )
            return self._pending

    def latest_resolution(self) -> FullFieldPredictionResolution | None:
        with self._lock:
            return self._latest_resolution

    def relation_records(self) -> tuple[dict[str, object], ...]:
        with self._lock:
            return tuple(
                self._relations[key].as_record()
                for key in sorted(self._relations)
            )

    def observer_summary(self) -> dict[str, object]:
        """Return bounded receipt-linked display data, never decision input."""
        with self._lock:
            pending = self._pending
            resolution = self._latest_resolution
            resolution_summary = None
            if resolution is not None:
                candidate_summaries = []
                for candidate in resolution.candidate_outcomes:
                    counts = {
                        "ambiguous": 0,
                        "exact": 0,
                        "mismatch": 0,
                        "unknown_unobserved": 0,
                    }
                    for outcome in candidate.get("field_outcomes", ()):
                        state = outcome.get("state")
                        if state in counts:
                            counts[state] += 1
                    candidate_summaries.append({
                        "candidate_episode_id": candidate.get(
                            "candidate_episode_id"
                        ),
                        "field_state_counts": counts,
                        "state": candidate.get("state"),
                    })
                resolution_summary = {
                    "actual_episode_id": resolution.actual_episode_record.get(
                        "episode_id"
                    ),
                    "candidate_summaries": candidate_summaries,
                    "matching_candidate_episode_ids": list(
                        resolution.matching_candidate_episode_ids
                    ),
                    "resolution_id": resolution.resolution_id,
                    "verification": resolution.verification,
                }
            return {
                "latest_resolution": resolution_summary,
                "pending": (
                    {
                        "attempt_id": pending.attempt_id,
                        "candidate_episode_ids": [
                            candidate.get("episode_id")
                            for candidate in pending.candidates
                        ],
                        "context_episode_id": pending.context_episode_id,
                        "mode": pending.mode,
                        "status": pending.status,
                    }
                    if pending is not None else None
                ),
                "schema": "guala.full_field_prediction.observer_summary.v1",
            }

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "action_relations": sum(
                    value.mode == "action_conditioned"
                    for value in self._relations.values()
                ),
                "active_context": self._current_episode_id is not None,
                "armed_action": self._armed_intent is not None,
                "episodes": len(self._episodes),
                "passive_relations": sum(
                    value.mode == "passive"
                    for value in self._relations.values()
                ),
                "pending_status": (
                    self._pending.status if self._pending is not None else None
                ),
            }

    def _state_payload(self) -> dict[str, object]:
        persisted_pending = self._pending
        if (
            self._armed_intent is not None
            and self._current_episode_id is not None
        ):
            # Live action authority belongs to the causal action cycle and is
            # never resurrected from this snapshot.  Persist the same current
            # episode with a freshly authenticated passive attempt.
            persisted_pending = self._issue_locked(
                self._episodes[self._current_episode_id],
                mode="passive",
                intent=None,
            )
        return {
            "capacities": {
                "action_relations": self._action_capacity,
                "encoded_state_bytes": self._max_encoded_state_bytes,
                "episodes": self._episode_capacity,
                "passive_relations": self._passive_capacity,
                "witness_bytes": self._max_witness_bytes,
            },
            "current_episode_id": self._current_episode_id,
            "episodes": [
                self._episodes[key].as_record() for key in sorted(self._episodes)
            ],
            "latest_resolution": (
                self._latest_resolution.as_record()
                if self._latest_resolution is not None
                else None
            ),
            "pending": (
                persisted_pending.as_record()
                if persisted_pending is not None
                else None
            ),
            "relations": [
                self._relations[key].as_record() for key in sorted(self._relations)
            ],
            "schema": STATE_SCHEMA,
        }

    def _encoded_locked(self) -> bytes:
        payload = _canonical(self._state_payload())
        envelope = _canonical({
            "authority_hmac_sha256": hmac.new(
                self._key, STATE_DOMAIN + payload, hashlib.sha256
            ).hexdigest(),
            "payload_base64": base64.b64encode(payload).decode("ascii"),
            "schema": ENVELOPE_SCHEMA,
        })
        if len(envelope) > self._max_encoded_state_bytes:
            raise RuntimeError("prediction_capacity_full")
        return envelope

    @contextmanager
    def _atomic(self):
        prior = (
            dict(self._episodes),
            dict(self._relations),
            self._current_episode_id,
            self._armed_intent,
            self._pending,
            self._latest_resolution,
        )
        try:
            yield
            self._encoded_locked()
        except BaseException:
            (
                self._episodes,
                self._relations,
                self._current_episode_id,
                self._armed_intent,
                self._pending,
                self._latest_resolution,
            ) = prior
            raise

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            return self._encoded_locked()

    def _episode_from_record(self, record: object) -> PredictiveEpisodeReceipt:
        if not isinstance(record, Mapping):
            raise ValueError("prediction episode record is malformed")
        episode = PredictiveEpisodeReceipt(
            episode_id=record.get("episode_id"),
            structure_id=record.get("structure_id"),
            settlement_receipt_sha256=record.get(
                "settlement_receipt_sha256"
            ),
            settlement_witness=dict(record.get("settlement_witness") or {}),
            auditory_attachment=(
                dict(record["auditory_attachment"])
                if record.get("auditory_attachment") is not None
                else None
            ),
            w1_attachment=(
                dict(record["w1_attachment"])
                if record.get("w1_attachment") is not None
                else None
            ),
            authority_hmac_sha256=record.get("authority_hmac_sha256"),
        )
        self._verify_episode(episode)
        if episode.as_record() != dict(record):
            raise ValueError("prediction episode record is not canonical")
        return episode

    def restore_encoded(self, encoded: bytes) -> None:
        if (
            not isinstance(encoded, bytes)
            or not encoded
            or len(encoded) > self._max_encoded_state_bytes
        ):
            raise ValueError("prediction snapshot exceeds its byte boundary")
        try:
            envelope = json.loads(encoded.decode("utf-8"))
            payload = base64.b64decode(
                envelope["payload_base64"], validate=True
            )
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("prediction snapshot is malformed") from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"authority_hmac_sha256", "payload_base64", "schema"}
            or envelope.get("schema") != ENVELOPE_SCHEMA
            or not hmac.compare_digest(
                str(envelope.get("authority_hmac_sha256")),
                hmac.new(
                    self._key, STATE_DOMAIN + payload, hashlib.sha256
                ).hexdigest(),
            )
            or base64.b64encode(payload).decode("ascii")
            != envelope.get("payload_base64")
        ):
            raise ValueError("prediction snapshot authority changed")
        try:
            state = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("prediction state is invalid") from error
        if not isinstance(state, Mapping) or _canonical(state) != payload:
            raise ValueError("prediction state is not canonical")
        expected_capacities = {
            "action_relations": self._action_capacity,
            "encoded_state_bytes": self._max_encoded_state_bytes,
            "episodes": self._episode_capacity,
            "passive_relations": self._passive_capacity,
            "witness_bytes": self._max_witness_bytes,
        }
        if (
            state.get("schema") != STATE_SCHEMA
            or state.get("capacities") != expected_capacities
        ):
            raise ValueError("prediction state boundary changed")
        raw_episodes = state.get("episodes")
        raw_relations = state.get("relations")
        if not isinstance(raw_episodes, list) or not isinstance(raw_relations, list):
            raise ValueError("prediction state collections changed")
        episodes = {
            item.episode_id: item
            for item in (self._episode_from_record(value) for value in raw_episodes)
        }
        if len(episodes) != len(raw_episodes) or len(episodes) > self._episode_capacity:
            raise ValueError("prediction state episode boundary changed")
        # Relations, pending attempts, and latest resolution are re-issued from
        # their authenticated records through narrow parsers below.
        relations = {
            item.relation_id: item
            for item in (self._relation_from_record(value) for value in raw_relations)
        }
        if len(relations) != len(raw_relations):
            raise ValueError("prediction state repeats a relation")
        if (
            sum(value.mode == "passive" for value in relations.values())
            > self._passive_capacity
            or sum(
                value.mode == "action_conditioned" for value in relations.values()
            )
            > self._action_capacity
        ):
            raise ValueError("prediction state relation capacity changed")
        current = state.get("current_episode_id")
        if current is not None and current not in episodes:
            raise ValueError("prediction state current episode is missing")
        pending = (
            self._attempt_from_record(state.get("pending"))
            if state.get("pending") is not None
            else None
        )
        latest = (
            self._resolution_from_record(state.get("latest_resolution"))
            if state.get("latest_resolution") is not None
            else None
        )
        if (current is None) != (pending is None):
            raise ValueError("prediction state active boundary changed")
        if pending is not None and pending.context_episode_id != current:
            raise ValueError("prediction pending context changed")
        canonical_input = bytes(encoded)
        with self._lock:
            prior = (
                self._episodes,
                self._relations,
                self._current_episode_id,
                self._armed_intent,
                self._pending,
                self._latest_resolution,
            )
            self._episodes = episodes
            self._relations = relations
            self._current_episode_id = current
            # An action must be re-authorized live after restart.  Snapshots
            # therefore never restore an armed action.
            self._armed_intent = None
            self._pending = pending
            self._latest_resolution = latest
            try:
                for relation in self._relations.values():
                    evidence = relation.latest_evidence
                    context_episode = self._episodes.get(
                        evidence.context_episode_id
                    )
                    target_episode = self._episodes.get(
                        evidence.target_episode_id
                    )
                    if (
                        context_episode is None
                        or target_episode is None
                        or evidence.mode != relation.mode
                        or context_episode.structure_id
                        != relation.context_structure_id
                        or target_episode.structure_id
                        != relation.target_structure_id
                    ):
                        raise ValueError(
                            "prediction relation lost its retained episodes"
                        )
                    intent_record = evidence.action_intent_record
                    if relation.mode == "action_conditioned":
                        action_record = (
                            intent_record.get("action")
                            if isinstance(intent_record, Mapping)
                            else None
                        )
                        if (
                            not isinstance(action_record, Mapping)
                            or _digest(action_record)
                            != relation.action_receipt_sha256
                        ):
                            raise ValueError(
                                "prediction action relation changed"
                            )
                if self._current_episode_id is not None:
                    expected_pending = self._issue_locked(
                        self._episodes[self._current_episode_id],
                        mode="passive",
                        intent=None,
                    )
                    if self._pending != expected_pending:
                        raise ValueError(
                            "prediction pending relation graph changed"
                        )
                if self._latest_resolution is not None:
                    actual_record = (
                        self._latest_resolution.actual_episode_record
                    )
                    actual_id = actual_record.get("episode_id")
                    actual = self._episodes.get(actual_id)
                    restored_attempt = self._attempt_from_record(
                        self._latest_resolution.attempt_record
                    )
                    if (
                        actual is None
                        or actual.as_record() != actual_record
                        or self._resolve_locked(restored_attempt, actual)
                        != self._latest_resolution
                    ):
                        raise ValueError(
                            "prediction latest resolution graph changed"
                        )
                if self._encoded_locked() != canonical_input:
                    raise ValueError("prediction snapshot is not canonical")
            except BaseException:
                (
                    self._episodes,
                    self._relations,
                    self._current_episode_id,
                    self._armed_intent,
                    self._pending,
                    self._latest_resolution,
                ) = prior
                raise

    def _transition_from_record(
        self, record: object
    ) -> PredictionTransitionEvidence:
        if not isinstance(record, Mapping):
            raise ValueError("prediction transition record is malformed")
        item = PredictionTransitionEvidence(
            transition_id=record.get("transition_id"),
            mode=record.get("mode"),
            context_episode_id=record.get("context_episode_id"),
            target_episode_id=record.get("target_episode_id"),
            action_intent_record=(
                dict(record["action_intent_record"])
                if record.get("action_intent_record") is not None
                else None
            ),
            closure_record=(
                dict(record["closure_record"])
                if record.get("closure_record") is not None
                else None
            ),
            authority_hmac_sha256=record.get("authority_hmac_sha256"),
        )
        if (
            item.mode not in {"passive", "action_conditioned"}
            or (
                item.mode == "passive"
                and (
                    item.action_intent_record is not None
                    or item.closure_record is not None
                )
            )
            or (
                item.mode == "action_conditioned"
                and (
                    item.action_intent_record is None
                    or item.closure_record is None
                )
            )
            or item.transition_id != _digest(item.payload())
            or not hmac.compare_digest(
                str(item.authority_hmac_sha256),
                _sign(self._key, TRANSITION_DOMAIN, item.payload()),
            )
            or item.as_record() != dict(record)
        ):
            raise ValueError("prediction transition authority changed")
        return item

    def _relation_from_record(self, record: object) -> PredictionRelation:
        if not isinstance(record, Mapping):
            raise ValueError("prediction relation record is malformed")
        item = PredictionRelation(
            relation_id=record.get("relation_id"),
            mode=record.get("mode"),
            context_structure_id=record.get("context_structure_id"),
            target_structure_id=record.get("target_structure_id"),
            action_receipt_sha256=record.get("action_receipt_sha256"),
            latest_evidence=self._transition_from_record(
                record.get("latest_evidence")
            ),
            authority_hmac_sha256=record.get("authority_hmac_sha256"),
        )
        identity = {
            "action_receipt_sha256": item.action_receipt_sha256,
            "context_structure_id": item.context_structure_id,
            "mode": item.mode,
            "schema": "guala.full_field_prediction.relation_identity.v1",
            "target_structure_id": item.target_structure_id,
        }
        if (
            item.relation_id != _digest(identity)
            or (
                item.mode == "passive"
                and item.action_receipt_sha256 is not None
            )
            or (
                item.mode == "action_conditioned"
                and item.action_receipt_sha256 is None
            )
            or not hmac.compare_digest(
                str(item.authority_hmac_sha256),
                _sign(self._key, RELATION_DOMAIN, item.payload()),
            )
            or item.as_record() != dict(record)
        ):
            raise ValueError("prediction relation authority changed")
        return item

    def _attempt_from_record(
        self, record: object
    ) -> FullFieldPredictionAttempt:
        if not isinstance(record, Mapping):
            raise ValueError("prediction attempt record is malformed")
        item = FullFieldPredictionAttempt(
            attempt_id=record.get("attempt_id"),
            mode=record.get("mode"),
            context_episode_id=record.get("context_episode_id"),
            context_structure_id=record.get("context_structure_id"),
            action_intent_record=(
                dict(record["action_intent_record"])
                if record.get("action_intent_record") is not None
                else None
            ),
            status=record.get("status"),
            candidates=tuple(dict(value) for value in record.get("candidates", ())),
            authority_hmac_sha256=record.get("authority_hmac_sha256"),
        )
        for candidate in item.candidates:
            self._episode_from_record(candidate)
        expected_status = (
            "unknown"
            if not item.candidates
            else "predicted"
            if len(item.candidates) == 1
            else "ambiguous"
        )
        if (
            item.mode not in {"passive", "action_conditioned"}
            or (
                item.mode == "passive"
                and item.action_intent_record is not None
            )
            or (
                item.mode == "action_conditioned"
                and item.action_intent_record is None
            )
            or item.status != expected_status
            or item.attempt_id != _digest(item.payload())
            or not hmac.compare_digest(
                str(item.authority_hmac_sha256),
                _sign(self._key, ATTEMPT_DOMAIN, item.payload()),
            )
            or item.as_record() != dict(record)
        ):
            raise ValueError("prediction attempt authority changed")
        return item

    def _resolution_from_record(
        self, record: object
    ) -> FullFieldPredictionResolution:
        if not isinstance(record, Mapping):
            raise ValueError("prediction resolution record is malformed")
        item = FullFieldPredictionResolution(
            resolution_id=record.get("resolution_id"),
            attempt_record=dict(record.get("attempt_record") or {}),
            actual_episode_record=dict(
                record.get("actual_episode_record") or {}
            ),
            verification=record.get("verification"),
            matching_candidate_episode_ids=tuple(
                record.get("matching_candidate_episode_ids") or ()
            ),
            candidate_outcomes=tuple(
                dict(value) for value in record.get("candidate_outcomes", ())
            ),
            authority_hmac_sha256=record.get("authority_hmac_sha256"),
        )
        self._attempt_from_record(item.attempt_record)
        self._episode_from_record(item.actual_episode_record)
        if (
            item.resolution_id != _digest(item.payload())
            or not hmac.compare_digest(
                str(item.authority_hmac_sha256),
                _sign(self._key, RESOLUTION_DOMAIN, item.payload()),
            )
            or item.as_record() != dict(record)
        ):
            raise ValueError("prediction resolution authority changed")
        return item


__all__ = (
    "DEFAULT_ACTION_RELATION_CAPACITY",
    "DEFAULT_EPISODE_CAPACITY",
    "DEFAULT_MAX_ENCODED_STATE_BYTES",
    "DEFAULT_MAX_WITNESS_BYTES",
    "DEFAULT_PASSIVE_RELATION_CAPACITY",
    "ExactFieldOutcome",
    "FullFieldPredictionAttempt",
    "FullFieldPredictionAuthority",
    "FullFieldPredictionResolution",
    "FullFieldPredictionStep",
    "PredictionRelation",
    "PredictionTransitionEvidence",
    "PredictiveEpisodeReceipt",
)
