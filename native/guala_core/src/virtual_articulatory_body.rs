//! Bounded exact developmental acoustic actuation driven by native layer-13
//! discharge.
//!
//! This is body mechanics, not language. A transient whole-carrier discharge
//! from the resident respiratory effector supplies finite pressure while the
//! existing nine area controls directly shape the acoustic instrument. Jaw and
//! lip geometry no longer caps those controls; their body senses remain real.
//! Resonator damping and tube wall loss return every coordinate to exact rest.
//! No phoneme, word, target waveform, retained program, or learned meaning is
//! present here.

use core::cmp::{max, min};

use crate::passive_body_source::{PassiveBodyTrajectory, PassiveBodySourceError};

use crate::virtual_articulated_body::{
    settle_body_effector_drives, AdmittedBodyEffectorDrives, ArticulatedBodyState,
    ArticulatoryAcousticState, BodyAxis, BodyProprioceptiveConsequence,
    ACOUSTIC_TRANSDUCER_SURFACE_COUNT,
    BODY_SETTLEMENT_CLOCK_MICROSECONDS,
    MIN_LUNG_AIR_MICROLITRES,
    NEUTRAL_LUNG_AIR_MICROLITRES,
    MAX_TRACT_AREA_SQUARE_MILLIMETRES, MIN_TRACT_AREA_SQUARE_MILLIMETRES,
    MAX_SPECTRAL_RESPIRATORY_WORK, SPECTRAL_FLUID_CELL_COUNT, SPECTRAL_MODE_COUNT,
    SpectralAcousticState,
    VOCAL_TRACT_SECTION_COUNT,
};

pub(crate) const ARTICULATORY_SAMPLE_RATE_HZ: u32 = 16_000;
pub(crate) const NATIVE_ARTICULATORY_INTERVAL_SAMPLES: usize = 16;
const TRACT_SECTION_COUNT: usize = VOCAL_TRACT_SECTION_COUNT;
#[cfg(test)]
const ACTIVE_SAMPLE_COUNT: usize = ARTICULATORY_SAMPLE_RATE_HZ as usize;
#[cfg(test)]
// Test-only composition may have to observe a complete passive return from
// residual lung volume (10 s at the declared 150 mL/s return flow) as well as
// the final acoustic tail. Production never allocates this relaxation buffer.
const MAX_RELAXATION_SAMPLES: usize = 192_000;
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
const MAX_ARTICULATORY_INTERVAL_SAMPLES: usize = 480_000;
const BODY_CLOCK_SAMPLES: usize = ARTICULATORY_SAMPLE_RATE_HZ as usize / 1_000;
pub(crate) const MAX_PASSIVE_BODY_FRAMES: usize =
    1 + (MAX_ARTICULATORY_INTERVAL_SAMPLES - 1) / BODY_CLOCK_SAMPLES;
pub(crate) const MAX_PASSIVE_BODY_SOURCE_BYTES: usize =
    21 + crate::virtual_articulated_body::BODY_AXES.len()
        * (1 + std::mem::size_of::<i32>() * MAX_PASSIVE_BODY_FRAMES);
const FIXED_ONE: i64 = 1_i64 << 30;
#[derive(Clone, Copy)]
struct SpectralOrganMaterial {
    respiratory_work_per_efferent_carrier: i64,
    valve_rate_floor_hz: i64,
    valve_rate_ceiling_hz: i64,
    respiratory_rest_loss_per_sample: i64,
    internal_pressure_per_pcm: i64,
}

// One carrier starts a finite tissue contraction rather than setting pitch.
// The laryngeal material owns a narrow child-scale natural-frequency band;
// falling respiratory pressure bends that frequency only slightly.  The work
// quantum gives the copied body's ordinary two-carrier act approximately one
// bounded vocal gesture while larger discharges saturate the existing fixed
// respiratory-work anatomy.
const SPECTRAL_ORGAN_MATERIAL: SpectralOrganMaterial = SpectralOrganMaterial {
    respiratory_work_per_efferent_carrier: 1_536_000,
    valve_rate_floor_hz: 352,
    valve_rate_ceiling_hz: 376,
    respiratory_rest_loss_per_sample: 256,
    internal_pressure_per_pcm: 1,
};
// The mounted body receptor declares a 4,000-unit respiratory volume-
// velocity span. Native values are millilitres/second; at 16 kHz one raw
// flow count therefore exhausts exactly one sixteenth microlitre. A retained
// remainder makes that conversion exact across interval/restart boundaries.
const RESPIRATORY_FLOW_SAMPLES_PER_MICROLITRE: u32 = 16;
// Quiet tidal measurements in young children put ordinary inspiratory flow
// near 100-150 mL/s.  The upper measured value is the fixed material return
// rate here: vocal expiration pushes the virtual chest below its declared
// neutral volume, and elastic return admits the displaced ambient air at this
// bounded rate after phonatory work exhausts.
const PASSIVE_INSPIRATORY_FLOW_MILLILITRES_PER_SECOND: i32 = 150;
// ---- Joe-directed minimal persistent valve organ (2026-09-02) ----------
// One virtual organ oscillator, not simulated fold anatomy. The cycle
// advances only while paid respiratory work remains; its shape is the
// human-accepted v22 source class: open ~0.708 of the cycle, conductance
// peaking smoothly at ~0.455, closing faster with smooth ends, exactly
// zero for the closed ~0.292. Rate spans the accepted child range and
// declines with the same finite work that supplies pressure. These are
// common organ properties, not a phoneme, pitch arc, or target table.
const VALVE_CYCLE_ONE: i64 = 1_048_576;
const VALVE_PEAK_POSITION: i64 = 477_102; // 0.455 of the unit cycle
const VALVE_OPEN_END_POSITION: i64 = 742_392; // 0.708 of the unit cycle
const VALVE_CONDUCTANCE_ONE: i64 = FOLD_POSITION_SCALE;
const FOLD_POSITION_SCALE: i64 = 1_536;
const FOLD_COLLISION_LIMIT: i64 = 3_072;
const FLOW_TO_INTERNAL_PRESSURE: i32 = 131_072;
const MODE_FREQUENCY_RANGES_HZ: [(i32, i32); SPECTRAL_MODE_COUNT] = [
    (300, 1_200),
    (900, 3_400),
    (2_500, 4_000),
    (4_000, 4_800),
    (5_000, 6_000),
];
const MODE_BANDWIDTHS_HZ: [i32; SPECTRAL_MODE_COUNT] = [180, 160, 260, 340, 400];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ArticulatoryBodyError {
    NoRecruitment,
    ArithmeticWidth,
    ResourceUnavailable,
    RelaxationDidNotQuiesce,
    PressureOutsideAudioWidth,
    PassiveSource(PassiveBodySourceError),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ArticulatoryBodyTransition {
    pub(crate) radiated_pressure_pcm: Vec<i16>,
    /// Port-major local body mechanics at the same sample instants as the
    /// radiated pressure: respiratory flow, glottal configuration
    /// displacement, oral aperture displacement, and perioral skin
    /// displacement. Port zero is the respiratory flow physically funded by
    /// the resident layer-13 effector; body displacement cannot manufacture it.
    pub(crate) body_mechanical_trajectories: [Vec<i16>; 4],
    pub(crate) peak_transducer_surface_velocity_pcm: i32,
    pub(crate) glottal_open_samples_at_apex: i32,
    /// Existing observation field: final direct section-7 outlet area, not
    /// an area reconstructed from jaw/lip geometry or a new semantic signal.
    pub(crate) mouth_area_square_millimetres_at_apex: i32,
    pub(crate) perioral_area_displacement_square_millimetres: i32,
    pub(crate) applied_motor_quanta: u128,
    pub(crate) stalled_motor_quanta: u128,
    pub(crate) relaxation_sample_count: usize,
    pub(crate) successor_body: ArticulatedBodyState,
    /// Transient exact samples; the runtime moves these into its existing
    /// pending sensory return before retaining acoustic observation.
    pub(crate) passive_body_trajectory: Option<PassiveBodyTrajectory>,
}

/// Advance the vocal body across one exact causal source interval.
///
/// Already-settled typed layer-12 motor consequences alter only resident body
/// posture. Respiratory work is admitted independently from actual discharge
/// of the persisted layer-13 body effector. This is body anatomy, not a phoneme
/// map: posture shapes the valve and tube, while finite respiratory work pays
/// for pressure. The persisted organ carries the consequence across interval
/// and restart boundaries without a shell phase clock or duration counter.
pub(crate) fn settle_native_articulatory_interval(
    articulated_body: ArticulatedBodyState,
    body_consequences: &[BodyProprioceptiveConsequence],
    respiratory_efferent_carriers: u128,
    interval_sample_count: usize,
) -> Result<ArticulatoryBodyTransition, ArticulatoryBodyError> {
    settle_native_articulatory_interval_with_material(
        articulated_body,
        body_consequences,
        respiratory_efferent_carriers,
        interval_sample_count,
        SPECTRAL_ORGAN_MATERIAL,
    )
}

fn settle_native_articulatory_interval_with_material(
    mut articulated_body: ArticulatedBodyState,
    body_consequences: &[BodyProprioceptiveConsequence],
    respiratory_efferent_carriers: u128,
    interval_sample_count: usize,
    material: SpectralOrganMaterial,
) -> Result<ArticulatoryBodyTransition, ArticulatoryBodyError> {
    if interval_sample_count == 0 || interval_sample_count > MAX_ARTICULATORY_INTERVAL_SAMPLES {
        return Err(ArticulatoryBodyError::NoRecruitment);
    }
    let frame_count = 1 + (interval_sample_count - 1) / BODY_CLOCK_SAMPLES;
    let mut passive_body_trajectory = PassiveBodyTrajectory::begin(
        &articulated_body, frame_count, MAX_PASSIVE_BODY_SOURCE_BYTES,
    ).map_err(ArticulatoryBodyError::PassiveSource)?;
    let mut acoustic = articulated_body.articulatory_acoustic_state();
    let mut lung_air_microlitres = articulated_body.lung_air_microlitres();
    let mut applied = 0_u128;
    let mut stalled = 0_u128;
    for consequence in body_consequences {
        match &mut acoustic {
            ArticulatoryAcousticState::LegacyV6(legacy) => {
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
                legacy.surface_previous_displacement[surface_index] = legacy
                    .surface_previous_displacement[surface_index]
                    .checked_sub(impulse)
                    .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            }
            // Spectral articulation reads the already-settled body posture
            // below. A glottal or tract movement is shape, not respiratory
            // work. In particular, the gustatory swallowing reflex must close
            // the airway without manufacturing breath or voiced pressure.
            ArticulatoryAcousticState::Spectral(_) => {}
        }
    }
    match &mut acoustic {
        ArticulatoryAcousticState::Spectral(spectral) => {
            // A below-equilibrium chest is in its physical return stroke.
            // More expiratory discharge cannot create air or reverse that
            // stroke; it stalls until the same lung reaches neutral again.
            let coupled = if lung_air_microlitres == NEUTRAL_LUNG_AIR_MICROLITRES
                && spectral.expiratory_volume_remainder_sixteenths_microlitre == 0
            {
                min(respiratory_efferent_carriers, 8)
            } else {
                0
            };
            applied = applied
                .checked_add(coupled)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            stalled = stalled
                .checked_add(respiratory_efferent_carriers - coupled)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
            if coupled != 0 {
                let added_work = i64::try_from(coupled)
                    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
                    .checked_mul(material.respiratory_work_per_efferent_carrier)
                    .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
                spectral.respiratory_work_remaining = min(
                    MAX_SPECTRAL_RESPIRATORY_WORK,
                    spectral
                        .respiratory_work_remaining
                        .checked_add(added_work)
                        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?,
                );
            }
        }
        ArticulatoryAcousticState::LegacyV6(_) => {
            stalled = stalled
                .checked_add(respiratory_efferent_carriers)
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        }
    }
    let glottal_apex = glottal_open_samples(&articulated_body)?;
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
    for interval_sample_index in 0..interval_sample_count {
        if interval_sample_index != 0 && interval_sample_index % BODY_CLOCK_SAMPLES == 0 {
            let settled = settle_body_effector_drives(
                &articulated_body,
                &AdmittedBodyEffectorDrives::quiescent(),
                BODY_SETTLEMENT_CLOCK_MICROSECONDS,
            )
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
            if let Some(trajectory) = passive_body_trajectory.as_mut() {
                trajectory.append_quiescent(&settled)
                    .map_err(ArticulatoryBodyError::PassiveSource)?;
            }
            articulated_body = settled.successor;
        }
        let areas = articulated_body.vocal_tract_areas_square_millimetres();
        let body_channels = articulated_body_channels(&articulated_body)?;
        let mut legacy_reached_rest = false;
        let mut respiratory_flow_sample = 0_i16;
        let emitted = match &mut acoustic {
            ArticulatoryAcousticState::LegacyV6(legacy) => {
                let mut source_pressure = 0_i32;
                for surface_index in 0..ACOUSTIC_TRANSDUCER_SURFACE_COUNT {
                    let current = legacy.surface_displacement[surface_index];
                    let previous = legacy.surface_previous_displacement[surface_index];
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
                    let next = i32::try_from(numerator / denominator)
                        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
                    let velocity = next
                        .checked_sub(current)
                        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
                    legacy.surface_previous_displacement[surface_index] = current;
                    legacy.surface_displacement[surface_index] = next;
                    source_pressure = source_pressure
                        .checked_add(velocity)
                        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
                    if velocity.unsigned_abs() > strongest_surface_velocity.unsigned_abs() {
                        strongest_surface_velocity = velocity;
                    }
                }
                let (next_right, next_left, emitted) = advance_tube(
                    legacy.right_traveling_pressure,
                    legacy.left_traveling_pressure,
                    areas,
                    source_pressure,
                )?;
                legacy.right_traveling_pressure = next_right;
                legacy.left_traveling_pressure = next_left;
                legacy_reached_rest = legacy.is_quiescent();
                emitted
            }
            ArticulatoryAcousticState::Spectral(spectral) => {
                let (emitted, flow, fold_velocity) = advance_spectral_organ(
                    spectral,
                    articulated_body.axis(BodyAxis::GlottalAperture),
                    areas,
                    &mut lung_air_microlitres,
                    material,
                )?;
                respiratory_flow_sample = flow;
                if fold_velocity.unsigned_abs() > strongest_surface_velocity.unsigned_abs() {
                    strongest_surface_velocity = fold_velocity;
                }
                emitted
            }
        };
        if legacy_reached_rest {
            acoustic = ArticulatoryAcousticState::at_rest();
        }
        radiated.push(emitted);
        body_mechanics[0].push(respiratory_flow_sample);
        body_mechanics[1].push(body_channels[0]);
        body_mechanics[2].push(body_channels[1]);
        body_mechanics[3].push(body_channels[2]);
    }
    let terminal_areas = articulated_body.vocal_tract_areas_square_millimetres();
    let terminal_body_channels = articulated_body_channels(&articulated_body)?;
    let successor_body = articulated_body
        .with_respiratory_successor(acoustic, lung_air_microlitres)
        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    Ok(ArticulatoryBodyTransition {
        radiated_pressure_pcm: radiated,
        body_mechanical_trajectories: body_mechanics,
        peak_transducer_surface_velocity_pcm: strongest_surface_velocity,
        glottal_open_samples_at_apex: glottal_apex,
        mouth_area_square_millimetres_at_apex: terminal_areas[TRACT_SECTION_COUNT - 1],
        perioral_area_displacement_square_millimetres: i32::from(terminal_body_channels[2]),
        applied_motor_quanta: applied,
        stalled_motor_quanta: stalled,
        relaxation_sample_count: 0,
        successor_body,
        passive_body_trajectory,
    })
}

/// Test-only composition of the production interval law. It owns no second
/// acoustic implementation: every active and relaxing sample crosses
/// `settle_native_articulatory_interval`, preserving the same resident state
/// that production persists.
#[cfg(test)]
pub(crate) fn settle_physical_transducer_interval_discharges(
    intervals: &[(
        usize,
        u128,
        Vec<BodyProprioceptiveConsequence>,
        ArticulatedBodyState,
    )],
) -> Result<ArticulatoryBodyTransition, ArticulatoryBodyError> {
    if intervals.is_empty()
        || intervals.iter().any(|(samples, _, _, _)| *samples == 0)
        || intervals
            .iter()
            .all(|(_, respiratory, consequences, _)| {
                *respiratory == 0 && consequences.is_empty()
            })
    {
        return Err(ArticulatoryBodyError::NoRecruitment);
    }
    let active_sample_count =
        intervals
            .iter()
            .try_fold(0usize, |total, (samples, _, _, _)| {
                total
                    .checked_add(*samples)
                    .ok_or(ArticulatoryBodyError::ArithmeticWidth)
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
    let mut acoustic = intervals[0].3.articulatory_acoustic_state();
    let mut final_body = intervals[0].3.clone();
    let mut applied_motor_quanta = 0_u128;
    let mut stalled_motor_quanta = 0_u128;
    let mut strongest_surface_velocity = 0_i32;
    let mut strongest_glottal_apex = 0_i32;
    let mut strongest_mouth_area = 0_i32;
    let mut final_perioral_area = 0_i32;

    for (samples, respiratory, consequences, body) in intervals {
        let body = body.clone().with_articulatory_acoustic_state(acoustic)
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
        let settled = settle_native_articulatory_interval(
            body,
            consequences,
            *respiratory,
            *samples,
        )?;
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
    while !final_body.articulatory_system_is_quiescent() {
        if relaxation_sample_count == MAX_RELAXATION_SAMPLES {
            return Err(ArticulatoryBodyError::RelaxationDidNotQuiesce);
        }
        let settled = settle_native_articulatory_interval(final_body.clone(), &[], 0, 1)?;
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
        // A test composition spans separate acts, not one pending return.
        passive_body_trajectory: None,
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

/// Advance the present body-owned voice by one acoustic sample. The only
/// continuing source is bounded respiratory work loaded by the resident
/// respiratory effector. The tract coordinates derive five lossy mechanical
/// modes; no sound name, target spectrum, phase clock, or waveform is present.
fn advance_spectral_organ(
    state: &mut SpectralAcousticState,
    glottal_area_square_millimetres: i32,
    tract_areas: [i32; TRACT_SECTION_COUNT],
    lung_air_microlitres: &mut u32,
    material: SpectralOrganMaterial,
) -> Result<(i16, i16, i32), ArticulatoryBodyError> {
    let work_active = state.respiratory_work_remaining > 0;
    let work_fraction = if work_active {
        min(
            FIXED_ONE,
            i64::try_from(
                (i128::from(state.respiratory_work_remaining) * i128::from(FIXED_ONE)
                    / i128::from(MAX_SPECTRAL_RESPIRATORY_WORK))
                    .max(0),
            )
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
        )
    } else {
        0
    };
    let mut strongest_fold_velocity = 0_i32;
    // State reuse in the rejected candidate's exact 16-byte slot:
    //   fold_displacement[0]          valve cycle position, 0..VALVE_CYCLE_ONE
    //   fold_displacement[1]          exact fractional-step remainder, 0..SR-1
    //   fold_previous_displacement[0] present valve conductance
    //   fold_previous_displacement[1] prior valve conductance
    if work_active {
        let rate_hz = material.valve_rate_floor_hz
            + (material.valve_rate_ceiling_hz - material.valve_rate_floor_hz)
                * i64::from(work_fraction)
                / i64::from(FIXED_ONE);
        let sample_rate = i64::from(ARTICULATORY_SAMPLE_RATE_HZ);
        let step_numerator = rate_hz
            .checked_mul(VALVE_CYCLE_ONE)
            .and_then(|value| value.checked_add(i64::from(state.fold_displacement[1])))
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        let mut position = i64::from(state.fold_displacement[0])
            .checked_add(step_numerator / sample_rate)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        let remainder = step_numerator % sample_rate;
        position %= VALVE_CYCLE_ONE;
        // Smooth rise to the peak, faster smooth fall to closure, exact
        // zero through the closed span. smoothstep t*t*(3-2t) has zero
        // slope at both ends: no hard corner sprays fold-over grit.
        let conductance = |pos: i64| -> Result<i64, ArticulatoryBodyError> {
            let (span_pos, span_len) = if pos < VALVE_PEAK_POSITION {
                (pos, VALVE_PEAK_POSITION)
            } else if pos < VALVE_OPEN_END_POSITION {
                (
                    VALVE_OPEN_END_POSITION - pos,
                    VALVE_OPEN_END_POSITION - VALVE_PEAK_POSITION,
                )
            } else {
                return Ok(0);
            };
            let t = i128::from(span_pos) * 32_768 / i128::from(span_len);
            let smooth = t * t * (3 * 32_768 - 2 * t) / (32_768_i128 * 32_768);
            i64::try_from(i128::from(VALVE_CONDUCTANCE_ONE) * smooth / 32_768)
                .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)
        };
        let next_conductance = conductance(position)?;
        let prior_conductance = state.fold_previous_displacement[0];
        state.fold_displacement[0] =
            i32::try_from(position).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
        state.fold_displacement[1] =
            i32::try_from(remainder).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
        state.fold_previous_displacement[1] = prior_conductance;
        state.fold_previous_displacement[0] =
            i32::try_from(next_conductance).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
        let velocity = state.fold_previous_displacement[0]
            .checked_sub(prior_conductance)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        if velocity.unsigned_abs() > strongest_fold_velocity.unsigned_abs() {
            strongest_fold_velocity = velocity;
        }
    } else {
        // Zero work stops further cycling. Ordinary loss returns every
        // coordinate to exact zero; a later motor act begins from rest.
        for slot in 0..2 {
            let decayed = i64::from(state.fold_displacement[slot]) * 985 / 1_000;
            state.fold_displacement[slot] =
                i32::try_from(if decayed.unsigned_abs() <= 1 { 0 } else { decayed })
                    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
            let conductance_decayed =
                i64::from(state.fold_previous_displacement[slot]) * 985 / 1_000;
            state.fold_previous_displacement[slot] = i32::try_from(
                if conductance_decayed.unsigned_abs() <= 1 { 0 } else { conductance_decayed },
            )
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
        }
    }

    let glottal_anatomy = BodyAxis::GlottalAperture.anatomy();
    let distance_from_closed = glottal_area_square_millimetres
        .checked_sub(glottal_anatomy.minimum)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    let distance_from_open = glottal_anatomy.maximum
        .checked_sub(glottal_area_square_millimetres)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    let anatomical_gate = max(0, min(distance_from_closed, distance_from_open));
    // The valve's conductance modulates the entire airway: the closed
    // span passes exactly zero flow, which is what carries the harmonic
    // train (the accepted closed-phase physics).
    let opening = if anatomical_gate == 0 {
        0
    } else {
        i64::from(anatomical_gate)
            .checked_mul(16)
            .map(|value| {
                value * i64::from(state.fold_previous_displacement[0])
                    / VALVE_CONDUCTANCE_ONE
            })
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?
    };
    let breath_pressure = if work_active {
        512_i64
            .checked_add(min(
                2_048,
                state.respiratory_work_remaining / 1_000,
            ))
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?
    } else {
        0
    };
    let candidate_volume_flow = if work_active {
        i32::try_from(
            i128::from(breath_pressure) * i128::from(opening)
                / i128::from(FOLD_POSITION_SCALE),
        )
        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
    } else if *lung_air_microlitres < NEUTRAL_LUNG_AIR_MICROLITRES
        || state.expiratory_volume_remainder_sixteenths_microlitre > 0
    {
        -PASSIVE_INSPIRATORY_FLOW_MILLILITRES_PER_SECOND
    } else {
        0
    };
    let retained_remainder =
        i64::from(state.expiratory_volume_remainder_sixteenths_microlitre);
    let volume_flow = if candidate_volume_flow >= 0 {
        let available_sixteenths = i64::from(
            lung_air_microlitres
                .checked_sub(MIN_LUNG_AIR_MICROLITRES)
                .and_then(|available| {
                    available.checked_mul(RESPIRATORY_FLOW_SAMPLES_PER_MICROLITRE)
                })
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?,
        )
        .checked_sub(retained_remainder)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        i32::try_from(min(i64::from(candidate_volume_flow), available_sixteenths))
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
    } else {
        let fillable_sixteenths = i64::from(
            NEUTRAL_LUNG_AIR_MICROLITRES
                .checked_sub(*lung_air_microlitres)
                .and_then(|deficit| {
                    deficit.checked_mul(RESPIRATORY_FLOW_SAMPLES_PER_MICROLITRE)
                })
                .ok_or(ArticulatoryBodyError::ArithmeticWidth)?,
        )
        .checked_add(retained_remainder)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        -i32::try_from(min(
            i64::from(candidate_volume_flow).unsigned_abs(),
            u64::try_from(fillable_sixteenths)
                .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
        ))
        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
    };
    let accumulated_sixteenths = retained_remainder
        .checked_add(i64::from(volume_flow))
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    let whole_microlitres = accumulated_sixteenths
        / i64::from(RESPIRATORY_FLOW_SAMPLES_PER_MICROLITRE);
    if whole_microlitres >= 0 {
        *lung_air_microlitres = lung_air_microlitres
            .checked_sub(
                u32::try_from(whole_microlitres)
                    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
            )
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    } else {
        *lung_air_microlitres = lung_air_microlitres
            .checked_add(
                u32::try_from(whole_microlitres.unsigned_abs())
                    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?,
            )
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    }
    state.expiratory_volume_remainder_sixteenths_microlitre = i32::try_from(
        accumulated_sixteenths
            % i64::from(RESPIRATORY_FLOW_SAMPLES_PER_MICROLITRE),
    )
    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    if work_active {
        let flow_loss = i64::from(volume_flow).unsigned_abs() / 32;
        let total_loss = material.respiratory_rest_loss_per_sample
            .checked_add(i64::try_from(flow_loss).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        state.respiratory_work_remaining = max(
            0,
            state
                .respiratory_work_remaining
                .checked_sub(total_loss)
                .unwrap_or(0),
        );
    }

    let previous_loss = state.source_loss[0];
    let softened_flow = i32::try_from(
        (5_i64 * i64::from(previous_loss) + 3_i64 * i64::from(volume_flow)) / 8,
    )
    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    state.source_loss[1] = previous_loss;
    state.source_loss[0] = softened_flow;
    let flow_radiation = softened_flow
        .checked_sub(previous_loss)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    let turbulence = advance_spectral_fluid_cells(state, volume_flow, tract_areas)?;
    let source_pressure = flow_radiation
        .checked_add(turbulence)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    let mut signal = source_pressure
        .checked_mul(FLOW_TO_INTERNAL_PRESSURE)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;

    for mode in 0..SPECTRAL_MODE_COUNT {
        let area = tract_areas[mode];
        let (minimum_hz, maximum_hz) = MODE_FREQUENCY_RANGES_HZ[mode];
        let frequency_hz = minimum_hz
            .checked_add(round_div(
                i64::from(area - MIN_TRACT_AREA_SQUARE_MILLIMETRES)
                    * i64::from(maximum_hz - minimum_hz),
                i64::from(
                    MAX_TRACT_AREA_SQUARE_MILLIMETRES
                        - MIN_TRACT_AREA_SQUARE_MILLIMETRES,
                ),
            )?)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        signal = advance_spectral_mode(
            signal,
            &mut state.mode_displacement[mode],
            &mut state.mode_previous_displacement[mode],
            frequency_hz,
            MODE_BANDWIDTHS_HZ[mode],
        )?;
    }

    let mouth_area = tract_areas[TRACT_SECTION_COUNT - 1];
    let lips_closed = mouth_area <= 60;
    for stage in 0..2 {
        let old = state.lip_low_pass[stage];
        let mut next = if lips_closed {
            old.checked_add(round_div(
                i64::from(signal - old) * 3_071,
                16_000,
            )?)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?
        } else {
            signal
        };
        if signal == 0 && next.unsigned_abs() <= 1 {
            next = 0;
        }
        state.lip_low_pass[stage] = next;
        signal = next;
    }
    for stage in 0..2 {
        let old = state.band_limit[stage];
        let mut next = old
            .checked_add(round_div(
                i64::from(signal - old) * 11_650,
                16_000,
            )?)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        if signal == 0 && next.unsigned_abs() <= 1 {
            next = 0;
        }
        state.band_limit[stage] = next;
        signal = next;
    }

    if state.respiratory_work_remaining == 0
        && state.fold_displacement.iter().all(|value| value.unsigned_abs() <= 1)
        && state.fold_previous_displacement.iter().all(|value| value.unsigned_abs() <= 1)
    {
        state.fold_displacement = [0; 2];
        state.fold_previous_displacement = [0; 2];
    }
    let emitted = i16::try_from(round_div(
        i64::from(signal),
        material.internal_pressure_per_pcm,
    )?)
        .map_err(|_| ArticulatoryBodyError::PressureOutsideAudioWidth)?;
    let flow_sample = i16::try_from(volume_flow)
        .map_err(|_| ArticulatoryBodyError::PressureOutsideAudioWidth)?;
    Ok((emitted, flow_sample, strongest_fold_velocity))
}

fn advance_spectral_fluid_cells(
    state: &mut SpectralAcousticState,
    volume_flow: i32,
    tract_areas: [i32; TRACT_SECTION_COUNT],
) -> Result<i32, ArticulatoryBodyError> {
    let old = state.fluid_cells;
    let mut next = [0_i32; SPECTRAL_FLUID_CELL_COUNT];
    let flow_magnitude = i64::from(volume_flow).unsigned_abs();
    let mut emitted = 0_i64;
    for wake in 0..SPECTRAL_FLUID_CELL_COUNT / 2 {
        let coordinate = wake * 2;
        let area = min(tract_areas[coordinate], tract_areas[coordinate + 1]);
        let constriction = i64::from(MAX_TRACT_AREA_SQUARE_MILLIMETRES - area);
        let shedding_hz = 1_100_i32
            .checked_add(
                i32::try_from(wake)
                    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
                    .checked_mul(950)
                    .ok_or(ArticulatoryBodyError::ArithmeticWidth)?,
            )
            .and_then(|value| {
                value.checked_add(
                    i32::try_from(min(
                        900_u64,
                        flow_magnitude
                            .checked_mul(64)?
                            / u64::try_from(max(area, MIN_TRACT_AREA_SQUARE_MILLIMETRES)).ok()?,
                    ))
                    .ok()?,
                )
            })
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
        let mut current = old[coordinate];
        let mut previous = old[coordinate + 1];
        if volume_flow == 0 || constriction == 0 {
            let _ = advance_spectral_mode(
                0,
                &mut current,
                &mut previous,
                shedding_hz,
                700,
            )?;
        } else {
            if current == 0 && previous == 0 {
                current = volume_flow.signum()
                    * (17
                        + i32::try_from(wake)
                            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
                            * 5);
            }
            let velocity = i64::from(current - previous);
            let theta_q30 = i128::from(
                2_i64
                    .checked_mul(355)
                    .and_then(|value| value.checked_mul(i64::from(shedding_hz)))
                    .ok_or(ArticulatoryBodyError::ArithmeticWidth)?,
            ) * i128::from(FIXED_ONE)
                / (113_i128 * i128::from(ARTICULATORY_SAMPLE_RATE_HZ));
            let stiffness_q30 = theta_q30 * theta_q30 / i128::from(FIXED_ONE);
            let target = max(
                192_i64,
                min(
                    2_048,
                    i64::try_from(flow_magnitude)
                        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
                        .checked_mul(constriction)
                        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?
                        / i64::from(max(area, MIN_TRACT_AREA_SQUARE_MILLIMETRES))
                        / 8,
                ),
            );
            let target_square = i128::from(target * target);
            let current_square = i128::from(current) * i128::from(current);
            let nonlinear_extent = target_square - current_square;
            let wake_drive = i128::from(velocity)
                * 24_000_000_i128
                * nonlinear_extent
                / target_square
                / i128::from(FIXED_ONE);
            let viscous_loss =
                i128::from(velocity) * 3_000_000_i128 / i128::from(FIXED_ONE);
            let upstream_coupling = if wake == 0 {
                0
            } else {
                i128::from(old[coordinate - 2] - old[coordinate - 1]) / 12
            };
            let restoring =
                -(stiffness_q30 * i128::from(current) / i128::from(FIXED_ONE));
            let candidate = i128::from(current)
                + i128::from(velocity)
                + restoring
                + wake_drive
                - viscous_loss
                + upstream_coupling;
            let bounded = max(-4_096_i128, min(4_096_i128, candidate));
            let successor = i32::try_from(bounded)
                .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
            previous = current;
            current = successor;
        }
        next[coordinate] = current;
        next[coordinate + 1] = previous;
        emitted = emitted
            .checked_add(
                i64::from(current - previous)
                    .checked_mul(constriction)
                    .ok_or(ArticulatoryBodyError::ArithmeticWidth)?
                    / 980,
            )
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    }
    state.fluid_cells = next;
    i32::try_from(emitted).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)
}

fn advance_spectral_mode(
    input: i32,
    current: &mut i32,
    previous: &mut i32,
    frequency_hz: i32,
    bandwidth_hz: i32,
) -> Result<i32, ArticulatoryBodyError> {
    let theta_q30 = i64::try_from(
        2_i128 * 355_i128 * i128::from(frequency_hz) * i128::from(FIXED_ONE)
            / (113_i128 * i128::from(ARTICULATORY_SAMPLE_RATE_HZ)),
    )
    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    let cosine = cosine_q30(theta_q30)?;
    let double_cosine = cosine_q30(
        theta_q30
            .checked_mul(2)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?,
    )?;
    let damping_extent = i64::try_from(
        355_i128 * i128::from(bandwidth_hz) * i128::from(FIXED_ONE)
            / (113_i128 * i128::from(ARTICULATORY_SAMPLE_RATE_HZ)),
    )
    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    let radius = FIXED_ONE
        .checked_sub(damping_extent)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    let a1 = i64::try_from(
        2_i128 * i128::from(radius) * i128::from(cosine) / i128::from(FIXED_ONE),
    )
    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    let a2 = -i64::try_from(
        i128::from(radius) * i128::from(radius) / i128::from(FIXED_ONE),
    )
    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    let radicand = i128::from(FIXED_ONE)
        - 2_i128 * i128::from(radius) * i128::from(double_cosine)
            / i128::from(FIXED_ONE)
        + i128::from(radius) * i128::from(radius) / i128::from(FIXED_ONE);
    if radicand < 0 {
        return Err(ArticulatoryBodyError::ArithmeticWidth);
    }
    let root = integer_square_root(
        u128::try_from(radicand)
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
            .checked_shl(30)
            .ok_or(ArticulatoryBodyError::ArithmeticWidth)?,
    );
    let gain = i64::try_from(
        i128::from(FIXED_ONE - radius) * i128::try_from(root)
            .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?
            / i128::from(FIXED_ONE),
    )
    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    let output = i32::try_from(
        (i128::from(gain) * i128::from(input)
            + i128::from(a1) * i128::from(*current)
            + i128::from(a2) * i128::from(*previous))
            / i128::from(FIXED_ONE),
    )
    .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    *previous = *current;
    *current = output;
    Ok(output)
}

fn cosine_q30(mut angle_q30: i64) -> Result<i64, ArticulatoryBodyError> {
    let pi_q30 = i64::try_from(355_i128 * i128::from(FIXED_ONE) / 113_i128)
        .map_err(|_| ArticulatoryBodyError::ArithmeticWidth)?;
    let two_pi_q30 = pi_q30
        .checked_mul(2)
        .ok_or(ArticulatoryBodyError::ArithmeticWidth)?;
    angle_q30 %= two_pi_q30;
    if angle_q30 > pi_q30 {
        angle_q30 -= two_pi_q30;
    } else if angle_q30 < -pi_q30 {
        angle_q30 += two_pi_q30;
    }
    let x = i128::from(angle_q30);
    let one = i128::from(FIXED_ONE);
    let x2 = x * x / one;
    let mut power = one;
    let mut result = one;
    for (order, denominator, positive) in [
        (2_i32, 2_i128, false),
        (4, 24, true),
        (6, 720, false),
        (8, 40_320, true),
        (10, 3_628_800, false),
        (12, 479_001_600, true),
        (14, 87_178_291_200, false),
    ] {
        let _ = order;
        power = power * x2 / one;
        let term = power / denominator;
        result = if positive { result + term } else { result - term };
    }
    i64::try_from(result).map_err(|_| ArticulatoryBodyError::ArithmeticWidth)
}

fn integer_square_root(value: u128) -> u128 {
    if value < 2 {
        return value;
    }
    let mut low = 1_u128;
    let mut high = 1_u128 << ((128 - value.leading_zeros() + 1) / 2);
    while low + 1 < high {
        let middle = (low + high) / 2;
        if middle <= value / middle {
            low = middle;
        } else {
            high = middle;
        }
    }
    low
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
        BodyEffectorDrive, BodyEffectorTerminal, BODY_AXIS_COUNT,
        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
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
        let transition =
            settle_body_effector_drives(predecessor, &admitted, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
                .unwrap();
        (transition.successor, transition.proprioceptive_consequences)
    }

    fn active_interval(
        predecessor: ArticulatedBodyState,
        axis: BodyAxis,
        direction: BodyEffectorDirection,
        body_carriers: u128,
        respiratory_carriers: u128,
        samples: usize,
    ) -> ArticulatoryBodyTransition {
        let (body, consequences) = moved(&predecessor, axis, direction, body_carriers);
        settle_native_articulatory_interval(
            body,
            &consequences,
            respiratory_carriers,
            samples,
        )
        .unwrap()
    }


    #[test]
    fn direct_acoustic_controls_preserve_identity_and_bypass_jaw_lip_caps() {
        use crate::virtual_articulated_body::{BodyAxisUnit, BODY_AXES};
        let expected = [18, 37, 38, 39, 40, 41, 42, 43, 44];
        for axis in BODY_AXES {
            assert_eq!(axis.is_acoustic_control(), expected.contains(&axis.index()));
            if axis.is_acoustic_control() {
                assert_eq!(axis.anatomy().unit, BodyAxisUnit::SquareMillimetre);
            }
        }
        let neutral = ArticulatedBodyState::at_neutral();
        let mut shut_axes = *neutral.axes();
        for axis in [BodyAxis::JawOpening, BodyAxis::LipAperture, BodyAxis::LipWidth] {
            shut_axes[axis.index()] = axis.anatomy().minimum;
        }
        let shut = ArticulatedBodyState::from_physical_state(
            shut_axes, neutral.lung_air_microlitres(), neutral.proprioception_initialized(),
        ).unwrap();
        let unchanged_bytes = shut.encode().unwrap();
        let direct_areas = shut.vocal_tract_areas_square_millimetres();
        assert_eq!(direct_areas, neutral.vocal_tract_areas_square_millimetres());
        assert_eq!(shut.encode().unwrap(), unchanged_bytes);
        // Neutral oral aperture is already closed. Use the declared maximum
        // posture for the contrasting body, not another zero-area mouth.
        let mut open_axes = *neutral.axes();
        for axis in [BodyAxis::JawOpening, BodyAxis::LipAperture, BodyAxis::LipWidth] {
            open_axes[axis.index()] = axis.anatomy().maximum;
        }
        let open = ArticulatedBodyState::from_physical_state(
            open_axes, neutral.lung_air_microlitres(), neutral.proprioception_initialized(),
        ).unwrap();
        let voice = settle_native_articulatory_interval(open, &[], 2, 4_000).unwrap();
        let uncapped = settle_native_articulatory_interval(shut.clone(), &[], 2, 4_000).unwrap();
        assert!(voice.radiated_pressure_pcm.iter().any(|sample| *sample != 0));
        assert_eq!(voice.radiated_pressure_pcm, uncapped.radiated_pressure_pcm);
        assert_eq!(
            voice.successor_body.articulatory_acoustic_state(),
            uncapped.successor_body.articulatory_acoustic_state()
        );
        assert_eq!(voice.successor_body.lung_air_microlitres(), uncapped.successor_body.lung_air_microlitres());
        assert_eq!(
            uncapped.mouth_area_square_millimetres_at_apex,
            uncapped.successor_body.axis(BodyAxis::VocalTractSection7Area)
        );
        // The body remains different and is not relabeled as the instrument.
        assert!(
            voice.body_mechanical_trajectories[2] != uncapped.body_mechanical_trajectories[2],
            "distinct jaw/lip geometry must retain distinct oral body feedback"
        );
        let mut changed_axes = *neutral.axes();
        changed_axes[BodyAxis::VocalTractSection0Area.index()] =
            BodyAxis::VocalTractSection0Area.anatomy().maximum;
        let changed = ArticulatedBodyState::from_physical_state(
            changed_axes, neutral.lung_air_microlitres(), neutral.proprioception_initialized(),
        ).unwrap();
        let shaped = settle_native_articulatory_interval(changed, &[], 2, 4_000).unwrap();
        assert_ne!(voice.radiated_pressure_pcm, shaped.radiated_pressure_pcm);
        let silent = settle_native_articulatory_interval(shut, &[], 0, 4_000).unwrap();
        assert!(silent.radiated_pressure_pcm.iter().all(|sample| *sample == 0));

        // Same continuation, with and without serialization at the boundary.
        // This proves the organ codec, not the separate cognitive scheduler.
        let warm = voice.successor_body;
        let restored = ArticulatedBodyState::decode(&warm.encode().unwrap()).unwrap();
        let a = settle_native_articulatory_interval(warm, &[], 0, 4_000).unwrap();
        let b = settle_native_articulatory_interval(restored, &[], 0, 4_000).unwrap();
        assert_eq!(a, b);
    }

    #[test]
    fn one_real_respiratory_discharge_uses_the_resident_body_and_radiates_pressure() {
        let settled = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            13,
            13,
            ACTIVE_SAMPLE_COUNT,
        );
        assert_eq!(settled.applied_motor_quanta, 8);
        assert_eq!(settled.stalled_motor_quanta, 5);
        assert!(settled.glottal_open_samples_at_apex < 80);
        assert_eq!(settled.perioral_area_displacement_square_millimetres, 0);
        assert_ne!(settled.peak_transducer_surface_velocity_pcm, 0);
        let peak = settled
            .radiated_pressure_pcm
            .iter()
            .map(|value| value.unsigned_abs())
            .max()
            .unwrap_or(0);
        let nonzero = settled
            .radiated_pressure_pcm
            .iter()
            .filter(|value| **value != 0)
            .count();
        eprintln!("spectral probe peak={peak} nonzero={nonzero} state={:?}", settled.successor_body.articulatory_acoustic_state());
        assert!(settled.radiated_pressure_pcm.iter().any(|value| *value != 0));
        assert!(settled.relaxation_sample_count <= MAX_RELAXATION_SAMPLES);
    }

    #[test]
    fn respiratory_work_is_the_source_while_body_axes_only_shape_it() {
        let voice = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            3,
            3,
            4_000,
        );
        let jaw = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::JawOpening,
            BodyEffectorDirection::TowardMaximum,
            3,
            0,
            4_000,
        );
        let lips = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::LipWidth,
            BodyEffectorDirection::TowardMaximum,
            3,
            0,
            4_000,
        );
        assert!(voice.radiated_pressure_pcm.iter().any(|sample| *sample != 0));
        assert!(jaw.radiated_pressure_pcm.iter().all(|sample| *sample == 0));
        assert!(lips.radiated_pressure_pcm.iter().all(|sample| *sample == 0));
    }

    #[test]
    fn one_motor_event_advances_only_one_native_millisecond() {
        let settled = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
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
    fn one_respiratory_event_launches_bounded_work_without_repeating_discharge() {
        let settled = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
            8,
            4_000,
        );

        assert_eq!(settled.radiated_pressure_pcm.len(), 4_000);
        assert!(settled.body_mechanical_trajectories[0]
            .iter()
            .any(|respiratory_flow| *respiratory_flow != 0));
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
    fn respiratory_flow_debits_the_exact_bounded_lung_and_stops_at_residual_volume() {
        let neutral = ArticulatedBodyState::at_neutral();
        let settled = active_interval(
            neutral.clone(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
            8,
            4_000,
        );
        let emitted_sixteenths = settled.body_mechanical_trajectories[0]
            .iter()
            .try_fold(0_u32, |total, flow| {
                total.checked_add(u32::from(flow.unsigned_abs()))
            })
            .unwrap();
        let ArticulatoryAcousticState::Spectral(acoustic) =
            settled.successor_body.articulatory_acoustic_state()
        else {
            panic!("current respiratory organ changed acoustic variant")
        };
        assert!(emitted_sixteenths > 0);
        assert_eq!(
            settled.successor_body.lung_air_microlitres(),
            neutral.lung_air_microlitres()
                - emitted_sixteenths / RESPIRATORY_FLOW_SAMPLES_PER_MICROLITRE,
        );
        assert_eq!(
            acoustic.expiratory_volume_remainder_sixteenths_microlitre,
            i32::try_from(emitted_sixteenths % RESPIRATORY_FLOW_SAMPLES_PER_MICROLITRE)
                .unwrap(),
        );

        let one_microlitre = ArticulatedBodyState::from_physical_state(
            *neutral.axes(),
            MIN_LUNG_AIR_MICROLITRES + 1,
            neutral.proprioception_initialized(),
        )
        .unwrap();
        let exhausted = active_interval(
            one_microlitre,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
            8,
            4_000,
        );
        let exhausted_outflow_sixteenths = exhausted.body_mechanical_trajectories[0]
            .iter()
            .filter(|flow| **flow > 0)
            .map(|flow| u32::try_from(*flow).unwrap())
            .sum::<u32>();
        assert_eq!(exhausted_outflow_sixteenths, 0);
        assert_eq!(exhausted.applied_motor_quanta, 0);
        assert_eq!(exhausted.stalled_motor_quanta, 8);
        assert!(exhausted.body_mechanical_trajectories[0]
            .iter()
            .any(|flow| *flow < 0));
        assert!(exhausted.successor_body.lung_air_microlitres()
            > MIN_LUNG_AIR_MICROLITRES);
        assert!(exhausted.successor_body.lung_air_microlitres()
            <= NEUTRAL_LUNG_AIR_MICROLITRES);

        let empty = ArticulatedBodyState::from_physical_state(
            *neutral.axes(),
            MIN_LUNG_AIR_MICROLITRES,
            neutral.proprioception_initialized(),
        )
        .unwrap();
        let recovering = active_interval(
            empty,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
            8,
            4_000,
        );
        assert!(recovering.body_mechanical_trajectories[0]
            .iter()
            .all(|flow| *flow <= 0));
        assert!(recovering.body_mechanical_trajectories[0]
            .iter()
            .any(|flow| *flow < 0));
        assert_eq!(recovering.applied_motor_quanta, 0);
        assert_eq!(recovering.stalled_motor_quanta, 8);
        assert_eq!(
            recovering.successor_body.lung_air_microlitres(),
            MIN_LUNG_AIR_MICROLITRES
                + (PASSIVE_INSPIRATORY_FLOW_MILLILITRES_PER_SECOND.unsigned_abs()
                    * 4_000)
                    / RESPIRATORY_FLOW_SAMPLES_PER_MICROLITRE,
        );
    }

    #[test]
    fn body_owned_transducer_cold_restores_and_reaches_exact_rest_without_another_discharge() {
        let first = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            3,
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
        let released =
            settle_native_articulatory_interval(restored, &[], 0, 184_000).unwrap();
        assert_eq!(released.applied_motor_quanta, 0);
        assert!(released.successor_body.articulatory_system_is_quiescent());
    }

    #[test]
    fn acoustic_pressure_and_surface_motion_continue_across_interval_and_restart() {
        let first = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
            8,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        let restored = ArticulatedBodyState::decode(
            &first.successor_body.encode().unwrap(),
        )
        .unwrap();
        let continued = active_interval(
            restored,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
            8,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        let uninterrupted = active_interval(
            first.successor_body,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
            8,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );

        assert_eq!(continued, uninterrupted);
        assert_eq!(continued.applied_motor_quanta, 0);
        assert_eq!(continued.stalled_motor_quanta, 8);
        assert_ne!(
            continued.successor_body.articulatory_acoustic_state(),
            ArticulatoryAcousticState::at_rest()
        );
    }

    #[test]
    fn absent_new_discharge_releases_the_resident_pressure_instead_of_repeating_it() {
        let active = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
            8,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        let released = settle_native_articulatory_interval(
            active.successor_body,
            &[],
            0,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        )
        .unwrap();

        assert_eq!(released.applied_motor_quanta, 0);
        assert_ne!(active.radiated_pressure_pcm, released.radiated_pressure_pcm);
    }

    #[test]
    fn causal_interval_timing_changes_the_physical_utterance() {
        let neutral = ArticulatedBodyState::at_neutral();
        let (first_body, first_breath) = moved(
            &neutral,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
        );
        let (second_body, second_breath) = moved(
            &first_body,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
        );
        let contiguous = settle_physical_transducer_interval_discharges(&[
            (4_000, 8, first_breath.clone(), first_body.clone()),
            (4_000, 8, second_breath.clone(), second_body.clone()),
        ])
        .unwrap();
        let separated = settle_physical_transducer_interval_discharges(&[
            (4_000, 8, first_breath, first_body.clone()),
            (4_000, 0, vec![], first_body),
            (4_000, 8, second_breath, second_body),
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
        assert_eq!(separated.applied_motor_quanta, 8);
        assert_eq!(separated.stalled_motor_quanta, 8);
    }

    #[test]
    fn lawful_long_recording_is_not_an_arithmetic_width_error() {
        let settled = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
            8,
            184_000,
        );

        assert_eq!(settled.applied_motor_quanta, 8);
        assert_eq!(settled.radiated_pressure_pcm.len(), 184_000);
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
        let (neutral_voice_body, neutral_breath) = moved(
            &neutral,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
        );
        let (open_voice_body, open_breath) = moved(
            &open,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
        );
        let neutral_sound = settle_physical_transducer_interval_discharges(&[(
            4_000,
            8,
            neutral_breath,
            neutral_voice_body,
        )])
        .unwrap();
        let open_sound = settle_physical_transducer_interval_discharges(&[(
            4_000,
            8,
            open_breath,
            open_voice_body,
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
        let (neutral_voice_body, neutral_breath) = moved(
            &neutral,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
        );
        let (shaped_voice_body, shaped_breath) = moved(
            &shaped,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
        );
        let neutral_sound = settle_physical_transducer_interval_discharges(&[(
            4_000,
            8,
            neutral_breath,
            neutral_voice_body,
        )])
        .unwrap();
        let shaped_sound = settle_physical_transducer_interval_discharges(&[(
            4_000,
            8,
            shaped_breath,
            shaped_voice_body,
        )])
        .unwrap();

        assert_ne!(neutral_sound.radiated_pressure_pcm, shaped_sound.radiated_pressure_pcm);
    }

    fn body_for_modal_frequencies(frequencies_hz: [i32; SPECTRAL_MODE_COUNT]) -> ArticulatedBodyState {
        let neutral = ArticulatedBodyState::at_neutral();
        let mut axes = *neutral.axes();
        axes[BodyAxis::JawOpening.index()] = 12_000;
        axes[BodyAxis::LipAperture.index()] = 9_000;
        for (mode, frequency_hz) in frequencies_hz.into_iter().enumerate() {
            let (minimum_hz, maximum_hz) = MODE_FREQUENCY_RANGES_HZ[mode];
            assert!((minimum_hz..=maximum_hz).contains(&frequency_hz));
            let area = minimum_hz
                .checked_sub(minimum_hz)
                .and_then(|_| {
                    round_div(
                        i64::from(frequency_hz - minimum_hz)
                            * i64::from(
                                MAX_TRACT_AREA_SQUARE_MILLIMETRES
                                    - MIN_TRACT_AREA_SQUARE_MILLIMETRES,
                            ),
                        i64::from(maximum_hz - minimum_hz),
                    )
                    .ok()
                })
                .and_then(|offset| offset.checked_add(MIN_TRACT_AREA_SQUARE_MILLIMETRES))
                .unwrap();
            axes[BodyAxis::VocalTractSection0Area.index() + mode] = area;
        }
        ArticulatedBodyState::from_physical_state(
            axes,
            neutral.lung_air_microlitres(),
            neutral.proprioception_initialized(),
        )
        .unwrap()
    }

    fn render_bounded_voice(
        body: ArticulatedBodyState,
        carriers: u128,
        samples: usize,
    ) -> ArticulatoryBodyTransition {
        settle_physical_transducer_interval_discharges(&[(samples, carriers, vec![], body)])
            .unwrap()
    }

    fn render_bounded_voice_with_material(
        body: ArticulatedBodyState,
        carriers: u128,
        samples: usize,
        material: SpectralOrganMaterial,
    ) -> ArticulatoryBodyTransition {
        settle_native_articulatory_interval_with_material(
            body,
            &[],
            carriers,
            samples,
            material,
        )
        .unwrap()
    }

    #[test]
    fn dynamic_source_material_range_locates_duration_rate_and_pressure_boundaries() {
        let body = body_for_modal_frequencies([1_030, 1_370, 3_170, 4_400, 5_500]);
        let mut accepted_region_count = 0usize;
        for work_per_carrier in [512_000_i64, 1_024_000, 1_536_000, 2_048_000] {
            for (rate_floor, rate_ceiling) in [(320_i64, 360_i64), (340, 376), (352, 376)] {
                for pressure_divisor in [4_i64, 2, 1] {
                    let material = SpectralOrganMaterial {
                        respiratory_work_per_efferent_carrier: work_per_carrier,
                        valve_rate_floor_hz: rate_floor,
                        valve_rate_ceiling_hz: rate_ceiling,
                        respiratory_rest_loss_per_sample: 256,
                        internal_pressure_per_pcm: pressure_divisor,
                    };
                    let rendered = render_bounded_voice_with_material(
                        body.clone(),
                        2,
                        16_000,
                        material,
                    );
                    let flow = &rendered.body_mechanical_trajectories[0];
                    let first_flow = flow.iter().position(|sample| *sample > 0);
                    let last_flow = flow.iter().rposition(|sample| *sample > 0);
                    let active_samples = match (first_flow, last_flow) {
                        (Some(first), Some(last)) => last - first + 1,
                        _ => 0,
                    };
                    let cycle_count = flow
                        .windows(2)
                        .filter(|pair| pair[0] == 0 && pair[1] > 0)
                        .count();
                    let observed_rate_hz = if active_samples == 0 {
                        0
                    } else {
                        cycle_count * ARTICULATORY_SAMPLE_RATE_HZ as usize / active_samples
                    };
                    let peak = rendered
                        .radiated_pressure_pcm
                        .iter()
                        .map(|sample| sample.unsigned_abs())
                        .max()
                        .unwrap_or(0);
                    let duration_in_accepted_gesture_band =
                        (8_000..=16_000).contains(&active_samples);
                    let rate_in_accepted_child_source_band =
                        (340..=390).contains(&observed_rate_hz);
                    let pressure_is_audible_without_clipping = peak >= 64 && peak < 32_768;
                    accepted_region_count += usize::from(
                        duration_in_accepted_gesture_band
                            && rate_in_accepted_child_source_band
                            && pressure_is_audible_without_clipping,
                    );
                    eprintln!(
                        "source-range work={work_per_carrier} floor={rate_floor} ceiling={rate_ceiling} divisor={pressure_divisor} active_samples={active_samples} observed_rate_hz={observed_rate_hz} peak={peak}"
                    );
                }
            }
        }
        assert!(accepted_region_count > 1, "the material gate collapsed to one guessed point");

        let no_work_predecessor = body;
        let no_work = render_bounded_voice_with_material(
            no_work_predecessor.clone(),
            0,
            16_000,
            SPECTRAL_ORGAN_MATERIAL,
        );
        assert!(no_work.radiated_pressure_pcm.iter().all(|sample| *sample == 0));
        assert_eq!(no_work.successor_body, no_work_predecessor);
    }

    #[test]
    fn dynamic_glottal_work_range_is_bounded_monotonic_and_not_one_point() {
        let body = body_for_modal_frequencies([1_030, 1_370, 3_170, 4_400, 5_500]);
        let mut prior_nonzero = 0usize;
        let mut distinct = Vec::new();
        for carriers in [1_u128, 2, 4, 8] {
            let rendered = render_bounded_voice(body.clone(), carriers, 16_000);
            let nonzero = rendered
                .radiated_pressure_pcm
                .iter()
                .filter(|sample| **sample != 0)
                .count();
            let peak = rendered
                .radiated_pressure_pcm
                .iter()
                .map(|sample| sample.unsigned_abs())
                .max()
                .unwrap_or(0);
            assert!(nonzero > prior_nonzero, "work range stopped changing at {carriers}");
            assert!(peak > 0);
            assert_eq!(
                rendered.successor_body.articulatory_acoustic_state(),
                ArticulatoryAcousticState::at_rest()
            );
            prior_nonzero = nonzero;
            distinct.push((nonzero, peak));
        }
        distinct.dedup();
        assert_eq!(distinct.len(), 4);
    }

    #[test]
    fn fully_closed_and_fully_open_boundaries_cannot_pass_paid_work() {
        for glottal_area in [
            BodyAxis::GlottalAperture.anatomy().minimum,
            BodyAxis::GlottalAperture.anatomy().maximum,
        ] {
            let neutral = ArticulatedBodyState::at_neutral();
            let mut axes = *neutral.axes();
            axes[BodyAxis::GlottalAperture.index()] = glottal_area;
            let mut acoustic = SpectralAcousticState::at_rest();
            acoustic.respiratory_work_remaining =
                SPECTRAL_ORGAN_MATERIAL.respiratory_work_per_efferent_carrier;
            acoustic.fold_displacement = [-384, -383];
            let body = ArticulatedBodyState::from_physical_state(
                axes,
                neutral.lung_air_microlitres(),
                neutral.proprioception_initialized(),
            )
            .unwrap()
            .with_articulatory_acoustic_state(ArticulatoryAcousticState::Spectral(acoustic))
            .unwrap();
            let settled = settle_native_articulatory_interval(body, &[], 0, 4_000).unwrap();
            assert!(settled.radiated_pressure_pcm.iter().all(|sample| *sample == 0));
        }
    }

    #[test]
    fn three_vowel_regions_and_adjacent_controls_are_physically_distinct() {
        let regions = [
            [1_030, 1_370, 3_170, 4_400, 5_500],
            [370, 3_200, 3_730, 4_400, 5_500],
            [580, 1_120, 3_350, 4_400, 5_500],
        ];
        let mut outputs = Vec::new();
        for frequencies in regions {
            let center = body_for_modal_frequencies(frequencies);
            let center_output = render_bounded_voice(center.clone(), 8, 12_000)
                .radiated_pressure_pcm;
            assert!(center_output.iter().any(|sample| *sample != 0));
            for delta in [-7, 7] {
                let mut axes = *center.axes();
                axes[BodyAxis::VocalTractSection0Area.index()] += delta;
                let adjacent = ArticulatedBodyState::from_physical_state(
                    axes,
                    center.lung_air_microlitres(),
                    center.proprioception_initialized(),
                )
                .unwrap();
                let adjacent_output = render_bounded_voice(adjacent, 8, 12_000)
                    .radiated_pressure_pcm;
                assert_ne!(center_output, adjacent_output);
            }
            outputs.push(center_output);
        }
        assert_ne!(outputs[0], outputs[1]);
        assert_ne!(outputs[1], outputs[2]);
        assert_ne!(outputs[0], outputs[2]);
    }

    #[test]
    #[ignore = "writes only the explicitly requested temporary listening board"]
    fn write_temporary_spectral_organ_listening_board() {
        use std::fs;
        use std::path::PathBuf;

        let output = PathBuf::from(
            std::env::var("GUALA_VOICE_HARNESS_DIR")
                .expect("AWS-bracketed harness must supply its isolated output directory"),
        );
        fs::create_dir_all(&output).unwrap();
        let neutral = ArticulatedBodyState::at_neutral();
        let mut copied_pose_axes = *neutral.axes();
        copied_pose_axes[BodyAxis::GlottalAperture.index()] = 39;
        for (axis, area) in [
            BodyAxis::VocalTractSection0Area,
            BodyAxis::VocalTractSection1Area,
            BodyAxis::VocalTractSection2Area,
            BodyAxis::VocalTractSection3Area,
            BodyAxis::VocalTractSection4Area,
            BodyAxis::VocalTractSection5Area,
            BodyAxis::VocalTractSection6Area,
            BodyAxis::VocalTractSection7Area,
        ]
        .iter()
        .zip([125, 145, 165, 185, 205, 225, 245, 265])
        {
            copied_pose_axes[axis.index()] = area;
        }
        let copied_pose = ArticulatedBodyState::from_physical_state(
            copied_pose_axes,
            NEUTRAL_LUNG_AIR_MICROLITRES,
            true,
        )
        .expect("task-1428 copied posture is anatomical");
        let candidates = vec![
            (
                "region-a",
                body_for_modal_frequencies([1_030, 1_370, 3_170, 4_400, 5_500]),
            ),
            (
                "region-b",
                body_for_modal_frequencies([370, 3_200, 3_730, 4_400, 5_500]),
            ),
            (
                "region-c",
                body_for_modal_frequencies([580, 1_120, 3_350, 4_400, 5_500]),
            ),
            ("task-1428-one-shot-control", copied_pose),
        ];
        for (name, body) in candidates {
            let transition = render_bounded_voice(body, 8, 16_000);
            let samples = transition.radiated_pressure_pcm;
            let flow = transition.body_mechanical_trajectories[0].clone();
            let amplified = samples
                .into_iter()
                .map(|sample| {
                    i16::try_from(i32::from(sample) * 49)
                        .expect("observer-only x49 playback must not clip")
                })
                .collect::<Vec<_>>();
            let byte_rate = ARTICULATORY_SAMPLE_RATE_HZ * 2;
            let data_bytes = u32::try_from(amplified.len() * 2).unwrap();
            let mut wav = Vec::with_capacity(44 + amplified.len() * 2);
            wav.extend_from_slice(b"RIFF");
            wav.extend_from_slice(&(36 + data_bytes).to_le_bytes());
            wav.extend_from_slice(b"WAVEfmt ");
            wav.extend_from_slice(&16_u32.to_le_bytes());
            wav.extend_from_slice(&1_u16.to_le_bytes());
            wav.extend_from_slice(&1_u16.to_le_bytes());
            wav.extend_from_slice(&ARTICULATORY_SAMPLE_RATE_HZ.to_le_bytes());
            wav.extend_from_slice(&byte_rate.to_le_bytes());
            wav.extend_from_slice(&2_u16.to_le_bytes());
            wav.extend_from_slice(&16_u16.to_le_bytes());
            wav.extend_from_slice(b"data");
            wav.extend_from_slice(&data_bytes.to_le_bytes());
            for sample in amplified {
                wav.extend_from_slice(&sample.to_le_bytes());
            }
            fs::write(output.join(format!("{name}.wav")), wav).unwrap();

            let flow_data_bytes = u32::try_from(flow.len() * 2).unwrap();
            let mut flow_wav = Vec::with_capacity(44 + flow.len() * 2);
            flow_wav.extend_from_slice(b"RIFF");
            flow_wav.extend_from_slice(&(36 + flow_data_bytes).to_le_bytes());
            flow_wav.extend_from_slice(b"WAVEfmt ");
            flow_wav.extend_from_slice(&16_u32.to_le_bytes());
            flow_wav.extend_from_slice(&1_u16.to_le_bytes());
            flow_wav.extend_from_slice(&1_u16.to_le_bytes());
            flow_wav.extend_from_slice(&ARTICULATORY_SAMPLE_RATE_HZ.to_le_bytes());
            flow_wav.extend_from_slice(&byte_rate.to_le_bytes());
            flow_wav.extend_from_slice(&2_u16.to_le_bytes());
            flow_wav.extend_from_slice(&16_u16.to_le_bytes());
            flow_wav.extend_from_slice(b"data");
            flow_wav.extend_from_slice(&flow_data_bytes.to_le_bytes());
            for sample in flow {
                flow_wav.extend_from_slice(&sample.to_le_bytes());
            }
            fs::write(output.join(format!("{name}-flow.wav")), flow_wav).unwrap();
        }
        let html = r#"<!doctype html><meta charset=utf-8><title>Guala spectral organ body proof</title><style>body{font:18px system-ui;max-width:760px;margin:40px auto;background:#10171c;color:#e8f2f2}button{font-size:20px;margin:8px;padding:12px 22px}</style><h1>Speech repair diagnostic control</h1><p>The first three are the rejected target-region record. The fourth is the exact task-1428 vocal posture supplied one ideal, isolated respiratory act. It is diagnostic only and cannot ship.</p><button onclick="new Audio('region-a.wav').play()">Intended AH — REJECTED</button><button onclick="new Audio('region-b.wav').play()">Intended EE — REJECTED</button><button onclick="new Audio('region-c.wav').play()">Intended OO — REJECTED</button><button onclick="new Audio('task-1428-one-shot-control.wav').play()">Task 1428 posture — one-shot diagnostic</button><p>These are exact deterministic 16-kHz pressures with observer-only x49 speaker gain. The labels belong only to this external test page; no sound name or target exists inside the organ.</p>"#;
        fs::write(output.join("index.html"), html).unwrap();
    }
    #[test]
    #[ignore = "writes only the explicitly requested bounded whole-word control"]
    fn write_temporary_native_whole_word_control() {
        use serde_json::json;
        use sha2::{Digest, Sha256};
        use std::fs;
        use std::path::{Path, PathBuf};

        #[derive(Clone, Copy)]
        struct Candidate {
            name: &'static str,
            closed_one_samples: usize,
            open_one_samples: usize,
            closed_two_samples: usize,
            open_two_samples: usize,
            transition_samples: usize,
            closed_terminal_area: i32,
            open_terminal_area: i32,
            respiratory_carriers: u128,
        }

        fn pose(
            frequencies_hz: [i32; SPECTRAL_MODE_COUNT],
            terminal_area: i32,
        ) -> ArticulatedBodyState {
            let base = body_for_modal_frequencies(frequencies_hz);
            let mut axes = *base.axes();
            axes[BodyAxis::VocalTractSection7Area.index()] = terminal_area;
            ArticulatedBodyState::from_physical_state(axes, NEUTRAL_LUNG_AIR_MICROLITRES, true)
                .expect("word-control posture must remain inside declared anatomy")
        }

        fn body_at_pose(
            predecessor: &ArticulatedBodyState,
            axes: [i32; BODY_AXIS_COUNT],
        ) -> ArticulatedBodyState {
            ArticulatedBodyState::from_physical_state(
                axes,
                predecessor.lung_air_microlitres(),
                true,
            )
            .expect("interpolated posture must remain inside declared anatomy")
            .with_articulatory_acoustic_state(predecessor.articulatory_acoustic_state())
            .expect("carried acoustic state must remain canonical")
        }

        fn settle_span(
            predecessor: ArticulatedBodyState,
            target_axes: [i32; BODY_AXIS_COUNT],
            respiratory_carriers: u128,
            samples: usize,
            pressure: &mut Vec<i16>,
            flow: &mut Vec<i16>,
        ) -> ArticulatedBodyState {
            let posed = body_at_pose(&predecessor, target_axes);
            let settled =
                settle_native_articulatory_interval(posed, &[], respiratory_carriers, samples)
                    .expect("bounded word-control span must settle");
            pressure.extend_from_slice(&settled.radiated_pressure_pcm);
            flow.extend_from_slice(&settled.body_mechanical_trajectories[0]);
            settled.successor_body
        }

        fn transition(
            mut predecessor: ArticulatedBodyState,
            target_axes: [i32; BODY_AXIS_COUNT],
            samples: usize,
            pressure: &mut Vec<i16>,
            flow: &mut Vec<i16>,
        ) -> ArticulatedBodyState {
            const STEP_SAMPLES: usize = 16;
            assert!(samples >= STEP_SAMPLES && samples % STEP_SAMPLES == 0);
            let start = *predecessor.axes();
            let steps = samples / STEP_SAMPLES;
            for step in 1..=steps {
                let mut axes = start;
                for axis in 0..BODY_AXIS_COUNT {
                    let delta = i64::from(target_axes[axis] - start[axis]);
                    axes[axis] = i32::try_from(
                        i64::from(start[axis])
                            + delta * i64::try_from(step).unwrap() / i64::try_from(steps).unwrap(),
                    )
                    .unwrap();
                }
                predecessor = settle_span(predecessor, axes, 0, STEP_SAMPLES, pressure, flow);
            }
            predecessor
        }

        fn render(
            candidate: Candidate,
            reverse: bool,
            frozen: bool,
            breathe: bool,
        ) -> (Vec<i16>, Vec<i16>, ArticulatedBodyState) {
            let closed = pose(
                [300, 1_150, 2_500, 4_400, 5_500],
                candidate.closed_terminal_area,
            );
            let open = pose(
                [1_030, 1_370, 3_170, 4_400, 5_500],
                candidate.open_terminal_area,
            );
            let first = if reverse { &open } else { &closed };
            let second = if frozen {
                first
            } else if reverse {
                &closed
            } else {
                &open
            };
            let mut body = first.clone();
            let first_axes = *first.axes();
            let second_axes = *second.axes();
            let mut pressure = Vec::new();
            let mut flow = Vec::new();
            body = settle_span(
                body,
                first_axes,
                if breathe {
                    candidate.respiratory_carriers
                } else {
                    0
                },
                candidate.closed_one_samples,
                &mut pressure,
                &mut flow,
            );
            body = transition(
                body,
                second_axes,
                candidate.transition_samples,
                &mut pressure,
                &mut flow,
            );
            body = settle_span(
                body,
                second_axes,
                0,
                candidate.open_one_samples,
                &mut pressure,
                &mut flow,
            );
            body = transition(
                body,
                first_axes,
                candidate.transition_samples,
                &mut pressure,
                &mut flow,
            );
            body = settle_span(
                body,
                first_axes,
                0,
                candidate.closed_two_samples,
                &mut pressure,
                &mut flow,
            );
            body = transition(
                body,
                second_axes,
                candidate.transition_samples,
                &mut pressure,
                &mut flow,
            );
            body = settle_span(
                body,
                second_axes,
                0,
                candidate.open_two_samples,
                &mut pressure,
                &mut flow,
            );
            (pressure, flow, body)
        }

        fn rest(mut body: ArticulatedBodyState) -> ArticulatedBodyState {
            for _ in 0..4 {
                if body.articulatory_system_is_quiescent() {
                    break;
                }
                let axes = *body.axes();
                let settled =
                    settle_native_articulatory_interval(body_at_pose(&body, axes), &[], 0, 48_000)
                        .expect("bounded passive return must settle");
                body = settled.successor_body;
            }
            assert!(body.articulatory_system_is_quiescent());
            body
        }

        fn sha256(samples: &[i16]) -> String {
            let mut digest = Sha256::new();
            for sample in samples {
                digest.update(sample.to_le_bytes());
            }
            format!("{:x}", digest.finalize())
        }

        fn write_wav(path: &Path, samples: &[i16]) {
            let data_bytes = u32::try_from(samples.len() * 2).unwrap();
            let byte_rate = ARTICULATORY_SAMPLE_RATE_HZ * 2;
            let mut wav = Vec::with_capacity(44 + samples.len() * 2);
            wav.extend_from_slice(b"RIFF");
            wav.extend_from_slice(&(36 + data_bytes).to_le_bytes());
            wav.extend_from_slice(b"WAVEfmt ");
            wav.extend_from_slice(&16_u32.to_le_bytes());
            wav.extend_from_slice(&1_u16.to_le_bytes());
            wav.extend_from_slice(&1_u16.to_le_bytes());
            wav.extend_from_slice(&ARTICULATORY_SAMPLE_RATE_HZ.to_le_bytes());
            wav.extend_from_slice(&byte_rate.to_le_bytes());
            wav.extend_from_slice(&2_u16.to_le_bytes());
            wav.extend_from_slice(&16_u16.to_le_bytes());
            wav.extend_from_slice(b"data");
            wav.extend_from_slice(&data_bytes.to_le_bytes());
            for sample in samples {
                wav.extend_from_slice(&sample.to_le_bytes());
            }
            fs::write(path, wav).unwrap();
        }

        let output = PathBuf::from(
            std::env::var("GUALA_VOICE_HARNESS_DIR")
                .expect("AWS-bracketed harness must supply its isolated output directory"),
        );
        fs::create_dir_all(&output).unwrap();
        let candidates = [
            Candidate {
                name: "mama-a",
                closed_one_samples: 2_400,
                open_one_samples: 3_520,
                closed_two_samples: 2_080,
                open_two_samples: 4_160,
                transition_samples: 640,
                closed_terminal_area: 40,
                open_terminal_area: 265,
                respiratory_carriers: 4,
            },
            Candidate {
                name: "mama-b",
                closed_one_samples: 2_400,
                open_one_samples: 3_520,
                closed_two_samples: 2_080,
                open_two_samples: 4_160,
                transition_samples: 640,
                closed_terminal_area: 40,
                open_terminal_area: 265,
                respiratory_carriers: 6,
            },
            Candidate {
                name: "mama-c",
                closed_one_samples: 2_400,
                open_one_samples: 3_520,
                closed_two_samples: 2_080,
                open_two_samples: 4_160,
                transition_samples: 640,
                closed_terminal_area: 40,
                open_terminal_area: 265,
                respiratory_carriers: 8,
            },
            Candidate {
                name: "mama-d",
                closed_one_samples: 2_160,
                open_one_samples: 3_200,
                closed_two_samples: 1_920,
                open_two_samples: 3_840,
                transition_samples: 480,
                closed_terminal_area: 35,
                open_terminal_area: 245,
                respiratory_carriers: 6,
            },
            Candidate {
                name: "mama-e",
                closed_one_samples: 2_640,
                open_one_samples: 3_840,
                closed_two_samples: 2_240,
                open_two_samples: 4_480,
                transition_samples: 800,
                closed_terminal_area: 45,
                open_terminal_area: 285,
                respiratory_carriers: 6,
            },
        ];
        let mut manifest = Vec::new();
        for candidate in candidates {
            let (pressure, flow, successor) = render(candidate, false, false, true);
            let repeated = render(candidate, false, false, true);
            assert_eq!(
                pressure, repeated.0,
                "whole-word control must repeat exactly"
            );
            assert_eq!(flow, repeated.1, "whole-word flow must repeat exactly");
            let at_rest = rest(successor).articulatory_system_is_quiescent();
            let peak = pressure
                .iter()
                .map(|sample| sample.unsigned_abs())
                .max()
                .unwrap_or(0);
            assert!(peak > 0 && peak < i16::MAX as u16);
            let gain = std::cmp::max(1, std::cmp::min(49, 28_000 / i32::from(peak)));
            let amplified = pressure
                .iter()
                .map(|sample| i16::try_from(i32::from(*sample) * gain).unwrap())
                .collect::<Vec<_>>();
            write_wav(&output.join(format!("{}.wav", candidate.name)), &amplified);
            manifest.push(json!({
                "name": candidate.name,
                "raw_pressure_sha256": sha256(&pressure),
                "sample_count": pressure.len(),
                "peak_raw_pressure": peak,
                "observer_gain": gain,
                "exact_rest": at_rest,
                "closed_one_samples": candidate.closed_one_samples,
                "open_one_samples": candidate.open_one_samples,
                "closed_two_samples": candidate.closed_two_samples,
                "open_two_samples": candidate.open_two_samples,
                "transition_samples": candidate.transition_samples,
                "closed_terminal_area": candidate.closed_terminal_area,
                "open_terminal_area": candidate.open_terminal_area,
                "respiratory_carriers": candidate.respiratory_carriers,
            }));
        }

        let control = candidates[1];
        let zero_breath = render(control, false, false, false);
        assert!(zero_breath.0.iter().all(|sample| *sample == 0));
        let frozen = render(control, false, true, true);
        let reversed = render(control, true, false, true);
        let reference = render(control, false, false, true);
        assert_ne!(frozen.0, reference.0);
        assert_ne!(reversed.0, reference.0);
        for (name, pressure) in [
            ("control-frozen", &frozen.0),
            ("control-reversed", &reversed.0),
        ] {
            let peak = pressure
                .iter()
                .map(|sample| sample.unsigned_abs())
                .max()
                .unwrap_or(0);
            let gain = std::cmp::max(1, std::cmp::min(49, 28_000 / i32::from(peak)));
            let amplified = pressure
                .iter()
                .map(|sample| i16::try_from(i32::from(*sample) * gain).unwrap())
                .collect::<Vec<_>>();
            write_wav(&output.join(format!("{name}.wav")), &amplified);
        }
        fs::write(
            output.join("manifest.json"),
            serde_json::to_vec_pretty(&json!({
                "schema": "guala.native-whole-word-control.v1",
                "sample_rate_hz": ARTICULATORY_SAMPLE_RATE_HZ,
                "candidates": manifest,
                "controls": {
                    "zero_breath_exact_silence": true,
                    "frozen_posture_sha256": sha256(&frozen.0),
                    "reversed_order_sha256": sha256(&reversed.0),
                    "reference_sha256": sha256(&reference.0),
                }
            }))
            .unwrap(),
        )
        .unwrap();
        let buttons = candidates
            .iter()
            .map(|candidate| {
                format!(
                    "<button onclick=\"new Audio('{}.wav').play()\">{}</button>",
                    candidate.name, candidate.name
                )
            })
            .collect::<Vec<_>>()
            .join("\n");
        let html = format!(
            r#"<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Guala native whole-word control</title><style>body{{font:18px system-ui;max-width:820px;margin:40px auto;background:#08151b;color:#edfafa}}button{{font-size:20px;margin:8px;padding:12px 22px}}.truth{{border:1px solid #b27b28;padding:12px}}</style><h1>Native-organ whole-word falsifier</h1><p class=truth><strong>This is not Guala speaking.</strong> These candidates use the production native organ physics with test-only continuous anatomical posture changes. No waveform, phoneme, word, meaning, TTS, or organism input is supplied. Labels exist only for human evaluation.</p><h2>Accepted acoustic reference</h2><button onclick="new Audio('/speech-v22-rate-ab/c-mama-16k-6800.wav').play()">Accepted V22 ma-ma reference</button><h2>Intended complete ma-ma candidates</h2>{buttons}<h2>Falsifiers</h2><button onclick="new Audio('control-frozen.wav').play()">Frozen one-posture control</button><button onclick="new Audio('control-reversed.wav').play()">Reversed posture-order control</button>"#
        );
        fs::write(output.join("index.html"), html).unwrap();
    }

    /// The copied-production-body pose falsifier (contract classes 4/5):
    /// her exact published tick-358454 pose — glottis at its 400 maximum,
    /// the learned tract [776,114,814,482,246,180,39,20], lung 2,000,000 —
    /// must be SILENT under any drive (posture is the control), and the
    /// same body one lawful closing movement later must phonate and reach
    /// exact rest. Axes not published for that tick hold their neutral.
    #[test]
    fn copied_body_pose_is_silent_wide_open_and_phonates_after_closure() {
        let neutral = ArticulatedBodyState::at_neutral();
        let mut axes = *neutral.axes();
        axes[BodyAxis::GlottalAperture.index()] =
            BodyAxis::GlottalAperture.anatomy().maximum;
        let tract = [776, 114, 814, 482, 246, 180, 39, 20];
        let tract_axes = [
            BodyAxis::VocalTractSection0Area,
            BodyAxis::VocalTractSection1Area,
            BodyAxis::VocalTractSection2Area,
            BodyAxis::VocalTractSection3Area,
            BodyAxis::VocalTractSection4Area,
            BodyAxis::VocalTractSection5Area,
            BodyAxis::VocalTractSection6Area,
            BodyAxis::VocalTractSection7Area,
        ];
        for (axis, area) in tract_axes.iter().zip(tract) {
            axes[axis.index()] = area;
        }
        let wide_open = ArticulatedBodyState::from_physical_state(
            axes,
            crate::virtual_articulated_body::NEUTRAL_LUNG_AIR_MICROLITRES,
            true,
        )
        .expect("published pose is anatomical");
        // Fully-open control: body motion has no respiratory source. The
        // off-neutral tissue may still return passively, but that return
        // cannot be relabeled as a new respiratory discharge.
        let (stalled_body, stalled_breath) = moved(
            &wide_open,
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMaximum,
            8,
        );
        let silent = settle_physical_transducer_interval_discharges(&[(
            16_000,
            0,
            stalled_breath,
            stalled_body,
        )])
        .unwrap();
        assert!(
            silent
                .radiated_pressure_pcm
                .iter()
                .all(|sample| *sample == 0),
            "an opening drive and passive return at maximum-open must be silent"
        );
        assert!(silent
            .successor_body
            .articulatory_acoustic_state()
            .is_quiescent());

        // one lawful closing movement into the proven voiced region
        let mut voiced_axes = axes;
        voiced_axes[BodyAxis::GlottalAperture.index()] = 80;
        let voiced_pose = ArticulatedBodyState::from_physical_state(
            voiced_axes,
            crate::virtual_articulated_body::NEUTRAL_LUNG_AIR_MICROLITRES,
            true,
        )
        .expect("closed pose is anatomical");
        let voiced = render_bounded_voice(voiced_pose, 8, 16_000);
        let nonzero = voiced
            .radiated_pressure_pcm
            .iter()
            .filter(|sample| **sample != 0)
            .count();
        assert!(
            nonzero > 4_000,
            "closing posture must sustain voiced pressure, got {nonzero} nonzero"
        );
        assert!(
            voiced
                .successor_body
                .articulatory_acoustic_state()
                .is_quiescent(),
            "every trajectory must end at exact rest"
        );
    }

    #[test]
    fn opening_activation_and_unattached_body_axis_cannot_manufacture_pressure() {
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
            0,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        let shoulder = active_interval(
            ArticulatedBodyState::at_neutral(),
            BodyAxis::LeftShoulderPitch,
            BodyEffectorDirection::TowardMaximum,
            7,
            0,
            NATIVE_ARTICULATORY_INTERVAL_SAMPLES,
        );
        assert_eq!(stalled.applied_motor_quanta, 0);
        assert_eq!(stalled.stalled_motor_quanta, 0);
        assert!(stalled.radiated_pressure_pcm.iter().all(|sample| *sample == 0));
        assert_eq!(shoulder.applied_motor_quanta, 0);
        assert!(shoulder.radiated_pressure_pcm.iter().all(|sample| *sample == 0));
    }

    #[test]
    fn swallowing_closure_without_l13_respiration_is_exact_silence() {
        let (closed_body, swallowing_consequences) = moved(
            &ArticulatedBodyState::at_neutral(),
            BodyAxis::GlottalAperture,
            BodyEffectorDirection::TowardMinimum,
            8,
        );
        let settled = settle_native_articulatory_interval(
            closed_body,
            &swallowing_consequences,
            0,
            16_000,
        )
        .unwrap();

        assert_eq!(settled.applied_motor_quanta, 0);
        assert!(settled
            .radiated_pressure_pcm
            .iter()
            .all(|sample| *sample == 0));
        assert!(settled
            .successor_body
            .articulatory_acoustic_state()
            .is_quiescent());
    }
}
