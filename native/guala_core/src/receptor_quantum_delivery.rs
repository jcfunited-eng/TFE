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

use crate::complete_neuron::{GatePopulationOpeningSchedule, GateWorkOccurrence};
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
    schedule: &GatePopulationOpeningSchedule,
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
    let activated = affordable_activation_prefix(schedule, available_quanta)?;
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
            schedule
                .predecessor_open_population()
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

/// Return the longest exact sequential channel prefix whose complete lattice
/// barriers can be paid. The barriers are an exact arithmetic progression;
/// summing their strict-positive floors uses the Euclidean floor-sum law and a
/// logarithmic binary search rather than materializing one rational per
/// channel.
fn affordable_activation_prefix(
    schedule: &GatePopulationOpeningSchedule,
    available_quanta: u128,
) -> Result<u128, ReceptorDeliveryError> {
    let count = schedule.channel_count();
    if count == 0 {
        return Ok(0);
    }
    let first_positive = first_positive_barrier_offset(schedule)?;
    if first_positive == count {
        return Ok(count);
    }
    let payable_count = count - first_positive;
    let available = BigInt::from(available_quanta);
    let mut low = 0_u128;
    let mut high = payable_count;
    while low < high {
        let distance = high - low;
        let middle = low + distance / 2 + distance % 2;
        let cost = positive_barrier_prefix_cost(schedule, first_positive, middle)?;
        if cost <= available {
            low = middle;
        } else {
            high = middle - 1;
        }
    }
    first_positive
        .checked_add(low)
        .ok_or(ReceptorDeliveryError::ResidueWidth)
}

fn barrier_at(
    schedule: &GatePopulationOpeningSchedule,
    offset: u128,
) -> BigRational {
    schedule.first_barrier_quanta()
        + schedule.barrier_step_quanta()
            * BigRational::from_integer(BigInt::from(offset))
}

fn first_positive_barrier_offset(
    schedule: &GatePopulationOpeningSchedule,
) -> Result<u128, ReceptorDeliveryError> {
    let count = schedule.channel_count();
    if schedule.barrier_step_quanta().is_negative() {
        return Err(ReceptorDeliveryError::OpeningWindowUnavailable);
    }
    if schedule.first_barrier_quanta().is_positive() {
        return Ok(0);
    }
    if !barrier_at(schedule, count - 1).is_positive() {
        return Ok(count);
    }
    let mut low = 1_u128;
    let mut high = count - 1;
    while low < high {
        let middle = low + (high - low) / 2;
        if barrier_at(schedule, middle).is_positive() {
            high = middle;
        } else {
            low = middle + 1;
        }
    }
    Ok(low)
}

fn positive_barrier_prefix_cost(
    schedule: &GatePopulationOpeningSchedule,
    first_positive: u128,
    count: u128,
) -> Result<BigInt, ReceptorDeliveryError> {
    if count == 0 {
        return Ok(BigInt::zero());
    }
    let first = barrier_at(schedule, first_positive);
    let step = schedule.barrier_step_quanta();
    if !first.is_positive() || step.is_negative() {
        return Err(ReceptorDeliveryError::OpeningWindowUnavailable);
    }
    // A common denominator need not be reduced: exact floor-sum sees the same
    // rational progression and avoids introducing another approximation.
    let modulus = first.denom() * step.denom();
    let slope = step.numer() * first.denom();
    let intercept = first.numer() * step.denom();
    let floors = floor_sum_nonnegative(count, modulus, slope, intercept)?;
    Ok(floors + BigInt::from(count))
}

/// Exact sum `sum_{i=0}^{n-1} floor((a*i+b)/m)` for non-negative integers.
/// Euclidean reduction makes runtime logarithmic in the integer widths.
fn floor_sum_nonnegative(
    count: u128,
    mut modulus: BigInt,
    mut slope: BigInt,
    mut intercept: BigInt,
) -> Result<BigInt, ReceptorDeliveryError> {
    if modulus <= BigInt::zero() || slope.is_negative() || intercept.is_negative() {
        return Err(ReceptorDeliveryError::OpeningWindowUnavailable);
    }
    let mut count = BigInt::from(count);
    let mut answer = BigInt::zero();
    loop {
        if slope >= modulus {
            let quotient = &slope / &modulus;
            answer += (&count * (&count - 1_u8) * quotient) / 2_u8;
            slope %= &modulus;
        }
        if intercept >= modulus {
            answer += &count * (&intercept / &modulus);
            intercept %= &modulus;
        }
        let upper = &slope * &count + &intercept;
        if upper < modulus {
            break;
        }
        count = &upper / &modulus;
        intercept = upper % &modulus;
        core::mem::swap(&mut modulus, &mut slope);
    }
    Ok(answer)
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
        let schedule = GatePopulationOpeningSchedule::from_progression(
            0,
            4,
            BigRational::from_integer(BigInt::from(17)),
            BigRational::zero(),
        )
        .unwrap();
        let delivery = quantize_population_receptor_delivery(
            &energy,
            rational(0, 1),
            &quantum,
            &schedule,
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
        let schedule = GatePopulationOpeningSchedule::from_progression(
            2,
            2,
            BigRational::from_integer(BigInt::from(17)),
            BigRational::zero(),
        )
        .unwrap();
        let delivery = quantize_population_receptor_delivery(
            &energy,
            predecessor,
            &quantum,
            &schedule,
        )
        .unwrap();
        assert_eq!(delivery.delivered_quanta, 0);
        assert!(delivery.gate_work.is_zero());
        assert_eq!(delivery.successor_residue, rational(1, 1));
        assert_eq!(
            exact_rational_to_big(delivery.successor_residue),
            exact_rational_to_big(predecessor) + energy,
        );
    }

    #[test]
    fn compact_progression_matches_explicit_strict_barriers_at_large_population() {
        let count = 4_563_410_u128;
        let schedule = GatePopulationOpeningSchedule::from_progression(
            0,
            count,
            BigRational::new(BigInt::from(-7), BigInt::from(3)),
            BigRational::new(BigInt::from(2), BigInt::from(3)),
        )
        .unwrap();
        assert_eq!(affordable_activation_prefix(&schedule, 0).unwrap(), 4);
        assert_eq!(affordable_activation_prefix(&schedule, 1).unwrap(), 5);
        assert!(affordable_activation_prefix(&schedule, u128::MAX).unwrap() <= count);
    }

    #[test]
    fn compact_progression_is_exactly_equivalent_to_explicit_channel_walk() {
        let laws = [
            (rational(17, 1), rational(0, 1)),
            (rational(1, 3), rational(2, 3)),
            (rational(-7, 3), rational(2, 3)),
            (rational(0, 1), rational(1, 4)),
        ];
        for (first, step) in laws {
            let first = exact_rational_to_big(first);
            let step = exact_rational_to_big(step);
            let schedule = GatePopulationOpeningSchedule::from_progression(
                0,
                257,
                first.clone(),
                step.clone(),
            )
            .unwrap();
            for available in 0..=1_024_u128 {
                let mut explicit_cost = 0_u128;
                let mut explicit_count = 0_u128;
                for offset in 0..257_u128 {
                    let barrier = &first
                        + &step * BigRational::from_integer(BigInt::from(offset));
                    let required = if barrier.is_positive() {
                        barrier.floor().to_integer().to_u128().unwrap() + 1
                    } else {
                        0
                    };
                    if explicit_cost + required > available {
                        break;
                    }
                    explicit_cost += required;
                    explicit_count += 1;
                }
                assert_eq!(
                    affordable_activation_prefix(&schedule, available).unwrap(),
                    explicit_count,
                    "first={first} step={step} available={available}"
                );
            }
        }
    }
}
