//! Exact custody of an admitted finite binary64 charge, not a current solver.
//!
//! e = 801088317 / (2^27 * 5^28) C exactly (SI).
//! Every binary64 J and z in {-1,1,2} therefore has J/(z e) on the
//! common integer lattice 1/D, D = 801088317 * 2^1048.
//! A remainder needs 1078 bits; 1152 bits also cover every admitted u64
//! whole-carrier transfer (1078 + 64 < 1152). Storage never grows with time.
//! Oversized transfers refuse before division or reservoir mutation.

use crate::mathloom::Uint1152;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Remainder {
    pub negative: bool,
    pub magnitude: Uint1152,
}

fn denominator() -> Uint1152 {
    // Compile-time-derived representation fits 1078 bits.
    let mut limbs = [0; 18];
    limbs[16] = 801088317u64 << 24;
    Uint1152 { limbs }
}

fn add(a: Uint1152, b: Uint1152) -> Result<Uint1152, String> {
    let mut out = Uint1152::ZERO;
    let mut carry = 0u128;
    for i in 0..18 {
        let sum = a.limbs[i] as u128 + b.limbs[i] as u128 + carry;
        out.limbs[i] = sum as u64;
        carry = sum >> 64;
    }
    if carry != 0 { return Err("Exact carrier lattice overflow".into()); }
    Ok(out)
}

fn mul_small(a: Uint1152, b: u64) -> Result<Uint1152, String> {
    let mut out = Uint1152::ZERO;
    let mut carry = 0u128;
    for i in 0..18 {
        let value = a.limbs[i] as u128 * b as u128 + carry;
        out.limbs[i] = value as u64;
        carry = value >> 64;
    }
    if carry != 0 { return Err("Exact carrier product overflow".into()); }
    Ok(out)
}

impl Remainder {
    pub const ZERO: Self = Self { negative: false, magnitude: Uint1152::ZERO };

    pub fn validate(&self) -> Result<(), String> {
        if self.magnitude.gte(&denominator()) {
            return Err("Carrier remainder must have magnitude less than one".into());
        }
        if self.negative && self.magnitude.is_zero() {
            return Err("Noncanonical negative-zero carrier remainder".into());
        }
        Ok(())
    }

    /// Return signed whole carriers and exact successor remainder. Does not
    /// change either endpoint. Callers stage all transfers before committing.
    pub fn prepare(&self, charge_c: f64, valence: i8) -> Result<(i128, Self), String> {
        self.validate()?;
        if !charge_c.is_finite() || !matches!(valence, -1 | 1 | 2) {
            return Err("Invalid finite charge or carrier valence".into());
        }
        let bits = charge_c.to_bits();
        let exponent = ((bits >> 52) & 0x7ff) as i32;
        let fraction = bits & ((1u64 << 52) - 1);
        let (mantissa, power) = if exponent == 0 {
            (fraction, -1074)
        } else {
            (fraction | (1u64 << 52), exponent - 1075)
        };
        if mantissa == 0 { return Ok((0, *self)); }

        // (J/e)*D = mantissa * 5^28 * 2^(power+1075).
        // For divalent carriers the exponent decreases by one.
        let shift = (power + 1075 - i32::from(valence == 2)) as usize;
        let mut incoming = Uint1152::from_u64(mantissa);
        for _ in 0..28 { incoming = mul_small(incoming, 5)?; }
        incoming = incoming.shl(shift)?;
        let incoming_negative = ((bits >> 63) != 0) ^ (valence < 0);

        let (mut magnitude, negative) = if incoming_negative == self.negative {
            (add(incoming, self.magnitude)?, incoming_negative)
        } else if incoming.gte(&self.magnitude) {
            (incoming.sub(&self.magnitude)?, incoming_negative)
        } else {
            (self.magnitude.sub(&incoming)?, self.negative)
        };

        let divisor = denominator();
        // A u64 transfer is the largest any finite reservoir can admit.
        let beyond_u64 = divisor.shl(64)?;
        if magnitude.gte(&beyond_u64) {
            return Err("Whole-carrier transfer exceeds reservoir representation".into());
        }
        let mut whole = 0u64;
        for bit in (0..64).rev() {
            let candidate = divisor.shl(bit)?;
            if magnitude.gte(&candidate) {
                magnitude = magnitude.sub(&candidate)?;
                whole |= 1u64 << bit;
            }
        }
        let next = Self { negative: negative && !magnitude.is_zero(), magnitude };
        let signed = if negative { -(whole as i128) } else { whole as i128 };
        Ok((signed, next))
    }

    pub fn encode(&self, out: &mut Vec<u8>) {
        out.push(u8::from(self.negative));
        for limb in self.magnitude.limbs { out.extend_from_slice(&limb.to_be_bytes()); }
    }

    pub fn decode(bytes: &[u8]) -> Result<Self, String> {
        if bytes.len() != 145 || bytes[0] > 1 {
            return Err("Invalid exact remainder framing".into());
        }
        let mut magnitude = Uint1152::ZERO;
        for i in 0..18 {
            let start = 1 + 8*i;
            magnitude.limbs[i] = u64::from_be_bytes(bytes[start..start+8].try_into().unwrap());
        }
        let result = Self { negative: bytes[0] == 1, magnitude };
        result.validate()?;
        Ok(result)
    }

    /// Exact numerator / common denominator, for independent falsification.
    pub fn evidence(&self) -> (bool, Vec<u64>, Vec<u64>) {
        (self.negative, self.magnitude.limbs.to_vec(), denominator().limbs.to_vec())
    }
}

pub(crate) fn transfer(source: &mut u64, dest: &mut u64, count: i128) -> Result<(), String> {
    let amount = u64::try_from(count.unsigned_abs())
        .map_err(|_| "Carrier count exceeds u64".to_string())?;
    let (new_source, new_dest) = if count >= 0 {
        (source.checked_sub(amount), dest.checked_add(amount))
    } else {
        (source.checked_add(amount), dest.checked_sub(amount))
    };
    match (new_source, new_dest) {
        (Some(a), Some(b)) => { *source = a; *dest = b; Ok(()) }
        _ => Err("Carrier reservoir depleted or overflowed".into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_reversal_including_subnormal_and_divalent() {
        for z in [-1, 1, 2] {
            for j in [f64::from_bits(1), 1e-23, 1e-19, 1e-13, -1e-13] {
                let (n, r) = Remainder::ZERO.prepare(j, z).unwrap();
                let (back, restored) = r.prepare(-j, z).unwrap();
                assert_eq!(n + back, 0);
                assert_eq!(restored, Remainder::ZERO);
                let mut bytes = Vec::new();
                r.encode(&mut bytes);
                assert_eq!(Remainder::decode(&bytes).unwrap(), r);
            }
        }
    }

    #[test]
    fn splitting_exactly_representable_charge_preserves_total() {
        for z in [-1, 1, 2] {
            let (whole, r) = Remainder::ZERO.prepare(1e-13, z).unwrap();
            let (a, ra) = Remainder::ZERO.prepare(1e-13 / 2.0, z).unwrap();
            let (b, rb) = ra.prepare(1e-13 / 2.0, z).unwrap();
            assert_eq!(whole, a+b);
            assert_eq!(r, rb);
        }
    }

    #[test]
    fn bounds_and_transfer_refusals_are_atomic() {
        for charge in [f64::NAN, f64::INFINITY, f64::MAX, -f64::MAX] {
            assert!(Remainder::ZERO.prepare(charge, 1).is_err());
        }
        let (mut a, mut b) = (3, u64::MAX);
        assert!(transfer(&mut a, &mut b, 1).is_err());
        assert_eq!((a,b), (3,u64::MAX));
        assert!(transfer(&mut a, &mut b, -1).is_ok());
        assert_eq!((a,b), (4,u64::MAX-1));
    }
}
