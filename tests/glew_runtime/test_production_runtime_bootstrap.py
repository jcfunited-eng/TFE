"""Real, non-monkeypatched conformance for
``dsf_ai_service.glew_runtime.production_runtime_bootstrap``.

Every fixture below drives the same real, already-committed production
machinery this module's own docstring describes (``mount_six_lane_runtime``,
``expression_learning``'s real transaction functions, the real packaged
production story-chemistry profile, ``ImmutableGenerationStore``) -- nothing
here monkeypatches recognition, commit, or persistence, and no test returns
``False`` instead of asserting the required result.
"""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.clean_conversation_engine import (
    ARCHIVE_CHECKPOINT_RELATIVE_PATH,
    GENERATION_IDENTITY_BINDING_RELATIVE_PATH,
    LEARNING_CHECKPOINT_RELATIVE_PATH,
    GenerationIdentityParameters,
    ProductionCleanConversationEngine,
)
from dsf_ai_service.glew_runtime.conversation import ConversationStatus
from dsf_ai_service.glew_runtime.conversation_service import (
    CleanConversationTurn,
    clean_conversation_turn_receipt_payload,
)
from dsf_ai_service.glew_runtime.expression_learning import (
    CoexperiencedOutput,
    learn_committed_binding_transaction,
    learned_binding_checkpoint_payload,
)
from dsf_ai_service.glew_runtime.coexperienced_scene_recall_provider import (
    CoexperiencedSceneRecallProvider,
)
from dsf_ai_service.glew_runtime.recall_reentry import FRESH_RECALL_SELF_SENSE_OPERATOR_ID
from dsf_ai_service.glew_runtime.generation_identity import bind_generation_identity
from dsf_ai_service.glew_runtime.model import ReceiptError, receipt_sha256
from dsf_ai_service.glew_runtime.operators import RequiredEdge
from dsf_ai_service.glew_runtime.production_runtime_bootstrap import (
    GENERATION_STORE_ROOT_ENVIRONMENT_VARIABLE,
    SixLaneRuntimeBootstrapParameters,
    bootstrap_genesis_learned_binding_state,
    bootstrap_production_clean_conversation_engine,
    resolve_default_generation_store_root,
)
from dsf_ai_service.glew_runtime.coexperienced_scene_archive import (
    CoexperiencedSceneArchive,
    coexperienced_scene_archive_checkpoint_payload,
)
from dsf_ai_service.glew_runtime.six_lane_runtime_mount import mount_six_lane_runtime
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    authenticate_production_story_chemistry_profile,
    mount_packaged_production_story_chemistry,
    production_story_chemistry_profile_payload,
)

from dsf_ai_service.substrate.immutable_generation_store import ImmutableGenerationStore

from tests.glew_runtime.test_story_native_replay import _sensor_port


_CHEM_KEY = b"production runtime bootstrap test chemistry runtime secret key!"
_CHEM_KEY_ID = "production-runtime-bootstrap-test-chemistry-key"
_ENGINE_ID = "production-runtime-bootstrap-test-engine"
_CHECKPOINT_KEY = bytes(range(32, 64))
_CHECKPOINT_KEY_ID = "production-runtime-bootstrap-test-checkpoint-key"
_GENESIS_IDENTITY = "33333333-3333-4333-8333-333333333333"
_GENESIS_GENERATION_UUID = "44444444-4444-8444-8444-444444444444"


def _generation_identity() -> GenerationIdentityParameters:
    return GenerationIdentityParameters(
        genesis_identity=_GENESIS_IDENTITY,
        genesis_generation_uuid=_GENESIS_GENERATION_UUID,
        genesis_tick=0,
    )


def _mount_test_chemistry_runtime():
    result = mount_packaged_production_story_chemistry(
        runtime_authentication_key=_CHEM_KEY, runtime_key_id=_CHEM_KEY_ID
    )
    assert result.status is StoryChemistryStatus.MOUNTED, result.reason
    return result.runtime


def _six_lane_runtime_parameters() -> SixLaneRuntimeBootstrapParameters:
    """Real, deliberately-chosen policy parameters for
    ``mount_six_lane_runtime`` -- mirrors exactly
    ``tests/glew_runtime/test_clean_conversation_engine.py``'s own
    ``_build_mounted_runtime()`` literals, since none of these values has any
    ratified production source (see this test's own module docstring and
    ``production_runtime_bootstrap.py``'s own "still genuinely synthetic"
    disclosure)."""

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

    return SixLaneRuntimeBootstrapParameters(
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
            b'{"schema":"test.production_runtime_bootstrap.kernel_adapter.v1"}'
        ),
        typed_language_adapter_id=f"{_ENGINE_ID}-typed-adapter",
        typed_language_interface_id=language_port_id,
        typed_language_phase_calibration_id=f"{_ENGINE_ID}-typed-phase",
        typed_language_phase_kappa=Fraction(1, 7),
        typed_language_derivation_payload=(
            b'{"schema":"test.production_runtime_bootstrap.typed_derivation.v1"}'
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
            b'{"schema":"test.production_runtime_bootstrap.memory_state.v1"}'
        ),
        pre_window_l6_state_payload=(
            b'{"schema":"test.production_runtime_bootstrap.l6_state.v1"}'
        ),
        l5_governance_profile_id=f"{_ENGINE_ID}-l5-profile",
        basin_profile_id=f"{_ENGINE_ID}-basin-profile",
        basin_physical_profile_payload=(
            b'{"schema":"test.production_runtime_bootstrap.physical_profile.v1"}'
        ),
        basin_hbar=Fraction(1),
        basin_source_time_unit=f"{_ENGINE_ID}-structural-time",
        basin_max_connected_component_dimension=1,
        basin_field_precision_bits=128,
    )


def _bootstrap(tmp_path, *, generation_identity=None):
    """Cold-start (or restore) through the real bootstrap. Per design section
    7.2.1 the bootstrap now constructs the real
    ``CoexperiencedSceneRecallProvider`` itself -- there is no injected
    fresh-recall provider to supply."""

    parameters = _six_lane_runtime_parameters()
    generation_identity = generation_identity or _generation_identity()

    engine = bootstrap_production_clean_conversation_engine(
        generation_store_root=tmp_path,
        story_chemistry_authentication_key=_CHEM_KEY,
        story_chemistry_key_id=_CHEM_KEY_ID,
        six_lane_runtime_parameters=parameters,
        checkpoint_authentication_key=_CHECKPOINT_KEY,
        checkpoint_key_id=_CHECKPOINT_KEY_ID,
        generation_identity=generation_identity,
        engine_id=_ENGINE_ID,
    )
    return engine, parameters


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


# ---------------------------------------------------------------------------
# (a) cold-start against an empty/fresh directory
# ---------------------------------------------------------------------------


def test_cold_start_against_empty_directory_produces_real_fresh_genesis_engine(tmp_path):
    engine, _parameters = _bootstrap(tmp_path)
    assert isinstance(engine, ProductionCleanConversationEngine)

    # A genuinely fresh genesis has never learned anything: any real turn
    # must produce typed silence, never a fabricated response, and the
    # engine's own internal learned state must show initial_event is None.
    assert engine._learned_state.initial_event is None
    engine._learned_state.verify()

    result = engine.run_clean_conversation(
        turn=_turn("production-runtime-bootstrap-cold-start-turn", "q"),
        story_chemistry=_mount_test_chemistry_runtime(),
    )
    result.verify()
    assert result.silent
    assert result.status is ConversationStatus.EXPLICIT_UNKNOWN_SILENCE
    assert result.initial_event_receipt_sha256 is None
    assert "no coexperienced output has been learned yet" in result.reason
    # Recognition still ran for real against the freshly-grown (rank two)
    # mode bank -- proving the genesis bootstrap's own real sensory/
    # expression/recognition pipeline actually executed, not merely a stub.
    assert result.recognition_receipt_sha256 is not None


def test_cold_start_constructs_the_real_coexperienced_scene_recall_provider(tmp_path):
    """Design section 7.2.1: the bootstrap now constructs the real
    ``CoexperiencedSceneRecallProvider`` itself (the whole point of "build
    recall before wiring live"), rather than demanding an injected stub."""

    engine, _parameters = _bootstrap(tmp_path)
    provider = engine._fresh_recall_provider
    assert isinstance(provider, CoexperiencedSceneRecallProvider)
    assert provider.operator_id == FRESH_RECALL_SELF_SENSE_OPERATOR_ID
    # The provider's authority receipt is mounted in the engine's registry, so
    # a real committing turn could reach it (the transaction resolves it).
    assert engine._registry.resolve(
        provider.authority_receipt_sha256, "provider authority"
    )
    # The provider shares the engine's live holder, so it recognizes against
    # the engine's live grown bank and sees prior-turn scene episodes.
    assert provider.executor.live_recall_state is engine._live_recall_state


# ---------------------------------------------------------------------------
# (b) persist one real learning checkpoint, then cold-start again against
# the SAME directory and confirm a genuine round trip.
# ---------------------------------------------------------------------------


def test_restore_round_trip_matches_persisted_learned_state(tmp_path):
    """Persist one real learned successor into the SAME store this
    bootstrap's own cold-start path would open, then bootstrap AGAIN against
    that identical directory and confirm the restored ``LearnedBindingState``
    genuinely matches what was persisted -- not merely "it didn't crash"."""

    generation_identity = _generation_identity()
    parameters = _six_lane_runtime_parameters()

    envelope = authenticate_production_story_chemistry_profile(
        profile_body_payload=production_story_chemistry_profile_payload(),
        runtime_authentication_key=_CHEM_KEY,
        runtime_key_id=_CHEM_KEY_ID,
    )
    mounted_runtime = mount_six_lane_runtime(
        story_chemistry_profile_bytes=envelope,
        story_chemistry_authentication_key=_CHEM_KEY,
        story_chemistry_expected_key_id=_CHEM_KEY_ID,
        **parameters.as_mount_kwargs(),
    )
    base_registry = mounted_runtime.story_chemistry_runtime.receipt_registry
    from dsf_ai_service.glew_runtime.production_runtime_bootstrap import _merge_registry

    base_registry = _merge_registry(base_registry, mounted_runtime.receipt_registry)

    genesis_result = bootstrap_genesis_learned_binding_state(
        mounted_runtime=mounted_runtime,
        engine_id=_ENGINE_ID,
        chemistry_authentication_key=_CHEM_KEY,
        chemistry_key_id=_CHEM_KEY_ID,
        typed_language_phase_calibration_id=parameters.typed_language_phase_calibration_id,
        typed_language_phase_kappa=parameters.typed_language_phase_kappa,
        receipt_registry=base_registry,
    )
    assert genesis_result.genesis.initial_event is None

    # Learn one real successor directly (mirrors
    # ``test_clean_conversation_engine.py``'s own fixture: the engine itself
    # can never learn its own first successor through ``run_clean_
    # conversation`` -- ``_run_locked`` returns typed silence immediately
    # whenever ``initial_event is None``, before any commit/learn is ever
    # attempted -- so bootstrapping the first real successor must happen
    # outside any engine instance, exactly as
    # ``real_experience_learning_pipeline.learn_one_real_multimodal_expression``
    # itself already does for its own narrower topology).
    learned = learn_committed_binding_transaction(
        state=genesis_result.genesis,
        committed=genesis_result.bootstrap_committed,
        coexperienced_output=CoexperiencedOutput.from_typed_scalar(genesis_result.bootstrap_language),
        prior_relation=genesis_result.initial_relation,
        relation_id=f"{_ENGINE_ID}-genesis-bootstrap-relation",
        expression_close=False,
        receipt_registry=genesis_result.genesis.receipt_registry,
    )
    assert learned.initial_event is not None

    # Persist it directly into the same generation store this bootstrap's
    # own restore path will later open -- replicating
    # ``ProductionCleanConversationEngine._persist_checkpoint``'s own real
    # persistence pattern exactly (same real functions, same file set).
    store = ImmutableGenerationStore(
        tmp_path,
        identity=generation_identity.genesis_identity,
        required_files=(
            LEARNING_CHECKPOINT_RELATIVE_PATH,
            ARCHIVE_CHECKPOINT_RELATIVE_PATH,
            GENERATION_IDENTITY_BINDING_RELATIVE_PATH,
        ),
    )
    learning_checkpoint_id = f"{_ENGINE_ID}-manual-learning-0"
    archive_checkpoint_id = f"{_ENGINE_ID}-manual-archive-0"
    learning_bytes = learned_binding_checkpoint_payload(
        state=learned,
        checkpoint_id=learning_checkpoint_id,
        authentication_key=_CHECKPOINT_KEY,
        key_id=_CHECKPOINT_KEY_ID,
    )
    archive_bytes = coexperienced_scene_archive_checkpoint_payload(
        archive=CoexperiencedSceneArchive(),
        checkpoint_id=archive_checkpoint_id,
        authentication_key=_CHECKPOINT_KEY,
        key_id=_CHECKPOINT_KEY_ID,
    )
    binding = bind_generation_identity(
        genesis_identity=generation_identity.genesis_identity,
        genesis_generation_uuid=generation_identity.genesis_generation_uuid,
        genesis_tick=generation_identity.genesis_tick,
        learning_checkpoint_id=learning_checkpoint_id,
        archive_checkpoint_id=archive_checkpoint_id,
    )
    store.commit(
        tick=0,
        files={
            LEARNING_CHECKPOINT_RELATIVE_PATH: learning_bytes,
            ARCHIVE_CHECKPOINT_RELATIVE_PATH: archive_bytes,
            GENERATION_IDENTITY_BINDING_RELATIVE_PATH: binding.receipt_payload,
        },
    )

    # Now cold-start AGAIN against the SAME directory: this must take the
    # restore branch, never the fresh-genesis branch.
    engine, _ = _bootstrap(tmp_path, generation_identity=generation_identity)
    restored_state = engine._learned_state

    # Round-trip proof: the restored state's own receipts genuinely match
    # what was persisted -- not merely "it didn't crash".
    assert restored_state.receipt_sha256 == learned.receipt_sha256
    assert restored_state.receipt_payload == learned.receipt_payload
    assert restored_state.initial_event is not None
    assert restored_state.initial_event.event_receipt_sha256 == learned.initial_event.event_receipt_sha256
    assert restored_state.output_bank.bank_receipt_sha256 == learned.output_bank.bank_receipt_sha256
    assert restored_state.stable_bank.bank_receipt_sha256 == learned.stable_bank.bank_receipt_sha256
    assert restored_state.terminal == learned.terminal
    restored_state.verify()


def test_restore_rejects_a_generation_identity_mismatch(tmp_path):
    """A persisted generation bound to one genesis identity triple must not
    be silently accepted by a bootstrap call claiming a different
    ``genesis_generation_uuid`` for that SAME ``genesis_identity`` -- this is
    exactly ``generation_identity.verify_generation_identity_binding``'s own
    stated purpose ("reject a restart that mixes generations"). (A mismatched
    ``genesis_identity`` itself is caught even earlier, by
    ``ImmutableGenerationStore``'s own CURRENT-pointer identity gate, since
    this bootstrap binds the store's own ``identity`` to
    ``genesis_identity`` -- see ``test_restore_rejects_a_store_identity_mismatch``
    below for that defense-in-depth layer.)"""

    original_identity = _generation_identity()
    _bootstrap_and_persist_one_learned_successor(tmp_path, original_identity)

    drifted_identity = GenerationIdentityParameters(
        genesis_identity=original_identity.genesis_identity,
        genesis_generation_uuid="55555555-5555-8555-8555-555555555555",
        genesis_tick=original_identity.genesis_tick,
    )
    with pytest.raises(ReceiptError, match="restored genesis generation_uuid"):
        _bootstrap(tmp_path, generation_identity=drifted_identity)


def test_restore_rejects_a_store_identity_mismatch(tmp_path):
    """A completely different ``genesis_identity`` is rejected even earlier,
    by ``ImmutableGenerationStore``'s own CURRENT-pointer identity gate."""

    original_identity = _generation_identity()
    _bootstrap_and_persist_one_learned_successor(tmp_path, original_identity)

    drifted_identity = GenerationIdentityParameters(
        genesis_identity="55555555-5555-4555-8555-555555555555",
        genesis_generation_uuid=original_identity.genesis_generation_uuid,
        genesis_tick=original_identity.genesis_tick,
    )
    with pytest.raises(Exception, match="identity mismatch"):
        _bootstrap(tmp_path, generation_identity=drifted_identity)


def _bootstrap_and_persist_one_learned_successor(tmp_path, generation_identity):
    parameters = _six_lane_runtime_parameters()
    envelope = authenticate_production_story_chemistry_profile(
        profile_body_payload=production_story_chemistry_profile_payload(),
        runtime_authentication_key=_CHEM_KEY,
        runtime_key_id=_CHEM_KEY_ID,
    )
    mounted_runtime = mount_six_lane_runtime(
        story_chemistry_profile_bytes=envelope,
        story_chemistry_authentication_key=_CHEM_KEY,
        story_chemistry_expected_key_id=_CHEM_KEY_ID,
        **parameters.as_mount_kwargs(),
    )
    from dsf_ai_service.glew_runtime.production_runtime_bootstrap import _merge_registry

    base_registry = _merge_registry(
        mounted_runtime.story_chemistry_runtime.receipt_registry, mounted_runtime.receipt_registry
    )
    genesis_result = bootstrap_genesis_learned_binding_state(
        mounted_runtime=mounted_runtime,
        engine_id=_ENGINE_ID,
        chemistry_authentication_key=_CHEM_KEY,
        chemistry_key_id=_CHEM_KEY_ID,
        typed_language_phase_calibration_id=parameters.typed_language_phase_calibration_id,
        typed_language_phase_kappa=parameters.typed_language_phase_kappa,
        receipt_registry=base_registry,
    )
    learned = learn_committed_binding_transaction(
        state=genesis_result.genesis,
        committed=genesis_result.bootstrap_committed,
        coexperienced_output=CoexperiencedOutput.from_typed_scalar(genesis_result.bootstrap_language),
        prior_relation=genesis_result.initial_relation,
        relation_id=f"{_ENGINE_ID}-identity-mismatch-relation",
        expression_close=False,
        receipt_registry=genesis_result.genesis.receipt_registry,
    )
    store = ImmutableGenerationStore(
        tmp_path,
        identity=generation_identity.genesis_identity,
        required_files=(
            LEARNING_CHECKPOINT_RELATIVE_PATH,
            ARCHIVE_CHECKPOINT_RELATIVE_PATH,
            GENERATION_IDENTITY_BINDING_RELATIVE_PATH,
        ),
    )
    learning_checkpoint_id = f"{_ENGINE_ID}-mismatch-learning-0"
    archive_checkpoint_id = f"{_ENGINE_ID}-mismatch-archive-0"
    learning_bytes = learned_binding_checkpoint_payload(
        state=learned,
        checkpoint_id=learning_checkpoint_id,
        authentication_key=_CHECKPOINT_KEY,
        key_id=_CHECKPOINT_KEY_ID,
    )
    archive_bytes = coexperienced_scene_archive_checkpoint_payload(
        archive=CoexperiencedSceneArchive(),
        checkpoint_id=archive_checkpoint_id,
        authentication_key=_CHECKPOINT_KEY,
        key_id=_CHECKPOINT_KEY_ID,
    )
    binding = bind_generation_identity(
        genesis_identity=generation_identity.genesis_identity,
        genesis_generation_uuid=generation_identity.genesis_generation_uuid,
        genesis_tick=generation_identity.genesis_tick,
        learning_checkpoint_id=learning_checkpoint_id,
        archive_checkpoint_id=archive_checkpoint_id,
    )
    store.commit(
        tick=0,
        files={
            LEARNING_CHECKPOINT_RELATIVE_PATH: learning_bytes,
            ARCHIVE_CHECKPOINT_RELATIVE_PATH: archive_bytes,
            GENERATION_IDENTITY_BINDING_RELATIVE_PATH: binding.receipt_payload,
        },
    )


# ---------------------------------------------------------------------------
# Env-var / default-path convention
# ---------------------------------------------------------------------------


def test_default_generation_store_root_env_var_is_honored():
    resolved = resolve_default_generation_store_root(
        {GENERATION_STORE_ROOT_ENVIRONMENT_VARIABLE: "/tmp/example-glew-store"}
    )
    assert str(resolved) == "/tmp/example-glew-store"


def test_default_generation_store_root_falls_back_to_state_dir_sibling():
    resolved = resolve_default_generation_store_root({"STATE_DIR": "/data/guala/state"})
    assert resolved.name == "state-glew-conversation-engine"
    assert resolved.parent == resolved.parent  # sibling of STATE_DIR's own directory
    assert str(resolved).endswith("guala/state-glew-conversation-engine")
    # Must never collide with the legacy engine's own "-sealed" sibling or
    # with GLEW_GENESIS_ROOT (which has no default at all).
    assert not resolved.name.endswith("-sealed")
