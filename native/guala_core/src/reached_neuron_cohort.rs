//! Atomic physical settlement for one explicitly reached neuron cohort.
//!
//! Every local neuron transition and every sparse electrical contact reads the
//! same predecessor generation. Contact carrier counts are then joined with
//! each neuron's local channel consequence before one membrane commit, while
//! the same carriers move equal-and-oppositely between intracellular material
//! reservoirs. Only the reached `N` neurons and `E` contacts participate.
//!
//! This module contains no whole-organism polling, dense topology, history,
//! owner, lock, database, receipt, score, label, or inferred connection.

use crate::complete_neuron::{
    apply_sparse_physical_state_delta, decode_neuron_physical_anatomy, decode_neuron_physical_cell,
    decode_neuron_physical_state, decode_sparse_physical_state_delta,
    encode_neuron_physical_anatomy, encode_neuron_physical_cell, encode_neuron_physical_state,
    encode_sparse_physical_state_delta, expand_legacy_receptor_channel_population,
    extend_neuron_positional_fabric, settle_extended_interval_with_contact,
    sparse_physical_state_delta, sparse_retained_physical_state_delta, NeuronAnatomyCodecError,
    NeuronIntervalInput, NeuronPhysicalAnatomy, NeuronPhysicalError, NeuronPhysicalState,
    NeuronStateCodecError, PlasticSupportState, RecoveryLaneAddress, SparsePhysicalStateDelta,
};
use crate::declared_geometric_anatomy::{declared_geometric_territory, DeclaredNeuronPlace};
use crate::elementary_charge_membrane::MembraneCapacitance;
use crate::elementary_charge_transfer::ChargeCarrierPhase;
use crate::exact_rational::ExactRational;
use crate::joint_source_episode::NativeJointSourceEpisode;
use crate::metabolic_feeding::{settle_dark_rest_neuron, MetabolicError};
use crate::neuron_source_anchor::{
    bind_neuron_source_anchor, decode_neuron_source_site, encode_neuron_source_site,
    NeuronSourceAnchorError, NeuronSourceSite, PhysicalSourceSense,
};
#[cfg(test)]
use crate::recovery_fluid_contact::RecoveryFluidReservoirAnatomy;
use crate::recovery_fluid_contact::{
    decode_reached_recovery_fluid_anatomy, decode_reached_recovery_fluid_state,
    encode_legacy_exhausted_recovery_fluid_state, encode_legacy_reached_recovery_fluid_anatomy,
    encode_reached_recovery_fluid_anatomy, encode_reached_recovery_fluid_state,
    expand_reached_recovery_fluid_state, extend_reached_recovery_fluid_state,
    is_legacy_recovery_fluid_state, settle_powered_environment_exchange,
    settle_resident_gate_recovery_before_interval, ReachedRecoveryFluidAnatomy, RecoveryFluidError,
    RecoveryFluidReservoirState,
};
use crate::sha256::sha256;
use crate::sparse_electrical_contact::{
    decode_sparse_electrical_cell, encode_sparse_electrical_cell, encode_sparse_electrical_cell_v1,
    settle_sparse_electrical_transfers_reached, ElectricalContactAnatomy, ElectricalContactState,
    ElectricalContactTransition, SparseElectricalAnatomy, SparseElectricalError,
    SparseElectricalState, SparseElectricalTransferSettlement,
};
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::Zero;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum ReachedCohortError {
    AnatomyStateWidth,
    InvalidNeuronLineage,
    IntervalDurationMismatch,
    PerspectiveMismatch,
    SourceAnatomyMismatch,
    MaterialConservation,
    SequenceEndedBeforeQuiescence,
    StateCodec(NeuronStateCodecError),
    NeuronCellCodec(NeuronAnatomyCodecError),
    InvalidStateEncoding,
    /// A checksum-valid retired reservoir carried a partial dimensionless
    /// quantity with no unique exact-energy image. It may be discarded only
    /// when it belongs to an unfinished, non-retained occurrence.
    UntranslatableLegacyRecoveryState,
    Electrical(SparseElectricalError),
    RecoveryFluid(RecoveryFluidError),
    Neuron {
        neuron_index: usize,
        error: NeuronPhysicalError,
    },
    Source(NeuronSourceAnchorError),
    Metabolic(MetabolicError),
    /// Two members of this cohort were authored physically identical.  Under
    /// the geometric-differentiation ratification (2026-08-05) that is not a
    /// cohort: distinct receptors occupy distinct declared places, and the
    /// energy-descent transfer law would blockade on the resulting exact tie.
    DegenerateDeclaredGeometry,
}

impl From<SparseElectricalError> for ReachedCohortError {
    fn from(value: SparseElectricalError) -> Self {
        Self::Electrical(value)
    }
}

impl From<RecoveryFluidError> for ReachedCohortError {
    fn from(value: RecoveryFluidError) -> Self {
        Self::RecoveryFluid(value)
    }
}

impl From<NeuronStateCodecError> for ReachedCohortError {
    fn from(value: NeuronStateCodecError) -> Self {
        Self::StateCodec(value)
    }
}

impl From<NeuronAnatomyCodecError> for ReachedCohortError {
    fn from(value: NeuronAnatomyCodecError) -> Self {
        Self::NeuronCellCodec(value)
    }
}

impl From<NeuronSourceAnchorError> for ReachedCohortError {
    fn from(value: NeuronSourceAnchorError) -> Self {
        Self::Source(value)
    }
}

impl From<MetabolicError> for ReachedCohortError {
    fn from(value: MetabolicError) -> Self {
        Self::Metabolic(value)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum ReachedNeuronMount {
    Receptor(NeuronSourceSite),
    Intrinsic(DeclaredNeuronPlace),
}

impl ReachedNeuronMount {
    pub(crate) fn place(&self) -> DeclaredNeuronPlace {
        match self {
            Self::Receptor(site) => DeclaredNeuronPlace::from_source_site(site),
            Self::Intrinsic(place) => *place,
        }
    }

    pub(crate) fn source_site(&self) -> Option<&NeuronSourceSite> {
        match self {
            Self::Receptor(site) => Some(site),
            Self::Intrinsic(_) => None,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ReachedCohortAnatomy {
    neurons: Box<[NeuronPhysicalAnatomy]>,
    neuron_lineages: Box<[[u8; 16]]>,
    mounts: Box<[ReachedNeuronMount]>,
    electrical: SparseElectricalAnatomy,
    recovery_fluid: ReachedRecoveryFluidAnatomy,
}

impl ReachedCohortAnatomy {
    pub(crate) fn new(
        neurons: Vec<NeuronPhysicalAnatomy>,
        neuron_lineages: Vec<[u8; 16]>,
        source_sites: Vec<NeuronSourceSite>,
        electrical: SparseElectricalAnatomy,
    ) -> Result<Self, ReachedCohortError> {
        Self::new_mounted(
            neurons,
            neuron_lineages,
            source_sites
                .into_iter()
                .map(ReachedNeuronMount::Receptor)
                .collect(),
            electrical,
        )
    }

    pub(crate) fn new_mounted(
        neurons: Vec<NeuronPhysicalAnatomy>,
        neuron_lineages: Vec<[u8; 16]>,
        mounts: Vec<ReachedNeuronMount>,
        electrical: SparseElectricalAnatomy,
    ) -> Result<Self, ReachedCohortError> {
        if neurons.is_empty()
            || neurons.len() != neuron_lineages.len()
            || neurons.len() != mounts.len()
            || neurons.len() != electrical.neuron_count()
        {
            return Err(ReachedCohortError::AnatomyStateWidth);
        }
        if neuron_lineages.iter().any(|lineage| *lineage == [0; 16])
            || neuron_lineages
                .iter()
                .enumerate()
                .any(|(index, lineage)| neuron_lineages[..index].contains(lineage))
        {
            return Err(ReachedCohortError::InvalidNeuronLineage);
        }
        // Injectivity, enforced where the cohort is authored: the capacitance
        // derivation is injective on declared places, so equal capacitances
        // here mean two members were declared at the same place.  Refuse
        // rather than author identical pieces (see declared_geometric_anatomy).
        if neurons.iter().enumerate().any(|(index, neuron)| {
            neurons[..index]
                .iter()
                .any(|earlier| earlier.capacitance() == neuron.capacitance())
        }) {
            return Err(ReachedCohortError::DegenerateDeclaredGeometry);
        }
        if mounts.iter().enumerate().any(|(index, mount)| {
            mounts[..index]
                .iter()
                .any(|earlier| earlier.place() == mount.place())
        }) {
            return Err(ReachedCohortError::DegenerateDeclaredGeometry);
        }
        let recovery_fluid = ReachedRecoveryFluidAnatomy::derive(&neurons)?;
        Ok(Self {
            neurons: neurons.into_boxed_slice(),
            neuron_lineages: neuron_lineages.into_boxed_slice(),
            mounts: mounts.into_boxed_slice(),
            electrical,
            recovery_fluid,
        })
    }

    pub(crate) fn neuron_count(&self) -> usize {
        self.neurons.len()
    }

    pub(crate) fn contact_count(&self) -> usize {
        self.electrical.contact_count()
    }

    pub(crate) fn mounts(&self) -> &[ReachedNeuronMount] {
        &self.mounts
    }

    pub(crate) fn source_site(&self, neuron_index: usize) -> Option<&NeuronSourceSite> {
        self.mounts.get(neuron_index)?.source_site()
    }

    pub(crate) fn source_sites(&self) -> impl Iterator<Item = &NeuronSourceSite> {
        self.mounts.iter().filter_map(ReachedNeuronMount::source_site)
    }

    pub(crate) fn source_site_member(&self, site: &NeuronSourceSite) -> Option<usize> {
        self.mounts.iter().position(|mount| mount.source_site() == Some(site))
    }

    pub(crate) fn neuron_anatomies(&self) -> &[NeuronPhysicalAnatomy] {
        &self.neurons
    }

    pub(crate) fn neuron_lineages(&self) -> &[[u8; 16]] {
        &self.neuron_lineages
    }

    pub(crate) fn contact_endpoints(&self) -> impl ExactSizeIterator<Item = (usize, usize)> + '_ {
        self.electrical.contact_endpoints()
    }

    pub(crate) fn electrical_anatomy(&self) -> &SparseElectricalAnatomy {
        &self.electrical
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ReachedCohortState {
    neurons: Box<[NeuronPhysicalState]>,
    electrical: SparseElectricalState,
    recovery_fluid: RecoveryFluidReservoirState,
}

impl ReachedCohortState {
    pub(crate) fn new(
        anatomy: &ReachedCohortAnatomy,
        neurons: Vec<NeuronPhysicalState>,
        electrical: SparseElectricalState,
    ) -> Result<Self, ReachedCohortError> {
        if neurons.len() != anatomy.neurons.len()
            || electrical.contact_count() != anatomy.electrical.contact_count()
        {
            return Err(ReachedCohortError::AnatomyStateWidth);
        }
        Ok(Self {
            neurons: neurons.into_boxed_slice(),
            electrical,
            recovery_fluid: anatomy.recovery_fluid.genesis_state(),
        })
    }

    fn from_mounted_parts(
        anatomy: &ReachedCohortAnatomy,
        neurons: Vec<NeuronPhysicalState>,
        electrical: SparseElectricalState,
        recovery_fluid: RecoveryFluidReservoirState,
    ) -> Result<Self, ReachedCohortError> {
        if neurons.len() != anatomy.neurons.len()
            || electrical.contact_count() != anatomy.electrical.contact_count()
        {
            return Err(ReachedCohortError::AnatomyStateWidth);
        }
        encode_reached_recovery_fluid_state(&anatomy.recovery_fluid, recovery_fluid)?;
        Ok(Self {
            neurons: neurons.into_boxed_slice(),
            electrical,
            recovery_fluid,
        })
    }

    pub(crate) fn neurons(&self) -> &[NeuronPhysicalState] {
        &self.neurons
    }

    pub(crate) fn electrical(&self) -> &SparseElectricalState {
        &self.electrical
    }

    pub(crate) fn recovery_fluid(&self) -> RecoveryFluidReservoirState {
        self.recovery_fluid
    }

    #[cfg(test)]
    pub(crate) fn with_recovery_fluid_for_test(
        &self,
        anatomy: &ReachedCohortAnatomy,
        recovery_fluid: RecoveryFluidReservoirState,
    ) -> Result<Self, ReachedCohortError> {
        Self::from_mounted_parts(
            anatomy,
            self.neurons.to_vec(),
            self.electrical.clone(),
            recovery_fluid,
        )
    }

    #[cfg(test)]
    pub(crate) fn recovery_fluid_anatomy_for_test(
        anatomy: &ReachedCohortAnatomy,
    ) -> RecoveryFluidReservoirAnatomy {
        anatomy.recovery_fluid.reservoir_anatomy()
    }

    pub(crate) fn resident_bytes(&self) -> Option<usize> {
        let mut total =
            core::mem::size_of::<Self>().checked_add(self.electrical.resident_contact_bytes()?)?;
        for neuron in &self.neurons {
            total = total.checked_add(neuron.resident_bytes()?)?;
        }
        Some(total)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ReachedNeuronGenesisCell {
    pub(crate) anatomy: NeuronPhysicalAnatomy,
    pub(crate) lineage: [u8; 16],
    pub(crate) mount: ReachedNeuronMount,
    pub(crate) state: NeuronPhysicalState,
}

pub(crate) fn extend_reached_cohort_cells(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
    additions: Vec<ReachedNeuronGenesisCell>,
) -> Result<(ReachedCohortAnatomy, ReachedCohortState), ReachedCohortError> {
    if additions.is_empty() {
        return Ok((anatomy.clone(), state.clone()));
    }
    let successor_count = anatomy
        .neuron_count()
        .checked_add(additions.len())
        .ok_or(ReachedCohortError::AnatomyStateWidth)?;
    let mut neurons = anatomy.neurons.to_vec();
    let mut lineages = anatomy.neuron_lineages.to_vec();
    let mut mounts = anatomy.mounts.to_vec();
    let mut neuron_states = state.neurons.to_vec();
    for addition in additions {
        if lineages.contains(&addition.lineage)
            || mounts.iter().any(|mount| mount.place() == addition.mount.place())
        {
            return Err(ReachedCohortError::InvalidNeuronLineage);
        }
        neurons.push(addition.anatomy);
        lineages.push(addition.lineage);
        mounts.push(addition.mount);
        neuron_states.push(addition.state);
    }
    let electrical = anatomy.electrical.extend_neuron_count(successor_count)?;
    let successor_anatomy =
        ReachedCohortAnatomy::new_mounted(neurons, lineages, mounts, electrical)?;
    let recovery_fluid = extend_reached_recovery_fluid_state(
        &anatomy.recovery_fluid,
        &successor_anatomy.recovery_fluid,
        state.recovery_fluid,
    )?;
    let successor_state = ReachedCohortState::from_mounted_parts(
        &successor_anatomy,
        neuron_states,
        state.electrical.clone(),
        recovery_fluid,
    )?;
    Ok((successor_anatomy, successor_state))
}

/// Extend the positional fabric of selected existing neurons while preserving
/// cohort contacts, lineage, declared place, fluid state, and every unrelated
/// neuronal coordinate.
pub(crate) fn extend_reached_cohort_positional_fabrics(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
    required_positions: &[usize],
) -> Result<(ReachedCohortAnatomy, ReachedCohortState), ReachedCohortError> {
    if required_positions.len() != anatomy.neuron_count()
        || state.neurons.len() != anatomy.neuron_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut neurons = Vec::with_capacity(anatomy.neuron_count());
    let mut states = Vec::with_capacity(anatomy.neuron_count());
    for (neuron_index, ((neuron_anatomy, neuron_state), required)) in anatomy
        .neurons
        .iter()
        .zip(state.neurons.iter())
        .zip(required_positions)
        .enumerate()
    {
        let (successor_anatomy, successor_state) =
            extend_neuron_positional_fabric(neuron_anatomy, neuron_state, *required).map_err(
                |error| ReachedCohortError::Neuron {
                    neuron_index,
                    error,
                },
            )?;
        neurons.push(successor_anatomy);
        states.push(successor_state);
    }
    if neurons == anatomy.neurons.as_ref() {
        return Ok((anatomy.clone(), state.clone()));
    }
    let successor_anatomy = ReachedCohortAnatomy::new_mounted(
        neurons,
        anatomy.neuron_lineages.to_vec(),
        anatomy.mounts.to_vec(),
        anatomy.electrical.clone(),
    )?;
    let recovery_fluid = extend_reached_recovery_fluid_state(
        &anatomy.recovery_fluid,
        &successor_anatomy.recovery_fluid,
        state.recovery_fluid,
    )?;
    let successor_state = ReachedCohortState::from_mounted_parts(
        &successor_anatomy,
        states,
        state.electrical.clone(),
        recovery_fluid,
    )?;
    Ok((successor_anatomy, successor_state))
}

/// One-way, locality-derived correction of legacy one-channel sight members.
/// Lineage, source place, contacts, every existing physical coordinate, and
/// reservoir history remain attached to the same neuron. Only omitted virgin
/// receptor material for that already-declared territory is added.
pub(crate) fn expand_legacy_sight_channel_populations(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
    virgin_carriers_per_compartment: u128,
) -> Result<(ReachedCohortAnatomy, ReachedCohortState), ReachedCohortError> {
    if anatomy.neuron_count() != state.neurons.len() {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut successor_anatomies = Vec::with_capacity(anatomy.neuron_count());
    let mut successor_states = Vec::with_capacity(anatomy.neuron_count());
    let mut changed = false;
    for (neuron_index, ((neuron_anatomy, neuron_state), mount)) in anatomy
        .neurons
        .iter()
        .zip(state.neurons.iter())
        .zip(anatomy.mounts.iter())
        .enumerate()
    {
        let target_population = match mount.source_site() {
            Some(source_site) if source_site.sense() == PhysicalSourceSense::Sight => {
                declared_geometric_territory(source_site)
                    .map_err(|_| ReachedCohortError::SourceAnatomyMismatch)?
            }
            _ => 1,
        };
        let (successor_anatomy, successor_state) = expand_legacy_receptor_channel_population(
            neuron_anatomy,
            neuron_state,
            target_population,
            virgin_carriers_per_compartment,
        )
        .map_err(|error| ReachedCohortError::Neuron {
            neuron_index,
            error,
        })?;
        changed |= successor_anatomy != *neuron_anatomy || successor_state != *neuron_state;
        successor_anatomies.push(successor_anatomy);
        successor_states.push(successor_state);
    }
    if !changed {
        return Ok((anatomy.clone(), state.clone()));
    }
    let successor_anatomy = ReachedCohortAnatomy::new_mounted(
        successor_anatomies,
        anatomy.neuron_lineages.to_vec(),
        anatomy.mounts.to_vec(),
        anatomy.electrical.clone(),
    )?;
    let recovery_fluid = expand_reached_recovery_fluid_state(
        &anatomy.recovery_fluid,
        &successor_anatomy.recovery_fluid,
        state.recovery_fluid,
    )?;
    let successor_state = ReachedCohortState::from_mounted_parts(
        &successor_anatomy,
        successor_states,
        state.electrical.clone(),
        recovery_fluid,
    )?;
    Ok((successor_anatomy, successor_state))
}

/// Append authored contacts to a living cohort.
///
/// Mirrors `extend_reached_cohort_cells`' discipline on the other axis: the
/// members, their lineages, their source sites, their physical states and the
/// recovery-fluid reservoir all travel through verbatim, and the electrical
/// anatomy grows only at its end.  Every already-authored contact keeps its
/// index, endpoints, conductance and its retained unresolved carrier phase;
/// each appended contact starts from the authored rest state.
///
/// `additions` are authored `(left_member, right_member, conductance)` in this
/// cohort's own member indices.  No adjacency, endpoint, or conductance is
/// derived here — this boundary only carries what the caller authored.
pub(crate) fn extend_reached_cohort_contacts(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
    additions: Vec<(usize, usize, ExactRational)>,
) -> Result<(ReachedCohortAnatomy, ReachedCohortState), ReachedCohortError> {
    if additions.is_empty() {
        return Ok((anatomy.clone(), state.clone()));
    }
    let neuron_count = anatomy.neuron_count();
    let mut authored = Vec::new();
    authored
        .try_reserve_exact(additions.len())
        .map_err(|_| ReachedCohortError::AnatomyStateWidth)?;
    for (left, right, conductance) in additions {
        authored.push(ElectricalContactAnatomy::new(
            left,
            right,
            conductance,
            neuron_count,
        )?);
    }
    let electrical = anatomy.electrical.append_contacts(authored)?;
    let electrical_state = state.electrical.append_genesis_contacts(&electrical)?;
    let successor_anatomy = ReachedCohortAnatomy::new_mounted(
        anatomy.neurons.to_vec(),
        anatomy.neuron_lineages.to_vec(),
        anatomy.mounts.to_vec(),
        electrical,
    )?;
    // Nothing about the members may move when only contacts are appended.
    if successor_anatomy.neurons != anatomy.neurons
        || successor_anatomy.neuron_lineages != anatomy.neuron_lineages
        || successor_anatomy.mounts != anatomy.mounts
        || successor_anatomy.recovery_fluid != anatomy.recovery_fluid
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let successor_state = ReachedCohortState::from_mounted_parts(
        &successor_anatomy,
        state.neurons.to_vec(),
        electrical_state,
        state.recovery_fluid,
    )?;
    Ok((successor_anatomy, successor_state))
}

/// Widen one retained cohort-state snapshot onto an anatomy whose contacts
/// were appended to.
///
/// Used for the rest-state snapshots a living cohort retains at experience
/// boundaries: every member state and every existing carrier phase travels
/// through verbatim, and each newly authored contact carries the authored
/// rest state, because a contact that did not exist held no unresolved phase.
pub(crate) fn widen_reached_cohort_state_contacts(
    successor_anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<ReachedCohortState, ReachedCohortError> {
    let electrical = state
        .electrical
        .append_genesis_contacts(&successor_anatomy.electrical)?;
    ReachedCohortState::from_mounted_parts(
        successor_anatomy,
        state.neurons.to_vec(),
        electrical,
        state.recovery_fluid,
    )
}

pub(crate) fn extend_reached_cohort_state_with_genesis(
    predecessor_anatomy: &ReachedCohortAnatomy,
    predecessor_state: &ReachedCohortState,
    successor_anatomy: &ReachedCohortAnatomy,
    genesis_states: &[NeuronPhysicalState],
) -> Result<ReachedCohortState, ReachedCohortError> {
    if predecessor_anatomy
        .neuron_count()
        .checked_add(genesis_states.len())
        != Some(successor_anatomy.neuron_count())
        || successor_anatomy.neuron_anatomies()[..predecessor_anatomy.neuron_count()]
            != predecessor_anatomy.neuron_anatomies()[..]
        || successor_anatomy.neuron_lineages()[..predecessor_anatomy.neuron_count()]
            != predecessor_anatomy.neuron_lineages()[..]
        || successor_anatomy.mounts()[..predecessor_anatomy.neuron_count()]
            != predecessor_anatomy.mounts()[..]
        || successor_anatomy.contact_count() != predecessor_anatomy.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut neurons = predecessor_state.neurons.to_vec();
    neurons.extend_from_slice(genesis_states);
    let recovery_fluid = extend_reached_recovery_fluid_state(
        &predecessor_anatomy.recovery_fluid,
        &successor_anatomy.recovery_fluid,
        predecessor_state.recovery_fluid,
    )?;
    ReachedCohortState::from_mounted_parts(
        successor_anatomy,
        neurons,
        predecessor_state.electrical.clone(),
        recovery_fluid,
    )
}

const REACHED_COHORT_CODEC_MAGIC: &[u8; 8] = b"GLRCS03\0";
const REACHED_COHORT_CELL_CODEC_MAGIC: &[u8; 8] = b"GLRCC03\0";
const REACHED_COHORT_CODEC_V4_MAGIC: &[u8; 8] = b"GLRCS04\0";
const REACHED_COHORT_CODEC_V5_MAGIC: &[u8; 8] = b"GLRCS05\0";
const REACHED_COHORT_CELL_CODEC_V5_MAGIC: &[u8; 8] = b"GLRCC05\0";
const REACHED_COHORT_CELL_CODEC_V6_MAGIC: &[u8; 8] = b"GLRCC06\0";
const REACHED_COHORT_STATE_DELTA_MAGIC: &[u8; 8] = b"GLRSD01\0";
const REACHED_COHORT_STATE_DELTA_V2_MAGIC: &[u8; 8] = b"GLRSD02\0";
const MIN_REACHED_COHORT_NEURON_RECORD_BYTES: usize = 32;
const CONTENT_DIGEST_BYTES: usize = 32;

/// Encode the fixed source specialization, complete physical neuron cells, and
/// sparse electrical fabric as one restartable reached cohort. This boundary
/// transports already-admitted physics; it selects no anatomy or coefficients.
/// This is the retired inline layout retained so that pre-deduplication bodies
/// still restore and re-verify canonically; new bodies use the `GLRCC05`
/// content-addressed layout.
pub(crate) fn encode_reached_cohort_cell(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<Vec<u8>, ReachedCohortError> {
    if anatomy.neurons.len() != anatomy.mounts.len()
        || anatomy.neurons.len() != state.neurons.len()
        || anatomy.electrical.contact_count() != state.electrical.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(REACHED_COHORT_CELL_CODEC_MAGIC);
    push_cohort_usize(&mut encoded, anatomy.neurons.len())?;
    for (((lineage, mount), neuron_anatomy), neuron_state) in anatomy
        .neuron_lineages
        .iter()
        .zip(anatomy.mounts.iter())
        .zip(anatomy.neurons.iter())
        .zip(state.neurons.iter())
    {
        encoded.extend_from_slice(lineage);
        let source_site = mount
            .source_site()
            .ok_or(ReachedCohortError::InvalidStateEncoding)?;
        let source = encode_neuron_source_site(source_site)?;
        let neuron = encode_neuron_physical_cell(neuron_anatomy, neuron_state)?;
        push_cohort_usize(&mut encoded, source.len())?;
        encoded.extend_from_slice(&source);
        push_cohort_usize(&mut encoded, neuron.len())?;
        encoded.extend_from_slice(&neuron);
    }
    let recovery_anatomy = encode_reached_recovery_fluid_anatomy(&anatomy.recovery_fluid)?;
    let recovery_state =
        encode_reached_recovery_fluid_state(&anatomy.recovery_fluid, state.recovery_fluid)?;
    push_cohort_usize(&mut encoded, recovery_anatomy.len())?;
    encoded.extend_from_slice(&recovery_anatomy);
    push_cohort_usize(&mut encoded, recovery_state.len())?;
    encoded.extend_from_slice(&recovery_state);
    let electrical = encode_sparse_electrical_cell(&anatomy.electrical, &state.electrical)?;
    push_cohort_usize(&mut encoded, electrical.len())?;
    encoded.extend_from_slice(&electrical);
    Ok(encoded)
}

pub(crate) fn decode_reached_cohort_cell(
    encoded: &[u8],
) -> Result<(ReachedCohortAnatomy, ReachedCohortState), ReachedCohortError> {
    if encoded.get(..REACHED_COHORT_CELL_CODEC_V6_MAGIC.len())
        == Some(REACHED_COHORT_CELL_CODEC_V6_MAGIC)
    {
        return decode_reached_cohort_cell_v6(encoded);
    }
    if encoded.get(..REACHED_COHORT_CELL_CODEC_V5_MAGIC.len())
        == Some(REACHED_COHORT_CELL_CODEC_V5_MAGIC)
    {
        return decode_reached_cohort_cell_v5(encoded);
    }
    let mut reader = CohortStateReader::new(encoded);
    if reader.take(REACHED_COHORT_CELL_CODEC_MAGIC.len())? != REACHED_COHORT_CELL_CODEC_MAGIC {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let neuron_count = reader.usize()?;
    if neuron_count == 0 {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    reader.require_records(neuron_count, MIN_REACHED_COHORT_NEURON_RECORD_BYTES)?;
    let mut source_sites = Vec::new();
    let mut neuron_lineages = Vec::new();
    let mut neuron_anatomies = Vec::new();
    let mut neuron_states = Vec::new();
    source_sites
        .try_reserve_exact(neuron_count)
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
    neuron_lineages
        .try_reserve_exact(neuron_count)
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
    neuron_anatomies
        .try_reserve_exact(neuron_count)
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
    neuron_states
        .try_reserve_exact(neuron_count)
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
    for _ in 0..neuron_count {
        neuron_lineages.push(
            reader
                .take(16)?
                .try_into()
                .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
        );
        let source_length = reader.usize()?;
        source_sites.push(decode_neuron_source_site(reader.take(source_length)?)?);
        let neuron_length = reader.usize()?;
        let (anatomy, state) = decode_neuron_physical_cell(reader.take(neuron_length)?)?;
        neuron_anatomies.push(anatomy);
        neuron_states.push(state);
    }
    let recovery_anatomy_length = reader.usize()?;
    let encoded_recovery_anatomy = reader.take(recovery_anatomy_length)?;
    let recovery_state_length = reader.usize()?;
    let encoded_recovery_state = reader.take(recovery_state_length)?;
    let electrical_length = reader.usize()?;
    let (electrical_anatomy, electrical_state) =
        decode_sparse_electrical_cell(reader.take(electrical_length)?)?;
    if !reader.finished() {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let anatomy = ReachedCohortAnatomy::new(
        neuron_anatomies,
        neuron_lineages,
        source_sites,
        electrical_anatomy,
    )?;
    let decoded_recovery_anatomy =
        decode_reached_recovery_fluid_anatomy(encoded_recovery_anatomy, &anatomy.neurons)?;
    if decoded_recovery_anatomy != anatomy.recovery_fluid {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let recovery_fluid =
        decode_reached_recovery_fluid_state(encoded_recovery_state, &anatomy.recovery_fluid)?;
    let state = ReachedCohortState::from_mounted_parts(
        &anatomy,
        neuron_states,
        electrical_state,
        recovery_fluid,
    )?;
    Ok((anatomy, state))
}

pub(crate) fn encode_reached_cohort_state(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<Vec<u8>, ReachedCohortError> {
    if state.neurons.len() != anatomy.neurons.len()
        || state.electrical.contact_count() != anatomy.electrical.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(REACHED_COHORT_CODEC_MAGIC);
    push_cohort_usize(&mut encoded, state.neurons.len())?;
    push_cohort_usize(&mut encoded, state.electrical.contact_count())?;
    for ((lineage, neuron_anatomy), neuron_state) in anatomy
        .neuron_lineages
        .iter()
        .zip(anatomy.neurons.iter())
        .zip(state.neurons.iter())
    {
        encoded.extend_from_slice(lineage);
        let neuron = encode_neuron_physical_state(neuron_anatomy, neuron_state)?;
        push_cohort_usize(&mut encoded, neuron.len())?;
        encoded.extend_from_slice(&neuron);
    }
    for contact in state.electrical.contact_states() {
        let (numerator, denominator) = contact.carrier_phase().parts();
        encoded.extend_from_slice(&numerator.to_le_bytes());
        encoded.extend_from_slice(&denominator.to_le_bytes());
    }
    let recovery_state =
        encode_reached_recovery_fluid_state(&anatomy.recovery_fluid, state.recovery_fluid)?;
    push_cohort_usize(&mut encoded, recovery_state.len())?;
    encoded.extend_from_slice(&recovery_state);
    Ok(encoded)
}

pub(crate) fn decode_reached_cohort_state(
    anatomy: &ReachedCohortAnatomy,
    encoded: &[u8],
) -> Result<ReachedCohortState, ReachedCohortError> {
    if encoded.get(..REACHED_COHORT_CODEC_V5_MAGIC.len()) == Some(REACHED_COHORT_CODEC_V5_MAGIC) {
        return decode_reached_cohort_state_v5(anatomy, encoded);
    }
    if encoded.get(..REACHED_COHORT_CODEC_V4_MAGIC.len()) == Some(REACHED_COHORT_CODEC_V4_MAGIC) {
        return decode_reached_cohort_state_v4(anatomy, encoded);
    }
    let mut reader = CohortStateReader::new(encoded);
    if reader.take(REACHED_COHORT_CODEC_MAGIC.len())? != REACHED_COHORT_CODEC_MAGIC {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let neuron_count = reader.usize()?;
    let contact_count = reader.usize()?;
    if neuron_count != anatomy.neurons.len() || contact_count != anatomy.electrical.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut neurons = Vec::with_capacity(neuron_count);
    for (index, neuron_anatomy) in anatomy.neurons.iter().enumerate() {
        let lineage: [u8; 16] = reader
            .take(16)?
            .try_into()
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        if lineage != anatomy.neuron_lineages[index] {
            return Err(ReachedCohortError::InvalidNeuronLineage);
        }
        let encoded_neuron_length = reader.usize()?;
        neurons.push(decode_neuron_physical_state(
            neuron_anatomy,
            reader.take(encoded_neuron_length)?,
        )?);
    }
    let mut contacts = Vec::with_capacity(contact_count);
    for _ in 0..contact_count {
        let phase = ChargeCarrierPhase::new(reader.i128()?, reader.u128()?)
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        contacts.push(ElectricalContactState::from_carrier_phase(phase));
    }
    let recovery_state_length = reader.usize()?;
    let recovery_fluid = decode_reached_recovery_fluid_state(
        reader.take(recovery_state_length)?,
        &anatomy.recovery_fluid,
    )?;
    if !reader.finished() {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let electrical = SparseElectricalState::from_contact_states(&anatomy.electrical, contacts)?;
    ReachedCohortState::from_mounted_parts(anatomy, neurons, electrical, recovery_fluid)
}

/// One digest-ordered table of distinct encoded bodies. Insertion keeps the
/// table sorted by content digest so the encoded form is canonical without a
/// separate normalization pass.
#[derive(Default)]
struct ContentDigestTable {
    entries: Vec<([u8; CONTENT_DIGEST_BYTES], Vec<u8>)>,
}

impl ContentDigestTable {
    fn intern(&mut self, body: Vec<u8>) -> [u8; CONTENT_DIGEST_BYTES] {
        let digest = sha256(&body);
        if let Err(position) = self
            .entries
            .binary_search_by(|(existing, _)| existing.cmp(&digest))
        {
            self.entries.insert(position, (digest, body));
        }
        digest
    }

    fn encode_into(&self, encoded: &mut Vec<u8>) -> Result<(), ReachedCohortError> {
        push_cohort_usize(encoded, self.entries.len())?;
        for (_, body) in &self.entries {
            push_cohort_usize(encoded, body.len())?;
            encoded.extend_from_slice(body);
        }
        Ok(())
    }
}

/// Decoded digest table: bodies keyed by digest, with per-entry use tracking so
/// a table entry no reference names is refused as noncanonical.
struct DecodedDigestTable<'a> {
    entries: Vec<([u8; CONTENT_DIGEST_BYTES], &'a [u8])>,
    used: Vec<bool>,
}

impl<'a> DecodedDigestTable<'a> {
    fn decode(reader: &mut CohortStateReader<'a>) -> Result<Self, ReachedCohortError> {
        let count = reader.usize()?;
        reader.require_records(count, 8)?;
        let mut entries: Vec<([u8; CONTENT_DIGEST_BYTES], &[u8])> = Vec::new();
        entries
            .try_reserve_exact(count)
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        for _ in 0..count {
            let length = reader.usize()?;
            let body = reader.take(length)?;
            let digest = sha256(body);
            if entries
                .last()
                .is_some_and(|(previous, _)| *previous >= digest)
            {
                return Err(ReachedCohortError::InvalidStateEncoding);
            }
            entries.push((digest, body));
        }
        let used = vec![false; entries.len()];
        Ok(Self { entries, used })
    }

    fn resolve(
        &mut self,
        digest: [u8; CONTENT_DIGEST_BYTES],
    ) -> Result<&'a [u8], ReachedCohortError> {
        let index = self
            .entries
            .binary_search_by(|(existing, _)| existing.cmp(&digest))
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        self.used[index] = true;
        Ok(self.entries[index].1)
    }

    fn fully_referenced(&self) -> Result<(), ReachedCohortError> {
        if self.used.iter().all(|used| *used) {
            Ok(())
        } else {
            Err(ReachedCohortError::InvalidStateEncoding)
        }
    }
}

fn take_content_digest(
    reader: &mut CohortStateReader<'_>,
) -> Result<[u8; CONTENT_DIGEST_BYTES], ReachedCohortError> {
    reader
        .take(CONTENT_DIGEST_BYTES)?
        .try_into()
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)
}

/// The canonical capacitance written into a `GLRCC05` shared-anatomy blob in
/// place of the member's own geometry-derived value: the authored base, one
/// unit patch of membrane.  It is a retention-layer placeholder only — every
/// member's real capacitance travels beside its reference and is restored
/// exactly — and it is what lets geometrically differentiated siblings still
/// intern one shared anatomy blob.
fn shared_anatomy_capacitance_placeholder() -> MembraneCapacitance {
    MembraneCapacitance::new(ExactRational::integer(1))
        .expect("one picofarad is a valid capacitance")
}

fn derived_recovery_fluid_anatomy_digest(
    anatomy: &ReachedCohortAnatomy,
) -> Result<[u8; CONTENT_DIGEST_BYTES], ReachedCohortError> {
    Ok(sha256(&encode_reached_recovery_fluid_anatomy(
        &anatomy.recovery_fluid,
    )?))
}

fn legacy_recovery_fluid_anatomy_digest(
    anatomy: &ReachedCohortAnatomy,
) -> Result<[u8; CONTENT_DIGEST_BYTES], ReachedCohortError> {
    Ok(sha256(&encode_legacy_reached_recovery_fluid_anatomy(
        &anatomy.recovery_fluid,
    )?))
}

/// Encode one restartable reached cohort with every distinct neuron-anatomy
/// and neuron-state body retained exactly once in a digest-ordered table and
/// per-neuron 32-byte content references. The derived recovery-fluid anatomy
/// is retained as the 32-byte digest of its canonical encoding; restore
/// re-derives it from the neuron anatomies and refuses on mismatch. This is a
/// retention-layer layout only: it transports already-admitted physics and
/// selects no anatomy or coefficients.
///
/// `GLRCC05` splits a member's anatomy the way the 2026-08-05 geometric
/// differentiation splits it physically.  The interned blob is the member's
/// SHARED anatomy — its whole encoding with the membrane capacitance written
/// as the canonical shared placeholder — and the member record carries its own
/// geometry-derived capacitance as an exact rational in 32 bytes.  Siblings
/// that differ only by their declared place therefore still intern ONE anatomy
/// blob, and a genuinely different anatomy still interns its own.  Restore
/// resolves the shared blob and puts each member's own capacitance back, so
/// the decoded anatomy is byte-for-byte the anatomy that was encoded.
pub(crate) fn encode_reached_cohort_cell_v5(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<Vec<u8>, ReachedCohortError> {
    encode_reached_cohort_cell_content_addressed(
        anatomy,
        state,
        ContentAddressedCohortFormat::V5WithoutContactPlasticity,
    )
}

pub(crate) fn encode_reached_cohort_cell_v5_with_contact_plasticity(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<Vec<u8>, ReachedCohortError> {
    encode_reached_cohort_cell_content_addressed(
        anatomy,
        state,
        ContentAddressedCohortFormat::V5WithContactPlasticity,
    )
}

pub(crate) fn encode_reached_cohort_cell_v6(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<Vec<u8>, ReachedCohortError> {
    encode_reached_cohort_cell_content_addressed(
        anatomy,
        state,
        ContentAddressedCohortFormat::V6Mounted,
    )
}

#[derive(Clone, Copy)]
enum ContentAddressedCohortFormat {
    V5WithoutContactPlasticity,
    V5WithContactPlasticity,
    V6Mounted,
}

fn encode_reached_cohort_cell_content_addressed(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
    format: ContentAddressedCohortFormat,
) -> Result<Vec<u8>, ReachedCohortError> {
    if anatomy.neurons.len() != anatomy.mounts.len()
        || anatomy.neurons.len() != state.neurons.len()
        || anatomy.electrical.contact_count() != state.electrical.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut anatomy_table = ContentDigestTable::default();
    let mut state_table = ContentDigestTable::default();
    let mut anatomy_references = Vec::with_capacity(anatomy.neurons.len());
    let mut state_references = Vec::with_capacity(anatomy.neurons.len());
    for (neuron_anatomy, neuron_state) in anatomy.neurons.iter().zip(state.neurons.iter()) {
        anatomy_references.push(anatomy_table.intern(encode_neuron_physical_anatomy(
            &neuron_anatomy.with_capacitance(shared_anatomy_capacitance_placeholder()),
        )?));
        state_references
            .push(state_table.intern(encode_neuron_physical_state(neuron_anatomy, neuron_state)?));
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(match format {
        ContentAddressedCohortFormat::V5WithoutContactPlasticity
        | ContentAddressedCohortFormat::V5WithContactPlasticity => {
            REACHED_COHORT_CELL_CODEC_V5_MAGIC
        }
        ContentAddressedCohortFormat::V6Mounted => REACHED_COHORT_CELL_CODEC_V6_MAGIC,
    });
    push_cohort_usize(&mut encoded, anatomy.neurons.len())?;
    anatomy_table.encode_into(&mut encoded)?;
    state_table.encode_into(&mut encoded)?;
    for (((lineage, mount), neuron_anatomy), (anatomy_reference, state_reference)) in anatomy
        .neuron_lineages
        .iter()
        .zip(anatomy.mounts.iter())
        .zip(anatomy.neurons.iter())
        .zip(anatomy_references.iter().zip(state_references.iter()))
    {
        encoded.extend_from_slice(lineage);
        match format {
            ContentAddressedCohortFormat::V5WithoutContactPlasticity
            | ContentAddressedCohortFormat::V5WithContactPlasticity => {
                let source = encode_neuron_source_site(
                    mount
                        .source_site()
                        .ok_or(ReachedCohortError::InvalidStateEncoding)?,
                )?;
                push_cohort_usize(&mut encoded, source.len())?;
                encoded.extend_from_slice(&source);
            }
            ContentAddressedCohortFormat::V6Mounted => match mount {
                ReachedNeuronMount::Receptor(source_site) => {
                    encoded.push(0);
                    let source = encode_neuron_source_site(source_site)?;
                    push_cohort_usize(&mut encoded, source.len())?;
                    encoded.extend_from_slice(&source);
                }
                ReachedNeuronMount::Intrinsic(place) => {
                    encoded.push(1);
                    encoded.extend_from_slice(&place.layer().to_le_bytes());
                    encoded.extend_from_slice(&place.topology_index().to_le_bytes());
                }
            },
        }
        encoded.extend_from_slice(anatomy_reference);
        encoded.extend_from_slice(state_reference);
        // This member's own geometry-derived membrane capacitance, beside its
        // reference to the anatomy it shares with its cohort-mates.
        let (numerator, denominator) = neuron_anatomy.capacitance().picofarads().parts();
        encoded.extend_from_slice(&numerator.to_le_bytes());
        encoded.extend_from_slice(&denominator.to_le_bytes());
    }
    encoded.extend_from_slice(&derived_recovery_fluid_anatomy_digest(anatomy)?);
    let recovery_state =
        encode_reached_recovery_fluid_state(&anatomy.recovery_fluid, state.recovery_fluid)?;
    push_cohort_usize(&mut encoded, recovery_state.len())?;
    encoded.extend_from_slice(&recovery_state);
    let electrical = if matches!(
        format,
        ContentAddressedCohortFormat::V5WithContactPlasticity
            | ContentAddressedCohortFormat::V6Mounted
    ) {
        encode_sparse_electrical_cell(&anatomy.electrical, &state.electrical)
    } else {
        encode_sparse_electrical_cell_v1(&anatomy.electrical, &state.electrical)
    }?;
    push_cohort_usize(&mut encoded, electrical.len())?;
    encoded.extend_from_slice(&electrical);
    Ok(encoded)
}

fn decode_reached_cohort_cell_v5(
    encoded: &[u8],
) -> Result<(ReachedCohortAnatomy, ReachedCohortState), ReachedCohortError> {
    decode_reached_cohort_cell_content_addressed(encoded, false)
}

fn decode_reached_cohort_cell_v6(
    encoded: &[u8],
) -> Result<(ReachedCohortAnatomy, ReachedCohortState), ReachedCohortError> {
    decode_reached_cohort_cell_content_addressed(encoded, true)
}

fn decode_reached_cohort_cell_content_addressed(
    encoded: &[u8],
    carries_mounted_sites: bool,
) -> Result<(ReachedCohortAnatomy, ReachedCohortState), ReachedCohortError> {
    let mut reader = CohortStateReader::new(encoded);
    let expected_magic = if carries_mounted_sites {
        REACHED_COHORT_CELL_CODEC_V6_MAGIC
    } else {
        REACHED_COHORT_CELL_CODEC_V5_MAGIC
    };
    if reader.take(expected_magic.len())? != expected_magic {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let neuron_count = reader.usize()?;
    if neuron_count == 0 {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut anatomy_table = DecodedDigestTable::decode(&mut reader)?;
    let mut state_table = DecodedDigestTable::decode(&mut reader)?;
    reader.require_records(neuron_count, 16 + 8 + 2 * CONTENT_DIGEST_BYTES + 32)?;
    let mut mounts = Vec::new();
    let mut neuron_lineages = Vec::new();
    let mut neuron_anatomies: Vec<NeuronPhysicalAnatomy> = Vec::new();
    let mut neuron_states = Vec::new();
    mounts
        .try_reserve_exact(neuron_count)
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
    neuron_lineages
        .try_reserve_exact(neuron_count)
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
    neuron_anatomies
        .try_reserve_exact(neuron_count)
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
    neuron_states
        .try_reserve_exact(neuron_count)
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
    let mut decoded_anatomies: Vec<([u8; CONTENT_DIGEST_BYTES], NeuronPhysicalAnatomy)> =
        Vec::new();
    for _ in 0..neuron_count {
        neuron_lineages.push(
            reader
                .take(16)?
                .try_into()
                .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
        );
        let mount = if carries_mounted_sites {
            match reader.u8()? {
                0 => {
                    let source_length = reader.usize()?;
                    ReachedNeuronMount::Receptor(decode_neuron_source_site(
                        reader.take(source_length)?,
                    )?)
                }
                1 => ReachedNeuronMount::Intrinsic(DeclaredNeuronPlace::new(
                    reader.u32()?,
                    reader.u32()?,
                )),
                _ => return Err(ReachedCohortError::InvalidStateEncoding),
            }
        } else {
            let source_length = reader.usize()?;
            ReachedNeuronMount::Receptor(decode_neuron_source_site(
                reader.take(source_length)?,
            )?)
        };
        mounts.push(mount);
        let anatomy_reference = take_content_digest(&mut reader)?;
        let state_reference = take_content_digest(&mut reader)?;
        let shared_anatomy = match decoded_anatomies
            .iter()
            .find(|(digest, _)| *digest == anatomy_reference)
        {
            Some((_, decoded)) => decoded.clone(),
            None => {
                let decoded =
                    decode_neuron_physical_anatomy(anatomy_table.resolve(anatomy_reference)?)?;
                decoded_anatomies.push((anatomy_reference, decoded.clone()));
                decoded
            }
        };
        // Put this member's own geometry-derived capacitance back onto the
        // anatomy it shares with its cohort-mates.
        let capacitance_numerator = reader.i128()?;
        let capacitance_denominator = reader.u128()?;
        let neuron_anatomy = shared_anatomy.with_capacitance(
            MembraneCapacitance::new(
                ExactRational::new(capacitance_numerator, capacitance_denominator)
                    .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
            )
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
        );
        let neuron_state =
            decode_neuron_physical_state(&neuron_anatomy, state_table.resolve(state_reference)?)?;
        neuron_anatomies.push(neuron_anatomy);
        neuron_states.push(neuron_state);
    }
    anatomy_table.fully_referenced()?;
    state_table.fully_referenced()?;
    let recovery_anatomy_digest = take_content_digest(&mut reader)?;
    let recovery_state_length = reader.usize()?;
    let encoded_recovery_state = reader.take(recovery_state_length)?;
    let electrical_length = reader.usize()?;
    let (electrical_anatomy, electrical_state) =
        decode_sparse_electrical_cell(reader.take(electrical_length)?)?;
    if !reader.finished() {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let anatomy = ReachedCohortAnatomy::new_mounted(
        neuron_anatomies,
        neuron_lineages,
        mounts,
        electrical_anatomy,
    )?;
    let current_digest = derived_recovery_fluid_anatomy_digest(&anatomy)?;
    let legacy_digest_matches = is_legacy_recovery_fluid_state(encoded_recovery_state)
        && legacy_recovery_fluid_anatomy_digest(&anatomy)? == recovery_anatomy_digest;
    if current_digest != recovery_anatomy_digest && !legacy_digest_matches {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let recovery_fluid =
        decode_reached_recovery_fluid_state(encoded_recovery_state, &anatomy.recovery_fluid)?;
    let state = ReachedCohortState::from_mounted_parts(
        &anatomy,
        neuron_states,
        electrical_state,
        recovery_fluid,
    )?;
    Ok((anatomy, state))
}

/// Encode one multi-neuron cohort state with every distinct neuron-state body
/// retained exactly once in a digest-ordered table and per-neuron 32-byte
/// content references.
pub(crate) fn encode_reached_cohort_state_v4(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<Vec<u8>, ReachedCohortError> {
    let contact_genesis = PlasticSupportState::definitive_virtual_genesis();
    if state.neurons.len() != anatomy.neurons.len()
        || state.electrical.contact_count() != anatomy.electrical.contact_count()
        || state
            .electrical
            .contact_states()
            .iter()
            .any(|contact| contact.plastic_state() != contact_genesis)
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut state_table = ContentDigestTable::default();
    let mut state_references = Vec::with_capacity(state.neurons.len());
    for (neuron_anatomy, neuron_state) in anatomy.neurons.iter().zip(state.neurons.iter()) {
        state_references
            .push(state_table.intern(encode_neuron_physical_state(neuron_anatomy, neuron_state)?));
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(REACHED_COHORT_CODEC_V4_MAGIC);
    push_cohort_usize(&mut encoded, state.neurons.len())?;
    push_cohort_usize(&mut encoded, state.electrical.contact_count())?;
    state_table.encode_into(&mut encoded)?;
    for (lineage, state_reference) in anatomy.neuron_lineages.iter().zip(state_references.iter()) {
        encoded.extend_from_slice(lineage);
        encoded.extend_from_slice(state_reference);
    }
    for contact in state.electrical.contact_states() {
        let (numerator, denominator) = contact.carrier_phase().parts();
        encoded.extend_from_slice(&numerator.to_le_bytes());
        encoded.extend_from_slice(&denominator.to_le_bytes());
    }
    let recovery_state =
        encode_reached_recovery_fluid_state(&anatomy.recovery_fluid, state.recovery_fluid)?;
    push_cohort_usize(&mut encoded, recovery_state.len())?;
    encoded.extend_from_slice(&recovery_state);
    Ok(encoded)
}

pub(crate) fn encode_reached_cohort_state_v5(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<Vec<u8>, ReachedCohortError> {
    if state.neurons.len() != anatomy.neurons.len()
        || state.electrical.contact_count() != anatomy.electrical.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut state_table = ContentDigestTable::default();
    let mut state_references = Vec::with_capacity(state.neurons.len());
    for (neuron_anatomy, neuron_state) in anatomy.neurons.iter().zip(state.neurons.iter()) {
        state_references
            .push(state_table.intern(encode_neuron_physical_state(neuron_anatomy, neuron_state)?));
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(REACHED_COHORT_CODEC_V5_MAGIC);
    push_cohort_usize(&mut encoded, state.neurons.len())?;
    push_cohort_usize(&mut encoded, state.electrical.contact_count())?;
    state_table.encode_into(&mut encoded)?;
    for (lineage, state_reference) in anatomy.neuron_lineages.iter().zip(state_references.iter()) {
        encoded.extend_from_slice(lineage);
        encoded.extend_from_slice(state_reference);
    }
    for contact in state.electrical.contact_states() {
        let (numerator, denominator) = contact.carrier_phase().parts();
        encoded.extend_from_slice(&numerator.to_le_bytes());
        encoded.extend_from_slice(&denominator.to_le_bytes());
        let (rest, dissipated, residue) = contact.plastic_state().physical_parts();
        let (rest_numerator, rest_denominator) = rest.parts();
        encoded.extend_from_slice(&rest_numerator.to_le_bytes());
        encoded.extend_from_slice(&rest_denominator.to_le_bytes());
        encoded.extend_from_slice(&dissipated.to_le_bytes());
        let (residue_numerator, residue_denominator) = residue.parts();
        encoded.extend_from_slice(&residue_numerator.to_le_bytes());
        encoded.extend_from_slice(&residue_denominator.to_le_bytes());
    }
    let recovery_state =
        encode_reached_recovery_fluid_state(&anatomy.recovery_fluid, state.recovery_fluid)?;
    push_cohort_usize(&mut encoded, recovery_state.len())?;
    encoded.extend_from_slice(&recovery_state);
    Ok(encoded)
}

fn decode_reached_cohort_state_v4(
    anatomy: &ReachedCohortAnatomy,
    encoded: &[u8],
) -> Result<ReachedCohortState, ReachedCohortError> {
    let mut reader = CohortStateReader::new(encoded);
    if reader.take(REACHED_COHORT_CODEC_V4_MAGIC.len())? != REACHED_COHORT_CODEC_V4_MAGIC {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let neuron_count = reader.usize()?;
    let contact_count = reader.usize()?;
    if neuron_count != anatomy.neurons.len() || contact_count != anatomy.electrical.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut state_table = DecodedDigestTable::decode(&mut reader)?;
    reader.require_records(neuron_count, 16 + CONTENT_DIGEST_BYTES)?;
    let mut neurons = Vec::with_capacity(neuron_count);
    for (index, neuron_anatomy) in anatomy.neurons.iter().enumerate() {
        let lineage: [u8; 16] = reader
            .take(16)?
            .try_into()
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        if lineage != anatomy.neuron_lineages[index] {
            return Err(ReachedCohortError::InvalidNeuronLineage);
        }
        let state_reference = take_content_digest(&mut reader)?;
        neurons.push(decode_neuron_physical_state(
            neuron_anatomy,
            state_table.resolve(state_reference)?,
        )?);
    }
    state_table.fully_referenced()?;
    let mut contacts = Vec::with_capacity(contact_count);
    for _ in 0..contact_count {
        let phase = ChargeCarrierPhase::new(reader.i128()?, reader.u128()?)
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        contacts.push(ElectricalContactState::from_carrier_phase(phase));
    }
    let recovery_state_length = reader.usize()?;
    let recovery_fluid = decode_reached_recovery_fluid_state(
        reader.take(recovery_state_length)?,
        &anatomy.recovery_fluid,
    )?;
    if !reader.finished() {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let electrical = SparseElectricalState::from_contact_states(&anatomy.electrical, contacts)?;
    ReachedCohortState::from_mounted_parts(anatomy, neurons, electrical, recovery_fluid)
}

fn decode_reached_cohort_state_v5(
    anatomy: &ReachedCohortAnatomy,
    encoded: &[u8],
) -> Result<ReachedCohortState, ReachedCohortError> {
    let mut reader = CohortStateReader::new(encoded);
    if reader.take(REACHED_COHORT_CODEC_V5_MAGIC.len())? != REACHED_COHORT_CODEC_V5_MAGIC {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let neuron_count = reader.usize()?;
    let contact_count = reader.usize()?;
    if neuron_count != anatomy.neurons.len() || contact_count != anatomy.electrical.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut state_table = DecodedDigestTable::decode(&mut reader)?;
    reader.require_records(neuron_count, 16 + CONTENT_DIGEST_BYTES)?;
    let mut neurons = Vec::with_capacity(neuron_count);
    for (index, neuron_anatomy) in anatomy.neurons.iter().enumerate() {
        let lineage: [u8; 16] = reader
            .take(16)?
            .try_into()
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        if lineage != anatomy.neuron_lineages[index] {
            return Err(ReachedCohortError::InvalidNeuronLineage);
        }
        let state_reference = take_content_digest(&mut reader)?;
        neurons.push(decode_neuron_physical_state(
            neuron_anatomy,
            state_table.resolve(state_reference)?,
        )?);
    }
    state_table.fully_referenced()?;
    let mut contacts = Vec::with_capacity(contact_count);
    for _ in 0..contact_count {
        let phase = ChargeCarrierPhase::new(reader.i128()?, reader.u128()?)
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        let plastic = PlasticSupportState::from_physical_parts(
            ExactRational::new(reader.i128()?, reader.u128()?)
                .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
            reader.u128()?,
            ExactRational::new(reader.i128()?, reader.u128()?)
                .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
        )
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        contacts.push(ElectricalContactState::from_physical_parts(phase, plastic));
    }
    let recovery_state_length = reader.usize()?;
    let recovery_fluid = decode_reached_recovery_fluid_state(
        reader.take(recovery_state_length)?,
        &anatomy.recovery_fluid,
    )?;
    if !reader.finished() {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let electrical = SparseElectricalState::from_contact_states(&anatomy.electrical, contacts)?;
    ReachedCohortState::from_mounted_parts(anatomy, neurons, electrical, recovery_fluid)
}

/// The 32-byte content digest of the canonical `GLRCS04` encoding of one
/// cohort state.
pub(crate) fn reached_cohort_state_content_digest(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<[u8; CONTENT_DIGEST_BYTES], ReachedCohortError> {
    Ok(sha256(&encode_reached_cohort_state_v5(anatomy, state)?))
}

pub(crate) fn reached_cohort_state_v4_content_digest(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> Result<[u8; CONTENT_DIGEST_BYTES], ReachedCohortError> {
    Ok(sha256(&encode_reached_cohort_state_v4(anatomy, state)?))
}

fn legacy_exhausted_recovery_content_digest(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
    carries_plastic: bool,
) -> Result<[u8; CONTENT_DIGEST_BYTES], ReachedCohortError> {
    let legacy_recovery = encode_legacy_exhausted_recovery_fluid_state(
        &anatomy.recovery_fluid,
        state.recovery_fluid,
    )?;
    cohort_state_content_digest_with_recovery(anatomy, state, carries_plastic, &legacy_recovery)
}

fn cohort_state_content_digest_with_recovery(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
    carries_plastic: bool,
    recovery_state: &[u8],
) -> Result<[u8; CONTENT_DIGEST_BYTES], ReachedCohortError> {
    let current_recovery =
        encode_reached_recovery_fluid_state(&anatomy.recovery_fluid, state.recovery_fluid)?;
    let mut encoded = if carries_plastic {
        encode_reached_cohort_state_v5(anatomy, state)?
    } else {
        encode_reached_cohort_state_v4(anatomy, state)?
    };
    let current_trailer = 8usize
        .checked_add(current_recovery.len())
        .ok_or(ReachedCohortError::InvalidStateEncoding)?;
    let prefix_length = encoded
        .len()
        .checked_sub(current_trailer)
        .ok_or(ReachedCohortError::InvalidStateEncoding)?;
    encoded.truncate(prefix_length);
    push_cohort_usize(&mut encoded, recovery_state.len())?;
    encoded.extend_from_slice(recovery_state);
    Ok(sha256(&encoded))
}

/// Encode `target` as per-neuron sparse physical-state deltas against `base`
/// using the existing settled delta machinery, with the target electrical and
/// recovery-fluid state carried exactly. The trailing content digest of the
/// canonical target encoding makes any divergent reconstruction refuse.
pub(crate) fn encode_reached_cohort_state_delta_v1(
    anatomy: &ReachedCohortAnatomy,
    base: &ReachedCohortState,
    target: &ReachedCohortState,
) -> Result<Vec<u8>, ReachedCohortError> {
    let contact_genesis = PlasticSupportState::definitive_virtual_genesis();
    if base.neurons.len() != anatomy.neurons.len()
        || target.neurons.len() != anatomy.neurons.len()
        || base.electrical.contact_count() != anatomy.electrical.contact_count()
        || target.electrical.contact_count() != anatomy.electrical.contact_count()
        || target
            .electrical
            .contact_states()
            .iter()
            .any(|contact| contact.plastic_state() != contact_genesis)
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(REACHED_COHORT_STATE_DELTA_MAGIC);
    push_cohort_usize(&mut encoded, anatomy.neurons.len())?;
    for (neuron_index, (base_neuron, target_neuron)) in
        base.neurons.iter().zip(target.neurons.iter()).enumerate()
    {
        match sparse_physical_state_delta(base_neuron, target_neuron).map_err(|error| {
            ReachedCohortError::Neuron {
                neuron_index,
                error,
            }
        })? {
            None => encoded.push(0),
            Some(delta) => {
                encoded.push(1);
                let body = encode_sparse_physical_state_delta(&delta)?;
                push_cohort_usize(&mut encoded, body.len())?;
                encoded.extend_from_slice(&body);
            }
        }
    }
    for contact in target.electrical.contact_states() {
        let (numerator, denominator) = contact.carrier_phase().parts();
        encoded.extend_from_slice(&numerator.to_le_bytes());
        encoded.extend_from_slice(&denominator.to_le_bytes());
    }
    let recovery_state =
        encode_reached_recovery_fluid_state(&anatomy.recovery_fluid, target.recovery_fluid)?;
    push_cohort_usize(&mut encoded, recovery_state.len())?;
    encoded.extend_from_slice(&recovery_state);
    encoded.extend_from_slice(&reached_cohort_state_v4_content_digest(anatomy, target)?);
    Ok(encoded)
}

pub(crate) fn encode_reached_cohort_state_delta(
    anatomy: &ReachedCohortAnatomy,
    base: &ReachedCohortState,
    target: &ReachedCohortState,
) -> Result<Vec<u8>, ReachedCohortError> {
    if base.neurons.len() != anatomy.neurons.len()
        || target.neurons.len() != anatomy.neurons.len()
        || base.electrical.contact_count() != anatomy.electrical.contact_count()
        || target.electrical.contact_count() != anatomy.electrical.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(REACHED_COHORT_STATE_DELTA_V2_MAGIC);
    push_cohort_usize(&mut encoded, anatomy.neurons.len())?;
    for (neuron_index, (base_neuron, target_neuron)) in
        base.neurons.iter().zip(target.neurons.iter()).enumerate()
    {
        match sparse_physical_state_delta(base_neuron, target_neuron).map_err(|error| {
            ReachedCohortError::Neuron {
                neuron_index,
                error,
            }
        })? {
            None => encoded.push(0),
            Some(delta) => {
                encoded.push(1);
                let body = encode_sparse_physical_state_delta(&delta)?;
                push_cohort_usize(&mut encoded, body.len())?;
                encoded.extend_from_slice(&body);
            }
        }
    }
    for contact in target.electrical.contact_states() {
        let (numerator, denominator) = contact.carrier_phase().parts();
        encoded.extend_from_slice(&numerator.to_le_bytes());
        encoded.extend_from_slice(&denominator.to_le_bytes());
        let (rest, dissipated, residue) = contact.plastic_state().physical_parts();
        let (rest_numerator, rest_denominator) = rest.parts();
        encoded.extend_from_slice(&rest_numerator.to_le_bytes());
        encoded.extend_from_slice(&rest_denominator.to_le_bytes());
        encoded.extend_from_slice(&dissipated.to_le_bytes());
        let (residue_numerator, residue_denominator) = residue.parts();
        encoded.extend_from_slice(&residue_numerator.to_le_bytes());
        encoded.extend_from_slice(&residue_denominator.to_le_bytes());
    }
    let recovery_state =
        encode_reached_recovery_fluid_state(&anatomy.recovery_fluid, target.recovery_fluid)?;
    push_cohort_usize(&mut encoded, recovery_state.len())?;
    encoded.extend_from_slice(&recovery_state);
    encoded.extend_from_slice(&reached_cohort_state_content_digest(anatomy, target)?);
    Ok(encoded)
}

pub(crate) fn decode_reached_cohort_state_delta(
    anatomy: &ReachedCohortAnatomy,
    base: &ReachedCohortState,
    encoded: &[u8],
) -> Result<ReachedCohortState, ReachedCohortError> {
    if base.neurons.len() != anatomy.neurons.len()
        || base.electrical.contact_count() != anatomy.electrical.contact_count()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut reader = CohortStateReader::new(encoded);
    let magic = reader.take(REACHED_COHORT_STATE_DELTA_MAGIC.len())?;
    let carries_plastic = magic == REACHED_COHORT_STATE_DELTA_V2_MAGIC;
    if !carries_plastic && magic != REACHED_COHORT_STATE_DELTA_MAGIC {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let neuron_count = reader.usize()?;
    if neuron_count != anatomy.neurons.len() {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let mut neurons = Vec::with_capacity(neuron_count);
    for (neuron_anatomy, base_neuron) in anatomy.neurons.iter().zip(base.neurons.iter()) {
        match reader.take(1)?[0] {
            0 => neurons.push(base_neuron.clone()),
            1 => {
                let body_length = reader.usize()?;
                let delta = decode_sparse_physical_state_delta(reader.take(body_length)?)?;
                neurons.push(apply_sparse_physical_state_delta(
                    neuron_anatomy,
                    base_neuron,
                    &delta,
                )?);
            }
            _ => return Err(ReachedCohortError::InvalidStateEncoding),
        }
    }
    let mut contacts = Vec::with_capacity(anatomy.electrical.contact_count());
    for _ in 0..anatomy.electrical.contact_count() {
        let phase = ChargeCarrierPhase::new(reader.i128()?, reader.u128()?)
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
        contacts.push(if carries_plastic {
            let plastic = PlasticSupportState::from_physical_parts(
                ExactRational::new(reader.i128()?, reader.u128()?)
                    .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
                reader.u128()?,
                ExactRational::new(reader.i128()?, reader.u128()?)
                    .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
            )
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?;
            ElectricalContactState::from_physical_parts(phase, plastic)
        } else {
            ElectricalContactState::from_carrier_phase(phase)
        });
    }
    let recovery_state_length = reader.usize()?;
    let encoded_recovery_state = reader.take(recovery_state_length)?;
    let legacy_recovery_state = is_legacy_recovery_fluid_state(encoded_recovery_state);
    let recovery_fluid_result =
        decode_reached_recovery_fluid_state(encoded_recovery_state, &anatomy.recovery_fluid);
    let untranslatable_legacy_recovery = legacy_recovery_state && recovery_fluid_result.is_err();
    let recovery_fluid = match recovery_fluid_result {
        Ok(state) => state,
        Err(_) if legacy_recovery_state => base.recovery_fluid,
        Err(error) => return Err(error.into()),
    };
    let expected_digest = take_content_digest(&mut reader)?;
    if !reader.finished() {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    let electrical = SparseElectricalState::from_contact_states(&anatomy.electrical, contacts)?;
    let target =
        ReachedCohortState::from_mounted_parts(anatomy, neurons, electrical, recovery_fluid)?;
    let actual_digest = if carries_plastic {
        reached_cohort_state_content_digest(anatomy, &target)?
    } else {
        reached_cohort_state_v4_content_digest(anatomy, &target)?
    };
    let legacy_digest_matches = legacy_recovery_state
        && cohort_state_content_digest_with_recovery(
            anatomy,
            &target,
            carries_plastic,
            encoded_recovery_state,
        )? == expected_digest;
    if actual_digest != expected_digest && !legacy_digest_matches {
        return Err(ReachedCohortError::InvalidStateEncoding);
    }
    if untranslatable_legacy_recovery {
        return Err(ReachedCohortError::UntranslatableLegacyRecoveryState);
    }
    Ok(target)
}

fn push_cohort_usize(encoded: &mut Vec<u8>, value: usize) -> Result<(), ReachedCohortError> {
    encoded.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| ReachedCohortError::InvalidStateEncoding)?
            .to_le_bytes(),
    );
    Ok(())
}

struct CohortStateReader<'a> {
    encoded: &'a [u8],
    cursor: usize,
}

impl<'a> CohortStateReader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self { encoded, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], ReachedCohortError> {
        let end = self
            .cursor
            .checked_add(count)
            .ok_or(ReachedCohortError::InvalidStateEncoding)?;
        let value = self
            .encoded
            .get(self.cursor..end)
            .ok_or(ReachedCohortError::InvalidStateEncoding)?;
        self.cursor = end;
        Ok(value)
    }

    fn require_records(
        &self,
        count: usize,
        minimum_record_bytes: usize,
    ) -> Result<(), ReachedCohortError> {
        let minimum = count
            .checked_mul(minimum_record_bytes)
            .ok_or(ReachedCohortError::InvalidStateEncoding)?;
        let remaining = self
            .encoded
            .len()
            .checked_sub(self.cursor)
            .ok_or(ReachedCohortError::InvalidStateEncoding)?;
        if minimum > remaining {
            return Err(ReachedCohortError::InvalidStateEncoding);
        }
        Ok(())
    }

    fn usize(&mut self) -> Result<usize, ReachedCohortError> {
        usize::try_from(u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
        ))
        .map_err(|_| ReachedCohortError::InvalidStateEncoding)
    }

    fn u8(&mut self) -> Result<u8, ReachedCohortError> {
        self.take(1)?
            .first()
            .copied()
            .ok_or(ReachedCohortError::InvalidStateEncoding)
    }

    fn u32(&mut self) -> Result<u32, ReachedCohortError> {
        Ok(u32::from_le_bytes(
            self.take(4)?
                .try_into()
                .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
        ))
    }

    fn i128(&mut self) -> Result<i128, ReachedCohortError> {
        Ok(i128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
        ))
    }

    fn u128(&mut self) -> Result<u128, ReachedCohortError> {
        Ok(u128::from_le_bytes(
            self.take(16)?
                .try_into()
                .map_err(|_| ReachedCohortError::InvalidStateEncoding)?,
        ))
    }

    fn finished(&self) -> bool {
        self.cursor == self.encoded.len()
    }
}

#[derive(Clone, Debug)]
pub(crate) struct ReachedCohortIntervalInput<'a> {
    neurons: Box<[NeuronIntervalInput<'a>]>,
    source_sites: Box<[NeuronSourceSite]>,
    resident_indices: Option<Box<[usize]>>,
    external_contact_outward_elementary_charges: Box<[i128]>,
    precomputed_local_electrical: Option<SparseElectricalTransferSettlement>,
}

impl<'a> ReachedCohortIntervalInput<'a> {
    pub(crate) fn from_episode(
        episode: &NativeJointSourceEpisode,
        neurons: Vec<NeuronIntervalInput<'a>>,
    ) -> Result<Self, ReachedCohortError> {
        let source_sites = neurons
            .iter()
            .map(|input| {
                bind_neuron_source_anchor(episode, input.perspective)
                    .map(NeuronSourceSite::from_anchor)
            })
            .collect::<Result<Vec<_>, _>>()?;
        Self::with_source_sites(neurons, source_sites)
    }

    #[cfg(test)]
    pub(crate) fn fixture(
        neurons: Vec<NeuronIntervalInput<'a>>,
        source_sites: Vec<NeuronSourceSite>,
    ) -> Result<Self, ReachedCohortError> {
        Self::with_source_sites(neurons, source_sites)
    }

    pub(crate) fn from_resident_indices(
        neurons: Vec<NeuronIntervalInput<'a>>,
        resident_indices: Vec<usize>,
        external_contact_outward_elementary_charges: Vec<i128>,
    ) -> Result<Self, ReachedCohortError> {
        let interval_microseconds = neurons
            .first()
            .ok_or(ReachedCohortError::AnatomyStateWidth)?
            .interval_microseconds;
        if neurons.len() != resident_indices.len()
            || neurons.len() != external_contact_outward_elementary_charges.len()
            || neurons
                .iter()
                .any(|input| input.interval_microseconds != interval_microseconds)
            || resident_indices
                .iter()
                .enumerate()
                .any(|(index, resident)| resident_indices[..index].contains(resident))
        {
            return Err(ReachedCohortError::IntervalDurationMismatch);
        }
        Ok(Self {
            neurons: neurons.into_boxed_slice(),
            source_sites: Box::new([]),
            resident_indices: Some(resident_indices.into_boxed_slice()),
            external_contact_outward_elementary_charges:
                external_contact_outward_elementary_charges.into_boxed_slice(),
            precomputed_local_electrical: None,
        })
    }

    pub(crate) fn from_resident_indices_with_precomputed_contacts(
        neurons: Vec<NeuronIntervalInput<'a>>,
        resident_indices: Vec<usize>,
        combined_contact_outward_elementary_charges: Vec<i128>,
        precomputed_local_electrical: SparseElectricalTransferSettlement,
    ) -> Result<Self, ReachedCohortError> {
        let mut input = Self::from_resident_indices(
            neurons,
            resident_indices,
            combined_contact_outward_elementary_charges,
        )?;
        input.precomputed_local_electrical = Some(precomputed_local_electrical);
        Ok(input)
    }

    fn with_source_sites(
        neurons: Vec<NeuronIntervalInput<'a>>,
        source_sites: Vec<NeuronSourceSite>,
    ) -> Result<Self, ReachedCohortError> {
        let interval_microseconds = neurons
            .first()
            .ok_or(ReachedCohortError::AnatomyStateWidth)?
            .interval_microseconds;
        if neurons.len() != source_sites.len()
            || neurons
                .iter()
                .any(|input| input.interval_microseconds != interval_microseconds)
        {
            return Err(ReachedCohortError::IntervalDurationMismatch);
        }
        Ok(Self {
            external_contact_outward_elementary_charges: vec![0; neurons.len()].into_boxed_slice(),
            neurons: neurons.into_boxed_slice(),
            source_sites: source_sites.into_boxed_slice(),
            resident_indices: None,
            precomputed_local_electrical: None,
        })
    }

    pub(crate) fn interval_microseconds(&self) -> u32 {
        self.neurons[0].interval_microseconds
    }

    fn resident_indices(
        &self,
        anatomy: &ReachedCohortAnatomy,
    ) -> Result<Vec<usize>, ReachedCohortError> {
        if let Some(indices) = &self.resident_indices {
            if indices.iter().any(|index| *index >= anatomy.neuron_count()) {
                return Err(ReachedCohortError::SourceAnatomyMismatch);
            }
            return Ok(indices.to_vec());
        }
        let mut indices = Vec::with_capacity(self.source_sites.len());
        for site in &self.source_sites {
            let resident = anatomy
                .source_site_member(site)
                .ok_or(ReachedCohortError::SourceAnatomyMismatch)?;
            if indices.contains(&resident) {
                return Err(ReachedCohortError::SourceAnatomyMismatch);
            }
            indices.push(resident);
        }
        Ok(indices)
    }

    fn resident_gate_work_perturbations(
        &self,
        anatomy: &ReachedCohortAnatomy,
    ) -> Result<Vec<(usize, bool)>, ReachedCohortError> {
        Ok(self
            .resident_indices(anatomy)?
            .into_iter()
            .zip(self.neurons.iter().map(|input| !input.gate_work.is_zero()))
            .collect())
    }

    pub(crate) fn resident_gate_work_bits(
        &self,
        anatomy: &ReachedCohortAnatomy,
    ) -> Result<Vec<bool>, ReachedCohortError> {
        let mut bits = vec![false; anatomy.neuron_count()];
        for (resident_index, perturbed) in self.resident_gate_work_perturbations(anatomy)? {
            bits[resident_index] |= perturbed;
        }
        Ok(bits)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ReachedCohortIntervalSettlement {
    pub(crate) successor: ReachedCohortState,
    pub(crate) contact_transitions: Box<[ElectricalContactTransition]>,
    pub(crate) contact_outward_elementary_charges_by_neuron: Box<[i128]>,
    pub(crate) locally_quiescent: Box<[bool]>,
    pub(crate) electrically_active: bool,
    pub(crate) quiescent: bool,
}

/// The settled reference state the physics measures experience deltas
/// against.  Historically this wrapper claimed GLOBAL quiescence; measured
/// F2 (2026-08-05) proved that after real electricity a driven cohort never
/// returns to global quiescence, so the truthful meaning is REST: the state
/// the cohort holds at a stimulus-boundary settlement (an interval that
/// carried zero exogenous stimulus energy).  A proven-quiescent state (the
/// `settle_reached_cohort_to_quiescence` constructors) is one lawful rest
/// state; it is no longer the only one.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct RestReachedCohortState {
    state: ReachedCohortState,
}

impl RestReachedCohortState {
    pub(crate) fn state(&self) -> &ReachedCohortState {
        &self.state
    }

    pub(crate) fn from_state(state: ReachedCohortState) -> Self {
        Self { state }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ReachedCohortPostExperienceSettlement {
    pub(crate) rest: RestReachedCohortState,
    pub(crate) neuron_fractals: Box<[Option<SparsePhysicalStateDelta>]>,
    pub(crate) receptor_excitation_zeptojoules: Box<[Option<ExactRational>]>,
    pub(crate) electrical_contact_was_active: bool,
    pub(crate) gate_work_perturbed_neurons: Box<[bool]>,
    pub(crate) active_electrical_contacts: Box<[bool]>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ReachedCohortRecurrenceSettlement {
    pub(crate) successor: ReachedCohortState,
    pub(crate) neuron_physical_deltas: Box<[Option<SparsePhysicalStateDelta>]>,
    pub(crate) receptor_excitation_zeptojoules: Box<[Option<ExactRational>]>,
    pub(crate) gate_work_perturbed_neurons: Box<[bool]>,
    pub(crate) active_electrical_contacts: Box<[bool]>,
}

/// What the metabolic loops did to one cohort in one settlement — reported
/// exactly, including the demand the body could NOT meet.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ReachedCohortMetabolicObservation {
    pub(crate) recovered_neuron_count: usize,
    pub(crate) drained_dissipation_quanta: u128,
    pub(crate) unmet_dissipation_quanta: u128,
    pub(crate) returned_elementary_charges: i128,
    pub(crate) unreturned_elementary_charges: i128,
    pub(crate) fuel_quanta: u128,
    pub(crate) pumped_elementary_charges: i128,
    pub(crate) pump_work_zeptojoules: ExactRational,
    pub(crate) environment_energy_delivered_zeptojoules: ExactRational,
    pub(crate) environment_heat_exported_zeptojoules: ExactRational,
}

impl Default for ReachedCohortMetabolicObservation {
    fn default() -> Self {
        Self {
            recovered_neuron_count: 0,
            drained_dissipation_quanta: 0,
            unmet_dissipation_quanta: 0,
            returned_elementary_charges: 0,
            unreturned_elementary_charges: 0,
            fuel_quanta: 0,
            pumped_elementary_charges: 0,
            pump_work_zeptojoules: ExactRational::integer(0),
            environment_energy_delivered_zeptojoules: ExactRational::integer(0),
            environment_heat_exported_zeptojoules: ExactRational::integer(0),
        }
    }
}

impl ReachedCohortMetabolicObservation {
    pub(crate) fn changed(&self) -> bool {
        self.recovered_neuron_count != 0
    }
}

/// Settle one genuinely dark interval's metabolism for a whole cohort: every
/// recovery lane of every neuron through its mounted contact.  Darkness does
/// not create a membrane conductance, a resting-voltage target, or carrier
/// transport; those require an actually reached passive path or an authored
/// active pump.
///
/// Conservation, checked here: total carrier material across the cohort is
/// unchanged, and every settled reaction is the exact one its own
/// stoichiometry defines.
pub(crate) fn settle_reached_cohort_dark_rest(
    anatomy: &ReachedCohortAnatomy,
    predecessor: &ReachedCohortState,
    interval_microseconds: u32,
) -> Result<(ReachedCohortState, ReachedCohortMetabolicObservation), ReachedCohortError> {
    if predecessor.neurons.len() != anatomy.neurons.len()
        || anatomy.recovery_fluid.neuron_count() != anatomy.neurons.len()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let predecessor_material = total_carrier_material(&predecessor.neurons)?;
    let mut neurons = predecessor.neurons.to_vec();
    let mut observation = ReachedCohortMetabolicObservation::default();
    let mut contact_rate = ExactRational::integer(0);
    for (neuron_index, neuron) in anatomy.neurons.iter().enumerate() {
        let local_rate = neuron
            .pump_contact_power_zeptojoules_per_microsecond()
            .map_err(|error| ReachedCohortError::Neuron {
                neuron_index,
                error,
            })?;
        contact_rate = contact_rate
            .checked_add(local_rate)
            .map_err(|_| ReachedCohortError::MaterialConservation)?;
    }
    let maximum_interval_energy = contact_rate
        .checked_mul_unsigned(u128::from(interval_microseconds))
        .map_err(|_| ReachedCohortError::MaterialConservation)?;
    let environment = settle_powered_environment_exchange(
        anatomy.recovery_fluid.reservoir_anatomy(),
        predecessor.recovery_fluid,
        maximum_interval_energy,
    )?;
    let mut reservoir = environment.successor;
    observation.environment_energy_delivered_zeptojoules = environment.delivered_energy_zeptojoules;
    observation.environment_heat_exported_zeptojoules = environment.exported_heat_zeptojoules;
    for (neuron_index, neuron_anatomy) in anatomy.neurons.iter().enumerate() {
        let settled = settle_dark_rest_neuron(
            &anatomy.recovery_fluid,
            neuron_index,
            neuron_anatomy,
            &neurons[neuron_index],
            reservoir,
            interval_microseconds,
        )?;
        observation.drained_dissipation_quanta = observation
            .drained_dissipation_quanta
            .checked_add(settled.drained_dissipation_quanta())
            .ok_or(ReachedCohortError::MaterialConservation)?;
        observation.unmet_dissipation_quanta = observation
            .unmet_dissipation_quanta
            .checked_add(settled.unmet_dissipation_quanta())
            .ok_or(ReachedCohortError::MaterialConservation)?;
        observation.returned_elementary_charges = observation
            .returned_elementary_charges
            .checked_add(settled.returned_elementary_charges)
            .ok_or(ReachedCohortError::MaterialConservation)?;
        observation.unreturned_elementary_charges = observation
            .unreturned_elementary_charges
            .checked_add(settled.unreturned_elementary_charges)
            .ok_or(ReachedCohortError::MaterialConservation)?;
        observation.fuel_quanta = observation
            .fuel_quanta
            .checked_add(settled.fuel_quanta())
            .ok_or(ReachedCohortError::MaterialConservation)?;
        observation.pumped_elementary_charges = observation
            .pumped_elementary_charges
            .checked_add(settled.pumped_elementary_charges)
            .ok_or(ReachedCohortError::MaterialConservation)?;
        observation.pump_work_zeptojoules = observation
            .pump_work_zeptojoules
            .checked_add(settled.pump_work_zeptojoules)
            .map_err(|_| ReachedCohortError::MaterialConservation)?;
        if settled.changed() {
            observation.recovered_neuron_count = observation
                .recovered_neuron_count
                .checked_add(1)
                .ok_or(ReachedCohortError::MaterialConservation)?;
        }
        reservoir = settled.successor_reservoir;
        neurons[neuron_index] = settled.successor_neuron;
    }
    if total_carrier_material(&neurons)? != predecessor_material {
        return Err(ReachedCohortError::MaterialConservation);
    }
    Ok((
        ReachedCohortState {
            neurons: neurons.into_boxed_slice(),
            electrical: predecessor.electrical.clone(),
            recovery_fluid: reservoir,
        },
        observation,
    ))
}

/// The cohort reservoir's exact energy state, for the observation surface.
pub(crate) fn reached_cohort_energy_state(
    anatomy: &ReachedCohortAnatomy,
    state: &ReachedCohortState,
) -> ReachedCohortEnergyState {
    let (fuel_capacity, spent_capacity, heat_capacity) =
        anatomy.recovery_fluid.reservoir_anatomy().capacities();
    let (fuel, spent, heat) = state.recovery_fluid.physical_parts();
    let mut dissipated = ExactRational::integer(0);
    let mut dissipation_capacity = ExactRational::integer(0);
    let mut separated = 0_i128;
    for (neuron_anatomy, neuron) in anatomy.neurons.iter().zip(state.neurons.iter()) {
        for address in (0..neuron_anatomy.psi_ring_count())
            .map(RecoveryLaneAddress::Psi)
            .chain([RecoveryLaneAddress::Gate, RecoveryLaneAddress::Plastic])
        {
            let quantum = neuron_anatomy
                .lane_dissipation_quantum_zeptojoules(address)
                .expect("validated reached-neuron dissipation anatomy");
            dissipated = dissipated
                .checked_add(
                    quantum
                        .checked_mul_unsigned(
                            neuron.lane_dissipated_quanta(address).unwrap_or_default(),
                        )
                        .expect("bounded reached-neuron dissipation energy"),
                )
                .expect("bounded cohort dissipation energy");
            dissipation_capacity = dissipation_capacity
                .checked_add(
                    quantum
                        .checked_mul_unsigned(
                            neuron_anatomy
                                .lane_dissipation_capacity_quanta(address)
                                .unwrap_or_default(),
                        )
                        .expect("bounded reached-neuron dissipation capacity"),
                )
                .expect("bounded cohort dissipation capacity");
        }
        separated = separated.saturating_add(neuron.separated_elementary_charges());
    }
    ReachedCohortEnergyState {
        available_energy_zeptojoules: wide_energy(fuel),
        spent_energy_zeptojoules: wide_energy(spent),
        thermal_energy_zeptojoules: wide_energy(heat),
        available_energy_capacity_zeptojoules: wide_energy(fuel_capacity),
        spent_energy_capacity_zeptojoules: wide_energy(spent_capacity),
        thermal_energy_capacity_zeptojoules: wide_energy(heat_capacity),
        dissipated_energy_zeptojoules: wide_energy(dissipated),
        dissipation_capacity_energy_zeptojoules: wide_energy(dissipation_capacity),
        separated_elementary_charges: separated,
    }
}

fn wide_energy(value: ExactRational) -> BigRational {
    let (numerator, denominator) = value.parts();
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ReachedCohortEnergyState {
    pub(crate) available_energy_zeptojoules: BigRational,
    pub(crate) spent_energy_zeptojoules: BigRational,
    pub(crate) thermal_energy_zeptojoules: BigRational,
    pub(crate) available_energy_capacity_zeptojoules: BigRational,
    pub(crate) spent_energy_capacity_zeptojoules: BigRational,
    pub(crate) thermal_energy_capacity_zeptojoules: BigRational,
    pub(crate) dissipated_energy_zeptojoules: BigRational,
    pub(crate) dissipation_capacity_energy_zeptojoules: BigRational,
    pub(crate) separated_elementary_charges: i128,
}

impl Default for ReachedCohortEnergyState {
    fn default() -> Self {
        Self {
            available_energy_zeptojoules: BigRational::zero(),
            spent_energy_zeptojoules: BigRational::zero(),
            thermal_energy_zeptojoules: BigRational::zero(),
            available_energy_capacity_zeptojoules: BigRational::zero(),
            spent_energy_capacity_zeptojoules: BigRational::zero(),
            thermal_energy_capacity_zeptojoules: BigRational::zero(),
            dissipated_energy_zeptojoules: BigRational::zero(),
            dissipation_capacity_energy_zeptojoules: BigRational::zero(),
            separated_elementary_charges: 0,
        }
    }
}

pub(crate) fn settle_reached_cohort_interval(
    anatomy: &ReachedCohortAnatomy,
    predecessor: &ReachedCohortState,
    mut input: ReachedCohortIntervalInput<'_>,
) -> Result<ReachedCohortIntervalSettlement, ReachedCohortError> {
    if predecessor.neurons.len() != anatomy.neurons.len()
        || predecessor.electrical.contact_count() != anatomy.electrical.contact_count()
        || input.neurons.is_empty()
        || input.neurons.len() > anatomy.neurons.len()
    {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let resident_indices = input.resident_indices(anatomy)?;
    let external_contact_outward = input.external_contact_outward_elementary_charges.clone();
    let mut reached_neurons = vec![false; anatomy.neurons.len()];
    for resident in resident_indices.iter().copied() {
        reached_neurons[resident] = true;
    }
    if anatomy.recovery_fluid.neuron_count() != anatomy.neurons.len() {
        return Err(ReachedCohortError::AnatomyStateWidth);
    }
    let shared = input.neurons[0].perspective.shared();
    if input.neurons.iter().enumerate().any(|(index, local)| {
        !std::ptr::eq(local.perspective.shared(), shared)
            || local.perspective.coordinate_index() >= shared.vertex_count()
            || input.neurons[..index].iter().any(|prior| {
                prior.perspective.coordinate_index() == local.perspective.coordinate_index()
            })
    }) {
        return Err(ReachedCohortError::PerspectiveMismatch);
    }

    let mut recovered_neurons = predecessor.neurons.to_vec();
    let mut recovered_reservoir = predecessor.recovery_fluid;
    let mut recovery_active = false;
    for (input_index, neuron_input) in input.neurons.iter_mut().enumerate() {
        let resident_index = resident_indices[input_index];
        let neuron_anatomy = &anatomy.neurons[resident_index];
        let neuron_predecessor = &predecessor.neurons[resident_index];
        let prepared_psi = match neuron_input.prepared_psi.take() {
            Some(prepared) => prepared,
            None => neuron_anatomy
                .prepare_psi_settlement(neuron_predecessor, neuron_input.perspective)
                .map_err(|error| ReachedCohortError::Neuron {
                    neuron_index: resident_index,
                    error,
                })?,
        };
        let recovered = settle_resident_gate_recovery_before_interval(
            &anatomy.recovery_fluid,
            resident_index,
            neuron_anatomy,
            neuron_predecessor,
            &neuron_input.gate_work,
            &prepared_psi,
            recovered_reservoir,
        )?;
        neuron_input.prepared_psi = Some(prepared_psi);
        recovery_active |= recovered.settled_extent != 0;
        recovered_reservoir = recovered.successor_reservoir;
        recovered_neurons[resident_index] = recovered.successor_neuron;
    }

    let capacitances = anatomy
        .neurons
        .iter()
        .map(NeuronPhysicalAnatomy::capacitance)
        .collect::<Vec<_>>();
    let predecessor_membranes = recovered_neurons
        .iter()
        .map(NeuronPhysicalState::membrane_state)
        .collect::<Vec<_>>();
    // What each neuron actually HAS to give this interval.  The contact law
    // was already right about the field but had no reserve term, so it moved
    // carriers out of neurons that had none — which is how neuron 8 emptied
    // and froze her whole body (2026-08-08).
    let available_carriers = recovered_neurons
        .iter()
        .map(|neuron| neuron.carrier_reservoirs().intracellular())
        .collect::<Vec<_>>();
    let precomputed_contact_input = input.precomputed_local_electrical.is_some();
    let electrical = match input.precomputed_local_electrical.take() {
        Some(precomputed)
            if precomputed.successor_contacts.contact_count() == anatomy.contact_count()
                && precomputed.transitions.len() == anatomy.contact_count()
                && precomputed.outward_elementary_charges_by_neuron.len()
                    == anatomy.neuron_count() =>
        {
            precomputed
        }
        Some(_) => return Err(ReachedCohortError::AnatomyStateWidth),
        None => settle_sparse_electrical_transfers_reached(
            &anatomy.electrical,
            &predecessor.electrical,
            &capacitances,
            &predecessor_membranes,
            &reached_neurons,
            &available_carriers,
            input.interval_microseconds(),
        )?,
    };

    let predecessor_material = total_carrier_material(&predecessor.neurons)?;
    let mut successor_neurons = recovered_neurons.clone();
    let mut locally_quiescent = vec![true; anatomy.neurons.len()];
    for (input_index, neuron_input) in input.neurons.into_vec().into_iter().enumerate() {
        let resident_index = resident_indices[input_index];
        let combined_contact_outward = if !precomputed_contact_input {
            electrical.outward_elementary_charges_by_neuron[resident_index]
                .checked_add(external_contact_outward[input_index])
                .ok_or(ReachedCohortError::MaterialConservation)?
        } else {
            // The injected whole-fabric charge already includes this cohort's
            // local contacts and every resident cross-cohort contact exactly
            // once.  Adding the local term again would duplicate material.
            external_contact_outward[input_index]
        };
        let settled = settle_extended_interval_with_contact(
            &anatomy.neurons[resident_index],
            &recovered_neurons[resident_index],
            neuron_input,
            combined_contact_outward,
        )
        .map_err(|error| ReachedCohortError::Neuron {
            neuron_index: resident_index,
            error,
        })?;
        successor_neurons[resident_index] = settled.successor;
        locally_quiescent[resident_index] = settled.quiescent;
    }
    let external_net_outward = external_contact_outward.iter().try_fold(0_i128, |total, value| {
        total
            .checked_add(*value)
            .ok_or(ReachedCohortError::MaterialConservation)
    })?;
    let expected_successor_material = if external_net_outward >= 0 {
        predecessor_material
            .checked_sub(external_net_outward.unsigned_abs())
            .ok_or(ReachedCohortError::MaterialConservation)?
    } else {
        predecessor_material
            .checked_add(external_net_outward.unsigned_abs())
            .ok_or(ReachedCohortError::MaterialConservation)?
    };
    if total_carrier_material(&successor_neurons)? != expected_successor_material {
        return Err(ReachedCohortError::MaterialConservation);
    }

    let electrically_active = electrical.successor_contacts != predecessor.electrical
        || electrical.transitions.iter().any(|transition| {
            transition.outward_current_from_left_picoamperes.parts().0 != 0
                || transition.outward_elementary_charges_from_left != 0
        });
    let quiescent =
        !recovery_active && !electrically_active && locally_quiescent.iter().all(|value| *value);
    Ok(ReachedCohortIntervalSettlement {
        successor: ReachedCohortState {
            neurons: successor_neurons.into_boxed_slice(),
            electrical: electrical.successor_contacts,
            recovery_fluid: recovered_reservoir,
        },
        contact_transitions: electrical.transitions,
        contact_outward_elementary_charges_by_neuron: electrical
            .outward_elementary_charges_by_neuron,
        locally_quiescent: locally_quiescent.into_boxed_slice(),
        electrically_active,
        quiescent,
    })
}

/// Settle only along the supplied exact reached-cohort interval sequence. The
/// sequence is causal input, not a timeout or iteration cap.
pub(crate) fn settle_reached_cohort_to_quiescence(
    anatomy: &ReachedCohortAnatomy,
    predecessor: &ReachedCohortState,
    intervals: &[ReachedCohortIntervalInput<'_>],
) -> Result<RestReachedCohortState, ReachedCohortError> {
    let mut state = predecessor.clone();
    for input in intervals {
        let settled = settle_reached_cohort_interval(anatomy, &state, input.clone())?;
        state = settled.successor;
        if settled.quiescent {
            return Ok(RestReachedCohortState { state });
        }
    }
    Err(ReachedCohortError::SequenceEndedBeforeQuiescence)
}

pub(crate) fn settle_reached_cohort_experience_to_quiescence(
    anatomy: &ReachedCohortAnatomy,
    predecessor: &RestReachedCohortState,
    intervals: &[ReachedCohortIntervalInput<'_>],
) -> Result<ReachedCohortPostExperienceSettlement, ReachedCohortError> {
    let mut state = predecessor.state.clone();
    let mut electrical_contact_was_active = false;
    let mut gate_work_perturbed_neurons = vec![false; anatomy.neurons.len()];
    let mut active_electrical_contacts = vec![false; anatomy.electrical.contact_count()];
    let mut quiescent = None;
    for input in intervals {
        for (resident_index, perturbed) in input.resident_gate_work_perturbations(anatomy)? {
            gate_work_perturbed_neurons[resident_index] |= perturbed;
        }
        let settled = settle_reached_cohort_interval(anatomy, &state, input.clone())?;
        electrical_contact_was_active |= settled.electrically_active;
        for (active, transition) in active_electrical_contacts
            .iter_mut()
            .zip(settled.contact_transitions.iter())
        {
            *active |= transition.outward_current_from_left_picoamperes.parts().0 != 0
                || transition.outward_elementary_charges_from_left != 0;
        }
        state = settled.successor;
        if settled.quiescent {
            quiescent = Some(RestReachedCohortState { state });
            break;
        }
    }
    let rest = quiescent.ok_or(ReachedCohortError::SequenceEndedBeforeQuiescence)?;
    let mut fractals = Vec::with_capacity(anatomy.neurons.len());
    for (prior, successor) in predecessor
        .state
        .neurons
        .iter()
        .zip(rest.state.neurons.iter())
    {
        fractals.push(
            sparse_retained_physical_state_delta(prior, successor).map_err(|error| {
                ReachedCohortError::Neuron {
                    neuron_index: fractals.len(),
                    error,
                }
            })?,
        );
    }
    Ok(ReachedCohortPostExperienceSettlement {
        rest,
        neuron_fractals: fractals.into_boxed_slice(),
        receptor_excitation_zeptojoules: vec![None; anatomy.neurons.len()].into_boxed_slice(),
        electrical_contact_was_active,
        gate_work_perturbed_neurons: gate_work_perturbed_neurons.into_boxed_slice(),
        active_electrical_contacts: active_electrical_contacts.into_boxed_slice(),
    })
}

/// Execute one exact later recurrence sequence without redefining active recall
/// as a new post-quiescence memory. The sequence length is supplied by the
/// causal occurrence; this function adds no timeout, threshold, or iteration
/// cap and retains no interval history.
pub(crate) fn settle_reached_cohort_recurrence(
    anatomy: &ReachedCohortAnatomy,
    predecessor: &ReachedCohortState,
    intervals: &[ReachedCohortIntervalInput<'_>],
) -> Result<ReachedCohortRecurrenceSettlement, ReachedCohortError> {
    if intervals.is_empty() {
        return Err(ReachedCohortError::SequenceEndedBeforeQuiescence);
    }
    let mut state = predecessor.clone();
    let mut gate_work_perturbed_neurons = vec![false; anatomy.neurons.len()];
    let mut active_electrical_contacts = vec![false; anatomy.electrical.contact_count()];
    for input in intervals {
        for (resident_index, perturbed) in input.resident_gate_work_perturbations(anatomy)? {
            gate_work_perturbed_neurons[resident_index] |= perturbed;
        }
        let settled = settle_reached_cohort_interval(anatomy, &state, input.clone())?;
        for (active, transition) in active_electrical_contacts
            .iter_mut()
            .zip(settled.contact_transitions.iter())
        {
            *active |= transition.outward_current_from_left_picoamperes.parts().0 != 0
                || transition.outward_elementary_charges_from_left != 0;
        }
        state = settled.successor;
    }
    let mut physical_deltas = Vec::with_capacity(anatomy.neurons.len());
    for (prior, successor) in predecessor.neurons.iter().zip(state.neurons.iter()) {
        physical_deltas.push(
            sparse_physical_state_delta(prior, successor).map_err(|error| {
                ReachedCohortError::Neuron {
                    neuron_index: physical_deltas.len(),
                    error,
                }
            })?,
        );
    }
    Ok(ReachedCohortRecurrenceSettlement {
        successor: state,
        neuron_physical_deltas: physical_deltas.into_boxed_slice(),
        receptor_excitation_zeptojoules: vec![None; anatomy.neurons.len()].into_boxed_slice(),
        gate_work_perturbed_neurons: gate_work_perturbed_neurons.into_boxed_slice(),
        active_electrical_contacts: active_electrical_contacts.into_boxed_slice(),
    })
}

fn total_carrier_material(neurons: &[NeuronPhysicalState]) -> Result<u128, ReachedCohortError> {
    neurons.iter().try_fold(0_u128, |total, neuron| {
        total
            .checked_add(
                neuron
                    .carrier_reservoirs()
                    .total()
                    .ok_or(ReachedCohortError::MaterialConservation)?,
            )
            .ok_or(ReachedCohortError::MaterialConservation)
    })
}
