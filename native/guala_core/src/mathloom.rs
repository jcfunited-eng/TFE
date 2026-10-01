//! Exact numerical representation only; this module supplies no neuronal current,
//! energy, plasticity or cognitive authority.
//! Finite binary64 has at most a 1024-bit integer numerator and denominator
//! 2^1074. Eighteen u64 limbs (1152 bits) cover both plus ternary intermediates.
//! The largest required denominator has 679 balanced-ternary digits.
const MAX_BINARY64_TRITS: usize = 679;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct Uint1152 {
    pub limbs: [u64; 18], // 18 * 64 = 1152 bits >= 1075 bits
}

impl Uint1152 {
    pub const ZERO: Self = Self { limbs: [0; 18] };

    pub fn from_u64(val: u64) -> Self {
        let mut limbs = [0u64; 18];
        limbs[0] = val;
        Self { limbs }
    }

    pub fn is_zero(&self) -> bool {
        self.limbs.iter().all(|&l| l == 0)
    }

    pub fn shl(&self, shift: usize) -> Result<Self, String> {
        if shift == 0 {
            return Ok(*self);
        }
        let limb_shift = shift / 64;
        let bit_shift = shift % 64;
        if limb_shift >= 18 {
            return Err("Shift exceeds maximum capacity 1152 bits".to_string());
        }
        let mut new_limbs = [0u64; 18];
        for i in 0..18 {
            if self.limbs[i] == 0 { continue; }
            let target_idx = i + limb_shift;
            if target_idx < 18 {
                new_limbs[target_idx] |= self.limbs[i] << bit_shift;
            } else {
                return Err("Bit overflow shifting Uint1152".to_string());
            }
            if bit_shift > 0 && target_idx + 1 < 18 {
                new_limbs[target_idx + 1] |= self.limbs[i] >> (64 - bit_shift);
            } else if bit_shift > 0 && (self.limbs[i] >> (64 - bit_shift)) != 0 {
                return Err("Bit overflow shifting Uint1152".to_string());
            }
        }
        Ok(Self { limbs: new_limbs })
    }

    pub fn shr(&self, shift: usize) -> Self {
        if shift == 0 {
            return *self;
        }
        let limb_shift = shift / 64;
        let bit_shift = shift % 64;
        if limb_shift >= 18 {
            return Self::ZERO;
        }
        let mut new_limbs = [0u64; 18];
        for i in limb_shift..18 {
            let target_idx = i - limb_shift;
            new_limbs[target_idx] |= self.limbs[i] >> bit_shift;
            if bit_shift > 0 && target_idx > 0 {
                new_limbs[target_idx - 1] |= self.limbs[i] << (64 - bit_shift);
            }
        }
        Self { limbs: new_limbs }
    }

    pub fn div_rem_3(&mut self) -> u8 {
        let mut rem: u128 = 0;
        for limb in self.limbs.iter_mut().rev() {
            let cur = (rem << 64) | (*limb as u128);
            *limb = (cur / 3) as u64;
            rem = cur % 3;
        }
        rem as u8
    }

    pub fn add_u64(&mut self, val: u64) -> Result<(), String> {
        let mut carry = val as u128;
        for limb in self.limbs.iter_mut() {
            let sum = (*limb as u128) + carry;
            *limb = sum as u64;
            carry = sum >> 64;
            if carry == 0 { break; }
        }
        if carry > 0 {
            return Err("Overflow adding to Uint1152".to_string());
        }
        Ok(())
    }

    pub fn mul_3_add(&mut self, digit: u64) -> Result<(), String> {
        let mut carry = digit as u128;
        for limb in self.limbs.iter_mut() {
            let cur = (*limb as u128) * 3 + carry;
            *limb = cur as u64;
            carry = cur >> 64;
        }
        if carry > 0 {
            return Err("Overflow in mul_3_add".to_string());
        }
        Ok(())
    }

    pub fn gte(&self, other: &Self) -> bool {
        for i in (0..18).rev() {
            if self.limbs[i] > other.limbs[i] { return true; }
            if self.limbs[i] < other.limbs[i] { return false; }
        }
        true
    }

    pub fn sub(&self, other: &Self) -> Result<Self, String> {
        let mut res = [0u64; 18];
        let mut borrow: u128 = 0;
        for i in 0..18 {
            let a = self.limbs[i] as u128;
            let b = (other.limbs[i] as u128) + borrow;
            if a >= b {
                res[i] = (a - b) as u64;
                borrow = 0;
            } else {
                res[i] = ((1u128 << 64) + a - b) as u64;
                borrow = 1;
            }
        }
        if borrow > 0 {
            return Err("Negative result in unsigned Uint1152 subtraction".to_string());
        }
        Ok(Self { limbs: res })
    }

    pub fn bit_length(&self) -> u32 {
        for i in (0..18).rev() {
            if self.limbs[i] != 0 {
                return (i as u32 + 1) * 64 - self.limbs[i].leading_zeros();
            }
        }
        0
    }

    pub fn trailing_zeros(&self) -> u32 {
        for i in 0..18 {
            if self.limbs[i] != 0 {
                return (i as u32) * 64 + self.limbs[i].trailing_zeros();
            }
        }
        1152
    }

    pub fn to_balanced_ternary(&self) -> Vec<i8> {
        if self.is_zero() {
            return vec![0];
        }
        let mut copy = *self;
        let mut trits = Vec::new();
        while !copy.is_zero() {
            let rem = copy.div_rem_3();
            if rem == 0 {
                trits.push(0);
            } else if rem == 1 {
                trits.push(1);
            } else {
                trits.push(-1);
                let _ = copy.add_u64(1);
            }
        }
        trits
    }

    pub fn from_balanced_ternary(trits: &[i8]) -> Result<(Self, bool), String> {
        if trits.is_empty() || trits.len() > MAX_BINARY64_TRITS {
            return Err("Balanced-ternary integer has invalid length".to_string());
        }
        if trits.len() > 1 && trits.last() == Some(&0) {
            return Err("Balanced-ternary integer has a leading zero".to_string());
        }
        if trits.iter().any(|&t| !(-1..=1).contains(&t)) {
            return Err("Invalid balanced-ternary digit".to_string());
        }
        let mut p = Self::ZERO;
        let mut m = Self::ZERO;
        for &t in trits.iter().rev() {
            p.mul_3_add(if t == 1 { 1 } else { 0 })?;
            m.mul_3_add(if t == -1 { 1 } else { 0 })?;
        }
        if p.gte(&m) {
            Ok((p.sub(&m)?, false))
        } else {
            Ok((m.sub(&p)?, true))
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct MathLoomRationalField {
    pub sign: i8, // -1 if negative, +1 if non-negative
    pub is_zero: bool,
    pub numerator_trits: Vec<i8>,
    pub denominator_trits: Vec<i8>,
}


    /// Exact MathLoom binary64 bit decomposition into integer numerator and denominator balanced ternary.
    pub fn float_to_rational_trits(val: f64) -> Result<MathLoomRationalField, String> {
        if !val.is_finite() {
            return Err(format!("Cannot convert non-finite float to MathLoom rational field: {}", val));
        }
        let bits = val.to_bits();
        let s = (bits >> 63) as u8;
        let e = ((bits >> 52) & 0x7FF) as u32;
        let f = bits & 0x000F_FFFF_FFFF_FFFF;

        let sign: i8 = if s == 1 { -1 } else { 1 };

        if e == 0 && f == 0 {
            return Ok(MathLoomRationalField {
                sign,
                is_zero: true,
                numerator_trits: vec![0],
                denominator_trits: vec![1],
            });
        }

        let (m, q): (u64, i32) = if e > 0 {
            ((1u64 << 52) | f, (e as i32) - 1075)
        } else {
            (f, -1074)
        };

        let tz = m.trailing_zeros();
        let (num_int, den_int) = if q >= 0 {
            let num = Uint1152::from_u64(m).shl(q as usize)?;
            let den = Uint1152::from_u64(1);
            (num, den)
        } else {
            let shift = (-q) as u32;
            let k = tz.min(shift);
            let num = Uint1152::from_u64(m >> k);
            let den = Uint1152::from_u64(1).shl((shift - k) as usize)?;
            (num, den)
        };

        let mut num_trits = num_int.to_balanced_ternary();
        if s == 1 {
            for t in num_trits.iter_mut() {
                *t = -*t;
            }
        }
        let den_trits = den_int.to_balanced_ternary();

        Ok(MathLoomRationalField {
            sign,
            is_zero: false,
            numerator_trits: num_trits,
            denominator_trits: den_trits,
        })
    }


/// Decode only canonical, exactly representable finite binary64 values.
/// No rounding, precision truncation, metadata override or subnormal wraparound.
pub fn rational_trits_to_float(field: &MathLoomRationalField) -> Result<f64, String> {
    if field.sign != -1 && field.sign != 1 {
        return Err("MathLoom sign must be -1 or +1".to_string());
    }
    let (num, negative) = Uint1152::from_balanced_ternary(&field.numerator_trits)?;
    let (den, den_negative) = Uint1152::from_balanced_ternary(&field.denominator_trits)?;
    if den_negative || den.is_zero() {
        return Err("MathLoom denominator must be positive".to_string());
    }
    let p = den.trailing_zeros();
    if p > 1074 || den != Uint1152::from_u64(1).shl(p as usize)? {
        return Err("MathLoom denominator must be a binary64 power of two".to_string());
    }
    if num.is_zero() {
        if !field.is_zero || den != Uint1152::from_u64(1) {
            return Err("Noncanonical MathLoom zero".to_string());
        }
        return Ok(f64::from_bits(if field.sign == -1 { 1u64 << 63 } else { 0 }));
    }
    if field.is_zero || negative != (field.sign == -1) {
        return Err("MathLoom sign or zero metadata disagrees with numerator".to_string());
    }
    if p > 0 && num.trailing_zeros() > 0 {
        return Err("MathLoom fraction must be reduced".to_string());
    }
    let bl = num.bit_length();
    let exponent = (bl as i32 - 1) - p as i32;
    if !(-1074..=1023).contains(&exponent) {
        return Err("MathLoom value is outside finite binary64 range".to_string());
    }
    let sign_bit = if negative { 1u64 << 63 } else { 0 };
    let bits = if exponent >= -1022 {
        let significand = if bl > 53 {
            let shift = bl - 53;
            if num.trailing_zeros() < shift {
                return Err("MathLoom value is not exactly representable in binary64".to_string());
            }
            num.shr(shift as usize).limbs[0]
        } else {
            num.limbs[0] << (53 - bl)
        };
        sign_bit | (((exponent + 1023) as u64) << 52)
            | (significand & 0x000f_ffff_ffff_ffff)
    } else {
        // p <= 1074 is checked before subtraction; this stays on the
        // subnormal lattice rather than rounding or wrapping an unsigned shift.
        let significand = num.shl((1074 - p) as usize)?.limbs[0];
        sign_bit | significand
    };
    Ok(f64::from_bits(bits))
}

#[cfg(test)]
mod tests {
    use super::*;
    fn rational(n: u64, p: usize) -> MathLoomRationalField {
        MathLoomRationalField {
            sign: 1, is_zero: n == 0,
            numerator_trits: Uint1152::from_u64(n).to_balanced_ternary(),
            denominator_trits: Uint1152::from_u64(1).shl(p).unwrap().to_balanced_ternary(),
        }
    }
    #[test]
    fn every_finite_exponent_and_boundary_mantissa_round_trips() {
        // 2 signs * 2047 finite exponents * 6 mantissas = 24,564 values.
        for sign in [0u64, 1] {
            for e in 0u64..2047 {
                for f in [0, 1, 2, (1u64 << 51) - 1, 1u64 << 51, (1u64 << 52) - 1] {
                    let bits = (sign << 63) | (e << 52) | f;
                    let v = f64::from_bits(bits);
                    let rep = float_to_rational_trits(v).unwrap();
                    assert!(rep.numerator_trits.len() <= MAX_BINARY64_TRITS);
                    assert!(rep.denominator_trits.len() <= MAX_BINARY64_TRITS);
                    assert_eq!(rational_trits_to_float(&rep).unwrap().to_bits(), bits);
                }
            }
        }
    }
    #[test]
    fn signed_zero_and_nonfinite_inputs() {
        for v in [0.0f64, -0.0, f64::from_bits(1), f64::MAX, -f64::MAX] {
            let rep = float_to_rational_trits(v).unwrap();
            assert_eq!(rational_trits_to_float(&rep).unwrap().to_bits(), v.to_bits());
        }
        for v in [f64::INFINITY, f64::NEG_INFINITY, f64::NAN] {
            assert!(float_to_rational_trits(v).is_err());
        }
        assert_eq!(float_to_rational_trits(0.5).unwrap(), rational(1, 1));
    }
    #[test]
    fn malformed_trits_and_metadata_are_not_coerced() {
        let valid = rational(1, 0);
        for digits in [vec![], vec![2], vec![-2], vec![1, 0], vec![0; MAX_BINARY64_TRITS + 1]] {
            let mut rep = valid.clone(); rep.numerator_trits = digits.clone();
            assert!(rational_trits_to_float(&rep).is_err());
            let mut rep = valid.clone(); rep.denominator_trits = digits;
            assert!(rational_trits_to_float(&rep).is_err());
        }
        for sign in [-2, 0, 2] {
            let mut rep = valid.clone(); rep.sign = sign;
            assert!(rational_trits_to_float(&rep).is_err());
        }
        let mut rep = valid.clone(); rep.is_zero = true;
        assert!(rational_trits_to_float(&rep).is_err());
        let mut rep = valid.clone(); rep.sign = -1;
        assert!(rational_trits_to_float(&rep).is_err());
        let mut rep = valid; rep.numerator_trits = vec![-1];
        assert!(rational_trits_to_float(&rep).is_err());
        let mut rep = rational(0, 0); rep.is_zero = false;
        assert!(rational_trits_to_float(&rep).is_err());
    }
    #[test]
    fn denominator_and_exact_precision_are_enforced() {
        for rep in [rational(2, 1), rational(0, 1), rational((1u64 << 53) + 1, 0),
                    rational(3, 1075), rational(1, 1075)] {
            assert!(rational_trits_to_float(&rep).is_err());
        }
        let mut rep = rational(1, 0); rep.denominator_trits = vec![0, 1]; // 3
        assert!(rational_trits_to_float(&rep).is_err());
        rep.denominator_trits = vec![-1];
        assert!(rational_trits_to_float(&rep).is_err());
        rep.denominator_trits = vec![0];
        assert!(rational_trits_to_float(&rep).is_err());
        let mut rep = rational(1, 0);
        rep.numerator_trits = Uint1152::from_u64(1).shl(1024).unwrap().to_balanced_ternary();
        assert!(rational_trits_to_float(&rep).is_err());
    }
    #[test]
    fn old_32_trit_collision_requires_complete_representation() {
        let a = 2.0f64.powi(-52);
        let b = ((2 * 3u64.pow(32) + 1) as f64) * a;
        assert!(0.0 < a && a < b && b < 1.0);
        let ra = float_to_rational_trits(a).unwrap();
        let rb = float_to_rational_trits(b).unwrap();
        assert_ne!(ra, rb);
        let prefix = |r: &MathLoomRationalField| r.numerator_trits.iter().copied()
            .chain(std::iter::repeat(0)).take(32).collect::<Vec<_>>();
        assert_eq!(prefix(&ra), prefix(&rb));
        assert_eq!(ra.denominator_trits, rb.denominator_trits);
        assert_eq!(rational_trits_to_float(&ra).unwrap().to_bits(), a.to_bits());
        assert_eq!(rational_trits_to_float(&rb).unwrap().to_bits(), b.to_bits());
    }
    #[test]
    fn fixed_limb_arithmetic_refuses_overflow() {
        assert!(Uint1152::from_u64(1).shl(1152).is_err());
        let top = Uint1152::from_u64(1).shl(1151).unwrap();
        assert!(top.shl(1).is_err());
        assert_eq!(top.shr(1151), Uint1152::from_u64(1));
        assert!(Uint1152::ZERO.sub(&Uint1152::from_u64(1)).is_err());
        assert_eq!(rational(1, 1074).denominator_trits.len(), MAX_BINARY64_TRITS);
    }
}

