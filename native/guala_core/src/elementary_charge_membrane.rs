//! Fixed-residency membrane charge driven by reached elementary carriers.
//!
//! The membrane stores signed separated charge as an integer count of the
//! SI-defined elementary charge and carries the deterministic ensemble-current
//! phase from `elementary_charge_transfer`. Potential is derived from charge
//! and an explicit positive capacitance. No ion species is fabricated here:
//! K+/Ca2+ partition and compartment material transfer remain a separate local
//! fluid boundary.

use core::mem::size_of;

use crate::elementary_charge_transfer::{
    settle_elementary_charge_transfer, ChargeCarrierPhase, ChargeTransferError,
};
use crate::exact_rational::ExactRational;

const ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR: u128 = 801_088_317;
const ELEMENTARY_CHARGE_FEMTOCOULOMB_DENOMINATOR: u128 = 5_000_000_000_000;
const CODEC_BYTES: usize = 3 * size_of::<i128>();

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum MembraneChargeError {
    InvalidCapacitance,
    InvalidInterval,
    ChargeTransfer(ChargeTransferError),
    ArithmeticWidth,
    InvalidRestart,
}

impl From<ChargeTransferError> for MembraneChargeError {
    fn from(value: ChargeTransferError) -> Self {
        Self::ChargeTransfer(value)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MembraneCapacitance {
    picofarads: ExactRational,
}

impl MembraneCapacitance {
    pub(crate) fn new(picofarads: ExactRational) -> Result<Self, MembraneChargeError> {
        if picofarads.parts().0 <= 0 {
            return Err(MembraneChargeError::InvalidCapacitance);
        }
        Ok(Self { picofarads })
    }

    pub(crate) fn picofarads(self) -> ExactRational {
        self.picofarads
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ElementaryChargeMembraneState {
    separated_elementary_charges: i128,
    carrier_phase: ChargeCarrierPhase,
}

impl ElementaryChargeMembraneState {
    pub(crate) fn genesis(separated_elementary_charges: i128) -> Self {
        Self {
            separated_elementary_charges,
            carrier_phase: ChargeCarrierPhase::zero(),
        }
    }

    pub(crate) fn separated_elementary_charges(self) -> i128 {
        self.separated_elementary_charges
    }

    pub(crate) fn carrier_phase(self) -> ChargeCarrierPhase {
        self.carrier_phase
    }

    pub(crate) fn from_physical_parts(
        separated_elementary_charges: i128,
        carrier_phase: ChargeCarrierPhase,
    ) -> Self {
        Self {
            separated_elementary_charges,
            carrier_phase,
        }
    }

    pub(crate) fn resident_bytes() -> usize {
        size_of::<Self>()
    }

    pub(crate) fn potential_millivolts(
        self,
        capacitance: MembraneCapacitance,
    ) -> Result<ExactRational, MembraneChargeError> {
        potential_from_charge(self.separated_elementary_charges, capacitance)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MembraneCurrentTransition {
    pub(crate) predecessor: ElementaryChargeMembraneState,
    pub(crate) successor: ElementaryChargeMembraneState,
    pub(crate) outward_elementary_charges: i128,
    pub(crate) predecessor_potential_millivolts: ExactRational,
    pub(crate) successor_potential_millivolts: ExactRational,
    pub(crate) interval_microseconds: u32,
    pub(crate) resident_state_bytes: usize,
}

pub(crate) fn settle_membrane_current(
    capacitance: MembraneCapacitance,
    predecessor: ElementaryChargeMembraneState,
    outward_current_picoamperes: ExactRational,
    interval_microseconds: u32,
) -> Result<MembraneCurrentTransition, MembraneChargeError> {
    let carrier = settle_elementary_charge_transfer(
        predecessor.carrier_phase,
        outward_current_picoamperes,
        interval_microseconds,
    )?;
    let successor_charge = predecessor
        .separated_elementary_charges
        .checked_sub(carrier.outward_elementary_charges)
        .ok_or(MembraneChargeError::ArithmeticWidth)?;
    let successor = ElementaryChargeMembraneState {
        separated_elementary_charges: successor_charge,
        carrier_phase: carrier.successor_phase,
    };
    Ok(MembraneCurrentTransition {
        predecessor,
        successor,
        outward_elementary_charges: carrier.outward_elementary_charges,
        predecessor_potential_millivolts: predecessor.potential_millivolts(capacitance)?,
        successor_potential_millivolts: successor.potential_millivolts(capacitance)?,
        interval_microseconds,
        resident_state_bytes: ElementaryChargeMembraneState::resident_bytes(),
    })
}

pub(crate) fn settle_membrane_elementary_charges(
    capacitance: MembraneCapacitance,
    predecessor: ElementaryChargeMembraneState,
    outward_elementary_charges: i128,
    interval_microseconds: u32,
) -> Result<MembraneCurrentTransition, MembraneChargeError> {
    if interval_microseconds == 0 {
        return Err(MembraneChargeError::InvalidInterval);
    }
    let successor_charge = predecessor
        .separated_elementary_charges
        .checked_sub(outward_elementary_charges)
        .ok_or(MembraneChargeError::ArithmeticWidth)?;
    let successor = ElementaryChargeMembraneState {
        separated_elementary_charges: successor_charge,
        carrier_phase: predecessor.carrier_phase,
    };
    Ok(MembraneCurrentTransition {
        predecessor,
        successor,
        outward_elementary_charges,
        predecessor_potential_millivolts: predecessor.potential_millivolts(capacitance)?,
        successor_potential_millivolts: successor.potential_millivolts(capacitance)?,
        interval_microseconds,
        resident_state_bytes: ElementaryChargeMembraneState::resident_bytes(),
    })
}

fn potential_from_charge(
    separated_elementary_charges: i128,
    capacitance: MembraneCapacitance,
) -> Result<ExactRational, MembraneChargeError> {
    if separated_elementary_charges == 0 {
        return Ok(ExactRational::integer(0));
    }
    let (capacitance_numerator, capacitance_denominator) = capacitance.picofarads.parts();
    let capacitance_numerator = u128::try_from(capacitance_numerator)
        .map_err(|_| MembraneChargeError::InvalidCapacitance)?;
    let charge_capacitance_cross = gcd(
        separated_elementary_charges.unsigned_abs(),
        capacitance_numerator,
    );
    let electron_capacitance_cross = gcd(
        ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR,
        capacitance_numerator / charge_capacitance_cross,
    );
    let charge_magnitude = separated_elementary_charges.unsigned_abs() / charge_capacitance_cross;
    let electron_numerator = ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR / electron_capacitance_cross;
    let remaining_capacitance_numerator =
        capacitance_numerator / charge_capacitance_cross / electron_capacitance_cross;
    let numerator_magnitude = charge_magnitude
        .checked_mul(electron_numerator)
        .and_then(|value| value.checked_mul(capacitance_denominator))
        .ok_or(MembraneChargeError::ArithmeticWidth)?;
    let denominator = ELEMENTARY_CHARGE_FEMTOCOULOMB_DENOMINATOR
        .checked_mul(remaining_capacitance_numerator)
        .ok_or(MembraneChargeError::ArithmeticWidth)?;
    let final_divisor = gcd(numerator_magnitude, denominator);
    let numerator_magnitude = numerator_magnitude / final_divisor;
    let denominator = denominator / final_divisor;
    let numerator = signed_from_magnitude(
        separated_elementary_charges.is_negative(),
        numerator_magnitude,
    )?;
    ExactRational::new(numerator, denominator).map_err(|_| MembraneChargeError::ArithmeticWidth)
}

pub(crate) fn encode_membrane_state(state: ElementaryChargeMembraneState) -> [u8; CODEC_BYTES] {
    let (phase_numerator, phase_denominator) = state.carrier_phase.parts();
    let mut output = [0_u8; CODEC_BYTES];
    output[0..16].copy_from_slice(&state.separated_elementary_charges.to_le_bytes());
    output[16..32].copy_from_slice(&phase_numerator.to_le_bytes());
    output[32..48].copy_from_slice(&phase_denominator.to_le_bytes());
    output
}

pub(crate) fn decode_membrane_state(
    encoded: &[u8],
) -> Result<ElementaryChargeMembraneState, MembraneChargeError> {
    if encoded.len() != CODEC_BYTES {
        return Err(MembraneChargeError::InvalidRestart);
    }
    let separated_elementary_charges = i128::from_le_bytes(
        encoded[0..16]
            .try_into()
            .map_err(|_| MembraneChargeError::InvalidRestart)?,
    );
    let phase_numerator = i128::from_le_bytes(
        encoded[16..32]
            .try_into()
            .map_err(|_| MembraneChargeError::InvalidRestart)?,
    );
    let phase_denominator = u128::from_le_bytes(
        encoded[32..48]
            .try_into()
            .map_err(|_| MembraneChargeError::InvalidRestart)?,
    );
    let carrier_phase = ChargeCarrierPhase::new(phase_numerator, phase_denominator)
        .map_err(|_| MembraneChargeError::InvalidRestart)?;
    Ok(ElementaryChargeMembraneState {
        separated_elementary_charges,
        carrier_phase,
    })
}

fn signed_from_magnitude(negative: bool, magnitude: u128) -> Result<i128, MembraneChargeError> {
    if negative && magnitude == (i128::MAX as u128) + 1 {
        return Ok(i128::MIN);
    }
    let magnitude = i128::try_from(magnitude).map_err(|_| MembraneChargeError::ArithmeticWidth)?;
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

    fn chick_type_two_reference_capacitance() -> MembraneCapacitance {
        MembraneCapacitance::new(ExactRational::new(11, 2).unwrap()).unwrap()
    }

    #[test]
    fn potential_is_charge_over_explicit_capacitance() {
        let state = ElementaryChargeMembraneState::genesis(-2_059_698);
        assert_eq!(
            state
                .potential_millivolts(chick_type_two_reference_capacitance())
                .unwrap()
                .parts(),
            (-825000002174133, 13750000000000)
        );
    }

    #[test]
    fn inward_current_adds_positive_membrane_charge_and_depolarizes() {
        let capacitance = chick_type_two_reference_capacitance();
        let predecessor = ElementaryChargeMembraneState::genesis(-2_059_698);
        let transition =
            settle_membrane_current(capacitance, predecessor, ExactRational::integer(-12), 1_000)
                .unwrap();
        assert_eq!(transition.outward_elementary_charges, -74_898);
        assert_eq!(
            transition.successor.separated_elementary_charges(),
            -1_984_800
        );
        let (successor_numerator, successor_denominator) =
            transition.successor_potential_millivolts.parts();
        let (predecessor_numerator, predecessor_denominator) =
            transition.predecessor_potential_millivolts.parts();
        assert!(
            successor_numerator * i128::try_from(predecessor_denominator).unwrap()
                > predecessor_numerator * i128::try_from(successor_denominator).unwrap()
        );
    }

    #[test]
    fn zero_current_is_exact_membrane_quiescence() {
        let capacitance = chick_type_two_reference_capacitance();
        let predecessor = ElementaryChargeMembraneState::genesis(-2_059_698);
        let transition =
            settle_membrane_current(capacitance, predecessor, ExactRational::integer(0), 1_000)
                .unwrap();
        assert_eq!(transition.successor, predecessor);
        assert_eq!(
            transition.successor_potential_millivolts,
            transition.predecessor_potential_millivolts
        );
    }

    #[test]
    fn restart_preserves_the_next_reached_current_transition() {
        let capacitance = chick_type_two_reference_capacitance();
        let first = settle_membrane_current(
            capacitance,
            ElementaryChargeMembraneState::genesis(-2_059_698),
            ExactRational::new(-37, 11).unwrap(),
            1_000,
        )
        .unwrap();
        let encoded = encode_membrane_state(first.successor);
        let restored = decode_membrane_state(&encoded).unwrap();
        assert_eq!(restored, first.successor);
        assert_eq!(
            settle_membrane_current(
                capacitance,
                first.successor,
                ExactRational::new(19, 7).unwrap(),
                1_000,
            )
            .unwrap(),
            settle_membrane_current(
                capacitance,
                restored,
                ExactRational::new(19, 7).unwrap(),
                1_000,
            )
            .unwrap()
        );
    }

    #[test]
    fn alternating_current_keeps_fixed_residency_without_charge_drift() {
        let capacitance = chick_type_two_reference_capacitance();
        let origin = ElementaryChargeMembraneState::genesis(0);
        let mut state = origin;
        let width = ElementaryChargeMembraneState::resident_bytes();
        for _ in 0..100_000 {
            state = settle_membrane_current(
                capacitance,
                state,
                ExactRational::new(-37, 11).unwrap(),
                1_000,
            )
            .unwrap()
            .successor;
            state = settle_membrane_current(
                capacitance,
                state,
                ExactRational::new(37, 11).unwrap(),
                1_000,
            )
            .unwrap()
            .successor;
            assert_eq!(ElementaryChargeMembraneState::resident_bytes(), width);
        }
        assert_eq!(state, origin);
    }

    #[test]
    fn invalid_capacitance_and_restart_are_refused() {
        assert_eq!(
            MembraneCapacitance::new(ExactRational::integer(0)),
            Err(MembraneChargeError::InvalidCapacitance)
        );
        assert_eq!(
            decode_membrane_state(&[0_u8; CODEC_BYTES - 1]),
            Err(MembraneChargeError::InvalidRestart)
        );
    }
}
