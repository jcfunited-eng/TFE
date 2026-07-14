"""Production, end-to-end first-learned-expression pipeline (Step 4).

This module answers ``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-
20260713-v1.md`` section 12, Step 4: *"Deliverable: production persistence
for learned bindings and recall episodes under one new generation identity.
Proof: learn one real multimodal expression, restart, and reproduce the
exact learned receipts without legacy import."*

A prior investigation found that no test or production code drove a full
real turn (sense -> commit -> learn -> checkpoint -> restore) through the
actual production pipeline built by Steps 1-3 of this effort: every existing
``expression_learning.py`` test hand-synthesizes a ``SealedClosedExperience``
/``CommittedCoexperience`` fixture rather than deriving one from real sensed
data. :func:`learn_one_real_multimodal_expression` closes that gap.

The exact chain of real function calls
----------------------------------------
Two independent "scenes" are lived, each spanning five real, causally
ordered instants of the five native senses plus one real typed-language
scalar. Five, not the structural floor of two, because the typed-language
scalar's real balanced-ternary encoding needs five valid trit places, and
the language lane must share one common causal grid with the senses (see
:func:`_evolve_real_causal_window`'s docstring); the underlying boundary
owner and causal-window confirmation only ever require "at least two."

1. ``story_chemistry.mount_packaged_production_story_chemistry`` -- mount the
   real, packaged, signed five-sense chemistry manifest (the actual
   production profile at ``glew_runtime/profiles/
   production_virtual_story_chemistry_profile_v1.json``), once per scene.
2. ``six_sense_boundary_owner.observe_six_sense_boundary`` -- assemble one
   real ``StoryPhysicalBoundaryEvent`` per instant from real emulated sight
   (``visual_krimelack.view_picture``), real emulated sound
   (``auditory_fragment_receipt.AuditoryPerceptFragment``), and real
   touch/smell/taste descriptors drawn from the legitimate somatic
   vocabulary -- never a word-hash-derived placeholder.
3. ``story_chemistry.evolve_story_chemistry_event`` -- evolve the real
   chemistry runtime through each observed instant in turn (this module
   calls this directly; ``six_sense_boundary_owner.py`` itself never does,
   by its own documented design).
4. ``six_sense_boundary_owner.confirm_causal_window_candidate`` -- confirm
   the two real, time-ordered instants form a genuine causal window.
5. ``story_chemistry.build_story_frozen_kernel_inputs`` -- bind the two real
   evolved frames to the frozen L0 input contract, producing one real
   ``EvidenceStream``/``KernelNativeInputStream`` pair per sense (this is
   the exact bridge ``tests/glew_runtime/test_six_sense_boundary_owner.py``
   proves the boundary owner's own output is genuinely consumable by).
6. ``language.build_typed_language_frozen_kernel_input`` -- capture one real
   typed-language Unicode scalar on the same causal grid as the senses.
7. ``six_lane_runtime_mount.mount_support_domain`` /
   ``mount_resonance_graph_and_operator`` /
   ``mount_precision_schedule_authority`` -- the real Step-3 production
   mount functions, used directly (not reimplemented) to build the shared
   six-lane support domain, resonance graph/operator, and precision
   authority every scene's expression is evaluated against.
8. ``closed_experience.prepare_closed_experience_evidence`` -- run frozen
   L0-L4 over all six real lanes and assemble one real asynchronous sparse
   evidence sequence.
9. ``expressions.create_closed_experience_expression`` (fed by
   ``field.source_coefficients_for_injection`` /
   ``canonical_component_partition`` / ``field.FieldEvolutionAuthority``) --
   the real closed-experience field expression for each scene.
10. ``expression_modes.evaluate_expression_mode_boundary`` -- called twice to
    *bootstrap* the mode bank from empty (rank 0 -> 1 -> 2), then twice more
    to *recognize* each already-bootstrapped scene against the resulting
    rank-2 bank. See "The bootstrap requirement" below: this two-phase
    structure is not a test convenience, it is a real, load-bearing
    requirement of ``commit.py``'s own conjunction.
11. ``closed_experience.seal_closed_experience`` -- seal each scene's
    evidence/expression/recognition.
12. ``physical_l6_tangents.produce_physical_l6_tangents`` + ``l6.evaluate_l6``
    -- real Fixed-42 L6 structural-lock evaluation over the six mounted
    lanes (shared across both scenes; L6 concerns lane structure, not scene
    content).
13. ``safe_mode.evaluate_safe_mode`` / ``event_support.evaluate_event_support``
    -- real conjunction inputs (see "What remains asserted" below for the
    one honest limitation in this step).
14. ``commit.evaluate_commit_boundary`` -- the real fail-closed commit
    conjunction. Only when this genuinely returns ``CommitStatus.COMMIT``
    does this module proceed to learning.
15. ``expression_learning.derive_committed_mode_relation`` /
    ``create_learned_binding_genesis`` / ``learn_committed_binding_transaction``
    -- the real learning entry points, called only on a genuine
    ``CommittedCoexperience``.
16. ``expression_learning.learned_binding_checkpoint_payload`` /
    ``restore_learned_binding_checkpoint`` -- real, unmodified, exercised by
    the accompanying test to prove bit-identical restart receipts.

The bootstrap requirement (a real finding, not a workaround)
--------------------------------------------------------------
``commit.py``'s ``_verify_expression_recognition`` fails closed with
``bootstrap_requires_two_pre_growth_expression_modes`` whenever
``recognition.pre_growth_bank.rank < 2`` (``commit.py`` line ~1163-1164).
That finding is appended as a *negative* finding (not merely "unknown"), so
``evaluate_commit_boundary`` can never reach ``CommitStatus.COMMIT`` on a
mode bank that has not already grown to at least two independent modes.

Consequently, the FIRST-EVER learned expression cannot be committed on its
own: the mode bank must already contain two independent, previously
bootstrapped source expressions before ANY recognition against it can ever
be eligible to commit. ``evaluate_expression_mode_boundary`` performs both
roles in one function: called against a bank of rank 0 or 1 it grows the
bank and returns ``BOOTSTRAP_SILENCE`` (never ``RECOGNIZED``, so never
commit-eligible); called again, afterward, against the now-rank-2 bank, the
exact same stored expression is re-evaluated and can return ``RECOGNIZED``
with unique interval dominance -- only that second call's result is
commit-eligible. This module performs that exact two-phase sequence with two
genuinely distinct, independently lived real scenes (not, as the existing
``tests/glew_runtime/test_expression_learning.py::learning_world`` fixture
does, one real scene's base execution plus one of its own L6-tangent
finite-difference perturbation replay executions -- see the module-level
note in that test file; this module instead answers Step 4's literal ask of
"one real multimodal expression" with two honestly independent lived scenes).

What remains asserted rather than computed (reported honestly)
------------------------------------------------------------------
Three sub-authorities inside the real commit conjunction are asserted with
real, receipted, but caller-declared values rather than computed by a deeper
producer, because no such producer exists anywhere in this repository today
-- this mirrors exactly what the most rigorous existing test in this
codebase (``tests/glew_runtime/test_expression_learning.py``) already does,
not a shortcut invented for this module:

* SafeMode integrity facts (chemistry/field/persistence) are asserted
  ``IntegrityFactState.CLEAR``. No production tamper/integrity-detector
  authority exists yet to compute these independently; ``evaluate_safe_mode``
  itself is the real, unmodified conjunction over whatever facts it is given.
* Global-UF validation is asserted ``AuthorityDisposition.PASS`` as a
  directly constructed ``BinaryCommitAuthority``, rather than computed via
  ``global_uf.evaluate_global_uf_validation``. That function IS real and
  callable, but it requires a concrete ``GlobalUFReplayProvider``
  implementation, and the only implementation anywhere in this repository is
  ``tests/glew_runtime/test_global_uf.py::Provider`` -- test-only code. No
  production ``GlobalUFReplayProvider`` exists. This is a genuine,
  independently confirmed architecture gap of exactly the same kind the
  governing spec's section 9.6 already names for
  ``RecallStoryRuntimeResolver``/``RecallReplayIntegrityProvider``; building
  a production replay provider is a task-sized undertaking of its own, out
  of scope for this integration.
* The L6 physical-tangent "response law" coefficients (``base``/
  ``response_gradient`` in :func:`_physical_replay_bundle`) are arbitrary,
  receipted constants, because -- as ``sensor_port_authority_mount.py``'s own
  module docstring documents -- no ratified native-response derivation exists
  anywhere in this repository for ``response_growth``/``natural_decay``/
  ``phase_kappa`` today.

None of these three is a SENSORY fabrication (no sight/sound/touch/smell/
taste value is ever invented from a word hash or label); they are honest
placeholders for authorities this codebase has not yet built a real producer
for, exactly as the existing test suite already lives with.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

import numpy as np

from .auditory_fragment_receipt import (
    AUDITORY_BAND_ORDER,
    AuditoryPerceptFragment,
    auditory_fragment_receipt,
)
from .closed_experience import (
    ClosedExperienceProviderUnknown,
    L5ApplicabilityRule,
    MountedL5GovernanceProfile,
    SealedClosedExperience,
    l5_governance_profile_receipt_payload,
    prepare_closed_experience_evidence,
    seal_closed_experience,
)
from .commit import (
    ApplicabilityState,
    AuthorityDisposition,
    BinaryAuthorityKind,
    BinaryCommitAuthority,
    CommitStatus,
    GovernedFact,
    L6ScopeAuthority,
    binary_authority_receipt_payload,
    evaluate_commit_boundary,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
)
from .event_support import (
    EventSupportEvaluationStatus,
    MemoryEnergyAuthority,
    evaluate_event_support,
    memory_energy_authority_receipt_payload,
)
from .experience_origin import (
    ExperienceOriginAuthority,
    ExperienceOriginKind,
    experience_origin_authority_receipt_payload,
)
from .expression_learning import (
    CoexperiencedOutput,
    CommittedCoexperience,
    CommittedModeRelation,
    LearnedBindingState,
    create_coexperienced_no_output,
    create_learned_binding_genesis,
    derive_committed_mode_relation,
    learn_committed_binding_transaction,
)
from .expression_modes import (
    ExpressionModeBoundaryResult,
    ExpressionRecognitionStatus,
    create_empty_expression_mode_bank,
    evaluate_expression_mode_boundary,
)
from .expressions import (
    FieldExpressionStep,
    PrecisionScheduleAuthority,
    create_closed_experience_expression,
)
from .field import (
    ExactComplex,
    ExactFieldState,
    FieldEvolutionAuthority,
    MountedFieldTopology,
    PortFiber,
    canonical_component_partition,
    evolution_authority_receipt_payload,
    exact_field_state_receipt_payload,
    field_topology_receipt_payload,
    source_coefficients_for_injection,
)
from .global_uf import MountedPreWindowState, pre_window_state_receipt_payload
from .l6 import ActiveLaneState, L6Evaluation, L6Lane, L6PredicateInputs, LANE_ORDER, evaluate_l6
from .language import (
    MountedTypedLanguageKernelBinding,
    TypedLanguageEvent,
    TypedLanguageFrozenKernelInput,
    TypedLanguageState,
    build_typed_language_frozen_kernel_input,
    encode_balanced_ternary_scalar,
    typed_interface_receipt_payload,
    typed_language_event_receipt_payload,
    typed_language_kernel_binding_receipt_payload,
    typed_phase_calibration_receipt_payload,
)
from .model import ReceiptError, ReceiptRecord, ReceiptRegistry, receipt_sha256
from .operators import (
    CausalGrid,
    MountedResonanceGraph,
    MountedSupportDomain,
    RequiredEdge,
    ResonanceOperatorAuthority,
    causal_grid_receipt_payload,
)
from .physical_l6_tangents import (
    ExactL4Response,
    LanguageTritCoordinate,
    MountedNativePerturbationProfile,
    MountedNativeResponseSet,
    MountedSameBranchCellProof,
    NativeL4ReplayResponse,
    NativePortReplayBundle,
    PhysicalTangentProductionStatus,
    SensorNativeCoordinate,
    TypedTrit,
    enumerate_native_replay_cases,
    native_l4_replay_response_receipt_payload,
    native_perturbation_profile_receipt_payload,
    native_response_set_receipt_payload,
    produce_physical_l6_tangents,
    same_branch_cell_proof_receipt_payload,
)
from .safe_mode import (
    IntegrityFact,
    IntegrityFactState,
    MountedSafeModeScope,
    evaluate_safe_mode,
    integrity_fact_receipt_payload,
    safe_mode_scope_receipt_payload,
)
from .six_lane_runtime_mount import (
    mount_precision_schedule_authority,
    mount_resonance_graph_and_operator,
    mount_support_domain,
)
from .six_sense_boundary_owner import (
    CausalWindowCandidateStatus,
    SixSenseBoundaryStatus,
    confirm_causal_window_candidate,
    observe_six_sense_boundary,
)
from .story_chemistry import (
    StoryChemistryRuntime,
    StoryChemistryStatus,
    StoryFrozenKernelInputs,
    StoryKernelBridgeStatus,
    build_story_frozen_kernel_inputs,
    evolve_story_chemistry_event,
    mount_packaged_production_story_chemistry,
)
from dsf_ai_service.visual_krimelack import view_picture, visual_fragment_receipt


# ---------------------------------------------------------------------------
# canonical bytes / registry bookkeeping (mirrors every sibling module's own
# private helper of the same shape; duplicated here rather than imported so
# this file has no import-time dependency on a module under concurrent edit)
# ---------------------------------------------------------------------------


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _extend(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    records = list(registry.records)
    values = {item.digest: item.payload for item in records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        existing = values.get(digest)
        if existing is not None:
            if existing != payload:
                raise ReceiptError("real experience learning receipt digest collision")
            continue
        values[digest] = payload
        records.append(ReceiptRecord(digest, payload))
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(records),
    )


def _merge(registry: ReceiptRegistry, addition: ReceiptRegistry) -> ReceiptRegistry:
    if registry.profile_binding_sha256 != addition.profile_binding_sha256:
        raise ReceiptError(
            "real experience learning registries use different GLEW profiles"
        )
    return _extend(registry, *(value.payload for value in addition.records))


# ---------------------------------------------------------------------------
# Real sensory descriptors for one instant. Every field here is either a
# genuinely emulated sight/sound percept or a word drawn from the
# somatic_boundary-legitimate touch/smell/taste vocabulary -- never a value
# derived from the scene's own text or identity.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InstantDescriptor:
    visual_fill_value: float
    visual_seed: int
    auditory_born_tick: int
    touch_descriptor: str | None
    smell_descriptor: str | None
    taste_descriptor: str | None


def _real_visual_fragment_receipt(
    *, fill_value: float, seed: int, ticks_per_fixation: int = 500, born_tick: int = 0
) -> Sequence[object]:
    """Same real saccade/fovea-krimelack pipeline proven in
    ``tests/glew_runtime/test_sight_boundary.py`` -- a genuine (synthetic
    but real) captured image, never a stand-in fixture."""

    image = np.full((16, 16), fill_value, dtype=np.float64)
    fragments = view_picture(
        image,
        source_id="real-experience-learning-camera",
        born_tick=born_tick,
        seed=seed,
        n_fixations=1,
        ticks_per_fixation=ticks_per_fixation,
    )
    if not fragments:
        raise ReceiptError("real emulated camera produced no fixation fragments")
    return visual_fragment_receipt(fragments[0])


def _silent_bands() -> dict:
    return {
        band_name: {"winding": 0, "n_events": 0, "events": []}
        for band_name in AUDITORY_BAND_ORDER
    }


def _real_auditory_fragment_receipt(*, born_tick: int):
    """Same real cochlear-band capture shape proven in
    ``tests/glew_runtime/test_sound_boundary.py`` -- one real nonzero band
    plus five genuinely silent bands."""

    bands = _silent_bands()
    bands["mid"] = {
        "winding": 3,
        "n_events": 5,
        "events": [
            {"t": 0.04 * (i + 1), "dw": (1 if i != 3 else -1), "s": 0.5}
            for i in range(5)
        ],
    }
    fragment = AuditoryPerceptFragment(
        source_id="real-experience-learning-mic",
        born_tick=born_tick,
        sample_rate_hz=200,
        input_sample_count=128,
        bands=bands,
    )
    return auditory_fragment_receipt(fragment)


def _mount_real_chemistry_runtime(
    *, runtime_authentication_key: bytes, runtime_key_id: str
) -> StoryChemistryRuntime:
    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=runtime_authentication_key,
        runtime_key_id=runtime_key_id,
    )
    if mounted.status is not StoryChemistryStatus.MOUNTED or mounted.runtime is None:
        raise ReceiptError(
            f"real production story chemistry failed to mount: {mounted.reason}"
        )
    return mounted.runtime


def _evolve_real_causal_window(
    runtime: StoryChemistryRuntime,
    *,
    scene_id: str,
    descriptors: Sequence[InstantDescriptor],
) -> StoryFrozenKernelInputs:
    """Live one real, N-instant (N >= 2) multimodal scene through the exact
    bridge proven by ``tests/glew_runtime/test_six_sense_boundary_owner.py::
    test_assembled_evolved_sequence_is_accepted_by_the_real_frozen_kernel_bridge``:
    ``observe_six_sense_boundary`` -> ``evolve_story_chemistry_event`` (once
    per instant) -> ``confirm_causal_window_candidate`` ->
    ``build_story_frozen_kernel_inputs``.

    N is driven by how many valid balanced-ternary trit places the scene's
    own typed-language scalar requires (a real, structural requirement of
    ``language.py``'s frozen kernel, not a convenience): the typed-language
    lane must supply exactly one real source timestamp per valid trit, and
    that lane shares one common causal grid with the five real senses, so
    the senses must be observed across at least as many real instants.
    """

    if len(descriptors) < 2:
        raise ReceiptError(
            "a causal window candidate requires at least two real instants"
        )

    events = []
    current_runtime = runtime
    all_outputs: list[tuple] = []
    for index, descriptor in enumerate(descriptors):
        start = Fraction(index)
        end = Fraction(index + 1)
        observed = observe_six_sense_boundary(
            current_runtime,
            event_id=f"{scene_id}-instant-{index + 1}",
            source_time_start=start,
            source_time_end=end,
            visual_fragment_receipt=_real_visual_fragment_receipt(
                fill_value=descriptor.visual_fill_value, seed=descriptor.visual_seed
            ),
            auditory_fragment_receipt=_real_auditory_fragment_receipt(
                born_tick=descriptor.auditory_born_tick
            ),
            touch_descriptor=descriptor.touch_descriptor,
            smell_descriptor=descriptor.smell_descriptor,
            taste_descriptor=descriptor.taste_descriptor,
        )
        if observed.status is not SixSenseBoundaryStatus.OBSERVED:
            raise ReceiptError(
                f"real six-sense boundary owner failed at {scene_id} instant "
                f"{index + 1}: {observed.reason}"
            )
        evolved = evolve_story_chemistry_event(
            runtime=current_runtime, event=observed.event
        )
        if evolved.status is not StoryChemistryStatus.EVOLVED:
            raise ReceiptError(
                f"real story chemistry evolution failed at {scene_id} instant "
                f"{index + 1}: {evolved.reason}"
            )
        events.append(observed.event)
        all_outputs.append(evolved.outputs)
        current_runtime = evolved.runtime

    candidate = confirm_causal_window_candidate(tuple(events))
    if candidate.status is not CausalWindowCandidateStatus.CANDIDATE:
        raise ReceiptError(
            f"{scene_id}'s real instants do not form a causal window "
            f"candidate: {candidate.reason}"
        )

    bridge = build_story_frozen_kernel_inputs(
        runtime=current_runtime,
        output_frames=tuple(all_outputs),
        source_epoch=f"{scene_id}-chemistry-epoch",
    )
    if bridge.status is not StoryKernelBridgeStatus.READY:
        raise ReceiptError(
            f"real frozen-kernel bridge failed for {scene_id}: {bridge.reason}"
        )
    return bridge


def _mount_shared_typed_language_kernel_binding(
    *, scenario_id: str, registry: ReceiptRegistry
) -> tuple[MountedTypedLanguageKernelBinding, ReceiptRegistry]:
    adapter_id = f"{scenario_id}-typed-adapter"
    interface_id = f"{scenario_id}-typed-interface"
    phase_id = f"{scenario_id}-typed-phase"
    phase_kappa = Fraction(1, 7)
    interface_payload = typed_interface_receipt_payload(interface_id)
    phase_payload = typed_phase_calibration_receipt_payload(phase_id, phase_kappa)
    derivation_payload = _canonical_bytes(
        {
            "equation": "F=1+s/2",
            "schema": "glew.real_experience_learning.typed_kernel_derivation.v1",
            "scenario_id": scenario_id,
        }
    )
    binding_payload = typed_language_kernel_binding_receipt_payload(
        adapter_id=adapter_id,
        interface_id=interface_id,
        interface_receipt_sha256=receipt_sha256(interface_payload),
        phase_calibration_receipt_sha256=receipt_sha256(phase_payload),
        derivation_receipt_sha256=receipt_sha256(derivation_payload),
    )
    binding = MountedTypedLanguageKernelBinding(
        adapter_id,
        interface_id,
        receipt_sha256(interface_payload),
        receipt_sha256(phase_payload),
        receipt_sha256(derivation_payload),
        receipt_sha256(binding_payload),
    )
    registry = _extend(
        registry, interface_payload, phase_payload, derivation_payload, binding_payload
    )
    return binding, registry, phase_id, phase_kappa


def _build_typed_language_lane(
    *,
    binding: MountedTypedLanguageKernelBinding,
    phase_id: str,
    phase_kappa: Fraction,
    text: str,
    event_id: str,
    source_epoch: str,
    timestamps: tuple[Fraction, ...],
    registry: ReceiptRegistry,
) -> tuple[TypedLanguageFrozenKernelInput, ReceiptRegistry]:
    if len(text) != 1:
        raise ReceiptError("one real typed-language lane requires one Unicode scalar")
    trits = encode_balanced_ternary_scalar(ord(text))
    valid_times = tuple(
        timestamp for trit, timestamp in zip(trits, timestamps) if trit.valid
    )
    event_payload = typed_language_event_receipt_payload(
        text=text,
        event_id=event_id,
        interface_id=binding.interface_id,
        source_epoch=source_epoch,
        valid_sample_times=valid_times,
    )
    event = TypedLanguageEvent.from_text(
        text=text,
        event_id=event_id,
        interface_id=binding.interface_id,
        source_epoch=source_epoch,
        valid_sample_times=valid_times,
        interface_receipt_sha256=binding.interface_receipt_sha256,
        event_receipt_sha256=receipt_sha256(event_payload),
        phase_calibration_id=phase_id,
        phase_kappa=phase_kappa,
        phase_calibration_receipt_sha256=binding.phase_calibration_receipt_sha256,
    )
    genesis_payload = _canonical_bytes(
        {
            "schema": "glew.real_experience_learning.typed_language_genesis.v1",
            "event_id": event_id,
        }
    )
    state = TypedLanguageState(
        phase_id,
        source_epoch,
        -1,
        Fraction(0),
        Fraction(0),
        receipt_sha256(genesis_payload),
    )
    registry = _extend(registry, event_payload, genesis_payload)
    typed = build_typed_language_frozen_kernel_input(
        event=event,
        initial_state=state,
        kernel_binding=binding,
        receipt_registry=registry,
    )
    return typed, typed.receipt_registry


def _mount_causal_grid(
    *, grid_id: str, timestamps: tuple[Fraction, ...], registry: ReceiptRegistry
) -> tuple[CausalGrid, ReceiptRegistry]:
    weights = tuple(Fraction(1) for _ in timestamps)
    payload = causal_grid_receipt_payload(grid_id, timestamps, weights)
    registry = _extend(registry, payload)
    grid = CausalGrid(grid_id, timestamps, weights, receipt_sha256(payload))
    grid.verify(registry)
    return grid, registry


def _mount_shared_six_lane_infrastructure(
    *,
    scenario_id: str,
    language_port_id: str,
    sense_streams,
    precision_bits: int,
    resonance_precision_bits: int,
    registry: ReceiptRegistry,
) -> tuple[
    MountedFieldTopology,
    MountedSupportDomain,
    MountedResonanceGraph,
    ResonanceOperatorAuthority,
    PrecisionScheduleAuthority,
    ReceiptRegistry,
]:
    fibers = (
        PortFiber(L6Lane.LANGUAGE.value, language_port_id),
        *(PortFiber(stream.lane_id, stream.port_id) for stream in sense_streams),
    )
    topology_payload = field_topology_receipt_payload(
        f"{scenario_id}-topology", fibers
    )
    registry = _extend(registry, topology_payload)
    topology = MountedFieldTopology(
        f"{scenario_id}-topology", fibers, receipt_sha256(topology_payload)
    )
    topology.verify(registry)

    support, registry = mount_support_domain(
        domain_id=f"{scenario_id}-support",
        topology=topology,
        receipt_registry=registry,
    )

    keys = tuple(fiber.key for fiber in fibers)
    edges = tuple(
        RequiredEdge(left, right) for left, right in zip(keys[:-1], keys[1:])
    )
    graph, operator, registry = mount_resonance_graph_and_operator(
        graph_id=f"{scenario_id}-resonance",
        required_edges=edges,
        operator_id=f"{scenario_id}-resonance-operator",
        precision_bits=resonance_precision_bits,
        receipt_registry=registry,
        topology=topology,
    )

    precision, registry = mount_precision_schedule_authority(
        authority_id=f"{scenario_id}-expression-precision",
        maximum_precision_bits=precision_bits,
        receipt_registry=registry,
    )

    return topology, support, graph, operator, precision, registry


def _build_expression(
    *,
    topology: MountedFieldTopology,
    preparation,
    precision: PrecisionScheduleAuthority,
    physical_profile_receipt_sha256: str,
    identity: str,
    registry: ReceiptRegistry,
):
    steps = []
    authority_payloads = []
    for index, event in enumerate(preparation.events):
        source = source_coefficients_for_injection(
            event.injection, event.source_time_end - event.source_time_start
        )
        components = canonical_component_partition(topology.dimension, ())
        authority_id = f"{identity}:field:{index:08d}"
        payload = evolution_authority_receipt_payload(
            authority_id=authority_id,
            physical_profile_receipt_sha256=physical_profile_receipt_sha256,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            map_injection_receipt_sha256=event.injection.receipt_sha256,
            source_time_start=event.source_time_start,
            source_time_end=event.source_time_end,
            source_time_unit="real-experience-learning-structural-time",
            hbar=Fraction(1),
            hamiltonian=(),
            local_rates=(),
            source=source,
            component_partition=components,
            max_connected_component_dimension=1,
            precision_bits=256,
        )
        authority = FieldEvolutionAuthority(
            authority_id=authority_id,
            physical_profile_receipt_sha256=physical_profile_receipt_sha256,
            topology_authority_receipt_sha256=topology.authority_receipt_sha256,
            map_injection_receipt_sha256=event.injection.receipt_sha256,
            source_time_start=event.source_time_start,
            source_time_end=event.source_time_end,
            source_time_unit="real-experience-learning-structural-time",
            hbar=Fraction(1),
            hamiltonian=(),
            local_rates=(),
            source=source,
            max_connected_component_dimension=1,
            precision_bits=256,
            authority_receipt_sha256=receipt_sha256(payload),
        )
        steps.append(FieldExpressionStep(event.injection, authority))
        authority_payloads.append(payload)

    initial_payload = exact_field_state_receipt_payload(
        topology.authority_receipt_sha256,
        preparation.source_time_start,
        tuple(ExactComplex(Fraction(0)) for _ in range(topology.dimension)),
    )
    initial = ExactFieldState(
        topology.authority_receipt_sha256,
        preparation.source_time_start,
        tuple(ExactComplex(Fraction(0)) for _ in range(topology.dimension)),
        receipt_sha256(initial_payload),
    )
    registry = _extend(registry, *authority_payloads, initial_payload)
    expression = create_closed_experience_expression(
        topology=topology,
        initial_state=initial,
        steps=tuple(steps),
        precision_authority=precision,
        receipt_registry=registry,
    )
    registry = _extend(registry, expression.receipt_payload)
    return expression, registry


def _mode_payloads(result: ExpressionModeBoundaryResult) -> tuple[bytes, ...]:
    payloads = [
        result.pre_growth_bank.receipt_payload,
        result.post_growth_bank.receipt_payload,
        result.receipt_payload,
    ]
    for bank in (result.pre_growth_bank, result.post_growth_bank):
        for mode in bank.modes:
            payloads.extend(
                (
                    mode.source_expression.receipt_payload,
                    mode.growth_proof_receipt_payload,
                    mode.receipt_payload,
                )
            )
    return tuple(payloads)


def _bootstrap_and_recognize(
    *,
    topology: MountedFieldTopology,
    precision: PrecisionScheduleAuthority,
    expr_root,
    expr_content,
    registry: ReceiptRegistry,
):
    """Grow the mode bank to rank two with two genuinely independent real
    scenes, then re-recognize each -- the real two-phase bootstrap this
    codebase's own commit conjunction requires (see module docstring)."""

    empty = create_empty_expression_mode_bank(
        topology=topology, precision_authority=precision, receipt_registry=registry
    )
    registry = _extend(registry, empty.receipt_payload)

    root_growth = evaluate_expression_mode_boundary(
        topology=topology,
        bank=empty,
        input_expression=expr_root,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(root_growth))
    if (
        root_growth.status is not ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
        or root_growth.post_growth_bank.rank != 1
    ):
        raise ReceiptError(
            "real root scene did not bootstrap the mode bank as expected: "
            f"{root_growth.status}/{root_growth.reason}"
        )

    content_growth = evaluate_expression_mode_boundary(
        topology=topology,
        bank=root_growth.post_growth_bank,
        input_expression=expr_content,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(content_growth))
    if (
        content_growth.status is not ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
        or content_growth.post_growth_bank.rank != 2
    ):
        raise ReceiptError(
            "real content scene did not bootstrap the mode bank to rank two "
            f"as expected: {content_growth.status}/{content_growth.reason}"
        )

    root_recognition = evaluate_expression_mode_boundary(
        topology=topology,
        bank=content_growth.post_growth_bank,
        input_expression=expr_root,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(root_recognition))
    content_recognition = evaluate_expression_mode_boundary(
        topology=topology,
        bank=content_growth.post_growth_bank,
        input_expression=expr_content,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(content_recognition))

    if root_recognition.status is not ExpressionRecognitionStatus.RECOGNIZED:
        raise ReceiptError(
            "real root scene was not RECOGNIZED against the bootstrapped "
            f"rank-two bank: {root_recognition.status}/{root_recognition.reason}"
        )
    if content_recognition.status is not ExpressionRecognitionStatus.RECOGNIZED:
        raise ReceiptError(
            "real content scene was not RECOGNIZED against the bootstrapped "
            f"rank-two bank: {content_recognition.status}/{content_recognition.reason}"
        )
    if root_recognition.winner_mode_index == content_recognition.winner_mode_index:
        raise ReceiptError(
            "real root and content scenes were not recognized as distinct modes"
        )
    return root_recognition, content_recognition, registry


def _seal(
    *,
    topology: MountedFieldTopology,
    preparation,
    expression,
    recognition: ExpressionModeBoundaryResult,
    identity: str,
    registry: ReceiptRegistry,
) -> tuple[SealedClosedExperience, ReceiptRegistry]:
    rules = tuple(
        L5ApplicabilityRule(
            fiber.lane_id, fiber.port_id, fact, ApplicabilityState.REQUIRED
        )
        for fiber in topology.ordered_port_fibers
        for fact in (GovernedFact.S_UF, GovernedFact.R_UF)
    )
    l5_payload = l5_governance_profile_receipt_payload(
        profile_id=f"{identity}:L5",
        topology_authority_receipt_sha256=topology.authority_receipt_sha256,
        rules=rules,
    )
    l5 = MountedL5GovernanceProfile(
        f"{identity}:L5", topology.authority_receipt_sha256, rules, receipt_sha256(l5_payload)
    )
    registry = _extend(registry, l5_payload)
    sealed = seal_closed_experience(
        experience_id=identity,
        structural_time_unit="real-experience-learning-structural-time",
        preparation=preparation,
        topology=topology,
        l5_governance=l5,
        expression=expression,
        recognition=recognition,
        receipt_registry=registry,
    )
    return sealed, _merge(registry, sealed.receipt_registry)


def _mount_simple_pre_window(
    *, identity: str, registry: ReceiptRegistry
) -> tuple[MountedPreWindowState, ReceiptRegistry]:
    """A minimal, self-contained pre-window state used only to enumerate L6
    physical-tangent perturbation cases (see module docstring: L6 structural
    lock concerns lane geometry, not scene content, and is independent of
    the recognition mode bank; the existing test suite's own
    ``_actual_authorities``/``_physical_l6`` helpers build exactly this kind
    of opaque, receipted-but-uncomputed pre-window for the same reason)."""

    state_payloads = {
        name: f"{identity}-pre-window-{name}".encode()
        for name in ("chemistry", "field", "mode", "memory", "l6")
    }
    state_payload = pre_window_state_receipt_payload(
        state_id=f"{identity}-pre-window",
        chemistry_state_receipt_sha256=receipt_sha256(state_payloads["chemistry"]),
        field_state_receipt_sha256=receipt_sha256(state_payloads["field"]),
        mode_state_receipt_sha256=receipt_sha256(state_payloads["mode"]),
        memory_state_receipt_sha256=receipt_sha256(state_payloads["memory"]),
        l6_state_receipt_sha256=receipt_sha256(state_payloads["l6"]),
    )
    pre_window = MountedPreWindowState(
        f"{identity}-pre-window",
        receipt_sha256(state_payloads["chemistry"]),
        receipt_sha256(state_payloads["field"]),
        receipt_sha256(state_payloads["mode"]),
        receipt_sha256(state_payloads["memory"]),
        receipt_sha256(state_payloads["l6"]),
        receipt_sha256(state_payload),
    )
    registry = _extend(registry, *state_payloads.values(), state_payload)
    return pre_window, registry


def _physical_replay_bundle(
    *,
    lane: L6Lane,
    native_port_id: str,
    pre_window: MountedPreWindowState,
    payloads: list[bytes],
) -> NativePortReplayBundle:
    """Mirrors ``tests/glew_runtime/test_closed_experience_provider.py::
    _physical_replay_bundle`` exactly (same real production constructors),
    reimplemented here with production-only imports. The response-law
    constants below are arbitrary receipted placeholders -- see the module
    docstring's "What remains asserted" section."""

    provider_id = f"real-experience-learning-{lane.value}-native-provider"
    profile_id = f"real-experience-learning-{lane.value}-native-profile"
    if lane is L6Lane.LANGUAGE:
        coordinate_source = b"real-experience-learning-typed-trit-authority"
        sensor_coordinates: tuple[SensorNativeCoordinate, ...] = ()
        language_coordinates = (
            LanguageTritCoordinate(
                "typed-utterance-trit",
                TypedTrit.QUIESCENT,
                receipt_sha256(coordinate_source),
            ),
        )
    else:
        coordinate_source = f"real-experience-learning-{lane.value}-code-authority".encode()
        sensor_coordinates = (
            SensorNativeCoordinate(
                f"{lane.value}-native-code",
                1,
                0,
                2,
                Fraction(1),
                receipt_sha256(coordinate_source),
            ),
        )
        language_coordinates = ()
    profile_payload = native_perturbation_profile_receipt_payload(
        profile_id=profile_id,
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        sensor_coordinates=sensor_coordinates,
        language_trit_coordinates=language_coordinates,
    )
    profile = MountedNativePerturbationProfile(
        profile_id,
        lane,
        provider_id,
        native_port_id,
        sensor_coordinates,
        language_coordinates,
        receipt_sha256(profile_payload),
    )
    payloads.extend((coordinate_source, profile_payload))

    cases = enumerate_native_replay_cases(profile, pre_window)
    branch_id = f"real-experience-learning-{lane.value}-replay-branch"
    cell_id = f"real-experience-learning-{lane.value}-replay-cell"
    base = tuple(Fraction(10 + index, 3) for index in range(7))
    response_gradient = tuple(Fraction(index + 1) for index in range(7))
    responses = []
    for case in cases:
        response_id = f"{profile_id}:response:{case.case_index}"
        source = f"{response_id}:exact-L4-replay-source".encode()
        values = tuple(
            value + case.native_delta * gradient
            for value, gradient in zip(base, response_gradient)
        )
        l4_response = ExactL4Response(*values)
        response_payload = native_l4_replay_response_receipt_payload(
            response_id=response_id,
            lane=lane,
            provider_id=provider_id,
            native_port_id=native_port_id,
            case_receipt_sha256=case.receipt_sha256,
            profile_receipt_sha256=profile.authority_receipt_sha256,
            pre_window_state_receipt_sha256=pre_window.authority_receipt_sha256,
            branch_id=branch_id,
            cell_id=cell_id,
            l4_response=l4_response,
            source_operator_receipt_sha256=receipt_sha256(source),
        )
        payloads.extend((source, response_payload))
        responses.append(
            NativeL4ReplayResponse(
                response_id,
                lane,
                provider_id,
                native_port_id,
                case.receipt_sha256,
                profile.authority_receipt_sha256,
                pre_window.authority_receipt_sha256,
                branch_id,
                cell_id,
                l4_response,
                receipt_sha256(source),
                receipt_sha256(response_payload),
            )
        )
    response_tuple = tuple(responses)
    completeness_source = f"{profile_id}:complete-native-replay-source".encode()
    response_set_payload = native_response_set_receipt_payload(
        response_set_id=f"{profile_id}:response-set",
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window.authority_receipt_sha256,
        responses=response_tuple,
        source_completeness_receipt_sha256=receipt_sha256(completeness_source),
    )
    response_set = MountedNativeResponseSet(
        f"{profile_id}:response-set",
        lane,
        provider_id,
        native_port_id,
        profile.authority_receipt_sha256,
        pre_window.authority_receipt_sha256,
        response_tuple,
        receipt_sha256(completeness_source),
        receipt_sha256(response_set_payload),
    )
    branch_source = f"{profile_id}:same-branch-cell-source".encode()
    branch_payload = same_branch_cell_proof_receipt_payload(
        proof_id=f"{profile_id}:same-branch-cell",
        lane=lane,
        provider_id=provider_id,
        native_port_id=native_port_id,
        profile_receipt_sha256=profile.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window.authority_receipt_sha256,
        branch_id=branch_id,
        cell_id=cell_id,
        response_receipt_sha256s=tuple(
            value.receipt_sha256 for value in response_tuple
        ),
        source_operator_receipt_sha256=receipt_sha256(branch_source),
    )
    branch_proof = MountedSameBranchCellProof(
        f"{profile_id}:same-branch-cell",
        lane,
        provider_id,
        native_port_id,
        profile.authority_receipt_sha256,
        pre_window.authority_receipt_sha256,
        branch_id,
        cell_id,
        tuple(value.receipt_sha256 for value in response_tuple),
        receipt_sha256(branch_source),
        receipt_sha256(branch_payload),
    )
    payloads.extend(
        (completeness_source, response_set_payload, branch_source, branch_payload)
    )
    return NativePortReplayBundle(profile, response_set, branch_proof)


def _physical_l6_evaluation(
    *,
    topology: MountedFieldTopology,
    pre_window: MountedPreWindowState,
    registry: ReceiptRegistry,
) -> tuple[L6Evaluation, ReceiptRegistry]:
    payloads: list[bytes] = []
    bundles = tuple(
        _physical_replay_bundle(
            lane=L6Lane(fiber.lane_id),
            native_port_id=fiber.port_id,
            pre_window=pre_window,
            payloads=payloads,
        )
        for fiber in topology.ordered_port_fibers
    )
    registry = _extend(registry, *payloads)
    production = produce_physical_l6_tangents(
        bundles=bundles, pre_window_state=pre_window, receipt_registry=registry
    )
    if production.status is not PhysicalTangentProductionStatus.KNOWN:
        raise ReceiptError(
            f"real physical L6 tangent production failed: {production.reason}"
        )
    registry = production.receipt_registry
    completeness = {
        value.lane: value.receipt_sha256
        for value in production.lane_completeness_receipts
    }
    base_u_star = {
        value.profile.lane: value.response_set.responses[0].l4_response.U_star_k
        for value in production.derived_ports
    }
    active_lanes = tuple(
        ActiveLaneState(lane, base_u_star[lane], True, completeness[lane])
        for lane in sorted(completeness, key=lambda value: LANE_ORDER.index(value))
    )
    predicates = L6PredicateInputs(active_lanes, True)
    evaluation = evaluate_l6(production.candidate_constraints.stack, predicates, registry)
    return evaluation, registry


def _commit_real_scene(
    *,
    identity: str,
    sealed: SealedClosedExperience,
    topology: MountedFieldTopology,
    l6_evaluation: L6Evaluation,
    registry: ReceiptRegistry,
) -> tuple[CommittedCoexperience, ReceiptRegistry]:
    experience_digest = sealed.closed_experience.authority_receipt_sha256
    topology_digest = topology.authority_receipt_sha256

    safe_profile = _canonical_bytes(
        {
            "identity": identity,
            "schema": "glew.real_experience_learning.integrity_profile.v1",
        }
    )
    fact_ids = ("chemistry", "field", "persistence")
    safe_scope_payload = safe_mode_scope_receipt_payload(
        scope_id=f"{identity}:safe-scope",
        topology_authority_receipt_sha256=topology_digest,
        required_fact_ids=fact_ids,
        source_profile_receipt_sha256=receipt_sha256(safe_profile),
    )
    safe_scope = MountedSafeModeScope(
        f"{identity}:safe-scope",
        topology_digest,
        fact_ids,
        receipt_sha256(safe_profile),
        receipt_sha256(safe_scope_payload),
    )
    facts = []
    fact_payloads = []
    for fact_id in fact_ids:
        source = f"{identity}:integrity:{fact_id}".encode()
        payload = integrity_fact_receipt_payload(
            fact_id=fact_id,
            state=IntegrityFactState.CLEAR,
            topology_authority_receipt_sha256=topology_digest,
            closed_experience_receipt_sha256=experience_digest,
            source_operator_receipt_sha256=receipt_sha256(source),
        )
        facts.append(
            IntegrityFact(
                fact_id,
                IntegrityFactState.CLEAR,
                topology_digest,
                experience_digest,
                receipt_sha256(source),
                receipt_sha256(payload),
            )
        )
        fact_payloads.extend((source, payload))
    registry = _extend(registry, safe_profile, safe_scope_payload, *fact_payloads)
    safe = evaluate_safe_mode(
        authority_id=f"{identity}:safe",
        topology_authority_receipt_sha256=topology_digest,
        closed_experience_receipt_sha256=experience_digest,
        scope=safe_scope,
        facts=tuple(facts),
        receipt_registry=registry,
    )
    if safe.disposition is not AuthorityDisposition.PASS:
        raise ReceiptError(f"real safe-mode evaluation did not pass for {identity}")
    registry = _extend(registry, *safe.generated_receipt_payloads)

    origin_source = f"{identity}:fresh-origin-source".encode()
    origin_payload = experience_origin_authority_receipt_payload(
        origin_id=f"{identity}:fresh-origin",
        kind=ExperienceOriginKind.FRESH_EXTERNAL,
        profile_binding_sha256=registry.profile_binding_sha256,
        topology_authority_receipt_sha256=topology_digest,
        closed_experience_receipt_sha256=experience_digest,
        source_authority_receipt_sha256=receipt_sha256(origin_source),
    )
    origin = ExperienceOriginAuthority(
        f"{identity}:fresh-origin",
        ExperienceOriginKind.FRESH_EXTERNAL,
        registry.profile_binding_sha256,
        topology_digest,
        experience_digest,
        receipt_sha256(origin_source),
        receipt_sha256(origin_payload),
    )
    registry = _extend(registry, origin_source, origin_payload)

    energy_derivation = f"{identity}:memory-energy-derivation".encode()
    physical_profile = sealed.expression.steps[0].authority.physical_profile_receipt_sha256
    energy_payload = memory_energy_authority_receipt_payload(
        authority_id=f"{identity}:memory-energy",
        energy_unit_id="real-experience-learning-energy-unit",
        exact_memory_energy=Fraction(1),
        derivation_receipt_sha256=receipt_sha256(energy_derivation),
        physical_profile_receipt_sha256=physical_profile,
    )
    energy = MemoryEnergyAuthority(
        f"{identity}:memory-energy",
        "real-experience-learning-energy-unit",
        Fraction(1),
        receipt_sha256(energy_derivation),
        physical_profile,
        receipt_sha256(energy_payload),
    )
    registry = _extend(registry, energy_derivation, energy_payload)
    event = evaluate_event_support(
        authority_id=f"{identity}:R-event",
        origin=origin,
        topology=topology,
        closed_experience_receipt_sha256=experience_digest,
        expression=sealed.expression,
        memory_energy=energy,
        receipt_registry=registry,
    )
    if event.status is not EventSupportEvaluationStatus.RESOLVED:
        raise ReceiptError(f"real event-support evaluation did not resolve for {identity}")
    registry = _extend(registry, *event.generated_receipt_payloads)

    l6_payload = l6_evaluation_receipt_payload(l6_evaluation)
    l6_scope_payload = l6_scope_authority_receipt_payload(
        authority_id=f"{identity}:L6-scope",
        topology_authority_receipt_sha256=topology_digest,
        closed_experience_receipt_sha256=experience_digest,
        l6_evaluation_receipt_sha256=receipt_sha256(l6_payload),
    )
    l6_scope = L6ScopeAuthority(
        f"{identity}:L6-scope",
        topology_digest,
        experience_digest,
        receipt_sha256(l6_payload),
        receipt_sha256(l6_scope_payload),
    )

    # Global-UF: asserted, not computed -- see module docstring "What
    # remains asserted rather than computed" for why no real production
    # GlobalUFReplayProvider exists yet to compute this genuinely.
    global_source = _canonical_bytes(
        {
            "identity": identity,
            "scope": "real_experience_learning_asserted_global_uf_authority",
            "schema": "glew.real_experience_learning.global_uf_source.v1",
        }
    )
    global_payload = binary_authority_receipt_payload(
        authority_id=f"{identity}:global-UF",
        kind=BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        disposition=AuthorityDisposition.PASS,
        topology_authority_receipt_sha256=topology_digest,
        closed_experience_receipt_sha256=experience_digest,
        source_operator_receipt_sha256=receipt_sha256(global_source),
    )
    global_uf = BinaryCommitAuthority(
        f"{identity}:global-UF",
        BinaryAuthorityKind.GLOBAL_UF_VALIDATION,
        AuthorityDisposition.PASS,
        topology_digest,
        experience_digest,
        receipt_sha256(global_source),
        receipt_sha256(global_payload),
    )
    registry = _extend(registry, l6_payload, l6_scope_payload, global_source, global_payload)

    decision = evaluate_commit_boundary(
        topology=topology,
        recognition=sealed.recognition,
        l6_evaluation=l6_evaluation,
        l6_scope=l6_scope,
        closed_experience=sealed.closed_experience,
        safe_mode=safe.authority,
        event_support=event.authority,
        evidence=sealed.evidence,
        l5_applicability=sealed.l5_applicability,
        global_uf_validation=global_uf,
        receipt_registry=registry,
    )
    if decision.status is not CommitStatus.COMMIT:
        raise ReceiptError(
            f"real commit boundary conjunction did not commit {identity}: "
            f"{decision.findings}"
        )
    registry = _extend(registry, decision.receipt_payload)
    winner = sealed.recognition.winner_mode_index
    if winner is None:
        raise ReceiptError(f"committed real scene {identity} lacks a recognized mode")
    committed = CommittedCoexperience(
        decision, sealed, sealed.recognition.pre_growth_bank.modes[winner]
    )
    committed.verify(registry)
    return committed, registry


# ---------------------------------------------------------------------------
# Public result and orchestrator
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RealMultimodalLearningResult:
    """Everything produced by one real, end-to-end first-learned-expression
    cycle: two independently lived, genuinely committed real scenes, the
    clean genesis learned-binding state, and the state after learning the
    content scene's coexperienced typed scalar."""

    root_committed: CommittedCoexperience
    content_committed: CommittedCoexperience
    initial_relation: CommittedModeRelation
    genesis: LearnedBindingState
    learned: LearnedBindingState
    content_language: TypedLanguageFrozenKernelInput


def learn_one_real_multimodal_expression(
    *,
    scenario_id: str = "real-experience-learning",
    chemistry_authentication_key: bytes = b"real experience learning pipeline chemistry runtime secret",
    chemistry_authentication_key_id: str = "real-experience-learning-runtime-key",
    root_text: str = "a",
    content_text: str = "b",
    precision_bits: int = 4096,
    resonance_precision_bits: int = 64,
) -> RealMultimodalLearningResult:
    """Learn one real, multimodal, first-ever expression end to end.

    Lives two genuinely independent real scenes (each two real, causally
    ordered instants of sight/sound/touch/smell/taste plus one real typed
    Unicode scalar), bootstraps the expression-mode bank to rank two with
    them (the real requirement documented in this module's docstring),
    re-recognizes each against the resulting bank, seals, evaluates real
    Fixed-42 L6 structural lock, evaluates the real fail-closed commit
    conjunction for both, and -- only because both genuinely commit --
    learns the content scene's coexperienced typed scalar as the first
    successor of a clean genesis ``LearnedBindingState``.

    Raises :class:`~dsf_ai_service.glew_runtime.model.ReceiptError` with a
    precise, undisguised reason at the first authority that fails to behave
    as a real first-learned-expression requires (never silently substitutes
    a synthetic shortcut).
    """

    # Five real, causally ordered instants per scene: the real, structural
    # floor is "at least two" (six_sense_boundary_owner.py section 9.1), but
    # both root_text and content_text's real balanced-ternary encodings
    # require five valid trit places (see _build_typed_language_lane), and
    # the typed-language lane must share one common causal grid with the
    # five real senses -- so the senses are lived across five real instants
    # too, not merely the structural floor of two.
    root_descriptors = (
        InstantDescriptor(0.8, 101, 0, "warm", None, None),
        InstantDescriptor(0.5, 102, 100, None, "floral", None),
        InstantDescriptor(0.65, 103, 200, "cool", None, None),
        InstantDescriptor(0.4, 104, 300, None, None, "savory"),
        InstantDescriptor(0.75, 105, 400, "dry", None, None),
    )
    content_descriptors = (
        InstantDescriptor(0.3, 201, 10, "cold", None, "sweet"),
        InstantDescriptor(0.9, 202, 110, None, "smoky", None),
        InstantDescriptor(0.2, 203, 210, "rough", None, None),
        InstantDescriptor(0.6, 204, 310, None, "fruity", None),
        InstantDescriptor(0.1, 205, 410, None, None, "bitter"),
    )

    # -- root scene: lived first, used only to bootstrap the mode bank and
    #    to seed the clean genesis learned-binding state --
    root_runtime = _mount_real_chemistry_runtime(
        runtime_authentication_key=chemistry_authentication_key,
        runtime_key_id=chemistry_authentication_key_id,
    )
    root_bridge = _evolve_real_causal_window(
        root_runtime,
        scene_id=f"{scenario_id}-root",
        descriptors=root_descriptors,
    )
    registry = root_bridge.receipt_registry

    binding, registry, phase_id, phase_kappa = _mount_shared_typed_language_kernel_binding(
        scenario_id=scenario_id, registry=registry
    )

    grid, registry = _mount_causal_grid(
        grid_id=f"{scenario_id}-grid",
        timestamps=tuple(Fraction(index) for index in range(1, len(root_descriptors) + 1)),
        registry=registry,
    )

    root_language, registry = _build_typed_language_lane(
        binding=binding,
        phase_id=phase_id,
        phase_kappa=phase_kappa,
        text=root_text,
        event_id=f"{scenario_id}-root-language",
        source_epoch=f"{scenario_id}-root-language-epoch",
        timestamps=grid.timestamps,
        registry=registry,
    )

    topology, support, resonance_graph, resonance_operator, precision, registry = (
        _mount_shared_six_lane_infrastructure(
            scenario_id=scenario_id,
            language_port_id=root_language.stream.port_id,
            sense_streams=root_bridge.streams,
            precision_bits=precision_bits,
            resonance_precision_bits=resonance_precision_bits,
            registry=registry,
        )
    )

    root_preparation = prepare_closed_experience_evidence(
        streams=(root_language.stream, *root_bridge.streams),
        kernel_inputs=(root_language.kernel_input, *root_bridge.kernel_inputs),
        source_time_start=Fraction(0),
        grid=grid,
        support_domain=support,
        resonance_graph=resonance_graph,
        resonance_operator=resonance_operator,
        topology=topology,
        receipt_registry=registry,
    )
    if isinstance(root_preparation, ClosedExperienceProviderUnknown):
        raise ReceiptError(
            f"real root scene evidence preparation failed: {root_preparation.reason}"
        )
    registry = root_preparation.receipt_registry

    physical_profile_payload = _canonical_bytes(
        {
            "identity": f"{scenario_id}-shared-field-profile",
            "schema": "glew.real_experience_learning.exact_field_profile.v1",
        }
    )
    registry = _extend(registry, physical_profile_payload)
    physical_profile_receipt_sha256 = receipt_sha256(physical_profile_payload)

    root_expression, registry = _build_expression(
        topology=topology,
        preparation=root_preparation,
        precision=precision,
        physical_profile_receipt_sha256=physical_profile_receipt_sha256,
        identity=f"{scenario_id}-root",
        registry=registry,
    )

    # -- content scene: the real multimodal expression actually being
    #    learned; a genuinely independent chemistry mount/evolution, but
    #    sharing the same topology/support/resonance/precision authorities
    #    (same packaged production chemistry profile => identical port ids) --
    content_runtime = _mount_real_chemistry_runtime(
        runtime_authentication_key=chemistry_authentication_key,
        runtime_key_id=chemistry_authentication_key_id,
    )
    content_bridge = _evolve_real_causal_window(
        content_runtime,
        scene_id=f"{scenario_id}-content",
        descriptors=content_descriptors,
    )
    registry = _merge(registry, content_bridge.receipt_registry)

    content_language, registry = _build_typed_language_lane(
        binding=binding,
        phase_id=phase_id,
        phase_kappa=phase_kappa,
        text=content_text,
        event_id=f"{scenario_id}-content-language",
        source_epoch=f"{scenario_id}-content-language-epoch",
        timestamps=grid.timestamps,
        registry=registry,
    )

    content_preparation = prepare_closed_experience_evidence(
        streams=(content_language.stream, *content_bridge.streams),
        kernel_inputs=(content_language.kernel_input, *content_bridge.kernel_inputs),
        source_time_start=Fraction(0),
        grid=grid,
        support_domain=support,
        resonance_graph=resonance_graph,
        resonance_operator=resonance_operator,
        topology=topology,
        receipt_registry=registry,
    )
    if isinstance(content_preparation, ClosedExperienceProviderUnknown):
        raise ReceiptError(
            f"real content scene evidence preparation failed: {content_preparation.reason}"
        )
    registry = content_preparation.receipt_registry

    content_expression, registry = _build_expression(
        topology=topology,
        preparation=content_preparation,
        precision=precision,
        physical_profile_receipt_sha256=physical_profile_receipt_sha256,
        identity=f"{scenario_id}-content",
        registry=registry,
    )

    root_recognition, content_recognition, registry = _bootstrap_and_recognize(
        topology=topology,
        precision=precision,
        expr_root=root_expression,
        expr_content=content_expression,
        registry=registry,
    )

    root_sealed, registry = _seal(
        topology=topology,
        preparation=root_preparation,
        expression=root_expression,
        recognition=root_recognition,
        identity=f"{scenario_id}-root",
        registry=registry,
    )
    content_sealed, registry = _seal(
        topology=topology,
        preparation=content_preparation,
        expression=content_expression,
        recognition=content_recognition,
        identity=f"{scenario_id}-content",
        registry=registry,
    )

    pre_window, registry = _mount_simple_pre_window(identity=scenario_id, registry=registry)
    l6_evaluation, registry = _physical_l6_evaluation(
        topology=topology, pre_window=pre_window, registry=registry
    )

    root_committed, registry = _commit_real_scene(
        identity=f"{scenario_id}-root",
        sealed=root_sealed,
        topology=topology,
        l6_evaluation=l6_evaluation,
        registry=registry,
    )
    content_committed, registry = _commit_real_scene(
        identity=f"{scenario_id}-content",
        sealed=content_sealed,
        topology=topology,
        l6_evaluation=l6_evaluation,
        registry=registry,
    )

    initial_relation, registry = derive_committed_mode_relation(
        relation_id=f"{scenario_id}-root-relation",
        committed=root_committed,
        output_source_receipt_sha256=root_committed.commit.receipt_sha256,
        receipt_registry=registry,
    )
    genesis = create_learned_binding_genesis(
        state_id=f"{scenario_id}-state",
        expression_id=f"{scenario_id}-expression",
        initial_relation=initial_relation,
        receipt_registry=registry,
    )

    learned = learn_committed_binding_transaction(
        state=genesis,
        committed=content_committed,
        coexperienced_output=CoexperiencedOutput.from_typed_scalar(content_language),
        prior_relation=initial_relation,
        relation_id=f"{scenario_id}-content-relation",
        expression_close=False,
        receipt_registry=genesis.receipt_registry,
    )

    return RealMultimodalLearningResult(
        root_committed=root_committed,
        content_committed=content_committed,
        initial_relation=initial_relation,
        genesis=genesis,
        learned=learned,
        content_language=content_language,
    )


def close_real_multimodal_expression(
    result: RealMultimodalLearningResult,
) -> LearnedBindingState:
    """Learn one further, explicit no-output expression-close successor of
    the root committed scene, exactly mirroring
    ``tests/glew_runtime/test_expression_learning.py::_learn_close``. Not
    required for Step 4's own proof (which only requires one learned
    expression to survive a checkpoint/restore round trip), but included so
    a caller can exercise the full learn -> close cycle if desired."""

    if result.learned.pending_relation is None:
        raise ReceiptError("learned state has no pending relation to close")
    no_output, registry = create_coexperienced_no_output(
        event_id=f"{result.genesis.state_id}-explicit-close",
        sealed=result.root_committed.sealed,
        source_authority_receipt_sha256=result.root_committed.commit.receipt_sha256,
        receipt_registry=result.learned.receipt_registry,
    )
    return learn_committed_binding_transaction(
        state=result.learned,
        committed=result.root_committed,
        coexperienced_output=CoexperiencedOutput.from_no_output(no_output),
        prior_relation=result.learned.pending_relation,
        relation_id=f"{result.genesis.state_id}-close-relation",
        expression_close=True,
        receipt_registry=registry,
    )


__all__ = (
    "InstantDescriptor",
    "RealMultimodalLearningResult",
    "close_real_multimodal_expression",
    "learn_one_real_multimodal_expression",
)
