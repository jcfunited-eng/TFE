//! The modality-blind receptor delivery law (ratified 2026-08-05).
//!
//! One transduced energy, one per-site exact-rational accumulator, whole
//! quanta on the RECEIVING GATE's own dissipation lattice, delivered only once
//! the accumulation reaches that gate's own opening threshold and capped at
//! that gate's own window.  The law knows nothing about which sense delivered
//! the energy: it takes an energy, a retained residue, a lattice step, a
//! threshold, and a cap.  It was authored for light and is reused VERBATIM for
//! sound (auditory transduction design 2026-08-06, Law A4) — the body below is
//! the same code that shipped under `quantize_optical_delivery`, moved here
//! unchanged so that no second delivery mechanism exists anywhere.
//!
//! Delivered energy plus retained residue equals the exact transduced integral
//! over any interval sequence: no rounding loss, no tuned coefficients, no
//! decay term.  A quiescent interval (dark, or silent) adds nothing, delivers
//! nothing, and erases nothing.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{Signed, ToPrimitive, Zero};

use crate::complete_neuron::GateWorkOccurrence;
use crate::exact_rational::ExactRational;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ReceptorDeliveryError {
    /// The transduced energy handed to the law was negative.  Both mounted
    /// receptor laws forbid this at their own boundary (irradiance cannot be
    /// negative; a squared pressure cannot be negative), so reaching this is a
    /// caller defect, never a stimulus.
    TransducedEnergyNegative,
    LatticeQuantumUnavailable,
    ResidueOutsideLattice,
    ResidueWidth,
    OpeningWindowUnavailable,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct QuantizedReceptorDelivery {
    pub(crate) delivered_quanta: u128,
    pub(crate) delivered_energy_zeptojoules: BigRational,
    pub(crate) successor_residue: ExactRational,
    pub(crate) gate_work: GateWorkOccurrence,
}

pub(crate) fn exact_rational_to_big(value: ExactRational) -> BigRational {
    let (numerator, denominator) = value.parts();
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

pub(crate) fn big_to_exact_rational(
    value: &BigRational,
) -> Result<ExactRational, ReceptorDeliveryError> {
    let numerator = value
        .numer()
        .to_i128()
        .ok_or(ReceptorDeliveryError::ResidueWidth)?;
    let denominator = value
        .denom()
        .to_u128()
        .ok_or(ReceptorDeliveryError::ResidueWidth)?;
    ExactRational::new(numerator, denominator).map_err(|_| ReceptorDeliveryError::ResidueWidth)
}

/// Integrate one interval's exact transduced energy into the per-site
/// accumulator and deliver whole lattice quanta only once the accumulated
/// count reaches the receiving gate's opening threshold.  The predecessor
/// residue must be non-negative; the successor residue always is.
pub(crate) fn quantize_receptor_delivery(
    transduced_energy_zeptojoules: &BigRational,
    predecessor_residue: ExactRational,
    lattice_quantum_zeptojoules: &BigRational,
    opening_threshold_quanta: u128,
    window_cap_quanta: u128,
) -> Result<QuantizedReceptorDelivery, ReceptorDeliveryError> {
    if lattice_quantum_zeptojoules <= &BigRational::zero() {
        return Err(ReceptorDeliveryError::LatticeQuantumUnavailable);
    }
    if opening_threshold_quanta == 0 {
        return Err(ReceptorDeliveryError::OpeningWindowUnavailable);
    }
    if transduced_energy_zeptojoules.is_negative() {
        return Err(ReceptorDeliveryError::TransducedEnergyNegative);
    }
    let residue = exact_rational_to_big(predecessor_residue);
    if residue.is_negative() {
        return Err(ReceptorDeliveryError::ResidueOutsideLattice);
    }
    let accumulated = residue + transduced_energy_zeptojoules;
    let accumulated_quanta = (&accumulated / lattice_quantum_zeptojoules)
        .floor()
        .to_integer()
        .to_u128()
        .ok_or(ReceptorDeliveryError::ResidueWidth)?;
    // Threshold-integrated delivery: below the receiving gate's own opening
    // threshold NOTHING is delivered and everything is retained; at or above
    // it, at most the gate's own window cap is passed.
    let delivered_quanta = if accumulated_quanta < opening_threshold_quanta {
        0
    } else {
        accumulated_quanta.min(window_cap_quanta)
    };
    let delivered_energy_zeptojoules =
        lattice_quantum_zeptojoules * BigRational::from_integer(BigInt::from(delivered_quanta));
    let successor_residue_big = accumulated - &delivered_energy_zeptojoules;
    debug_assert!(!successor_residue_big.is_negative());
    let successor_residue = big_to_exact_rational(&successor_residue_big)?;
    Ok(QuantizedReceptorDelivery {
        delivered_quanta,
        gate_work: GateWorkOccurrence::new(-delivered_energy_zeptojoules.clone()),
        delivered_energy_zeptojoules,
        successor_residue,
    })
}

/// Pay the current receptor occurrence across the finite ordered channel
/// population.  Complete activation barriers determine how many channels can
/// open.  Once at least one barrier is paid, every whole lattice quantum from
/// this occurrence enters the same settlement exactly once; surplus becomes
/// dissipation there instead of being carried into later presentations.  A
/// genuinely sub-threshold occurrence is retained intact, and a sub-quantum
/// remainder is always retained exactly.
pub(crate) fn quantize_population_receptor_delivery(
    transduced_energy_zeptojoules: &BigRational,
    predecessor_residue: ExactRational,
    lattice_quantum_zeptojoules: &BigRational,
    predecessor_open_population: u128,
    activation_quanta: &[u128],
) -> Result<QuantizedReceptorDelivery, ReceptorDeliveryError> {
    if lattice_quantum_zeptojoules <= &BigRational::zero() {
        return Err(ReceptorDeliveryError::LatticeQuantumUnavailable);
    }
    if transduced_energy_zeptojoules.is_negative() {
        return Err(ReceptorDeliveryError::TransducedEnergyNegative);
    }
    let residue = exact_rational_to_big(predecessor_residue);
    if residue.is_negative() {
        return Err(ReceptorDeliveryError::ResidueOutsideLattice);
    }
    let accumulated = residue + transduced_energy_zeptojoules;
    let available_quanta = (&accumulated / lattice_quantum_zeptojoules)
        .floor()
        .to_integer()
        .to_u128()
        .ok_or(ReceptorDeliveryError::ResidueWidth)?;
    let mut barrier_quanta = 0_u128;
    let mut activated = 0_u128;
    for required in activation_quanta {
        let next_barrier = barrier_quanta
            .checked_add(*required)
            .ok_or(ReceptorDeliveryError::ResidueWidth)?;
        if next_barrier > available_quanta {
            break;
        }
        barrier_quanta = next_barrier;
        activated = activated
            .checked_add(1)
            .ok_or(ReceptorDeliveryError::ResidueWidth)?;
    }
    let consumed_quanta = if activated == 0 { 0 } else { available_quanta };
    let delivered_energy_zeptojoules =
        lattice_quantum_zeptojoules * BigRational::from_integer(BigInt::from(consumed_quanta));
    let successor_residue_big = &accumulated - &delivered_energy_zeptojoules;
    let successor_residue = big_to_exact_rational(&successor_residue_big)?;
    let gate_work = if activated == 0 {
        GateWorkOccurrence::new(BigRational::zero())
    } else {
        GateWorkOccurrence::receptor_activation(
            -delivered_energy_zeptojoules.clone(),
            predecessor_open_population
                .checked_add(activated)
                .ok_or(ReceptorDeliveryError::ResidueWidth)?,
        )
        .map_err(|_| ReceptorDeliveryError::OpeningWindowUnavailable)?
    };
    Ok(QuantizedReceptorDelivery {
        delivered_quanta: consumed_quanta,
        delivered_energy_zeptojoules,
        successor_residue,
        gate_work,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rational(numerator: i128, denominator: u128) -> ExactRational {
        ExactRational::new(numerator, denominator).unwrap()
    }

    #[test]
    fn population_delivery_pays_barriers_then_delivers_the_occurrence_once() {
        let quantum = BigRational::new(BigInt::from(1), BigInt::from(16));
        let energy = &quantum * BigRational::from_integer(BigInt::from(35));
        let delivery = quantize_population_receptor_delivery(
            &energy,
            rational(0, 1),
            &quantum,
            0,
            &[17, 17, 17, 17],
        )
        .unwrap();
        assert_eq!(delivery.delivered_quanta, 35);
        assert_eq!(
            delivery.delivered_energy_zeptojoules,
            &quantum * BigRational::from_integer(BigInt::from(35))
        );
        assert_eq!(delivery.successor_residue, rational(0, 1));
        assert!(!delivery.gate_work.is_zero());
        assert_eq!(
            delivery.delivered_energy_zeptojoules
                + exact_rational_to_big(delivery.successor_residue),
            energy
        );
    }

    #[test]
    fn population_delivery_retains_a_genuinely_subthreshold_occurrence() {
        let quantum = BigRational::new(BigInt::from(1), BigInt::from(16));
        let predecessor = rational(3, 16);
        let energy = &quantum * BigRational::from_integer(BigInt::from(13));
        let delivery =
            quantize_population_receptor_delivery(&energy, predecessor, &quantum, 2, &[17, 17])
                .unwrap();
        assert_eq!(delivery.delivered_quanta, 0);
        assert!(delivery.gate_work.is_zero());
        assert_eq!(delivery.successor_residue, rational(1, 1));
        assert_eq!(
            exact_rational_to_big(delivery.successor_residue),
            exact_rational_to_big(predecessor) + energy,
        );
    }
}
