//! Production construction of one finite virtual-material neuron.
//!
//! The constructor derives lattice width from the complete seven-field UF
//! perspective and instantiates the exact virtual units accepted for the
//! definitive neuron: zeptojoule coupling, nanometre plastic geometry,
//! picofarad membrane capacitance, picosiemens conductance, and the finite
//! elementary-charge inventory required by one femtocoulomb.  It creates no
//! meaning, score, owner, lock, database row, history, or compatibility state.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{ToPrimitive, Zero};

use crate::complete_neuron::{
    CarrierReservoirs, DnaExpressionAnatomy, DnaExpressionError, DnaExpressionState,
    GateSettlementError, NeuronPhysicalAnatomy, NeuronPhysicalError, NeuronPhysicalState,
    PlasticSupportAnatomy, PlasticSupportState, PlasticityError, PsiKrimelackAnatomy,
    PsiKrimelackState, PsiRingAnatomy, PsiSettlementError, RecoveryAnatomy, RecoveryError,
    RecoveryLaneAnatomy, RecoveryLaneState, RecoveryState, TwoStateGateAnatomy, TwoStateGateState,
};
use crate::elementary_charge_membrane::{MembraneCapacitance, MembraneChargeError};
use crate::exact_rational::{ExactRational, ExactRationalError};
use crate::joint_source_episode::NativeJointSourceEpisode;
use crate::joint_uf_neuron_boundary::{
    bind_neuron_perspective, prepare_complete_joint_field, required_mathloom_positions,
    BalancedTrit, JointNeuronBoundaryError, JointNeuronPerspective, MathLoomAnatomy,
    SharedCompleteJointField,
};
use crate::local_membrane_conductance_balance::LocalMembraneConductanceState;
use crate::neuron_source_anchor::{
    bind_neuron_source_anchor, NeuronSourceAnchorError, NeuronSourceSite,
};
use crate::reached_neuron_cohort::{
    extend_reached_cohort_cells, ReachedCohortAnatomy, ReachedCohortError, ReachedCohortState,
    ReachedNeuronGenesisCell,
};
use crate::sparse_electrical_contact::{
    SparseElectricalAnatomy, SparseElectricalError, SparseElectricalState,
};

const DSF_CONSTRAINTS: usize = 7;
const ORDINARY_GATE_DISSIPATION_QUANTUM_NUMERATOR: i64 = 1;
const ORDINARY_GATE_DISSIPATION_QUANTUM_DENOMINATOR: i64 = 16;
const ORDINARY_GATE_DISSIPATION_CAPACITY_QUANTA: u128 = 36;
const PLASTIC_ELASTIC_ENERGY_SCALE_NUMERATOR: i64 = 2;
const PLASTIC_ELASTIC_ENERGY_SCALE_DENOMINATOR: i64 = 1;
const PLASTIC_YIELD_STRESS_NUMERATOR: i64 = 1;
const PLASTIC_YIELD_STRESS_DENOMINATOR: i64 = 1;
const PLASTIC_CLOSED_COORDINATE_NUMERATOR: i64 = 1;
const PLASTIC_CLOSED_COORDINATE_DENOMINATOR: i64 = 1;
const PLASTIC_OPEN_COORDINATE_NUMERATOR: i64 = 2;
const PLASTIC_OPEN_COORDINATE_DENOMINATOR: i64 = 1;
const PLASTIC_DISSIPATION_QUANTUM_NUMERATOR: i64 = 3;
const PLASTIC_DISSIPATION_QUANTUM_DENOMINATOR: i64 = 4;
const PLASTIC_GENESIS_REST_LENGTH_NUMERATOR: i64 = 1;
const PLASTIC_GENESIS_REST_LENGTH_DENOMINATOR: i64 = 1;

/// `ceil(1 fC / e)`, where the SI elementary charge is exact.
const ONE_FEMTOCOULOMB_CARRIER_QUANTA: u128 = 6_242;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum VirtualMaterialGenesisError {
    JointField(JointNeuronBoundaryError),
    ExactRational(ExactRationalError),
    Psi(PsiSettlementError),
    Gate(GateSettlementError),
    Membrane(MembraneChargeError),
    Recovery(RecoveryError),
    Dna(DnaExpressionError),
    Plasticity(PlasticityError),
    Neuron(NeuronPhysicalError),
    Source(NeuronSourceAnchorError),
    Cohort(ReachedCohortError),
    Electrical(SparseElectricalError),
    GateEnergyLatticeUnavailable,
    ArithmeticWidth,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct VirtualMaterialNeuronGenesis {
    pub(crate) anatomy: NeuronPhysicalAnatomy,
    pub(crate) state: NeuronPhysicalState,
    pub(crate) zero_recovery_catalysts: Box<[u128]>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct VirtualMaterialReachedCohortGenesis {
    pub(crate) anatomy: ReachedCohortAnatomy,
    pub(crate) state: ReachedCohortState,
    pub(crate) zero_recovery_catalysts: Box<[Box<[u128]>]>,
}

/// Construct the complete source-specialized cells for one explicit joint
/// occurrence. Sparse contact anatomy must already exist; this function never
/// infers a synapse or gap junction from source order, coordinate proximity,
/// DSF values, or simultaneous observation.
pub(crate) fn create_virtual_material_reached_cohort(
    episode: &NativeJointSourceEpisode,
    occurrence_index: usize,
    neuron_lineages: Vec<[u8; 16]>,
    electrical: SparseElectricalAnatomy,
) -> Result<VirtualMaterialReachedCohortGenesis, VirtualMaterialGenesisError> {
    let shared = prepare_complete_joint_field(episode, occurrence_index)
        .map_err(VirtualMaterialGenesisError::JointField)?;
    create_virtual_material_reached_cohort_from_shared(
        episode,
        &shared,
        neuron_lineages,
        electrical,
    )
}

pub(crate) fn create_virtual_material_reached_cohort_from_shared(
    episode: &NativeJointSourceEpisode,
    shared: &SharedCompleteJointField,
    neuron_lineages: Vec<[u8; 16]>,
    electrical: SparseElectricalAnatomy,
) -> Result<VirtualMaterialReachedCohortGenesis, VirtualMaterialGenesisError> {
    let mut neurons = Vec::new();
    let mut states = Vec::new();
    let mut source_sites = Vec::new();
    let mut catalysts = Vec::new();
    neurons
        .try_reserve_exact(shared.vertex_count())
        .map_err(|_| VirtualMaterialGenesisError::ArithmeticWidth)?;
    states
        .try_reserve_exact(shared.vertex_count())
        .map_err(|_| VirtualMaterialGenesisError::ArithmeticWidth)?;
    source_sites
        .try_reserve_exact(shared.vertex_count())
        .map_err(|_| VirtualMaterialGenesisError::ArithmeticWidth)?;
    catalysts
        .try_reserve_exact(shared.vertex_count())
        .map_err(|_| VirtualMaterialGenesisError::ArithmeticWidth)?;
    for coordinate_index in 0..shared.vertex_count() {
        let perspective = bind_neuron_perspective(&shared, coordinate_index, 0)
            .map_err(VirtualMaterialGenesisError::JointField)?;
        let source = bind_neuron_source_anchor(episode, perspective)
            .map_err(VirtualMaterialGenesisError::Source)?;
        let genesis = create_virtual_material_neuron(perspective)?;
        source_sites.push(NeuronSourceSite::from_anchor(source));
        neurons.push(genesis.anatomy);
        states.push(genesis.state);
        catalysts.push(genesis.zero_recovery_catalysts);
    }
    let electrical_state = SparseElectricalState::genesis(&electrical);
    let anatomy = ReachedCohortAnatomy::new(neurons, neuron_lineages, source_sites, electrical)
        .map_err(VirtualMaterialGenesisError::Cohort)?;
    let state = ReachedCohortState::new(&anatomy, states, electrical_state)
        .map_err(VirtualMaterialGenesisError::Cohort)?;
    Ok(VirtualMaterialReachedCohortGenesis {
        anatomy,
        state,
        zero_recovery_catalysts: catalysts.into_boxed_slice(),
    })
}

pub(crate) fn extend_virtual_material_reached_cohort_from_shared(
    episode: &NativeJointSourceEpisode,
    shared: &SharedCompleteJointField,
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
    additions: &[(usize, [u8; 16])],
) -> Result<(ReachedCohortAnatomy, ReachedCohortState), VirtualMaterialGenesisError> {
    let mut cells = Vec::new();
    cells
        .try_reserve_exact(additions.len())
        .map_err(|_| VirtualMaterialGenesisError::ArithmeticWidth)?;
    for (coordinate_index, lineage) in additions {
        let perspective = bind_neuron_perspective(shared, *coordinate_index, 0)
            .map_err(VirtualMaterialGenesisError::JointField)?;
        let source = bind_neuron_source_anchor(episode, perspective)
            .map_err(VirtualMaterialGenesisError::Source)?;
        let genesis = create_virtual_material_neuron(perspective)?;
        cells.push(ReachedNeuronGenesisCell {
            anatomy: genesis.anatomy,
            lineage: *lineage,
            source_site: NeuronSourceSite::from_anchor(source),
            state: genesis.state,
        });
    }
    extend_reached_cohort_cells(anatomy, state, cells).map_err(VirtualMaterialGenesisError::Cohort)
}

impl VirtualMaterialNeuronGenesis {
    pub(crate) fn anatomy(&self) -> &NeuronPhysicalAnatomy {
        &self.anatomy
    }

    pub(crate) fn state(&self) -> &NeuronPhysicalState {
        &self.state
    }

    pub(crate) fn zero_recovery_catalysts(&self) -> &[u128] {
        &self.zero_recovery_catalysts
    }

    pub(crate) fn into_parts(self) -> (NeuronPhysicalAnatomy, NeuronPhysicalState, Box<[u128]>) {
        (self.anatomy, self.state, self.zero_recovery_catalysts)
    }
}

fn exact(numerator: i64, denominator: i64) -> BigRational {
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

fn ratio(numerator: i128, denominator: u128) -> Result<ExactRational, VirtualMaterialGenesisError> {
    ExactRational::new(numerator, denominator).map_err(VirtualMaterialGenesisError::ExactRational)
}

pub(crate) fn definitive_virtual_gate_capacity_zeptojoules() -> BigRational {
    exact(
        ORDINARY_GATE_DISSIPATION_QUANTUM_NUMERATOR,
        ORDINARY_GATE_DISSIPATION_QUANTUM_DENOMINATOR,
    ) * BigRational::from_integer(ORDINARY_GATE_DISSIPATION_CAPACITY_QUANTA.into())
}

/// Exact open-minus-closed support energy at the already-mounted genesis rest
/// geometry. This derives the occurrence from the same declared plastic
/// anatomy used below; it does not add a receptor coefficient.
pub(crate) fn definitive_virtual_genesis_support_energy_zeptojoules() -> BigRational {
    definitive_virtual_reachable_support_energies_zeptojoules()[0].clone()
}

/// Exact support energies reachable by the definitive one-channel plastic
/// anatomy. Genesis begins closed at rest length one. Its only yielding move
/// is the first opening, whose existing return map gives
/// `r' = xE/(E+Y) = 2*2/(2+1) = 4/3`; later closed/open moves remain inside
/// that yield surface. A receptor-specialized gate lattice must represent both
/// support energies because either can participate in its next exact delta-G.
pub(crate) fn definitive_virtual_reachable_support_energies_zeptojoules() -> [BigRational; 2] {
    let elastic_scale = exact(
        PLASTIC_ELASTIC_ENERGY_SCALE_NUMERATOR,
        PLASTIC_ELASTIC_ENERGY_SCALE_DENOMINATOR,
    );
    let yield_stress = exact(
        PLASTIC_YIELD_STRESS_NUMERATOR,
        PLASTIC_YIELD_STRESS_DENOMINATOR,
    );
    let genesis_rest = exact(
        PLASTIC_GENESIS_REST_LENGTH_NUMERATOR,
        PLASTIC_GENESIS_REST_LENGTH_DENOMINATOR,
    );
    let closed_coordinate = exact(
        PLASTIC_CLOSED_COORDINATE_NUMERATOR,
        PLASTIC_CLOSED_COORDINATE_DENOMINATOR,
    );
    let open_coordinate = exact(
        PLASTIC_OPEN_COORDINATE_NUMERATOR,
        PLASTIC_OPEN_COORDINATE_DENOMINATOR,
    );
    let yielded_open_rest = &open_coordinate * &elastic_scale / (&elastic_scale + yield_stress);
    [
        support_energy_at_rest(
            &elastic_scale,
            &closed_coordinate,
            &open_coordinate,
            &genesis_rest,
        ),
        support_energy_at_rest(
            &elastic_scale,
            &closed_coordinate,
            &open_coordinate,
            &yielded_open_rest,
        ),
    ]
}

fn support_energy_at_rest(
    elastic_scale: &BigRational,
    closed_coordinate: &BigRational,
    open_coordinate: &BigRational,
    rest: &BigRational,
) -> BigRational {
    let closed_strain = (closed_coordinate - rest) / rest;
    let open_strain = (open_coordinate - rest) / rest;
    let two = BigRational::from_integer(2.into());
    let closed_energy = elastic_scale * &closed_strain * &closed_strain / &two;
    let open_energy = elastic_scale * &open_strain * &open_strain / two;
    open_energy - closed_energy
}

/// Construct one quiescent neuron from the exact width demanded by its full
/// DSF perspective.  The constructor does not consume an experience and cannot
/// itself create a neuronal fractal.
pub(crate) fn create_virtual_material_neuron(
    perspective: JointNeuronPerspective<'_>,
) -> Result<VirtualMaterialNeuronGenesis, VirtualMaterialGenesisError> {
    create_virtual_material_neuron_with_gate_energy_quantum(
        perspective,
        exact(
            ORDINARY_GATE_DISSIPATION_QUANTUM_NUMERATOR,
            ORDINARY_GATE_DISSIPATION_QUANTUM_DENOMINATOR,
        ),
    )
}

/// Construct the same definitive virtual-material neuron with a receptor-
/// derived exact gate-energy lattice. The physical dissipation capacity is
/// preserved from the ordinary genesis as `(1/16 zJ) * 36 = 9/4 zJ`; only its
/// exact quantum count changes. No energy is rounded or selected by modality.
pub(crate) fn create_virtual_material_neuron_with_gate_energy_quantum(
    perspective: JointNeuronPerspective<'_>,
    gate_dissipation_quantum_zeptojoules: BigRational,
) -> Result<VirtualMaterialNeuronGenesis, VirtualMaterialGenesisError> {
    if gate_dissipation_quantum_zeptojoules <= BigRational::zero() {
        return Err(VirtualMaterialGenesisError::GateEnergyLatticeUnavailable);
    }
    let physical_gate_capacity_zeptojoules = definitive_virtual_gate_capacity_zeptojoules();
    let derived_capacity =
        physical_gate_capacity_zeptojoules / &gate_dissipation_quantum_zeptojoules;
    if !derived_capacity.is_integer() {
        return Err(VirtualMaterialGenesisError::GateEnergyLatticeUnavailable);
    }
    let gate_dissipation_capacity_quanta = derived_capacity
        .to_integer()
        .to_u128()
        .filter(|value| *value != 0)
        .ok_or(VirtualMaterialGenesisError::GateEnergyLatticeUnavailable)?;
    let positions = required_mathloom_positions(perspective)
        .map_err(VirtualMaterialGenesisError::JointField)?;
    let ring_count = positions
        .checked_mul(DSF_CONSTRAINTS)
        .and_then(|value| value.checked_mul(2))
        .ok_or(VirtualMaterialGenesisError::ArithmeticWidth)?;

    let ring = PsiRingAnatomy::new(
        [1, 1, 1],
        [exact(0, 1), exact(0, 1), exact(0, 1)],
        exact(1, 1),
        exact(9, 2),
        1,
        [[true; 3]; 3],
        BalancedTrit::Quiescent,
    )
    .map_err(VirtualMaterialGenesisError::Psi)?;
    let psi = PsiKrimelackAnatomy::new(positions, DSF_CONSTRAINTS, vec![ring; ring_count])
        .map_err(VirtualMaterialGenesisError::Psi)?;

    let gate = TwoStateGateAnatomy::new(
        1,
        0,
        exact(0, 1),
        gate_dissipation_quantum_zeptojoules,
        gate_dissipation_capacity_quanta,
        ratio(1, 1)?,
        ratio(-1, 1)?,
        Vec::new(),
        ring_count,
    )
    .map_err(VirtualMaterialGenesisError::Gate)?;

    let recovery_lane = RecoveryLaneAnatomy::new(1, 1, 1, 1, 1, 1, 1)
        .map_err(VirtualMaterialGenesisError::Recovery)?;
    let gate_recovery_lane = RecoveryLaneAnatomy::new(
        1,
        1,
        1,
        1,
        gate_dissipation_capacity_quanta,
        gate_dissipation_capacity_quanta,
        gate_dissipation_capacity_quanta,
    )
    .map_err(VirtualMaterialGenesisError::Recovery)?;
    let recovery = RecoveryAnatomy::new(
        vec![recovery_lane; ring_count],
        gate_recovery_lane,
        recovery_lane,
        ring_count,
    )
    .map_err(VirtualMaterialGenesisError::Recovery)?;
    let dna =
        DnaExpressionAnatomy::new(1, 1, 1, 1, 1, 1, 1).map_err(VirtualMaterialGenesisError::Dna)?;
    let plastic = PlasticSupportAnatomy::new(
        ratio(
            PLASTIC_ELASTIC_ENERGY_SCALE_NUMERATOR.into(),
            PLASTIC_ELASTIC_ENERGY_SCALE_DENOMINATOR as u128,
        )?,
        ratio(
            PLASTIC_YIELD_STRESS_NUMERATOR.into(),
            PLASTIC_YIELD_STRESS_DENOMINATOR as u128,
        )?,
        ratio(
            PLASTIC_CLOSED_COORDINATE_NUMERATOR.into(),
            PLASTIC_CLOSED_COORDINATE_DENOMINATOR as u128,
        )?,
        ratio(
            PLASTIC_OPEN_COORDINATE_NUMERATOR.into(),
            PLASTIC_OPEN_COORDINATE_DENOMINATOR as u128,
        )?,
        ratio(
            PLASTIC_DISSIPATION_QUANTUM_NUMERATOR.into(),
            PLASTIC_DISSIPATION_QUANTUM_DENOMINATOR as u128,
        )?,
        1,
    )
    .map_err(VirtualMaterialGenesisError::Plasticity)?;
    let capacitance =
        MembraneCapacitance::new(ratio(1, 1)?).map_err(VirtualMaterialGenesisError::Membrane)?;
    let mathloom =
        MathLoomAnatomy::new(positions).map_err(VirtualMaterialGenesisError::JointField)?;
    let anatomy = NeuronPhysicalAnatomy::new(
        mathloom,
        psi.clone(),
        gate,
        capacitance,
        recovery,
        dna,
        plastic,
    )
    .map_err(VirtualMaterialGenesisError::Neuron)?;
    let state = NeuronPhysicalState {
        psi: PsiKrimelackState::genesis(&psi),
        gate: TwoStateGateState::genesis(0),
        membrane: LocalMembraneConductanceState::genesis(0),
        carriers: CarrierReservoirs::new(
            ONE_FEMTOCOULOMB_CARRIER_QUANTA,
            ONE_FEMTOCOULOMB_CARRIER_QUANTA,
        ),
        recovery: RecoveryState::new(
            vec![RecoveryLaneState::new(1); ring_count],
            RecoveryLaneState::new(gate_dissipation_capacity_quanta),
            RecoveryLaneState::new(1),
        ),
        dna_expression: DnaExpressionState::new(1, 1),
        plastic: PlasticSupportState::new(ratio(
            PLASTIC_GENESIS_REST_LENGTH_NUMERATOR.into(),
            PLASTIC_GENESIS_REST_LENGTH_DENOMINATOR as u128,
        )?)
        .map_err(VirtualMaterialGenesisError::Plasticity)?,
    };
    Ok(VirtualMaterialNeuronGenesis {
        anatomy,
        state,
        zero_recovery_catalysts: vec![0; ring_count].into_boxed_slice(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::complete_neuron::{decode_neuron_physical_cell, encode_neuron_physical_cell};
    use crate::joint_uf_neuron_boundary::{bind_neuron_perspective, prepare_complete_joint_field};
    use crate::neuron_source_anchor::tests::exact_episode;
    use crate::reached_neuron_cohort::{decode_reached_cohort_cell, encode_reached_cohort_cell};
    use crate::sparse_electrical_contact::SparseElectricalAnatomy;

    #[test]
    fn production_genesis_is_exact_finite_and_cold_restorable() {
        let episode = exact_episode();
        let shared = prepare_complete_joint_field(&episode, 0).unwrap();
        let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
        let genesis = create_virtual_material_neuron(perspective).unwrap();
        assert_eq!(
            genesis.zero_recovery_catalysts().len(),
            genesis.state().psi.rings().len()
        );
        assert_eq!(
            genesis.state().carrier_reservoirs().total(),
            Some(ONE_FEMTOCOULOMB_CARRIER_QUANTA * 2)
        );
        let encoded = encode_neuron_physical_cell(genesis.anatomy(), genesis.state()).unwrap();
        let (restored_anatomy, restored_state) = decode_neuron_physical_cell(&encoded).unwrap();
        assert_eq!(&restored_anatomy, genesis.anatomy());
        assert_eq!(&restored_state, genesis.state());
        assert_eq!(
            encode_neuron_physical_cell(&restored_anatomy, &restored_state).unwrap(),
            encoded
        );
        assert!(restored_state.resident_bytes().unwrap() < encoded.len());
    }

    #[test]
    fn reached_cohort_genesis_preserves_every_source_specialization_and_cell() {
        let episode = exact_episode();
        let shared = prepare_complete_joint_field(&episode, 0).unwrap();
        let electrical = SparseElectricalAnatomy::new(shared.vertex_count(), Vec::new()).unwrap();
        let lineages = (1..=shared.vertex_count())
            .map(|index| (index as u128).to_be_bytes())
            .collect();
        let genesis =
            create_virtual_material_reached_cohort(&episode, 0, lineages, electrical).unwrap();
        assert_eq!(genesis.anatomy.neuron_count(), shared.vertex_count());
        assert_eq!(genesis.state.neurons().len(), shared.vertex_count());
        assert_eq!(genesis.zero_recovery_catalysts.len(), shared.vertex_count());
        let encoded = encode_reached_cohort_cell(&genesis.anatomy, &genesis.state).unwrap();
        let (restored_anatomy, restored_state) = decode_reached_cohort_cell(&encoded).unwrap();
        assert_eq!(restored_anatomy, genesis.anatomy);
        assert_eq!(restored_state, genesis.state);
        assert_eq!(
            encode_reached_cohort_cell(&restored_anatomy, &restored_state).unwrap(),
            encoded
        );
    }
}
