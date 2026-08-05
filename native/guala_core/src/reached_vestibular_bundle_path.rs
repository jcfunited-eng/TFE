//! One reached mechanical tick from signed body yaw through canal mechanics
//! to one local embedded vestibular hair bundle.
//!
//! The composition consumes no endpoint inference and stores no trajectory.
//! It reuses the exact canal and local-geometry laws atomically, so downstream
//! receptor mechanics can receive the complete time-ordered physical sequence.
//! It does not gate a channel, create current, evaluate DSF, or create cognition.

use core::mem::size_of;

use crate::local_cupula_hair_bundle_geometry::{
    settle_local_cupula_hair_bundle_geometry, CupulaBundleGeometryError, LocalCupulaBundleAnatomy,
    LocalHairBundleOccurrence,
};
use crate::virtual_vestibular_canal::{
    settle_signed_yaw_trajectory, CanalAnatomy, CanalState, ExactSignedRatio, SignedYawTrajectory,
    VestibularError, WORLD_MECHANICAL_TICK_MICROSECONDS,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ReachedVestibularBundleError {
    Canal(VestibularError),
    Bundle(CupulaBundleGeometryError),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ReachedVestibularBundleTick {
    pub(crate) predecessor_canal: CanalState,
    pub(crate) successor_canal: CanalState,
    pub(crate) canal_anatomy: CanalAnatomy,
    pub(crate) bundle_anatomy: LocalCupulaBundleAnatomy,
    pub(crate) central_cupula_displacement_nanometres: ExactSignedRatio,
    pub(crate) local_bundle: LocalHairBundleOccurrence,
    pub(crate) signed_body_motion_millidegrees: i32,
    pub(crate) interval_microseconds: u32,
    pub(crate) resident_canal_bytes: usize,
    pub(crate) resident_canal_anatomy_bytes: usize,
    pub(crate) resident_bundle_anatomy_bytes: usize,
}

pub(crate) fn settle_reached_vestibular_bundle_tick(
    canal_anatomy: CanalAnatomy,
    predecessor_canal: CanalState,
    signed_body_motion_millidegrees: i32,
    bundle_anatomy: LocalCupulaBundleAnatomy,
) -> Result<ReachedVestibularBundleTick, ReachedVestibularBundleError> {
    let one_tick = [signed_body_motion_millidegrees];
    let canal = settle_signed_yaw_trajectory(
        canal_anatomy,
        predecessor_canal,
        SignedYawTrajectory::new(&one_tick).map_err(ReachedVestibularBundleError::Canal)?,
    )
    .map_err(ReachedVestibularBundleError::Canal)?;
    let local_bundle = settle_local_cupula_hair_bundle_geometry(
        bundle_anatomy,
        canal.final_cupula_displacement_nanometres,
    )
    .map_err(ReachedVestibularBundleError::Bundle)?;
    Ok(ReachedVestibularBundleTick {
        predecessor_canal,
        successor_canal: canal.successor,
        canal_anatomy,
        bundle_anatomy,
        central_cupula_displacement_nanometres: canal.final_cupula_displacement_nanometres,
        local_bundle,
        signed_body_motion_millidegrees,
        interval_microseconds: WORLD_MECHANICAL_TICK_MICROSECONDS,
        resident_canal_bytes: CanalState::resident_bytes(),
        resident_canal_anatomy_bytes: size_of::<CanalAnatomy>(),
        resident_bundle_anatomy_bytes: LocalCupulaBundleAnatomy::resident_bytes(),
    })
}

pub(crate) fn resident_path_bytes() -> usize {
    CanalState::resident_bytes()
        + size_of::<CanalAnatomy>()
        + LocalCupulaBundleAnatomy::resident_bytes()
}

pub(crate) fn transient_tick_bytes() -> usize {
    size_of::<ReachedVestibularBundleTick>()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::exact_rational::ExactRational;
    use crate::virtual_vestibular_canal::PositiveRatio;

    fn canal_anatomy() -> CanalAnatomy {
        CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap()
    }

    fn bundle_anatomy() -> LocalCupulaBundleAnatomy {
        LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap()
    }

    #[test]
    fn reached_ticks_reproduce_the_batch_canal_without_storing_a_path() {
        let samples = [450_i32; 200];
        let batch = settle_signed_yaw_trajectory(
            canal_anatomy(),
            CanalState::at_rest(),
            SignedYawTrajectory::new(&samples).unwrap(),
        )
        .unwrap();
        let mut state = CanalState::at_rest();
        let mut last = None;
        for sample in samples {
            let tick = settle_reached_vestibular_bundle_tick(
                canal_anatomy(),
                state,
                sample,
                bundle_anatomy(),
            )
            .unwrap();
            state = tick.successor_canal;
            last = Some(tick);
        }
        let last = last.unwrap();
        assert_eq!(state, batch.successor);
        assert_eq!(
            last.central_cupula_displacement_nanometres,
            batch.final_cupula_displacement_nanometres
        );
        assert_eq!(last.interval_microseconds, 1_000);
        assert_eq!(last.signed_body_motion_millidegrees, 450);
        assert_eq!(last.canal_anatomy, canal_anatomy());
        assert_eq!(last.bundle_anatomy, bundle_anatomy());
    }

    #[test]
    fn rest_is_exactly_quiescent_through_both_mechanical_layers() {
        let tick = settle_reached_vestibular_bundle_tick(
            canal_anatomy(),
            CanalState::at_rest(),
            0,
            bundle_anatomy(),
        )
        .unwrap();
        assert_eq!(tick.successor_canal, CanalState::at_rest());
        assert_eq!(
            tick.central_cupula_displacement_nanometres.parts(),
            (false, 0, 1)
        );
        assert_eq!(
            tick.local_bundle.signed_tip_displacement_nanometres,
            ExactRational::integer(0)
        );
        assert_eq!(
            tick.local_bundle.signed_bundle_slope,
            ExactRational::integer(0)
        );
    }

    #[test]
    fn opposite_ticks_preserve_sign_through_the_complete_path() {
        let positive = settle_reached_vestibular_bundle_tick(
            canal_anatomy(),
            CanalState::at_rest(),
            1,
            bundle_anatomy(),
        )
        .unwrap();
        let negative = settle_reached_vestibular_bundle_tick(
            canal_anatomy(),
            CanalState::at_rest(),
            -1,
            bundle_anatomy(),
        )
        .unwrap();
        let positive_tip = positive
            .local_bundle
            .signed_tip_displacement_nanometres
            .parts();
        let negative_tip = negative
            .local_bundle
            .signed_tip_displacement_nanometres
            .parts();
        assert_eq!(positive_tip.0, -negative_tip.0);
        assert_eq!(positive_tip.1, negative_tip.1);
    }

    #[test]
    fn recurrent_operation_has_fixed_residency_and_transient_width() {
        let resident = resident_path_bytes();
        let transient = transient_tick_bytes();
        let mut state = CanalState::at_rest();
        for index in 0..100_000 {
            let signed_step = if index % 2 == 0 { 1 } else { -1 };
            let tick = settle_reached_vestibular_bundle_tick(
                canal_anatomy(),
                state,
                signed_step,
                bundle_anatomy(),
            )
            .unwrap();
            assert_eq!(tick.predecessor_canal, state);
            assert_eq!(tick.canal_anatomy, canal_anatomy());
            assert_eq!(tick.bundle_anatomy, bundle_anatomy());
            state = tick.successor_canal;
            assert_eq!(
                tick.resident_canal_bytes
                    + tick.resident_canal_anatomy_bytes
                    + tick.resident_bundle_anatomy_bytes,
                resident
            );
            assert_eq!(transient_tick_bytes(), transient);
        }
    }
}
