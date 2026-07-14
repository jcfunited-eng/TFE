"""UNRATIFIED PLACEHOLDER sensor-calibration + bootstrap literals for the
live ``ProductionCleanConversationEngine`` cutover.

    ================================================================
    STATUS = "unratified_placeholder"   --  READ THIS FIRST
    ================================================================

Every concrete value in this module (sensor-port calibration literals such as
``signal_offset`` / ``signal_per_native_flux`` / ``response_growth`` /
``natural_decay`` / ``phase_kappa`` / ``physical_quantum`` / ``flux_at_code_zero``,
the six-lane ids / edge sets / precision-bit ceilings, and the genesis identity
triple / HMAC key-ids below) is a **deliberately-chosen placeholder**, NOT a
real, derived-from-data physical calibration.

Nothing anywhere in this codebase has ever computed a real, ratified value for
these. ``six_lane_runtime_mount.py`` and ``production_runtime_bootstrap.py``
both document this exact gap in their own module docstrings: every module that
needs these treats them as required, unguessed caller parameters precisely
because no ratified production source exists. The values here are copied,
shape-for-shape, from the two fixtures already proven to construct a running
engine end-to-end:

    * ``tests/glew_runtime/test_production_runtime_bootstrap.py``
      ``_six_lane_runtime_parameters()``
    * ``tests/glew_runtime/test_story_native_replay.py`` ``_sensor_port()``

They are known to *work* (472+ tests pass on them); they are NOT known to be
*physically correct*. They exist only so a real engine can be constructed and
seeded with two genesis scenes. When a real sensor calibration is derived, it
replaces this file wholesale; this file must never be mistaken for that.

This module deliberately imports only real production ``glew_runtime`` modules
(never any ``tests/`` module), so importing it in the live app pulls in no test
code. It reproduces the fixtures' literal shapes locally instead.

The two HMAC *keys themselves* are NOT here (a placeholder secret would be a
security hole): they are loaded at app startup from named environment variables
populated from AWS Secrets Manager -- see ``dsf_ai_service/app.py``'s GLEW
wiring. Only the non-secret key *ids* live here.
"""

from __future__ import annotations

import json
from fractions import Fraction

from .l6 import L6Lane
from .model import receipt_sha256
from .operators import RequiredEdge
from .production_runtime_bootstrap import SixLaneRuntimeBootstrapParameters
from .story_chemistry import (
    StoryChemistryStatus,
    mount_packaged_production_story_chemistry,
)
from .story_native_replay import (
    StorySensorPortAuthority,
    story_sensor_port_authority_receipt_payload,
)

# Prominent, machine-checkable honesty marker (asserted by the wiring/tests).
STATUS = "unratified_placeholder"

# --- stable identity / engine constants (placeholder, but MUST stay fixed) ---
# genesis_identity must be a canonical RFC-4122 UUIDv4; genesis_generation_uuid
# only has to be a canonical UUID (see generation_identity._validate_*). Both
# are placeholders, but they anchor the persisted generation store: once a
# generation has been persisted under them, changing either would make the
# restore path reject the store as a mixed generation. They are fixed here
# precisely so they are stable across restarts (a random-per-boot identity
# could never restore a prior generation).
ENGINE_ID = "guala-glew-production-conversation-engine-v1"
GENESIS_IDENTITY_UUID = "6fc05d04-1512-421f-a2a0-a0a394d408a6"
GENESIS_GENERATION_UUID = "9fed7503-1ede-4d21-92b8-c680097688da"

# Non-secret key ids paired with the two runtime HMAC secrets (the secret bytes
# come from the environment; see app.py). These label which key signed a
# checkpoint / chemistry envelope; they are not themselves secret.
CHEMISTRY_HMAC_KEY_ID = "gualaloom-glew-chemistry-hmac-prod-v1"
CHECKPOINT_HMAC_KEY_ID = "gualaloom-glew-checkpoint-hmac-prod-v1"

# --- per-lane sensor calibration literals (placeholder) ----------------------
# Mirrors tests/glew_runtime/test_story_native_replay.py's own BASE_FLUX/QUANTUM.
_BASE_FLUX = {
    "sound": Fraction(1, 5),
    "smell": Fraction(1, 6),
    "taste": Fraction(-1, 7),
    "touch": Fraction(2, 9),
    "sight": Fraction(1, 4),
}
_QUANTUM = {
    "sound": Fraction(1, 20),
    "smell": Fraction(1, 24),
    "taste": Fraction(1, 28),
    "touch": Fraction(1, 18),
    "sight": Fraction(1, 16),
}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _build_sensor_port(port) -> tuple[StorySensorPortAuthority, bytes, bytes]:
    """Reproduce test_story_native_replay._sensor_port with production imports
    only. Returns (authority, authority_payload, source_payload) exactly as the
    proven fixture does."""

    lane = L6Lane(port.kernel_binding.lane_id)
    source = _canonical_bytes(
        {
            "port_id": port.port_id,
            "schema": "glew.production_sensor_calibration_unratified.source_authority.v1",
        }
    )
    values = dict(
        lane=lane,
        story_port_id=port.port_id,
        field_port_id=port.port_id,
        scene_coordinate_id=f"scene-{port.port_id}",
        base_raw_code=0,
        minimum_raw_code=-1,
        maximum_raw_code=1,
        flux_at_code_zero=_BASE_FLUX[lane.value],
        physical_quantum=_QUANTUM[lane.value],
        native_flux_unit=port.native_signal_unit,
        signal_offset=Fraction(0),
        signal_per_native_flux=Fraction(1),
        response_growth=Fraction(1, 2),
        natural_decay=Fraction(1, 8),
        phase_kappa=Fraction(1, 3),
        source_epoch="candidate-five-sense-story-epoch-0",
        port_kind="authenticated_virtual_story_boundary",
        signal_physical_unit="dimensionless_story_response",
        boundary_source_authority_receipt_sha256=receipt_sha256(source),
    )
    payload = story_sensor_port_authority_receipt_payload(**values)
    return (
        StorySensorPortAuthority(
            **values,
            authority_receipt_sha256=receipt_sha256(payload),
        ),
        payload,
        source,
    )


def production_six_lane_runtime_parameters(
    *,
    engine_id: str,
    chemistry_authentication_key: bytes,
    chemistry_key_id: str,
) -> SixLaneRuntimeBootstrapParameters:
    """Build the (placeholder) ``SixLaneRuntimeBootstrapParameters`` for the
    live engine. Mounts a preliminary real story-chemistry runtime (from the
    ratified packaged profile) purely to read its manifest ports, exactly as
    the proven bootstrap fixture does, then derives the sensor-port authorities
    and lane edges from them.

    STATUS: unratified_placeholder -- see this module's docstring.
    """

    preliminary = mount_packaged_production_story_chemistry(
        runtime_authentication_key=chemistry_authentication_key,
        runtime_key_id=chemistry_key_id,
    )
    if preliminary.status is not StoryChemistryStatus.MOUNTED or preliminary.runtime is None:
        raise RuntimeError(
            f"production sensor calibration could not mount preliminary story "
            f"chemistry runtime: {preliminary.reason}"
        )

    mounted_ports = tuple(
        _build_sensor_port(value) for value in preliminary.runtime.manifest.ports
    )
    sensor_ports = tuple(value[0] for value in mounted_ports)
    sensor_port_receipt_payloads = tuple(
        payload for value in mounted_ports for payload in (value[1], value[2])
    )
    five_sense_keys = tuple(value.field_key for value in sensor_ports)
    five_sense_edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(five_sense_keys[:-1], five_sense_keys[1:], strict=True)
    )
    language_port_id = f"{engine_id}-typed-interface"
    six_lane_keys = (("language", language_port_id), *five_sense_keys)
    six_lane_edges = tuple(
        RequiredEdge(left, right)
        for left, right in zip(six_lane_keys[:-1], six_lane_keys[1:], strict=True)
    )

    return SixLaneRuntimeBootstrapParameters(
        sensor_ports=sensor_ports,
        sensor_port_receipt_payloads=sensor_port_receipt_payloads,
        five_sense_topology_id=f"{engine_id}-five-sense-topology",
        causal_grid_id=f"{engine_id}-causal-grid",
        causal_timestamps=tuple(Fraction(index) for index in range(1, 6)),
        causal_positive_weights=tuple(Fraction(1) for _ in range(5)),
        five_sense_support_domain_id=f"{engine_id}-five-sense-support",
        five_sense_resonance_graph_id=f"{engine_id}-five-sense-resonance",
        five_sense_resonance_required_edges=five_sense_edges,
        resonance_operator_id=f"{engine_id}-resonance-operator",
        resonance_precision_bits=128,
        story_replay_profile_id=f"{engine_id}-story-replay-profile",
        story_replay_provider_id=f"{engine_id}-story-replay-provider",
        story_replay_kernel_adapter_id=f"{engine_id}-kernel-adapter",
        story_replay_kernel_adapter_profile_payload=(
            b'{"schema":"glew.production_sensor_calibration_unratified.kernel_adapter.v1"}'
        ),
        typed_language_adapter_id=f"{engine_id}-typed-adapter",
        typed_language_interface_id=language_port_id,
        typed_language_phase_calibration_id=f"{engine_id}-typed-phase",
        typed_language_phase_kappa=Fraction(1, 7),
        typed_language_derivation_payload=(
            b'{"schema":"glew.production_sensor_calibration_unratified.typed_derivation.v1"}'
        ),
        language_port_id=language_port_id,
        six_lane_topology_id=f"{engine_id}-six-lane-topology",
        six_lane_support_domain_id=f"{engine_id}-six-lane-support",
        six_lane_resonance_graph_id=f"{engine_id}-six-lane-resonance",
        six_lane_resonance_required_edges=six_lane_edges,
        expression_precision_authority_id=f"{engine_id}-expression-precision",
        expression_maximum_precision_bits=4096,
        pre_window_state_id=f"{engine_id}-pre-window",
        pre_window_memory_state_payload=(
            b'{"schema":"glew.production_sensor_calibration_unratified.memory_state.v1"}'
        ),
        pre_window_l6_state_payload=(
            b'{"schema":"glew.production_sensor_calibration_unratified.l6_state.v1"}'
        ),
        l5_governance_profile_id=f"{engine_id}-l5-profile",
        basin_profile_id=f"{engine_id}-basin-profile",
        basin_physical_profile_payload=(
            b'{"schema":"glew.production_sensor_calibration_unratified.physical_profile.v1"}'
        ),
        basin_hbar=Fraction(1),
        basin_source_time_unit=f"{engine_id}-structural-time",
        basin_max_connected_component_dimension=1,
        basin_field_precision_bits=128,
    )


__all__ = (
    "STATUS",
    "ENGINE_ID",
    "GENESIS_IDENTITY_UUID",
    "GENESIS_GENERATION_UUID",
    "CHEMISTRY_HMAC_KEY_ID",
    "CHECKPOINT_HMAC_KEY_ID",
    "production_six_lane_runtime_parameters",
)
