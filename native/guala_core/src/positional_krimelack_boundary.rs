//! Explicit retirement of the reduced D1-sign-to-Krimelack boundary.
//!
//! A DSF delivery impression contains only sign/null observations. It loses
//! exact rational magnitude, denominator, typed field identity, MathLoom
//! balanced-ternary positions, and physical oscillator state. It therefore
//! cannot constitute Psi/Krimelack or any neuronal transition.
//!
//! The only admissible future boundary is complete unchanged DSF delivery
//! through exact typed MathLoom constraints into mounted dissipative
//! Psi/Krimelack physics.

use std::fmt;

pub(crate) const REDUCED_DSF_TO_KRIMELACK_UNAVAILABLE: &str =
    "reduced DSF delivery impressions cannot constitute Psi/Krimelack";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ReducedDsfToKrimelackUnavailable;

impl fmt::Display for ReducedDsfToKrimelackUnavailable {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        output.write_str(REDUCED_DSF_TO_KRIMELACK_UNAVAILABLE)
    }
}

impl std::error::Error for ReducedDsfToKrimelackUnavailable {}

pub(crate) fn refuse_reduced_dsf_to_krimelack() -> Result<(), ReducedDsfToKrimelackUnavailable> {
    Err(ReducedDsfToKrimelackUnavailable)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sign_compressed_delivery_cannot_become_krimelack() {
        assert_eq!(
            refuse_reduced_dsf_to_krimelack().unwrap_err().to_string(),
            REDUCED_DSF_TO_KRIMELACK_UNAVAILABLE
        );
    }
}
