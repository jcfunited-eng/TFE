"""Real cold-start bootstrap for ``ProductionCleanConversationEngine``.

A prior investigation (see
``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
Steps 1-6, already committed) found that every real construction anywhere in
this codebase of a :class:`~dsf_ai_service.glew_runtime.six_lane_runtime_mount.MountedSixLaneRuntime`
plus a :class:`~dsf_ai_service.glew_runtime.expression_learning.LearnedBindingState`
plus a :class:`~dsf_ai_service.glew_runtime.model.ReceiptRegistry` plus an
:class:`~dsf_ai_service.substrate.immutable_generation_store.ImmutableGenerationStore`
is test-only and synthetic (for example
``tests/glew_runtime/test_clean_conversation_engine.py``'s
``_build_mounted_runtime()``/``fixture()``, which hand-build every authority
from literal test constants). There was no function anywhere that builds this
real machinery either from actual persisted production checkpoint files, or,
when none yet exists, from a real, honest fresh-genesis starting point. This
module closes exactly that gap. It introduces no new field physics, no new
commit rule, no new recognition rule, and no new persistence schema: every
authority below is built by calling the identical real, already-committed
production functions ``six_lane_runtime_mount.mount_six_lane_runtime``,
``expression_learning.create_learned_binding_genesis`` /
``learn_committed_binding_transaction`` /
``restore_learned_binding_checkpoint``,
``recall_story_episode_archive.restore_recall_story_archive_checkpoint``,
``generation_identity.bind_generation_identity`` /
``verify_generation_identity_binding``, and
``immutable_generation_store.ImmutableGenerationStore`` already prove correct
in isolation.

Two real, honest gaps this module does NOT invent a fix for (see "Honest
remaining gaps" below): (1) no production constructor exists anywhere in this
repository for ``StorySensorPortAuthority``, so this module requires it as a
caller-supplied input, exactly as ``six_lane_runtime_mount.py`` itself already
documents; (2) no checkpoint/restore mechanism exists anywhere in this
repository for ``ExpressionModeBank`` growth, so a restored generation's mode
bank starts empty (rank zero) every process boot regardless of how much has
previously been learned -- restored ``LearnedBindingState`` content is real
and byte-verified, but not immediately reachable through recognition until
the substrate lives enough new experience to regrow its own bank.

Why cold-start still requires two real lived scenes
------------------------------------------------------
``LearnedBindingState`` has no "truly empty" genesis: ``expression_learning.
create_learned_binding_genesis`` requires a real, already-committed
``CommittedModeRelation`` as its ``initial_relation``, and ``commit.py``'s own
fail-closed conjunction can never reach ``CommitStatus.COMMIT`` against a mode
bank with fewer than two independent modes (see
``real_experience_learning_pipeline.py``'s own module docstring, "The
bootstrap requirement" -- a real, cited finding, not a workaround invented
here). So even the most honest possible "nothing has ever been learned yet"
starting point requires this module to live two real, mutually independent
scenes through the same real six-lane pipeline
``ProductionCleanConversationEngine`` itself uses for every later turn,
grow the mode bank from empty to rank two, and commit exactly one of them
(never the second) to seed ``create_learned_binding_genesis``'s own
``initial_relation``. The returned state's own ``initial_event`` is always
``None`` -- nothing beyond that root relation is ever learned here, so no
"fake learned content" is fabricated; this exactly matches the governing
spec's own Step 4 proof requirement and mirrors, but does not reuse verbatim,
``real_experience_learning_pipeline.learn_one_real_multimodal_expression``
(that function cannot be reused directly: it mounts its own narrower
support/resonance/topology authorities via
``six_lane_runtime_mount.mount_support_domain`` /
``mount_resonance_graph_and_operator`` /
``mount_precision_schedule_authority`` alone, never the full
``mount_six_lane_runtime`` thirteen-authority bundle
``ProductionCleanConversationEngine`` actually requires).

Real profile files already on disk vs. still-synthetic caller inputs
-------------------------------------------------------------------------
Already real, ratified, committed files this module reads directly (never
fabricated):

* ``dsf_ai_service/glew_runtime/profiles/production_virtual_story_chemistry_profile_v1.json``
  -- read verbatim via ``story_chemistry.production_story_chemistry_profile_payload()``
  (``importlib.resources``, the same real accessor
  ``mount_packaged_production_story_chemistry`` itself already uses).
* ``dsf_ai_service/glew_runtime/GLEW_LANGUAGE_WEAVE_PROFILE_v1.json`` and
  ``GLEW_UPSTREAM_PROFILE_v1.json`` document (by recorded SHA-256 digest) that
  the above chemistry file, read this same way, is the ratified five-sense
  profile authority -- this module's use of it is therefore the ratified
  choice, not an invented one. Neither weave file is itself consumed as bytes
  by ``mount_six_lane_runtime``; they are ratification records, not runtime
  input shapes.

Still genuinely synthetic / caller-supplied, because no ratified production
source or constructor exists anywhere in this repository today (named
honestly, not papered over -- see ``six_lane_runtime_mount.py``'s own module
docstring for the identical disclosure at the mount layer):

* The story-chemistry HMAC authentication key/key-id (``mount_packaged_
  production_story_chemistry`` itself requires this as a runtime secret;
  nothing in this repository ratifies or ships a production value for it).
* ``StorySensorPortAuthority`` per port, plus each one's own two receipt
  payloads (``sensor_ports``/``sensor_port_receipt_payloads``) -- no
  production ``mount_story_sensor_port_authority``-equivalent constructor
  exists anywhere (``six_lane_runtime_mount.py`` names this exact gap in its
  own ``mount_story_sensor_states`` docstring).
* Every identifier, edge set, and precision-bit ceiling
  ``SixLaneRuntimeBootstrapParameters`` bundles below -- these are
  operational/product policy decisions ``six_lane_runtime_mount.py`` itself
  deliberately refuses to default (see that module's docstring's "Genuine
  physical/computational constraint vs. arbitrary test-fixture choice"
  section); this module does not invent ratified values for them either.
* The checkpoint HMAC authentication key/key-id, and the genesis identity
  triple (``GenerationIdentityParameters``) -- real secret/identity material
  a caller must supply from wherever it is really managed (for example
  ``genesis.py``'s own ``create_clean_genesis``/``restore_clean_genesis`` for
  the identity triple). This module does not itself call ``genesis.py``:
  that module owns a separate, independent generation lifecycle (its own
  ``GLEW_GENESIS_ROOT``-rooted store, its own ``fixed42_provider``/
  ``field_provider`` coupling) that ``generation_identity.py``'s own
  docstring already documents as a deliberately deferred reconciliation
  ("one side of it does not exist yet") -- this module does not invent that
  reconciliation, only accepts its eventual real output as a plain input.
* ``fresh_recall_provider`` -- explicitly excluded per this module's charter;
  a separate, concurrent effort owns that gap (see
  ``clean_conversation_engine.py``'s own "The fresh-recall gap").

Persistent storage root convention
--------------------------------------
The legacy v5 engine locates its own EFS-backed state through ``dsf_ai_service/
app.py``'s ``STATE_DIR`` env var (default ``"state"``), and that same module
already derives a *second*, sibling ``ImmutableGenerationStore`` root for its
own sealed-state generation store via ``GUALA_GENERATION_STORE_ROOT``
(default: ``STATE_DIR``'s own parent directory, ``STATE_DIR``'s own basename
plus ``"-sealed"``). ``dsf_ai_service/glew_runtime/conformance.py`` separately
roots ``genesis.py``'s own clean executable-profile genesis at
``GLEW_GENESIS_ROOT`` (no default -- required explicitly, "legacy discovery
and migration are forbidden"). This module's own checkpoint files
(``clean_conversation_learning_checkpoint.json`` /
``clean_conversation_archive_checkpoint.json`` /
``clean_conversation_generation_identity_binding.json``) are a *third*,
independent fixed file set -- reusing either of the above roots would corrupt
or collide with an unrelated store's own ``CURRENT``/``generations`` layout
(``ImmutableGenerationStore`` binds one root to exactly one required-file
set). :func:`resolve_default_generation_store_root` therefore introduces one
more dedicated env var, ``GLEW_CONVERSATION_ENGINE_STORE_ROOT``, defaulting
(mirroring the legacy engine's own sibling-of-``STATE_DIR`` derivation style)
to a sibling of ``STATE_DIR`` named ``STATE_DIR``'s basename plus
``"-glew-conversation-engine"`` -- distinct from both the legacy engine's own
``"-sealed"`` sibling and from ``GLEW_GENESIS_ROOT``. The main bootstrap
function itself never reads environment variables directly (it takes
``generation_store_root`` as a plain, explicit ``Path``, exactly like every
other real constructor in this package) -- ``resolve_default_generation_store_root``
is an optional, separate convenience a real caller may use to resolve that
path the same way the rest of this codebase already resolves its own
storage roots.
"""

from __future__ import annotations

import dataclasses
import json
import os
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Mapping

from .clean_conversation_engine import (
    ARCHIVE_CHECKPOINT_RELATIVE_PATH,
    CHECKPOINT_RELATIVE_PATHS,
    GENERATION_IDENTITY_BINDING_RELATIVE_PATH,
    LEARNING_CHECKPOINT_RELATIVE_PATH,
    GenerationIdentityParameters,
    ProductionCleanConversationEngine,
    _build_commit_providers,
    _scene_descriptors,
)
from .closed_experience import ClosedExperienceProviderUnknown, prepare_closed_experience_evidence
from .commit import CommitStatus, evaluate_commit_boundary
from .expression_learning import (
    CommittedCoexperience,
    CommittedModeRelation,
    LearnedBindingState,
    create_learned_binding_genesis,
    derive_committed_mode_relation,
    restore_learned_binding_checkpoint,
)
from .expression_modes import ExpressionModeBoundaryResult, ExpressionRecognitionStatus, evaluate_expression_mode_boundary
from .field import HamiltonianEntry, LocalRate
from .generation_identity import bind_generation_identity, verify_generation_identity_binding
from .language import TypedLanguageFrozenKernelInput
from .model import ReceiptError, ReceiptRecord, ReceiptRegistry, receipt_sha256
from .operators import PortKey, RequiredEdge
from .real_experience_learning_pipeline import (
    _build_expression,
    _build_typed_language_lane,
    _commit_real_scene,
    _evolve_real_causal_window,
    _physical_l6_evaluation,
    _seal,
)
from .recall_reentry import FreshRecallSelfSenseProvider
from .recall_story_episode_archive import RecallStoryEpisodeArchive, restore_recall_story_archive_checkpoint
from .six_lane_runtime_mount import MountedSixLaneRuntime, mount_six_lane_runtime
from .story_chemistry import (
    StoryChemistryRuntime,
    StoryChemistryStatus,
    authenticate_production_story_chemistry_profile,
    mount_packaged_production_story_chemistry,
    production_story_chemistry_profile_payload,
)
from .story_native_replay import StorySensorPortAuthority

from dsf_ai_service.substrate.immutable_generation_store import CURRENT_NAME, ImmutableGenerationStore, LoadedGeneration


GENERATION_STORE_ROOT_ENVIRONMENT_VARIABLE = "GLEW_CONVERSATION_ENGINE_STORE_ROOT"
DEFAULT_GENESIS_ROOT_TEXT = "a"
DEFAULT_GENESIS_BOOTSTRAP_TEXT = "b"


def resolve_default_generation_store_root(
    environment: Mapping[str, str] | None = None,
) -> Path:
    """Resolve this bootstrap's own real, discoverable persistent-storage root.

    See the module docstring's "Persistent storage root convention" section
    for the full rationale. Reads ``GLEW_CONVERSATION_ENGINE_STORE_ROOT`` if
    set; otherwise derives a sibling of ``STATE_DIR`` (the legacy engine's own
    real persistent-storage env var, per ``dsf_ai_service/app.py``), named
    ``STATE_DIR``'s basename plus ``"-glew-conversation-engine"`` -- distinct
    from that same module's own ``GUALA_GENERATION_STORE_ROOT`` default
    (``STATE_DIR``'s basename plus ``"-sealed"``) and from
    ``conformance.py``'s ``GLEW_GENESIS_ROOT`` (which has no default at all).
    """

    source = os.environ if environment is None else environment
    configured = source.get(GENERATION_STORE_ROOT_ENVIRONMENT_VARIABLE)
    if configured:
        return Path(configured)
    state_dir = Path(source.get("STATE_DIR", "state")).resolve()
    return state_dir.parent / f"{state_dir.name}-glew-conversation-engine"


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


def _archive_canonical_bytes(value: object) -> bytes:
    """Mirrors ``recall_story_episode_archive.py``'s own private
    ``_canonical_bytes`` exactly (``ensure_ascii=True`` + ASCII encoding --
    deliberately different from every other module's own UTF-8 style)."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _extend_registry(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    values = {item.digest: item.payload for item in registry.records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        existing = values.get(digest)
        if existing is not None and existing != payload:
            raise ReceiptError("production runtime bootstrap receipt digest collision")
        values[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, values[key]) for key in sorted(values)),
    )


def _merge_registry(registry: ReceiptRegistry, addition: ReceiptRegistry) -> ReceiptRegistry:
    """Union ``addition``'s records into ``registry``, keeping ``registry``'s
    own root -- exactly mirroring ``clean_conversation_engine.py``'s own
    ``_merge_registry`` (see that function's docstring: ``mount_six_lane_
    runtime`` re-roots its own registry at its story-native-replay profile,
    while every story-chemistry mount/evolution registry stays rooted at the
    chemistry manifest instead; no ratified profile unifies the two roots
    anywhere in this repository, so this helper keeps one chosen root and
    unions the other source's records in beneath it)."""

    return _extend_registry(registry, *(value.payload for value in addition.records))


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


# ---------------------------------------------------------------------------
# SixLaneRuntimeBootstrapParameters -- every ``mount_six_lane_runtime`` input
# this module cannot itself source from a ratified file or a prior persisted
# generation (see module docstring's "still genuinely synthetic" list).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SixLaneRuntimeBootstrapParameters:
    """Every ``mount_six_lane_runtime`` argument this bootstrap does not
    itself decide -- ids, edges, precision-bit ceilings, sensor-port
    authorities, and opaque derivation payloads that ``six_lane_runtime_
    mount.py``'s own module docstring already documents as genuinely open
    operational/product policy decisions or genuinely missing production
    constructors, not physics constants this module could compute. A real
    caller must supply real, deliberately-chosen values (see that module's
    docstring for exactly which fields are a genuine physical constraint
    versus an arbitrary-but-required operational choice).

    Field names match ``mount_six_lane_runtime``'s own keyword arguments
    exactly (excluding ``story_chemistry_profile_bytes``/
    ``story_chemistry_authentication_key``/``story_chemistry_expected_key_id``,
    which :func:`bootstrap_production_clean_conversation_engine` derives
    itself from the real packaged profile file plus the caller's own
    chemistry authentication key), so :meth:`as_mount_kwargs` can pass this
    dataclass straight through without any renaming.
    """

    sensor_ports: tuple[StorySensorPortAuthority, ...]
    sensor_port_receipt_payloads: tuple[bytes, ...]
    five_sense_topology_id: str
    causal_grid_id: str
    causal_timestamps: tuple[Fraction, ...]
    causal_positive_weights: tuple[Fraction, ...]
    five_sense_support_domain_id: str
    five_sense_resonance_graph_id: str
    five_sense_resonance_required_edges: tuple[RequiredEdge, ...]
    resonance_operator_id: str
    resonance_precision_bits: int
    story_replay_profile_id: str
    story_replay_provider_id: str
    story_replay_kernel_adapter_id: str
    story_replay_kernel_adapter_profile_payload: bytes
    typed_language_adapter_id: str
    typed_language_interface_id: str
    typed_language_phase_calibration_id: str
    typed_language_phase_kappa: Fraction
    typed_language_derivation_payload: bytes
    language_port_id: str
    six_lane_topology_id: str
    six_lane_support_domain_id: str
    six_lane_resonance_graph_id: str
    six_lane_resonance_required_edges: tuple[RequiredEdge, ...]
    expression_precision_authority_id: str
    expression_maximum_precision_bits: int
    pre_window_state_id: str
    pre_window_memory_state_payload: bytes
    pre_window_l6_state_payload: bytes
    l5_governance_profile_id: str
    basin_profile_id: str
    basin_physical_profile_payload: bytes
    basin_hbar: Fraction
    basin_source_time_unit: str
    basin_max_connected_component_dimension: int
    basin_field_precision_bits: int
    basin_hamiltonian: tuple[HamiltonianEntry, ...] = ()
    basin_local_rates: tuple[LocalRate, ...] = ()
    five_sense_support_required_port_keys: tuple[PortKey, ...] | None = None
    six_lane_support_required_port_keys: tuple[PortKey, ...] | None = None

    def as_mount_kwargs(self) -> dict[str, object]:
        """Return this parameter set as a plain kwargs dict for
        ``mount_six_lane_runtime`` (shallow -- nested dataclass values such
        as ``sensor_ports``/``six_lane_resonance_required_edges`` entries are
        passed through as-is, never recursively converted)."""

        return {field.name: getattr(self, field.name) for field in dataclasses.fields(self)}


# ---------------------------------------------------------------------------
# Real cold-start genesis: live two real, mutually independent scenes through
# the real six-lane pipeline, grow the mode bank from empty to rank two, and
# commit exactly the root scene to seed a genuinely fresh LearnedBindingState.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenesisBootstrapResult:
    """Everything produced by one real cold-start genesis bootstrap: the
    six-lane runtime with its mode bank grown to rank two, the resulting
    fresh-genesis ``LearnedBindingState`` (``initial_event`` always
    ``None``), and the two real committed scenes/relation that produced it --
    exposed so a caller (for example this module's own test suite) can go on
    to learn a real successor via ``expression_learning.
    learn_committed_binding_transaction`` without re-deriving any of this."""

    mounted_runtime: MountedSixLaneRuntime
    genesis: LearnedBindingState
    root_committed: CommittedCoexperience
    bootstrap_committed: CommittedCoexperience
    initial_relation: CommittedModeRelation
    bootstrap_language: TypedLanguageFrozenKernelInput
    receipt_registry: ReceiptRegistry


def _mount_real_chemistry_runtime(
    *, authentication_key: bytes, key_id: str
) -> StoryChemistryRuntime:
    mounted = mount_packaged_production_story_chemistry(
        runtime_authentication_key=authentication_key, runtime_key_id=key_id
    )
    if mounted.status is not StoryChemistryStatus.MOUNTED or mounted.runtime is None:
        raise ReceiptError(
            f"real production story chemistry failed to mount: {mounted.reason}"
        )
    return mounted.runtime


def _engine_physical_profile_payload(engine_id: str) -> bytes:
    """Bit-for-bit the same payload shape
    ``ProductionCleanConversationEngine.__init__`` itself computes from its
    own ``engine_id`` -- genesis-scene construction must use the identical
    receipt so a later real turn replaying the same scene reconstructs the
    same field expression the engine's own turn-building path would."""

    return _canonical_bytes(
        {
            "identity": f"{engine_id}-shared-field-profile",
            "schema": "glew.clean_conversation_engine.exact_field_profile.v1",
        }
    )


def _build_genesis_scene(
    *,
    mounted_runtime: MountedSixLaneRuntime,
    task_id: str,
    text: str,
    chemistry_runtime: StoryChemistryRuntime,
    engine_id: str,
    typed_language_phase_calibration_id: str,
    typed_language_phase_kappa: Fraction,
    registry: ReceiptRegistry,
):
    """Build one real scene's field expression, mirroring
    ``ProductionCleanConversationEngine._build_turn_expression`` exactly
    (same real helpers, same identity conventions, same physical-profile
    receipt derived from the same ``engine_id``), so a later real turn
    replaying the same ``task_id``/``text`` reconstructs this same scene
    bit-for-bit."""

    descriptors = _scene_descriptors(task_id)
    bridge = _evolve_real_causal_window(chemistry_runtime, scene_id=task_id, descriptors=descriptors)
    registry = _merge_registry(registry, bridge.receipt_registry)

    language_input, registry = _build_typed_language_lane(
        binding=mounted_runtime.typed_language_kernel_binding,
        phase_id=typed_language_phase_calibration_id,
        phase_kappa=typed_language_phase_kappa,
        text=text,
        event_id=f"{task_id}-language",
        source_epoch=f"{task_id}-language-epoch",
        timestamps=mounted_runtime.causal_grid.timestamps,
        registry=registry,
    )

    preparation = prepare_closed_experience_evidence(
        streams=(language_input.stream, *bridge.streams),
        kernel_inputs=(language_input.kernel_input, *bridge.kernel_inputs),
        source_time_start=Fraction(0),
        grid=mounted_runtime.causal_grid,
        support_domain=mounted_runtime.support_domain,
        resonance_graph=mounted_runtime.resonance_graph,
        resonance_operator=mounted_runtime.resonance_operator,
        topology=mounted_runtime.field_topology,
        receipt_registry=registry,
    )
    if isinstance(preparation, ClosedExperienceProviderUnknown):
        raise ReceiptError(
            f"real genesis scene evidence preparation failed for {task_id}: {preparation.reason}"
        )
    registry = preparation.receipt_registry

    physical_profile_payload = _engine_physical_profile_payload(engine_id)
    registry = _extend_registry(registry, physical_profile_payload)

    expression, registry = _build_expression(
        topology=mounted_runtime.field_topology,
        preparation=preparation,
        precision=mounted_runtime.precision_authority,
        physical_profile_receipt_sha256=receipt_sha256(physical_profile_payload),
        identity=task_id,
        registry=registry,
    )
    return expression, language_input, preparation, registry


def bootstrap_genesis_learned_binding_state(
    *,
    mounted_runtime: MountedSixLaneRuntime,
    engine_id: str,
    chemistry_authentication_key: bytes,
    chemistry_key_id: str,
    typed_language_phase_calibration_id: str,
    typed_language_phase_kappa: Fraction,
    receipt_registry: ReceiptRegistry,
    root_scene_id: str | None = None,
    bootstrap_scene_id: str | None = None,
    root_text: str = DEFAULT_GENESIS_ROOT_TEXT,
    bootstrap_text: str = DEFAULT_GENESIS_BOOTSTRAP_TEXT,
) -> GenesisBootstrapResult:
    """Live two real, independent scenes through ``mounted_runtime`` (its
    empty, rank-zero mode bank grows to rank two as a genuine, load-bearing
    side effect of recognition itself -- see ``clean_conversation_engine.py``'s
    own module docstring), commit only the root scene, and seed a genuinely
    fresh ``create_learned_binding_genesis`` state from it. See this module's
    own docstring, "Why cold-start still requires two real lived scenes," for
    why a real ``LearnedBindingState`` cannot exist without this.
    """

    root_scene_id = root_scene_id or f"{engine_id}-genesis-root"
    bootstrap_scene_id = bootstrap_scene_id or f"{engine_id}-genesis-bootstrap"
    if root_scene_id == bootstrap_scene_id:
        raise ReceiptError("genesis root and bootstrap scene ids must be distinct")
    if len(root_text) != 1 or len(bootstrap_text) != 1:
        raise ReceiptError("genesis scenes each require exactly one Unicode scalar")

    root_chemistry = _mount_real_chemistry_runtime(
        authentication_key=chemistry_authentication_key, key_id=chemistry_key_id
    )
    bootstrap_chemistry = _mount_real_chemistry_runtime(
        authentication_key=chemistry_authentication_key, key_id=chemistry_key_id
    )

    registry = receipt_registry
    root_expression, root_language, root_preparation, registry = _build_genesis_scene(
        mounted_runtime=mounted_runtime,
        task_id=root_scene_id,
        text=root_text,
        chemistry_runtime=root_chemistry,
        engine_id=engine_id,
        typed_language_phase_calibration_id=typed_language_phase_calibration_id,
        typed_language_phase_kappa=typed_language_phase_kappa,
        registry=registry,
    )
    bootstrap_expression, bootstrap_language, bootstrap_preparation, registry = _build_genesis_scene(
        mounted_runtime=mounted_runtime,
        task_id=bootstrap_scene_id,
        text=bootstrap_text,
        chemistry_runtime=bootstrap_chemistry,
        engine_id=engine_id,
        typed_language_phase_calibration_id=typed_language_phase_calibration_id,
        typed_language_phase_kappa=typed_language_phase_kappa,
        registry=registry,
    )

    empty_bank = mounted_runtime.expression_mode_bank
    root_growth = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=empty_bank,
        input_expression=root_expression,
        receipt_registry=registry,
    )
    registry = _extend_registry(registry, *_mode_payloads(root_growth))
    if (
        root_growth.status is not ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
        or root_growth.post_growth_bank.rank != 1
    ):
        raise ReceiptError(
            "genesis root scene did not bootstrap the mode bank as expected: "
            f"{root_growth.status}/{root_growth.reason}"
        )

    bootstrap_growth = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=root_growth.post_growth_bank,
        input_expression=bootstrap_expression,
        receipt_registry=registry,
    )
    registry = _extend_registry(registry, *_mode_payloads(bootstrap_growth))
    if (
        bootstrap_growth.status is not ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
        or bootstrap_growth.post_growth_bank.rank != 2
    ):
        raise ReceiptError(
            "genesis bootstrap scene did not grow the mode bank to rank two "
            f"as expected: {bootstrap_growth.status}/{bootstrap_growth.reason}"
        )

    grown_bank = bootstrap_growth.post_growth_bank

    root_recognition = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=grown_bank,
        input_expression=root_expression,
        receipt_registry=registry,
    )
    registry = _extend_registry(registry, *_mode_payloads(root_recognition))
    if root_recognition.status is not ExpressionRecognitionStatus.RECOGNIZED:
        raise ReceiptError(
            "genesis root scene was not RECOGNIZED against the bootstrapped "
            f"rank-two bank: {root_recognition.status}/{root_recognition.reason}"
        )

    bootstrap_recognition = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=grown_bank,
        input_expression=bootstrap_expression,
        receipt_registry=registry,
    )
    registry = _extend_registry(registry, *_mode_payloads(bootstrap_recognition))
    if bootstrap_recognition.status is not ExpressionRecognitionStatus.RECOGNIZED:
        raise ReceiptError(
            "genesis bootstrap scene was not RECOGNIZED against the "
            f"bootstrapped rank-two bank: {bootstrap_recognition.status}/"
            f"{bootstrap_recognition.reason}"
        )
    if root_recognition.winner_mode_index == bootstrap_recognition.winner_mode_index:
        raise ReceiptError(
            "genesis root and bootstrap scenes were not recognized as distinct modes"
        )

    l6_evaluation, registry = _physical_l6_evaluation(
        topology=mounted_runtime.field_topology,
        pre_window=mounted_runtime.pre_window_state,
        registry=registry,
    )

    root_sealed, registry = _seal(
        topology=mounted_runtime.field_topology,
        preparation=root_preparation,
        expression=root_expression,
        recognition=root_recognition,
        identity=root_scene_id,
        registry=registry,
    )
    bootstrap_sealed, registry = _seal(
        topology=mounted_runtime.field_topology,
        preparation=bootstrap_preparation,
        expression=bootstrap_expression,
        recognition=bootstrap_recognition,
        identity=bootstrap_scene_id,
        registry=registry,
    )

    # The root scene's own commit MUST go through the engine's own
    # ``_build_commit_providers`` + ``evaluate_commit_boundary`` (never
    # ``_commit_real_scene``, which uses different receipt schema strings) --
    # this is the exact scene a later real turn will independently rebuild
    # and re-commit byte-for-byte, and ``conversation.py``'s own
    # ``_preflight_initial_output`` requires that replayed commit receipt to
    # exactly equal the one recorded in ``initial_event`` at learning time.
    root_commit_providers, registry = _build_commit_providers(
        identity=root_scene_id,
        sealed=root_sealed,
        topology=mounted_runtime.field_topology,
        l6_evaluation=l6_evaluation,
        registry=registry,
    )
    root_commit_decision = evaluate_commit_boundary(
        topology=mounted_runtime.field_topology,
        recognition=root_recognition,
        l6_evaluation=root_commit_providers.l6_evaluation,
        l6_scope=root_commit_providers.l6_scope,
        closed_experience=root_commit_providers.closed_experience,
        safe_mode=root_commit_providers.safe_mode,
        event_support=root_commit_providers.event_support,
        evidence=root_commit_providers.evidence,
        l5_applicability=root_commit_providers.l5_applicability,
        global_uf_validation=root_commit_providers.global_uf_validation,
        receipt_registry=registry,
    )
    if root_commit_decision.status is not CommitStatus.COMMIT:
        raise ReceiptError(
            f"genesis root scene did not commit: {root_commit_decision.findings}"
        )
    registry = _extend_registry(registry, root_commit_decision.receipt_payload)

    root_winner = root_recognition.winner_mode_index
    if root_winner is None:
        raise ReceiptError("genesis root scene lacks a recognized mode")
    root_committed = CommittedCoexperience(
        root_commit_decision, root_sealed, root_recognition.pre_growth_bank.modes[root_winner]
    )
    root_committed.verify(registry)

    # The bootstrap scene is never replayed as ``initial_event``, so its own
    # commit only needs to satisfy ``CommittedCoexperience.verify()`` -- the
    # simpler, already-real ``_commit_real_scene`` suffices (same real
    # conjunction, different but equally valid receipt schema strings).
    bootstrap_committed, registry = _commit_real_scene(
        identity=bootstrap_scene_id,
        sealed=bootstrap_sealed,
        topology=mounted_runtime.field_topology,
        l6_evaluation=l6_evaluation,
        registry=registry,
    )

    initial_relation, registry = derive_committed_mode_relation(
        relation_id=f"{root_scene_id}-initial-relation",
        committed=root_committed,
        output_source_receipt_sha256=root_committed.commit.receipt_sha256,
        receipt_registry=registry,
    )
    genesis = create_learned_binding_genesis(
        state_id=f"{engine_id}-genesis-state",
        expression_id=f"{engine_id}-genesis-expression",
        initial_relation=initial_relation,
        receipt_registry=registry,
    )

    grown_runtime = dataclasses.replace(mounted_runtime, expression_mode_bank=grown_bank)

    return GenesisBootstrapResult(
        mounted_runtime=grown_runtime,
        genesis=genesis,
        root_committed=root_committed,
        bootstrap_committed=bootstrap_committed,
        initial_relation=initial_relation,
        bootstrap_language=bootstrap_language,
        receipt_registry=genesis.receipt_registry,
    )


# ---------------------------------------------------------------------------
# Restore path: real ``ImmutableGenerationStore`` -> real restored
# LearnedBindingState / RecallStoryEpisodeArchive / GenerationIdentityBinding.
# ---------------------------------------------------------------------------


def _restore_generation(
    *,
    loaded: LoadedGeneration,
    checkpoint_authentication_key: bytes,
    checkpoint_key_id: str,
    generation_identity: GenerationIdentityParameters,
) -> tuple[LearnedBindingState, RecallStoryEpisodeArchive]:
    """Restore the real learned-binding state and recall archive from one
    verified ``LoadedGeneration``, then cross-check the persisted generation
    identity binding against the caller's own current genesis identity and
    the two checkpoints' own restored ``checkpoint_id`` fields -- rejecting a
    restart that mixes generations (``generation_identity.
    verify_generation_identity_binding``'s own stated purpose)."""

    learning_envelope = loaded.payload(LEARNING_CHECKPOINT_RELATIVE_PATH)
    archive_envelope = loaded.payload(ARCHIVE_CHECKPOINT_RELATIVE_PATH)
    identity_envelope = loaded.payload(GENERATION_IDENTITY_BINDING_RELATIVE_PATH)

    if not isinstance(learning_envelope, Mapping) or not isinstance(learning_envelope.get("body"), Mapping):
        raise ReceiptError("restored learning checkpoint envelope is malformed")
    if not isinstance(archive_envelope, Mapping) or not isinstance(archive_envelope.get("body"), Mapping):
        raise ReceiptError("restored archive checkpoint envelope is malformed")

    learned_state = restore_learned_binding_checkpoint(
        checkpoint_payload=_canonical_bytes(learning_envelope),
        authentication_key=checkpoint_authentication_key,
        expected_key_id=checkpoint_key_id,
    )
    archive = restore_recall_story_archive_checkpoint(
        checkpoint_payload=_archive_canonical_bytes(archive_envelope),
        authentication_key=checkpoint_authentication_key,
        expected_key_id=checkpoint_key_id,
    )

    if not isinstance(identity_envelope, Mapping):
        raise ReceiptError("restored generation identity binding is malformed")
    persisted_binding = bind_generation_identity(
        genesis_identity=identity_envelope["genesis_identity"],
        genesis_generation_uuid=identity_envelope["genesis_generation_uuid"],
        genesis_tick=identity_envelope["genesis_tick"],
        learning_checkpoint_id=identity_envelope["learning_checkpoint_id"],
        archive_checkpoint_id=identity_envelope["archive_checkpoint_id"],
    )
    verify_generation_identity_binding(
        persisted_binding,
        restored_genesis_identity=generation_identity.genesis_identity,
        restored_genesis_generation_uuid=generation_identity.genesis_generation_uuid,
        restored_genesis_tick=generation_identity.genesis_tick,
        restored_learning_checkpoint_id=learning_envelope["body"]["checkpoint_id"],
        restored_archive_checkpoint_id=archive_envelope["body"]["checkpoint_id"],
    )
    return learned_state, archive


# ---------------------------------------------------------------------------
# Top-level production bootstrap.
# ---------------------------------------------------------------------------


def bootstrap_production_clean_conversation_engine(
    *,
    generation_store_root: Path,
    story_chemistry_authentication_key: bytes,
    story_chemistry_key_id: str,
    six_lane_runtime_parameters: SixLaneRuntimeBootstrapParameters,
    checkpoint_authentication_key: bytes,
    checkpoint_key_id: str,
    generation_identity: GenerationIdentityParameters,
    fresh_recall_provider: FreshRecallSelfSenseProvider,
    engine_id: str = "clean-conversation-engine",
    genesis_root_scene_id: str | None = None,
    genesis_bootstrap_scene_id: str | None = None,
    genesis_root_text: str = DEFAULT_GENESIS_ROOT_TEXT,
    genesis_bootstrap_text: str = DEFAULT_GENESIS_BOOTSTRAP_TEXT,
    receipt_registry: ReceiptRegistry | None = None,
) -> ProductionCleanConversationEngine:
    """Build one real, cold-started ``ProductionCleanConversationEngine``.

    1. Loads the real, packaged, ratified five-sense chemistry profile bytes
       from disk and authenticates them with the caller's own real chemistry
       secret (never fabricated -- see module docstring).
    2. Mounts one real ``MountedSixLaneRuntime`` via
       ``six_lane_runtime_mount.mount_six_lane_runtime`` from those real
       profile bytes plus ``six_lane_runtime_parameters``.
    3. Opens a real ``ImmutableGenerationStore`` at ``generation_store_root``.
       If a prior real generation already exists there (its ``CURRENT``
       pointer is present), restores ``LearnedBindingState``/
       ``RecallStoryEpisodeArchive``/generation-identity from it via the
       real, already-existing restore functions, cross-checked against
       ``generation_identity``. If none exists yet, lives two real scenes
       through the mounted runtime and builds a real, honest fresh-genesis
       ``LearnedBindingState`` (``initial_event`` always ``None``) --
       never fabricated learned content.
    4. Returns a fully real, constructed ``ProductionCleanConversationEngine``
       -- except ``fresh_recall_provider``, which remains a required,
       pass-through parameter this function never constructs or defaults
       (a separate, concurrent effort owns that gap).

    See this module's own docstring, "Honest remaining gaps," for the two
    real limitations this function does not attempt to solve: no production
    ``StorySensorPortAuthority`` constructor exists (caller-supplied via
    ``six_lane_runtime_parameters``), and no ``ExpressionModeBank``
    checkpoint/restore mechanism exists anywhere in this repository (a
    restored generation's mode bank is always freshly mounted at rank zero,
    regardless of how much has previously been learned).
    """

    if fresh_recall_provider is None:
        raise ReceiptError(
            "production runtime bootstrap requires an injected fresh-recall "
            "provider; constructing one is out of this module's scope (see "
            "module docstring)"
        )

    chemistry_envelope = authenticate_production_story_chemistry_profile(
        profile_body_payload=production_story_chemistry_profile_payload(),
        runtime_authentication_key=story_chemistry_authentication_key,
        runtime_key_id=story_chemistry_key_id,
    )
    mounted_runtime = mount_six_lane_runtime(
        story_chemistry_profile_bytes=chemistry_envelope,
        story_chemistry_authentication_key=story_chemistry_authentication_key,
        story_chemistry_expected_key_id=story_chemistry_key_id,
        **six_lane_runtime_parameters.as_mount_kwargs(),
    )

    store = ImmutableGenerationStore(
        generation_store_root,
        identity=generation_identity.genesis_identity,
        required_files=CHECKPOINT_RELATIVE_PATHS,
    )

    # ``EvidenceStream``/etc. objects built for every real scene (genesis or
    # any later turn) embed and are re-checked against the story-chemistry
    # manifest's own registry root, not ``mount_six_lane_runtime``'s own
    # re-rooted registry (see ``clean_conversation_engine.py``'s own
    # ``_merge_registry`` docstring) -- so the registry this bootstrap
    # ultimately hands to the engine must be rooted there too.
    base_registry = _merge_registry(
        mounted_runtime.story_chemistry_runtime.receipt_registry,
        mounted_runtime.receipt_registry,
    )

    current_pointer_path = Path(generation_store_root) / CURRENT_NAME
    if current_pointer_path.exists():
        loaded = store.load_current()
        learned_state, recall_archive = _restore_generation(
            loaded=loaded,
            checkpoint_authentication_key=checkpoint_authentication_key,
            checkpoint_key_id=checkpoint_key_id,
            generation_identity=generation_identity,
        )
        grown_runtime = mounted_runtime
        registry = _merge_registry(base_registry, learned_state.receipt_registry)
    else:
        result = bootstrap_genesis_learned_binding_state(
            mounted_runtime=mounted_runtime,
            engine_id=engine_id,
            chemistry_authentication_key=story_chemistry_authentication_key,
            chemistry_key_id=story_chemistry_key_id,
            typed_language_phase_calibration_id=six_lane_runtime_parameters.typed_language_phase_calibration_id,
            typed_language_phase_kappa=six_lane_runtime_parameters.typed_language_phase_kappa,
            receipt_registry=base_registry,
            root_scene_id=genesis_root_scene_id,
            bootstrap_scene_id=genesis_bootstrap_scene_id,
            root_text=genesis_root_text,
            bootstrap_text=genesis_bootstrap_text,
        )
        grown_runtime = result.mounted_runtime
        learned_state = result.genesis
        registry = result.receipt_registry
        recall_archive = RecallStoryEpisodeArchive()

    if receipt_registry is not None:
        registry = _merge_registry(receipt_registry, registry)

    return ProductionCleanConversationEngine(
        mounted_runtime=grown_runtime,
        learned_state=learned_state,
        receipt_registry=registry,
        fresh_recall_provider=fresh_recall_provider,
        typed_language_phase_calibration_id=six_lane_runtime_parameters.typed_language_phase_calibration_id,
        typed_language_phase_kappa=six_lane_runtime_parameters.typed_language_phase_kappa,
        generation_identity=generation_identity,
        generation_store=store,
        checkpoint_authentication_key=checkpoint_authentication_key,
        checkpoint_key_id=checkpoint_key_id,
        recall_story_episode_archive=recall_archive,
        engine_id=engine_id,
    )


__all__ = (
    "GENERATION_STORE_ROOT_ENVIRONMENT_VARIABLE",
    "GenesisBootstrapResult",
    "SixLaneRuntimeBootstrapParameters",
    "bootstrap_genesis_learned_binding_state",
    "bootstrap_production_clean_conversation_engine",
    "resolve_default_generation_store_root",
)
