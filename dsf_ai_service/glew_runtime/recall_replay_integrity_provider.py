"""Production ``RecallReplayIntegrityProvider`` (Step 5, spec section 9.6).

``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
section 9.6 requires a production implementation of
``fresh_recall_executor.RecallReplayIntegrityProvider``. Before this module,
no implementation existed anywhere in the repository -- every real pipeline
built so far (including Step 4's ``real_experience_learning_pipeline.py``)
simply *asserts* ``IntegrityFactState.CLEAR`` for its SafeMode facts, because
no production tamper-detector authority existed to compute them.

``mount_integrity`` is called once per prepared replay context (BASE and
each adjacent direction; ``fresh_recall_executor.py:693-701``), and its
output feeds directly into ``safe_mode.evaluate_safe_mode`` and the L6
predicate's ``disruption_clear`` (``fresh_recall_executor.py:742,789``).  A
wrong CLEAR there would let corrupted or tampered recalled state pass the
same safe-mode/L6 gate meant to catch it.  This module never asserts a
state it has not actually computed: every fact below is produced by
recomputing the canonical receipt bytes for a piece of real, already-mounted
state from the caller's own real objects, and comparing that recomputation
byte-for-byte against what was actually recorded/mounted -- the same
"recompute the expected receipt, compare against the recorded receipt"
convention used throughout this codebase (``ReceiptRegistry.resolve`` +
``receipt_sha256`` equality in ``model.py``; ``GenerationIdentityBinding
.verify`` in ``generation_identity.py``; the ``.verify()`` methods in
``expression_learning.py``/``output.py``), adapted here to return a
tri-state ``IntegrityFactState`` instead of raising, because
``safe_mode.evaluate_safe_mode`` consumes tri-state facts (CLEAR/FAULT/
UNKNOWN), not exceptions.

Three real, independently-computed facts
-----------------------------------------
Every fact below can independently reach CLEAR, FAULT, or UNKNOWN --
tampering with the input that feeds one fact does not flip the others (see
the accompanying test module for a proof of each).

* ``chemistry`` -- Is the archived ``RecallStoryEpisode`` object passed to
  this call still internally self-consistent right now?  ``RecallStoryEpisode``
  (``recall_story_episode_archive.py``) carries the real pre/post-window
  receiver-state and sensor-state receipts -- the chemistry facts as they
  were when originally sealed -- but, unlike most receipted dataclasses in
  this codebase, it has no ``__post_init__`` self-check; only its own
  explicit ``.verify()`` recomputes and compares.  This fact independently
  recomputes ``recall_story_episode_receipt_payload`` from the episode's
  CURRENT fields and compares the result against the digest/payload the
  episode object still carries, then confirms that digest is still mounted,
  unaltered, in the currently active receipt registry.
* ``field`` -- Does this replay context's sealed closed-experience
  (``context.sealed.closed_experience``, a ``commit.ClosedExperienceSeal``)
  still correspond, byte for byte, to the independently-produced field
  expression and mode-recognition result for this SAME context
  (``context.expression_facts``), and does its own canonical receipt bytes
  still hash to the digest it carries and remain mounted unaltered?
* ``persistence`` -- Does the specific source material for this recall
  (the committed motif event being recalled, its private-staged settlement,
  and its coexperienced output binding) still name, byte for byte, the same
  sensory-evidence receipt set and GLEW profile binding as the archived
  episode being replayed, and is the episode's own top-level receipt still
  mounted unaltered?  This is the check that would catch a caller swapping
  in a different real episode's chemistry state while keeping the same
  source materials.

What this module does NOT do (honest limits)
----------------------------------------------
* It does not invent a check for every conceivable tamper vector; it applies
  the codebase's established recompute-and-compare pattern to the specific
  real data ``mount_integrity`` actually receives (``context``, ``episode``,
  ``source_event``, ``staged_output``, ``source_binding``,
  ``receipt_registry`` -- notably NOT the mounted six-lane runtime itself,
  which the executor never passes to this provider).
* A real, receipted dataclass in this codebase is correct-by-construction
  with respect to its OWN digest (``ReceiptRecord.digest`` is always
  ``sha256(payload)``); the only reachable tamper for such an object is a
  *field substitution* (a real field replaced by a different, otherwise
  valid, value) rather than an arbitrary byte flip, which would simply
  change that field's own digest instead of colliding with the original.
  The tamper tests in the accompanying test module mutate a real field via
  ``dataclasses.replace`` for exactly this reason -- this is not a weaker
  test, it is the only tamper this architecture can actually manifest.
* This module noticed, but does not fix (out of scope for Step 5), that
  ``fresh_recall_executor._verify_staged_source`` compares
  ``staged_output.receipt.binding_receipt_sha256s`` against
  ``(source_binding.binding_receipt_sha256,)`` for a
  ``OutputStatus.STAGED_PRIVATE`` settlement, but the real production
  actuator (``output.RememberedExpressionActuator._process_verified``'s
  ``STAGED_PRIVATE`` branch) never populates ``binding_receipt_sha256s`` for
  that status (it stays the default empty tuple; only the
  ``EXPRESSION_RELEASED``/``EXPRESSION_CLOSE`` branch populates it).  Because
  of this, this module's own ``persistence`` fact deliberately does NOT
  compare ``staged_output.receipt.binding_receipt_sha256s`` against
  ``source_binding`` -- doing so would manufacture a false FAULT on every
  genuine STAGED_PRIVATE recall.  It does still compare
  ``staged_output.receipt.event_receipt_sha256`` against
  ``source_event.event_receipt_sha256``, which the real actuator always sets
  consistently.
"""

from __future__ import annotations

import json

from .commit import closed_experience_seal_receipt_payload
from .fresh_recall_executor import MountedRecallReplayIntegrity
from .model import ReceiptError, ReceiptRecord, ReceiptRegistry, receipt_sha256
from .output import CommittedMotifEvent, MotifOutputBinding, OutputActuation
from .recall_story_episode_archive import (
    RecallStoryEpisode,
    recall_story_episode_receipt_payload,
)
from .safe_mode import (
    IntegrityFact,
    IntegrityFactState,
    MountedSafeModeScope,
    integrity_fact_receipt_payload,
    safe_mode_scope_receipt_payload,
)
from .story_global_uf_basin import PreparedStoryReplayContext


PRODUCTION_RECALL_REPLAY_INTEGRITY_OPERATOR_ID = (
    "glew.recall.production_replay_integrity.v1"
)
_REQUIRED_FACT_IDS: tuple[str, ...] = ("chemistry", "field", "persistence")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _extend_payloads(
    registry: ReceiptRegistry, payloads: tuple[bytes, ...]
) -> ReceiptRegistry:
    """Append-only, digest-collision-safe registry merge (established
    per-module convention; see e.g. ``fresh_recall_executor._extend_payloads``
    and ``story_global_uf_basin._extend_payloads``, duplicated here rather
    than imported so this module has no import-time dependency on a sibling
    module's private helper)."""

    records = list(registry.records)
    mounted = {value.digest: value.payload for value in records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("recall replay integrity generated an empty receipt")
        digest = receipt_sha256(payload)
        prior = mounted.get(digest)
        if prior is not None:
            if prior != payload:
                raise ReceiptError("recall replay integrity receipt digest collision")
            continue
        mounted[digest] = payload
        records.append(ReceiptRecord(digest, payload))
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(records),
    )


def _resolve_or_none(
    registry: ReceiptRegistry, digest: str, field_name: str
) -> bytes | None:
    """Real resolution attempt; ``None`` means the comparison genuinely
    cannot be performed (the digest is not mounted), never a guess."""

    try:
        return registry.resolve(digest, field_name)
    except ReceiptError:
        return None


def _chemistry_fact_state(
    *, episode: RecallStoryEpisode, receipt_registry: ReceiptRegistry
) -> IntegrityFactState:
    recomputed_payload = recall_story_episode_receipt_payload(
        profile_binding_sha256=episode.profile_binding_sha256,
        profile_receipt_sha256s=episode.profile_receipt_sha256s,
        boundary_receipt_sha256=episode.boundary_receipt_sha256,
        boundary_observation_receipt_sha256s=(
            episode.boundary_observation_receipt_sha256s
        ),
        pre_window_state_receipt_sha256=episode.pre_window_state_receipt_sha256,
        pre_window_receiver_state_receipt_sha256s=(
            episode.pre_window_receiver_state_receipt_sha256s
        ),
        post_window_receiver_state_receipt_sha256s=(
            episode.post_window_receiver_state_receipt_sha256s
        ),
        pre_window_sensor_state_receipt_sha256s=(
            episode.pre_window_sensor_state_receipt_sha256s
        ),
        post_window_sensor_state_receipt_sha256s=(
            episode.post_window_sensor_state_receipt_sha256s
        ),
        evidence_preparation_receipt_sha256=(
            episode.evidence_preparation_receipt_sha256
        ),
        sensory_evidence_bindings=episode.sensory_evidence_bindings,
        mounted_receipt_sha256s=tuple(
            value.digest for value in episode.receipt_records
        ),
    )
    if (
        recomputed_payload != episode.episode_receipt_payload
        or receipt_sha256(recomputed_payload) != episode.episode_receipt_sha256
    ):
        return IntegrityFactState.FAULT
    mounted = _resolve_or_none(
        receipt_registry,
        episode.episode_receipt_sha256,
        "chemistry episode receipt",
    )
    if mounted is None:
        return IntegrityFactState.UNKNOWN
    if mounted != recomputed_payload:
        return IntegrityFactState.FAULT
    return IntegrityFactState.CLEAR


def _field_fact_state(
    *, context: PreparedStoryReplayContext, receipt_registry: ReceiptRegistry
) -> IntegrityFactState:
    seal = context.sealed.closed_experience
    facts = context.expression_facts
    if (
        seal.input_expression_receipt_sha256 != facts.expression.receipt_sha256
        or seal.recognition_receipt_sha256 != facts.recognition.receipt_sha256
    ):
        return IntegrityFactState.FAULT
    recomputed_payload = closed_experience_seal_receipt_payload(
        experience_id=seal.experience_id,
        topology_authority_receipt_sha256=seal.topology_authority_receipt_sha256,
        input_expression_receipt_sha256=seal.input_expression_receipt_sha256,
        recognition_receipt_sha256=seal.recognition_receipt_sha256,
        ordered_evidence_receipt_sha256s=seal.ordered_evidence_receipt_sha256s,
        source_time_start=seal.source_time_start,
        source_time_end=seal.source_time_end,
        structural_time_unit=seal.structural_time_unit,
    )
    if receipt_sha256(recomputed_payload) != seal.authority_receipt_sha256:
        return IntegrityFactState.FAULT
    mounted = _resolve_or_none(
        receipt_registry,
        seal.authority_receipt_sha256,
        "field closed-experience seal receipt",
    )
    if mounted is None:
        return IntegrityFactState.UNKNOWN
    if mounted != recomputed_payload:
        return IntegrityFactState.FAULT
    return IntegrityFactState.CLEAR


def _persistence_fact_state(
    *,
    episode: RecallStoryEpisode,
    source_event: CommittedMotifEvent,
    staged_output: OutputActuation,
    source_binding: MotifOutputBinding,
    receipt_registry: ReceiptRegistry,
) -> IntegrityFactState:
    episode_key = tuple(sorted(episode.sensory_evidence_receipt_sha256s))
    binding_key = tuple(sorted(source_binding.sensory_evidence_receipt_sha256s))
    event_key = tuple(sorted(source_event.sensory_evidence_receipt_sha256s))
    if (
        episode.profile_binding_sha256 != source_binding.profile_binding_sha256
        or episode.profile_binding_sha256 != source_event.profile_binding_sha256
        or episode_key != binding_key
        or binding_key != event_key
        or staged_output.receipt.event_receipt_sha256
        != source_event.event_receipt_sha256
    ):
        return IntegrityFactState.FAULT
    mounted = _resolve_or_none(
        receipt_registry,
        episode.episode_receipt_sha256,
        "persistence episode receipt",
    )
    if mounted is None:
        return IntegrityFactState.UNKNOWN
    if mounted != episode.episode_receipt_payload:
        return IntegrityFactState.FAULT
    return IntegrityFactState.CLEAR


class ProductionRecallReplayIntegrityProvider:
    """Real ``RecallReplayIntegrityProvider``: measures, never invents.

    Stateless -- every fact is derived solely from the real objects passed
    to a given ``mount_integrity`` call.  See the module docstring for
    exactly which three facts are computed and from what real source data.
    """

    def mount_integrity(
        self,
        *,
        context: PreparedStoryReplayContext,
        episode: RecallStoryEpisode,
        source_event: CommittedMotifEvent,
        staged_output: OutputActuation,
        source_binding: MotifOutputBinding,
        receipt_registry: ReceiptRegistry,
    ) -> MountedRecallReplayIntegrity:
        if not isinstance(context, PreparedStoryReplayContext):
            raise ReceiptError(
                "recall replay integrity requires a real prepared replay context"
            )
        if not isinstance(episode, RecallStoryEpisode):
            raise ReceiptError(
                "recall replay integrity requires a real archived story episode"
            )
        if not isinstance(source_event, CommittedMotifEvent):
            raise ReceiptError(
                "recall replay integrity requires a real committed motif event"
            )
        if not isinstance(staged_output, OutputActuation):
            raise ReceiptError(
                "recall replay integrity requires a real staged output actuation"
            )
        if not isinstance(source_binding, MotifOutputBinding):
            raise ReceiptError(
                "recall replay integrity requires a real motif output binding"
            )
        if not isinstance(receipt_registry, ReceiptRegistry):
            raise ReceiptError(
                "recall replay integrity requires a mounted receipt registry"
            )

        topology_digest = context.request.topology_authority_receipt_sha256
        experience_digest = context.sealed.closed_experience.authority_receipt_sha256

        chemistry_state = _chemistry_fact_state(
            episode=episode, receipt_registry=receipt_registry
        )
        field_state = _field_fact_state(
            context=context, receipt_registry=receipt_registry
        )
        persistence_state = _persistence_fact_state(
            episode=episode,
            source_event=source_event,
            staged_output=staged_output,
            source_binding=source_binding,
            receipt_registry=receipt_registry,
        )

        new_payloads: list[bytes] = []
        facts: list[IntegrityFact] = []
        for fact_id, state, compared_digest in (
            ("chemistry", chemistry_state, episode.episode_receipt_sha256),
            ("field", field_state, experience_digest),
            ("persistence", persistence_state, episode.episode_receipt_sha256),
        ):
            source_payload = _canonical_bytes(
                {
                    "compared_digest": compared_digest,
                    "episode_receipt_sha256": episode.episode_receipt_sha256,
                    "fact_id": fact_id,
                    "operator": PRODUCTION_RECALL_REPLAY_INTEGRITY_OPERATOR_ID,
                    "request_receipt_sha256": context.request.receipt_sha256,
                    "schema": (
                        "glew.recall.production_replay_integrity_source.v1"
                    ),
                }
            )
            source_digest = receipt_sha256(source_payload)
            fact_payload = integrity_fact_receipt_payload(
                fact_id=fact_id,
                state=state,
                topology_authority_receipt_sha256=topology_digest,
                closed_experience_receipt_sha256=experience_digest,
                source_operator_receipt_sha256=source_digest,
            )
            new_payloads.extend((source_payload, fact_payload))
            facts.append(
                IntegrityFact(
                    fact_id,
                    state,
                    topology_digest,
                    experience_digest,
                    source_digest,
                    receipt_sha256(fact_payload),
                )
            )

        scope_id = (
            f"{context.request.request_id}:production-recall-integrity-scope"
        )
        scope_profile_payload = _canonical_bytes(
            {
                "episode_receipt_sha256": episode.episode_receipt_sha256,
                "fact_ids": list(_REQUIRED_FACT_IDS),
                "operator": PRODUCTION_RECALL_REPLAY_INTEGRITY_OPERATOR_ID,
                "request_receipt_sha256": context.request.receipt_sha256,
                "schema": "glew.recall.production_replay_integrity_scope.v1",
            }
        )
        scope_profile_digest = receipt_sha256(scope_profile_payload)
        scope_payload = safe_mode_scope_receipt_payload(
            scope_id=scope_id,
            topology_authority_receipt_sha256=topology_digest,
            required_fact_ids=_REQUIRED_FACT_IDS,
            source_profile_receipt_sha256=scope_profile_digest,
        )
        scope = MountedSafeModeScope(
            scope_id,
            topology_digest,
            _REQUIRED_FACT_IDS,
            scope_profile_digest,
            receipt_sha256(scope_payload),
        )
        new_payloads.extend((scope_profile_payload, scope_payload))

        registry = _extend_payloads(receipt_registry, tuple(new_payloads))

        states = (chemistry_state, field_state, persistence_state)
        disruption_clear: bool | None
        if IntegrityFactState.FAULT in states:
            disruption_clear = False
        elif IntegrityFactState.UNKNOWN in states:
            disruption_clear = None
        else:
            disruption_clear = True

        return MountedRecallReplayIntegrity(
            request_receipt_sha256=context.request.receipt_sha256,
            safe_mode_scope=scope,
            safe_mode_facts=tuple(
                sorted(facts, key=lambda value: value.fact_id)
            ),
            disruption_clear=disruption_clear,
            receipt_registry=registry,
        )


__all__ = (
    "PRODUCTION_RECALL_REPLAY_INTEGRITY_OPERATOR_ID",
    "ProductionRecallReplayIntegrityProvider",
)
