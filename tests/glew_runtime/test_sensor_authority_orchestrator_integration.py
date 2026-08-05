"""Integration test proving the two independently-built Step 3 pieces
genuinely compose:

* ``dsf_ai_service/glew_runtime/sensor_port_authority_mount.py``'s
  ``mount_story_sensor_port_authority`` -- the real, substrate-true
  production constructor for ``StorySensorPortAuthority``.
* ``dsf_ai_service/glew_runtime/six_lane_runtime_mount.py``'s
  ``mount_six_lane_runtime`` -- the top-level orchestrator that *consumes* a
  tuple of ``StorySensorPortAuthority`` via its ``sensor_ports=`` parameter.

Until now, ``mount_six_lane_runtime``'s own end-to-end test
(``tests/glew_runtime/test_six_lane_runtime_mount.py::
_six_lane_runtime_kwargs``) built its ``sensor_ports`` tuple with an ad-hoc
test literal (``tests/glew_runtime/test_story_native_replay.py::
_sensor_port``), because no promoted production constructor existed yet when
that test was written. This test replaces that ad-hoc construction with the
real ``mount_story_sensor_port_authority`` call -- one call per real port of
the *same* candidate five-sense chemistry manifest
``_six_lane_runtime_kwargs`` itself mounts (same fixture bytes, same
authentication key/id, so the mounted manifest is bit-identical, exactly as
the suite's own
``test_mount_six_lane_runtime_construction_is_deterministic_across_cold_start_and_restart``
already proves for repeated mounts of this fixture) -- and feeds the
resulting real authorities into ``mount_six_lane_runtime`` alongside every
other already-proven-working parameter value, copied unchanged from
``_six_lane_runtime_kwargs``.

The five real port ids used here are cross-checked directly against
``dsf_ai_service/glew_runtime/profiles/production_virtual_story_chemistry_profile_v1.json``,
the real production 5-port chemistry manifest, to ground the claim that this
is testing the real 5-sense shape (auditory/smell/taste/touch/vision) and not
some other, differently-shaped fixture.

For the fields ``mount_story_sensor_port_authority`` itself documents as
having no real grounding anywhere in this codebase (``scene_coordinate_id``,
the raw-code system, the native-response coefficients, ``source_epoch``,
``port_kind``, ``signal_physical_unit``, and the boundary-source receipt),
this test reuses -- rather than invents -- the exact literal values
``tests/glew_runtime/test_sensor_port_authority_mount.py``'s own
``_mandatory_fields``/``_mounted_boundary_source_receipt`` helpers already
use successfully in that module's own passing tests.
"""

from __future__ import annotations

import json
from pathlib import Path

from dsf_ai_service.glew_runtime.l6 import L6Lane
from dsf_ai_service.glew_runtime.sensor_port_authority_mount import (
    mount_story_sensor_port_authority,
)
from dsf_ai_service.glew_runtime.six_lane_runtime_mount import (
    MountedSixLaneRuntime,
    mount_six_lane_runtime,
)
from dsf_ai_service.glew_runtime.story_chemistry import (
    StoryChemistryStatus,
    mount_story_chemistry,
)

from tests.glew_runtime.test_sensor_port_authority_mount import (
    _mandatory_fields,
    _mounted_boundary_source_receipt,
)
from tests.glew_runtime.test_six_lane_runtime_mount import _six_lane_runtime_kwargs


PRODUCTION_CHEMISTRY_PROFILE_PATH = (
    Path(__file__).resolve().parents[2]
    / "dsf_ai_service"
    / "glew_runtime"
    / "profiles"
    / "production_virtual_story_chemistry_profile_v1.json"
)


def _real_production_port_ids() -> tuple[str, ...]:
    """The real production 5-port chemistry manifest's own port ids, read
    directly from the packaged production profile -- used only to ground
    this test's claim that it exercises the real 5-sense shape, not to mount
    that file itself (mounting the packaged production profile requires a
    real production runtime secret via
    ``story_chemistry.mount_packaged_production_story_chemistry``, out of
    scope here; this test instead reuses the same candidate manifest
    ``_six_lane_runtime_kwargs`` already mounts, which authenticates with a
    transparent test key and carries the identical five port ids/lanes).
    """

    body = json.loads(PRODUCTION_CHEMISTRY_PROFILE_PATH.read_text())
    return tuple(port["port_id"] for port in body["ports"])


def _mount_real_sensor_ports_over_orchestrator_manifest():
    """Build a real tuple of ``StorySensorPortAuthority`` -- one per port of
    the exact chemistry manifest ``_six_lane_runtime_kwargs`` mounts -- via
    the real ``mount_story_sensor_port_authority`` constructor, plus the
    ``sensor_port_receipt_payloads`` ``mount_six_lane_runtime`` needs to
    re-derive the same registry state.

    Returns ``(kwargs, real_sensor_ports, story_runtime)`` where ``kwargs``
    is ready to pass straight to :func:`mount_six_lane_runtime`.
    """

    base_kwargs, _ad_hoc_sensor_ports = _six_lane_runtime_kwargs()

    mounted = mount_story_chemistry(
        manifest_envelope_payload=base_kwargs["story_chemistry_profile_bytes"],
        trusted_authentication_key=base_kwargs["story_chemistry_authentication_key"],
        expected_key_id=base_kwargs["story_chemistry_expected_key_id"],
    )
    assert mounted.status is StoryChemistryStatus.MOUNTED
    assert mounted.runtime is not None
    story_runtime = mounted.runtime

    boundary_digest, registry = _mounted_boundary_source_receipt(
        story_runtime.receipt_registry
    )
    base_digests = {record.digest for record in story_runtime.receipt_registry.records}

    real_sensor_ports = []
    for chemistry_port in story_runtime.manifest.ports:
        authority, registry = mount_story_sensor_port_authority(
            manifest=story_runtime.manifest,
            story_port_id=chemistry_port.port_id,
            receipt_registry=registry,
            **_mandatory_fields(
                boundary_source_authority_receipt_sha256=boundary_digest
            ),
        )
        real_sensor_ports.append(authority)
    real_sensor_ports = tuple(real_sensor_ports)

    # Everything mounted above beyond the story runtime's own registry (the
    # boundary-source receipt plus each real port's own authority receipt)
    # is exactly the set mount_six_lane_runtime needs handed to it as
    # sensor_port_receipt_payloads to re-derive the identical registry state
    # internally.
    sensor_port_receipt_payloads = tuple(
        record.payload for record in registry.records if record.digest not in base_digests
    )

    kwargs = dict(base_kwargs)
    kwargs["sensor_ports"] = real_sensor_ports
    kwargs["sensor_port_receipt_payloads"] = sensor_port_receipt_payloads
    return kwargs, real_sensor_ports, story_runtime


def test_real_sensor_port_authorities_are_built_over_the_real_five_production_ports():
    """Ground the manifest used: its five port ids are exactly the real
    production 5-port chemistry manifest's own port ids (same senses, same
    lanes), not a coincidentally similar but different shape.
    """

    _kwargs, real_sensor_ports, story_runtime = _mount_real_sensor_ports_over_orchestrator_manifest()

    assert len(real_sensor_ports) == 5
    assert {port.story_port_id for port in real_sensor_ports} == set(
        _real_production_port_ids()
    )
    assert {port.lane.value for port in real_sensor_ports} == {
        "sound",
        "smell",
        "taste",
        "touch",
        "sight",
    }
    # Each real authority's derived fields genuinely track its own real
    # chemistry port, not a disguised constant.
    for authority in real_sensor_ports:
        chemistry_port = story_runtime.manifest.port(authority.story_port_id)
        assert authority.lane.value == chemistry_port.kernel_binding.lane_id
        assert authority.field_port_id == chemistry_port.port_id
        assert authority.native_flux_unit == chemistry_port.native_signal_unit


def test_real_sensor_port_authorities_compose_with_the_six_lane_orchestrator():
    """The real end-to-end proof: real ``StorySensorPortAuthority`` values,
    built by the real production constructor over the same manifest the
    orchestrator's own test mounts, feed cleanly into
    ``mount_six_lane_runtime`` alongside every other already-proven parameter
    value -- producing a fully cross-verified thirteen-authority
    ``MountedSixLaneRuntime``.
    """

    kwargs, real_sensor_ports, story_runtime = _mount_real_sensor_ports_over_orchestrator_manifest()

    result = mount_six_lane_runtime(**kwargs)
    assert isinstance(result, MountedSixLaneRuntime)
    registry = result.receipt_registry

    # The orchestrator mounted the identical manifest content this test
    # mounted separately above -- proving this is the SAME real object
    # (bit-identical receipt), not two different manifests that merely look
    # alike.
    assert result.story_chemistry_runtime.manifest.receipt_sha256 == (
        story_runtime.manifest.receipt_sha256
    )

    # Every one of the thirteen named authorities independently re-verifies
    # against the SAME final registry.
    result.story_native_replay_profile.verify(registry)
    result.field_topology.verify(registry)
    assert len(result.field_topology.ordered_port_fibers) == 6
    assert {fiber.lane_id for fiber in result.field_topology.ordered_port_fibers} == {
        item.value for item in L6Lane
    }
    result.causal_grid.verify(registry)
    result.support_domain.verify(registry)
    result.resonance_graph.verify(registry)
    result.resonance_operator.verify(registry)
    assert len(result.sensor_states) == len(real_sensor_ports)
    for port, state in zip(real_sensor_ports, result.sensor_states, strict=True):
        state.verify(port=port, receipt_registry=registry)
    result.typed_language_kernel_binding.verify(registry)
    result.precision_authority.verify(registry)
    result.expression_mode_bank.verify(
        topology=result.field_topology, receipt_registry=registry
    )
    result.pre_window_state.verify(registry)
    result.l5_governance_profile.verify(result.field_topology, registry)
    result.story_global_uf_basin_profile.verify(
        story_profile=result.story_native_replay_profile,
        pre_window_state=result.pre_window_state,
        topology=result.field_topology,
        receipt_registry=registry,
    )

    # And each real sensor port authority built by the production
    # constructor still independently re-verifies against the final
    # orchestrator registry -- not merely the intermediate registry
    # mount_story_sensor_port_authority itself built it against.
    for port in real_sensor_ports:
        port.verify(registry)
