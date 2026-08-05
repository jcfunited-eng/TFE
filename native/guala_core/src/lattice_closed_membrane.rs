//! Fixed-residency exact membrane charge on an admitted physical lattice.
//!
//! Immutable rational scales are admitted once. Resident charge is a signed
//! count of the admitted charge quantum. A rational outward charge transfer
//! becomes an event only when it is exactly lattice-aligned and its successor
//! remains inside the declared finite physical domain. Consuming that event is
//! pure and infallible. This isolated primitive derives no channel kinetics,
//! receptor gating, recovery, Krimelack state, cognition, or persistence.

use core::num::NonZeroU128;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum MembraneAdmissionError {
    ZeroScale,
    NonCanonicalScale,
    ArithmeticWidth,
    InvalidChargeDomain,
    ChargeOutsideDomain,
    NonLatticeChargeTransfer,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct PositiveRatio {
    numerator: NonZeroU128,
    denominator: NonZeroU128,
}

impl PositiveRatio {
    fn new(numerator: u128, denominator: u128) -> Result<Self, MembraneAdmissionError> {
        let numerator = NonZeroU128::new(numerator).ok_or(MembraneAdmissionError::ZeroScale)?;
        let denominator = NonZeroU128::new(denominator).ok_or(MembraneAdmissionError::ZeroScale)?;
        if gcd(numerator.get(), denominator.get()) != 1 {
            return Err(MembraneAdmissionError::NonCanonicalScale);
        }
        Ok(Self {
            numerator,
            denominator,
        })
    }

    fn multiply(self, other: Self) -> Result<Self, MembraneAdmissionError> {
        let left_cross = gcd(self.numerator.get(), other.denominator.get());
        let right_cross = gcd(other.numerator.get(), self.denominator.get());
        let numerator = (self.numerator.get() / left_cross)
            .checked_mul(other.numerator.get() / right_cross)
            .ok_or(MembraneAdmissionError::ArithmeticWidth)?;
        let denominator = (self.denominator.get() / right_cross)
            .checked_mul(other.denominator.get() / left_cross)
            .ok_or(MembraneAdmissionError::ArithmeticWidth)?;
        Self::new(numerator, denominator)
    }

    fn divide(self, divisor: Self) -> Result<Self, MembraneAdmissionError> {
        let numerator_cross = gcd(self.numerator.get(), divisor.numerator.get());
        let denominator_cross = gcd(divisor.denominator.get(), self.denominator.get());
        let numerator = (self.numerator.get() / numerator_cross)
            .checked_mul(divisor.denominator.get() / denominator_cross)
            .ok_or(MembraneAdmissionError::ArithmeticWidth)?;
        let denominator = (self.denominator.get() / denominator_cross)
            .checked_mul(divisor.numerator.get() / numerator_cross)
            .ok_or(MembraneAdmissionError::ArithmeticWidth)?;
        Self::new(numerator, denominator)
    }

    fn parts(self) -> (u128, u128) {
        (self.numerator.get(), self.denominator.get())
    }
}

macro_rules! positive_scale {
    ($name:ident) => {
        #[derive(Clone, Copy, Debug, Eq, PartialEq)]
        pub(crate) struct $name(PositiveRatio);

        impl $name {
            pub(crate) fn new(
                numerator: u128,
                denominator: u128,
            ) -> Result<Self, MembraneAdmissionError> {
                PositiveRatio::new(numerator, denominator).map(Self)
            }

            pub(crate) fn parts(self) -> (u128, u128) {
                self.0.parts()
            }
        }
    };
}

positive_scale!(SurfaceAreaScale);
positive_scale!(SpecificCapacitanceScale);
positive_scale!(ChargeQuantum);
positive_scale!(TimeQuantum);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExactSignedCharge {
    negative: bool,
    magnitude: u128,
    denominator: NonZeroU128,
}

impl ExactSignedCharge {
    pub(crate) fn new(numerator: i128, denominator: u128) -> Result<Self, MembraneAdmissionError> {
        let denominator = NonZeroU128::new(denominator).ok_or(MembraneAdmissionError::ZeroScale)?;
        let magnitude = numerator.unsigned_abs();
        if magnitude == 0 {
            if denominator.get() != 1 {
                return Err(MembraneAdmissionError::NonCanonicalScale);
            }
            return Ok(Self {
                negative: false,
                magnitude: 0,
                denominator,
            });
        }
        if gcd(magnitude, denominator.get()) != 1 {
            return Err(MembraneAdmissionError::NonCanonicalScale);
        }
        Ok(Self {
            negative: numerator.is_negative(),
            magnitude,
            denominator,
        })
    }

    fn positive_ratio(self) -> Option<PositiveRatio> {
        NonZeroU128::new(self.magnitude).map(|numerator| PositiveRatio {
            numerator,
            denominator: self.denominator,
        })
    }

    pub(crate) fn parts(self) -> (bool, u128, u128) {
        (self.negative, self.magnitude, self.denominator.get())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExactPotential {
    negative: bool,
    magnitude: u128,
    denominator: NonZeroU128,
}

impl ExactPotential {
    pub(crate) fn parts(self) -> (bool, u128, u128) {
        (self.negative, self.magnitude, self.denominator.get())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct FiniteChargeDomain {
    minimum_quanta: i128,
    maximum_quanta: i128,
}

impl FiniteChargeDomain {
    pub(crate) fn new(
        minimum_quanta: i128,
        maximum_quanta: i128,
    ) -> Result<Self, MembraneAdmissionError> {
        if minimum_quanta > maximum_quanta {
            return Err(MembraneAdmissionError::InvalidChargeDomain);
        }
        Ok(Self {
            minimum_quanta,
            maximum_quanta,
        })
    }

    pub(crate) fn bounds(self) -> (i128, i128) {
        (self.minimum_quanta, self.maximum_quanta)
    }

    fn contains(self, charge_quanta: i128) -> bool {
        self.minimum_quanta <= charge_quanta && charge_quanta <= self.maximum_quanta
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MembraneAnatomy {
    surface_area: SurfaceAreaScale,
    specific_capacitance: SpecificCapacitanceScale,
    charge_quantum: ChargeQuantum,
    time_quantum: TimeQuantum,
    capacitance: PositiveRatio,
    current_quantum: PositiveRatio,
    potential_per_charge_quantum: PositiveRatio,
    charge_domain: FiniteChargeDomain,
}

impl MembraneAnatomy {
    pub(crate) fn admit(
        surface_area: SurfaceAreaScale,
        specific_capacitance: SpecificCapacitanceScale,
        charge_quantum: ChargeQuantum,
        time_quantum: TimeQuantum,
        charge_domain: FiniteChargeDomain,
    ) -> Result<Self, MembraneAdmissionError> {
        let capacitance = surface_area.0.multiply(specific_capacitance.0)?;
        let current_quantum = charge_quantum.0.divide(time_quantum.0)?;
        let potential_per_charge_quantum = charge_quantum.0.divide(capacitance)?;
        prove_domain_potential_width(charge_domain, potential_per_charge_quantum)?;
        Ok(Self {
            surface_area,
            specific_capacitance,
            charge_quantum,
            time_quantum,
            capacitance,
            current_quantum,
            potential_per_charge_quantum,
            charge_domain,
        })
    }

    pub(crate) fn surface_area(self) -> SurfaceAreaScale {
        self.surface_area
    }

    pub(crate) fn specific_capacitance(self) -> SpecificCapacitanceScale {
        self.specific_capacitance
    }

    pub(crate) fn charge_quantum(self) -> ChargeQuantum {
        self.charge_quantum
    }

    pub(crate) fn time_quantum(self) -> TimeQuantum {
        self.time_quantum
    }

    pub(crate) fn capacitance(self) -> (u128, u128) {
        self.capacitance.parts()
    }

    pub(crate) fn current_quantum(self) -> (u128, u128) {
        self.current_quantum.parts()
    }

    pub(crate) fn charge_domain(self) -> FiniteChargeDomain {
        self.charge_domain
    }

    pub(crate) fn genesis(
        self,
        charge_quanta: i128,
    ) -> Result<MembraneState, MembraneAdmissionError> {
        if !self.charge_domain.contains(charge_quanta) {
            return Err(MembraneAdmissionError::ChargeOutsideDomain);
        }
        Ok(MembraneState {
            anatomy: self,
            charge_quanta,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MembraneState {
    anatomy: MembraneAnatomy,
    charge_quanta: i128,
}

impl MembraneState {
    pub(crate) fn anatomy(self) -> MembraneAnatomy {
        self.anatomy
    }

    pub(crate) fn charge_quanta(self) -> i128 {
        self.charge_quanta
    }

    pub(crate) fn potential(self) -> ExactPotential {
        let scale = self.anatomy.potential_per_charge_quantum;
        let divisor = gcd(self.charge_quanta.unsigned_abs(), scale.denominator.get());
        let magnitude = (self.charge_quanta.unsigned_abs() / divisor) * scale.numerator.get();
        let denominator = NonZeroU128::new(scale.denominator.get() / divisor)
            .expect("positive admitted potential denominator");
        ExactPotential {
            negative: self.charge_quanta.is_negative(),
            magnitude,
            denominator,
        }
    }

    pub(crate) fn admit_outward_charge(
        self,
        transfer: ExactSignedCharge,
    ) -> Result<AdmittedMembraneEvent, MembraneAdmissionError> {
        let outward_charge_quanta = match transfer.positive_ratio() {
            None => 0,
            Some(transfer_ratio) => {
                let lattice_count = transfer_ratio.divide(self.anatomy.charge_quantum.0)?;
                if lattice_count.denominator.get() != 1 {
                    return Err(MembraneAdmissionError::NonLatticeChargeTransfer);
                }
                signed_from_magnitude(transfer.negative, lattice_count.numerator.get())?
            }
        };
        let successor_charge = self
            .charge_quanta
            .checked_sub(outward_charge_quanta)
            .ok_or(MembraneAdmissionError::ArithmeticWidth)?;
        if !self.anatomy.charge_domain.contains(successor_charge) {
            return Err(MembraneAdmissionError::ChargeOutsideDomain);
        }
        let successor = Self {
            anatomy: self.anatomy,
            charge_quanta: successor_charge,
        };
        Ok(AdmittedMembraneEvent {
            predecessor: self,
            successor,
            outward_charge_quanta,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct AdmittedMembraneEvent {
    predecessor: MembraneState,
    successor: MembraneState,
    outward_charge_quanta: i128,
}

impl AdmittedMembraneEvent {
    pub(crate) fn predecessor(self) -> MembraneState {
        self.predecessor
    }

    pub(crate) fn successor(self) -> MembraneState {
        self.successor
    }

    pub(crate) fn outward_charge_quanta(self) -> i128 {
        self.outward_charge_quanta
    }
}

pub(crate) fn transition_membrane(event: AdmittedMembraneEvent) -> MembraneState {
    event.successor
}

fn prove_domain_potential_width(
    domain: FiniteChargeDomain,
    potential_scale: PositiveRatio,
) -> Result<(), MembraneAdmissionError> {
    for charge in [domain.minimum_quanta, domain.maximum_quanta] {
        let divisor = gcd(charge.unsigned_abs(), potential_scale.denominator.get());
        (charge.unsigned_abs() / divisor)
            .checked_mul(potential_scale.numerator.get())
            .ok_or(MembraneAdmissionError::ArithmeticWidth)?;
    }
    Ok(())
}

fn signed_from_magnitude(negative: bool, magnitude: u128) -> Result<i128, MembraneAdmissionError> {
    if negative {
        if magnitude == (i128::MAX as u128) + 1 {
            return Ok(i128::MIN);
        }
        let value =
            i128::try_from(magnitude).map_err(|_| MembraneAdmissionError::ArithmeticWidth)?;
        Ok(-value)
    } else {
        i128::try_from(magnitude).map_err(|_| MembraneAdmissionError::ArithmeticWidth)
    }
}

fn gcd(mut left: u128, mut right: u128) -> u128 {
    while right != 0 {
        let remainder = left % right;
        left = right;
        right = remainder;
    }
    left
}
