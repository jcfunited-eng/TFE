"""Adapter: mint one designated "live-instant" scene-code registration per
port from a real live :class:`~dsf_ai_service.glew_runtime.story_chemistry.
StoryPhysicalBoundaryEvent`, so that event can pass ``story_native_replay.py``'s
``MountedAuthenticatedClosedStoryBoundary.verify()`` and flow into
``recall_story_episode_archive.create_recall_story_episode`` -- without
loosening that check and without fabricating any sensory content.

The precise incompatibility this module closes
--------------------------------------------------------------------------
``story_native_replay.py``'s ``MountedAuthenticatedClosedStoryBoundary.verify()``
(lines 542-545) hard-enforces, for every mounted port::

    if observation.signed_native_flux != port.flux_for_code(port.base_raw_code):
        raise ReceiptError("story boundary flux differs from mounted base raw code")

``base_raw_code`` is a fixed integer baked into a ``StorySensorPortAuthority``
at mount time, and ``flux_for_code`` is that authority's own fixed
``flux_at_code_zero + physical_quantum * raw_code`` law -- not derived from a
live reading.  A genuinely continuous live sensory value (from
``six_sense_boundary_owner.observe_six_sense_boundary``) has essentially zero
chance of exactly equaling a pre-chosen, arbitrary ``flux_at_code_zero``.

Investigated directly (not assumed) before writing any code here
--------------------------------------------------------------------------
* ``sensor_port_authority_mount.py``'s own module docstring already
  identifies the entire "integer raw scene code" system (``scene_coordinate_
  id``, ``base_raw_code``, ``minimum_raw_code``, ``maximum_raw_code``,
  ``physical_quantum``, ``flux_at_code_zero``) as having "no corresponding
  concept anywhere in ``SignedStoryChemistryManifest``" -- i.e. it is not a
  chemistry fact, it is a discrete, author-designated "which scene is this"
  label bolted on top of the shared chemistry manifest specifically so
  ``physical_l6_tangents.enumerate_native_replay_cases`` can walk to nearby
  *integer* codes and compute L6 tangent rows for a controlled counterfactual
  perturbation (``NativeReplayCaseKind.SENSOR_ADJACENT_CODE``).  Every real
  construction path for this type found in this repository (this module's own
  sibling ``sensor_port_authority_mount.py``, every ``story_native_replay``
  test fixture, and ``real_end_to_end_recall_pipeline.py``'s own
  ``_mount_real_sensor_port``) picks ``base_raw_code``/``flux_at_code_zero``
  as hand-chosen literals for one authored "scene", with a genuinely wide
  ``[minimum_raw_code, maximum_raw_code]`` band of *hypothetical* nearby
  codes around it -- confirming this system was designed around discrete,
  author-designated resting scenes, not continuously sampled live readings.
* ``physical_l6_tangents.enumerate_native_replay_cases`` (confirmed by direct
  reading, not assumed) only ever perturbs a port's own code by exactly
  ``+-1`` and silently skips any candidate that falls outside
  ``[minimum_code, maximum_code]`` -- it raises nothing, and produces zero
  ``SENSOR_ADJACENT_CODE`` cases, when ``minimum_code == base_code ==
  maximum_code``.  A single-point code range is therefore an entirely legal
  registration under this system's own existing rules: it just honestly
  declares "no admissible adjacent scene exists for this registration",
  which is exactly true of one live instant that was never authored as a
  discrete scene with real neighbours.
* ``recall_story_episode_archive.create_recall_story_episode`` only ever
  admits a ``NativeReplayCaseKind.BASE`` execution ("counterfactual replay
  cannot enter lived episode memory") and, per direct reading of
  ``ArchivedSensoryEvidenceBinding``/``RecallStoryEpisode`` and their own
  ``verify()``/``resolve()`` logic, never stores or compares
  ``scene_coordinate_id``/``base_raw_code``/``flux_for_code`` at all -- the
  archive's own real identity is the frozen-kernel evidence's receipted
  digests (``lane_id``, ``port_id``, ``evidence_id``,
  ``evidence_receipt_sha256``, ``raw_record_sha256``).  The scene-code system
  is therefore only a *gate* this instant's boundary must honestly pass
  through on its way into the frozen L0-L4 kernel; it is not part of what
  gets recalled.
* ``sight_boundary.py``/``sound_boundary.py``/``somatic_boundary.py``
  (confirmed directly) already derive every one of their observations'
  ``native_flux_unit`` from the exact same
  ``story_chemistry.SignedStoryChemistryManifest`` port's
  ``native_signal_unit`` that ``sensor_port_authority_mount
  .mount_story_sensor_port_authority`` also derives its authority's
  ``native_flux_unit`` from -- so a ``StorySensorPortAuthority`` minted here
  against ``observation.port_id``'s own manifest port is guaranteed to carry
  a matching ``native_flux_unit``, with no separate derivation needed.

The genuine, honest fix this module implements
--------------------------------------------------------------------------
For each real observation already present in a real, self-verifying
``StoryPhysicalBoundaryEvent`` (produced by
``six_sense_boundary_owner.observe_six_sense_boundary``), this module mints
one ``StorySensorPortAuthority`` via the existing, unmodified
``sensor_port_authority_mount.mount_story_sensor_port_authority`` where::

    base_raw_code = minimum_raw_code = maximum_raw_code = 0
    flux_at_code_zero = observation.signed_native_flux
    boundary_source_authority_receipt_sha256 = observation.observation_receipt_sha256

That is: THIS live instant is registered as its own designated "scene code
zero", honestly, because ``flux_for_code(0) == flux_at_code_zero ==
observation.signed_native_flux`` by construction -- an exact identity, not an
approximation or a loosened check.  No adjacent code is claimed to exist for
it (a true statement: nothing elsewhere in this codebase designates a
"neighbouring" live moment for an instant that was never authored as a
discrete scene), so ``physical_quantum`` is never actually multiplied by
anything but zero in any produced flux -- callers must still supply a real
positive ``Fraction`` for it (the type's own invariant demands one), but its
specific value is provably inert for a registration built this way, exactly
the kind of thing this module documents rather than pretends is meaningful.
``boundary_source_authority_receipt_sha256`` is grounded, for the first time
in this codebase, in something genuinely real: the very observation the
registration exists to describe (``sensor_port_authority_mount.py``'s own
docstring left this field unresolved because "no production authority
anywhere yet could supply it" -- the live six-sense boundary owner this
module adapts *is* that production authority now).

What this module deliberately does NOT claim to fix
--------------------------------------------------------------------------
This closes exactly the ``flux_for_code`` exact-match incompatibility the
governing investigation identified -- nothing more.  It does not attempt to
reconcile Step 4's own separately-mounted field topology
(``real_experience_learning_pipeline.py``, via
``six_lane_runtime_mount.mount_support_domain``/
``mount_resonance_graph_and_operator``) with a distinct topology built around
these minted authorities; that is the separate, larger "two disjoint
five-sense sensory subsystems" gap ``real_end_to_end_recall_pipeline.py``'s
own module docstring already documents and explicitly scopes out. It also
does not attempt to make one minted ``MountedStoryNativeReplayProfile``
reusable, unchanged, across many different live instants: because
``flux_at_code_zero`` is anchored to one specific instant's real flux, a
profile built from these authorities is only genuinely valid for the boundary
event that flux was drawn from. Archiving a second, later live instant
honestly requires minting a second set of authorities (and therefore a
distinct ``profile_binding_sha256``) from that instant's own real flux --
this module does not paper over that architectural cost, it names it.
"""

from __future__ import annotations

from fractions import Fraction

from .model import ReceiptError, ReceiptRecord, ReceiptRegistry, receipt_sha256
from .sensor_port_authority_mount import mount_story_sensor_port_authority
from .story_chemistry import (
    SignedStoryChemistryManifest,
    StoryPhysicalBoundaryEvent,
    StoryPhysicalBoundaryObservation,
)
from .story_native_replay import StorySensorPortAuthority


def _extend_receipt_registry(
    registry: ReceiptRegistry, *payloads: bytes
) -> ReceiptRegistry:
    """Append-only registry merge; identical in spirit to every sibling
    module's own private copy (``story_native_replay._extend_payloads``,
    ``sensor_port_authority_mount._extend_receipt_registry``,
    ``story_chemistry._extend_registry``): a digest already mounted with
    identical bytes is a no-op, a collision with different bytes fails
    closed. Duplicated locally rather than imported so this file has no
    import-time dependency on a sibling module under concurrent edit.
    """

    merged: dict[str, bytes] = {
        record.digest: record.payload for record in registry.records
    }
    for payload in payloads:
        if not isinstance(payload, bytes) or not payload:
            raise ReceiptError(
                "live boundary episode adapter received an empty receipt payload"
            )
        digest = receipt_sha256(payload)
        existing = merged.get(digest)
        if existing is not None and existing != payload:
            raise ReceiptError(
                "live boundary episode adapter receipt digest collides with "
                "different payload bytes"
            )
        merged[digest] = payload
    return ReceiptRegistry(
        registry.profile_binding_sha256,
        tuple(ReceiptRecord(digest, merged[digest]) for digest in sorted(merged)),
    )


def mint_live_boundary_as_episode_scene_authority(
    *,
    boundary_event: StoryPhysicalBoundaryEvent,
    manifest: SignedStoryChemistryManifest,
    receipt_registry: ReceiptRegistry,
    signal_offset: Fraction,
    signal_per_native_flux: Fraction,
    response_growth: Fraction,
    natural_decay: Fraction,
    phase_kappa: Fraction,
    physical_quantum: Fraction,
    source_epoch: str,
    port_kind: str,
    signal_physical_unit: str,
) -> tuple[tuple[StorySensorPortAuthority, ...], ReceiptRegistry]:
    """Mint one real ``StorySensorPortAuthority`` per port named in
    ``boundary_event``, each one honestly registering that port's own real
    observed flux this instant as scene "code zero", with no admissible
    adjacent code claimed.

    ``boundary_event`` must be an already-real, already-verifying
    ``StoryPhysicalBoundaryEvent`` -- typically the direct output of
    ``six_sense_boundary_owner.observe_six_sense_boundary``. It is
    independently re-verified here (``boundary_event.verify()``) rather than
    trusted on the caller's word.

    ``manifest`` must be the same already-mounted ``SignedStoryChemistryManifest``
    (``StoryChemistryRuntime.manifest``) the boundary event's own observations
    were translated against -- exactly what
    ``sensor_port_authority_mount.mount_story_sensor_port_authority`` requires
    of its own ``manifest`` argument, and for the identical reason: ``lane``,
    ``story_port_id``, ``field_port_id``, and ``native_flux_unit`` are derived
    from it, never accepted as independent inputs that could silently
    disagree.

    ``receipt_registry`` must already carry the manifest's own authenticated
    static receipts (for example a mounted ``StoryChemistryRuntime
    .receipt_registry.records``) -- the same precondition
    ``mount_story_sensor_port_authority`` already documents and enforces via
    ``chemistry_port.kernel_binding.verify(receipt_registry)`` failing closed
    otherwise.

    ``signal_offset``, ``signal_per_native_flux``, ``response_growth``,
    ``natural_decay``, ``phase_kappa``, ``source_epoch``, ``port_kind``,
    ``signal_physical_unit``, and ``physical_quantum`` are exactly the fields
    ``sensor_port_authority_mount.py`` already found no real, derivable
    grounding for anywhere in this codebase (see that module's docstring);
    this adapter invents no new grounding for them either and accepts them as
    mandatory, unguessed caller parameters with no default, for the same
    reason. ``physical_quantum`` in particular is provably never multiplied
    by anything but zero for a registration this function builds (its
    ``minimum_raw_code``/``maximum_raw_code``/``base_raw_code`` are always
    ``0``), but a real positive ``Fraction`` is still required by
    ``StorySensorPortAuthority``'s own invariant, so it remains an explicit
    caller decision rather than a silently invented constant.

    Returns one ``StorySensorPortAuthority`` per observation in
    ``boundary_event`` (in the same canonical port-id order the event's own
    observations already carry -- ``StoryPhysicalBoundaryEvent.verify()``
    already requires that order to be unique and sorted), plus the receipt
    registry extended with every payload minted along the way. Each returned
    authority satisfies, by construction and without any loosened check::

        authority.flux_for_code(authority.base_raw_code) == observation.signed_native_flux

    so a ``MountedAuthenticatedClosedStoryBoundary`` built from
    ``boundary_event`` against a profile mounting these authorities passes
    ``.verify()`` genuinely.
    """

    if not isinstance(boundary_event, StoryPhysicalBoundaryEvent):
        raise ReceiptError(
            "live boundary episode adapter requires a typed boundary event"
        )
    boundary_event.verify()
    if not isinstance(manifest, SignedStoryChemistryManifest):
        raise ReceiptError(
            "live boundary episode adapter requires an authenticated story "
            "chemistry manifest"
        )

    registry = receipt_registry
    authorities: list[StorySensorPortAuthority] = []
    for observation in boundary_event.observations:
        if not isinstance(observation, StoryPhysicalBoundaryObservation):
            raise ReceiptError(
                "live boundary episode adapter received an untyped observation"
            )
        registry = _extend_receipt_registry(
            registry,
            observation.provenance_receipt_payload,
            observation.observation_receipt_payload,
        )
        authority, registry = mount_story_sensor_port_authority(
            manifest=manifest,
            story_port_id=observation.port_id,
            scene_coordinate_id=(
                f"{boundary_event.event_id}:{observation.port_id}:live-instant"
            ),
            base_raw_code=0,
            minimum_raw_code=0,
            maximum_raw_code=0,
            flux_at_code_zero=observation.signed_native_flux,
            physical_quantum=physical_quantum,
            signal_offset=signal_offset,
            signal_per_native_flux=signal_per_native_flux,
            response_growth=response_growth,
            natural_decay=natural_decay,
            phase_kappa=phase_kappa,
            source_epoch=source_epoch,
            port_kind=port_kind,
            signal_physical_unit=signal_physical_unit,
            boundary_source_authority_receipt_sha256=(
                observation.observation_receipt_sha256
            ),
            receipt_registry=registry,
        )
        authorities.append(authority)

    ordered = tuple(sorted(authorities, key=lambda value: value.story_port_id))
    return ordered, registry


__all__ = ("mint_live_boundary_as_episode_scene_authority",)
