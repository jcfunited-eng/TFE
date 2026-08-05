from __future__ import annotations

import ast
import inspect

from dsf_ai_service.substrate.auditory_motif_causal_grounding import (
    grounding_roots_from_settlement,
)
from dsf_ai_service.substrate.embodiment_world import (
    PORT_ID,
    MoveCommand,
    PoseMM,
    PositionMM,
    encode_command,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_action_vocal_lesson import (
    is_dynamic_grounding_root,
)
import dsf_ai_service.substrate.w1_action_vocal_demonstration as demonstration
import dsf_ai_service.substrate.w1_external_self_imitation as imitation
import dsf_ai_service.substrate.w1_fresh_spatial_vocal_challenge as challenge
from dsf_ai_service.substrate.w1_signed_spatial_action_settlement import (
    W1_SIGNED_SPATIAL_ACTION_CONSUMER_ID,
    W1SignedSpatialActionResourceProfile,
    W1SignedSpatialActionSettlementAuthority,
)
from tests.test_w1_audiovisual_physical_evidence import (
    EVIDENCE_KEY,
    WORLD_KEY,
    _authority,
    _world,
)


KEY = b"W1-recurrence-custody-boundary-test-key"


def _called_attributes(module) -> frozenset[str]:
    tree = ast.parse(inspect.getsource(module))
    return frozenset(
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
    )


def _imported_names(module) -> frozenset[str]:
    tree = ast.parse(inspect.getsource(module))
    return frozenset(
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    )


def test_recurrence_consumers_have_no_raw_mount_or_remount_surface():
    forbidden_calls = {
        "mount",
        "mount_action_outcome",
        "mount_authenticated_action_outcome",
        "mount_current_observation",
        "propagate",
        "settle",
        "transduce",
        "transduce_auditory_full_field",
    }
    forbidden_types = {
        "PreparedSelfVocalEmission",
        "W1PhysicalEvidenceMount",
        "W1SelfAcousticMount",
    }
    for module in (demonstration, imitation, challenge):
        assert _called_attributes(module).isdisjoint(forbidden_calls)
        assert _imported_names(module).isdisjoint(forbidden_types)


def test_recurrence_entry_points_require_purpose_bound_custody():
    demonstration_parameters = set(inspect.signature(
        demonstration.W1ActionVocalDemonstrationOwner.admit
    ).parameters)
    imitation_parameters = set(inspect.signature(
        imitation.W1ExternalSelfImitationAuthority.admit
    ).parameters)
    challenge_prepare_parameters = set(inspect.signature(
        challenge.W1FreshSpatialVocalChallengeExecutor.prepare
    ).parameters)
    challenge_commit_parameters = set(inspect.signature(
        challenge.W1FreshSpatialVocalChallengeExecutor.commit
    ).parameters)

    assert {
        "action_custody_authority",
        "action_custody_capability",
        "self_custody_authority",
        "self_custody_capability",
    }.issubset(demonstration_parameters)
    assert {
        "external_custody_authority",
        "external_custody_capability",
        "self_custody_authority",
        "self_custody_capability",
    }.issubset(imitation_parameters)
    assert {
        "vocal_custody_authority",
        "vocal_custody_capability",
    }.issubset(challenge_prepare_parameters)
    assert {
        "action_custody_authority",
        "action_custody_capability",
        "spatial_custody_capability",
    }.issubset(challenge_commit_parameters)
    assert {
        "action_execution",
        "action_mount",
        "external_execution",
        "self_emission",
        "self_mount",
        "vocal_execution",
        "vocal_mount",
    }.isdisjoint(
        demonstration_parameters
        | imitation_parameters
        | challenge_prepare_parameters
        | challenge_commit_parameters
    )


def test_signed_spatial_outcome_settles_from_custody_without_remount(
    monkeypatch,
):
    world = _world()
    physical = _authority(world)
    before = world.observation_snapshot()
    execution = world.execute_port_command(
        port_id=PORT_ID,
        command_payload=encode_command(MoveCommand(
            PoseMM(PositionMM(1_000, 1_400, 0), 0), 200_000
        )),
        causal_intent_receipt_sha256="a" * 64,
        expected_revision=before.revision,
    )
    mount = physical.mount_action_outcome(execution)
    dynamic_roots = tuple(
        value
        for value in grounding_roots_from_settlement(
            mount.causal_settlement
        )
        if is_dynamic_grounding_root(value)
    )
    custody = SettledExperienceCustodyAuthority(
        authority_key=KEY,
        w1_physical_authority_key=EVIDENCE_KEY,
        world_authority_key=WORLD_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="W1-recurrence-spatial-custody",
            max_children=2,
            max_snapshot_bytes=64 * 1024 * 1024,
        ),
    )
    custody.admit(mount, execution)
    capability = custody.issue_child(
        W1_SIGNED_SPATIAL_ACTION_CONSUMER_ID
    )
    spatial = W1SignedSpatialActionSettlementAuthority(
        authority_key=KEY,
        resource_profile=W1SignedSpatialActionResourceProfile.create(
            profile_id="W1-recurrence-spatial-settlement",
            max_settlements=1,
            required_dynamic_root_count=len(dynamic_roots),
            max_settlement_bytes=32 * 1024 * 1024,
            max_state_bytes=64 * 1024 * 1024,
        ),
        world_authority=world,
        physical_authority=physical,
    )

    monkeypatch.setattr(
        physical,
        "mount_action_outcome",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("downstream remount attempted")
        ),
    )
    result = spatial.settle_custodied(
        custody_authority=custody,
        custody_capability=capability,
    )

    assert result.execution_receipt_sha256 == (
        execution.authority_receipt_sha256
    )
    assert result.signed_displacement == (0, 400, 0, 0)
    assert result.full_dynamic_roots == dynamic_roots
