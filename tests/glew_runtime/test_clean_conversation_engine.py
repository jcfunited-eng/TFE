"""Real, non-monkeypatched conformance for ``ProductionCleanConversationEngine``
(``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
section 12, Step 6).

Every fixture below is built by directly driving the same real, already-
committed Step 1-5 machinery ``real_experience_learning_pipeline.py`` already
proves works (its own private helpers are imported and reused unmodified,
never re-implemented), so that the ``MountedSixLaneRuntime``/
``LearnedBindingState`` this test hands the engine are genuine, receipt-
verified objects -- not test doubles. Nothing here monkeypatches recognition
or commit. The one still-missing production authority (a real
``fresh_recall_provider`` wired to a non-empty episode archive; see
``clean_conversation_engine.py``'s module docstring, "The fresh-recall gap")
is represented by the real, unmodified ``FullFieldFreshRecallProvider``
wired to a real but genuinely empty ``RecallStoryEpisodeArchive`` -- so every
turn this test drives through it exercises the real archive-lookup failure
path honestly, rather than faking success.
"""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.clean_conversation_engine import (
    ARCHIVE_CHECKPOINT_RELATIVE_PATH,
    CHECKPOINT_RELATIVE_PATHS,
    GENERATION_IDENTITY_BINDING_RELATIVE_PATH,
    LEARNING_CHECKPOINT_RELATIVE_PATH,
    GenerationIdentityParameters,
    ProductionCleanConversationEngine,
    _scene_descriptors,
)
from dsf_ai_service.glew_runtime.commit import CommitStatus
from dsf_ai_service.glew_runtime.conversation import ConversationStatus
from dsf_ai_service.glew_runtime.conversation_service import (
    CleanConversationTurn,
    clean_conversation_turn_receipt_payload,
)
from dsf_ai_service.glew_runtime.expression_learning import (
    CoexperiencedOutput,
    create_learned_binding_genesis,
    derive_committed_mode_relation,
    learn_committed_binding_transaction,
)
from dsf_ai_service.glew_runtime.fresh_recall_executor import FreshRecallClosedExperienceExecutor
from dsf_ai_service.glew_runtime.fresh_recall_provider import (
    FullFieldFreshRecallProvider,
    fresh_recall_provider_authority_receipt_payload,
)
from dsf_ai_service.glew_runtime.model import ReceiptError, receipt_sha256
from dsf_ai_service.glew_runtime.operators import RequiredEdge
from dsf_ai_service.glew_runtime.real_experience_learning_pipeline import (
    _build_expression,
    _build_typed_language_lane,
    _commit_real_scene,
    _evolve_real_causal_window,
    _physical_l6_evaluation,
    _seal,
)
from dsf_ai_service.glew_runtime.recall_story_episode_archive import RecallStoryEpisodeArchive
from dsf_ai_service.glew_runtime.six_lane_runtime_mount import mount_six_lane_runtime
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    authenticate_production_story_chemistry_profile,
    mount_packaged_production_story_chemistry,
    production_story_chemistry_profile_payload,
)

from dsf_ai_service.substrate.immutable_generation_store import ImmutableGenerationStore

from tests.glew_runtime.test_story_native_replay import _sensor_port


_CHEM_KEY = b"clean conversation engine test chemistry runtime secret key!!"
_CHEM_KEY_ID = "clean-conversation-engine-test-chemistry-key"
_ENGINE_ID = "clean-conversation-engine-test"
_CHECKPOINT_KEY = bytes(range(32))
_CHECKPOINT_KEY_ID = "clean-conversation-engine-test-checkpoint-key"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _engine_physical_profile_payload() -> bytes:
    return _canonical_bytes(
        {
            "identity": f"{_ENGINE_ID}-shared-field-profile",
            "schema": "glew.clean_conversation_engine.exact_field_profile.v1",
        }
    )


def _mount_test_chemistry_runtime():
    result = mount_packaged_production_story_chemistry(
        runtime_authentication_key=_CHEM_KEY,
        runtime_key_id=_CHEM_KEY_ID,
    )
    assert result.status is StoryChemistryStatus.MOUNTED, result.reason
    return result.runtime


def _build_mounted_runtime():
    envelope = authenticate_production_story_chemistry_profile(
        profile_body_payload=production_story_chemistry_profile_payload(),
        runtime_authentication_key=_CHEM_KEY,
        runtime_key_id=_CHEM_KEY_ID,
    )
    preliminary_runtime = _mount_test_chemistry_runtime()
    mounted_ports = tuple(_sensor_port(value) for value in preliminary_runtime.manifest.ports)
    sensor_ports = tuple(value[0] for value in mounted_ports)
    sensor_port_receipt_payloads = tuple(
        payload for value in mounted_ports for payload in (value[1], value[2])
    )
    five_sense_keys = tuple(value.field_key for value in sensor_ports)
    five_sense_edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(five_sense_keys[:-1], five_sense_keys[1:], strict=True)
    )
    language_port_id = f"{_ENGINE_ID}-typed-interface"
    six_lane_keys = (("language", language_port_id), *five_sense_keys)
    six_lane_edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(six_lane_keys[:-1], six_lane_keys[1:], strict=True)
    )

    return mount_six_lane_runtime(
        story_chemistry_profile_bytes=envelope,
        story_chemistry_authentication_key=_CHEM_KEY,
        story_chemistry_expected_key_id=_CHEM_KEY_ID,
        sensor_ports=sensor_ports,
        sensor_port_receipt_payloads=sensor_port_receipt_payloads,
        five_sense_topology_id=f"{_ENGINE_ID}-five-sense-topology",
        causal_grid_id=f"{_ENGINE_ID}-causal-grid",
        causal_timestamps=tuple(Fraction(index) for index in range(1, 6)),
        causal_positive_weights=tuple(Fraction(1) for _ in range(5)),
        five_sense_support_domain_id=f"{_ENGINE_ID}-five-sense-support",
        five_sense_resonance_graph_id=f"{_ENGINE_ID}-five-sense-resonance",
        five_sense_resonance_required_edges=five_sense_edges,
        resonance_operator_id=f"{_ENGINE_ID}-resonance-operator",
        resonance_precision_bits=128,
        story_replay_profile_id=f"{_ENGINE_ID}-story-replay-profile",
        story_replay_provider_id=f"{_ENGINE_ID}-story-replay-provider",
        story_replay_kernel_adapter_id=f"{_ENGINE_ID}-kernel-adapter",
        story_replay_kernel_adapter_profile_payload=(
            b'{"schema":"test.clean_conversation_engine.kernel_adapter.v1"}'
        ),
        typed_language_adapter_id=f"{_ENGINE_ID}-typed-adapter",
        typed_language_interface_id=language_port_id,
        typed_language_phase_calibration_id=f"{_ENGINE_ID}-typed-phase",
        typed_language_phase_kappa=Fraction(1, 7),
        typed_language_derivation_payload=(
            b'{"schema":"test.clean_conversation_engine.typed_derivation.v1"}'
        ),
        language_port_id=language_port_id,
        six_lane_topology_id=f"{_ENGINE_ID}-six-lane-topology",
        six_lane_support_domain_id=f"{_ENGINE_ID}-six-lane-support",
        six_lane_resonance_graph_id=f"{_ENGINE_ID}-six-lane-resonance",
        six_lane_resonance_required_edges=six_lane_edges,
        expression_precision_authority_id=f"{_ENGINE_ID}-expression-precision",
        expression_maximum_precision_bits=4096,
        pre_window_state_id=f"{_ENGINE_ID}-pre-window",
        pre_window_memory_state_payload=(
            b'{"schema":"test.clean_conversation_engine.memory_state.v1"}'
        ),
        pre_window_l6_state_payload=(
            b'{"schema":"test.clean_conversation_engine.l6_state.v1"}'
        ),
        l5_governance_profile_id=f"{_ENGINE_ID}-l5-profile",
        basin_profile_id=f"{_ENGINE_ID}-basin-profile",
        basin_physical_profile_payload=(
            b'{"schema":"test.clean_conversation_engine.physical_profile.v1"}'
        ),
        basin_hbar=Fraction(1),
        basin_source_time_unit=f"{_ENGINE_ID}-structural-time",
        basin_max_connected_component_dimension=1,
        basin_field_precision_bits=128,
    )


def _build_scene(*, mounted_runtime, task_id: str, text: str, chemistry_runtime, registry):
    """Build one real turn's field expression, mirroring
    ``ProductionCleanConversationEngine._build_turn_expression`` exactly (same
    real helpers, same identity-string conventions), so this fixture's scenes
    are bit-for-bit reproducible by the engine's own later replay."""

    from dsf_ai_service.glew_runtime.closed_experience import (
        ClosedExperienceProviderUnknown,
        prepare_closed_experience_evidence,
    )

    descriptors = _scene_descriptors(task_id)
    bridge = _evolve_real_causal_window(
        chemistry_runtime, scene_id=task_id, descriptors=descriptors
    )
    registry = _merge(registry, bridge.receipt_registry)

    language_input, registry = _build_typed_language_lane(
        binding=mounted_runtime.typed_language_kernel_binding,
        phase_id=f"{_ENGINE_ID}-typed-phase",
        phase_kappa=Fraction(1, 7),
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
    assert not isinstance(preparation, ClosedExperienceProviderUnknown), preparation
    registry = preparation.receipt_registry
    physical_profile_payload = _engine_physical_profile_payload()
    registry = _extend(registry, physical_profile_payload)

    expression, registry = _build_expression(
        topology=mounted_runtime.field_topology,
        preparation=preparation,
        precision=mounted_runtime.precision_authority,
        physical_profile_receipt_sha256=receipt_sha256(physical_profile_payload),
        identity=task_id,
        registry=registry,
    )
    return expression, language_input, preparation, registry


def _merge(registry, addition):
    # Keeps ``registry``'s own root; see clean_conversation_engine.py's
    # ``_merge_registry`` docstring for why the two sources' roots may
    # legitimately differ (mount_six_lane_runtime re-roots to its own
    # story-native-replay profile; chemistry-evolution registries stay
    # rooted at the chemistry manifest -- no single ratified root unifies
    # them anywhere in this repository yet).
    values = {item.digest: item.payload for item in registry.records}
    for record in addition.records:
        prior = values.get(record.digest)
        assert prior is None or prior == record.payload
        values[record.digest] = record.payload
    from dsf_ai_service.glew_runtime.model import ReceiptRecord, ReceiptRegistry

    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, values[key]) for key in sorted(values)),
    )


def _real_fresh_recall_provider(*, profile_binding_sha256: str, registry):
    """The real, unmodified ``FullFieldFreshRecallProvider`` wired to a real
    but genuinely empty ``RecallStoryEpisodeArchive`` -- see this test
    module's own docstring and ``clean_conversation_engine.py``'s "The
    fresh-recall gap" for why an empty archive, not a monkeypatch, is the
    honest choice here."""

    provider_id = f"{_ENGINE_ID}-fresh-recall-provider"
    provider_payload = fresh_recall_provider_authority_receipt_payload(
        provider_id=provider_id,
        profile_binding_sha256=profile_binding_sha256,
    )
    registry = _extend(registry, provider_payload)
    executor = FreshRecallClosedExperienceExecutor(
        executor_id=f"{_ENGINE_ID}-fresh-recall-executor",
        archive=RecallStoryEpisodeArchive(),
        runtime_resolver=None,  # never reached: archive.resolve() fails first (empty archive)
        language_interface=None,
        integrity_provider=None,
    )
    provider = FullFieldFreshRecallProvider(
        provider_id=provider_id,
        profile_binding_sha256=profile_binding_sha256,
        executor=executor,
        motif_kinds=(),
        authority_receipt_sha256=receipt_sha256(provider_payload),
    )
    return provider, registry


def _mode_payloads(result) -> tuple[bytes, ...]:
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


def _extend(registry, *payloads: bytes):
    from dsf_ai_service.glew_runtime.model import ReceiptRecord, ReceiptRegistry

    values = {item.digest: item.payload for item in registry.records}
    for payload in payloads:
        digest = receipt_sha256(payload)
        prior = values.get(digest)
        assert prior is None or prior == payload
        values[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, values[key]) for key in sorted(values)),
    )


@pytest.fixture(scope="module")
def fixture():
    """Real, non-monkeypatched fixture: mounts a genuine six-lane runtime,
    bootstraps its mode bank to rank two with two genuinely independent real
    scenes ("root" root_task_id text 'a', "content" text 'b'; the same
    real bootstrap requirement ``real_experience_learning_pipeline.py``'s own
    module docstring documents), commits both, and learns the content
    scene's own scalar as the root's first successor -- exactly mirroring
    ``learn_one_real_multimodal_expression``'s own real construction, just
    driven manually here so this test can keep direct access to the mounted
    runtime (``learn_one_real_multimodal_expression`` does not expose it)."""

    from dsf_ai_service.glew_runtime.expression_modes import (
        ExpressionRecognitionStatus,
        evaluate_expression_mode_boundary,
    )

    mounted_runtime = _build_mounted_runtime()

    root_task_id = "clean-conv-engine-fixture-root"
    content_task_id = "clean-conv-engine-fixture-content"

    root_chemistry = _mount_test_chemistry_runtime()
    content_chemistry = _mount_test_chemistry_runtime()

    # ``mount_six_lane_runtime`` re-roots its own returned registry at its
    # story-native-replay profile's own payload, while every chemistry-
    # runtime mount (and therefore every ``EvidenceStream``/typed-language
    # object built downstream of it) stays rooted at the chemistry
    # manifest's own payload instead -- and those two roots are not equal.
    # ``EvidenceStream``/etc. objects embed the exact root they were built
    # against and are re-checked against it later
    # (``closed_experience.prepare_closed_experience_evidence`` line ~1006),
    # so the registry threaded through scene construction must stay rooted
    # at the chemistry manifest (the root every real evidence stream this
    # test builds actually carries), with ``mounted_runtime``'s own records
    # folded in under that root instead of the other way around.
    registry = _merge(root_chemistry.receipt_registry, mounted_runtime.receipt_registry)

    root_expression, root_language, root_preparation, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id=root_task_id,
        text="a",
        chemistry_runtime=root_chemistry,
        registry=registry,
    )
    content_expression, content_language, content_preparation, registry = _build_scene(
        mounted_runtime=mounted_runtime,
        task_id=content_task_id,
        text="b",
        chemistry_runtime=content_chemistry,
        registry=registry,
    )

    empty_bank = mounted_runtime.expression_mode_bank
    root_growth = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=empty_bank,
        input_expression=root_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(root_growth))
    assert root_growth.status is ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
    assert root_growth.post_growth_bank.rank == 1
    content_growth = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=root_growth.post_growth_bank,
        input_expression=content_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(content_growth))
    assert content_growth.status is ExpressionRecognitionStatus.BOOTSTRAP_SILENCE
    assert content_growth.post_growth_bank.rank == 2

    grown_bank = content_growth.post_growth_bank
    root_recognition = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=grown_bank,
        input_expression=root_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(root_recognition))
    content_recognition = evaluate_expression_mode_boundary(
        topology=mounted_runtime.field_topology,
        bank=grown_bank,
        input_expression=content_expression,
        receipt_registry=registry,
    )
    registry = _extend(registry, *_mode_payloads(content_recognition))
    assert root_recognition.status is ExpressionRecognitionStatus.RECOGNIZED
    assert content_recognition.status is ExpressionRecognitionStatus.RECOGNIZED
    assert root_recognition.winner_mode_index != content_recognition.winner_mode_index

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
        identity=root_task_id,
        registry=registry,
    )
    content_sealed, registry = _seal(
        topology=mounted_runtime.field_topology,
        preparation=content_preparation,
        expression=content_expression,
        recognition=content_recognition,
        identity=content_task_id,
        registry=registry,
    )

    # The root scene's own commit MUST be built via the engine's own
    # ``_build_commit_providers`` + ``evaluate_commit_boundary`` (not
    # ``_commit_real_scene``, which uses different receipt schema strings)
    # -- this is the exact scene the engine will independently rebuild and
    # re-commit byte-for-byte when this fixture's root turn is later replayed
    # through ``ProductionCleanConversationEngine.run_clean_conversation``,
    # and ``conversation.py``'s ``_preflight_initial_output`` requires the
    # replayed commit receipt to exactly equal the one recorded in
    # ``initial_event`` at learning time.
    from dsf_ai_service.glew_runtime.commit import evaluate_commit_boundary
    from dsf_ai_service.glew_runtime.clean_conversation_engine import _build_commit_providers
    from dsf_ai_service.glew_runtime.expression_learning import CommittedCoexperience

    root_commit_providers, registry = _build_commit_providers(
        identity=root_task_id,
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
    assert root_commit_decision.status is CommitStatus.COMMIT
    registry = _extend(registry, root_commit_decision.receipt_payload)
    root_winner = root_recognition.winner_mode_index
    assert root_winner is not None
    root_committed = CommittedCoexperience(
        root_commit_decision, root_sealed, root_recognition.pre_growth_bank.modes[root_winner]
    )
    root_committed.verify(registry)

    content_committed, registry = _commit_real_scene(
        identity=content_task_id,
        sealed=content_sealed,
        topology=mounted_runtime.field_topology,
        l6_evaluation=l6_evaluation,
        registry=registry,
    )
    assert root_committed.commit.status is CommitStatus.COMMIT
    assert content_committed.commit.status is CommitStatus.COMMIT

    initial_relation, registry = derive_committed_mode_relation(
        relation_id=f"{root_task_id}-initial-relation",
        committed=root_committed,
        output_source_receipt_sha256=root_committed.commit.receipt_sha256,
        receipt_registry=registry,
    )
    genesis = create_learned_binding_genesis(
        state_id="clean-conv-engine-fixture-state",
        expression_id="clean-conv-engine-fixture-expression",
        initial_relation=initial_relation,
        receipt_registry=registry,
    )
    learned = learn_committed_binding_transaction(
        state=genesis,
        committed=content_committed,
        coexperienced_output=CoexperiencedOutput.from_typed_scalar(content_language),
        prior_relation=initial_relation,
        relation_id=f"{content_task_id}-content-relation",
        expression_close=False,
        receipt_registry=genesis.receipt_registry,
    )
    assert genesis.initial_event is None
    assert learned.initial_event is not None

    grown_runtime = mounted_runtime.__class__(
        story_chemistry_runtime=mounted_runtime.story_chemistry_runtime,
        story_native_replay_profile=mounted_runtime.story_native_replay_profile,
        field_topology=mounted_runtime.field_topology,
        causal_grid=mounted_runtime.causal_grid,
        support_domain=mounted_runtime.support_domain,
        resonance_graph=mounted_runtime.resonance_graph,
        resonance_operator=mounted_runtime.resonance_operator,
        sensor_states=mounted_runtime.sensor_states,
        typed_language_kernel_binding=mounted_runtime.typed_language_kernel_binding,
        precision_authority=mounted_runtime.precision_authority,
        expression_mode_bank=grown_bank,
        pre_window_state=mounted_runtime.pre_window_state,
        l5_governance_profile=mounted_runtime.l5_governance_profile,
        story_global_uf_basin_profile=mounted_runtime.story_global_uf_basin_profile,
        receipt_registry=mounted_runtime.receipt_registry,
    )

    return {
        "mounted_runtime": grown_runtime,
        "genesis": genesis,
        "learned": learned,
        "registry": learned.receipt_registry,
        "root_task_id": root_task_id,
        "root_chemistry": root_chemistry,
    }


def _new_generation_store(tmp_path_factory) -> ImmutableGenerationStore:
    root = tmp_path_factory.mktemp("clean-conv-engine-store")
    return ImmutableGenerationStore(
        root, identity="clean-conv-engine-test-identity", required_files=CHECKPOINT_RELATIVE_PATHS
    )


def _build_engine(
    *, mounted_runtime, learned_state, registry, generation_store, fresh_recall_provider=None
) -> ProductionCleanConversationEngine:
    if fresh_recall_provider is None:
        fresh_recall_provider, registry = _real_fresh_recall_provider(
            profile_binding_sha256=registry.profile_binding_sha256, registry=registry
        )
    return ProductionCleanConversationEngine(
        mounted_runtime=mounted_runtime,
        learned_state=learned_state,
        receipt_registry=registry,
        fresh_recall_provider=fresh_recall_provider,
        typed_language_phase_calibration_id=f"{_ENGINE_ID}-typed-phase",
        typed_language_phase_kappa=Fraction(1, 7),
        generation_identity=GenerationIdentityParameters(
            genesis_identity="11111111-1111-4111-8111-111111111111",
            genesis_generation_uuid="22222222-2222-8222-8222-222222222222",
            genesis_tick=0,
        ),
        generation_store=generation_store,
        checkpoint_authentication_key=_CHECKPOINT_KEY,
        checkpoint_key_id=_CHECKPOINT_KEY_ID,
        engine_id=_ENGINE_ID,
    )


def _turn(task_id: str, text: str, source: str = "test") -> CleanConversationTurn:
    payload = clean_conversation_turn_receipt_payload(task_id=task_id, text=text, source=source)
    turn = CleanConversationTurn(
        task_id=task_id,
        text=text,
        source=source,
        receipt_sha256=receipt_sha256(payload),
        receipt_payload=payload,
    )
    turn.verify()
    return turn


def test_fresh_genesis_learned_state_never_fabricates_a_response(fixture, tmp_path_factory):
    """Section 9.7 / section 12 Step 6's proof: construct the engine with a
    genuinely fresh-genesis ``LearnedBindingState`` (nothing learned yet --
    ``initial_event is None``) and confirm a real turn against it produces
    typed silence, never a fabricated response."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["genesis"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )

    turn = _turn("clean-conv-engine-fresh-genesis-turn", "a")
    result = engine.run_clean_conversation(
        turn=turn, story_chemistry=_mount_test_chemistry_runtime()
    )
    result.verify()

    assert result.silent
    assert result.status is ConversationStatus.EXPLICIT_UNKNOWN_SILENCE
    assert result.initial_event_receipt_sha256 is None
    assert result.commit_receipt_sha256 is None
    # Recognition was still evaluated for real (proving the engine's real
    # sensory/expression/recognition pipeline actually ran), even though the
    # engine refused to proceed to output because nothing has been learned.
    assert result.recognition_receipt_sha256 is not None
    assert "no coexperienced output has been learned yet" in result.reason


def test_real_end_to_end_commit_and_learn_no_monkeypatching(fixture, tmp_path_factory):
    """The Step 6 proof bar: drive a real turn through the engine's real
    ``run_clean_conversation`` -- recognition and commit are never
    monkeypatched -- and confirm a real ``ConversationTransactionResult``
    with real, self-verifying receipts. This turn exactly replays the
    fixture's own root scene ('a'), which is the only turn for which the
    fixture's real ``learned_state.initial_event`` can validly settle (see
    ``clean_conversation_engine.py``'s module docstring): a real full-field
    commit is expected to succeed, while the real, unmodified fresh-recall
    provider honestly fails (empty archive) rather than fabricating text --
    and, because a real commit did occur, the engine should learn a new
    binding and atomically persist a new checkpoint generation.
    """

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["learned"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )

    turn = _turn(fixture["root_task_id"], "a")
    result = engine.run_clean_conversation(
        turn=turn, story_chemistry=fixture["root_chemistry"]
    )
    result.verify()

    assert result.recognition_receipt_sha256 is not None
    assert result.commit_receipt_sha256 is not None
    assert result.initial_event_receipt_sha256 is not None
    # The real full-field commit succeeded; the real fresh-recall provider
    # honestly could not complete recall (empty archive), so this stays
    # typed silence rather than fabricated text.
    assert result.status is ConversationStatus.EXPLICIT_UNKNOWN_SILENCE
    assert "fresh_reentry_UNKNOWN" in result.reason
    assert not result.visible_text

    # A real commit happened, so the engine should have learned a new
    # binding and persisted a new checkpoint generation atomically.
    current = generation_store.load_current()
    learning_payload = current.payload(LEARNING_CHECKPOINT_RELATIVE_PATH)
    archive_payload = current.payload(ARCHIVE_CHECKPOINT_RELATIVE_PATH)
    identity_payload = current.payload(GENERATION_IDENTITY_BINDING_RELATIVE_PATH)
    assert learning_payload["body"]["schema"] == "glew.learning.binding_checkpoint.v1"
    assert archive_payload["body"]["schema"] == "glew.recall.coexperienced_scene_archive_checkpoint.v1"
    assert identity_payload["schema"] == "glew.identity.generation_binding.v1"
    # The engine archived the coexperienced scene it just learned (design 7.1.3):
    # exactly one episode, keyed to the learned binding's six-lane receipts.
    assert len(archive_payload["body"]["episodes"]) == 1


def test_missing_fresh_recall_provider_is_rejected_at_construction(fixture, tmp_path_factory):
    """The engine must not silently fabricate/substitute a fresh-recall
    provider: constructing it without one fails closed."""

    generation_store = _new_generation_store(tmp_path_factory)
    with pytest.raises(ReceiptError, match="fresh-recall provider"):
        ProductionCleanConversationEngine(
            mounted_runtime=fixture["mounted_runtime"],
            learned_state=fixture["genesis"],
            receipt_registry=fixture["registry"],
            fresh_recall_provider=None,
            typed_language_phase_calibration_id=f"{_ENGINE_ID}-typed-phase",
            typed_language_phase_kappa=Fraction(1, 7),
            generation_identity=GenerationIdentityParameters(
                genesis_identity="11111111-1111-4111-8111-111111111111",
                genesis_generation_uuid="22222222-2222-8222-8222-222222222222",
                genesis_tick=0,
            ),
            generation_store=generation_store,
            checkpoint_authentication_key=_CHECKPOINT_KEY,
            checkpoint_key_id=_CHECKPOINT_KEY_ID,
            engine_id=_ENGINE_ID,
        )


def test_multi_scalar_turn_text_is_rejected_not_truncated(fixture, tmp_path_factory):
    """A malformed turn (more than one Unicode scalar) is a transport
    defect, not a case of honest cognitive uncertainty -- it must not be
    silently truncated or converted into fabricated typed silence."""

    generation_store = _new_generation_store(tmp_path_factory)
    engine = _build_engine(
        mounted_runtime=fixture["mounted_runtime"],
        learned_state=fixture["genesis"],
        registry=fixture["registry"],
        generation_store=generation_store,
    )
    turn = _turn("clean-conv-engine-malformed-turn", "hello")
    with pytest.raises(ReceiptError, match="exactly one Unicode scalar"):
        engine.run_clean_conversation(
            turn=turn, story_chemistry=_mount_test_chemistry_runtime()
        )
