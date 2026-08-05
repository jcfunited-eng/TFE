from __future__ import annotations

import inspect
import json
from dataclasses import replace
from fractions import Fraction

import pytest

from dsf_ai_service.glew_runtime.global_uf import DSF_FIELD_ORDER
from dsf_ai_service.substrate.articulatory_self_vocal_motor import (
    ArticulatoryMotorResourceProfile,
    ArticulatorySelfVocalMotorOwner,
)
from dsf_ai_service.substrate.auditory_recurrent_motif import (
    AuditoryMotifResourceProfile,
    AuditoryRecurrentMotifOwner,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_VOCAL_SAMPLE_COUNT,
    VOCAL_SAMPLE_RATE_HZ,
    EmbodimentWorldAuthority,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.fresh_articulatory_self_acoustic_custody import (
    FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID,
    FreshArticulatorySelfAcousticCustodyAuthority,
    FreshArticulatorySelfAcousticCustodyProfile,
)
from dsf_ai_service.substrate.settled_experience_custody import (
    SettledExperienceCustodyAuthority,
    SettledExperienceCustodyProfile,
)
from dsf_ai_service.substrate.w1_binaural_auditory_l5 import (
    W1BinauralAuditoryL5Owner,
)
from dsf_ai_service.substrate.w1_self_acoustic_propagation import (
    W1SelfAcousticPropagationAuthority,
)
from tests.test_articulatory_self_vocal_motor import _program


ARTICULATORY_KEY = b"fresh-articulatory-custody-motor-authority-key"
WORLD_KEY = b"fresh-articulatory-custody-world-authority-key"
ACOUSTIC_KEY = b"fresh-articulatory-custody-acoustic-authority-key"
SETTLED_KEY = b"fresh-articulatory-custody-settled-authority-key"
PHYSICAL_KEY = b"fresh-articulatory-custody-physical-authority-key"
CUSTODY_KEY = b"fresh-articulatory-custody-receipt-authority-key"


def _profile(
    *,
    max_full_field_tuples: int = 4_000_000,
    max_receipt_bytes: int = 64 * 1024,
) -> FreshArticulatorySelfAcousticCustodyProfile:
    return FreshArticulatorySelfAcousticCustodyProfile.create(
        profile_id="fresh-generated-self-acoustic-test",
        max_full_field_tuples=max_full_field_tuples,
        max_receipt_bytes=max_receipt_bytes,
    )


@pytest.fixture(scope="module")
def fresh_occurrence():
    world = EmbodimentWorldAuthority(authority_key=WORLD_KEY)
    articulatory = ArticulatorySelfVocalMotorOwner(
        authority_key=ARTICULATORY_KEY,
        resource_profile=ArticulatoryMotorResourceProfile.create(
            profile_id="fresh-custody-articulatory-programs",
            max_programs=2,
            max_state_bytes=256 * 1024,
        ),
    )
    program = articulatory.admit_program(_program(16_000))

    acoustic = W1SelfAcousticPropagationAuthority(
        authority_key=ACOUSTIC_KEY,
        world_authority=world,
        causal_owner=ExactCausalExperienceOwner(
            on_settlement=lambda _settlement: None,
            log_event=lambda *_args, **_kwargs: None,
        ),
        binaural_l5_owner=W1BinauralAuditoryL5Owner(),
        binaural_motif_owner=AuditoryRecurrentMotifOwner(
            AuditoryMotifResourceProfile.create(
                profile_id="fresh-custody-binaural-recurrent-q",
                ear_count=2,
                max_motif_neurons=24_192,
                max_pending_experiences=8,
                max_work_cells_per_observation=8_000_000,
                max_exact_fraction_text_bytes=4_096,
                encoded_state_allocation_bytes=128 * 1024 * 1024,
            ),
            ear_ids=("left", "right"),
        ),
    )
    before = world.observation_snapshot()
    synthesis = articulatory.synthesize(
        program_id=program.program_id,
        source_time_start=Fraction(
            before.revision * MAX_VOCAL_SAMPLE_COUNT,
            VOCAL_SAMPLE_RATE_HZ,
        ),
    )
    prepared_emission = articulatory.prepare_generated_emission(
        synthesis=synthesis,
        world_authority=world,
        causal_intent_receipt_sha256="a" * 64,
    )
    prepared_mount = acoustic.prepare_articulatory(
        prepared_emission,
        articulatory_owner=articulatory,
    )
    emission, mount, _undo = acoustic.commit_prepared_articulatory(
        prepared_mount
    )
    settled = SettledExperienceCustodyAuthority(
        authority_key=SETTLED_KEY,
        w1_physical_authority_key=PHYSICAL_KEY,
        world_authority_key=WORLD_KEY,
        w1_self_acoustic_authority_key=ACOUSTIC_KEY,
        profile=SettledExperienceCustodyProfile.create(
            profile_id="fresh-generated-self-acoustic-settled",
            max_children=4,
            max_snapshot_bytes=128 * 1024 * 1024,
        ),
    )
    settled_value = settled.admit(
        mount,
        emission.execution_receipt,
    )
    capability = settled.issue_child(
        FRESH_ARTICULATORY_SELF_ACOUSTIC_CONSUMER_ID
    )
    profile = _profile()
    authority = FreshArticulatorySelfAcousticCustodyAuthority(
        authority_key=CUSTODY_KEY,
        profile=profile,
        articulatory_owner=articulatory,
        world_authority=world,
        acoustic_authority=acoustic,
    )
    return {
        "acoustic": acoustic,
        "articulatory": articulatory,
        "authority": authority,
        "capability": capability,
        "emission": emission,
        "mount": mount,
        "profile": profile,
        "settled": settled,
        "settled_value": settled_value,
        "synthesis": synthesis,
        "world": world,
    }


def _seal(values):
    return values["authority"].seal(
        synthesis=values["synthesis"],
        emission=values["emission"],
        acoustic_mount=values["mount"],
        settled_custody_authority=values["settled"],
        settled_custody_capability=values["capability"],
    )


def test_seals_one_fresh_full_field_occurrence_without_retained_media(
    fresh_occurrence,
) -> None:
    receipt = _seal(fresh_occurrence)
    fresh_occurrence["authority"].verify_occurrence(
        receipt,
        synthesis=fresh_occurrence["synthesis"],
        emission=fresh_occurrence["emission"],
        acoustic_mount=fresh_occurrence["mount"],
        settled_custody_authority=fresh_occurrence["settled"],
        settled_custody_capability=fresh_occurrence["capability"],
    )

    settlement = fresh_occurrence["mount"].causal_settlement
    expected_counts = []
    for interpretation in settlement.interpretations:
        if interpretation.state != "observed":
            continue
        count = 0
        for substream in interpretation.substreams:
            for field_tuple in substream.field_tuples:
                count += 1
                assert tuple(
                    name for name, _value in field_tuple.fields
                ) == DSF_FIELD_ORDER
        expected_counts.append((interpretation.sense, count))

    assert receipt.observed_senses == (
        "body",
        "sight",
        "sound",
        "touch",
    )
    assert receipt.full_dsf_tuple_counts == tuple(
        sorted(expected_counts)
    )
    assert receipt.full_dsf_tuple_count == sum(
        count for _sense, count in expected_counts
    )
    assert receipt.source_occurrence_id == (
        fresh_occurrence["settled_value"].source_occurrence_id
    )
    assert receipt.program_id == (
        fresh_occurrence["synthesis"].program.program_id
    )
    assert fresh_occurrence["authority"].status() == {
        "full_field_authority": True,
        "max_full_field_tuples": 4_000_000,
        "max_receipt_bytes": 64 * 1024,
        "profile_receipt_sha256": (
            fresh_occurrence["profile"].authority_receipt_sha256
        ),
        "retained_pcm_bytes": 0,
        "retained_receipts": 0,
        "schema": (
            "guala.fresh_articulatory_self_acoustic_custody.receipt.v1"
        ),
        "stateful": False,
    }

    record = receipt.record()
    encoded = json.dumps(record, sort_keys=True)
    for forbidden in (
        "bridge",
        "exemplar",
        "label",
        "pcm",
        "score",
        "target",
        "thing_id",
        "transcript",
    ):
        assert forbidden not in encoded.lower()
    assert not any(
        isinstance(value, (bytes, bytearray, memoryview))
        for value in record.values()
    )


def test_receipt_is_cold_verifiable_without_retained_state(
    fresh_occurrence,
) -> None:
    receipt = _seal(fresh_occurrence)
    cold = FreshArticulatorySelfAcousticCustodyAuthority(
        authority_key=CUSTODY_KEY,
        profile=fresh_occurrence["profile"],
        articulatory_owner=fresh_occurrence["articulatory"],
        world_authority=fresh_occurrence["world"],
        acoustic_authority=fresh_occurrence["acoustic"],
    )

    cold.verify_receipt(receipt)
    assert cold.status()["retained_receipts"] == 0
    assert cold.status()["retained_pcm_bytes"] == 0

    with pytest.raises(
        ValueError,
        match="receipt authority changed",
    ):
        cold.verify_receipt(
            replace(receipt, program_id="0" * 64)
        )


def test_rejects_crossed_synthesis_and_wrong_consumer_capability(
    fresh_occurrence,
) -> None:
    crossed_synthesis = fresh_occurrence["articulatory"].synthesize(
        program_id=fresh_occurrence["synthesis"].program.program_id,
        source_time_start=Fraction(99),
    )
    with pytest.raises(
        ValueError,
        match="changed synthesis occurrence",
    ):
        fresh_occurrence["authority"].seal(
            synthesis=crossed_synthesis,
            emission=fresh_occurrence["emission"],
            acoustic_mount=fresh_occurrence["mount"],
            settled_custody_authority=fresh_occurrence["settled"],
            settled_custody_capability=fresh_occurrence["capability"],
        )

    wrong_capability = fresh_occurrence["settled"].issue_child(
        "not-fresh-articulatory-custody"
    )
    with pytest.raises(
        ValueError,
        match="requires its child capability",
    ):
        fresh_occurrence["authority"].seal(
            synthesis=fresh_occurrence["synthesis"],
            emission=fresh_occurrence["emission"],
            acoustic_mount=fresh_occurrence["mount"],
            settled_custody_authority=fresh_occurrence["settled"],
            settled_custody_capability=wrong_capability,
        )


def test_full_field_and_receipt_capacities_fail_closed(
    fresh_occurrence,
) -> None:
    receipt = _seal(fresh_occurrence)
    tuple_limited = FreshArticulatorySelfAcousticCustodyAuthority(
        authority_key=CUSTODY_KEY,
        profile=_profile(
            max_full_field_tuples=receipt.full_dsf_tuple_count - 1,
        ),
        articulatory_owner=fresh_occurrence["articulatory"],
        world_authority=fresh_occurrence["world"],
        acoustic_authority=fresh_occurrence["acoustic"],
    )
    with pytest.raises(
        RuntimeError,
        match="tuple capacity exhausted",
    ):
        tuple_limited.seal(
            synthesis=fresh_occurrence["synthesis"],
            emission=fresh_occurrence["emission"],
            acoustic_mount=fresh_occurrence["mount"],
            settled_custody_authority=fresh_occurrence["settled"],
            settled_custody_capability=fresh_occurrence["capability"],
        )

    receipt_bytes = len(
        json.dumps(
            receipt.record(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    byte_limited = FreshArticulatorySelfAcousticCustodyAuthority(
        authority_key=CUSTODY_KEY,
        profile=_profile(
            max_receipt_bytes=receipt_bytes - 1,
        ),
        articulatory_owner=fresh_occurrence["articulatory"],
        world_authority=fresh_occurrence["world"],
        acoustic_authority=fresh_occurrence["acoustic"],
    )
    with pytest.raises(
        ValueError,
        match="receipt authority changed",
    ):
        byte_limited.seal(
            synthesis=fresh_occurrence["synthesis"],
            emission=fresh_occurrence["emission"],
            acoustic_mount=fresh_occurrence["mount"],
            settled_custody_authority=fresh_occurrence["settled"],
            settled_custody_capability=fresh_occurrence["capability"],
        )


def test_public_api_cannot_accept_semantic_or_replay_authority() -> None:
    parameters = set(
        inspect.signature(
            FreshArticulatorySelfAcousticCustodyAuthority.seal
        ).parameters
    )
    assert parameters == {
        "self",
        "synthesis",
        "emission",
        "acoustic_mount",
        "settled_custody_authority",
        "settled_custody_capability",
    }
    assert parameters.isdisjoint({
        "bridge",
        "exemplar",
        "label",
        "pcm",
        "pcm_motor_owner",
        "score",
        "target",
        "thing_id",
        "transcript",
    })
