//! Exact local membrane-current balance across explicit conductive paths.
//!
//! Every reached path settles its own `I = g * (V - E)` current and its own
//! elementary-carrier phase before the signed carrier counts are summed at the
//! membrane capacitor. This separation is essential: equal opposing currents
//! can leave membrane charge unchanged while real material continues to cross
//! both paths. No path current is flattened into the net membrane current
//! before carrier settlement.
//!
//! The compile-time path count is anatomy, not a runtime cap. State size is
//! fixed for that anatomy and does not grow with organism age. This module
//! does not invent channel gating, ion composition, channel density, resting
//! target, material routing, or a recovery schedule.

use core::mem::size_of;

use crate::elementary_charge_membrane::{
    settle_membrane_elementary_charges, ElementaryChargeMembraneState, MembraneCapacitance,
    MembraneChargeError, MembraneCurrentTransition,
};
use crate::elementary_charge_transfer::{
    settle_elementary_charge_transfer, ChargeCarrierPhase, ChargeTransferError,
};
use crate::exact_rational::{ExactRational, ExactRationalError};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum MembraneConductanceError {
    NegativeConductance,
    ChargeTransfer(ChargeTransferError),
    Membrane(MembraneChargeError),
    ArithmeticWidth,
}

impl From<ChargeTransferError> for MembraneConductanceError {
    fn from(value: ChargeTransferError) -> Self {
        Self::ChargeTransfer(value)
    }
}

impl From<MembraneChargeError> for MembraneConductanceError {
    fn from(value: MembraneChargeError) -> Self {
        Self::Membrane(value)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LocalConductancePath {
    conductance_picosiemens: ExactRational,
    reversal_potential_millivolts: ExactRational,
}

impl LocalConductancePath {
    pub(crate) fn new(
        conductance_picosiemens: ExactRational,
        reversal_potential_millivolts: ExactRational,
    ) -> Result<Self, MembraneConductanceError> {
        if conductance_picosiemens.parts().0 < 0 {
            return Err(MembraneConductanceError::NegativeConductance);
        }
        Ok(Self {
            conductance_picosiemens,
            reversal_potential_millivolts,
        })
    }

    pub(crate) fn conductance_picosiemens(self) -> ExactRational {
        self.conductance_picosiemens
    }

    pub(crate) fn reversal_potential_millivolts(self) -> ExactRational {
        self.reversal_potential_millivolts
    }

    pub(crate) fn current_picoamperes(
        self,
        membrane_potential_millivolts: ExactRational,
    ) -> Result<ExactRational, MembraneConductanceError> {
        let driving_potential = checked_sub(
            membrane_potential_millivolts,
            self.reversal_potential_millivolts,
        )?;
        checked_div_positive_integer(
            checked_mul(self.conductance_picosiemens, driving_potential)?,
            1_000,
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LocalMembraneConductanceState<const PATHS: usize> {
    membrane: ElementaryChargeMembraneState,
    path_carrier_phases: [ChargeCarrierPhase; PATHS],
}

impl<const PATHS: usize> LocalMembraneConductanceState<PATHS> {
    pub(crate) fn genesis(separated_elementary_charges: i128) -> Self {
        Self {
            membrane: ElementaryChargeMembraneState::genesis(separated_elementary_charges),
            path_carrier_phases: [ChargeCarrierPhase::zero(); PATHS],
        }
    }

    pub(crate) fn membrane(self) -> ElementaryChargeMembraneState {
        self.membrane
    }

    pub(crate) fn path_carrier_phases(self) -> [ChargeCarrierPhase; PATHS] {
        self.path_carrier_phases
    }

    pub(crate) fn from_physical_parts(
        membrane: ElementaryChargeMembraneState,
        path_carrier_phases: [ChargeCarrierPhase; PATHS],
    ) -> Self {
        Self {
            membrane,
            path_carrier_phases,
        }
    }

    pub(crate) fn resident_bytes() -> usize {
        size_of::<Self>()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LocalMembraneConductanceTransition<const PATHS: usize> {
    pub(crate) predecessor: LocalMembraneConductanceState<PATHS>,
    pub(crate) successor: LocalMembraneConductanceState<PATHS>,
    pub(crate) path_currents_picoamperes: [ExactRational; PATHS],
    pub(crate) outward_elementary_charges_by_path: [i128; PATHS],
    pub(crate) net_outward_current_picoamperes: ExactRational,
    pub(crate) conductive_outward_elementary_charges: i128,
    pub(crate) active_transport_outward_elementary_charges: i128,
    pub(crate) inter_neuron_outward_elementary_charges: i128,
    pub(crate) net_outward_elementary_charges: i128,
    pub(crate) membrane: MembraneCurrentTransition,
    pub(crate) resident_state_bytes: usize,
}

pub(crate) fn settle_local_membrane_conductances<const PATHS: usize>(
    capacitance: MembraneCapacitance,
    predecessor: LocalMembraneConductanceState<PATHS>,
    reached_paths: &[LocalConductancePath; PATHS],
    interval_microseconds: u32,
) -> Result<LocalMembraneConductanceTransition<PATHS>, MembraneConductanceError> {
    settle_local_membrane_conductances_with_reached_charge_consequences(
        capacitance,
        predecessor,
        reached_paths,
        interval_microseconds,
        0,
        0,
    )
}

pub(crate) fn settle_local_membrane_conductances_with_active_transport<const PATHS: usize>(
    capacitance: MembraneCapacitance,
    predecessor: LocalMembraneConductanceState<PATHS>,
    reached_paths: &[LocalConductancePath; PATHS],
    interval_microseconds: u32,
    active_transport_outward_elementary_charges: i128,
) -> Result<LocalMembraneConductanceTransition<PATHS>, MembraneConductanceError> {
    settle_local_membrane_conductances_with_reached_charge_consequences(
        capacitance,
        predecessor,
        reached_paths,
        interval_microseconds,
        active_transport_outward_elementary_charges,
        0,
    )
}

pub(crate) fn settle_local_membrane_conductances_with_inter_neuron_contact<const PATHS: usize>(
    capacitance: MembraneCapacitance,
    predecessor: LocalMembraneConductanceState<PATHS>,
    reached_paths: &[LocalConductancePath; PATHS],
    interval_microseconds: u32,
    inter_neuron_outward_elementary_charges: i128,
) -> Result<LocalMembraneConductanceTransition<PATHS>, MembraneConductanceError> {
    settle_local_membrane_conductances_with_reached_charge_consequences(
        capacitance,
        predecessor,
        reached_paths,
        interval_microseconds,
        0,
        inter_neuron_outward_elementary_charges,
    )
}

pub(crate) fn settle_local_membrane_conductances_with_reached_charge_consequences<
    const PATHS: usize,
>(
    capacitance: MembraneCapacitance,
    predecessor: LocalMembraneConductanceState<PATHS>,
    reached_paths: &[LocalConductancePath; PATHS],
    interval_microseconds: u32,
    active_transport_outward_elementary_charges: i128,
    inter_neuron_outward_elementary_charges: i128,
) -> Result<LocalMembraneConductanceTransition<PATHS>, MembraneConductanceError> {
    let predecessor_potential = predecessor.membrane.potential_millivolts(capacitance)?;
    let mut successor_phases = predecessor.path_carrier_phases;
    let mut path_currents = [ExactRational::integer(0); PATHS];
    let mut outward_charges_by_path = [0_i128; PATHS];
    let mut net_current = ExactRational::integer(0);
    let mut net_outward_charges = 0_i128;

    for path_index in 0..PATHS {
        let current = reached_paths[path_index].current_picoamperes(predecessor_potential)?;
        let carrier = settle_elementary_charge_transfer(
            predecessor.path_carrier_phases[path_index],
            current,
            interval_microseconds,
        )?;
        path_currents[path_index] = current;
        outward_charges_by_path[path_index] = carrier.outward_elementary_charges;
        successor_phases[path_index] = carrier.successor_phase;
        net_current = checked_add(net_current, current)?;
        net_outward_charges = net_outward_charges
            .checked_add(carrier.outward_elementary_charges)
            .ok_or(MembraneConductanceError::ArithmeticWidth)?;
    }

    let total_outward_charges = net_outward_charges
        .checked_add(active_transport_outward_elementary_charges)
        .and_then(|value| value.checked_add(inter_neuron_outward_elementary_charges))
        .ok_or(MembraneConductanceError::ArithmeticWidth)?;
    let membrane = settle_membrane_elementary_charges(
        capacitance,
        predecessor.membrane,
        total_outward_charges,
        interval_microseconds,
    )?;
    let successor = LocalMembraneConductanceState {
        membrane: membrane.successor,
        path_carrier_phases: successor_phases,
    };
    Ok(LocalMembraneConductanceTransition {
        predecessor,
        successor,
        path_currents_picoamperes: path_currents,
        outward_elementary_charges_by_path: outward_charges_by_path,
        net_outward_current_picoamperes: net_current,
        conductive_outward_elementary_charges: net_outward_charges,
        active_transport_outward_elementary_charges,
        inter_neuron_outward_elementary_charges,
        net_outward_elementary_charges: total_outward_charges,
        membrane,
        resident_state_bytes: LocalMembraneConductanceState::<PATHS>::resident_bytes(),
    })
}

fn checked_add(
    left: ExactRational,
    right: ExactRational,
) -> Result<ExactRational, MembraneConductanceError> {
    let (left_numerator, left_denominator) = left.parts();
    let (right_numerator, right_denominator) = right.parts();
    let common_divisor = gcd(left_denominator, right_denominator);
    let left_scale = right_denominator / common_divisor;
    let right_scale = left_denominator / common_divisor;
    let left_scaled = left_numerator
        .checked_mul(
            i128::try_from(left_scale).map_err(|_| MembraneConductanceError::ArithmeticWidth)?,
        )
        .ok_or(MembraneConductanceError::ArithmeticWidth)?;
    let right_scaled = right_numerator
        .checked_mul(
            i128::try_from(right_scale).map_err(|_| MembraneConductanceError::ArithmeticWidth)?,
        )
        .ok_or(MembraneConductanceError::ArithmeticWidth)?;
    let denominator = left_denominator
        .checked_mul(left_scale)
        .ok_or(MembraneConductanceError::ArithmeticWidth)?;
    canonical(
        left_scaled
            .checked_add(right_scaled)
            .ok_or(MembraneConductanceError::ArithmeticWidth)?,
        denominator,
    )
}

fn checked_sub(
    left: ExactRational,
    right: ExactRational,
) -> Result<ExactRational, MembraneConductanceError> {
    let (right_numerator, right_denominator) = right.parts();
    let negated = right_numerator
        .checked_neg()
        .ok_or(MembraneConductanceError::ArithmeticWidth)?;
    checked_add(
        left,
        ExactRational::new(negated, right_denominator)
            .map_err(|_| MembraneConductanceError::ArithmeticWidth)?,
    )
}

fn checked_mul(
    left: ExactRational,
    right: ExactRational,
) -> Result<ExactRational, MembraneConductanceError> {
    let (left_numerator, left_denominator) = left.parts();
    let (right_numerator, right_denominator) = right.parts();
    let left_cross = gcd(left_numerator.unsigned_abs(), right_denominator);
    let right_cross = gcd(right_numerator.unsigned_abs(), left_denominator);
    let left_reduced = divide_signed(left_numerator, left_cross)?;
    let right_reduced = divide_signed(right_numerator, right_cross)?;
    canonical(
        left_reduced
            .checked_mul(right_reduced)
            .ok_or(MembraneConductanceError::ArithmeticWidth)?,
        (left_denominator / right_cross)
            .checked_mul(right_denominator / left_cross)
            .ok_or(MembraneConductanceError::ArithmeticWidth)?,
    )
}

fn checked_div_positive_integer(
    value: ExactRational,
    divisor: u128,
) -> Result<ExactRational, MembraneConductanceError> {
    let (numerator, denominator) = value.parts();
    let cross = gcd(numerator.unsigned_abs(), divisor);
    canonical(
        divide_signed(numerator, cross)?,
        denominator
            .checked_mul(divisor / cross)
            .ok_or(MembraneConductanceError::ArithmeticWidth)?,
    )
}

fn divide_signed(value: i128, divisor: u128) -> Result<i128, MembraneConductanceError> {
    let magnitude = value.unsigned_abs() / divisor;
    signed_from_magnitude(value.is_negative(), magnitude)
}

fn canonical(
    numerator: i128,
    denominator: u128,
) -> Result<ExactRational, MembraneConductanceError> {
    if denominator == 0 {
        return Err(MembraneConductanceError::ArithmeticWidth);
    }
    if numerator == 0 {
        return Ok(ExactRational::integer(0));
    }
    let divisor = gcd(numerator.unsigned_abs(), denominator);
    ExactRational::new(
        signed_from_magnitude(numerator.is_negative(), numerator.unsigned_abs() / divisor)?,
        denominator / divisor,
    )
    .map_err(|error| match error {
        ExactRationalError::ArithmeticWidth
        | ExactRationalError::NonCanonicalRatio
        | ExactRationalError::ZeroDenominator => MembraneConductanceError::ArithmeticWidth,
    })
}

fn signed_from_magnitude(
    negative: bool,
    magnitude: u128,
) -> Result<i128, MembraneConductanceError> {
    if negative && magnitude == (i128::MAX as u128) + 1 {
        return Ok(i128::MIN);
    }
    let magnitude =
        i128::try_from(magnitude).map_err(|_| MembraneConductanceError::ArithmeticWidth)?;
    Ok(if negative { -magnitude } else { magnitude })
}

fn gcd(mut left: u128, mut right: u128) -> u128 {
    while right != 0 {
        let remainder = left % right;
        left = right;
        right = remainder;
    }
    left
}

#[cfg(test)]
mod tests {
    use super::*;

    fn proof_capacitance() -> MembraneCapacitance {
        // With one million separated charges this capacitance yields exactly
        // fifty millivolts. It is a unit-proof fixture, not organism anatomy.
        MembraneCapacitance::new(ExactRational::new(801_088_317, 250_000_000).unwrap()).unwrap()
    }

    fn path(conductance: i128, reversal: i128) -> LocalConductancePath {
        LocalConductancePath::new(
            ExactRational::integer(conductance),
            ExactRational::integer(reversal),
        )
        .unwrap()
    }

    #[test]
    fn opposed_currents_preserve_material_flux_when_net_charge_is_zero() {
        let state = LocalMembraneConductanceState::<2>::genesis(-1_000_000);
        assert_eq!(
            state
                .membrane()
                .potential_millivolts(proof_capacitance())
                .unwrap()
                .parts(),
            (-50, 1)
        );
        let settled = settle_local_membrane_conductances(
            proof_capacitance(),
            state,
            &[path(240, 0), path(240, -100)],
            1_000,
        )
        .unwrap();
        assert_eq!(settled.path_currents_picoamperes[0].parts(), (-12, 1));
        assert_eq!(settled.path_currents_picoamperes[1].parts(), (12, 1));
        assert_eq!(
            settled.outward_elementary_charges_by_path,
            [-74_898, 74_898]
        );
        assert_eq!(settled.net_outward_current_picoamperes.parts(), (0, 1));
        assert_eq!(settled.net_outward_elementary_charges, 0);
        assert_eq!(settled.successor.membrane(), state.membrane());
        assert_ne!(
            settled.successor.path_carrier_phases(),
            state.path_carrier_phases()
        );
    }

    #[test]
    fn local_current_direction_is_restorative_on_both_sides_of_equilibrium() {
        let paths = [path(240, 0), path(240, -100)];
        let more_negative = settle_local_membrane_conductances(
            proof_capacitance(),
            LocalMembraneConductanceState::<2>::genesis(-1_100_000),
            &paths,
            1_000,
        )
        .unwrap();
        let less_negative = settle_local_membrane_conductances(
            proof_capacitance(),
            LocalMembraneConductanceState::<2>::genesis(-900_000),
            &paths,
            1_000,
        )
        .unwrap();
        assert!(more_negative.net_outward_current_picoamperes.parts().0 < 0);
        assert!(more_negative.net_outward_elementary_charges < 0);
        assert!(
            more_negative
                .successor
                .membrane()
                .separated_elementary_charges()
                > more_negative
                    .predecessor
                    .membrane()
                    .separated_elementary_charges()
        );
        assert!(less_negative.net_outward_current_picoamperes.parts().0 > 0);
        assert!(less_negative.net_outward_elementary_charges > 0);
        assert!(
            less_negative
                .successor
                .membrane()
                .separated_elementary_charges()
                < less_negative
                    .predecessor
                    .membrane()
                    .separated_elementary_charges()
        );
    }

    #[test]
    fn closed_or_reversal_matched_paths_are_exactly_quiescent() {
        let state = LocalMembraneConductanceState::<2>::genesis(-1_000_000);
        let closed =
            LocalConductancePath::new(ExactRational::integer(0), ExactRational::integer(777))
                .unwrap();
        let reversal_matched = path(19_000, -50);
        let settled = settle_local_membrane_conductances(
            proof_capacitance(),
            state,
            &[closed, reversal_matched],
            1_000,
        )
        .unwrap();
        assert_eq!(settled.path_currents_picoamperes[0].parts(), (0, 1));
        assert_eq!(settled.path_currents_picoamperes[1].parts(), (0, 1));
        assert_eq!(settled.outward_elementary_charges_by_path, [0, 0]);
        assert_eq!(settled.successor, state);
    }

    #[test]
    fn negative_conductance_is_not_a_physical_path() {
        assert_eq!(
            LocalConductancePath::new(ExactRational::integer(-1), ExactRational::integer(0),),
            Err(MembraneConductanceError::NegativeConductance)
        );
    }

    #[test]
    fn inter_neuron_carriers_join_local_paths_before_one_membrane_commit() {
        let state = LocalMembraneConductanceState::<1>::genesis(1_000_000);
        let closed =
            LocalConductancePath::new(ExactRational::integer(0), ExactRational::integer(0))
                .unwrap();
        let settled = settle_local_membrane_conductances_with_inter_neuron_contact(
            proof_capacitance(),
            state,
            &[closed],
            1_000,
            17,
        )
        .unwrap();
        assert_eq!(settled.conductive_outward_elementary_charges, 0);
        assert_eq!(settled.active_transport_outward_elementary_charges, 0);
        assert_eq!(settled.inter_neuron_outward_elementary_charges, 17);
        assert_eq!(settled.net_outward_elementary_charges, 17);
        assert_eq!(
            settled.successor.membrane().separated_elementary_charges(),
            999_983
        );
        assert_eq!(
            settled.successor.path_carrier_phases(),
            state.path_carrier_phases()
        );
    }

    #[test]
    fn age_does_not_expand_state_or_erase_opposed_material_flow() {
        let capacitance = proof_capacitance();
        let paths = [path(240, 0), path(240, -100)];
        let origin = LocalMembraneConductanceState::<2>::genesis(-1_000_000);
        let mut state = origin;
        let mut inward_path_total = 0_i128;
        let mut outward_path_total = 0_i128;
        for _ in 0..100_000 {
            let settled =
                settle_local_membrane_conductances(capacitance, state, &paths, 1_000).unwrap();
            inward_path_total = inward_path_total
                .checked_add(settled.outward_elementary_charges_by_path[0])
                .unwrap();
            outward_path_total = outward_path_total
                .checked_add(settled.outward_elementary_charges_by_path[1])
                .unwrap();
            assert_eq!(settled.net_outward_elementary_charges, 0);
            assert_eq!(
                settled.resident_state_bytes,
                LocalMembraneConductanceState::<2>::resident_bytes()
            );
            state = settled.successor;
        }
        assert!(inward_path_total < 0);
        assert!(outward_path_total > 0);
        assert_eq!(inward_path_total, -outward_path_total);
        assert_eq!(state.membrane(), origin.membrane());
        assert_eq!(
            size_of::<LocalMembraneConductanceState<2>>(),
            LocalMembraneConductanceState::<2>::resident_bytes()
        );
    }
}
