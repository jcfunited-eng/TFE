"""Evidence-derived lower-bound acceptance for grounded conversation.

This evaluator never supplies cognition, answers, transcript meaning, or a
human-age mapping.  It reports only structures proven by authenticated live
owners.  A missing structural authority remains explicit.
"""

from __future__ import annotations

from dataclasses import dataclass

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    AuditoryMotifCausalGroundingOwner,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.grounded_turn_conversation import (
    GroundedTurnConstructionState,
    GroundedTurnConversationOwner,
)
from dsf_ai_service.substrate.self_vocal_pcm_motor import (
    SelfVocalPCMMotorOwner,
)
from dsf_ai_service.substrate.w1_grounded_demonstration import (
    W1GroundedDemonstration,
    W1GroundedDemonstrationOwner,
)
from dsf_ai_service.substrate.w1_grounded_lived_sequence import (
    W1GroundedLivedSequenceOwner,
    W1GroundedLivedSequenceProof,
)


CONVERSATION_ACCEPTANCE_SCHEMA = (
    "guala.experience_grounded_conversation.acceptance.v2"
)
MIN_GROUNDED_REFERENTS = 2
MIN_DISTINCT_CUE_CONSTRUCTIONS = 2
MIN_DISTINCT_PCM_MOTORS = 2
MIN_TURN_EPISODES = 2 * MIN_DISTINCT_CUE_CONSTRUCTIONS
MIN_ORDERED_CUE_ELEMENTS = 2
MIN_MULTI_REFERENT_EMISSION_ELEMENTS = 4
MIN_GOAL_EXCHANGES = 2


@dataclass(frozen=True, slots=True)
class GoalAcceptanceRung:
    capability: str
    state: str
    missing_authority: str

    def as_record(self) -> dict[str, str]:
        return {
            "capability": self.capability,
            "missing_authority": self.missing_authority,
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class ExperienceGroundedConversationAcceptance:
    state: str
    goal_state: str
    developmental_equivalence: str
    grounded_referent_count: int
    unresolved_referent_count: int
    motor_exemplar_count: int
    turn_episode_count: int
    unique_construction_count: int
    ambiguous_construction_count: int
    ordered_construction_count: int
    physical_source_receipt_count: int
    physical_source_receipts_disjoint: bool
    capacity_available: bool
    unsatisfied_conditions: tuple[str, ...]
    goal_rungs: tuple[GoalAcceptanceRung, ...]

    def as_record(self) -> dict[str, object]:
        return {
            "ambiguous_construction_count": (
                self.ambiguous_construction_count
            ),
            "capacity_available": self.capacity_available,
            "developmental_equivalence": self.developmental_equivalence,
            "grounded_referent_count": self.grounded_referent_count,
            "goal_rungs": [value.as_record() for value in self.goal_rungs],
            "goal_state": self.goal_state,
            "motor_exemplar_count": self.motor_exemplar_count,
            "ordered_construction_count": self.ordered_construction_count,
            "physical_source_receipt_count": (
                self.physical_source_receipt_count
            ),
            "physical_source_receipts_disjoint": (
                self.physical_source_receipts_disjoint
            ),
            "schema": CONVERSATION_ACCEPTANCE_SCHEMA,
            "state": self.state,
            "turn_episode_count": self.turn_episode_count,
            "unique_construction_count": self.unique_construction_count,
            "unresolved_referent_count": self.unresolved_referent_count,
            "unsatisfied_conditions": list(self.unsatisfied_conditions),
        }


def _rung(
    capability: str,
    *,
    achieved: bool,
    missing: str,
) -> GoalAcceptanceRung:
    return GoalAcceptanceRung(
        capability=capability,
        state=(
            "achieved_authenticated_lived_proof"
            if achieved
            else "not_evaluable_missing_authority"
        ),
        missing_authority="" if achieved else missing,
    )


def _vocal_demonstrations(
    owner: W1GroundedDemonstrationOwner | None,
) -> tuple[W1GroundedDemonstration, ...]:
    if owner is None:
        return ()
    return tuple(
        value
        for value in owner.demonstrations
        if value.response_cue is not None
        and value.motor_id is not None
        and value.self_hearing_receipt_sha256 is not None
    )


def _demonstration_for_proof(
    proof: W1GroundedLivedSequenceProof,
    demonstrations: tuple[W1GroundedDemonstration, ...],
) -> W1GroundedDemonstration:
    matches = tuple(
        value
        for value in demonstrations
        if value.demonstration_id == proof.demonstration_id
    )
    if len(matches) != 1:
        raise ValueError(
            "conversation acceptance lost sequence demonstration"
        )
    return matches[0]


def _challenge_follows_sequence(
    proof: W1GroundedLivedSequenceProof,
    demonstration: W1GroundedDemonstration,
) -> bool:
    if not proof.ordered_events or not demonstration.challenge_cue.elements:
        return False
    terminal_time = proof.ordered_events[-1].source_time_end
    return min(
        value.source_time_start
        for value in demonstration.challenge_cue.elements
    ) >= terminal_time


def _topic_continues(
    proofs: tuple[W1GroundedLivedSequenceProof, ...],
) -> bool:
    return any(
        set(left.response_root_identities).intersection(
            right.response_root_identities
        )
        for left_index, left in enumerate(proofs)
        for right in proofs[left_index + 1 :]
    )


def _goal_rungs(
    *,
    demonstration_owner: W1GroundedDemonstrationOwner | None,
    lived_sequence_owner: W1GroundedLivedSequenceOwner | None,
) -> tuple[GoalAcceptanceRung, ...]:
    vocal = _vocal_demonstrations(demonstration_owner)
    sequence_proofs = (
        lived_sequence_owner.proofs
        if lived_sequence_owner is not None
        else ()
    )
    sequence_demo_ids = {
        value.demonstration_id for value in sequence_proofs
    }
    story_answer_proofs = tuple(
        proof
        for proof in sequence_proofs
        if _challenge_follows_sequence(
            proof,
            _demonstration_for_proof(proof, vocal),
        )
    )

    multi_candidates = tuple(
        value
        for value in vocal
        if value.demonstration_id not in sequence_demo_ids
        and value.response_cue is not None
        and len(value.response_cue.elements)
        >= MIN_MULTI_REFERENT_EMISSION_ELEMENTS
    )
    multi_demo_id = (
        multi_candidates[0].demonstration_id
        if multi_candidates
        else None
    )
    reserved = set(sequence_demo_ids)
    if multi_demo_id is not None:
        reserved.add(multi_demo_id)
    exchange_candidates = tuple(
        value
        for value in vocal
        if value.demonstration_id not in reserved
    )
    repeated_goal_exchange = (
        len(exchange_candidates) >= MIN_GOAL_EXCHANGES
        and len({
            value.challenge_cue.structure_id
            for value in exchange_candidates
        }) >= MIN_GOAL_EXCHANGES
        and len({
            value.motor_id for value in exchange_candidates
        }) >= MIN_GOAL_EXCHANGES
    )

    return (
        _rung(
            "four_or_more_grounded_referents_in_one_emission",
            achieved=multi_demo_id is not None,
            missing=(
                "source-disjoint grounded self-heard response cue with "
                "four exact referent elements"
            ),
        ),
        _rung(
            "answer_what_who_where_why_and_function_challenges",
            achieved=False,
            missing=(
                "complete internal structural answer set: referent "
                "continuity, emitter-body continuity, exact pose relation, "
                "cited causal predecessor, and action-outcome affordance"
            ),
        ),
        _rung(
            "describe_one_lived_daily_event",
            achieved=False,
            missing=(
                "repeated authenticated W1 routine with exact time-cycle "
                "continuity and a grounded response citation"
            ),
        ),
        _rung(
            "attend_to_short_story_and_answer_about_it",
            achieved=bool(story_answer_proofs),
            missing=(
                "ordered authenticated event sequence followed by a "
                "source-disjoint grounded challenge and response citation"
            ),
        ),
        _rung(
            "keep_simple_story_on_topic",
            achieved=(
                len(story_answer_proofs) >= 2
                and _topic_continues(story_answer_proofs)
            ),
            missing=(
                "two source-disjoint post-sequence exchanges with a "
                "nonempty exact grounded response-root intersection"
            ),
        ),
        _rung(
            "use_spatial_time_category_and_comparison_relations",
            achieved=False,
            missing=(
                "complete internal relation set: exact pose/region, event "
                "order, shared demonstrated affordance, and exact ordered "
                "physical quantity"
            ),
        ),
        _rung(
            "follow_simple_directions_and_rules_in_play",
            achieved=False,
            missing=(
                "fresh grounded cue resolved through the authenticated "
                "cue-to-action temporal relation into an exact action and "
                "rule-state outcome"
            ),
        ),
        _rung(
            "communicate_easily_across_goal_demonstrations",
            achieved=repeated_goal_exchange,
            missing=(
                "two additional source-disjoint grounded exchanges with "
                "distinct cue structures and distinct self-heard motors"
            ),
        ),
    )


def evaluate_experience_grounded_conversation(
    *,
    motif_owner: AuditoryRecurrentMotifOwner,
    grounding_owner: AuditoryMotifCausalGroundingOwner,
    motor_owner: SelfVocalPCMMotorOwner,
    turn_owner: GroundedTurnConversationOwner,
    demonstration_owner: W1GroundedDemonstrationOwner | None = None,
    lived_sequence_owner: W1GroundedLivedSequenceOwner | None = None,
) -> ExperienceGroundedConversationAcceptance:
    """Evaluate exact live-owner conjunctions without semantic guessing."""

    if not isinstance(motif_owner, AuditoryRecurrentMotifOwner):
        raise TypeError("conversation acceptance requires the motif owner")
    if not isinstance(
        grounding_owner, AuditoryMotifCausalGroundingOwner
    ):
        raise TypeError(
            "conversation acceptance requires the grounding owner"
        )
    if not isinstance(motor_owner, SelfVocalPCMMotorOwner):
        raise TypeError("conversation acceptance requires the PCM motor owner")
    if not isinstance(turn_owner, GroundedTurnConversationOwner):
        raise TypeError("conversation acceptance requires the turn owner")
    if (
        demonstration_owner is not None
        and not isinstance(
            demonstration_owner, W1GroundedDemonstrationOwner
        )
    ):
        raise TypeError(
            "conversation acceptance demonstration authority changed"
        )
    if (
        lived_sequence_owner is not None
        and not isinstance(
            lived_sequence_owner, W1GroundedLivedSequenceOwner
        )
    ):
        raise TypeError(
            "conversation acceptance lived sequence authority changed"
        )
    if lived_sequence_owner is not None and demonstration_owner is None:
        raise ValueError(
            "lived sequence acceptance lacks demonstration authority"
        )

    motor_owner.cross_validate_restored(motif_owner=motif_owner)
    turn_owner.cross_validate_restored(
        grounding_owner=grounding_owner,
        motor_owner=motor_owner,
    )
    if demonstration_owner is not None:
        demonstration_owner.cross_validate_restored(
            grounding_owner=grounding_owner,
            motor_owner=motor_owner,
        )
    if lived_sequence_owner is not None:
        for proof in lived_sequence_owner.proofs:
            lived_sequence_owner.verify(proof)

    grounding_status = grounding_owner.status()
    motor_status = motor_owner.status()
    turn_status = turn_owner.status()
    constructions = turn_owner.constructions
    episodes = turn_owner.episodes
    unique_constructions = tuple(
        value
        for value in constructions
        if value.state is GroundedTurnConstructionState.UNIQUE
    )
    episode_by_id = {
        value.episode_id: value for value in episodes
    }
    ordered_construction_count = sum(
        any(
            len(episode_by_id[episode_id].cue.elements)
            >= MIN_ORDERED_CUE_ELEMENTS
            and any(
                element.temporal_relation != "first"
                for element in episode_by_id[episode_id].cue.elements
            )
            for episode_id in construction.proof_episode_ids
        )
        for construction in unique_constructions
    )

    grounding_sources = tuple(
        value.auditory_source_event_receipt_sha256
        for value in grounding_owner.episodes
    )
    motor_sources = tuple(
        value.receptor_event_receipt_sha256
        for value in motor_owner.exemplars
    )
    turn_sources = tuple(
        receipt
        for value in episodes
        for receipt in (
            value.prompt_settlement_receipt_sha256,
            value.outcome_settlement_receipt_sha256,
            value.self_hearing_receipt_sha256,
        )
    )
    base_sources = grounding_sources + motor_sources + turn_sources
    demonstration_sources = tuple(
        receipt
        for value in (
            demonstration_owner.demonstrations
            if demonstration_owner is not None
            else ()
        )
        for receipt in value.source_episode_receipt_sha256s
    )
    sources_disjoint = (
        len(set(base_sources)) == len(base_sources)
        and len(set(demonstration_sources)) == len(demonstration_sources)
    )
    physical_source_count = len(set(
        base_sources + demonstration_sources
    ))

    optional_capacity = True
    if demonstration_owner is not None:
        optional_capacity = (
            optional_capacity
            and not demonstration_owner.status()["capacity_exhausted"]
        )
    if lived_sequence_owner is not None:
        optional_capacity = (
            optional_capacity
            and not lived_sequence_owner.status()["capacity_exhausted"]
        )
    capacity_available = (
        not grounding_status["episode_capacity_exhausted"]
        and not grounding_status["distinction_capacity_exhausted"]
        and grounding_status["state_bytes_remaining"] > 0
        and not motor_status["exemplar_capacity_exhausted"]
        and motor_status["pcm_bytes_remaining"] > 0
        and not turn_status["episode_capacity_exhausted"]
        and turn_status["construction_count"]
        < turn_status["construction_capacity"]
        and optional_capacity
    )
    conditions = (
        (
            grounding_status["learned_referent_count"]
            >= MIN_GROUNDED_REFERENTS,
            "fewer_than_two_controlled_grounded_referents",
        ),
        (
            grounding_status["unresolved_referent_count"] == 0,
            "unresolved_grounding_is_retained",
        ),
        (
            motor_status["exemplar_count"] >= MIN_DISTINCT_PCM_MOTORS,
            "fewer_than_two_physical_pcm_motors",
        ),
        (
            len(episodes) >= MIN_TURN_EPISODES,
            "fewer_than_four_independent_lived_turns",
        ),
        (
            len(unique_constructions)
            >= MIN_DISTINCT_CUE_CONSTRUCTIONS,
            "fewer_than_two_unique_cue_response_constructions",
        ),
        (
            turn_status["ambiguous_construction_count"] == 0,
            "ambiguous_cue_response_construction_is_retained",
        ),
        (
            ordered_construction_count >= 1,
            "no_ordered_multi_referent_cue_construction",
        ),
        (
            sources_disjoint,
            "physical_source_receipts_are_reused",
        ),
        (
            capacity_available,
            "conversation_growth_capacity_is_exhausted",
        ),
    )
    failures = tuple(reason for accepted, reason in conditions if not accepted)
    goal_rungs = _goal_rungs(
        demonstration_owner=demonstration_owner,
        lived_sequence_owner=lived_sequence_owner,
    )
    return ExperienceGroundedConversationAcceptance(
        state=(
            "minimal_starting_conversation_ready"
            if not failures
            else "not_ready"
        ),
        goal_state=(
            "all_authenticated_lived_goal_rungs_achieved"
            if all(
                value.state == "achieved_authenticated_lived_proof"
                for value in goal_rungs
            )
            else "not_evaluable_missing_authority"
        ),
        developmental_equivalence=(
            "not_claimed_no_validated_human_age_mapping"
        ),
        grounded_referent_count=grounding_status[
            "learned_referent_count"
        ],
        unresolved_referent_count=grounding_status[
            "unresolved_referent_count"
        ],
        motor_exemplar_count=motor_status["exemplar_count"],
        turn_episode_count=len(episodes),
        unique_construction_count=len(unique_constructions),
        ambiguous_construction_count=turn_status[
            "ambiguous_construction_count"
        ],
        ordered_construction_count=ordered_construction_count,
        physical_source_receipt_count=physical_source_count,
        physical_source_receipts_disjoint=sources_disjoint,
        capacity_available=capacity_available,
        unsatisfied_conditions=failures,
        goal_rungs=goal_rungs,
    )


__all__ = [
    "CONVERSATION_ACCEPTANCE_SCHEMA",
    "ExperienceGroundedConversationAcceptance",
    "GoalAcceptanceRung",
    "MIN_DISTINCT_CUE_CONSTRUCTIONS",
    "MIN_DISTINCT_PCM_MOTORS",
    "MIN_GOAL_EXCHANGES",
    "MIN_GROUNDED_REFERENTS",
    "MIN_MULTI_REFERENT_EMISSION_ELEMENTS",
    "MIN_ORDERED_CUE_ELEMENTS",
    "MIN_TURN_EPISODES",
    "evaluate_experience_grounded_conversation",
]
