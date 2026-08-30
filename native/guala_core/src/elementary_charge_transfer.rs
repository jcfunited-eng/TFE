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


/// Wide-duration form of the same integration law: identical arithmetic
/// with the duration taken as `interval_microseconds x elapsed_clocks`,
/// widened before multiplication so arbitrarily long quiet spans integrate
/// in one exact step. `settle_elementary_charge_transfer(p, i, d)` equals
/// `settle_elementary_charge_transfer_clocks(p, i, d, 1)` by construction.
pub(crate) fn settle_elementary_charge_transfer_clocks(
    predecessor_phase: ChargeCarrierPhase,
    outward_current_picoamperes: ExactRational,
    interval_microseconds: u32,
    elapsed_clocks: u64,
) -> Result<ElementaryChargeTransition, ChargeTransferError> {
    if interval_microseconds == 0 || elapsed_clocks == 0 {
        return Err(ChargeTransferError::InvalidDuration);
    }
    let (current_numerator, current_denominator) = outward_current_picoamperes.parts();
    let (phase_numerator, phase_denominator) = predecessor_phase.parts();
    let wide_duration =
        BigInt::from(interval_microseconds) * BigInt::from(elapsed_clocks);
    let ideal_carrier_transfer = BigRational::new(
        BigInt::from(current_numerator)
            * wide_duration
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

/// Earliest whole number of clocks at which a contact under this standing
/// drive crosses its next whole elementary charge, computed — never
/// discovered by repeated settlement. `None` when the drive can never cross
/// (zero current). The claim proven by the oracle tests: settling at the
/// returned clock count transfers at least one whole carrier and settling
/// one clock earlier transfers none.
pub(crate) fn next_whole_carrier_crossing_clocks(
    predecessor_phase: ChargeCarrierPhase,
    outward_current_picoamperes: ExactRational,
    interval_microseconds: u32,
) -> Result<Option<u64>, ChargeTransferError> {
    if interval_microseconds == 0 {
        return Err(ChargeTransferError::InvalidDuration);
    }
    let (current_numerator, current_denominator) = outward_current_picoamperes.parts();
    if current_numerator == 0 {
        return Ok(None);
    }
    let (phase_numerator, phase_denominator) = predecessor_phase.parts();
    if let Some(crossing) = fixed_width_next_crossing(
        phase_numerator,
        phase_denominator,
        current_numerator,
        current_denominator,
        interval_microseconds,
    ) {
        return Ok(Some(crossing));
    }
    // Per-clock transfer t and remaining distance r to the next whole charge
    // in the drive's direction; the crossing is ceil(r / |t|) clocks.
    let per_clock_numerator = BigInt::from(current_numerator)
        * BigInt::from(interval_microseconds)
        * BigInt::from(ELEMENTARY_CHARGE_FEMTOCOULOMB_DENOMINATOR);
    let per_clock_denominator = BigInt::from(current_denominator)
        * BigInt::from(MICROSECONDS_PER_MILLISECOND)
        * BigInt::from(ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR);
    let per_clock = BigRational::new(per_clock_numerator, per_clock_denominator);
    let phase = BigRational::new(
        BigInt::from(phase_numerator),
        BigInt::from(phase_denominator),
    );
    let remaining = if per_clock < BigRational::from_integer(BigInt::from(0_u8)) {
        BigRational::from_integer(BigInt::from(-1_i8)) - phase
    } else {
        BigRational::from_integer(BigInt::from(1_u8)) - phase
    };
    let ratio = remaining / per_clock;
    debug_assert!(ratio >= BigRational::from_integer(BigInt::from(0_u8)));
    let ceiling = (ratio.numer() + ratio.denom() - BigInt::from(1_u8)) / ratio.denom();
    ceiling
        .to_u64()
        .map(Some)
        .ok_or(ChargeTransferError::ArithmeticWidth)
}

/// Exact cancellation-first form of the crossing equation. `None` means only
/// that a remaining product is wider than u128; the arbitrary-precision law
/// above then evaluates the same ratio. No rounded value leaves this helper.
fn fixed_width_next_crossing(
    phase_numerator: i128,
    phase_denominator: u128,
    current_numerator: i128,
    current_denominator: u128,
    interval_microseconds: u32,
) -> Option<u64> {
    let phase_magnitude = phase_numerator.unsigned_abs();
    let remaining = match (current_numerator.is_negative(), phase_numerator.is_negative()) {
        (false, false) => phase_denominator.checked_sub(phase_magnitude)?,
        (false, true) => phase_denominator.checked_add(phase_magnitude)?,
        (true, false) => phase_denominator.checked_add(phase_magnitude)?,
        (true, true) => phase_denominator.checked_sub(phase_magnitude)?,
    };
    let mut numerator_factors = [
        remaining,
        current_denominator,
        MICROSECONDS_PER_MILLISECOND,
        ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR,
    ];
    let mut denominator_factors = [
        phase_denominator,
        current_numerator.unsigned_abs(),
        u128::from(interval_microseconds),
        ELEMENTARY_CHARGE_FEMTOCOULOMB_DENOMINATOR,
    ];
    for numerator in &mut numerator_factors {
        for denominator in &mut denominator_factors {
            let divisor = gcd(*numerator, *denominator);
            *numerator /= divisor;
            *denominator /= divisor;
        }
    }
    let numerator = numerator_factors
        .into_iter()
        .try_fold(1_u128, u128::checked_mul)?;
    let denominator = denominator_factors
        .into_iter()
        .try_fold(1_u128, u128::checked_mul)?;
    let quotient = numerator / denominator;
    let ceiling = quotient.checked_add(u128::from(numerator % denominator != 0))?;
    u64::try_from(ceiling).ok()
}

pub(crate) fn settle_elementary_charge_transfer(
    predecessor_phase: ChargeCarrierPhase,
    outward_current_picoamperes: ExactRational,
    interval_microseconds: u32,
) -> Result<ElementaryChargeTransition, ChargeTransferError> {
    if interval_microseconds == 0 {
        return Err(ChargeTransferError::InvalidDuration);
    }
    if let Some(settled) = fixed_width_elementary_charge_transfer(
        predecessor_phase,
        outward_current_picoamperes,
        interval_microseconds,
    ) {
        return Ok(settled);
    }
    settle_elementary_charge_transfer_wide(
        predecessor_phase,
        outward_current_picoamperes,
        interval_microseconds,
    )
}

fn fixed_width_elementary_charge_transfer(
    predecessor_phase: ChargeCarrierPhase,
    outward_current_picoamperes: ExactRational,
    interval_microseconds: u32,
) -> Option<ElementaryChargeTransition> {
    let ideal = SignedRatio::from_external(outward_current_picoamperes)
        .ok()?
        .checked_mul_unsigned(u128::from(interval_microseconds))
        .ok()?
        .checked_mul_unsigned(ELEMENTARY_CHARGE_FEMTOCOULOMB_DENOMINATOR)
        .ok()?
        .checked_div_unsigned(MICROSECONDS_PER_MILLISECOND)
        .ok()?
        .checked_div_unsigned(ELEMENTARY_CHARGE_FEMTOCOULOMB_NUMERATOR)
        .ok()?;
    let accumulated = ideal.checked_add(predecessor_phase.ratio()).ok()?;
    let whole_magnitude = accumulated.numerator.unsigned_abs() / accumulated.denominator;
    let outward_elementary_charges =
        signed_from_magnitude(accumulated.numerator.is_negative(), whole_magnitude).ok()?;
    let unresolved_magnitude = accumulated.numerator.unsigned_abs() % accumulated.denominator;
    let unresolved_numerator = signed_from_magnitude(
        accumulated.numerator.is_negative(),
        unresolved_magnitude,
    )
    .ok()?;
    let successor_phase =
        ChargeCarrierPhase::new(unresolved_numerator, accumulated.denominator).ok()?;
    Some(ElementaryChargeTransition {
        successor_phase,
        outward_elementary_charges,
        interval_microseconds,
        resident_state_bytes: ChargeCarrierPhase::resident_bytes(),
    })
}

fn settle_elementary_charge_transfer_wide(
    predecessor_phase: ChargeCarrierPhase,
    outward_current_picoamperes: ExactRational,
    interval_microseconds: u32,
) -> Result<ElementaryChargeTransition, ChargeTransferError> {
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
    fn fixed_width_one_clock_settlement_matches_arbitrary_precision_law() {
        let current_numerators = [
            -1_000_000_i128,
            -801_088_317,
            -12,
            -1,
            0,
            1,
            12,
            801_088_317,
            1_000_000,
        ];
        let current_denominators = [1_u128, 3, 997, 5_000_000_000_000];
        let phase_numerators = [-998_i128, -1, 0, 1, 998];
        let durations = [1_u32, 250, 1_000, 250_000, u32::MAX];
        let mut fixed_width_cases = 0_usize;
        for current_numerator in current_numerators {
            for current_denominator in current_denominators {
                let canonical =
                    SignedRatio::canonical(current_numerator, current_denominator).unwrap();
                let current =
                    ExactRational::new(canonical.numerator, canonical.denominator).unwrap();
                for phase_numerator in phase_numerators {
                    let phase = ChargeCarrierPhase::new(phase_numerator, 999).unwrap();
                    for duration in durations {
                        let expected = settle_elementary_charge_transfer_wide(
                            phase,
                            current,
                            duration,
                        )
                        .unwrap();
                        let observed = settle_elementary_charge_transfer(phase, current, duration)
                            .unwrap();
                        assert_eq!(
                            observed, expected,
                            "current={current_numerator}/{current_denominator} phase={phase_numerator}/999 duration={duration}"
                        );
                        fixed_width_cases += usize::from(
                            fixed_width_elementary_charge_transfer(phase, current, duration)
                                .is_some(),
                        );
                    }
                }
            }
        }
        assert!(fixed_width_cases > 500);
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
