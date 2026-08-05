from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from dsf_ai_service.substrate.embodiment_world import (
    AdvancePhysicalTimeCommand,
    EmbodimentWorldAuthority,
    ObjectOpticalSurface,
    _base_objects,
    _canonical,
    encode_command,
)
from dsf_ai_service.substrate.physical_internal_body_state import (
    InternalBodyEvolutionRequest,
    InternalQuantityChange,
    _canonical as body_canonical,
    create_embodiment_proprioceptive_internal_body_authority,
)


FIXTURE_ROOT = (
    Path(__file__).parents[1] / "native" / "guala_core" / "tests" / "fixtures"
)


def _fixture(name: str) -> bytes:
    return bytes.fromhex((FIXTURE_ROOT / name).read_text(encoding="ascii"))


def test_native_world_body_fixtures_are_exact_python_authority_outputs() -> None:
    world_key = bytes([0x11]) * 32
    body_key = bytes([0x22]) * 32
    surface = ObjectOpticalSurface(
        columns=2,
        rows=1,
        palette_reflectance_ppm=(
            (0, 100_000, 200_000, 300_000, 400_000, 500_000),
            (1_000_000, 900_000, 800_000, 700_000, 600_000, 500_000),
        ),
        cell_palette_indices=(0, 1),
    )
    physical_object = replace(
        _base_objects()[0],
        object_id="W1-object-é-\x01",
        optical_surface=surface,
    )
    world = EmbodimentWorldAuthority(
        authority_key=world_key,
        initial_objects=(physical_object,),
    )
    current_world = world.observation_snapshot()
    self_body = next(
        item for item in current_world.bodies
        if item.body_id == current_world.self_body_id
    )
    body = create_embodiment_proprioceptive_internal_body_authority(
        authority_key=body_key,
        world_observation_receipt_sha256=(
            world.physical_body_mount_observation_receipt()
        ),
        position_x_mm=Fraction(self_body.pose.position.x),
        position_y_mm=Fraction(self_body.pose.position.y),
        position_z_mm=Fraction(self_body.pose.position.z),
        supported_load_grams=Fraction(0),
        neurochemical_references=(),
    )
    current_body = body.state

    world.execute_port_command(
        port_id="guala.embodiment.w1",
        command_payload=encode_command(AdvancePhysicalTimeCommand(1_000)),
        causal_intent_receipt_sha256="aa" * 32,
        expected_revision=0,
    )
    successor_world = world.observation_snapshot()
    prepared = body.prepare_evolution(InternalBodyEvolutionRequest(
        source_kind="world-observation",
        physical_source_receipt_sha256=(
            successor_world.authority_receipt_sha256
        ),
        source_time_start=Fraction(0),
        source_time_end=Fraction(1, 1_000),
        expected_state_receipt_sha256=(
            current_body.authority_receipt_sha256
        ),
        changes=(
            InternalQuantityChange(
                "quantity:proprioception:position_x",
                Fraction(0),
            ),
        ),
    ))
    body.commit_prepared(prepared)

    expected = {
        "world_observation_v6.hex": _canonical(
            current_world._canonical_record()
        ),
        "world_observation_v6_successor.hex": _canonical(
            successor_world._canonical_record()
        ),
        "body_manifest_v1.hex": body_canonical(body.manifest.record()),
        "body_state_v1.hex": body_canonical(current_body.record()),
        "body_state_v1_successor.hex": body_canonical(body.state.record()),
        "canonical_unicode_control_negative.hex": _canonical({
            "a": "é\x01",
            "c0_inside": "x\x1cy",
            "n": -7,
            "z": "\u2028",
        }),
    }
    assert {name: _fixture(name) for name in expected} == expected
