"""Concrete Python boundary for one native resident Guala organism.

The native object is the sole active and pending-state authority.  Python
retains only that object and returns fixed prepare receipts; it never carries
prepared organism bytes or a second materialized-fabric state.
"""

from __future__ import annotations

import hashlib
import importlib
import sys
from dataclasses import dataclass
from typing import Protocol


RUNTIME_SCHEMA = "guala.native.resident_organism_runtime.v3"
OBSERVATION_SCHEMA = "guala.native.resident_organism_observation.v3"
PREPARE_SCHEMA = "guala.native.resident_organism_prepare.v3"

_FACTORY_AUTHORITY = object()


class NativeJointSourceView(Protocol):
    """Annotation only; the native prepare method enforces source type."""

    @property
    def port_count(self) -> int: ...


class NativeResidentObservationView(Protocol):
    @property
    def schema(self) -> str: ...

    @property
    def identity(self) -> str: ...

    @property
    def organism_tick(self) -> int: ...

    @property
    def fabric_generation(self) -> int: ...

    @property
    def mounted_generation(self) -> int: ...

    @property
    def state_bytes(self) -> int: ...

    @property
    def state_sha256(self) -> str: ...

    @property
    def fabric_bytes(self) -> int: ...

    @property
    def fabric_sha256(self) -> str: ...

    @property
    def joint_field_count(self) -> int: ...

    @property
    def joint_neuron_count(self) -> int: ...

    @property
    def complete_neuron_count(self) -> int: ...

    @property
    def developmental_resting_neuron_count(self) -> int: ...

    @property
    def physically_transitioned_neuron_count(self) -> int: ...

    @property
    def cold_restore_authentication_count(self) -> int: ...

    @property
    def cold_restore_decode_count(self) -> int: ...

    @property
    def cold_restore_rebuilt_field_count(self) -> int: ...

    @property
    def mounted_step_completed(self) -> bool: ...

    @property
    def physical_transition_claimed(self) -> bool: ...

    @property
    def cognitive_formation_claimed(self) -> bool: ...

    @property
    def cognitive_ordinal(self) -> int: ...

    @property
    def cognitive_trace_count(self) -> int: ...

    @property
    def cognitive_mosaic_count(self) -> int: ...

    @property
    def mosaic_of_mosaics_count(self) -> int: ...

    @property
    def formation_activation_count(self) -> int: ...

    @property
    def partial_cue_reassembly_count(self) -> int: ...

    @property
    def endogenous_partial_cue_reassembly_count(self) -> int: ...

    @property
    def python_callback_count(self) -> int: ...

    # Exact shared body-energy state. Local neuronal lanes keep their own
    # discrete reaction extents; only exact rational zeptojoules cross this
    # organism boundary.
    @property
    def available_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def spent_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def thermal_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def available_energy_capacity_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def dissipated_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def dissipation_capacity_energy_zeptojoules(self) -> tuple[int, int]: ...

    @property
    def separated_elementary_charges(self) -> int: ...

    @property
    def energy_exhausted(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class ResidentContactGrowthEvidence:
    """Receipts for one prepared AUTHORED contact growth.

    Developmental authorship, not a sensory occurrence: it advances the
    organism tick and the fabric generation and nothing else.  The mounted
    joint generation is unchanged, and this boundary refuses any candidate
    that claims otherwise.
    """

    token: bytes
    token_hex: str
    predecessor_state_sha256: str
    prepared_state_sha256: str
    predecessor_organism_tick: int
    organism_tick: int
    predecessor_fabric_generation: int
    fabric_generation: int
    mounted_generation: int
    authored_contact_count: int


@dataclass(frozen=True, slots=True)
class ResidentPrepareEvidence:
    """Fixed receipt and causal evidence for one native pending candidate."""

    token: bytes
    token_hex: str
    predecessor_state_sha256: str
    prepared_state_sha256: str
    predecessor_organism_tick: int
    organism_tick: int
    predecessor_fabric_generation: int
    fabric_generation: int
    predecessor_mounted_generation: int
    mounted_generation: int
    predecessor_authentication_count: int
    predecessor_decode_count: int
    predecessor_rebuilt_field_count: int
    current_cohort_evaluation_count: int
    successor_seal_count: int
    dsf_delivery_count: int
    complete_neuron_fractal_count: int
    recurrent_complete_neuron_fractal_count: int
    physical_transition_claimed: bool
    cognitive_formation_claimed: bool
    cognitive_ordinal: int
    cognitive_trace_count: int
    cognitive_mosaic_count: int
    formation_activation_count: int
    partial_cue_reassembly_count: int
    endogenous_partial_cue_reassembly_count: int
    python_callback_count: int
    complete_neuron_count: int = 0
    developmental_resting_neuron_count: int = 0
    physically_transitioned_neuron_count: int = 0


def _native_core():
    return importlib.import_module("guala_core")


def _positive_integer(value: object, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > sys.maxsize
    ):
        raise ValueError(f"resident organism {label} must be a positive native integer")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"resident organism {label} is not a nonnegative integer")
    return value


def _canonical_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"resident organism {label} is not canonical SHA-256")
    return value


def _validated_causal_intervals(
    maximum_causal_intervals: object,
) -> list[tuple[int, int]]:
    """Validate caller-authored maximum causal intervals.

    One exact positive rational ``(numerator, denominator)`` per source
    occurrence, in exact occurrence order.  Every value is authored by the
    caller as independent environment/anatomy authority; nothing is defaulted
    or derived here.
    """

    if not isinstance(maximum_causal_intervals, (tuple, list)) or not (
        maximum_causal_intervals
    ):
        raise ValueError(
            "resident organism admission requires one authored maximum causal "
            "interval per source occurrence"
        )
    validated: list[tuple[int, int]] = []
    for index, interval in enumerate(maximum_causal_intervals):
        if not isinstance(interval, (tuple, list)) or len(interval) != 2:
            raise TypeError(
                f"authored admission {index} must be (numerator, denominator)"
            )
        numerator, denominator = interval
        if (
            isinstance(numerator, bool)
            or isinstance(denominator, bool)
            or not isinstance(numerator, int)
            or not isinstance(denominator, int)
        ):
            raise TypeError(
                f"authored admission {index} must carry exact integers"
            )
        if denominator == 0:
            raise ValueError(f"authored admission {index} has a zero denominator")
        if numerator * denominator <= 0:
            raise ValueError(
                f"authored admission {index} is not a positive causal interval"
            )
        validated.append((numerator, denominator))
    return validated


def _exact_token(value: object) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise ValueError("resident organism token must be exactly 32 immutable bytes")
    return value


def _concrete_class(core: object, name: str) -> type:
    candidate = getattr(core, name, None)
    if not isinstance(candidate, type):
        raise RuntimeError(f"guala_core does not expose concrete {name}")
    return candidate


def _validate_budget(
    max_envelope_bytes: object,
    max_fabric_bytes: object,
    max_logical_peak_bytes: object,
) -> tuple[int, int, int]:
    envelope = _positive_integer(max_envelope_bytes, "envelope budget")
    fabric = _positive_integer(max_fabric_bytes, "fabric budget")
    logical = _positive_integer(max_logical_peak_bytes, "logical peak budget")
    if fabric >= envelope:
        raise ValueError(
            "resident organism fabric budget must fit inside its envelope budget"
        )
    if logical <= 2 * envelope:
        raise ValueError(
            "resident organism logical peak budget must retain two envelopes and workspace"
        )
    return envelope, fabric, logical


def _observation_signature(
    observation: NativeResidentObservationView,
) -> tuple[object, ...]:
    return (
        observation.identity,
        observation.organism_tick,
        observation.fabric_generation,
        observation.mounted_generation,
        observation.state_bytes,
        observation.state_sha256,
        observation.fabric_bytes,
        observation.fabric_sha256,
        observation.joint_field_count,
        observation.joint_neuron_count,
        observation.complete_neuron_count,
        observation.developmental_resting_neuron_count,
        observation.cognitive_ordinal,
        observation.cognitive_trace_count,
        observation.cognitive_mosaic_count,
        observation.partial_cue_reassembly_count,
        observation.endogenous_partial_cue_reassembly_count,
    )


class NativeResidentOrganism:
    """Factory-only handle retaining exactly one concrete native runtime."""

    __slots__ = (
        "__runtime",
        "__runtime_type",
        "__observation_type",
        "__prepare_type",
    )

    def __new__(cls, authority: object = None, *args: object, **kwargs: object):
        del args, kwargs
        if authority is not _FACTORY_AUTHORITY:
            raise TypeError(
                "native resident organism must be created by cold restore"
            )
        return super().__new__(cls)

    def __init__(
        self,
        authority: object,
        runtime: object,
        runtime_type: type,
        observation_type: type,
        prepare_type: type,
    ) -> None:
        if authority is not _FACTORY_AUTHORITY or not isinstance(
            runtime, runtime_type
        ):
            raise TypeError("native resident organism runtime is not concrete")
        self.__runtime = runtime
        self.__runtime_type = runtime_type
        self.__observation_type = observation_type
        self.__prepare_type = prepare_type

    def _require_observation(
        self, candidate: object
    ) -> NativeResidentObservationView:
        if not isinstance(candidate, self.__observation_type):
            raise TypeError(
                "resident organism operation returned a structural impostor"
            )
        if candidate.schema != OBSERVATION_SCHEMA:
            raise RuntimeError("resident organism observation schema changed")
        if not isinstance(candidate.identity, str) or not candidate.identity:
            raise RuntimeError("resident organism identity is absent")
        organism_tick = _nonnegative_integer(
            candidate.organism_tick, "organism tick"
        )
        fabric_generation = _nonnegative_integer(
            candidate.fabric_generation, "fabric generation"
        )
        mounted_generation = _nonnegative_integer(
            candidate.mounted_generation, "mounted generation"
        )
        del organism_tick, fabric_generation, mounted_generation
        state_bytes = _positive_integer(candidate.state_bytes, "state bytes")
        fabric_bytes = _positive_integer(candidate.fabric_bytes, "fabric bytes")
        if fabric_bytes >= state_bytes:
            raise RuntimeError("resident organism fabric does not fit its envelope")
        _canonical_sha256(candidate.state_sha256, "state receipt")
        _canonical_sha256(candidate.fabric_sha256, "fabric receipt")
        _nonnegative_integer(
            candidate.joint_field_count, "joint field count"
        )
        _nonnegative_integer(
            candidate.joint_neuron_count, "joint neuron count"
        )
        if (
            _nonnegative_integer(
                candidate.cold_restore_authentication_count,
                "cold authentication count",
            )
            != 1
            or _nonnegative_integer(
                candidate.cold_restore_decode_count, "cold decode count"
            )
            != 1
        ):
            raise RuntimeError("resident organism did not cold restore exactly once")
        _nonnegative_integer(
            candidate.cold_restore_rebuilt_field_count,
            "cold rebuilt field count",
        )
        cognitive_ordinal = _nonnegative_integer(
            candidate.cognitive_ordinal, "cognitive ordinal"
        )
        cognitive_trace_count = _nonnegative_integer(
            candidate.cognitive_trace_count, "cognitive trace count"
        )
        cognitive_mosaic_count = _nonnegative_integer(
            candidate.cognitive_mosaic_count, "cognitive mosaic count"
        )
        mosaic_of_mosaics_count = _nonnegative_integer(
            candidate.mosaic_of_mosaics_count, "mosaic of mosaics count"
        )
        del mosaic_of_mosaics_count
        activation_count = _nonnegative_integer(
            candidate.formation_activation_count,
            "formation activation count",
        )
        partial_count = _nonnegative_integer(
            candidate.partial_cue_reassembly_count,
            "partial cue reassembly count",
        )
        endogenous_partial_count = _nonnegative_integer(
            candidate.endogenous_partial_cue_reassembly_count,
            "endogenous partial cue reassembly count",
        )
        complete_count = _nonnegative_integer(
            candidate.complete_neuron_count, "complete neuron count"
        )
        resting_count = _nonnegative_integer(
            candidate.developmental_resting_neuron_count,
            "developmental resting neuron count",
        )
        transitioned_count = _nonnegative_integer(
            candidate.physically_transitioned_neuron_count,
            "physically transitioned neuron count",
        )
        del cognitive_ordinal, cognitive_trace_count, complete_count, resting_count
        if (
            not isinstance(candidate.mounted_step_completed, bool)
            or not isinstance(candidate.physical_transition_claimed, bool)
            or not isinstance(candidate.cognitive_formation_claimed, bool)
            or candidate.physical_transition_claimed
            != (transitioned_count > 0)
            or candidate.python_callback_count != 0
            or endogenous_partial_count > partial_count
        ):
            raise RuntimeError("resident organism observation made a false claim")
        if not candidate.mounted_step_completed and (
            candidate.physical_transition_claimed
            or candidate.cognitive_formation_claimed
            or activation_count != 0
            or partial_count != 0
            or transitioned_count != 0
        ):
            raise RuntimeError(
                "resident organism cold observation claimed step effects"
            )
        del cognitive_mosaic_count
        return candidate

    def readiness(self) -> NativeResidentObservationView:
        """Observe only the active native state."""

        if not isinstance(self.__runtime, self.__runtime_type):
            raise RuntimeError("resident organism runtime identity changed")
        return self._require_observation(self.__runtime.readiness())

    def save(self) -> bytes:
        """Seal only the active GLORUN envelope."""

        observation = self.readiness()
        state = self.__runtime.save()
        if (
            not isinstance(state, bytes)
            or not state.startswith(b"GLORUN01")
            or len(state) != observation.state_bytes
            or hashlib.sha256(state).hexdigest() != observation.state_sha256
        ):
            raise RuntimeError("resident organism save changed active custody")
        return state

    def observe_retained_formations(self) -> tuple[tuple[tuple[str, ...], int], ...]:
        """Read-only structure of the retained distributed formations.

        One entry per admitted mosaic as ``(member_lineage_hexes,
        recurrence_bond_count)``.  Structure only — no recognition, recall,
        meaning, or capital — and reading advances nothing (verified against
        the active state receipt).
        """

        before = self.readiness()
        formations = self.__runtime.observe_retained_formations()
        validated = []
        for members, bond_count in formations:
            lineages = tuple(str(lineage) for lineage in members)
            if len(lineages) < 3 or any(
                len(lineage) != 32 for lineage in lineages
            ):
                raise RuntimeError(
                    "retained formation observation is structurally invalid"
                )
            validated.append((lineages, _nonnegative_integer(
                bond_count, "recurrence bond count"
            )))
        if self.readiness().state_sha256 != before.state_sha256:
            raise RuntimeError("formation observation advanced the organism")
        return tuple(validated)

    def navigate_hippocampal(self, lineage_hex: str) -> None:
        """Refused: the hippocampal episode archive is retired.

        This walked an archived posting chain and returned episode addresses.
        The archive is no longer written or read: it never carried
        recognition, recall or meaning, and it grew by roughly 893 files per
        recognition.  Her memories are the retained formations in her body —
        read those with :meth:`observe_retained_formations`.
        """

        return self.__runtime.navigate_hippocampal(lineage_hex)

    def prepare(self, source: NativeJointSourceView) -> ResidentPrepareEvidence:
        """Prepare one native candidate and return receipts, never state bytes.

        The bare source path remains severed by the mandatory-admission law:
        the native runtime refuses it because no occurrence admission is
        supplied.  Use :meth:`prepare_admitted`.
        """

        source_port_count = _nonnegative_integer(
            getattr(source, "port_count", None), "source port count"
        )
        active_before = self.readiness()
        candidate = self.__runtime.prepare(source)
        return self._validated_prepare_evidence(
            candidate, source_port_count, active_before
        )

    def prepare_admitted(
        self,
        source: NativeJointSourceView,
        maximum_causal_intervals: object,
    ) -> ResidentPrepareEvidence:
        """Prepare one admitted native candidate and return receipts.

        ``maximum_causal_intervals`` carries one caller-authored maximum
        causal interval ``(numerator, denominator)`` in source-time units per
        source occurrence, in exact occurrence order.  It is independent
        environment/anatomy authority; this boundary never derives it from the
        occurrence.

        An admitted transition requires NO durable cold-custody directory and
        writes no file of its own: what a lesson changes is her body, and the
        caller persists that body once per lesson.
        """

        source_port_count = _nonnegative_integer(
            getattr(source, "port_count", None), "source port count"
        )
        intervals = _validated_causal_intervals(maximum_causal_intervals)
        active_before = self.readiness()
        candidate = self.__runtime.prepare_admitted(source, intervals)
        return self._validated_prepare_evidence(
            candidate, source_port_count, active_before
        )

    def prepare_vestibular_tick(
        self,
        predecessor_heading_millidegrees: int,
        signed_body_motion_millidegrees: int,
    ) -> ResidentPrepareEvidence:
        """Prepare one native one-millisecond body-and-balance successor."""

        predecessor_heading = _nonnegative_integer(
            predecessor_heading_millidegrees,
            "vestibular predecessor heading",
        )
        if predecessor_heading >= 360_000:
            raise ValueError("vestibular predecessor heading must be below 360000")
        if (
            not isinstance(signed_body_motion_millidegrees, int)
            or isinstance(signed_body_motion_millidegrees, bool)
            or not -(1 << 31)
            <= signed_body_motion_millidegrees
            < (1 << 31)
        ):
            raise TypeError("vestibular signed yaw step must be a signed 32-bit integer")
        active_before = self.readiness()
        candidate = self.__runtime.prepare_vestibular_tick(
            predecessor_heading,
            signed_body_motion_millidegrees,
        )
        return self._validated_prepare_evidence(candidate, 1, active_before)

    def _validated_prepare_evidence(
        self,
        candidate: object,
        source_port_count: int,
        active_before: NativeResidentObservationView,
    ) -> ResidentPrepareEvidence:
        if not isinstance(candidate, self.__prepare_type):
            raise TypeError("resident organism prepare returned a structural impostor")
        if candidate.schema != PREPARE_SCHEMA:
            raise RuntimeError("resident organism prepare schema changed")
        token = candidate.token
        if (
            not isinstance(token, bytes)
            or len(token) != 32
            or candidate.token_hex != token.hex()
        ):
            raise RuntimeError("resident organism prepare token changed format")
        predecessor_state_sha256 = _canonical_sha256(
            candidate.predecessor_state_sha256, "predecessor state receipt"
        )
        prepared_state_sha256 = _canonical_sha256(
            candidate.prepared_state_sha256, "prepared state receipt"
        )
        predecessor_organism_tick = _nonnegative_integer(
            candidate.predecessor_organism_tick, "predecessor organism tick"
        )
        organism_tick = _nonnegative_integer(
            candidate.organism_tick, "prepared organism tick"
        )
        predecessor_fabric_generation = _nonnegative_integer(
            candidate.predecessor_fabric_generation,
            "predecessor fabric generation",
        )
        fabric_generation = _nonnegative_integer(
            candidate.fabric_generation, "prepared fabric generation"
        )
        predecessor_mounted_generation = _nonnegative_integer(
            candidate.predecessor_mounted_generation,
            "predecessor mounted generation",
        )
        mounted_generation = _nonnegative_integer(
            candidate.mounted_generation, "prepared mounted generation"
        )
        predecessor_authentication_count = _nonnegative_integer(
            candidate.predecessor_authentication_count,
            "prepare predecessor authentication count",
        )
        predecessor_decode_count = _nonnegative_integer(
            candidate.predecessor_decode_count,
            "prepare predecessor decode count",
        )
        predecessor_rebuilt_field_count = _nonnegative_integer(
            candidate.predecessor_rebuilt_field_count,
            "prepare predecessor rebuilt field count",
        )
        current_cohort_evaluation_count = _nonnegative_integer(
            candidate.current_cohort_evaluation_count,
            "current cohort evaluation count",
        )
        successor_seal_count = _nonnegative_integer(
            candidate.successor_seal_count, "successor seal count"
        )
        dsf_delivery_count = _nonnegative_integer(
            candidate.dsf_delivery_count,
            "DSF delivery count",
        )
        complete_neuron_fractal_count = _nonnegative_integer(
            candidate.complete_neuron_fractal_count,
            "complete-neuron fractal count",
        )
        recurrent_complete_neuron_fractal_count = _nonnegative_integer(
            candidate.recurrent_complete_neuron_fractal_count,
            "recurrent complete-neuron fractal count",
        )
        cognitive_ordinal = _nonnegative_integer(
            candidate.cognitive_ordinal, "cognitive ordinal"
        )
        cognitive_trace_count = _nonnegative_integer(
            candidate.cognitive_trace_count, "cognitive trace count"
        )
        cognitive_mosaic_count = _nonnegative_integer(
            candidate.cognitive_mosaic_count, "cognitive mosaic count"
        )
        formation_activation_count = _nonnegative_integer(
            candidate.formation_activation_count,
            "formation activation count",
        )
        partial_cue_reassembly_count = _nonnegative_integer(
            candidate.partial_cue_reassembly_count,
            "partial cue reassembly count",
        )
        endogenous_partial_cue_reassembly_count = _nonnegative_integer(
            candidate.endogenous_partial_cue_reassembly_count,
            "endogenous partial cue reassembly count",
        )
        complete_neuron_count = _nonnegative_integer(
            candidate.complete_neuron_count, "complete neuron count"
        )
        developmental_resting_neuron_count = _nonnegative_integer(
            candidate.developmental_resting_neuron_count,
            "developmental resting neuron count",
        )
        physically_transitioned_neuron_count = _nonnegative_integer(
            candidate.physically_transitioned_neuron_count,
            "physically transitioned neuron count",
        )
        # A mounted joint cohort exists only where at least two ports share
        # one exact source clock, so a lawful episode can evaluate zero
        # mounted cohorts (cognition still receives its occurrences).
        cohort_count_changed = (
            current_cohort_evaluation_count > source_port_count
        )
        reached_neuron_growth = (
            complete_neuron_count - active_before.complete_neuron_count
        )
        claimed_resting_neurons = (
            active_before.developmental_resting_neuron_count
            - developmental_resting_neuron_count
        )
        if (
            predecessor_state_sha256 != active_before.state_sha256
            or predecessor_organism_tick != active_before.organism_tick
            or organism_tick != predecessor_organism_tick + 1
            or predecessor_fabric_generation
            != active_before.fabric_generation
            or fabric_generation != predecessor_fabric_generation + 1
            or predecessor_mounted_generation
            != active_before.mounted_generation
            or mounted_generation != predecessor_mounted_generation + 1
            or predecessor_authentication_count != 0
            or predecessor_decode_count != 0
            or predecessor_rebuilt_field_count != 0
            or cohort_count_changed
            or successor_seal_count != 1
            or recurrent_complete_neuron_fractal_count
            > complete_neuron_fractal_count
            or reached_neuron_growth < 0
            or claimed_resting_neurons < 0
            or claimed_resting_neurons > reached_neuron_growth
            or endogenous_partial_cue_reassembly_count
            > partial_cue_reassembly_count
            or not isinstance(candidate.physical_transition_claimed, bool)
            or not isinstance(candidate.cognitive_formation_claimed, bool)
            or candidate.physical_transition_claimed
            != (physically_transitioned_neuron_count > 0)
            # A cognitive-formation claim must ride on evidence of the
            # formation kind: mosaic admission, activations, or partial-cue
            # reassembly stand on their own counters; trace/ordinal advance
            # is only lawful in a step that delivered genuine neuronal
            # fractals. A bare-DSF prepare dressing itself in advanced
            # cognitive counters is an impostor.
            or (
                candidate.cognitive_formation_claimed
                and cognitive_mosaic_count <= active_before.cognitive_mosaic_count
                and formation_activation_count == 0
                and partial_cue_reassembly_count
                <= active_before.partial_cue_reassembly_count
                and complete_neuron_fractal_count == 0
            )
            or candidate.python_callback_count != 0
        ):
            raise RuntimeError("resident organism prepare changed causal physics")
        active_after = self.readiness()
        if _observation_signature(active_after) != _observation_signature(
            active_before
        ):
            raise RuntimeError("resident organism prepare published pending state")
        return ResidentPrepareEvidence(
            token=token,
            token_hex=candidate.token_hex,
            predecessor_state_sha256=predecessor_state_sha256,
            prepared_state_sha256=prepared_state_sha256,
            predecessor_organism_tick=predecessor_organism_tick,
            organism_tick=organism_tick,
            predecessor_fabric_generation=predecessor_fabric_generation,
            fabric_generation=fabric_generation,
            predecessor_mounted_generation=predecessor_mounted_generation,
            mounted_generation=mounted_generation,
            predecessor_authentication_count=predecessor_authentication_count,
            predecessor_decode_count=predecessor_decode_count,
            predecessor_rebuilt_field_count=predecessor_rebuilt_field_count,
            current_cohort_evaluation_count=current_cohort_evaluation_count,
            successor_seal_count=successor_seal_count,
            dsf_delivery_count=dsf_delivery_count,
            complete_neuron_fractal_count=complete_neuron_fractal_count,
            recurrent_complete_neuron_fractal_count=(
                recurrent_complete_neuron_fractal_count
            ),
            cognitive_ordinal=cognitive_ordinal,
            cognitive_trace_count=cognitive_trace_count,
            cognitive_mosaic_count=cognitive_mosaic_count,
            formation_activation_count=formation_activation_count,
            partial_cue_reassembly_count=partial_cue_reassembly_count,
            endogenous_partial_cue_reassembly_count=(
                endogenous_partial_cue_reassembly_count
            ),
            physical_transition_claimed=candidate.physical_transition_claimed,
            cognitive_formation_claimed=candidate.cognitive_formation_claimed,
            python_callback_count=0,
            complete_neuron_count=complete_neuron_count,
            developmental_resting_neuron_count=(
                developmental_resting_neuron_count
            ),
            physically_transitioned_neuron_count=(
                physically_transitioned_neuron_count
            ),
        )

    def prepare_authored_contacts(
        self, contacts: object
    ) -> ResidentContactGrowthEvidence:
        """Prepare one AUTHORED contact growth and return its receipts.

        ``contacts`` is a sequence of ``(left_sensor_id, left_substream_id,
        right_sensor_id, right_substream_id, conductance_picosiemens)``: the
        caller names two of its OWN declared receptors and the conductance of
        the contact between them, exactly the authorship growth DNA carries at
        genesis.  This boundary derives no adjacency and no conductance.

        Growth is append-only in the body: existing contacts keep their index,
        endpoints, conductance and retained carrier phase. A growth carries
        no sensory occurrence, so no fractal may be claimed. The resident
        cognitive generation advances once because the body itself changed.
        """

        authored: list[tuple[str, str, str, str, int]] = []
        for entry in contacts:
            left_sensor, left_substream, right_sensor, right_substream, conductance = (
                entry
            )
            if (
                not isinstance(left_sensor, str)
                or not isinstance(left_substream, str)
                or not isinstance(right_sensor, str)
                or not isinstance(right_substream, str)
                or not left_sensor
                or not left_substream
                or not right_sensor
                or not right_substream
            ):
                raise TypeError("authored contact endpoints must be declared receptor names")
            authored.append(
                (
                    left_sensor,
                    left_substream,
                    right_sensor,
                    right_substream,
                    _positive_integer(conductance, "authored contact conductance"),
                )
            )
        if not authored:
            raise ValueError("authored contact growth requires at least one contact")
        active_before = self.readiness()
        candidate = self.__runtime.prepare_authored_contacts(authored)
        if not isinstance(candidate, self.__prepare_type):
            raise TypeError("resident organism prepare returned a structural impostor")
        if candidate.schema != PREPARE_SCHEMA:
            raise RuntimeError("resident organism prepare schema changed")
        token = candidate.token
        if (
            not isinstance(token, bytes)
            or len(token) != 32
            or candidate.token_hex != token.hex()
        ):
            raise RuntimeError("resident organism prepare token changed format")
        predecessor_state_sha256 = _canonical_sha256(
            candidate.predecessor_state_sha256, "predecessor state receipt"
        )
        prepared_state_sha256 = _canonical_sha256(
            candidate.prepared_state_sha256, "prepared state receipt"
        )
        if (
            predecessor_state_sha256 != active_before.state_sha256
            or candidate.predecessor_organism_tick != active_before.organism_tick
            or candidate.organism_tick != active_before.organism_tick + 1
            or candidate.predecessor_fabric_generation
            != active_before.fabric_generation
            or candidate.fabric_generation != active_before.fabric_generation + 1
            or candidate.mounted_generation
            != active_before.mounted_generation + 1
            or candidate.dsf_delivery_count != 0
            or candidate.complete_neuron_fractal_count != 0
            or candidate.physical_transition_claimed
            or candidate.cognitive_formation_claimed
        ):
            raise RuntimeError(
                "resident organism contact growth changed causal physics"
            )
        active_after = self.readiness()
        if _observation_signature(active_after) != _observation_signature(
            active_before
        ):
            raise RuntimeError("resident organism prepare published pending state")
        return ResidentContactGrowthEvidence(
            token=token,
            token_hex=candidate.token_hex,
            predecessor_state_sha256=predecessor_state_sha256,
            prepared_state_sha256=prepared_state_sha256,
            predecessor_organism_tick=candidate.predecessor_organism_tick,
            organism_tick=candidate.organism_tick,
            predecessor_fabric_generation=candidate.predecessor_fabric_generation,
            fabric_generation=candidate.fabric_generation,
            mounted_generation=candidate.mounted_generation,
            authored_contact_count=len(authored),
        )

    def observe_cohort_contacts(self) -> tuple[tuple[int, int], ...]:
        """Decoded ``(member_count, contact_count)`` per living cohort."""

        return tuple(
            (int(members), int(contacts))
            for members, contacts in self.__runtime.observe_cohort_contacts()
        )

    def observe_reached_source_site_count(
        self,
        sensor_id: str,
        substream_id: str,
    ) -> int:
        """Count reached cells with one exact persisted physical source."""

        if not isinstance(sensor_id, str) or not sensor_id:
            raise TypeError("reached source sensor identity must be nonempty text")
        if not isinstance(substream_id, str) or not substream_id:
            raise TypeError("reached source substream identity must be nonempty text")
        return _nonnegative_integer(
            self.__runtime.observe_reached_source_site_count(
                sensor_id,
                substream_id,
            ),
            "reached source site count",
        )

    def commit(self, token: bytes) -> NativeResidentObservationView:
        """Commit the native pending candidate selected by its fixed token."""

        self.__runtime.commit(_exact_token(token))
        return self.readiness()

    def discard(self, token: bytes) -> NativeResidentObservationView:
        """Discard the native pending candidate and preserve active state."""

        active_before = self.readiness()
        self.__runtime.discard(_exact_token(token))
        active_after = self.readiness()
        if _observation_signature(active_after) != _observation_signature(
            active_before
        ):
            raise RuntimeError("resident organism discard changed active state")
        return active_after


def restore_native_resident_organism(
    *,
    current_envelope: bytes,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> NativeResidentOrganism:
    """Cold restore one current GLORUN state into one native resident runtime."""

    if (
        not isinstance(current_envelope, bytes)
        or not current_envelope.startswith(b"GLORUN01")
    ):
        raise TypeError("resident organism cold restore requires GLORUN bytes")
    envelope, fabric, logical = _validate_budget(
        max_envelope_bytes,
        max_fabric_bytes,
        max_logical_peak_bytes,
    )
    core = _native_core()
    runtime_type = _concrete_class(core, "NativeResidentOrganismRuntime")
    observation_type = _concrete_class(
        core, "NativeResidentOrganismObservation"
    )
    prepare_type = _concrete_class(core, "NativeResidentOrganismPrepare")
    restore = getattr(core, "restore_native_resident_organism_runtime", None)
    if not callable(restore):
        raise RuntimeError("guala_core does not expose resident cold restore")
    runtime = restore(current_envelope, envelope, fabric, logical)
    if not isinstance(runtime, runtime_type):
        raise TypeError("resident organism cold restore returned a structural impostor")
    if runtime.schema != RUNTIME_SCHEMA:
        raise RuntimeError("resident organism runtime schema changed")
    organism = NativeResidentOrganism(
        _FACTORY_AUTHORITY,
        runtime,
        runtime_type,
        observation_type,
        prepare_type,
    )
    organism.save()
    return organism


def exact_native_yaw_trajectory(
    *,
    predecessor_heading_millidegrees: int,
    signed_displacement_millidegrees: int,
    duration_microseconds: int,
) -> tuple[int, tuple[int, ...]]:
    """Return the native minimum-jerk yaw path on the 1 ms body clock."""

    trajectory = getattr(_native_core(), "exact_virtual_yaw_trajectory", None)
    if not callable(trajectory):
        raise RuntimeError("guala_core does not expose exact virtual yaw physics")
    successor, steps = trajectory(
        predecessor_heading_millidegrees,
        signed_displacement_millidegrees,
        duration_microseconds,
    )
    return int(successor), tuple(int(step) for step in steps)


def migrate_native_resident_organism_exact_energy(
    *,
    current_envelope: bytes,
    expected_predecessor_sha256: str,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> bytes:
    """Perform the explicit one-way retired-reservoir cutover."""

    if (
        not isinstance(current_envelope, bytes)
        or not current_envelope.startswith(b"GLORUN01")
    ):
        raise TypeError("exact-energy migration requires GLORUN bytes")
    predecessor = _canonical_sha256(
        expected_predecessor_sha256, "exact-energy predecessor receipt"
    )
    if hashlib.sha256(current_envelope).hexdigest() != predecessor:
        raise RuntimeError("exact-energy migration predecessor changed")
    envelope, fabric, logical = _validate_budget(
        max_envelope_bytes,
        max_fabric_bytes,
        max_logical_peak_bytes,
    )
    migrate = getattr(
        _native_core(), "migrate_native_resident_organism_exact_energy", None
    )
    if not callable(migrate):
        raise RuntimeError("guala_core does not expose exact-energy migration")
    migrated = bytes(migrate(current_envelope, envelope, fabric, logical))
    if (
        migrated == current_envelope
        or not migrated.startswith(b"GLORUN01")
        or len(migrated) > envelope
    ):
        raise RuntimeError("exact-energy migration did not produce one new body")
    restore_native_resident_organism(
        current_envelope=migrated,
        max_envelope_bytes=envelope,
        max_fabric_bytes=fabric,
        max_logical_peak_bytes=logical,
    )
    return migrated


def _validated_growth_dna(
    growth_dna: object,
    episode_type: type,
) -> tuple[object, list[tuple[list[int], list[tuple[int, int, int]]]]]:
    """Validate authored growth DNA: (anatomy_episode, seed_groups).

    Each seed group is (port_indices, contacts): port_indices name joint
    source ports of the anatomy episode, and each contact is
    (left_seed_index, right_seed_index, conductance_picosiemens). Every value
    is authored by the caller; nothing is defaulted or inferred here.
    """

    if not isinstance(growth_dna, (tuple, list)) or len(growth_dna) != 2:
        raise TypeError(
            "resident organism growth_dna must be (anatomy_episode, seed_groups)"
        )
    anatomy_episode, seed_groups = growth_dna
    if not isinstance(anatomy_episode, episode_type):
        raise TypeError(
            "resident organism growth_dna anatomy episode must be a concrete "
            "native joint source episode"
        )
    if not isinstance(seed_groups, (tuple, list)) or not seed_groups:
        raise ValueError(
            "resident organism growth_dna requires at least one authored seed group"
        )

    def _index(value: object, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"growth_dna {label} must be a nonnegative integer")
        return value

    validated_groups: list[tuple[list[int], list[tuple[int, int, int]]]] = []
    for group_index, group in enumerate(seed_groups):
        if not isinstance(group, (tuple, list)) or len(group) != 2:
            raise TypeError(
                f"growth_dna seed group {group_index} must be "
                "(port_indices, contacts)"
            )
        port_indices, contacts = group
        if not isinstance(port_indices, (tuple, list)) or not port_indices:
            raise ValueError(
                f"growth_dna seed group {group_index} must name at least one "
                "port index"
            )
        validated_ports = [
            _index(port_index, f"seed group {group_index} port index")
            for port_index in port_indices
        ]
        if not isinstance(contacts, (tuple, list)):
            raise TypeError(
                f"growth_dna seed group {group_index} contacts must be a sequence"
            )
        validated_contacts: list[tuple[int, int, int]] = []
        for contact in contacts:
            if not isinstance(contact, (tuple, list)) or len(contact) != 3:
                raise TypeError(
                    f"growth_dna seed group {group_index} contact must be "
                    "(left_seed_index, right_seed_index, conductance_picosiemens)"
                )
            left, right, conductance = contact
            if isinstance(conductance, bool) or not isinstance(conductance, int):
                raise ValueError(
                    f"growth_dna seed group {group_index} conductance must be "
                    "an authored integer picosiemens value"
                )
            validated_contacts.append(
                (
                    _index(left, f"seed group {group_index} contact left index"),
                    _index(right, f"seed group {group_index} contact right index"),
                    conductance,
                )
            )
        validated_groups.append((validated_ports, validated_contacts))
    return anatomy_episode, validated_groups


def create_native_resident_organism(
    *,
    organism_identity: str,
    organism_tick: int = 0,
    growth_dna: object,
    max_envelope_bytes: int,
    max_fabric_bytes: int,
    max_logical_peak_bytes: int,
) -> NativeResidentOrganism:
    """Create the canonical native genesis carrying authored growth DNA.

    ``growth_dna`` is required: growth never invents electrical contacts, so a
    genesis without authored developmental seeds could never form a physical
    mosaic. The seeded genesis is still structurally empty — zero cohorts,
    traces, and mosaics — until its seeds are reached and expressed.
    """

    if not isinstance(organism_identity, str) or not organism_identity:
        raise TypeError("resident organism genesis identity must be text")
    tick = _nonnegative_integer(organism_tick, "genesis organism tick")
    envelope, fabric, logical = _validate_budget(
        max_envelope_bytes,
        max_fabric_bytes,
        max_logical_peak_bytes,
    )
    core = _native_core()
    runtime_type = _concrete_class(core, "NativeResidentOrganismRuntime")
    observation_type = _concrete_class(
        core, "NativeResidentOrganismObservation"
    )
    prepare_type = _concrete_class(core, "NativeResidentOrganismPrepare")
    episode_type = _concrete_class(core, "NativeJointSourceEpisode")
    anatomy_episode, seed_groups = _validated_growth_dna(
        growth_dna, episode_type
    )
    create = getattr(
        core, "create_native_resident_organism_runtime_with_growth_dna", None
    )
    if not callable(create):
        raise RuntimeError(
            "guala_core does not expose resident growth-dna genesis"
        )
    runtime = create(
        organism_identity,
        tick,
        anatomy_episode,
        seed_groups,
        envelope,
        fabric,
        logical,
    )
    if not isinstance(runtime, runtime_type):
        raise TypeError("resident organism genesis returned a structural impostor")
    if runtime.schema != RUNTIME_SCHEMA:
        raise RuntimeError("resident organism genesis runtime schema changed")
    organism = NativeResidentOrganism(
        _FACTORY_AUTHORITY,
        runtime,
        runtime_type,
        observation_type,
        prepare_type,
    )
    observation = organism.readiness()
    if (
        observation.identity != organism_identity
        or observation.organism_tick != tick
        or observation.fabric_generation != 0
        or observation.mounted_generation != 0
        or observation.joint_field_count != 0
        or observation.joint_neuron_count != 0
        or observation.cognitive_ordinal != 0
        or observation.cognitive_trace_count != 0
        or observation.cognitive_mosaic_count != 0
    ):
        raise RuntimeError("resident organism genesis was not structurally empty")
    organism.save()
    return organism


__all__ = (
    "NativeResidentObservationView",
    "NativeResidentOrganism",
    "OBSERVATION_SCHEMA",
    "PREPARE_SCHEMA",
    "RUNTIME_SCHEMA",
    "ResidentPrepareEvidence",
    "create_native_resident_organism",
    "exact_native_yaw_trajectory",
    "restore_native_resident_organism",
    "migrate_native_resident_organism_exact_energy",
)
