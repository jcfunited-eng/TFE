//! Fixed-width exact arithmetic for the electrical hot path.
//!
//! Every quantity in the per-contact settlement law is a ratio of integers
//! whose denominators are fixed by anatomy and unit constants.  This module
//! evaluates the same law in fixed-width machine arithmetic — widening only
//! transient products to 256 bits, exactly as the resident doctrine widens
//! temporaries — and reduces results to the identical canonical parts the
//! arbitrary-precision path stores.  Any width the fixed form cannot hold
//! answers `None` and the caller runs the original path; no value is ever
//! approximated.

/// Unsigned 256-bit value as four little-endian 64-bit limbs.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct U256 {
    limbs: [u64; 4],
}

impl U256 {
    pub(crate) const ZERO: U256 = U256 { limbs: [0; 4] };

    pub(crate) fn from_u128(value: u128) -> U256 {
        U256 {
            limbs: [value as u64, (value >> 64) as u64, 0, 0],
        }
    }

    pub(crate) fn to_u128(self) -> Option<u128> {
        if self.limbs[2] != 0 || self.limbs[3] != 0 {
            return None;
        }
        Some(u128::from(self.limbs[0]) | (u128::from(self.limbs[1]) << 64))
    }

    pub(crate) fn is_zero(self) -> bool {
        self.limbs == [0; 4]
    }

    pub(crate) fn mul_u128(left: u128, right: u128) -> U256 {
        let l0 = left as u64 as u128;
        let l1 = (left >> 64) as u64 as u128;
        let r0 = right as u64 as u128;
        let r1 = (right >> 64) as u64 as u128;
        let p00 = l0 * r0;
        let p01 = l0 * r1;
        let p10 = l1 * r0;
        let p11 = l1 * r1;
        let mut limbs = [0_u64; 4];
        limbs[0] = p00 as u64;
        let mut carry = (p00 >> 64) + (p01 as u64 as u128) + (p10 as u64 as u128);
        limbs[1] = carry as u64;
        carry = (carry >> 64) + (p01 >> 64) + (p10 >> 64) + (p11 as u64 as u128);
        limbs[2] = carry as u64;
        carry = (carry >> 64) + (p11 >> 64);
        limbs[3] = carry as u64;
        U256 { limbs }
    }

    pub(crate) fn checked_mul_small(self, factor: u128) -> Option<U256> {
        let mut result = U256::ZERO;
        let mut carry: u128 = 0;
        let f0 = factor as u64 as u128;
        let f1 = (factor >> 64) as u64 as u128;
        if f1 != 0 {
            // Full 256x128 multiplication via two shifted 256x64 passes.
            let low = self.checked_mul_small(f0)?;
            let high = self.checked_mul_small(f1)?.checked_shl64()?;
            return low.checked_add(high);
        }
        for index in 0..4 {
            let product = u128::from(self.limbs[index]) * f0 + carry;
            result.limbs[index] = product as u64;
            carry = product >> 64;
        }
        if carry != 0 {
            return None;
        }
        Some(result)
    }

    fn checked_shl64(self) -> Option<U256> {
        if self.limbs[3] != 0 {
            return None;
        }
        Some(U256 {
            limbs: [0, self.limbs[0], self.limbs[1], self.limbs[2]],
        })
    }

    pub(crate) fn checked_add(self, other: U256) -> Option<U256> {
        let mut limbs = [0_u64; 4];
        let mut carry = 0_u128;
        for index in 0..4 {
            let sum = u128::from(self.limbs[index]) + u128::from(other.limbs[index]) + carry;
            limbs[index] = sum as u64;
            carry = sum >> 64;
        }
        if carry != 0 {
            return None;
        }
        Some(U256 { limbs })
    }

    pub(crate) fn checked_sub(self, other: U256) -> Option<U256> {
        if self < other {
            return None;
        }
        let mut limbs = [0_u64; 4];
        let mut borrow = 0_i128;
        for index in 0..4 {
            let diff =
                i128::from(self.limbs[index]) - i128::from(other.limbs[index]) - borrow;
            if diff < 0 {
                limbs[index] = (diff + (1_i128 << 64)) as u64;
                borrow = 1;
            } else {
                limbs[index] = diff as u64;
                borrow = 0;
            }
        }
        Some(U256 { limbs })
    }

    fn bits(self) -> u32 {
        for index in (0..4).rev() {
            if self.limbs[index] != 0 {
                return index as u32 * 64 + (64 - self.limbs[index].leading_zeros());
            }
        }
        0
    }

    fn shl1(self) -> U256 {
        let mut limbs = [0_u64; 4];
        let mut carry = 0_u64;
        for index in 0..4 {
            limbs[index] = (self.limbs[index] << 1) | carry;
            carry = self.limbs[index] >> 63;
        }
        U256 { limbs }
    }

    fn shr1(self) -> U256 {
        let mut limbs = [0_u64; 4];
        let mut carry = 0_u64;
        for index in (0..4).rev() {
            limbs[index] = (self.limbs[index] >> 1) | (carry << 63);
            carry = self.limbs[index] & 1;
        }
        U256 { limbs }
    }

    fn is_even(self) -> bool {
        self.limbs[0] & 1 == 0
    }

    /// Truncating division with remainder by binary long division.
    pub(crate) fn div_rem(self, divisor: U256) -> Option<(U256, U256)> {
        if divisor.is_zero() {
            return None;
        }
        if self < divisor {
            return Some((U256::ZERO, self));
        }
        let shift = self.bits() - divisor.bits();
        let mut shifted = divisor;
        for _ in 0..shift {
            shifted = shifted.shl1();
        }
        let mut remainder = self;
        let mut quotient = U256::ZERO;
        for _ in 0..=shift {
            quotient = quotient.shl1();
            if remainder >= shifted {
                remainder = remainder.checked_sub(shifted)?;
                quotient.limbs[0] |= 1;
            }
            shifted = shifted.shr1();
        }
        Some((quotient, remainder))
    }

    /// Binary greatest common divisor.
    pub(crate) fn gcd(self, other: U256) -> U256 {
        let (mut a, mut b) = (self, other);
        if a.is_zero() {
            return b;
        }
        if b.is_zero() {
            return a;
        }
        let mut shift = 0_u32;
        while a.is_even() && b.is_even() {
            a = a.shr1();
            b = b.shr1();
            shift += 1;
        }
        while a.is_even() {
            a = a.shr1();
        }
        loop {
            while b.is_even() {
                b = b.shr1();
            }
            if a > b {
                core::mem::swap(&mut a, &mut b);
            }
            b = b.checked_sub(a).expect("b >= a after swap");
            if b.is_zero() {
                let mut result = a;
                for _ in 0..shift {
                    result = result.shl1();
                }
                return result;
            }
        }
    }
}

impl Ord for U256 {
    fn cmp(&self, other: &Self) -> core::cmp::Ordering {
        for index in (0..4).rev() {
            match self.limbs[index].cmp(&other.limbs[index]) {
                core::cmp::Ordering::Equal => continue,
                order => return order,
            }
        }
        core::cmp::Ordering::Equal
    }
}

impl PartialOrd for U256 {
    fn partial_cmp(&self, other: &Self) -> Option<core::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

/// Exact signed ratio held as sign + unsigned 256-bit parts.  The value is
/// `sign * numerator / denominator`; construction never normalizes — callers
/// reduce exactly once at the storage boundary, matching the canonical
/// arbitrary-precision result.
#[derive(Clone, Copy, Debug)]
pub(crate) struct SignedRatio256 {
    pub(crate) negative: bool,
    pub(crate) numerator: U256,
    pub(crate) denominator: U256,
}

impl SignedRatio256 {
    pub(crate) fn from_i128_ratio(numerator: i128, denominator: u128) -> SignedRatio256 {
        SignedRatio256 {
            negative: numerator < 0,
            numerator: U256::from_u128(numerator.unsigned_abs()),
            denominator: U256::from_u128(denominator),
        }
    }

    /// Exact sum of two ratios over a shared 256-bit cross denominator.
    pub(crate) fn checked_add(self, other: SignedRatio256) -> Option<SignedRatio256> {
        let denominator = self
            .denominator
            .to_u128()
            .and_then(|left| {
                other
                    .denominator
                    .to_u128()
                    .map(|right| U256::mul_u128(left, right))
            })?;
        let left = self
            .numerator
            .to_u128()
            .and_then(|n| other.denominator.to_u128().map(|d| U256::mul_u128(n, d)))?;
        let right = other
            .numerator
            .to_u128()
            .and_then(|n| self.denominator.to_u128().map(|d| U256::mul_u128(n, d)))?;
        let (negative, numerator) = match (self.negative, other.negative) {
            (a, b) if a == b => (a, left.checked_add(right)?),
            (a, _) => {
                if left >= right {
                    (a, left.checked_sub(right)?)
                } else {
                    (!a, right.checked_sub(left)?)
                }
            }
        };
        Some(SignedRatio256 {
            negative: negative && !numerator.is_zero(),
            numerator,
            denominator,
        })
    }

    /// Truncated-toward-zero whole part and the exact remainder ratio.
    pub(crate) fn trunc_rem(self) -> Option<(i128, SignedRatio256)> {
        let (quotient, remainder) = self.numerator.div_rem(self.denominator)?;
        let whole_magnitude = quotient.to_u128()?;
        let whole = i128::try_from(whole_magnitude).ok()?;
        let whole = if self.negative { whole.checked_neg()? } else { whole };
        Some((
            whole,
            SignedRatio256 {
                negative: self.negative && !remainder.is_zero(),
                numerator: remainder,
                denominator: self.denominator,
            },
        ))
    }

    /// Reduce to canonical `(i128, u128)` parts by one exact gcd.
    pub(crate) fn reduced_parts(self) -> Option<(i128, u128)> {
        if self.numerator.is_zero() {
            return Some((0, 1));
        }
        let divisor = self.numerator.gcd(self.denominator);
        let (numerator, _) = self.numerator.div_rem(divisor)?;
        let (denominator, _) = self.denominator.div_rem(divisor)?;
        let numerator = numerator.to_u128().and_then(|n| i128::try_from(n).ok())?;
        let denominator = denominator.to_u128()?;
        Some((
            if self.negative { numerator.checked_neg()? } else { numerator },
            denominator,
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mul_div_round_trip_is_exact() {
        let a = 340_282_366_920_938_463_463_374_607_431_768_211_455_u128; // u128::MAX
        let b = 981_234_567_890_123_456_789_u128;
        let product = U256::mul_u128(a, b);
        let (quotient, remainder) = product.div_rem(U256::from_u128(b)).unwrap();
        assert_eq!(quotient.to_u128(), Some(a));
        assert!(remainder.is_zero());
    }

    #[test]
    fn gcd_matches_euclid_on_wide_values() {
        let a = U256::mul_u128(2_u128.pow(90) * 3 * 5 * 7, 11 * 13);
        let b = U256::mul_u128(2_u128.pow(70) * 3 * 11, 17);
        let gcd = a.gcd(b);
        assert_eq!(gcd.to_u128(), Some(2_u128.pow(70) * 3 * 11));
    }

    #[test]
    fn signed_ratio_add_and_truncate_matches_manual_arithmetic() {
        // -7/4 + 5/6 = -11/12 -> whole 0, remainder -11/12
        let left = SignedRatio256::from_i128_ratio(-7, 4);
        let right = SignedRatio256::from_i128_ratio(5, 6);
        let sum = left.checked_add(right).unwrap();
        let (whole, remainder) = sum.trunc_rem().unwrap();
        assert_eq!(whole, 0);
        assert_eq!(remainder.reduced_parts(), Some((-11, 12)));
        // 9/4 + 5/6 = 37/12 -> whole 3, remainder 1/12
        let left = SignedRatio256::from_i128_ratio(9, 4);
        let sum = left.checked_add(right).unwrap();
        let (whole, remainder) = sum.trunc_rem().unwrap();
        assert_eq!(whole, 3);
        assert_eq!(remainder.reduced_parts(), Some((1, 12)));
    }
}
