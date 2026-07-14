"""Concrete fresh-recall execution through heterogeneous six-lane L6.

The executor resolves one exact archived five-sense episode from the sensory
receipts cited by the committed output binding.  It stages the bound Unicode
scalar through the mounted 14-place typed-language interface, runs all five
sensor replays plus the complete discrete language tangent cone, and evaluates
replay-scoped self-recall origin, SafeMode, exact-zero fresh event support,
Fixed-42 L6, pending commit, and Global-UF authorities.

Archived five-sense transport receipts cannot equal the new six-lane
transport receipts: the latter bind a different topology and new S_UF/R_UF
facts.  The invariant that survives re-entry is stronger and physical: every
archived raw L0--L4 trace must be the exact raw trace carried by one fresh
six-lane evidence record.  ``FreshRecallArchiveLineageAuthority`` preserves
that one-to-one relation without flattening either evidence record.

The final provider bundle uses the explicit heterogeneous-L6 assembly: five
continuous same-cell sensor tangent authorities remain independent from the
complete discrete language cone, while their exact row union and rank bind one
six-lane L6 result.  No language row, commit, safety fact, or event is
fabricated.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Protocol

from .closed_experience import (
    ClosedExperienceProviderBundle,
    ClosedExperienceProviderUnknown,
    ProviderStatus,
    assemble_closed_experience_provider_bundle,
)
from .commit import (
    L6ScopeAuthority,
    evaluate_commit_boundary,
    evaluate_pending_global_uf_conjunction,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
)
from .event_support import (
    EventSupportEvaluationStatus,
    evaluate_event_support,
)
from .experience_origin import (
    ExperienceOriginAuthority,
    ExperienceOriginKind,
    experience_origin_authority_receipt_payload,
)
from .fresh_recall_provider import RecallClosedExperienceExecution
from .global_uf import MountedPreWindowState, ReplayKind
from .heterogeneous_l6 import assemble_heterogeneous_l6
from .l6 import ActiveLaneState, L6Lane, L6PredicateInputs, evaluate_l6
from .language import (
    TRIT_PLACES,
    MountedTypedLanguageKernelBinding,
    TypedLanguageEvent,
    TypedLanguageFrozenKernelInput,
    TypedLanguageState,
    build_typed_language_frozen_kernel_input,
    encode_balanced_ternary_scalar,
    typed_language_event_receipt_payload,
)
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
    require_fraction,
    require_identifier,
    sha256_digest,
)
from .operators import (
    MountedResonanceGraph,
    MountedSupportDomain,
    ResonanceOperatorAuthority,
)
from .field import MountedFieldTopology
from .output import (
    CommittedMotifEvent,
    MotifOutputBinding,
    OutputActuation,
    OutputBindingKind,
    OutputReason,
    OutputStatus,
    StageDisposition,
)
from .recall_story_episode_archive import (
    RecallStoryEpisode,
    RecallStoryEpisodeArchive,
)
from .safe_mode import IntegrityFact, MountedSafeModeScope, evaluate_safe_mode
from .story_chemistry import StoryChemistryRuntime
from .story_global_uf_basin import (
    MountedStoryGlobalUFBasinProfile,
    MountedStoryReplayAuthorities,
    PreparedStoryReplayContext,
    StoryGlobalUFPreparation,
    evaluate_story_global_uf,
    prepare_story_global_uf,
)
from .story_native_replay import (
    MountedAuthenticatedClosedStoryBoundary,
    MountedStoryNativeReplayProfile,
    MountedStorySensorState,
)


FRESH_RECALL_EXECUTOR_OPERATOR_ID = (
    "glew.recall.exact_archived_story_six_lane_execution.v1"
)
FRESH_RECALL_LINEAGE_OPERATOR_ID = (
    "glew.recall.archived_to_six_lane_raw_trace_lineage.v1"
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _extend_records(
    registry: ReceiptRegistry,
    records: tuple[ReceiptRecord, ...],
) -> ReceiptRegistry:
    if not isinstance(registry, ReceiptRegistry):
        raise ReceiptError("fresh recall requires an immutable receipt registry")
    result = list(registry.records)
    mounted = {value.digest: value.payload for value in result}
    for record in records:
        if not isinstance(record, ReceiptRecord):
            raise ReceiptError("fresh recall received an untyped receipt record")
        prior = mounted.get(record.digest)
        if prior is not None:
            if prior != record.payload:
                raise ReceiptError("fresh recall receipt digest collision")
            continue
        mounted[record.digest] = record.payload
        result.append(record)
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(result),
    )


def _extend_payloads(
    registry: ReceiptRegistry,
    payloads: tuple[bytes, ...],
) -> ReceiptRegistry:
    records = []
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("fresh recall generated an empty receipt")
        records.append(ReceiptRecord(receipt_sha256(payload), payload))
    return _extend_records(registry, tuple(records))


def _verify_extension(before: ReceiptRegistry, after: ReceiptRegistry) -> None:
    if before.profile_binding_sha256 != after.profile_binding_sha256:
        raise ReceiptError("fresh recall changed the mounted runtime profile")
    for record in before.records:
        if after.resolve(record.digest, "prior fresh-recall receipt") != record.payload:
            raise ReceiptError("fresh recall changed an existing receipt")


@dataclass(frozen=True, slots=True)
class FreshRecallLineageEntry:
    lane_id: str
    port_id: str
    archived_evidence_receipt_sha256: str
    archived_raw_record_sha256: str
    fresh_evidence_receipt_sha256: str
    fresh_raw_record_sha256: str

    def __post_init__(self) -> None:
        require_identifier(self.lane_id, "recall lineage lane")
        require_identifier(self.port_id, "recall lineage port")
        for value, name in (
            (self.archived_evidence_receipt_sha256, "archived evidence receipt"),
            (self.archived_raw_record_sha256, "archived raw trace receipt"),
            (self.fresh_evidence_receipt_sha256, "fresh evidence receipt"),
            (self.fresh_raw_record_sha256, "fresh raw trace receipt"),
        ):
            sha256_digest(value, name)
        if self.archived_raw_record_sha256 != self.fresh_raw_record_sha256:
            raise ReceiptError("fresh recall changed an archived raw L0-L4 trace")


def fresh_recall_archive_lineage_receipt_payload(
    *,
    episode_receipt_sha256: str,
    source_binding_receipt_sha256: str,
    fresh_closed_experience_receipt_sha256: str,
    entries: tuple[FreshRecallLineageEntry, ...],
) -> bytes:
    for value, name in (
        (episode_receipt_sha256, "recall lineage episode receipt"),
        (source_binding_receipt_sha256, "recall lineage source binding"),
        (
            fresh_closed_experience_receipt_sha256,
            "recall lineage fresh closed experience",
        ),
    ):
        sha256_digest(value, name)
    if not isinstance(entries, tuple) or not entries:
        raise ReceiptError("recall lineage requires immutable five-sense entries")
    keys = tuple((value.lane_id, value.port_id) for value in entries)
    if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
        raise ReceiptError("recall lineage entries are not canonical and unique")
    return _canonical_bytes(
        {
            "entries": [
                {
                    "archived_evidence_receipt_sha256": (
                        value.archived_evidence_receipt_sha256
                    ),
                    "archived_raw_record_sha256": value.archived_raw_record_sha256,
                    "fresh_evidence_receipt_sha256": (
                        value.fresh_evidence_receipt_sha256
                    ),
                    "fresh_raw_record_sha256": value.fresh_raw_record_sha256,
                    "lane_id": value.lane_id,
                    "port_id": value.port_id,
                }
                for value in entries
            ],
            "episode_receipt_sha256": episode_receipt_sha256,
            "fresh_closed_experience_receipt_sha256": (
                fresh_closed_experience_receipt_sha256
            ),
            "operator": FRESH_RECALL_LINEAGE_OPERATOR_ID,
            "schema": "glew.recall.archive_to_fresh_raw_trace_lineage.v1",
            "source_binding_receipt_sha256": source_binding_receipt_sha256,
        }
    )


@dataclass(frozen=True, slots=True)
class FreshRecallArchiveLineageAuthority:
    episode_receipt_sha256: str
    source_binding_receipt_sha256: str
    fresh_closed_experience_receipt_sha256: str
    entries: tuple[FreshRecallLineageEntry, ...]
    authority_receipt_sha256: str
    authority_receipt_payload: bytes

    def verify(
        self,
        *,
        episode: RecallStoryEpisode,
        fresh_sensory_evidence: tuple,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        episode.verify()
        if self.episode_receipt_sha256 != episode.episode_receipt_sha256:
            raise ReceiptError("recall lineage belongs to another archived episode")
        receipt_registry.resolve(
            self.source_binding_receipt_sha256,
            "recall lineage source binding receipt",
        )
        receipt_registry.resolve(
            self.fresh_closed_experience_receipt_sha256,
            "recall lineage fresh closed-experience receipt",
        )
        archived = {
            (value.lane_id, value.port_id): value
            for value in episode.sensory_evidence_bindings
        }
        fresh = {(value.lane_id, value.port_id): value for value in fresh_sensory_evidence}
        if len(archived) != len(episode.sensory_evidence_bindings):
            raise ReceiptError("archived lineage contains an ambiguous sensory port")
        if len(fresh) != len(fresh_sensory_evidence):
            raise ReceiptError("fresh lineage contains an ambiguous sensory port")
        if set(archived) != set(fresh) or len(archived) != 5:
            raise ReceiptError("recall lineage does not exactly cover five senses")
        expected_entries = tuple(
            FreshRecallLineageEntry(
                lane_id=key[0],
                port_id=key[1],
                archived_evidence_receipt_sha256=(
                    archived[key].evidence_receipt_sha256
                ),
                archived_raw_record_sha256=archived[key].raw_record_sha256,
                fresh_evidence_receipt_sha256=(
                    fresh[key].evidence_receipt_sha256
                ),
                fresh_raw_record_sha256=fresh[key].raw_record.digest,
            )
            for key in sorted(archived)
        )
        if self.entries != expected_entries:
            raise ReceiptError("recall lineage differs from the exact evidence pairings")
        for entry in self.entries:
            receipt_registry.resolve(
                entry.archived_evidence_receipt_sha256,
                "archived lineage evidence receipt",
            )
            receipt_registry.resolve(
                entry.archived_raw_record_sha256,
                "archived lineage raw L0-L4 trace",
            )
            receipt_registry.resolve(
                entry.fresh_evidence_receipt_sha256,
                "fresh lineage evidence receipt",
            )
            receipt_registry.resolve(
                entry.fresh_raw_record_sha256,
                "fresh lineage raw L0-L4 trace",
            )
        expected = fresh_recall_archive_lineage_receipt_payload(
            episode_receipt_sha256=self.episode_receipt_sha256,
            source_binding_receipt_sha256=self.source_binding_receipt_sha256,
            fresh_closed_experience_receipt_sha256=(
                self.fresh_closed_experience_receipt_sha256
            ),
            entries=self.entries,
        )
        if (
            self.authority_receipt_payload != expected
            or receipt_sha256(expected) != self.authority_receipt_sha256
            or receipt_registry.resolve(
                self.authority_receipt_sha256,
                "fresh recall archive-lineage authority receipt",
            )
            != expected
        ):
            raise ReceiptError("recall archive lineage differs from exact receipt")


def create_fresh_recall_archive_lineage(
    *,
    episode: RecallStoryEpisode,
    source_binding_receipt_sha256: str,
    fresh_closed_experience_receipt_sha256: str,
    fresh_sensory_evidence: tuple,
    receipt_registry: ReceiptRegistry,
) -> tuple[FreshRecallArchiveLineageAuthority, ReceiptRegistry]:
    """Bind unchanged raw senses to their new topology-bound evidence records."""

    episode.verify()
    archived = {
        (value.lane_id, value.port_id): value
        for value in episode.sensory_evidence_bindings
    }
    fresh = {(value.lane_id, value.port_id): value for value in fresh_sensory_evidence}
    if (
        len(archived) != len(episode.sensory_evidence_bindings)
        or len(fresh) != len(fresh_sensory_evidence)
        or set(archived) != set(fresh)
        or len(archived) != 5
    ):
        raise ReceiptError("archive-to-fresh lineage is not exact one-to-one five-sense")
    entries = tuple(
        FreshRecallLineageEntry(
            key[0],
            key[1],
            archived[key].evidence_receipt_sha256,
            archived[key].raw_record_sha256,
            fresh[key].evidence_receipt_sha256,
            fresh[key].raw_record.digest,
        )
        for key in sorted(archived)
    )
    payload = fresh_recall_archive_lineage_receipt_payload(
        episode_receipt_sha256=episode.episode_receipt_sha256,
        source_binding_receipt_sha256=source_binding_receipt_sha256,
        fresh_closed_experience_receipt_sha256=(
            fresh_closed_experience_receipt_sha256
        ),
        entries=entries,
    )
    registry = _extend_payloads(
        receipt_registry,
        (episode.episode_receipt_payload, payload),
    )
    authority = FreshRecallArchiveLineageAuthority(
        episode.episode_receipt_sha256,
        source_binding_receipt_sha256,
        fresh_closed_experience_receipt_sha256,
        entries,
        receipt_sha256(payload),
        payload,
    )
    authority.verify(
        episode=episode,
        fresh_sensory_evidence=fresh_sensory_evidence,
        receipt_registry=registry,
    )
    return authority, registry


@dataclass(frozen=True, slots=True)
class MountedRecallStoryRuntime:
    """Non-serialized objects required to replay one archived episode exactly."""

    episode_receipt_sha256: str
    story_profile: MountedStoryNativeReplayProfile
    boundary: MountedAuthenticatedClosedStoryBoundary
    pre_window_state: MountedPreWindowState
    story_runtime: StoryChemistryRuntime
    sensor_states: tuple[MountedStorySensorState, ...]
    basin_profile: MountedStoryGlobalUFBasinProfile
    topology: MountedFieldTopology
    support_domain: MountedSupportDomain
    resonance_graph: MountedResonanceGraph
    resonance_operator: ResonanceOperatorAuthority
    receipt_registry: ReceiptRegistry

    def verify(
        self,
        *,
        episode: RecallStoryEpisode,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        if self.episode_receipt_sha256 != episode.episode_receipt_sha256:
            raise ReceiptError("mounted recall runtime belongs to another episode")
        _verify_extension(self.receipt_registry, receipt_registry)
        if self.story_profile.authority_receipt_sha256 != episode.profile_binding_sha256:
            raise ReceiptError("mounted recall story profile differs from archive")
        if self.boundary.authority_receipt_sha256 != episode.boundary_receipt_sha256:
            raise ReceiptError("mounted recall boundary differs from archive")
        if self.pre_window_state.authority_receipt_sha256 != (
            episode.pre_window_state_receipt_sha256
        ):
            raise ReceiptError("mounted recall pre-window state differs from archive")
        if tuple(value.receipt_sha256 for value in self.story_runtime.states) != (
            episode.pre_window_receiver_state_receipt_sha256s
        ):
            raise ReceiptError("mounted receiver states differ from archive")
        if tuple(value.authority_receipt_sha256 for value in self.sensor_states) != (
            episode.pre_window_sensor_state_receipt_sha256s
        ):
            raise ReceiptError("mounted native sensor states differ from archive")
        self.story_profile.verify(receipt_registry)
        self.boundary.verify(
            profile=self.story_profile,
            receipt_registry=receipt_registry,
        )
        self.pre_window_state.verify(receipt_registry)
        self.support_domain.verify(receipt_registry)
        self.resonance_graph.verify(receipt_registry)
        self.resonance_operator.verify(receipt_registry)
        self.basin_profile.verify(
            story_profile=self.story_profile,
            pre_window_state=self.pre_window_state,
            topology=self.topology,
            receipt_registry=receipt_registry,
        )


class RecallStoryRuntimeResolver(Protocol):
    def resolve_runtime(
        self,
        *,
        episode: RecallStoryEpisode,
        receipt_registry: ReceiptRegistry,
    ) -> MountedRecallStoryRuntime: ...


@dataclass(frozen=True, slots=True)
class MountedRecallLanguageInterface:
    kernel_binding: MountedTypedLanguageKernelBinding
    initial_state: TypedLanguageState
    phase_kappa: Fraction

    def verify(self, receipt_registry: ReceiptRegistry) -> None:
        require_fraction(self.phase_kappa, "fresh recall typed phase kappa")
        self.kernel_binding.verify(receipt_registry)
        receipt_registry.resolve(
            self.initial_state.genesis_receipt_sha256,
            "fresh recall typed genesis receipt",
        )
        if self.initial_state.disrupted:
            raise ReceiptError("fresh recall typed interface is disrupted")


@dataclass(frozen=True, slots=True)
class MountedRecallReplayIntegrity:
    request_receipt_sha256: str
    safe_mode_scope: MountedSafeModeScope
    safe_mode_facts: tuple[IntegrityFact, ...]
    disruption_clear: bool | None
    receipt_registry: ReceiptRegistry

    def __post_init__(self) -> None:
        sha256_digest(
            self.request_receipt_sha256,
            "fresh recall integrity replay request",
        )
        if not isinstance(self.safe_mode_facts, tuple):
            raise ReceiptError("fresh recall integrity facts must be immutable")
        if self.disruption_clear is not None and not isinstance(
            self.disruption_clear,
            bool,
        ):
            raise ReceiptError("fresh recall disruption state must be bool or unknown")


class RecallReplayIntegrityProvider(Protocol):
    """External measured integrity; the executor never invents clear facts."""

    def mount_integrity(
        self,
        *,
        context: PreparedStoryReplayContext,
        episode: RecallStoryEpisode,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        receipt_registry: ReceiptRegistry,
    ) -> MountedRecallReplayIntegrity: ...


@dataclass(frozen=True, slots=True)
class LineagedRecallClosedExperienceExecution(RecallClosedExperienceExecution):
    episode: RecallStoryEpisode
    archive_lineage: FreshRecallArchiveLineageAuthority

    def verify(self, prior_registry: ReceiptRegistry) -> None:
        super().verify(prior_registry)
        self.archive_lineage.verify(
            episode=self.episode,
            fresh_sensory_evidence=self.sensory_evidence,
            receipt_registry=self.receipt_registry,
        )


def _recall_origin_source_receipt_payload(
    *,
    episode_receipt_sha256: str,
    request_receipt_sha256: str,
    source_event_receipt_sha256: str,
    staged_output_receipt_sha256: str,
    source_binding_receipt_sha256: str,
) -> bytes:
    for value in (
        episode_receipt_sha256,
        request_receipt_sha256,
        source_event_receipt_sha256,
        staged_output_receipt_sha256,
        source_binding_receipt_sha256,
    ):
        sha256_digest(value, "fresh recall origin source receipt")
    return _canonical_bytes(
        {
            "episode_receipt_sha256": episode_receipt_sha256,
            "operator": FRESH_RECALL_EXECUTOR_OPERATOR_ID,
            "request_receipt_sha256": request_receipt_sha256,
            "schema": "glew.recall.self_generated_origin_source.v1",
            "source_binding_receipt_sha256": source_binding_receipt_sha256,
            "source_event_receipt_sha256": source_event_receipt_sha256,
            "staged_output_receipt_sha256": staged_output_receipt_sha256,
        }
    )


class FreshRecallClosedExperienceExecutor:
    """Run a fresh scalar re-entry through the complete six-lane field."""

    def __init__(
        self,
        *,
        executor_id: str,
        archive: RecallStoryEpisodeArchive,
        runtime_resolver: RecallStoryRuntimeResolver,
        language_interface: MountedRecallLanguageInterface,
        integrity_provider: RecallReplayIntegrityProvider,
    ) -> None:
        self.executor_id = require_identifier(executor_id, "fresh recall executor id")
        if not isinstance(archive, RecallStoryEpisodeArchive):
            raise ReceiptError("fresh recall executor requires an exact story archive")
        self.archive = archive
        self.runtime_resolver = runtime_resolver
        self.language_interface = language_interface
        self.integrity_provider = integrity_provider

    def _verify_staged_source(
        self,
        *,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        receipt_registry: ReceiptRegistry,
    ) -> None:
        source_event.verify(receipt_registry)
        source_binding.verify(receipt_registry)
        if source_binding.kind is not OutputBindingKind.LANGUAGE_SCALAR:
            raise ReceiptError("fresh recall source binding is not one typed scalar")
        if (
            source_event.motif_receipt_sha256 != source_binding.motif_receipt_sha256
            or source_event.sensory_evidence_receipt_sha256s
            != source_binding.sensory_evidence_receipt_sha256s
        ):
            raise ReceiptError("fresh recall event and source binding differ")
        settlement = staged_output.receipt
        # A STAGED_PRIVATE settlement can never legitimately carry
        # `binding_receipt_sha256s`. `output._output_settlement_receipt_payload`
        # enforces this as a fail-closed contract on its OWN construction: any
        # non-``EXPRESSION_RELEASED`` status must have an EMPTY
        # `binding_receipt_sha256s` (and empty `visible_text` /
        # `emitted_scalar_codepoints` / `contributing_event_receipt_sha256s`) --
        # only the ``EXPRESSION_RELEASED``/``EXPRESSION_CLOSE`` branch of
        # `output.RememberedExpressionActuator._process_verified` ever
        # populates it, from the actuator's private `_staged` accumulator.
        # This check used to compare
        # `settlement.binding_receipt_sha256s == (source_binding.binding_receipt_sha256,)`,
        # a value the real actuator's `STAGED_PRIVATE` branch never produces
        # (it stays the default empty tuple), so that comparison failed
        # closed on every genuine private-staged recall, not just a tampered
        # one (independently documented in
        # `recall_replay_integrity_provider.py`'s module docstring, which for
        # the same reason deliberately does not compare
        # `binding_receipt_sha256s` in its own `persistence` fact either).
        #
        # What genuinely ties this settlement back to `source_binding` for a
        # non-released status is NOT a settlement field naming the binding
        # directly -- which specific binding among possibly-several equal-
        # scalar bindings for one motif was staged is legitimately private
        # until release (see `RememberedExpressionActuator._process_verified`:
        # it picks `decoded[0]` from `binding_bank.for_motif(...)` and only
        # records that choice in the private `_staged` list). The real,
        # already-populated correlation is the existing chain: this
        # settlement's own `event_receipt_sha256` (checked below) ties it to
        # `source_event`, and `source_event.motif_receipt_sha256` /
        # `sensory_evidence_receipt_sha256s` (checked above) tie that same
        # event to `source_binding`. What is left to verify ON the settlement
        # itself, without inventing a new field, is that it carries exactly
        # the values a genuine STAGED_PRIVATE settlement can carry: `reason`
        # is `UNIQUE_COEXPERIENCED_LANGUAGE_BINDING` -- the only reason the
        # real actuator ever pairs with `STAGED_PRIVATE` (its sole production
        # call site), even though the payload builder does not itself
        # constrain `reason` against `status` -- and `binding_receipt_sha256s`
        # is exactly the empty tuple the actuator's own contract requires
        # (defense-in-depth against a malformed/foreign settlement object,
        # since a real one could never have been constructed otherwise).
        if (
            staged_output.text
            or settlement.status is not OutputStatus.STAGED_PRIVATE
            or settlement.reason is not OutputReason.UNIQUE_COEXPERIENCED_LANGUAGE_BINDING
            or settlement.stage_disposition is not StageDisposition.RETAINED_PRIVATE
            or settlement.event_receipt_sha256 != source_event.event_receipt_sha256
            or settlement.binding_receipt_sha256s != ()
        ):
            raise ReceiptError("fresh recall scalar was not exactly private-staged")

    def _typed_input(
        self,
        *,
        scalar: str,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        runtime: MountedRecallStoryRuntime,
        receipt_registry: ReceiptRegistry,
    ) -> TypedLanguageFrozenKernelInput:
        if len(scalar) != 1:
            raise ReceiptError("fresh recall requires exactly one bound Unicode scalar")
        grid_times = runtime.story_profile.grid.timestamps
        if len(grid_times) != TRIT_PLACES:
            raise ReceiptError("fresh recall language requires the exact 14-place grid")
        interface = self.language_interface
        interface.verify(receipt_registry)
        if interface.initial_state.last_timestamp != (
            runtime.basin_profile.initial_field_state.source_time
        ):
            raise ReceiptError("typed recall genesis and field pre-window time differ")
        trits = encode_balanced_ternary_scalar(ord(scalar))
        valid_times = tuple(
            timestamp
            for trit, timestamp in zip(trits, grid_times, strict=True)
            if trit.valid
        )
        identity = _canonical_bytes(
            {
                "binding": source_binding.binding_receipt_sha256,
                "event": source_event.event_receipt_sha256,
                "settlement": staged_output.receipt.receipt_sha256,
            }
        )
        event_id = f"fresh-recall-{receipt_sha256(identity)}"
        event_payload = typed_language_event_receipt_payload(
            text=scalar,
            event_id=event_id,
            interface_id=interface.kernel_binding.interface_id,
            source_epoch=interface.initial_state.source_epoch,
            valid_sample_times=valid_times,
        )
        registry = _extend_payloads(receipt_registry, (event_payload,))
        event = TypedLanguageEvent.from_text(
            text=scalar,
            event_id=event_id,
            interface_id=interface.kernel_binding.interface_id,
            source_epoch=interface.initial_state.source_epoch,
            valid_sample_times=valid_times,
            interface_receipt_sha256=(
                interface.kernel_binding.interface_receipt_sha256
            ),
            event_receipt_sha256=receipt_sha256(event_payload),
            phase_calibration_id=interface.initial_state.phase_calibration_id,
            phase_kappa=interface.phase_kappa,
            phase_calibration_receipt_sha256=(
                interface.kernel_binding.phase_calibration_receipt_sha256
            ),
        )
        return build_typed_language_frozen_kernel_input(
            event=event,
            initial_state=interface.initial_state,
            kernel_binding=interface.kernel_binding,
            receipt_registry=registry,
            complete_grid_times=grid_times,
        )

    def _mount_replay_authorities(
        self,
        *,
        preparation: StoryGlobalUFPreparation,
        runtime: MountedRecallStoryRuntime,
        episode: RecallStoryEpisode,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        receipt_registry: ReceiptRegistry,
    ) -> tuple[tuple[MountedStoryReplayAuthorities, ...], ReceiptRegistry]:
        registry = receipt_registry
        completeness = {
            value.lane: value.receipt_sha256
            for value in preparation.lane_completeness_receipts
        }
        mounted_values = []
        for context in preparation.contexts:
            integrity = self.integrity_provider.mount_integrity(
                context=context,
                episode=episode,
                source_event=source_event,
                staged_output=staged_output,
                source_binding=source_binding,
                receipt_registry=registry,
            )
            if not isinstance(integrity, MountedRecallReplayIntegrity):
                raise ReceiptError("fresh recall integrity provider returned invalid type")
            if integrity.request_receipt_sha256 != context.request.receipt_sha256:
                raise ReceiptError("fresh recall integrity belongs to another replay")
            _verify_extension(registry, integrity.receipt_registry)
            registry = integrity.receipt_registry
            seal = context.sealed.closed_experience
            origin_source = _recall_origin_source_receipt_payload(
                episode_receipt_sha256=episode.episode_receipt_sha256,
                request_receipt_sha256=context.request.receipt_sha256,
                source_event_receipt_sha256=source_event.event_receipt_sha256,
                staged_output_receipt_sha256=staged_output.receipt.receipt_sha256,
                source_binding_receipt_sha256=(
                    source_binding.binding_receipt_sha256
                ),
            )
            origin_id = f"{context.request.request_id}:self-recall-origin"
            origin_payload = experience_origin_authority_receipt_payload(
                origin_id=origin_id,
                kind=ExperienceOriginKind.SELF_GENERATED_RECALL,
                profile_binding_sha256=registry.profile_binding_sha256,
                topology_authority_receipt_sha256=(
                    runtime.topology.authority_receipt_sha256
                ),
                closed_experience_receipt_sha256=seal.authority_receipt_sha256,
                source_authority_receipt_sha256=receipt_sha256(origin_source),
            )
            origin = ExperienceOriginAuthority(
                origin_id,
                ExperienceOriginKind.SELF_GENERATED_RECALL,
                registry.profile_binding_sha256,
                runtime.topology.authority_receipt_sha256,
                seal.authority_receipt_sha256,
                receipt_sha256(origin_source),
                receipt_sha256(origin_payload),
            )
            registry = _extend_payloads(
                registry,
                (origin_source, origin_payload),
            )
            safe_mode = evaluate_safe_mode(
                authority_id=f"{context.request.request_id}:recall-safe-mode",
                topology_authority_receipt_sha256=(
                    runtime.topology.authority_receipt_sha256
                ),
                closed_experience_receipt_sha256=seal.authority_receipt_sha256,
                scope=integrity.safe_mode_scope,
                facts=integrity.safe_mode_facts,
                receipt_registry=registry,
            )
            registry = _extend_payloads(
                registry,
                safe_mode.generated_receipt_payloads,
            )
            event_support = evaluate_event_support(
                authority_id=f"{context.request.request_id}:recall-R-event",
                origin=origin,
                topology=runtime.topology,
                closed_experience_receipt_sha256=seal.authority_receipt_sha256,
                expression=context.expression_facts.expression,
                memory_energy=None,
                receipt_registry=registry,
            )
            if (
                event_support.status is not EventSupportEvaluationStatus.RESOLVED
                or event_support.exact_r_event != 0
            ):
                raise ReceiptError("self-generated recall did not resolve exact-zero R_event")
            registry = _extend_payloads(
                registry,
                event_support.generated_receipt_payloads,
            )
            evidence_by_lane = {
                value.lane_id: value for value in context.preparation.evidence
            }
            if set(evidence_by_lane) != {value.value for value in L6Lane}:
                raise ReceiptError("fresh recall L6 predicates lack one native lane")
            predicates = L6PredicateInputs(
                tuple(
                    ActiveLaneState(
                        lane,
                        evidence_by_lane[lane.value].coordinates.U_star_k,
                        True,
                        completeness[lane],
                    )
                    for lane in L6Lane
                ),
                integrity.disruption_clear,
            )
            l6_evaluation = evaluate_l6(
                preparation.fixed42_stack,
                predicates,
                registry,
            )
            l6_payload = l6_evaluation_receipt_payload(l6_evaluation)
            l6_scope_payload = l6_scope_authority_receipt_payload(
                authority_id=f"{context.request.request_id}:recall-L6-scope",
                topology_authority_receipt_sha256=(
                    runtime.topology.authority_receipt_sha256
                ),
                closed_experience_receipt_sha256=seal.authority_receipt_sha256,
                l6_evaluation_receipt_sha256=receipt_sha256(l6_payload),
            )
            l6_scope = L6ScopeAuthority(
                f"{context.request.request_id}:recall-L6-scope",
                runtime.topology.authority_receipt_sha256,
                seal.authority_receipt_sha256,
                receipt_sha256(l6_payload),
                receipt_sha256(l6_scope_payload),
            )
            registry = _extend_payloads(
                registry,
                (l6_payload, l6_scope_payload),
            )
            pending = evaluate_pending_global_uf_conjunction(
                topology=runtime.topology,
                recognition=context.expression_facts.recognition,
                l6_evaluation=l6_evaluation,
                l6_scope=l6_scope,
                closed_experience=seal,
                safe_mode=safe_mode.authority,
                event_support=event_support.authority,
                evidence=context.sealed.evidence,
                l5_applicability=context.sealed.l5_applicability,
                receipt_registry=registry,
            )
            registry = _extend_payloads(registry, (pending.receipt_payload,))
            mounted_values.append(
                MountedStoryReplayAuthorities(
                    context.request.receipt_sha256,
                    origin,
                    integrity.safe_mode_scope,
                    integrity.safe_mode_facts,
                    safe_mode,
                    None,
                    event_support,
                    predicates,
                    l6_evaluation,
                    l6_scope,
                    pending,
                )
            )
        return tuple(mounted_values), registry

    def execute(
        self,
        *,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        receipt_registry: ReceiptRegistry,
    ) -> RecallClosedExperienceExecution:
        self._verify_staged_source(
            source_event=source_event,
            staged_output=staged_output,
            source_binding=source_binding,
            receipt_registry=receipt_registry,
        )
        episode = self.archive.resolve(
            profile_binding_sha256=source_binding.profile_binding_sha256,
            sensory_evidence_receipt_sha256s=(
                source_binding.sensory_evidence_receipt_sha256s
            ),
        )
        registry = _extend_records(receipt_registry, episode.receipt_records)
        registry = _extend_payloads(
            registry,
            (self.archive.receipt_payload, episode.episode_receipt_payload),
        )
        runtime = self.runtime_resolver.resolve_runtime(
            episode=episode,
            receipt_registry=registry,
        )
        if not isinstance(runtime, MountedRecallStoryRuntime):
            raise ReceiptError("fresh recall runtime resolver returned invalid type")
        registry = _extend_records(registry, runtime.receipt_registry.records)
        registry = _extend_records(
            registry,
            runtime.story_runtime.receipt_registry.records,
        )
        runtime.verify(episode=episode, receipt_registry=registry)
        scalar = source_binding.decoded_scalar()
        typed_input = self._typed_input(
            scalar=scalar,
            source_event=source_event,
            staged_output=staged_output,
            source_binding=source_binding,
            runtime=runtime,
            receipt_registry=registry,
        )
        registry = _extend_records(registry, typed_input.receipt_registry.records)
        preparation = prepare_story_global_uf(
            story_profile=runtime.story_profile,
            basin_profile=runtime.basin_profile,
            boundary=runtime.boundary,
            pre_window_state=runtime.pre_window_state,
            story_runtime=runtime.story_runtime,
            sensor_states=runtime.sensor_states,
            typed_input=typed_input,
            topology=runtime.topology,
            grid=runtime.story_profile.grid,
            support_domain=runtime.support_domain,
            resonance_graph=runtime.resonance_graph,
            resonance_operator=runtime.resonance_operator,
            receipt_registry=registry,
        )
        registry = preparation.receipt_registry
        mounted, registry = self._mount_replay_authorities(
            preparation=preparation,
            runtime=runtime,
            episode=episode,
            source_event=source_event,
            staged_output=staged_output,
            source_binding=source_binding,
            receipt_registry=registry,
        )
        global_result = evaluate_story_global_uf(
            authority_id=f"{self.executor_id}:fresh-recall-global-UF",
            preparation=preparation,
            mounted_authorities=mounted,
            topology=runtime.topology,
            pre_window_state=runtime.pre_window_state,
            receipt_registry=registry,
        )
        registry = global_result.receipt_registry
        base_context = next(
            value
            for value in preparation.contexts
            if value.request.kind is ReplayKind.BASE
        )
        base_authorities = next(
            value
            for value in mounted
            if value.request_receipt_sha256 == base_context.request.receipt_sha256
        )
        commit = evaluate_commit_boundary(
            topology=runtime.topology,
            recognition=base_context.expression_facts.recognition,
            l6_evaluation=base_authorities.l6_evaluation,
            l6_scope=base_authorities.l6_scope,
            closed_experience=base_context.sealed.closed_experience,
            safe_mode=base_authorities.safe_mode_evaluation.authority,
            event_support=base_authorities.event_support_evaluation.authority,
            evidence=base_context.sealed.evidence,
            l5_applicability=base_context.sealed.l5_applicability,
            global_uf_validation=global_result.validation.authority,
            receipt_registry=registry,
        )
        registry = _extend_payloads(registry, (commit.receipt_payload,))
        sensory = tuple(
            value
            for value in base_context.sealed.evidence
            if value.lane_id != L6Lane.LANGUAGE.value
        )
        language_values = tuple(
            value
            for value in base_context.sealed.evidence
            if value.lane_id == L6Lane.LANGUAGE.value
        )
        if not language_values:
            raise ReceiptError("fresh recall base seal lacks language evidence")
        language = max(
            language_values,
            key=lambda value: (
                value.provenance.source_timestamp,
                value.provenance.source_index,
            ),
        )
        lineage, registry = create_fresh_recall_archive_lineage(
            episode=episode,
            source_binding_receipt_sha256=source_binding.binding_receipt_sha256,
            fresh_closed_experience_receipt_sha256=(
                base_context.sealed.closed_experience.authority_receipt_sha256
            ),
            fresh_sensory_evidence=sensory,
            receipt_registry=registry,
        )
        heterogeneous_l6 = assemble_heterogeneous_l6(
            sensor_production=preparation.sensor_l6_production,
            language_replay=preparation.language_replay,
            pre_window_state=runtime.pre_window_state,
            combined_stack=preparation.fixed42_stack,
            combined_rank=preparation.fixed42_rank,
            lane_completeness_receipts=(
                preparation.lane_completeness_receipts
            ),
            topology=runtime.topology,
            receipt_registry=registry,
        )
        registry = _extend_records(
            registry,
            heterogeneous_l6.receipt_registry.records,
        )
        assembled = assemble_closed_experience_provider_bundle(
            sealed=base_context.sealed,
            topology=runtime.topology,
            experience_origin=base_authorities.origin,
            safe_mode_evaluation=base_authorities.safe_mode_evaluation,
            event_support_evaluation=(
                base_authorities.event_support_evaluation
            ),
            global_uf_validation=global_result.validation,
            l6_production=heterogeneous_l6,
            l6_predicates=base_authorities.l6_predicates,
            l6_evaluation=base_authorities.l6_evaluation,
            l6_scope=base_authorities.l6_scope,
            receipt_registry=registry,
        )
        if isinstance(assembled, ClosedExperienceProviderUnknown):
            raise ReceiptError(
                "heterogeneous six-lane bundle is unresolved: "
                f"{assembled.missing_authority}: {assembled.reason}"
            )
        bundle = assembled
        if (
            bundle.status is not ProviderStatus.READY
            or bundle.sealed != base_context.sealed
            or bundle.experience_origin != base_authorities.origin
            or bundle.l6_evaluation != base_authorities.l6_evaluation
            or bundle.l6_scope != base_authorities.l6_scope
            or bundle.safe_mode_evaluation
            != base_authorities.safe_mode_evaluation
            or bundle.event_support_evaluation
            != base_authorities.event_support_evaluation
            or bundle.global_uf_result != global_result.validation
        ):
            raise ReceiptError("heterogeneous L6 bundle changed exact recall facts")
        registry = _extend_records(registry, bundle.receipt_registry.records)
        execution = LineagedRecallClosedExperienceExecution(
            bundle=bundle,
            expression_evaluation=base_context.expression_facts.evaluation,
            language_evidence=language,
            sensory_evidence=sensory,
            typed_language_input=typed_input,
            commit_decision=commit,
            receipt_registry=registry,
            episode=episode,
            archive_lineage=lineage,
        )
        execution.verify(receipt_registry)
        lineage.verify(
            episode=episode,
            fresh_sensory_evidence=sensory,
            receipt_registry=registry,
        )
        return execution


__all__ = (
    "FRESH_RECALL_EXECUTOR_OPERATOR_ID",
    "FRESH_RECALL_LINEAGE_OPERATOR_ID",
    "FreshRecallArchiveLineageAuthority",
    "FreshRecallClosedExperienceExecutor",
    "FreshRecallLineageEntry",
    "LineagedRecallClosedExperienceExecution",
    "MountedRecallLanguageInterface",
    "MountedRecallReplayIntegrity",
    "MountedRecallStoryRuntime",
    "RecallReplayIntegrityProvider",
    "RecallStoryRuntimeResolver",
    "create_fresh_recall_archive_lineage",
    "fresh_recall_archive_lineage_receipt_payload",
)
