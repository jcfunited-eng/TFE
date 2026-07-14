"""Mounted six-lane runtime -- production constructor for
``StorySensorPortAuthority`` (governing native-replay/L6-tangent "response
law": raw-code perturbation bounds, physical quantum, drive law, growth/
decay, and phase kappa).

This module closes exactly one gap identified while building
``dsf_ai_service/glew_runtime/six_lane_runtime_mount.py``'s
``mount_story_sensor_states``: that function's own docstring records that
``StorySensorPortAuthority`` "encodes an entirely separate native-replay
physical response law (response growth/decay, phase kappa, raw-code
bounds, ...) that has no corresponding field anywhere in
``SignedStoryChemistryManifest``'s receptor-kinetics ports and so cannot be
derived from ``manifest`` alone," and that no production constructor for it
existed anywhere in the repository -- only ad-hoc test literals (for example
``tests/glew_runtime/test_story_native_replay.py``'s ``_sensor_port``
helper).

Investigated directly against ``story_native_replay.py`` and
``story_chemistry.py`` (not assumed from any prior framing):

Genuine, mechanistically-required derivations from an already-mounted
``SignedStoryChemistryManifest`` port
---------------------------------------------------------------------------
* ``lane`` -- ``story_chemistry.py``'s per-port ``kernel_binding.lane_id`` is
  the same lane identity ``mount_field_topology``
  (``six_lane_runtime_mount.py`` lines 449-455) already uses to build every
  ``PortFiber`` in the mounted ``MountedFieldTopology``, and
  ``MountedStoryNativeReplayProfile.verify`` (``story_native_replay.py``
  lines 456-459) *requires* every mounted port's ``field_key`` (``(lane,
  field_port_id)``) to exactly equal the topology's own ordered fiber keys.
  A ``StorySensorPortAuthority`` whose ``lane`` disagreed with the
  chemistry manifest's own ``kernel_binding.lane_id`` would therefore always
  fail that coverage check once mounted into a real profile built over the
  same manifest. This is not a convenience default; it is derived directly
  and is not exposed as a separate caller parameter at all, removing the
  possibility of a caller supplying an inconsistent value.
* ``story_port_id`` / ``field_port_id`` -- for the identical reason, the
  established production topology-building path (``mount_field_topology``)
  always sets a fiber's ``port_id`` to the chemistry manifest's own
  ``port_id``, and ``story_native_replay.py`` looks up chemistry state by
  ``story_port_id`` (``StoryChemistryRuntime.state``,
  ``SignedStoryChemistryManifest.port``). Both are therefore derived as the
  same value -- the caller's own already-mounted manifest port's
  ``port_id`` -- rather than accepted as independent, potentially
  inconsistent inputs.
* ``native_flux_unit`` -- ``story_chemistry.py``'s ``_evolve_one_observation``
  (line 1458) hard-fails every single causal interval
  (``"story observation unit differs from mounted port authority"``,
  propagating to ``StoryChemistryStatus.UNKNOWN`` and then to
  ``execute_story_native_replay``'s ``ReceiptError("story chemistry replay
  unresolved: ...")``) unless the boundary observation's unit -- which
  ``story_native_replay.py``'s own ``_derived_story_observation`` always sets
  from ``port.native_flux_unit`` -- exactly equals the chemistry manifest's
  own per-port ``native_signal_unit``. This is a hard mechanistic
  requirement of the real replay path, not a numerically convenient
  coincidence, so it is derived directly here rather than accepted as a
  caller parameter that could silently diverge.

Fields with NO real grounding found anywhere in this codebase (left as
mandatory, unguessed caller parameters; no default is invented)
---------------------------------------------------------------------------
* ``scene_coordinate_id``, ``base_raw_code``, ``minimum_raw_code``,
  ``maximum_raw_code``, ``physical_quantum``, ``flux_at_code_zero`` -- the
  entire "integer raw scene code" system (an integer scene parameter mapped
  to a native flux value, whose admissible adjacent range bounds the finite-
  secant perturbations ``physical_l6_tangents.enumerate_native_replay_cases``
  enumerates for L6 tangent-row computation) has no corresponding concept
  anywhere in ``SignedStoryChemistryManifest``. That system belongs to the
  governing spec's still-unbuilt "live six-sense boundary owner" (see
  ``docs/GL-SPC-GLEW-AE-CONVERSATION-REARCHITECTURE-HANDOFF-20260713-v1.md``
  section 9.1: "This is the first missing production builder"). No chemistry
  rate, unit, or receptor state constrains what a legitimate code range,
  quantum, or zero-code flux baseline should be for any given port.
* ``signal_offset``, ``signal_per_native_flux``, ``response_growth``,
  ``natural_decay``, ``phase_kappa`` -- confirmed independently (not merely
  quoted from the sibling module's docstring): ``story_native_replay.py``'s
  ``_execute_streams`` (lines 895-917) computes the causal "signal" sample
  entirely from these five fields via
  ``drive = signal_offset + signal_per_native_flux * flux`` and
  ``signal = retained_signal + response_growth * (drive - retained_signal)
  - natural_decay * retained_signal``, completely independent of the real
  receptor-kinetics evolution (``evolve_story_chemistry_event``, driven by
  the manifest's ``activation_susceptibility`` and its three
  ``A_to_R_deactivation`` / ``A_to_D_desensitization`` / ``D_to_R_recovery``
  rates) that produces the *separate* ``relevance`` value for the same
  interval. No code anywhere cross-checks the two. They are not even
  dimensionally comparable as they stand: the chemistry manifest's rates are
  genuine inverse-time-unit physical rates (their own receipt schema is
  literally ``"dimension": "inverse_mounted_time_unit"``), while
  ``response_growth``/``natural_decay`` are applied as fixed per-step
  blending coefficients with **no** scaling by the causal-grid interval
  ``delta`` at all (only ``phase_kappa`` is scaled by ``delta``, in
  ``phase = phase_prev + phase_kappa * signal * delta``). Rescaling a real
  per-time rate into one of these per-step coefficients would require
  inventing an unstated time-discretization assumption (for example
  ``1 - exp(-rate * delta)``) that does not exist anywhere in this
  repository. This is exactly the same open item ``mount_story_sensor_states``
  already flagged; independent investigation confirms it rather than
  resolving it.
* ``source_epoch`` -- an ordinary externally-decided session/generation
  identifier, the same concept ``EvidenceStream``, ``coupling.py``,
  ``language.py``, and ``field.py`` already use elsewhere. There is no
  per-port "epoch" field anywhere in ``SignedStoryChemistryManifest``, so
  this is simply supplied by the runtime/caller for the turn being mounted
  -- an ordinary construction input (like ``mount_causal_grid``'s
  ``grid_id``), not a physics gap.
* ``port_kind``, ``signal_physical_unit`` -- descriptive identifiers with no
  canonical value enforced anywhere for *this* authority. A different,
  alternate chemistry-to-kernel bridge (``story_chemistry.build_story_frozen_
  kernel_inputs``, line 1837) hardcodes ``port_kind=
  "independent_virtual_story_native_port"`` and ``physical_unit=
  port.native_signal_unit`` directly, but that path bypasses
  ``StorySensorPortAuthority`` entirely and is not cited anywhere as binding
  on this one -- copying its literal would be exactly the "plausible-looking
  fabrication" the governing instruction warns against. One real structural
  fact was confirmed: the "signal" this authority's response law produces is
  always a dimensionless value in ``[-1,1]`` (``MountedStorySensorState.
  __post_init__``'s own ``-1 <= retained_signal <= 1`` invariant, and the
  identical ``"normalized_signal_domain": "[-1,1]"`` convention hardcoded in
  both ``story_kernel_binding_authority_receipt_payload`` and this module's
  own ``native_response`` equation payload). That fact constrains the
  *value domain*, not a specific *string label*, so no label is derived from
  it here.
* ``boundary_source_authority_receipt_sha256`` -- depends entirely on the
  governing spec's still-unbuilt live six-sense boundary owner (section
  9.1); no production authority anywhere yet could supply it.

Composability
-------------
Mirrors ``six_lane_runtime_mount.py``'s "chain the registry" pattern exactly
(append-only merge; a digest already mounted with identical bytes is a
no-op, a collision with different bytes fails closed) via a private,
module-local ``_extend_receipt_registry``, the same independent-copy
convention every other module in this package already follows
(``story_native_replay.py``'s ``_extend_records``/``_extend_payloads``,
``story_chemistry.py``'s ``_extend_registry``,
``closed_experience.py``'s ``_extend_registry``,
``six_lane_runtime_mount.py``'s own ``extend_receipt_registry``) rather than
importing a shared helper from a sibling module under concurrent edit.
"""

from __future__ import annotations

from fractions import Fraction

from .l6 import L6Lane
from .model import (
    ReceiptError,
    ReceiptRecord,
    ReceiptRegistry,
    receipt_sha256,
)
from .story_chemistry import SignedStoryChemistryManifest
from .story_native_replay import (
    StorySensorPortAuthority,
    story_sensor_port_authority_receipt_payload,
)


def _extend_receipt_registry(
    registry: ReceiptRegistry, *payloads: bytes
) -> ReceiptRegistry:
    """Append-only registry merge; identical to the sibling module's
    ``extend_receipt_registry`` (``six_lane_runtime_mount.py``), duplicated
    here rather than imported so this file has no import-time dependency on
    a sibling module under concurrent, active edit.
    """

    merged: dict[str, bytes] = {record.digest: record.payload for record in registry.records}
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError("mounted receipt payload must be nonempty exact bytes")
        digest = receipt_sha256(payload)
        existing = merged.get(digest)
        if existing is not None and existing != payload:
            raise ReceiptError(
                "mounted receipt digest collides with different payload bytes"
            )
        merged[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(digest, merged[digest]) for digest in sorted(merged)),
    )


def mount_story_sensor_port_authority(
    *,
    manifest: SignedStoryChemistryManifest,
    story_port_id: str,
    scene_coordinate_id: str,
    base_raw_code: int,
    minimum_raw_code: int,
    maximum_raw_code: int,
    flux_at_code_zero: Fraction,
    physical_quantum: Fraction,
    signal_offset: Fraction,
    signal_per_native_flux: Fraction,
    response_growth: Fraction,
    natural_decay: Fraction,
    phase_kappa: Fraction,
    source_epoch: str,
    port_kind: str,
    signal_physical_unit: str,
    boundary_source_authority_receipt_sha256: str,
    receipt_registry: ReceiptRegistry,
) -> tuple[StorySensorPortAuthority, ReceiptRegistry]:
    """Mount and verify one :class:`StorySensorPortAuthority` for the
    already-mounted chemistry manifest port named by ``story_port_id``.

    ``lane``, the returned authority's ``story_port_id``, and
    ``field_port_id`` are never accepted as caller inputs: they are derived
    directly from ``manifest.port(story_port_id)``'s own ``kernel_binding``
    (see the module docstring for exactly why this is a mechanistic
    requirement, not a convenience default), so a caller cannot construct an
    authority whose lane/port identity silently disagrees with the manifest
    it is meant to replay against. ``native_flux_unit`` is likewise derived
    directly from the same chemistry port's ``native_signal_unit`` --
    supplying any other value would deterministically fail every interval of
    a real replay (``story_chemistry._evolve_one_observation``).

    Every other field named in the module docstring's second section
    (``scene_coordinate_id`` through
    ``boundary_source_authority_receipt_sha256``) is a mandatory,
    unguessed, caller-supplied parameter with no default: this function
    found no real, derivable relationship for any of them anywhere in this
    codebase. Callers ratifying real values for these -- in particular
    ``response_growth``/``natural_decay``/``phase_kappa`` and the raw-code
    system -- should treat that ratification as a separate, explicit
    decision, exactly as Stage 1's ``mount_resonance_graph_and_operator``
    left ``required_edges``/``precision_bits`` open rather than defaulting
    them.

    The caller must already have folded the manifest's authenticated static
    receipts (for example a mounted ``StoryChemistryRuntime.receipt_registry
    .records``) into ``receipt_registry`` before calling this function --
    mirroring exactly what ``mount_field_topology`` requires of its own
    ``manifest`` argument.
    """

    if not isinstance(manifest, SignedStoryChemistryManifest):
        raise ReceiptError(
            "story sensor port authority requires an authenticated story "
            "chemistry manifest"
        )
    chemistry_port = manifest.port(story_port_id)
    chemistry_port.kernel_binding.verify(receipt_registry)
    if chemistry_port.kernel_binding.port_id != chemistry_port.port_id:
        raise ReceiptError(
            "story chemistry port id disagrees with its own kernel binding"
        )
    try:
        lane = L6Lane(chemistry_port.kernel_binding.lane_id)
    except ValueError as exc:
        raise ReceiptError(
            "story chemistry port lane id is not a mounted L6 lane"
        ) from exc

    payload = story_sensor_port_authority_receipt_payload(
        lane=lane,
        story_port_id=chemistry_port.port_id,
        field_port_id=chemistry_port.port_id,
        scene_coordinate_id=scene_coordinate_id,
        base_raw_code=base_raw_code,
        minimum_raw_code=minimum_raw_code,
        maximum_raw_code=maximum_raw_code,
        flux_at_code_zero=flux_at_code_zero,
        physical_quantum=physical_quantum,
        native_flux_unit=chemistry_port.native_signal_unit,
        signal_offset=signal_offset,
        signal_per_native_flux=signal_per_native_flux,
        response_growth=response_growth,
        natural_decay=natural_decay,
        phase_kappa=phase_kappa,
        source_epoch=source_epoch,
        port_kind=port_kind,
        signal_physical_unit=signal_physical_unit,
        boundary_source_authority_receipt_sha256=(
            boundary_source_authority_receipt_sha256
        ),
    )
    registry = _extend_receipt_registry(receipt_registry, payload)
    authority = StorySensorPortAuthority(
        lane=lane,
        story_port_id=chemistry_port.port_id,
        field_port_id=chemistry_port.port_id,
        scene_coordinate_id=scene_coordinate_id,
        base_raw_code=base_raw_code,
        minimum_raw_code=minimum_raw_code,
        maximum_raw_code=maximum_raw_code,
        flux_at_code_zero=flux_at_code_zero,
        physical_quantum=physical_quantum,
        native_flux_unit=chemistry_port.native_signal_unit,
        signal_offset=signal_offset,
        signal_per_native_flux=signal_per_native_flux,
        response_growth=response_growth,
        natural_decay=natural_decay,
        phase_kappa=phase_kappa,
        source_epoch=source_epoch,
        port_kind=port_kind,
        signal_physical_unit=signal_physical_unit,
        boundary_source_authority_receipt_sha256=(
            boundary_source_authority_receipt_sha256
        ),
        authority_receipt_sha256=receipt_sha256(payload),
    )
    authority.verify(registry)
    return authority, registry


__all__ = (
    "mount_story_sensor_port_authority",
)
