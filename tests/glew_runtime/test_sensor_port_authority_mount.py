"""Tests for :mod:`dsf_ai_service.glew_runtime.sensor_port_authority_mount`.

Covers: a valid mount + verify against a real, authenticated
``SignedStoryChemistryManifest``; rejection of an unmounted/tampered input;
and a proof that the derived fields (``lane``, ``story_port_id``,
``field_port_id``, ``native_flux_unit``) genuinely track each real mounted
chemistry port rather than being disguised constants -- the only fields this
module found a genuine, derivable relationship for (see the module
docstring for the full field-by-field grounding analysis).
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from dsf_ai_service.glew_runtime.l6 import L6Lane
from dsf_ai_service.glew_runtime.model import ReceiptError, ReceiptRecord, ReceiptRegistry
from dsf_ai_service.glew_runtime.sensor_port_authority_mount import (
    mount_story_sensor_port_authority,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    mount_story_chemistry,
)


FIXTURE = (
    Path(__file__).parent / "fixtures" / "candidate_story_chemistry_manifest.json"
)
CANDIDATE_KEY = b"transparent candidate test key; never production authority"
CANDIDATE_KEY_ID = "candidate-test-hmac-key-not-production"


def _mounted_runtime():
    mounted = mount_story_chemistry(
        manifest_envelope_payload=FIXTURE.read_bytes(),
        trusted_authentication_key=CANDIDATE_KEY,
        expected_key_id=CANDIDATE_KEY_ID,
    )
    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    return mounted.runtime


def _mandatory_fields(*, boundary_source_authority_receipt_sha256: str) -> dict:
    """The fields this module found no real grounding for anywhere in the
    codebase (see the module docstring); values here are pure test
    convenience, not a claim of physical meaning.
    """

    return dict(
        scene_coordinate_id="scene-under-test",
        base_raw_code=0,
        minimum_raw_code=-2,
        maximum_raw_code=2,
        flux_at_code_zero=Fraction(1, 5),
        physical_quantum=Fraction(1, 20),
        signal_offset=Fraction(0),
        signal_per_native_flux=Fraction(1),
        response_growth=Fraction(1, 2),
        natural_decay=Fraction(1, 8),
        phase_kappa=Fraction(1, 3),
        source_epoch="test-source-epoch-0",
        port_kind="authenticated_virtual_story_boundary",
        signal_physical_unit="dimensionless_story_response",
        boundary_source_authority_receipt_sha256=(
            boundary_source_authority_receipt_sha256
        ),
    )


def _mounted_boundary_source_receipt(registry: ReceiptRegistry) -> tuple[str, ReceiptRegistry]:
    """Mount one arbitrary, opaque 'boundary source authority' receipt so a
    valid mount has something real to resolve for
    ``boundary_source_authority_receipt_sha256`` (this authority itself is
    out of this module's scope -- see the module docstring's note that it
    depends on the still-unbuilt live six-sense boundary owner).
    """

    from dsf_ai_service.glew_runtime.model import receipt_sha256

    payload = b'{"schema":"test.boundary_source_authority.v1"}'
    digest = receipt_sha256(payload)
    merged = {record.digest: record.payload for record in registry.records}
    merged[digest] = payload
    return digest, ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(key, merged[key]) for key in sorted(merged)),
    )


def test_valid_mount_derives_lane_and_unit_and_verifies():
    runtime = _mounted_runtime()
    boundary_digest, registry = _mounted_boundary_source_receipt(
        runtime.receipt_registry
    )
    chemistry_port = runtime.manifest.port("story-vision.native-port-0")

    authority, extended_registry = mount_story_sensor_port_authority(
        manifest=runtime.manifest,
        story_port_id="story-vision.native-port-0",
        receipt_registry=registry,
        **_mandatory_fields(boundary_source_authority_receipt_sha256=boundary_digest),
    )

    assert authority.lane is L6Lane.SIGHT
    assert authority.story_port_id == "story-vision.native-port-0"
    assert authority.field_port_id == "story-vision.native-port-0"
    assert authority.native_flux_unit == chemistry_port.native_signal_unit
    # Independently re-verify against the returned, extended registry --
    # mount_story_sensor_port_authority already calls authority.verify()
    # internally, but a fresh call here proves it is genuinely re-checkable,
    # not merely unraised the first time.
    authority.verify(extended_registry)


def test_unmounted_story_port_id_is_rejected():
    runtime = _mounted_runtime()
    boundary_digest, registry = _mounted_boundary_source_receipt(
        runtime.receipt_registry
    )
    with pytest.raises(ReceiptError):
        mount_story_sensor_port_authority(
            manifest=runtime.manifest,
            story_port_id="story-does-not-exist.native-port-0",
            receipt_registry=registry,
            **_mandatory_fields(
                boundary_source_authority_receipt_sha256=boundary_digest
            ),
        )


def test_unresolvable_boundary_source_receipt_is_rejected():
    runtime = _mounted_runtime()
    # A syntactically valid sha256 that was never actually mounted anywhere.
    unmounted_digest = "0" * 64
    with pytest.raises(ReceiptError):
        mount_story_sensor_port_authority(
            manifest=runtime.manifest,
            story_port_id="story-vision.native-port-0",
            receipt_registry=runtime.receipt_registry,
            **_mandatory_fields(
                boundary_source_authority_receipt_sha256=unmounted_digest
            ),
        )


def test_inverted_raw_code_bounds_are_rejected():
    runtime = _mounted_runtime()
    boundary_digest, registry = _mounted_boundary_source_receipt(
        runtime.receipt_registry
    )
    fields = _mandatory_fields(
        boundary_source_authority_receipt_sha256=boundary_digest
    )
    fields["minimum_raw_code"] = 5
    fields["maximum_raw_code"] = -5
    with pytest.raises(ReceiptError):
        mount_story_sensor_port_authority(
            manifest=runtime.manifest,
            story_port_id="story-vision.native-port-0",
            receipt_registry=registry,
            **fields,
        )


def test_tampered_authority_object_fails_verification():
    """After a valid mount, mutate the returned authority object itself
    (its receipt digest still names the *original* mounted bytes) and prove
    ``.verify()`` catches the divergence between the tampered object's
    fields and the immutable receipt it claims -- rather than silently
    trusting the object's own in-memory state.
    """

    runtime = _mounted_runtime()
    boundary_digest, registry = _mounted_boundary_source_receipt(
        runtime.receipt_registry
    )
    authority, extended_registry = mount_story_sensor_port_authority(
        manifest=runtime.manifest,
        story_port_id="story-vision.native-port-0",
        receipt_registry=registry,
        **_mandatory_fields(boundary_source_authority_receipt_sha256=boundary_digest),
    )

    # Confirm the untampered object still verifies before tampering.
    authority.verify(extended_registry)

    tampered = replace(authority, scene_coordinate_id="a-different-scene-entirely")
    assert tampered.authority_receipt_sha256 == authority.authority_receipt_sha256

    with pytest.raises(ReceiptError):
        tampered.verify(extended_registry)


def test_derived_fields_genuinely_track_each_real_mounted_port_not_a_constant():
    """Prove ``lane``/``native_flux_unit`` are read from the manifest, not a
    disguised fixed value: mount every one of the five real chemistry ports
    and confirm each authority's derived fields exactly match that port's
    own ``kernel_binding.lane_id``/``native_signal_unit`` -- and that these
    values genuinely differ from port to port.
    """

    runtime = _mounted_runtime()
    boundary_digest, registry = _mounted_boundary_source_receipt(
        runtime.receipt_registry
    )

    observed_lanes = set()
    observed_units = set()
    for chemistry_port in runtime.manifest.ports:
        authority, registry = mount_story_sensor_port_authority(
            manifest=runtime.manifest,
            story_port_id=chemistry_port.port_id,
            receipt_registry=registry,
            **_mandatory_fields(
                boundary_source_authority_receipt_sha256=boundary_digest
            ),
        )
        assert authority.lane.value == chemistry_port.kernel_binding.lane_id
        assert authority.native_flux_unit == chemistry_port.native_signal_unit
        assert authority.story_port_id == chemistry_port.port_id
        assert authority.field_port_id == chemistry_port.port_id
        observed_lanes.add(authority.lane.value)
        observed_units.add(authority.native_flux_unit)

    # Five real senses, five distinct lanes, five distinct native units --
    # if this function were secretly hardcoding a single value, these sets
    # would collapse to size 1.
    assert len(runtime.manifest.ports) == 5
    assert observed_lanes == {"sound", "smell", "taste", "touch", "sight"}
    assert len(observed_units) == 5
