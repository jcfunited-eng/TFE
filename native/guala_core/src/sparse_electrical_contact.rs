//! Sparse exact electrical contact physics for reached neurons.
//!
//! Every contact reads one synchronous predecessor membrane generation,
//! computes `I = g(V_left - V_right)`, transfers one shared exact carrier
//! count from left to right, and applies equal-and-opposite membrane charge.
//! Contact state retains only the proper unresolved carrier phase.  Work and
//! current-state residency are linear in the reached neurons and contacts and
//! do not grow with organism age.
//!
//! Conduction is dissipative and therefore obeys the ratified energy-descent
//! law (`docs/GUALA_ENERGY_DESCENT_CHARGE_TRANSFER_RATIFICATION_2026-08-05.md`):
//! whole elementary charges cross a contact only while doing so STRICTLY
//! decreases the exact stored electrostatic energy of the two participating
//! neurons.  Ties and increases move zero charge, exactly as the psi ring
//! refuses a tied successor.  See `stored_energy_strictly_decreases`.
//!
//! This module contains no dense topology, neuron polling, owner, lock,
//! database, score, semantic label, receipt, or history log.

use core::cmp::Ordering;

use crate::complete_neuron::{PlasticSupportState, PlasticityError};
use crate::elementary_charge_membrane::{
    settle_membrane_elementary_charges, ElementaryChargeMembraneState, MembraneCapacitance,
    MembraneChargeError,
};
use crate::elementary_charge_transfer::{
    current_limited_by_available_carriers, exact_current_for_whole_carrier_transfer,
    settle_elementary_charge_transfer, ChargeCarrierPhase, ChargeTransferError,
};
use crate::exact_rational::{ExactRational, ExactRationalError};
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{Signed, ToPrimitive, Zero};

const PICOSIEMENS_MILLIVOLTS_PER_PICOAMPERE: u128 = 1_000;
const JUNCTION_TOTAL_CHANNEL_POPULATION: u128 = 6_400;
const JUNCTION_GENESIS_CONDUCTING_POPULATION: u128 = 50;
const JUNCTION_TRANSITION_WORK_NUMERATOR: i128 = 16_822_854_657;
const JUNCTION_TRANSITION_WORK_DENOMINATOR: u128 = 800_000_000;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum SparseElectricalError {
    InvalidEndpoint,
    /// An authored addition names a pair of members that this contact set
    /// already contacts.  Appending it would author the same physical
    /// adjacency twice; the caller is told rather than obeyed.
    ContactAlreadyAuthored,
    IncompleteReachedFrontier,
    NonPositiveConductance,
    AnatomyStateWidth,
    InvalidEncoding,
    ArithmeticWidth,
    Rational(ExactRationalError),
    ChargeTransfer(ChargeTransferError),
    Membrane(MembraneChargeError),
    Plasticity(PlasticityError),
}

impl From<ExactRationalError> for SparseElectricalError {
    fn from(value: ExactRationalError) -> Self {
        Self::Rational(value)
    }
}

impl From<ChargeTransferError> for SparseElectricalError {
    fn from(value: ChargeTransferError) -> Self {
        Self::ChargeTransfer(value)
    }
}

impl From<MembraneChargeError> for SparseElectricalError {
    fn from(value: MembraneChargeError) -> Self {
        Self::Membrane(value)
    }
}

impl From<PlasticityError> for SparseElectricalError {
    fn from(value: PlasticityError) -> Self {
        Self::Plasticity(value)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ElectricalContactAnatomy {
    left_neuron: usize,
    right_neuron: usize,
    single_channel_conductance_picosiemens: ExactRational,
    total_channel_population: u128,
    genesis_conducting_population: u128,
    transition_work_quantum_zeptojoules: ExactRational,
}

impl ElectricalContactAnatomy {
    pub(crate) fn new(
        left_neuron: usize,
        right_neuron: usize,
        conductance_picosiemens: ExactRational,
        neuron_count: usize,
    ) -> Result<Self, SparseElectricalError> {
        if left_neuron >= neuron_count
            || right_neuron >= neuron_count
            || left_neuron == right_neuron
        {
            return Err(SparseElectricalError::InvalidEndpoint);
        }
        if conductance_picosiemens.parts().0 <= 0 {
            return Err(SparseElectricalError::NonPositiveConductance);
        }
        let single_channel_conductance_picosiemens = conductance_picosiemens
            .checked_div_unsigned(JUNCTION_GENESIS_CONDUCTING_POPULATION)?;
        Ok(Self {
            left_neuron,
            right_neuron,
            single_channel_conductance_picosiemens,
            total_channel_population: JUNCTION_TOTAL_CHANNEL_POPULATION,
            genesis_conducting_population: JUNCTION_GENESIS_CONDUCTING_POPULATION,
            transition_work_quantum_zeptojoules: ExactRational::new(
                JUNCTION_TRANSITION_WORK_NUMERATOR,
                JUNCTION_TRANSITION_WORK_DENOMINATOR,
            )?,
        })
    }

    pub(crate) fn endpoints(self) -> (usize, usize) {
        (self.left_neuron, self.right_neuron)
    }

    pub(crate) fn conductance_picosiemens(self) -> ExactRational {
        self.single_channel_conductance_picosiemens
            .checked_mul_unsigned(self.genesis_conducting_population)
            .expect("validated contact constitution preserves its authored conductance")
    }

    pub(crate) fn single_channel_conductance_picosiemens(self) -> ExactRational {
        self.single_channel_conductance_picosiemens
    }

    pub(crate) fn total_channel_population(self) -> u128 {
        self.total_channel_population
    }

    pub(crate) fn genesis_conducting_population(self) -> u128 {
        self.genesis_conducting_population
    }

    pub(crate) fn transition_work_quantum_zeptojoules(self) -> ExactRational {
        self.transition_work_quantum_zeptojoules
    }

    pub(crate) fn rebind_endpoints(
        self,
        left_neuron: usize,
        right_neuron: usize,
        neuron_count: usize,
    ) -> Result<Self, SparseElectricalError> {
        if left_neuron >= neuron_count
            || right_neuron >= neuron_count
            || left_neuron == right_neuron
        {
            return Err(SparseElectricalError::InvalidEndpoint);
        }
        Ok(Self {
            left_neuron,
            right_neuron,
            ..self
        })
    }

    pub(crate) fn effective_conductance(
        self,
        state: &ElectricalContactState,
    ) -> Result<ExactRational, SparseElectricalError> {
        if state.conducting_channel_population > self.total_channel_population {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        self.single_channel_conductance_picosiemens
            .checked_mul_unsigned(state.conducting_channel_population)
            .map_err(Into::into)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ElectricalContactState {
    carrier_phase: ChargeCarrierPhase,
    conducting_channel_population: u128,
    /// Proper exact fraction of one approved transition-work quantum.
    /// Retained work is this phase multiplied by the contact's fixed quantum.
    transition_work_phase: ExactRational,
    /// Decode-only compatibility material for predecessor GLSEC02/GLRCS05
    /// bodies. It is never read by electrical or junctional physics.
    legacy_plastic_compatibility: PlasticSupportState,
}

impl ElectricalContactState {
    pub(crate) fn genesis(anatomy: ElectricalContactAnatomy) -> Self {
        Self {
            carrier_phase: ChargeCarrierPhase::zero(),
            conducting_channel_population: anatomy.genesis_conducting_population,
            transition_work_phase: ExactRational::integer(0),
            legacy_plastic_compatibility: PlasticSupportState::definitive_virtual_genesis(),
        }
    }

    pub(crate) fn from_legacy_carrier_phase(
        anatomy: ElectricalContactAnatomy,
        carrier_phase: ChargeCarrierPhase,
    ) -> Self {
        Self {
            carrier_phase,
            ..Self::genesis(anatomy)
        }
    }

    pub(crate) fn carrier_phase(&self) -> ChargeCarrierPhase {
        self.carrier_phase
    }

    pub(crate) fn conducting_channel_population(&self) -> u128 {
        self.conducting_channel_population
    }

    pub(crate) fn transition_work_phase(&self) -> ExactRational {
        self.transition_work_phase
    }

    pub(crate) fn legacy_plastic_compatibility_state(&self) -> PlasticSupportState {
        self.legacy_plastic_compatibility.clone()
    }

    pub(crate) fn from_legacy_physical_parts(
        anatomy: ElectricalContactAnatomy,
        carrier_phase: ChargeCarrierPhase,
        legacy_plastic_compatibility: PlasticSupportState,
    ) -> Self {
        Self {
            carrier_phase,
            legacy_plastic_compatibility,
            ..Self::genesis(anatomy)
        }
    }

    pub(crate) fn from_channel_parts(
        anatomy: ElectricalContactAnatomy,
        carrier_phase: ChargeCarrierPhase,
        conducting_channel_population: u128,
        transition_work_phase: ExactRational,
    ) -> Result<Self, SparseElectricalError> {
        if conducting_channel_population > anatomy.total_channel_population
            || transition_work_phase.parts().0 < 0
            || transition_work_phase.checked_cmp(ExactRational::integer(1))? != Ordering::Less
        {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        Ok(Self {
            carrier_phase,
            conducting_channel_population,
            transition_work_phase,
            legacy_plastic_compatibility: PlasticSupportState::definitive_virtual_genesis(),
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ElectricalContactTransition {
    pub(crate) successor: ElectricalContactState,
    pub(crate) outward_current_from_left_picoamperes: ExactRational,
    pub(crate) outward_elementary_charges_from_left: i128,
    pub(crate) released_work_zeptojoules: BigRational,
    pub(crate) exported_heat_zeptojoules: BigRational,
    pub(crate) conductance_changed: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum LocalGradientDirection {
    PassiveReturn,
    Quiescent,
    ActivePump,
}

fn combined_gradient_direction(
    left: LocalGradientDirection,
    right: LocalGradientDirection,
) -> LocalGradientDirection {
    use LocalGradientDirection::{ActivePump, PassiveReturn, Quiescent};
    match (left, right) {
        (Quiescent, direction) | (direction, Quiescent) => direction,
        (ActivePump, ActivePump) => ActivePump,
        (PassiveReturn, PassiveReturn) => PassiveReturn,
        (ActivePump, PassiveReturn) | (PassiveReturn, ActivePump) => Quiescent,
    }
}

fn wide_rational(value: ExactRational) -> BigRational {
    let (numerator, denominator) = value.parts();
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

fn narrow_rational(value: BigRational) -> Result<ExactRational, SparseElectricalError> {
    ExactRational::new(
        value
            .numer()
            .to_i128()
            .ok_or(SparseElectricalError::ArithmeticWidth)?,
        value
            .denom()
            .to_u128()
            .ok_or(SparseElectricalError::ArithmeticWidth)?,
    )
    .map_err(Into::into)
}

/// Apply the ratified contact-local junctional transition after electrical
/// current has settled. The exact work belongs to this contact alone; endpoint
/// gradient motion supplies only its physical direction. The successor
/// conductance cannot affect the interval that produced it.
pub(crate) fn settle_contact_local_conductance(
    anatomy: ElectricalContactAnatomy,
    mut transition: ElectricalContactTransition,
    left_direction: LocalGradientDirection,
    right_direction: LocalGradientDirection,
) -> Result<ElectricalContactTransition, SparseElectricalError> {
    let direction = combined_gradient_direction(left_direction, right_direction);
    let work = transition.released_work_zeptojoules.clone();
    if work.is_negative() {
        return Err(SparseElectricalError::ArithmeticWidth);
    }
    if work.is_zero() || direction == LocalGradientDirection::Quiescent {
        transition.exported_heat_zeptojoules = transition.released_work_zeptojoules.clone();
        return Ok(transition);
    }
    let quantum = wide_rational(anatomy.transition_work_quantum_zeptojoules);
    let predecessor_residue =
        wide_rational(transition.successor.transition_work_phase) * &quantum;
    let accumulated = predecessor_residue + work;
    let whole = (&accumulated / &quantum).floor().to_integer();
    let available = match direction {
        LocalGradientDirection::ActivePump => anatomy
            .total_channel_population
            .checked_sub(transition.successor.conducting_channel_population)
            .ok_or(SparseElectricalError::AnatomyStateWidth)?,
        LocalGradientDirection::PassiveReturn => {
            transition.successor.conducting_channel_population
        }
        LocalGradientDirection::Quiescent => 0,
    };
    let moved = if whole >= BigInt::from(available) {
        available
    } else {
        whole
            .to_u128()
            .ok_or(SparseElectricalError::ArithmeticWidth)?
    };
    if moved == 0 {
        if available == 0 {
            transition.successor.transition_work_phase = ExactRational::integer(0);
            transition.exported_heat_zeptojoules = accumulated;
        } else {
            transition.successor.transition_work_phase =
                narrow_rational(accumulated / &quantum)?;
            transition.exported_heat_zeptojoules = BigRational::zero();
        }
        return Ok(transition);
    }
    transition.successor.conducting_channel_population = match direction {
        LocalGradientDirection::ActivePump => transition
            .successor
            .conducting_channel_population
            .checked_add(moved)
            .ok_or(SparseElectricalError::ArithmeticWidth)?,
        LocalGradientDirection::PassiveReturn => transition
            .successor
            .conducting_channel_population
            .checked_sub(moved)
            .ok_or(SparseElectricalError::ArithmeticWidth)?,
        LocalGradientDirection::Quiescent => unreachable!(),
    };
    let reached_boundary = transition.successor.conducting_channel_population == 0
        || transition.successor.conducting_channel_population == anatomy.total_channel_population;
    let successor_residue = if reached_boundary {
        BigRational::zero()
    } else {
        &accumulated - &quantum * BigInt::from(moved)
    };
    let exported_heat = &accumulated - &successor_residue;
    transition.successor.transition_work_phase =
        narrow_rational(successor_residue / &quantum)?;
    transition.exported_heat_zeptojoules = exported_heat;
    transition.conductance_changed = moved != 0;
    Ok(transition)
}

/// One endpoint of a contact as the settlement sees it: the exact separated
/// charge and the authored capacitance that already define its potential.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ContactEndpoint {
    potential_millivolts: ExactRational,
    separated_elementary_charges: i128,
    capacitance: MembraneCapacitance,
    /// What this side actually HAS to give (2026-08-08).  A contact that
    /// knows only potentials will move charge carriers that do not exist.
    available_carriers: u128,
}

impl ContactEndpoint {
    fn new(
        potential_millivolts: ExactRational,
        membrane: ElementaryChargeMembraneState,
        capacitance: MembraneCapacitance,
        available_carriers: u128,
    ) -> Self {
        Self {
            potential_millivolts,
            separated_elementary_charges: membrane.separated_elementary_charges(),
            capacitance,
            available_carriers,
        }
    }
}

/// Exact energy-descent test for moving `transferred_from_left` whole
/// elementary charges from the left neuron to the right neuron.
///
/// A node's stored electrostatic energy in the unit system that already
/// exists here is `q^2 e^2 / (2 C)`: integrating the existing potential law
/// `V = q e / C` over the node's own separated charge.  Moving `n` whole
/// charges from left to right therefore changes the pair's stored energy by
///
/// ```text
///   dE = (e^2 / 2) * [ (n^2 - 2 n q_left) / C_left
///                    + (n^2 + 2 n q_right) / C_right ]
/// ```
///
/// The factor `e^2 / 2` is strictly positive and common to both terms, so it
/// cannot change the sign: the exact rational bracket alone decides
/// lawfulness.  No new constant, threshold, or damping factor is introduced —
/// only the authored capacitances and the separated charges already in state.
fn stored_energy_strictly_decreases(
    left: ContactEndpoint,
    right: ContactEndpoint,
    transferred_from_left: i128,
) -> Result<bool, SparseElectricalError> {
    let squared = transferred_from_left
        .checked_mul(transferred_from_left)
        .ok_or(SparseElectricalError::ArithmeticWidth)?;
    let doubled = transferred_from_left
        .checked_mul(2)
        .ok_or(SparseElectricalError::ArithmeticWidth)?;
    let left_numerator = squared
        .checked_sub(
            doubled
                .checked_mul(left.separated_elementary_charges)
                .ok_or(SparseElectricalError::ArithmeticWidth)?,
        )
        .ok_or(SparseElectricalError::ArithmeticWidth)?;
    let right_numerator = squared
        .checked_add(
            doubled
                .checked_mul(right.separated_elementary_charges)
                .ok_or(SparseElectricalError::ArithmeticWidth)?,
        )
        .ok_or(SparseElectricalError::ArithmeticWidth)?;
    let bracket = ExactRational::integer(left_numerator)
        .checked_div(left.capacitance.picofarads())?
        .checked_add(
            ExactRational::integer(right_numerator)
                .checked_div(right.capacitance.picofarads())?,
        )?;
    Ok(bracket.checked_cmp(ExactRational::integer(0))? == Ordering::Less)
}

/// Largest whole-carrier transfer in the field-driven direction that remains
/// strictly on the descending side of the pair's exact electrostatic energy.
/// For `m > 0`, the energy change is `A m² - 2|drive|m`, so descent requires
/// `m < 2|drive|/A`.  The strict integer maximum is therefore
/// `(numerator - 1) / denominator`; no time step or damping constant enters.
fn maximum_energy_descending_carriers(
    left: ContactEndpoint,
    right: ContactEndpoint,
    driven_direction: i128,
) -> Result<u128, SparseElectricalError> {
    let rational = |value: ExactRational| {
        let (numerator, denominator) = value.parts();
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    };
    let left_capacitance = rational(left.capacitance.picofarads());
    let right_capacitance = rational(right.capacitance.picofarads());
    let drive = BigRational::from_integer(BigInt::from(left.separated_elementary_charges))
        / &left_capacitance
        - BigRational::from_integer(BigInt::from(right.separated_elementary_charges))
            / &right_capacitance;
    if drive.is_zero()
        || drive.signum() != BigRational::from_integer(BigInt::from(driven_direction))
    {
        return Ok(0);
    }
    let curvature = BigRational::from_integer(BigInt::from(1)) / left_capacitance
        + BigRational::from_integer(BigInt::from(1)) / right_capacitance;
    let strict_boundary = (drive.abs() * BigInt::from(2)) / curvature;
    let numerator = strict_boundary.numer();
    if numerator <= &BigInt::from(0) {
        return Ok(0);
    }
    ((numerator - BigInt::from(1)) / strict_boundary.denom())
        .to_u128()
        .ok_or(SparseElectricalError::ArithmeticWidth)
}

/// A contact that conducts nothing this interval: no charge crosses, no
/// current is settled, and the unresolved carrier phase is retained exactly.
fn quiescent_contact(predecessor: ElectricalContactState) -> ElectricalContactTransition {
    ElectricalContactTransition {
        successor: predecessor,
        outward_current_from_left_picoamperes: ExactRational::integer(0),
        outward_elementary_charges_from_left: 0,
        released_work_zeptojoules: BigRational::zero(),
        exported_heat_zeptojoules: BigRational::zero(),
        conductance_changed: false,
    }
}

fn settle_contact(
    anatomy: ElectricalContactAnatomy,
    predecessor: ElectricalContactState,
    left: ContactEndpoint,
    right: ContactEndpoint,
    interval_microseconds: u32,
) -> Result<ElectricalContactTransition, SparseElectricalError> {
    let potential_difference = left
        .potential_millivolts
        .checked_sub(right.potential_millivolts)?;
    let current = anatomy
        .effective_conductance(&predecessor)?
        .checked_mul(potential_difference)?
        .checked_div_unsigned(PICOSIEMENS_MILLIVOLTS_PER_PICOAMPERE)?;
    settle_contact_at_current(predecessor, left, right, current, interval_microseconds)
}

fn settle_contact_at_current(
    predecessor: ElectricalContactState,
    left: ContactEndpoint,
    right: ContactEndpoint,
    current: ExactRational,
    interval_microseconds: u32,
) -> Result<ElectricalContactTransition, SparseElectricalError> {
    // Dissipative conduction cannot flow without descent.  Charge is
    // quantized, so the smallest move this contact could ever make is one
    // elementary charge in the direction the field drives.  If even that move
    // does not strictly lower the pair's exact stored energy there is no
    // lawful move at all: the contact conducts nothing, retains its exact
    // phase, and the pair rests.  (A move against the drive raises the energy
    // by `1/C_left + 1/C_right` plus twice the driving gradient, so the
    // driven direction is the only candidate; when the potentials are equal
    // both directions raise it.)
    let driven_direction = i128::from(current.parts().0.signum());
    if driven_direction == 0 || !stored_energy_strictly_decreases(left, right, driven_direction)? {
        return Ok(quiescent_contact(predecessor));
    }
    let maximum_descending = maximum_energy_descending_carriers(
        left,
        right,
        driven_direction,
    )?;
    let sender_reserve = if driven_direction > 0 {
        left.available_carriers
    } else {
        right.available_carriers
    };
    let available_descending = maximum_descending.min(sender_reserve);
    if available_descending == 0 {
        return Ok(quiescent_contact(predecessor));
    }
    let bounded_current = current_limited_by_available_carriers(
        predecessor.carrier_phase,
        current,
        interval_microseconds,
        available_descending,
    )?;
    let carrier = settle_elementary_charge_transfer(
        predecessor.carrier_phase,
        bounded_current,
        interval_microseconds,
    )?;
    // The settled whole-charge transfer itself must descend.  Only a step
    // that overshoots the pair's equalization point can fail here, which the
    // authored anatomy cannot reach (500 pS across 1 pF over 1 ms moves half
    // the imbalance); such a step is refused rather than silently applied.
    if carrier.outward_elementary_charges != 0
        && !stored_energy_strictly_decreases(left, right, carrier.outward_elementary_charges)?
    {
        return Ok(quiescent_contact(predecessor));
    }
    Ok(ElectricalContactTransition {
        successor: ElectricalContactState {
            carrier_phase: carrier.successor_phase,
            ..predecessor
        },
        outward_current_from_left_picoamperes: bounded_current,
        outward_elementary_charges_from_left: carrier.outward_elementary_charges,
        released_work_zeptojoules: BigRational::zero(),
        exported_heat_zeptojoules: BigRational::zero(),
        conductance_changed: false,
    })
}

/// Resolve simultaneous contact competition for each neuron's finite carrier
/// reservoir. Every provisional current is derived from the same predecessor
/// membrane generation. If their combined outward whole-carrier demand is
/// larger than the sender contains, every outgoing branch receives the same
/// exact availability fraction. Integer transport uses the conservative floor;
/// an indivisible remainder stays in the neuron rather than being assigned by
/// contact order.
fn jointly_carrier_bound_transitions(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    available_carriers: &[u128],
    interval_microseconds: u32,
    provisional: Vec<ElectricalContactTransition>,
) -> Result<Vec<ElectricalContactTransition>, SparseElectricalError> {
    let mut demanded_by_sender = vec![0_u128; anatomy.neuron_count];
    for (contact, transition) in anatomy.contacts.iter().zip(&provisional) {
        let sender = if transition.outward_elementary_charges_from_left > 0 {
            Some(contact.left_neuron)
        } else if transition.outward_elementary_charges_from_left < 0 {
            Some(contact.right_neuron)
        } else {
            None
        };
        if let Some(sender) = sender {
            demanded_by_sender[sender] = demanded_by_sender[sender]
                .checked_add(transition.outward_elementary_charges_from_left.unsigned_abs())
                .ok_or(SparseElectricalError::ArithmeticWidth)?;
        }
    }

    let potentials = predecessor_membranes
        .iter()
        .copied()
        .zip(capacitances.iter().copied())
        .map(|(membrane, capacitance)| membrane.potential_millivolts(capacitance))
        .collect::<Result<Vec<_>, _>>()?;
    let transitions = anatomy
        .contacts
        .iter()
        .copied()
        .zip(predecessor_contacts.contacts.iter().cloned())
        .zip(provisional)
        .map(|((contact, predecessor), transition)| -> Result<
            ElectricalContactTransition,
            SparseElectricalError,
        > {
            let sender = if transition.outward_elementary_charges_from_left > 0 {
                Some(contact.left_neuron)
            } else if transition.outward_elementary_charges_from_left < 0 {
                Some(contact.right_neuron)
            } else {
                None
            };
            let Some(sender) = sender else {
                return Ok(transition);
            };
            let total_demand = demanded_by_sender[sender];
            let available = available_carriers[sender];
            if total_demand <= available {
                return Ok(transition);
            }
            let demand = transition.outward_elementary_charges_from_left.unsigned_abs();
            let allocated = (BigInt::from(demand) * BigInt::from(available)
                / BigInt::from(total_demand))
            .to_u128()
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
            let bounded_current = current_limited_by_available_carriers(
                predecessor.carrier_phase,
                transition.outward_current_from_left_picoamperes,
                interval_microseconds,
                allocated,
            )?;
            let left_available = if sender == contact.left_neuron {
                allocated
            } else {
                available_carriers[contact.left_neuron]
            };
            let right_available = if sender == contact.right_neuron {
                allocated
            } else {
                available_carriers[contact.right_neuron]
            };
            settle_contact_at_current(
                predecessor,
                ContactEndpoint::new(
                    potentials[contact.left_neuron],
                    predecessor_membranes[contact.left_neuron],
                    capacitances[contact.left_neuron],
                    left_available,
                ),
                ContactEndpoint::new(
                    potentials[contact.right_neuron],
                    predecessor_membranes[contact.right_neuron],
                    capacitances[contact.right_neuron],
                    right_available,
                ),
                bounded_current,
                interval_microseconds,
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    globally_energy_descending_transitions(
        anatomy,
        predecessor_contacts,
        capacitances,
        predecessor_membranes,
        available_carriers,
        interval_microseconds,
        transitions,
    )
}

/// Settle simultaneous sparse currents on the exact minimum of the cohort's
/// electrostatic energy along their already-derived flow direction. Pairwise
/// descent alone is insufficient when contacts share a neuron: two lawful
/// pair moves can overshoot one another in the same interval. For node outward
/// transfers `d_i`, cohort energy along scale `lambda` is
/// `E(lambda)=E(0)-2 B lambda+A lambda²`; its physical line minimum is
/// `lambda=B/A`. The full step is retained when it already lies before that
/// minimum. Otherwise all sparse currents receive the same exact scale.
fn globally_energy_descending_transitions(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    available_carriers: &[u128],
    interval_microseconds: u32,
    transitions: Vec<ElectricalContactTransition>,
) -> Result<Vec<ElectricalContactTransition>, SparseElectricalError> {
    let outward = outward_by_neuron(anatomy, &transitions)?;
    let mut curvature = BigRational::from_integer(BigInt::from(0));
    let mut descent = BigRational::from_integer(BigInt::from(0));
    for ((membrane, capacitance), node_outward) in predecessor_membranes
        .iter()
        .zip(capacitances)
        .zip(&outward)
    {
        let (capacitance_numerator, capacitance_denominator) =
            capacitance.picofarads().parts();
        let capacitance = BigRational::new(
            BigInt::from(capacitance_numerator),
            BigInt::from(capacitance_denominator),
        );
        let flow = BigInt::from(*node_outward);
        let charge = BigInt::from(membrane.separated_elementary_charges());
        curvature += BigRational::from_integer(&flow * &flow) / &capacitance;
        descent += BigRational::from_integer(charge * flow) / capacitance;
    }
    if curvature.is_zero() {
        return Ok(transitions);
    }
    if descent <= BigRational::from_integer(BigInt::from(0)) {
        return Ok(predecessor_contacts
            .contacts
            .iter()
            .cloned()
            .map(quiescent_contact)
            .collect());
    }
    let scale = &descent / &curvature;
    if scale >= BigRational::from_integer(BigInt::from(1)) {
        return Ok(transitions);
    }
    let scaled = anatomy
        .contacts
        .iter()
        .copied()
        .zip(predecessor_contacts.contacts.iter().cloned())
        .zip(transitions)
        .map(|((contact, predecessor), transition)| -> Result<
            ElectricalContactTransition,
            SparseElectricalError,
        > {
            let magnitude = (BigInt::from(
                transition
                    .outward_elementary_charges_from_left
                    .unsigned_abs(),
            ) * scale.numer())
                / scale.denom();
            let magnitude = magnitude
                .to_u128()
                .ok_or(SparseElectricalError::ArithmeticWidth)?;
            let magnitude = i128::try_from(magnitude)
                .map_err(|_| SparseElectricalError::ArithmeticWidth)?;
            let carriers = if transition.outward_elementary_charges_from_left < 0 {
                -magnitude
            } else {
                magnitude
            };
            if carriers == 0 {
                return Ok(quiescent_contact(predecessor));
            }
            let left = ContactEndpoint::new(
                predecessor_membranes[contact.left_neuron]
                    .potential_millivolts(capacitances[contact.left_neuron])?,
                predecessor_membranes[contact.left_neuron],
                capacitances[contact.left_neuron],
                available_carriers[contact.left_neuron],
            );
            let right = ContactEndpoint::new(
                predecessor_membranes[contact.right_neuron]
                    .potential_millivolts(capacitances[contact.right_neuron])?,
                predecessor_membranes[contact.right_neuron],
                capacitances[contact.right_neuron],
                available_carriers[contact.right_neuron],
            );
            if !stored_energy_strictly_decreases(left, right, carriers)? {
                return Ok(quiescent_contact(predecessor));
            }
            Ok(ElectricalContactTransition {
                successor: predecessor,
                outward_current_from_left_picoamperes:
                    exact_current_for_whole_carrier_transfer(carriers, interval_microseconds)?,
                outward_elementary_charges_from_left: carriers,
                released_work_zeptojoules: BigRational::zero(),
                exported_heat_zeptojoules: BigRational::zero(),
                conductance_changed: false,
            })
        })
        .collect::<Result<Vec<_>, _>>()?;
    let scaled_outward = outward_by_neuron(anatomy, &scaled)?;
    let mut energy_change = BigRational::from_integer(BigInt::from(0));
    for ((membrane, capacitance), node_outward) in predecessor_membranes
        .iter()
        .zip(capacitances)
        .zip(scaled_outward)
    {
        let (capacitance_numerator, capacitance_denominator) =
            capacitance.picofarads().parts();
        let capacitance = BigRational::new(
            BigInt::from(capacitance_numerator),
            BigInt::from(capacitance_denominator),
        );
        let prior = BigInt::from(membrane.separated_elementary_charges());
        let successor = &prior - BigInt::from(node_outward);
        energy_change += BigRational::from_integer(&successor * &successor - &prior * &prior)
            / capacitance;
    }
    if energy_change < BigRational::from_integer(BigInt::from(0)) {
        Ok(scaled)
    } else {
        Ok(predecessor_contacts
            .contacts
            .iter()
            .cloned()
            .map(quiescent_contact)
            .collect())
    }
}

fn outward_by_neuron(
    anatomy: &SparseElectricalAnatomy,
    transitions: &[ElectricalContactTransition],
) -> Result<Vec<i128>, SparseElectricalError> {
    let mut outward = vec![0_i128; anatomy.neuron_count];
    for (contact, transition) in anatomy.contacts.iter().zip(transitions) {
        outward[contact.left_neuron] = outward[contact.left_neuron]
            .checked_add(transition.outward_elementary_charges_from_left)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        outward[contact.right_neuron] = outward[contact.right_neuron]
            .checked_sub(transition.outward_elementary_charges_from_left)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
    }
    Ok(outward)
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SparseElectricalAnatomy {
    neuron_count: usize,
    contacts: Box<[ElectricalContactAnatomy]>,
}

impl SparseElectricalAnatomy {
    pub(crate) fn new(
        neuron_count: usize,
        contacts: Vec<ElectricalContactAnatomy>,
    ) -> Result<Self, SparseElectricalError> {
        if neuron_count == 0
            || contacts.iter().any(|contact| {
                contact.left_neuron >= neuron_count
                    || contact.right_neuron >= neuron_count
                    || contact.left_neuron == contact.right_neuron
            })
        {
            return Err(SparseElectricalError::InvalidEndpoint);
        }
        Ok(Self {
            neuron_count,
            contacts: contacts.into_boxed_slice(),
        })
    }

    pub(crate) fn neuron_count(&self) -> usize {
        self.neuron_count
    }

    pub(crate) fn contact_count(&self) -> usize {
        self.contacts.len()
    }

    pub(crate) fn contact_endpoints(&self) -> impl ExactSizeIterator<Item = (usize, usize)> + '_ {
        self.contacts.iter().map(|contact| contact.endpoints())
    }

    pub(crate) fn contact_anatomies(&self) -> &[ElectricalContactAnatomy] {
        &self.contacts
    }

    pub(crate) fn extend_neuron_count(
        &self,
        neuron_count: usize,
    ) -> Result<Self, SparseElectricalError> {
        if neuron_count < self.neuron_count {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        Self::new(neuron_count, self.contacts.to_vec())
    }

    /// Append authored contacts to a living contact set, at the end, and
    /// nowhere else.
    ///
    /// The same discipline `extend_neuron_count` holds for members holds here
    /// for contacts: every already-authored contact keeps its exact index,
    /// endpoints and conductance, so the unresolved carrier phase retained
    /// against that index (and every `StablePhysicalBondReference` derived
    /// from it) still names the same physical contact afterwards.  Nothing is
    /// reordered, renumbered, removed or re-materialized.
    ///
    /// An addition whose endpoint pair is already contacted — in the existing
    /// set or earlier in the same batch — is refused rather than silently
    /// authored a second time: re-running an authorship must not quietly
    /// double a body's anatomy.  A body that already carries the addition is
    /// therefore left exactly as it is, with its reason named.
    pub(crate) fn append_contacts(
        &self,
        additions: Vec<ElectricalContactAnatomy>,
    ) -> Result<Self, SparseElectricalError> {
        let mut contacts = self.contacts.to_vec();
        for addition in additions {
            if addition.left_neuron >= self.neuron_count
                || addition.right_neuron >= self.neuron_count
                || addition.left_neuron == addition.right_neuron
            {
                return Err(SparseElectricalError::InvalidEndpoint);
            }
            if contacts.iter().any(|contact| {
                (contact.left_neuron, contact.right_neuron)
                    == (addition.left_neuron, addition.right_neuron)
                    || (contact.left_neuron, contact.right_neuron)
                        == (addition.right_neuron, addition.left_neuron)
            }) {
                return Err(SparseElectricalError::ContactAlreadyAuthored);
            }
            contacts.push(addition);
        }
        let successor = Self::new(self.neuron_count, contacts)?;
        // Append-only, checked rather than assumed: the successor's leading
        // contacts are this anatomy's contacts, unchanged and in order.
        if successor.contacts.len() < self.contacts.len()
            || successor.contacts[..self.contacts.len()] != *self.contacts
        {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        Ok(successor)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SparseElectricalState {
    contacts: Box<[ElectricalContactState]>,
}

impl SparseElectricalState {
    pub(crate) fn genesis(anatomy: &SparseElectricalAnatomy) -> Self {
        Self {
            contacts: anatomy
                .contacts
                .iter()
                .copied()
                .map(ElectricalContactState::genesis)
                .collect::<Vec<_>>()
                .into_boxed_slice(),
        }
    }

    pub(crate) fn contact_count(&self) -> usize {
        self.contacts.len()
    }

    pub(crate) fn resident_contact_bytes(&self) -> Option<usize> {
        self.contacts
            .len()
            .checked_mul(core::mem::size_of::<ElectricalContactState>())
    }

    pub(crate) fn contact_states(&self) -> &[ElectricalContactState] {
        &self.contacts
    }

    pub(crate) fn from_contact_states(
        anatomy: &SparseElectricalAnatomy,
        contacts: Vec<ElectricalContactState>,
    ) -> Result<Self, SparseElectricalError> {
        if contacts.len() != anatomy.contacts.len() {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        Ok(Self {
            contacts: contacts.into_boxed_slice(),
        })
    }

    /// Widen this state onto an anatomy whose contact list was appended to.
    ///
    /// Every retained carrier phase travels through verbatim at its own
    /// index; each newly authored contact starts from the authored rest
    /// state — the same `ElectricalContactState::genesis()` a contact is born
    /// with — because a contact that has never conducted holds no unresolved
    /// phase.
    pub(crate) fn append_genesis_contacts(
        &self,
        successor_anatomy: &SparseElectricalAnatomy,
    ) -> Result<Self, SparseElectricalError> {
        if successor_anatomy.contacts.len() < self.contacts.len() {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        let mut contacts = self.contacts.to_vec();
        contacts.extend(
            successor_anatomy.contacts[self.contacts.len()..]
                .iter()
                .copied()
                .map(ElectricalContactState::genesis),
        );
        Self::from_contact_states(successor_anatomy, contacts)
    }
}

const SPARSE_ELECTRICAL_CELL_CODEC_MAGIC: &[u8; 8] = b"GLSEC01\0";
const SPARSE_ELECTRICAL_CELL_CODEC_V2_MAGIC: &[u8; 8] = b"GLSEC02\0";
const SPARSE_ELECTRICAL_CELL_CODEC_V3_MAGIC: &[u8; 8] = b"GLSEC03\0";
const SPARSE_ELECTRICAL_CELL_CONTACT_BYTES: usize = 80;
const SPARSE_ELECTRICAL_CELL_V2_CONTACT_BYTES: usize = 160;
const SPARSE_ELECTRICAL_CELL_V3_CONTACT_BYTES: usize = 192;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum SparseElectricalCellFormat {
    V1,
    V2,
    V3,
}

pub(crate) fn sparse_electrical_cell_format(
    encoded: &[u8],
) -> Result<SparseElectricalCellFormat, SparseElectricalError> {
    match encoded.get(..SPARSE_ELECTRICAL_CELL_CODEC_MAGIC.len()) {
        Some(magic) if magic == SPARSE_ELECTRICAL_CELL_CODEC_MAGIC => {
            Ok(SparseElectricalCellFormat::V1)
        }
        Some(magic) if magic == SPARSE_ELECTRICAL_CELL_CODEC_V2_MAGIC => {
            Ok(SparseElectricalCellFormat::V2)
        }
        Some(magic) if magic == SPARSE_ELECTRICAL_CELL_CODEC_V3_MAGIC => {
            Ok(SparseElectricalCellFormat::V3)
        }
        _ => Err(SparseElectricalError::InvalidEncoding),
    }
}

/// Keep fixed sparse-contact anatomy and its unresolved carrier phase together
/// across cold restart. The encoding chooses no contacts or conductances.
pub(crate) fn encode_sparse_electrical_cell(
    anatomy: &SparseElectricalAnatomy,
    state: &SparseElectricalState,
) -> Result<Vec<u8>, SparseElectricalError> {
    if anatomy.contacts.len() != state.contacts.len() {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(SPARSE_ELECTRICAL_CELL_CODEC_V3_MAGIC);
    push_electrical_usize(&mut encoded, anatomy.neuron_count)?;
    push_electrical_usize(&mut encoded, anatomy.contacts.len())?;
    for (contact, contact_state) in anatomy.contacts.iter().zip(state.contacts.iter()) {
        push_electrical_usize(&mut encoded, contact.left_neuron)?;
        push_electrical_usize(&mut encoded, contact.right_neuron)?;
        let (unit_numerator, unit_denominator) =
            contact.single_channel_conductance_picosiemens.parts();
        encoded.extend_from_slice(&unit_numerator.to_le_bytes());
        encoded.extend_from_slice(&unit_denominator.to_le_bytes());
        encoded.extend_from_slice(&contact.total_channel_population.to_le_bytes());
        encoded.extend_from_slice(&contact.genesis_conducting_population.to_le_bytes());
        let (quantum_numerator, quantum_denominator) =
            contact.transition_work_quantum_zeptojoules.parts();
        encoded.extend_from_slice(&quantum_numerator.to_le_bytes());
        encoded.extend_from_slice(&quantum_denominator.to_le_bytes());
        let (phase_numerator, phase_denominator) = contact_state.carrier_phase.parts();
        encoded.extend_from_slice(&phase_numerator.to_le_bytes());
        encoded.extend_from_slice(&phase_denominator.to_le_bytes());
        encoded.extend_from_slice(&contact_state.conducting_channel_population.to_le_bytes());
        let (residue_numerator, residue_denominator) =
            contact_state.transition_work_phase.parts();
        encoded.extend_from_slice(&residue_numerator.to_le_bytes());
        encoded.extend_from_slice(&residue_denominator.to_le_bytes());
    }
    Ok(encoded)
}

/// Reproduce an admitted `GLSEC02` body exactly.  The retained plastic fields
/// are predecessor compatibility bytes only; current contact physics never
/// reads them.
pub(crate) fn encode_sparse_electrical_cell_v2(
    anatomy: &SparseElectricalAnatomy,
    state: &SparseElectricalState,
) -> Result<Vec<u8>, SparseElectricalError> {
    if anatomy.contacts.len() != state.contacts.len()
        || anatomy
            .contacts
            .iter()
            .zip(state.contacts.iter())
            .any(|(anatomy, contact)| {
                contact.conducting_channel_population != anatomy.genesis_conducting_population
                    || contact.transition_work_phase.parts().0 != 0
            })
    {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(SPARSE_ELECTRICAL_CELL_CODEC_V2_MAGIC);
    push_electrical_usize(&mut encoded, anatomy.neuron_count)?;
    push_electrical_usize(&mut encoded, anatomy.contacts.len())?;
    for (contact, contact_state) in anatomy.contacts.iter().zip(state.contacts.iter()) {
        push_electrical_usize(&mut encoded, contact.left_neuron)?;
        push_electrical_usize(&mut encoded, contact.right_neuron)?;
        let (conductance_numerator, conductance_denominator) =
            contact.conductance_picosiemens().parts();
        encoded.extend_from_slice(&conductance_numerator.to_le_bytes());
        encoded.extend_from_slice(&conductance_denominator.to_le_bytes());
        let (phase_numerator, phase_denominator) = contact_state.carrier_phase.parts();
        encoded.extend_from_slice(&phase_numerator.to_le_bytes());
        encoded.extend_from_slice(&phase_denominator.to_le_bytes());
        let (rest, dissipated, residue) = contact_state
            .legacy_plastic_compatibility
            .physical_parts();
        let (rest_numerator, rest_denominator) = rest.parts();
        encoded.extend_from_slice(&rest_numerator.to_le_bytes());
        encoded.extend_from_slice(&rest_denominator.to_le_bytes());
        encoded.extend_from_slice(&dissipated.to_le_bytes());
        let (residue_numerator, residue_denominator) = residue.parts();
        encoded.extend_from_slice(&residue_numerator.to_le_bytes());
        encoded.extend_from_slice(&residue_denominator.to_le_bytes());
    }
    Ok(encoded)
}

/// Reproduce the admitted pre-contact-plasticity `GLSEC01` body exactly.
/// This exists only so an outer legacy cognitive codec can prove that an old
/// body was canonical before upgrading it; new state is always written by
/// `encode_sparse_electrical_cell` above.
pub(crate) fn encode_sparse_electrical_cell_v1(
    anatomy: &SparseElectricalAnatomy,
    state: &SparseElectricalState,
) -> Result<Vec<u8>, SparseElectricalError> {
    if anatomy.contacts.len() != state.contacts.len()
        || anatomy
            .contacts
            .iter()
            .zip(state.contacts.iter())
            .any(|(anatomy, contact)| {
                contact.conducting_channel_population != anatomy.genesis_conducting_population
                    || contact.transition_work_phase.parts().0 != 0
                    || contact.legacy_plastic_compatibility
                        != PlasticSupportState::definitive_virtual_genesis()
            })
    {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(SPARSE_ELECTRICAL_CELL_CODEC_MAGIC);
    push_electrical_usize(&mut encoded, anatomy.neuron_count)?;
    push_electrical_usize(&mut encoded, anatomy.contacts.len())?;
    for (contact, contact_state) in anatomy.contacts.iter().zip(state.contacts.iter()) {
        push_electrical_usize(&mut encoded, contact.left_neuron)?;
        push_electrical_usize(&mut encoded, contact.right_neuron)?;
        let (conductance_numerator, conductance_denominator) =
            contact.conductance_picosiemens().parts();
        encoded.extend_from_slice(&conductance_numerator.to_le_bytes());
        encoded.extend_from_slice(&conductance_denominator.to_le_bytes());
        let (phase_numerator, phase_denominator) = contact_state.carrier_phase.parts();
        encoded.extend_from_slice(&phase_numerator.to_le_bytes());
        encoded.extend_from_slice(&phase_denominator.to_le_bytes());
    }
    Ok(encoded)
}

pub(crate) fn decode_sparse_electrical_cell(
    encoded: &[u8],
) -> Result<(SparseElectricalAnatomy, SparseElectricalState), SparseElectricalError> {
    let mut reader = SparseElectricalCellReader::new(encoded);
    let magic = reader.take(SPARSE_ELECTRICAL_CELL_CODEC_MAGIC.len())?;
    let carries_channels = magic == SPARSE_ELECTRICAL_CELL_CODEC_V3_MAGIC;
    let carries_plastic = magic == SPARSE_ELECTRICAL_CELL_CODEC_V2_MAGIC;
    if !carries_channels && !carries_plastic && magic != SPARSE_ELECTRICAL_CELL_CODEC_MAGIC {
        return Err(SparseElectricalError::InvalidEncoding);
    }
    let neuron_count = reader.usize()?;
    let contact_count = reader.usize()?;
    reader.require_records(
        contact_count,
        if carries_channels {
            SPARSE_ELECTRICAL_CELL_V3_CONTACT_BYTES
        } else if carries_plastic {
            SPARSE_ELECTRICAL_CELL_V2_CONTACT_BYTES
        } else {
            SPARSE_ELECTRICAL_CELL_CONTACT_BYTES
        },
    )?;
    let mut contacts = Vec::new();
    let mut states = Vec::new();
    contacts
        .try_reserve_exact(contact_count)
        .map_err(|_| SparseElectricalError::ArithmeticWidth)?;
    states
        .try_reserve_exact(contact_count)
        .map_err(|_| SparseElectricalError::ArithmeticWidth)?;
    for _ in 0..contact_count {
        let left = reader.usize()?;
        let right = reader.usize()?;
        let contact = if carries_channels {
            let single_channel_conductance_picosiemens =
                ExactRational::new(reader.i128()?, reader.u128()?)?;
            let total_channel_population = reader.u128()?;
            let genesis_conducting_population = reader.u128()?;
            let transition_work_quantum_zeptojoules =
                ExactRational::new(reader.i128()?, reader.u128()?)?;
            if left >= neuron_count
                || right >= neuron_count
                || left == right
                || single_channel_conductance_picosiemens.parts().0 <= 0
                || total_channel_population != JUNCTION_TOTAL_CHANNEL_POPULATION
                || genesis_conducting_population != JUNCTION_GENESIS_CONDUCTING_POPULATION
                || transition_work_quantum_zeptojoules
                    != ExactRational::new(
                        JUNCTION_TRANSITION_WORK_NUMERATOR,
                        JUNCTION_TRANSITION_WORK_DENOMINATOR,
                    )?
            {
                return Err(SparseElectricalError::InvalidEncoding);
            }
            ElectricalContactAnatomy {
                left_neuron: left,
                right_neuron: right,
                single_channel_conductance_picosiemens,
                total_channel_population,
                genesis_conducting_population,
                transition_work_quantum_zeptojoules,
            }
        } else {
            ElectricalContactAnatomy::new(
                left,
                right,
                ExactRational::new(reader.i128()?, reader.u128()?)?,
                neuron_count,
            )?
        };
        let phase = ChargeCarrierPhase::new(reader.i128()?, reader.u128()?)?;
        states.push(if carries_channels {
            ElectricalContactState::from_channel_parts(
                contact,
                phase,
                reader.u128()?,
                ExactRational::new(reader.i128()?, reader.u128()?)?,
            )?
        } else if carries_plastic {
            let legacy_plastic = PlasticSupportState::from_physical_parts(
                ExactRational::new(reader.i128()?, reader.u128()?)?,
                reader.u128()?,
                ExactRational::new(reader.i128()?, reader.u128()?)?,
            )?;
            ElectricalContactState::from_legacy_physical_parts(contact, phase, legacy_plastic)
        } else {
            ElectricalContactState::from_legacy_carrier_phase(contact, phase)
        });
        contacts.push(contact);
    }
    if !reader.finished() {
        return Err(SparseElectricalError::InvalidEncoding);
    }
    let anatomy = SparseElectricalAnatomy::new(neuron_count, contacts)?;
    let state = SparseElectricalState::from_contact_states(&anatomy, states)?;
    Ok((anatomy, state))
}

fn push_electrical_usize(encoded: &mut Vec<u8>, value: usize) -> Result<(), SparseElectricalError> {
    encoded.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| SparseElectricalError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

struct SparseElectricalCellReader<'a> {
    encoded: &'a [u8],
    cursor: usize,
}

impl<'a> SparseElectricalCellReader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self { encoded, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], SparseElectricalError> {
        let end = self
            .cursor
            .checked_add(count)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        let value = self
            .encoded
            .get(self.cursor..end)
            .ok_or(SparseElectricalError::InvalidEncoding)?;
        self.cursor = end;
        Ok(value)
    }

    fn require_records(
        &self,
        count: usize,
        record_bytes: usize,
    ) -> Result<(), SparseElectricalError> {
        let required = count
            .checked_mul(record_bytes)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        let remaining = self
            .encoded
            .len()
            .checked_sub(self.cursor)
            .ok_or(SparseElectricalError::InvalidEncoding)?;
        if required > remaining {
            return Err(SparseElectricalError::InvalidEncoding);
        }
        Ok(())
    }

    fn usize(&mut self) -> Result<usize, SparseElectricalError> {
        usize::try_from(u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| SparseElectricalError::InvalidEncoding)?,
        ))
        .map_err(|_| SparseElectricalError::ArithmeticWidth)
    }

    fn i128(&mut self) -> Result<i128, SparseElectricalError> {
        Ok(i128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| SparseElectricalError::InvalidEncoding)?,
        ))
    }

    fn u128(&mut self) -> Result<u128, SparseElectricalError> {
        Ok(u128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| SparseElectricalError::InvalidEncoding)?,
        ))
    }

    fn finished(&self) -> bool {
        self.cursor == self.encoded.len()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SparseElectricalSettlement {
    pub(crate) successor_membranes: Box<[ElementaryChargeMembraneState]>,
    pub(crate) successor_contacts: SparseElectricalState,
    pub(crate) transitions: Box<[ElectricalContactTransition]>,
    pub(crate) outward_elementary_charges_by_neuron: Box<[i128]>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SparseElectricalTransferSettlement {
    pub(crate) successor_contacts: SparseElectricalState,
    pub(crate) transitions: Box<[ElectricalContactTransition]>,
    pub(crate) outward_elementary_charges_by_neuron: Box<[i128]>,
}

fn attach_contact_local_released_work(
    anatomy: &SparseElectricalAnatomy,
    potentials_millivolts: &[ExactRational],
    interval_microseconds: u32,
    transitions: &mut [ElectricalContactTransition],
) -> Result<(), SparseElectricalError> {
    if anatomy.contacts.len() != transitions.len()
        || potentials_millivolts.len() != anatomy.neuron_count
    {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }
    for (contact, transition) in anatomy.contacts.iter().zip(transitions.iter_mut()) {
        // Exact zero current releases exactly zero work and heat.  Returning
        // here avoids constructing and multiplying arbitrary-precision
        // rationals for every quiescent contact in a large reached frontier;
        // it changes no physical value.
        if transition
            .outward_current_from_left_picoamperes
            .parts()
            .0
            == 0
        {
            transition.released_work_zeptojoules = BigRational::zero();
            transition.exported_heat_zeptojoules = BigRational::zero();
            continue;
        }
        let potential_difference = wide_rational(potentials_millivolts[contact.left_neuron])
            - wide_rational(potentials_millivolts[contact.right_neuron]);
        let released = wide_rational(transition.outward_current_from_left_picoamperes)
            * potential_difference
            * BigInt::from(interval_microseconds);
        if released.is_negative() {
            return Err(SparseElectricalError::ArithmeticWidth);
        }
        transition.released_work_zeptojoules = released.clone();
        transition.exported_heat_zeptojoules = released;
    }
    Ok(())
}

/// Settle sparse contact currents and their shared carrier phases from one
/// predecessor generation. The returned equal-and-opposite carrier counts are
/// not applied here; a reached neuron cohort must combine them atomically with
/// each neuron's same-interval local membrane and material consequences.
pub(crate) fn settle_sparse_electrical_transfers(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    available_carriers: &[u128],
    interval_microseconds: u32,
) -> Result<SparseElectricalTransferSettlement, SparseElectricalError> {
    if predecessor_contacts.contacts.len() != anatomy.contacts.len()
        || capacitances.len() != anatomy.neuron_count
        || predecessor_membranes.len() != anatomy.neuron_count
    {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }

    let potentials = predecessor_membranes
        .iter()
        .copied()
        .zip(capacitances.iter().copied())
        .map(|(membrane, capacitance)| membrane.potential_millivolts(capacitance))
        .collect::<Result<Vec<_>, _>>()?;
    let mut provisional = Vec::with_capacity(anatomy.contacts.len());

    for (index, contact) in anatomy.contacts.iter().copied().enumerate() {
        let transition = settle_contact(
            contact,
            predecessor_contacts.contacts[index].clone(),
            ContactEndpoint::new(
                potentials[contact.left_neuron],
                predecessor_membranes[contact.left_neuron],
                capacitances[contact.left_neuron],
                u128::MAX,
            ),
            ContactEndpoint::new(
                potentials[contact.right_neuron],
                predecessor_membranes[contact.right_neuron],
                capacitances[contact.right_neuron],
                u128::MAX,
            ),
            interval_microseconds,
        )?;
        provisional.push(transition);
    }
    let mut transitions = jointly_carrier_bound_transitions(
        anatomy,
        predecessor_contacts,
        capacitances,
        predecessor_membranes,
        available_carriers,
        interval_microseconds,
        provisional,
    )?;
    attach_contact_local_released_work(
        anatomy,
        &potentials,
        interval_microseconds,
        &mut transitions,
    )?;
    let mut outward_by_neuron = vec![0_i128; anatomy.neuron_count];
    for (contact, transition) in anatomy.contacts.iter().zip(&transitions) {
        let right_outward = transition
            .outward_elementary_charges_from_left
            .checked_neg()
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        outward_by_neuron[contact.left_neuron] = outward_by_neuron[contact.left_neuron]
            .checked_add(transition.outward_elementary_charges_from_left)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        outward_by_neuron[contact.right_neuron] = outward_by_neuron[contact.right_neuron]
            .checked_add(right_outward)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
    }
    let conserved = outward_by_neuron.iter().try_fold(0_i128, |total, value| {
        total
            .checked_add(*value)
            .ok_or(SparseElectricalError::ArithmeticWidth)
    })?;
    if conserved != 0 {
        return Err(SparseElectricalError::ArithmeticWidth);
    }

    Ok(SparseElectricalTransferSettlement {
        successor_contacts: SparseElectricalState {
            contacts: transitions
                .iter()
                .map(|transition| transition.successor.clone())
                .collect::<Vec<_>>()
                .into_boxed_slice(),
        },
        transitions: transitions.into_boxed_slice(),
        outward_elementary_charges_by_neuron: outward_by_neuron.into_boxed_slice(),
    })
}

/// Settle only contacts whose two endpoints are in the supplied reached
/// frontier. A mounted contact crossing the frontier makes that frontier
/// physically incomplete: the neighbour must be reached rather than silently
/// ignored. Contacts wholly outside the frontier retain their exact state and
/// perform zero work.
pub(crate) fn settle_sparse_electrical_transfers_reached(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    reached_neurons: &[bool],
    available_carriers: &[u128],
    interval_microseconds: u32,
) -> Result<SparseElectricalTransferSettlement, SparseElectricalError> {
    if predecessor_contacts.contacts.len() != anatomy.contacts.len()
        || capacitances.len() != anatomy.neuron_count
        || predecessor_membranes.len() != anatomy.neuron_count
        || reached_neurons.len() != anatomy.neuron_count
    {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }

    let potentials = predecessor_membranes
        .iter()
        .copied()
        .zip(capacitances.iter().copied())
        .map(|(membrane, capacitance)| membrane.potential_millivolts(capacitance))
        .collect::<Result<Vec<_>, _>>()?;
    let mut provisional = Vec::with_capacity(anatomy.contacts.len());

    for (index, contact) in anatomy.contacts.iter().copied().enumerate() {
        let left_reached = reached_neurons[contact.left_neuron];
        let right_reached = reached_neurons[contact.right_neuron];
        if left_reached != right_reached {
            return Err(SparseElectricalError::IncompleteReachedFrontier);
        }
        let transition = if left_reached {
            settle_contact(
                contact,
                predecessor_contacts.contacts[index].clone(),
                ContactEndpoint::new(
                    potentials[contact.left_neuron],
                    predecessor_membranes[contact.left_neuron],
                    capacitances[contact.left_neuron],
                    u128::MAX,
                ),
                ContactEndpoint::new(
                    potentials[contact.right_neuron],
                    predecessor_membranes[contact.right_neuron],
                    capacitances[contact.right_neuron],
                    u128::MAX,
                ),
                interval_microseconds,
            )?
        } else {
            quiescent_contact(predecessor_contacts.contacts[index].clone())
        };
        provisional.push(transition);
    }
    let mut transitions = jointly_carrier_bound_transitions(
        anatomy,
        predecessor_contacts,
        capacitances,
        predecessor_membranes,
        available_carriers,
        interval_microseconds,
        provisional,
    )?;
    attach_contact_local_released_work(
        anatomy,
        &potentials,
        interval_microseconds,
        &mut transitions,
    )?;
    let mut outward_by_neuron = vec![0_i128; anatomy.neuron_count];
    for (contact, transition) in anatomy.contacts.iter().zip(&transitions) {
        let right_outward = transition
            .outward_elementary_charges_from_left
            .checked_neg()
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        outward_by_neuron[contact.left_neuron] = outward_by_neuron[contact.left_neuron]
            .checked_add(transition.outward_elementary_charges_from_left)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
        outward_by_neuron[contact.right_neuron] = outward_by_neuron[contact.right_neuron]
            .checked_add(right_outward)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
    }

    if outward_by_neuron.iter().try_fold(0_i128, |total, value| {
        total
            .checked_add(*value)
            .ok_or(SparseElectricalError::ArithmeticWidth)
    })? != 0
    {
        return Err(SparseElectricalError::ArithmeticWidth);
    }

    Ok(SparseElectricalTransferSettlement {
        successor_contacts: SparseElectricalState {
            contacts: transitions
                .iter()
                .map(|transition| transition.successor.clone())
                .collect::<Vec<_>>()
                .into_boxed_slice(),
        },
        transitions: transitions.into_boxed_slice(),
        outward_elementary_charges_by_neuron: outward_by_neuron.into_boxed_slice(),
    })
}

/// Settle only the supplied sparse reached contact fabric.  Every current is
/// computed from the same predecessor membrane generation before any charge
/// consequence is applied.
pub(crate) fn settle_sparse_electrical_contacts(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    available_carriers: &[u128],
    interval_microseconds: u32,
) -> Result<SparseElectricalSettlement, SparseElectricalError> {
    let transfer = settle_sparse_electrical_transfers(
        anatomy,
        predecessor_contacts,
        capacitances,
        predecessor_membranes,
        available_carriers,
        interval_microseconds,
    )?;

    let successor_membranes = predecessor_membranes
        .iter()
        .copied()
        .zip(capacitances.iter().copied())
        .zip(
            transfer
                .outward_elementary_charges_by_neuron
                .iter()
                .copied(),
        )
        .map(|((membrane, capacitance), outward)| {
            settle_membrane_elementary_charges(
                capacitance,
                membrane,
                outward,
                interval_microseconds,
            )
            .map(|transition| transition.successor)
        })
        .collect::<Result<Vec<_>, _>>()?;

    Ok(SparseElectricalSettlement {
        successor_membranes: successor_membranes.into_boxed_slice(),
        successor_contacts: transfer.successor_contacts,
        transitions: transfer.transitions,
        outward_elementary_charges_by_neuron: transfer.outward_elementary_charges_by_neuron,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn capacitances(count: usize) -> Vec<MembraneCapacitance> {
        vec![MembraneCapacitance::new(ExactRational::integer(1)).unwrap(); count]
    }

    fn total_charge(memebranes: &[ElementaryChargeMembraneState]) -> i128 {
        memebranes
            .iter()
            .map(|membrane| membrane.separated_elementary_charges())
            .sum()
    }

    fn released_transition(
        contact: ElectricalContactAnatomy,
        work: ExactRational,
    ) -> ElectricalContactTransition {
        ElectricalContactTransition {
            successor: ElectricalContactState::genesis(contact),
            outward_current_from_left_picoamperes: ExactRational::integer(1),
            outward_elementary_charges_from_left: 1,
            released_work_zeptojoules: wide_rational(work),
            exported_heat_zeptojoules: wide_rational(work),
            conductance_changed: false,
        }
    }

    #[test]
    fn one_contact_changes_only_next_interval_conductance_and_conserves_work() {
        let contact = ElectricalContactAnatomy::new(
            0,
            1,
            ExactRational::integer(500),
            2,
        )
        .unwrap();
        let quantum = contact.transition_work_quantum_zeptojoules();
        let half_quantum = quantum.checked_div_unsigned(2).unwrap();
        let work = quantum
            .checked_mul_unsigned(2)
            .unwrap()
            .checked_add(half_quantum)
            .unwrap();
        let strengthened = settle_contact_local_conductance(
            contact,
            released_transition(contact, work),
            LocalGradientDirection::ActivePump,
            LocalGradientDirection::Quiescent,
        )
        .unwrap();
        assert_eq!(strengthened.successor.conducting_channel_population(), 52);
        assert_eq!(
            strengthened.successor.transition_work_phase(),
            ExactRational::new(1, 2).unwrap()
        );
        assert_eq!(
            strengthened.exported_heat_zeptojoules,
            wide_rational(quantum.checked_mul_unsigned(2).unwrap())
        );
        assert!(strengthened.conductance_changed);
        assert_eq!(
            contact.effective_conductance(&strengthened.successor).unwrap(),
            ExactRational::integer(520)
        );

        let weakened = settle_contact_local_conductance(
            contact,
            ElectricalContactTransition {
                released_work_zeptojoules: wide_rational(half_quantum),
                exported_heat_zeptojoules: wide_rational(half_quantum),
                conductance_changed: false,
                ..strengthened
            },
            LocalGradientDirection::PassiveReturn,
            LocalGradientDirection::Quiescent,
        )
        .unwrap();
        assert_eq!(weakened.successor.conducting_channel_population(), 51);
        assert_eq!(contact.effective_conductance(&weakened.successor).unwrap(), ExactRational::integer(510));
    }

    #[test]
    fn mature_contact_work_retains_an_exact_bounded_transition_phase() {
        let contact = ElectricalContactAnatomy::new(
            0,
            1,
            ExactRational::integer(500),
            2,
        )
        .unwrap();
        let work = BigRational::new(
            BigInt::parse_bytes(
                b"240649705228216893057568596195456040809",
                10,
            )
            .unwrap(),
            BigInt::parse_bytes(
                b"14651898759795200000000000000000000000",
                10,
            )
            .unwrap(),
        );
        let settled = settle_contact_local_conductance(
            contact,
            ElectricalContactTransition {
                successor: ElectricalContactState::genesis(contact),
                outward_current_from_left_picoamperes: ExactRational::integer(1),
                outward_elementary_charges_from_left: 1,
                released_work_zeptojoules: work,
                exported_heat_zeptojoules: BigRational::zero(),
                conductance_changed: false,
            },
            LocalGradientDirection::ActivePump,
            LocalGradientDirection::Quiescent,
        )
        .unwrap();
        assert_eq!(settled.successor.conducting_channel_population(), 50);
        assert_eq!(
            settled.successor.transition_work_phase(),
            ExactRational::new(
                300_403_463_789_644_672_920_087_781_277,
                384_612_342_444_624_000_000_000_000_000,
            )
            .unwrap()
        );
        assert_eq!(settled.exported_heat_zeptojoules, BigRational::zero());
    }

    #[test]
    fn three_contacts_settle_independently_and_opposing_directions_tie() {
        let contacts = [
            ElectricalContactAnatomy::new(0, 1, ExactRational::integer(500), 4).unwrap(),
            ElectricalContactAnatomy::new(1, 2, ExactRational::integer(500), 4).unwrap(),
            ElectricalContactAnatomy::new(2, 3, ExactRational::integer(500), 4).unwrap(),
        ];
        let quantum = contacts[0].transition_work_quantum_zeptojoules();
        let first = settle_contact_local_conductance(
            contacts[0],
            released_transition(contacts[0], quantum),
            LocalGradientDirection::ActivePump,
            LocalGradientDirection::Quiescent,
        )
        .unwrap();
        let tied_work = quantum.checked_mul_unsigned(2).unwrap();
        let tied = settle_contact_local_conductance(
            contacts[1],
            released_transition(contacts[1], tied_work),
            LocalGradientDirection::ActivePump,
            LocalGradientDirection::PassiveReturn,
        )
        .unwrap();
        let third_work = quantum.checked_mul_unsigned(3).unwrap();
        let third = settle_contact_local_conductance(
            contacts[2],
            released_transition(contacts[2], third_work),
            LocalGradientDirection::PassiveReturn,
            LocalGradientDirection::Quiescent,
        )
        .unwrap();
        assert_eq!(first.successor.conducting_channel_population(), 51);
        assert_eq!(tied.successor.conducting_channel_population(), 50);
        assert_eq!(third.successor.conducting_channel_population(), 47);
        assert_eq!(first.exported_heat_zeptojoules, wide_rational(quantum));
        assert_eq!(tied.exported_heat_zeptojoules, wide_rational(tied_work));
        assert_eq!(third.exported_heat_zeptojoules, wide_rational(third_work));
        assert!(!tied.conductance_changed);
    }

    /// A living body's retained charge lives at contact INDICES.  Appending
    /// must therefore leave every existing index, endpoint, conductance and
    /// unresolved carrier phase exactly where it was.
    #[test]
    fn appended_contacts_leave_every_existing_contact_and_phase_untouched() {
        let anatomy = SparseElectricalAnatomy::new(
            4,
            vec![
                ElectricalContactAnatomy::new(0, 1, ExactRational::integer(500), 4).unwrap(),
                ElectricalContactAnatomy::new(1, 2, ExactRational::integer(500), 4).unwrap(),
            ],
        )
        .unwrap();
        // A body that has conducted: both existing contacts carry a real
        // unresolved sub-carrier phase, not the rest state.
        let lived = SparseElectricalState::from_contact_states(
            &anatomy,
            vec![
                ElectricalContactState::from_legacy_carrier_phase(
                    anatomy.contacts[0],
                    ChargeCarrierPhase::new(3, 7).unwrap(),
                ),
                ElectricalContactState::from_legacy_carrier_phase(
                    anatomy.contacts[1],
                    ChargeCarrierPhase::new(-2, 5).unwrap(),
                ),
            ],
        )
        .unwrap();
        let grown = anatomy
            .append_contacts(vec![
                ElectricalContactAnatomy::new(0, 3, ExactRational::integer(500), 4).unwrap(),
            ])
            .unwrap();
        let grown_state = lived.append_genesis_contacts(&grown).unwrap();
        assert_eq!(grown.contact_count(), 3);
        assert_eq!(
            grown.contact_endpoints().collect::<Vec<_>>(),
            [(0, 1), (1, 2), (0, 3)]
        );
        assert_eq!(grown.contacts[..2], anatomy.contacts[..]);
        assert_eq!(grown.neuron_count(), anatomy.neuron_count());
        assert_eq!(grown_state.contact_states()[..2], lived.contact_states()[..]);
        assert_eq!(
            grown_state.contact_states()[2],
            ElectricalContactState::genesis(grown.contacts[2])
        );
    }

    /// Determinism: the same authorship on the same body produces the same
    /// bytes, and a pre-growth body still encodes byte-identically.
    #[test]
    fn appending_is_deterministic_and_pre_growth_receipts_do_not_drift() {
        let anatomy = SparseElectricalAnatomy::new(
            3,
            vec![
                ElectricalContactAnatomy::new(0, 1, ExactRational::integer(500), 3).unwrap(),
                ElectricalContactAnatomy::new(1, 2, ExactRational::integer(500), 3).unwrap(),
            ],
        )
        .unwrap();
        let state = SparseElectricalState::genesis(&anatomy);
        let before = encode_sparse_electrical_cell(&anatomy, &state).unwrap();
        let addition =
            || vec![ElectricalContactAnatomy::new(0, 2, ExactRational::integer(500), 3).unwrap()];
        let grown = anatomy.append_contacts(addition()).unwrap();
        let grown_again = anatomy.append_contacts(addition()).unwrap();
        assert_eq!(grown, grown_again);
        let grown_state = state.append_genesis_contacts(&grown).unwrap();
        let after = encode_sparse_electrical_cell(&grown, &grown_state).unwrap();
        assert_eq!(
            after,
            encode_sparse_electrical_cell(&grown_again, &grown_state).unwrap()
        );
        // The pre-growth body is untouched and still encodes exactly as it did.
        assert_eq!(encode_sparse_electrical_cell(&anatomy, &state).unwrap(), before);
        // Byte level: magic and neuron count unchanged, the contact count is
        // the only header field that moved, and every existing contact record
        // sits byte-identically at its own offset.
        assert_eq!(after[..16], before[..16]);
        assert_eq!(after[24..before.len()], before[24..]);
        assert_eq!(after.len(), before.len() + SPARSE_ELECTRICAL_CELL_V3_CONTACT_BYTES);
        let (restored_anatomy, restored_state) = decode_sparse_electrical_cell(&after).unwrap();
        assert_eq!(restored_anatomy, grown);
        assert_eq!(restored_state, grown_state);
        let (pre_anatomy, pre_state) = decode_sparse_electrical_cell(&before).unwrap();
        assert_eq!(pre_anatomy, anatomy);
        assert_eq!(pre_state, state);
    }

    /// Re-running an authorship must not quietly double a body's anatomy,
    /// and no addition may name a member the cohort does not have.
    #[test]
    fn appending_refuses_an_already_authored_pair_and_an_absent_member() {
        let anatomy = SparseElectricalAnatomy::new(
            3,
            vec![ElectricalContactAnatomy::new(0, 1, ExactRational::integer(500), 3).unwrap()],
        )
        .unwrap();
        assert_eq!(
            anatomy.append_contacts(vec![ElectricalContactAnatomy::new(
                1,
                0,
                ExactRational::integer(500),
                3
            )
            .unwrap()]),
            Err(SparseElectricalError::ContactAlreadyAuthored)
        );
        let duplicate_in_batch = vec![
            ElectricalContactAnatomy::new(1, 2, ExactRational::integer(500), 3).unwrap(),
            ElectricalContactAnatomy::new(2, 1, ExactRational::integer(500), 3).unwrap(),
        ];
        assert_eq!(
            anatomy.append_contacts(duplicate_in_batch),
            Err(SparseElectricalError::ContactAlreadyAuthored)
        );
        assert_eq!(
            anatomy.append_contacts(vec![ElectricalContactAnatomy::new(
                0,
                3,
                ExactRational::integer(500),
                4
            )
            .unwrap()]),
            Err(SparseElectricalError::InvalidEndpoint)
        );
        // Refusal leaves the body exactly as it was.
        assert_eq!(anatomy.contact_count(), 1);
    }

    #[test]
    fn three_neuron_one_contact_uses_one_predecessor_and_conserves_charge() {
        let contacts =
            vec![ElectricalContactAnatomy::new(0, 1, ExactRational::integer(1), 3).unwrap()];
        let anatomy = SparseElectricalAnatomy::new(3, contacts).unwrap();
        let state = SparseElectricalState::genesis(&anatomy);
        let membranes = vec![
            ElementaryChargeMembraneState::genesis(1_000_000_000),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(0),
        ];
        let settled = settle_sparse_electrical_contacts(
            &anatomy,
            &state,
            &capacitances(3),
            &membranes,
            &[u128::MAX; 8],
            1_000,
        )
        .unwrap();
        assert_eq!(anatomy.neuron_count(), 3);
        assert_eq!(anatomy.contact_count(), 1);
        assert_eq!(settled.transitions.len(), 1);
        assert!(settled.transitions[0].outward_elementary_charges_from_left > 0);
        assert_eq!(
            settled.outward_elementary_charges_by_neuron[0],
            settled.transitions[0].outward_elementary_charges_from_left
        );
        assert_eq!(
            settled.outward_elementary_charges_by_neuron[1],
            -settled.transitions[0].outward_elementary_charges_from_left
        );
        assert_eq!(settled.outward_elementary_charges_by_neuron[2], 0);
        assert_eq!(
            settled
                .outward_elementary_charges_by_neuron
                .iter()
                .sum::<i128>(),
            0
        );
        assert_eq!(
            total_charge(&settled.successor_membranes),
            total_charge(&membranes)
        );
    }

    #[test]
    fn sparse_reached_frontier_preserves_unreached_contacts_and_rejects_open_edges() {
        let contacts =
            vec![ElectricalContactAnatomy::new(0, 1, ExactRational::integer(1), 3).unwrap()];
        let anatomy = SparseElectricalAnatomy::new(3, contacts).unwrap();
        let state = SparseElectricalState::genesis(&anatomy);
        let membranes = vec![
            ElementaryChargeMembraneState::genesis(1_000_000_000),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(0),
        ];

        let isolated = settle_sparse_electrical_transfers_reached(
            &anatomy,
            &state,
            &capacitances(3),
            &membranes,
            &[false, false, true],
            &[u128::MAX; 8],
            1_000,
        )
        .unwrap();
        assert_eq!(isolated.successor_contacts, state);
        assert_eq!(
            isolated.outward_elementary_charges_by_neuron.as_ref(),
            &[0, 0, 0]
        );
        assert_eq!(
            isolated.transitions[0].outward_current_from_left_picoamperes,
            ExactRational::integer(0)
        );

        assert_eq!(
            settle_sparse_electrical_transfers_reached(
                &anatomy,
                &state,
                &capacitances(3),
                &membranes,
                &[true, false, false],
                &[u128::MAX; 8],
                1_000,
            ),
            Err(SparseElectricalError::IncompleteReachedFrontier)
        );

        let closed = settle_sparse_electrical_transfers_reached(
            &anatomy,
            &state,
            &capacitances(3),
            &membranes,
            &[true, true, false],
            &[u128::MAX; 8],
            1_000,
        )
        .unwrap();
        assert!(closed.transitions[0].outward_elementary_charges_from_left > 0);
        assert_eq!(
            closed
                .outward_elementary_charges_by_neuron
                .iter()
                .sum::<i128>(),
            0
        );
    }

    #[test]
    fn four_neuron_sparse_chain_has_fixed_current_state_shape_under_recurrence() {
        let contacts = vec![
            ElectricalContactAnatomy::new(0, 1, ExactRational::integer(1), 4).unwrap(),
            ElectricalContactAnatomy::new(1, 2, ExactRational::integer(1), 4).unwrap(),
            ElectricalContactAnatomy::new(2, 3, ExactRational::integer(1), 4).unwrap(),
        ];
        let anatomy = SparseElectricalAnatomy::new(4, contacts).unwrap();
        let capacitances = capacitances(4);
        let mut contact_state = SparseElectricalState::genesis(&anatomy);
        let mut membranes = vec![
            ElementaryChargeMembraneState::genesis(1_000_000_000),
            ElementaryChargeMembraneState::genesis(500_000_000),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(-500_000_000),
        ];
        let original_total = total_charge(&membranes);
        for _ in 0..100 {
            let settled = settle_sparse_electrical_contacts(
                &anatomy,
                &contact_state,
                &capacitances,
                &membranes,
                &[u128::MAX; 8],
                1_000,
            )
            .unwrap();
            assert_eq!(settled.successor_membranes.len(), 4);
            assert_eq!(settled.successor_contacts.contact_count(), 3);
            assert_eq!(settled.transitions.len(), 3);
            assert_eq!(total_charge(&settled.successor_membranes), original_total);
            membranes = settled.successor_membranes.into_vec();
            contact_state = settled.successor_contacts;
        }
    }

    #[test]
    fn opposing_contact_currents_settle_independently_before_zero_soma_net() {
        let anatomy = SparseElectricalAnatomy::new(
            3,
            vec![
                ElectricalContactAnatomy::new(0, 1, ExactRational::integer(500), 3).unwrap(),
                ElectricalContactAnatomy::new(1, 2, ExactRational::integer(500), 3).unwrap(),
            ],
        )
        .unwrap();
        let predecessor_contacts = SparseElectricalState::genesis(&anatomy);
        let predecessor_membranes = vec![
            ElementaryChargeMembraneState::genesis(1_000_000_000),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(-1_000_000_000),
        ];
        let settled = settle_sparse_electrical_contacts(
            &anatomy,
            &predecessor_contacts,
            &capacitances(3),
            &predecessor_membranes,
            &[u128::MAX; 8],
            1_000,
        )
        .unwrap();

        assert_eq!(settled.transitions.len(), 2);
        assert!(
            settled.transitions[0].outward_elementary_charges_from_left > 0
                && settled.transitions[1].outward_elementary_charges_from_left > 0
        );
        assert_eq!(settled.outward_elementary_charges_by_neuron[1], 0);
        assert_eq!(
            settled.successor_membranes[1].separated_elementary_charges(),
            predecessor_membranes[1].separated_elementary_charges()
        );
        assert_ne!(
            settled.successor_membranes[0],
            predecessor_membranes[0]
        );
        assert_ne!(
            settled.successor_membranes[2],
            predecessor_membranes[2]
        );
        assert_eq!(
            settled
                .outward_elementary_charges_by_neuron
                .iter()
                .sum::<i128>(),
            0
        );
    }

    #[test]
    fn lawful_prior_local_state_concentrates_a_finite_branch_frontier_without_selector() {
        let bias_anatomy = SparseElectricalAnatomy::new(
            2,
            vec![ElectricalContactAnatomy::new(
                0,
                1,
                ExactRational::integer(500),
                2,
            )
            .unwrap()],
        )
        .unwrap();
        let bias_predecessor = vec![
            ElementaryChargeMembraneState::genesis(2_000_000_000),
            ElementaryChargeMembraneState::genesis(0),
        ];
        let bias = settle_sparse_electrical_contacts(
            &bias_anatomy,
            &SparseElectricalState::genesis(&bias_anatomy),
            &capacitances(2),
            &bias_predecessor,
            &[u128::MAX; 2],
            1_000,
        )
        .unwrap();
        assert_eq!(
            bias.successor_membranes[1].separated_elementary_charges(),
            1_000_000_000
        );

        let branch_anatomy = SparseElectricalAnatomy::new(
            3,
            vec![
                ElectricalContactAnatomy::new(0, 1, ExactRational::integer(500), 3).unwrap(),
                ElectricalContactAnatomy::new(0, 2, ExactRational::integer(500), 3).unwrap(),
            ],
        )
        .unwrap();
        let branch_contacts = SparseElectricalState::genesis(&branch_anatomy);
        let unbiased = settle_sparse_electrical_transfers(
            &branch_anatomy,
            &branch_contacts,
            &capacitances(3),
            &[
                ElementaryChargeMembraneState::genesis(1_000_000_000),
                ElementaryChargeMembraneState::genesis(0),
                ElementaryChargeMembraneState::genesis(0),
            ],
            &[2, u128::MAX, u128::MAX],
            1_000,
        )
        .unwrap();
        assert_eq!(
            unbiased
                .transitions
                .iter()
                .map(|transition| transition.outward_elementary_charges_from_left)
                .collect::<Vec<_>>(),
            vec![1, 1]
        );

        let concentrated = settle_sparse_electrical_transfers(
            &branch_anatomy,
            &branch_contacts,
            &capacitances(3),
            &[
                ElementaryChargeMembraneState::genesis(1_000_000_000),
                bias.successor_membranes[1],
                ElementaryChargeMembraneState::genesis(0),
            ],
            &[2, u128::MAX, u128::MAX],
            1_000,
        )
        .unwrap();
        assert_eq!(
            concentrated
                .transitions
                .iter()
                .map(|transition| transition.outward_elementary_charges_from_left)
                .collect::<Vec<_>>(),
            vec![0, 2]
        );
        assert_eq!(
            concentrated
                .outward_elementary_charges_by_neuron
                .iter()
                .sum::<i128>(),
            0
        );
    }

    #[test]
    fn unsupported_legacy_contact_plastic_state_cannot_change_conduction() {
        let anatomy = measured_two_neuron_anatomy();
        let virgin = SparseElectricalState::genesis(&anatomy);
        let legacy_material = PlasticSupportState::from_physical_parts(
            ExactRational::integer(2),
            1,
            ExactRational::integer(0),
        )
        .unwrap();
        let mut legacy_body = Vec::new();
        legacy_body.extend_from_slice(SPARSE_ELECTRICAL_CELL_CODEC_V2_MAGIC);
        push_electrical_usize(&mut legacy_body, anatomy.neuron_count()).unwrap();
        push_electrical_usize(&mut legacy_body, 1).unwrap();
        push_electrical_usize(&mut legacy_body, 0).unwrap();
        push_electrical_usize(&mut legacy_body, 1).unwrap();
        let (conductance_numerator, conductance_denominator) =
            anatomy.contacts[0].conductance_picosiemens().parts();
        legacy_body.extend_from_slice(&conductance_numerator.to_le_bytes());
        legacy_body.extend_from_slice(&conductance_denominator.to_le_bytes());
        legacy_body.extend_from_slice(&0_i128.to_le_bytes());
        legacy_body.extend_from_slice(&1_u128.to_le_bytes());
        let (rest, dissipated, residue) = legacy_material.physical_parts();
        let (rest_numerator, rest_denominator) = rest.parts();
        legacy_body.extend_from_slice(&rest_numerator.to_le_bytes());
        legacy_body.extend_from_slice(&rest_denominator.to_le_bytes());
        legacy_body.extend_from_slice(&dissipated.to_le_bytes());
        let (residue_numerator, residue_denominator) = residue.parts();
        legacy_body.extend_from_slice(&residue_numerator.to_le_bytes());
        legacy_body.extend_from_slice(&residue_denominator.to_le_bytes());
        let (restored_anatomy, legacy) = decode_sparse_electrical_cell(&legacy_body).unwrap();
        assert_eq!(restored_anatomy, anatomy);
        assert_eq!(
            encode_sparse_electrical_cell_v2(&restored_anatomy, &legacy).unwrap(),
            legacy_body
        );
        assert_eq!(legacy.contact_states()[0].conducting_channel_population(), 50);
        assert_eq!(
            legacy.contact_states()[0].transition_work_phase(),
            ExactRational::integer(0)
        );
        let membranes = vec![
            ElementaryChargeMembraneState::genesis(1_000_000_000),
            ElementaryChargeMembraneState::genesis(0),
        ];
        let virgin_transition = settle_sparse_electrical_contacts(
            &anatomy,
            &virgin,
            &measured_capacitances(),
            &membranes,
            &[u128::MAX; 8],
            1_000,
        )
        .unwrap();
        let legacy_transition = settle_sparse_electrical_contacts(
            &anatomy,
            &legacy,
            &measured_capacitances(),
            &membranes,
            &[u128::MAX; 8],
            1_000,
        )
        .unwrap();

        assert_eq!(
            legacy_transition.transitions[0].outward_current_from_left_picoamperes,
            virgin_transition.transitions[0].outward_current_from_left_picoamperes
        );
        assert_eq!(
            legacy_transition.transitions[0].outward_elementary_charges_from_left,
            virgin_transition.transitions[0].outward_elementary_charges_from_left
        );
        assert_eq!(
            legacy_transition.successor_contacts.contact_states()[0]
                .legacy_plastic_compatibility_state(),
            legacy_material
        );
    }

    /// The exact anatomy of the measured obstruction: neuron capacitance
    /// 1 pF, one authored contact at 500 pS, settled on 1 ms intervals.
    fn measured_two_neuron_anatomy() -> SparseElectricalAnatomy {
        SparseElectricalAnatomy::new(
            2,
            vec![
                ElectricalContactAnatomy::new(0, 1, ExactRational::integer(500), 2).unwrap(),
            ],
        )
        .unwrap()
    }

    fn measured_capacitances() -> Vec<MembraneCapacitance> {
        capacitances(2)
    }

    fn run_measured_pair(
        left_charges: i128,
        right_charges: i128,
        intervals: usize,
    ) -> (Vec<ElementaryChargeMembraneState>, SparseElectricalState, bool) {
        let anatomy = measured_two_neuron_anatomy();
        let capacitances = measured_capacitances();
        let mut contacts = SparseElectricalState::genesis(&anatomy);
        let mut membranes = vec![
            ElementaryChargeMembraneState::genesis(left_charges),
            ElementaryChargeMembraneState::genesis(right_charges),
        ];
        let mut any_charge_moved_after_settling = false;
        let mut settled_at: Option<usize> = None;
        for index in 0..intervals {
            let settled = settle_sparse_electrical_contacts(
                &anatomy,
                &contacts,
                &capacitances,
                &membranes,
                &[u128::MAX; 8],
                1_000,
            )
            .unwrap();
            let moved = settled.transitions[0].outward_elementary_charges_from_left != 0;
            let state_changed = settled.successor_contacts != contacts
                || settled.successor_membranes.as_ref() != membranes.as_slice();
            if settled_at.is_some() && moved {
                any_charge_moved_after_settling = true;
            }
            if !state_changed && settled_at.is_none() {
                settled_at = Some(index);
            }
            membranes = settled.successor_membranes.into_vec();
            contacts = settled.successor_contacts;
        }
        (membranes, contacts, any_charge_moved_after_settling)
    }

    fn charges(membranes: &[ElementaryChargeMembraneState]) -> Vec<i128> {
        membranes
            .iter()
            .map(|membrane| membrane.separated_elementary_charges())
            .collect()
    }

    #[test]
    fn energy_descent_condition_is_exact_and_refuses_ties_and_increases() {
        // Stored energy of a node is q^2/(2C) in the existing unit system.
        // With C = 1 pF on both sides the bracket is exactly
        // (n^2 - 2 n q_left) + (n^2 + 2 n q_right).
        let unit = MembraneCapacitance::new(ExactRational::integer(1)).unwrap();
        let left = ContactEndpoint {
            potential_millivolts: ExactRational::integer(0),
            separated_elementary_charges: -12,
            capacitance: unit,
            available_carriers: u128::MAX,
        };
        let right = ContactEndpoint {
            potential_millivolts: ExactRational::integer(0),
            separated_elementary_charges: -11,
            capacitance: unit,
            available_carriers: u128::MAX,
        };
        // The measured oscillation step: (-12,-11) -> (-11,-12).  Stored
        // energy is exactly equal (144+121 == 121+144): a TIE, refused.
        assert!(!stored_energy_strictly_decreases(left, right, -1).unwrap());
        // The reverse step is an increase, also refused.
        assert!(!stored_energy_strictly_decreases(left, right, 1).unwrap());
        // An even imbalance descends by exactly 2 (in units of e^2/2):
        // (-12,-10) -> (-11,-11) is 244 -> 242.
        let even_right = ContactEndpoint {
            separated_elementary_charges: -10,
            ..right
        };
        assert!(stored_energy_strictly_decreases(left, even_right, -1).unwrap());
        // Overshooting the equalization point is refused: two charges would
        // take (-12,-10) to (-10,-12), exactly the same stored energy.
        assert!(!stored_energy_strictly_decreases(left, even_right, -2).unwrap());
        // Three charges would raise it; refused.
        assert!(!stored_energy_strictly_decreases(left, even_right, -3).unwrap());
        // Unequal capacitance is honoured exactly: with C_right = 4 pF the
        // equalization point moves, so a single charge from the higher
        // potential still descends.
        let soft_right = ContactEndpoint {
            capacitance: MembraneCapacitance::new(ExactRational::integer(4)).unwrap(),
            separated_elementary_charges: 0,
            ..right
        };
        let charged_left = ContactEndpoint {
            separated_elementary_charges: 1,
            ..left
        };
        assert!(stored_energy_strictly_decreases(charged_left, soft_right, 1).unwrap());
        assert!(!stored_energy_strictly_decreases(charged_left, soft_right, -1).unwrap());
    }

    #[test]
    fn measured_odd_imbalance_oscillation_terminates_with_zero_lawful_moves() {
        // MEASURED BEFORE the ratified energy-descent law, this exact
        // anatomy and state (-12, -11) produced a permanent +1/-1 limit
        // cycle: one charge crossed every two intervals, forever, so the
        // contact was electrically active for ever and no experience could
        // settle.  AFTER the law the pair rests at its one-charge residual
        // with zero lawful moves remaining.
        let (membranes, contacts, moved_after_settling) = run_measured_pair(-12, -11, 512);
        assert_eq!(charges(&membranes), vec![-12, -11]);
        assert_eq!(contacts, SparseElectricalState::genesis(&measured_two_neuron_anatomy()));
        assert!(!moved_after_settling);

        // No lawful move remains in either direction, from either resting
        // orientation of the same odd imbalance.
        let anatomy = measured_two_neuron_anatomy();
        let capacitances = measured_capacitances();
        for pair in [(-12_i128, -11_i128), (-11, -12), (0, 1), (7, 6)] {
            let membranes = vec![
                ElementaryChargeMembraneState::genesis(pair.0),
                ElementaryChargeMembraneState::genesis(pair.1),
            ];
            let settled = settle_sparse_electrical_contacts(
                &anatomy,
                &SparseElectricalState::genesis(&anatomy),
                &capacitances,
                &membranes,
                &[u128::MAX; 8],
                1_000,
            )
            .unwrap();
            assert_eq!(settled.transitions[0].outward_elementary_charges_from_left, 0);
            assert_eq!(
                settled.transitions[0].outward_current_from_left_picoamperes,
                ExactRational::integer(0)
            );
            assert_eq!(settled.successor_membranes.as_ref(), membranes.as_slice());
            assert_eq!(
                settled.successor_contacts,
                SparseElectricalState::genesis(&anatomy)
            );
        }
    }

    #[test]
    fn even_imbalance_settles_exactly_to_zero_current_and_odd_rests_at_one_charge() {
        // Even difference: exact settlement, zero residual, zero current.
        let (membranes, contacts, moved_after_settling) = run_measured_pair(-12, -10, 64);
        assert_eq!(charges(&membranes), vec![-11, -11]);
        assert_eq!(contacts, SparseElectricalState::genesis(&measured_two_neuron_anatomy()));
        assert!(!moved_after_settling);

        // A larger even difference also reaches exact equality.
        let (membranes, _, _) = run_measured_pair(1_000, 0, 4_096);
        assert_eq!(charges(&membranes), vec![500, 500]);

        // Odd difference: rests at exactly one elementary charge of residual
        // imbalance — a physical resting potential, not a limit cycle.
        let (membranes, _, moved_after_settling) = run_measured_pair(1_001, 0, 4_096);
        let resting = charges(&membranes);
        assert_eq!(resting[0] + resting[1], 1_001);
        assert_eq!((resting[0] - resting[1]).abs(), 1);
        assert!(!moved_after_settling);
    }

    #[test]
    fn energy_descent_conserves_charge_exactly_and_never_raises_cohort_energy() {
        // Stored cohort energy sum(q_i^2 / (2 C_i)) with equal capacitance is
        // proportional to sum(q_i^2); it must never rise, and total charge
        // must be exactly conserved, along a connected chain.
        let contacts = vec![
            ElectricalContactAnatomy::new(0, 1, ExactRational::integer(500), 4).unwrap(),
            ElectricalContactAnatomy::new(1, 2, ExactRational::integer(500), 4).unwrap(),
            ElectricalContactAnatomy::new(2, 3, ExactRational::integer(500), 4).unwrap(),
        ];
        let anatomy = SparseElectricalAnatomy::new(4, contacts).unwrap();
        let capacitances = capacitances(4);
        let mut contact_state = SparseElectricalState::genesis(&anatomy);
        let mut membranes = vec![
            ElementaryChargeMembraneState::genesis(1_000),
            ElementaryChargeMembraneState::genesis(-7),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(-501),
        ];
        let conserved = total_charge(&membranes);
        let mut energy = charges(&membranes)
            .into_iter()
            .map(|charge| charge * charge)
            .sum::<i128>();
        let mut quiescent_from: Option<usize> = None;
        for index in 0..4_096 {
            let settled = settle_sparse_electrical_contacts(
                &anatomy,
                &contact_state,
                &capacitances,
                &membranes,
                &[u128::MAX; 8],
                1_000,
            )
            .unwrap();
            assert_eq!(total_charge(&settled.successor_membranes), conserved);
            let successor_energy = charges(&settled.successor_membranes)
                .into_iter()
                .map(|charge| charge * charge)
                .sum::<i128>();
            assert!(successor_energy <= energy);
            let unchanged = settled.successor_contacts == contact_state
                && settled.successor_membranes.as_ref() == membranes.as_slice();
            if unchanged {
                quiescent_from.get_or_insert(index);
            } else {
                assert!(
                    quiescent_from.is_none(),
                    "a rested chain moved again at interval {index}"
                );
            }
            energy = successor_energy;
            membranes = settled.successor_membranes.into_vec();
            contact_state = settled.successor_contacts;
        }
        assert!(quiescent_from.is_some());
        // Every remaining imbalance is at most one elementary charge.
        let resting = charges(&membranes);
        for pair in resting.windows(2) {
            assert!((pair[0] - pair[1]).abs() <= 1);
        }
        assert_eq!(resting.into_iter().sum::<i128>(), conserved);
    }

    #[test]
    fn absent_or_invalid_physical_contact_is_refused_without_topology_invention() {
        assert_eq!(
            ElectricalContactAnatomy::new(0, 0, ExactRational::integer(1), 1),
            Err(SparseElectricalError::InvalidEndpoint)
        );
        assert_eq!(
            ElectricalContactAnatomy::new(0, 1, ExactRational::integer(0), 2),
            Err(SparseElectricalError::NonPositiveConductance)
        );
    }

    #[test]
    fn sparse_contact_anatomy_and_phase_cold_restore_exactly() {
        let contacts = vec![
            ElectricalContactAnatomy::new(0, 1, ExactRational::new(3, 2).unwrap(), 3).unwrap(),
            ElectricalContactAnatomy::new(1, 2, ExactRational::new(5, 4).unwrap(), 3).unwrap(),
        ];
        let anatomy = SparseElectricalAnatomy::new(3, contacts).unwrap();
        let retained_phase = ExactRational::new(1, 2).unwrap();
        let state = SparseElectricalState::from_contact_states(
            &anatomy,
            vec![
                ElectricalContactState::from_channel_parts(
                    anatomy.contacts[0],
                    ChargeCarrierPhase::new(1, 3).unwrap(),
                    51,
                    retained_phase,
                )
                .unwrap(),
                ElectricalContactState::from_legacy_carrier_phase(
                    anatomy.contacts[1],
                    ChargeCarrierPhase::new(-2, 7).unwrap(),
                ),
            ],
        )
        .unwrap();
        let encoded = encode_sparse_electrical_cell(&anatomy, &state).unwrap();
        let (restored_anatomy, restored_state) = decode_sparse_electrical_cell(&encoded).unwrap();
        assert_eq!(restored_anatomy, anatomy);
        assert_eq!(restored_state, state);
        assert_eq!(
            encode_sparse_electrical_cell(&restored_anatomy, &restored_state).unwrap(),
            encoded
        );

        let mut impossible = Vec::new();
        impossible.extend_from_slice(SPARSE_ELECTRICAL_CELL_CODEC_MAGIC);
        impossible.extend_from_slice(&3_u64.to_le_bytes());
        impossible.extend_from_slice(&u64::MAX.to_le_bytes());
        assert_eq!(
            decode_sparse_electrical_cell(&impossible),
            Err(SparseElectricalError::ArithmeticWidth)
        );
    }
}
