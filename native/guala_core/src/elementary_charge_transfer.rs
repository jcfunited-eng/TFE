//! Exact bounded conversion from reached macroscopic current to elementary
//! charge-carrier events.
//!
//! A measured ensemble current is continuous while physical charge carriers
//! are discrete. This local deterministic sigma-delta bridge integrates exact
//! picoamperes over exact microseconds, divides by the SI-defined elementary
//! charge, emits the reached whole signed carrier count, and retains only the
//! proper fractional phase for the next reached interval. The phase is an
//! algorithmic representation of unresolved ensemble current; it is not a
//! sub-electron, probability, membrane charge, scheduler, or cognitive state.

use core::mem::size_of;

use crate::exact_rational::ExactRational;

const ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR: u128 = 801_088_317;
const ELEMENTARY_CHARGE_FEMTOCOULOMB_DENOMINATOR: u128 = 5_000_000_000_000;
const MICROSECONDS_PER_MILLISECOND: u128 = 1_000;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ChargeTransferError {
    InvalidDuration,
    InvalidPhase,
    ArithmeticWidth,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ChargeCarrierPhase {
    numerator: i128,
    denominator: u128,
}

impl ChargeCarrierPhase {
    pub(crate) fn zero() -> Self {
        Self {
            numerator: 0,
            denominator: 1,
        }
    }

    pub(crate) fn new(numerator: i128, denominator: u128) -> Result<Self, ChargeTransferError> {
        if denominator == 0 || numerator.unsigned_abs() >= denominator {
            return Err(ChargeTransferError::InvalidPhase);
        }
        let ratio = SignedRatio::canonical(numerator, denominator)?;
        Ok(Self {
            numerator: ratio.numerator,
            denominator: ratio.denominator,
        })
    }

    pub(crate) fn parts(self) -> (i128, u128) {
        (self.numerator, self.denominator)
    }

    pub(crate) fn resident_bytes() -> usize {
        size_of::<Self>()
    }

    fn ratio(self) -> SignedRatio {
        SignedRatio {
            numerator: self.numerator,
            denominator: self.denominator,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ElementaryChargeTransition {
    pub(crate) successor_phase: ChargeCarrierPhase,
    pub(crate) outward_elementary_charges: i128,
    pub(crate) interval_microseconds: u32,
    pub(crate) resident_state_bytes: usize,
}

pub(crate) fn settle_elementary_charge_transfer(
    predecessor_phase: ChargeCarrierPhase,
    outward_current_picoamperes: ExactRational,
    interval_microseconds: u32,
) -> Result<ElementaryChargeTransition, ChargeTransferError> {
    if interval_microseconds == 0 {
        return Err(ChargeTransferError::InvalidDuration);
    }
    let current = SignedRatio::from_external(outward_current_picoamperes)?;
    let ideal_carrier_transfer = current
        .checked_mul_unsigned(u128::from(interval_microseconds))?
        .checked_mul_unsigned(ELEMENTARY_CHARGE_FEMTOCOULOMB_DENOMINATOR)?
        .checked_div_unsigned(MICROSECONDS_PER_MILLISECOND)?
        .checked_div_unsigned(ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR)?;
    let accumulated = predecessor_phase
        .ratio()
        .checked_add(ideal_carrier_transfer)?;
    let outward_elementary_charges = accumulated.numerator
        / i128::try_from(accumulated.denominator)
            .map_err(|_| ChargeTransferError::ArithmeticWidth)?;
    let unresolved_numerator = accumulated.numerator
        % i128::try_from(accumulated.denominator)
            .map_err(|_| ChargeTransferError::ArithmeticWidth)?;
    let successor = SignedRatio::canonical(unresolved_numerator, accumulated.denominator)?;
    let successor_phase = ChargeCarrierPhase::new(successor.numerator, successor.denominator)?;
    Ok(ElementaryChargeTransition {
        successor_phase,
        outward_elementary_charges,
        interval_microseconds,
        resident_state_bytes: ChargeCarrierPhase::resident_bytes(),
    })
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct SignedRatio {
    numerator: i128,
    denominator: u128,
}

impl SignedRatio {
    fn from_external(value: ExactRational) -> Result<Self, ChargeTransferError> {
        let (numerator, denominator) = value.parts();
        Self::canonical(numerator, denominator)
    }

    fn canonical(numerator: i128, denominator: u128) -> Result<Self, ChargeTransferError> {
        if denominator == 0 {
            return Err(ChargeTransferError::ArithmeticWidth);
        }
        if numerator == 0 {
            return Ok(Self {
                numerator: 0,
                denominator: 1,
            });
        }
        let divisor = gcd(numerator.unsigned_abs(), denominator);
        let magnitude = numerator.unsigned_abs() / divisor;
        Ok(Self {
            numerator: signed_from_magnitude(numerator.is_negative(), magnitude)?,
            denominator: denominator / divisor,
        })
    }

    fn checked_mul_unsigned(self, multiplier: u128) -> Result<Self, ChargeTransferError> {
        if multiplier == 0 || self.numerator == 0 {
            return Ok(Self {
                numerator: 0,
                denominator: 1,
            });
        }
        let divisor = gcd(multiplier, self.denominator);
        let multiplier = multiplier / divisor;
        let denominator = self.denominator / divisor;
        let multiplier =
            i128::try_from(multiplier).map_err(|_| ChargeTransferError::ArithmeticWidth)?;
        let numerator = self
            .numerator
            .checked_mul(multiplier)
            .ok_or(ChargeTransferError::ArithmeticWidth)?;
        Self::canonical(numerator, denominator)
    }

    fn checked_div_unsigned(self, divisor: u128) -> Result<Self, ChargeTransferError> {
        if divisor == 0 {
            return Err(ChargeTransferError::ArithmeticWidth);
        }
        if self.numerator == 0 {
            return Ok(self);
        }
        let cancellation = gcd(self.numerator.unsigned_abs(), divisor);
        let reduced_magnitude = self.numerator.unsigned_abs() / cancellation;
        let numerator = signed_from_magnitude(self.numerator.is_negative(), reduced_magnitude)?;
        let denominator = self
            .denominator
            .checked_mul(divisor / cancellation)
            .ok_or(ChargeTransferError::ArithmeticWidth)?;
        Self::canonical(numerator, denominator)
    }

    fn checked_add(self, other: Self) -> Result<Self, ChargeTransferError> {
        let shared = gcd(self.denominator, other.denominator);
        let left_scale = other.denominator / shared;
        let right_scale = self.denominator / shared;
        let left_scale =
            i128::try_from(left_scale).map_err(|_| ChargeTransferError::ArithmeticWidth)?;
        let right_scale =
            i128::try_from(right_scale).map_err(|_| ChargeTransferError::ArithmeticWidth)?;
        let left = self
            .numerator
            .checked_mul(left_scale)
            .ok_or(ChargeTransferError::ArithmeticWidth)?;
        let right = other
            .numerator
            .checked_mul(right_scale)
            .ok_or(ChargeTransferError::ArithmeticWidth)?;
        let denominator = self
            .denominator
            .checked_mul(other.denominator / shared)
            .ok_or(ChargeTransferError::ArithmeticWidth)?;
        Self::canonical(
            left.checked_add(right)
                .ok_or(ChargeTransferError::ArithmeticWidth)?,
            denominator,
        )
    }
}

fn signed_from_magnitude(negative: bool, magnitude: u128) -> Result<i128, ChargeTransferError> {
    if negative && magnitude == (i128::MAX as u128) + 1 {
        return Ok(i128::MIN);
    }
    let magnitude = i128::try_from(magnitude).map_err(|_| ChargeTransferError::ArithmeticWidth)?;
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

    #[test]
    fn exact_si_elementary_charge_converts_reached_current_without_rounding_loss() {
        let transition = settle_elementary_charge_transfer(
            ChargeCarrierPhase::zero(),
            ExactRational::integer(-12),
            1_000,
        )
        .unwrap();
        assert_eq!(transition.outward_elementary_charges, -74_898);
        assert_eq!(
            transition.successor_phase.parts(),
            (-29_077_778, 267_029_439)
        );
        assert_eq!(transition.interval_microseconds, 1_000);
    }

    #[test]
    fn zero_current_is_exact_quiescence() {
        let transition = settle_elementary_charge_transfer(
            ChargeCarrierPhase::zero(),
            ExactRational::integer(0),
            1_000,
        )
        .unwrap();
        assert_eq!(transition.outward_elementary_charges, 0);
        assert_eq!(transition.successor_phase, ChargeCarrierPhase::zero());
    }

    #[test]
    fn opposing_currents_are_samplewise_symmetric() {
        let positive = settle_elementary_charge_transfer(
            ChargeCarrierPhase::zero(),
            ExactRational::new(37, 11).unwrap(),
            1_000,
        )
        .unwrap();
        let negative = settle_elementary_charge_transfer(
            ChargeCarrierPhase::zero(),
            ExactRational::new(-37, 11).unwrap(),
            1_000,
        )
        .unwrap();
        assert_eq!(
            positive.outward_elementary_charges,
            -negative.outward_elementary_charges
        );
        assert_eq!(
            positive.successor_phase.parts().0,
            -negative.successor_phase.parts().0
        );
        assert_eq!(
            positive.successor_phase.parts().1,
            negative.successor_phase.parts().1
        );
    }

    #[test]
    fn recurrent_operation_has_fixed_residency_and_conserves_fractional_phase() {
        let mut phase = ChargeCarrierPhase::zero();
        let width = ChargeCarrierPhase::resident_bytes();
        let mut transferred = 0_i128;
        for _ in 0..100_000 {
            let transition =
                settle_elementary_charge_transfer(phase, ExactRational::integer(-12), 1_000)
                    .unwrap();
            transferred = transferred
                .checked_add(transition.outward_elementary_charges)
                .unwrap();
            phase = transition.successor_phase;
            assert_eq!(transition.resident_state_bytes, width);
        }
        let ideal = SignedRatio::canonical(
            -1_200_000_i128.checked_mul(5_000_000_000_000).unwrap(),
            801_088_317,
        )
        .unwrap();
        let recovered = SignedRatio::canonical(
            transferred
                .checked_mul(i128::try_from(phase.denominator).unwrap())
                .and_then(|value| value.checked_add(phase.numerator))
                .unwrap(),
            phase.denominator,
        )
        .unwrap();
        assert_eq!(recovered, ideal);
        assert_eq!(width, size_of::<ChargeCarrierPhase>());
    }

    #[test]
    fn invalid_duration_and_phase_are_refused() {
        assert_eq!(
            settle_elementary_charge_transfer(
                ChargeCarrierPhase::zero(),
                ExactRational::integer(1),
                0,
            ),
            Err(ChargeTransferError::InvalidDuration)
        );
        assert_eq!(
            ChargeCarrierPhase::new(1, 1),
            Err(ChargeTransferError::InvalidPhase)
        );
        let full_width = settle_elementary_charge_transfer(
            ChargeCarrierPhase::zero(),
            ExactRational::integer(0),
            u32::MAX,
        )
        .unwrap();
        assert_eq!(full_width.interval_microseconds, u32::MAX);
        assert_eq!(full_width.outward_elementary_charges, 0);
    }
}
