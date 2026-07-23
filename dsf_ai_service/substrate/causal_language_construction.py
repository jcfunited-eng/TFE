"""Bounded learned language constructions over exact causal experience.

This authority learns no grammatical labels.  It receives an authenticated
ordered auditory-token sequence and a verified six-sense causal settlement,
then retains only the minimum contrast lattice needed to prove an arbitrary
token order.  A variable token position is licensed only when one independently
varied token class corresponds bijectively to one changed full-field causal
referent.  Multi-position constructions require the complete Cartesian
independence lattice.

Comprehension and generation are separate read-only operations.  Unknown or
ambiguous token classes, incomplete lattices, non-unique causal contrasts, and
conflicting constructions produce explicit no-op states.  Routing chi, source
tags, Atlas, fixed grammatical sections, counts, scores, text parsing, raw
media, and lifetime episode indexes are absent by construction.
"""

from __future__ import annotations

import hashlib
import hmac
import itertools
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Mapping, Sequence

from dsf_ai_service.substrate.auditory_batch_causal_intake import (
    AuditoryBatchCausalIntakeAuthority,
    AuditoryBatchCausalIntakeReceipt,
)
from dsf_ai_service.substrate.auditory_token_sequence import (
    MAX_TOKEN_OCCURRENCES_PER_SEQUENCE,
    AuditoryTokenSequenceAuthority,
    AuditoryTokenSequenceReceipt,
    TokenClassificationState,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    causal_experience_settlement_receipt_payload,
)


EPISODE_SCHEMA = "guala.causal_language.episode.v1"
CONSTRUCTION_SCHEMA = "guala.causal_language.construction.v1"
STATE_SCHEMA = "guala.causal_language.state.v1"
ENVELOPE_SCHEMA = "guala.causal_language.state.hmac.v1"

STATE_DOMAIN = b"guala-causal-language-construction-state-v1\0"
EPISODE_DOMAIN = b"guala-causal-language-episode-v1\0"
CONSTRUCTION_DOMAIN = b"guala-causal-language-construction-v1\0"

DEFAULT_WORKING_CAPACITY = 8
DEFAULT_CONSTRUCTION_CAPACITY = 64
DEFAULT_MAX_STATE_BYTES = 32 * 1024 * 1024
MAX_IDENTIFIER_BYTES = 256


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


def _sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 identity")
    return value


def _identifier(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or len(value.encode("utf-8")) > MAX_IDENTIFIER_BYTES
    ):
        raise ValueError(f"{name} must be a bounded canonical identifier")
    return value


def _key(value: object) -> bytes:
    if isinstance(value, str):
        result = value.encode("utf-8")
    elif isinstance(value, (bytes, bytearray, memoryview)):
        result = bytes(value)
    else:
        raise ValueError("causal language authority key must be bytes or text")
    if len(result) < 32 or len(result) > 4096:
        raise ValueError("causal language authority key has an invalid boundary")
    return result


def _sign(key: bytes, domain: bytes, value: object) -> str:
    return hmac.new(key, domain + _canonical(value), hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class ConstructionToken:
    token_class_id: str
    token_form: str

    def __post_init__(self) -> None:
        _sha256(self.token_class_id, "construction token class")
        if (
            not isinstance(self.token_form, str)
            or not self.token_form
            or len(tuple(self.token_form)) > 512
            or any(0xD800 <= ord(value) <= 0xDFFF for value in self.token_form)
        ):
            raise ValueError("construction token form is invalid")

    def as_record(self) -> dict[str, str]:
        return {
            "token_class_id": self.token_class_id,
            "token_form": self.token_form,
        }


@dataclass(frozen=True, slots=True)
class CausalLanguageEpisode:
    episode_id: str
    structure_id: str
    causal_intake_id: str
    sequence_id: str
    settlement_receipt_sha256: str
    tokens: tuple[ConstructionToken, ...]
    field_roots: tuple[tuple[str, object], ...]
    causal_intake_record: Mapping[str, object]
    sequence_record: Mapping[str, object]
    settlement_witness: Mapping[str, object]
    authority_hmac_sha256: str

    def as_record(self) -> dict[str, object]:
        return {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "causal_intake_id": self.causal_intake_id,
            "causal_intake_record": dict(self.causal_intake_record),
            "episode_id": self.episode_id,
            "field_roots": [[key, value] for key, value in self.field_roots],
            "schema": EPISODE_SCHEMA,
            "sequence_id": self.sequence_id,
            "sequence_record": dict(self.sequence_record),
            "settlement_receipt_sha256": self.settlement_receipt_sha256,
            "settlement_witness": dict(self.settlement_witness),
            "structure_id": self.structure_id,
            "tokens": [value.as_record() for value in self.tokens],
        }


@dataclass(frozen=True, slots=True)
class EpisodeAdmission:
    state: str
    reason: str
    episode: CausalLanguageEpisode | None
    stored: bool


@dataclass(frozen=True, slots=True)
class ConstructionAlternative:
    causal_value_sha256: str
    causal_value: object
    token: ConstructionToken

    def as_record(self) -> dict[str, object]:
        return {
            "causal_value": self.causal_value,
            "causal_value_sha256": self.causal_value_sha256,
            "token": self.token.as_record(),
        }


@dataclass(frozen=True, slots=True)
class ConstructionElement:
    ordinal: int
    kind: str
    fixed_token: ConstructionToken | None = None
    referent_root: str | None = None
    alternatives: tuple[ConstructionAlternative, ...] = ()

    def __post_init__(self) -> None:
        if (
            isinstance(self.ordinal, bool)
            or not isinstance(self.ordinal, int)
            or self.ordinal < 0
        ):
            raise ValueError("construction element ordinal is invalid")
        if self.kind == "fixed":
            if self.fixed_token is None or self.referent_root is not None or self.alternatives:
                raise ValueError("fixed construction element changed shape")
        elif self.kind == "slot":
            if (
                self.fixed_token is not None
                or not self.referent_root
                or len(self.alternatives) < 2
            ):
                raise ValueError("slot construction element changed shape")
            causal_values = [value.causal_value_sha256 for value in self.alternatives]
            token_classes = [value.token.token_class_id for value in self.alternatives]
            if len(set(causal_values)) != len(causal_values) or len(set(token_classes)) != len(token_classes):
                raise ValueError("construction slot is not bijective")
        else:
            raise ValueError("construction element kind is invalid")

    def as_record(self) -> dict[str, object]:
        return {
            "alternatives": [value.as_record() for value in self.alternatives],
            "fixed_token": self.fixed_token.as_record() if self.fixed_token else None,
            "kind": self.kind,
            "ordinal": self.ordinal,
            "referent_root": self.referent_root,
        }


@dataclass(frozen=True, slots=True)
class LearnedConstruction:
    construction_id: str
    family_id: str
    state: str
    elements: tuple[ConstructionElement, ...]
    background_roots: tuple[tuple[str, object], ...]
    proof_episodes: tuple[Mapping[str, object], ...]
    authority_hmac_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "background_roots": [[key, value] for key, value in self.background_roots],
            "elements": [value.as_record() for value in self.elements],
            "family_id": self.family_id,
            "proof_episodes": [dict(value) for value in self.proof_episodes],
            "schema": CONSTRUCTION_SCHEMA,
            "state": self.state,
        }

    def as_record(self) -> dict[str, object]:
        return {
            **self.payload(),
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "construction_id": self.construction_id,
        }


@dataclass(frozen=True, slots=True)
class LearningResult:
    state: str
    reason: str
    construction: LearnedConstruction | None = None


@dataclass(frozen=True, slots=True)
class LanguageResolution:
    state: str
    reason: str
    construction_id: str | None = None
    tokens: tuple[ConstructionToken, ...] = ()
    referents: tuple[tuple[str, str], ...] = ()


def _token_from_record(value: object) -> ConstructionToken:
    if not isinstance(value, Mapping) or set(value) != {"token_class_id", "token_form"}:
        raise ValueError("construction token record changed")
    return ConstructionToken(
        token_class_id=value.get("token_class_id"),
        token_form=value.get("token_form"),
    )


def _settlement_witness(settlement: CausalExperienceSettlement) -> dict[str, object]:
    payload = causal_experience_settlement_receipt_payload(
        event_id=settlement.event_id,
        structural_fingerprint=settlement.structural_fingerprint,
        assembly_id=settlement.assembly_id,
        source_time_start=settlement.source_time_start,
        source_time_end=settlement.source_time_end,
        interpretations=settlement.interpretations,
        language_events=settlement.language_events,
        routing_chis=settlement.routing_chis,
        source_tags=settlement.source_tags,
        assembly_receipt_sha256=settlement.assembly_receipt_sha256,
    )
    decoded = json.loads(payload.decode("utf-8"))
    if not isinstance(decoded, dict):
        raise RuntimeError("causal settlement witness is not an object")
    return decoded


def _structural_substream(value: Mapping[str, object]) -> dict[str, object]:
    """Preserve all explicit topology and DSF values, excluding receipts."""
    return {
        "coordinates": value.get("coordinates"),
        "field_tuples": [
            {
                "fields": item.get("fields"),
                "tuple_index": item.get("tuple_index"),
            }
            for item in value.get("field_tuples", ())
        ],
        "physical_quantity": value.get("physical_quantity"),
        "physical_unit": value.get("physical_unit"),
        "sensor_id": value.get("sensor_id"),
        "substream_id": value.get("substream_id"),
        "topology_index": value.get("topology_index"),
    }


def _field_roots(witness: Mapping[str, object]) -> tuple[tuple[str, object], ...]:
    interpretations = witness.get("interpretations")
    if not isinstance(interpretations, list) or len(interpretations) != 6:
        raise ValueError("causal language witness lost six-sense structure")
    roots: dict[str, object] = {}
    for sense in interpretations:
        if not isinstance(sense, Mapping):
            raise ValueError("causal language witness sense changed")
        name = _identifier(sense.get("sense"), "causal language sense")
        # Until physical source separation exists, the whole sound sense is
        # the language carrier.  It remains complete in settlement_witness but
        # cannot also be treated as the independently changing referent.
        if name == "sound":
            continue
        # Relation is derived settlement history, not a physical referent.
        # Preserve it in settlement_witness; only availability is a candidate.
        roots[f"sense:{name}:boundary"] = {
            "state": sense.get("state"),
        }
        substreams = sense.get("substreams")
        if not isinstance(substreams, list):
            raise ValueError("causal language witness substreams changed")
        for substream in substreams:
            if not isinstance(substream, Mapping):
                raise ValueError("causal language witness substream changed")
            substream_id = _identifier(
                substream.get("substream_id"), "causal language substream"
            )
            key = f"sense:{name}:substream:{substream_id}"
            if key in roots:
                raise ValueError("causal language witness repeats a referent root")
            roots[key] = _structural_substream(substream)
    return tuple((key, roots[key]) for key in sorted(roots))


def _unique_tokens(
    sequence: AuditoryTokenSequenceReceipt,
) -> tuple[ConstructionToken, ...] | None:
    tokens = []
    for occurrence in sequence.occurrences:
        if (
            occurrence.classification_state is not TokenClassificationState.UNIQUE
            or len(occurrence.token_candidates) != 1
        ):
            return None
        candidate = occurrence.token_candidates[0]
        tokens.append(ConstructionToken(
            token_class_id=candidate.token_class_id,
            token_form=candidate.token_form,
        ))
    return tuple(tokens)


def _construction_identity_payload(
    *,
    family_id: str,
    elements: Sequence[ConstructionElement],
    background_roots: Sequence[tuple[str, object]],
) -> dict[str, object]:
    """Identity learned relation structure, never its replaceable proof copy."""
    return {
        "background_roots": [[key, value] for key, value in background_roots],
        "elements": [value.as_record() for value in elements],
        "family_id": family_id,
        "schema": "guala.causal_language.construction_identity.v1",
    }


class CausalLanguageConstructionAuthority:
    """Owns finite causal construction proofs; never a language corpus."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        working_capacity: int = DEFAULT_WORKING_CAPACITY,
        construction_capacity: int = DEFAULT_CONSTRUCTION_CAPACITY,
        max_state_bytes: int = DEFAULT_MAX_STATE_BYTES,
    ) -> None:
        root = hashlib.sha256(_key(authority_key)).digest()
        self._state_key = hashlib.sha256(STATE_DOMAIN + root).digest()
        self._episode_key = hashlib.sha256(EPISODE_DOMAIN + root).digest()
        self._construction_key = hashlib.sha256(CONSTRUCTION_DOMAIN + root).digest()
        if (
            isinstance(working_capacity, bool)
            or not isinstance(working_capacity, int)
            or not 0 < working_capacity <= DEFAULT_WORKING_CAPACITY
            or isinstance(construction_capacity, bool)
            or not isinstance(construction_capacity, int)
            or not 0 < construction_capacity <= DEFAULT_CONSTRUCTION_CAPACITY
            or isinstance(max_state_bytes, bool)
            or not isinstance(max_state_bytes, int)
            or not 0 < max_state_bytes <= DEFAULT_MAX_STATE_BYTES
        ):
            raise ValueError("causal language capacities are invalid")
        self._working_capacity = working_capacity
        self._construction_capacity = construction_capacity
        self._max_state_bytes = max_state_bytes
        self._working: OrderedDict[str, CausalLanguageEpisode] = OrderedDict()
        self._constructions: OrderedDict[str, LearnedConstruction] = OrderedDict()
        self._ambiguous_families: set[str] = set()
        self._lock = threading.RLock()

    @property
    def working_count(self) -> int:
        with self._lock:
            return len(self._working)

    @property
    def construction_count(self) -> int:
        with self._lock:
            return len(self._constructions)

    def _episode_payload(
        self,
        *,
        intake: AuditoryBatchCausalIntakeReceipt,
        sequence: AuditoryTokenSequenceReceipt,
        settlement: CausalExperienceSettlement,
        tokens: tuple[ConstructionToken, ...],
        roots: tuple[tuple[str, object], ...],
        sequence_record: Mapping[str, object],
        witness: Mapping[str, object],
    ) -> dict[str, object]:
        return {
            "causal_intake_id": intake.intake_id,
            "causal_intake_record": intake.as_record(),
            "field_roots": [[key, value] for key, value in roots],
            "schema": EPISODE_SCHEMA,
            "sequence_id": sequence.sequence_id,
            "sequence_record": dict(sequence_record),
            "settlement_receipt_sha256": settlement.authority_receipt_sha256,
            "settlement_witness": dict(witness),
            "tokens": [value.as_record() for value in tokens],
        }

    def admit_episode(
        self,
        *,
        intake_authority: AuditoryBatchCausalIntakeAuthority,
        intake: AuditoryBatchCausalIntakeReceipt,
        token_authority: AuditoryTokenSequenceAuthority,
        sequence: AuditoryTokenSequenceReceipt,
        settlement: CausalExperienceSettlement,
    ) -> EpisodeAdmission:
        if not isinstance(
            intake_authority, AuditoryBatchCausalIntakeAuthority
        ):
            raise TypeError("causal language episode requires intake authority")
        if not isinstance(intake, AuditoryBatchCausalIntakeReceipt):
            raise TypeError("causal language episode requires causal intake")
        if not isinstance(token_authority, AuditoryTokenSequenceAuthority):
            raise TypeError("causal language episode requires token authority")
        if not isinstance(sequence, AuditoryTokenSequenceReceipt):
            raise TypeError("causal language episode requires a token sequence")
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("causal language episode requires a causal settlement")
        token_authority.verify_sequence(sequence)
        settlement.verify()
        intake_authority.verify_for_episode(
            intake=intake,
            sequence=sequence,
            settlement=settlement,
        )
        if any(
            occurrence.source_time_start < settlement.source_time_start
            or occurrence.source_time_end > settlement.source_time_end
            for occurrence in sequence.occurrences
        ):
            raise ValueError("auditory sequence is outside its causal experience")
        tokens = _unique_tokens(sequence)
        if tokens is None:
            states = {value.classification_state for value in sequence.occurrences}
            state = (
                "ambiguous"
                if TokenClassificationState.AMBIGUOUS in states
                else "unknown"
            )
            return EpisodeAdmission(
                state=state,
                reason="token_classification_not_unique",
                episode=None,
                stored=False,
            )
        witness = _settlement_witness(settlement)
        roots = _field_roots(witness)
        sequence_record = sequence.as_record()
        payload = self._episode_payload(
            intake=intake,
            sequence=sequence,
            settlement=settlement,
            tokens=tokens,
            roots=roots,
            sequence_record=sequence_record,
            witness=witness,
        )
        structure_id = _digest({
            "field_roots": payload["field_roots"],
            "tokens": payload["tokens"],
        })
        episode_id = _digest({
            "causal_intake_id": intake.intake_id,
            "sequence_id": sequence.sequence_id,
            "settlement_receipt_sha256": settlement.authority_receipt_sha256,
            "structure_id": structure_id,
        })
        episode = CausalLanguageEpisode(
            episode_id=episode_id,
            structure_id=structure_id,
            causal_intake_id=intake.intake_id,
            sequence_id=sequence.sequence_id,
            settlement_receipt_sha256=settlement.authority_receipt_sha256,
            tokens=tokens,
            field_roots=roots,
            causal_intake_record=intake.as_record(),
            sequence_record=sequence_record,
            settlement_witness=witness,
            authority_hmac_sha256=_sign(self._episode_key, EPISODE_DOMAIN, payload),
        )
        with self._lock:
            existing = self._working.get(structure_id)
            if existing is not None:
                return EpisodeAdmission("unique", "duplicate_structure", existing, False)
            if len(self._working) >= self._working_capacity:
                return EpisodeAdmission("unknown", "working_capacity_full", None, False)
            prospective = OrderedDict(self._working)
            prospective[structure_id] = episode
            self._state_envelope(prospective, self._constructions, self._ambiguous_families)
            self._working = prospective
        return EpisodeAdmission("unique", "episode_admitted", episode, True)

    @staticmethod
    def _root_map(episode: CausalLanguageEpisode) -> dict[str, object]:
        return dict(episode.field_roots)

    def learn_construction(
        self, episode_structure_ids: tuple[str, ...]
    ) -> LearningResult:
        if (
            not isinstance(episode_structure_ids, tuple)
            or len(episode_structure_ids) < 2
            or len(set(episode_structure_ids)) != len(episode_structure_ids)
        ):
            raise ValueError("construction learning requires distinct episode structures")
        with self._lock:
            try:
                episodes = tuple(self._working[value] for value in episode_structure_ids)
            except KeyError:
                return LearningResult("unknown", "episode_not_available")
            return self._learn_locked(episodes)

    def _learn_locked(
        self, episodes: tuple[CausalLanguageEpisode, ...]
    ) -> LearningResult:
        lengths = {len(value.tokens) for value in episodes}
        if len(lengths) != 1:
            return LearningResult("unknown", "token_cardinality_changed")
        token_count = next(iter(lengths))
        if not 0 < token_count <= MAX_TOKEN_OCCURRENCES_PER_SEQUENCE:
            return LearningResult("unknown", "token_boundary_invalid")
        variants = tuple(
            {
                episode.tokens[position].token_class_id: episode.tokens[position]
                for episode in episodes
            }
            for position in range(token_count)
        )
        variable_positions = tuple(
            position for position, values in enumerate(variants) if len(values) > 1
        )
        if not variable_positions:
            return LearningResult("unknown", "no_token_contrast")
        roots = tuple(self._root_map(value) for value in episodes)
        root_keys = set(roots[0])
        if any(set(value) != root_keys for value in roots[1:]):
            return LearningResult("unknown", "causal_topology_changed")

        position_roots: dict[int, str] = {}
        for left_index, right_index in itertools.combinations(range(len(episodes)), 2):
            token_changes = tuple(
                position for position in variable_positions
                if episodes[left_index].tokens[position].token_class_id
                != episodes[right_index].tokens[position].token_class_id
            )
            causal_changes = tuple(
                key for key in sorted(root_keys)
                if roots[left_index][key] != roots[right_index][key]
            )
            if not token_changes:
                if causal_changes:
                    return LearningResult("unknown", "unbound_causal_change")
                continue
            if len(token_changes) == 1:
                if len(causal_changes) != 1:
                    return LearningResult("unknown", "causal_contrast_not_unique")
                position = token_changes[0]
                current = position_roots.get(position)
                if current is not None and current != causal_changes[0]:
                    return LearningResult("ambiguous", "slot_referent_conflict")
                position_roots[position] = causal_changes[0]
        if set(position_roots) != set(variable_positions):
            return LearningResult("unknown", "independent_contrast_missing")
        if len(set(position_roots.values())) != len(position_roots):
            return LearningResult("ambiguous", "referent_used_by_multiple_slots")

        for left_index, right_index in itertools.combinations(range(len(episodes)), 2):
            token_changes = {
                position for position in variable_positions
                if episodes[left_index].tokens[position].token_class_id
                != episodes[right_index].tokens[position].token_class_id
            }
            causal_changes = {
                key for key in root_keys if roots[left_index][key] != roots[right_index][key]
            }
            if causal_changes != {position_roots[position] for position in token_changes}:
                return LearningResult("unknown", "causal_contrast_not_one_to_one")

        observed_lattice = {
            tuple(episode.tokens[position].token_class_id for position in variable_positions)
            for episode in episodes
        }
        required_lattice = set(itertools.product(*(
            tuple(sorted(variants[position])) for position in variable_positions
        )))
        if observed_lattice != required_lattice:
            return LearningResult("unknown", "independence_lattice_incomplete")

        slot_roots = set(position_roots.values())
        background_roots = tuple(
            (key, roots[0][key]) for key in sorted(root_keys - slot_roots)
        )
        if any(
            any(root[key] != value for key, value in background_roots)
            for root in roots[1:]
        ):
            return LearningResult("unknown", "background_structure_changed")

        elements = []
        for position in range(token_count):
            if position not in position_roots:
                elements.append(ConstructionElement(
                    ordinal=position,
                    kind="fixed",
                    fixed_token=episodes[0].tokens[position],
                ))
                continue
            referent = position_roots[position]
            by_causal: dict[str, ConstructionAlternative] = {}
            by_token: dict[str, str] = {}
            for episode, root in zip(episodes, roots, strict=True):
                token = episode.tokens[position]
                causal_value = root[referent]
                causal_identity = _digest(causal_value)
                existing = by_causal.get(causal_identity)
                if existing is not None and existing.token != token:
                    return LearningResult("ambiguous", "causal_value_has_conflicting_tokens")
                prior_causal = by_token.get(token.token_class_id)
                if prior_causal is not None and prior_causal != causal_identity:
                    return LearningResult("ambiguous", "token_has_conflicting_causal_values")
                by_causal[causal_identity] = ConstructionAlternative(
                    causal_value_sha256=causal_identity,
                    causal_value=causal_value,
                    token=token,
                )
                by_token[token.token_class_id] = causal_identity
            elements.append(ConstructionElement(
                ordinal=position,
                kind="slot",
                referent_root=referent,
                alternatives=tuple(by_causal[key] for key in sorted(by_causal)),
            ))

        family_id = _digest({
            "background_roots": [[key, value] for key, value in background_roots],
            "slot_roots": sorted(slot_roots),
        })
        proof = tuple(episode.as_record() for episode in episodes)
        provisional = LearnedConstruction(
            construction_id="",
            family_id=family_id,
            state="unique",
            elements=tuple(elements),
            background_roots=background_roots,
            proof_episodes=proof,
            authority_hmac_sha256="",
        )
        payload = provisional.payload()
        construction_id = _digest(_construction_identity_payload(
            family_id=family_id,
            elements=elements,
            background_roots=background_roots,
        ))
        existing = self._constructions.get(construction_id)
        if existing is not None:
            # The construction already retains its minimal proof lattice.
            # Newly admitted structurally identical evidence is redundant,
            # so release it atomically instead of turning repetition into a
            # second episode store.
            prospective_working = OrderedDict(self._working)
            for episode in episodes:
                prospective_working.pop(episode.structure_id, None)
            self._state_envelope(
                prospective_working,
                self._constructions,
                self._ambiguous_families,
            )
            self._working = prospective_working
            return LearningResult(existing.state, "construction_duplicate", existing)
        if len(self._constructions) >= self._construction_capacity:
            return LearningResult("unknown", "construction_capacity_full")

        conflict = family_id in self._ambiguous_families or any(
            value.family_id == family_id for value in self._constructions.values()
        )
        state = "ambiguous" if conflict else "unique"
        construction = LearnedConstruction(
            construction_id=construction_id,
            family_id=family_id,
            state=state,
            elements=tuple(elements),
            background_roots=background_roots,
            proof_episodes=proof,
            authority_hmac_sha256=_sign(self._construction_key, CONSTRUCTION_DOMAIN, payload),
        )
        prospective_constructions = OrderedDict(self._constructions)
        prospective_ambiguous = set(self._ambiguous_families)
        if conflict:
            prospective_ambiguous.add(family_id)
            for key, value in tuple(prospective_constructions.items()):
                if value.family_id == family_id and value.state != "ambiguous":
                    prospective_constructions[key] = replace(value, state="ambiguous")
        prospective_constructions[construction_id] = construction
        prospective_working = OrderedDict(self._working)
        for episode in episodes:
            prospective_working.pop(episode.structure_id, None)
        self._state_envelope(
            prospective_working, prospective_constructions, prospective_ambiguous
        )
        self._working = prospective_working
        self._constructions = prospective_constructions
        self._ambiguous_families = prospective_ambiguous
        return LearningResult(
            state,
            "construction_conflict" if conflict else "construction_learned",
            construction,
        )

    @staticmethod
    def _match_background(
        construction: LearnedConstruction, roots: Mapping[str, object]
    ) -> bool:
        return all(roots.get(key) == value for key, value in construction.background_roots)

    def generate(
        self, settlement: CausalExperienceSettlement
    ) -> LanguageResolution:
        if not isinstance(settlement, CausalExperienceSettlement):
            raise TypeError("causal language generation requires a settlement")
        settlement.verify()
        roots = dict(_field_roots(_settlement_witness(settlement)))
        matches = []
        with self._lock:
            constructions = tuple(self._constructions.values())
        for construction in constructions:
            if construction.state != "unique" or not self._match_background(construction, roots):
                continue
            tokens = []
            referents = []
            valid = True
            for element in construction.elements:
                if element.kind == "fixed":
                    tokens.append(element.fixed_token)
                    continue
                value = roots.get(element.referent_root)
                identity = _digest(value) if value is not None else None
                alternatives = [
                    item for item in element.alternatives
                    if item.causal_value_sha256 == identity and item.causal_value == value
                ]
                if len(alternatives) != 1:
                    valid = False
                    break
                tokens.append(alternatives[0].token)
                referents.append((element.referent_root, identity))
            if valid:
                matches.append((construction, tuple(tokens), tuple(referents)))
        if not matches:
            return LanguageResolution("unknown", "no_unique_construction")
        if len(matches) != 1:
            return LanguageResolution("ambiguous", "multiple_constructions")
        construction, tokens, referents = matches[0]
        return LanguageResolution(
            "unique", "construction_generated", construction.construction_id,
            tokens, referents,
        )

    def comprehend(
        self,
        *,
        token_authority: AuditoryTokenSequenceAuthority,
        sequence: AuditoryTokenSequenceReceipt,
        settlement: CausalExperienceSettlement,
    ) -> LanguageResolution:
        token_authority.verify_sequence(sequence)
        settlement.verify()
        tokens = _unique_tokens(sequence)
        if tokens is None:
            return LanguageResolution("unknown", "token_classification_not_unique")
        generated = self.generate(settlement)
        if generated.state != "unique":
            return generated
        if tuple(value.token_class_id for value in generated.tokens) != tuple(
            value.token_class_id for value in tokens
        ):
            return LanguageResolution("unknown", "sequence_causal_relation_disagrees")
        return LanguageResolution(
            "unique", "construction_comprehended", generated.construction_id,
            tokens, generated.referents,
        )

    def _state_payload(
        self,
        working: Mapping[str, CausalLanguageEpisode],
        constructions: Mapping[str, LearnedConstruction],
        ambiguous_families: set[str],
    ) -> dict[str, object]:
        return {
            "ambiguous_families": sorted(ambiguous_families),
            "construction_capacity": self._construction_capacity,
            "constructions": [constructions[key].as_record() for key in sorted(constructions)],
            "schema": STATE_SCHEMA,
            "working": [working[key].as_record() for key in sorted(working)],
            "working_capacity": self._working_capacity,
        }

    def _state_envelope(
        self,
        working: Mapping[str, CausalLanguageEpisode],
        constructions: Mapping[str, LearnedConstruction],
        ambiguous_families: set[str],
    ) -> dict[str, object]:
        payload = self._state_payload(working, constructions, ambiguous_families)
        envelope = {
            "authority_hmac_sha256": _sign(self._state_key, STATE_DOMAIN, payload),
            "payload": payload,
            "schema": ENVELOPE_SCHEMA,
        }
        if len(_canonical(envelope)) > self._max_state_bytes:
            raise RuntimeError("causal language state capacity is full")
        return envelope

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return self._state_envelope(
                self._working, self._constructions, self._ambiguous_families
            )

    def verify_episode_record(
        self, record: object
    ) -> CausalLanguageEpisode:
        """Reverify one immutable episode record without retaining it."""

        return self._episode_from_record(record)

    def restore(self, snapshot: object) -> None:
        if (
            not isinstance(snapshot, Mapping)
            or set(snapshot) != {"authority_hmac_sha256", "payload", "schema"}
            or snapshot.get("schema") != ENVELOPE_SCHEMA
        ):
            raise ValueError("causal language state envelope is malformed")
        if len(_canonical(snapshot)) > self._max_state_bytes:
            raise ValueError("causal language state exceeds its byte boundary")
        payload = snapshot.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("causal language state payload is malformed")
        signature = _sha256(snapshot.get("authority_hmac_sha256"), "state HMAC")
        if not hmac.compare_digest(signature, _sign(self._state_key, STATE_DOMAIN, payload)):
            raise ValueError("causal language state authority changed")
        expected = {
            "ambiguous_families", "construction_capacity", "constructions",
            "schema", "working", "working_capacity",
        }
        if set(payload) != expected or payload.get("schema") != STATE_SCHEMA:
            raise ValueError("causal language state fields changed")
        if (
            payload.get("working_capacity") != self._working_capacity
            or payload.get("construction_capacity") != self._construction_capacity
        ):
            raise ValueError("causal language state capacities changed")
        raw_working = payload.get("working")
        raw_constructions = payload.get("constructions")
        raw_ambiguous = payload.get("ambiguous_families")
        if (
            not isinstance(raw_working, list)
            or len(raw_working) > self._working_capacity
            or not isinstance(raw_constructions, list)
            or len(raw_constructions) > self._construction_capacity
            or not isinstance(raw_ambiguous, list)
        ):
            raise ValueError("causal language state collections changed")
        working = OrderedDict()
        for record in raw_working:
            episode = self._episode_from_record(record)
            if episode.structure_id in working:
                raise ValueError("causal language state repeats a working episode")
            working[episode.structure_id] = episode
        constructions = OrderedDict()
        for record in raw_constructions:
            construction = self._construction_from_record(record)
            if construction.construction_id in constructions:
                raise ValueError("causal language state repeats a construction")
            constructions[construction.construction_id] = construction
        ambiguous = {_sha256(value, "ambiguous family") for value in raw_ambiguous}
        if any(
            value.family_id in ambiguous and value.state != "ambiguous"
            for value in constructions.values()
        ):
            raise ValueError("ambiguous family retained a unique construction")
        canonical = self._state_envelope(working, constructions, ambiguous)
        if _canonical(canonical) != _canonical(snapshot):
            raise ValueError("causal language state is not canonical")
        with self._lock:
            self._working = working
            self._constructions = constructions
            self._ambiguous_families = ambiguous

    def _episode_from_record(self, record: object) -> CausalLanguageEpisode:
        if not isinstance(record, Mapping):
            raise ValueError("causal language episode record is malformed")
        tokens = tuple(_token_from_record(value) for value in record.get("tokens", ()))
        roots = tuple((str(value[0]), value[1]) for value in record.get("field_roots", ()))
        episode = CausalLanguageEpisode(
            episode_id=_sha256(record.get("episode_id"), "episode id"),
            structure_id=_sha256(record.get("structure_id"), "episode structure"),
            causal_intake_id=_sha256(
                record.get("causal_intake_id"), "episode causal intake"
            ),
            sequence_id=_sha256(record.get("sequence_id"), "episode sequence"),
            settlement_receipt_sha256=_sha256(
                record.get("settlement_receipt_sha256"), "episode settlement"
            ),
            tokens=tokens,
            field_roots=roots,
            causal_intake_record=dict(record.get("causal_intake_record") or {}),
            sequence_record=dict(record.get("sequence_record") or {}),
            settlement_witness=dict(record.get("settlement_witness") or {}),
            authority_hmac_sha256=_sha256(record.get("authority_hmac_sha256"), "episode HMAC"),
        )
        payload = {
            key: value for key, value in episode.as_record().items()
            if key not in {"authority_hmac_sha256", "episode_id", "structure_id"}
        }
        if not hmac.compare_digest(
            episode.authority_hmac_sha256,
            _sign(self._episode_key, EPISODE_DOMAIN, payload),
        ):
            raise ValueError("causal language episode authority changed")
        expected_structure = _digest({
            "field_roots": payload["field_roots"], "tokens": payload["tokens"]
        })
        if (
            episode.causal_intake_record.get("intake_id")
            != episode.causal_intake_id
        ):
            raise ValueError("causal language episode intake identity changed")
        expected_episode = _digest({
            "causal_intake_id": episode.causal_intake_id,
            "sequence_id": episode.sequence_id,
            "settlement_receipt_sha256": episode.settlement_receipt_sha256,
            "structure_id": expected_structure,
        })
        if episode.structure_id != expected_structure or episode.episode_id != expected_episode:
            raise ValueError("causal language episode identity changed")
        return episode

    def _construction_from_record(self, record: object) -> LearnedConstruction:
        if not isinstance(record, Mapping):
            raise ValueError("causal language construction record is malformed")
        elements = []
        for raw in record.get("elements", ()):
            if not isinstance(raw, Mapping):
                raise ValueError("construction element record changed")
            fixed = raw.get("fixed_token")
            alternatives = tuple(
                ConstructionAlternative(
                    causal_value_sha256=_sha256(
                        value.get("causal_value_sha256"), "causal alternative"
                    ),
                    causal_value=value.get("causal_value"),
                    token=_token_from_record(value.get("token")),
                )
                for value in raw.get("alternatives", ())
            )
            elements.append(ConstructionElement(
                ordinal=raw.get("ordinal"),
                kind=raw.get("kind"),
                fixed_token=_token_from_record(fixed) if fixed is not None else None,
                referent_root=raw.get("referent_root"),
                alternatives=alternatives,
            ))
        construction = LearnedConstruction(
            construction_id=_sha256(record.get("construction_id"), "construction id"),
            family_id=_sha256(record.get("family_id"), "construction family"),
            state=record.get("state"),
            elements=tuple(elements),
            background_roots=tuple(
                (str(value[0]), value[1]) for value in record.get("background_roots", ())
            ),
            proof_episodes=tuple(dict(value) for value in record.get("proof_episodes", ())),
            authority_hmac_sha256=_sha256(
                record.get("authority_hmac_sha256"), "construction HMAC"
            ),
        )
        if construction.state not in {"unique", "ambiguous"}:
            raise ValueError("construction state changed")
        payload = construction.payload()
        # State can become ambiguous after the original proof is signed.  The
        # proof HMAC authenticates the immutable unique payload; family state
        # is authenticated by the outer state envelope.
        signed_payload = {**payload, "state": "unique"}
        if (
            construction.construction_id != _digest(
                _construction_identity_payload(
                    family_id=construction.family_id,
                    elements=construction.elements,
                    background_roots=construction.background_roots,
                )
            )
            or not hmac.compare_digest(
                construction.authority_hmac_sha256,
                _sign(self._construction_key, CONSTRUCTION_DOMAIN, signed_payload),
            )
        ):
            raise ValueError("causal language construction authority changed")
        return construction


__all__ = [
    "CausalLanguageConstructionAuthority",
    "CausalLanguageEpisode",
    "ConstructionAlternative",
    "ConstructionElement",
    "ConstructionToken",
    "EpisodeAdmission",
    "LanguageResolution",
    "LearnedConstruction",
    "LearningResult",
]
