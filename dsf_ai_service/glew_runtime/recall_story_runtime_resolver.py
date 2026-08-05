"""Production ``RecallStoryRuntimeResolver`` (governing spec section 9.6).

``fresh_recall_executor.py`` defines two authorities that a prior
investigation found have ZERO construction sites anywhere in this repository
-- production or test:

* ``RecallStoryRuntimeResolver`` (a ``Protocol``): resolves one archived
  ``RecallStoryEpisode`` back into a live ``MountedRecallStoryRuntime`` --
  the complete mounted six-lane authority set the episode's story-native
  replay ran against, byte-identically re-verified via
  ``MountedRecallStoryRuntime.verify`` against the episode's own recorded
  receipts.
* ``MountedRecallLanguageInterface`` (a real frozen dataclass, not a
  Protocol): the typed-language kernel binding plus a live
  ``TypedLanguageState`` that ``FreshRecallClosedExperienceExecutor``
  stages the one bound Unicode scalar through.

This module closes both gaps with one production resolver,
:class:`ProductionRecallStoryRuntimeResolver`, plus the checkpoint format its
construction depends on, :class:`MountedRecallStoryRuntimeCheckpoint`.

The central design question and its answer
-------------------------------------------
``RecallStoryEpisode`` (``recall_story_episode_archive.py``) only ever
records the FIVE-SENSE side of one admitted BASE story-native-replay
execution: a ``MountedStoryNativeReplayProfile``, a
``MountedAuthenticatedClosedStoryBoundary``, a five-sense
``MountedPreWindowState``, the pre-window ``StoryChemistryRuntime`` and
``MountedStorySensorState`` tuple, and the specific sensory evidence bindings
for that one lived scene. It never mentions the SIX-LANE side
(``MountedFieldTopology`` with the language fiber, the six-lane support
domain and resonance graph, ``MountedStoryGlobalUFBasinProfile``, the typed-
language kernel binding) -- because at archive time, per every real
construction path in this repository (``tests/glew_runtime/
test_recall_story_episode_archive.py::admitted_archive``,
built from ``tests/glew_runtime/test_story_native_replay.py::
_mounted_five_sense_runtime``), no six-lane runtime is ever mounted at all;
only the five real senses are.

So what must ``resolve_runtime`` actually rebuild? Investigating
``MountedRecallStoryRuntime.verify`` (``fresh_recall_executor.py`` lines
412-451) and ``MountedStoryGlobalUFBasinProfile.verify``
(``story_global_uf_basin.py`` lines 309-361) directly (not assumed) settles
this:

1. ``MountedRecallStoryRuntime.pre_window_state`` must byte-match
   ``episode.pre_window_state_receipt_sha256`` -- a FIXED value baked in at
   archive time. But ``MountedStoryGlobalUFBasinProfile.verify`` ALSO
   requires that this exact ``pre_window_state.field_state_receipt_sha256``
   equal a real, independently-verifying ``ExactFieldState``'s own receipt,
   and its ``mode_state_receipt_sha256`` equal a real
   ``ExpressionModeBank``'s own receipt. A ``MountedPreWindowState`` built
   with opaque test placeholders for those two fields (exactly what
   ``_mounted_five_sense_runtime`` does, since that fixture predates the
   six-lane/basin authorities and never needed them) can NEVER be paired
   with a genuinely-verifying basin profile -- the two digests can only
   agree if the SAME real ``ExactFieldState``/``ExpressionModeBank`` were
   used when the pre-window state now baked into the episode was first
   built. In other words: **an episode can only ever be resolved for real
   recall if its pre-window state was built against the six-lane basin
   authorities from the start.** This is a genuine, load-bearing
   requirement on whatever upstream code seals episodes for a system that
   intends to recall them later -- not a limitation of this resolver.
2. Given (1), the five-sense authorities the episode fixes
   (``story_profile``, ``boundary``, ``pre_window_state``,
   ``story_runtime``, ``sensor_states``) are -- in every real construction
   path today -- the SAME canonical genesis snapshot for one story profile,
   shared identically across every episode ever archived under it (there is
   no "continuously evolving, mid-stream pre-window checkpoint" mechanism
   anywhere in this repository; every admitted episode starts its causal
   window from the same at-rest, ``-1``/zero sentinel state).  Concretely,
   nothing in this five-sense side varies per episode except which specific
   sensory evidence was captured during that one causal window, which the
   episode already carries directly.
3. The six-lane/basin authorities (topology-with-language-fiber, six-lane
   support domain and resonance graph, precision authority, expression mode
   bank, L5 governance profile, basin profile, typed-language kernel
   binding) are likewise constant for the whole life of one story profile
   -- they are mounted once, the same way every ``mount_six_lane_runtime``
   (``six_lane_runtime_mount.py``) caller mounts them today, and reused for
   every subsequent recall.

Consequently, **the entire ``MountedRecallStoryRuntime`` for one profile is
one fixed value, identical across every episode of that profile** -- only
``episode_receipt_sha256`` changes per call. That fixed value, plus the
typed-language kernel binding/phase authorities ``MountedRecallLanguageInterface``
also needs, is exactly what :class:`MountedRecallStoryRuntimeCheckpoint`
below packages up as one real, receipted, independently ``.verify()``-able
bundle -- built once (mirroring ``mount_six_lane_runtime``'s own "mount from
authenticated profile bytes, then reuse" pattern), and handed to
:class:`ProductionRecallStoryRuntimeResolver`'s constructor.

What callers must supply that they may not already have
---------------------------------------------------------
``resolve_runtime``'s bare Protocol signature is ``(episode, receipt_registry)
-> MountedRecallStoryRuntime``. The real production requirement is
considerably larger and this module does not hide that:

* The resolver's CONSTRUCTOR requires one already-mounted, already-verified
  :class:`MountedRecallStoryRuntimeCheckpoint` -- i.e. a caller (generation
  start-up code, not this module) must, once per generation/profile, mount
  the five-sense chemistry, the six-lane topology/support/resonance, the
  precision authority and expression-mode bank, the pre-window state (built
  so its field/mode digests genuinely match the mounted
  ``ExactFieldState``/``ExpressionModeBank``, per point 1 above), the L5
  governance profile, the basin profile, the boundary, and the typed-
  language kernel binding, and persist that bundle (:func:`mount_recall_story_runtime_checkpoint`
  builds and verifies it from already-mounted pieces; nothing here invents
  new mount physics -- every sub-authority is verified with its own,
  already-real ``.verify()``).
* This checkpoint has NO existing persistence path anywhere in this
  repository today. ``generation_identity.py`` (Step 4) already found and
  documented that ``mount_six_lane_runtime``/``story_chemistry.py`` have no
  tick/generation-progression concept of their own; this module's checkpoint
  is a FOURTH, still entirely separate identity surface with no binding yet
  into ``GenerationIdentityBinding``. Wiring "this checkpoint belongs to
  generation X" is a real, open gap this module does not attempt to close.
* Because point 1 above is a real structural requirement (not a stylistic
  preference), any ``RecallStoryEpisode`` sealed the way today's ONLY real
  episode-admission test fixture builds one (``_mounted_five_sense_runtime``'s
  placeholder field/mode digests) can never actually be resolved for real
  recall. Step 4/5's learning and archival path must build its pre-window
  states against real basin authorities from the start if recalled episodes
  are meant to be replayable later -- this is exactly the kind of upstream
  persistence implication the governing spec asked this investigation to
  surface honestly.

``MountedRecallLanguageInterface``
-----------------------------------
``fresh_recall_executor.py``'s own consumer (``_typed_input``) only ever
requires ``interface.initial_state.last_timestamp`` to equal
``runtime.basin_profile.initial_field_state.source_time`` -- i.e. the SAME
genesis instant the recall runtime itself starts from. There is no evidence
anywhere in this codebase that this specific interface, AS CONSUMED BY THIS
EXECUTOR, needs continuity carried across multiple real conversation turns
(that is a different, broader concept -- an ongoing typed-language interface
for live, non-recall conversation -- outside this Protocol's scope and not
built here). :func:`mount_recall_language_interface_genesis` therefore mounts
a fresh, deterministic genesis state synced to the checkpoint's own basin
genesis instant every time, exactly mirroring
``real_experience_learning_pipeline.py``'s own ``_build_typed_language_lane``
genesis construction (``last_source_index=-1``, ``phase_turns=Fraction(0)``,
an opaque caller-declared genesis marker receipt -- no ratified derivation
for a typed-language genesis exists anywhere in this repository, mirroring
``mount_typed_language_kernel_binding``'s own ``derivation_payload``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction

from .field import MountedFieldTopology
from .fresh_recall_executor import (
    MountedRecallLanguageInterface,
    MountedRecallStoryRuntime,
)
from .global_uf import MountedPreWindowState
from .language import MountedTypedLanguageKernelBinding, TypedLanguageState
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from .operators import MountedResonanceGraph, MountedSupportDomain, ResonanceOperatorAuthority
from .recall_story_episode_archive import RecallStoryEpisode
from .six_lane_runtime_mount import extend_receipt_registry
from .story_chemistry import StoryChemistryRuntime
from .story_global_uf_basin import MountedStoryGlobalUFBasinProfile
from .story_native_replay import (
    MountedAuthenticatedClosedStoryBoundary,
    MountedStoryNativeReplayProfile,
    MountedStorySensorState,
)


RECALL_STORY_RUNTIME_CHECKPOINT_SCHEMA = "glew.recall.story_runtime_mount_checkpoint.v1"
RECALL_LANGUAGE_INTERFACE_GENESIS_SCHEMA = "glew.recall.language_interface_genesis.v1"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _fraction_text(value: Fraction) -> str:
    require_fraction(value, "recall runtime checkpoint fraction")
    return f"{value.numerator}/{value.denominator}"


def _extend_records(
    registry: ReceiptRegistry,
    records: tuple[ReceiptRecord, ...],
) -> ReceiptRegistry:
    if not isinstance(registry, ReceiptRegistry):
        raise ReceiptError(
            "recall story runtime resolution requires an immutable receipt registry"
        )
    result = list(registry.records)
    mounted = {value.digest: value.payload for value in result}
    for record in records:
        if not isinstance(record, ReceiptRecord):
            raise ReceiptError(
                "recall story runtime resolver received an untyped receipt record"
            )
        prior = mounted.get(record.digest)
        if prior is not None:
            if prior != record.payload:
                raise ReceiptError("recall story runtime resolver receipt digest collision")
            continue
        mounted[record.digest] = record.payload
        result.append(record)
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(result),
    )


def recall_story_runtime_checkpoint_receipt_payload(
    *,
    checkpoint_id: str,
    story_profile_receipt_sha256: str,
    boundary_receipt_sha256: str,
    pre_window_state_receipt_sha256: str,
    story_runtime_manifest_receipt_sha256: str,
    story_runtime_state_receipt_sha256s: tuple[str, ...],
    sensor_state_receipt_sha256s: tuple[str, ...],
    topology_receipt_sha256: str,
    support_domain_receipt_sha256: str,
    resonance_graph_receipt_sha256: str,
    resonance_operator_receipt_sha256: str,
    basin_profile_receipt_sha256: str,
    typed_language_kernel_binding_receipt_sha256: str,
    typed_language_phase_calibration_id: str,
    typed_language_phase_kappa: Fraction,
    typed_language_source_epoch: str,
) -> bytes:
    """Exact canonical bytes bound by one :class:`MountedRecallStoryRuntimeCheckpoint`.

    Mirrors ``recall_story_episode_archive.recall_story_episode_receipt_payload``'s
    own pattern: bind every constituent authority's ALREADY-computed receipt
    digest into one envelope, never re-encode the constituent's own internal
    structure (that structure is independently verified via each authority's
    own ``.verify()``, not re-derived here).
    """

    require_identifier(checkpoint_id, "recall runtime checkpoint id")
    for value, name in (
        (story_profile_receipt_sha256, "checkpoint story profile receipt"),
        (boundary_receipt_sha256, "checkpoint boundary receipt"),
        (pre_window_state_receipt_sha256, "checkpoint pre-window state receipt"),
        (
            story_runtime_manifest_receipt_sha256,
            "checkpoint story chemistry manifest receipt",
        ),
        (topology_receipt_sha256, "checkpoint six-lane topology receipt"),
        (support_domain_receipt_sha256, "checkpoint six-lane support domain receipt"),
        (
            resonance_graph_receipt_sha256,
            "checkpoint six-lane resonance graph receipt",
        ),
        (resonance_operator_receipt_sha256, "checkpoint resonance operator receipt"),
        (basin_profile_receipt_sha256, "checkpoint basin profile receipt"),
        (
            typed_language_kernel_binding_receipt_sha256,
            "checkpoint typed-language kernel binding receipt",
        ),
    ):
        sha256_digest(value, name)
    if not isinstance(story_runtime_state_receipt_sha256s, tuple) or not (
        story_runtime_state_receipt_sha256s
    ):
        raise ReceiptError(
            "recall runtime checkpoint requires the pre-window receiver-state receipts"
        )
    if not isinstance(sensor_state_receipt_sha256s, tuple) or not sensor_state_receipt_sha256s:
        raise ReceiptError(
            "recall runtime checkpoint requires the pre-window native sensor-state receipts"
        )
    for index, value in enumerate(story_runtime_state_receipt_sha256s):
        sha256_digest(value, f"checkpoint receiver-state receipt[{index}]")
    for index, value in enumerate(sensor_state_receipt_sha256s):
        sha256_digest(value, f"checkpoint sensor-state receipt[{index}]")
    require_identifier(
        typed_language_phase_calibration_id,
        "checkpoint typed-language phase calibration id",
    )
    require_identifier(
        typed_language_source_epoch, "checkpoint typed-language source epoch"
    )
    require_fraction(
        typed_language_phase_kappa, "checkpoint typed-language phase kappa"
    )
    return _canonical_bytes(
        {
            "basin_profile_receipt_sha256": basin_profile_receipt_sha256,
            "boundary_receipt_sha256": boundary_receipt_sha256,
            "checkpoint_id": checkpoint_id,
            "pre_window_state_receipt_sha256": pre_window_state_receipt_sha256,
            "resonance_graph_receipt_sha256": resonance_graph_receipt_sha256,
            "resonance_operator_receipt_sha256": resonance_operator_receipt_sha256,
            "schema": RECALL_STORY_RUNTIME_CHECKPOINT_SCHEMA,
            "sensor_state_receipt_sha256s": list(sensor_state_receipt_sha256s),
            "story_profile_receipt_sha256": story_profile_receipt_sha256,
            "story_runtime_manifest_receipt_sha256": story_runtime_manifest_receipt_sha256,
            "story_runtime_state_receipt_sha256s": list(
                story_runtime_state_receipt_sha256s
            ),
            "support_domain_receipt_sha256": support_domain_receipt_sha256,
            "topology_receipt_sha256": topology_receipt_sha256,
            "typed_language_kernel_binding_receipt_sha256": (
                typed_language_kernel_binding_receipt_sha256
            ),
            "typed_language_phase_calibration_id": typed_language_phase_calibration_id,
            "typed_language_phase_kappa": _fraction_text(typed_language_phase_kappa),
            "typed_language_source_epoch": typed_language_source_epoch,
        }
    )


@dataclass(frozen=True, slots=True)
class MountedRecallStoryRuntimeCheckpoint:
    """One real, receipted, per-profile "mounted recall runtime" bundle.

    Every field is an already-typed, already-real authority object (never a
    raw byte blob this class re-derives); ``.verify()`` independently
    re-verifies every one of them against ``receipt_registry`` and recomputes
    this checkpoint's own envelope receipt from their digests, exactly the
    same "authority of authorities" pattern ``RecallStoryEpisode`` and
    ``MountedSixLaneRuntime`` already use.
    """

    checkpoint_id: str
    story_profile: MountedStoryNativeReplayProfile
    boundary: MountedAuthenticatedClosedStoryBoundary
    pre_window_state: MountedPreWindowState
    story_runtime: StoryChemistryRuntime
    sensor_states: tuple[MountedStorySensorState, ...]
    topology: MountedFieldTopology
    support_domain: MountedSupportDomain
    resonance_graph: MountedResonanceGraph
    resonance_operator: ResonanceOperatorAuthority
    basin_profile: MountedStoryGlobalUFBasinProfile
    typed_language_kernel_binding: MountedTypedLanguageKernelBinding
    typed_language_phase_calibration_id: str
    typed_language_phase_kappa: Fraction
    typed_language_source_epoch: str
    receipt_registry: ReceiptRegistry
    checkpoint_receipt_sha256: str
    checkpoint_receipt_payload: bytes

    def verify(self) -> None:
        require_identifier(self.checkpoint_id, "recall runtime checkpoint id")
        if not isinstance(self.receipt_registry, ReceiptRegistry):
            raise ReceiptError(
                "recall runtime checkpoint requires an immutable receipt registry"
            )
        registry = self.receipt_registry
        if not isinstance(self.story_profile, MountedStoryNativeReplayProfile):
            raise ReceiptError(
                "recall runtime checkpoint requires a mounted story native-replay profile"
            )
        self.story_profile.verify(registry)
        if not isinstance(self.boundary, MountedAuthenticatedClosedStoryBoundary):
            raise ReceiptError(
                "recall runtime checkpoint requires an authenticated closed story boundary"
            )
        self.boundary.verify(profile=self.story_profile, receipt_registry=registry)
        if not isinstance(self.pre_window_state, MountedPreWindowState):
            raise ReceiptError("recall runtime checkpoint requires a mounted pre-window state")
        self.pre_window_state.verify(registry)
        if not isinstance(self.story_runtime, StoryChemistryRuntime):
            raise ReceiptError(
                "recall runtime checkpoint requires a mounted story chemistry runtime"
            )
        for value in self.story_runtime.states:
            value.verify(registry)
        if not isinstance(self.sensor_states, tuple) or not self.sensor_states:
            raise ReceiptError(
                "recall runtime checkpoint requires the pre-window native sensor states"
            )
        if tuple(value.field_port_id for value in self.sensor_states) != tuple(
            port.field_port_id for port in self.story_profile.ports
        ):
            raise ReceiptError(
                "recall runtime checkpoint sensor states do not exactly cover the "
                "mounted story ports"
            )
        for port, state in zip(self.story_profile.ports, self.sensor_states, strict=True):
            state.verify(port=port, receipt_registry=registry)
        if not isinstance(self.topology, MountedFieldTopology):
            raise ReceiptError("recall runtime checkpoint requires a mounted field topology")
        self.topology.verify(registry)
        if not isinstance(self.support_domain, MountedSupportDomain):
            raise ReceiptError("recall runtime checkpoint requires a mounted support domain")
        self.support_domain.verify(registry)
        if not isinstance(self.resonance_graph, MountedResonanceGraph):
            raise ReceiptError("recall runtime checkpoint requires a mounted resonance graph")
        self.resonance_graph.verify(registry)
        if not isinstance(self.resonance_operator, ResonanceOperatorAuthority):
            raise ReceiptError(
                "recall runtime checkpoint requires a mounted resonance operator authority"
            )
        self.resonance_operator.verify(registry)
        if not isinstance(self.basin_profile, MountedStoryGlobalUFBasinProfile):
            raise ReceiptError("recall runtime checkpoint requires a mounted basin profile")
        self.basin_profile.verify(
            story_profile=self.story_profile,
            pre_window_state=self.pre_window_state,
            topology=self.topology,
            receipt_registry=registry,
        )
        if not isinstance(
            self.typed_language_kernel_binding, MountedTypedLanguageKernelBinding
        ):
            raise ReceiptError(
                "recall runtime checkpoint requires a mounted typed-language kernel binding"
            )
        self.typed_language_kernel_binding.verify(registry)
        expected = recall_story_runtime_checkpoint_receipt_payload(
            checkpoint_id=self.checkpoint_id,
            story_profile_receipt_sha256=self.story_profile.authority_receipt_sha256,
            boundary_receipt_sha256=self.boundary.authority_receipt_sha256,
            pre_window_state_receipt_sha256=self.pre_window_state.authority_receipt_sha256,
            story_runtime_manifest_receipt_sha256=self.story_runtime.manifest.receipt_sha256,
            story_runtime_state_receipt_sha256s=tuple(
                value.receipt_sha256 for value in self.story_runtime.states
            ),
            sensor_state_receipt_sha256s=tuple(
                value.authority_receipt_sha256 for value in self.sensor_states
            ),
            topology_receipt_sha256=self.topology.authority_receipt_sha256,
            support_domain_receipt_sha256=self.support_domain.authority_receipt_sha256,
            resonance_graph_receipt_sha256=self.resonance_graph.authority_receipt_sha256,
            resonance_operator_receipt_sha256=(
                self.resonance_operator.authority_receipt_sha256
            ),
            basin_profile_receipt_sha256=self.basin_profile.authority_receipt_sha256,
            typed_language_kernel_binding_receipt_sha256=(
                self.typed_language_kernel_binding.authority_receipt_sha256
            ),
            typed_language_phase_calibration_id=self.typed_language_phase_calibration_id,
            typed_language_phase_kappa=self.typed_language_phase_kappa,
            typed_language_source_epoch=self.typed_language_source_epoch,
        )
        if (
            self.checkpoint_receipt_payload != expected
            or receipt_sha256(expected) != self.checkpoint_receipt_sha256
            or registry.resolve(
                self.checkpoint_receipt_sha256, "recall runtime checkpoint receipt"
            )
            != expected
        ):
            raise ReceiptError("recall runtime checkpoint differs from its own receipt")


def mount_recall_story_runtime_checkpoint(
    *,
    checkpoint_id: str,
    story_profile: MountedStoryNativeReplayProfile,
    boundary: MountedAuthenticatedClosedStoryBoundary,
    pre_window_state: MountedPreWindowState,
    story_runtime: StoryChemistryRuntime,
    sensor_states: tuple[MountedStorySensorState, ...],
    topology: MountedFieldTopology,
    support_domain: MountedSupportDomain,
    resonance_graph: MountedResonanceGraph,
    resonance_operator: ResonanceOperatorAuthority,
    basin_profile: MountedStoryGlobalUFBasinProfile,
    typed_language_kernel_binding: MountedTypedLanguageKernelBinding,
    typed_language_phase_calibration_id: str,
    typed_language_phase_kappa: Fraction,
    typed_language_source_epoch: str,
    receipt_registry: ReceiptRegistry,
) -> MountedRecallStoryRuntimeCheckpoint:
    """Mount and verify one :class:`MountedRecallStoryRuntimeCheckpoint`.

    Every argument must already be a real, independently-typed, already-
    mountable authority -- built the same way every other authority in this
    package is built (e.g. via ``six_lane_runtime_mount.py``'s ``mount_*``
    functions for the six-lane side, and ``story_native_replay.py`` /
    ``story_chemistry.py`` production constructors for the five-sense side).
    This function selects, invents, or infers nothing; it only cross-
    verifies and receipts the bundle as a whole, exactly mirroring
    ``recall_story_episode_archive.create_recall_story_episode``'s own
    "verify every piece, then bind their digests" shape.
    """

    for value, expected_type, name in (
        (story_profile, MountedStoryNativeReplayProfile, "a mounted story native-replay profile"),
        (boundary, MountedAuthenticatedClosedStoryBoundary, "an authenticated closed story boundary"),
        (pre_window_state, MountedPreWindowState, "a mounted pre-window state"),
        (story_runtime, StoryChemistryRuntime, "a mounted story chemistry runtime"),
        (topology, MountedFieldTopology, "a mounted field topology"),
        (support_domain, MountedSupportDomain, "a mounted support domain"),
        (resonance_graph, MountedResonanceGraph, "a mounted resonance graph"),
        (resonance_operator, ResonanceOperatorAuthority, "a mounted resonance operator authority"),
        (basin_profile, MountedStoryGlobalUFBasinProfile, "a mounted basin profile"),
        (
            typed_language_kernel_binding,
            MountedTypedLanguageKernelBinding,
            "a mounted typed-language kernel binding",
        ),
    ):
        if not isinstance(value, expected_type):
            raise ReceiptError(f"recall runtime checkpoint requires {name}")
    if not isinstance(sensor_states, tuple) or not sensor_states:
        raise ReceiptError(
            "recall runtime checkpoint requires the pre-window native sensor states"
        )

    payload = recall_story_runtime_checkpoint_receipt_payload(
        checkpoint_id=checkpoint_id,
        story_profile_receipt_sha256=story_profile.authority_receipt_sha256,
        boundary_receipt_sha256=boundary.authority_receipt_sha256,
        pre_window_state_receipt_sha256=pre_window_state.authority_receipt_sha256,
        story_runtime_manifest_receipt_sha256=story_runtime.manifest.receipt_sha256,
        story_runtime_state_receipt_sha256s=tuple(
            value.receipt_sha256 for value in story_runtime.states
        ),
        sensor_state_receipt_sha256s=tuple(
            value.authority_receipt_sha256 for value in sensor_states
        ),
        topology_receipt_sha256=topology.authority_receipt_sha256,
        support_domain_receipt_sha256=support_domain.authority_receipt_sha256,
        resonance_graph_receipt_sha256=resonance_graph.authority_receipt_sha256,
        resonance_operator_receipt_sha256=resonance_operator.authority_receipt_sha256,
        basin_profile_receipt_sha256=basin_profile.authority_receipt_sha256,
        typed_language_kernel_binding_receipt_sha256=(
            typed_language_kernel_binding.authority_receipt_sha256
        ),
        typed_language_phase_calibration_id=typed_language_phase_calibration_id,
        typed_language_phase_kappa=typed_language_phase_kappa,
        typed_language_source_epoch=typed_language_source_epoch,
    )
    registry = extend_receipt_registry(receipt_registry, payload)
    checkpoint = MountedRecallStoryRuntimeCheckpoint(
        checkpoint_id=checkpoint_id,
        story_profile=story_profile,
        boundary=boundary,
        pre_window_state=pre_window_state,
        story_runtime=story_runtime,
        sensor_states=tuple(sensor_states),
        topology=topology,
        support_domain=support_domain,
        resonance_graph=resonance_graph,
        resonance_operator=resonance_operator,
        basin_profile=basin_profile,
        typed_language_kernel_binding=typed_language_kernel_binding,
        typed_language_phase_calibration_id=typed_language_phase_calibration_id,
        typed_language_phase_kappa=typed_language_phase_kappa,
        typed_language_source_epoch=typed_language_source_epoch,
        receipt_registry=registry,
        checkpoint_receipt_sha256=receipt_sha256(payload),
        checkpoint_receipt_payload=payload,
    )
    checkpoint.verify()
    return checkpoint


def mount_recall_language_interface_genesis(
    *,
    kernel_binding: MountedTypedLanguageKernelBinding,
    phase_calibration_id: str,
    phase_kappa: Fraction,
    source_epoch: str,
    source_time: Fraction,
    genesis_marker: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[MountedRecallLanguageInterface, ReceiptRegistry]:
    """Mount one fresh, genesis :class:`MountedRecallLanguageInterface`.

    Synced to ``source_time`` (in production, the checkpoint's own basin
    genesis instant -- see the module docstring for why a fresh genesis
    state, not one carried across turns, is what this Protocol's one real
    consumer, ``FreshRecallClosedExperienceExecutor._typed_input``, actually
    requires). ``genesis_marker`` is caller-declared, opaque, receipted data:
    there is no ratified derivation for a typed-language genesis anywhere in
    this repository, exactly mirroring
    ``mount_typed_language_kernel_binding``'s own ``derivation_payload``.
    """

    if not isinstance(kernel_binding, MountedTypedLanguageKernelBinding):
        raise ReceiptError(
            "recall language interface requires a mounted typed-language kernel binding"
        )
    kernel_binding.verify(receipt_registry)
    require_identifier(
        phase_calibration_id, "recall language interface phase calibration id"
    )
    require_fraction(phase_kappa, "recall language interface phase kappa")
    require_identifier(source_epoch, "recall language interface source epoch")
    require_fraction(source_time, "recall language interface source time")
    require_identifier(genesis_marker, "recall language interface genesis marker")
    genesis_payload = _canonical_bytes(
        {
            "genesis_marker": genesis_marker,
            "kernel_binding_receipt_sha256": kernel_binding.authority_receipt_sha256,
            "schema": RECALL_LANGUAGE_INTERFACE_GENESIS_SCHEMA,
            "source_epoch": source_epoch,
            "source_time": _fraction_text(source_time),
        }
    )
    registry = extend_receipt_registry(receipt_registry, genesis_payload)
    state = TypedLanguageState(
        phase_calibration_id,
        source_epoch,
        -1,
        source_time,
        Fraction(0),
        receipt_sha256(genesis_payload),
    )
    interface = MountedRecallLanguageInterface(kernel_binding, state, phase_kappa)
    interface.verify(registry)
    return interface, registry


@dataclass(frozen=True, slots=True)
class ProductionRecallStoryRuntimeResolver:
    """Real ``RecallStoryRuntimeResolver`` (structurally satisfies the
    Protocol in ``fresh_recall_executor.py``) plus the
    ``MountedRecallLanguageInterface`` construction path.

    Constructed from one already-mounted, already-verified
    :class:`MountedRecallStoryRuntimeCheckpoint` -- see the module docstring
    for why this is the real, necessary extra input beyond the Protocol's
    bare ``(episode, receipt_registry)`` signature, and for the genuine
    upstream requirement (episodes must be sealed against real basin
    authorities) this resolver's correctness depends on but cannot itself
    enforce retroactively.
    """

    checkpoint: MountedRecallStoryRuntimeCheckpoint

    def __post_init__(self) -> None:
        if not isinstance(self.checkpoint, MountedRecallStoryRuntimeCheckpoint):
            raise ReceiptError(
                "recall story runtime resolver requires a mounted recall runtime checkpoint"
            )
        self.checkpoint.verify()

    def resolve_runtime(
        self,
        *,
        episode: RecallStoryEpisode,
        receipt_registry: ReceiptRegistry,
    ) -> MountedRecallStoryRuntime:
        if not isinstance(episode, RecallStoryEpisode):
            raise ReceiptError(
                "recall story runtime resolver requires a typed archived episode"
            )
        episode.verify()
        checkpoint = self.checkpoint
        if checkpoint.story_profile.authority_receipt_sha256 != episode.profile_binding_sha256:
            raise ReceiptError(
                "recall runtime checkpoint was mounted for a different story "
                "profile than the one this episode was archived under"
            )
        if checkpoint.boundary.authority_receipt_sha256 != episode.boundary_receipt_sha256:
            raise ReceiptError(
                "recall runtime checkpoint boundary differs from the exact "
                "boundary this episode was archived against"
            )
        if (
            checkpoint.pre_window_state.authority_receipt_sha256
            != episode.pre_window_state_receipt_sha256
        ):
            raise ReceiptError(
                "recall runtime checkpoint pre-window state differs from the "
                "exact pre-window state this episode was archived against"
            )
        if tuple(
            value.receipt_sha256 for value in checkpoint.story_runtime.states
        ) != episode.pre_window_receiver_state_receipt_sha256s:
            raise ReceiptError(
                "recall runtime checkpoint receiver states differ from this "
                "episode's archived pre-window receiver states"
            )
        if tuple(
            value.authority_receipt_sha256 for value in checkpoint.sensor_states
        ) != episode.pre_window_sensor_state_receipt_sha256s:
            raise ReceiptError(
                "recall runtime checkpoint native sensor states differ from "
                "this episode's archived pre-window sensor states"
            )
        merged = _extend_records(receipt_registry, checkpoint.receipt_registry.records)
        runtime = MountedRecallStoryRuntime(
            episode_receipt_sha256=episode.episode_receipt_sha256,
            story_profile=checkpoint.story_profile,
            boundary=checkpoint.boundary,
            pre_window_state=checkpoint.pre_window_state,
            story_runtime=checkpoint.story_runtime,
            sensor_states=checkpoint.sensor_states,
            basin_profile=checkpoint.basin_profile,
            topology=checkpoint.topology,
            support_domain=checkpoint.support_domain,
            resonance_graph=checkpoint.resonance_graph,
            resonance_operator=checkpoint.resonance_operator,
            receipt_registry=checkpoint.receipt_registry,
        )
        runtime.verify(episode=episode, receipt_registry=merged)
        return runtime

    def mount_language_interface(
        self,
        *,
        genesis_marker: str,
        receipt_registry: ReceiptRegistry,
    ) -> tuple[MountedRecallLanguageInterface, ReceiptRegistry]:
        """Mount one fresh :class:`MountedRecallLanguageInterface` synced to
        this resolver's own checkpoint (kernel binding, phase authorities,
        and the basin's own genesis instant)."""

        checkpoint = self.checkpoint
        return mount_recall_language_interface_genesis(
            kernel_binding=checkpoint.typed_language_kernel_binding,
            phase_calibration_id=checkpoint.typed_language_phase_calibration_id,
            phase_kappa=checkpoint.typed_language_phase_kappa,
            source_epoch=checkpoint.typed_language_source_epoch,
            source_time=checkpoint.basin_profile.initial_field_state.source_time,
            genesis_marker=genesis_marker,
            receipt_registry=receipt_registry,
        )


__all__ = (
    "RECALL_STORY_RUNTIME_CHECKPOINT_SCHEMA",
    "RECALL_LANGUAGE_INTERFACE_GENESIS_SCHEMA",
    "MountedRecallStoryRuntimeCheckpoint",
    "ProductionRecallStoryRuntimeResolver",
    "mount_recall_language_interface_genesis",
    "mount_recall_story_runtime_checkpoint",
    "recall_story_runtime_checkpoint_receipt_payload",
)
