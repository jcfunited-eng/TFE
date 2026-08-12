//! Exact bounded virtual-body yaw actuation.
//!
//! A signed actuation retains the physical path information that wrapped start
//! and end headings cannot provide. The endpoint-constrained minimum-jerk
//! polynomial is evaluated on the embodiment world's one-millisecond lattice,
//! yielding an exact signed integer trajectory whose samples sum to the full
//! commanded displacement. This is body/motor physics; no sensory receptor,
//! fluid-brain, DSF, Krimelack, neuron, or cognition state participates.

use core::mem::size_of;

use crate::virtual_vestibular_canal::{WORLD_MAX_ACTION_TICKS, WORLD_MECHANICAL_TICK_MICROSECONDS};

const FULL_TURN_MILLIDEGREES: i64 = 360_000;
const BODY_STATE_BYTES: usize = size_of::<u32>();

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum YawMotionError {
    InvalidHeading,
    InvalidDuration,
    ArithmeticWidth,
    InvalidRestart,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct YawBodyState {
    heading_millidegrees: u32,
}

impl YawBodyState {
    pub(crate) fn new(heading_millidegrees: u32) -> Result<Self, YawMotionError> {
        if i64::from(heading_millidegrees) >= FULL_TURN_MILLIDEGREES {
            return Err(YawMotionError::InvalidHeading);
        }
        Ok(Self {
            heading_millidegrees,
        })
    }

    pub(crate) fn heading_millidegrees(self) -> u32 {
        self.heading_millidegrees
    }

    pub(crate) fn resident_bytes() -> usize {
        BODY_STATE_BYTES
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct SignedYawActuation {
    signed_displacement_millidegrees: i32,
    duration_ticks: usize,
}

impl SignedYawActuation {
    pub(crate) fn new(
        signed_displacement_millidegrees: i32,
        duration_microseconds: u32,
    ) -> Result<Self, YawMotionError> {
        if duration_microseconds == 0
            || duration_microseconds % WORLD_MECHANICAL_TICK_MICROSECONDS != 0
        {
            return Err(YawMotionError::InvalidDuration);
        }
        let duration_ticks =
            usize::try_from(duration_microseconds / WORLD_MECHANICAL_TICK_MICROSECONDS)
                .map_err(|_| YawMotionError::InvalidDuration)?;
        if duration_ticks == 0 || duration_ticks > WORLD_MAX_ACTION_TICKS {
            return Err(YawMotionError::InvalidDuration);
        }
        Ok(Self {
            signed_displacement_millidegrees,
            duration_ticks,
        })
    }

    pub(crate) fn signed_displacement_millidegrees(self) -> i32 {
        self.signed_displacement_millidegrees
    }

    pub(crate) fn duration_microseconds(self) -> u32 {
        u32::try_from(self.duration_ticks).expect("admitted duration")
            * WORLD_MECHANICAL_TICK_MICROSECONDS
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ExactYawTrajectory {
    signed_millidegrees_by_tick: [i32; WORLD_MAX_ACTION_TICKS],
    len: usize,
}

impl ExactYawTrajectory {
    fn new() -> Self {
        Self {
            signed_millidegrees_by_tick: [0; WORLD_MAX_ACTION_TICKS],
            len: 0,
        }
    }

    pub(crate) fn as_slice(&self) -> &[i32] {
        &self.signed_millidegrees_by_tick[..self.len]
    }

    pub(crate) fn transient_bytes() -> usize {
        size_of::<Self>()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct YawBodyTransition {
    pub(crate) successor: YawBodyState,
    pub(crate) trajectory: ExactYawTrajectory,
    pub(crate) recovered_signed_displacement_millidegrees: i64,
    pub(crate) ticks_processed: usize,
    pub(crate) resident_state_bytes: usize,
    pub(crate) transient_trajectory_bytes: usize,
}

pub(crate) fn settle_signed_yaw_actuation(
    predecessor: YawBodyState,
    actuation: SignedYawActuation,
) -> Result<YawBodyTransition, YawMotionError> {
    let magnitude = actuation.signed_displacement_millidegrees.unsigned_abs() as u128;
    let ticks = actuation.duration_ticks;
    preflight(magnitude, ticks)?;

    let mut trajectory = ExactYawTrajectory::new();
    let mut previous_position = 0_i64;
    let mut recovered = 0_i64;
    for tick in 1..=ticks {
        let position =
            signed_cumulative_position(actuation.signed_displacement_millidegrees, tick, ticks)?;
        let step = position
            .checked_sub(previous_position)
            .ok_or(YawMotionError::ArithmeticWidth)?;
        let step = i32::try_from(step).map_err(|_| YawMotionError::ArithmeticWidth)?;
        trajectory.signed_millidegrees_by_tick[tick - 1] = step;
        recovered = recovered
            .checked_add(i64::from(step))
            .ok_or(YawMotionError::ArithmeticWidth)?;
        previous_position = position;
    }
    trajectory.len = ticks;

    if recovered != i64::from(actuation.signed_displacement_millidegrees) {
        return Err(YawMotionError::ArithmeticWidth);
    }
    let successor_heading = (i64::from(predecessor.heading_millidegrees)
        + i64::from(actuation.signed_displacement_millidegrees))
    .rem_euclid(FULL_TURN_MILLIDEGREES);
    let successor = YawBodyState::new(
        u32::try_from(successor_heading).map_err(|_| YawMotionError::ArithmeticWidth)?,
    )?;

    Ok(YawBodyTransition {
        successor,
        trajectory,
        recovered_signed_displacement_millidegrees: recovered,
        ticks_processed: ticks,
        resident_state_bytes: YawBodyState::resident_bytes(),
        transient_trajectory_bytes: ExactYawTrajectory::transient_bytes(),
    })
}

/// Convert transient opposed motor-unit discharge into the body's smallest
/// exact yaw actuation. Even topology is the positive member of an antagonist
/// pair and odd topology is the negative member. One outward whole elementary
/// carrier contributes one millidegree, the body's existing integer lattice;
/// no gain, target, or retained command exists.
pub(crate) fn settle_motor_unit_yaw_actuation(
    predecessor: YawBodyState,
    recruitments: &[(u32, u128)],
) -> Result<YawBodyTransition, YawMotionError> {
    let mut signed_displacement = 0_i128;
    for (topology_index, outward_elementary_carriers) in recruitments.iter().copied() {
        let magnitude = i128::try_from(outward_elementary_carriers)
            .map_err(|_| YawMotionError::ArithmeticWidth)?;
        signed_displacement = if topology_index % 2 == 0 {
            signed_displacement.checked_add(magnitude)
        } else {
            signed_displacement.checked_sub(magnitude)
        }
        .ok_or(YawMotionError::ArithmeticWidth)?;
    }
    let signed_displacement =
        i32::try_from(signed_displacement).map_err(|_| YawMotionError::ArithmeticWidth)?;
    settle_signed_yaw_actuation(
        predecessor,
        SignedYawActuation::new(
            signed_displacement,
            WORLD_MECHANICAL_TICK_MICROSECONDS,
        )?,
    )
}

fn signed_cumulative_position(
    signed_displacement_millidegrees: i32,
    tick: usize,
    ticks: usize,
) -> Result<i64, YawMotionError> {
    let progress = minimum_jerk_progress_numerator(tick, ticks)?;
    let denominator = (ticks as u128)
        .checked_pow(5)
        .ok_or(YawMotionError::ArithmeticWidth)?;
    let magnitude = (signed_displacement_millidegrees.unsigned_abs() as u128)
        .checked_mul(progress)
        .ok_or(YawMotionError::ArithmeticWidth)?
        / denominator;
    let magnitude = i64::try_from(magnitude).map_err(|_| YawMotionError::ArithmeticWidth)?;
    Ok(if signed_displacement_millidegrees.is_negative() {
        -magnitude
    } else {
        magnitude
    })
}

fn minimum_jerk_progress_numerator(tick: usize, ticks: usize) -> Result<u128, YawMotionError> {
    let t = tick as u128;
    let n = ticks as u128;
    let t3 = t.checked_pow(3).ok_or(YawMotionError::ArithmeticWidth)?;
    let t4 = t.checked_pow(4).ok_or(YawMotionError::ArithmeticWidth)?;
    let t5 = t.checked_pow(5).ok_or(YawMotionError::ArithmeticWidth)?;
    let n2 = n.checked_pow(2).ok_or(YawMotionError::ArithmeticWidth)?;
    let first = 10_u128
        .checked_mul(t3)
        .and_then(|value| value.checked_mul(n2))
        .ok_or(YawMotionError::ArithmeticWidth)?;
    let middle = 15_u128
        .checked_mul(t4)
        .and_then(|value| value.checked_mul(n))
        .ok_or(YawMotionError::ArithmeticWidth)?;
    let last = 6_u128
        .checked_mul(t5)
        .ok_or(YawMotionError::ArithmeticWidth)?;
    first
        .checked_add(last)
        .and_then(|value| value.checked_sub(middle))
        .ok_or(YawMotionError::ArithmeticWidth)
}

fn preflight(magnitude: u128, ticks: usize) -> Result<(), YawMotionError> {
    let denominator = (ticks as u128)
        .checked_pow(5)
        .ok_or(YawMotionError::ArithmeticWidth)?;
    magnitude
        .checked_mul(denominator)
        .ok_or(YawMotionError::ArithmeticWidth)?;
    if minimum_jerk_progress_numerator(ticks, ticks)? != denominator {
        return Err(YawMotionError::ArithmeticWidth);
    }
    Ok(())
}

pub(crate) fn encode_yaw_body_state(state: YawBodyState) -> [u8; BODY_STATE_BYTES] {
    state.heading_millidegrees.to_le_bytes()
}

pub(crate) fn decode_yaw_body_state(encoded: &[u8]) -> Result<YawBodyState, YawMotionError> {
    if encoded.len() != BODY_STATE_BYTES {
        return Err(YawMotionError::InvalidRestart);
    }
    let heading = u32::from_le_bytes(
        encoded
            .try_into()
            .map_err(|_| YawMotionError::InvalidRestart)?,
    );
    YawBodyState::new(heading).map_err(|_| YawMotionError::InvalidRestart)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::virtual_vestibular_canal::{
        settle_signed_yaw_trajectory, CanalAnatomy, CanalState, PositiveRatio, SignedYawTrajectory,
    };

    fn anatomy() -> CanalAnatomy {
        CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap()
    }

    #[test]
    fn signed_path_conserves_rotation_and_wraps_only_body_orientation() {
        let predecessor = YawBodyState::new(350_000).unwrap();
        let transition = settle_signed_yaw_actuation(
            predecessor,
            SignedYawActuation::new(20_000, 200_000).unwrap(),
        )
        .unwrap();
        assert_eq!(transition.successor.heading_millidegrees(), 10_000);
        assert_eq!(
            transition.recovered_signed_displacement_millidegrees,
            20_000
        );
        assert_eq!(
            transition
                .trajectory
                .as_slice()
                .iter()
                .map(|v| i64::from(*v))
                .sum::<i64>(),
            20_000
        );
        assert_eq!(transition.ticks_processed, 200);
        assert!(transition
            .trajectory
            .as_slice()
            .iter()
            .all(|step| *step >= 0));
    }

    #[test]
    fn opposed_motor_topologies_sum_once_on_the_existing_body_lattice() {
        let settled = settle_motor_unit_yaw_actuation(
            YawBodyState::new(0).unwrap(),
            &[(0, 7), (1, 2), (2, 1)],
        )
        .unwrap();
        assert_eq!(settled.recovered_signed_displacement_millidegrees, 6);
        assert_eq!(settled.successor.heading_millidegrees(), 6);
        assert_eq!(settled.trajectory.as_slice(), &[6]);
    }

    #[test]
    fn opposite_actuation_is_samplewise_symmetric() {
        let start = YawBodyState::new(0).unwrap();
        let positive =
            settle_signed_yaw_actuation(start, SignedYawActuation::new(90_000, 200_000).unwrap())
                .unwrap();
        let negative =
            settle_signed_yaw_actuation(start, SignedYawActuation::new(-90_000, 200_000).unwrap())
                .unwrap();
        for (left, right) in positive
            .trajectory
            .as_slice()
            .iter()
            .zip(negative.trajectory.as_slice())
        {
            assert_eq!(i64::from(*left), -i64::from(*right));
        }
        assert_eq!(positive.successor.heading_millidegrees(), 90_000);
        assert_eq!(negative.successor.heading_millidegrees(), 270_000);
    }

    #[test]
    fn exact_body_trajectory_drives_canal_without_endpoint_inference() {
        let body = settle_signed_yaw_actuation(
            YawBodyState::new(0).unwrap(),
            SignedYawActuation::new(90_000, 200_000).unwrap(),
        )
        .unwrap();
        let canal = settle_signed_yaw_trajectory(
            anatomy(),
            CanalState::at_rest(),
            SignedYawTrajectory::new(body.trajectory.as_slice()).unwrap(),
        )
        .unwrap();
        assert_eq!(canal.recovered_signed_motion_millidegrees, 90_000);
        assert!(canal.final_cupula_displacement_nanometres.parts().1 > 0);
        assert_eq!(canal.ticks_processed, body.ticks_processed);
    }

    #[test]
    fn restart_and_width_are_fixed() {
        let state = YawBodyState::new(123_456).unwrap();
        let encoded = encode_yaw_body_state(state);
        assert_eq!(encoded.len(), YawBodyState::resident_bytes());
        assert_eq!(decode_yaw_body_state(&encoded).unwrap(), state);
        assert_eq!(
            ExactYawTrajectory::transient_bytes(),
            size_of::<ExactYawTrajectory>()
        );
    }

    #[test]
    fn invalid_duration_heading_and_restart_are_refused() {
        assert_eq!(
            YawBodyState::new(360_000),
            Err(YawMotionError::InvalidHeading)
        );
        assert_eq!(
            SignedYawActuation::new(1, 999),
            Err(YawMotionError::InvalidDuration)
        );
        assert_eq!(
            SignedYawActuation::new(1, 5_001_000),
            Err(YawMotionError::InvalidDuration)
        );
        assert_eq!(
            decode_yaw_body_state(&[0; BODY_STATE_BYTES - 1]),
            Err(YawMotionError::InvalidRestart)
        );
    }
}
