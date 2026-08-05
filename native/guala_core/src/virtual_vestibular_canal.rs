//! Exact, bounded virtual semicircular-canal mechanics.
//!
//! This candidate consumes an already-physical signed yaw trajectory at the
//! embodiment world's one-millisecond mechanical lattice. It does not infer a
//! path from wrapped endpoints and does not generate body motion. Two local
//! relaxation states represent the fast and slow mechanical response. Their
//! velocity lattice is millidegrees per second, derived directly from the
//! body's admitted one-millidegree spatial lattice rather than a tuned sensing
//! threshold. No scheduler, database, DSF, Krimelack, or fluid-brain state is
//! involved.

use core::mem::size_of;
use core::num::NonZeroU64;

pub(crate) const WORLD_MECHANICAL_TICK_MICROSECONDS: u32 = 1_000;
pub(crate) const WORLD_MAX_ACTION_TICKS: usize = 5_000;
pub(crate) const VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND: i64 = 1_000;
const CODEC_BYTES: usize = 4 * size_of::<i64>();

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum VestibularError {
    ZeroTimeConstant,
    InvalidTimeConstants,
    InvalidGain,
    InvalidTrajectory,
    ArithmeticWidth,
    InvalidRestart,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PositiveRatio {
    numerator: u64,
    denominator: NonZeroU64,
}

impl PositiveRatio {
    pub(crate) fn new(numerator: u64, denominator: u64) -> Result<Self, VestibularError> {
        if numerator == 0 || denominator == 0 || gcd_u64(numerator, denominator) != 1 {
            return Err(VestibularError::InvalidGain);
        }
        Ok(Self {
            numerator,
            denominator: NonZeroU64::new(denominator).expect("nonzero checked"),
        })
    }

    pub(crate) fn parts(self) -> (u64, u64) {
        (self.numerator, self.denominator.get())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CanalAnatomy {
    fast_time_constant_ticks: NonZeroU64,
    slow_time_constant_ticks: NonZeroU64,
    cupula_nanometres_per_degree_per_second: PositiveRatio,
}

impl CanalAnatomy {
    pub(crate) fn new(
        fast_time_constant_ticks: u64,
        slow_time_constant_ticks: u64,
        cupula_nanometres_per_degree_per_second: PositiveRatio,
    ) -> Result<Self, VestibularError> {
        let fast_time_constant_ticks =
            NonZeroU64::new(fast_time_constant_ticks).ok_or(VestibularError::ZeroTimeConstant)?;
        let slow_time_constant_ticks =
            NonZeroU64::new(slow_time_constant_ticks).ok_or(VestibularError::ZeroTimeConstant)?;
        if fast_time_constant_ticks >= slow_time_constant_ticks
            || slow_time_constant_ticks.get() >= i64::MAX as u64
            || cupula_nanometres_per_degree_per_second
                .denominator
                .get()
                .checked_mul(VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND as u64)
                .is_none()
        {
            return Err(VestibularError::InvalidTimeConstants);
        }
        Ok(Self {
            fast_time_constant_ticks,
            slow_time_constant_ticks,
            cupula_nanometres_per_degree_per_second,
        })
    }

    pub(crate) fn fast_time_constant_ticks(self) -> u64 {
        self.fast_time_constant_ticks.get()
    }

    pub(crate) fn slow_time_constant_ticks(self) -> u64 {
        self.slow_time_constant_ticks.get()
    }

    pub(crate) fn cupula_gain(self) -> PositiveRatio {
        self.cupula_nanometres_per_degree_per_second
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct RelaxationState {
    millidegrees_per_second: i64,
    remainder: i64,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub(crate) struct CanalState {
    fast: RelaxationState,
    slow: RelaxationState,
}

impl CanalState {
    pub(crate) fn at_rest() -> Self {
        Self::default()
    }

    pub(crate) fn fast_millidegrees_per_second(self) -> i64 {
        self.fast.millidegrees_per_second
    }

    pub(crate) fn slow_millidegrees_per_second(self) -> i64 {
        self.slow.millidegrees_per_second
    }

    pub(crate) fn resident_bytes() -> usize {
        size_of::<Self>()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct SignedYawTrajectory<'a> {
    signed_millidegrees_by_tick: &'a [i32],
}

impl<'a> SignedYawTrajectory<'a> {
    pub(crate) fn new(signed_millidegrees_by_tick: &'a [i32]) -> Result<Self, VestibularError> {
        if signed_millidegrees_by_tick.is_empty()
            || signed_millidegrees_by_tick.len() > WORLD_MAX_ACTION_TICKS
        {
            return Err(VestibularError::InvalidTrajectory);
        }
        Ok(Self {
            signed_millidegrees_by_tick,
        })
    }

    pub(crate) fn signed_millidegrees_by_tick(self) -> &'a [i32] {
        self.signed_millidegrees_by_tick
    }

    pub(crate) fn duration_microseconds(self) -> u32 {
        u32::try_from(self.signed_millidegrees_by_tick.len())
            .expect("trajectory length is admitted")
            * WORLD_MECHANICAL_TICK_MICROSECONDS
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExactSignedRatio {
    negative: bool,
    magnitude: u128,
    denominator: NonZeroU64,
}

impl ExactSignedRatio {
    fn from_velocity_and_gain(
        velocity_millidegrees_per_second: i64,
        gain: PositiveRatio,
    ) -> Result<Self, VestibularError> {
        let numerator = (velocity_millidegrees_per_second.unsigned_abs() as u128)
            .checked_mul(gain.numerator as u128)
            .ok_or(VestibularError::ArithmeticWidth)?;
        if numerator == 0 {
            return Ok(Self {
                negative: false,
                magnitude: 0,
                denominator: NonZeroU64::new(1).expect("one is nonzero"),
            });
        }
        let denominator = gain
            .denominator
            .get()
            .checked_mul(VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND as u64)
            .ok_or(VestibularError::ArithmeticWidth)?;
        let divisor = gcd_u128_u64(numerator, denominator);
        Ok(Self {
            negative: velocity_millidegrees_per_second.is_negative(),
            magnitude: numerator / divisor as u128,
            denominator: NonZeroU64::new(denominator / divisor)
                .expect("gcd cannot exhaust denominator"),
        })
    }

    pub(crate) fn parts(self) -> (bool, u128, u64) {
        (self.negative, self.magnitude, self.denominator.get())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CanalTransition {
    pub(crate) successor: CanalState,
    pub(crate) final_cupula_displacement_nanometres: ExactSignedRatio,
    pub(crate) peak_positive_cupula_displacement_nanometres: ExactSignedRatio,
    pub(crate) peak_negative_cupula_displacement_nanometres: ExactSignedRatio,
    pub(crate) recovered_signed_motion_millidegrees: i64,
    pub(crate) ticks_processed: usize,
    pub(crate) resident_state_bytes: usize,
}

pub(crate) fn settle_signed_yaw_trajectory(
    anatomy: CanalAnatomy,
    predecessor: CanalState,
    trajectory: SignedYawTrajectory<'_>,
) -> Result<CanalTransition, VestibularError> {
    let mut successor = predecessor;
    let mut recovered_motion = 0_i64;
    let mut peak_positive = 0_i64;
    let mut peak_negative = 0_i64;

    for signed_millidegrees in trajectory.signed_millidegrees_by_tick {
        // 1 millidegree / 1 millisecond = 1 degree/second. The relaxation
        // state uses millidegrees/second so filtered sub-degree velocities are
        // retained on the body's own spatial lattice.
        let wall_velocity = i64::from(*signed_millidegrees)
            .checked_mul(VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND)
            .ok_or(VestibularError::ArithmeticWidth)?;
        recovered_motion = recovered_motion
            .checked_add(i64::from(*signed_millidegrees))
            .ok_or(VestibularError::ArithmeticWidth)?;
        successor.fast = relax_toward(
            successor.fast,
            wall_velocity,
            anatomy.fast_time_constant_ticks.get(),
        )?;
        successor.slow = relax_toward(
            successor.slow,
            wall_velocity,
            anatomy.slow_time_constant_ticks.get(),
        )?;
        let relative = successor
            .fast
            .millidegrees_per_second
            .checked_sub(successor.slow.millidegrees_per_second)
            .ok_or(VestibularError::ArithmeticWidth)?;
        peak_positive = peak_positive.max(relative);
        peak_negative = peak_negative.min(relative);
    }

    let final_relative = successor
        .fast
        .millidegrees_per_second
        .checked_sub(successor.slow.millidegrees_per_second)
        .ok_or(VestibularError::ArithmeticWidth)?;
    let gain = anatomy.cupula_nanometres_per_degree_per_second;
    Ok(CanalTransition {
        successor,
        final_cupula_displacement_nanometres: ExactSignedRatio::from_velocity_and_gain(
            final_relative,
            gain,
        )?,
        peak_positive_cupula_displacement_nanometres: ExactSignedRatio::from_velocity_and_gain(
            peak_positive,
            gain,
        )?,
        peak_negative_cupula_displacement_nanometres: ExactSignedRatio::from_velocity_and_gain(
            peak_negative,
            gain,
        )?,
        recovered_signed_motion_millidegrees: recovered_motion,
        ticks_processed: trajectory.signed_millidegrees_by_tick.len(),
        resident_state_bytes: CanalState::resident_bytes(),
    })
}

fn relax_toward(
    predecessor: RelaxationState,
    input_millidegrees_per_second: i64,
    time_constant_ticks: u64,
) -> Result<RelaxationState, VestibularError> {
    let denominator = time_constant_ticks
        .checked_add(1)
        .ok_or(VestibularError::ArithmeticWidth)? as i128;
    let numerator = i128::from(input_millidegrees_per_second)
        .checked_sub(i128::from(predecessor.millidegrees_per_second))
        .and_then(|value| value.checked_add(i128::from(predecessor.remainder)))
        .ok_or(VestibularError::ArithmeticWidth)?;
    let delta = numerator / denominator;
    let remainder = numerator % denominator;
    let value = i128::from(predecessor.millidegrees_per_second)
        .checked_add(delta)
        .ok_or(VestibularError::ArithmeticWidth)?;
    Ok(RelaxationState {
        millidegrees_per_second: i64::try_from(value)
            .map_err(|_| VestibularError::ArithmeticWidth)?,
        remainder: i64::try_from(remainder).map_err(|_| VestibularError::ArithmeticWidth)?,
    })
}

pub(crate) fn encode_canal_state(state: CanalState) -> [u8; CODEC_BYTES] {
    let values = [
        state.fast.millidegrees_per_second,
        state.fast.remainder,
        state.slow.millidegrees_per_second,
        state.slow.remainder,
    ];
    let mut output = [0_u8; CODEC_BYTES];
    for (index, value) in values.into_iter().enumerate() {
        let start = index * size_of::<i64>();
        output[start..start + size_of::<i64>()].copy_from_slice(&value.to_le_bytes());
    }
    output
}

pub(crate) fn decode_canal_state(
    anatomy: CanalAnatomy,
    encoded: &[u8],
) -> Result<CanalState, VestibularError> {
    if encoded.len() != CODEC_BYTES {
        return Err(VestibularError::InvalidRestart);
    }
    let mut values = [0_i64; 4];
    for (index, value) in values.iter_mut().enumerate() {
        let start = index * size_of::<i64>();
        *value = i64::from_le_bytes(
            encoded[start..start + size_of::<i64>()]
                .try_into()
                .map_err(|_| VestibularError::InvalidRestart)?,
        );
    }
    let state = CanalState {
        fast: RelaxationState {
            millidegrees_per_second: values[0],
            remainder: values[1],
        },
        slow: RelaxationState {
            millidegrees_per_second: values[2],
            remainder: values[3],
        },
    };
    let fast_bound = i64::try_from(anatomy.fast_time_constant_ticks.get() + 1)
        .map_err(|_| VestibularError::InvalidRestart)?;
    let slow_bound = i64::try_from(anatomy.slow_time_constant_ticks.get() + 1)
        .map_err(|_| VestibularError::InvalidRestart)?;
    if !fits_velocity_lattice(state.fast.millidegrees_per_second)
        || !fits_velocity_lattice(state.slow.millidegrees_per_second)
        || state.fast.remainder.unsigned_abs() >= fast_bound as u64
        || state.slow.remainder.unsigned_abs() >= slow_bound as u64
    {
        return Err(VestibularError::InvalidRestart);
    }
    Ok(state)
}

fn fits_velocity_lattice(value: i64) -> bool {
    let minimum = i64::from(i32::MIN) * VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND;
    let maximum = i64::from(i32::MAX) * VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND;
    minimum <= value && value <= maximum
}

fn gcd_u64(mut left: u64, mut right: u64) -> u64 {
    while right != 0 {
        let remainder = left % right;
        left = right;
        right = remainder;
    }
    left
}

fn gcd_u128_u64(mut left: u128, mut right: u64) -> u64 {
    while right != 0 {
        let remainder = (left % right as u128) as u64;
        left = right as u128;
        right = remainder;
    }
    left as u64
}

#[cfg(test)]
mod tests {
    use super::*;

    fn anatomy() -> CanalAnatomy {
        CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap()
    }

    #[test]
    fn rest_is_exact_quiescence() {
        let samples = [0_i32; 200];
        let trajectory = SignedYawTrajectory::new(&samples).unwrap();
        let result =
            settle_signed_yaw_trajectory(anatomy(), CanalState::at_rest(), trajectory).unwrap();
        assert_eq!(result.successor, CanalState::at_rest());
        assert_eq!(
            result.final_cupula_displacement_nanometres.parts(),
            (false, 0, 1)
        );
        assert_eq!(result.recovered_signed_motion_millidegrees, 0);
        assert_eq!(trajectory.duration_microseconds(), 200_000);
    }

    #[test]
    fn signed_motion_is_conserved_and_opposing_motion_is_symmetric() {
        let positive_samples = [450_i32; 200];
        let negative_samples = [-450_i32; 200];
        let positive = settle_signed_yaw_trajectory(
            anatomy(),
            CanalState::at_rest(),
            SignedYawTrajectory::new(&positive_samples).unwrap(),
        )
        .unwrap();
        let negative = settle_signed_yaw_trajectory(
            anatomy(),
            CanalState::at_rest(),
            SignedYawTrajectory::new(&negative_samples).unwrap(),
        )
        .unwrap();
        assert_eq!(positive.recovered_signed_motion_millidegrees, 90_000);
        assert_eq!(negative.recovered_signed_motion_millidegrees, -90_000);
        assert_eq!(
            positive.successor.fast_millidegrees_per_second(),
            -negative.successor.fast_millidegrees_per_second()
        );
        assert_eq!(
            positive.successor.slow_millidegrees_per_second(),
            -negative.successor.slow_millidegrees_per_second()
        );
        let positive_output = positive.final_cupula_displacement_nanometres.parts();
        let negative_output = negative.final_cupula_displacement_nanometres.parts();
        assert!(!positive_output.0);
        assert!(negative_output.0);
        assert_eq!(positive_output.1, negative_output.1);
        assert_eq!(positive_output.2, negative_output.2);
    }

    #[test]
    fn stopped_rotation_has_a_physical_opposing_after_response() {
        let rotation = [450_i32; 200];
        let moved = settle_signed_yaw_trajectory(
            anatomy(),
            CanalState::at_rest(),
            SignedYawTrajectory::new(&rotation).unwrap(),
        )
        .unwrap();
        let rest = [0_i32; WORLD_MAX_ACTION_TICKS];
        let stopped = settle_signed_yaw_trajectory(
            anatomy(),
            moved.successor,
            SignedYawTrajectory::new(&rest).unwrap(),
        )
        .unwrap();
        assert!(stopped.final_cupula_displacement_nanometres.parts().0);
        assert_eq!(stopped.recovered_signed_motion_millidegrees, 0);
    }

    #[test]
    fn byte_exact_restart_preserves_the_next_transition() {
        let first_samples = [150_i32; 300];
        let first = settle_signed_yaw_trajectory(
            anatomy(),
            CanalState::at_rest(),
            SignedYawTrajectory::new(&first_samples).unwrap(),
        )
        .unwrap();
        let encoded = encode_canal_state(first.successor);
        assert_eq!(encoded.len(), CanalState::resident_bytes());
        let restored = decode_canal_state(anatomy(), &encoded).unwrap();
        let next_samples = [-120_i32; 125];
        let next = SignedYawTrajectory::new(&next_samples).unwrap();
        assert_eq!(
            settle_signed_yaw_trajectory(anatomy(), first.successor, next).unwrap(),
            settle_signed_yaw_trajectory(anatomy(), restored, next).unwrap()
        );
    }

    #[test]
    fn residency_does_not_grow_with_age() {
        let positive = [1_i32];
        let negative = [-1_i32];
        let mut state = CanalState::at_rest();
        let width = CanalState::resident_bytes();
        for index in 0..100_000 {
            let samples = if index % 2 == 0 { &positive } else { &negative };
            state = settle_signed_yaw_trajectory(
                anatomy(),
                state,
                SignedYawTrajectory::new(samples).unwrap(),
            )
            .unwrap()
            .successor;
            assert_eq!(CanalState::resident_bytes(), width);
        }
        assert_eq!(width, 32);
    }

    #[test]
    fn invalid_trajectory_anatomy_and_restart_are_refused() {
        assert_eq!(
            SignedYawTrajectory::new(&[]).unwrap_err(),
            VestibularError::InvalidTrajectory
        );
        assert_eq!(
            CanalAnatomy::new(6, 6, PositiveRatio::new(25, 1).unwrap()).unwrap_err(),
            VestibularError::InvalidTimeConstants
        );
        assert_eq!(
            decode_canal_state(anatomy(), &[0_u8; 31]).unwrap_err(),
            VestibularError::InvalidRestart
        );
    }
}
