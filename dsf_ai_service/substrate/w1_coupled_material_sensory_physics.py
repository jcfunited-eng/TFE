"""World-owned material receptors for one signed physical occurrence.

Object material, body receptor geometry, air volume, portal transport, and
contact state are authenticated by :mod:`embodiment_world`. This module owns
no material inventory and performs no object-identity lookup policy. It only
transduces the exact before/after world edge into touch, smell, and taste
receptor quantities, then joins those quantities with sight, sound, and body
evidence from that same edge.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import isqrt

from dsf_ai_service.glew_runtime.native_sensory_full_field import (
    BuiltSixSenseFullField,
    NativeSensorySubstreamInput,
    build_transaction_owned_six_sense_full_field,
    declare_joint_source_occurrences,
)
from dsf_ai_service.glew_runtime.sensory_full_field_boundary import (
    NativeAxisCoordinate,
    PhysicalSense,
    SENSE_ORDER,
    SenseBoundaryState,
)
from dsf_ai_service.substrate.embodiment_world import (
    MAX_PHYSICAL_PPM,
    ODORANT_CHANNELS,
    TASTANT_CHANNELS,
    ActionExecutionReceipt,
    EmbodiedBody,
    EmbodiedObject,
    EmbodimentWorldAuthority,
    ObservationSnapshot,
    PhysicalRegion,
    PositionMM,
)
from dsf_ai_service.substrate.exact_causal_experience import (
    CausalExperienceSettlement,
    ExactCausalExperienceOwner,
)
from dsf_ai_service.substrate.exact_lattice_rotation import (
    rotate_lattice_offset,
)
from dsf_ai_service.substrate.w1_binaural_acoustic_physics import (
    W1EarAuditoryTransductionCustody,
    binaural_joint_units,
    binaural_sound_field_inputs,
)
from dsf_ai_service.substrate.w1_physical_receptors import (
    physical_receptor_joint_units,
    physical_receptor_substreams,
)


TOUCH_RECEPTOR_COUNT = 6


def _bounded_fraction(value: Fraction) -> Fraction:
    if value < -1:
        return Fraction(-1)
    if value > 1:
        return Fraction(1)
    return value


def _native_signal(
    *,
    sense: PhysicalSense,
    sensor_id: str,
    substream_id: str,
    topology_index: int,
    coordinates: tuple[NativeAxisCoordinate, ...],
    physical_quantity: str,
    physical_unit: str,
    values: tuple[Fraction, Fraction],
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> NativeSensorySubstreamInput:
    if (
        not isinstance(source_time_start, Fraction)
        or not isinstance(source_time_end, Fraction)
        or source_time_end <= source_time_start
    ):
        raise ValueError("material receptor interval must be exact and positive")
    bounded = tuple(_bounded_fraction(value) for value in values)
    interval = source_time_end - source_time_start
    return NativeSensorySubstreamInput(
        sense=sense,
        sensor_id=sensor_id,
        substream_id=substream_id,
        topology_index=topology_index,
        coordinates=coordinates,
        physical_quantity=physical_quantity,
        physical_unit=physical_unit,
        source_times=(
            source_time_start + interval * Fraction(1, 3),
            source_time_start + interval * Fraction(2, 3),
        ),
        normalized_signal=tuple(float(value) for value in bounded),
        phase_turns=(Fraction(0), Fraction(0)),
    )


def _self_body(observation: ObservationSnapshot) -> EmbodiedBody:
    matches = tuple(
        body
        for body in observation.bodies
        if body.body_id == observation.self_body_id
    )
    if len(matches) != 1:
        raise ValueError("world observation has no unique embodied self")
    return matches[0]


def _body_fixed_position(
    body: EmbodiedBody,
    offset: PositionMM,
) -> PositionMM:
    dx, dy = rotate_lattice_offset(
        offset.x,
        offset.y,
        body.pose.heading_millidegrees,
    )
    return PositionMM(
        body.pose.position.x + dx,
        body.pose.position.y + dy,
        body.pose.position.z + offset.z,
    )


def _region_at_point(
    observation: ObservationSnapshot,
    position: PositionMM,
) -> PhysicalRegion | None:
    matches = tuple(
        region
        for region in observation.regions
        if (
            region.bounds.minimum.x <= position.x <= region.bounds.maximum.x
            and region.bounds.minimum.y <= position.y <= region.bounds.maximum.y
            and region.bounds.minimum.z <= position.z <= region.bounds.maximum.z
        )
    )
    return matches[0] if len(matches) == 1 else None


def _object_for_contact(
    observation: ObservationSnapshot,
    body: EmbodiedBody,
) -> EmbodiedObject | None:
    contact = body.active_contact
    if contact is None:
        return None
    matches = tuple(
        item
        for item in observation.objects
        if item.object_id == contact.object_id
    )
    if len(matches) != 1:
        raise ValueError("signed body contact lost its physical object")
    item = matches[0]
    if item.material is None:
        raise ValueError("signed body contact lost material state")
    if contact.kind == "oral" and (
        body.held_object_id != item.object_id
        or item.held_by_body_id != body.body_id
    ):
        raise ValueError("signed oral contact lost reciprocal custody")
    return item


def _touch_values(
    observation: ObservationSnapshot,
) -> tuple[Fraction, ...]:
    body = _self_body(observation)
    geometry = body.receptor_geometry
    if geometry is None:
        raise ValueError("touch receptor geometry is unavailable")
    item = _object_for_contact(observation, body)
    if item is None:
        return (Fraction(0),) * TOUCH_RECEPTOR_COUNT
    contact = body.active_contact
    material = item.material
    assert contact is not None
    assert material is not None
    contact_fraction = Fraction(
        contact.contact_patch_square_mm,
        item.radius_mm * item.radius_mm,
    )
    temperature_fraction = (
        Fraction(
            2
            * (
                material.surface_temperature_millikelvin
                - geometry.touch_temperature_min_millikelvin
            ),
            geometry.touch_temperature_max_millikelvin
            - geometry.touch_temperature_min_millikelvin,
        )
        - 1
    )
    return (
        Fraction(1),
        _bounded_fraction(
            Fraction(item.mass_grams, geometry.touch_mass_span_grams)
        ),
        _bounded_fraction(temperature_fraction),
        Fraction(material.compliance_ppm, MAX_PHYSICAL_PPM),
        _bounded_fraction(
            Fraction(
                material.roughness_micrometers,
                geometry.touch_roughness_span_micrometers,
            )
        ),
        Fraction(material.moisture_ppm, MAX_PHYSICAL_PPM)
        * contact_fraction,
    )


def _smell_values(
    observation: ObservationSnapshot,
) -> tuple[Fraction, ...]:
    body = _self_body(observation)
    geometry = body.receptor_geometry
    if geometry is None:
        raise ValueError("olfactory receptor geometry is unavailable")
    position = _body_fixed_position(
        body,
        geometry.olfactory_offset_mm,
    )
    region = (
        _region_at_point(observation, position)
        if position is not None
        else None
    )
    if region is None or region.air is None:
        raise ValueError("signed olfactory air volume is unavailable")
    # THE AIR IN A ROOM IS NOT ONE NUMBER. Dividing the room's whole odorant
    # mass by the room's whole volume says every corner of a kitchen smells
    # exactly as much of the apple as the spot the apple is sitting in, which
    # is false and — measured — leaves an organism with nothing whatever to
    # follow: a perfectly flat field cannot be walked up.
    #
    # What is missing is the near field. Mass released by a thing has not
    # finished mixing: it is denser close to its source and tends to the
    # room's average far away. So each source's share of the room's mass
    # (its share of the channel's release into that room) is taken as
    # occupying the sphere of air between it and her nose, and the room's
    # well-mixed value is the floor beneath that rather than the whole story.
    #
    # Nothing here is a new constant. Masses, release rates, volumes and
    # distances are all already declared by her world; this only stops
    # pretending the mixing is instantaneous and perfect.
    sources = tuple(
        item
        for item in observation.objects
        if item.material is not None
        and item.position is not None
        and _region_at_point(observation, item.position) is region
    )
    values: list[Fraction] = []
    for channel, (mass, saturation) in enumerate(
        zip(
            region.air.odorant_mass_nanograms,
            geometry.odorant_saturation_nanograms_per_cubic_meter,
        )
    ):
        well_mixed = Fraction(
            mass * 1_000_000_000, region.air.volume_cubic_mm * saturation
        )
        released = sum(
            item.material.odorant_release_nanograms_per_second[channel]
            for item in sources
        )
        strongest = well_mixed
        if released > 0 and mass > 0:
            for item in sources:
                rate = item.material.odorant_release_nanograms_per_second[
                    channel
                ]
                if rate <= 0:
                    continue
                distance = _distance_mm(position, item.position)
                # Her nose cannot be closer to a thing than its own surface,
                # and a source is never denser than undiluted.
                span = max(distance, item.radius_mm)
                near_volume = 4 * span * span * span
                if near_volume <= 0:
                    continue
                share = Fraction(mass * rate, released)
                near = Fraction(share * 1_000_000_000, near_volume * saturation)
                if near > strongest:
                    strongest = near
        values.append(_bounded_fraction(strongest))
    return tuple(values)


def _distance_mm(left: object, right: object) -> int:
    return isqrt(
        (left.x - right.x) ** 2
        + (left.y - right.y) ** 2
        + (left.z - right.z) ** 2
    )


def _taste_values(
    observation: ObservationSnapshot,
) -> tuple[Fraction, ...]:
    body = _self_body(observation)
    geometry = body.receptor_geometry
    if geometry is None:
        raise ValueError("gustatory receptor geometry is unavailable")
    item = _object_for_contact(observation, body)
    if item is None or body.active_contact.kind != "oral":
        return (Fraction(0),) * TASTANT_CHANNELS
    material = item.material
    contact = body.active_contact
    assert material is not None
    contact_fraction = Fraction(
        contact.contact_patch_square_mm,
        item.radius_mm * item.radius_mm,
    )
    solvent_fraction = Fraction(
        material.moisture_ppm,
        MAX_PHYSICAL_PPM,
    )
    return tuple(
        _bounded_fraction(
            Fraction(mass, saturation)
            * contact_fraction
            * solvent_fraction
        )
        for mass, saturation in zip(
            material.tastant_mass_micrograms,
            geometry.tastant_saturation_micrograms,
        )
    )


def _sense_is_available(
    observation: ObservationSnapshot,
    sense: PhysicalSense,
) -> bool:
    body = _self_body(observation)
    geometry = body.receptor_geometry
    if geometry is None:
        return False
    if sense is PhysicalSense.SMELL:
        position = _body_fixed_position(
            body,
            geometry.olfactory_offset_mm,
        )
        region = (
            _region_at_point(observation, position)
            if position is not None
            else None
        )
        return region is not None and region.air is not None
    if sense in {PhysicalSense.TOUCH, PhysicalSense.TASTE}:
        if body.active_contact is None:
            return True
        try:
            _object_for_contact(observation, body)
        except ValueError:
            return False
        return True
    raise ValueError("material authority received a non-material sense")


@dataclass(frozen=True, slots=True)
class CoupledSixSenseExperience:
    built: BuiltSixSenseFullField
    settlement: CausalExperienceSettlement


def material_interval_states(
    *,
    world_authority: EmbodimentWorldAuthority,
    before: ObservationSnapshot,
    after: ObservationSnapshot,
) -> dict[PhysicalSense, SenseBoundaryState]:
    if not isinstance(world_authority, EmbodimentWorldAuthority):
        raise TypeError(
            "material receptors require the embodiment world owner"
        )
    world_authority.verify_observation_snapshot(before)
    world_authority.verify_observation_snapshot(after)
    return {
        sense: (
            SenseBoundaryState.OBSERVED
            if (
                _sense_is_available(before, sense)
                and _sense_is_available(after, sense)
            )
            else SenseBoundaryState.SENSOR_UNAVAILABLE
        )
        for sense in (
            PhysicalSense.TOUCH,
            PhysicalSense.SMELL,
            PhysicalSense.TASTE,
        )
    }


def material_receptor_substreams(
    *,
    world_authority: EmbodimentWorldAuthority,
    before: ObservationSnapshot,
    after: ObservationSnapshot,
    source_time_start: Fraction,
    source_time_end: Fraction,
) -> dict[
    PhysicalSense,
    tuple[NativeSensorySubstreamInput, ...],
]:
    states = material_interval_states(
        world_authority=world_authority,
        before=before,
        after=after,
    )
    observed: dict[
        PhysicalSense,
        tuple[NativeSensorySubstreamInput, ...],
    ] = {}
    if states[PhysicalSense.TOUCH] is SenseBoundaryState.OBSERVED:
        touch_before = _touch_values(before)
        touch_after = _touch_values(after)
        quantities = (
            ("surface-contact", "contact-state"),
            ("supported-mass", "receptor-mass-span"),
            ("surface-temperature", "signed-receptor-thermal-span"),
            ("material-compliance", "fraction"),
            ("surface-roughness", "receptor-roughness-span"),
            ("surface-moisture", "contact-solvent-fraction"),
        )
        observed[PhysicalSense.TOUCH] = tuple(
            _native_signal(
                sense=PhysicalSense.TOUCH,
                sensor_id="body-surface-receptor-field",
                substream_id=f"surface-receptor-{index:02d}",
                topology_index=index,
                coordinates=(
                    NativeAxisCoordinate(
                        "receptor-index",
                        f"{index:02d}",
                    ),
                ),
                physical_quantity=quantity,
                physical_unit=unit,
                values=(
                    touch_before[index],
                    touch_after[index],
                ),
                source_time_start=source_time_start,
                source_time_end=source_time_end,
            )
            for index, (quantity, unit) in enumerate(quantities)
        )
    if states[PhysicalSense.SMELL] is SenseBoundaryState.OBSERVED:
        smell_before = _smell_values(before)
        smell_after = _smell_values(after)
        observed[PhysicalSense.SMELL] = tuple(
            _native_signal(
                sense=PhysicalSense.SMELL,
                sensor_id="olfactory-receptor-field",
                substream_id=f"olfactory-receptor-{index:02d}",
                topology_index=index,
                coordinates=(
                    NativeAxisCoordinate(
                        "receptor-index",
                        f"{index:02d}",
                    ),
                ),
                physical_quantity="airborne-odorant-concentration",
                physical_unit="receptor-saturation-fraction",
                values=(
                    smell_before[index],
                    smell_after[index],
                ),
                source_time_start=source_time_start,
                source_time_end=source_time_end,
            )
            for index in range(ODORANT_CHANNELS)
        )
    if states[PhysicalSense.TASTE] is SenseBoundaryState.OBSERVED:
        taste_before = _taste_values(before)
        taste_after = _taste_values(after)
        observed[PhysicalSense.TASTE] = tuple(
            _native_signal(
                sense=PhysicalSense.TASTE,
                sensor_id="gustatory-receptor-field",
                substream_id=f"gustatory-receptor-{index:02d}",
                topology_index=index,
                coordinates=(
                    NativeAxisCoordinate(
                        "receptor-index",
                        f"{index:02d}",
                    ),
                ),
                physical_quantity="dissolved-tastant-mass",
                physical_unit="receptor-saturation-fraction",
                values=(
                    taste_before[index],
                    taste_after[index],
                ),
                source_time_start=source_time_start,
                source_time_end=source_time_end,
            )
            for index in range(TASTANT_CHANNELS)
        )
    return observed


def material_receptor_joint_units(
    observed: dict[
        PhysicalSense, tuple[NativeSensorySubstreamInput, ...]
    ],
) -> tuple[tuple[tuple[PhysicalSense, int], ...], ...]:
    """Declare this anatomy's joint-source units for one world edge.

    Each material receptor field transduces one signed material contact or
    diffusion event: the surface receptor axes sample one touched material
    jointly, the odorant channels sample one airborne mixture jointly, and
    the tastant channels sample one dissolved mixture jointly.  Each
    observed material sense is therefore one joint source occurrence.
    """

    return tuple(
        tuple((sense, port.topology_index) for port in ports)
        for sense, ports in observed.items()
        if ports
    )


def build_coupled_six_sense_full_field(
    *,
    assembly_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    world_authority: EmbodimentWorldAuthority,
    execution_receipt: ActionExecutionReceipt,
    left_sound: W1EarAuditoryTransductionCustody | None = None,
    right_sound: W1EarAuditoryTransductionCustody | None = None,
) -> BuiltSixSenseFullField:
    """Build one six-sense boundary from one signed world edge.

    Binaural sound is optional because an applied material action does not
    imply that an authenticated acoustic capture exists for the same exact
    interval.  Both ears must be supplied together; absence is represented as
    ``sensor_unavailable``, never as an observed zero pressure field.
    """

    world_authority.verify_execution_receipt(execution_receipt)
    if (
        source_time_end - source_time_start
        != Fraction(
            execution_receipt.elapsed_nanoseconds,
            1_000_000_000,
        )
    ):
        raise ValueError(
            "sensory interval differs from signed world elapsed time"
        )
    if (left_sound is None) != (right_sound is None):
        raise ValueError(
            "binaural sound must supply both ears or remain unavailable"
        )
    sound_substreams: tuple[NativeSensorySubstreamInput, ...] = ()
    sound_state = SenseBoundaryState.SENSOR_UNAVAILABLE
    if left_sound is not None and right_sound is not None:
        left_sound.verify()
        right_sound.verify()
        if (
            left_sound.ear_id != "left"
            or right_sound.ear_id != "right"
            or left_sound.topology_index != 0
            or right_sound.topology_index != len(left_sound)
        ):
            raise ValueError(
                "binaural sound topology is incomplete or reordered"
            )
        sound_substreams = tuple(left_sound) + tuple(right_sound)
        sound_state = SenseBoundaryState.OBSERVED
    physical = physical_receptor_substreams(
        execution_receipt.before,
        execution_receipt.after,
        causal_transition=True,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
    )
    material = material_receptor_substreams(
        world_authority=world_authority,
        before=execution_receipt.before,
        after=execution_receipt.after,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
    )
    material_states = material_interval_states(
        world_authority=world_authority,
        before=execution_receipt.before,
        after=execution_receipt.after,
    )
    observed = {
        PhysicalSense.SIGHT: physical[PhysicalSense.SIGHT],
        PhysicalSense.BODY: physical[PhysicalSense.BODY],
        **material,
    }
    if sound_substreams:
        observed[PhysicalSense.SOUND] = sound_substreams
    states = {
        PhysicalSense.SIGHT: SenseBoundaryState.OBSERVED,
        PhysicalSense.SOUND: sound_state,
        PhysicalSense.BODY: SenseBoundaryState.OBSERVED,
        **material_states,
    }
    declared_units = (
        *physical_receptor_joint_units({
            PhysicalSense.SIGHT: physical[PhysicalSense.SIGHT],
            PhysicalSense.BODY: physical[PhysicalSense.BODY],
        }),
        *material_receptor_joint_units(material),
        *(
            binaural_joint_units(left_sound, right_sound)
            if sound_substreams
            else ()
        ),
    )
    return build_transaction_owned_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        observed_substreams=observed,
        states={sense: states[sense] for sense in SENSE_ORDER},
        occurrences=declare_joint_source_occurrences(
            observed_substreams=observed,
            declared_units=declared_units,
        ),
    )


def settle_coupled_six_sense_experience(
    *,
    causal_owner: ExactCausalExperienceOwner,
    assembly_id: str,
    source_time_start: Fraction,
    source_time_end: Fraction,
    world_authority: EmbodimentWorldAuthority,
    execution_receipt: ActionExecutionReceipt,
    left_sound: W1EarAuditoryTransductionCustody | None = None,
    right_sound: W1EarAuditoryTransductionCustody | None = None,
) -> CoupledSixSenseExperience:
    if not isinstance(causal_owner, ExactCausalExperienceOwner):
        raise TypeError("coupled experience requires the exact causal owner")
    built = build_coupled_six_sense_full_field(
        assembly_id=assembly_id,
        source_time_start=source_time_start,
        source_time_end=source_time_end,
        world_authority=world_authority,
        execution_receipt=execution_receipt,
        left_sound=left_sound,
        right_sound=right_sound,
    )
    settlement = causal_owner.settle(
        built,
        routing_chis=(),
        source_tags=(),
    )
    return CoupledSixSenseExperience(
        built=built,
        settlement=settlement,
    )


def settle_coupled_multi_emitter_six_sense_experience(
    *,
    causal_owner: ExactCausalExperienceOwner,
    assembly_id: str,
    world_authority: EmbodimentWorldAuthority,
    execution_receipt: ActionExecutionReceipt,
    multi_emitter_capture: object,
    multi_emitter_authority_key: bytes | str,
) -> CoupledSixSenseExperience:
    from dsf_ai_service.substrate.senses.auditory_full_field_provider import (
        OBSERVATION_HOP_SAMPLES,
    )
    from dsf_ai_service.substrate.w1_acoustic_emitter import (
        PCM_SAMPLE_RATE_HZ,
    )
    from dsf_ai_service.substrate.w1_authenticated_multi_emitter_capture import (
        W1AuthenticatedMultiEmitterBinauralCapture,
        W1MultiEmitterCaptureState,
    )

    if not isinstance(
        multi_emitter_capture,
        W1AuthenticatedMultiEmitterBinauralCapture,
    ):
        raise TypeError("coupled room hearing capture is not typed")
    multi_emitter_capture.verify(multi_emitter_authority_key)
    if (
        multi_emitter_capture.state
        is not W1MultiEmitterCaptureState.CAPTURED
    ):
        raise ValueError(
            "indeterminate multi-emitter pressure cannot settle experience"
        )
    source_start = Fraction(
        multi_emitter_capture.source_sample_start,
        PCM_SAMPLE_RATE_HZ,
    )
    padded_sample_count = (
        (
            multi_emitter_capture.capture_sample_count
            + OBSERVATION_HOP_SAMPLES
            - 1
        )
        // OBSERVATION_HOP_SAMPLES
        * OBSERVATION_HOP_SAMPLES
    )
    padding = b"\0\0" * (
        padded_sample_count
        - multi_emitter_capture.capture_sample_count
    )
    source_end = source_start + Fraction(
        padded_sample_count,
        PCM_SAMPLE_RATE_HZ,
    )
    left = binaural_sound_field_inputs(
        ear="left",
        topology_index=0,
        pcm=multi_emitter_capture.left_pcm_s16le + padding,
        source_time_start=source_start,
    )
    right = binaural_sound_field_inputs(
        ear="right",
        topology_index=len(left),
        pcm=multi_emitter_capture.right_pcm_s16le + padding,
        source_time_start=source_start,
    )
    return settle_coupled_six_sense_experience(
        causal_owner=causal_owner,
        assembly_id=assembly_id,
        source_time_start=source_start,
        source_time_end=source_end,
        world_authority=world_authority,
        execution_receipt=execution_receipt,
        left_sound=left,
        right_sound=right,
    )


__all__ = (
    "CoupledSixSenseExperience",
    "build_coupled_six_sense_full_field",
    "material_interval_states",
    "material_receptor_substreams",
    "settle_coupled_multi_emitter_six_sense_experience",
    "settle_coupled_six_sense_experience",
)
