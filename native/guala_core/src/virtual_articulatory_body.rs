//! Bounded exact developmental acoustic actuation driven by native layer-13
//! discharge.
//!
//! This is body mechanics, not language. A transient whole-carrier discharge
//! gives finite momentum to three persisted acoustic surfaces. Their changing
//! displacement excites the organism's existing bounded acoustic tube;
//! resonator damping and tube wall loss return every coordinate to exact rest.
//! No phoneme, word, target waveform, retained program, or learned meaning is
//! present here.

use core::cmp::{max, min};

use crate::virtual_articulated_body::{
    ArticulatedBodyState, BodyAxis, BodyProprioceptiveConsequence,
    ACOUSTIC_TRANSDUCER_SURFACE_COUNT,
    MAX_TRACT_AREA_SQUARE_MILLIMETRES, MIN_TRACT_AREA_SQUARE_MILLIMETRES,
    VOCAL_TRACT_SECTION_COUNT,
};
#[cfg(test)]
use crate::virtual_articulated_body::ArticulatoryAcousticState;

pub(crate) const ARTICULATORY_SAMPLE_RATE_HZ: u32 = 16_000;
pub(crate) const NATIVE_ARTICULATORY_INTERVAL_SAMPLES: usize = 16;
const TRACT_SECTION_COUNT: usize = VOCAL_TRACT_SECTION_COUNT;
#[cfg(test)]
const ACTIVE_SAMPLE_COUNT: usize = ARTICULATORY_SAMPLE_RATE_HZ as usize;
#[cfg(test)]
const MAX_RELAXATION_SAMPLES: usize = 16_384;
const NEUTRAL_GLOTTAL_OPEN_SAMPLES: i32 = 80;
const MIN_GLOTTAL_OPEN_SAMPLES: i32 = 16;
const MAX_GLOTTAL_OPEN_SAMPLES: i32 = 144;
// Exact fixed-capacity developmental transducer anatomy. Each surface has the
// same mass and viscous damping; stiffness alone changes by one factor-four
// lattice scale. These are physical body quantities from which the recurrence
// is derived, not fitted oscillator coefficients or sound targets.
const TRANSDUCER_SURFACE_MASS_QUANTA: i64 = 4_096;
const TRANSDUCER_VISCOUS_DAMPING_QUANTA: i64 = 1;
const TRANSDUCER_SURFACE_STIFFNESS_QUANTA: [i64; ACOUSTIC_TRANSDUCER_SURFACE_COUNT] =
    [64, 256, 1_024];
const MOTOR_IMPULSE_DISPLACEMENT_QUANTA: i32 = 64;
const WALL_RETENTION_PARTS_PER_MILLION: i64 = 985_000;
const PARTS_PER_MILLION: i64 = 1_000_000;
const RADIATION_LOAD_AREA_SQUARE_MILLIMETRES: i32 = 265;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ArticulatoryBodyError {
    NoRecruitment,
    ArithmeticWidth,
    ResourceUnavailable,
    RelaxationDidNotQuiesce,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ArticulatoryBodyTransition {
    pub(crate) radiated_pressure_pcm: Vec<i16>,
    /// Port-major local body mechanics at the same sample instants as the
    /// radiated pressure: respiratory flow, glottal configuration
    /// displacement, oral aperture displacement, and perioral skin
    /// displacement. The developmental transducer does not manufacture
    /// respiratory flow, so port zero remains exact zero.
    pub(crate) body_mechanical_trajectories: [Vec<i16>; 4],
    pub(crate) peak_transducer_surface_velocity_pcm: i32,
    pub(crate) glottal_open_samples_at_apex: i32,
    pub(crate) mouth_area_square_millimetres_at_apex: i32,
    pub(crate) perioral_area_displacement_square_millimetres: i32,
    pub(crate) applied_motor_quanta: u128,
    pub(crate) stalled_motor_quanta: u128,
    pub(crate) relaxation_sample_count: usize,
    pub(crate) successor_body: ArticulatedBodyState,
}

/// Advance the vocal body across one exact causal source interval.
///
/// An already-settled typed layer-12 motor displacement is accepted exactly
/// once; it is never repeated or stretched across the preceding sensory
/// episode. Glottis, jaw and lip-width tissue have one fixed attachment each
/// to the three resident acoustic surfaces. This is body anatomy, not a
/// phoneme map: the actual signed displacement supplies direction, and a motor
/// stalled at its anatomical stop supplies no acoustic impulse. The surfaces
/// and tube then produce the consequence across interval and restart
/// boundaries without a phase clock or duration counter.
pub(crate) fn settle_native_articulatory_interval(
    articulated_body: ArticulatedBodyState,
    body_consequences: &[BodyProprioceptiveConsequence],
    interval_sample_count: usize,
) -> Result<ArticulatoryBodyTransition, ArticulatoryBodyError> {
    if interval_sample_count == 0 {
        return Err(ArticulatoryBodyError::NoRecruitment);
    }
    let mut acoustic = articulated_body.articulatory_acoustic_state();
    let mut applied = 0_u128;
    let mut stalled = 0_u128;
    for consequence in body_consequences {
        let surface_index = match consequence.axis {
            BodyAxis::GlottalAperture => Some(0),
            BodyAxis::JawOpening => Some(1),
            BodyAxis::LipWidth => Some(2),
            _ => None,
        };
        let Some(surface_index) = surface_index else {
            continue;
        };
        stalled = stalled
            .checked_add(consequence.stalled_carriers)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        let displacement = i128::from(consequence.signed_displacement);
        let magnitude = displacement.unsigned_abs();
        let coupled = min(magnitude, 8);
        applied = applied
            .checked_add(coupled)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        stalled = stalled
            .checked_add(magnitude - coupled)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        if coupled == 0 {
            continue;
        }
        let signed_coupled = i32::try_from(coupled)
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
            * if displacement.is_negative() { -1 } else { 1 };
        let impulse = signed_coupled
            .checked_mul(MOTOR_IMPULSE_DISPLACEMENT_QUANTA)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        acoustic.surface_previous_displacement[surface_index] = acoustic
            .surface_previous_displacement[surface_index]
            .checked_sub(impulse)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    }
    let glottal_apex = glottal_open_samples(&articulated_body)?;
    let areas = articulated_vocal_tract_areas(&articulated_body)?;
    let body_channels = articulated_body_channels(&articulated_body)?;
    let mut radiated = Vec::new();
    radiated
        .try_reserve_exact(interval_sample_count)
        .map_err(|_| ArticulatoryBodyError::ResourceUnavailable)?;
    let mut body_mechanics: [Vec<i16>; 4] = std::array::from_fn(|_| Vec::new());
    for trajectory in &mut body_mechanics {
        trajectory
            .try_reserve_exact(interval_sample_count)
            .map_err(|_| ArticulatoryBodyError::ResourceUnavailable)?;
    }

    let mut strongest_surface_velocity = 0_i32;
    for _interval_sample_index in 0..interval_sample_count {
        let mut source_pressure = 0_i32;
        for surface_index in 0..ACOUSTIC_TRANSDUCER_SURFACE_COUNT {
            let current = acoustic.surface_displacement[surface_index];
            let previous = acoustic.surface_previous_displacement[surface_index];
            let stiffness = TRANSDUCER_SURFACE_STIFFNESS_QUANTA[surface_index];
            let current_coefficient = 2_i64
                .checked_mul(TRANSDUCER_SURFACE_MASS_QUANTA)
                .and_then(|twice_mass| twice_mass.checked_sub(stiffness))
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            let numerator = current_coefficient
                .checked_mul(i64::from(current))
                .and_then(|value| {
                    value.checked_sub(
                        TRANSDUCER_SURFACE_MASS_QUANTA
                            .checked_mul(i64::from(previous))?,
                    )
                })
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            let denominator = TRANSDUCER_SURFACE_MASS_QUANTA
                .checked_add(TRANSDUCER_VISCOUS_DAMPING_QUANTA)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            // Exact central-difference settlement of
            // m*x'' + c*x' + k*x = 0. Truncation toward zero is part of the
            // finite lattice and cannot recreate sub-quantum energy.
            let next = i32::try_from(numerator / denominator)
                .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
            let velocity = next
                .checked_sub(current)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            acoustic.surface_previous_displacement[surface_index] = current;
            acoustic.surface_displacement[surface_index] = next;
            source_pressure = source_pressure
                .checked_add(velocity)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            if velocity.unsigned_abs() > strongest_surface_velocity.unsigned_abs() {
                strongest_surface_velocity = velocity;
            }
        }
        let (next_right, next_left, emitted) = advance_tube(
            acoustic.right_traveling_pressure,
            acoustic.left_traveling_pressure,
            areas,
            source_pressure,
        )?;
        acoustic.right_traveling_pressure = next_right;
        acoustic.left_traveling_pressure = next_left;
        radiated.push(emitted);
        body_mechanics[0].push(0);
        body_mechanics[1].push(body_channels[0]);
        body_mechanics[2].push(body_channels[1]);
        body_mechanics[3].push(body_channels[2]);
    }
    let successor_body = articulated_body
        .with_articulatory_acoustic_state(acoustic)
        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    Ok(ArticulatoryBodyTransition {
        radiated_pressure_pcm: radiated,
        body_mechanical_trajectories: body_mechanics,
        peak_transducer_surface_velocity_pcm: strongest_surface_velocity,
        glottal_open_samples_at_apex: glottal_apex,
        mouth_area_square_millimetres_at_apex: areas[TRACT_SECTION_COUNT - 1],
        perioral_area_displacement_square_millimetres: i32::from(body_channels[2]),
        applied_motor_quanta: applied,
        stalled_motor_quanta: stalled,
        relaxation_sample_count: 0,
        successor_body,
    })
}

/// Test-only composition of the production interval law. It owns no second
/// acoustic implementation: every active and relaxing sample crosses
/// `settle_native_articulatory_interval`, preserving the same resident state
/// that production persists.
#[cfg(test)]
pub(crate) fn settle_physical_transducer_interval_discharges(
    intervals: &[(usize, Vec<BodyProprioceptiveConsequence>, ArticulatedBodyState)],
) -> Result<ArticulatoryBodyTransition, ArticulatoryBodyError> {
    if intervals.is_empty()
        || intervals.iter().any(|(samples, _, _)| *samples == 0)
        || intervals
            .iter()
            .all(|(_, consequences, _)| consequences.is_empty())
    {
        return Err(ArticulatoryBodyError::NoRecruitment);
    }
    let active_sample_count = intervals.iter().try_fold(0usize, |total, (samples, _, _)| {
        total.checked_add(*samples).ok_or(ArticulatoryBodyError::ArithmeticWidth)
    })?;
    let output_capacity = active_sample_count
        .checked_add(MAX_RELAXATION_SAMPLES)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    let mut radiated = Vec::new();
    radiated.try_reserve_exact(output_capacity)
        .map_err(|_| ArticulatoryBodyError::ResourceUnavailable)?;
    let mut body_mechanics: [Vec<i16>; 4] = std::array::from_fn(|_| Vec::new());
    for trajectory in &mut body_mechanics {
        trajectory.try_reserve_exact(output_capacity)
            .map_err(|_| ArticulatoryBodyError::ResourceUnavailable)?;
    }
    let mut acoustic = intervals[0].2.articulatory_acoustic_state();
    let mut final_body = intervals[0].2.clone();
    let mut applied_motor_quanta = 0_u128;
    let mut stalled_motor_quanta = 0_u128;
    let mut strongest_surface_velocity = 0_i32;
    let mut strongest_glottal_apex = 0_i32;
    let mut strongest_mouth_area = 0_i32;
    let mut final_perioral_area = 0_i32;

    for (samples, consequences, body) in intervals {
        let body = body.clone().with_articulatory_acoustic_state(acoustic)
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
        let settled = settle_native_articulatory_interval(body, consequences, *samples)?;
        acoustic = settled.successor_body.articulatory_acoustic_state();
        final_body = settled.successor_body.clone();
        radiated.extend_from_slice(&settled.radiated_pressure_pcm);
        for (aggregate, interval) in body_mechanics.iter_mut()
            .zip(&settled.body_mechanical_trajectories)
        {
            aggregate.extend_from_slice(interval);
        }
        applied_motor_quanta = applied_motor_quanta
            .checked_add(settled.applied_motor_quanta)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        stalled_motor_quanta = stalled_motor_quanta
            .checked_add(settled.stalled_motor_quanta)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        if settled.peak_transducer_surface_velocity_pcm.unsigned_abs()
            >= strongest_surface_velocity.unsigned_abs()
        {
            strongest_surface_velocity = settled.peak_transducer_surface_velocity_pcm;
            strongest_glottal_apex = settled.glottal_open_samples_at_apex;
            strongest_mouth_area = settled.mouth_area_square_millimetres_at_apex;
        }
        final_perioral_area = settled.perioral_area_displacement_square_millimetres;
    }
    let mut relaxation_sample_count = 0usize;
    while !acoustic.is_quiescent() {
        if relaxation_sample_count == MAX_RELAXATION_SAMPLES {
            return Err(ArticulatoryBodyError::RelaxationDidNotQuiesce);
        }
        let settled = settle_native_articulatory_interval(final_body.clone(), &[], 1)?;
        acoustic = settled.successor_body.articulatory_acoustic_state();
        final_body = settled.successor_body.clone();
        radiated.extend_from_slice(&settled.radiated_pressure_pcm);
        for (aggregate, interval) in body_mechanics.iter_mut()
            .zip(&settled.body_mechanical_trajectories)
        {
            aggregate.extend_from_slice(interval);
        }
        relaxation_sample_count += 1;
    }
    Ok(ArticulatoryBodyTransition {
        radiated_pressure_pcm: radiated,
        body_mechanical_trajectories: body_mechanics,
        peak_transducer_surface_velocity_pcm: strongest_surface_velocity,
        glottal_open_samples_at_apex: strongest_glottal_apex,
        mouth_area_square_millimetres_at_apex: strongest_mouth_area,
        perioral_area_displacement_square_millimetres: final_perioral_area,
        applied_motor_quanta,
        stalled_motor_quanta,
        relaxation_sample_count,
        successor_body: final_body,
    })
}

fn glottal_open_samples(
    body: &ArticulatedBodyState,
) -> Result<i32, ArticulatoryBodyError> {
    let anatomy = BodyAxis::GlottalAperture.anatomy();
    let area = body.axis(BodyAxis::GlottalAperture);
    if area <= anatomy.neutral {
        MIN_GLOTTAL_OPEN_SAMPLES
            .checked_add(round_div(
                i64::from(area - anatomy.minimum)
                    * i64::from(NEUTRAL_GLOTTAL_OPEN_SAMPLES - MIN_GLOTTAL_OPEN_SAMPLES),
                i64::from(anatomy.neutral - anatomy.minimum),
            )?)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)
    } else {
        NEUTRAL_GLOTTAL_OPEN_SAMPLES
            .checked_add(round_div(
                i64::from(area - anatomy.neutral)
                    * i64::from(MAX_GLOTTAL_OPEN_SAMPLES - NEUTRAL_GLOTTAL_OPEN_SAMPLES),
                i64::from(anatomy.maximum - anatomy.neutral),
            )?)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)
    }
}

fn articulated_vocal_tract_areas(
    body: &ArticulatedBodyState,
) -> Result<[i32; TRACT_SECTION_COUNT], ArticulatoryBodyError> {
    let mut areas = body.vocal_tract_areas_square_millimetres();
    let lip_width = i64::from(body.axis(BodyAxis::LipWidth));
    let lip_aperture = i64::from(body.axis(BodyAxis::LipAperture));
    let jaw_opening = i64::from(body.axis(BodyAxis::JawOpening));
    let oral_area = round_div(lip_width * jaw_opening, 1_000_000)?;
    let mouth_area = round_div(lip_width * lip_aperture, 1_000_000)?;
    areas[TRACT_SECTION_COUNT - 2] = min(
        areas[TRACT_SECTION_COUNT - 2],
        max(
            MIN_TRACT_AREA_SQUARE_MILLIMETRES,
            min(MAX_TRACT_AREA_SQUARE_MILLIMETRES, oral_area),
        ),
    );
    areas[TRACT_SECTION_COUNT - 1] = min(
        areas[TRACT_SECTION_COUNT - 1],
        max(
            MIN_TRACT_AREA_SQUARE_MILLIMETRES,
            min(MAX_TRACT_AREA_SQUARE_MILLIMETRES, mouth_area),
        ),
    );
    Ok(areas)
}

fn articulated_body_channels(
    body: &ArticulatedBodyState,
) -> Result<[i16; 3], ArticulatoryBodyError> {
    let glottal = body.axis(BodyAxis::GlottalAperture)
        - BodyAxis::GlottalAperture.anatomy().neutral;
    let lip_width = i64::from(body.axis(BodyAxis::LipWidth));
    let oral = min(
        MAX_TRACT_AREA_SQUARE_MILLIMETRES,
        round_div(
            lip_width * i64::from(body.axis(BodyAxis::LipAperture)),
            1_000_000,
        )?,
    );
    let perioral = round_div(
        lip_width * i64::from(body.axis(BodyAxis::PerioralDisplacement)),
        1_000_000,
    )?;
    Ok([
        i16::try_from(glottal).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
        i16::try_from(oral).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
        i16::try_from(perioral).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
    ])
}

fn advance_tube(
    right: [i32; TRACT_SECTION_COUNT],
    left: [i32; TRACT_SECTION_COUNT],
    areas: [i32; TRACT_SECTION_COUNT],
    source_pressure: i32,
) -> Result<([i32; TRACT_SECTION_COUNT], [i32; TRACT_SECTION_COUNT], i16), ArticulatoryBodyError> {
    let mut next_right = [0_i32; TRACT_SECTION_COUNT];
    let mut next_left = [0_i32; TRACT_SECTION_COUNT];
    next_right[0] = source_pressure;
    for junction in 0..TRACT_SECTION_COUNT - 1 {
        let left_area = i64::from(areas[junction]);
        let right_area = i64::from(areas[junction + 1]);
        let total = left_area + right_area;
        let outward_right = round_div(
            2 * left_area * i64::from(right[junction])
                + (right_area - left_area) * i64::from(left[junction + 1]),
            total,
        )?;
        let outward_left = round_div(
            (left_area - right_area) * i64::from(right[junction])
                + 2 * right_area * i64::from(left[junction + 1]),
            total,
        )?;
        next_right[junction + 1] = retain_wall(outward_right)?;
        next_left[junction] = retain_wall(outward_left)?;
    }
    let mouth_area = i64::from(areas[TRACT_SECTION_COUNT - 1]);
    let load = i64::from(RADIATION_LOAD_AREA_SQUARE_MILLIMETRES);
    let total = mouth_area + load;
    let reflected = round_div(
        (mouth_area - load) * i64::from(right[TRACT_SECTION_COUNT - 1]),
        total,
    )?;
    let transmitted = round_div(
        2 * mouth_area * i64::from(right[TRACT_SECTION_COUNT - 1]),
        total,
    )?;
    next_left[TRACT_SECTION_COUNT - 1] = retain_wall(reflected)?;
    let emitted = i16::try_from(max(i64::from(i16::MIN), min(i64::from(i16::MAX), i64::from(transmitted))))
        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    Ok((next_right, next_left, emitted))
}

fn retain_wall(value: i32) -> Result<i32, ArticulatoryBodyError> {
    let retained = i64::from(value).unsigned_abs()
        * u64::try_from(WALL_RETENTION_PARTS_PER_MILLION)
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
        / u64::try_from(PARTS_PER_MILLION)
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    let retained = i32::try_from(retained)
        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    Ok(if value.is_negative() { -retained } else { retained })
}

fn round_div(numerator: i64, denominator: i64) -> Result<i32, ArticulatoryBodyError> {
    if denominator <= 0 {
        return Err(ArticulatoryBodyError::ArithmeticWidth);
    }
    let sign = if numerator.is_negative() { -1_i128 } else { 1_i128 };
    let magnitude = i128::from(numerator).abs();
    let denominator = i128::from(denominator);
    let mut quotient = magnitude / denominator;
    if 2 * (magnitude % denominator) >= denominator {
        quotient += 1;
    }
    i32::try_from(sign * quotient).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::virtual_articulated_body::{
        settle_body_effector_drives, AdmittedBodyEffectorDrives, BodyEffectorDirection,
        BodyEffectorDrive, BodyEffectorTerminal,
    };

    fn moved(
        predecessor: &ArticulatedBodyState,
        axis: BodyAxis,
        direction: BodyEffectorDirection,
        carriers: u128,
    ) -> (ArticulatedBodyState, Vec<BodyProprioceptiveConsequence>) {
        let admitted = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
            terminal: BodyEffectorTerminal::new(axis, direction),
            outward_elementary_carriers: carriers,
        }])
        .unwrap();
        let transition = settle_body_effector_drives(predecessor, &admitted).unwrap();
        (transition.successor, transition.proprioceptive_consequences)
    }

    fn active_interval(
        predecessor: ArticulatedBodyState,
        axis: BodyAxis,
        direction: BodyEffectorDirection,
        carriers: u128,
        samples: usize,
    ) -> ArticulatoryBodyTransition {
        let (body, consequences) = moved(&predecessor, axis, direction, carriers);
        settle_native_articulatory_interval(body, &consequences, samples).unwrap()
    }

    fn jaw_consequences(carriers: u128) -> Vec<BodyProprioceptiveConsequence> {
        moved(
            &ArticulatedBodyState::at_neutral(),
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            carriers,
        )
        .1
    }

    #[test]
    fn one_real_typed_displacement_uses_the_resident_body_and_radiates_pressure() {
        let settled = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            13,
            ACTIVE_SAMPLE_COUNT,
        );
        assert_eq!(settled.applied_motor_quanta, 8);
        assert_eq!(settled.stalled_motor_quanta, 5);
        assert_eq!(settled.glottal_open_samples_at_apex, 80);
        assert_eq!(settled.perioral_area_displacement_square_millimetres, 0);
        assert_ne!(settled.peak_transducer_surface_velocity_pcm, 0);
        assert!(settled.radiated_pressure_pcm.iter().any(|value| *value != 0));
        assert!(settled.relaxation_sample_count <= MAX_RELAXATION_SAMPLES);
    }

    #[test]
    fn distinct_typed_vocal_paths_drive_distinct_persisted_surfaces_and_spectra() {
        let glottis = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMaximum,
            3,
            4_000,
        );
        let jaw = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            3,
            4_000,
        );
        let lips = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::LipWidth,
            BodyEffectorDirection::TowardMaximum,
            3,
            4_000,
        );
        assert_ne!(glottis.radiated_pressure_pcm, jaw.radiated_pressure_pcm);
        assert_ne!(jaw.radiated_pressure_pcm, lips.radiated_pressure_pcm);
    }

    #[test]
    fn one_motor_event_advances_only_one_native_millisecond() {
        let settled = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            8,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );

        assert_eq!(
            settled.radiated_pressure_pcm.len(),
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES
        );
        assert_eq!(settled.applied_motor_quanta, 8);
        assert_eq!(settled.relaxation_sample_count, 0);
        assert_ne!(
            settled.successor_body.articulatory_acoustic_state(),
            ArticulatoryAcousticState::at_rest()
        );
    }

    #[test]
    fn one_motor_event_moves_only_the_bounded_transducer_without_repeating_discharge() {
        let settled = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            8,
            4_000,
        );

        assert_eq!(settled.radiated_pressure_pcm.len(), 4_000);
        assert!(settled.body_mechanical_trajectories[0]
            .iter()
            .all(|respiratory_flow| *respiratory_flow == 0));
        assert_eq!(settled.applied_motor_quanta, 8);
        assert_eq!(settled.stalled_motor_quanta, 0);
        assert_ne!(settled.peak_transducer_surface_velocity_pcm, 0);
        assert_ne!(
            settled.successor_body.articulatory_acoustic_state(),
            ArticulatoryAcousticState::at_rest()
        );
        assert!(settled.radiated_pressure_pcm.iter().any(|sample| *sample != 0));
    }

    #[test]
    fn body_owned_transducer_cold_restores_and_reaches_exact_rest_without_another_discharge() {
        let first = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            3,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        let restored = ArticulatedBodyState::decode(
            &first.successor_body.encode().unwrap(),
        )
        .unwrap();
        assert_eq!(
            restored.articulatory_acoustic_state(),
            first.successor_body.articulatory_acoustic_state()
        );
        let released = settle_native_articulatory_interval(restored, &[], 8_000).unwrap();
        assert_eq!(released.applied_motor_quanta, 0);
        assert_eq!(
            released.successor_body.articulatory_acoustic_state(),
            ArticulatoryAcousticState::at_rest()
        );
    }

    #[test]
    fn acoustic_pressure_and_surface_motion_continue_across_interval_and_restart() {
        let first = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            8,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        let restored = ArticulatedBodyState::decode(
            &first.successor_body.encode().unwrap(),
        )
        .unwrap();
        let continued = active_interval(
            restored,
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            8,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        let uninterrupted = active_interval(
            first.successor_body,
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            8,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );

        assert_eq!(continued, uninterrupted);
        assert_ne!(
            first.radiated_pressure_pcm,
            continued.radiated_pressure_pcm
        );
        assert_ne!(
            continued.successor_body.articulatory_acoustic_state(),
            ArticulatoryAcousticState::at_rest()
        );
    }

    #[test]
    fn absent_new_discharge_releases_the_resident_pressure_instead_of_repeating_it() {
        let active = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            8,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        let released = settle_native_articulatory_interval(
            active.successor_body,
            &[],
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        )
        .unwrap();

        assert_eq!(released.applied_motor_quanta, 0);
        assert_ne!(active.radiated_pressure_pcm, released.radiated_pressure_pcm);
    }

    #[test]
    fn causal_interval_timing_changes_the_physical_utterance() {
        let jaw = jaw_consequences(8);
        let contiguous = settle_physical_transducer_interval_discharges(&[
            (4_000, jaw.clone(), ArticulatedBodyState::at_neutral()),
            (4_000, jaw.clone(), ArticulatedBodyState::at_neutral()),
        ])
        .unwrap();
        let separated = settle_physical_transducer_interval_discharges(&[
            (4_000, jaw.clone(), ArticulatedBodyState::at_neutral()),
            (4_000, vec![], ArticulatedBodyState::at_neutral()),
            (4_000, jaw, ArticulatedBodyState::at_neutral()),
        ])
        .unwrap();

        assert_ne!(
            contiguous.radiated_pressure_pcm,
            separated.radiated_pressure_pcm
        );
        assert_eq!(
            separated.radiated_pressure_pcm.len(),
            12_000 + separated.relaxation_sample_count
        );
        assert_eq!(separated.applied_motor_quanta, 16);
    }

    #[test]
    fn lawful_long_recording_is_not_an_arithmetic_width_error() {
        let intervals = (0..46)
            .map(|index| {
                let consequences = if matches!(index, 0 | 8 | 17 | 27 | 35 | 45) {
                    jaw_consequences(8)
                } else {
                    Vec::new()
                };
                (4_000, consequences, ArticulatedBodyState::at_neutral())
            })
            .collect::<Vec<_>>();
        let settled = settle_physical_transducer_interval_discharges(&intervals).unwrap();

        assert_eq!(settled.applied_motor_quanta, 48);
        assert_eq!(
            settled.radiated_pressure_pcm.len(),
            184_000 + settled.relaxation_sample_count
        );
    }

    #[test]
    fn the_same_discharge_changes_when_the_resident_mouth_changes() {
        let neutral = ArticulatedBodyState::at_neutral();
        let mut axes = *neutral.axes();
        axes[BodyAxis::JawOpening.index()] = 10_000;
        axes[BodyAxis::LipAperture.index()] = 8_000;
        let open = ArticulatedBodyState::from_physical_state(
            axes,
            neutral.lung_air_microlitres(),
            neutral.proprioception_initialized(),
        )
        .unwrap();
        let neutral_sound = settle_physical_transducer_interval_discharges(&[(
            4_000,
            jaw_consequences(8),
            neutral,
        )])
        .unwrap();
        let open_sound = settle_physical_transducer_interval_discharges(&[(
            4_000,
            jaw_consequences(8),
            open,
        )])
        .unwrap();
        assert_ne!(neutral_sound.radiated_pressure_pcm, open_sound.radiated_pressure_pcm);
        assert_ne!(
            neutral_sound.mouth_area_square_millimetres_at_apex,
            open_sound.mouth_area_square_millimetres_at_apex
        );
    }

    #[test]
    fn the_same_discharge_changes_when_one_resident_tract_section_moves() {
        let neutral = ArticulatedBodyState::at_neutral();
        let mut axes = *neutral.axes();
        axes[BodyAxis::VocalTractSection3Area.index()] += 7;
        let shaped = ArticulatedBodyState::from_physical_state(
            axes,
            neutral.lung_air_microlitres(),
            neutral.proprioception_initialized(),
        )
        .unwrap();
        let neutral_sound = settle_physical_transducer_interval_discharges(&[(
            4_000,
            jaw_consequences(8),
            neutral,
        )])
        .unwrap();
        let shaped_sound = settle_physical_transducer_interval_discharges(&[(
            4_000,
            jaw_consequences(8),
            shaped,
        )])
        .unwrap();

        assert_ne!(neutral_sound.radiated_pressure_pcm, shaped_sound.radiated_pressure_pcm);
    }

    #[test]
    fn stalled_motor_and_unattached_body_axis_cannot_manufacture_pressure() {
        let neutral = ArticulatedBodyState::at_neutral();
        let mut axes = *neutral.axes();
        axes[BodyAxis::GlottalAperture.index()] = BodyAxis::GlottalAperture.anatomy().maximum;
        let at_stop = ArticulatedBodyState::from_physical_state(
            axes,
            neutral.lung_air_microlitres(),
            neutral.proprioception_initialized(),
        )
        .unwrap();
        let stalled = active_interval(
            at_stop,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMaximum,
            7,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        let shoulder = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::LeftShoulderPitch,
            BodyEffectorDirection::TowardMaximum,
            7,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        assert_eq!(stalled.applied_motor_quanta, 0);
        assert_eq!(stalled.stalled_motor_quanta, 7);
        assert!(stalled.radiated_pressure_pcm.iter().all(|sample| *sample == 0));
        assert_eq!(shoulder.applied_motor_quanta, 0);
        assert!(shoulder.radiated_pressure_pcm.iter().all(|sample| *sample == 0));
    }
}
