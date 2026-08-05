"""Receipt-driven autonomous experience and truthful internal re-entry.

The driver advances only work carrying an authenticated source receipt.  It
has no clock-driven cognition path.  Internal dreams re-enter by verifying
already committed full-field neuron assemblies and whole-organism episodes;
all mounted receptor families remain explicitly quiescent, no external event
is claimed, and neurochemical state is not advanced.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass
from typing import Callable, Mapping

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.organism_dream_wake_weave import (
    OrganismDreamRecord,
    OrganismOrderedDreamRecord,
    OrganismDreamWakeWeaveOwner,
)
from dsf_ai_service.substrate.organism_ordered_lived_experience import (
    OrganismOrderedLivedExperienceOwner,
)
from dsf_ai_service.substrate.passive_whole_organism_thing_learning import (
    PassiveWholeOrganismThingLearningOwner,
)
from dsf_ai_service.substrate.whole_organism_episode import (
    DownstreamAuthority,
    MechanismKind,
    WholeOrganismEpisodeAuthority,
)
from dsf_ai_service.substrate.whole_organism_neuron_population import (
    WholeOrganismNeuronPopulationOwner,
)
from dsf_ai_service.substrate.whole_organism_thing_mosaic_learning import (
    WholeOrganismThingMosaicLearningOwner,
)
from dsf_ai_service.substrate.causal_mosaic_tapestry import (
    CausalMosaicTapestryOwner,
)


WORK_SCHEMA = "guala.autonomous_experience.work.v1"
COMPLETION_SCHEMA = "guala.autonomous_experience.completion.v1"
DRIVER_STATE_SCHEMA = "guala.autonomous_experience.driver_state.v1"
DRIVER_ENVELOPE_SCHEMA = "guala.autonomous_experience.driver_state_hmac.v1"
INTERNAL_REENTRY_SCHEMA = "guala.whole_organism.internal_reentry.v1"
INTERNAL_REENTRY_STATE_SCHEMA = (
    "guala.whole_organism.internal_reentry_state.v1"
)
INTERNAL_REENTRY_ENVELOPE_SCHEMA = (
    "guala.whole_organism.internal_reentry_state_hmac.v1"
)

WORK_KINDS = frozenset({
    "causal_settlement",
    "internal_dream",
    "action_intent",
    "action_execution",
    "body_evolution",
})

_WORK_DOMAIN = b"guala-autonomous-experience-work-v1\0"
_COMPLETION_DOMAIN = b"guala-autonomous-experience-completion-v1\0"
_DRIVER_STATE_DOMAIN = b"guala-autonomous-experience-driver-state-v1\0"
_REENTRY_DOMAIN = b"guala-whole-organism-internal-reentry-v1\0"
_REENTRY_STATE_DOMAIN = b"guala-whole-organism-internal-reentry-state-v1\0"
_HEX = frozenset("0123456789abcdef")


class InternalReentryCustodyUnavailable(RuntimeError):
    """A dream cannot re-enter because exact retained custody is absent."""


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
        raise ValueError("autonomous-experience authority key changed")
    return hashlib.sha256(domain + raw).digest()


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _positive(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be positive")
    return value


@dataclass(frozen=True, slots=True)
class AutonomousExperienceWork:
    kind: str
    source_receipt_sha256: str
    dependency_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "dependency_receipt_sha256s": list(
                self.dependency_receipt_sha256s
            ),
            "kind": self.kind,
            "schema": WORK_SCHEMA,
            "source_receipt_sha256": self.source_receipt_sha256,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class AutonomousExperienceCompletion:
    work_receipt_sha256: str
    output_receipt_sha256s: tuple[str, ...]
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "output_receipt_sha256s": list(
                self.output_receipt_sha256s
            ),
            "schema": COMPLETION_SCHEMA,
            "work_receipt_sha256": self.work_receipt_sha256,
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


@dataclass(frozen=True, slots=True)
class WholeOrganismInternalReentry:
    dream_receipt_sha256: str
    manifest_receipt_sha256: str
    source_tapestry_receipt_sha256s: tuple[str, ...]
    source_relation_receipt_sha256s: tuple[str, ...]
    source_episode_receipt_sha256s: tuple[str, ...]
    source_learning_receipt_sha256s: tuple[str, ...]
    neuron_mosaic_assembly_receipt_sha256s: tuple[str, ...]
    full_field_root_receipt_sha256s: tuple[str, ...]
    receptor_states: tuple[tuple[str, str], ...]
    external_event_claimed: bool
    neurochemical_advanced: bool
    reduced_approximation: bool
    authority_hmac_sha256: str
    authority_receipt_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "dream_receipt_sha256": self.dream_receipt_sha256,
            "external_event_claimed": self.external_event_claimed,
            "full_field_root_receipt_sha256s": list(
                self.full_field_root_receipt_sha256s
            ),
            "manifest_receipt_sha256": self.manifest_receipt_sha256,
            "neurochemical_advanced": self.neurochemical_advanced,
            "neuron_mosaic_assembly_receipt_sha256s": list(
                self.neuron_mosaic_assembly_receipt_sha256s
            ),
            "receptor_states": [
                {"mechanism_id": mechanism_id, "state": state}
                for mechanism_id, state in self.receptor_states
            ],
            "reduced_approximation": self.reduced_approximation,
            "schema": INTERNAL_REENTRY_SCHEMA,
            "source_episode_receipt_sha256s": list(
                self.source_episode_receipt_sha256s
            ),
            "source_learning_receipt_sha256s": list(
                self.source_learning_receipt_sha256s
            ),
            "source_relation_receipt_sha256s": list(
                self.source_relation_receipt_sha256s
            ),
            "source_tapestry_receipt_sha256s": list(
                self.source_tapestry_receipt_sha256s
            ),
        }

    def record(self) -> dict[str, object]:
        return self.payload() | {
            "authority_hmac_sha256": self.authority_hmac_sha256,
            "authority_receipt_sha256": self.authority_receipt_sha256,
        }


class WholeOrganismInternalReentryAuthority:
    """Seal internal re-entry without asserting new receptor perturbation."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        dream_owner: OrganismDreamWakeWeaveOwner,
        tapestry_owner: CausalMosaicTapestryOwner,
        learning_owner: WholeOrganismThingMosaicLearningOwner,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
        episode_authority: WholeOrganismEpisodeAuthority,
        ordered_lived_experience_owner: (
            OrganismOrderedLivedExperienceOwner | None
        ) = None,
        passive_learning_owner: (
            PassiveWholeOrganismThingLearningOwner | None
        ) = None,
        max_records: int = 64,
        max_state_bytes: int = 4 * 1024 * 1024,
    ) -> None:
        if not isinstance(dream_owner, OrganismDreamWakeWeaveOwner):
            raise TypeError("internal re-entry dream owner is not typed")
        if not isinstance(tapestry_owner, CausalMosaicTapestryOwner):
            raise TypeError("internal re-entry tapestry owner is not typed")
        if not isinstance(
            learning_owner,
            WholeOrganismThingMosaicLearningOwner,
        ):
            raise TypeError("internal re-entry learning owner is not typed")
        if not isinstance(
            neuron_owner,
            WholeOrganismNeuronPopulationOwner,
        ):
            raise TypeError("internal re-entry neuron owner is not typed")
        if not isinstance(
            episode_authority,
            WholeOrganismEpisodeAuthority,
        ):
            raise TypeError("internal re-entry episode owner is not typed")
        self._record_key = _key(authority_key, _REENTRY_DOMAIN)
        self._state_key = _key(authority_key, _REENTRY_STATE_DOMAIN)
        self._dreams = dream_owner
        self._tapestries = tapestry_owner
        self._learning = learning_owner
        self._neurons = neuron_owner
        self._episodes = episode_authority
        self._ordered = ordered_lived_experience_owner
        self._passive = passive_learning_owner
        self._max_records = _positive(max_records, "internal re-entry capacity")
        self._max_state_bytes = _positive(
            max_state_bytes,
            "internal re-entry byte capacity",
        )
        self._records: dict[str, WholeOrganismInternalReentry] = {}
        self._lock = threading.RLock()
        if (
            ordered_lived_experience_owner is None
        ) != (passive_learning_owner is None):
            raise ValueError(
                "ordered internal re-entry source owners must bind together"
            )
        if ordered_lived_experience_owner is not None:
            self._verify_current_owner_graph(
                dream_owner=dream_owner,
                ordered_lived_experience_owner=(
                    ordered_lived_experience_owner
                ),
                passive_learning_owner=passive_learning_owner,
            )
        self._encoded_locked()

    @property
    def records(self) -> tuple[WholeOrganismInternalReentry, ...]:
        with self._lock:
            return tuple(
                self._records[receipt] for receipt in sorted(self._records)
            )

    def _verify_current_owner_graph(
        self,
        *,
        dream_owner: OrganismDreamWakeWeaveOwner,
        ordered_lived_experience_owner: (
            OrganismOrderedLivedExperienceOwner
        ),
        passive_learning_owner: (
            PassiveWholeOrganismThingLearningOwner
        ),
    ) -> None:
        if not isinstance(dream_owner, OrganismDreamWakeWeaveOwner):
            raise TypeError("internal re-entry dream owner is not typed")
        if not isinstance(
            ordered_lived_experience_owner,
            OrganismOrderedLivedExperienceOwner,
        ):
            raise TypeError(
                "internal re-entry ordered owner is not typed"
            )
        if not isinstance(
            passive_learning_owner,
            PassiveWholeOrganismThingLearningOwner,
        ):
            raise TypeError(
                "internal re-entry passive owner is not typed"
            )
        custody = ordered_lived_experience_owner._source_custody
        if custody is None:
            raise ValueError(
                "internal re-entry ordered owner lacks source custody"
            )
        custody.verify()
        if (
            custody.episode_authority is not self._episodes
            or custody.passive_learning_owner
            is not passive_learning_owner
            or custody.consequence_learning_owner is not self._learning
            or getattr(passive_learning_owner, "_neurons", None)
            is not self._neurons
            or getattr(self._learning, "_neurons", None)
            is not self._neurons
            or getattr(self._learning, "_episodes", None)
            is not self._episodes
            or getattr(
                dream_owner,
                "_ordered_lived_experience_owner",
                None,
            )
            is not ordered_lived_experience_owner
        ):
            raise ValueError(
                "internal re-entry current owner graph crossed custody"
            )

    def rebind_current_owners(
        self,
        *,
        dream_owner: OrganismDreamWakeWeaveOwner,
        ordered_lived_experience_owner: (
            OrganismOrderedLivedExperienceOwner
        ),
        passive_learning_owner: (
            PassiveWholeOrganismThingLearningOwner
        ),
    ) -> None:
        """Atomically bind restored current owners after owner replacement."""

        with self._lock:
            self._verify_current_owner_graph(
                dream_owner=dream_owner,
                ordered_lived_experience_owner=(
                    ordered_lived_experience_owner
                ),
                passive_learning_owner=passive_learning_owner,
            )
            prior = (self._dreams, self._ordered, self._passive)
            self._dreams = dream_owner
            self._ordered = ordered_lived_experience_owner
            self._passive = passive_learning_owner
            try:
                for record in self._records.values():
                    dream = self._retained_dream(
                        record.dream_receipt_sha256
                    )
                    self._verify_retained_source_record(record, dream)
            except BaseException:
                self._dreams, self._ordered, self._passive = prior
                raise

    def rebind_whole_organism_authorities(
        self,
        *,
        learning_owner: WholeOrganismThingMosaicLearningOwner,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
        episode_authority: WholeOrganismEpisodeAuthority,
    ) -> None:
        """Rebind equivalent restored whole-organism authorities atomically."""

        if not isinstance(
            learning_owner,
            WholeOrganismThingMosaicLearningOwner,
        ):
            raise TypeError("internal re-entry learning owner is not typed")
        if not isinstance(
            neuron_owner,
            WholeOrganismNeuronPopulationOwner,
        ):
            raise TypeError("internal re-entry neuron owner is not typed")
        if not isinstance(
            episode_authority,
            WholeOrganismEpisodeAuthority,
        ):
            raise TypeError("internal re-entry episode owner is not typed")
        with self._lock:
            prior = (self._learning, self._neurons, self._episodes)
            self._learning = learning_owner
            self._neurons = neuron_owner
            self._episodes = episode_authority
            try:
                if self._ordered is not None:
                    self._verify_current_owner_graph(
                        dream_owner=self._dreams,
                        ordered_lived_experience_owner=self._ordered,
                        passive_learning_owner=self._passive,
                    )
                for record in self._records.values():
                    dream = self._retained_dream(
                        record.dream_receipt_sha256
                    )
                    self._verify_retained_source_record(record, dream)
            except BaseException:
                self._learning, self._neurons, self._episodes = prior
                raise

    def _retained_dream(
        self,
        receipt_sha256: str,
    ) -> OrganismDreamRecord | OrganismOrderedDreamRecord:
        _sha(receipt_sha256, "internal re-entry dream")
        with self._dreams._lock:
            ordered = self._dreams._ordered_dreams.get(
                receipt_sha256
            )
            if ordered is not None:
                self._ordered_sources(ordered)
            dream = self._dreams._retained_dream_locked(
                receipt_sha256
            )
        if dream is None:
            raise ValueError("internal re-entry dream is not retained")
        if (
            dream.external_event_claimed
            or dream.external_embodiment_state != "quiescent"
            or dream.origin.value != "internally_simulated"
        ):
            raise ValueError("internal re-entry dream provenance changed")
        return dream

    @staticmethod
    def _root_receipt(root: object) -> str:
        root.verify()
        evidence = json.loads(root.full_evidence_json)
        tuples = evidence.get("field_tuples")
        if not isinstance(tuples, list) or not tuples:
            raise ValueError("internal re-entry root lost its field tuples")
        for item in tuples:
            fields = item.get("fields") if isinstance(item, Mapping) else None
            if (
                not isinstance(fields, list)
                or tuple(value[0] for value in fields)
                != DSF_FIELD_ORDER
            ):
                raise ValueError(
                    "internal re-entry root flattened its DSF field"
                )
        return _digest(root.record())

    def _required_sources(
        self,
        dream: OrganismDreamRecord | OrganismOrderedDreamRecord,
    ) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        if isinstance(dream, OrganismDreamRecord):
            tapestries = tuple(
                self._tapestries.require_settled_tapestry(receipt)
                for receipt in dream.source_tapestry_receipt_sha256s
            )
            learning_receipts = tuple(sorted({
                receipt
                for tapestry in tapestries
                for receipt in (
                    tapestry.observation.source_learning_receipt_sha256,
                    tapestry.observation.target_learning_receipt_sha256,
                )
            }))
            episode_receipts = tuple(sorted({
                receipt
                for tapestry in tapestries
                for receipt in (
                    tapestry.observation.source_episode_receipt_sha256,
                    tapestry.observation.target_episode_receipt_sha256,
                )
            }))
            root_receipts = tuple(sorted({
                self._root_receipt(root)
                for tapestry in tapestries
                for root in tapestry.full_field_roots
            }))
            return learning_receipts, episode_receipts, root_receipts

        required_roots = tuple(sorted({
            receipt
            for transition in dream.transitions
            for receipt in (
                *transition.source_full_field_root_receipt_sha256s,
                *transition.target_full_field_root_receipt_sha256s,
            )
        }))
        return (), (), required_roots

    def _ordered_sources(
        self,
        dream: OrganismOrderedDreamRecord,
    ) -> tuple[
        tuple[tuple[object, str, str], ...],
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        ordered = self._ordered
        passive = self._passive
        if ordered is None or passive is None:
            raise InternalReentryCustodyUnavailable(
                "ordered internal re-entry source owners are unbound"
            )
        if (
            dream.chronology_authority_receipt_sha256
            != ordered.chronology_authority_receipt_sha256
        ):
            raise ValueError(
                "ordered internal re-entry crossed chronology authority"
            )
        transition_occurrences = tuple(
            receipt
            for transition in dream.transitions
            for receipt in (
                transition.source_occurrence_receipt_sha256,
                transition.target_occurrence_receipt_sha256,
            )
        )
        if (
            not dream.source_occurrence_receipt_sha256s
            or dream.source_occurrence_receipt_sha256s
            != transition_occurrences
        ):
            raise ValueError(
                "ordered internal re-entry occurrence custody changed"
            )
        occurrences = tuple(ordered.occurrences)
        occurrence_by_receipt = {
            value.authority_receipt_sha256: value
            for value in occurrences
        }
        if len(occurrence_by_receipt) != len(occurrences):
            raise ValueError(
                "ordered internal re-entry occurrence custody repeats"
            )
        passive_records = tuple(passive.records)
        consequence_records = tuple(self._learning.records)
        selected: list[tuple[object, str, str]] = []
        for receipt in dream.source_occurrence_receipt_sha256s:
            occurrence = occurrence_by_receipt.get(receipt)
            if occurrence is None:
                raise InternalReentryCustodyUnavailable(
                    "ordered internal re-entry occurrence is not retained"
                )
            ordered._evidence.verify(occurrence)
            records = (
                passive_records
                if occurrence.learning_kind == "passive"
                else consequence_records
            )
            matches = tuple(
                record
                for record in records
                if record.authority_receipt_sha256
                == occurrence.learning_receipt_sha256
            )
            if not matches:
                raise InternalReentryCustodyUnavailable(
                    "ordered internal re-entry learning is not retained"
                )
            if len(matches) != 1:
                raise ValueError(
                    "ordered internal re-entry learning custody repeats"
                )
            record = matches[0]
            if occurrence.learning_kind == "passive":
                settlement_receipt = (
                    record.story.settlement_authority_receipt_sha256
                )
            elif occurrence.learning_kind == "consequence":
                settlement_receipt = (
                    record.partition.settlement_receipt_sha256
                )
                if (
                    record.story.episode_authority_receipt_sha256
                    != occurrence.episode_receipt_sha256
                ):
                    raise ValueError(
                        "ordered internal re-entry crossed learned episode"
                    )
            else:
                raise ValueError(
                    "ordered internal re-entry learning kind changed"
                )
            if (
                record.thing_id != occurrence.thing_id
                or record.story.source_occurrence_id
                != occurrence.source_occurrence_id
                or record.full_field_roots != occurrence.full_field_roots
                or settlement_receipt
                != occurrence.settlement_receipt_sha256
            ):
                raise ValueError(
                    "ordered internal re-entry crossed learned occurrence"
                )
            episode_matches = tuple(
                episode
                for episode in self._episodes.episodes
                if episode.authority_receipt_sha256
                == occurrence.episode_receipt_sha256
            )
            if not episode_matches:
                raise InternalReentryCustodyUnavailable(
                    "ordered internal re-entry episode is not retained"
                )
            if len(episode_matches) != 1:
                raise ValueError(
                    "ordered internal re-entry episode custody repeats"
                )
            selected.append((
                record,
                occurrence.episode_receipt_sha256,
                settlement_receipt,
            ))
        required_roots = tuple(sorted({
            receipt
            for transition in dream.transitions
            for receipt in (
                *transition.source_full_field_root_receipt_sha256s,
                *transition.target_full_field_root_receipt_sha256s,
            )
        }))
        observed_roots = {
            self._root_receipt(root)
            for occurrence_receipt in set(
                dream.source_occurrence_receipt_sha256s
            )
            for root in occurrence_by_receipt[
                occurrence_receipt
            ].full_field_roots
        }
        if set(required_roots) != observed_roots:
            raise ValueError(
                "ordered internal re-entry root custody changed"
            )
        return (
            tuple(selected),
            tuple(sorted({
                occurrence_by_receipt[receipt].learning_receipt_sha256
                for receipt in dream.source_occurrence_receipt_sha256s
            })),
            tuple(sorted({
                occurrence_by_receipt[receipt].episode_receipt_sha256
                for receipt in dream.source_occurrence_receipt_sha256s
            })),
            required_roots,
        )

    def _verified_source_custody(
        self,
        dream: OrganismDreamRecord | OrganismOrderedDreamRecord,
    ) -> tuple[
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        if isinstance(dream, OrganismOrderedDreamRecord):
            (
                selected,
                required_learning,
                required_episodes,
                required_roots,
            ) = self._ordered_sources(dream)
        else:
            (
                required_learning,
                required_episodes,
                required_roots,
            ) = self._required_sources(dream)
            learning_by_receipt = {
                record.authority_receipt_sha256: record
                for record in self._learning.records
            }
            records = tuple(
                learning_by_receipt.get(receipt)
                for receipt in required_learning
            )
            if any(record is None for record in records):
                raise InternalReentryCustodyUnavailable(
                    "internal re-entry learning custody is not retained"
                )
            selected = tuple(
                (
                    record,
                    record.story.episode_authority_receipt_sha256,
                    record.partition.settlement_receipt_sha256,
                )
                for record in records
            )

        assemblies = []
        observed_roots = set()
        observed_episodes = set()
        for record, episode_receipt, settlement_receipt in selected:
            assembly = record.neuron_mosaic_assembly
            self._neurons.verify_mosaic_assembly(
                assembly,
                expected_roots=record.full_field_roots,
                expected_settlement_receipt_sha256=settlement_receipt,
            )
            assemblies.append(assembly.authority_receipt_sha256)
            observed_roots.update(
                self._root_receipt(root)
                for root in record.full_field_roots
            )
            episode_matches = tuple(
                episode
                for episode in self._episodes.episodes
                if episode.authority_receipt_sha256 == episode_receipt
            )
            if not episode_matches:
                raise InternalReentryCustodyUnavailable(
                    "internal re-entry episode custody is not retained"
                )
            if len(episode_matches) != 1:
                raise ValueError(
                    "internal re-entry episode custody repeats"
                )
            capability = self._episodes.capability_for(episode_receipt)
            episode = self._episodes.require(
                capability,
                DownstreamAuthority.LEARNING,
            )
            if (
                episode != episode_matches[0]
                or episode.full_field_roots != record.full_field_roots
                or episode.settlement_authority_receipt_sha256
                != settlement_receipt
            ):
                raise ValueError(
                    "internal re-entry crossed whole-organism episode"
                )
            observed_episodes.add(episode_receipt)
        if (
            set(required_roots) != observed_roots
            or set(required_episodes) != observed_episodes
        ):
            raise ValueError("internal re-entry source field changed")
        return (
            required_learning,
            required_episodes,
            required_roots,
            tuple(sorted(set(assemblies))),
        )

    def _verify_retained_source_record(
        self,
        record: WholeOrganismInternalReentry,
        dream: OrganismDreamRecord | OrganismOrderedDreamRecord,
    ) -> None:
        (
            required_learning,
            required_episodes,
            required_roots,
            assemblies,
        ) = self._verified_source_custody(dream)
        if (
            record.manifest_receipt_sha256
            != self._episodes.manifest.authority_receipt_sha256
            or record.source_tapestry_receipt_sha256s
            != (
                dream.source_tapestry_receipt_sha256s
                if isinstance(dream, OrganismDreamRecord)
                else ()
            )
            or record.source_relation_receipt_sha256s
            != dream.source_relation_receipt_sha256s
            or record.source_episode_receipt_sha256s
            != required_episodes
            or record.source_learning_receipt_sha256s
            != required_learning
            or record.neuron_mosaic_assembly_receipt_sha256s
            != assemblies
            or record.full_field_root_receipt_sha256s
            != required_roots
        ):
            raise ValueError(
                "internal re-entry retained source custody changed"
            )

    def record_dream(
        self,
        dream_receipt_sha256: str,
    ) -> WholeOrganismInternalReentry:
        with self._lock:
            dream = self._retained_dream(dream_receipt_sha256)
            existing = self._records.get(dream_receipt_sha256)
            if existing is not None:
                self.verify(existing)
                self._verify_retained_source_record(existing, dream)
                return existing
            if len(self._records) >= self._max_records:
                raise RuntimeError("internal re-entry capacity exhausted")

            (
                required_learning,
                required_episodes,
                required_roots,
                assemblies,
            ) = self._verified_source_custody(dream)

            receptor_states = tuple(
                (spec.mechanism_id, "quiescent")
                for spec in self._episodes.manifest.mechanisms
                if spec.kind is MechanismKind.RECEPTOR_FAMILY
            )
            if not receptor_states:
                raise ValueError("internal re-entry has no mounted receptors")
            provisional = WholeOrganismInternalReentry(
                dream_receipt_sha256=dream.authority_receipt_sha256,
                manifest_receipt_sha256=(
                    self._episodes.manifest.authority_receipt_sha256
                ),
                source_tapestry_receipt_sha256s=(
                    dream.source_tapestry_receipt_sha256s
                    if isinstance(dream, OrganismDreamRecord)
                    else ()
                ),
                source_relation_receipt_sha256s=(
                    dream.source_relation_receipt_sha256s
                ),
                source_episode_receipt_sha256s=required_episodes,
                source_learning_receipt_sha256s=required_learning,
                neuron_mosaic_assembly_receipt_sha256s=assemblies,
                full_field_root_receipt_sha256s=required_roots,
                receptor_states=receptor_states,
                external_event_claimed=False,
                neurochemical_advanced=False,
                reduced_approximation=False,
                authority_hmac_sha256="0" * 64,
                authority_receipt_sha256="0" * 64,
            )
            signature = hmac.new(
                self._record_key,
                _REENTRY_DOMAIN + _canonical(provisional.payload()),
                hashlib.sha256,
            ).hexdigest()
            result = WholeOrganismInternalReentry(
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
            self.verify(result)
            self._records[dream_receipt_sha256] = result
            try:
                self._encoded_locked()
            except BaseException:
                del self._records[dream_receipt_sha256]
                raise
            return result

    def verify(self, record: WholeOrganismInternalReentry) -> None:
        if not isinstance(record, WholeOrganismInternalReentry):
            raise TypeError("whole-organism internal re-entry is not typed")
        if (
            record.external_event_claimed
            or record.neurochemical_advanced
            or record.reduced_approximation
            or not record.receptor_states
            or any(state != "quiescent" for _, state in record.receptor_states)
        ):
            raise ValueError("internal re-entry fabricated physical activity")
        for receipt in (
            record.dream_receipt_sha256,
            record.manifest_receipt_sha256,
            *record.source_relation_receipt_sha256s,
            *record.source_episode_receipt_sha256s,
            *record.source_learning_receipt_sha256s,
            *record.neuron_mosaic_assembly_receipt_sha256s,
            *record.full_field_root_receipt_sha256s,
        ):
            _sha(receipt, "internal re-entry custody")
        expected = hmac.new(
            self._record_key,
            _REENTRY_DOMAIN + _canonical(record.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, record.authority_hmac_sha256)
            or record.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": record.payload(),
            })
        ):
            raise ValueError("internal re-entry authority changed")

    def _state_payload_locked(self) -> dict[str, object]:
        return {
            "max_records": self._max_records,
            "max_state_bytes": self._max_state_bytes,
            "records": [
                self._records[receipt].record()
                for receipt in sorted(self._records)
            ],
            "schema": INTERNAL_REENTRY_STATE_SCHEMA,
        }

    def _encoded_locked(self) -> bytes:
        payload = self._state_payload_locked()
        signature = hmac.new(
            self._state_key,
            _REENTRY_STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "authority_hmac_sha256": signature,
            "payload": payload,
            "schema": INTERNAL_REENTRY_ENVELOPE_SCHEMA,
        })
        if len(encoded) > self._max_state_bytes:
            raise RuntimeError("internal re-entry byte capacity exhausted")
        return encoded

    def encoded_snapshot(self) -> bytes:
        with self._lock:
            return self._encoded_locked()

    def status(self) -> dict[str, object]:
        with self._lock:
            latest = (
                self._records[sorted(self._records)[-1]]
                if self._records
                else None
            )
            return {
                "available": True,
                "external_event_claimed": False,
                "latest_authority_receipt_sha256": (
                    latest.authority_receipt_sha256
                    if latest is not None
                    else None
                ),
                "neurochemical_advanced": False,
                "receptor_state": "quiescent",
                "records": len(self._records),
                "record_capacity": self._max_records,
                "reduced_approximation": False,
                "schema": "guala.whole_organism.internal_reentry.status.v1",
                "state_bytes": len(self._encoded_locked()),
                "state_capacity_bytes": self._max_state_bytes,
            }

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        dream_owner: OrganismDreamWakeWeaveOwner,
        tapestry_owner: CausalMosaicTapestryOwner,
        learning_owner: WholeOrganismThingMosaicLearningOwner,
        neuron_owner: WholeOrganismNeuronPopulationOwner,
        episode_authority: WholeOrganismEpisodeAuthority,
        ordered_lived_experience_owner: (
            OrganismOrderedLivedExperienceOwner | None
        ) = None,
        passive_learning_owner: (
            PassiveWholeOrganismThingLearningOwner | None
        ) = None,
        encoded: bytes,
    ) -> "WholeOrganismInternalReentryAuthority":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("internal re-entry cold state is absent")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("internal re-entry cold state is unreadable") from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"authority_hmac_sha256", "payload", "schema"}
            or envelope.get("schema") != INTERNAL_REENTRY_ENVELOPE_SCHEMA
            or not isinstance(envelope.get("payload"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("internal re-entry cold envelope changed")
        payload = envelope["payload"]
        if (
            payload.get("schema") != INTERNAL_REENTRY_STATE_SCHEMA
            or set(payload)
            != {
                "max_records",
                "max_state_bytes",
                "records",
                "schema",
            }
            or not isinstance(payload.get("records"), list)
        ):
            raise ValueError("internal re-entry cold payload changed")
        owner = cls(
            authority_key=authority_key,
            dream_owner=dream_owner,
            tapestry_owner=tapestry_owner,
            learning_owner=learning_owner,
            neuron_owner=neuron_owner,
            episode_authority=episode_authority,
            ordered_lived_experience_owner=(
                ordered_lived_experience_owner
            ),
            passive_learning_owner=passive_learning_owner,
            max_records=payload.get("max_records"),
            max_state_bytes=payload.get("max_state_bytes"),
        )
        expected = hmac.new(
            owner._state_key,
            _REENTRY_STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected,
            envelope.get("authority_hmac_sha256", ""),
        ):
            raise ValueError("internal re-entry cold authority changed")
        for raw in payload["records"]:
            if not isinstance(raw, Mapping):
                raise ValueError("internal re-entry cold record changed")
            restored = owner.record_dream(raw.get("dream_receipt_sha256"))
            if restored.record() != dict(raw):
                raise ValueError("internal re-entry cold record changed")
        if owner.encoded_snapshot() != encoded:
            raise ValueError("internal re-entry cold bytes changed")
        return owner


class AutonomousExperienceDriver:
    """Bounded exact-receipt work owner with one in-flight mutation."""

    def __init__(
        self,
        *,
        authority_key: bytes | str,
        max_records: int = 128,
        max_state_bytes: int = 2 * 1024 * 1024,
    ) -> None:
        root = _key(authority_key, _DRIVER_STATE_DOMAIN)
        self._work_key = hashlib.sha256(_WORK_DOMAIN + root).digest()
        self._completion_key = hashlib.sha256(
            _COMPLETION_DOMAIN + root
        ).digest()
        self._state_key = hashlib.sha256(
            _DRIVER_STATE_DOMAIN + root
        ).digest()
        self._max_records = _positive(max_records, "autonomous work capacity")
        self._max_state_bytes = _positive(
            max_state_bytes,
            "autonomous driver byte capacity",
        )
        self._pending: list[AutonomousExperienceWork] = []
        self._in_flight: AutonomousExperienceWork | None = None
        self._completed: dict[str, AutonomousExperienceCompletion] = {}
        self._failure: dict[str, str] | None = None
        self._handler: (
            Callable[[AutonomousExperienceWork], tuple[str, ...]] | None
        ) = None
        self._transition_scope: Callable[
            [], contextlib.AbstractContextManager[None]
        ] = contextlib.nullcontext
        self._transition_failure: dict[str, object] | None = None
        self._thread: threading.Thread | None = None
        self._started = False
        self._stopped = False
        self._condition = threading.Condition()
        self._encoded_locked()

    def issue_work(
        self,
        *,
        kind: str,
        source_receipt_sha256: str,
        dependency_receipt_sha256s: tuple[str, ...] = (),
    ) -> AutonomousExperienceWork:
        if kind not in WORK_KINDS:
            raise ValueError("autonomous experience work kind changed")
        _sha(source_receipt_sha256, "autonomous work source")
        dependencies = tuple(sorted(set(dependency_receipt_sha256s)))
        for receipt in dependencies:
            _sha(receipt, "autonomous work dependency")
        provisional = AutonomousExperienceWork(
            kind=kind,
            source_receipt_sha256=source_receipt_sha256,
            dependency_receipt_sha256s=dependencies,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._work_key,
            _WORK_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return AutonomousExperienceWork(
            kind=provisional.kind,
            source_receipt_sha256=provisional.source_receipt_sha256,
            dependency_receipt_sha256s=(
                provisional.dependency_receipt_sha256s
            ),
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def verify_work(self, work: AutonomousExperienceWork) -> None:
        if not isinstance(work, AutonomousExperienceWork):
            raise TypeError("autonomous experience work is not typed")
        if work.kind not in WORK_KINDS:
            raise ValueError("autonomous experience work kind changed")
        _sha(work.source_receipt_sha256, "autonomous work source")
        if work.dependency_receipt_sha256s != tuple(
            sorted(set(work.dependency_receipt_sha256s))
        ):
            raise ValueError("autonomous work dependency order changed")
        for receipt in work.dependency_receipt_sha256s:
            _sha(receipt, "autonomous work dependency")
        expected = hmac.new(
            self._work_key,
            _WORK_DOMAIN + _canonical(work.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(expected, work.authority_hmac_sha256)
            or work.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": work.payload(),
            })
        ):
            raise ValueError("autonomous work authority changed")

    def admit(self, work: AutonomousExperienceWork) -> str:
        return self.admit_batch((work,))[0]

    def admit_batch(
        self,
        works: tuple[AutonomousExperienceWork, ...],
    ) -> tuple[str, ...]:
        if not works:
            return ()
        for work in works:
            self.verify_work(work)
        receipts = tuple(
            work.authority_receipt_sha256 for work in works
        )
        if len(set(receipts)) != len(receipts):
            raise ValueError("autonomous work batch repeats a receipt")
        with self._condition:
            if self._stopped:
                raise RuntimeError("autonomous experience admission is closed")
            retained_receipts = {
                *self._completed,
                *(
                    (self._in_flight.authority_receipt_sha256,)
                    if self._in_flight is not None
                    else ()
                ),
                *(
                    value.authority_receipt_sha256
                    for value in self._pending
                ),
            }
            novel = tuple(
                work
                for work in works
                if work.authority_receipt_sha256
                not in retained_receipts
            )
            protected_completed = frozenset(receipts).intersection(
                self._completed
            )
            active = (
                len(self._pending)
                + int(self._in_flight is not None)
            )
            if (
                active + len(novel) + len(protected_completed)
                > self._max_records
            ):
                raise RuntimeError("autonomous experience capacity exhausted")
            completed_capacity = self._max_records - active - len(novel)
            retirement_count = max(
                0,
                len(self._completed) - completed_capacity,
            )
            retired_completed = tuple(
                receipt
                for receipt in self._completed
                if receipt not in protected_completed
            )[:retirement_count]
            if len(retired_completed) != retirement_count:
                raise RuntimeError(
                    "autonomous completed journal cannot retain this batch"
                )
            prior_completed = self._completed.copy()
            for receipt in retired_completed:
                del self._completed[receipt]
            prior_length = len(self._pending)
            self._pending.extend(novel)
            try:
                self._encoded_locked()
            except BaseException:
                del self._pending[prior_length:]
                self._completed = prior_completed
                raise
            self._condition.notify()
            return tuple(
                (
                    "already_completed"
                    if receipt in self._completed
                    else (
                        "already_admitted"
                        if receipt in retained_receipts
                        else "admitted"
                    )
                )
                for receipt in receipts
            )

    def _seal_completion(
        self,
        work: AutonomousExperienceWork,
        outputs: tuple[str, ...],
    ) -> AutonomousExperienceCompletion:
        normalized = tuple(sorted(set(outputs)))
        for receipt in normalized:
            _sha(receipt, "autonomous completion output")
        provisional = AutonomousExperienceCompletion(
            work_receipt_sha256=work.authority_receipt_sha256,
            output_receipt_sha256s=normalized,
            authority_hmac_sha256="0" * 64,
            authority_receipt_sha256="0" * 64,
        )
        signature = hmac.new(
            self._completion_key,
            _COMPLETION_DOMAIN + _canonical(provisional.payload()),
            hashlib.sha256,
        ).hexdigest()
        return AutonomousExperienceCompletion(
            work_receipt_sha256=provisional.work_receipt_sha256,
            output_receipt_sha256s=provisional.output_receipt_sha256s,
            authority_hmac_sha256=signature,
            authority_receipt_sha256=_digest({
                "authority_hmac_sha256": signature,
                "payload": provisional.payload(),
            }),
        )

    def _verify_completion(
        self,
        completion: AutonomousExperienceCompletion,
    ) -> None:
        if not isinstance(completion, AutonomousExperienceCompletion):
            raise TypeError("autonomous completion is not typed")
        _sha(completion.work_receipt_sha256, "autonomous completed work")
        if completion.output_receipt_sha256s != tuple(
            sorted(set(completion.output_receipt_sha256s))
        ):
            raise ValueError("autonomous completion output order changed")
        for receipt in completion.output_receipt_sha256s:
            _sha(receipt, "autonomous completion output")
        expected = hmac.new(
            self._completion_key,
            _COMPLETION_DOMAIN + _canonical(completion.payload()),
            hashlib.sha256,
        ).hexdigest()
        if (
            not hmac.compare_digest(
                expected,
                completion.authority_hmac_sha256,
            )
            or completion.authority_receipt_sha256
            != _digest({
                "authority_hmac_sha256": expected,
                "payload": completion.payload(),
            })
        ):
            raise ValueError("autonomous completion authority changed")

    def start(
        self,
        handler: Callable[
            [AutonomousExperienceWork],
            tuple[str, ...],
        ],
        *,
        transition_scope: Callable[
            [], contextlib.AbstractContextManager[None]
        ] | None = None,
    ) -> None:
        if not callable(handler):
            raise TypeError("autonomous experience handler is not callable")
        if transition_scope is not None and not callable(transition_scope):
            raise TypeError(
                "autonomous experience transition scope is not callable"
            )
        with self._condition:
            if self._stopped:
                raise RuntimeError(
                    "autonomous experience driver cannot restart"
                )
            if (
                self._failure is not None
                or self._transition_failure is not None
            ):
                raise RuntimeError(
                    "autonomous experience driver has a latched failure"
                )
            if self._thread is not None and self._thread.is_alive():
                return
            self._handler = handler
            self._transition_scope = (
                contextlib.nullcontext
                if transition_scope is None
                else transition_scope
            )
            self._started = True
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="guala-autonomous-experience",
            )
            self._thread.start()

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(
                    lambda: (
                        self._stopped
                        or self._failure is not None
                        or self._transition_failure is not None
                        or self._in_flight is not None
                        or bool(self._pending)
                    )
                )
                if (
                    self._stopped
                    or self._failure is not None
                    or self._transition_failure is not None
                ):
                    return
                transition_scope = self._transition_scope
            try:
                with transition_scope():
                    if not self._run_one_transition():
                        return
            except BaseException as error:
                with self._condition:
                    active = self._in_flight
                    failure = {
                        "error_type": type(error).__name__,
                        "reason": str(error),
                        "work_receipt_sha256": (
                            active.authority_receipt_sha256
                            if active is not None
                            else None
                        ),
                    }
                    if active is None:
                        self._transition_failure = failure
                    else:
                        self._failure = failure
                        self._encoded_locked()
                    self._condition.notify_all()
                return

    def _run_one_transition(self) -> bool:
        """Settle one work receipt inside its caller-owned causal boundary."""

        with self._condition:
            if self._stopped or self._failure is not None:
                return False
            if self._in_flight is None and not self._pending:
                return True
            if self._in_flight is None:
                self._in_flight = self._pending.pop(0)
                self._encoded_locked()
            work = self._in_flight
            handler = self._handler
        if handler is None:
            raise RuntimeError(
                "autonomous experience handler disappeared"
            )
        try:
            outputs = handler(work)
            if not isinstance(outputs, tuple):
                raise TypeError(
                    "autonomous experience handler output is not typed"
                )
            completion = self._seal_completion(work, outputs)
        except InternalReentryCustodyUnavailable:
            completion = self._seal_completion(work, ())
        except BaseException as error:
            with self._condition:
                self._failure = {
                    "error_type": type(error).__name__,
                    "reason": str(error),
                    "work_receipt_sha256": (
                        work.authority_receipt_sha256
                    ),
                }
                self._encoded_locked()
                self._condition.notify_all()
            return False
        with self._condition:
            self._completed[
                work.authority_receipt_sha256
            ] = completion
            self._in_flight = None
            try:
                self._encoded_locked()
            except BaseException:
                del self._completed[
                    work.authority_receipt_sha256
                ]
                self._in_flight = work
                raise
            self._condition.notify_all()
        return True

    def quiesce(self, timeout: float) -> None:
        if timeout < 0:
            raise ValueError("autonomous quiescence timeout changed")
        with self._condition:
            if (
                self._started
                and self._failure is None
                and self._transition_failure is None
            ):
                drained = self._condition.wait_for(
                    lambda: (
                        self._failure is not None
                        or self._transition_failure is not None
                        or (
                            not self._pending
                            and self._in_flight is None
                        )
                    ),
                    timeout=timeout,
                )
                if not drained:
                    raise RuntimeError(
                        "autonomous experience work did not drain"
                    )
            failure = self._failure or self._transition_failure
            if failure is not None:
                raise RuntimeError(
                    "autonomous experience driver failed: "
                    f"{failure['error_type']}: "
                    f"{failure['reason']}"
                )
            self._stopped = True
            self._condition.notify_all()
            thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
            if thread.is_alive():
                raise RuntimeError(
                    "autonomous experience driver did not quiesce"
                )

    def _state_payload_locked(self) -> dict[str, object]:
        return {
            "completed": [
                completion.record()
                for completion in self._completed.values()
            ],
            "failure": self._failure,
            "in_flight": (
                self._in_flight.record()
                if self._in_flight is not None
                else None
            ),
            "max_records": self._max_records,
            "max_state_bytes": self._max_state_bytes,
            "pending": [value.record() for value in self._pending],
            "schema": DRIVER_STATE_SCHEMA,
        }

    def _encoded_locked(self) -> bytes:
        payload = self._state_payload_locked()
        signature = hmac.new(
            self._state_key,
            _DRIVER_STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        encoded = _canonical({
            "authority_hmac_sha256": signature,
            "payload": payload,
            "schema": DRIVER_ENVELOPE_SCHEMA,
        })
        if len(encoded) > self._max_state_bytes:
            raise RuntimeError(
                "autonomous experience state byte capacity exhausted"
            )
        return encoded

    def encoded_snapshot(self) -> bytes:
        with self._condition:
            return self._encoded_locked()

    def status(self) -> dict[str, object]:
        with self._condition:
            thread_alive = (
                self._thread is not None and self._thread.is_alive()
            )
            failure = self._failure or self._transition_failure
            if failure is not None:
                lifecycle = "failed"
            elif self._stopped:
                lifecycle = "stopped"
            elif thread_alive:
                lifecycle = "running"
            elif self._started:
                lifecycle = "exited"
            else:
                lifecycle = "not_started"
            return {
                "completed": len(self._completed),
                "failure": failure,
                "in_flight_work_receipt_sha256": (
                    self._in_flight.authority_receipt_sha256
                    if self._in_flight is not None
                    else None
                ),
                "lifecycle": lifecycle,
                "pending": len(self._pending),
                "record_capacity": self._max_records,
                "schema": "guala.autonomous_experience.driver_status.v1",
                "state_bytes": len(self._encoded_locked()),
                "state_capacity_bytes": self._max_state_bytes,
                "thread_alive": thread_alive,
                "work_source": "authenticated_receipts_only",
            }

    @staticmethod
    def _work_from_record(raw: object) -> AutonomousExperienceWork:
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != {
                "authority_hmac_sha256",
                "authority_receipt_sha256",
                "dependency_receipt_sha256s",
                "kind",
                "schema",
                "source_receipt_sha256",
            }
            or raw.get("schema") != WORK_SCHEMA
        ):
            raise ValueError("autonomous cold work changed")
        return AutonomousExperienceWork(
            kind=raw.get("kind"),
            source_receipt_sha256=raw.get("source_receipt_sha256"),
            dependency_receipt_sha256s=tuple(
                raw.get("dependency_receipt_sha256s", ())
            ),
            authority_hmac_sha256=raw.get("authority_hmac_sha256"),
            authority_receipt_sha256=raw.get("authority_receipt_sha256"),
        )

    @staticmethod
    def _completion_from_record(
        raw: object,
    ) -> AutonomousExperienceCompletion:
        if (
            not isinstance(raw, Mapping)
            or set(raw)
            != {
                "authority_hmac_sha256",
                "authority_receipt_sha256",
                "output_receipt_sha256s",
                "schema",
                "work_receipt_sha256",
            }
            or raw.get("schema") != COMPLETION_SCHEMA
        ):
            raise ValueError("autonomous cold completion changed")
        return AutonomousExperienceCompletion(
            work_receipt_sha256=raw.get("work_receipt_sha256"),
            output_receipt_sha256s=tuple(
                raw.get("output_receipt_sha256s", ())
            ),
            authority_hmac_sha256=raw.get("authority_hmac_sha256"),
            authority_receipt_sha256=raw.get("authority_receipt_sha256"),
        )

    @classmethod
    def restore_encoded(
        cls,
        *,
        authority_key: bytes | str,
        encoded: bytes,
    ) -> "AutonomousExperienceDriver":
        if not isinstance(encoded, bytes) or not encoded:
            raise ValueError("autonomous driver cold state is absent")
        try:
            envelope = json.loads(encoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("autonomous driver cold state is unreadable") from error
        if (
            not isinstance(envelope, Mapping)
            or set(envelope)
            != {"authority_hmac_sha256", "payload", "schema"}
            or envelope.get("schema") != DRIVER_ENVELOPE_SCHEMA
            or not isinstance(envelope.get("payload"), Mapping)
            or _canonical(envelope) != encoded
        ):
            raise ValueError("autonomous driver cold envelope changed")
        payload = envelope["payload"]
        if (
            payload.get("schema") != DRIVER_STATE_SCHEMA
            or set(payload)
            != {
                "completed",
                "failure",
                "in_flight",
                "max_records",
                "max_state_bytes",
                "pending",
                "schema",
            }
            or not isinstance(payload.get("pending"), list)
            or not isinstance(payload.get("completed"), list)
        ):
            raise ValueError("autonomous driver cold payload changed")
        owner = cls(
            authority_key=authority_key,
            max_records=payload.get("max_records"),
            max_state_bytes=payload.get("max_state_bytes"),
        )
        expected = hmac.new(
            owner._state_key,
            _DRIVER_STATE_DOMAIN + _canonical(payload),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(
            expected,
            envelope.get("authority_hmac_sha256", ""),
        ):
            raise ValueError("autonomous driver cold authority changed")
        pending = [
            owner._work_from_record(raw)
            for raw in payload["pending"]
        ]
        in_flight = (
            None
            if payload.get("in_flight") is None
            else owner._work_from_record(payload["in_flight"])
        )
        completed = [
            owner._completion_from_record(raw)
            for raw in payload["completed"]
        ]
        for work in (*pending, *((in_flight,) if in_flight else ())):
            owner.verify_work(work)
        for completion in completed:
            owner._verify_completion(completion)
        work_receipts = [
            work.authority_receipt_sha256
            for work in (*pending, *((in_flight,) if in_flight else ()))
        ]
        completed_receipts = [
            value.work_receipt_sha256 for value in completed
        ]
        if (
            len(set(work_receipts)) != len(work_receipts)
            or len(set(completed_receipts)) != len(completed_receipts)
            or set(work_receipts).intersection(completed_receipts)
        ):
            raise ValueError("autonomous driver cold receipt set changed")
        failure = payload.get("failure")
        if failure is not None and (
            not isinstance(failure, Mapping)
            or set(failure)
            != {"error_type", "reason", "work_receipt_sha256"}
            or in_flight is None
            or failure["work_receipt_sha256"]
            != in_flight.authority_receipt_sha256
        ):
            raise ValueError("autonomous driver cold failure changed")
        with owner._condition:
            owner._pending = (
                ([in_flight] if in_flight is not None and failure is None else [])
                + pending
            )
            owner._in_flight = in_flight if failure is not None else None
            owner._completed = {
                value.work_receipt_sha256: value for value in completed
            }
            owner._failure = dict(failure) if failure is not None else None
            retained = (
                len(owner._pending)
                + len(owner._completed)
                + int(owner._in_flight is not None)
            )
            if retained > owner._max_records:
                raise ValueError("autonomous driver cold capacity changed")
            if in_flight is None or failure is not None:
                if owner._encoded_locked() != encoded:
                    raise ValueError("autonomous driver cold bytes changed")
        return owner


__all__ = (
    "AutonomousExperienceCompletion",
    "AutonomousExperienceDriver",
    "AutonomousExperienceWork",
    "InternalReentryCustodyUnavailable",
    "WholeOrganismInternalReentry",
    "WholeOrganismInternalReentryAuthority",
)
