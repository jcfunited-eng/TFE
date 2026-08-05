//! Exact local geometric transfer from central cupular displacement to one
//! embedded vestibular hair bundle.
//!
//! A declared virtual anatomy supplies the local displacement ratio and bundle
//! height. The law preserves signed displacement and derives an exact geometric
//! slope. It does not infer an angle, gating force, channel state, current,
//! neuronal phase, DSF, Krimelack, or cognition.

use core::mem::size_of;

use crate::exact_rational::{ExactRational, ExactRationalError};
use crate::virtual_vestibular_canal::ExactSignedRatio;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum CupulaBundleGeometryError {
    ZeroLocalTransfer,
    ZeroBundleHeight,
    ArithmeticWidth,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LocalCupulaBundleAnatomy {
    local_displacement_per_central_displacement: ExactRational,
    bundle_height_nanometres: u64,
}

impl LocalCupulaBundleAnatomy {
    pub(crate) fn new(
        local_transfer_numerator: u64,
        local_transfer_denominator: u64,
        bundle_height_nanometres: u64,
    ) -> Result<Self, CupulaBundleGeometryError> {
        if local_transfer_numerator == 0 {
            return Err(CupulaBundleGeometryError::ZeroLocalTransfer);
        }
        if bundle_height_nanometres == 0 {
            return Err(CupulaBundleGeometryError::ZeroBundleHeight);
        }
        let local_displacement_per_central_displacement = ExactRational::from_ratio(
            i128::from(local_transfer_numerator),
            u128::from(local_transfer_denominator),
        )
        .map_err(|_| CupulaBundleGeometryError::ArithmeticWidth)?;
        Ok(Self {
            local_displacement_per_central_displacement,
            bundle_height_nanometres,
        })
    }

    pub(crate) fn local_transfer(self) -> ExactRational {
        self.local_displacement_per_central_displacement
    }

    pub(crate) fn bundle_height_nanometres(self) -> u64 {
        self.bundle_height_nanometres
    }

    pub(crate) fn resident_bytes() -> usize {
        size_of::<Self>()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LocalHairBundleOccurrence {
    pub(crate) signed_tip_displacement_nanometres: ExactRational,
    pub(crate) signed_bundle_slope: ExactRational,
    pub(crate) anatomy_bytes: usize,
}

pub(crate) fn settle_local_cupula_hair_bundle_geometry(
    anatomy: LocalCupulaBundleAnatomy,
    central_cupula_displacement_nanometres: ExactSignedRatio,
) -> Result<LocalHairBundleOccurrence, CupulaBundleGeometryError> {
    let (negative, magnitude, denominator) = central_cupula_displacement_nanometres.parts();
    let magnitude =
        i128::try_from(magnitude).map_err(|_| CupulaBundleGeometryError::ArithmeticWidth)?;
    let signed_magnitude = if negative {
        magnitude
            .checked_neg()
            .ok_or(CupulaBundleGeometryError::ArithmeticWidth)?
    } else {
        magnitude
    };
    let central = ExactRational::from_ratio(signed_magnitude, u128::from(denominator))
        .map_err(map_exact_error)?;
    let signed_tip_displacement_nanometres = central
        .checked_mul(anatomy.local_displacement_per_central_displacement)
        .map_err(map_exact_error)?;
    let signed_bundle_slope = signed_tip_displacement_nanometres
        .checked_div_unsigned(u128::from(anatomy.bundle_height_nanometres))
        .map_err(map_exact_error)?;
    Ok(LocalHairBundleOccurrence {
        signed_tip_displacement_nanometres,
        signed_bundle_slope,
        anatomy_bytes: LocalCupulaBundleAnatomy::resident_bytes(),
    })
}

fn map_exact_error(_: ExactRationalError) -> CupulaBundleGeometryError {
    CupulaBundleGeometryError::ArithmeticWidth
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::virtual_vestibular_canal::{
        settle_signed_yaw_trajectory, CanalAnatomy, CanalState, PositiveRatio, SignedYawTrajectory,
    };

    fn canal_anatomy() -> CanalAnatomy {
        CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap()
    }

    fn central_displacement(step: i32) -> ExactSignedRatio {
        settle_signed_yaw_trajectory(
            canal_anatomy(),
            CanalState::at_rest(),
            SignedYawTrajectory::new(&[step]).unwrap(),
        )
        .unwrap()
        .final_cupula_displacement_nanometres
    }

    #[test]
    fn declared_geometry_preserves_exact_tip_displacement_and_slope() {
        let anatomy = LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap();
        let result =
            settle_local_cupula_hair_bundle_geometry(anatomy, central_displacement(1)).unwrap();
        assert_eq!(anatomy.local_transfer().parts(), (2, 5));
        assert_eq!(anatomy.bundle_height_nanometres(), 20_000);
        assert_eq!(result.signed_tip_displacement_nanometres.parts(), (71, 50));
        assert_eq!(result.signed_bundle_slope.parts(), (71, 1_000_000));
        assert_eq!(result.anatomy_bytes, size_of::<LocalCupulaBundleAnatomy>());
    }

    #[test]
    fn opposite_motion_is_exactly_symmetric() {
        let anatomy = LocalCupulaBundleAnatomy::new(3, 5, 80_000).unwrap();
        let positive =
            settle_local_cupula_hair_bundle_geometry(anatomy, central_displacement(1)).unwrap();
        let negative =
            settle_local_cupula_hair_bundle_geometry(anatomy, central_displacement(-1)).unwrap();
        let positive_tip = positive.signed_tip_displacement_nanometres.parts();
        let negative_tip = negative.signed_tip_displacement_nanometres.parts();
        assert_eq!(positive_tip.0, -negative_tip.0);
        assert_eq!(positive_tip.1, negative_tip.1);
        let positive_slope = positive.signed_bundle_slope.parts();
        let negative_slope = negative.signed_bundle_slope.parts();
        assert_eq!(positive_slope.0, -negative_slope.0);
        assert_eq!(positive_slope.1, negative_slope.1);
    }

    #[test]
    fn exact_rest_is_quiescent_without_a_gate() {
        let rest = settle_signed_yaw_trajectory(
            canal_anatomy(),
            CanalState::at_rest(),
            SignedYawTrajectory::new(&[0]).unwrap(),
        )
        .unwrap();
        let result = settle_local_cupula_hair_bundle_geometry(
            LocalCupulaBundleAnatomy::new(1, 2, 40_000).unwrap(),
            rest.final_cupula_displacement_nanometres,
        )
        .unwrap();
        assert_eq!(
            result.signed_tip_displacement_nanometres,
            ExactRational::integer(0)
        );
        assert_eq!(result.signed_bundle_slope, ExactRational::integer(0));
    }

    #[test]
    fn invalid_anatomy_is_refused_without_a_fallback() {
        assert_eq!(
            LocalCupulaBundleAnatomy::new(0, 1, 20_000),
            Err(CupulaBundleGeometryError::ZeroLocalTransfer)
        );
        assert_eq!(
            LocalCupulaBundleAnatomy::new(1, 2, 0),
            Err(CupulaBundleGeometryError::ZeroBundleHeight)
        );
        assert_eq!(
            LocalCupulaBundleAnatomy::new(1, 0, 20_000),
            Err(CupulaBundleGeometryError::ArithmeticWidth)
        );
    }
}
