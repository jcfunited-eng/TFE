//! Exact local gating-spring energy difference for one tip-link occurrence.
//!
//! The implemented relation is the two-conformation gating-spring energy law
//! ΔE(C->O) = ΔE° - kappa*d*(extension + x_C - d/2). Declared anatomy supplies
//! every coefficient with explicit physical units. The result is energy only;
//! this module does not produce probability, a threshold, a channel successor,
//! current, neuronal state, DSF, Krimelack, or cognition.

use core::mem::size_of;

use crate::exact_rational::{ExactRational, ExactRationalError};
use crate::local_tip_link_extension::LocalTipLinkOccurrence;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum GatingSpringEnergyError {
    NonPositiveStiffness,
    NonPositiveGateSwing,
    NegativeRestingExtension,
    ArithmeticWidth,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct GatingSpringEnergyAnatomy {
    stiffness_piconewtons_per_nanometre: ExactRational,
    gate_swing_nanometres: ExactRational,
    closed_resting_extension_nanometres: ExactRational,
    intrinsic_open_minus_closed_zeptojoules: ExactRational,
}

impl GatingSpringEnergyAnatomy {
    pub(crate) fn new(
        stiffness_piconewtons_per_nanometre: ExactRational,
        gate_swing_nanometres: ExactRational,
        closed_resting_extension_nanometres: ExactRational,
        intrinsic_open_minus_closed_zeptojoules: ExactRational,
    ) -> Result<Self, GatingSpringEnergyError> {
        if stiffness_piconewtons_per_nanometre.parts().0 <= 0 {
            return Err(GatingSpringEnergyError::NonPositiveStiffness);
        }
        if gate_swing_nanometres.parts().0 <= 0 {
            return Err(GatingSpringEnergyError::NonPositiveGateSwing);
        }
        if closed_resting_extension_nanometres.parts().0 < 0 {
            return Err(GatingSpringEnergyError::NegativeRestingExtension);
        }
        Ok(Self {
            stiffness_piconewtons_per_nanometre,
            gate_swing_nanometres,
            closed_resting_extension_nanometres,
            intrinsic_open_minus_closed_zeptojoules,
        })
    }

    pub(crate) fn resident_bytes() -> usize {
        size_of::<Self>()
    }

    pub(crate) fn exact_parts(
        self,
    ) -> (ExactRational, ExactRational, ExactRational, ExactRational) {
        (
            self.stiffness_piconewtons_per_nanometre,
            self.gate_swing_nanometres,
            self.closed_resting_extension_nanometres,
            self.intrinsic_open_minus_closed_zeptojoules,
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct GatingSpringEnergyOccurrence {
    pub(crate) loaded_closed_extension_nanometres: ExactRational,
    pub(crate) open_minus_closed_energy_zeptojoules: ExactRational,
    pub(crate) anatomy_bytes: usize,
}

pub(crate) fn settle_local_gating_spring_energy(
    anatomy: GatingSpringEnergyAnatomy,
    tip_link: LocalTipLinkOccurrence,
) -> Result<GatingSpringEnergyOccurrence, GatingSpringEnergyError> {
    let half_gate_swing = anatomy
        .gate_swing_nanometres
        .checked_div_unsigned(2)
        .map_err(map_exact_error)?;
    let loaded_closed_extension_nanometres = tip_link
        .signed_extension_nanometres
        .checked_add(anatomy.closed_resting_extension_nanometres)
        .and_then(|value| value.checked_sub(half_gate_swing))
        .map_err(map_exact_error)?;
    let mechanical_opening_work_zeptojoules = anatomy
        .stiffness_piconewtons_per_nanometre
        .checked_mul(anatomy.gate_swing_nanometres)
        .and_then(|value| value.checked_mul(loaded_closed_extension_nanometres))
        .map_err(map_exact_error)?;
    let open_minus_closed_energy_zeptojoules = anatomy
        .intrinsic_open_minus_closed_zeptojoules
        .checked_sub(mechanical_opening_work_zeptojoules)
        .map_err(map_exact_error)?;
    Ok(GatingSpringEnergyOccurrence {
        loaded_closed_extension_nanometres,
        open_minus_closed_energy_zeptojoules,
        anatomy_bytes: GatingSpringEnergyAnatomy::resident_bytes(),
    })
}

fn map_exact_error(_: ExactRationalError) -> GatingSpringEnergyError {
    GatingSpringEnergyError::ArithmeticWidth
}

#[cfg(test)]
mod tests {
    use super::*;

    fn anatomy() -> GatingSpringEnergyAnatomy {
        GatingSpringEnergyAnatomy::new(
            ExactRational::integer(1),
            ExactRational::integer(4),
            ExactRational::integer(2),
            ExactRational::integer(8),
        )
        .unwrap()
    }

    fn tip_link(extension: i128) -> LocalTipLinkOccurrence {
        LocalTipLinkOccurrence {
            signed_extension_nanometres: ExactRational::integer(extension),
            geometry_bytes: 8,
        }
    }

    #[test]
    fn exact_gating_spring_equation_returns_energy_not_a_decision() {
        let result = settle_local_gating_spring_energy(anatomy(), tip_link(1)).unwrap();
        assert_eq!(result.loaded_closed_extension_nanometres.parts(), (1, 1));
        assert_eq!(result.open_minus_closed_energy_zeptojoules.parts(), (4, 1));
        assert_eq!(result.anatomy_bytes, size_of::<GatingSpringEnergyAnatomy>());
    }

    #[test]
    fn opposing_extension_changes_energy_symmetrically_about_rest() {
        let rest = settle_local_gating_spring_energy(anatomy(), tip_link(0)).unwrap();
        let positive = settle_local_gating_spring_energy(anatomy(), tip_link(1)).unwrap();
        let negative = settle_local_gating_spring_energy(anatomy(), tip_link(-1)).unwrap();
        assert_eq!(rest.open_minus_closed_energy_zeptojoules.parts(), (8, 1));
        assert_eq!(
            positive.open_minus_closed_energy_zeptojoules.parts(),
            (4, 1)
        );
        assert_eq!(
            negative.open_minus_closed_energy_zeptojoules.parts(),
            (12, 1)
        );
    }

    #[test]
    fn exact_fractional_anatomy_and_occurrence_do_not_round() {
        let anatomy = GatingSpringEnergyAnatomy::new(
            ExactRational::new(3, 5).unwrap(),
            ExactRational::new(7, 2).unwrap(),
            ExactRational::new(11, 3).unwrap(),
            ExactRational::new(13, 7).unwrap(),
        )
        .unwrap();
        let result = settle_local_gating_spring_energy(
            anatomy,
            LocalTipLinkOccurrence {
                signed_extension_nanometres: ExactRational::new(5, 11).unwrap(),
                geometry_bytes: 8,
            },
        )
        .unwrap();
        assert_eq!(
            result.loaded_closed_extension_nanometres.parts(),
            (313, 132)
        );
        assert_eq!(
            result.open_minus_closed_energy_zeptojoules.parts(),
            (-9_617, 3_080)
        );
    }

    #[test]
    fn invalid_anatomy_has_no_default_or_clamp() {
        assert_eq!(
            GatingSpringEnergyAnatomy::new(
                ExactRational::integer(0),
                ExactRational::integer(4),
                ExactRational::integer(2),
                ExactRational::integer(8),
            ),
            Err(GatingSpringEnergyError::NonPositiveStiffness)
        );
        assert_eq!(
            GatingSpringEnergyAnatomy::new(
                ExactRational::integer(1),
                ExactRational::integer(-4),
                ExactRational::integer(2),
                ExactRational::integer(8),
            ),
            Err(GatingSpringEnergyError::NonPositiveGateSwing)
        );
        assert_eq!(
            GatingSpringEnergyAnatomy::new(
                ExactRational::integer(1),
                ExactRational::integer(4),
                ExactRational::integer(-2),
                ExactRational::integer(8),
            ),
            Err(GatingSpringEnergyError::NegativeRestingExtension)
        );
    }
}
