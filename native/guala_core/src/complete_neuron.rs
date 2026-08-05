//! Definitive local physical transition for one reached Guala neuron.
//!
//! One ingress is a borrowed perspective over one shared UF v1.4 result. All
//! seven DSF facts pass through exact MathLoom balanced ternary into the mounted
//! Psi/Krimelack energy fabric. The same local interval also receives exact gate
//! work, recovery and DNA contacts, elapsed physical duration, and any sparse
//! inter-neuron charge transfer. Physical gate, conductance, membrane, finite
//! material, recovery, DNA, and plasticity consequences follow. A
//! neuronal fractal exists only as the retained sparse difference between
//! pre-experience and post-experience quiescent physical states.
//!
//! This pure transition contains no owner, lock, database, receipt, hash,
//! serializer, semantic label, score, ML approximation, or legacy VTVR field.

use crate::elementary_charge_membrane::{ElementaryChargeMembraneState, MembraneCapacitance};
use crate::elementary_charge_transfer::ChargeCarrierPhase;
use crate::exact_rational::{ExactRational, ExactRationalError};
use crate::joint_uf_neuron_boundary::{
    settle_shared_dsf_mathloom, BalancedTrit, BorrowedMathLoomDelivery, JointNeuronBoundaryError,
    JointNeuronPerspective, MathLoomAnatomy,
};
use crate::local_membrane_conductance_balance::{
    settle_local_membrane_conductances_with_inter_neuron_contact, LocalConductancePath,
    LocalMembraneConductanceState, LocalMembraneConductanceTransition, MembraneConductanceError,
};
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Signed, ToPrimitive, Zero};

type Exact = BigRational;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PsiRingAnatomy {
    node_amplitude_quanta: [u128; 3],
    rest_energy_zeptojoules: [Exact; 3],
    dsf_coupling_zeptojoules: Exact,
    dissipation_quantum_zeptojoules: Exact,
    dissipation_capacity_quanta: u128,
    reachable: [[bool; 3]; 3],
    genesis_winding: BalancedTrit,
}

impl PsiRingAnatomy {
    pub(crate) fn new(
        node_amplitude_quanta: [u128; 3],
        rest_energy_zeptojoules: [Exact; 3],
        dsf_coupling_zeptojoules: Exact,
        dissipation_quantum_zeptojoules: Exact,
        dissipation_capacity_quanta: u128,
        reachable: [[bool; 3]; 3],
        genesis_winding: BalancedTrit,
    ) -> Result<Self, PsiSettlementError> {
        if node_amplitude_quanta.contains(&0)
            || dsf_coupling_zeptojoules <= Exact::zero()
            || dissipation_quantum_zeptojoules <= Exact::zero()
        {
            return Err(PsiSettlementError::NonPositiveEnergyAnatomy);
        }
        for state in 0..3 {
            if !reachable[state][state] || reachable[state] != transpose_row(&reachable, state) {
                return Err(PsiSettlementError::AsymmetricReachability);
            }
        }
        Ok(Self {
            node_amplitude_quanta,
            rest_energy_zeptojoules,
            dsf_coupling_zeptojoules,
            dissipation_quantum_zeptojoules,
            dissipation_capacity_quanta,
            reachable,
            genesis_winding,
        })
    }
}

fn transpose_row(matrix: &[[bool; 3]; 3], row: usize) -> [bool; 3] {
    [matrix[0][row], matrix[1][row], matrix[2][row]]
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PsiKrimelackAnatomy {
    positions: usize,
    constraint_count: usize,
    rings: Box<[PsiRingAnatomy]>,
}

impl PsiKrimelackAnatomy {
    pub(crate) fn new(
        positions: usize,
        constraint_count: usize,
        rings: Vec<PsiRingAnatomy>,
    ) -> Result<Self, PsiSettlementError> {
        let required = constraint_count
            .checked_mul(2)
            .and_then(|count| count.checked_mul(positions))
            .ok_or(PsiSettlementError::AnatomyWidth)?;
        if positions == 0 || rings.len() != required {
            return Err(PsiSettlementError::AnatomyWidth);
        }
        Ok(Self {
            positions,
            constraint_count,
            rings: rings.into_boxed_slice(),
        })
    }

    pub(crate) fn ring_count(&self) -> usize {
        self.rings.len()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PsiRingState {
    amplitude_quanta: [u128; 3],
    phase_thirds: [i8; 3],
    winding: BalancedTrit,
    dissipated_quanta: u128,
}

impl PsiRingState {
    pub(crate) fn amplitude_quanta(self) -> [u128; 3] {
        self.amplitude_quanta
    }

    pub(crate) fn phase_thirds(self) -> [i8; 3] {
        self.phase_thirds
    }

    pub(crate) fn winding(self) -> BalancedTrit {
        self.winding
    }

    pub(crate) fn dissipated_quanta(self) -> u128 {
        self.dissipated_quanta
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PsiKrimelackState {
    rings: Box<[PsiRingState]>,
}

impl PsiKrimelackState {
    pub(crate) fn genesis(anatomy: &PsiKrimelackAnatomy) -> Self {
        let rings = anatomy
            .rings
            .iter()
            .map(|ring| PsiRingState {
                amplitude_quanta: ring.node_amplitude_quanta,
                phase_thirds: canonical_phase_thirds(ring.genesis_winding),
                winding: ring.genesis_winding,
                dissipated_quanta: 0,
            })
            .collect::<Vec<_>>()
            .into_boxed_slice();
        Self { rings }
    }

    pub(crate) fn rings(&self) -> &[PsiRingState] {
        &self.rings
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PsiSettlementError {
    NonPositiveEnergyAnatomy,
    AsymmetricReachability,
    AnatomyWidth,
    DeliveryShapeChanged,
    DegenerateLowerEnergySuccessor,
    DissipationNotQuantized,
    ArithmeticWidth,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PsiSettlement {
    pub(crate) successor: PsiKrimelackState,
    pub(crate) changed_rings: usize,
    pub(crate) dissipated_quanta: u128,
}

/// Settle every typed MathLoom position through its mounted finite energy
/// landscape. DSF supplies only the canonical coupling-energy term. The
/// successor is selected by reachable exact energy descent, never assignment
/// from the incoming trit. Exact ties retain the predecessor when possible and
/// otherwise refuse an unresolved symmetric successor.
pub(crate) fn settle_psi_krimelack(
    anatomy: &PsiKrimelackAnatomy,
    predecessor: &PsiKrimelackState,
    delivery: &BorrowedMathLoomDelivery<'_>,
) -> Result<PsiSettlement, PsiSettlementError> {
    if delivery.constraints().len() != anatomy.constraint_count
        || predecessor.rings.len() != anatomy.rings.len()
        || delivery
            .constraints()
            .iter()
            .any(|constraint| constraint.word().numerator().len() != anatomy.positions)
    {
        return Err(PsiSettlementError::DeliveryShapeChanged);
    }
    let mut successor = predecessor.clone();
    let mut changed_rings = 0_usize;
    let mut dissipated_quanta = 0_u128;
    for constraint_index in 0..anatomy.constraint_count {
        let word = delivery.constraints()[constraint_index].word();
        for (part_index, part) in [word.numerator(), word.denominator()].iter().enumerate() {
            for (position, target) in part.iter().enumerate() {
                let ring_index = (constraint_index * 2 + part_index) * anatomy.positions + position;
                let ring_anatomy = &anatomy.rings[ring_index];
                let prior = predecessor.rings[ring_index];
                let settled = settle_one_ring(ring_anatomy, prior, *target)?;
                if settled.winding != prior.winding {
                    changed_rings += 1;
                    let used = settled
                        .dissipated_quanta
                        .checked_sub(prior.dissipated_quanta)
                        .ok_or(PsiSettlementError::ArithmeticWidth)?;
                    dissipated_quanta = dissipated_quanta
                        .checked_add(used)
                        .ok_or(PsiSettlementError::ArithmeticWidth)?;
                }
                successor.rings[ring_index] = settled;
            }
        }
    }
    Ok(PsiSettlement {
        successor,
        changed_rings,
        dissipated_quanta,
    })
}

fn settle_one_ring(
    anatomy: &PsiRingAnatomy,
    predecessor: PsiRingState,
    target: BalancedTrit,
) -> Result<PsiRingState, PsiSettlementError> {
    let current_index = trit_index(predecessor.winding);
    let mut energies = [Exact::zero(), Exact::zero(), Exact::zero()];
    for candidate in all_trits() {
        let index = trit_index(candidate);
        energies[index] = ring_energy(anatomy, candidate, target);
    }
    let mut minimum: Option<(usize, &Exact)> = None;
    let mut tied = false;
    for candidate in 0..3 {
        if !anatomy.reachable[current_index][candidate] {
            continue;
        }
        match minimum {
            None => minimum = Some((candidate, &energies[candidate])),
            Some((_, energy)) if energies[candidate] < *energy => {
                minimum = Some((candidate, &energies[candidate]));
                tied = false;
            }
            Some((_, energy)) if energies[candidate] == *energy => tied = true,
            _ => {}
        }
    }
    let (minimum_index, minimum_energy) = minimum.expect("self reachability is admitted");
    if energies[current_index] == *minimum_energy {
        return Ok(predecessor);
    }
    if tied {
        return Err(PsiSettlementError::DegenerateLowerEnergySuccessor);
    }
    let drop = &energies[current_index] - minimum_energy;
    let quanta = exact_unsigned_quanta(&drop, &anatomy.dissipation_quantum_zeptojoules)
        .ok_or(PsiSettlementError::DissipationNotQuantized)?;
    let next_dissipated = predecessor
        .dissipated_quanta
        .checked_add(quanta)
        .ok_or(PsiSettlementError::ArithmeticWidth)?;
    if next_dissipated > anatomy.dissipation_capacity_quanta {
        return Ok(predecessor);
    }
    Ok(PsiRingState {
        amplitude_quanta: anatomy.node_amplitude_quanta,
        phase_thirds: canonical_phase_thirds(all_trits()[minimum_index]),
        winding: all_trits()[minimum_index],
        dissipated_quanta: next_dissipated,
    })
}

fn ring_energy(anatomy: &PsiRingAnatomy, candidate: BalancedTrit, target: BalancedTrit) -> Exact {
    let constraint = if candidate == target {
        -Exact::from_integer(BigInt::from(3_u8)) * &anatomy.dsf_coupling_zeptojoules
    } else {
        Exact::new(BigInt::from(3_u8), BigInt::from(2_u8)) * &anatomy.dsf_coupling_zeptojoules
    };
    &anatomy.rest_energy_zeptojoules[trit_index(candidate)] + constraint
}

fn all_trits() -> [BalancedTrit; 3] {
    [
        BalancedTrit::Negative,
        BalancedTrit::Quiescent,
        BalancedTrit::Positive,
    ]
}

fn trit_index(value: BalancedTrit) -> usize {
    match value {
        BalancedTrit::Negative => 0,
        BalancedTrit::Quiescent => 1,
        BalancedTrit::Positive => 2,
    }
}

fn canonical_phase_thirds(winding: BalancedTrit) -> [i8; 3] {
    match winding {
        BalancedTrit::Negative => [0, -1, 1],
        BalancedTrit::Quiescent => [0, 0, 0],
        BalancedTrit::Positive => [0, 1, -1],
    }
}

fn exact_unsigned_quanta(energy: &Exact, quantum: &Exact) -> Option<u128> {
    if energy <= &Exact::zero() || quantum <= &Exact::zero() {
        return None;
    }
    let ratio = energy / quantum;
    if !ratio.is_integer() || ratio.is_negative() {
        return None;
    }
    ratio.to_integer().to_u128()
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct GatePsiContact {
    ring_index: usize,
    node_index: usize,
    preferred_phase_third: i8,
    open_minus_closed_coupling_zeptojoules: Exact,
}

impl GatePsiContact {
    pub(crate) fn new(
        ring_index: usize,
        node_index: usize,
        preferred_phase_third: i8,
        open_minus_closed_coupling_zeptojoules: Exact,
    ) -> Result<Self, GateSettlementError> {
        if node_index >= 3
            || !(-1..=1).contains(&preferred_phase_third)
            || open_minus_closed_coupling_zeptojoules < Exact::zero()
        {
            return Err(GateSettlementError::InvalidPsiContact);
        }
        Ok(Self {
            ring_index,
            node_index,
            preferred_phase_third,
            open_minus_closed_coupling_zeptojoules,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct TwoStateGateAnatomy {
    population: u128,
    gating_charge_elementary: i128,
    chemical_open_minus_closed_zeptojoules: Exact,
    dissipation_quantum_zeptojoules: Exact,
    dissipation_capacity_quanta: u128,
    single_channel_conductance_picosiemens: ExactRational,
    reversal_potential_millivolts: ExactRational,
    psi_contacts: Box<[GatePsiContact]>,
}

impl TwoStateGateAnatomy {
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn new(
        population: u128,
        gating_charge_elementary: i128,
        chemical_open_minus_closed_zeptojoules: Exact,
        dissipation_quantum_zeptojoules: Exact,
        dissipation_capacity_quanta: u128,
        single_channel_conductance_picosiemens: ExactRational,
        reversal_potential_millivolts: ExactRational,
        psi_contacts: Vec<GatePsiContact>,
        psi_ring_count: usize,
    ) -> Result<Self, GateSettlementError> {
        if population == 0
            || dissipation_quantum_zeptojoules <= Exact::zero()
            || single_channel_conductance_picosiemens.parts().0 < 0
        {
            return Err(GateSettlementError::InvalidAnatomy);
        }
        if psi_contacts
            .iter()
            .any(|contact| contact.ring_index >= psi_ring_count)
        {
            return Err(GateSettlementError::ContactOutsidePsiAnatomy);
        }
        Ok(Self {
            population,
            gating_charge_elementary,
            chemical_open_minus_closed_zeptojoules,
            dissipation_quantum_zeptojoules,
            dissipation_capacity_quanta,
            single_channel_conductance_picosiemens,
            reversal_potential_millivolts,
            psi_contacts: psi_contacts.into_boxed_slice(),
        })
    }

    pub(crate) fn dissipation_capacity_quanta(&self) -> u128 {
        self.dissipation_capacity_quanta
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct TwoStateGateState {
    open_population: u128,
    dissipated_quanta: u128,
}

impl TwoStateGateState {
    pub(crate) fn genesis(open_population: u128) -> Self {
        Self {
            open_population,
            dissipated_quanta: 0,
        }
    }

    pub(crate) fn open_population(self) -> u128 {
        self.open_population
    }

    pub(crate) fn dissipated_quanta(self) -> u128 {
        self.dissipated_quanta
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct CarrierReservoirs {
    intracellular: u128,
    extracellular: u128,
}

impl CarrierReservoirs {
    pub(crate) fn new(intracellular: u128, extracellular: u128) -> Self {
        Self {
            intracellular,
            extracellular,
        }
    }

    pub(crate) fn total(self) -> Option<u128> {
        self.intracellular.checked_add(self.extracellular)
    }

    pub(crate) fn intracellular(self) -> u128 {
        self.intracellular
    }

    pub(crate) fn extracellular(self) -> u128 {
        self.extracellular
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryLaneAnatomy {
    catalyst_per_extent: u128,
    fuel_per_extent: u128,
    spent_per_extent: u128,
    exported_heat_per_extent: u128,
    fuel_capacity: u128,
    spent_capacity: u128,
    exported_heat_capacity: u128,
}

impl RecoveryLaneAnatomy {
    pub(crate) fn new(
        catalyst_per_extent: u128,
        fuel_per_extent: u128,
        spent_per_extent: u128,
        exported_heat_per_extent: u128,
        fuel_capacity: u128,
        spent_capacity: u128,
        exported_heat_capacity: u128,
    ) -> Result<Self, RecoveryError> {
        if catalyst_per_extent == 0
            || fuel_per_extent == 0
            || spent_per_extent == 0
            || exported_heat_per_extent == 0
            || fuel_per_extent != spent_per_extent
        {
            return Err(RecoveryError::InvalidAnatomy);
        }
        Ok(Self {
            catalyst_per_extent,
            fuel_per_extent,
            spent_per_extent,
            exported_heat_per_extent,
            fuel_capacity,
            spent_capacity,
            exported_heat_capacity,
        })
    }

    pub(crate) fn capacities(self) -> (u128, u128, u128) {
        (
            self.fuel_capacity,
            self.spent_capacity,
            self.exported_heat_capacity,
        )
    }

    pub(crate) fn stoichiometry(self) -> (u128, u128, u128, u128) {
        (
            self.catalyst_per_extent,
            self.fuel_per_extent,
            self.spent_per_extent,
            self.exported_heat_per_extent,
        )
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryLaneState {
    fuel_quanta: u128,
    spent_quanta: u128,
    exported_heat_quanta: u128,
}

impl RecoveryLaneState {
    pub(crate) fn new(fuel_quanta: u128) -> Self {
        Self {
            fuel_quanta,
            spent_quanta: 0,
            exported_heat_quanta: 0,
        }
    }

    pub(crate) fn physical_parts(self) -> (u128, u128, u128) {
        (
            self.fuel_quanta,
            self.spent_quanta,
            self.exported_heat_quanta,
        )
    }

    pub(crate) fn from_physical_parts(
        anatomy: RecoveryLaneAnatomy,
        fuel_quanta: u128,
        spent_quanta: u128,
        exported_heat_quanta: u128,
    ) -> Result<Self, RecoveryError> {
        let (fuel_capacity, spent_capacity, heat_capacity) = anatomy.capacities();
        if fuel_quanta > fuel_capacity
            || spent_quanta > spent_capacity
            || exported_heat_quanta > heat_capacity
        {
            return Err(RecoveryError::InvalidAnatomy);
        }
        Ok(Self {
            fuel_quanta,
            spent_quanta,
            exported_heat_quanta,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryAnatomy {
    psi_lanes: Box<[RecoveryLaneAnatomy]>,
    gate_lane: RecoveryLaneAnatomy,
    plastic_lane: RecoveryLaneAnatomy,
}

impl RecoveryAnatomy {
    pub(crate) fn new(
        psi_lanes: Vec<RecoveryLaneAnatomy>,
        gate_lane: RecoveryLaneAnatomy,
        plastic_lane: RecoveryLaneAnatomy,
        psi_ring_count: usize,
    ) -> Result<Self, RecoveryError> {
        if psi_lanes.len() != psi_ring_count {
            return Err(RecoveryError::AnatomyWidth);
        }
        Ok(Self {
            psi_lanes: psi_lanes.into_boxed_slice(),
            gate_lane,
            plastic_lane,
        })
    }

    pub(crate) fn lane(&self, address: RecoveryLaneAddress) -> Option<RecoveryLaneAnatomy> {
        match address {
            RecoveryLaneAddress::Psi(index) => self.psi_lanes.get(index).copied(),
            RecoveryLaneAddress::Gate => Some(self.gate_lane),
            RecoveryLaneAddress::Plastic => Some(self.plastic_lane),
        }
    }

    pub(crate) fn psi_lane_count(&self) -> usize {
        self.psi_lanes.len()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryState {
    psi_lanes: Box<[RecoveryLaneState]>,
    gate_lane: RecoveryLaneState,
    plastic_lane: RecoveryLaneState,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum RecoveryLaneAddress {
    Psi(usize),
    Gate,
    Plastic,
}

impl RecoveryState {
    pub(crate) fn new(
        psi_lanes: Vec<RecoveryLaneState>,
        gate_lane: RecoveryLaneState,
        plastic_lane: RecoveryLaneState,
    ) -> Self {
        Self {
            psi_lanes: psi_lanes.into_boxed_slice(),
            gate_lane,
            plastic_lane,
        }
    }

    pub(crate) fn lane(&self, address: RecoveryLaneAddress) -> Option<RecoveryLaneState> {
        match address {
            RecoveryLaneAddress::Psi(index) => self.psi_lanes.get(index).copied(),
            RecoveryLaneAddress::Gate => Some(self.gate_lane),
            RecoveryLaneAddress::Plastic => Some(self.plastic_lane),
        }
    }

    pub(crate) fn replace_lane(
        &mut self,
        address: RecoveryLaneAddress,
        successor: RecoveryLaneState,
    ) -> Result<(), RecoveryError> {
        match address {
            RecoveryLaneAddress::Psi(index) => {
                *self
                    .psi_lanes
                    .get_mut(index)
                    .ok_or(RecoveryError::AnatomyWidth)? = successor;
            }
            RecoveryLaneAddress::Gate => self.gate_lane = successor,
            RecoveryLaneAddress::Plastic => self.plastic_lane = successor,
        }
        Ok(())
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum RecoveryError {
    InvalidAnatomy,
    AnatomyWidth,
    ArithmeticWidth,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DnaExpressionAnatomy {
    catalyst_per_extent: u128,
    substrate_per_extent: u128,
    fuel_per_extent: u128,
    product_per_extent: u128,
    waste_per_extent: u128,
    product_capacity: u128,
    waste_capacity: u128,
}

impl DnaExpressionAnatomy {
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn new(
        catalyst_per_extent: u128,
        substrate_per_extent: u128,
        fuel_per_extent: u128,
        product_per_extent: u128,
        waste_per_extent: u128,
        product_capacity: u128,
        waste_capacity: u128,
    ) -> Result<Self, DnaExpressionError> {
        if catalyst_per_extent == 0
            || substrate_per_extent == 0
            || fuel_per_extent == 0
            || product_per_extent == 0
            || waste_per_extent == 0
            || substrate_per_extent != product_per_extent
            || fuel_per_extent != waste_per_extent
        {
            return Err(DnaExpressionError::InvalidAnatomy);
        }
        Ok(Self {
            catalyst_per_extent,
            substrate_per_extent,
            fuel_per_extent,
            product_per_extent,
            waste_per_extent,
            product_capacity,
            waste_capacity,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DnaExpressionState {
    substrate_quanta: u128,
    fuel_quanta: u128,
    expressed_product_quanta: u128,
    waste_quanta: u128,
}

impl DnaExpressionState {
    pub(crate) fn new(substrate_quanta: u128, fuel_quanta: u128) -> Self {
        Self {
            substrate_quanta,
            fuel_quanta,
            expressed_product_quanta: 0,
            waste_quanta: 0,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DnaExpressionError {
    InvalidAnatomy,
    ArithmeticWidth,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PlasticSupportAnatomy {
    elastic_energy_scale_zeptojoules: ExactRational,
    yield_stress_zeptojoules: ExactRational,
    closed_coordinate_nanometres: ExactRational,
    open_coordinate_nanometres: ExactRational,
    dissipation_quantum_zeptojoules: ExactRational,
    dissipation_capacity_quanta: u128,
}

impl PlasticSupportAnatomy {
    pub(crate) fn new(
        elastic_energy_scale_zeptojoules: ExactRational,
        yield_stress_zeptojoules: ExactRational,
        closed_coordinate_nanometres: ExactRational,
        open_coordinate_nanometres: ExactRational,
        dissipation_quantum_zeptojoules: ExactRational,
        dissipation_capacity_quanta: u128,
    ) -> Result<Self, PlasticityError> {
        let zero = ExactRational::integer(0);
        if elastic_energy_scale_zeptojoules.checked_cmp(yield_stress_zeptojoules)?
            != core::cmp::Ordering::Greater
            || yield_stress_zeptojoules.checked_cmp(zero)? != core::cmp::Ordering::Greater
            || closed_coordinate_nanometres.checked_cmp(zero)? != core::cmp::Ordering::Greater
            || open_coordinate_nanometres.checked_cmp(zero)? != core::cmp::Ordering::Greater
            || dissipation_quantum_zeptojoules.checked_cmp(zero)? != core::cmp::Ordering::Greater
        {
            return Err(PlasticityError::InvalidAnatomy);
        }
        Ok(Self {
            elastic_energy_scale_zeptojoules,
            yield_stress_zeptojoules,
            closed_coordinate_nanometres,
            open_coordinate_nanometres,
            dissipation_quantum_zeptojoules,
            dissipation_capacity_quanta,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PlasticSupportState {
    rest_length_nanometres: ExactRational,
    dissipated_quanta: u128,
}

impl PlasticSupportState {
    pub(crate) fn new(rest_length_nanometres: ExactRational) -> Result<Self, PlasticityError> {
        if rest_length_nanometres.checked_cmp(ExactRational::integer(0))?
            != core::cmp::Ordering::Greater
        {
            return Err(PlasticityError::InvalidState);
        }
        Ok(Self {
            rest_length_nanometres,
            dissipated_quanta: 0,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PlasticityError {
    InvalidAnatomy,
    InvalidState,
    DissipationNotQuantized,
    DissipationCapacityUnavailable,
    ArithmeticWidth,
}

impl From<ExactRationalError> for PlasticityError {
    fn from(value: ExactRationalError) -> Self {
        match value {
            ExactRationalError::ArithmeticWidth => Self::ArithmeticWidth,
            ExactRationalError::ZeroDenominator | ExactRationalError::NonCanonicalRatio => {
                Self::InvalidState
            }
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PlasticityAvailability {
    ExecutedExactReturnMapping,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct PlasticSettlement {
    successor: PlasticSupportState,
    changed: bool,
}

/// Settle a one-dimensional elastic support against an exact material yield
/// surface. Below yield, the rest geometry is unchanged. Beyond yield, the
/// successor rest length is the exact return-map solution whose stress is
/// exactly `+Y` or `-Y`; the released elastic work enters the mounted finite
/// dissipation reservoir.
fn settle_plastic_support(
    anatomy: &PlasticSupportAnatomy,
    predecessor: &PlasticSupportState,
    gate_population: u128,
    open_population: u128,
) -> Result<PlasticSettlement, PlasticityError> {
    if gate_population == 0 || open_population > gate_population {
        return Err(PlasticityError::InvalidState);
    }
    let closed_population = gate_population - open_population;
    let observed_coordinate = anatomy
        .closed_coordinate_nanometres
        .checked_mul_unsigned(closed_population)?
        .checked_add(
            anatomy
                .open_coordinate_nanometres
                .checked_mul_unsigned(open_population)?,
        )?
        .checked_div_unsigned(gate_population)?;
    let trial_strain = observed_coordinate
        .checked_sub(predecessor.rest_length_nanometres)?
        .checked_div(predecessor.rest_length_nanometres)?;
    let trial_stress = anatomy
        .elastic_energy_scale_zeptojoules
        .checked_mul(trial_strain)?;
    if trial_stress
        .checked_abs()?
        .checked_cmp(anatomy.yield_stress_zeptojoules)?
        != core::cmp::Ordering::Greater
    {
        return Ok(PlasticSettlement {
            successor: predecessor.clone(),
            changed: false,
        });
    }

    let return_denominator = if trial_stress.parts().0 > 0 {
        anatomy
            .elastic_energy_scale_zeptojoules
            .checked_add(anatomy.yield_stress_zeptojoules)?
    } else {
        anatomy
            .elastic_energy_scale_zeptojoules
            .checked_sub(anatomy.yield_stress_zeptojoules)?
    };
    let next_rest_length = observed_coordinate
        .checked_mul(anatomy.elastic_energy_scale_zeptojoules)?
        .checked_div(return_denominator)?;
    if next_rest_length.checked_cmp(ExactRational::integer(0))? != core::cmp::Ordering::Greater {
        return Err(PlasticityError::InvalidState);
    }
    let returned_strain = observed_coordinate
        .checked_sub(next_rest_length)?
        .checked_div(next_rest_length)?;
    let returned_stress = anatomy
        .elastic_energy_scale_zeptojoules
        .checked_mul(returned_strain)?;
    let expected_stress = if trial_stress.parts().0 > 0 {
        anatomy.yield_stress_zeptojoules
    } else {
        anatomy.yield_stress_zeptojoules.checked_neg()?
    };
    if returned_stress != expected_stress {
        return Err(PlasticityError::ArithmeticWidth);
    }

    let trial_energy = anatomy
        .elastic_energy_scale_zeptojoules
        .checked_mul(trial_strain)?
        .checked_mul(trial_strain)?
        .checked_div_unsigned(2)?;
    let returned_energy = anatomy
        .elastic_energy_scale_zeptojoules
        .checked_mul(returned_strain)?
        .checked_mul(returned_strain)?
        .checked_div_unsigned(2)?;
    let released_energy = trial_energy.checked_sub(returned_energy)?;
    let released_ratio = released_energy.checked_div(anatomy.dissipation_quantum_zeptojoules)?;
    let (released_numerator, released_denominator) = released_ratio.parts();
    if released_numerator <= 0 || released_denominator != 1 {
        return Err(PlasticityError::DissipationNotQuantized);
    }
    let released_quanta =
        u128::try_from(released_numerator).map_err(|_| PlasticityError::ArithmeticWidth)?;
    let next_dissipated = predecessor
        .dissipated_quanta
        .checked_add(released_quanta)
        .ok_or(PlasticityError::ArithmeticWidth)?;
    if next_dissipated > anatomy.dissipation_capacity_quanta {
        return Err(PlasticityError::DissipationCapacityUnavailable);
    }
    Ok(PlasticSettlement {
        successor: PlasticSupportState {
            rest_length_nanometres: next_rest_length,
            dissipated_quanta: next_dissipated,
        },
        changed: true,
    })
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct NeuronPhysicalState {
    pub(crate) psi: PsiKrimelackState,
    pub(crate) gate: TwoStateGateState,
    pub(crate) membrane: LocalMembraneConductanceState<1>,
    pub(crate) carriers: CarrierReservoirs,
    pub(crate) recovery: RecoveryState,
    pub(crate) dna_expression: DnaExpressionState,
    pub(crate) plastic: PlasticSupportState,
    /// Retained sub-quantum optical transduction residue (2026-08-05 ratified
    /// quantized-light law): the exact-rational remainder of the continuous
    /// `2·L·T` integral not yet deliverable as a whole gate-lattice quantum.
    /// Always inside `[0, gate dissipation quantum)`. Same retained-residue
    /// discipline as the charge-carrier phases.
    pub(crate) optical_quantum_residue: ExactRational,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct NeuronPhysicalAnatomy {
    mathloom: MathLoomAnatomy,
    psi: PsiKrimelackAnatomy,
    gate: TwoStateGateAnatomy,
    capacitance: MembraneCapacitance,
    recovery: RecoveryAnatomy,
    dna_expression: DnaExpressionAnatomy,
    plastic: PlasticSupportAnatomy,
}

impl NeuronPhysicalAnatomy {
    pub(crate) fn new(
        mathloom: MathLoomAnatomy,
        psi: PsiKrimelackAnatomy,
        gate: TwoStateGateAnatomy,
        capacitance: MembraneCapacitance,
        recovery: RecoveryAnatomy,
        dna_expression: DnaExpressionAnatomy,
        plastic: PlasticSupportAnatomy,
    ) -> Result<Self, NeuronPhysicalError> {
        if psi.positions != mathloom.positions() {
            return Err(NeuronPhysicalError::AnatomyMismatch);
        }
        if recovery.psi_lanes.len() != psi.ring_count() {
            return Err(NeuronPhysicalError::AnatomyMismatch);
        }
        Ok(Self {
            mathloom,
            psi,
            gate,
            capacitance,
            recovery,
            dna_expression,
            plastic,
        })
    }

    pub(crate) fn capacitance(&self) -> MembraneCapacitance {
        self.capacitance
    }

    pub(crate) fn recovery_anatomy(&self) -> &RecoveryAnatomy {
        &self.recovery
    }

    pub(crate) fn gate_dissipation_capacity_quanta(&self) -> u128 {
        self.gate.dissipation_capacity_quanta()
    }

    /// The receiving gate's exact dissipation-lattice step. Quantized optical
    /// delivery derives its whole-quantum count from THIS anatomy value; no
    /// new constant is introduced anywhere.
    pub(crate) fn gate_dissipation_quantum_zeptojoules(&self) -> &Exact {
        &self.gate.dissipation_quantum_zeptojoules
    }

    pub(crate) fn recovery_full_saturation_requirement(
        &self,
        address: RecoveryLaneAddress,
    ) -> Result<RecoverySaturationRequirement, NeuronPhysicalError> {
        let lane = self
            .recovery
            .lane(address)
            .ok_or(RecoveryError::AnatomyWidth)?;
        let dissipation_capacity = match address {
            RecoveryLaneAddress::Psi(index) => {
                self.psi
                    .rings
                    .get(index)
                    .ok_or(RecoveryError::AnatomyWidth)?
                    .dissipation_capacity_quanta
            }
            RecoveryLaneAddress::Gate => self.gate.dissipation_capacity_quanta,
            RecoveryLaneAddress::Plastic => self.plastic.dissipation_capacity_quanta,
        };
        let (catalyst_per_extent, fuel_per_extent, spent_per_extent, heat_per_extent) =
            lane.stoichiometry();
        if dissipation_capacity % heat_per_extent != 0 {
            return Err(RecoveryError::InvalidAnatomy.into());
        }
        let extents = dissipation_capacity / heat_per_extent;
        Ok(RecoverySaturationRequirement {
            catalyst_quanta: extents
                .checked_mul(catalyst_per_extent)
                .ok_or(RecoveryError::ArithmeticWidth)?,
            fuel_quanta: extents
                .checked_mul(fuel_per_extent)
                .ok_or(RecoveryError::ArithmeticWidth)?,
            spent_quanta: extents
                .checked_mul(spent_per_extent)
                .ok_or(RecoveryError::ArithmeticWidth)?,
            heat_quanta: extents
                .checked_mul(heat_per_extent)
                .ok_or(RecoveryError::ArithmeticWidth)?,
        })
    }

    pub(crate) fn psi_ring_count(&self) -> usize {
        self.psi.ring_count()
    }

    pub(crate) fn sparse_delta_coordinate_count(&self) -> Option<usize> {
        self.psi.ring_count().checked_mul(5)?.checked_add(20)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoverySaturationRequirement {
    pub(crate) catalyst_quanta: u128,
    pub(crate) fuel_quanta: u128,
    pub(crate) spent_quanta: u128,
    pub(crate) heat_quanta: u128,
}

impl NeuronPhysicalState {
    pub(crate) fn membrane_state(
        &self,
    ) -> crate::elementary_charge_membrane::ElementaryChargeMembraneState {
        self.membrane.membrane()
    }

    pub(crate) fn carrier_reservoirs(&self) -> CarrierReservoirs {
        self.carriers
    }

    pub(crate) fn resident_bytes(&self) -> Option<usize> {
        core::mem::size_of::<Self>()
            .checked_add(
                self.psi
                    .rings
                    .len()
                    .checked_mul(core::mem::size_of::<PsiRingState>())?,
            )?
            .checked_add(
                self.recovery
                    .psi_lanes
                    .len()
                    .checked_mul(core::mem::size_of::<RecoveryLaneState>())?,
            )
    }
}

const NEURON_ANATOMY_CODEC_MAGIC: &[u8; 8] = b"GLNPA02\0";
const NEURON_CELL_CODEC_MAGIC: &[u8; 8] = b"GLNPC02\0";
const MIN_PSI_RING_ANATOMY_BYTES: usize = 164;
const MIN_GATE_PSI_CONTACT_BYTES: usize = 35;
const RECOVERY_LANE_ANATOMY_BYTES: usize = 112;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum NeuronAnatomyCodecError {
    InvalidEncoding,
    InvalidAnatomy,
    ArithmeticWidth,
    State(NeuronStateCodecError),
}

impl From<NeuronStateCodecError> for NeuronAnatomyCodecError {
    fn from(value: NeuronStateCodecError) -> Self {
        Self::State(value)
    }
}

/// Encode immutable physical anatomy exactly. This carrier chooses no anatomy
/// and derives no coefficients; it only makes already-admitted anatomy
/// restartable with the neuron that uses it.
pub(crate) fn encode_neuron_physical_anatomy(
    anatomy: &NeuronPhysicalAnatomy,
) -> Result<Vec<u8>, NeuronAnatomyCodecError> {
    let mut encoded = Vec::new();
    encoded.extend_from_slice(NEURON_ANATOMY_CODEC_MAGIC);
    push_anatomy_usize(&mut encoded, anatomy.mathloom.positions())?;
    push_anatomy_usize(&mut encoded, anatomy.psi.constraint_count)?;
    push_anatomy_usize(&mut encoded, anatomy.psi.rings.len())?;
    for ring in &anatomy.psi.rings {
        for value in ring.node_amplitude_quanta {
            encoded.extend_from_slice(&value.to_le_bytes());
        }
        for value in &ring.rest_energy_zeptojoules {
            push_big_rational(&mut encoded, value)?;
        }
        push_big_rational(&mut encoded, &ring.dsf_coupling_zeptojoules)?;
        push_big_rational(&mut encoded, &ring.dissipation_quantum_zeptojoules)?;
        encoded.extend_from_slice(&ring.dissipation_capacity_quanta.to_le_bytes());
        for row in ring.reachable {
            for value in row {
                encoded.push(u8::from(value));
            }
        }
        encoded.push(ring.genesis_winding as i8 as u8);
    }

    encoded.extend_from_slice(&anatomy.gate.population.to_le_bytes());
    encoded.extend_from_slice(&anatomy.gate.gating_charge_elementary.to_le_bytes());
    push_big_rational(
        &mut encoded,
        &anatomy.gate.chemical_open_minus_closed_zeptojoules,
    )?;
    push_big_rational(&mut encoded, &anatomy.gate.dissipation_quantum_zeptojoules)?;
    encoded.extend_from_slice(&anatomy.gate.dissipation_capacity_quanta.to_le_bytes());
    push_exact_rational(
        &mut encoded,
        anatomy.gate.single_channel_conductance_picosiemens,
    );
    push_exact_rational(&mut encoded, anatomy.gate.reversal_potential_millivolts);
    push_anatomy_usize(&mut encoded, anatomy.gate.psi_contacts.len())?;
    for contact in &anatomy.gate.psi_contacts {
        push_anatomy_usize(&mut encoded, contact.ring_index)?;
        push_anatomy_usize(&mut encoded, contact.node_index)?;
        encoded.push(contact.preferred_phase_third as u8);
        push_big_rational(
            &mut encoded,
            &contact.open_minus_closed_coupling_zeptojoules,
        )?;
    }
    push_exact_rational(&mut encoded, anatomy.capacitance.picofarads());

    push_anatomy_usize(&mut encoded, anatomy.recovery.psi_lanes.len())?;
    for lane in &anatomy.recovery.psi_lanes {
        push_recovery_lane_anatomy(&mut encoded, *lane);
    }
    push_recovery_lane_anatomy(&mut encoded, anatomy.recovery.gate_lane);
    push_recovery_lane_anatomy(&mut encoded, anatomy.recovery.plastic_lane);

    for value in [
        anatomy.dna_expression.catalyst_per_extent,
        anatomy.dna_expression.substrate_per_extent,
        anatomy.dna_expression.fuel_per_extent,
        anatomy.dna_expression.product_per_extent,
        anatomy.dna_expression.waste_per_extent,
        anatomy.dna_expression.product_capacity,
        anatomy.dna_expression.waste_capacity,
    ] {
        encoded.extend_from_slice(&value.to_le_bytes());
    }
    for value in [
        anatomy.plastic.elastic_energy_scale_zeptojoules,
        anatomy.plastic.yield_stress_zeptojoules,
        anatomy.plastic.closed_coordinate_nanometres,
        anatomy.plastic.open_coordinate_nanometres,
        anatomy.plastic.dissipation_quantum_zeptojoules,
    ] {
        push_exact_rational(&mut encoded, value);
    }
    encoded.extend_from_slice(&anatomy.plastic.dissipation_capacity_quanta.to_le_bytes());
    Ok(encoded)
}

pub(crate) fn decode_neuron_physical_anatomy(
    encoded: &[u8],
) -> Result<NeuronPhysicalAnatomy, NeuronAnatomyCodecError> {
    let mut reader = NeuronAnatomyReader::new(encoded);
    if reader.take(NEURON_ANATOMY_CODEC_MAGIC.len())? != NEURON_ANATOMY_CODEC_MAGIC {
        return Err(NeuronAnatomyCodecError::InvalidEncoding);
    }
    let positions = reader.usize()?;
    let constraint_count = reader.usize()?;
    let ring_count = reader.usize()?;
    let required_rings = constraint_count
        .checked_mul(2)
        .and_then(|value| value.checked_mul(positions))
        .ok_or(NeuronAnatomyCodecError::ArithmeticWidth)?;
    if positions == 0 || ring_count != required_rings {
        return Err(NeuronAnatomyCodecError::InvalidAnatomy);
    }
    reader.require_records(ring_count, MIN_PSI_RING_ANATOMY_BYTES)?;
    let mut rings = Vec::new();
    rings
        .try_reserve_exact(ring_count)
        .map_err(|_| NeuronAnatomyCodecError::ArithmeticWidth)?;
    for _ in 0..ring_count {
        let node_amplitude_quanta = [reader.u128()?, reader.u128()?, reader.u128()?];
        let rest_energy_zeptojoules = [
            reader.big_rational()?,
            reader.big_rational()?,
            reader.big_rational()?,
        ];
        let dsf_coupling_zeptojoules = reader.big_rational()?;
        let dissipation_quantum_zeptojoules = reader.big_rational()?;
        let dissipation_capacity_quanta = reader.u128()?;
        let mut reachable = [[false; 3]; 3];
        for row in &mut reachable {
            for value in row {
                *value = reader.boolean()?;
            }
        }
        let genesis_winding =
            decode_winding(reader.i8()?).map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?;
        rings.push(
            PsiRingAnatomy::new(
                node_amplitude_quanta,
                rest_energy_zeptojoules,
                dsf_coupling_zeptojoules,
                dissipation_quantum_zeptojoules,
                dissipation_capacity_quanta,
                reachable,
                genesis_winding,
            )
            .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?,
        );
    }
    let psi = PsiKrimelackAnatomy::new(positions, constraint_count, rings)
        .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?;
    let mathloom =
        MathLoomAnatomy::new(positions).map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?;

    let population = reader.u128()?;
    let gating_charge_elementary = reader.i128()?;
    let chemical_open_minus_closed_zeptojoules = reader.big_rational()?;
    let gate_dissipation_quantum = reader.big_rational()?;
    let gate_dissipation_capacity = reader.u128()?;
    let single_channel_conductance = reader.exact_rational()?;
    let reversal_potential = reader.exact_rational()?;
    let contact_count = reader.usize()?;
    reader.require_records(contact_count, MIN_GATE_PSI_CONTACT_BYTES)?;
    let mut contacts = Vec::new();
    contacts
        .try_reserve_exact(contact_count)
        .map_err(|_| NeuronAnatomyCodecError::ArithmeticWidth)?;
    for _ in 0..contact_count {
        contacts.push(
            GatePsiContact::new(
                reader.usize()?,
                reader.usize()?,
                reader.i8()?,
                reader.big_rational()?,
            )
            .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?,
        );
    }
    let gate = TwoStateGateAnatomy::new(
        population,
        gating_charge_elementary,
        chemical_open_minus_closed_zeptojoules,
        gate_dissipation_quantum,
        gate_dissipation_capacity,
        single_channel_conductance,
        reversal_potential,
        contacts,
        psi.ring_count(),
    )
    .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?;
    let capacitance = MembraneCapacitance::new(reader.exact_rational()?)
        .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?;

    let recovery_lane_count = reader.usize()?;
    if recovery_lane_count != psi.ring_count() {
        return Err(NeuronAnatomyCodecError::InvalidAnatomy);
    }
    reader.require_records(recovery_lane_count, RECOVERY_LANE_ANATOMY_BYTES)?;
    let mut recovery_lanes = Vec::new();
    recovery_lanes
        .try_reserve_exact(recovery_lane_count)
        .map_err(|_| NeuronAnatomyCodecError::ArithmeticWidth)?;
    for _ in 0..recovery_lane_count {
        recovery_lanes.push(reader.recovery_lane()?);
    }
    let recovery = RecoveryAnatomy::new(
        recovery_lanes,
        reader.recovery_lane()?,
        reader.recovery_lane()?,
        psi.ring_count(),
    )
    .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?;
    let dna_expression = DnaExpressionAnatomy::new(
        reader.u128()?,
        reader.u128()?,
        reader.u128()?,
        reader.u128()?,
        reader.u128()?,
        reader.u128()?,
        reader.u128()?,
    )
    .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?;
    let plastic = PlasticSupportAnatomy::new(
        reader.exact_rational()?,
        reader.exact_rational()?,
        reader.exact_rational()?,
        reader.exact_rational()?,
        reader.exact_rational()?,
        reader.u128()?,
    )
    .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)?;
    if !reader.finished() {
        return Err(NeuronAnatomyCodecError::InvalidEncoding);
    }
    NeuronPhysicalAnatomy::new(
        mathloom,
        psi,
        gate,
        capacitance,
        recovery,
        dna_expression,
        plastic,
    )
    .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)
}

pub(crate) fn encode_neuron_physical_cell(
    anatomy: &NeuronPhysicalAnatomy,
    state: &NeuronPhysicalState,
) -> Result<Vec<u8>, NeuronAnatomyCodecError> {
    let anatomy_bytes = encode_neuron_physical_anatomy(anatomy)?;
    let state_bytes = encode_neuron_physical_state(anatomy, state)?;
    let mut encoded = Vec::new();
    encoded.extend_from_slice(NEURON_CELL_CODEC_MAGIC);
    push_anatomy_usize(&mut encoded, anatomy_bytes.len())?;
    push_anatomy_usize(&mut encoded, state_bytes.len())?;
    encoded.extend_from_slice(&anatomy_bytes);
    encoded.extend_from_slice(&state_bytes);
    Ok(encoded)
}

pub(crate) fn decode_neuron_physical_cell(
    encoded: &[u8],
) -> Result<(NeuronPhysicalAnatomy, NeuronPhysicalState), NeuronAnatomyCodecError> {
    let mut reader = NeuronAnatomyReader::new(encoded);
    if reader.take(NEURON_CELL_CODEC_MAGIC.len())? != NEURON_CELL_CODEC_MAGIC {
        return Err(NeuronAnatomyCodecError::InvalidEncoding);
    }
    let anatomy_len = reader.usize()?;
    let state_len = reader.usize()?;
    let anatomy = decode_neuron_physical_anatomy(reader.take(anatomy_len)?)?;
    let state = decode_neuron_physical_state(&anatomy, reader.take(state_len)?)?;
    if !reader.finished() {
        return Err(NeuronAnatomyCodecError::InvalidEncoding);
    }
    Ok((anatomy, state))
}

fn push_anatomy_usize(encoded: &mut Vec<u8>, value: usize) -> Result<(), NeuronAnatomyCodecError> {
    encoded.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| NeuronAnatomyCodecError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

fn push_exact_rational(encoded: &mut Vec<u8>, value: ExactRational) {
    let (numerator, denominator) = value.parts();
    encoded.extend_from_slice(&numerator.to_le_bytes());
    encoded.extend_from_slice(&denominator.to_le_bytes());
}

fn push_big_rational(
    encoded: &mut Vec<u8>,
    value: &BigRational,
) -> Result<(), NeuronAnatomyCodecError> {
    for integer in [value.numer(), value.denom()] {
        let text = integer.to_string();
        push_anatomy_usize(encoded, text.len())?;
        encoded.extend_from_slice(text.as_bytes());
    }
    Ok(())
}

fn push_recovery_lane_anatomy(encoded: &mut Vec<u8>, lane: RecoveryLaneAnatomy) {
    for value in [
        lane.catalyst_per_extent,
        lane.fuel_per_extent,
        lane.spent_per_extent,
        lane.exported_heat_per_extent,
        lane.fuel_capacity,
        lane.spent_capacity,
        lane.exported_heat_capacity,
    ] {
        encoded.extend_from_slice(&value.to_le_bytes());
    }
}

struct NeuronAnatomyReader<'a> {
    encoded: &'a [u8],
    cursor: usize,
}

impl<'a> NeuronAnatomyReader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self { encoded, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], NeuronAnatomyCodecError> {
        let end = self
            .cursor
            .checked_add(count)
            .ok_or(NeuronAnatomyCodecError::ArithmeticWidth)?;
        let value = self
            .encoded
            .get(self.cursor..end)
            .ok_or(NeuronAnatomyCodecError::InvalidEncoding)?;
        self.cursor = end;
        Ok(value)
    }

    fn require_records(
        &self,
        count: usize,
        minimum_record_bytes: usize,
    ) -> Result<(), NeuronAnatomyCodecError> {
        let minimum_bytes = count
            .checked_mul(minimum_record_bytes)
            .ok_or(NeuronAnatomyCodecError::ArithmeticWidth)?;
        let remaining = self
            .encoded
            .len()
            .checked_sub(self.cursor)
            .ok_or(NeuronAnatomyCodecError::InvalidEncoding)?;
        if minimum_bytes > remaining {
            return Err(NeuronAnatomyCodecError::InvalidEncoding);
        }
        Ok(())
    }

    fn usize(&mut self) -> Result<usize, NeuronAnatomyCodecError> {
        usize::try_from(u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| NeuronAnatomyCodecError::InvalidEncoding)?,
        ))
        .map_err(|_| NeuronAnatomyCodecError::ArithmeticWidth)
    }

    fn u128(&mut self) -> Result<u128, NeuronAnatomyCodecError> {
        Ok(u128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| NeuronAnatomyCodecError::InvalidEncoding)?,
        ))
    }

    fn i128(&mut self) -> Result<i128, NeuronAnatomyCodecError> {
        Ok(i128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| NeuronAnatomyCodecError::InvalidEncoding)?,
        ))
    }

    fn i8(&mut self) -> Result<i8, NeuronAnatomyCodecError> {
        Ok(self.take(1)?[0] as i8)
    }

    fn boolean(&mut self) -> Result<bool, NeuronAnatomyCodecError> {
        match self.take(1)?[0] {
            0 => Ok(false),
            1 => Ok(true),
            _ => Err(NeuronAnatomyCodecError::InvalidEncoding),
        }
    }

    fn exact_rational(&mut self) -> Result<ExactRational, NeuronAnatomyCodecError> {
        ExactRational::new(self.i128()?, self.u128()?)
            .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)
    }

    fn big_rational(&mut self) -> Result<BigRational, NeuronAnatomyCodecError> {
        let numerator = self.big_integer()?;
        let denominator = self.big_integer()?;
        if denominator <= BigInt::zero() {
            return Err(NeuronAnatomyCodecError::InvalidAnatomy);
        }
        let value = BigRational::new(numerator.clone(), denominator.clone());
        if value.numer() != &numerator || value.denom() != &denominator {
            return Err(NeuronAnatomyCodecError::InvalidEncoding);
        }
        Ok(value)
    }

    fn big_integer(&mut self) -> Result<BigInt, NeuronAnatomyCodecError> {
        let length = self.usize()?;
        let text = std::str::from_utf8(self.take(length)?)
            .map_err(|_| NeuronAnatomyCodecError::InvalidEncoding)?;
        let value = text
            .parse::<BigInt>()
            .map_err(|_| NeuronAnatomyCodecError::InvalidEncoding)?;
        if value.to_string() != text {
            return Err(NeuronAnatomyCodecError::InvalidEncoding);
        }
        Ok(value)
    }

    fn recovery_lane(&mut self) -> Result<RecoveryLaneAnatomy, NeuronAnatomyCodecError> {
        RecoveryLaneAnatomy::new(
            self.u128()?,
            self.u128()?,
            self.u128()?,
            self.u128()?,
            self.u128()?,
            self.u128()?,
            self.u128()?,
        )
        .map_err(|_| NeuronAnatomyCodecError::InvalidAnatomy)
    }

    fn finished(&self) -> bool {
        self.cursor == self.encoded.len()
    }
}

const NEURON_STATE_CODEC_MAGIC: &[u8; 8] = b"GLNPS01\0";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum NeuronStateCodecError {
    AnatomyMismatch,
    InvalidEncoding,
    ArithmeticWidth,
}

pub(crate) fn encode_neuron_physical_state(
    anatomy: &NeuronPhysicalAnatomy,
    state: &NeuronPhysicalState,
) -> Result<Vec<u8>, NeuronStateCodecError> {
    if state.psi.rings.len() != anatomy.psi.rings.len()
        || state.recovery.psi_lanes.len() != anatomy.recovery.psi_lanes.len()
        || state.gate.open_population > anatomy.gate.population
        || state.gate.dissipated_quanta > anatomy.gate.dissipation_capacity_quanta
        || state.plastic.dissipated_quanta > anatomy.plastic.dissipation_capacity_quanta
        || state.dna_expression.expressed_product_quanta > anatomy.dna_expression.product_capacity
        || state.dna_expression.waste_quanta > anatomy.dna_expression.waste_capacity
        // Law 1 (threshold-integrated delivery, ratified 2026-08-05): the
        // receptor accumulator RETAINS energy across intervals until the
        // receiving gate's own opening threshold is reached, so a lawful
        // residue is routinely several whole quanta.  Its only canonical
        // bound is non-negativity; no anatomy number bounds it from above,
        // and inventing one would silently destroy retained energy.
        || rational_to_exact(state.optical_quantum_residue) < Exact::zero()
    {
        return Err(NeuronStateCodecError::AnatomyMismatch);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(NEURON_STATE_CODEC_MAGIC);
    push_usize(&mut encoded, state.psi.rings.len())?;
    for (ring, ring_anatomy) in state.psi.rings.iter().zip(anatomy.psi.rings.iter()) {
        if ring.amplitude_quanta != ring_anatomy.node_amplitude_quanta
            || ring.phase_thirds != canonical_phase_thirds(ring.winding)
            || ring.dissipated_quanta > ring_anatomy.dissipation_capacity_quanta
        {
            return Err(NeuronStateCodecError::AnatomyMismatch);
        }
        encoded.push(ring.winding as i8 as u8);
        push_u128(&mut encoded, ring.dissipated_quanta);
    }
    push_u128(&mut encoded, state.gate.open_population);
    push_u128(&mut encoded, state.gate.dissipated_quanta);
    push_i128(
        &mut encoded,
        state.membrane.membrane().separated_elementary_charges(),
    );
    push_phase(&mut encoded, state.membrane.membrane().carrier_phase());
    push_phase(&mut encoded, state.membrane.path_carrier_phases()[0]);
    push_u128(&mut encoded, state.carriers.intracellular);
    push_u128(&mut encoded, state.carriers.extracellular);
    push_usize(&mut encoded, state.recovery.psi_lanes.len())?;
    for (lane, lane_anatomy) in state
        .recovery
        .psi_lanes
        .iter()
        .zip(anatomy.recovery.psi_lanes.iter())
    {
        encode_recovery_lane(&mut encoded, *lane, *lane_anatomy)?;
    }
    encode_recovery_lane(
        &mut encoded,
        state.recovery.gate_lane,
        anatomy.recovery.gate_lane,
    )?;
    encode_recovery_lane(
        &mut encoded,
        state.recovery.plastic_lane,
        anatomy.recovery.plastic_lane,
    )?;
    push_u128(&mut encoded, state.dna_expression.substrate_quanta);
    push_u128(&mut encoded, state.dna_expression.fuel_quanta);
    push_u128(&mut encoded, state.dna_expression.expressed_product_quanta);
    push_u128(&mut encoded, state.dna_expression.waste_quanta);
    let (rest_numerator, rest_denominator) = state.plastic.rest_length_nanometres.parts();
    push_i128(&mut encoded, rest_numerator);
    push_u128(&mut encoded, rest_denominator);
    push_u128(&mut encoded, state.plastic.dissipated_quanta);
    // Retained quantized-optical sub-quantum residue (ratified 2026-08-05):
    // encoded with the same exact-rational fixed-width discipline as the
    // retained charge-carrier phases above.
    let (residue_numerator, residue_denominator) = state.optical_quantum_residue.parts();
    push_i128(&mut encoded, residue_numerator);
    push_u128(&mut encoded, residue_denominator);
    Ok(encoded)
}

pub(crate) fn decode_neuron_physical_state(
    anatomy: &NeuronPhysicalAnatomy,
    encoded: &[u8],
) -> Result<NeuronPhysicalState, NeuronStateCodecError> {
    let mut reader = NeuronStateReader::new(encoded);
    if reader.take(NEURON_STATE_CODEC_MAGIC.len())? != NEURON_STATE_CODEC_MAGIC {
        return Err(NeuronStateCodecError::InvalidEncoding);
    }
    let psi_count = reader.usize()?;
    if psi_count != anatomy.psi.rings.len() {
        return Err(NeuronStateCodecError::AnatomyMismatch);
    }
    let mut rings = Vec::with_capacity(psi_count);
    for ring_anatomy in &anatomy.psi.rings {
        let winding = decode_winding(reader.i8()?)?;
        let dissipated_quanta = reader.u128()?;
        if dissipated_quanta > ring_anatomy.dissipation_capacity_quanta {
            return Err(NeuronStateCodecError::AnatomyMismatch);
        }
        rings.push(PsiRingState {
            amplitude_quanta: ring_anatomy.node_amplitude_quanta,
            phase_thirds: canonical_phase_thirds(winding),
            winding,
            dissipated_quanta,
        });
    }
    let gate = TwoStateGateState {
        open_population: reader.u128()?,
        dissipated_quanta: reader.u128()?,
    };
    if gate.open_population > anatomy.gate.population
        || gate.dissipated_quanta > anatomy.gate.dissipation_capacity_quanta
    {
        return Err(NeuronStateCodecError::AnatomyMismatch);
    }
    let separated_elementary_charges = reader.i128()?;
    let membrane_phase = reader.phase()?;
    let path_phase = reader.phase()?;
    let membrane = LocalMembraneConductanceState::from_physical_parts(
        ElementaryChargeMembraneState::from_physical_parts(
            separated_elementary_charges,
            membrane_phase,
        ),
        [path_phase],
    );
    let carriers = CarrierReservoirs {
        intracellular: reader.u128()?,
        extracellular: reader.u128()?,
    };
    let recovery_count = reader.usize()?;
    if recovery_count != anatomy.recovery.psi_lanes.len() {
        return Err(NeuronStateCodecError::AnatomyMismatch);
    }
    let mut psi_lanes = Vec::with_capacity(recovery_count);
    for lane_anatomy in &anatomy.recovery.psi_lanes {
        psi_lanes.push(decode_recovery_lane(&mut reader, *lane_anatomy)?);
    }
    let recovery = RecoveryState {
        psi_lanes: psi_lanes.into_boxed_slice(),
        gate_lane: decode_recovery_lane(&mut reader, anatomy.recovery.gate_lane)?,
        plastic_lane: decode_recovery_lane(&mut reader, anatomy.recovery.plastic_lane)?,
    };
    let dna_expression = DnaExpressionState {
        substrate_quanta: reader.u128()?,
        fuel_quanta: reader.u128()?,
        expressed_product_quanta: reader.u128()?,
        waste_quanta: reader.u128()?,
    };
    if dna_expression.expressed_product_quanta > anatomy.dna_expression.product_capacity
        || dna_expression.waste_quanta > anatomy.dna_expression.waste_capacity
    {
        return Err(NeuronStateCodecError::AnatomyMismatch);
    }
    let plastic = PlasticSupportState {
        rest_length_nanometres: ExactRational::new(reader.i128()?, reader.u128()?)
            .map_err(|_| NeuronStateCodecError::InvalidEncoding)?,
        dissipated_quanta: reader.u128()?,
    };
    let optical_quantum_residue = ExactRational::new(reader.i128()?, reader.u128()?)
        .map_err(|_| NeuronStateCodecError::InvalidEncoding)?;
    if plastic.rest_length_nanometres.parts().0 <= 0
        || plastic.dissipated_quanta > anatomy.plastic.dissipation_capacity_quanta
        // Law 1: a retained receptor accumulator is bounded only by
        // non-negativity (see the encoder).
        || rational_to_exact(optical_quantum_residue) < Exact::zero()
        || !reader.finished()
    {
        return Err(NeuronStateCodecError::AnatomyMismatch);
    }
    Ok(NeuronPhysicalState {
        psi: PsiKrimelackState {
            rings: rings.into_boxed_slice(),
        },
        gate,
        membrane,
        carriers,
        recovery,
        dna_expression,
        plastic,
        optical_quantum_residue,
    })
}

fn encode_recovery_lane(
    encoded: &mut Vec<u8>,
    lane: RecoveryLaneState,
    anatomy: RecoveryLaneAnatomy,
) -> Result<(), NeuronStateCodecError> {
    if lane.fuel_quanta > anatomy.fuel_capacity
        || lane.spent_quanta > anatomy.spent_capacity
        || lane.exported_heat_quanta > anatomy.exported_heat_capacity
    {
        return Err(NeuronStateCodecError::AnatomyMismatch);
    }
    push_u128(encoded, lane.fuel_quanta);
    push_u128(encoded, lane.spent_quanta);
    push_u128(encoded, lane.exported_heat_quanta);
    Ok(())
}

fn decode_recovery_lane(
    reader: &mut NeuronStateReader<'_>,
    anatomy: RecoveryLaneAnatomy,
) -> Result<RecoveryLaneState, NeuronStateCodecError> {
    let lane = RecoveryLaneState {
        fuel_quanta: reader.u128()?,
        spent_quanta: reader.u128()?,
        exported_heat_quanta: reader.u128()?,
    };
    if lane.fuel_quanta > anatomy.fuel_capacity
        || lane.spent_quanta > anatomy.spent_capacity
        || lane.exported_heat_quanta > anatomy.exported_heat_capacity
    {
        return Err(NeuronStateCodecError::AnatomyMismatch);
    }
    Ok(lane)
}

fn push_phase(encoded: &mut Vec<u8>, phase: ChargeCarrierPhase) {
    let (numerator, denominator) = phase.parts();
    push_i128(encoded, numerator);
    push_u128(encoded, denominator);
}

fn push_usize(encoded: &mut Vec<u8>, value: usize) -> Result<(), NeuronStateCodecError> {
    encoded.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| NeuronStateCodecError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

fn push_u128(encoded: &mut Vec<u8>, value: u128) {
    encoded.extend_from_slice(&value.to_le_bytes());
}

fn push_i128(encoded: &mut Vec<u8>, value: i128) {
    encoded.extend_from_slice(&value.to_le_bytes());
}

fn decode_winding(value: i8) -> Result<BalancedTrit, NeuronStateCodecError> {
    match value {
        -1 => Ok(BalancedTrit::Negative),
        0 => Ok(BalancedTrit::Quiescent),
        1 => Ok(BalancedTrit::Positive),
        _ => Err(NeuronStateCodecError::InvalidEncoding),
    }
}

struct NeuronStateReader<'a> {
    encoded: &'a [u8],
    cursor: usize,
}

impl<'a> NeuronStateReader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self { encoded, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], NeuronStateCodecError> {
        let end = self
            .cursor
            .checked_add(count)
            .ok_or(NeuronStateCodecError::ArithmeticWidth)?;
        let value = self
            .encoded
            .get(self.cursor..end)
            .ok_or(NeuronStateCodecError::InvalidEncoding)?;
        self.cursor = end;
        Ok(value)
    }

    fn i8(&mut self) -> Result<i8, NeuronStateCodecError> {
        Ok(self.take(1)?[0] as i8)
    }

    fn u128(&mut self) -> Result<u128, NeuronStateCodecError> {
        Ok(u128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| NeuronStateCodecError::InvalidEncoding)?,
        ))
    }

    fn i128(&mut self) -> Result<i128, NeuronStateCodecError> {
        Ok(i128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| NeuronStateCodecError::InvalidEncoding)?,
        ))
    }

    fn usize(&mut self) -> Result<usize, NeuronStateCodecError> {
        usize::try_from(u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| NeuronStateCodecError::InvalidEncoding)?,
        ))
        .map_err(|_| NeuronStateCodecError::ArithmeticWidth)
    }

    fn phase(&mut self) -> Result<ChargeCarrierPhase, NeuronStateCodecError> {
        ChargeCarrierPhase::new(self.i128()?, self.u128()?)
            .map_err(|_| NeuronStateCodecError::InvalidEncoding)
    }

    fn finished(&self) -> bool {
        self.cursor == self.encoded.len()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum NeuronPhysicalError {
    AnatomyMismatch,
    Boundary(JointNeuronBoundaryError),
    Psi(PsiSettlementError),
    Gate(GateSettlementError),
    Recovery(RecoveryError),
    DnaExpression(DnaExpressionError),
    Plasticity(PlasticityError),
    ExactDelta(ExactRationalError),
    SequenceEndedBeforeQuiescence,
}

impl From<JointNeuronBoundaryError> for NeuronPhysicalError {
    fn from(value: JointNeuronBoundaryError) -> Self {
        Self::Boundary(value)
    }
}

impl From<PsiSettlementError> for NeuronPhysicalError {
    fn from(value: PsiSettlementError) -> Self {
        Self::Psi(value)
    }
}

impl From<GateSettlementError> for NeuronPhysicalError {
    fn from(value: GateSettlementError) -> Self {
        Self::Gate(value)
    }
}

impl From<RecoveryError> for NeuronPhysicalError {
    fn from(value: RecoveryError) -> Self {
        Self::Recovery(value)
    }
}

impl From<DnaExpressionError> for NeuronPhysicalError {
    fn from(value: DnaExpressionError) -> Self {
        Self::DnaExpression(value)
    }
}

impl From<PlasticityError> for NeuronPhysicalError {
    fn from(value: PlasticityError) -> Self {
        Self::Plasticity(value)
    }
}

impl From<ExactRationalError> for NeuronPhysicalError {
    fn from(value: ExactRationalError) -> Self {
        Self::ExactDelta(value)
    }
}

#[derive(Clone, Debug)]
pub(crate) struct NeuronPhysicalInterval<'a> {
    pub(crate) mathloom: BorrowedMathLoomDelivery<'a>,
    pub(crate) psi: PsiSettlement,
    pub(crate) gate_membrane: GateMembraneSettlement,
    pub(crate) successor: NeuronPhysicalState,
}

/// Execute one exact reached physical interval. This produces current physical
/// successor state only. It does not emit a neuronal fractal because a single
/// membrane interval is not, by itself, proof of post-experience quiescence.
pub(crate) fn settle_neuron_physical_interval<'a>(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &NeuronPhysicalState,
    perspective: JointNeuronPerspective<'a>,
    gate_work: GateWorkOccurrence,
    interval_microseconds: u32,
) -> Result<NeuronPhysicalInterval<'a>, NeuronPhysicalError> {
    settle_neuron_physical_interval_with_contact(
        anatomy,
        predecessor,
        perspective,
        gate_work,
        interval_microseconds,
        0,
    )
}

pub(crate) fn settle_neuron_physical_interval_with_contact<'a>(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &NeuronPhysicalState,
    perspective: JointNeuronPerspective<'a>,
    gate_work: GateWorkOccurrence,
    interval_microseconds: u32,
    inter_neuron_outward_elementary_charges: i128,
) -> Result<NeuronPhysicalInterval<'a>, NeuronPhysicalError> {
    let mathloom = settle_shared_dsf_mathloom(perspective, anatomy.mathloom)?;
    let psi = settle_psi_krimelack(&anatomy.psi, &predecessor.psi, &mathloom)?;
    let gate_membrane = settle_gate_membrane_with_contact(
        &anatomy.gate,
        &anatomy.plastic,
        &predecessor.plastic,
        predecessor.gate,
        &psi.successor,
        gate_work,
        anatomy.capacitance,
        predecessor.membrane,
        predecessor.carriers,
        interval_microseconds,
        inter_neuron_outward_elementary_charges,
    )?;
    let successor = NeuronPhysicalState {
        psi: psi.successor.clone(),
        gate: gate_membrane.successor_gate,
        membrane: gate_membrane.membrane.successor,
        carriers: gate_membrane.successor_carriers,
        recovery: predecessor.recovery.clone(),
        dna_expression: predecessor.dna_expression,
        plastic: predecessor.plastic.clone(),
        optical_quantum_residue: predecessor.optical_quantum_residue,
    };
    Ok(NeuronPhysicalInterval {
        mathloom,
        psi,
        gate_membrane,
        successor,
    })
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum GateSettlementError {
    InvalidAnatomy,
    InvalidPsiContact,
    ContactOutsidePsiAnatomy,
    GatePopulationExceeded,
    DissipationNotQuantized,
    ArithmeticWidth,
    InsufficientCarrierMaterial,
    Membrane(MembraneConductanceError),
    Plasticity(PlasticityError),
}

impl From<MembraneConductanceError> for GateSettlementError {
    fn from(value: MembraneConductanceError) -> Self {
        Self::Membrane(value)
    }
}

impl From<PlasticityError> for GateSettlementError {
    fn from(value: PlasticityError) -> Self {
        Self::Plasticity(value)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct GateMembraneSettlement {
    pub(crate) successor_gate: TwoStateGateState,
    pub(crate) successor_carriers: CarrierReservoirs,
    pub(crate) membrane: LocalMembraneConductanceTransition<1>,
    pub(crate) open_minus_closed_energy_zeptojoules: Exact,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct GateWorkOccurrence {
    open_minus_closed_zeptojoules: Exact,
}

impl GateWorkOccurrence {
    pub(crate) fn new(open_minus_closed_zeptojoules: Exact) -> Self {
        Self {
            open_minus_closed_zeptojoules,
        }
    }

    pub(crate) fn is_zero(&self) -> bool {
        self.open_minus_closed_zeptojoules.is_zero()
    }
}

/// Deterministic two-state free-energy descent approved for virtual material.
/// `delta_g < 0` can open finite closed conformations; `delta_g > 0` can close
/// finite open conformations; equality retains the predecessor. Every changed
/// conformation deposits its exact released energy in the finite dissipation
/// reservoir. Conductance follows only from the resulting open population.
pub(crate) fn settle_gate_membrane(
    anatomy: &TwoStateGateAnatomy,
    plastic_anatomy: &PlasticSupportAnatomy,
    plastic_state: &PlasticSupportState,
    predecessor_gate: TwoStateGateState,
    psi: &PsiKrimelackState,
    gate_work: GateWorkOccurrence,
    capacitance: MembraneCapacitance,
    predecessor_membrane: LocalMembraneConductanceState<1>,
    predecessor_carriers: CarrierReservoirs,
    interval_microseconds: u32,
) -> Result<GateMembraneSettlement, GateSettlementError> {
    settle_gate_membrane_with_contact(
        anatomy,
        plastic_anatomy,
        plastic_state,
        predecessor_gate,
        psi,
        gate_work,
        capacitance,
        predecessor_membrane,
        predecessor_carriers,
        interval_microseconds,
        0,
    )
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn settle_gate_membrane_with_contact(
    anatomy: &TwoStateGateAnatomy,
    plastic_anatomy: &PlasticSupportAnatomy,
    plastic_state: &PlasticSupportState,
    predecessor_gate: TwoStateGateState,
    psi: &PsiKrimelackState,
    gate_work: GateWorkOccurrence,
    capacitance: MembraneCapacitance,
    predecessor_membrane: LocalMembraneConductanceState<1>,
    predecessor_carriers: CarrierReservoirs,
    interval_microseconds: u32,
    inter_neuron_outward_elementary_charges: i128,
) -> Result<GateMembraneSettlement, GateSettlementError> {
    if predecessor_gate.open_population > anatomy.population {
        return Err(GateSettlementError::GatePopulationExceeded);
    }
    let delta_g = gate_open_minus_closed_free_energy(
        anatomy,
        plastic_anatomy,
        plastic_state,
        predecessor_membrane,
        capacitance,
        psi,
        &gate_work,
    )?;

    let available_population = if delta_g.is_negative() {
        anatomy.population - predecessor_gate.open_population
    } else if delta_g.is_positive() {
        predecessor_gate.open_population
    } else {
        0
    };
    let mut successor_gate = predecessor_gate;
    if available_population > 0 {
        let per_channel =
            exact_unsigned_quanta(&delta_g.abs(), &anatomy.dissipation_quantum_zeptojoules)
                .ok_or(GateSettlementError::DissipationNotQuantized)?;
        if per_channel == 0 {
            return Err(GateSettlementError::DissipationNotQuantized);
        }
        let free_quanta = anatomy
            .dissipation_capacity_quanta
            .checked_sub(predecessor_gate.dissipated_quanta)
            .ok_or(GateSettlementError::GatePopulationExceeded)?;
        let settled_population = available_population.min(free_quanta / per_channel);
        let released = settled_population
            .checked_mul(per_channel)
            .ok_or(GateSettlementError::ArithmeticWidth)?;
        successor_gate.dissipated_quanta = predecessor_gate
            .dissipated_quanta
            .checked_add(released)
            .ok_or(GateSettlementError::ArithmeticWidth)?;
        successor_gate.open_population = if delta_g.is_negative() {
            predecessor_gate
                .open_population
                .checked_add(settled_population)
                .ok_or(GateSettlementError::ArithmeticWidth)?
        } else {
            predecessor_gate.open_population - settled_population
        };
    }

    let open_i128 = i128::try_from(successor_gate.open_population)
        .map_err(|_| GateSettlementError::ArithmeticWidth)?;
    let conductance = anatomy
        .single_channel_conductance_picosiemens
        .checked_mul(ExactRational::integer(open_i128))
        .map_err(|_| GateSettlementError::ArithmeticWidth)?;
    let path = LocalConductancePath::new(conductance, anatomy.reversal_potential_millivolts)?;
    let membrane = settle_local_membrane_conductances_with_inter_neuron_contact(
        capacitance,
        predecessor_membrane,
        &[path],
        interval_microseconds,
        inter_neuron_outward_elementary_charges,
    )?;
    let locally_settled_carriers = move_carriers(
        predecessor_carriers,
        membrane.outward_elementary_charges_by_path[0],
    )?;
    let successor_carriers = move_inter_neuron_carriers(
        locally_settled_carriers,
        inter_neuron_outward_elementary_charges,
    )?;
    Ok(GateMembraneSettlement {
        successor_gate,
        successor_carriers,
        membrane,
        open_minus_closed_energy_zeptojoules: delta_g,
    })
}

fn gate_open_minus_closed_free_energy(
    anatomy: &TwoStateGateAnatomy,
    plastic_anatomy: &PlasticSupportAnatomy,
    plastic_state: &PlasticSupportState,
    predecessor_membrane: LocalMembraneConductanceState<1>,
    capacitance: MembraneCapacitance,
    psi: &PsiKrimelackState,
    gate_work: &GateWorkOccurrence,
) -> Result<Exact, GateSettlementError> {
    let potential = predecessor_membrane
        .membrane()
        .potential_millivolts(capacitance)
        .map_err(MembraneConductanceError::from)?;
    let mut delta_g = gate_work.open_minus_closed_zeptojoules.clone();
    delta_g += &anatomy.chemical_open_minus_closed_zeptojoules;
    delta_g += rational_to_exact(open_minus_closed_support_energy(
        plastic_anatomy,
        plastic_state,
    )?);
    let electrical = rational_to_exact(potential)
        * Exact::from_integer(BigInt::from(anatomy.gating_charge_elementary))
        * Exact::new(
            BigInt::from(801_088_317_u64),
            BigInt::from(5_000_000_000_u64),
        );
    delta_g -= electrical;
    for contact in &anatomy.psi_contacts {
        let phase = psi.rings[contact.ring_index].phase_thirds[contact.node_index];
        let cosine = if phase == contact.preferred_phase_third {
            Exact::one()
        } else {
            Exact::new(BigInt::from(-1_i8), BigInt::from(2_u8))
        };
        delta_g -= &contact.open_minus_closed_coupling_zeptojoules * cosine;
    }
    Ok(delta_g)
}

/// The receiving gate's own opening window, in whole dissipation-lattice
/// quanta, for the pending local interval.
///
/// Ratified 2026-08-05 (Law 1, threshold-integrated delivery). Nothing here
/// is a new constant: the barrier is this gate's existing exact
/// open-minus-closed free energy with ZERO receptor work (its chemical,
/// plastic-support, electrical, and psi-contact terms), read on the same
/// lattice the gate already dissipates on; the cap is that barrier plus the
/// gate's declared dissipation capacity, which is the most work one
/// conformational settlement can lawfully dissipate once the recovery
/// reaction has freed the gate's full capacity.
///
/// * `opening_threshold_quanta` — the least whole quantum count whose work
///   drives the gate's free energy strictly downhill (`floor(barrier) + 1`).
/// * `window_cap_quanta` — the greatest whole quantum count whose settlement
///   still fits the gate's declared dissipation capacity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct GateOpeningQuantumWindow {
    pub(crate) opening_threshold_quanta: u128,
    pub(crate) window_cap_quanta: u128,
}

pub(crate) fn gate_opening_quantum_window(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &NeuronPhysicalState,
    perspective: JointNeuronPerspective<'_>,
) -> Result<GateOpeningQuantumWindow, NeuronPhysicalError> {
    let mathloom = settle_shared_dsf_mathloom(perspective, anatomy.mathloom)?;
    let psi = settle_psi_krimelack(&anatomy.psi, &predecessor.psi, &mathloom)?;
    let barrier = gate_open_minus_closed_free_energy(
        &anatomy.gate,
        &anatomy.plastic,
        &predecessor.plastic,
        predecessor.membrane,
        anatomy.capacitance,
        &psi.successor,
        &GateWorkOccurrence::new(Exact::zero()),
    )?;
    let barrier_quanta = if barrier.is_positive() {
        (&barrier / &anatomy.gate.dissipation_quantum_zeptojoules)
            .floor()
            .to_integer()
            .to_u128()
            .ok_or(GateSettlementError::ArithmeticWidth)?
    } else {
        0
    };
    let opening_threshold_quanta = barrier_quanta
        .checked_add(1)
        .ok_or(GateSettlementError::ArithmeticWidth)?;
    let window_cap_quanta = barrier_quanta
        .checked_add(anatomy.gate.dissipation_capacity_quanta)
        .ok_or(GateSettlementError::ArithmeticWidth)?;
    Ok(GateOpeningQuantumWindow {
        opening_threshold_quanta,
        window_cap_quanta,
    })
}

/// Exact recovery reaction extents needed for every currently downhill gate
/// conformation to settle under the pending local interval. This is derived
/// from the same free-energy expression and dissipation quantum used by gate
/// settlement. It introduces no firing threshold or elapsed-time rule.
pub(crate) fn required_gate_recovery_extent_for_interval(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &NeuronPhysicalState,
    perspective: JointNeuronPerspective<'_>,
    gate_work: &GateWorkOccurrence,
) -> Result<u128, NeuronPhysicalError> {
    if predecessor.gate.open_population > anatomy.gate.population {
        return Err(GateSettlementError::GatePopulationExceeded.into());
    }
    let mathloom = settle_shared_dsf_mathloom(perspective, anatomy.mathloom)?;
    let psi = settle_psi_krimelack(&anatomy.psi, &predecessor.psi, &mathloom)?;
    let delta_g = gate_open_minus_closed_free_energy(
        &anatomy.gate,
        &anatomy.plastic,
        &predecessor.plastic,
        predecessor.membrane,
        anatomy.capacitance,
        &psi.successor,
        gate_work,
    )?;
    let available_population = if delta_g.is_negative() {
        anatomy.gate.population - predecessor.gate.open_population
    } else if delta_g.is_positive() {
        predecessor.gate.open_population
    } else {
        return Ok(0);
    };
    if available_population == 0 {
        return Ok(0);
    }
    let per_channel = exact_unsigned_quanta(
        &delta_g.abs(),
        &anatomy.gate.dissipation_quantum_zeptojoules,
    )
    .ok_or(GateSettlementError::DissipationNotQuantized)?;
    let required_quanta = available_population
        .checked_mul(per_channel)
        .ok_or(GateSettlementError::ArithmeticWidth)?;
    let free_quanta = anatomy
        .gate
        .dissipation_capacity_quanta
        .checked_sub(predecessor.gate.dissipated_quanta)
        .ok_or(GateSettlementError::GatePopulationExceeded)?;
    let missing_quanta = required_quanta.saturating_sub(free_quanta);
    if missing_quanta == 0 {
        return Ok(0);
    }
    let gate_lane = anatomy
        .recovery
        .lane(RecoveryLaneAddress::Gate)
        .ok_or(RecoveryError::AnatomyWidth)?;
    let exported_heat_per_extent = gate_lane.stoichiometry().3;
    let rounded = missing_quanta
        .checked_add(exported_heat_per_extent - 1)
        .ok_or(RecoveryError::ArithmeticWidth)?;
    Ok(rounded / exported_heat_per_extent)
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryOnlySettlement {
    pub(crate) successor: NeuronPhysicalState,
    pub(crate) extent: u128,
}

/// Execute only the already-defined local recovery reaction. Fluid exchange is
/// a distinct control-volume settlement and must debit/credit its own material.
pub(crate) fn settle_recovery_only(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &NeuronPhysicalState,
    contact: RecoveryContact<'_>,
) -> Result<RecoveryOnlySettlement, NeuronPhysicalError> {
    let mut successor = predecessor.clone();
    let recovery = settle_recovery(&anatomy.recovery, &mut successor, contact)?;
    Ok(RecoveryOnlySettlement {
        successor,
        extent: recovery.extent,
    })
}

fn move_inter_neuron_carriers(
    predecessor: CarrierReservoirs,
    outward: i128,
) -> Result<CarrierReservoirs, GateSettlementError> {
    let amount = outward.unsigned_abs();
    let intracellular = if outward >= 0 {
        predecessor
            .intracellular
            .checked_sub(amount)
            .ok_or(GateSettlementError::InsufficientCarrierMaterial)?
    } else {
        predecessor
            .intracellular
            .checked_add(amount)
            .ok_or(GateSettlementError::ArithmeticWidth)?
    };
    Ok(CarrierReservoirs {
        intracellular,
        extracellular: predecessor.extracellular,
    })
}

fn open_minus_closed_support_energy(
    anatomy: &PlasticSupportAnatomy,
    state: &PlasticSupportState,
) -> Result<ExactRational, PlasticityError> {
    let closed_strain = anatomy
        .closed_coordinate_nanometres
        .checked_sub(state.rest_length_nanometres)?
        .checked_div(state.rest_length_nanometres)?;
    let open_strain = anatomy
        .open_coordinate_nanometres
        .checked_sub(state.rest_length_nanometres)?
        .checked_div(state.rest_length_nanometres)?;
    let closed_energy = anatomy
        .elastic_energy_scale_zeptojoules
        .checked_mul(closed_strain)?
        .checked_mul(closed_strain)?
        .checked_div_unsigned(2)?;
    let open_energy = anatomy
        .elastic_energy_scale_zeptojoules
        .checked_mul(open_strain)?
        .checked_mul(open_strain)?
        .checked_div_unsigned(2)?;
    Ok(open_energy.checked_sub(closed_energy)?)
}

fn rational_to_exact(value: ExactRational) -> Exact {
    let (numerator, denominator) = value.parts();
    Exact::new(BigInt::from(numerator), BigInt::from(denominator))
}

fn move_carriers(
    predecessor: CarrierReservoirs,
    outward: i128,
) -> Result<CarrierReservoirs, GateSettlementError> {
    let amount = outward.unsigned_abs();
    if outward >= 0 {
        if amount > predecessor.intracellular {
            return Err(GateSettlementError::InsufficientCarrierMaterial);
        }
        Ok(CarrierReservoirs {
            intracellular: predecessor.intracellular - amount,
            extracellular: predecessor
                .extracellular
                .checked_add(amount)
                .ok_or(GateSettlementError::ArithmeticWidth)?,
        })
    } else {
        if amount > predecessor.extracellular {
            return Err(GateSettlementError::InsufficientCarrierMaterial);
        }
        Ok(CarrierReservoirs {
            intracellular: predecessor
                .intracellular
                .checked_add(amount)
                .ok_or(GateSettlementError::ArithmeticWidth)?,
            extracellular: predecessor.extracellular - amount,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RecoveryContact<'a> {
    psi_catalyst_quanta: &'a [u128],
    gate_catalyst_quanta: u128,
    plastic_catalyst_quanta: u128,
}

impl<'a> RecoveryContact<'a> {
    pub(crate) fn new(
        psi_catalyst_quanta: &'a [u128],
        gate_catalyst_quanta: u128,
        plastic_catalyst_quanta: u128,
    ) -> Self {
        Self {
            psi_catalyst_quanta,
            gate_catalyst_quanta,
            plastic_catalyst_quanta,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DnaExpressionContact {
    catalyst_quanta: u128,
}

impl DnaExpressionContact {
    pub(crate) fn new(catalyst_quanta: u128) -> Self {
        Self { catalyst_quanta }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct RecoverySettlement {
    extent: u128,
}

fn settle_recovery(
    anatomy: &RecoveryAnatomy,
    state: &mut NeuronPhysicalState,
    contact: RecoveryContact<'_>,
) -> Result<RecoverySettlement, RecoveryError> {
    if contact.psi_catalyst_quanta.len() != anatomy.psi_lanes.len()
        || state.recovery.psi_lanes.len() != anatomy.psi_lanes.len()
        || state.psi.rings.len() != anatomy.psi_lanes.len()
    {
        return Err(RecoveryError::AnatomyWidth);
    }
    let mut total_extent = 0_u128;
    for lane_index in 0..anatomy.psi_lanes.len() {
        let extent = settle_recovery_lane(
            anatomy.psi_lanes[lane_index],
            &mut state.psi.rings[lane_index].dissipated_quanta,
            &mut state.recovery.psi_lanes[lane_index],
            contact.psi_catalyst_quanta[lane_index],
        )?;
        total_extent = total_extent
            .checked_add(extent)
            .ok_or(RecoveryError::ArithmeticWidth)?;
    }
    let gate_extent = settle_recovery_lane(
        anatomy.gate_lane,
        &mut state.gate.dissipated_quanta,
        &mut state.recovery.gate_lane,
        contact.gate_catalyst_quanta,
    )?;
    total_extent = total_extent
        .checked_add(gate_extent)
        .ok_or(RecoveryError::ArithmeticWidth)?;
    let plastic_extent = settle_recovery_lane(
        anatomy.plastic_lane,
        &mut state.plastic.dissipated_quanta,
        &mut state.recovery.plastic_lane,
        contact.plastic_catalyst_quanta,
    )?;
    total_extent = total_extent
        .checked_add(plastic_extent)
        .ok_or(RecoveryError::ArithmeticWidth)?;
    Ok(RecoverySettlement {
        extent: total_extent,
    })
}

fn settle_recovery_lane(
    anatomy: RecoveryLaneAnatomy,
    dissipated_quanta: &mut u128,
    state: &mut RecoveryLaneState,
    catalyst_quanta: u128,
) -> Result<u128, RecoveryError> {
    let spent_free = anatomy
        .spent_capacity
        .checked_sub(state.spent_quanta)
        .ok_or(RecoveryError::InvalidAnatomy)?;
    let heat_free = anatomy
        .exported_heat_capacity
        .checked_sub(state.exported_heat_quanta)
        .ok_or(RecoveryError::InvalidAnatomy)?;
    let extent = (catalyst_quanta / anatomy.catalyst_per_extent)
        .min(state.fuel_quanta / anatomy.fuel_per_extent)
        .min(spent_free / anatomy.spent_per_extent)
        .min(*dissipated_quanta / anatomy.exported_heat_per_extent)
        .min(heat_free / anatomy.exported_heat_per_extent);
    if extent == 0 {
        return Ok(0);
    }
    let fuel = extent
        .checked_mul(anatomy.fuel_per_extent)
        .ok_or(RecoveryError::ArithmeticWidth)?;
    let spent = extent
        .checked_mul(anatomy.spent_per_extent)
        .ok_or(RecoveryError::ArithmeticWidth)?;
    let heat = extent
        .checked_mul(anatomy.exported_heat_per_extent)
        .ok_or(RecoveryError::ArithmeticWidth)?;
    state.fuel_quanta -= fuel;
    state.spent_quanta = state
        .spent_quanta
        .checked_add(spent)
        .ok_or(RecoveryError::ArithmeticWidth)?;
    *dissipated_quanta -= heat;
    state.exported_heat_quanta = state
        .exported_heat_quanta
        .checked_add(heat)
        .ok_or(RecoveryError::ArithmeticWidth)?;
    Ok(extent)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DnaExpressionSettlement {
    extent: u128,
}

fn settle_dna_expression(
    anatomy: DnaExpressionAnatomy,
    state: &mut DnaExpressionState,
    contact: DnaExpressionContact,
) -> Result<DnaExpressionSettlement, DnaExpressionError> {
    let product_free = anatomy
        .product_capacity
        .checked_sub(state.expressed_product_quanta)
        .ok_or(DnaExpressionError::InvalidAnatomy)?;
    let waste_free = anatomy
        .waste_capacity
        .checked_sub(state.waste_quanta)
        .ok_or(DnaExpressionError::InvalidAnatomy)?;
    let extent = (contact.catalyst_quanta / anatomy.catalyst_per_extent)
        .min(state.substrate_quanta / anatomy.substrate_per_extent)
        .min(state.fuel_quanta / anatomy.fuel_per_extent)
        .min(product_free / anatomy.product_per_extent)
        .min(waste_free / anatomy.waste_per_extent);
    if extent == 0 {
        return Ok(DnaExpressionSettlement { extent: 0 });
    }
    let substrate = extent
        .checked_mul(anatomy.substrate_per_extent)
        .ok_or(DnaExpressionError::ArithmeticWidth)?;
    let fuel = extent
        .checked_mul(anatomy.fuel_per_extent)
        .ok_or(DnaExpressionError::ArithmeticWidth)?;
    let product = extent
        .checked_mul(anatomy.product_per_extent)
        .ok_or(DnaExpressionError::ArithmeticWidth)?;
    let waste = extent
        .checked_mul(anatomy.waste_per_extent)
        .ok_or(DnaExpressionError::ArithmeticWidth)?;
    state.substrate_quanta -= substrate;
    state.fuel_quanta -= fuel;
    state.expressed_product_quanta = state
        .expressed_product_quanta
        .checked_add(product)
        .ok_or(DnaExpressionError::ArithmeticWidth)?;
    state.waste_quanta = state
        .waste_quanta
        .checked_add(waste)
        .ok_or(DnaExpressionError::ArithmeticWidth)?;
    Ok(DnaExpressionSettlement { extent })
}

#[derive(Clone, Debug)]
pub(crate) struct NeuronIntervalInput<'a> {
    pub(crate) perspective: JointNeuronPerspective<'a>,
    pub(crate) gate_work: GateWorkOccurrence,
    pub(crate) interval_microseconds: u32,
    pub(crate) recovery: RecoveryContact<'a>,
    pub(crate) dna_expression: DnaExpressionContact,
    /// `Some(residue)` when this interval's gate work is a quantized optical
    /// delivery (ratified 2026-08-05): the exact sub-quantum remainder to
    /// retain in the successor state after the whole-quantum delivery carried
    /// by `gate_work`. `None` for every non-optical delivery: the predecessor
    /// residue is carried through unchanged.
    pub(crate) optical_successor_residue: Option<ExactRational>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct QuiescentNeuronState {
    state: NeuronPhysicalState,
}

impl QuiescentNeuronState {
    pub(crate) fn state(&self) -> &NeuronPhysicalState {
        &self.state
    }

    pub(crate) fn from_state(state: NeuronPhysicalState) -> Self {
        Self { state }
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum PhysicalStateCoordinate {
    PsiWinding(usize),
    PsiDissipatedEnergy(usize),
    GateOpenPopulation,
    GateDissipatedEnergy,
    MembraneSeparatedCharge,
    MembraneCarrierPhase,
    ConductancePathCarrierPhase(usize),
    IntracellularCarrier,
    ExtracellularCarrier,
    RecoveryPsiFuel(usize),
    RecoveryPsiSpent(usize),
    RecoveryPsiExportedHeat(usize),
    RecoveryGateFuel,
    RecoveryGateSpent,
    RecoveryGateExportedHeat,
    PlasticRestLength,
    PlasticDissipatedEnergy,
    RecoveryPlasticFuel,
    RecoveryPlasticSpent,
    RecoveryPlasticExportedHeat,
    DnaSubstrate,
    DnaFuel,
    DnaExpressedProduct,
    DnaWaste,
    OpticalQuantumResidue,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExactSignedDelta {
    negative: bool,
    magnitude: u128,
}

impl ExactSignedDelta {
    pub(crate) fn from_parts(negative: bool, magnitude: u128) -> Option<Self> {
        (magnitude != 0).then_some(Self {
            negative,
            magnitude,
        })
    }

    pub(crate) fn parts(self) -> (bool, u128) {
        (self.negative, self.magnitude)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ExactPhysicalStateDelta {
    Integral(ExactSignedDelta),
    Rational(ExactRational),
}

impl ExactPhysicalStateDelta {
    fn is_zero(self) -> bool {
        match self {
            Self::Integral(delta) => delta.magnitude == 0,
            Self::Rational(delta) => delta.parts().0 == 0,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct PhysicalStateDeltaEntry {
    coordinate: PhysicalStateCoordinate,
    delta: ExactPhysicalStateDelta,
}

impl PhysicalStateDeltaEntry {
    pub(crate) fn new(
        coordinate: PhysicalStateCoordinate,
        delta: ExactPhysicalStateDelta,
    ) -> Option<Self> {
        (!delta.is_zero() && coordinate_accepts_delta(coordinate, delta))
            .then_some(Self { coordinate, delta })
    }

    pub(crate) fn coordinate(self) -> PhysicalStateCoordinate {
        self.coordinate
    }

    pub(crate) fn delta(self) -> ExactPhysicalStateDelta {
        self.delta
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct SparsePhysicalStateDelta {
    entries: Box<[PhysicalStateDeltaEntry]>,
}

impl SparsePhysicalStateDelta {
    pub(crate) fn from_canonical_entries(entries: Vec<PhysicalStateDeltaEntry>) -> Option<Self> {
        if entries.is_empty()
            || entries.iter().any(|entry| {
                entry.delta.is_zero() || !coordinate_accepts_delta(entry.coordinate, entry.delta)
            })
            || entries
                .windows(2)
                .any(|pair| pair[0].coordinate >= pair[1].coordinate)
        {
            return None;
        }
        Some(Self {
            entries: entries.into_boxed_slice(),
        })
    }

    pub(crate) fn entries(&self) -> &[PhysicalStateDeltaEntry] {
        &self.entries
    }

    pub(crate) fn exact_delta(
        &self,
        coordinate: PhysicalStateCoordinate,
    ) -> Option<ExactPhysicalStateDelta> {
        self.entries
            .binary_search_by_key(&coordinate, |entry| entry.coordinate)
            .ok()
            .map(|index| self.entries[index].delta)
    }

    pub(crate) fn resident_bytes(&self) -> Option<usize> {
        core::mem::size_of::<Self>().checked_add(
            self.entries
                .len()
                .checked_mul(core::mem::size_of::<PhysicalStateDeltaEntry>())?,
        )
    }
}

fn coordinate_accepts_delta(
    coordinate: PhysicalStateCoordinate,
    delta: ExactPhysicalStateDelta,
) -> bool {
    matches!(
        (coordinate, delta),
        (
            PhysicalStateCoordinate::MembraneCarrierPhase
                | PhysicalStateCoordinate::ConductancePathCarrierPhase(_)
                | PhysicalStateCoordinate::PlasticRestLength
                | PhysicalStateCoordinate::OpticalQuantumResidue,
            ExactPhysicalStateDelta::Rational(_)
        ) | (
            PhysicalStateCoordinate::PsiWinding(_)
                | PhysicalStateCoordinate::PsiDissipatedEnergy(_)
                | PhysicalStateCoordinate::GateOpenPopulation
                | PhysicalStateCoordinate::GateDissipatedEnergy
                | PhysicalStateCoordinate::MembraneSeparatedCharge
                | PhysicalStateCoordinate::IntracellularCarrier
                | PhysicalStateCoordinate::ExtracellularCarrier
                | PhysicalStateCoordinate::RecoveryPsiFuel(_)
                | PhysicalStateCoordinate::RecoveryPsiSpent(_)
                | PhysicalStateCoordinate::RecoveryPsiExportedHeat(_)
                | PhysicalStateCoordinate::RecoveryGateFuel
                | PhysicalStateCoordinate::RecoveryGateSpent
                | PhysicalStateCoordinate::RecoveryGateExportedHeat
                | PhysicalStateCoordinate::PlasticDissipatedEnergy
                | PhysicalStateCoordinate::RecoveryPlasticFuel
                | PhysicalStateCoordinate::RecoveryPlasticSpent
                | PhysicalStateCoordinate::RecoveryPlasticExportedHeat
                | PhysicalStateCoordinate::DnaSubstrate
                | PhysicalStateCoordinate::DnaFuel
                | PhysicalStateCoordinate::DnaExpressedProduct
                | PhysicalStateCoordinate::DnaWaste,
            ExactPhysicalStateDelta::Integral(_)
        )
    )
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PostExperienceSettlement {
    pub(crate) quiescent: QuiescentNeuronState,
    pub(crate) fractal: Option<SparsePhysicalStateDelta>,
    pub(crate) plasticity: PlasticityAvailability,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ExtendedIntervalSettlement {
    pub(crate) successor: NeuronPhysicalState,
    pub(crate) quiescent: bool,
}

fn settle_extended_interval(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &NeuronPhysicalState,
    input: NeuronIntervalInput<'_>,
) -> Result<ExtendedIntervalSettlement, NeuronPhysicalError> {
    settle_extended_interval_with_contact(anatomy, predecessor, input, 0)
}

pub(crate) fn settle_extended_interval_with_contact(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &NeuronPhysicalState,
    input: NeuronIntervalInput<'_>,
    inter_neuron_outward_elementary_charges: i128,
) -> Result<ExtendedIntervalSettlement, NeuronPhysicalError> {
    let physical = settle_neuron_physical_interval_with_contact(
        anatomy,
        predecessor,
        input.perspective,
        input.gate_work,
        input.interval_microseconds,
        inter_neuron_outward_elementary_charges,
    )?;
    let psi_changed = physical.psi.changed_rings != 0;
    let gate_changed = physical.successor.gate != predecessor.gate;
    let membrane_active = physical
        .gate_membrane
        .membrane
        .path_currents_picoamperes
        .iter()
        .any(|current| current.parts().0 != 0)
        || physical.successor.membrane != predecessor.membrane;
    let mut successor = physical.successor;
    // The retained sub-quantum residue is a receptor accumulator, not a
    // settled physical coordinate: it does not enter the quiescence
    // predicate.  The ratified law changes WHAT energy arrives, nothing else.
    if let Some(residue) = input.optical_successor_residue {
        successor.optical_quantum_residue = residue;
    }
    let plastic = settle_plastic_support(
        &anatomy.plastic,
        &predecessor.plastic,
        anatomy.gate.population,
        successor.gate.open_population,
    )?;
    successor.plastic = plastic.successor;
    let recovery = settle_recovery(&anatomy.recovery, &mut successor, input.recovery)?;
    let dna = settle_dna_expression(
        anatomy.dna_expression,
        &mut successor.dna_expression,
        input.dna_expression,
    )?;
    Ok(ExtendedIntervalSettlement {
        successor,
        quiescent: !psi_changed
            && !gate_changed
            && !membrane_active
            && !plastic.changed
            && recovery.extent == 0
            && dna.extent == 0,
    })
}

/// Settle only along the supplied exact physical interval sequence. The
/// sequence is the causal occurrence, not a timeout. If it ends before an
/// unchanged zero-current interval, no quiescence or fractal is claimed.
pub(crate) fn settle_to_quiescence(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &NeuronPhysicalState,
    intervals: &[NeuronIntervalInput<'_>],
) -> Result<QuiescentNeuronState, NeuronPhysicalError> {
    let mut state = predecessor.clone();
    for input in intervals {
        let settled = settle_extended_interval(anatomy, &state, input.clone())?;
        state = settled.successor;
        if settled.quiescent {
            return Ok(QuiescentNeuronState { state });
        }
    }
    Err(NeuronPhysicalError::SequenceEndedBeforeQuiescence)
}

pub(crate) fn settle_experience_to_quiescence(
    anatomy: &NeuronPhysicalAnatomy,
    predecessor: &QuiescentNeuronState,
    perturbation: NeuronIntervalInput<'_>,
    post_experience_intervals: &[NeuronIntervalInput<'_>],
) -> Result<PostExperienceSettlement, NeuronPhysicalError> {
    let first = settle_extended_interval(anatomy, &predecessor.state, perturbation)?;
    let quiescent = if first.quiescent {
        QuiescentNeuronState {
            state: first.successor,
        }
    } else {
        settle_to_quiescence(anatomy, &first.successor, post_experience_intervals)?
    };
    let fractal = sparse_physical_state_delta(&predecessor.state, &quiescent.state)?;
    Ok(PostExperienceSettlement {
        quiescent,
        fractal,
        plasticity: PlasticityAvailability::ExecutedExactReturnMapping,
    })
}

pub(crate) fn sparse_physical_state_delta(
    predecessor: &NeuronPhysicalState,
    successor: &NeuronPhysicalState,
) -> Result<Option<SparsePhysicalStateDelta>, NeuronPhysicalError> {
    if predecessor.psi.rings.len() != successor.psi.rings.len()
        || predecessor.recovery.psi_lanes.len() != successor.recovery.psi_lanes.len()
    {
        return Err(NeuronPhysicalError::AnatomyMismatch);
    }
    let capacity = predecessor
        .psi
        .rings
        .len()
        .checked_mul(5)
        .and_then(|count| count.checked_add(20))
        .ok_or(NeuronPhysicalError::AnatomyMismatch)?;
    let mut entries = Vec::new();
    entries
        .try_reserve_exact(capacity)
        .map_err(|_| NeuronPhysicalError::AnatomyMismatch)?;
    for index in 0..predecessor.psi.rings.len() {
        push_i128_delta(
            &mut entries,
            PhysicalStateCoordinate::PsiWinding(index),
            predecessor.psi.rings[index].winding as i8 as i128,
            successor.psi.rings[index].winding as i8 as i128,
        );
        push_u128_delta(
            &mut entries,
            PhysicalStateCoordinate::PsiDissipatedEnergy(index),
            predecessor.psi.rings[index].dissipated_quanta,
            successor.psi.rings[index].dissipated_quanta,
        );
        let prior_recovery = predecessor.recovery.psi_lanes[index];
        let next_recovery = successor.recovery.psi_lanes[index];
        push_u128_delta(
            &mut entries,
            PhysicalStateCoordinate::RecoveryPsiFuel(index),
            prior_recovery.fuel_quanta,
            next_recovery.fuel_quanta,
        );
        push_u128_delta(
            &mut entries,
            PhysicalStateCoordinate::RecoveryPsiSpent(index),
            prior_recovery.spent_quanta,
            next_recovery.spent_quanta,
        );
        push_u128_delta(
            &mut entries,
            PhysicalStateCoordinate::RecoveryPsiExportedHeat(index),
            prior_recovery.exported_heat_quanta,
            next_recovery.exported_heat_quanta,
        );
    }
    push_u128_delta(
        &mut entries,
        PhysicalStateCoordinate::GateOpenPopulation,
        predecessor.gate.open_population,
        successor.gate.open_population,
    );
    push_u128_delta(
        &mut entries,
        PhysicalStateCoordinate::GateDissipatedEnergy,
        predecessor.gate.dissipated_quanta,
        successor.gate.dissipated_quanta,
    );
    push_i128_delta(
        &mut entries,
        PhysicalStateCoordinate::MembraneSeparatedCharge,
        predecessor
            .membrane
            .membrane()
            .separated_elementary_charges(),
        successor.membrane.membrane().separated_elementary_charges(),
    );
    let prior_membrane_phase = predecessor.membrane.membrane().carrier_phase().parts();
    let next_membrane_phase = successor.membrane.membrane().carrier_phase().parts();
    push_rational_delta(
        &mut entries,
        PhysicalStateCoordinate::MembraneCarrierPhase,
        ExactRational::new(prior_membrane_phase.0, prior_membrane_phase.1)?,
        ExactRational::new(next_membrane_phase.0, next_membrane_phase.1)?,
    )?;
    for (index, (prior_phase, next_phase)) in predecessor
        .membrane
        .path_carrier_phases()
        .iter()
        .zip(successor.membrane.path_carrier_phases().iter())
        .enumerate()
    {
        let prior = prior_phase.parts();
        let next = next_phase.parts();
        push_rational_delta(
            &mut entries,
            PhysicalStateCoordinate::ConductancePathCarrierPhase(index),
            ExactRational::new(prior.0, prior.1)?,
            ExactRational::new(next.0, next.1)?,
        )?;
    }
    push_u128_delta(
        &mut entries,
        PhysicalStateCoordinate::IntracellularCarrier,
        predecessor.carriers.intracellular,
        successor.carriers.intracellular,
    );
    push_u128_delta(
        &mut entries,
        PhysicalStateCoordinate::ExtracellularCarrier,
        predecessor.carriers.extracellular,
        successor.carriers.extracellular,
    );
    push_recovery_gate_delta(&mut entries, predecessor, successor);
    push_dna_delta(
        &mut entries,
        predecessor.dna_expression,
        successor.dna_expression,
    );
    push_rational_delta(
        &mut entries,
        PhysicalStateCoordinate::PlasticRestLength,
        predecessor.plastic.rest_length_nanometres,
        successor.plastic.rest_length_nanometres,
    )?;
    push_rational_delta(
        &mut entries,
        PhysicalStateCoordinate::OpticalQuantumResidue,
        predecessor.optical_quantum_residue,
        successor.optical_quantum_residue,
    )?;
    push_u128_delta(
        &mut entries,
        PhysicalStateCoordinate::PlasticDissipatedEnergy,
        predecessor.plastic.dissipated_quanta,
        successor.plastic.dissipated_quanta,
    );
    push_recovery_plastic_delta(&mut entries, predecessor, successor);
    entries.sort_unstable_by_key(|entry| entry.coordinate);
    Ok(SparsePhysicalStateDelta::from_canonical_entries(entries))
}

fn push_recovery_gate_delta(
    entries: &mut Vec<PhysicalStateDeltaEntry>,
    predecessor: &NeuronPhysicalState,
    successor: &NeuronPhysicalState,
) {
    let prior = predecessor.recovery.gate_lane;
    let next = successor.recovery.gate_lane;
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::RecoveryGateFuel,
        prior.fuel_quanta,
        next.fuel_quanta,
    );
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::RecoveryGateSpent,
        prior.spent_quanta,
        next.spent_quanta,
    );
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::RecoveryGateExportedHeat,
        prior.exported_heat_quanta,
        next.exported_heat_quanta,
    );
}

fn push_recovery_plastic_delta(
    entries: &mut Vec<PhysicalStateDeltaEntry>,
    predecessor: &NeuronPhysicalState,
    successor: &NeuronPhysicalState,
) {
    let prior = predecessor.recovery.plastic_lane;
    let next = successor.recovery.plastic_lane;
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::RecoveryPlasticFuel,
        prior.fuel_quanta,
        next.fuel_quanta,
    );
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::RecoveryPlasticSpent,
        prior.spent_quanta,
        next.spent_quanta,
    );
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::RecoveryPlasticExportedHeat,
        prior.exported_heat_quanta,
        next.exported_heat_quanta,
    );
}

fn push_dna_delta(
    entries: &mut Vec<PhysicalStateDeltaEntry>,
    predecessor: DnaExpressionState,
    successor: DnaExpressionState,
) {
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::DnaSubstrate,
        predecessor.substrate_quanta,
        successor.substrate_quanta,
    );
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::DnaFuel,
        predecessor.fuel_quanta,
        successor.fuel_quanta,
    );
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::DnaExpressedProduct,
        predecessor.expressed_product_quanta,
        successor.expressed_product_quanta,
    );
    push_u128_delta(
        entries,
        PhysicalStateCoordinate::DnaWaste,
        predecessor.waste_quanta,
        successor.waste_quanta,
    );
}

fn push_u128_delta(
    entries: &mut Vec<PhysicalStateDeltaEntry>,
    coordinate: PhysicalStateCoordinate,
    predecessor: u128,
    successor: u128,
) {
    if predecessor == successor {
        return;
    }
    entries.push(PhysicalStateDeltaEntry {
        coordinate,
        delta: ExactPhysicalStateDelta::Integral(ExactSignedDelta {
            negative: successor < predecessor,
            magnitude: predecessor.abs_diff(successor),
        }),
    });
}

fn push_rational_delta(
    entries: &mut Vec<PhysicalStateDeltaEntry>,
    coordinate: PhysicalStateCoordinate,
    predecessor: ExactRational,
    successor: ExactRational,
) -> Result<(), NeuronPhysicalError> {
    let delta = successor.checked_sub(predecessor)?;
    if delta.parts().0 != 0 {
        entries.push(PhysicalStateDeltaEntry {
            coordinate,
            delta: ExactPhysicalStateDelta::Rational(delta),
        });
    }
    Ok(())
}

fn push_i128_delta(
    entries: &mut Vec<PhysicalStateDeltaEntry>,
    coordinate: PhysicalStateCoordinate,
    predecessor: i128,
    successor: i128,
) {
    if predecessor == successor {
        return;
    }
    let (negative, magnitude) = if successor < predecessor {
        (true, predecessor.abs_diff(successor))
    } else {
        (false, successor.abs_diff(predecessor))
    };
    entries.push(PhysicalStateDeltaEntry {
        coordinate,
        delta: ExactPhysicalStateDelta::Integral(ExactSignedDelta {
            negative,
            magnitude,
        }),
    });
}

const SPARSE_DELTA_ENTRY_BYTES: usize = 1 + 8 + 1 + 16 + 16;

fn sparse_delta_coordinate_parts(coordinate: PhysicalStateCoordinate) -> (u8, usize) {
    match coordinate {
        PhysicalStateCoordinate::PsiWinding(index) => (0, index),
        PhysicalStateCoordinate::PsiDissipatedEnergy(index) => (1, index),
        PhysicalStateCoordinate::GateOpenPopulation => (2, 0),
        PhysicalStateCoordinate::GateDissipatedEnergy => (3, 0),
        PhysicalStateCoordinate::MembraneSeparatedCharge => (4, 0),
        PhysicalStateCoordinate::MembraneCarrierPhase => (5, 0),
        PhysicalStateCoordinate::ConductancePathCarrierPhase(index) => (6, index),
        PhysicalStateCoordinate::IntracellularCarrier => (7, 0),
        PhysicalStateCoordinate::ExtracellularCarrier => (8, 0),
        PhysicalStateCoordinate::RecoveryPsiFuel(index) => (9, index),
        PhysicalStateCoordinate::RecoveryPsiSpent(index) => (10, index),
        PhysicalStateCoordinate::RecoveryPsiExportedHeat(index) => (11, index),
        PhysicalStateCoordinate::RecoveryGateFuel => (12, 0),
        PhysicalStateCoordinate::RecoveryGateSpent => (13, 0),
        PhysicalStateCoordinate::RecoveryGateExportedHeat => (14, 0),
        PhysicalStateCoordinate::PlasticRestLength => (15, 0),
        PhysicalStateCoordinate::PlasticDissipatedEnergy => (16, 0),
        PhysicalStateCoordinate::RecoveryPlasticFuel => (17, 0),
        PhysicalStateCoordinate::RecoveryPlasticSpent => (18, 0),
        PhysicalStateCoordinate::RecoveryPlasticExportedHeat => (19, 0),
        PhysicalStateCoordinate::DnaSubstrate => (20, 0),
        PhysicalStateCoordinate::DnaFuel => (21, 0),
        PhysicalStateCoordinate::DnaExpressedProduct => (22, 0),
        PhysicalStateCoordinate::DnaWaste => (23, 0),
        PhysicalStateCoordinate::OpticalQuantumResidue => (24, 0),
    }
}

fn sparse_delta_coordinate_from_parts(
    tag: u8,
    index: usize,
) -> Result<PhysicalStateCoordinate, NeuronStateCodecError> {
    let coordinate = match tag {
        0 => PhysicalStateCoordinate::PsiWinding(index),
        1 => PhysicalStateCoordinate::PsiDissipatedEnergy(index),
        2 if index == 0 => PhysicalStateCoordinate::GateOpenPopulation,
        3 if index == 0 => PhysicalStateCoordinate::GateDissipatedEnergy,
        4 if index == 0 => PhysicalStateCoordinate::MembraneSeparatedCharge,
        5 if index == 0 => PhysicalStateCoordinate::MembraneCarrierPhase,
        6 => PhysicalStateCoordinate::ConductancePathCarrierPhase(index),
        7 if index == 0 => PhysicalStateCoordinate::IntracellularCarrier,
        8 if index == 0 => PhysicalStateCoordinate::ExtracellularCarrier,
        9 => PhysicalStateCoordinate::RecoveryPsiFuel(index),
        10 => PhysicalStateCoordinate::RecoveryPsiSpent(index),
        11 => PhysicalStateCoordinate::RecoveryPsiExportedHeat(index),
        12 if index == 0 => PhysicalStateCoordinate::RecoveryGateFuel,
        13 if index == 0 => PhysicalStateCoordinate::RecoveryGateSpent,
        14 if index == 0 => PhysicalStateCoordinate::RecoveryGateExportedHeat,
        15 if index == 0 => PhysicalStateCoordinate::PlasticRestLength,
        16 if index == 0 => PhysicalStateCoordinate::PlasticDissipatedEnergy,
        17 if index == 0 => PhysicalStateCoordinate::RecoveryPlasticFuel,
        18 if index == 0 => PhysicalStateCoordinate::RecoveryPlasticSpent,
        19 if index == 0 => PhysicalStateCoordinate::RecoveryPlasticExportedHeat,
        20 if index == 0 => PhysicalStateCoordinate::DnaSubstrate,
        21 if index == 0 => PhysicalStateCoordinate::DnaFuel,
        22 if index == 0 => PhysicalStateCoordinate::DnaExpressedProduct,
        23 if index == 0 => PhysicalStateCoordinate::DnaWaste,
        24 if index == 0 => PhysicalStateCoordinate::OpticalQuantumResidue,
        _ => return Err(NeuronStateCodecError::InvalidEncoding),
    };
    Ok(coordinate)
}

/// Exact wire form for one already-computed sparse physical-state delta. The
/// codec transports the existing coordinate machinery only; it computes no new
/// physics and admits no coordinate the settled delta law cannot produce.
pub(crate) fn encode_sparse_physical_state_delta(
    delta: &SparsePhysicalStateDelta,
) -> Result<Vec<u8>, NeuronStateCodecError> {
    let mut encoded = Vec::new();
    push_usize(&mut encoded, delta.entries.len())?;
    for entry in delta.entries.iter() {
        let (tag, index) = sparse_delta_coordinate_parts(entry.coordinate);
        encoded.push(tag);
        push_usize(&mut encoded, index)?;
        match entry.delta {
            ExactPhysicalStateDelta::Integral(signed) => {
                let (negative, magnitude) = signed.parts();
                encoded.push(0);
                push_u128(&mut encoded, magnitude);
                push_u128(&mut encoded, u128::from(negative));
            }
            ExactPhysicalStateDelta::Rational(rational) => {
                let (numerator, denominator) = rational.parts();
                encoded.push(1);
                push_i128(&mut encoded, numerator);
                push_u128(&mut encoded, denominator);
            }
        }
    }
    Ok(encoded)
}

pub(crate) fn decode_sparse_physical_state_delta(
    encoded: &[u8],
) -> Result<SparsePhysicalStateDelta, NeuronStateCodecError> {
    let mut reader = NeuronStateReader::new(encoded);
    let entry_count = reader.usize()?;
    let expected_length = entry_count
        .checked_mul(SPARSE_DELTA_ENTRY_BYTES)
        .and_then(|value| value.checked_add(8))
        .ok_or(NeuronStateCodecError::ArithmeticWidth)?;
    if encoded.len() != expected_length {
        return Err(NeuronStateCodecError::InvalidEncoding);
    }
    let mut entries = Vec::new();
    entries
        .try_reserve_exact(entry_count)
        .map_err(|_| NeuronStateCodecError::ArithmeticWidth)?;
    for _ in 0..entry_count {
        let tag = reader.take(1)?[0];
        let index = reader.usize()?;
        let coordinate = sparse_delta_coordinate_from_parts(tag, index)?;
        let kind = reader.take(1)?[0];
        let delta = match kind {
            0 => {
                let magnitude = reader.u128()?;
                let negative = match reader.u128()? {
                    0 => false,
                    1 => true,
                    _ => return Err(NeuronStateCodecError::InvalidEncoding),
                };
                ExactPhysicalStateDelta::Integral(
                    ExactSignedDelta::from_parts(negative, magnitude)
                        .ok_or(NeuronStateCodecError::InvalidEncoding)?,
                )
            }
            1 => {
                let numerator = reader.i128()?;
                let denominator = reader.u128()?;
                ExactPhysicalStateDelta::Rational(
                    ExactRational::new(numerator, denominator)
                        .map_err(|_| NeuronStateCodecError::InvalidEncoding)?,
                )
            }
            _ => return Err(NeuronStateCodecError::InvalidEncoding),
        };
        entries.push(
            PhysicalStateDeltaEntry::new(coordinate, delta)
                .ok_or(NeuronStateCodecError::InvalidEncoding)?,
        );
    }
    if !reader.finished() {
        return Err(NeuronStateCodecError::InvalidEncoding);
    }
    SparsePhysicalStateDelta::from_canonical_entries(entries)
        .ok_or(NeuronStateCodecError::InvalidEncoding)
}

fn apply_unsigned_member_delta(
    value: u128,
    delta: ExactSignedDelta,
) -> Result<u128, NeuronStateCodecError> {
    let (negative, magnitude) = delta.parts();
    if negative {
        value.checked_sub(magnitude)
    } else {
        value.checked_add(magnitude)
    }
    .ok_or(NeuronStateCodecError::InvalidEncoding)
}

fn apply_signed_member_delta(
    value: i128,
    delta: ExactSignedDelta,
) -> Result<i128, NeuronStateCodecError> {
    let (negative, magnitude) = delta.parts();
    let magnitude =
        i128::try_from(magnitude).map_err(|_| NeuronStateCodecError::InvalidEncoding)?;
    if negative {
        value.checked_sub(magnitude)
    } else {
        value.checked_add(magnitude)
    }
    .ok_or(NeuronStateCodecError::InvalidEncoding)
}

fn apply_rational_member_delta(
    base: ExactRational,
    delta: ExactRational,
) -> Result<ExactRational, NeuronStateCodecError> {
    base.checked_add(delta)
        .map_err(|_| NeuronStateCodecError::InvalidEncoding)
}

fn apply_phase_member_delta(
    base: ChargeCarrierPhase,
    delta: ExactRational,
) -> Result<ChargeCarrierPhase, NeuronStateCodecError> {
    let (numerator, denominator) = base.parts();
    let base = ExactRational::new(numerator, denominator)
        .map_err(|_| NeuronStateCodecError::InvalidEncoding)?;
    let (numerator, denominator) = apply_rational_member_delta(base, delta)?.parts();
    ChargeCarrierPhase::new(numerator, denominator)
        .map_err(|_| NeuronStateCodecError::InvalidEncoding)
}

fn integral_member_delta(
    delta: ExactPhysicalStateDelta,
) -> Result<ExactSignedDelta, NeuronStateCodecError> {
    match delta {
        ExactPhysicalStateDelta::Integral(signed) => Ok(signed),
        ExactPhysicalStateDelta::Rational(_) => Err(NeuronStateCodecError::InvalidEncoding),
    }
}

fn rational_member_delta(
    delta: ExactPhysicalStateDelta,
) -> Result<ExactRational, NeuronStateCodecError> {
    match delta {
        ExactPhysicalStateDelta::Rational(rational) => Ok(rational),
        ExactPhysicalStateDelta::Integral(_) => Err(NeuronStateCodecError::InvalidEncoding),
    }
}

/// Reconstruct the exact successor of `base` under one already-settled sparse
/// physical-state delta. This applies the existing coordinate machinery in the
/// forward direction; `sparse_physical_state_delta(base, applied)` returns the
/// same delta. It settles no physics and clamps nothing: any coordinate the
/// anatomy cannot carry, any capacity violation, and any arithmetic escape
/// refuses instead of adjusting.
pub(crate) fn apply_sparse_physical_state_delta(
    anatomy: &NeuronPhysicalAnatomy,
    base: &NeuronPhysicalState,
    delta: &SparsePhysicalStateDelta,
) -> Result<NeuronPhysicalState, NeuronStateCodecError> {
    let mut applied = base.clone();
    let mut separated_elementary_charges =
        applied.membrane.membrane().separated_elementary_charges();
    let mut membrane_phase = applied.membrane.membrane().carrier_phase();
    let mut path_phases = applied.membrane.path_carrier_phases();
    for entry in delta.entries() {
        match entry.coordinate() {
            PhysicalStateCoordinate::PsiWinding(index) => {
                let ring = applied
                    .psi
                    .rings
                    .get_mut(index)
                    .ok_or(NeuronStateCodecError::InvalidEncoding)?;
                let winding = apply_signed_member_delta(
                    ring.winding as i8 as i128,
                    integral_member_delta(entry.delta())?,
                )?;
                let winding = decode_winding(
                    i8::try_from(winding).map_err(|_| NeuronStateCodecError::InvalidEncoding)?,
                )?;
                ring.winding = winding;
                ring.phase_thirds = canonical_phase_thirds(winding);
            }
            PhysicalStateCoordinate::PsiDissipatedEnergy(index) => {
                let ring = applied
                    .psi
                    .rings
                    .get_mut(index)
                    .ok_or(NeuronStateCodecError::InvalidEncoding)?;
                ring.dissipated_quanta = apply_unsigned_member_delta(
                    ring.dissipated_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::GateOpenPopulation => {
                applied.gate.open_population = apply_unsigned_member_delta(
                    applied.gate.open_population,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::GateDissipatedEnergy => {
                applied.gate.dissipated_quanta = apply_unsigned_member_delta(
                    applied.gate.dissipated_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::MembraneSeparatedCharge => {
                separated_elementary_charges = apply_signed_member_delta(
                    separated_elementary_charges,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::MembraneCarrierPhase => {
                membrane_phase = apply_phase_member_delta(
                    membrane_phase,
                    rational_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::ConductancePathCarrierPhase(index) => {
                let phase = path_phases
                    .get_mut(index)
                    .ok_or(NeuronStateCodecError::InvalidEncoding)?;
                *phase = apply_phase_member_delta(*phase, rational_member_delta(entry.delta())?)?;
            }
            PhysicalStateCoordinate::IntracellularCarrier => {
                applied.carriers.intracellular = apply_unsigned_member_delta(
                    applied.carriers.intracellular,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::ExtracellularCarrier => {
                applied.carriers.extracellular = apply_unsigned_member_delta(
                    applied.carriers.extracellular,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::RecoveryPsiFuel(index) => {
                let lane = applied
                    .recovery
                    .psi_lanes
                    .get_mut(index)
                    .ok_or(NeuronStateCodecError::InvalidEncoding)?;
                lane.fuel_quanta = apply_unsigned_member_delta(
                    lane.fuel_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::RecoveryPsiSpent(index) => {
                let lane = applied
                    .recovery
                    .psi_lanes
                    .get_mut(index)
                    .ok_or(NeuronStateCodecError::InvalidEncoding)?;
                lane.spent_quanta = apply_unsigned_member_delta(
                    lane.spent_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::RecoveryPsiExportedHeat(index) => {
                let lane = applied
                    .recovery
                    .psi_lanes
                    .get_mut(index)
                    .ok_or(NeuronStateCodecError::InvalidEncoding)?;
                lane.exported_heat_quanta = apply_unsigned_member_delta(
                    lane.exported_heat_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::RecoveryGateFuel => {
                applied.recovery.gate_lane.fuel_quanta = apply_unsigned_member_delta(
                    applied.recovery.gate_lane.fuel_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::RecoveryGateSpent => {
                applied.recovery.gate_lane.spent_quanta = apply_unsigned_member_delta(
                    applied.recovery.gate_lane.spent_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::RecoveryGateExportedHeat => {
                applied.recovery.gate_lane.exported_heat_quanta = apply_unsigned_member_delta(
                    applied.recovery.gate_lane.exported_heat_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::PlasticRestLength => {
                applied.plastic.rest_length_nanometres = apply_rational_member_delta(
                    applied.plastic.rest_length_nanometres,
                    rational_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::PlasticDissipatedEnergy => {
                applied.plastic.dissipated_quanta = apply_unsigned_member_delta(
                    applied.plastic.dissipated_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::RecoveryPlasticFuel => {
                applied.recovery.plastic_lane.fuel_quanta = apply_unsigned_member_delta(
                    applied.recovery.plastic_lane.fuel_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::RecoveryPlasticSpent => {
                applied.recovery.plastic_lane.spent_quanta = apply_unsigned_member_delta(
                    applied.recovery.plastic_lane.spent_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::RecoveryPlasticExportedHeat => {
                applied.recovery.plastic_lane.exported_heat_quanta = apply_unsigned_member_delta(
                    applied.recovery.plastic_lane.exported_heat_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::DnaSubstrate => {
                applied.dna_expression.substrate_quanta = apply_unsigned_member_delta(
                    applied.dna_expression.substrate_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::DnaFuel => {
                applied.dna_expression.fuel_quanta = apply_unsigned_member_delta(
                    applied.dna_expression.fuel_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::DnaExpressedProduct => {
                applied.dna_expression.expressed_product_quanta = apply_unsigned_member_delta(
                    applied.dna_expression.expressed_product_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::DnaWaste => {
                applied.dna_expression.waste_quanta = apply_unsigned_member_delta(
                    applied.dna_expression.waste_quanta,
                    integral_member_delta(entry.delta())?,
                )?;
            }
            PhysicalStateCoordinate::OpticalQuantumResidue => {
                applied.optical_quantum_residue = apply_rational_member_delta(
                    applied.optical_quantum_residue,
                    rational_member_delta(entry.delta())?,
                )?;
            }
        }
    }
    applied.membrane = LocalMembraneConductanceState::from_physical_parts(
        ElementaryChargeMembraneState::from_physical_parts(
            separated_elementary_charges,
            membrane_phase,
        ),
        path_phases,
    );
    encode_neuron_physical_state(anatomy, &applied)?;
    Ok(applied)
}

// Measurement-only test accessors (no production logic): expose otherwise
// private conserved quantities so probe tests can report them exactly.
#[cfg(test)]
impl DnaExpressionState {
    pub(crate) fn probe_parts(self) -> (u128, u128, u128, u128) {
        (
            self.substrate_quanta,
            self.fuel_quanta,
            self.expressed_product_quanta,
            self.waste_quanta,
        )
    }
}

#[cfg(test)]
impl PlasticSupportState {
    pub(crate) fn probe_dissipated_quanta(self) -> u128 {
        self.dissipated_quanta
    }
}

#[cfg(test)]
impl NeuronPhysicalAnatomy {
    pub(crate) fn probe_plastic_dissipation_capacity_quanta(&self) -> u128 {
        self.plastic.dissipation_capacity_quanta
    }

    pub(crate) fn probe_psi_ring_dissipation_capacity_quanta(&self, index: usize) -> Option<u128> {
        self.psi
            .rings
            .get(index)
            .map(|ring| ring.dissipation_capacity_quanta)
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use super::*;
    use crate::joint_uf_neuron_boundary::{
        bind_isolated_neuron_perspective, bind_neuron_perspective,
        prepare_complete_joint_field_admitted_fixture, prepare_complete_joint_field_fixture,
        prepare_isolated_single_neuron_field_fixture, DsfFactFamily, SharedCompleteJointField,
    };
    use crate::joint_uf_source_adapter::EvaluatedJointSourceOccurrence;
    use crate::joint_uf_v1_4::{
        evaluate_with_physical_bounds, JointIntersampleLaw, JointUfCoordinateBounds, JointUfInput,
        JointUfPhysicalBounds, JointUfResult,
    };
    use crate::neuron_source_anchor::tests::exact_episode;
    use crate::neuron_source_anchor::{
        bind_neuron_source_anchor, NeuronSourceSite, PhysicalSourceSense,
    };
    use crate::physical_mosaic::admit_physical_mosaic;
    use crate::reached_neuron_cohort::{
        decode_reached_cohort_cell, decode_reached_cohort_state, decode_reached_cohort_state_delta,
        encode_reached_cohort_cell, encode_reached_cohort_cell_v4, encode_reached_cohort_state,
        encode_reached_cohort_state_delta, encode_reached_cohort_state_v4,
        settle_reached_cohort_experience_to_quiescence, settle_reached_cohort_interval,
        settle_reached_cohort_recurrence, settle_reached_cohort_to_quiescence,
        ReachedCohortAnatomy, ReachedCohortIntervalInput, ReachedCohortState,
    };
    use crate::sparse_electrical_contact::{
        ElectricalContactAnatomy, SparseElectricalAnatomy, SparseElectricalState,
    };

    fn q(numerator: i64, denominator: i64) -> Exact {
        Exact::new(BigInt::from(numerator), BigInt::from(denominator))
    }

    fn r(numerator: i128, denominator: u128) -> ExactRational {
        ExactRational::new(numerator, denominator).unwrap()
    }

    #[test]
    fn sparse_fractal_rejects_coordinate_delta_kind_mismatch() {
        let integral =
            ExactPhysicalStateDelta::Integral(ExactSignedDelta::from_parts(false, 1).unwrap());
        let rational = ExactPhysicalStateDelta::Rational(r(1, 3));

        assert!(PhysicalStateDeltaEntry::new(
            PhysicalStateCoordinate::GateOpenPopulation,
            integral,
        )
        .is_some());
        assert!(
            PhysicalStateDeltaEntry::new(PhysicalStateCoordinate::PlasticRestLength, rational,)
                .is_some()
        );
        assert!(PhysicalStateDeltaEntry::new(
            PhysicalStateCoordinate::GateOpenPopulation,
            rational,
        )
        .is_none());
        assert!(
            PhysicalStateDeltaEntry::new(PhysicalStateCoordinate::PlasticRestLength, integral,)
                .is_none()
        );
        assert!(
            SparsePhysicalStateDelta::from_canonical_entries(vec![PhysicalStateDeltaEntry {
                coordinate: PhysicalStateCoordinate::MembraneCarrierPhase,
                delta: integral,
            },])
            .is_none()
        );
    }

    fn fixture_source_sites(count: usize) -> Vec<NeuronSourceSite> {
        (0..count)
            .map(|index| NeuronSourceSite::fixture(index as u32))
            .collect()
    }

    fn fixture_lineages(count: usize) -> Vec<[u8; 16]> {
        (0..count)
            .map(|index| {
                let mut lineage = [0u8; 16];
                lineage[8..].copy_from_slice(&(index as u64 + 1).to_be_bytes());
                lineage
            })
            .collect()
    }

    fn evaluate_fixture(input: JointUfInput, bounds: &[(f64, f64)]) -> JointUfResult {
        evaluate_with_physical_bounds(
            input,
            JointUfPhysicalBounds::new(
                bounds
                    .iter()
                    .map(|(minimum, maximum)| {
                        JointUfCoordinateBounds::new(*minimum, *maximum).unwrap()
                    })
                    .collect(),
                BigRational::from_integer(BigInt::from(2)),
            )
            .unwrap(),
        )
        .unwrap()
    }

    fn shared_field() -> SharedCompleteJointField {
        let field = evaluate_fixture(
            JointUfInput {
                times: vec![q(0, 1), q(1, 2), q(1, 1), q(2, 1)],
                fields: vec![vec![0.0], vec![0.3], vec![0.3], vec![0.0]],
                relevance: vec![0.1, 0.2, 0.3, 0.4],
                intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
            },
            &[(0.0, 0.3)],
        );
        prepare_isolated_single_neuron_field_fixture(
            Arc::from([1_u8, 2, 3]),
            [4; 32],
            0,
            EvaluatedJointSourceOccurrence {
                port_indices: vec![0],
                groups: vec![vec![0]],
                field,
            },
        )
        .unwrap()
    }

    fn shared_three_neuron_field() -> SharedCompleteJointField {
        let field = evaluate_fixture(
            JointUfInput {
                times: vec![q(0, 1), q(1, 2), q(1, 1), q(2, 1)],
                fields: vec![
                    vec![0.0, 2.0, -2.0],
                    vec![0.3, 2.4, -1.7],
                    vec![0.3, 2.8, -1.4],
                    vec![0.0, 3.2, -1.1],
                ],
                relevance: vec![0.1, 0.2, 0.3, 0.4],
                intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
            },
            &[(0.0, 0.3), (2.0, 3.2), (-2.0, -1.1)],
        );
        prepare_complete_joint_field_fixture(
            Arc::from([8_u8, 9, 10]),
            [11; 32],
            0,
            EvaluatedJointSourceOccurrence {
                port_indices: vec![0, 1, 2],
                groups: vec![vec![0, 1, 2]],
                field,
            },
        )
        .unwrap()
    }

    fn shared_four_neuron_field() -> SharedCompleteJointField {
        let field = evaluate_fixture(
            JointUfInput {
                times: vec![q(0, 1), q(1, 2), q(1, 1), q(2, 1)],
                fields: vec![
                    vec![0.0, 2.0, -2.0, 4.0],
                    vec![0.3, 2.4, -1.7, 4.2],
                    vec![0.3, 2.8, -1.4, 4.4],
                    vec![0.0, 3.2, -1.1, 4.6],
                ],
                relevance: vec![0.1, 0.2, 0.3, 0.4],
                intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
            },
            &[(-10.0, 10.0), (-10.0, 10.0), (-10.0, 10.0), (-10.0, 10.0)],
        );
        prepare_complete_joint_field_fixture(
            Arc::from([12_u8, 13, 14]),
            [15; 32],
            0,
            EvaluatedJointSourceOccurrence {
                port_indices: vec![0, 1, 2, 3],
                groups: vec![vec![0, 1, 2, 3]],
                field,
            },
        )
        .unwrap()
    }

    fn ring_anatomy() -> PsiRingAnatomy {
        PsiRingAnatomy::new(
            [1, 1, 1],
            [q(0, 1), q(0, 1), q(0, 1)],
            q(1, 1),
            q(9, 2),
            10_000,
            [[true; 3]; 3],
            BalancedTrit::Quiescent,
        )
        .unwrap()
    }

    struct Fixture {
        anatomy: NeuronPhysicalAnatomy,
        state: NeuronPhysicalState,
        zero_catalysts: Vec<u128>,
        ring_count: usize,
    }

    fn physical_fixture() -> Fixture {
        scaled_physical_fixture(64, 7)
    }

    fn scaled_physical_fixture(positions: usize, constraint_count: usize) -> Fixture {
        let ring_count = positions * constraint_count * 2;
        let psi = PsiKrimelackAnatomy::new(
            positions,
            constraint_count,
            vec![ring_anatomy(); ring_count],
        )
        .unwrap();
        let gate = TwoStateGateAnatomy::new(
            2,
            0,
            q(0, 1),
            q(1, 9),
            10_000,
            r(1, 1),
            r(-1, 1),
            vec![GatePsiContact::new(0, 1, 1, q(12, 1)).unwrap()],
            ring_count,
        )
        .unwrap();
        let recovery_lane =
            RecoveryLaneAnatomy::new(1, 1, 1, 1, 100_000, 100_000, 100_000).unwrap();
        let recovery = RecoveryAnatomy::new(
            vec![recovery_lane; ring_count],
            recovery_lane,
            recovery_lane,
            ring_count,
        )
        .unwrap();
        let dna_expression = DnaExpressionAnatomy::new(1, 1, 1, 1, 1, 100_000, 100_000).unwrap();
        let plastic =
            PlasticSupportAnatomy::new(r(4, 1), r(1, 1), r(1, 1), r(3, 1), r(1, 72), 100_000)
                .unwrap();
        let anatomy = NeuronPhysicalAnatomy::new(
            MathLoomAnatomy::new(positions).unwrap(),
            psi.clone(),
            gate,
            MembraneCapacitance::new(r(1, 1)).unwrap(),
            recovery,
            dna_expression,
            plastic,
        )
        .unwrap();
        let state = NeuronPhysicalState {
            psi: PsiKrimelackState::genesis(&psi),
            gate: TwoStateGateState::genesis(0),
            membrane: LocalMembraneConductanceState::genesis(0),
            carriers: CarrierReservoirs::new(1_000_000, 1_000_000),
            recovery: RecoveryState::new(
                vec![RecoveryLaneState::new(100_000); ring_count],
                RecoveryLaneState::new(100_000),
                RecoveryLaneState::new(100_000),
            ),
            dna_expression: DnaExpressionState::new(100_000, 100_000),
            plastic: PlasticSupportState::new(r(1, 1)).unwrap(),
            optical_quantum_residue: r(0, 1),
        };
        Fixture {
            anatomy,
            state,
            zero_catalysts: vec![0; ring_count],
            ring_count,
        }
    }

    #[test]
    fn definitive_neuron_anatomy_and_state_cold_restore_exactly() {
        let fixture = physical_fixture();
        let anatomy_bytes = encode_neuron_physical_anatomy(&fixture.anatomy).unwrap();
        let restored_anatomy = decode_neuron_physical_anatomy(&anatomy_bytes).unwrap();
        assert_eq!(restored_anatomy, fixture.anatomy);
        assert_eq!(
            encode_neuron_physical_anatomy(&restored_anatomy).unwrap(),
            anatomy_bytes
        );

        let cell = encode_neuron_physical_cell(&fixture.anatomy, &fixture.state).unwrap();
        let (restored_anatomy, restored_state) = decode_neuron_physical_cell(&cell).unwrap();
        assert_eq!(restored_anatomy, fixture.anatomy);
        assert_eq!(restored_state, fixture.state);
        assert_eq!(
            encode_neuron_physical_cell(&restored_anatomy, &restored_state).unwrap(),
            cell
        );
        assert_eq!(
            decode_neuron_physical_cell(&cell[..cell.len() - 1]),
            Err(NeuronAnatomyCodecError::InvalidEncoding)
        );

        let mut incompatible_anatomy = fixture.anatomy.clone();
        incompatible_anatomy.gate.population = 1;
        let mut incompatible_state = fixture.state.clone();
        incompatible_state.gate.open_population = 2;
        let state_bytes =
            encode_neuron_physical_state(&fixture.anatomy, &incompatible_state).unwrap();
        assert_eq!(
            decode_neuron_physical_state(&incompatible_anatomy, &state_bytes),
            Err(NeuronStateCodecError::AnatomyMismatch)
        );

        let mut overfilled_recovery = fixture.state.clone();
        overfilled_recovery.recovery.psi_lanes[0].fuel_quanta = 100_001;
        assert_eq!(
            encode_neuron_physical_state(&fixture.anatomy, &overfilled_recovery),
            Err(NeuronStateCodecError::AnatomyMismatch)
        );

        let mut impossible_ring_allocation = Vec::new();
        impossible_ring_allocation.extend_from_slice(NEURON_ANATOMY_CODEC_MAGIC);
        impossible_ring_allocation.extend_from_slice(&1_u64.to_le_bytes());
        impossible_ring_allocation.extend_from_slice(&1_000_u64.to_le_bytes());
        impossible_ring_allocation.extend_from_slice(&2_000_u64.to_le_bytes());
        assert_eq!(
            decode_neuron_physical_anatomy(&impossible_ring_allocation),
            Err(NeuronAnatomyCodecError::InvalidEncoding)
        );
    }

    fn interval<'a>(
        perspective: JointNeuronPerspective<'a>,
        catalysts: &'a [u128],
    ) -> NeuronIntervalInput<'a> {
        NeuronIntervalInput {
            perspective,
            gate_work: GateWorkOccurrence::new(q(0, 1)),
            interval_microseconds: 1_000,
            recovery: RecoveryContact::new(catalysts, 0, 0),
            dna_expression: DnaExpressionContact::new(0),
            optical_successor_residue: None,
        }
    }

    fn cohort_interval_with_work<'a>(
        shared: &'a SharedCompleteJointField,
        fixtures: &'a [Fixture; 3],
        gate_index: usize,
        gate_work: [i64; 3],
    ) -> ReachedCohortIntervalInput<'a> {
        ReachedCohortIntervalInput::fixture(
            fixtures
                .iter()
                .enumerate()
                .map(|(index, fixture)| NeuronIntervalInput {
                    perspective: bind_neuron_perspective(shared, index, gate_index).unwrap(),
                    gate_work: GateWorkOccurrence::new(q(gate_work[index], 1)),
                    interval_microseconds: 1_000,
                    recovery: RecoveryContact::new(&fixture.zero_catalysts, 0, 0),
                    dna_expression: DnaExpressionContact::new(0),
                    optical_successor_residue: None,
                })
                .collect(),
            fixture_source_sites(fixtures.len()),
        )
        .unwrap()
    }

    fn four_neuron_control_interval<'a>(
        shared: &'a SharedCompleteJointField,
        fixtures: &'a [Fixture; 4],
    ) -> ReachedCohortIntervalInput<'a> {
        ReachedCohortIntervalInput::fixture(
            fixtures
                .iter()
                .enumerate()
                .map(|(index, fixture)| NeuronIntervalInput {
                    perspective: bind_neuron_perspective(shared, index, 0).unwrap(),
                    gate_work: GateWorkOccurrence::new(q(100, 1)),
                    interval_microseconds: 1_000,
                    recovery: RecoveryContact::new(&fixture.zero_catalysts, 0, 0),
                    dna_expression: DnaExpressionContact::new(0),
                    optical_successor_residue: None,
                })
                .collect(),
            fixture_source_sites(fixtures.len()),
        )
        .unwrap()
    }

    fn four_neuron_interval_with_work<'a>(
        shared: &'a SharedCompleteJointField,
        fixtures: &'a [Fixture; 4],
        gate_index: usize,
        gate_work: [i64; 4],
    ) -> ReachedCohortIntervalInput<'a> {
        ReachedCohortIntervalInput::fixture(
            fixtures
                .iter()
                .enumerate()
                .map(|(index, fixture)| NeuronIntervalInput {
                    perspective: bind_neuron_perspective(shared, index, gate_index).unwrap(),
                    gate_work: GateWorkOccurrence::new(q(gate_work[index], 1)),
                    interval_microseconds: 1_000,
                    recovery: RecoveryContact::new(&fixture.zero_catalysts, 0, 0),
                    dna_expression: DnaExpressionContact::new(0),
                    optical_successor_residue: None,
                })
                .collect(),
            fixture_source_sites(fixtures.len()),
        )
        .unwrap()
    }

    #[test]
    fn shared_dsf_causally_reaches_post_quiescence_fractal_and_control_is_zero() {
        let shared = shared_field();
        let control = bind_isolated_neuron_perspective(&shared, 0).unwrap();
        let perturbation = bind_isolated_neuron_perspective(&shared, 1).unwrap();
        assert_eq!(control.dsf().d_k, 0.0);
        assert_eq!(perturbation.dsf().d_k, 1.0);

        let fixture = physical_fixture();
        let predecessor = settle_to_quiescence(
            &fixture.anatomy,
            &fixture.state,
            &[
                interval(control, &fixture.zero_catalysts),
                interval(control, &fixture.zero_catalysts),
            ],
        )
        .unwrap();

        let causal_interval = settle_neuron_physical_interval(
            &fixture.anatomy,
            predecessor.state(),
            perturbation,
            GateWorkOccurrence::new(q(0, 1)),
            1_000,
        )
        .unwrap();
        let displacement = &causal_interval.mathloom.constraints()[0];
        assert_eq!(displacement.family(), DsfFactFamily::Displacement);
        assert_eq!(displacement.binary64_bits(), 1.0_f64.to_bits());
        assert_eq!(
            causal_interval.psi.successor.rings()[0].winding(),
            BalancedTrit::Positive
        );
        assert_eq!(
            causal_interval
                .gate_membrane
                .successor_gate
                .open_population(),
            2
        );
        assert_ne!(
            causal_interval.gate_membrane.membrane.successor,
            causal_interval.gate_membrane.membrane.predecessor
        );
        assert_eq!(
            causal_interval.gate_membrane.successor_carriers.total(),
            predecessor.state().carriers.total()
        );

        let post = [
            interval(control, &fixture.zero_catalysts),
            interval(control, &fixture.zero_catalysts),
        ];
        let settled = settle_experience_to_quiescence(
            &fixture.anatomy,
            &predecessor,
            interval(perturbation, &fixture.zero_catalysts),
            &post,
        )
        .unwrap();
        assert_eq!(settled.quiescent.state().gate.open_population(), 0);
        assert!(settled
            .quiescent
            .state()
            .psi
            .rings()
            .iter()
            .zip(predecessor.state().psi.rings())
            .all(|(successor, prior)| successor.winding() == prior.winding()));
        assert!(settled
            .quiescent
            .state()
            .psi
            .rings()
            .iter()
            .zip(predecessor.state().psi.rings())
            .any(|(successor, prior)| {
                successor.dissipated_quanta() > prior.dissipated_quanta()
            }));
        assert_eq!(
            settled
                .fractal
                .as_ref()
                .unwrap()
                .exact_delta(PhysicalStateCoordinate::PlasticRestLength),
            Some(ExactPhysicalStateDelta::Rational(r(1, 3)))
        );
        assert!(settled.fractal.as_ref().unwrap().entries().len() > 1);

        let control_only = settle_experience_to_quiescence(
            &fixture.anatomy,
            &predecessor,
            interval(control, &fixture.zero_catalysts),
            &[],
        )
        .unwrap();
        assert!(control_only.fractal.is_none());
    }

    #[test]
    fn fixed_anatomy_and_recurrence_do_not_grow_resident_state() {
        let shared = shared_field();
        let control = bind_isolated_neuron_perspective(&shared, 0).unwrap();
        let fixture = physical_fixture();
        let mut quiescent = settle_to_quiescence(
            &fixture.anatomy,
            &fixture.state,
            &[
                interval(control, &fixture.zero_catalysts),
                interval(control, &fixture.zero_catalysts),
            ],
        )
        .unwrap();
        let state_width = core::mem::size_of_val(quiescent.state());
        let psi_width = quiescent.state().psi.rings().len();
        assert_eq!(psi_width, fixture.ring_count);
        for _ in 0..100 {
            let settled = settle_experience_to_quiescence(
                &fixture.anatomy,
                &quiescent,
                interval(control, &fixture.zero_catalysts),
                &[],
            )
            .unwrap();
            assert!(settled.fractal.is_none());
            quiescent = settled.quiescent;
            assert_eq!(core::mem::size_of_val(quiescent.state()), state_width);
            assert_eq!(quiescent.state().psi.rings().len(), psi_width);
        }
    }

    #[test]
    fn three_complete_neurons_and_one_contact_commit_one_synchronous_generation() {
        let shared = shared_three_neuron_field();
        let fixtures = [physical_fixture(), physical_fixture(), physical_fixture()];
        let mut predecessor_neurons = fixtures
            .iter()
            .map(|fixture| fixture.state.clone())
            .collect::<Vec<_>>();
        predecessor_neurons[0].membrane = LocalMembraneConductanceState::genesis(1_000_000);

        let electrical_anatomy = SparseElectricalAnatomy::new(
            3,
            vec![ElectricalContactAnatomy::new(0, 1, r(1, 1), 3).unwrap()],
        )
        .unwrap();
        let electrical_state = SparseElectricalState::genesis(&electrical_anatomy);
        let cohort_anatomy = ReachedCohortAnatomy::new(
            fixtures
                .iter()
                .map(|fixture| fixture.anatomy.clone())
                .collect(),
            fixture_lineages(fixtures.len()),
            fixture_source_sites(fixtures.len()),
            electrical_anatomy,
        )
        .unwrap();
        let predecessor = ReachedCohortState::new(
            &cohort_anatomy,
            predecessor_neurons.clone(),
            electrical_state,
        )
        .unwrap();
        let inputs = fixtures
            .iter()
            .enumerate()
            .map(|(index, fixture)| {
                interval(
                    bind_neuron_perspective(&shared, index, 1).unwrap(),
                    &fixture.zero_catalysts,
                )
            })
            .collect::<Vec<_>>();
        let baselines = fixtures
            .iter()
            .zip(predecessor_neurons.iter())
            .zip(inputs.iter().cloned())
            .map(|((fixture, state), input)| {
                settle_extended_interval_with_contact(&fixture.anatomy, state, input, 0)
                    .unwrap()
                    .successor
            })
            .collect::<Vec<_>>();
        let predecessor_material = predecessor
            .neurons()
            .iter()
            .map(|state| state.carrier_reservoirs().total().unwrap())
            .sum::<u128>();
        let settled = settle_reached_cohort_interval(
            &cohort_anatomy,
            &predecessor,
            ReachedCohortIntervalInput::fixture(inputs, fixture_source_sites(fixtures.len()))
                .unwrap(),
        )
        .unwrap();

        assert_eq!(cohort_anatomy.neuron_count(), 3);
        assert_eq!(cohort_anatomy.contact_count(), 1);
        assert_eq!(settled.contact_transitions.len(), 1);
        let transferred = settled.contact_transitions[0].outward_elementary_charges_from_left;
        assert!(transferred > 0);
        assert_eq!(
            settled
                .contact_outward_elementary_charges_by_neuron
                .as_ref(),
            [transferred, -transferred, 0]
        );
        assert_eq!(
            settled
                .contact_outward_elementary_charges_by_neuron
                .iter()
                .sum::<i128>(),
            0
        );
        for index in 0..3 {
            let expected_contact = settled.contact_outward_elementary_charges_by_neuron[index];
            assert_eq!(
                settled.successor.neurons()[index]
                    .membrane_state()
                    .separated_elementary_charges(),
                baselines[index]
                    .membrane_state()
                    .separated_elementary_charges()
                    - expected_contact
            );
            let expected_intracellular = if expected_contact >= 0 {
                baselines[index].carrier_reservoirs().intracellular()
                    - expected_contact.unsigned_abs()
            } else {
                baselines[index].carrier_reservoirs().intracellular()
                    + expected_contact.unsigned_abs()
            };
            assert_eq!(
                settled.successor.neurons()[index]
                    .carrier_reservoirs()
                    .intracellular(),
                expected_intracellular
            );
            assert_eq!(
                settled.successor.neurons()[index]
                    .carrier_reservoirs()
                    .extracellular(),
                baselines[index].carrier_reservoirs().extracellular()
            );
        }
        assert_eq!(
            settled
                .successor
                .neurons()
                .iter()
                .map(|state| state.carrier_reservoirs().total().unwrap())
                .sum::<u128>(),
            predecessor_material
        );
        assert!(settled.electrically_active);
        assert!(!settled.quiescent);

        let reordered_inputs = fixtures
            .iter()
            .enumerate()
            .map(|(index, fixture)| {
                interval(
                    bind_neuron_perspective(&shared, index, 1).unwrap(),
                    &fixture.zero_catalysts,
                )
            })
            .collect::<Vec<_>>();
        let mut reordered_sites = fixture_source_sites(fixtures.len());
        reordered_sites.swap(0, 1);
        let reordered = settle_reached_cohort_interval(
            &cohort_anatomy,
            &predecessor,
            ReachedCohortIntervalInput::fixture(reordered_inputs, reordered_sites).unwrap(),
        )
        .unwrap();
        assert_eq!(reordered.successor.neurons().len(), fixtures.len());
    }

    #[test]
    fn reached_cohort_requires_exact_sight_sound_and_body_source_anatomy() {
        let episode = exact_episode();
        let shared = prepare_complete_joint_field_admitted_fixture(&episode, 0).unwrap();
        let fixtures = [
            physical_fixture(),
            physical_fixture(),
            physical_fixture(),
            physical_fixture(),
        ];
        let source_sites = (0..fixtures.len())
            .map(|index| {
                NeuronSourceSite::from_anchor(
                    bind_neuron_source_anchor(
                        &episode,
                        bind_neuron_perspective(&shared, index, 0).unwrap(),
                    )
                    .unwrap(),
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(
            source_sites
                .iter()
                .map(NeuronSourceSite::sense)
                .collect::<Vec<_>>(),
            [
                PhysicalSourceSense::Sight,
                PhysicalSourceSense::Sound,
                PhysicalSourceSense::Sound,
                PhysicalSourceSense::Body,
            ]
        );
        assert_eq!(source_sites[1].topology_index(), 0);
        assert_eq!(source_sites[2].topology_index(), 1);

        let electrical_anatomy = SparseElectricalAnatomy::new(
            4,
            vec![
                ElectricalContactAnatomy::new(0, 1, r(250, 1), 4).unwrap(),
                ElectricalContactAnatomy::new(1, 2, r(250, 1), 4).unwrap(),
                ElectricalContactAnatomy::new(2, 3, r(250, 1), 4).unwrap(),
            ],
        )
        .unwrap();
        let anatomy = ReachedCohortAnatomy::new(
            fixtures
                .iter()
                .map(|fixture| fixture.anatomy.clone())
                .collect(),
            fixture_lineages(fixtures.len()),
            source_sites,
            electrical_anatomy.clone(),
        )
        .unwrap();
        let predecessor = ReachedCohortState::new(
            &anatomy,
            fixtures
                .iter()
                .map(|fixture| fixture.state.clone())
                .collect(),
            SparseElectricalState::genesis(&electrical_anatomy),
        )
        .unwrap();
        let inputs = fixtures
            .iter()
            .enumerate()
            .map(|(index, fixture)| {
                interval(
                    bind_neuron_perspective(&shared, index, 0).unwrap(),
                    &fixture.zero_catalysts,
                )
            })
            .collect::<Vec<_>>();
        let cohort_cell = encode_reached_cohort_cell(&anatomy, &predecessor).unwrap();
        let (restored_anatomy, restored_predecessor) =
            decode_reached_cohort_cell(&cohort_cell).unwrap();
        assert_eq!(restored_anatomy, anatomy);
        assert_eq!(restored_predecessor, predecessor);
        assert_eq!(
            encode_reached_cohort_cell(&restored_anatomy, &restored_predecessor).unwrap(),
            cohort_cell
        );
        assert!(decode_reached_cohort_cell(&cohort_cell[..cohort_cell.len() - 1]).is_err());
        let input = ReachedCohortIntervalInput::from_episode(&episode, inputs).unwrap();
        let settled = settle_reached_cohort_interval(&anatomy, &predecessor, input).unwrap();
        assert_eq!(settled.successor.neurons().len(), 4);
        assert_eq!(anatomy.source_sites().len(), 4);
    }

    #[test]
    fn three_neuron_causal_sequence_emits_three_true_post_quiescence_fractals() {
        let shared = shared_three_neuron_field();
        let mut fixtures = [physical_fixture(), physical_fixture(), physical_fixture()];
        for fixture in &mut fixtures {
            fixture.anatomy.gate.single_channel_conductance_picosiemens = r(2, 1);
        }
        let electrical_anatomy = SparseElectricalAnatomy::new(
            3,
            vec![ElectricalContactAnatomy::new(0, 1, r(500, 1), 3).unwrap()],
        )
        .unwrap();
        let electrical_state = SparseElectricalState::genesis(&electrical_anatomy);
        let cohort_anatomy = ReachedCohortAnatomy::new(
            fixtures
                .iter()
                .map(|fixture| fixture.anatomy.clone())
                .collect(),
            fixture_lineages(fixtures.len()),
            fixture_source_sites(fixtures.len()),
            electrical_anatomy,
        )
        .unwrap();
        let genesis = ReachedCohortState::new(
            &cohort_anatomy,
            fixtures
                .iter()
                .map(|fixture| fixture.state.clone())
                .collect(),
            electrical_state,
        )
        .unwrap();
        let initial_controls = [
            cohort_interval_with_work(&shared, &fixtures, 0, [0, 0, 0]),
            cohort_interval_with_work(&shared, &fixtures, 0, [0, 0, 0]),
        ];
        let predecessor =
            settle_reached_cohort_to_quiescence(&cohort_anatomy, &genesis, &initial_controls)
                .unwrap();
        let predecessor_material = predecessor
            .state()
            .neurons()
            .iter()
            .map(|state| state.carrier_reservoirs().total().unwrap())
            .sum::<u128>();

        let causal_sequence = [
            cohort_interval_with_work(&shared, &fixtures, 1, [-100, 100, 100]),
            cohort_interval_with_work(&shared, &fixtures, 0, [100, 100, 100]),
            cohort_interval_with_work(&shared, &fixtures, 1, [100, -100, 100]),
            cohort_interval_with_work(&shared, &fixtures, 0, [100, 100, 100]),
            cohort_interval_with_work(&shared, &fixtures, 1, [100, 100, -100]),
            cohort_interval_with_work(&shared, &fixtures, 0, [100, 100, 100]),
            cohort_interval_with_work(&shared, &fixtures, 0, [0, 0, 0]),
            cohort_interval_with_work(&shared, &fixtures, 0, [0, 0, 0]),
        ];
        let settled = settle_reached_cohort_experience_to_quiescence(
            &cohort_anatomy,
            &predecessor,
            &causal_sequence,
        )
        .unwrap();
        assert!(settled.electrical_contact_was_active);
        assert_eq!(settled.neuron_fractals.len(), 3);
        for fractal in &settled.neuron_fractals {
            assert_eq!(
                fractal
                    .as_ref()
                    .unwrap()
                    .exact_delta(PhysicalStateCoordinate::PlasticRestLength),
                Some(ExactPhysicalStateDelta::Rational(r(1, 3)))
            );
            assert!(fractal.as_ref().unwrap().entries().len() > 1);
        }
        assert_eq!(
            settled
                .quiescent
                .state()
                .neurons()
                .iter()
                .map(|state| state.carrier_reservoirs().total().unwrap())
                .sum::<u128>(),
            predecessor_material
        );
    }

    #[test]
    fn four_neuron_partial_cue_recurs_through_sparse_chain_without_state_growth() {
        let shared = shared_four_neuron_field();
        let fixtures = [
            physical_fixture(),
            physical_fixture(),
            physical_fixture(),
            physical_fixture(),
        ];
        let electrical_anatomy = SparseElectricalAnatomy::new(
            4,
            vec![
                ElectricalContactAnatomy::new(0, 1, r(250, 1), 4).unwrap(),
                ElectricalContactAnatomy::new(1, 2, r(250, 1), 4).unwrap(),
                ElectricalContactAnatomy::new(2, 3, r(250, 1), 4).unwrap(),
            ],
        )
        .unwrap();
        let electrical_state = SparseElectricalState::genesis(&electrical_anatomy);
        let cohort_anatomy = ReachedCohortAnatomy::new(
            fixtures
                .iter()
                .map(|fixture| fixture.anatomy.clone())
                .collect(),
            fixture_lineages(fixtures.len()),
            fixture_source_sites(fixtures.len()),
            electrical_anatomy,
        )
        .unwrap();
        let mut neurons = fixtures
            .iter()
            .map(|fixture| fixture.state.clone())
            .collect::<Vec<_>>();
        neurons[0].membrane = LocalMembraneConductanceState::genesis(800_000);
        let mut state =
            ReachedCohortState::new(&cohort_anatomy, neurons, electrical_state).unwrap();
        let resident_bytes = state.resident_bytes().unwrap();
        let initial_charge = state
            .neurons()
            .iter()
            .map(|neuron| neuron.membrane_state().separated_elementary_charges())
            .sum::<i128>();
        let initial_material = state
            .neurons()
            .iter()
            .map(|neuron| neuron.carrier_reservoirs().total().unwrap())
            .sum::<u128>();
        let mut fourth_neuron_reached = false;
        for recurrence in 0..100 {
            let settled = settle_reached_cohort_interval(
                &cohort_anatomy,
                &state,
                four_neuron_control_interval(&shared, &fixtures),
            )
            .unwrap();
            assert_eq!(settled.contact_transitions.len(), 3);
            assert_eq!(settled.successor.resident_bytes(), Some(resident_bytes));
            assert_eq!(
                settled
                    .successor
                    .neurons()
                    .iter()
                    .map(|neuron| neuron.membrane_state().separated_elementary_charges())
                    .sum::<i128>(),
                initial_charge
            );
            assert_eq!(
                settled
                    .successor
                    .neurons()
                    .iter()
                    .map(|neuron| neuron.carrier_reservoirs().total().unwrap())
                    .sum::<u128>(),
                initial_material
            );
            if recurrence >= 2
                && settled.successor.neurons()[3]
                    .membrane_state()
                    .separated_elementary_charges()
                    != 0
            {
                fourth_neuron_reached = true;
            }
            state = settled.successor;
        }
        assert!(fourth_neuron_reached);
        assert_eq!(state.neurons().len(), 4);
        assert_eq!(state.electrical().contact_count(), 3);
        let encoded = encode_reached_cohort_state(&cohort_anatomy, &state).unwrap();
        let restored = decode_reached_cohort_state(&cohort_anatomy, &encoded).unwrap();
        assert_eq!(restored, state);
        assert_eq!(restored.resident_bytes(), Some(resident_bytes));
        let uninterrupted = settle_reached_cohort_interval(
            &cohort_anatomy,
            &state,
            four_neuron_control_interval(&shared, &fixtures),
        )
        .unwrap();
        let after_restart = settle_reached_cohort_interval(
            &cohort_anatomy,
            &restored,
            four_neuron_control_interval(&shared, &fixtures),
        )
        .unwrap();
        assert_eq!(after_restart, uninterrupted);
        assert!(
            decode_reached_cohort_state(&cohort_anatomy, &encoded[..encoded.len() - 1]).is_err()
        );
    }

    #[test]
    fn four_neuron_learned_assembly_admits_only_after_partial_cue_and_exact_restart() {
        let shared = shared_four_neuron_field();
        let mut fixtures = [
            physical_fixture(),
            physical_fixture(),
            physical_fixture(),
            physical_fixture(),
        ];
        for fixture in &mut fixtures {
            fixture.anatomy.gate.single_channel_conductance_picosiemens = r(2, 1);
        }
        let electrical_anatomy = SparseElectricalAnatomy::new(
            4,
            vec![
                ElectricalContactAnatomy::new(0, 1, r(500, 1), 4).unwrap(),
                ElectricalContactAnatomy::new(1, 2, r(500, 1), 4).unwrap(),
                ElectricalContactAnatomy::new(2, 3, r(500, 1), 4).unwrap(),
            ],
        )
        .unwrap();
        let cohort_anatomy = ReachedCohortAnatomy::new(
            fixtures
                .iter()
                .map(|fixture| fixture.anatomy.clone())
                .collect(),
            fixture_lineages(fixtures.len()),
            fixture_source_sites(fixtures.len()),
            electrical_anatomy.clone(),
        )
        .unwrap();
        let genesis = ReachedCohortState::new(
            &cohort_anatomy,
            fixtures
                .iter()
                .map(|fixture| fixture.state.clone())
                .collect(),
            SparseElectricalState::genesis(&electrical_anatomy),
        )
        .unwrap();
        let controls = [
            four_neuron_interval_with_work(&shared, &fixtures, 0, [0, 0, 0, 0]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [0, 0, 0, 0]),
        ];
        let pre_learning =
            settle_reached_cohort_to_quiescence(&cohort_anatomy, &genesis, &controls).unwrap();

        let mut learning = vec![
            four_neuron_interval_with_work(&shared, &fixtures, 1, [-100, 100, 100, 100]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [100, 100, 100, 100]),
            four_neuron_interval_with_work(&shared, &fixtures, 1, [100, -100, 100, 100]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [100, 100, 100, 100]),
            four_neuron_interval_with_work(&shared, &fixtures, 1, [100, 100, -100, 100]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [100, 100, 100, 100]),
            four_neuron_interval_with_work(&shared, &fixtures, 1, [100, 100, 100, -100]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [100, 100, 100, 100]),
        ];
        for _ in 0..64 {
            learning.push(four_neuron_interval_with_work(
                &shared,
                &fixtures,
                0,
                [0, 0, 0, 0],
            ));
        }
        let original = settle_reached_cohort_experience_to_quiescence(
            &cohort_anatomy,
            &pre_learning,
            &learning,
        )
        .unwrap();
        assert!(original.neuron_fractals.iter().all(Option::is_some));
        assert!(original
            .active_electrical_contacts
            .iter()
            .all(|active| *active));

        let recurrence_inputs = [
            four_neuron_interval_with_work(&shared, &fixtures, 1, [-100, 0, 0, 0]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [100, 0, 0, 0]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [0, 0, 0, 0]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [0, 0, 0, 0]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [0, 0, 0, 0]),
            four_neuron_interval_with_work(&shared, &fixtures, 0, [0, 0, 0, 0]),
        ];
        let learned_predecessor = original.quiescent.clone();
        let recurrence = settle_reached_cohort_recurrence(
            &cohort_anatomy,
            learned_predecessor.state(),
            &recurrence_inputs,
        )
        .unwrap();
        let control = settle_reached_cohort_recurrence(
            &cohort_anatomy,
            pre_learning.state(),
            &recurrence_inputs,
        )
        .unwrap();

        let encoded =
            encode_reached_cohort_state(&cohort_anatomy, learned_predecessor.state()).unwrap();
        let restored = decode_reached_cohort_state(&cohort_anatomy, &encoded).unwrap();
        let restored_recurrence =
            settle_reached_cohort_recurrence(&cohort_anatomy, &restored, &recurrence_inputs)
                .unwrap();
        assert_ne!(recurrence.successor, control.successor);
        assert_eq!(recurrence, restored_recurrence);
        let mosaic = admit_physical_mosaic(&cohort_anatomy, &original, &recurrence).unwrap();
        let mut expected_lineages = cohort_anatomy.neuron_lineages().to_vec();
        expected_lineages.sort_unstable();
        assert_eq!(mosaic.member_lineages(), expected_lineages);
        assert_eq!(mosaic.retained_fractals().len(), 4);
        assert!(mosaic.retained_fractals().iter().all(|fractal| {
            fractal.exact_delta(PhysicalStateCoordinate::PlasticRestLength)
                == Some(ExactPhysicalStateDelta::Rational(r(1, 3)))
        }));
        assert_eq!(mosaic.partial_cue_lineages(), &expected_lineages[..1]);
        assert_eq!(mosaic.original_bonds().len(), 3);
        assert_eq!(mosaic.recurrence_bonds().len(), 3);
        assert!(
            mosaic.resident_bytes().unwrap()
                < learned_predecessor.state().resident_bytes().unwrap()
        );
    }

    fn wide_cohort(
        neuron_count: usize,
    ) -> (Vec<Fixture>, ReachedCohortAnatomy, ReachedCohortState) {
        let fixtures = (0..neuron_count)
            .map(|_| physical_fixture())
            .collect::<Vec<_>>();
        let electrical_anatomy = SparseElectricalAnatomy::new(neuron_count, Vec::new()).unwrap();
        let electrical_state = SparseElectricalState::genesis(&electrical_anatomy);
        let anatomy = ReachedCohortAnatomy::new(
            fixtures
                .iter()
                .map(|fixture| fixture.anatomy.clone())
                .collect(),
            fixture_lineages(neuron_count),
            fixture_source_sites(neuron_count),
            electrical_anatomy,
        )
        .unwrap();
        let state = ReachedCohortState::new(
            &anatomy,
            fixtures
                .iter()
                .map(|fixture| fixture.state.clone())
                .collect(),
            electrical_state,
        )
        .unwrap();
        (fixtures, anatomy, state)
    }

    fn read_test_u64(encoded: &[u8], cursor: &mut usize) -> usize {
        let value = u64::from_le_bytes(encoded[*cursor..*cursor + 8].try_into().unwrap());
        *cursor += 8;
        usize::try_from(value).unwrap()
    }

    /// Structural walk of one `GLRCC04` cell: distinct anatomy-blob count,
    /// distinct state-blob count, and the byte offset of the derived
    /// recovery-fluid anatomy digest.
    fn v4_cell_shape(encoded: &[u8]) -> (usize, usize, usize) {
        assert_eq!(&encoded[..8], b"GLRCC04\0");
        let mut cursor = 8;
        let neuron_count = read_test_u64(encoded, &mut cursor);
        let anatomy_table_count = read_test_u64(encoded, &mut cursor);
        for _ in 0..anatomy_table_count {
            let length = read_test_u64(encoded, &mut cursor);
            cursor += length;
        }
        let state_table_count = read_test_u64(encoded, &mut cursor);
        for _ in 0..state_table_count {
            let length = read_test_u64(encoded, &mut cursor);
            cursor += length;
        }
        for _ in 0..neuron_count {
            cursor += 16;
            let source_length = read_test_u64(encoded, &mut cursor);
            cursor += source_length + 32 + 32;
        }
        (anatomy_table_count, state_table_count, cursor)
    }

    #[test]
    fn content_addressed_cell_dedupes_and_a_single_mutation_adds_exactly_one_blob() {
        let (_, anatomy, state) = wide_cohort(29);
        let inline_cell = encode_reached_cohort_cell(&anatomy, &state).unwrap();
        let deduplicated_cell = encode_reached_cohort_cell_v4(&anatomy, &state).unwrap();
        let (anatomy_blobs, state_blobs, _) = v4_cell_shape(&deduplicated_cell);
        assert_eq!(anatomy_blobs, 1);
        assert_eq!(state_blobs, 1);
        assert!(deduplicated_cell.len() * 10 < inline_cell.len());
        let (restored_anatomy, restored_state) =
            decode_reached_cohort_cell(&deduplicated_cell).unwrap();
        assert_eq!(restored_anatomy, anatomy);
        assert_eq!(restored_state, state);
        assert_eq!(
            encode_reached_cohort_cell_v4(&restored_anatomy, &restored_state).unwrap(),
            deduplicated_cell
        );

        let mut mutated_neurons = state.neurons().to_vec();
        mutated_neurons[5].carriers = CarrierReservoirs::new(999_999, 1_000_001);
        let mutated_state =
            ReachedCohortState::new(&anatomy, mutated_neurons, state.electrical().clone()).unwrap();
        let mutated_cell = encode_reached_cohort_cell_v4(&anatomy, &mutated_state).unwrap();
        let (anatomy_blobs, state_blobs, _) = v4_cell_shape(&mutated_cell);
        assert_eq!(anatomy_blobs, 1);
        assert_eq!(state_blobs, 2);
        let (_, remutated) = decode_reached_cohort_cell(&mutated_cell).unwrap();
        assert_eq!(remutated, mutated_state);

        eprintln!(
            "MEASURE cohort-cell 29 neurons: inline GLRCC03 = {} B, content-addressed GLRCC04 = {} B",
            inline_cell.len(),
            deduplicated_cell.len()
        );
        let inline_state = encode_reached_cohort_state(&anatomy, &state).unwrap();
        let deduplicated_state = encode_reached_cohort_state_v4(&anatomy, &state).unwrap();
        eprintln!(
            "MEASURE cohort-state 29 neurons: inline GLRCS03 = {} B, content-addressed GLRCS04 = {} B",
            inline_state.len(),
            deduplicated_state.len()
        );
    }

    /// The standard 29-neuron post-lesson body at live blob scale: 27
    /// byte-identical 458-ring card neurons plus two small distinct neurons,
    /// with retained experience evidence whose POST snapshot equals the
    /// current state and whose PRE snapshot differs in four members.
    #[test]
    fn standard_twenty_nine_neuron_post_lesson_body_measurement() {
        let card = scaled_physical_fixture(229, 1);
        let small_a = scaled_physical_fixture(8, 1);
        let small_b = scaled_physical_fixture(8, 1);
        let mut small_b_state = small_b.state.clone();
        small_b_state.carriers = CarrierReservoirs::new(999_999, 1_000_001);
        let mut anatomies = vec![card.anatomy.clone(); 27];
        anatomies.push(small_a.anatomy.clone());
        anatomies.push(small_b.anatomy.clone());
        let mut states = vec![card.state.clone(); 27];
        states.push(small_a.state.clone());
        states.push(small_b_state);
        let electrical_anatomy = SparseElectricalAnatomy::new(29, Vec::new()).unwrap();
        let electrical_state = SparseElectricalState::genesis(&electrical_anatomy);
        let anatomy = ReachedCohortAnatomy::new(
            anatomies,
            fixture_lineages(29),
            fixture_source_sites(29),
            electrical_anatomy,
        )
        .unwrap();
        let post = ReachedCohortState::new(&anatomy, states, electrical_state).unwrap();
        let mut pre_neurons = post.neurons().to_vec();
        for neuron in pre_neurons.iter_mut().take(4) {
            neuron.carriers = CarrierReservoirs::new(1_000_500, 999_500);
            neuron.gate.open_population = 1;
        }
        let pre =
            ReachedCohortState::new(&anatomy, pre_neurons, post.electrical().clone()).unwrap();

        let inline_cell = encode_reached_cohort_cell(&anatomy, &post).unwrap();
        let deduplicated_cell = encode_reached_cohort_cell_v4(&anatomy, &post).unwrap();
        let inline_snapshot = encode_reached_cohort_state(&anatomy, &pre).unwrap();
        let pre_delta = encode_reached_cohort_state_delta(&anatomy, &post, &pre).unwrap();
        assert_eq!(
            decode_reached_cohort_state_delta(&anatomy, &post, &pre_delta).unwrap(),
            pre
        );
        let (restored_anatomy, restored_post) =
            decode_reached_cohort_cell(&deduplicated_cell).unwrap();
        assert_eq!(restored_anatomy, anatomy);
        assert_eq!(restored_post, post);

        // Evidence framing: magic + mode bytes + length prefixes + the two
        // bool sections (29 neurons, 0 contacts).
        let bool_sections = 8 + 29 + 8;
        let retired_evidence =
            8 + 8 + inline_snapshot.len() + 1 + 8 + inline_snapshot.len() + bool_sections;
        let current_evidence = 8 + 1 + 8 + pre_delta.len() + 1 + 32 + bool_sections;
        let header_and_checkpoint = 90 + 74;
        let retired_body = header_and_checkpoint + 8 + inline_cell.len() + 3 + 8 + retired_evidence;
        let current_body =
            header_and_checkpoint + 8 + deduplicated_cell.len() + 3 + 8 + current_evidence;
        eprintln!(
            "MEASURE standard 29-neuron post-lesson body: retired layout = {} B, \
             content-addressed layout = {} B (cell {} -> {} B, evidence {} -> {} B)",
            retired_body,
            current_body,
            inline_cell.len(),
            deduplicated_cell.len(),
            retired_evidence,
            current_evidence
        );
        assert!(current_body < 450_000);
        assert!(current_body * 10 < retired_body);
    }

    #[test]
    fn derived_recovery_fluid_digest_mismatch_is_refused() {
        let (_, anatomy, state) = wide_cohort(3);
        let mut cell = encode_reached_cohort_cell_v4(&anatomy, &state).unwrap();
        assert!(decode_reached_cohort_cell(&cell).is_ok());
        let (_, _, digest_offset) = v4_cell_shape(&cell);
        cell[digest_offset] ^= 1;
        assert!(decode_reached_cohort_cell(&cell).is_err());
    }

    #[test]
    fn sparse_delta_wire_and_apply_reconstruct_the_exact_target_state() {
        let fixture = physical_fixture();
        let base = fixture.state.clone();
        let mut target = base.clone();
        target.gate.open_population = 1;
        target.carriers = CarrierReservoirs::new(999_000, 1_001_000);
        target.plastic.rest_length_nanometres = r(3, 2);
        target.dna_expression.waste_quanta = 7;
        target.recovery.psi_lanes[3] = RecoveryLaneState {
            fuel_quanta: 99_998,
            spent_quanta: 1,
            exported_heat_quanta: 1,
        };
        target.psi.rings[0].winding = BalancedTrit::Positive;
        target.psi.rings[0].phase_thirds = canonical_phase_thirds(BalancedTrit::Positive);
        target.membrane = LocalMembraneConductanceState::from_physical_parts(
            ElementaryChargeMembraneState::from_physical_parts(
                5,
                ChargeCarrierPhase::new(1, 3).unwrap(),
            ),
            [ChargeCarrierPhase::new(-1, 4).unwrap()],
        );
        let delta = sparse_physical_state_delta(&base, &target)
            .unwrap()
            .unwrap();
        let wire = encode_sparse_physical_state_delta(&delta).unwrap();
        let decoded = decode_sparse_physical_state_delta(&wire).unwrap();
        assert_eq!(decoded, delta);
        let applied = apply_sparse_physical_state_delta(&fixture.anatomy, &base, &decoded).unwrap();
        assert_eq!(applied, target);
        assert_eq!(
            sparse_physical_state_delta(&base, &applied).unwrap().unwrap(),
            delta
        );
        assert!(decode_sparse_physical_state_delta(&wire[..wire.len() - 1]).is_err());
        let mut unordered = wire.clone();
        unordered[0] = 2;
        assert!(decode_sparse_physical_state_delta(&unordered).is_err());
    }

    #[test]
    fn cohort_state_delta_reconstructs_exactly_and_refuses_digest_divergence() {
        let (_, anatomy, base) = wide_cohort(4);
        let mut target_neurons = base.neurons().to_vec();
        target_neurons[2].carriers = CarrierReservoirs::new(999_999, 1_000_001);
        target_neurons[2].dna_expression.waste_quanta = 3;
        let target =
            ReachedCohortState::new(&anatomy, target_neurons, base.electrical().clone()).unwrap();
        let encoded = encode_reached_cohort_state_delta(&anatomy, &base, &target).unwrap();
        let reconstructed = decode_reached_cohort_state_delta(&anatomy, &base, &encoded).unwrap();
        assert_eq!(reconstructed, target);
        assert!(encoded.len() * 20 < encode_reached_cohort_state_v4(&anatomy, &target).unwrap().len());
        eprintln!(
            "MEASURE cohort-state delta 4 neurons/1 changed: {} B (full GLRCS04 = {} B)",
            encoded.len(),
            encode_reached_cohort_state_v4(&anatomy, &target).unwrap().len()
        );

        let mut lying_digest = encoded.clone();
        let last = lying_digest.len() - 1;
        lying_digest[last] ^= 1;
        assert!(decode_reached_cohort_state_delta(&anatomy, &base, &lying_digest).is_err());
        assert!(decode_reached_cohort_state_delta(&anatomy, &target, &encoded).is_err());
    }
}
