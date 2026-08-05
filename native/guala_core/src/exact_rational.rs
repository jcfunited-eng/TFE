//! Canonical exact signed rational arithmetic for isolated physical laws.
//!
//! This type preserves integer ratios without floating-point approximation.
//! It carries no biological kinetics, probability, threshold, ownership,
//! semantic meaning, DSF authority, or fallback value.

use core::cmp::Ordering;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ExactRationalError {
    ZeroDenominator,
    NonCanonicalRatio,
    ArithmeticWidth,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExactRational {
    numerator: i128,
    denominator: u128,
}

impl ExactRational {
    pub(crate) fn new(numerator: i128, denominator: u128) -> Result<Self, ExactRationalError> {
        if denominator == 0 {
            return Err(ExactRationalError::ZeroDenominator);
        }
        if numerator == 0 {
            if denominator != 1 {
                return Err(ExactRationalError::NonCanonicalRatio);
            }
            return Ok(Self::integer(0));
        }
        if gcd(numerator.unsigned_abs(), denominator) != 1 {
            return Err(ExactRationalError::NonCanonicalRatio);
        }
        Ok(Self {
            numerator,
            denominator,
        })
    }

    pub(crate) fn from_ratio(
        numerator: i128,
        denominator: u128,
    ) -> Result<Self, ExactRationalError> {
        if denominator == 0 {
            return Err(ExactRationalError::ZeroDenominator);
        }
        if numerator == 0 {
            return Ok(Self::integer(0));
        }
        let divisor = gcd(numerator.unsigned_abs(), denominator);
        let reduced_magnitude = numerator.unsigned_abs() / divisor;
        Ok(Self {
            numerator: signed_from_magnitude(numerator.is_negative(), reduced_magnitude)?,
            denominator: denominator / divisor,
        })
    }

    pub(crate) fn integer(value: i128) -> Self {
        Self {
            numerator: value,
            denominator: 1,
        }
    }

    pub(crate) fn parts(self) -> (i128, u128) {
        (self.numerator, self.denominator)
    }

    pub(crate) fn checked_neg(self) -> Result<Self, ExactRationalError> {
        Ok(Self {
            numerator: self
                .numerator
                .checked_neg()
                .ok_or(ExactRationalError::ArithmeticWidth)?,
            denominator: self.denominator,
        })
    }

    pub(crate) fn checked_abs(self) -> Result<Self, ExactRationalError> {
        if self.numerator.is_negative() {
            self.checked_neg()
        } else {
            Ok(self)
        }
    }

    /// Compare exactly without widening resident representation. Products that
    /// cannot be represented are refused rather than approximated.
    pub(crate) fn checked_cmp(self, other: Self) -> Result<Ordering, ExactRationalError> {
        match (self.numerator.is_negative(), other.numerator.is_negative()) {
            (true, false) => return Ok(Ordering::Less),
            (false, true) => return Ok(Ordering::Greater),
            _ => {}
        }
        let left = self
            .numerator
            .unsigned_abs()
            .checked_mul(other.denominator)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        let right = other
            .numerator
            .unsigned_abs()
            .checked_mul(self.denominator)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        let magnitude_order = left.cmp(&right);
        Ok(if self.numerator.is_negative() {
            magnitude_order.reverse()
        } else {
            magnitude_order
        })
    }

    pub(crate) fn checked_add(self, other: Self) -> Result<Self, ExactRationalError> {
        let shared = gcd(self.denominator, other.denominator);
        let left_scale = other.denominator / shared;
        let right_scale = self.denominator / shared;
        let left_scale =
            i128::try_from(left_scale).map_err(|_| ExactRationalError::ArithmeticWidth)?;
        let right_scale =
            i128::try_from(right_scale).map_err(|_| ExactRationalError::ArithmeticWidth)?;
        let left = self
            .numerator
            .checked_mul(left_scale)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        let right = other
            .numerator
            .checked_mul(right_scale)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        let denominator = self
            .denominator
            .checked_mul(other.denominator / shared)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        Self::from_ratio(
            left.checked_add(right)
                .ok_or(ExactRationalError::ArithmeticWidth)?,
            denominator,
        )
    }

    pub(crate) fn checked_sub(self, other: Self) -> Result<Self, ExactRationalError> {
        self.checked_add(other.checked_neg()?)
    }

    pub(crate) fn checked_mul(self, other: Self) -> Result<Self, ExactRationalError> {
        if self.numerator == 0 || other.numerator == 0 {
            return Ok(Self::integer(0));
        }
        let left_cancellation = gcd(self.numerator.unsigned_abs(), other.denominator);
        let right_cancellation = gcd(other.numerator.unsigned_abs(), self.denominator);
        let left_magnitude = self.numerator.unsigned_abs() / left_cancellation;
        let right_magnitude = other.numerator.unsigned_abs() / right_cancellation;
        let magnitude = left_magnitude
            .checked_mul(right_magnitude)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        let denominator = (self.denominator / right_cancellation)
            .checked_mul(other.denominator / left_cancellation)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        Self::new(
            signed_from_magnitude(
                self.numerator.is_negative() != other.numerator.is_negative(),
                magnitude,
            )?,
            denominator,
        )
    }

    pub(crate) fn checked_mul_unsigned(self, multiplier: u128) -> Result<Self, ExactRationalError> {
        if self.numerator == 0 || multiplier == 0 {
            return Ok(Self::integer(0));
        }
        let cancellation = gcd(multiplier, self.denominator);
        let magnitude = self
            .numerator
            .unsigned_abs()
            .checked_mul(multiplier / cancellation)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        Self::new(
            signed_from_magnitude(self.numerator.is_negative(), magnitude)?,
            self.denominator / cancellation,
        )
    }

    pub(crate) fn checked_div(self, divisor: Self) -> Result<Self, ExactRationalError> {
        if divisor.numerator == 0 {
            return Err(ExactRationalError::ZeroDenominator);
        }
        if self.numerator == 0 {
            return Ok(self);
        }
        let numerator_cancellation = gcd(
            self.numerator.unsigned_abs(),
            divisor.numerator.unsigned_abs(),
        );
        let denominator_cancellation = gcd(divisor.denominator, self.denominator);
        let magnitude = (self.numerator.unsigned_abs() / numerator_cancellation)
            .checked_mul(divisor.denominator / denominator_cancellation)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        let denominator = (self.denominator / denominator_cancellation)
            .checked_mul(divisor.numerator.unsigned_abs() / numerator_cancellation)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        Self::new(
            signed_from_magnitude(
                self.numerator.is_negative() != divisor.numerator.is_negative(),
                magnitude,
            )?,
            denominator,
        )
    }

    pub(crate) fn checked_div_unsigned(self, divisor: u128) -> Result<Self, ExactRationalError> {
        if divisor == 0 {
            return Err(ExactRationalError::ZeroDenominator);
        }
        if self.numerator == 0 {
            return Ok(self);
        }
        let cancellation = gcd(self.numerator.unsigned_abs(), divisor);
        let magnitude = self.numerator.unsigned_abs() / cancellation;
        let denominator = self
            .denominator
            .checked_mul(divisor / cancellation)
            .ok_or(ExactRationalError::ArithmeticWidth)?;
        Self::new(
            signed_from_magnitude(self.numerator.is_negative(), magnitude)?,
            denominator,
        )
    }
}

fn signed_from_magnitude(negative: bool, magnitude: u128) -> Result<i128, ExactRationalError> {
    if negative && magnitude == (i128::MAX as u128) + 1 {
        return Ok(i128::MIN);
    }
    let magnitude = i128::try_from(magnitude).map_err(|_| ExactRationalError::ArithmeticWidth)?;
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
    fn canonical_values_retain_exact_parts() {
        assert_eq!(ExactRational::new(-37, 11).unwrap().parts(), (-37, 11));
        assert_eq!(ExactRational::integer(0).parts(), (0, 1));
    }

    #[test]
    fn arbitrary_integer_ratio_is_reduced_exactly() {
        assert_eq!(
            ExactRational::from_ratio(90_000, 360_000).unwrap().parts(),
            (1, 4)
        );
        assert_eq!(
            ExactRational::from_ratio(-270_000, 360_000)
                .unwrap()
                .parts(),
            (-3, 4)
        );
        assert_eq!(ExactRational::from_ratio(0, 19).unwrap().parts(), (0, 1));
    }

    #[test]
    fn addition_and_subtraction_reduce_exactly() {
        let left = ExactRational::new(7, 10).unwrap();
        let right = ExactRational::new(11, 15).unwrap();
        assert_eq!(left.checked_add(right).unwrap().parts(), (43, 30));
        assert_eq!(left.checked_sub(right).unwrap().parts(), (-1, 30));
        assert_eq!(
            ExactRational::new(-7, 11)
                .unwrap()
                .checked_neg()
                .unwrap()
                .parts(),
            (7, 11)
        );
    }

    #[test]
    fn multiplication_cross_cancels_before_width_growth() {
        let left = ExactRational::new(i128::MAX, 11).unwrap();
        let right = ExactRational::new(11, i128::MAX as u128).unwrap();
        assert_eq!(left.checked_mul(right).unwrap().parts(), (1, 1));
        assert_eq!(
            ExactRational::new(-7, 13)
                .unwrap()
                .checked_mul(ExactRational::new(26, 5).unwrap())
                .unwrap()
                .parts(),
            (-14, 5)
        );
    }

    #[test]
    fn unsigned_division_cross_cancels_and_preserves_sign() {
        assert_eq!(
            ExactRational::new(-14, 5)
                .unwrap()
                .checked_div_unsigned(7)
                .unwrap()
                .parts(),
            (-2, 5)
        );
        assert_eq!(
            ExactRational::integer(0)
                .checked_div_unsigned(u128::MAX)
                .unwrap()
                .parts(),
            (0, 1)
        );
    }

    #[test]
    fn signed_division_absolute_value_and_comparison_are_exact() {
        assert_eq!(
            ExactRational::new(-14, 5)
                .unwrap()
                .checked_div(ExactRational::new(7, 3).unwrap())
                .unwrap()
                .parts(),
            (-6, 5)
        );
        assert_eq!(
            ExactRational::new(-3, 4)
                .unwrap()
                .checked_abs()
                .unwrap()
                .parts(),
            (3, 4)
        );
        assert_eq!(
            ExactRational::new(-3, 4)
                .unwrap()
                .checked_cmp(ExactRational::new(-2, 3).unwrap())
                .unwrap(),
            Ordering::Less
        );
        assert_eq!(
            ExactRational::new(2, 3)
                .unwrap()
                .checked_mul_unsigned(9)
                .unwrap()
                .parts(),
            (6, 1)
        );
    }

    #[test]
    fn fixed_width_operations_refuse_overflow() {
        assert_eq!(
            ExactRational::integer(i128::MAX).checked_mul_unsigned(2),
            Err(ExactRationalError::ArithmeticWidth)
        );
        assert_eq!(
            ExactRational::new(i128::MAX, 1)
                .unwrap()
                .checked_cmp(ExactRational::new(i128::MAX, 3).unwrap()),
            Err(ExactRationalError::ArithmeticWidth)
        );
        assert_eq!(
            ExactRational::integer(1).checked_div(ExactRational::integer(0)),
            Err(ExactRationalError::ZeroDenominator)
        );
    }

    #[test]
    fn noncanonical_zero_denominator_or_width_failure_is_refused() {
        assert_eq!(
            ExactRational::new(2, 4),
            Err(ExactRationalError::NonCanonicalRatio)
        );
        assert_eq!(
            ExactRational::new(1, 0),
            Err(ExactRationalError::ZeroDenominator)
        );
        assert_eq!(
            ExactRational::from_ratio(1, 0),
            Err(ExactRationalError::ZeroDenominator)
        );
        assert_eq!(
            ExactRational::integer(1).checked_div_unsigned(0),
            Err(ExactRationalError::ZeroDenominator)
        );
        assert_eq!(
            ExactRational::integer(i128::MIN).checked_neg(),
            Err(ExactRationalError::ArithmeticWidth)
        );
    }
}
