"""Concrete production ``CleanConversationEngine`` (Step 6).

Answers ``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
section 9.7 / section 12 Step 6: *"Implement one concrete
``CleanConversationEngine`` that: owns the mounted runtime and clean learned
state; verifies the incoming turn receipt; obtains the six-lane experience
from the live boundary owner; constructs all commit providers; resolves the
unique initial remembered motif; constructs fresh recall; calls
``run_clean_conversation_transaction``; atomically persists all newly learned
state and receipts; returns only ``ConversationTransactionResult``. The
engine must not fabricate a response when any authority is absent."*

This module wires already-real, already-committed Step 1-5 machinery into one
concrete engine; it introduces no new field physics, no new commit rule, and
no new recognition rule.

What this engine actually does, per call to :meth:`run_clean_conversation`
--------------------------------------------------------------------------
1. Builds one real six-lane input expression for this turn from the given
   ``story_chemistry`` runtime plus the turn's own single Unicode-scalar
   utterance, following ``real_experience_learning_pipeline.py``'s own
   ``_evolve_real_causal_window`` / ``_build_typed_language_lane`` /
   ``_build_expression`` pattern (Step 4, already committed) -- this module
   imports those private helpers directly rather than re-deriving them, so
   this engine's sensory/expression construction is bit-for-bit the same
   proven code path, not a re-implementation that could silently diverge.
2. Evaluates real expression-mode recognition
   (``expression_modes.evaluate_expression_mode_boundary``) against this
   engine's own in-memory mode bank, and folds the real growth this call
   produces back into that bank for the next call -- mode-bank growth is a
   real, load-bearing side effect of recognition itself (see
   ``expression_modes.py``), not something this engine invents.
3. If nothing has ever been learned yet (``learned_state.initial_event is
   None``), returns typed silence immediately after recognition, without
   ever attempting to build ``RememberedOutputProviders`` -- see "Handling a
   missing initial_event" below for why that check must happen before, not
   inside, the real transaction.
4. Otherwise, extracts the same eight real commit authorities
   ``real_experience_learning_pipeline._commit_real_scene`` already builds
   (SafeMode, event support, experience origin, Fixed-42 L6 scope, the
   asserted Global-UF validation, and the sealed evidence/applicability
   itself) into a ``ConversationCommitProviders`` value -- WITHOUT gating on
   its own separate evaluation of ``evaluate_commit_boundary`` (this engine
   never pre-decides bootstrap/no-commit/commit itself; only
   ``run_clean_conversation_transaction`` decides that, from these same
   extracted authorities).
5. Evaluates ``commit.evaluate_commit_boundary`` exactly once, over these
   same eight authorities plus this turn's own real recognition, and mounts
   its receipt. This one call is structurally required, not optional or
   redundant: ``run_clean_conversation_transaction`` recomputes the identical
   commit decision internally and, before even looking at its status,
   requires that decision's own receipt payload to already resolve in the
   registry (``conversation.py``'s own ``_mounted_exact`` check, immediately
   after its internal ``evaluate_commit_boundary`` call) -- nothing in this
   codebase mounts that payload as a side effect of computing it. This was
   verified directly against the real code, not assumed: calling the
   transaction without first mounting this receipt fails closed with
   "conversation full-field commit receipt is not mounted in the active
   receipt registry" every time, for every real commit. So this one call
   both satisfies that real structural requirement and produces the typed
   ``CommitDecision`` value the later learning step needs -- the same
   decision is reused for both purposes, never evaluated a second time.
6. Assembles ``RememberedOutputProviders`` from the engine's own learned
   state plus the injected ``fresh_recall_provider`` (see "The fresh-recall
   gap" below), and calls the real, unmodified
   ``conversation.run_clean_conversation_transaction``, which independently
   recomputes recognition and commit over the identical inputs and confirms
   they match what this engine already mounted.
7. Only when that call's own public result already proves a real full-field
   commit happened (``result.initial_event_receipt_sha256 is not None`` --
   this field is populated by ``conversation.py`` only after
   ``commit.status is CommitStatus.COMMIT``, so it is a public, honest,
   already-exposed signal that a real commit occurred) does this engine learn
   a new binding, from the same ``CommitDecision`` computed in step 5, and
   persist a new checkpoint atomically.

Handling a missing initial_event
---------------------------------
``RememberedOutputProviders.__post_init__`` (``conversation.py`` lines
111-136) unconditionally raises ``ReceiptError`` when ``initial_event`` is
not a ``CommittedMotifEvent`` instance. That raise happens at construction
time, in this engine's own code, before ``run_clean_conversation_transaction``
is ever called -- it is not caught by that function's own internal
``try/except ReceiptError`` (``conversation.py`` lines 430-589), because by
the time a ``RememberedOutputProviders`` value exists at all, it is already
guaranteed non-``None`` by that dataclass's own invariant. So
``run_clean_conversation_transaction`` itself has no "if initial_event is
None" branch to fall back on -- there is structurally no way to call it at
all without an already-learned initial event. This engine therefore checks
``self._learned_state.initial_event is None`` explicitly, before attempting
to build ``RememberedOutputProviders``, and returns typed silence directly in
that case via ``conversation._make_result`` -- the same private canonical
result constructor ``run_clean_conversation_transaction`` itself uses for
every other silence outcome, imported directly (not re-implemented) so this
silence path stays byte-for-byte consistent with every other typed-silence
receipt this substrate produces, rather than duplicating (and risking
drifting from) that schema.

Fresh recall of freshly-learned content (design GL-SPC-RECALL-BASIN-RECONCILIATION)
------------------------------------------------------------------------------------
The five-sense ``FullFieldFreshRecallProvider`` /
``FreshRecallClosedExperienceExecutor`` / ``RecallStoryEpisodeArchive`` stack
(Step 5) can never resolve, or even recognize, a scalar this engine actually
learns: a five-sense episode's per-port sensory receipts can never equal the
*six-lane* receipts a real learned binding carries (design section 3), and the
frozen basin's empty genesis mode bank returns UNKNOWN for a real grown scene
(section 3.4). ``docs/GL-SPC-RECALL-BASIN-RECONCILIATION-DESIGN-20260714-v1.md``
resolves this by recalling a learned scene through the engine's OWN
deterministic six-lane turn construction, natively in the six-lane universe
the engine commits and learns in.

This engine wires that resolution with three small, named couplings, all
additive and none touching recognition / commit / learning / the transaction:
``coexperienced_scene_archive`` (a six-lane-native scene archive, replacing the
unused five-sense episode archive), a shared ``live_recall_state`` holder the
engine republishes each turn (so the injected provider recognizes against this
engine's live grown bank and sees prior-turn episodes), and archive-on-learn in
:meth:`_learn_and_persist`. This engine still never constructs its own
``fresh_recall_provider``: it remains a required constructor parameter. The
bootstrap (``production_runtime_bootstrap.py``) constructs the real
``CoexperiencedSceneRecallProvider`` against the same shared holder; a caller
may inject any genuinely real (never monkeypatched, never a bare stub returning
success) ``FreshRecallSelfSenseProvider``, and any turn whose scene has no
matching archived episode -- or whose learned expression has not been closed --
honestly resolves to typed silence.

Constructor coupling this engine cannot avoid
------------------------------------------------
Building one turn's typed-language lane requires the exact
``phase_calibration_id``/``phase_kappa``/causal-grid timestamps already baked
into the caller's ``MountedSixLaneRuntime`` (its ``typed_language_kernel_
binding`` only records receipt digests, not the underlying ``Fraction``
value). This mirrors exactly the same coupling
``recall_story_runtime_resolver.mount_recall_language_interface_genesis``
already requires and documents for the same reason -- this engine's
constructor requires the same two extra values rather than inventing a way
around a real, already-established precedent in this codebase.

One real language scalar per turn
------------------------------------
``real_experience_learning_pipeline._build_typed_language_lane`` already
requires ``len(text) == 1`` (one real typed-language lane requires one
Unicode scalar). This engine inherits that same real, structural limitation
rather than inventing a multi-scalar turn scheduler (section 9.3's "typed-
language turn scheduler" is a separate, larger, not-yet-built authority) --
a turn whose text is not exactly one Unicode scalar is rejected with a
``ReceiptError`` that propagates out of ``run_clean_conversation`` as a task
transport error (``conversation_service.py``'s own task executor already
turns any raised exception into ``ConversationTaskStatus.ERROR``), not
silently truncated and not converted into fabricated typed silence -- a
malformed turn is a caller/transport defect, not a case of honest cognitive
uncertainty.

Sensory honesty for this integration layer
----------------------------------------------
No live external camera/microphone feed is wired into this conversation
engine (this is a real, acknowledged gap, not a claim of full section 9.1
compliance). Rather than fabricate "the caller cares" plausible-looking
sight/sound content from the turn's own text -- forbidden outright by
section 6 -- this engine derives its five real per-instant sensory
descriptors deterministically from the turn's own opaque ``task_id`` (a
structural transport identifier, never the turn's semantic content) using
the same real emulator functions Step 4 already proved
(``real_experience_learning_pipeline._real_visual_fragment_receipt`` /
``_real_auditory_fragment_receipt``), never from a hash of the spoken words.
Touch/smell/taste descriptors are drawn, in fixed rotation, from the same
"legitimate somatic vocabulary" Step 4's own descriptors already use.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from fractions import Fraction
from .closed_experience import SealedClosedExperience
from .commit import (
    AuthorityDisposition,
    BinaryAuthorityKind,
    BinaryCommitAuthority,
    CommitDecision,
    CommitStatus,
    L6ScopeAuthority,
    binary_authority_receipt_payload,
    evaluate_commit_boundary,
    l6_evaluation_receipt_payload,
    l6_scope_authority_receipt_payload,
)
from .conversation import (
    ConversationCommitProviders,
    ConversationStatus,
    ConversationTransactionResult,
    RememberedOutputProviders,
    _make_result,
    run_clean_conversation_transaction,
)
from .conversation_service import CleanConversationTurn
from .event_support import EventSupportEvaluationStatus, MemoryEnergyAuthority, evaluate_event_support, memory_energy_authority_receipt_payload
from .expression_learning import (
    CoexperiencedOutput,
    CommittedCoexperience,
    LearnedBindingState,
    _sensory_receipts,
    create_coexperienced_no_output,
    learn_committed_binding_transaction,
    learned_binding_checkpoint_payload,
)
from .expression_modes import (
    RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
    ExpressionModeBank,
    ExpressionModeBoundaryResult,
    evaluate_expression_mode_boundary,
)
from .experience_origin import ExperienceOriginAuthority, ExperienceOriginKind, experience_origin_authority_receipt_payload
from .field import MountedFieldTopology
from .l6 import L6Evaluation
from .language import encode_balanced_ternary_scalar
from .model import ReceiptError, ReceiptRecord, ReceiptRegistry, receipt_sha256
from .real_experience_learning_pipeline import (
    InstantDescriptor,
    _build_expression,
    _build_typed_language_lane,
    _evolve_real_causal_window,
    _mount_causal_grid,
    _physical_l6_evaluation,
    _seal,
)
from .recall_reentry import FreshRecallSelfSenseProvider
from .coexperienced_scene_archive import (
    CoexperiencedSceneArchive,
    coexperienced_scene_archive_checkpoint_payload,
    create_coexperienced_scene_episode,
)
from .coexperienced_scene_recall_executor import LiveRecallState
from .generation_identity import bind_generation_identity
from .safe_mode import IntegrityFact, IntegrityFactState, MountedSafeModeScope, evaluate_safe_mode, integrity_fact_receipt_payload, safe_mode_scope_receipt_payload
from .six_lane_runtime_mount import MountedSixLaneRuntime
from .story_chemistry import StoryChemistryRuntime

from dsf_ai_service.substrate.immutable_generation_store import ImmutableGenerationStore


LEARNING_CHECKPOINT_RELATIVE_PATH = "clean_conversation_learning_checkpoint.json"
ARCHIVE_CHECKPOINT_RELATIVE_PATH = "coexperienced_scene_archive_checkpoint.json"
GENERATION_IDENTITY_BINDING_RELATIVE_PATH = "clean_conversation_generation_identity_binding.json"
CHECKPOINT_RELATIVE_PATHS = (
    LEARNING_CHECKPOINT_RELATIVE_PATH,
    ARCHIVE_CHECKPOINT_RELATIVE_PATH,
    GENERATION_IDENTITY_BINDING_RELATIVE_PATH,
)

_SCENE_INSTANT_COUNT = 5
"""Historical default retained only for callers that still want a fixed
five-instant scene (e.g. bootstrap genesis scenes using 'a'/'b', which both
happen to need exactly five valid trit places). Real per-turn scene
construction must NOT assume this -- see ``_scene_descriptors``'s ``count``
parameter and ``real_experience_learning_pipeline._evolve_real_causal_window``'s
own docstring: N is driven by how many valid balanced-ternary trit places
the scene's own typed-language scalar actually requires, which is NOT always
five (confirmed directly: space needs four, many letters need six). A prior
version of this module hardcoded five unconditionally, which every existing
test happened never to catch because every fixture only ever used 'a'/'b' --
both of which need exactly five. This was found live, from a real multi-word
sentence containing a space failing with "native stream does not match
common causal grid"."""

_SOMATIC_ROTATION: tuple[tuple[str | None, str | None, str | None], ...] = (
    ("warm", None, None),
    (None, "floral", None),
    ("cool", None, None),
    (None, None, "savory"),
    ("dry", None, None),
)

# The fixed, canonical sight/sound reading that stands in for "no real
# camera/mic attached this turn" -- see ``_scene_descriptors``. These are the
# exact values the prior per-``task_id`` SHA-256 seed produced when its seed
# byte was zero (``fill_value = 0.15 + (0/255)*0.7 == 0.15``; ``visual_seed =
# 10_000 + index*257 + 0``; ``born_tick = index*100 + 0``), so the descriptor
# formulas, the ``InstantDescriptor`` shape, and every downstream frame are
# byte-identical in structure -- only the cross-request random variation is
# removed. Named and greppable so the "this is the reproducible placeholder for
# absent real capture, NOT a sensed value" intent is legible: the request UUID
# has no physical authority over sensory content (design
# ``GL-SPC-REPRODUCIBLE-EXPERIENCE-IDENTITY-DESIGN-20260714-v3`` sections 2, 4.3).
_CANONICAL_ABSENT_FILL_VALUE = 0.15
_CANONICAL_ABSENT_VISUAL_SEED_BASE = 10_000

# The exact, single message ``expression_learning.
# learn_committed_binding_transaction`` raises (that module, the "prior
# committed mode already has a learned successor" guard) when a real,
# already-committed turn cannot ALSO learn a new successor because the mode it
# committed against already holds its one permitted learned successor. This is
# a real, intentional one-successor-per-mode invariant -- ``LearnedBindingState.
# verify`` treats "learned mode has more than one successor" as a first-class
# state invariant too. This module never re-implements that invariant; it only
# recognizes this exact fault (see ``_learn_and_persist``) so it can degrade it
# to honest typed silence instead of letting a raw internal fault surface as
# spoken output. Kept as a named constant, mirrored by a test that asserts it
# still equals the message the committed code actually raises, so a future
# reword of that message fails a test loudly (re-surfacing the raw error, the
# safe direction) rather than silently un-catching in production.
_LEARN_SUCCESSOR_ALREADY_EXISTS_MESSAGE = (
    "prior committed mode already learned this exact transition context"
)
# Raised by ``CoexperiencedSceneArchive.with_episode`` when the same scene
# (same six-lane sensory receipt set) is archived under a different episode --
# the "same scene, two successors" boundary of owner Requirement 2.
_SCENE_ALREADY_ARCHIVED_MESSAGE = (
    "this exact binding receipt set is already archived"
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _extend_registry(registry: ReceiptRegistry, *payloads: bytes) -> ReceiptRegistry:
    """Digest-collision-safe append, mirroring every sibling module's own
    private helper of the same shape (duplicated here rather than imported so
    this file has no import-time dependency on a module under concurrent
    edit)."""

    records = list(registry.records)
    values = {item.digest: item.payload for item in records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        existing = values.get(digest)
        if existing is not None:
            if existing != payload:
                raise ReceiptError("clean conversation engine receipt digest collision")
            continue
        values[digest] = payload
        records.append(ReceiptRecord(digest, payload))
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(records),
    )


def _merge_registry(registry: ReceiptRegistry, addition: ReceiptRegistry) -> ReceiptRegistry:
    """Union ``addition``'s records into ``registry``, keeping ``registry``'s
    own root.

    ``mount_six_lane_runtime`` re-roots its own returned registry at its
    story-native-replay-profile's own payload (see
    ``six_lane_runtime_mount._reroot_registry``'s own docstring for exactly
    why), while ``story_chemistry.mount_story_chemistry`` (and therefore
    every per-turn chemistry-evolution registry
    ``real_experience_learning_pipeline._evolve_real_causal_window`` builds)
    roots its own registry at the chemistry manifest's own payload instead.
    No single ratified GLEW profile digest unifies these choices anywhere in
    this repository today -- this is an honest, pre-existing inconsistency
    between two already-committed modules, not something this engine
    invented. Exactly mirroring the same ``_reroot_registry`` precedent,
    this function keeps one chosen root (``registry``'s) and unions in the
    other source's records under it, rather than requiring their two
    independently-chosen roots to already agree.
    """

    return _extend_registry(registry, *(value.payload for value in addition.records))


def _scene_descriptors(
    *, count: int = _SCENE_INSTANT_COUNT
) -> tuple[InstantDescriptor, ...]:
    """``count`` real, deterministic instant descriptors representing the
    fixed, reproducible "no real camera/mic attached this turn" sensory
    reading.

    ``count`` MUST equal how many valid balanced-ternary trit places the
    scene's own typed-language scalar requires (see
    ``_evolve_real_causal_window``'s own docstring) -- the sensory lanes
    built from these descriptors must share one common causal grid with the
    language lane, and the language lane only ever produces one real sample
    per valid trit place. Every caller MUST compute this from the real
    scalar being processed (``sum(1 for trit in encode_balanced_ternary_scalar(
    ord(text)) if trit.valid)``); the parameter has no safe default because a
    fixed guess silently produces a shorter or longer sensory stream than the
    real language stream, which fails closed downstream (a real, caught
    integrity check -- confirmed live for a space character, which needs
    four places, against a caller that had hardcoded five) rather than
    silently fabricating anything.

    Derived from the instant POSITION only -- never from the turn's transport
    id (the request UUID is deliberately removed from this function's
    signature so it CANNOT have physical authority over sensory content:
    design ``GL-SPC-REPRODUCIBLE-EXPERIENCE-IDENTITY-DESIGN-20260714-v3``
    sections 2, 3.3, 4) and never from the turn's text content (the standing
    prohibition -- no sensory value is ever derived from the spoken/typed
    meaning). The same canonical scene is therefore produced for every turn of
    a given length, so recognition (which operates on the numeric field, not
    on any id) can see a recurring language pattern across distinct moments;
    distinct MOMENTS are still distinguished, correctly, by their receipt
    identity (the id-bearing ``scene_id``/``event_id``/``identity`` naming the
    callers keep), not by manufactured sensory noise. Sight/sound take the
    fixed ``_CANONICAL_ABSENT_*`` reading (byte-identical in structure to the
    old per-id formulas with a zero seed byte, so intra-scene variation across
    ``index`` is preserved and only the cross-request randomness is removed);
    touch/smell/taste rotate through the same fixed "legitimate somatic
    vocabulary" tuples -- already position-indexed and thus never part of the
    request-id defect.
    """

    if not isinstance(count, int) or count < 2:
        raise ReceiptError(
            "scene descriptor count must be a real integer of at least two "
            "(a causal window candidate requires at least two real instants)"
        )

    descriptors = []
    for index in range(count):
        fill_value = _CANONICAL_ABSENT_FILL_VALUE
        visual_seed = _CANONICAL_ABSENT_VISUAL_SEED_BASE + (index * 257)
        born_tick = index * 100
        touch, smell, taste = _SOMATIC_ROTATION[index % len(_SOMATIC_ROTATION)]
        descriptors.append(
            InstantDescriptor(fill_value, visual_seed, born_tick, touch, smell, taste)
        )
    return tuple(descriptors)


def _build_commit_providers(
    *,
    identity: str,
    sealed: SealedClosedExperience,
    topology: MountedFieldTopology,
    l6_evaluation: L6Evaluation,
    registry: ReceiptRegistry,
) -> tuple[ConversationCommitProviders, ReceiptRegistry]:
    """Extract the same eight real commit authorities
    ``real_experience_learning_pipeline._commit_real_scene`` builds --
    WITHOUT calling ``evaluate_commit_boundary`` (see module docstring).

    Every authority below is the identical real construction
    ``_commit_real_scene`` already proves; this function differs from it only
    by returning a ``ConversationCommitProviders`` value instead of calling
    ``evaluate_commit_boundary`` and inspecting a ``CommitStatus``.
    """

    experience_digest = sealed.closed_experience.authority_receipt_sha256
    topology_digest = topology.authority_receipt_sha256

    safe_profile = _canonical_bytes(
        {
            "identity": identity,
            "schema": "glew.clean_conversation_engine.integrity_profile.v1",
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
    fact_payloads: list[bytes] = []
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
    registry = _extend_registry(registry, safe_profile, safe_scope_payload, *fact_payloads)
    safe = evaluate_safe_mode(
        authority_id=f"{identity}:safe",
        topology_authority_receipt_sha256=topology_digest,
        closed_experience_receipt_sha256=experience_digest,
        scope=safe_scope,
        facts=tuple(facts),
        receipt_registry=registry,
    )
    registry = _extend_registry(registry, *safe.generated_receipt_payloads)
    # Unlike _commit_real_scene, we do not raise on a non-PASS disposition:
    # that determination belongs solely to evaluate_commit_boundary inside
    # run_clean_conversation_transaction. Extraction must not pre-empt it.

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
    registry = _extend_registry(registry, origin_source, origin_payload)

    energy_derivation = f"{identity}:memory-energy-derivation".encode()
    physical_profile = sealed.expression.steps[0].authority.physical_profile_receipt_sha256
    energy_payload = memory_energy_authority_receipt_payload(
        authority_id=f"{identity}:memory-energy",
        energy_unit_id="clean-conversation-engine-energy-unit",
        exact_memory_energy=Fraction(1),
        derivation_receipt_sha256=receipt_sha256(energy_derivation),
        physical_profile_receipt_sha256=physical_profile,
    )
    energy = MemoryEnergyAuthority(
        f"{identity}:memory-energy",
        "clean-conversation-engine-energy-unit",
        Fraction(1),
        receipt_sha256(energy_derivation),
        physical_profile,
        receipt_sha256(energy_payload),
    )
    registry = _extend_registry(registry, energy_derivation, energy_payload)
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
    registry = _extend_registry(registry, *event.generated_receipt_payloads)

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

    # Global-UF: asserted, not computed -- mirrors _commit_real_scene's own
    # honestly-documented limitation (no production GlobalUFReplayProvider
    # exists anywhere in this repository yet; see that module's docstring).
    global_source = _canonical_bytes(
        {
            "identity": identity,
            "scope": "clean_conversation_engine_asserted_global_uf_authority",
            "schema": "glew.clean_conversation_engine.global_uf_source.v1",
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
    registry = _extend_registry(registry, l6_payload, l6_scope_payload, global_source, global_payload)

    providers = ConversationCommitProviders(
        l6_evaluation=l6_evaluation,
        l6_scope=l6_scope,
        closed_experience=sealed.closed_experience,
        safe_mode=safe.authority,
        event_support=event.authority,
        evidence=sealed.evidence,
        l5_applicability=sealed.l5_applicability,
        global_uf_validation=global_uf,
    )
    return providers, registry


@dataclass(frozen=True, slots=True)
class GenerationIdentityParameters:
    """The genesis identity triple this engine binds every persisted
    checkpoint to (see ``generation_identity.py``). ``tick`` is genesis's own
    birth-certificate revision counter, contractually always ``0``
    (``genesis.py``'s own documented contract) -- a different concept from
    this engine's own checkpoint-revision tick, tracked separately below.
    """

    genesis_identity: str
    genesis_generation_uuid: str
    genesis_tick: int = 0


class ProductionCleanConversationEngine:
    """Concrete, constructed-once ``CleanConversationEngine``.

    Per :meth:`run_clean_conversation` call, ``turn``/``story_chemistry`` are
    the only per-call inputs (matching the ``CleanConversationEngine``
    Protocol exactly); every other authority is owned by this instance,
    constructed once.
    """

    def __init__(
        self,
        *,
        mounted_runtime: MountedSixLaneRuntime,
        learned_state: LearnedBindingState,
        receipt_registry: ReceiptRegistry,
        fresh_recall_provider: FreshRecallSelfSenseProvider,
        typed_language_phase_calibration_id: str,
        typed_language_phase_kappa: Fraction,
        generation_identity: GenerationIdentityParameters,
        generation_store: ImmutableGenerationStore,
        checkpoint_authentication_key: bytes,
        checkpoint_key_id: str,
        coexperienced_scene_archive: CoexperiencedSceneArchive | None = None,
        live_recall_state: LiveRecallState | None = None,
        engine_id: str = "clean-conversation-engine",
    ) -> None:
        if not isinstance(mounted_runtime, MountedSixLaneRuntime):
            raise ReceiptError("clean conversation engine requires a mounted six-lane runtime")
        if not isinstance(learned_state, LearnedBindingState):
            raise ReceiptError("clean conversation engine requires a real learned-binding state")
        if fresh_recall_provider is None:
            raise ReceiptError(
                "clean conversation engine requires an injected fresh-recall provider "
                "(see module docstring: constructing one here is out of this engine's "
                "scope -- a concurrent, separate effort owns that gap)"
            )
        if not isinstance(generation_store, ImmutableGenerationStore):
            raise ReceiptError("clean conversation engine requires a real generation store")
        if set(generation_store.required_files) != set(CHECKPOINT_RELATIVE_PATHS):
            raise ReceiptError(
                "generation store is not configured for this engine's exact three "
                "checkpoint files"
            )
        if not isinstance(checkpoint_authentication_key, bytes) or not checkpoint_authentication_key:
            raise ReceiptError("clean conversation engine requires a checkpoint authentication key")

        learned_state.verify()
        mounted_runtime.field_topology.verify(mounted_runtime.receipt_registry)

        self._engine_id = engine_id
        self._mounted_runtime = mounted_runtime
        self._topology = mounted_runtime.field_topology
        self._mode_bank: ExpressionModeBank = mounted_runtime.expression_mode_bank
        self._learned_state = learned_state
        self._fresh_recall_provider = fresh_recall_provider
        self._typed_language_phase_calibration_id = typed_language_phase_calibration_id
        self._typed_language_phase_kappa = typed_language_phase_kappa
        self._generation_identity = generation_identity
        self._generation_store = generation_store
        self._checkpoint_authentication_key = checkpoint_authentication_key
        self._checkpoint_key_id = checkpoint_key_id
        self._scene_archive = (
            CoexperiencedSceneArchive()
            if coexperienced_scene_archive is None
            else coexperienced_scene_archive
        )
        # One shared mutable holder the engine updates each turn and the
        # injected recall provider reads at settle time (design section 5 /
        # 6.2). A real caller (the bootstrap) supplies the SAME holder the
        # provider was constructed against, so recall recognizes against this
        # engine's live grown bank and sees prior-turn scene episodes. When no
        # holder is injected (e.g. a caller wiring a recall provider that does
        # not consult it), the engine owns a private one so its own bank /
        # archive / motif-kind growth stays consistent.
        if live_recall_state is None:
            live_recall_state = LiveRecallState(
                mode_bank=self._mode_bank,
                scene_archive=self._scene_archive,
                motif_kinds=self._learned_state.motif_kinds,
            )
        self._live_recall_state = live_recall_state
        self._checkpoint_tick = 0
        # Deferred-persistence bookkeeping (utterance-transaction Milestone 1)
        # is kept in TWO deliberately separate pieces of state, because the
        # engine has to answer two genuinely different questions honestly:
        #
        # 1. ``_deferred_checkpoint_tick`` -- the FLUSH TARGET. ``None`` means
        #    there is no batched, not-yet-attempted commit outstanding; an
        #    ``int`` is the checkpoint tick a real multi-scalar turn
        #    (``defer_persistence=True``) consumed for a learned-state change
        #    whose store commit it BATCHED and never attempted yet. Only the
        #    defer path sets this. It is what the turn's single end-of-turn
        #    flush (and the abort-flush) commits, so those never re-attempt an
        #    immediate commit that already failed.
        #
        # 2. ``_unpersisted_learned_change`` -- the HONESTY flag's backing.
        #    ``True`` iff this engine's in-memory learned state is ahead of the
        #    last generation a store commit actually SUCCEEDED in publishing.
        #    Set ``True`` before ANY store write is attempted (deferred or
        #    immediate) and cleared ONLY after a commit genuinely succeeds, so
        #    :attr:`has_unpersisted_learned_state` stays truthful in every
        #    failure path -- including an immediate commit that raises
        #    mid-write, where there is no deferred tick at all.
        self._deferred_checkpoint_tick: int | None = None
        self._unpersisted_learned_change: bool = False
        self._lock = threading.Lock()
        # Turn-level mutex (Fix 1). ``self._lock`` above serializes individual
        # SCALARS; this one serializes whole TURNS. See :meth:`serialize_turn`.
        self._turn_lock = threading.Lock()

        registry = _merge_registry(receipt_registry, mounted_runtime.receipt_registry)
        registry = _merge_registry(registry, learned_state.receipt_registry)

        physical_profile_payload = _canonical_bytes(
            {
                "identity": f"{engine_id}-shared-field-profile",
                "schema": "glew.clean_conversation_engine.exact_field_profile.v1",
            }
        )
        registry = _extend_registry(registry, physical_profile_payload)
        self._physical_profile_receipt_sha256 = receipt_sha256(physical_profile_payload)

        # L6 concerns lane structure, not scene content (see
        # real_experience_learning_pipeline.py's own docstring); computed once
        # and reused for every turn, exactly mirroring that module's pattern.
        l6_evaluation, registry = _physical_l6_evaluation(
            topology=self._topology,
            pre_window=mounted_runtime.pre_window_state,
            registry=registry,
        )
        self._l6_evaluation = l6_evaluation
        self._registry = registry

    # -- per-turn scene construction -------------------------------------

    def _build_turn_expression(
        self,
        *,
        turn: CleanConversationTurn,
        story_chemistry: StoryChemistryRuntime,
    ):
        if not isinstance(story_chemistry, StoryChemistryRuntime):
            raise ReceiptError("clean conversation turn requires a mounted story chemistry runtime")
        if story_chemistry.manifest.receipt_sha256 != (
            self._mounted_runtime.story_chemistry_runtime.manifest.receipt_sha256
        ):
            raise ReceiptError(
                "the supplied story chemistry runtime belongs to a different "
                "manifest than this engine's mounted six-lane runtime"
            )
        if len(turn.text) != 1:
            raise ReceiptError(
                "this engine's typed-language lane requires exactly one Unicode "
                "scalar per turn (see module docstring); a multi-scalar turn "
                "scheduler is a separate, not-yet-built authority (section 9.3)"
            )
        trits = encode_balanced_ternary_scalar(ord(turn.text))
        valid_count = sum(1 for trit in trits if trit.valid)
        if valid_count > len(self._mounted_runtime.causal_grid.timestamps):
            raise ReceiptError(
                "this turn's Unicode scalar needs more valid balanced-ternary "
                "trit places than this engine's mounted causal grid carries "
                "timestamps for"
            )

        registry = self._registry
        # NB: ``turn.task_id`` is deliberately NOT passed here -- the request
        # UUID has no physical authority over sensory content (design v3). It
        # legitimately remains the scene's receipt-identity naming below
        # (``scene_id``/``event_id``/``source_epoch``/``identity``), which is
        # bookkeeping, not physical percept.
        descriptors = _scene_descriptors(count=valid_count)
        bridge = _evolve_real_causal_window(
            story_chemistry,
            scene_id=turn.task_id,
            descriptors=descriptors,
        )
        registry = _merge_registry(registry, bridge.receipt_registry)

        # This turn's own real streams (sensory, from the `valid_count`
        # descriptors above; language, filtered to `valid_count` valid trit
        # timestamps by _build_typed_language_lane below) carry exactly
        # `valid_count` samples -- never the engine's fixed mounted
        # causal_grid's own timestamp count (which is a per-generation
        # maximum, not every turn's real length; see `_scene_descriptors`'s
        # own docstring). `prepare_closed_experience_evidence` requires every
        # stream's real timestamps to equal this grid's exactly, so the grid
        # passed to it here must be minted to this turn's own real length,
        # not the runtime's fixed one -- found live: a mismatch here is what
        # raised "native stream does not match common causal grid" for any
        # scalar (e.g. a space) needing fewer places than the runtime's max.
        scene_grid, registry = _mount_causal_grid(
            grid_id=f"{turn.task_id}-scene-causal-grid",
            timestamps=tuple(Fraction(index) for index in range(1, valid_count + 1)),
            registry=registry,
        )

        language_input, registry = _build_typed_language_lane(
            binding=self._mounted_runtime.typed_language_kernel_binding,
            phase_id=self._typed_language_phase_calibration_id,
            phase_kappa=self._typed_language_phase_kappa,
            text=turn.text,
            event_id=f"{turn.task_id}-language",
            source_epoch=f"{turn.task_id}-language-epoch",
            timestamps=self._mounted_runtime.causal_grid.timestamps,
            registry=registry,
        )

        preparation = self._prepare_evidence(
            language_input=language_input,
            bridge=bridge,
            grid=scene_grid,
            registry=registry,
        )
        registry = preparation.receipt_registry

        expression, registry = _build_expression(
            topology=self._topology,
            preparation=preparation,
            precision=self._mounted_runtime.precision_authority,
            physical_profile_receipt_sha256=self._physical_profile_receipt_sha256,
            identity=turn.task_id,
            registry=registry,
        )
        return expression, language_input, preparation, registry

    def _prepare_evidence(self, *, language_input, bridge, grid, registry: ReceiptRegistry):
        from .closed_experience import ClosedExperienceProviderUnknown, prepare_closed_experience_evidence

        preparation = prepare_closed_experience_evidence(
            streams=(language_input.stream, *bridge.streams),
            kernel_inputs=(language_input.kernel_input, *bridge.kernel_inputs),
            source_time_start=Fraction(0),
            grid=grid,
            support_domain=self._mounted_runtime.support_domain,
            resonance_graph=self._mounted_runtime.resonance_graph,
            resonance_operator=self._mounted_runtime.resonance_operator,
            topology=self._topology,
            receipt_registry=registry,
        )
        if isinstance(preparation, ClosedExperienceProviderUnknown):
            raise ReceiptError(
                f"real turn evidence preparation failed: {preparation.reason}"
            )
        return preparation

    # -- public Protocol surface ------------------------------------------

    def run_clean_conversation(
        self,
        *,
        turn: CleanConversationTurn,
        story_chemistry: StoryChemistryRuntime,
        is_final_scalar: bool = False,
        defer_persistence: bool = False,
    ) -> ConversationTransactionResult:
        """Return only the typed result of ``run_clean_conversation_transaction``.

        ``is_final_scalar`` is the one real, non-fabricated close signal (see
        :meth:`_learn_and_persist`): the ``MultiScalarTurnScheduler`` already
        knows, structurally, which scalar (by ``index == len(text) - 1``) is the
        last real Unicode scalar of the real per-request message a real person
        actually sent this request, and threads that fact here. It defaults to
        ``False`` so every lower-level or single-turn caller (and every existing
        test) keeps the historical accumulate-only behaviour unchanged: only the
        scheduler's genuinely-final scalar carries ``True``, and only that turn
        (if it commits) closes the accumulating expression. This is a true fact
        about where the real message ends -- not a guess about semantic
        completeness, and not invented content.

        ``defer_persistence`` is the second real scheduler-owned signal
        (utterance-transaction Milestone 1): ``True`` means this call is one
        scalar of one real multi-scalar turn whose durable store commit is
        batched at the turn's final scalar. Every learn this call performs
        still happens for real, per scalar, in memory -- every receipt
        mechanism, every learn transaction, every checkpoint-tick advance is
        byte-identical to the immediate-persistence path -- but the
        ``ImmutableGenerationStore`` commit itself (8 fsyncs + two full
        verification passes per commit) is deferred and fired exactly once,
        after the final scalar's own result is complete, so long as ANY scalar
        of the turn genuinely changed learned state. A turn that changes no
        learned state commits nothing. It defaults to ``False`` so every
        existing single-scalar caller keeps today's commit-immediately
        behaviour unchanged. Crash honesty is preserved structurally: a
        deferred turn performs NO store write before its single flush, so a
        death anywhere mid-turn leaves the store's last published generation
        exactly as it was before the turn began (the store's own atomic-commit
        contract), and :attr:`has_unpersisted_learned_state` reports honestly
        whenever in-memory learned state is ahead of the persisted generation.
        """

        if not isinstance(is_final_scalar, bool):
            raise ReceiptError(
                "is_final_scalar must be a real boolean end-of-message signal"
            )
        if not isinstance(defer_persistence, bool):
            raise ReceiptError(
                "defer_persistence must be a real boolean turn-batching signal"
            )
        turn.verify()
        with self._lock:
            try:
                result = self._run_locked(
                    turn=turn,
                    story_chemistry=story_chemistry,
                    is_final_scalar=is_final_scalar,
                    defer_persistence=defer_persistence,
                )
            except Exception:
                # Aborted-turn durability (Fix 2). A genuine exception
                # propagated out of this scalar's real processing (a fail-closed
                # ReceiptError, a store fault, etc.). That scalar is fail-closed
                # -- it mutated no learned state before raising -- but EARLIER
                # scalars of the same deferred turn already learned, each
                # individually passed every receipt gate, and left a batched
                # deferred checkpoint (``_deferred_checkpoint_tick``) that was
                # never written. Baseline per-scalar mode would have durably
                # persisted those learns; flushing them now, before the abort
                # propagates, keeps an aborted turn exactly as durable as
                # baseline and leaves no stranded pending state for deploy
                # quiescence to lose. Nothing is invented (the aborted scalar
                # itself learned nothing), and because only a genuinely
                # DEFERRED (never-attempted) checkpoint is flushed, this never
                # re-attempts an immediate commit that just failed and single-
                # scalar immediate callers (which never defer) are untouched.
                # Deliberately ``Exception``, not ``BaseException``: a
                # process-directed ``KeyboardInterrupt``/``SystemExit`` is
                # crash-like, and the crash-mid-turn contract is to leave the
                # untouched pre-turn generation (see the crash tests), so those
                # propagate WITHOUT a flush.
                if defer_persistence:
                    self._flush_deferred_checkpoint()
                raise
            # The one deferred flush point on the SUCCESS path: the turn's real
            # final scalar has fully completed (commit or honest silence alike
            # -- the flush fires whether or not the final scalar ITSELF
            # committed, so long as some scalar of the turn changed learned
            # state). A successful expression-close already persisted
            # immediately inside ``_close_learned_expression`` (that persist IS
            # this turn's one commit, and it clears the flush target), in which
            # case this is a no-op.
            if defer_persistence and is_final_scalar:
                self._flush_deferred_checkpoint()
            return result

    def serialize_turn(self):
        """Return the turn-level mutex (Fix 1), a real context manager the
        ``MultiScalarTurnScheduler`` holds for the WHOLE duration of one real
        multi-scalar turn.

        This engine's own ``self._lock`` serializes individual SCALARS, not
        whole turns. Two concurrent ``MultiScalarTurnScheduler.run_turn`` calls
        -- exactly what two overlapping ``/converse`` requests produce through
        app.py's lifecycle executor -- would otherwise interleave their scalars
        against this engine's single shared learned state at ``self._lock``
        granularity, so one turn's end-of-turn deferred flush could durably
        commit ANOTHER turn's mid-turn, still-in-flight learns (and lower its
        honesty flag). Holding this mutex for a whole turn makes turns fully
        serial -- architecture-consistent for a system that deliberately speaks
        with one mouth, one conversation turn at a time -- so each turn's
        single deferred flush covers exactly its own learns. Direct
        single-scalar callers of :meth:`run_clean_conversation` never acquire
        it and keep today's behaviour unchanged.
        """

        return self._turn_lock

    @property
    def has_unpersisted_learned_state(self) -> bool:
        """True iff this engine's in-memory learned state is ahead of the last
        generation a store commit actually SUCCEEDED in publishing. This is
        truthful in every path (Fix 3): it is raised before any store write is
        attempted -- deferred or immediate -- and lowered only after a commit
        genuinely succeeds, so it never reads False while memory is ahead, not
        even when an immediate commit raises mid-write. Any later successful
        checkpoint commit (deferred flush or immediate persist) writes the full
        current state and clears this."""

        return self._unpersisted_learned_change

    def _run_locked(
        self,
        *,
        turn: CleanConversationTurn,
        story_chemistry: StoryChemistryRuntime,
        is_final_scalar: bool,
        defer_persistence: bool,
    ) -> ConversationTransactionResult:
        expression, language_input, preparation, registry = self._build_turn_expression(
            turn=turn, story_chemistry=story_chemistry
        )

        pre_growth_bank = self._mode_bank
        recognition: ExpressionModeBoundaryResult = evaluate_expression_mode_boundary(
            topology=self._topology,
            bank=pre_growth_bank,
            input_expression=expression,
            receipt_registry=registry,
            # Live experience must GROW when the full field is structurally
            # distinct from every existing mode (owner Requirement 1), not
            # misrecognize it as the nearest reference.
            recognition_arbiter=RECOGNITION_ARBITER_CERTIFIED_RESIDUAL,
        )
        registry = _extend_registry(registry, *self._mode_payloads(recognition))
        # Real growth is a load-bearing side effect of recognition itself
        # (expression_modes.py); folding it back in makes every later turn's
        # recognition see everything genuinely experienced so far.
        self._mode_bank = recognition.post_growth_bank
        self._registry = registry
        # The single line that lets the injected recall provider recognize
        # against this engine's live grown bank (design section 3.4) and see
        # every prior-turn scene episode (section 5): publish the current bank,
        # scene archive, and learned motif-kind authorities into the shared
        # holder BEFORE run_clean_conversation_transaction consults the
        # provider.
        self._live_recall_state.update(
            mode_bank=self._mode_bank,
            scene_archive=self._scene_archive,
            motif_kinds=self._learned_state.motif_kinds,
        )

        if self._learned_state.initial_event is None:
            # Section 9.5: "A commit cannot speak unless a clean learned
            # state contains a unique coexperienced output binding."
            # RememberedOutputProviders cannot even be constructed without a
            # real initial_event (see module docstring) -- there is
            # structurally nothing further this call can honestly attempt.
            return _make_result(
                status=ConversationStatus.EXPLICIT_UNKNOWN_SILENCE,
                visible_text="",
                topology=self._topology,
                input_expression=expression,
                recognition=recognition,
                commit=None,
                initial_event=None,
                complete_expression=None,
                reason=(
                    "no coexperienced output has been learned yet; refusing "
                    "to fabricate a response"
                ),
            )

        try:
            sealed, registry = _seal(
                topology=self._topology,
                preparation=preparation,
                expression=expression,
                recognition=recognition,
                identity=turn.task_id,
                registry=registry,
            )
            commit_providers, registry = _build_commit_providers(
                identity=turn.task_id,
                sealed=sealed,
                topology=self._topology,
                l6_evaluation=self._l6_evaluation,
                registry=registry,
            )
            # ``run_clean_conversation_transaction`` recomputes the commit
            # decision internally and, before ever looking at its status,
            # requires the decision's OWN receipt payload to already be
            # mounted (``conversation.py``'s own ``_mounted_exact`` check,
            # immediately after its internal ``evaluate_commit_boundary``
            # call) -- nothing else in this codebase mounts that payload as a
            # side effect. This engine therefore evaluates the real, exact
            # same commit boundary once, here, so the transaction's own
            # internal (bit-for-bit identical, since both calls share every
            # input) recomputation finds it already mounted. This is the one
            # necessary call to ``evaluate_commit_boundary``, not a second,
            # redundant one: the same ``commit_decision`` computed here is
            # reused below for the learning step, so it is never evaluated
            # twice for two different purposes.
            commit_decision = evaluate_commit_boundary(
                topology=self._topology,
                recognition=recognition,
                l6_evaluation=commit_providers.l6_evaluation,
                l6_scope=commit_providers.l6_scope,
                closed_experience=commit_providers.closed_experience,
                safe_mode=commit_providers.safe_mode,
                event_support=commit_providers.event_support,
                evidence=commit_providers.evidence,
                l5_applicability=commit_providers.l5_applicability,
                global_uf_validation=commit_providers.global_uf_validation,
                receipt_registry=registry,
            )
            registry = _extend_registry(registry, commit_decision.receipt_payload)
        except ReceiptError as error:
            self._registry = registry
            return _make_result(
                status=ConversationStatus.EXPLICIT_UNKNOWN_SILENCE,
                visible_text="",
                topology=self._topology,
                input_expression=expression,
                recognition=recognition,
                commit=None,
                initial_event=None,
                complete_expression=None,
                reason=f"receipt_failure_before_transaction:{error}",
            )

        remembered_output = RememberedOutputProviders(
            binding_bank=self._learned_state.output_bank,
            stable_mode_motif_bank=self._learned_state.stable_bank,
            initial_event=self._learned_state.initial_event,
            fresh_recall_provider=self._fresh_recall_provider,
        )

        result = run_clean_conversation_transaction(
            topology=self._topology,
            mode_bank=pre_growth_bank,
            input_expression=expression,
            h_mem_providers=(),
            commit_providers=commit_providers,
            remembered_output=remembered_output,
            receipt_registry=registry,
        )
        result.verify()
        self._registry = registry

        if result.initial_event_receipt_sha256 is not None:
            # A real full-field commit genuinely happened this turn (see
            # module docstring for why this public field is the correct,
            # already-exposed signal). Learn it, then persist atomically.
            self._learn_and_persist(
                turn=turn,
                sealed=sealed,
                commit_decision=commit_decision,
                language_input=language_input,
                is_final_scalar=is_final_scalar,
                defer_persistence=defer_persistence,
            )

        return result

    @staticmethod
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

    # -- learning + atomic persistence ------------------------------------

    def _learn_and_persist(
        self,
        *,
        turn: CleanConversationTurn,
        sealed: SealedClosedExperience,
        commit_decision: CommitDecision,
        language_input,
        is_final_scalar: bool,
        defer_persistence: bool = False,
    ) -> None:
        if commit_decision.status is not CommitStatus.COMMIT:
            raise ReceiptError(
                "clean conversation engine attempted to learn from a "
                "non-committed turn"
            )
        registry = self._registry
        winner = sealed.recognition.winner_mode_index
        if winner is None:
            raise ReceiptError("committed turn lacks a recognized mode; cannot learn")
        committed = CommittedCoexperience(
            commit_decision, sealed, sealed.recognition.pre_growth_bank.modes[winner]
        )
        committed.verify(registry)

        prior_relation = self._learned_state.pending_relation
        if prior_relation is None:
            # Expression already explicitly closed (state is terminal); there is
            # nothing left to accumulate OR to close.
            return

        # Expression-close decision -- now driven by a real, non-fabricated
        # signal (design section 12's named cognition gate).
        #
        # ``is_final_scalar`` is the one true fact the ``MultiScalarTurnScheduler``
        # already knows structurally: which real Unicode scalar is the LAST one
        # in the real per-request message a real person actually sent this
        # request (``index == len(text) - 1``). That is a fact about where the
        # real message ends -- not a guess about semantic completeness, and not
        # invented content. Using it as the close signal encodes exactly one new
        # decision: "the real per-request message has ended, so if its last real
        # character committed, close what has been accumulated." It changes no
        # recognition/commit/preflight/stable-binding mechanism.
        #
        # * Every NON-final scalar keeps ``expression_close=False`` -- the
        #   historical accumulate-only path, unchanged: it chains
        #   ``pending_relation.selected_mode -> new content motif`` and moves
        #   ``pending`` forward, so the single ``LearnedBindingState``'s chain
        #   grows by one real scalar while ``initial_event`` stays anchored to
        #   genesis (recall replays the whole accumulated chain as one
        #   expression). This is "a real multi-scalar expression accumulates
        #   across several learn calls before closing."
        #
        # * The FINAL scalar of a committing turn closes the accumulated
        #   expression instead of extending it. ``learn_committed_binding_
        #   transaction(expression_close=True)`` rejects a typed-scalar close --
        #   it REQUIRES an explicit no-output coexperience (that module's own
        #   "expression close requires explicit no-output coexperience" guard),
        #   so a close is not "flip a boolean" but a genuinely different learn
        #   call mapping the accumulated leaf mode -> a close motif via a real
        #   ``create_coexperienced_no_output`` fact bound to this real committed
        #   scene, exactly as ``real_experience_learning_pipeline.
        #   close_real_multimodal_expression`` establishes (adapted here to reuse
        #   THIS engine's own six-lane runtime and atomic persistence rather than
        #   that narrower pipeline's). Because the close attaches to the current
        #   ``pending`` leaf and adds no content binding, it makes the accumulated
        #   expression terminal and emittable at exact close (``output.py`` /
        #   ``recall_reentry.py`` release visible text only at exact expression
        #   close) -- without ever fabricating a scalar or a meaning. This is the
        #   single, honest cognition the scheduler's real end-of-message fact
        #   authorises.
        if is_final_scalar:
            self._close_learned_expression(
                turn=turn,
                sealed=sealed,
                committed=committed,
                commit_decision=commit_decision,
                prior_relation=prior_relation,
            )
            return

        try:
            new_state = learn_committed_binding_transaction(
                state=self._learned_state,
                committed=committed,
                coexperienced_output=CoexperiencedOutput.from_typed_scalar(language_input),
                prior_relation=prior_relation,
                relation_id=f"{turn.task_id}-learn-{self._checkpoint_tick}",
                expression_close=False,
                receipt_registry=registry,
            )
        except ReceiptError as learn_error:
            # A real, already-succeeded recognition + full-field commit for
            # this turn (the caller only reaches this method when
            # ``result.initial_event_receipt_sha256 is not None``) can now
            # normally ALSO learn a new successor -- a committed mode may own
            # several successors keyed by distinct transition contexts (owner
            # Requirement 2). The one exception is re-living an IDENTICAL
            # transition context (same mode, same prior relation, same scene,
            # same senses): there is genuinely nothing new to learn, so
            # ``learn_committed_binding_transaction`` raises the exact
            # true-duplicate guard. That is honest cognitive "nothing new to
            # learn this turn," NOT a malformed-input/transport defect, and
            # never a reason to fabricate output: the real, already-computed
            # recognition + commit result is kept and returned unchanged by
            # ``_run_locked``; only this learn-and-persist side effect is
            # skipped. ``learn_committed_binding_transaction`` raises this
            # BEFORE mutating any state (it builds a new state and returns it;
            # on this raise nothing is assigned to ``self``), so this engine's
            # learned state, scene archive, registry and checkpoint tick are
            # all left exactly as they were.
            #
            # This converts ONLY that one exact, named, structurally-verified
            # fault to honest silence. Any OTHER real learn fault is a genuine
            # internal defect, not honest uncertainty, and must still surface
            # loudly as a real error -- so it is deliberately re-raised unless
            # BOTH the exact true-duplicate message AND the live structural
            # precondition (the mode really does already hold a successor in
            # this engine's own unmutated stable bank) hold. When unsure,
            # louder is safer than silently hiding a genuine bug.
            mode_already_has_successor = any(
                binding.mode_receipt_sha256
                == prior_relation.selected_mode_receipt_sha256
                for binding in self._learned_state.stable_bank.bindings
            )
            if (
                _LEARN_SUCCESSOR_ALREADY_EXISTS_MESSAGE not in str(learn_error)
                or not mode_already_has_successor
            ):
                raise
            # Loud diagnostic, per the owner's explicit instruction: failure
            # stays loud in diagnostics but must never become spoken output.
            # Printed to stdout (the established ``[glew]`` diagnostics channel;
            # captured by the deployment's log stream) with the real exception
            # type and message, so this remains fully diagnosable by a real
            # operator while the conversational interface only ever sees honest
            # typed silence.
            print(
                "[glew] learn-and-persist degraded to honest typed silence for "
                f"turn {turn.task_id!r}: {type(learn_error).__name__}: "
                f"{learn_error} -- the committed mode already holds its one "
                "learned successor, so this turn learned nothing new; the real "
                "recognition+commit result is kept unchanged (no fabricated "
                "output).",
                flush=True,
            )
            return

        # Archive the coexperienced scene so a later turn's fresh full-field
        # recall can deterministically reconstruct it (design section 7.1.3).
        # The episode stores only the learned binding's identity plus the
        # reconstruction key ``(task_id, text)``; the sensory receipts recorded
        # are exactly the six-lane, non-language receipts the new binding
        # already carries (``_sensory_receipts(sealed)``), so a real learned
        # binding resolves it (section 3.2).
        prior_binding_ids = {
            value.binding_receipt_sha256 for value in self._learned_state.output_bank.bindings
        }
        new_bindings = tuple(
            value
            for value in new_state.output_bank.bindings
            if value.binding_receipt_sha256 not in prior_binding_ids
        )
        if len(new_bindings) != 1:
            raise ReceiptError(
                "clean conversation engine expected exactly one new output binding to archive"
            )
        new_binding = new_bindings[0]
        sensory_receipts = _sensory_receipts(sealed)
        if new_binding.sensory_evidence_receipt_sha256s != sensory_receipts:
            raise ReceiptError(
                "learned binding sensory evidence differs from the sealed scene's six-lane receipts"
            )
        episode = create_coexperienced_scene_episode(
            profile_binding_sha256=new_state.receipt_registry.profile_binding_sha256,
            motif_receipt_sha256=new_binding.motif_receipt_sha256,
            sensory_evidence_receipt_sha256s=sensory_receipts,
            coexperienced_scalar_text=turn.text,
            scene_task_id=turn.task_id,
            scene_language_text=turn.text,
            engine_id=self._engine_id,
        )
        try:
            updated_archive = self._scene_archive.with_episode(episode)
        except ReceiptError as archive_error:
            # A committed mode may now own several successors keyed by distinct
            # transition contexts (owner Requirement 2), so re-experiencing an
            # ALREADY-ARCHIVED scene from a new prior context genuinely learns a
            # sibling successor above.  But the coexperienced-scene archive is
            # keyed by the scene's own six-lane sensory receipts (one episode
            # per scene), so that identical scene cannot be archived a second
            # time under a different motif -- exactly the "same scene, two
            # successors" boundary the fresh-commit self-recall chain cannot
            # reproduce at recall time either.  Rather than crash or persist a
            # learned/archived split, degrade THIS turn to honest typed silence
            # atomically: nothing is assigned to ``self``, so the engine's
            # learned state, scene archive, registry and checkpoint tick are
            # left exactly as they were.  Any OTHER archive fault is a genuine
            # defect and stays loud.
            if _SCENE_ALREADY_ARCHIVED_MESSAGE not in str(archive_error):
                raise
            print(
                "[glew] learn-and-persist degraded to honest typed silence for "
                f"turn {turn.task_id!r}: {type(archive_error).__name__}: "
                f"{archive_error} -- this scene is already archived, so a "
                "Requirement-2 sibling successor for the same scene cannot be "
                "durably re-archived; the real recognition+commit result is "
                "kept unchanged (no fabricated output).",
                flush=True,
            )
            return
        self._scene_archive = updated_archive

        self._learned_state = new_state
        self._registry = new_state.receipt_registry
        self._live_recall_state.update(
            mode_bank=self._mode_bank,
            scene_archive=self._scene_archive,
            motif_kinds=self._learned_state.motif_kinds,
        )
        # A deferred (real multi-scalar) turn advances the checkpoint tick
        # exactly as an immediate persist would -- so every relation id /
        # checkpoint id stays byte-identical to the per-scalar commit chain --
        # but batches the actual store commit at the turn's final scalar.
        self._persist_checkpoint(defer=defer_persistence)

    def _close_learned_expression(
        self,
        *,
        turn: CleanConversationTurn,
        sealed: SealedClosedExperience,
        committed: CommittedCoexperience,
        commit_decision: CommitDecision,
        prior_relation,
    ) -> None:
        """Close the currently-accumulated expression at its pending leaf.

        Called only for the real final scalar of a committing turn (see
        :meth:`_learn_and_persist`). A close is NOT a content learn and NOT a
        boolean flip: ``learn_committed_binding_transaction(expression_close=
        True)`` requires an explicit ``create_coexperienced_no_output`` fact
        bound to a real sealed committed scene (its own "expression close
        requires explicit no-output coexperience" guard). This reuses the exact
        real construction ``real_experience_learning_pipeline.
        close_real_multimodal_expression`` establishes, but against THIS turn's
        own just-committed six-lane scene and this engine's own atomic
        persistence -- so the close is native to the same runtime the engine
        commits and learns in, per this session's own two-pipeline distinction.

        The close maps ``prior_relation.selected_mode`` (the accumulated leaf
        mode) -> a close motif, adds no output binding, and makes the state
        terminal; ``output.py`` / ``recall_reentry.py`` then release the
        accumulated visible text at this exact close. No new scene is archived
        (a close carries no reconstructable coexperienced scene); the existing
        scene archive is untouched.

        Fail-closed and honest: any receipt fault here is confined to this
        learn/persist side effect. The real recognition+commit+recall result for
        this turn was already computed and returned by ``_run_locked`` BEFORE
        this method runs, so a close-side fault must never crash the turn and
        must never become fabricated output. It is degraded to loud ``[glew]``
        diagnostics (the owner's explicit rule: failure stays loud in
        diagnostics but never becomes spoken output) with nothing assigned to
        ``self`` -- the engine's learned state, archive, registry and checkpoint
        tick are left exactly as they were.
        """

        registry = self._registry
        try:
            no_output, registry = create_coexperienced_no_output(
                event_id=f"{turn.task_id}-expression-close-{self._checkpoint_tick}",
                sealed=sealed,
                source_authority_receipt_sha256=commit_decision.receipt_sha256,
                receipt_registry=registry,
            )
            closed_state = learn_committed_binding_transaction(
                state=self._learned_state,
                committed=committed,
                coexperienced_output=CoexperiencedOutput.from_no_output(no_output),
                prior_relation=prior_relation,
                relation_id=f"{turn.task_id}-expression-close-relation-{self._checkpoint_tick}",
                expression_close=True,
                receipt_registry=registry,
            )
        except ReceiptError as close_error:
            print(
                "[glew] expression-close degraded to honest typed silence for "
                f"turn {turn.task_id!r}: {type(close_error).__name__}: "
                f"{close_error} -- the accumulated expression could not be closed "
                "this turn; the real recognition+commit+recall result is kept "
                "unchanged (no fabricated output).",
                flush=True,
            )
            return

        self._learned_state = closed_state
        self._registry = closed_state.receipt_registry
        self._live_recall_state.update(
            mode_bank=self._mode_bank,
            scene_archive=self._scene_archive,
            motif_kinds=self._learned_state.motif_kinds,
        )
        self._persist_checkpoint()

    def _persist_checkpoint(self, *, defer: bool = False) -> None:
        """Record one learned-state change at the next checkpoint tick.

        ``defer=False`` (the default, and the exact historical behaviour every
        existing caller keeps): build this tick's checkpoint payloads and
        commit a new immutable generation NOW.

        ``defer=True`` (only a real multi-scalar turn's non-final state
        changes): consume the checkpoint tick exactly as an immediate persist
        would -- the tick counter is the input to every relation id and
        checkpoint id, so consuming it identically is what keeps the deferred
        turn's learned state byte-identical to the per-scalar commit chain --
        but record the tick as the flush target instead of committing, so the
        turn's single flush (:meth:`_flush_deferred_checkpoint`) commits the
        full accumulated state once, labelled with the LAST consumed tick (the
        same tick today's final per-scalar commit of the same turn would
        carry).

        Either way, the honesty flag ``_unpersisted_learned_change`` is raised
        FIRST -- before any store write is attempted -- and cleared only inside
        :meth:`_commit_checkpoint_generation` after a commit genuinely
        succeeds, so :attr:`has_unpersisted_learned_state` is truthful even if
        an immediate commit raises mid-write (Fix 3). A successful immediate
        commit also clears any pending deferred flush target: a generation
        commit always persists this engine's ENTIRE current learned state, so
        whatever change the deferred tick was recording is durably included in
        the newer generation.
        """

        tick = self._checkpoint_tick
        self._checkpoint_tick += 1
        # Truthful in every failure path: in-memory learned state is now ahead
        # of the last durable commit. Recorded before ANY store write.
        self._unpersisted_learned_change = True
        if defer:
            self._deferred_checkpoint_tick = tick
            return
        self._commit_checkpoint_generation(tick)

    def _flush_deferred_checkpoint(self) -> None:
        """Commit the one pending DEFERRED (batched, never-attempted) generation,
        if any, and clear the flush target.

        Called on a deferred turn's final scalar (success) and on abort of a
        deferred turn (Fix 2). No-op when no deferred commit is outstanding --
        either the turn never changed learned state (a turn with zero state
        changes commits nothing), or the final scalar's own successful
        expression-close already persisted immediately (that immediate persist
        was this turn's single commit and cleared the flush target). Because it
        only ever fires for a genuinely-deferred tick, it never re-attempts an
        immediate commit that already raised."""

        tick = self._deferred_checkpoint_tick
        if tick is None:
            return
        self._commit_checkpoint_generation(tick)

    def _commit_checkpoint_generation(self, tick: int) -> None:
        learning_checkpoint_id = f"{self._engine_id}-learning-{tick}"
        archive_checkpoint_id = f"{self._engine_id}-archive-{tick}"

        learning_bytes = learned_binding_checkpoint_payload(
            state=self._learned_state,
            checkpoint_id=learning_checkpoint_id,
            authentication_key=self._checkpoint_authentication_key,
            key_id=self._checkpoint_key_id,
        )
        archive_bytes = coexperienced_scene_archive_checkpoint_payload(
            archive=self._scene_archive,
            checkpoint_id=archive_checkpoint_id,
            authentication_key=self._checkpoint_authentication_key,
            key_id=self._checkpoint_key_id,
        )
        binding = bind_generation_identity(
            genesis_identity=self._generation_identity.genesis_identity,
            genesis_generation_uuid=self._generation_identity.genesis_generation_uuid,
            genesis_tick=self._generation_identity.genesis_tick,
            learning_checkpoint_id=learning_checkpoint_id,
            archive_checkpoint_id=archive_checkpoint_id,
        )

        self._generation_store.commit(
            tick=tick,
            files={
                LEARNING_CHECKPOINT_RELATIVE_PATH: learning_bytes,
                ARCHIVE_CHECKPOINT_RELATIVE_PATH: archive_bytes,
                GENERATION_IDENTITY_BINDING_RELATIVE_PATH: binding.receipt_payload,
            },
        )
        # The commit published this engine's ENTIRE current learned state, so
        # every outstanding marker is now durably satisfied. Cleared ONLY here,
        # after ``store.commit`` actually returned -- if it raised, both markers
        # stay set and ``has_unpersisted_learned_state`` keeps reporting the
        # truth (Fix 3), while the deferred flush target is left intact so the
        # never-attempted work is not silently forgotten.
        self._deferred_checkpoint_tick = None
        self._unpersisted_learned_change = False


__all__ = (
    "ARCHIVE_CHECKPOINT_RELATIVE_PATH",
    "CHECKPOINT_RELATIVE_PATHS",
    "GENERATION_IDENTITY_BINDING_RELATIVE_PATH",
    "LEARNING_CHECKPOINT_RELATIVE_PATH",
    "GenerationIdentityParameters",
    "ProductionCleanConversationEngine",
)
