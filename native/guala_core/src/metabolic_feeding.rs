//! Exact dark recovery for one reached neuron cohort.
//!
//! Authorized by Joe on 2026-08-05 ("the current energy supply depletes too
//! soon and your design rectifies that"), with the expectation that it is
//! altered later.  Nature principle governs: the loops below are the smallest
//! set that closes the body's one-way ratchets, and every one of them is built
//! out of reactions and quantities that already exist.
//!
//! Two local loops live here. Neither invents a rate, schedule, threshold, or
//! unit conversion:
//!
//! 1. REST RECOVERY OF EVERY LANE.  The mounted fluid anatomy already carries
//!    a contact for every Psi, gate and plastic recovery lane of every neuron;
//!    only the gate lane was ever addressed, and only on demand from a pending
//!    gate transition.  During a genuinely dark settlement every lane's
//!    existing recovery reaction runs at the rate its own mounted contact
//!    permits, paying fuel at the lane's own stoichiometry.
//!
//! 2. CARRIER-GRADIENT PUMP.  The existing intracellular/extracellular carrier
//!    partition is the finite gradient material.  A local pump moves whole
//!    carriers only uphill according to the authored E_rev sign, at the
//!    existing one-channel conductance/time bound, and only when exact body
//!    energy pays the increase in membrane-plus-gradient work.  There is no
//!    desired voltage, automatic refill target, or fabricated ion species.
//!
//! Conservation is exact and stated on every settlement.  Nothing here holds
//! an owner, a lock, a timer, a schedule, a database, or a whole-brain scan.

use crate::complete_neuron::{
    membrane_and_gradient_work_zeptojoules, membrane_gradient_pump_charge_bound,
    settle_membrane_pump_transport, settle_recovery_only, NeuronPhysicalAnatomy,
    NeuronPhysicalError, NeuronPhysicalState, RecoveryContact, RecoveryError,
    RecoveryLaneAddress, RecoveryLaneState,
};
use crate::exact_rational::{ExactRational, ExactRationalError};
use crate::elementary_charge_membrane::MembraneChargeError;
use crate::recovery_fluid_contact::{
    recovery_exchange_extent_is_representable, settle_recovery_fluid_contact,
    whole_extents_carried, whole_extents_carried_difference, ReachedRecoveryFluidAnatomy,
    RecoveryFluidError, RecoveryFluidReservoirAnatomy, RecoveryFluidReservoirState,
};
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::ToPrimitive;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum MetabolicError {
    /// A settled reaction did not move exactly the material its own
    /// stoichiometry requires.
    MaterialContinuity,
    ArithmeticWidth,
    AnatomyWidth,
    Membrane(MembraneChargeError),
    Neuron(NeuronPhysicalError),
    RecoveryFluid(RecoveryFluidError),
}

impl From<NeuronPhysicalError> for MetabolicError {
    fn from(value: NeuronPhysicalError) -> Self {
        Self::Neuron(value)
    }
}

impl From<MembraneChargeError> for MetabolicError {
    fn from(value: MembraneChargeError) -> Self {
        Self::Membrane(value)
    }
}

impl From<RecoveryError> for MetabolicError {
    fn from(value: RecoveryError) -> Self {
        Self::Neuron(NeuronPhysicalError::Recovery(value))
    }
}

impl From<RecoveryFluidError> for MetabolicError {
    fn from(value: RecoveryFluidError) -> Self {
        Self::RecoveryFluid(value)
    }
}

impl From<ExactRationalError> for MetabolicError {
    fn from(_: ExactRationalError) -> Self {
        Self::ArithmeticWidth
    }
}

/// One lane's settled rest recovery.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RestLaneRecovery {
    pub(crate) address: RecoveryLaneAddress,
    pub(crate) extent: u128,
    pub(crate) drained_dissipation_quanta: u128,
    pub(crate) fuel_quanta: u128,
    /// Dissipation this lane still carries after the interval — the demand the
    /// body could not meet.  Reported, never hidden.
    pub(crate) unmet_dissipation_quanta: u128,
}

/// The exact consequence of one dark interval on one neuron and the shared
/// reservoir.
///
/// Conservation (all exact):
///   * material: every fuel quantum the reservoir gives up appears as a spent
///     quantum, in the lanes or back in the reservoir — `fuel + spent` over
///     reservoir and lanes together is unchanged;
///   * heat: every quantum drained from a dissipation ledger appears in the
///     reservoir's heat ledger;
///   * charge: the membrane's separated charge and the carrier partition move
///     equal and opposite, so total carrier material is unchanged.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct DarkRestNeuronSettlement {
    pub(crate) successor_neuron: NeuronPhysicalState,
    pub(crate) successor_reservoir: RecoveryFluidReservoirState,
    pub(crate) lane_recoveries: Vec<RestLaneRecovery>,
    unmet_dissipation_quanta: u128,
    pub(crate) returned_elementary_charges: i128,
    pub(crate) membrane_return_fuel_quanta: u128,
    pub(crate) pumped_elementary_charges: i128,
    pub(crate) pump_work_zeptojoules: ExactRational,
    /// Separated charge still standing away from rest after the interval.
    pub(crate) unreturned_elementary_charges: i128,
}

impl DarkRestNeuronSettlement {
    pub(crate) fn drained_dissipation_quanta(&self) -> u128 {
        self.lane_recoveries
            .iter()
            .map(|lane| lane.drained_dissipation_quanta)
            .sum()
    }

    pub(crate) fn unmet_dissipation_quanta(&self) -> u128 {
        self.unmet_dissipation_quanta
    }

    pub(crate) fn fuel_quanta(&self) -> u128 {
        self.lane_recoveries
            .iter()
            .map(|lane| lane.fuel_quanta)
            .sum::<u128>()
            + self.membrane_return_fuel_quanta
    }

    pub(crate) fn changed(&self) -> bool {
        self.pumped_elementary_charges != 0
            || self.lane_recoveries.iter().any(|lane| lane.extent != 0)
    }
}

/// Settle one dark interval for one resident neuron by recovering every
/// physically depleted recovery lane.  A dark interval is the
/// stimulus-boundary law's own truth signal (an interval carrying zero
/// exogenous energy); it is not itself a membrane path or pump.
pub(crate) fn settle_dark_rest_neuron(
    recovery_anatomy: &ReachedRecoveryFluidAnatomy,
    neuron_index: usize,
    neuron_anatomy: &NeuronPhysicalAnatomy,
    predecessor_neuron: &NeuronPhysicalState,
    predecessor_reservoir: RecoveryFluidReservoirState,
    interval_microseconds: u32,
) -> Result<DarkRestNeuronSettlement, MetabolicError> {
    let mut reservoir = predecessor_reservoir;
    let mut lane_recoveries = Vec::new();
    let mut successor_lane_states = Vec::new();
    let psi_lane_count = neuron_anatomy.psi_ring_count();
    let mut psi_catalysts = vec![0_u128; psi_lane_count];
    let mut gate_catalyst = 0_u128;
    let mut plastic_catalyst = 0_u128;
    let mut total_extent = 0_u128;
    let mut unmet_dissipation_quanta = 0_u128;
    let mut reservoir_recovery_open = reservoir_can_recover(recovery_anatomy, reservoir);
    let mut settle_reached_lane = |address: RecoveryLaneAddress| -> Result<(), MetabolicError> {
        let dissipated = predecessor_neuron
            .lane_dissipated_quanta(address)
            .ok_or(MetabolicError::AnatomyWidth)?;
        if !reservoir_recovery_open {
            unmet_dissipation_quanta = unmet_dissipation_quanta
                .checked_add(dissipated)
                .ok_or(MetabolicError::ArithmeticWidth)?;
            return Ok(());
        }
        let planned = plan_rest_lane(
            recovery_anatomy,
            neuron_index,
            neuron_anatomy,
            address,
            predecessor_neuron,
            reservoir,
        )?;
        unmet_dissipation_quanta = unmet_dissipation_quanta
            .checked_add(planned.observation.unmet_dissipation_quanta)
            .ok_or(MetabolicError::ArithmeticWidth)?;
        if planned.observation.extent == 0 {
            return Ok(());
        }
        match address {
            RecoveryLaneAddress::Psi(index) => psi_catalysts[index] = planned.catalyst_quanta,
            RecoveryLaneAddress::Gate => gate_catalyst = planned.catalyst_quanta,
            RecoveryLaneAddress::Plastic => plastic_catalyst = planned.catalyst_quanta,
        }
        total_extent = total_extent
            .checked_add(planned.observation.extent)
            .ok_or(MetabolicError::ArithmeticWidth)?;
        reservoir = planned.successor_reservoir;
        if planned.observation.extent != 0 {
            reservoir_recovery_open = reservoir_can_recover(recovery_anatomy, reservoir);
        }
        successor_lane_states.push((address, planned.successor_lane));
        lane_recoveries.push(planned.observation);
        Ok(())
    };
    // Dissipation itself is the reached frontier for recovery. A lane with no
    // standing dissipated material cannot react, so it must not enter contact
    // planning merely because positional anatomy exists.
    for (index, ring) in predecessor_neuron.psi_state().rings().iter().enumerate() {
        if ring.dissipated_quanta() != 0 {
            settle_reached_lane(RecoveryLaneAddress::Psi(index))?;
        }
    }
    for address in [RecoveryLaneAddress::Gate, RecoveryLaneAddress::Plastic] {
        if predecessor_neuron
            .lane_dissipated_quanta(address)
            .ok_or(MetabolicError::AnatomyWidth)?
            != 0
        {
            settle_reached_lane(address)?;
        }
    }
    drop(settle_reached_lane);
    let mut neuron = if total_extent == 0 {
        predecessor_neuron.clone()
    } else {
        let recovered = settle_recovery_only(
            neuron_anatomy,
            predecessor_neuron,
            RecoveryContact::new(&psi_catalysts, gate_catalyst, plastic_catalyst),
        )?;
        if recovered.extent != total_extent {
            return Err(MetabolicError::MaterialContinuity);
        }
        recovered.successor
    };
    for ((address, successor_lane), observation) in successor_lane_states
        .into_iter()
        .zip(lane_recoveries.iter())
    {
        neuron.recovery.replace_lane(address, successor_lane)?;
        if neuron
            .lane_dissipated_quanta(address)
            .ok_or(MetabolicError::AnatomyWidth)?
            != observation.unmet_dissipation_quanta
        {
            return Err(MetabolicError::MaterialContinuity);
        }
    }
    let (successor_neuron, successor_reservoir, returned, pumped, pump_work) =
        settle_membrane_gradient_transport(
            neuron_anatomy,
            &neuron,
            recovery_anatomy.reservoir_anatomy(),
            reservoir,
            interval_microseconds,
        )?;
    let membrane_fuel = 0;
    Ok(DarkRestNeuronSettlement {
        unreturned_elementary_charges: successor_neuron.separated_elementary_charges(),
        successor_neuron,
        successor_reservoir,
        lane_recoveries,
        unmet_dissipation_quanta,
        returned_elementary_charges: returned,
        membrane_return_fuel_quanta: membrane_fuel,
        pumped_elementary_charges: pumped,
        pump_work_zeptojoules: pump_work,
    })
}

fn reservoir_can_recover(
    recovery_anatomy: &ReachedRecoveryFluidAnatomy,
    reservoir: RecoveryFluidReservoirState,
) -> bool {
    let (_, spent_capacity, thermal_capacity) =
        recovery_anatomy.reservoir_anatomy().capacities();
    let (available, spent, thermal) = reservoir.physical_parts();
    let minimum = recovery_anatomy.minimum_recovery_energy_per_extent_zeptojoules();
    let minimum = wide_rational(minimum);
    wide_rational(available) >= minimum
        && wide_rational(spent_capacity) - wide_rational(spent) >= minimum
        && wide_rational(thermal_capacity) - wide_rational(thermal) >= minimum
}

/// Settle the neuron's one retained carrier-gradient transport path.
///
/// The same local electrochemical difference has two exact regimes.  When the
/// authored transport direction lowers membrane-plus-gradient work, material
/// moves passively and the released work becomes local heat.  When it raises
/// stored work, body energy pays that increase and becomes spent material.
/// The path cannot cross its own reversal potential in one interval, and no
/// desired voltage or extra gradient coordinate is introduced.
pub(crate) fn settle_membrane_gradient_transport(
    neuron_anatomy: &NeuronPhysicalAnatomy,
    predecessor_neuron: &NeuronPhysicalState,
    reservoir_anatomy: RecoveryFluidReservoirAnatomy,
    predecessor_reservoir: RecoveryFluidReservoirState,
    interval_microseconds: u32,
) -> Result<
    (
        NeuronPhysicalState,
        RecoveryFluidReservoirState,
        i128,
        i128,
        ExactRational,
    ),
    MetabolicError,
> {
    let bound = membrane_gradient_pump_charge_bound(
        neuron_anatomy,
        predecessor_neuron,
        interval_microseconds,
    )?;
    if bound.charges == 0 {
        return Ok((
            predecessor_neuron.clone(),
            predecessor_reservoir,
            0,
            0,
            ExactRational::integer(0),
        ));
    }
    let (_, spent_capacity, _) = reservoir_anatomy.capacities();
    let (available, spent, thermal) = predecessor_reservoir.physical_parts();
    // Compare the two exact sources of pump work in widened arithmetic.  A
    // reservoir's remaining spent capacity may be a perfectly finite positive
    // rational whose reduced numerator is wider than the resident i128 format;
    // narrowing that headroom before taking the smaller available-energy
    // budget falsely refused an otherwise representable local transition.
    let budget = wide_rational(available)
        .min(wide_rational(spent_capacity) - wide_rational(spent));
    if budget <= wide_rational(ExactRational::integer(0)) {
        return Ok((
            predecessor_neuron.clone(),
            predecessor_reservoir,
            0,
            0,
            ExactRational::integer(0),
        ));
    }
    let predecessor_work =
        membrane_and_gradient_work_zeptojoules(neuron_anatomy, predecessor_neuron)?;
    let direction_negative = bound.charges.is_negative();
    let full_magnitude = bound.charges.unsigned_abs();
    let mut lower = 0_u128;
    let mut upper = full_magnitude;
    let mut accepted_state = predecessor_neuron.clone();
    let mut accepted_reservoir = predecessor_reservoir;
    let mut accepted_work = ExactRational::integer(0);
    let mut passive = None;
    while lower < upper {
        let middle = lower
            .checked_add((upper - lower + 1) / 2)
            .ok_or(MetabolicError::ArithmeticWidth)?;
        let signed = signed_magnitude(direction_negative, middle)?;
        let candidate = settle_membrane_pump_transport(
            neuron_anatomy,
            predecessor_neuron,
            signed,
            (middle == full_magnitude)
                .then_some(bound.successor_phase)
                .flatten(),
            interval_microseconds,
        )?;
        let successor_work = membrane_and_gradient_work_zeptojoules(neuron_anatomy, &candidate)?;
        let signed_work = match wide_sub(successor_work, predecessor_work) {
            Ok(required) => required,
            Err(MetabolicError::ArithmeticWidth) => {
                upper = middle - 1;
                continue;
            }
            Err(error) => return Err(error),
        };
        let candidate_passive = wide_rational(signed_work)
            < wide_rational(ExactRational::integer(0));
        if passive.is_none() {
            passive = Some(candidate_passive);
        }
        if passive != Some(candidate_passive)
            || !transport_stays_on_reversal_side(neuron_anatomy, predecessor_neuron, &candidate)?
        {
            upper = middle - 1;
            continue;
        }
        let settled_work = if candidate_passive {
            signed_work.checked_neg()?
        } else {
            signed_work
        };
        if !candidate_passive && wide_rational(settled_work) > budget {
            upper = middle - 1;
            continue;
        }
        let candidate_reservoir = match if candidate_passive {
            passive_reservoir_successor(
                reservoir_anatomy,
                available,
                spent,
                thermal,
                settled_work,
            )
        } else {
            pump_reservoir_successor(
                reservoir_anatomy,
                available,
                spent,
                thermal,
                settled_work,
            )
        }? {
            Some(candidate_reservoir) => candidate_reservoir,
            None => {
                // Fixed-width exact state is part of the resident physical
                // boundary.  If this whole-carrier extent has no exact
                // representable successor, the local pump stalls before that
                // extent; no value is rounded and the organism's other local
                // settlements remain free to proceed.
                upper = middle - 1;
                continue;
            }
        };
        lower = middle;
        accepted_state = candidate;
        accepted_reservoir = candidate_reservoir;
        accepted_work = settled_work;
    }
    if lower == 0 {
        return Ok((
            predecessor_neuron.clone(),
            predecessor_reservoir,
            0,
            0,
            ExactRational::integer(0),
        ));
    }
    Ok((
        accepted_state,
        accepted_reservoir,
        if passive == Some(true) {
            signed_magnitude(direction_negative, lower)?
        } else {
            0
        },
        if passive == Some(false) {
            signed_magnitude(direction_negative, lower)?
        } else {
            0
        },
        accepted_work,
    ))
}

fn transport_stays_on_reversal_side(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &NeuronPhysicalState,
    successor: &NeuronPhysicalState,
) -> Result<bool, MetabolicError> {
    let reversal = anatomy.gate_reversal_potential_millivolts();
    let predecessor_drive = predecessor
        .membrane_state()
        .potential_millivolts(anatomy.capacitance())?
        .checked_sub(reversal)?;
    let successor_drive = successor
        .membrane_state()
        .potential_millivolts(anatomy.capacitance())?
        .checked_sub(reversal)?;
    let predecessor_sign = predecessor_drive.parts().0.signum();
    let successor_sign = successor_drive.parts().0.signum();
    Ok(successor_sign == 0 || predecessor_sign == successor_sign)
}

fn passive_reservoir_successor(
    anatomy: RecoveryFluidReservoirAnatomy,
    available: ExactRational,
    spent: ExactRational,
    thermal: ExactRational,
    released_work: ExactRational,
) -> Result<Option<RecoveryFluidReservoirState>, MetabolicError> {
    let (_, _, thermal_capacity) = anatomy.capacities();
    let successor_thermal = match wide_add(thermal, released_work) {
        Ok(value) => value,
        Err(MetabolicError::ArithmeticWidth) => return Ok(None),
        Err(error) => return Err(error),
    };
    if wide_rational(successor_thermal) > wide_rational(thermal_capacity) {
        return Ok(None);
    }
    match RecoveryFluidReservoirState::new(anatomy, available, spent, successor_thermal) {
        Ok(successor) => Ok(Some(successor)),
        Err(RecoveryFluidError::ArithmeticWidth) => Ok(None),
        Err(error) => Err(error.into()),
    }
}

fn pump_reservoir_successor(
    anatomy: RecoveryFluidReservoirAnatomy,
    available: ExactRational,
    spent: ExactRational,
    thermal: ExactRational,
    work: ExactRational,
) -> Result<Option<RecoveryFluidReservoirState>, MetabolicError> {
    let successor_available = match wide_sub(available, work) {
        Ok(value) => value,
        Err(MetabolicError::ArithmeticWidth) => return Ok(None),
        Err(error) => return Err(error),
    };
    let successor_spent = match wide_add(spent, work) {
        Ok(value) => value,
        Err(MetabolicError::ArithmeticWidth) => return Ok(None),
        Err(error) => return Err(error),
    };
    match RecoveryFluidReservoirState::new(
        anatomy,
        successor_available,
        successor_spent,
        thermal,
    ) {
        Ok(successor) => Ok(Some(successor)),
        Err(RecoveryFluidError::ArithmeticWidth) => Ok(None),
        Err(error) => Err(error.into()),
    }
}

fn wide_rational(value: ExactRational) -> BigRational {
    let (numerator, denominator) = value.parts();
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

fn narrow_rational(value: BigRational) -> Result<ExactRational, MetabolicError> {
    ExactRational::new(
        value
            .numer()
            .to_i128()
            .ok_or(MetabolicError::ArithmeticWidth)?,
        value
            .denom()
            .to_u128()
            .ok_or(MetabolicError::ArithmeticWidth)?,
    )
    .map_err(Into::into)
}

fn wide_add(
    left: ExactRational,
    right: ExactRational,
) -> Result<ExactRational, MetabolicError> {
    narrow_rational(wide_rational(left) + wide_rational(right))
}

fn wide_sub(
    left: ExactRational,
    right: ExactRational,
) -> Result<ExactRational, MetabolicError> {
    narrow_rational(wide_rational(left) - wide_rational(right))
}

fn signed_magnitude(negative: bool, magnitude: u128) -> Result<i128, MetabolicError> {
    let magnitude = i128::try_from(magnitude).map_err(|_| MetabolicError::ArithmeticWidth)?;
    Ok(if negative { -magnitude } else { magnitude })
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct RestLanePlan {
    catalyst_quanta: u128,
    successor_lane: RecoveryLaneState,
    successor_reservoir: RecoveryFluidReservoirState,
    observation: RestLaneRecovery,
}

fn plan_rest_lane(
    recovery_anatomy: &ReachedRecoveryFluidAnatomy,
    neuron_index: usize,
    neuron_anatomy: &NeuronPhysicalAnatomy,
    address: RecoveryLaneAddress,
    predecessor_neuron: &NeuronPhysicalState,
    predecessor_reservoir: RecoveryFluidReservoirState,
) -> Result<RestLanePlan, MetabolicError> {
    let lane_anatomy = neuron_anatomy
        .recovery_anatomy()
        .lane(address)
        .ok_or(RecoveryError::AnatomyWidth)?;
    let lane_state = predecessor_neuron
        .recovery
        .lane(address)
        .ok_or(RecoveryError::AnatomyWidth)?;
    let dissipated = predecessor_neuron
        .lane_dissipated_quanta(address)
        .ok_or(MetabolicError::AnatomyWidth)?;
    if dissipated == 0 {
        return Ok(RestLanePlan {
            catalyst_quanta: 0,
            successor_lane: lane_state,
            successor_reservoir: predecessor_reservoir,
            observation: RestLaneRecovery {
                address,
                extent: 0,
                drained_dissipation_quanta: 0,
                fuel_quanta: 0,
                unmet_dissipation_quanta: 0,
            },
        });
    }
    let contact = recovery_anatomy
        .mounted_contact(neuron_index, address)
        .ok_or(MetabolicError::AnatomyWidth)?;
    let (catalyst_per_extent, fuel_per_extent, spent_per_extent, heat_per_extent) =
        lane_anatomy.stoichiometry();
    let (_, lane_spent_capacity, lane_heat_capacity) = lane_anatomy.capacities();
    let (lane_fuel, lane_spent, lane_heat) = lane_state.physical_parts();
    let (contact_catalyst, contact_fuel, contact_spent, contact_heat) = contact.parts();
    // Reject a physically blocked lane using local integer bounds before doing
    // exact shared-reservoir arithmetic. The typed anatomy/state constructors
    // already enforce their capacity invariants; repeating those proofs for
    // every reached lane made a zero-extent rest interval needlessly expensive.
    let local_extent = (dissipated / heat_per_extent)
        .min(lane_fuel / fuel_per_extent)
        .min(
            lane_spent_capacity
                .checked_sub(lane_spent)
                .ok_or(MetabolicError::MaterialContinuity)?
                / spent_per_extent,
        )
        .min(
            lane_heat_capacity
                .checked_sub(lane_heat)
                .ok_or(MetabolicError::MaterialContinuity)?
                / heat_per_extent,
        )
        .min(contact_catalyst / catalyst_per_extent)
        .min(contact_fuel / fuel_per_extent)
        .min(contact_spent / spent_per_extent)
        .min(contact_heat / heat_per_extent);
    if local_extent == 0 {
        return Ok(RestLanePlan {
            catalyst_quanta: 0,
            successor_lane: lane_state,
            successor_reservoir: predecessor_reservoir,
            observation: RestLaneRecovery {
                address,
                extent: 0,
                drained_dissipation_quanta: 0,
                fuel_quanta: 0,
                unmet_dissipation_quanta: dissipated,
            },
        });
    }
    let reservoir_anatomy = recovery_anatomy.reservoir_anatomy();
    let (_, reservoir_spent_capacity, reservoir_thermal_capacity) =
        reservoir_anatomy.capacities();
    let (reservoir_available, reservoir_spent, reservoir_thermal) =
        predecessor_reservoir.physical_parts();
    let energy_per_extent = neuron_anatomy.recovery_energy_per_extent_zeptojoules(address)?;
    // The rest demand is the dissipation that actually stands in the ledger.
    // Every other term is a capacity the mounted anatomy already declares.
    let extent = local_extent
        .min(whole_extents_carried(
            reservoir_available,
            energy_per_extent,
        )?)
        .min(whole_extents_carried_difference(
            reservoir_spent_capacity,
            reservoir_spent,
            energy_per_extent,
        )?)
        .min(whole_extents_carried_difference(
            reservoir_thermal_capacity,
            reservoir_thermal,
            energy_per_extent,
        )?);
    let extent = if recovery_exchange_extent_is_representable(
        predecessor_reservoir,
        energy_per_extent,
        extent,
    ) {
        extent
    } else {
        0
    };
    if extent == 0 {
        return Ok(RestLanePlan {
            catalyst_quanta: 0,
            successor_lane: lane_state,
            successor_reservoir: predecessor_reservoir,
            observation: RestLaneRecovery {
                address,
                extent: 0,
                drained_dissipation_quanta: 0,
                fuel_quanta: 0,
                unmet_dissipation_quanta: dissipated,
            },
        });
    }
    let catalyst = extent
        .checked_mul(catalyst_per_extent)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    let expected_fuel = extent
        .checked_mul(fuel_per_extent)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    let expected_spent = extent
        .checked_mul(spent_per_extent)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    let expected_heat = extent
        .checked_mul(heat_per_extent)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    let recovered_lane = RecoveryLaneState::from_physical_parts(
        lane_anatomy,
        lane_fuel
            .checked_sub(expected_fuel)
            .ok_or(MetabolicError::MaterialContinuity)?,
        lane_spent
            .checked_add(expected_spent)
            .ok_or(MetabolicError::ArithmeticWidth)?,
        lane_heat
            .checked_add(expected_heat)
            .ok_or(MetabolicError::ArithmeticWidth)?,
    )?;
    let exchanged = settle_recovery_fluid_contact(
        lane_anatomy,
        energy_per_extent,
        recovered_lane,
        reservoir_anatomy,
        predecessor_reservoir,
        contact,
    )?;
    if exchanged.inward_fuel_quanta != expected_fuel
        || exchanged.outward_spent_quanta != expected_spent
        || exchanged.outward_heat_quanta != expected_heat
    {
        return Err(MetabolicError::MaterialContinuity);
    }
    let unmet = dissipated
        .checked_sub(expected_heat)
        .ok_or(MetabolicError::MaterialContinuity)?;
    if dissipated
        .checked_sub(unmet)
        .ok_or(MetabolicError::MaterialContinuity)?
        != expected_heat
    {
        return Err(MetabolicError::MaterialContinuity);
    }
    Ok(RestLanePlan {
        catalyst_quanta: catalyst,
        successor_lane: exchanged.successor_lane,
        successor_reservoir: exchanged.successor_reservoir,
        observation: RestLaneRecovery {
            address,
            extent,
            drained_dissipation_quanta: expected_heat,
            fuel_quanta: expected_fuel,
            unmet_dissipation_quanta: unmet,
        },
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pump_stalls_before_an_unrepresentable_exact_reservoir_successor() {
        let maximum = ExactRational::integer(i128::MAX);
        let anatomy = RecoveryFluidReservoirAnatomy::new(
            ExactRational::integer(1),
            maximum,
            ExactRational::integer(0),
        )
        .unwrap();
        let spent = ExactRational::new(i128::MAX - 2, 2).unwrap();

        assert!(pump_reservoir_successor(
            anatomy,
            ExactRational::integer(1),
            spent,
            ExactRational::integer(0),
            ExactRational::new(1, 3).unwrap(),
        )
        .unwrap()
        .is_none());

        let representable = pump_reservoir_successor(
            anatomy,
            ExactRational::integer(1),
            spent,
            ExactRational::integer(0),
            ExactRational::new(1, 2).unwrap(),
        )
        .unwrap()
        .unwrap();
        assert_eq!(
            representable.physical_parts(),
            (
                ExactRational::new(1, 2).unwrap(),
                ExactRational::integer((i128::MAX - 1) / 2),
                ExactRational::integer(0),
            )
        );
    }
}
