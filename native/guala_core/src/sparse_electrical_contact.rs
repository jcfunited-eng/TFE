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
use rayon::prelude::*;

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
    // This is a transient comparison, not resident state.  A mature membrane
    // may lawfully hold an i128 charge while the exact q² and 2nq terms need
    // more than i128 during the comparison.  Keeping those intermediate
    // products in fixed width made a lawful local cascade fail merely because
    // its stored charge had matured.  Widen only the temporary arithmetic;
    // no persisted coordinate or transfer is widened or approximated.
    let transfer = BigInt::from(transferred_from_left);
    let squared = &transfer * &transfer;
    let doubled = &transfer * BigInt::from(2_u8);
    let left_numerator = &squared
        - &doubled * BigInt::from(left.separated_elementary_charges);
    let right_numerator = squared
        + doubled * BigInt::from(right.separated_elementary_charges);
    let bracket = BigRational::from_integer(left_numerator)
        / wide_rational(left.capacitance.picofarads())
        + BigRational::from_integer(right_numerator)
            / wide_rational(right.capacitance.picofarads());
    Ok(bracket.is_negative())
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


/// Read-only standing-current authority for scheduling.
///
/// Returns `Some(current)` exactly when the standing conditions permit an
/// eventual whole-carrier transfer under the mounted settlement law: a
/// nonzero Ohmic drive, strict electrostatic-energy descent for one
/// elementary charge in the driven direction, and at least one available
/// descending sender carrier within the lawful maximum. A contact resting
/// on an odd residual imbalance, or with an empty sender reservoir, answers
/// `None` — it can never cross while sleeping, exactly as settlement would
/// refuse it every clock. While a permitted contact sleeps, each clock's
/// settlement would integrate phase at the unbounded requested current
/// (zero whole charges never trip the carrier clamp), so the returned raw
/// current is the exact sleeping integration rate. Read-only: no state is
/// touched, and this is the single authority the restore rebuild may use.
#[allow(clippy::too_many_arguments)]
pub(crate) fn standing_contact_current(
    anatomy: ElectricalContactAnatomy,
    state: &ElectricalContactState,
    left_potential: ExactRational,
    left_charges: i128,
    left_capacitance: MembraneCapacitance,
    left_available: u128,
    right_potential: ExactRational,
    right_charges: i128,
    right_capacitance: MembraneCapacitance,
    right_available: u128,
) -> Result<Option<ExactRational>, SparseElectricalError> {
    let potential_difference = left_potential.checked_sub(right_potential)?;
    let current = anatomy
        .effective_conductance(state)?
        .checked_mul(potential_difference)?
        .checked_div_unsigned(PICOSIEMENS_MILLIVOLTS_PER_PICOAMPERE)?;
    let driven_direction = i128::from(current.parts().0.signum());
    if driven_direction == 0 {
        return Ok(None);
    }
    let left = ContactEndpoint {
        potential_millivolts: left_potential,
        separated_elementary_charges: left_charges,
        capacitance: left_capacitance,
        available_carriers: left_available,
    };
    let right = ContactEndpoint {
        potential_millivolts: right_potential,
        separated_elementary_charges: right_charges,
        capacitance: right_capacitance,
        available_carriers: right_available,
    };
    if !stored_energy_strictly_decreases(left, right, driven_direction)? {
        return Ok(None);
    }
    let maximum_descending =
        maximum_energy_descending_carriers(left, right, driven_direction)?;
    let sender_reserve = if driven_direction > 0 {
        left.available_carriers
    } else {
        right.available_carriers
    };
    if maximum_descending.min(sender_reserve) == 0 {
        return Ok(None);
    }
    Ok(Some(current))
}

/// Exact fixed-width settlement of one contact: the same law as
/// ``settle_contact`` evaluated in 256-bit machine arithmetic. Returns
/// ``None`` whenever any width gate fails, and the caller runs the
/// arbitrary-precision path; a returned transition is byte-identical to
/// that path's result by construction and by the differential test below.
fn settle_contact_fast(
    anatomy: ElectricalContactAnatomy,
    predecessor: &ElectricalContactState,
    left: &ContactEndpoint,
    right: &ContactEndpoint,
    interval_microseconds: u32,
) -> Option<ElectricalContactTransition> {
    use crate::fast_charge_math::{SignedRatio256, U256};

    // The exact path refuses a zero-duration active settlement; the fast
    // path must present the identical refusal boundary, so it answers None
    // and lets the exact path speak for every zero-duration call.
    if interval_microseconds == 0 {
        return None;
    }
    // Current numerator/denominator: g_single * population * dV / PSMV.
    let (single_n, single_d) = anatomy.single_channel_conductance_picosiemens.parts();
    let population = predecessor.conducting_channel_population;
    let (vl_n, vl_d) = left.potential_millivolts.parts();
    let (vr_n, vr_d) = right.potential_millivolts.parts();
    let cross_left = U256::mul_u128(vl_n.unsigned_abs(), vr_d);
    let cross_right = U256::mul_u128(vr_n.unsigned_abs(), vl_d);
    let (difference_negative, difference) = match (vl_n < 0, vr_n < 0) {
        (false, false) => match cross_left.cmp(&cross_right) {
            core::cmp::Ordering::Less => (true, cross_right.checked_sub(cross_left)?),
            _ => (false, cross_left.checked_sub(cross_right)?),
        },
        (true, true) => match cross_left.cmp(&cross_right) {
            core::cmp::Ordering::Greater => (true, cross_left.checked_sub(cross_right)?),
            _ => (false, cross_right.checked_sub(cross_left)?),
        },
        (false, true) => (false, cross_left.checked_add(cross_right)?),
        (true, false) => (true, cross_left.checked_add(cross_right)?),
    };
    let conductance_scale = U256::mul_u128(single_n.unsigned_abs(), population).to_u128()?;
    if conductance_scale == 0 || difference.is_zero() {
        return Some(quiescent_contact(predecessor.clone()));
    }
    let current_numerator = difference.checked_mul_small(conductance_scale)?;
    let current_denominator = U256::mul_u128(vl_d, vr_d)
        .checked_mul_small(single_d)?
        .checked_mul_small(PICOSIEMENS_MILLIVOLTS_PER_PICOAMPERE)?;
    let current_negative = difference_negative;

    // Energy-descent test for one elementary charge in the driven direction,
    // and the strict maximum descending transfer, in shared integer scale.
    let driven_from_left = !current_negative;
    let (q_sender, q_receiver, sender_available) = if driven_from_left {
        (
            left.separated_elementary_charges,
            right.separated_elementary_charges,
            left.available_carriers,
        )
    } else {
        (
            right.separated_elementary_charges,
            left.separated_elementary_charges,
            right.available_carriers,
        )
    };
    let (cs_n, cs_d, cr_n, cr_d) = if driven_from_left {
        let (a, b) = left.capacitance.picofarads().parts();
        let (c, d) = right.capacitance.picofarads().parts();
        (a, b, c, d)
    } else {
        let (a, b) = right.capacitance.picofarads().parts();
        let (c, d) = left.capacitance.picofarads().parts();
        (a, b, c, d)
    };
    let cs_n = u128::try_from(cs_n).ok()?;
    let cr_n = u128::try_from(cr_n).ok()?;
    // term_sender = (1 - 2 q_s) * cr_n * cs_d ; term_receiver = (1 + 2 q_r) * cs_n * cr_d
    let signed_term = |base: i128, scale_a: u128, scale_b: u128| -> Option<(bool, U256)> {
        let magnitude = U256::mul_u128(base.unsigned_abs(), scale_a)
            .checked_mul_small(scale_b)?;
        Some((base < 0, magnitude))
    };
    let one_minus = 1_i128.checked_sub(q_sender.checked_mul(2)?)?;
    let one_plus = 1_i128.checked_add(q_receiver.checked_mul(2)?)?;
    let (sender_negative, sender_magnitude) = signed_term(one_minus, cr_n, cs_d)?;
    let (receiver_negative, receiver_magnitude) = signed_term(one_plus, cs_n, cr_d)?;
    let (bracket_negative, bracket_magnitude) = match (sender_negative, receiver_negative) {
        (a, b) if a == b => (a, sender_magnitude.checked_add(receiver_magnitude)?),
        (a, _) => match sender_magnitude.cmp(&receiver_magnitude) {
            core::cmp::Ordering::Less => (
                !a,
                receiver_magnitude.checked_sub(sender_magnitude)?,
            ),
            _ => (a, sender_magnitude.checked_sub(receiver_magnitude)?),
        },
    };
    if !bracket_negative || bracket_magnitude.is_zero() {
        // Even one elementary charge cannot strictly descend: quiescent.
        return Some(quiescent_contact(predecessor.clone()));
    }
    // A = cr_n * cs_d + cs_n * cr_d ; 2*drive*scale = A + |bracket| ; m_max = (2drive - 1) / A
    let a_coefficient = U256::mul_u128(cr_n, cs_d).checked_add(U256::mul_u128(cs_n, cr_d))?;
    let two_drive = a_coefficient.checked_add(bracket_magnitude)?;
    let (m_max, _) = two_drive
        .checked_sub(U256::from_u128(1))?
        .div_rem(a_coefficient)?;
    let m_max = m_max.to_u128()?;
    let available_descending = m_max.min(sender_available);
    if available_descending == 0 {
        return Some(quiescent_contact(predecessor.clone()));
    }

    // Ideal transfer ratio: current * dt * E_d / (MSPM * E_n), reduced once.
    let transfer_numerator = current_numerator
        .checked_mul_small(u128::from(interval_microseconds))?
        .checked_mul_small(FAST_E_DENOMINATOR)?;
    let transfer_denominator = current_denominator
        .checked_mul_small(FAST_MICROSECONDS_PER_MILLISECOND)?
        .checked_mul_small(FAST_E_NUMERATOR)?;
    let reduction = transfer_numerator.gcd(transfer_denominator);
    let (transfer_numerator, _) = transfer_numerator.div_rem(reduction)?;
    let (transfer_denominator, _) = transfer_denominator.div_rem(reduction)?;
    let transfer = SignedRatio256 {
        negative: current_negative,
        numerator: transfer_numerator,
        denominator: transfer_denominator,
    };
    let (phase_n, phase_d) = predecessor.carrier_phase.parts();
    let phase = SignedRatio256::from_i128_ratio(phase_n, phase_d);
    let accumulated = transfer.checked_add(phase)?;
    let (requested_whole, _) = accumulated.trunc_rem()?;

    let (bounded_negative, bounded_numerator, bounded_denominator, final_accumulated) =
        if requested_whole.unsigned_abs() <= available_descending {
            (
                current_negative,
                current_numerator,
                current_denominator,
                accumulated,
            )
        } else {
            // Clamp to the exact inverse current for the available transfer,
            // then integrate again with the existing phase, as the law does.
            let clamped = available_descending;
            let clamped_negative = requested_whole < 0;
            let numerator = U256::mul_u128(clamped, FAST_E_NUMERATOR)
                .checked_mul_small(FAST_MICROSECONDS_PER_MILLISECOND)?;
            let denominator = U256::mul_u128(
                u128::from(interval_microseconds),
                FAST_E_DENOMINATOR,
            );
            let reduction = numerator.gcd(denominator);
            let (numerator, _) = numerator.div_rem(reduction)?;
            let (denominator, _) = denominator.div_rem(reduction)?;
            let clamped_transfer = SignedRatio256 {
                negative: clamped_negative,
                numerator: U256::from_u128(clamped),
                denominator: U256::from_u128(1),
            };
            let accumulated = clamped_transfer.checked_add(phase)?;
            (clamped_negative, numerator, denominator, accumulated)
        };
    let (whole, remainder) = final_accumulated.trunc_rem()?;

    // The settled whole transfer must itself strictly descend, mirrored from
    // the law's final refusal: bracket(m) = A m^2 - 2 drive m, strict.
    if whole != 0 {
        let magnitude = whole.unsigned_abs();
        let quadratic = a_coefficient
            .checked_mul_small(magnitude)?
            .checked_mul_small(magnitude)?;
        let linear = two_drive.checked_mul_small(magnitude)?;
        let descends = match (whole < 0) == current_negative {
            true => quadratic < linear,
            false => false,
        };
        if !descends {
            return Some(quiescent_contact(predecessor.clone()));
        }
    }

    let (remainder_numerator, remainder_denominator) = remainder.reduced_parts()?;
    let successor_phase =
        ChargeCarrierPhase::new(remainder_numerator, remainder_denominator).ok()?;
    let bounded_current = exact_rational_from_reduced(
        bounded_negative,
        bounded_numerator,
        bounded_denominator,
    )?;
    Some(ElectricalContactTransition {
        successor: ElectricalContactState {
            carrier_phase: successor_phase,
            ..predecessor.clone()
        },
        outward_current_from_left_picoamperes: bounded_current,
        outward_elementary_charges_from_left: whole,
        released_work_zeptojoules: BigRational::zero(),
        exported_heat_zeptojoules: BigRational::zero(),
        conductance_changed: false,
    })
}

const FAST_E_NUMERATOR: u128 = 801_088_317;
const FAST_E_DENOMINATOR: u128 = 5_000_000_000_000;
const FAST_MICROSECONDS_PER_MILLISECOND: u128 = 1_000;

fn exact_rational_from_reduced(
    negative: bool,
    numerator: crate::fast_charge_math::U256,
    denominator: crate::fast_charge_math::U256,
) -> Option<ExactRational> {
    let reduction = numerator.gcd(denominator);
    let (numerator, _) = numerator.div_rem(reduction)?;
    let (denominator, _) = denominator.div_rem(reduction)?;
    let numerator = numerator.to_u128().and_then(|n| i128::try_from(n).ok())?;
    let denominator = denominator
        .to_u128()
        .and_then(|d| i128::try_from(d).ok())?;
    let signed = if negative { numerator.checked_neg()? } else { numerator };
    ExactRational::integer(signed)
        .checked_div(ExactRational::integer(denominator))
        .ok()
}

fn settle_contact(
    anatomy: ElectricalContactAnatomy,
    predecessor: ElectricalContactState,
    left: ContactEndpoint,
    right: ContactEndpoint,
    interval_microseconds: u32,
) -> Result<ElectricalContactTransition, SparseElectricalError> {
    if let Some(transition) =
        settle_contact_fast(anatomy, &predecessor, &left, &right, interval_microseconds)
    {
        return Ok(transition);
    }
    settle_contact_exact(anatomy, predecessor, left, right, interval_microseconds)
}

fn settle_contact_exact(
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
    potentials: &[ExactRational],
) -> Result<Vec<ElectricalContactTransition>, SparseElectricalError> {
    // A neuron's per-contact demands are individually bounded whole-carrier
    // values, but their transient sum across a real fan-out need not fit the
    // width of one resident carrier store.  The sum exists only to derive the
    // exact per-neuron availability fraction, so keep it wide and narrow only
    // each physically allocated contact transfer below.
    let mut demanded_by_sender =
        vec![crate::fast_charge_math::U256::ZERO; anatomy.neuron_count];
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
                .checked_add(crate::fast_charge_math::U256::from_u128(
                    transition.outward_elementary_charges_from_left.unsigned_abs(),
                ))
                .ok_or(SparseElectricalError::ArithmeticWidth)?;
        }
    }

    let transitions = anatomy
        .contacts
        .par_iter()
        .copied()
        .zip(predecessor_contacts.contacts.par_iter().cloned())
        .zip(provisional.into_par_iter())
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
            if total_demand <= crate::fast_charge_math::U256::from_u128(available) {
                return Ok(transition);
            }
            let demand = transition.outward_elementary_charges_from_left.unsigned_abs();
            let (allocated_wide, _) = crate::fast_charge_math::U256::mul_u128(
                demand, available,
            )
            .div_rem(total_demand)
            .ok_or(SparseElectricalError::ArithmeticWidth)?;
            let allocated = allocated_wide
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
    component_energy_descending_transitions(
        anatomy,
        predecessor_contacts,
        capacitances,
        predecessor_membranes,
        available_carriers,
        interval_microseconds,
        transitions,
    )
}

/// Settle simultaneous sparse currents on the exact minimum of each connected
/// electrical component's stored energy along its already-derived flow
/// direction. Pairwise descent alone is insufficient when contacts share a
/// neuron: two lawful pair moves can overshoot one another in the same
/// interval. Disconnected components share no neuron or contact and therefore
/// have no physical authority over one another's settlement. For node outward
/// transfers `d_i`, component energy along scale `lambda` is
/// `E(lambda)=E(0)-2 B lambda+A lambda²`; its physical line minimum is
/// `lambda=B/A`. The full step is retained when it already lies before that
/// minimum. Otherwise only currents in that connected component receive its
/// exact scale.
fn component_energy_descending_transitions(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    available_carriers: &[u128],
    interval_microseconds: u32,
    mut transitions: Vec<ElectricalContactTransition>,
) -> Result<Vec<ElectricalContactTransition>, SparseElectricalError> {
    for component_contacts in connected_contact_components(anatomy, &transitions)? {
        settle_energy_component(
            anatomy,
            predecessor_contacts,
            capacitances,
            predecessor_membranes,
            available_carriers,
            interval_microseconds,
            &component_contacts,
            &mut transitions,
        )?;
    }
    Ok(transitions)
}

#[allow(clippy::too_many_arguments)]
fn settle_energy_component(
    anatomy: &SparseElectricalAnatomy,
    predecessor_contacts: &SparseElectricalState,
    capacitances: &[MembraneCapacitance],
    predecessor_membranes: &[ElementaryChargeMembraneState],
    available_carriers: &[u128],
    interval_microseconds: u32,
    component_contacts: &[usize],
    transitions: &mut [ElectricalContactTransition],
) -> Result<(), SparseElectricalError> {
    let (component_neurons, outward) =
        outward_by_contact_indices(anatomy, transitions, component_contacts)?;
    // Per-neuron integer pre-scan with the exact wide path as fallback.
    // descent - curvature = sum over neurons of w(q - w)/C with C > 0, and
    // descent = sum of qw/C. When every neuron's w(q - w) is nonnegative the
    // sum cannot be negative, so descent >= curvature and the component
    // keeps its transitions unchanged (the same early return the exact
    // arithmetic below reaches); when additionally some qw > 0, descent > 0.
    // Only a neuron that moved more carriers than its separated charge — a
    // genuine overshoot candidate — forces the exact common-denominator
    // computation. Machine integers with checked widening; any overflow
    // falls through to the exact path.
    {
        let mut all_within_charge = true;
        let mut any_positive_descent_term = false;
        for (neuron_index, node_outward) in component_neurons.iter().zip(&outward) {
            let Some(w) = node_outward.to_i128() else {
                all_within_charge = false;
                break;
            };
            let q = predecessor_membranes[*neuron_index].separated_elementary_charges();
            let Some(q_minus_w) = q.checked_sub(w) else {
                all_within_charge = false;
                break;
            };
            let Some(product) = w.checked_mul(q_minus_w) else {
                all_within_charge = false;
                break;
            };
            if product < 0 {
                all_within_charge = false;
                break;
            }
            match w.checked_mul(q) {
                Some(qw) if qw > 0 => any_positive_descent_term = true,
                Some(_) => {}
                None => {
                    all_within_charge = false;
                    break;
                }
            }
        }
        if all_within_charge && any_positive_descent_term {
            return Ok(());
        }
    }
    let common_denominator = inverse_capacitance_common_denominator(
        capacitances,
        component_neurons.iter().copied(),
    )?;
    let curvature = inverse_capacitance_sum_numerator(
        capacitances,
        component_neurons.iter().copied(),
        outward.iter().map(|node_outward| node_outward * node_outward),
        &common_denominator,
    )?;
    let descent = inverse_capacitance_sum_numerator(
        capacitances,
        component_neurons.iter().copied(),
        component_neurons
            .iter()
            .zip(&outward)
            .map(|(neuron_index, node_outward)| {
                BigInt::from(
                    predecessor_membranes[*neuron_index].separated_elementary_charges(),
                ) * node_outward
            }),
        &common_denominator,
    )?;
    if curvature.is_zero() {
        return Ok(());
    }
    if descent <= BigInt::from(0_u8) {
        for contact_index in component_contacts {
            transitions[*contact_index] =
                quiescent_contact(predecessor_contacts.contacts[*contact_index].clone());
        }
        return Ok(());
    }
    if descent >= curvature {
        return Ok(());
    }
    for contact_index in component_contacts {
        let contact = anatomy.contacts[*contact_index];
        let predecessor = predecessor_contacts.contacts[*contact_index].clone();
        let transition = &transitions[*contact_index];
            let magnitude = (BigInt::from(
                transition
                    .outward_elementary_charges_from_left
                    .unsigned_abs(),
            ) * &descent)
                / &curvature;
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
                transitions[*contact_index] = quiescent_contact(predecessor);
                continue;
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
                transitions[*contact_index] = quiescent_contact(predecessor);
                continue;
            }
            transitions[*contact_index] = ElectricalContactTransition {
                successor: predecessor,
                outward_current_from_left_picoamperes:
                    exact_current_for_whole_carrier_transfer(carriers, interval_microseconds)?,
                outward_elementary_charges_from_left: carriers,
                released_work_zeptojoules: BigRational::zero(),
                exported_heat_zeptojoules: BigRational::zero(),
                conductance_changed: false,
            };
    }
    let (scaled_component_neurons, scaled_outward) =
        outward_by_contact_indices(anatomy, transitions, component_contacts)?;
    if scaled_component_neurons != component_neurons {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }
    let energy_change = inverse_capacitance_sum_numerator(
        capacitances,
        component_neurons.iter().copied(),
        component_neurons
            .iter()
            .zip(&scaled_outward)
            .map(|(neuron_index, node_outward)| {
                let prior = BigInt::from(
                    predecessor_membranes[*neuron_index].separated_elementary_charges(),
                );
                let successor = &prior - node_outward;
                &successor * &successor - &prior * &prior
            }),
        &common_denominator,
    )?;
    if energy_change < BigInt::from(0_u8) {
        Ok(())
    } else {
        for contact_index in component_contacts {
            transitions[*contact_index] =
                quiescent_contact(predecessor_contacts.contacts[*contact_index].clone());
        }
        Ok(())
    }
}

fn connected_contact_components(
    anatomy: &SparseElectricalAnatomy,
    transitions: &[ElectricalContactTransition],
) -> Result<Vec<Vec<usize>>, SparseElectricalError> {
    fn root(parent: &mut [usize], mut node: usize) -> usize {
        while parent[node] != node {
            parent[node] = parent[parent[node]];
            node = parent[node];
        }
        node
    }

    if transitions.len() != anatomy.contacts.len() {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }
    let mut parent = (0..anatomy.neuron_count).collect::<Vec<_>>();
    for (contact, transition) in anatomy.contacts.iter().zip(transitions) {
        if transition.outward_elementary_charges_from_left == 0 {
            continue;
        }
        let left = root(&mut parent, contact.left_neuron);
        let right = root(&mut parent, contact.right_neuron);
        if left != right {
            parent[right] = left;
        }
    }
    let mut component_by_root = vec![usize::MAX; anatomy.neuron_count];
    let mut components = Vec::<Vec<usize>>::new();
    for (contact_index, (contact, transition)) in
        anatomy.contacts.iter().zip(transitions).enumerate()
    {
        if transition.outward_elementary_charges_from_left == 0 {
            continue;
        }
        let component_root = root(&mut parent, contact.left_neuron);
        let component_index = if component_by_root[component_root] == usize::MAX {
            component_by_root[component_root] = components.len();
            components.push(Vec::new());
            components.len() - 1
        } else {
            component_by_root[component_root]
        };
        components[component_index].push(contact_index);
    }
    Ok(components)
}

fn outward_by_contact_indices(
    anatomy: &SparseElectricalAnatomy,
    transitions: &[ElectricalContactTransition],
    contact_indices: &[usize],
) -> Result<(Vec<usize>, Vec<BigInt>), SparseElectricalError> {
    let mut neuron_indices = Vec::with_capacity(contact_indices.len().saturating_mul(2));
    for contact_index in contact_indices {
        let contact = anatomy
            .contacts
            .get(*contact_index)
            .ok_or(SparseElectricalError::AnatomyStateWidth)?;
        neuron_indices.extend([contact.left_neuron, contact.right_neuron]);
    }
    neuron_indices.sort_unstable();
    neuron_indices.dedup();
    let mut outward = vec![BigInt::from(0_u8); neuron_indices.len()];
    for contact_index in contact_indices {
        let contact = anatomy
            .contacts
            .get(*contact_index)
            .ok_or(SparseElectricalError::AnatomyStateWidth)?;
        let transition = transitions
            .get(*contact_index)
            .ok_or(SparseElectricalError::AnatomyStateWidth)?;
        let transferred = BigInt::from(transition.outward_elementary_charges_from_left);
        let left = neuron_indices
            .binary_search(&contact.left_neuron)
            .map_err(|_| SparseElectricalError::AnatomyStateWidth)?;
        let right = neuron_indices
            .binary_search(&contact.right_neuron)
            .map_err(|_| SparseElectricalError::AnatomyStateWidth)?;
        outward[left] += &transferred;
        outward[right] -= transferred;
    }
    Ok((neuron_indices, outward))
}

fn settled_outward_by_neuron(
    anatomy: &SparseElectricalAnatomy,
    transitions: &[ElectricalContactTransition],
) -> Result<Box<[i128]>, SparseElectricalError> {
    if anatomy.contacts.len() != transitions.len() {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }
    let mut outward = vec![BigInt::from(0_u8); anatomy.neuron_count];
    for (contact, transition) in anatomy.contacts.iter().zip(transitions) {
        let transferred = BigInt::from(transition.outward_elementary_charges_from_left);
        outward[contact.left_neuron] += &transferred;
        outward[contact.right_neuron] -= transferred;
    }
    if outward.iter().fold(BigInt::from(0_u8), |sum, value| sum + value)
        != BigInt::from(0_u8)
    {
        return Err(SparseElectricalError::ArithmeticWidth);
    }
    outward
        .into_iter()
        .map(|value| {
            value
                .to_i128()
                .ok_or(SparseElectricalError::ArithmeticWidth)
        })
        .collect::<Result<Vec<_>, _>>()
        .map(Vec::into_boxed_slice)
}

fn positive_bigint_gcd(mut left: BigInt, mut right: BigInt) -> BigInt {
    while !right.is_zero() {
        let remainder = &left % &right;
        left = right;
        right = remainder;
    }
    left
}

/// Return the one exact common denominator for the supplied pathway members.
/// A capacitance is the exact rational `n/d`, so each inverse-capacitance term
/// has denominator `n`. Every member of the connected pathway participates in
/// this denominator even when its initial net transfer cancels to zero: exact
/// per-contact integer scaling can make that member's final net nonzero.
fn inverse_capacitance_common_denominator<I>(
    capacitances: &[MembraneCapacitance],
    neuron_indices: I,
) -> Result<BigInt, SparseElectricalError>
where
    I: IntoIterator<Item = usize>,
{
    let mut common = BigInt::from(1_u8);
    for neuron_index in neuron_indices {
        let capacitance = capacitances
            .get(neuron_index)
            .ok_or(SparseElectricalError::AnatomyStateWidth)?;
        let (numerator, _) = capacitance.picofarads().parts();
        if numerator <= 0 {
            return Err(SparseElectricalError::ArithmeticWidth);
        }
        let numerator = BigInt::from(numerator);
        let gcd = positive_bigint_gcd(common.clone(), numerator.clone());
        common = (common / gcd) * numerator;
    }
    Ok(common)
}

fn inverse_capacitance_sum_numerator<I, J>(
    capacitances: &[MembraneCapacitance],
    neuron_indices: I,
    numerators: J,
    common_denominator: &BigInt,
) -> Result<BigInt, SparseElectricalError>
where
    I: IntoIterator<Item = usize>,
    J: IntoIterator<Item = BigInt>,
{
    let mut neuron_indices = neuron_indices.into_iter();
    let mut numerators = numerators.into_iter();
    let mut sum = BigInt::from(0_u8);
    while let Some(neuron_index) = neuron_indices.next() {
        let value = numerators
            .next()
            .ok_or(SparseElectricalError::AnatomyStateWidth)?;
        let capacitance = capacitances
            .get(neuron_index)
            .ok_or(SparseElectricalError::AnatomyStateWidth)?;
        if value.is_zero() {
            continue;
        }
        let (capacitance_numerator, capacitance_denominator) =
            capacitance.picofarads().parts();
        if capacitance_numerator <= 0 {
            return Err(SparseElectricalError::ArithmeticWidth);
        }
        let divisor = BigInt::from(capacitance_numerator);
        if common_denominator % &divisor != BigInt::from(0_u8) {
            return Err(SparseElectricalError::ArithmeticWidth);
        }
        sum += value
            * BigInt::from(capacitance_denominator)
            * (common_denominator / divisor);
    }
    if numerators.next().is_some() || neuron_indices.next().is_some() {
        return Err(SparseElectricalError::AnatomyStateWidth);
    }
    Ok(sum)
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

    /// Replace only the exact resident contacts reached by one settled
    /// interval.  Validate every address before the first write so a malformed
    /// sparse projection cannot partially mutate the resident state.
    pub(crate) fn replace_contact_states(
        &mut self,
        replacements: Vec<(usize, ElectricalContactState)>,
    ) -> Result<(), SparseElectricalError> {
        if replacements
            .iter()
            .any(|(contact_index, _)| *contact_index >= self.contacts.len())
            || replacements
                .windows(2)
                .any(|pair| pair[0].0 >= pair[1].0)
        {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        for (contact_index, successor) in replacements {
            self.contacts[contact_index] = successor;
        }
        Ok(())
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

/// Exact fixed-width form of ``current x potential difference x interval``:
/// the released-work value with the same sign law as the arbitrary-precision
/// expression. ``None`` on any width gate or on a negative product, which the
/// caller's original path then reports exactly as before.
fn fast_released_work_parts(
    current: ExactRational,
    left_potential: ExactRational,
    right_potential: ExactRational,
    interval_microseconds: u32,
) -> Option<(u128, u128)> {
    use crate::fast_charge_math::U256;
    let (i_n, i_d) = current.parts();
    let (vl_n, vl_d) = left_potential.parts();
    let (vr_n, vr_d) = right_potential.parts();
    let cross_left = U256::mul_u128(vl_n.unsigned_abs(), vr_d);
    let cross_right = U256::mul_u128(vr_n.unsigned_abs(), vl_d);
    let (difference_negative, difference) = match (vl_n < 0, vr_n < 0) {
        (false, false) => match cross_left.cmp(&cross_right) {
            core::cmp::Ordering::Less => (true, cross_right.checked_sub(cross_left)?),
            _ => (false, cross_left.checked_sub(cross_right)?),
        },
        (true, true) => match cross_left.cmp(&cross_right) {
            core::cmp::Ordering::Greater => (true, cross_left.checked_sub(cross_right)?),
            _ => (false, cross_right.checked_sub(cross_left)?),
        },
        (false, true) => (false, cross_left.checked_add(cross_right)?),
        (true, false) => (true, cross_left.checked_add(cross_right)?),
    };
    if (i_n < 0) != difference_negative {
        // A negative product is the exact path's own refusal; let it speak.
        return None;
    }
    let numerator = difference
        .to_u128()
        .map(|d| U256::mul_u128(i_n.unsigned_abs(), d))?
        .checked_mul_small(u128::from(interval_microseconds))?;
    let denominator = U256::mul_u128(i_d, vl_d).checked_mul_small(vr_d)?;
    let reduction = numerator.gcd(denominator);
    let (numerator, _) = numerator.div_rem(reduction)?;
    let (denominator, _) = denominator.div_rem(reduction)?;
    Some((numerator.to_u128()?, denominator.to_u128()?))
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
    anatomy
        .contacts
        .par_iter()
        .zip(transitions.par_iter_mut())
        .try_for_each(|(contact, transition)| -> Result<(), SparseElectricalError> {
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
            return Ok(());
        }
        if let Some((numerator, denominator)) = fast_released_work_parts(
            transition.outward_current_from_left_picoamperes,
            potentials_millivolts[contact.left_neuron],
            potentials_millivolts[contact.right_neuron],
            interval_microseconds,
        ) {
            let released = BigRational::new(BigInt::from(numerator), BigInt::from(denominator));
            transition.released_work_zeptojoules = released.clone();
            transition.exported_heat_zeptojoules = released;
            return Ok(());
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
        Ok(())
    })?;
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
        .par_iter()
        .copied()
        .zip(capacitances.par_iter().copied())
        .map(|(membrane, capacitance)| membrane.potential_millivolts(capacitance))
        .collect::<Result<Vec<_>, _>>()?;
    // Every contact reads the same immutable predecessor generation. Settle
    // those independent pair proposals concurrently; the exact shared-sender
    // carrier bound and connected-component energy descent still follow as
    // their single deterministic reconciliation steps.
    let solver_stopwatch = std::time::Instant::now();
    let provisional = anatomy
        .contacts
        .par_iter()
        .copied()
        .zip(predecessor_contacts.contacts.par_iter().cloned())
        .map(|(contact, predecessor)| {
            settle_contact(
                contact,
                predecessor,
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
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    let provisional_wall = solver_stopwatch.elapsed();
    let mut transitions = jointly_carrier_bound_transitions(
        anatomy,
        predecessor_contacts,
        capacitances,
        predecessor_membranes,
        available_carriers,
        interval_microseconds,
        provisional,
        &potentials,
    )?;
    let jointly_wall = solver_stopwatch.elapsed();
    attach_contact_local_released_work(
        anatomy,
        &potentials,
        interval_microseconds,
        &mut transitions,
    )?;
    let attach_wall = solver_stopwatch.elapsed();
    let outward_by_neuron = settled_outward_by_neuron(anatomy, &transitions)?;
    eprintln!(
        "guala-solver-phases provisional_ms={} jointly_ms={} attach_ms={} tail_ms_pending",
        provisional_wall.as_millis(),
        (jointly_wall - provisional_wall).as_millis(),
        (attach_wall - jointly_wall).as_millis(),
    );
    let mut moved_whole = 0usize;
    let mut phase_only = 0usize;
    let mut true_identity = 0usize;
    for (transition, predecessor) in transitions.iter().zip(&predecessor_contacts.contacts) {
        if transition.outward_elementary_charges_from_left != 0 {
            moved_whole += 1;
        } else if transition.successor != *predecessor {
            phase_only += 1;
        } else {
            true_identity += 1;
        }
    }
    let mut sender_flags = vec![false; anatomy.neuron_count];
    for (contact, transition) in anatomy.contacts.iter().zip(&transitions) {
        if transition.outward_elementary_charges_from_left > 0 {
            sender_flags[contact.left_neuron] = true;
        } else if transition.outward_elementary_charges_from_left < 0 {
            sender_flags[contact.right_neuron] = true;
        }
    }
    let senders = sender_flags.iter().filter(|flag| **flag).count();
    let mut approximate_potentials = potentials
        .iter()
        .map(|potential| {
            let (numerator, denominator) = potential.parts();
            numerator as f64 / denominator as f64
        })
        .collect::<Vec<f64>>();
    approximate_potentials.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let quartile = |fraction: f64| {
        approximate_potentials
            [(fraction * (approximate_potentials.len() - 1) as f64) as usize]
    };
    eprintln!(
        "guala-contact-outcomes moved_whole={} phase_only={} true_identity={} senders={} pot_min={:.3} p25={:.3} p50={:.3} p75={:.3} pot_max={:.3}",
        moved_whole, phase_only, true_identity, senders,
        quartile(0.0), quartile(0.25), quartile(0.5), quartile(0.75), quartile(1.0),
    );

    Ok(SparseElectricalTransferSettlement {
        successor_contacts: SparseElectricalState {
            contacts: transitions
                .iter()
                .map(|transition| transition.successor.clone())
                .collect::<Vec<_>>()
                .into_boxed_slice(),
        },
        transitions: transitions.into_boxed_slice(),
        outward_elementary_charges_by_neuron: outward_by_neuron,
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
        &potentials,
    )?;
    attach_contact_local_released_work(
        anatomy,
        &potentials,
        interval_microseconds,
        &mut transitions,
    )?;
    let outward_by_neuron = settled_outward_by_neuron(anatomy, &transitions)?;

    Ok(SparseElectricalTransferSettlement {
        successor_contacts: SparseElectricalState {
            contacts: transitions
                .iter()
                .map(|transition| transition.successor.clone())
                .collect::<Vec<_>>()
                .into_boxed_slice(),
        },
        transitions: transitions.into_boxed_slice(),
        outward_elementary_charges_by_neuron: outward_by_neuron,
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

    #[test]
    fn fast_settlement_matches_exact_settlement_across_grid() {
        let capacitance = |n: i128, d: u128| {
            MembraneCapacitance::new(
                ExactRational::integer(n)
                    .checked_div(ExactRational::integer(d as i128))
                    .unwrap(),
            )
            .unwrap()
        };
        let anatomy = |g_n: i128, g_d: u128, _population: u128| {
            ElectricalContactAnatomy::new(
                0,
                1,
                ExactRational::integer(g_n)
                    .checked_div(ExactRational::integer(g_d as i128))
                    .unwrap(),
                2,
            )
            .unwrap()
        };
        let mut compared = 0_u64;
        let mut fast_answers = 0_u64;
        for q_left in [-1_000_000_007_i128, -7, 0, 3, 981_234_567] {
            for q_right in [-13_i128, 0, 5, 40_000_001] {
                for (cl_n, cl_d, cr_n, cr_d) in
                    [(3_i128, 2_u128, 7_i128, 5_u128), (1, 1, 1, 1), (11, 4, 5, 8)]
                {
                    for (g_n, g_d) in [(1_i128, 2_u128), (500, 1)] {
                        for population in [0_u128, 1, 9] {
                            for (p_n, p_d) in [(0_i128, 1_u128), (1, 3), (-2, 5)] {
                                for (avail_l, avail_r) in [(0_u128, 0_u128), (1, 1), (100, 3)]
                                {
                                    let contact_anatomy = anatomy(g_n, g_d, population.max(1));
                                    let mut state =
                                        ElectricalContactState::from_legacy_carrier_phase(
                                            contact_anatomy,
                                            ChargeCarrierPhase::new(p_n, p_d).unwrap(),
                                        );
                                    state.conducting_channel_population = population;
                                    let cl = capacitance(cl_n, cl_d);
                                    let cr = capacitance(cr_n, cr_d);
                                    let left = ContactEndpoint::new(
                                        potential_from_membrane(q_left, cl),
                                        membrane_with_charge(q_left),
                                        cl,
                                        avail_l,
                                    );
                                    let right = ContactEndpoint::new(
                                        potential_from_membrane(q_right, cr),
                                        membrane_with_charge(q_right),
                                        cr,
                                        avail_r,
                                    );
                                    compared += 1;
                                    let fast = settle_contact_fast(
                                        contact_anatomy,
                                        &state,
                                        &left,
                                        &right,
                                        250_000,
                                    );
                                    let exact = settle_contact_exact(
                                        contact_anatomy,
                                        state.clone(),
                                        left,
                                        right,
                                        250_000,
                                    )
                                    .unwrap();
                                    if let Some(fast) = fast {
                                        fast_answers += 1;
                                        assert_eq!(
                                            fast.successor, exact.successor,
                                            "successor diverged at q=({q_left},{q_right}) c=({cl_n}/{cl_d},{cr_n}/{cr_d}) g={g_n}/{g_d} pop={population} phase={p_n}/{p_d} avail=({avail_l},{avail_r})"
                                        );
                                        assert_eq!(
                                            fast.outward_elementary_charges_from_left,
                                            exact.outward_elementary_charges_from_left,
                                        );
                                        assert_eq!(
                                            fast.outward_current_from_left_picoamperes.parts(),
                                            exact.outward_current_from_left_picoamperes.parts(),
                                        );
                                        assert_eq!(
                                            fast.conductance_changed,
                                            exact.conductance_changed,
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        assert!(compared > 1_000);
        assert!(
            fast_answers * 10 >= compared * 9,
            "fast path answered only {fast_answers} of {compared}"
        );
    }

    fn membrane_with_charge(charges: i128) -> ElementaryChargeMembraneState {
        ElementaryChargeMembraneState::genesis(charges)
    }

    fn potential_from_membrane(
        charges: i128,
        capacitance: MembraneCapacitance,
    ) -> ExactRational {
        membrane_with_charge(charges)
            .potential_millivolts(capacitance)
            .unwrap()
    }
    use super::*;

    fn unit_capacitance() -> MembraneCapacitance {
        MembraneCapacitance::new(ExactRational::integer(1)).unwrap()
    }

    fn standing_fixture_state(
        conductance_denominator: i128,
    ) -> (ElectricalContactAnatomy, ElectricalContactState) {
        let anatomy = ElectricalContactAnatomy::new(
            0,
            1,
            ExactRational::integer(1)
                .checked_div(ExactRational::integer(conductance_denominator))
                .unwrap(),
            2,
        )
        .unwrap();
        let mut state = ElectricalContactState::from_legacy_carrier_phase(
            anatomy,
            ChargeCarrierPhase::zero(),
        );
        state.conducting_channel_population = 1;
        (anatomy, state)
    }

    /// Falsifier 1: a mature odd-charge pair rests with a genuine residual
    /// voltage, yet moving its one elementary charge only mirrors the pair —
    /// stored energy does not strictly descend, so settlement refuses every
    /// clock. The standing authority must answer None (unscheduled), even
    /// though the naive Ohmic current is nonzero. This is exactly the
    /// eternal-false-schedule defect the raw-current rebuild had.
    #[test]
    fn standing_authority_refuses_odd_residual_resting_pair() {
        let (anatomy, state) = standing_fixture_state(100_000);
        let c = unit_capacitance();
        let left_potential = potential_from_membrane(1, c);
        let right_potential = potential_from_membrane(0, c);
        assert!(
            left_potential.checked_sub(right_potential).unwrap().parts().0 != 0,
            "fixture must carry a real residual voltage"
        );
        let standing = standing_contact_current(
            anatomy,
            &state,
            left_potential,
            1,
            c,
            100,
            right_potential,
            0,
            c,
            100,
        )
        .unwrap();
        assert!(standing.is_none(), "resting residual pair must stay unscheduled");
        let oracle = settle_contact(
            anatomy,
            state,
            ContactEndpoint::new(left_potential, membrane_with_charge(1), c, 100),
            ContactEndpoint::new(right_potential, membrane_with_charge(0), c, 100),
            250_000,
        )
        .unwrap();
        assert_eq!(oracle.outward_elementary_charges_from_left, 0);
        assert_eq!(
            oracle.successor.carrier_phase().parts(),
            (0, 1),
            "settlement must hold the resting pair at exact rest"
        );
    }

    /// Falsifier 2: lawful descent exists but the sender reservoir is empty.
    /// Settlement can never move a carrier, so the authority must refuse.
    #[test]
    fn standing_authority_refuses_empty_sender_reservoir() {
        let (anatomy, state) = standing_fixture_state(100_000);
        let c = unit_capacitance();
        let left_potential = potential_from_membrane(10, c);
        let right_potential = potential_from_membrane(0, c);
        let standing = standing_contact_current(
            anatomy,
            &state,
            left_potential,
            10,
            c,
            0,
            right_potential,
            0,
            c,
            100,
        )
        .unwrap();
        assert!(standing.is_none(), "empty sender reservoir must stay unscheduled");
        let flush = settle_contact(
            anatomy,
            state,
            ContactEndpoint::new(left_potential, membrane_with_charge(10), c, 0),
            ContactEndpoint::new(right_potential, membrane_with_charge(0), c, 100),
            250_000,
        )
        .unwrap();
        assert_eq!(flush.outward_elementary_charges_from_left, 0);
    }

    /// Falsifiers 3 and 4 together, for both drive signs: a lawful drive is
    /// scheduled at its exact computed crossing, and that restored due clock
    /// agrees with the real settlement law stepped clock by clock — zero
    /// whole carriers on every clock before the due clock, exactly one whole
    /// carrier in the driven direction on the due clock itself.
    #[test]
    fn standing_authority_due_clock_agrees_with_settlement() {
        for (q_left, q_right, expected_sign) in [(10_i128, 0_i128, 1_i128), (0, 10, -1)] {
            let (anatomy, state) = standing_fixture_state(100);
            let c = unit_capacitance();
            let left_potential = potential_from_membrane(q_left, c);
            let right_potential = potential_from_membrane(q_right, c);
            let standing = standing_contact_current(
                anatomy,
                &state,
                left_potential,
                q_left,
                c,
                100,
                right_potential,
                q_right,
                c,
                100,
            )
            .unwrap()
            .expect("lawful drive must be schedulable");
            assert_eq!(i128::from(standing.parts().0.signum()), expected_sign);
            let due = crate::elementary_charge_transfer::next_whole_carrier_crossing_clocks(
                state.carrier_phase(),
                standing,
                250_000,
            )
            .unwrap()
            .expect("standing drive must cross");
            assert!(
                (2..=100_000).contains(&due),
                "fixture must be multi-clock and steppable, got {due}"
            );
            let left = ContactEndpoint::new(left_potential, membrane_with_charge(q_left), c, 100);
            let right =
                ContactEndpoint::new(right_potential, membrane_with_charge(q_right), c, 100);
            let mut stepped = state;
            for clock in 1..=due {
                let transition =
                    settle_contact(anatomy, stepped, left, right, 250_000).unwrap();
                if clock < due {
                    assert_eq!(
                        transition.outward_elementary_charges_from_left, 0,
                        "no whole carrier may move before the due clock (clock {clock})"
                    );
                } else {
                    assert_eq!(
                        transition.outward_elementary_charges_from_left, expected_sign,
                        "exactly one whole carrier must move on the due clock"
                    );
                }
                stepped = transition.successor;
            }
        }
    }

    fn capacitances(count: usize) -> Vec<MembraneCapacitance> {
        vec![MembraneCapacitance::new(ExactRational::integer(1)).unwrap(); count]
    }

    #[test]
    fn mature_membrane_energy_descent_uses_exact_wide_intermediates() {
        let capacitance = MembraneCapacitance::new(ExactRational::integer(1)).unwrap();
        let mature_charge = i128::MAX / 2;
        let left = ContactEndpoint {
            potential_millivolts: ExactRational::integer(0),
            separated_elementary_charges: mature_charge,
            capacitance,
            available_carriers: u128::MAX,
        };
        let right = ContactEndpoint {
            potential_millivolts: ExactRational::integer(0),
            separated_elementary_charges: -mature_charge,
            capacitance,
            available_carriers: u128::MAX,
        };

        assert!(stored_energy_strictly_decreases(left, right, 2).unwrap());
    }

    #[test]
    fn common_denominator_energy_sum_is_exact_for_distinct_capacitances() {
        let capacitances = [
            MembraneCapacitance::new(ExactRational::integer(1)).unwrap(),
            MembraneCapacitance::new(ExactRational::new(3, 2).unwrap()).unwrap(),
            MembraneCapacitance::new(ExactRational::new(5, 7).unwrap()).unwrap(),
            MembraneCapacitance::new(ExactRational::integer(11)).unwrap(),
        ];
        let values = [BigInt::from(0), BigInt::from(0), BigInt::from(25), BigInt::from(14)];
        let common = inverse_capacitance_common_denominator(
            &capacitances,
            0..capacitances.len(),
        )
        .unwrap();
        assert_eq!(common, BigInt::from(165));
        let actual = BigRational::new(
            inverse_capacitance_sum_numerator(
                &capacitances,
                0..capacitances.len(),
                values.clone(),
                &common,
            )
            .unwrap(),
            common,
        );
        let expected = values
            .into_iter()
            .zip(capacitances)
            .fold(BigRational::from_integer(BigInt::from(0)), |sum, (value, capacitance)| {
                sum + BigRational::from_integer(value)
                    / wide_rational(capacitance.picofarads())
            });
        assert_eq!(actual, expected);
    }

    #[test]
    fn disconnected_pathways_settle_with_independent_exact_energy_scales() {
        let anatomy = SparseElectricalAnatomy::new(
            4,
            vec![
                ElectricalContactAnatomy::new(0, 1, ExactRational::integer(1), 4)
                    .unwrap(),
                ElectricalContactAnatomy::new(2, 3, ExactRational::integer(1), 4)
                    .unwrap(),
            ],
        )
        .unwrap();
        let predecessor = SparseElectricalState::genesis(&anatomy);
        let membranes = [
            ElementaryChargeMembraneState::genesis(101),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(10),
            ElementaryChargeMembraneState::genesis(0),
        ];
        let provisional = vec![
            ElectricalContactTransition {
                successor: predecessor.contacts[0].clone(),
                outward_current_from_left_picoamperes: ExactRational::integer(100),
                outward_elementary_charges_from_left: 100,
                released_work_zeptojoules: BigRational::zero(),
                exported_heat_zeptojoules: BigRational::zero(),
                conductance_changed: false,
            },
            ElectricalContactTransition {
                successor: predecessor.contacts[1].clone(),
                outward_current_from_left_picoamperes: ExactRational::integer(1),
                outward_elementary_charges_from_left: 1,
                released_work_zeptojoules: BigRational::zero(),
                exported_heat_zeptojoules: BigRational::zero(),
                conductance_changed: false,
            },
        ];

        let settled = component_energy_descending_transitions(
            &anatomy,
            &predecessor,
            &capacitances(4),
            &membranes,
            &[u128::MAX; 4],
            1_000,
            provisional,
        )
        .unwrap();

        // The first pair is past its line minimum and is reduced locally.
        assert_eq!(settled[0].outward_elementary_charges_from_left, 50);
        // The second pair is already descending before its own minimum. Its
        // carrier must move even though the unrelated first pair needs a
        // different scale; a network-wide fraction incorrectly rounded this
        // independent one-carrier transfer down to zero.
        assert_eq!(settled[1].outward_elementary_charges_from_left, 1);
    }

    #[test]
    fn zero_current_contact_does_not_merge_independent_energy_settlements() {
        let anatomy = SparseElectricalAnatomy::new(
            4,
            vec![
                ElectricalContactAnatomy::new(0, 1, ExactRational::integer(1), 4)
                    .unwrap(),
                ElectricalContactAnatomy::new(1, 2, ExactRational::integer(1), 4)
                    .unwrap(),
                ElectricalContactAnatomy::new(2, 3, ExactRational::integer(1), 4)
                    .unwrap(),
            ],
        )
        .unwrap();
        let predecessor = SparseElectricalState::genesis(&anatomy);
        let membranes = [
            ElementaryChargeMembraneState::genesis(101),
            ElementaryChargeMembraneState::genesis(0),
            ElementaryChargeMembraneState::genesis(10),
            ElementaryChargeMembraneState::genesis(0),
        ];
        let transition = |contact_index: usize, carriers: i128| {
            ElectricalContactTransition {
                successor: predecessor.contacts[contact_index].clone(),
                outward_current_from_left_picoamperes: ExactRational::integer(carriers),
                outward_elementary_charges_from_left: carriers,
                released_work_zeptojoules: BigRational::zero(),
                exported_heat_zeptojoules: BigRational::zero(),
                conductance_changed: false,
            }
        };
        let settled = component_energy_descending_transitions(
            &anatomy,
            &predecessor,
            &capacitances(4),
            &membranes,
            &[u128::MAX; 4],
            1_000,
            vec![transition(0, 100), transition(1, 0), transition(2, 1)],
        )
        .unwrap();

        assert_eq!(settled[0].outward_elementary_charges_from_left, 50);
        assert_eq!(settled[1].outward_elementary_charges_from_left, 0);
        assert_eq!(settled[2].outward_elementary_charges_from_left, 1);
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
