from __future__ import annotations

import hashlib
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.substrate import (
    articulatory_self_vocal_mechanics as module,
)
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryGeneratedEmission,
    ArticulatoryMotorResourceProfile,
    ArticulatoryProgram,
    ArticulatorySelfVocalMotorOwner,
    LaryngealExcitationConfiguration,
    PreparedArticulatoryGeneratedEmission,
    VocalTractConfiguration,
)
from dsf_ai_service.substrate.embodiment_world import (
    EmbodimentWorldAuthority,
)


KEY = b"prepared-articulatory-emission-test-key"
INTENT = "7" * 64


def _program() -> ArticulatoryProgram:
    return ArticulatoryProgram.create(
        sample_count=3_200,
        larynx=LaryngealExcitationConfiguration(
            cycle_samples=80,
            open_samples=48,
            peak_volume_velocity_pcm=14_000,
        ),
        tract=VocalTractConfiguration(
            initial_section_area_mm2=(
                90, 110, 150, 210, 280, 360, 470, 620
            ),
            apex_section_area_mm2=(
                420, 90, 520, 120, 680, 160, 760, 240
            ),
            final_section_area_mm2=(
                90, 110, 150, 210, 280, 360, 470, 620
            ),
            radiation_load_area_mm2=900,
            wall_retention_ppm=990_000,
        ),
    )


def _system(
    key: bytes = KEY,
) -> tuple[
    ArticulatorySelfVocalMotorOwner,
    EmbodimentWorldAuthority,
    object,
]:
    owner = ArticulatorySelfVocalMotorOwner(
        authority_key=key,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id=f"prepared-emission-{key.hex()[:8]}",
            max_programs=2,
            max_state_bytes=64 * 1024,
        ),
    )
    program = owner.admit_program(_program())
    synthesis = owner.synthesize(
        program_id=program.program_id,
        source_time_start=Fraction(0),
    )
    world = EmbodimentWorldAuthority(
        authority_key=b"prepared-articulatory-world-test-key"
    )
    return owner, world, synthesis


def _preverified_commit(owner, world, prepared):
    preverified = owner.preverify_generated_emission_commit(
        prepared,
        world_authority=world,
    )
    owner.verify_preverified_generated_emission_commit(
        preverified,
        world_authority=world,
    )
    with owner.preverified_generated_emission_transaction(
        preverified,
        world_authority=world,
    ) as commit:
        return commit()


def test_prepare_is_physically_pure_and_discard_releases_without_claim():
    owner, world, synthesis = _system()
    world_before = world.observation_snapshot()
    recent_before = world.recent_applied_receipts()
    owner_before = owner.snapshot_encoded()

    prepared = owner.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=world,
        causal_intent_receipt_sha256=INTENT,
    )

    assert isinstance(prepared, PreparedArticulatoryGeneratedEmission)
    assert not isinstance(prepared, ArticulatoryGeneratedEmission)
    assert not hasattr(prepared, "emission_receipt")
    assert hashlib.sha256(prepared.pcm_s16le).hexdigest() == (
        prepared.payload()["pcm_sha256"]
    )
    owner.verify_prepared_generated_emission(
        prepared,
        world_authority=world,
    )
    assert world.observation_snapshot() == world_before
    assert world.recent_applied_receipts() == recent_before
    assert owner.snapshot_encoded() == owner_before

    owner.discard_prepared_generated_emission(
        prepared,
        world_authority=world,
    )
    assert world.observation_snapshot() == world_before
    with pytest.raises(ValueError, match="changed custody"):
        owner.preverify_generated_emission_commit(
            prepared,
            world_authority=world,
        )


def test_preverified_transaction_is_exactly_once_final_world_commit():
    owner, world, synthesis = _system()
    before = world.observation_snapshot()
    prepared = owner.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=world,
        causal_intent_receipt_sha256=INTENT,
    )
    preverified = owner.preverify_generated_emission_commit(
        prepared,
        world_authority=world,
    )
    with owner.preverified_generated_emission_transaction(
        preverified,
        world_authority=world,
    ) as commit:
        result = commit()
        with pytest.raises(AssertionError, match="not live"):
            commit()

    assert result.execution_receipt.before == before
    assert result.execution_receipt.after.revision == before.revision + 1
    assert world.observation_snapshot() == result.execution_receipt.after
    assert world.recent_applied_receipts()[-1] is result.execution_receipt
    assert result.emission_receipt.authority_receipt_sha256 == (
        prepared.prospective_emission_receipt_sha256
    )
    owner.verify_generated_emission(result, world_authority=world)


def test_prospective_receipt_is_complete_before_world_visibility(monkeypatch):
    owner, world, synthesis = _system()
    signed_domains = []
    original_sign = module._sign
    original_commit = world.commit_prepared_action
    world_swapped = False

    def observed_sign(key, domain, value):
        if world_swapped:
            raise AssertionError("receipt signing occurred after world swap")
        signed_domains.append(domain)
        return original_sign(key, domain, value)

    def observed_commit(prepared):
        nonlocal world_swapped
        result = original_commit(prepared)
        world_swapped = True
        return result

    monkeypatch.setattr(module, "_sign", observed_sign)
    monkeypatch.setattr(world, "commit_prepared_action", observed_commit)
    prepared = owner.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=world,
        causal_intent_receipt_sha256=INTENT,
    )
    prospective = prepared.prospective_emission_receipt_sha256
    result = _preverified_commit(owner, world, prepared)

    assert module._GENERATED_EMISSION_DOMAIN in signed_domains
    assert result.emission_receipt.authority_receipt_sha256 == prospective


def test_crossed_owner_world_and_tampered_capability_fail_closed():
    owner, world, synthesis = _system()
    prepared = owner.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=world,
        causal_intent_receipt_sha256=INTENT,
    )
    other_owner, other_world, _ = _system(
        b"other-prepared-articulatory-owner-key"
    )

    with pytest.raises(ValueError, match="changed custody"):
        other_owner.preverify_generated_emission_commit(
            prepared,
            world_authority=world,
        )
    with pytest.raises(ValueError, match="changed custody"):
        owner.preverify_generated_emission_commit(
            prepared,
            world_authority=other_world,
        )
    changed = replace(
        prepared,
        preparation_receipt_sha256="0" * 64,
    )
    with pytest.raises(ValueError, match="changed custody"):
        owner.preverify_generated_emission_commit(
            changed,
            world_authority=world,
        )
    owner.discard_prepared_generated_emission(
        prepared,
        world_authority=world,
    )


def test_failed_preverified_commit_remains_discardable(monkeypatch):
    owner, world, synthesis = _system()
    before = world.observation_snapshot()
    prepared = owner.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=world,
        causal_intent_receipt_sha256=INTENT,
    )
    preverified = owner.preverify_generated_emission_commit(
        prepared,
        world_authority=world,
    )

    def fail_commit(_prepared):
        raise RuntimeError("injected commit failure")

    monkeypatch.setattr(world, "commit_prepared_action", fail_commit)
    with pytest.raises(RuntimeError, match="injected commit failure"):
        with owner.preverified_generated_emission_transaction(
            preverified,
            world_authority=world,
        ) as commit:
            commit()
    assert world.observation_snapshot() == before
    owner.discard_prepared_generated_emission(
        prepared,
        world_authority=world,
    )


def test_direct_world_commit_convenience_surfaces_are_absent():
    owner, _world, _synthesis = _system()
    assert not hasattr(owner, "commit_prepared_generated_emission")
    assert not hasattr(owner, "execute_synthesis")
