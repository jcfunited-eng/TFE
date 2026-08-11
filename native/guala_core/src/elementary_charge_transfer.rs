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
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::ToPrimitive;

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
    let (current_numerator, current_denominator) = outward_current_picoamperes.parts();
    let (phase_numerator, phase_denominator) = predecessor_phase.parts();
    let ideal_carrier_transfer = BigRational::new(
        BigInt::from(current_numerator)
            * BigInt::from(interval_microseconds)
            * BigInt::from(ELEMENTARY_CHARGE_FEMTOCOULOMB_DENOMINATOR),
        BigInt::from(current_denominator)
            * BigInt::from(MICROSECONDS_PER_MILLISECOND)
            * BigInt::from(ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR),
    );
    let accumulated = ideal_carrier_transfer
        + BigRational::new(
            BigInt::from(phase_numerator),
            BigInt::from(phase_denominator),
        );
    let outward_elementary_charges = (accumulated.numer() / accumulated.denom())
        .to_i128()
        .ok_or(ChargeTransferError::ArithmeticWidth)?;
    let unresolved = accumulated
        - BigRational::from_integer(BigInt::from(outward_elementary_charges));
    let successor_phase = ChargeCarrierPhase::new(
        unresolved
            .numer()
            .to_i128()
            .ok_or(ChargeTransferError::ArithmeticWidth)?,
        unresolved
            .denom()
            .to_u128()
            .ok_or(ChargeTransferError::ArithmeticWidth)?,
    )?;
    Ok(ElementaryChargeTransition {
        successor_phase,
        outward_elementary_charges,
        interval_microseconds,
        resident_state_bytes: ChargeCarrierPhase::resident_bytes(),
    })
}

/// The exact current that moves no more than the locally available whole
/// carriers over this interval. If the requested current is reachable it is
/// unchanged. If material limits it, the returned current transports exactly
/// the available whole carriers and preserves the predecessor's unresolved
/// sub-carrier phase. This is carrier-limited conductivity, not a clamp chosen
/// by code: zero material yields zero current and finite material yields the
/// current that the SI charge quantum permits over the elapsed physical time.
pub(crate) fn current_limited_by_available_carriers(
    predecessor_phase: ChargeCarrierPhase,
    requested_current_picoamperes: ExactRational,
    interval_microseconds: u32,
    available_carriers: u128,
) -> Result<ExactRational, ChargeTransferError> {
    let requested = settle_elementary_charge_transfer(
        predecessor_phase,
        requested_current_picoamperes,
        interval_microseconds,
    )?;
    if requested.outward_elementary_charges.unsigned_abs() <= available_carriers {
        return Ok(requested_current_picoamperes);
    }
    if available_carriers == 0 {
        return Ok(ExactRational::integer(0));
    }
    let signed_carriers = if requested.outward_elementary_charges < 0 {
        -BigInt::from(available_carriers)
    } else {
        BigInt::from(available_carriers)
    };
    exact_current_for_big_whole_carrier_transfer(signed_carriers, interval_microseconds)
}

/// Exact ensemble current corresponding to a reached whole-carrier transfer.
/// This is the inverse of the SI elementary-charge integration used above;
/// it introduces no fractional carrier state.
pub(crate) fn exact_current_for_whole_carrier_transfer(
    outward_elementary_charges: i128,
    interval_microseconds: u32,
) -> Result<ExactRational, ChargeTransferError> {
    if interval_microseconds == 0 {
        return Err(ChargeTransferError::InvalidDuration);
    }
    exact_current_for_big_whole_carrier_transfer(
        BigInt::from(outward_elementary_charges),
        interval_microseconds,
    )
}

fn exact_current_for_big_whole_carrier_transfer(
    outward_elementary_charges: BigInt,
    interval_microseconds: u32,
) -> Result<ExactRational, ChargeTransferError> {
    let current = BigRational::new(
        outward_elementary_charges
            * BigInt::from(MICROSECONDS_PER_MILLISECOND)
            * BigInt::from(ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR),
        BigInt::from(interval_microseconds)
            * BigInt::from(ELEMENTARY_CHARGE_FEMTOCOULOMB_DENOMINATOR),
    );
    ExactRational::new(
        current
            .numer()
            .to_i128()
            .ok_or(ChargeTransferError::ArithmeticWidth)?,
        current
            .denom()
            .to_u128()
            .ok_or(ChargeTransferError::ArithmeticWidth)?,
    )
    .map_err(|_| ChargeTransferError::ArithmeticWidth)
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
