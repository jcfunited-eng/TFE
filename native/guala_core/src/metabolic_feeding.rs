//! Minimal feeding metabolism for one reached neuron cohort.
//!
//! Authorized by Joe on 2026-08-05 ("the current energy supply depletes too
//! soon and your design rectifies that"), with the expectation that it is
//! altered later.  Nature principle governs: the loops below are the smallest
//! set that closes the body's one-way ratchets, and every one of them is built
//! out of reactions and quantities that already exist.
//!
//! Three loops live here.  None of them invents a rate, a stoichiometry, a
//! schedule, a threshold, or a constant:
//!
//! 1. NUTRITION INTAKE.  An AUTHORED nutrition declaration (an intake
//!    declaration, like curriculum card media — never a physics constant)
//!    carries whole quanta of energy content denominated in the body's own
//!    fuel quantum.  The reaction is `spent + intake energy -> fuel`, one
//!    quantum each way: the recovery lane law already fixes
//!    `fuel_per_extent == spent_per_extent`, so one spent quantum is exactly
//!    the residue of one burnt fuel quantum and exactly one quantum of intake
//!    energy restores it.  Intake energy that finds no spent quantum to
//!    restore is not absorbed and leaves as waste; the reservoir's heat is
//!    vented to the environment by the same exchange.
//!
//! 2. REST RECOVERY OF EVERY LANE.  The mounted fluid anatomy already carries
//!    a contact for every Psi, gate and plastic recovery lane of every neuron;
//!    only the gate lane was ever addressed, and only on demand from a pending
//!    gate transition.  During a genuinely dark settlement every lane's
//!    existing recovery reaction runs at the rate its own mounted contact
//!    permits, paying fuel at the lane's own stoichiometry.
//!
//! 3. MEMBRANE RETURN.  Gate work pumps separated charge into the cohort with
//!    no reverse path once the gates close (conductance is zero, so the
//!    existing conductive path carries nothing).  The return is an
//!    energy-paid whole-charge transport toward the authored rest — zero
//!    separated charge, the state every neuron is born at — bounded by what
//!    the gate's own single-channel conductance would carry in this interval
//!    and paid for in fuel on the gate's own dissipation lattice.
//!
//! Conservation is exact and stated on every settlement.  Nothing here holds
//! an owner, a lock, a timer, a schedule, a database, or a whole-brain scan.

use crate::complete_neuron::{
    membrane_return_affordable_charges, membrane_return_charge_bound, membrane_return_quanta_cost,
    settle_membrane_return_transport, settle_recovery_only, NeuronPhysicalAnatomy,
    NeuronPhysicalError, NeuronPhysicalState, RecoveryContact, RecoveryError, RecoveryLaneAddress,
};
use crate::recovery_fluid_contact::{
    settle_recovery_fluid_contact, ReachedRecoveryFluidAnatomy, RecoveryFluidError,
    RecoveryFluidReservoirAnatomy, RecoveryFluidReservoirState,
};

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum MetabolicError {
    /// The authored nutrition declaration carries no energy at all.
    EmptyNutritionDeclaration,
    /// The body has no spent material left to restore: it is already carrying
    /// every fuel quantum its reservoir can hold.  Over-feeding is refused
    /// here rather than silently discarded.
    NothingToRegenerate,
    /// A settled reaction did not move exactly the material its own
    /// stoichiometry requires.
    MaterialContinuity,
    ArithmeticWidth,
    AnatomyWidth,
    Neuron(NeuronPhysicalError),
    RecoveryFluid(RecoveryFluidError),
}

impl From<NeuronPhysicalError> for MetabolicError {
    fn from(value: NeuronPhysicalError) -> Self {
        Self::Neuron(value)
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

/// One authored nutrition declaration.
///
/// This is an INTAKE DECLARATION, in exactly the sense a curriculum card's
/// media is: the caller declares what is being delivered to the organism, and
/// the physics settles the consequence.  Its energy content is denominated in
/// the body's own fuel quantum — the unit the recovery lanes already burn — so
/// the reaction below needs no conversion factor and this declaration adds no
/// constant to the physics.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct AuthoredNutritionDeclaration {
    energy_quanta: u128,
}

impl AuthoredNutritionDeclaration {
    pub(crate) fn new(energy_quanta: u128) -> Result<Self, MetabolicError> {
        if energy_quanta == 0 {
            return Err(MetabolicError::EmptyNutritionDeclaration);
        }
        Ok(Self { energy_quanta })
    }

    pub(crate) fn energy_quanta(self) -> u128 {
        self.energy_quanta
    }
}

/// The exact consequence of one nutrition intake on one cohort reservoir.
///
/// Conservation (all exact, all checked by `nutrition_feed_conserves`):
///   * material: `fuel + spent` is unchanged — regeneration moves quanta back,
///     it never creates or destroys them;
///   * intake: `declaration.energy_quanta == regenerated_fuel_quanta +
///     unabsorbed_waste_quanta` — every delivered quantum is either absorbed
///     or leaves as waste;
///   * heat: `predecessor heat == successor heat + vented_heat_quanta` — the
///     reservoir's heat leaves the body ledger to the environment, exactly.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct NutritionFeedSettlement {
    pub(crate) successor_reservoir: RecoveryFluidReservoirState,
    pub(crate) regenerated_fuel_quanta: u128,
    pub(crate) unabsorbed_waste_quanta: u128,
    pub(crate) vented_heat_quanta: u128,
}

pub(crate) fn settle_nutrition_feed(
    reservoir_anatomy: RecoveryFluidReservoirAnatomy,
    predecessor: RecoveryFluidReservoirState,
    declaration: AuthoredNutritionDeclaration,
) -> Result<NutritionFeedSettlement, MetabolicError> {
    let (fuel_capacity, spent_capacity, heat_capacity) = reservoir_anatomy.capacities();
    let (fuel, spent, heat) = predecessor.physical_parts();
    if fuel > fuel_capacity || spent > spent_capacity || heat > heat_capacity {
        return Err(MetabolicError::RecoveryFluid(
            RecoveryFluidError::StateOutsideAnatomy,
        ));
    }
    let free_fuel_capacity = fuel_capacity
        .checked_sub(fuel)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    // One quantum of intake energy restores one spent quantum to fuel; the
    // reservoir can never hold more fuel than its derived capacity.
    let regenerated = declaration
        .energy_quanta()
        .min(spent)
        .min(free_fuel_capacity);
    if regenerated == 0 {
        // Honest refusal: the body is carrying every fuel quantum it can hold,
        // so this intake would be pure waste.  It is not silently accepted.
        return Err(MetabolicError::NothingToRegenerate);
    }
    let unabsorbed = declaration
        .energy_quanta()
        .checked_sub(regenerated)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    let successor = RecoveryFluidReservoirState::new(
        reservoir_anatomy,
        fuel.checked_add(regenerated)
            .ok_or(MetabolicError::ArithmeticWidth)?,
        spent - regenerated,
        0,
    )?;
    let settlement = NutritionFeedSettlement {
        successor_reservoir: successor,
        regenerated_fuel_quanta: regenerated,
        unabsorbed_waste_quanta: unabsorbed,
        vented_heat_quanta: heat,
    };
    debug_assert_eq!(
        settle_reservoir_heat_vent(reservoir_anatomy, predecessor).map(|vent| vent.1),
        Ok(heat)
    );
    if !nutrition_feed_conserves(predecessor, declaration, &settlement) {
        return Err(MetabolicError::MaterialContinuity);
    }
    Ok(settlement)
}

/// Vent the reservoir's accumulated heat to the environment.
///
/// The same exchange that carries nutrition in carries heat out; a body whose
/// heat ledger is full can run no further recovery reaction, because the
/// existing fluid contact refuses to export heat it has nowhere to put.  The
/// vented quanta leave the body ledger and are reported exactly.
pub(crate) fn settle_reservoir_heat_vent(
    reservoir_anatomy: RecoveryFluidReservoirAnatomy,
    predecessor: RecoveryFluidReservoirState,
) -> Result<(RecoveryFluidReservoirState, u128), MetabolicError> {
    let (fuel, spent, heat) = predecessor.physical_parts();
    if heat == 0 {
        return Ok((predecessor, 0));
    }
    Ok((
        RecoveryFluidReservoirState::new(reservoir_anatomy, fuel, spent, 0)?,
        heat,
    ))
}

/// The stated conservation of one nutrition intake, recomputed from the
/// predecessor and the settlement alone.
pub(crate) fn nutrition_feed_conserves(
    predecessor: RecoveryFluidReservoirState,
    declaration: AuthoredNutritionDeclaration,
    settlement: &NutritionFeedSettlement,
) -> bool {
    let (fuel, spent, heat) = predecessor.physical_parts();
    let (successor_fuel, successor_spent, successor_heat) =
        settlement.successor_reservoir.physical_parts();
    let material = fuel.checked_add(spent);
    let successor_material = successor_fuel.checked_add(successor_spent);
    let intake = settlement
        .regenerated_fuel_quanta
        .checked_add(settlement.unabsorbed_waste_quanta);
    let vented = successor_heat.checked_add(settlement.vented_heat_quanta);
    material.is_some()
        && material == successor_material
        && intake == Some(declaration.energy_quanta())
        && vented == Some(heat)
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
///     reservoir's heat ledger, plus one heat quantum for every fuel quantum
///     burnt by the membrane return;
///   * charge: the membrane's separated charge and the carrier partition move
///     equal and opposite, so total carrier material is unchanged.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct DarkRestNeuronSettlement {
    pub(crate) successor_neuron: NeuronPhysicalState,
    pub(crate) successor_reservoir: RecoveryFluidReservoirState,
    pub(crate) lane_recoveries: Vec<RestLaneRecovery>,
    pub(crate) returned_elementary_charges: i128,
    pub(crate) membrane_return_fuel_quanta: u128,
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
        self.lane_recoveries
            .iter()
            .map(|lane| lane.unmet_dissipation_quanta)
            .sum()
    }

    pub(crate) fn fuel_quanta(&self) -> u128 {
        self.lane_recoveries
            .iter()
            .map(|lane| lane.fuel_quanta)
            .sum::<u128>()
            + self.membrane_return_fuel_quanta
    }

    pub(crate) fn changed(&self) -> bool {
        self.returned_elementary_charges != 0
            || self.lane_recoveries.iter().any(|lane| lane.extent != 0)
    }
}

/// Settle one dark interval for one resident neuron: every recovery lane, then
/// the membrane return.  A dark interval is the stimulus-boundary law's own
/// truth signal (an interval carrying zero exogenous energy); this function
/// never decides when it is dark.
pub(crate) fn settle_dark_rest_neuron(
    recovery_anatomy: &ReachedRecoveryFluidAnatomy,
    neuron_index: usize,
    neuron_anatomy: &NeuronPhysicalAnatomy,
    predecessor_neuron: &NeuronPhysicalState,
    predecessor_reservoir: RecoveryFluidReservoirState,
    interval_microseconds: u32,
) -> Result<DarkRestNeuronSettlement, MetabolicError> {
    let mut neuron = predecessor_neuron.clone();
    let mut reservoir = predecessor_reservoir;
    let mut lane_recoveries = Vec::new();
    let psi_lane_count = neuron_anatomy.psi_ring_count();
    lane_recoveries
        .try_reserve_exact(
            psi_lane_count
                .checked_add(2)
                .ok_or(MetabolicError::ArithmeticWidth)?,
        )
        .map_err(|_| MetabolicError::ArithmeticWidth)?;
    for address in (0..psi_lane_count)
        .map(RecoveryLaneAddress::Psi)
        .chain([RecoveryLaneAddress::Gate, RecoveryLaneAddress::Plastic])
    {
        let settled = settle_rest_lane(
            recovery_anatomy,
            neuron_index,
            neuron_anatomy,
            address,
            &neuron,
            reservoir,
        )?;
        neuron = settled.0;
        reservoir = settled.1;
        lane_recoveries.push(settled.2);
    }
    let (successor_neuron, successor_reservoir, returned, membrane_fuel) = settle_membrane_return(
        neuron_anatomy,
        &neuron,
        recovery_anatomy.reservoir_anatomy(),
        reservoir,
        interval_microseconds,
    )?;
    Ok(DarkRestNeuronSettlement {
        unreturned_elementary_charges: successor_neuron.separated_elementary_charges(),
        successor_neuron,
        successor_reservoir,
        lane_recoveries,
        returned_elementary_charges: returned,
        membrane_return_fuel_quanta: membrane_fuel,
    })
}

fn settle_rest_lane(
    recovery_anatomy: &ReachedRecoveryFluidAnatomy,
    neuron_index: usize,
    neuron_anatomy: &NeuronPhysicalAnatomy,
    address: RecoveryLaneAddress,
    predecessor_neuron: &NeuronPhysicalState,
    predecessor_reservoir: RecoveryFluidReservoirState,
) -> Result<
    (
        NeuronPhysicalState,
        RecoveryFluidReservoirState,
        RestLaneRecovery,
    ),
    MetabolicError,
> {
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
    let contact = recovery_anatomy
        .mounted_contact(neuron_index, address)
        .ok_or(MetabolicError::AnatomyWidth)?;
    let (catalyst_per_extent, fuel_per_extent, spent_per_extent, heat_per_extent) =
        lane_anatomy.stoichiometry();
    let (lane_fuel_capacity, lane_spent_capacity, lane_heat_capacity) = lane_anatomy.capacities();
    let (lane_fuel, lane_spent, lane_heat) = lane_state.physical_parts();
    let reservoir_anatomy = recovery_anatomy.reservoir_anatomy();
    let (reservoir_fuel_capacity, reservoir_spent_capacity, reservoir_heat_capacity) =
        reservoir_anatomy.capacities();
    let (reservoir_fuel, reservoir_spent, reservoir_heat) = predecessor_reservoir.physical_parts();
    if lane_fuel > lane_fuel_capacity
        || lane_spent > lane_spent_capacity
        || lane_heat > lane_heat_capacity
        || reservoir_fuel > reservoir_fuel_capacity
        || reservoir_spent > reservoir_spent_capacity
        || reservoir_heat > reservoir_heat_capacity
    {
        return Err(MetabolicError::RecoveryFluid(
            RecoveryFluidError::StateOutsideAnatomy,
        ));
    }
    let (contact_catalyst, contact_fuel, contact_spent, contact_heat) = contact.parts();
    // The rest demand is the dissipation that actually stands in the ledger.
    // Every other term is a capacity the mounted anatomy already declares.
    let extent = (dissipated / heat_per_extent)
        .min(lane_fuel / fuel_per_extent)
        .min((lane_spent_capacity - lane_spent) / spent_per_extent)
        .min((lane_heat_capacity - lane_heat) / heat_per_extent)
        .min(reservoir_fuel / fuel_per_extent)
        .min((reservoir_spent_capacity - reservoir_spent) / spent_per_extent)
        .min((reservoir_heat_capacity - reservoir_heat) / heat_per_extent)
        .min(contact_catalyst / catalyst_per_extent)
        .min(contact_fuel / fuel_per_extent)
        .min(contact_spent / spent_per_extent)
        .min(contact_heat / heat_per_extent);
    if extent == 0 {
        return Ok((
            predecessor_neuron.clone(),
            predecessor_reservoir,
            RestLaneRecovery {
                address,
                extent: 0,
                drained_dissipation_quanta: 0,
                fuel_quanta: 0,
                unmet_dissipation_quanta: dissipated,
            },
        ));
    }
    let catalyst = extent
        .checked_mul(catalyst_per_extent)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    let mut psi_catalysts = vec![0_u128; neuron_anatomy.psi_ring_count()];
    let (gate_catalyst, plastic_catalyst) = match address {
        RecoveryLaneAddress::Psi(index) => {
            *psi_catalysts
                .get_mut(index)
                .ok_or(MetabolicError::AnatomyWidth)? = catalyst;
            (0, 0)
        }
        RecoveryLaneAddress::Gate => (catalyst, 0),
        RecoveryLaneAddress::Plastic => (0, catalyst),
    };
    let recovered = settle_recovery_only(
        neuron_anatomy,
        predecessor_neuron,
        RecoveryContact::new(&psi_catalysts, gate_catalyst, plastic_catalyst),
    )?;
    if recovered.extent != extent {
        return Err(MetabolicError::MaterialContinuity);
    }
    let expected_fuel = extent
        .checked_mul(fuel_per_extent)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    let expected_spent = extent
        .checked_mul(spent_per_extent)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    let expected_heat = extent
        .checked_mul(heat_per_extent)
        .ok_or(MetabolicError::ArithmeticWidth)?;
    let recovered_lane = recovered
        .successor
        .recovery
        .lane(address)
        .ok_or(RecoveryError::AnatomyWidth)?;
    let exchanged = settle_recovery_fluid_contact(
        lane_anatomy,
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
    let mut successor_neuron = recovered.successor;
    successor_neuron
        .recovery
        .replace_lane(address, exchanged.successor_lane)?;
    let unmet = successor_neuron
        .lane_dissipated_quanta(address)
        .ok_or(MetabolicError::AnatomyWidth)?;
    if dissipated
        .checked_sub(unmet)
        .ok_or(MetabolicError::MaterialContinuity)?
        != expected_heat
    {
        return Err(MetabolicError::MaterialContinuity);
    }
    Ok((
        successor_neuron,
        exchanged.successor_reservoir,
        RestLaneRecovery {
            address,
            extent,
            drained_dissipation_quanta: expected_heat,
            fuel_quanta: expected_fuel,
            unmet_dissipation_quanta: unmet,
        },
    ))
}

/// Return separated membrane charge toward the authored rest, paid in fuel.
///
/// The transport bound is the neuron's own conductive anatomy; the price is
/// the exact electrical work, quantized on the gate's own dissipation lattice.
/// If the reservoir cannot pay the whole bound, the transport is reduced to
/// exactly what it can pay — never silently completed for free.
fn settle_membrane_return(
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
        u128,
    ),
    MetabolicError,
> {
    let bound = membrane_return_charge_bound(
        neuron_anatomy,
        predecessor_neuron,
        interval_microseconds,
    )?;
    let (_, spent_capacity, heat_capacity) = reservoir_anatomy.capacities();
    let (fuel, spent, heat) = predecessor_reservoir.physical_parts();
    let affordable_quanta = fuel
        .min(
            spent_capacity
                .checked_sub(spent)
                .ok_or(MetabolicError::ArithmeticWidth)?,
        )
        .min(
            heat_capacity
                .checked_sub(heat)
                .ok_or(MetabolicError::ArithmeticWidth)?,
        );
    let mut charges = bound.charges;
    let mut successor_phase = bound.successor_phase;
    let mut cost = membrane_return_quanta_cost(neuron_anatomy, predecessor_neuron, charges)?;
    if cost > affordable_quanta {
        let affordable_charges = membrane_return_affordable_charges(
            neuron_anatomy,
            predecessor_neuron,
            affordable_quanta,
        )?;
        let magnitude = charges.unsigned_abs().min(affordable_charges);
        charges = if bound.charges.is_negative() {
            -i128::try_from(magnitude).map_err(|_| MetabolicError::ArithmeticWidth)?
        } else {
            i128::try_from(magnitude).map_err(|_| MetabolicError::ArithmeticWidth)?
        };
        // The body could not pay the whole transport, so the unresolved
        // fraction is NOT carried forward: the displacement itself remains.
        successor_phase = None;
        cost = membrane_return_quanta_cost(neuron_anatomy, predecessor_neuron, charges)?;
        if cost > affordable_quanta {
            return Err(MetabolicError::MaterialContinuity);
        }
    }
    let successor_neuron = settle_membrane_return_transport(
        neuron_anatomy,
        predecessor_neuron,
        charges,
        successor_phase,
        interval_microseconds,
    )?;
    if cost == 0 {
        return Ok((successor_neuron, predecessor_reservoir, charges, 0));
    }
    // The burnt fuel leaves one spent quantum behind (the lanes' own
    // fuel/spent identity) and vents its energy into the heat ledger.
    let successor_reservoir = RecoveryFluidReservoirState::new(
        reservoir_anatomy,
        fuel - cost,
        spent
            .checked_add(cost)
            .ok_or(MetabolicError::ArithmeticWidth)?,
        heat.checked_add(cost)
            .ok_or(MetabolicError::ArithmeticWidth)?,
    )?;
    Ok((successor_neuron, successor_reservoir, charges, cost))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn reservoir_anatomy() -> RecoveryFluidReservoirAnatomy {
        RecoveryFluidReservoirAnatomy::new(100, 100, 100)
    }

    #[test]
    fn nutrition_intake_restores_spent_material_exactly() {
        let anatomy = reservoir_anatomy();
        let predecessor = RecoveryFluidReservoirState::new(anatomy, 40, 60, 25).unwrap();
        let settled = settle_nutrition_feed(
            anatomy,
            predecessor,
            AuthoredNutritionDeclaration::new(50).unwrap(),
        )
        .unwrap();
        assert_eq!(settled.regenerated_fuel_quanta, 50);
        assert_eq!(settled.unabsorbed_waste_quanta, 0);
        assert_eq!(settled.vented_heat_quanta, 25);
        assert_eq!(settled.successor_reservoir.physical_parts(), (90, 10, 0));
        assert!(nutrition_feed_conserves(
            predecessor,
            AuthoredNutritionDeclaration::new(50).unwrap(),
            &settled
        ));
    }

    #[test]
    fn intake_beyond_what_the_body_can_absorb_leaves_as_waste() {
        let anatomy = reservoir_anatomy();
        let predecessor = RecoveryFluidReservoirState::new(anatomy, 95, 5, 3).unwrap();
        let declaration = AuthoredNutritionDeclaration::new(40).unwrap();
        let settled = settle_nutrition_feed(anatomy, predecessor, declaration).unwrap();
        assert_eq!(settled.regenerated_fuel_quanta, 5);
        assert_eq!(settled.unabsorbed_waste_quanta, 35);
        assert_eq!(settled.successor_reservoir.physical_parts(), (100, 0, 0));
        assert!(nutrition_feed_conserves(predecessor, declaration, &settled));
    }

    #[test]
    fn feeding_a_full_body_is_refused_not_silently_discarded() {
        let anatomy = reservoir_anatomy();
        let predecessor = RecoveryFluidReservoirState::new(anatomy, 100, 0, 0).unwrap();
        assert_eq!(
            settle_nutrition_feed(
                anatomy,
                predecessor,
                AuthoredNutritionDeclaration::new(10).unwrap()
            ),
            Err(MetabolicError::NothingToRegenerate)
        );
    }

    #[test]
    fn an_empty_nutrition_declaration_is_refused() {
        assert_eq!(
            AuthoredNutritionDeclaration::new(0),
            Err(MetabolicError::EmptyNutritionDeclaration)
        );
    }
}
