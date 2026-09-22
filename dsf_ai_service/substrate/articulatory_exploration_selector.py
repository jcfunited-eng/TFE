"""Stateless exact physical selection among unclosed articulatory actions.

Each retained motor program is represented by nine independent actuator
dimensions: total absolute laryngeal excitation travel and the total area
travel of each of the eight vocal-tract sections.  The selector admits a
program only when it is the unique minimal member of the exact componentwise
partial order.  It never combines dimensions into a score and never inspects
or retains PCM, sensory fields, labels, or program identity ordering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from dsf_ai_service.substrate.articulatory_consequence_closure import (
    ArticulatoryConsequenceClosureOwner,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    TRACT_SECTION_COUNT,
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.pending_articulatory_causal_attempt import (
    PendingArticulatoryCausalAttemptOwner,
)


STATUS_SCHEMA = "guala.articulatory_exploration_selector.status.v1"


def _round_div(numerator: int, denominator: int) -> int:
    """Match the motor's exact nearest-integer, half-away-from-zero law."""

    if denominator <= 0:
        raise ValueError("articulatory divisor must be positive")
    sign = -1 if numerator < 0 else 1
    magnitude = abs(numerator)
    quotient, remainder = divmod(magnitude, denominator)
    if 2 * remainder >= denominator:
        quotient += 1
    return sign * quotient


@dataclass(frozen=True, slots=True)
class ArticulatoryPhysicalAction:
    """Nine separate exact physical actuator-action dimensions."""

    laryngeal_excitation_travel_pcm: int
    tract_section_area_travel_mm2: tuple[int, ...]

    def verify(self) -> None:
        if (
            isinstance(self.laryngeal_excitation_travel_pcm, bool)
            or not isinstance(
                self.laryngeal_excitation_travel_pcm,
                int,
            )
            or self.laryngeal_excitation_travel_pcm < 0
            or not isinstance(
                self.tract_section_area_travel_mm2,
                tuple,
            )
            or len(self.tract_section_area_travel_mm2)
            != TRACT_SECTION_COUNT
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                for value in self.tract_section_area_travel_mm2
            )
        ):
            raise ValueError(
                "articulatory physical action dimensions changed"
            )


def physical_action_for_program(
    program: ArticulatoryProgram,
) -> ArticulatoryPhysicalAction:
    """Derive exact action dimensions without synthesizing pressure."""

    if not isinstance(program, ArticulatoryProgram):
        raise TypeError(
            "articulatory physical action requires a motor program"
        )
    program.verify()
    larynx = program.larynx
    prior_flow = 0
    excitation_travel = 0
    for sample_index in range(program.sample_count):
        phase = sample_index % larynx.cycle_samples
        flow = (
            _round_div(
                larynx.peak_volume_velocity_pcm
                * 4
                * phase
                * (larynx.open_samples - phase),
                larynx.open_samples * larynx.open_samples,
            )
            if phase < larynx.open_samples
            else 0
        )
        excitation_travel += abs(flow - prior_flow)
        prior_flow = flow
    tract = program.tract
    section_area_travel = tuple(
        abs(apex - initial) + abs(final - apex)
        for initial, apex, final in zip(
            tract.initial_section_area_mm2,
            tract.apex_section_area_mm2,
            tract.final_section_area_mm2,
            strict=True,
        )
    )
    result = ArticulatoryPhysicalAction(
        laryngeal_excitation_travel_pcm=excitation_travel,
        tract_section_area_travel_mm2=section_area_travel,
    )
    result.verify()
    return result


def _strictly_componentwise_below(
    left: ArticulatoryPhysicalAction,
    right: ArticulatoryPhysicalAction,
) -> bool:
    left.verify()
    right.verify()
    pairs = (
        (
            left.laryngeal_excitation_travel_pcm,
            right.laryngeal_excitation_travel_pcm,
        ),
        *zip(
            left.tract_section_area_travel_mm2,
            right.tract_section_area_travel_mm2,
            strict=True,
        ),
    )
    return (
        all(left_value <= right_value for left_value, right_value in pairs)
        and any(
            left_value < right_value
            for left_value, right_value in pairs
        )
    )


class ArticulatoryExplorationState(str, Enum):
    SELECTED = "selected"
    SILENT = "silent"


@dataclass(frozen=True, slots=True)
class ArticulatoryExplorationSelection:
    state: ArticulatoryExplorationState
    reason: str
    program: ArticulatoryProgram | None
    physical_action: ArticulatoryPhysicalAction | None
    unclosed_program_count: int
    minimal_program_count: int
    _owner_authority: object = field(repr=False, compare=False)


class ActivePendingArticulatoryAttemptError(RuntimeError):
    """Selection is forbidden while an attempt transaction has custody."""


class ArticulatoryExplorationSelector:
    """Owner-bound, bounded, and dynamically stateless exploration law."""

    def __init__(
        self,
        *,
        motor_owner: ArticulatorySelfVocalMotorOwner,
        consequence_closure_owner: ArticulatoryConsequenceClosureOwner,
        pending_attempt_owner: PendingArticulatoryCausalAttemptOwner,
    ) -> None:
        if not isinstance(
            motor_owner,
            ArticulatorySelfVocalMotorOwner,
        ):
            raise TypeError(
                "articulatory exploration requires its motor owner"
            )
        if not isinstance(
            consequence_closure_owner,
            ArticulatoryConsequenceClosureOwner,
        ):
            raise TypeError(
                "articulatory exploration requires consequence closure"
            )
        if not isinstance(
            pending_attempt_owner,
            PendingArticulatoryCausalAttemptOwner,
        ):
            raise TypeError(
                "articulatory exploration requires pending-attempt custody"
            )
        pending_attempt_owner.verify_articulatory_exploration_owners(
            motor_owner=motor_owner,
            consequence_closure_owner=consequence_closure_owner,
        )
        self._motor = motor_owner
        self._closure = consequence_closure_owner
        self._pending = pending_attempt_owner
        self._owner_authority = object()

    def select(self) -> ArticulatoryExplorationSelection:
        """Return only one unique exact componentwise physical minimum."""

        with self._pending.articulatory_exploration_read_transaction(
            motor_owner=self._motor,
            consequence_closure_owner=self._closure,
        ) as owner_read:
            if owner_read.active_pending_attempt:
                raise ActivePendingArticulatoryAttemptError(
                    "articulatory exploration rejected an active pending "
                    "attempt"
                )
            candidates = tuple(
                (program, physical_action_for_program(program))
                for program in owner_read.retained_programs
                if program.program_id
                not in owner_read.closed_program_ids
            )
            minima = tuple(
                candidate
                for candidate in candidates
                if not any(
                    other_program is not candidate[0]
                    and _strictly_componentwise_below(
                        other_action,
                        candidate[1],
                    )
                    for other_program, other_action in candidates
                )
            )
            if len(minima) == 1:
                program, action = minima[0]
                return ArticulatoryExplorationSelection(
                    state=ArticulatoryExplorationState.SELECTED,
                    reason=(
                        "unique_componentwise_minimal_unclosed_action"
                    ),
                    program=program,
                    physical_action=action,
                    unclosed_program_count=len(candidates),
                    minimal_program_count=1,
                    _owner_authority=self._owner_authority,
                )
            return ArticulatoryExplorationSelection(
                state=ArticulatoryExplorationState.SILENT,
                reason=(
                    "no_unclosed_articulatory_action"
                    if not candidates
                    else "no_unique_componentwise_minimal_action"
                ),
                program=None,
                physical_action=None,
                unclosed_program_count=len(candidates),
                minimal_program_count=len(minima),
                _owner_authority=self._owner_authority,
            )

    def verify_selection(
        self,
        selection: ArticulatoryExplorationSelection,
    ) -> None:
        if (
            not isinstance(
                selection,
                ArticulatoryExplorationSelection,
            )
            or selection._owner_authority
            is not self._owner_authority
            or selection != self.select()
        ):
            raise ValueError(
                "articulatory exploration selection changed custody"
            )

    def status(self) -> dict[str, object]:
        return {
            "actuator_dimensions": 1 + TRACT_SECTION_COUNT,
            "retained_pcm_bytes": 0,
            "retained_selection_count": 0,
            "schema": STATUS_SCHEMA,
            "stateful": False,
        }


__all__ = (
    "STATUS_SCHEMA",
    "ActivePendingArticulatoryAttemptError",
    "ArticulatoryExplorationSelection",
    "ArticulatoryExplorationSelector",
    "ArticulatoryExplorationState",
    "ArticulatoryPhysicalAction",
    "physical_action_for_program",
)
