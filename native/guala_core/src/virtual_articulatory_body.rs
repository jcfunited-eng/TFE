//! Bounded exact virtual articulation driven by native layer-13 discharge.
//!
//! This is body mechanics, not language. A transient whole-carrier discharge
//! drives one finite exhalation through the organism's persisted glottis,
//! lung, mouth and eight-section loss tube, then returns only the traveling
//! pressure field to exact rest. The articulated body remains its one resident
//! physical authority.
//! No phoneme, word, target waveform, retained program, or learned meaning is
//! present here.

use core::cmp::{max, min};

use crate::virtual_articulated_body::{
    ArticulatedBodyState, BodyAxis, MAX_LUNG_AIR_MICROLITRES,
    MAX_TRACT_AREA_SQUARE_MILLIMETRES, MIN_TRACT_AREA_SQUARE_MILLIMETRES,
    NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES, VOCAL_TRACT_SECTION_COUNT,
};

pub(crate) const ARTICULATORY_SAMPLE_RATE_HZ: u32 = 16_000;
const TRACT_SECTION_COUNT: usize = VOCAL_TRACT_SECTION_COUNT;
#[cfg(test)]
const ACTIVE_SAMPLE_COUNT: usize = ARTICULATORY_SAMPLE_RATE_HZ as usize;
const MAX_RELAXATION_SAMPLES: usize = 16_384;
const LARYNGEAL_CYCLE_SAMPLES: usize = 160;
const NEUTRAL_GLOTTAL_OPEN_SAMPLES: i32 = 80;
const MIN_GLOTTAL_OPEN_SAMPLES: i32 = 16;
const MAX_GLOTTAL_OPEN_SAMPLES: i32 = 144;
const RESPIRATORY_PEAK_VOLUME_VELOCITY_PCM: i32 = 4_000;
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
    /// radiated pressure: breath flow, glottal configuration displacement,
    /// oral aperture displacement, and perioral skin displacement.
    pub(crate) body_mechanical_trajectories: [Vec<i16>; 4],
    pub(crate) peak_breath_flow_pcm: i32,
    pub(crate) glottal_open_samples_at_apex: i32,
    pub(crate) mouth_area_square_millimetres_at_apex: i32,
    pub(crate) perioral_area_displacement_square_millimetres: i32,
    pub(crate) applied_motor_quanta: u128,
    pub(crate) stalled_motor_quanta: u128,
    pub(crate) relaxation_sample_count: usize,
}

/// Settle one layer-13 discharge into the organism's one articulated body.
/// Topology ordinals carry identity only; they never manufacture actuator
/// direction. One whole carrier is one native respiratory excitation quantum.
#[cfg(test)]
pub(crate) fn settle_articulatory_unit_discharge(
    recruitments: &[(u32, u128)],
) -> Result<ArticulatoryBodyTransition, ArticulatoryBodyError> {
    settle_articulatory_interval_discharges(&[(
        ACTIVE_SAMPLE_COUNT,
        recruitments.to_vec(),
        ArticulatedBodyState::at_neutral(),
    )])
}

/// Settle the exact ordered layer-13 discharge intervals as one continuous
/// vocal-body trajectory.
///
/// Each interval carries its real duration on the 16-kHz body clock and the
/// layer-13 cells that discharged during that native causal interval. Empty
/// intervals between discharges remain physical time rather than being
/// deleted. The traveling pressure state crosses interval boundaries without
/// reset and relaxes exactly once after the final interval. No formation ID,
/// phoneme, word, target waveform, or semantic value enters this law.
pub(crate) fn settle_articulatory_interval_discharges(
    intervals: &[(usize, Vec<(u32, u128)>, ArticulatedBodyState)],
) -> Result<ArticulatoryBodyTransition, ArticulatoryBodyError> {
    if intervals.is_empty()
        || intervals
            .iter()
            .any(|(samples, _, _)| *samples == 0)
    {
        return Err(ArticulatoryBodyError::NoRecruitment);
    }
    let active_sample_count = intervals
        .iter()
        .try_fold(0usize, |total, (samples, _, _)| {
            total
                .checked_add(*samples)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)
        })?;
    let output_capacity = active_sample_count
        .checked_add(MAX_RELAXATION_SAMPLES)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    let mut right = [0_i32; TRACT_SECTION_COUNT];
    let mut left = [0_i32; TRACT_SECTION_COUNT];
    let mut previous_flow = 0_i32;
    let mut radiated = Vec::new();
    radiated
        .try_reserve_exact(output_capacity)
        .map_err(|_| ArticulatoryBodyError::ResourceUnavailable)?;
    let mut body_mechanics: [Vec<i16>; 4] = std::array::from_fn(|_| Vec::new());
    for trajectory in &mut body_mechanics {
        trajectory
            .try_reserve_exact(output_capacity)
            .map_err(|_| ArticulatoryBodyError::ResourceUnavailable)?;
    }
    let mut applied_motor_quanta = 0_u128;
    let mut stalled_motor_quanta = 0_u128;
    let mut strongest_glottal_apex = NEUTRAL_GLOTTAL_OPEN_SAMPLES;
    let mut strongest_areas = NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES;
    let mut strongest_peak_flow = 0_i32;
    let mut global_sample_index = 0usize;
    let mut any_recruitment = false;
    let mut final_areas = NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES;
    let mut final_body_channels = [0_i16; 3];

    for (interval_sample_count, recruitments, articulated_body) in intervals {
        any_recruitment |= !recruitments.is_empty();
        let magnitude = recruitments.iter().try_fold(
            0_u128,
            |total, (_topology_index, carriers)| {
                total
                    .checked_add(*carriers)
                    .ok_or(ArticulatoryBodyError::ArithmeticWidth)
            },
        )?;
        let applied = min(magnitude, 8);
        let stalled = magnitude - applied;
        applied_motor_quanta = applied_motor_quanta
            .checked_add(applied)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        stalled_motor_quanta = stalled_motor_quanta
            .checked_add(stalled)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        let applied_i32 = i32::try_from(applied)
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
        let glottal_apex = glottal_open_samples(articulated_body)?;
        let apex_areas = articulated_vocal_tract_areas(articulated_body)?;
        let peak_flow = round_div(
            i64::from(RESPIRATORY_PEAK_VOLUME_VELOCITY_PCM)
                * i64::from(applied_i32)
                * i64::from(articulated_body.lung_air_microlitres()),
            8 * i64::from(MAX_LUNG_AIR_MICROLITRES),
        )?;
        let body_channels = articulated_body_channels(articulated_body)?;
        final_areas = apex_areas;
        final_body_channels = body_channels;
        if peak_flow.unsigned_abs() > strongest_peak_flow.unsigned_abs() {
            strongest_glottal_apex = glottal_apex;
            strongest_areas = apex_areas;
            strongest_peak_flow = peak_flow;
        }

        for _interval_sample_index in 0..*interval_sample_count {
            let phase = global_sample_index % LARYNGEAL_CYCLE_SAMPLES;
            let flow = if magnitude != 0
                && phase
                    < usize::try_from(glottal_apex)
                        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
            {
                round_div(
                    i64::from(peak_flow)
                        * 4
                        * i64::try_from(phase)
                            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
                        * i64::from(
                            glottal_apex
                                - i32::try_from(phase)
                                    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
                        ),
                    i64::from(glottal_apex) * i64::from(glottal_apex),
                )?
            } else {
                0
            };
            let source_pressure = flow
                .checked_sub(previous_flow)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            previous_flow = flow;
            let areas = apex_areas;
            let (next_right, next_left, emitted) =
                advance_tube(right, left, areas, source_pressure)?;
            right = next_right;
            left = next_left;
            radiated.push(emitted);
            body_mechanics[0].push(
                i16::try_from(flow).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
            );
            body_mechanics[1].push(body_channels[0]);
            body_mechanics[2].push(body_channels[1]);
            body_mechanics[3].push(body_channels[2]);
            global_sample_index = global_sample_index
                .checked_add(1)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        }
    }
    if !any_recruitment {
        return Err(ArticulatoryBodyError::NoRecruitment);
    }
    let mut relaxation_sample_count = 0usize;
    while previous_flow != 0
        || right.iter().any(|value| *value != 0)
        || left.iter().any(|value| *value != 0)
    {
        if relaxation_sample_count == MAX_RELAXATION_SAMPLES {
            return Err(ArticulatoryBodyError::RelaxationDidNotQuiesce);
        }
        let source_pressure = previous_flow
            .checked_neg()
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        previous_flow = 0;
        let (next_right, next_left, emitted) = advance_tube(
            right,
            left,
            final_areas,
            source_pressure,
        )?;
        right = next_right;
        left = next_left;
        radiated.push(emitted);
        body_mechanics[0].push(0);
        body_mechanics[1].push(final_body_channels[0]);
        body_mechanics[2].push(final_body_channels[1]);
        body_mechanics[3].push(final_body_channels[2]);
        relaxation_sample_count += 1;
    }
    if body_mechanics
        .iter()
        .any(|trajectory| trajectory.len() != radiated.len())
    {
        return Err(ArticulatoryBodyError::ArithmeticWidth);
    }
    Ok(ArticulatoryBodyTransition {
        radiated_pressure_pcm: radiated,
        body_mechanical_trajectories: body_mechanics,
        peak_breath_flow_pcm: strongest_peak_flow,
        glottal_open_samples_at_apex: strongest_glottal_apex,
        mouth_area_square_millimetres_at_apex: strongest_areas[TRACT_SECTION_COUNT - 1],
        perioral_area_displacement_square_millimetres: i32::from(final_body_channels[2]),
        applied_motor_quanta,
        stalled_motor_quanta,
        relaxation_sample_count,
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
    let mut areas = *body.vocal_tract_areas_square_millimetres();
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

    #[test]
    fn one_real_discharge_uses_the_resident_body_and_radiates_pressure() {
        let settled = settle_articulatory_unit_discharge(&[(0, 13)]).unwrap();
        assert_eq!(settled.applied_motor_quanta, 8);
        assert_eq!(settled.stalled_motor_quanta, 5);
        assert_eq!(settled.glottal_open_samples_at_apex, 80);
        assert_eq!(settled.mouth_area_square_millimetres_at_apex, 20);
        assert_eq!(settled.perioral_area_displacement_square_millimetres, 0);
        assert!(settled.peak_breath_flow_pcm > 0);
        assert!(settled.radiated_pressure_pcm.iter().any(|value| *value != 0));
        assert!(settled.relaxation_sample_count <= MAX_RELAXATION_SAMPLES);
    }

    #[test]
    fn topology_ordinals_do_not_manufacture_opposed_motor_meaning() {
        let left = settle_articulatory_unit_discharge(&[(0, 3), (1, 3)]).unwrap();
        let right = settle_articulatory_unit_discharge(&[(41, 3), (82, 3)]).unwrap();
        assert_eq!(left, right);
        assert_eq!(left.applied_motor_quanta, 6);
    }

    #[test]
    fn causal_interval_timing_changes_the_physical_utterance() {
        let contiguous = settle_articulatory_interval_discharges(&[
            (4_000, vec![(0, 8)], ArticulatedBodyState::at_neutral()),
            (4_000, vec![(0, 8)], ArticulatedBodyState::at_neutral()),
        ])
        .unwrap();
        let separated = settle_articulatory_interval_discharges(&[
            (4_000, vec![(0, 8)], ArticulatedBodyState::at_neutral()),
            (4_000, vec![], ArticulatedBodyState::at_neutral()),
            (4_000, vec![(0, 8)], ArticulatedBodyState::at_neutral()),
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
                let recruitments = if matches!(index, 0 | 8 | 17 | 27 | 35 | 45) {
                    vec![(0, 8)]
                } else {
                    Vec::new()
                };
                (4_000, recruitments, ArticulatedBodyState::at_neutral())
            })
            .collect::<Vec<_>>();
        let settled = settle_articulatory_interval_discharges(&intervals).unwrap();

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
            *neutral.vocal_tract_areas_square_millimetres(),
            neutral.proprioception_initialized(),
        )
        .unwrap();
        let neutral_sound = settle_articulatory_interval_discharges(&[(
            4_000,
            vec![(0, 8)],
            neutral,
        )])
        .unwrap();
        let open_sound = settle_articulatory_interval_discharges(&[(
            4_000,
            vec![(0, 8)],
            open,
        )])
        .unwrap();
        assert_ne!(neutral_sound.radiated_pressure_pcm, open_sound.radiated_pressure_pcm);
        assert_ne!(
            neutral_sound.mouth_area_square_millimetres_at_apex,
            open_sound.mouth_area_square_millimetres_at_apex
        );
    }
}
