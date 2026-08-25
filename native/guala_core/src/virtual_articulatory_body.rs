//! Bounded exact virtual articulation driven by native layer-13 discharge.
//!
//! This is body mechanics, not language.  A transient whole-carrier discharge
//! moves one declared antagonist lattice, drives one finite exhalation through
//! an eight-section loss tube, and returns the pressure field to exact rest.
//! No phoneme, word, target waveform, retained program, or learned meaning is
//! present here.

use core::cmp::{max, min};

pub(crate) const ARTICULATORY_SAMPLE_RATE_HZ: u32 = 16_000;
const TRACT_SECTION_COUNT: usize = 8;
#[cfg(test)]
const ACTIVE_SAMPLE_COUNT: usize = ARTICULATORY_SAMPLE_RATE_HZ as usize;
const MAX_ARTICULATORY_DURATION_SECONDS: usize = 5;
const MAX_ACTIVE_SAMPLE_COUNT: usize =
    ARTICULATORY_SAMPLE_RATE_HZ as usize * MAX_ARTICULATORY_DURATION_SECONDS;
const MAX_RELAXATION_SAMPLES: usize = 16_384;
const LARYNGEAL_CYCLE_SAMPLES: usize = 160;
const NEUTRAL_GLOTTAL_OPEN_SAMPLES: i32 = 80;
const GLOTTAL_RESOLUTION_SAMPLES: i32 = 8;
const MIN_GLOTTAL_OPEN_SAMPLES: i32 = 16;
const MAX_GLOTTAL_OPEN_SAMPLES: i32 = 144;
const RESPIRATORY_PEAK_VOLUME_VELOCITY_PCM: i32 = 4_000;
const WALL_RETENTION_PARTS_PER_MILLION: i64 = 985_000;
const PARTS_PER_MILLION: i64 = 1_000_000;
const TRACT_RESOLUTION_SQUARE_MILLIMETRES: i32 = 5;
const NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES: [i32; TRACT_SECTION_COUNT] =
    [125, 145, 165, 185, 205, 225, 245, 265];
const RADIATION_LOAD_AREA_SQUARE_MILLIMETRES: i32 = 265;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ArticulatoryBodyError {
    NoRecruitment,
    CancelledRecruitment,
    ArithmeticWidth,
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

/// Settle an opposed layer-13 population into one finite articulatory act.
/// Even topology pulls the local lattice positive and odd topology pulls it
/// negative, matching the already-mounted antagonist convention used by the
/// native body. One whole carrier is one native actuator quantum. The eight
/// available quanta are the exact distance from neutral to either anatomical
/// stop; discharge beyond the stop is reported as stalled rather than silently
/// converted into more motion.
#[cfg(test)]
pub(crate) fn settle_articulatory_unit_discharge(
    recruitments: &[(u32, u128)],
) -> Result<ArticulatoryBodyTransition, ArticulatoryBodyError> {
    settle_articulatory_interval_discharges(&[(
        ACTIVE_SAMPLE_COUNT,
        recruitments.to_vec(),
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
    intervals: &[(usize, Vec<(u32, u128)>)],
) -> Result<ArticulatoryBodyTransition, ArticulatoryBodyError> {
    if intervals.is_empty() || intervals.iter().any(|(samples, _)| *samples == 0) {
        return Err(ArticulatoryBodyError::NoRecruitment);
    }
    let active_sample_count = intervals.iter().try_fold(0usize, |total, (samples, _)| {
        total
            .checked_add(*samples)
            .filter(|candidate| *candidate <= MAX_ACTIVE_SAMPLE_COUNT)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)
    })?;
    let mut right = [0_i32; TRACT_SECTION_COUNT];
    let mut left = [0_i32; TRACT_SECTION_COUNT];
    let mut previous_flow = 0_i32;
    let mut radiated = Vec::with_capacity(active_sample_count + MAX_RELAXATION_SAMPLES);
    let mut body_mechanics: [Vec<i16>; 4] = std::array::from_fn(|_| {
        Vec::with_capacity(active_sample_count + MAX_RELAXATION_SAMPLES)
    });
    let mut applied_motor_quanta = 0_u128;
    let mut stalled_motor_quanta = 0_u128;
    let mut strongest_applied = 0_u128;
    let mut strongest_glottal_apex = NEUTRAL_GLOTTAL_OPEN_SAMPLES;
    let mut strongest_areas = NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES;
    let mut strongest_peak_flow = 0_i32;
    let mut global_sample_index = 0usize;
    let mut any_recruitment = false;
    let mut any_uncancelled_recruitment = false;

    for (interval_sample_count, recruitments) in intervals {
        any_recruitment |= !recruitments.is_empty();
        let mut signed_quanta = 0_i128;
        for (topology_index, carriers) in recruitments.iter().copied() {
            let magnitude = i128::try_from(carriers)
                .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
            signed_quanta = if topology_index % 2 == 0 {
                signed_quanta.checked_add(magnitude)
            } else {
                signed_quanta.checked_sub(magnitude)
            }
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        }
        let magnitude = signed_quanta.unsigned_abs();
        let applied = min(magnitude, 8);
        let stalled = magnitude - applied;
        applied_motor_quanta = applied_motor_quanta
            .checked_add(applied)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        stalled_motor_quanta = stalled_motor_quanta
            .checked_add(stalled)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        any_uncancelled_recruitment |= signed_quanta != 0;
        let applied_i32 = i32::try_from(applied)
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
        let direction = if signed_quanta.is_negative() { -1 } else { 1 };
        let glottal_apex = if signed_quanta == 0 {
            NEUTRAL_GLOTTAL_OPEN_SAMPLES
        } else {
            NEUTRAL_GLOTTAL_OPEN_SAMPLES
                .checked_add(direction * GLOTTAL_RESOLUTION_SAMPLES * applied_i32)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?
        };
        if !(MIN_GLOTTAL_OPEN_SAMPLES..=MAX_GLOTTAL_OPEN_SAMPLES).contains(&glottal_apex) {
            return Err(ArticulatoryBodyError::ArithmeticWidth);
        }
        let area_delta = if signed_quanta == 0 {
            0
        } else {
            direction * TRACT_RESOLUTION_SQUARE_MILLIMETRES * applied_i32
        };
        let mut apex_areas = [0_i32; TRACT_SECTION_COUNT];
        for (index, neutral) in NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES
            .iter()
            .copied()
            .enumerate()
        {
            apex_areas[index] = neutral
                .checked_add(area_delta)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            if apex_areas[index] <= 0 {
                return Err(ArticulatoryBodyError::ArithmeticWidth);
            }
        }
        let peak_flow = RESPIRATORY_PEAK_VOLUME_VELOCITY_PCM
            .checked_mul(applied_i32)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?
            / 8;
        if applied > strongest_applied {
            strongest_applied = applied;
            strongest_glottal_apex = glottal_apex;
            strongest_areas = apex_areas;
            strongest_peak_flow = peak_flow;
        }

        for interval_sample_index in 0..*interval_sample_count {
            let phase = global_sample_index % LARYNGEAL_CYCLE_SAMPLES;
            let flow = if signed_quanta != 0
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
            let areas = interpolated_areas_for_extent(
                interval_sample_index,
                *interval_sample_count,
                &apex_areas,
            )?;
            let (next_right, next_left, emitted) =
                advance_tube(right, left, areas, source_pressure)?;
            right = next_right;
            left = next_left;
            radiated.push(emitted);
            body_mechanics[0].push(
                i16::try_from(flow).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
            );
            body_mechanics[1].push(
                i16::try_from(glottal_apex - NEUTRAL_GLOTTAL_OPEN_SAMPLES)
                    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
            );
            body_mechanics[2].push(
                i16::try_from(
                    areas[TRACT_SECTION_COUNT - 1]
                        - NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[TRACT_SECTION_COUNT - 1],
                )
                .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
            );
            body_mechanics[3].push(
                i16::try_from(areas[0] - NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[0])
                    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
            );
            global_sample_index = global_sample_index
                .checked_add(1)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        }
    }
    if !any_recruitment {
        return Err(ArticulatoryBodyError::NoRecruitment);
    }
    if !any_uncancelled_recruitment {
        return Err(ArticulatoryBodyError::CancelledRecruitment);
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
            NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES,
            source_pressure,
        )?;
        right = next_right;
        left = next_left;
        radiated.push(emitted);
        for trajectory in &mut body_mechanics {
            trajectory.push(0);
        }
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
        perioral_area_displacement_square_millimetres: strongest_areas[0]
            - NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[0],
        applied_motor_quanta,
        stalled_motor_quanta,
        relaxation_sample_count,
    })
}

fn interpolated_areas_for_extent(
    sample_index: usize,
    sample_count: usize,
    apex: &[i32; TRACT_SECTION_COUNT],
) -> Result<[i32; TRACT_SECTION_COUNT], ArticulatoryBodyError> {
    if sample_count == 0 || sample_index >= sample_count {
        return Err(ArticulatoryBodyError::ArithmeticWidth);
    }
    let final_index = sample_count - 1;
    let apex_index = final_index / 2;
    let (position, denominator) = if sample_index <= apex_index {
        (sample_index, apex_index)
    } else {
        (final_index - sample_index, final_index - apex_index)
    };
    let mut result = [0_i32; TRACT_SECTION_COUNT];
    for index in 0..TRACT_SECTION_COUNT {
        let neutral = NEUTRAL_TRACT_AREAS_SQUARE_MILLIMETRES[index];
        let delta = apex[index] - neutral;
        result[index] = neutral
            .checked_add(round_div(
                i64::from(delta)
                    * i64::try_from(position)
                        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
                i64::try_from(max(1, denominator))
                    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
            )?)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    }
    Ok(result)
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
    fn one_real_discharge_moves_body_radiates_pressure_and_returns_to_rest() {
        let settled = settle_articulatory_unit_discharge(&[(0, 13)]).unwrap();
        assert_eq!(settled.applied_motor_quanta, 8);
        assert_eq!(settled.stalled_motor_quanta, 5);
        assert_eq!(settled.glottal_open_samples_at_apex, 144);
        assert_eq!(settled.mouth_area_square_millimetres_at_apex, 305);
        assert_eq!(settled.perioral_area_displacement_square_millimetres, 40);
        assert!(settled.peak_breath_flow_pcm > 0);
        assert!(settled.radiated_pressure_pcm.iter().any(|value| *value != 0));
        assert!(settled.relaxation_sample_count <= MAX_RELAXATION_SAMPLES);
    }

    #[test]
    fn exact_antagonists_cancel_without_inventing_an_act() {
        assert_eq!(
            settle_articulatory_unit_discharge(&[(0, 3), (1, 3)]),
            Err(ArticulatoryBodyError::CancelledRecruitment)
        );
    }

    #[test]
    fn causal_interval_timing_changes_the_physical_utterance() {
        let contiguous = settle_articulatory_interval_discharges(&[
            (4_000, vec![(0, 8)]),
            (4_000, vec![(0, 8)]),
        ])
        .unwrap();
        let separated = settle_articulatory_interval_discharges(&[
            (4_000, vec![(0, 8)]),
            (4_000, vec![]),
            (4_000, vec![(0, 8)]),
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
}
