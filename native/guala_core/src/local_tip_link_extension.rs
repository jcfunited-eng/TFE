//! Exact tip-link extension from one local vestibular hair-bundle occurrence.
//!
//! Hair-bundle geometry gives the classical gain gamma = s / H, where s is
//! the separation of the tip-link insertion points and H is the height of the
//! taller stereocilium. The upstream bundle occurrence already carries X / H
//! as exact slope, so extension is exactly slope * s. This module supplies no
//! elasticity, thermal transition, channel conformation, current, or cognition.

use core::mem::size_of;

use crate::exact_rational::{ExactRational, ExactRationalError};
use crate::local_cupula_hair_bundle_geometry::LocalHairBundleOccurrence;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum TipLinkGeometryError {
    ZeroInsertionSeparation,
    ArithmeticWidth,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct TipLinkInsertionGeometry {
    insertion_separation_nanometres: u64,
}

impl TipLinkInsertionGeometry {
    pub(crate) fn new(insertion_separation_nanometres: u64) -> Result<Self, TipLinkGeometryError> {
        if insertion_separation_nanometres == 0 {
            return Err(TipLinkGeometryError::ZeroInsertionSeparation);
        }
        Ok(Self {
            insertion_separation_nanometres,
        })
    }

    pub(crate) fn insertion_separation_nanometres(self) -> u64 {
        self.insertion_separation_nanometres
    }

    pub(crate) fn resident_bytes() -> usize {
        size_of::<Self>()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LocalTipLinkOccurrence {
    pub(crate) signed_extension_nanometres: ExactRational,
    pub(crate) geometry_bytes: usize,
}

pub(crate) fn settle_local_tip_link_extension(
    geometry: TipLinkInsertionGeometry,
    bundle: LocalHairBundleOccurrence,
) -> Result<LocalTipLinkOccurrence, TipLinkGeometryError> {
    let signed_extension_nanometres = bundle
        .signed_bundle_slope
        .checked_mul(ExactRational::integer(i128::from(
            geometry.insertion_separation_nanometres,
        )))
        .map_err(map_exact_error)?;
    Ok(LocalTipLinkOccurrence {
        signed_extension_nanometres,
        geometry_bytes: TipLinkInsertionGeometry::resident_bytes(),
    })
}

fn map_exact_error(_: ExactRationalError) -> TipLinkGeometryError {
    TipLinkGeometryError::ArithmeticWidth
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::local_cupula_hair_bundle_geometry::LocalCupulaBundleAnatomy;
    use crate::reached_vestibular_bundle_path::settle_reached_vestibular_bundle_tick;
    use crate::virtual_vestibular_canal::{CanalAnatomy, CanalState, PositiveRatio};

    fn canal_anatomy() -> CanalAnatomy {
        CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap()
    }

    fn reached_bundle(signed_step: i32) -> LocalHairBundleOccurrence {
        settle_reached_vestibular_bundle_tick(
            canal_anatomy(),
            CanalState::at_rest(),
            signed_step,
            LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap(),
        )
        .unwrap()
        .local_bundle
    }

    #[test]
    fn exact_geometric_gain_extends_the_tip_link_without_a_gate() {
        let geometry = TipLinkInsertionGeometry::new(500).unwrap();
        let occurrence = settle_local_tip_link_extension(geometry, reached_bundle(1)).unwrap();
        assert_eq!(geometry.insertion_separation_nanometres(), 500);
        assert_eq!(occurrence.signed_extension_nanometres.parts(), (71, 2_000));
        assert_eq!(
            occurrence.geometry_bytes,
            size_of::<TipLinkInsertionGeometry>()
        );
    }

    #[test]
    fn opposite_body_motion_produces_opposite_exact_extension() {
        let geometry = TipLinkInsertionGeometry::new(500).unwrap();
        let positive = settle_local_tip_link_extension(geometry, reached_bundle(1)).unwrap();
        let negative = settle_local_tip_link_extension(geometry, reached_bundle(-1)).unwrap();
        let positive = positive.signed_extension_nanometres.parts();
        let negative = negative.signed_extension_nanometres.parts();
        assert_eq!(positive.0, -negative.0);
        assert_eq!(positive.1, negative.1);
    }

    #[test]
    fn rest_produces_no_tip_link_extension() {
        let occurrence = settle_local_tip_link_extension(
            TipLinkInsertionGeometry::new(500).unwrap(),
            reached_bundle(0),
        )
        .unwrap();
        assert_eq!(
            occurrence.signed_extension_nanometres,
            ExactRational::integer(0)
        );
    }

    #[test]
    fn absent_insertion_geometry_has_no_fallback() {
        assert_eq!(
            TipLinkInsertionGeometry::new(0),
            Err(TipLinkGeometryError::ZeroInsertionSeparation)
        );
    }
}
