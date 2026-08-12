//! Proof-stage functional vestibular receptor mounted on the definitive neuron.
//!
//! One reached millisecond carries exact signed body motion through canal,
//! cupula, hair-bundle, tip-link, and gating-spring mechanics. The resulting
//! open-minus-closed energy is converted losslessly into the complete neuron's
//! `GateWorkOccurrence`. A borrowed full joint DSF perspective can then reach
//! MathLoom/Psi exactly once through the ordinary complete-neuron transition.
//! This module does not yet prove that perspective was built from the same
//! vestibular occurrence; the exact joint-source builder owns that boundary.
//!
//! This is virtual-material functional embodiment. Its membrane reservoirs are
//! undifferentiated elementary carriers. It does not claim Type-II channel
//! kinetics, K+/Ca2+ identity, pumps, PMCA, or microscopic vestibular chemistry.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, ToPrimitive};

use crate::complete_neuron::{
    settle_extended_interval_with_contact, DnaExpressionContact, GateWorkOccurrence,
    NeuronIntervalInput, NeuronPhysicalAnatomy, NeuronPhysicalError, NeuronPhysicalState,
    RecoveryContact,
};
use crate::developmental_resting_population::MaterializedRestingNeuron;
use crate::declared_geometric_anatomy::declared_geometric_territory;
use crate::exact_rational::{ExactRational, ExactRationalError};
use crate::joint_uf_neuron_boundary::{
    bind_neuron_perspective, JointNeuronPerspective, SharedCompleteJointField,
};
use crate::local_cupula_hair_bundle_geometry::{
    CupulaBundleGeometryError, LocalCupulaBundleAnatomy,
};
use crate::local_gating_spring_energy::{
    settle_local_gating_spring_energy, GatingSpringEnergyAnatomy, GatingSpringEnergyError,
    GatingSpringEnergyOccurrence,
};
use crate::local_tip_link_extension::{
    settle_local_tip_link_extension, TipLinkGeometryError, TipLinkInsertionGeometry,
};
use crate::neuron_source_anchor::{bind_neuron_source_anchor, NeuronSourceSite};
use crate::reached_neuron_cohort::{ReachedCohortAnatomy, ReachedCohortState};
use crate::reached_vestibular_bundle_path::ReachedVestibularBundleTick;
use crate::sparse_electrical_contact::{SparseElectricalAnatomy, SparseElectricalState};
use crate::vestibular_joint_source_builder::VestibularJointSourceAdmission;
use crate::virtual_material_neuron_genesis::{
    create_virtual_material_neuron_with_gate_energy_quantum,
    definitive_virtual_gate_capacity_zeptojoules,
    definitive_virtual_reachable_support_energies_zeptojoules, VirtualMaterialGenesisError,
    specialize_quiescent_virtual_material_neuron_with_gate_energy_quantum,
    VirtualMaterialNeuronGenesis, VirtualMaterialReachedCohortGenesis,
};
use crate::virtual_vestibular_canal::{
    CanalAnatomy, PositiveRatio, VestibularError, VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND,
};

const FUNCTIONAL_VESTIBULAR_ANATOMY_MAGIC: &[u8; 8] = b"GLVANAT1";
const FUNCTIONAL_VESTIBULAR_ANATOMY_VERSION: u16 = 1;
pub(crate) const FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES: usize = 218;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum FunctionalVestibularError {
    EnergyLatticeUnavailable,
    NotIsolatedSingleVertex,
    ReachedAnatomyMismatch,
    TipLink(TipLinkGeometryError),
    Gating(GatingSpringEnergyError),
    Genesis(VirtualMaterialGenesisError),
    Neuron(NeuronPhysicalError),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum FunctionalVestibularAnatomyCodecError {
    Truncated { expected: usize, actual: usize },
    TrailingBytes { expected: usize, actual: usize },
    BadMagic,
    BadVersion(u16),
    NoncanonicalRational(ExactRationalError),
    InvalidCanal(VestibularError),
    InvalidBundle(CupulaBundleGeometryError),
    InvalidTipLink(TipLinkGeometryError),
    InvalidGatingSpring(GatingSpringEnergyError),
    InvalidFunctionalAnatomy(FunctionalVestibularError),
}

impl From<TipLinkGeometryError> for FunctionalVestibularError {
    fn from(value: TipLinkGeometryError) -> Self {
        Self::TipLink(value)
    }
}

impl From<GatingSpringEnergyError> for FunctionalVestibularError {
    fn from(value: GatingSpringEnergyError) -> Self {
        Self::Gating(value)
    }
}

impl From<VirtualMaterialGenesisError> for FunctionalVestibularError {
    fn from(value: VirtualMaterialGenesisError) -> Self {
        Self::Genesis(value)
    }
}

impl From<NeuronPhysicalError> for FunctionalVestibularError {
    fn from(value: NeuronPhysicalError) -> Self {
        Self::Neuron(value)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct FunctionalVestibularAnatomy {
    canal: CanalAnatomy,
    bundle: LocalCupulaBundleAnatomy,
    tip_link: TipLinkInsertionGeometry,
    gating_spring: GatingSpringEnergyAnatomy,
    gate_energy_quantum_zeptojoules: BigRational,
    gate_dissipation_capacity_quanta: u128,
}

impl FunctionalVestibularAnatomy {
    pub(crate) fn new(
        canal: CanalAnatomy,
        bundle: LocalCupulaBundleAnatomy,
        tip_link: TipLinkInsertionGeometry,
        gating_spring: GatingSpringEnergyAnatomy,
    ) -> Result<Self, FunctionalVestibularError> {
        let gate_energy_quantum_zeptojoules =
            derive_gate_energy_quantum(canal, bundle, tip_link, gating_spring)?;
        let physical_capacity = definitive_virtual_gate_capacity_zeptojoules();
        let capacity = physical_capacity / &gate_energy_quantum_zeptojoules;
        if !capacity.is_integer() {
            return Err(FunctionalVestibularError::EnergyLatticeUnavailable);
        }
        let gate_dissipation_capacity_quanta = capacity
            .to_integer()
            .to_u128()
            .filter(|value| *value != 0)
            .ok_or(FunctionalVestibularError::EnergyLatticeUnavailable)?;
        Ok(Self {
            canal,
            bundle,
            tip_link,
            gating_spring,
            gate_energy_quantum_zeptojoules,
            gate_dissipation_capacity_quanta,
        })
    }

    pub(crate) fn gate_energy_quantum_zeptojoules(&self) -> &BigRational {
        &self.gate_energy_quantum_zeptojoules
    }

    pub(crate) fn gate_dissipation_capacity_quanta(&self) -> u128 {
        self.gate_dissipation_capacity_quanta
    }

    pub(crate) fn canal_anatomy(&self) -> CanalAnatomy {
        self.canal
    }

    pub(crate) fn bundle_anatomy(&self) -> LocalCupulaBundleAnatomy {
        self.bundle
    }

    pub(crate) fn create_neuron(
        &self,
        perspective: JointNeuronPerspective<'_>,
        site: &NeuronSourceSite,
    ) -> Result<VirtualMaterialNeuronGenesis, FunctionalVestibularError> {
        create_virtual_material_neuron_with_gate_energy_quantum(
            perspective,
            site,
            self.gate_energy_quantum_zeptojoules.clone(),
        )
        .map_err(Into::into)
    }
}

/// Phase-one virtual body-and-balance anatomy.
///
/// This is deliberately a virtual-organism constitution, not a claim that one
/// biological preparation supplies every dimension below.  Its canal and
/// cupula geometry use the already documented biological-reference anatomy.
/// Its tip-link assembly uses the 5 pN/nm stiffness and 25 pN resting tension
/// reported by Nam et al., which derive an exact 5 nm resting extension.  The
/// 2 nm gate swing is the smaller explicitly evaluated swing in that same
/// model.  The intrinsic term is not fitted: 40 zJ is exactly
/// `kappa * d * (x_rest - d/2)`, so an unmoved body has zero externally
/// delivered gate work and opposite motion remains signed about that rest.
pub(crate) fn phase_one_virtual_vestibular_anatomy(
) -> Result<FunctionalVestibularAnatomy, FunctionalVestibularError> {
    FunctionalVestibularAnatomy::new(
        CanalAnatomy::new(
            6,
            13_200,
            PositiveRatio::new(25, 1)
                .map_err(|_| FunctionalVestibularError::EnergyLatticeUnavailable)?,
        )
        .map_err(|_| FunctionalVestibularError::EnergyLatticeUnavailable)?,
        LocalCupulaBundleAnatomy::new(2, 5, 20_000)
            .map_err(|_| FunctionalVestibularError::EnergyLatticeUnavailable)?,
        TipLinkInsertionGeometry::new(500)
            .map_err(FunctionalVestibularError::TipLink)?,
        GatingSpringEnergyAnatomy::new(
            ExactRational::integer(5),
            ExactRational::integer(2),
            ExactRational::integer(5),
            ExactRational::integer(40),
        )?,
    )
}

/// Encode only independently authored vestibular anatomy. The receptor's gate
/// energy quantum and dissipation capacity are derived consequences and are
/// deliberately absent from this record.
pub(crate) fn encode_functional_vestibular_anatomy(
    anatomy: &FunctionalVestibularAnatomy,
) -> [u8; FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES] {
    let mut encoded = [0_u8; FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES];
    let mut cursor = 0_usize;
    put_anatomy_bytes(
        &mut encoded,
        &mut cursor,
        FUNCTIONAL_VESTIBULAR_ANATOMY_MAGIC,
    );
    put_anatomy_bytes(
        &mut encoded,
        &mut cursor,
        &FUNCTIONAL_VESTIBULAR_ANATOMY_VERSION.to_le_bytes(),
    );
    put_anatomy_bytes(
        &mut encoded,
        &mut cursor,
        &anatomy.canal.fast_time_constant_ticks().to_le_bytes(),
    );
    put_anatomy_bytes(
        &mut encoded,
        &mut cursor,
        &anatomy.canal.slow_time_constant_ticks().to_le_bytes(),
    );
    let (gain_numerator, gain_denominator) = anatomy.canal.cupula_gain().parts();
    put_anatomy_bytes(&mut encoded, &mut cursor, &gain_numerator.to_le_bytes());
    put_anatomy_bytes(&mut encoded, &mut cursor, &gain_denominator.to_le_bytes());
    put_exact_rational(&mut encoded, &mut cursor, anatomy.bundle.local_transfer());
    put_anatomy_bytes(
        &mut encoded,
        &mut cursor,
        &anatomy.bundle.bundle_height_nanometres().to_le_bytes(),
    );
    put_anatomy_bytes(
        &mut encoded,
        &mut cursor,
        &anatomy
            .tip_link
            .insertion_separation_nanometres()
            .to_le_bytes(),
    );
    let (stiffness, gate_swing, closed_extension, intrinsic_energy) =
        anatomy.gating_spring.exact_parts();
    for value in [stiffness, gate_swing, closed_extension, intrinsic_energy] {
        put_exact_rational(&mut encoded, &mut cursor, value);
    }
    debug_assert_eq!(cursor, FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES);
    encoded
}

/// Decode authored vestibular anatomy through its existing typed constructors.
/// This re-derives and re-checks the receptor energy lattice rather than
/// accepting persisted derived authority.
pub(crate) fn decode_functional_vestibular_anatomy(
    encoded: &[u8],
) -> Result<FunctionalVestibularAnatomy, FunctionalVestibularAnatomyCodecError> {
    if encoded.len() < FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES {
        return Err(FunctionalVestibularAnatomyCodecError::Truncated {
            expected: FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES,
            actual: encoded.len(),
        });
    }
    if encoded.len() > FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES {
        return Err(FunctionalVestibularAnatomyCodecError::TrailingBytes {
            expected: FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES,
            actual: encoded.len(),
        });
    }
    let mut cursor = 0_usize;
    if take_anatomy_bytes(
        encoded,
        &mut cursor,
        FUNCTIONAL_VESTIBULAR_ANATOMY_MAGIC.len(),
    ) != FUNCTIONAL_VESTIBULAR_ANATOMY_MAGIC
    {
        return Err(FunctionalVestibularAnatomyCodecError::BadMagic);
    }
    let version = u16::from_le_bytes(
        take_anatomy_bytes(encoded, &mut cursor, 2)
            .try_into()
            .expect("fixed codec width"),
    );
    if version != FUNCTIONAL_VESTIBULAR_ANATOMY_VERSION {
        return Err(FunctionalVestibularAnatomyCodecError::BadVersion(version));
    }
    let fast_ticks = take_u64(encoded, &mut cursor);
    let slow_ticks = take_u64(encoded, &mut cursor);
    let gain = PositiveRatio::new(
        take_u64(encoded, &mut cursor),
        take_u64(encoded, &mut cursor),
    )
    .map_err(FunctionalVestibularAnatomyCodecError::InvalidCanal)?;
    let canal = CanalAnatomy::new(fast_ticks, slow_ticks, gain)
        .map_err(FunctionalVestibularAnatomyCodecError::InvalidCanal)?;

    let bundle_transfer = take_exact_rational(encoded, &mut cursor)?;
    let (bundle_transfer_numerator, bundle_transfer_denominator) = bundle_transfer.parts();
    let bundle_transfer_numerator = u64::try_from(bundle_transfer_numerator).map_err(|_| {
        FunctionalVestibularAnatomyCodecError::InvalidBundle(
            CupulaBundleGeometryError::ArithmeticWidth,
        )
    })?;
    let bundle_transfer_denominator = u64::try_from(bundle_transfer_denominator).map_err(|_| {
        FunctionalVestibularAnatomyCodecError::InvalidBundle(
            CupulaBundleGeometryError::ArithmeticWidth,
        )
    })?;
    let bundle = LocalCupulaBundleAnatomy::new(
        bundle_transfer_numerator,
        bundle_transfer_denominator,
        take_u64(encoded, &mut cursor),
    )
    .map_err(FunctionalVestibularAnatomyCodecError::InvalidBundle)?;
    let tip_link = TipLinkInsertionGeometry::new(take_u64(encoded, &mut cursor))
        .map_err(FunctionalVestibularAnatomyCodecError::InvalidTipLink)?;
    let gating_spring = GatingSpringEnergyAnatomy::new(
        take_exact_rational(encoded, &mut cursor)?,
        take_exact_rational(encoded, &mut cursor)?,
        take_exact_rational(encoded, &mut cursor)?,
        take_exact_rational(encoded, &mut cursor)?,
    )
    .map_err(FunctionalVestibularAnatomyCodecError::InvalidGatingSpring)?;
    debug_assert_eq!(cursor, FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES);
    FunctionalVestibularAnatomy::new(canal, bundle, tip_link, gating_spring)
        .map_err(FunctionalVestibularAnatomyCodecError::InvalidFunctionalAnatomy)
}

fn put_anatomy_bytes(
    encoded: &mut [u8; FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES],
    cursor: &mut usize,
    bytes: &[u8],
) {
    let end = *cursor + bytes.len();
    encoded[*cursor..end].copy_from_slice(bytes);
    *cursor = end;
}

fn put_exact_rational(
    encoded: &mut [u8; FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES],
    cursor: &mut usize,
    value: ExactRational,
) {
    let (numerator, denominator) = value.parts();
    put_anatomy_bytes(encoded, cursor, &numerator.to_le_bytes());
    put_anatomy_bytes(encoded, cursor, &denominator.to_le_bytes());
}

fn take_anatomy_bytes<'a>(encoded: &'a [u8], cursor: &mut usize, length: usize) -> &'a [u8] {
    let end = *cursor + length;
    let bytes = &encoded[*cursor..end];
    *cursor = end;
    bytes
}

fn take_u64(encoded: &[u8], cursor: &mut usize) -> u64 {
    u64::from_le_bytes(
        take_anatomy_bytes(encoded, cursor, 8)
            .try_into()
            .expect("fixed codec width"),
    )
}

fn take_exact_rational(
    encoded: &[u8],
    cursor: &mut usize,
) -> Result<ExactRational, FunctionalVestibularAnatomyCodecError> {
    let numerator = i128::from_le_bytes(
        take_anatomy_bytes(encoded, cursor, 16)
            .try_into()
            .expect("fixed codec width"),
    );
    let denominator = u128::from_le_bytes(
        take_anatomy_bytes(encoded, cursor, 16)
            .try_into()
            .expect("fixed codec width"),
    );
    ExactRational::new(numerator, denominator)
        .map_err(FunctionalVestibularAnatomyCodecError::NoncanonicalRational)
}

/// Create the sole reached cell for one typed vestibular source occurrence.
/// The receptor-derived energy lattice becomes persisted neuron anatomy; the
/// source anchor becomes the persisted source site. The empty electrical set
/// is explicit because one isolated neuron has no possible inter-neuron edge.
pub(crate) fn create_single_vertex_vestibular_reached_cohort(
    vestibular: &FunctionalVestibularAnatomy,
    source: &VestibularJointSourceAdmission,
    shared: &SharedCompleteJointField,
    neuron_lineage: [u8; 16],
) -> Result<VirtualMaterialReachedCohortGenesis, FunctionalVestibularError> {
    create_single_vertex_vestibular_reached_cohort_inner(
        vestibular,
        source,
        shared,
        neuron_lineage,
        None,
    )
}

/// Specialize one already-declared virgin body-and-balance cell without
/// replacing its lineage, place, membrane, carriers, or lived state.
pub(crate) fn specialize_single_vertex_vestibular_reached_cohort(
    vestibular: &FunctionalVestibularAnatomy,
    source: &VestibularJointSourceAdmission,
    shared: &SharedCompleteJointField,
    neuron_lineage: [u8; 16],
    resting: &MaterializedRestingNeuron,
) -> Result<VirtualMaterialReachedCohortGenesis, FunctionalVestibularError> {
    create_single_vertex_vestibular_reached_cohort_inner(
        vestibular,
        source,
        shared,
        neuron_lineage,
        Some(resting),
    )
}

fn create_single_vertex_vestibular_reached_cohort_inner(
    vestibular: &FunctionalVestibularAnatomy,
    source: &VestibularJointSourceAdmission,
    shared: &SharedCompleteJointField,
    neuron_lineage: [u8; 16],
    resting: Option<&MaterializedRestingNeuron>,
) -> Result<VirtualMaterialReachedCohortGenesis, FunctionalVestibularError> {
    if shared.vertex_count() != 1
        || shared.groups().len() != 1
        || shared.groups()[0].as_slice() != [0]
        || source.sparse_contact_count() != 0
    {
        return Err(FunctionalVestibularError::NotIsolatedSingleVertex);
    }
    let (episode, _) = source.joint_source_with_contacts();
    let perspective = bind_neuron_perspective(shared, 0, 0).map_err(|error| {
        FunctionalVestibularError::Genesis(VirtualMaterialGenesisError::JointField(error))
    })?;
    let source_anchor = bind_neuron_source_anchor(episode, perspective).map_err(|error| {
        FunctionalVestibularError::Genesis(VirtualMaterialGenesisError::Source(error))
    })?;
    let site = NeuronSourceSite::from_anchor(source_anchor);
    let neuron = match resting {
        Some(resting) => specialize_quiescent_virtual_material_neuron_with_gate_energy_quantum(
            perspective,
            &site,
            resting.place,
            &resting.anatomy,
            &resting.state,
            vestibular.gate_energy_quantum_zeptojoules.clone(),
        )
        .map_err(FunctionalVestibularError::Genesis)?,
        None => vestibular.create_neuron(perspective, &site)?,
    };
    let electrical = SparseElectricalAnatomy::new(1, Vec::new()).map_err(|error| {
        FunctionalVestibularError::Genesis(VirtualMaterialGenesisError::Electrical(error))
    })?;
    let electrical_state = SparseElectricalState::genesis(&electrical);
    let (neuron_anatomy, neuron_state, zero_recovery_catalysts) = neuron.into_parts();
    let anatomy = ReachedCohortAnatomy::new(
        vec![neuron_anatomy],
        vec![neuron_lineage],
        vec![site],
        electrical,
    )
    .map_err(|error| {
        FunctionalVestibularError::Genesis(VirtualMaterialGenesisError::Cohort(error))
    })?;
    let state = ReachedCohortState::new(&anatomy, vec![neuron_state], electrical_state).map_err(
        |error| FunctionalVestibularError::Genesis(VirtualMaterialGenesisError::Cohort(error)),
    )?;
    Ok(VirtualMaterialReachedCohortGenesis {
        anatomy,
        state,
        zero_recovery_catalysts: vec![zero_recovery_catalysts].into_boxed_slice(),
    })
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct FunctionalVestibularTransduction {
    pub(crate) reached_tick: ReachedVestibularBundleTick,
    pub(crate) gating_spring: GatingSpringEnergyOccurrence,
    pub(crate) gate_work_zeptojoules: BigRational,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct FunctionalVestibularNeuronInterval {
    pub(crate) transduction: FunctionalVestibularTransduction,
    pub(crate) successor_neuron: NeuronPhysicalState,
    pub(crate) exported_heat_zeptojoules: BigRational,
    pub(crate) quiescent: bool,
}

pub(crate) fn transduce_functional_vestibular_interval(
    anatomy: &FunctionalVestibularAnatomy,
    reached_tick: ReachedVestibularBundleTick,
) -> Result<FunctionalVestibularTransduction, FunctionalVestibularError> {
    if reached_tick.canal_anatomy != anatomy.canal || reached_tick.bundle_anatomy != anatomy.bundle
    {
        return Err(FunctionalVestibularError::ReachedAnatomyMismatch);
    }
    let tip_link = settle_local_tip_link_extension(anatomy.tip_link, reached_tick.local_bundle)?;
    let gating_spring = settle_local_gating_spring_energy(anatomy.gating_spring, tip_link)?;
    let gate_work_zeptojoules =
        exact_to_big_rational(gating_spring.open_minus_closed_energy_zeptojoules);
    Ok(FunctionalVestibularTransduction {
        reached_tick,
        gating_spring,
        gate_work_zeptojoules,
    })
}

/// Prove compatibility between one exact vestibular GateWork occurrence and
/// the ordinary complete-neuron path. The borrowed perspective remains a full
/// joint DSF and is consumed once, but this boundary cannot prove it came from
/// the same physical occurrence. The joint-source mount must establish that
/// causal identity before this can become truthful body re-entry.
#[allow(clippy::too_many_arguments)]
pub(crate) fn settle_vestibular_neuron_compatibility_interval(
    vestibular: &FunctionalVestibularAnatomy,
    reached_tick: ReachedVestibularBundleTick,
    neuron_anatomy: &NeuronPhysicalAnatomy,
    predecessor_neuron: &NeuronPhysicalState,
    perspective: JointNeuronPerspective<'_>,
    zero_recovery_catalysts: &[u128],
    inter_neuron_outward_elementary_charges: i128,
) -> Result<FunctionalVestibularNeuronInterval, FunctionalVestibularError> {
    let transduction = transduce_functional_vestibular_interval(vestibular, reached_tick)?;
    let settled = settle_extended_interval_with_contact(
        neuron_anatomy,
        predecessor_neuron,
        NeuronIntervalInput {
            perspective,
            gate_work: GateWorkOccurrence::new(transduction.gate_work_zeptojoules.clone()),
            interval_microseconds: transduction.reached_tick.interval_microseconds,
            recovery: RecoveryContact::new(zero_recovery_catalysts, 0, 0),
            dna_expression: DnaExpressionContact::new(0),
            receptor_successor_residue: None,
            prepared_psi: None,
        },
        inter_neuron_outward_elementary_charges,
    )?;
    let exported_heat_zeptojoules = settled.exported_heat_zeptojoules.clone();
    Ok(FunctionalVestibularNeuronInterval {
        transduction,
        successor_neuron: settled.successor,
        exported_heat_zeptojoules,
        quiescent: settled.quiescent,
    })
}

fn derive_gate_energy_quantum(
    canal: CanalAnatomy,
    bundle: LocalCupulaBundleAnatomy,
    tip_link: TipLinkInsertionGeometry,
    gating_spring: GatingSpringEnergyAnatomy,
) -> Result<BigRational, FunctionalVestibularError> {
    let (gain_numerator, gain_denominator) = canal.cupula_gain().parts();
    let (stiffness, gate_swing, resting_extension, intrinsic) = gating_spring.exact_parts();
    let half_swing =
        exact_to_big_rational(gate_swing) / BigRational::from_integer(BigInt::from(2_u8));
    let stiffness = exact_to_big_rational(stiffness);
    let gate_swing = exact_to_big_rational(gate_swing);
    let baseline = exact_to_big_rational(intrinsic)
        - &stiffness * &gate_swing * (exact_to_big_rational(resting_extension) - half_swing);
    let mechanical_unit = stiffness
        * gate_swing
        * BigRational::new(BigInt::from(gain_numerator), BigInt::from(gain_denominator))
        / BigRational::from_integer(BigInt::from(VELOCITY_STATE_UNITS_PER_DEGREE_PER_SECOND))
        * exact_to_big_rational(bundle.local_transfer())
        / BigRational::from_integer(BigInt::from(bundle.bundle_height_nanometres()))
        * BigRational::from_integer(BigInt::from(tip_link.insertion_separation_nanometres()));
    if mechanical_unit <= BigRational::from_integer(BigInt::from(0_u8)) {
        return Err(FunctionalVestibularError::EnergyLatticeUnavailable);
    }

    let reachable_support_energies = definitive_virtual_reachable_support_energies_zeptojoules();
    let physical_capacity = definitive_virtual_gate_capacity_zeptojoules();
    let mut common_denominator = 1_u128;
    for energy in [&baseline, &mechanical_unit, &physical_capacity]
        .into_iter()
        .chain(reachable_support_energies.iter())
    {
        let denominator = energy
            .denom()
            .to_u128()
            .ok_or(FunctionalVestibularError::EnergyLatticeUnavailable)?;
        common_denominator = checked_lcm(common_denominator, denominator)
            .ok_or(FunctionalVestibularError::EnergyLatticeUnavailable)?;
    }
    Ok(BigRational::new(
        BigInt::one(),
        BigInt::from(common_denominator),
    ))
}

fn exact_to_big_rational(value: ExactRational) -> BigRational {
    let (numerator, denominator) = value.parts();
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

fn checked_lcm(left: u128, right: u128) -> Option<u128> {
    left.checked_div(gcd(left, right))?.checked_mul(right)
}

fn gcd(mut left: u128, mut right: u128) -> u128 {
    while right != 0 {
        let remainder = left % right;
        left = right;
        right = remainder;
    }
    left
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::joint_uf_neuron_boundary::prepare_complete_joint_field_with_admission;
    use crate::reached_neuron_cohort::{decode_reached_cohort_cell, encode_reached_cohort_cell};
    use crate::reached_vestibular_bundle_path::settle_reached_vestibular_bundle_tick as externally_settle_tick;
    use crate::vestibular_joint_source_builder::admit_same_cause_vestibular_joint_source_interval;
    use crate::virtual_body_yaw_motion::{
        settle_signed_yaw_actuation, SignedYawActuation, YawBodyState,
    };
    use crate::virtual_material_neuron_genesis::create_virtual_material_neuron;
    use crate::virtual_vestibular_canal::{
        CanalState, PositiveRatio, WORLD_MECHANICAL_TICK_MICROSECONDS,
    };

    fn exact(numerator: i128, denominator: u128) -> ExactRational {
        ExactRational::new(numerator, denominator).unwrap()
    }

    fn candidate_anatomy() -> FunctionalVestibularAnatomy {
        FunctionalVestibularAnatomy::new(
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap(),
            LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap(),
            TipLinkInsertionGeometry::new(500).unwrap(),
            GatingSpringEnergyAnatomy::new(
                ExactRational::integer(1),
                ExactRational::integer(4),
                ExactRational::integer(2),
                ExactRational::integer(8),
            )
            .unwrap(),
        )
        .unwrap()
    }

    fn reached_tick(
        anatomy: &FunctionalVestibularAnatomy,
        signed_body_motion_millidegrees: i32,
    ) -> ReachedVestibularBundleTick {
        externally_settle_tick(
            anatomy.canal,
            CanalState::at_rest(),
            signed_body_motion_millidegrees,
            anatomy.bundle,
        )
        .unwrap()
    }

    fn admitted_source(
        anatomy: &FunctionalVestibularAnatomy,
        signed_body_motion_millidegrees: i32,
    ) -> (VestibularJointSourceAdmission, ReachedVestibularBundleTick) {
        let predecessor_body = YawBodyState::new(0).unwrap();
        let body = settle_signed_yaw_actuation(
            predecessor_body,
            SignedYawActuation::new(
                signed_body_motion_millidegrees,
                WORLD_MECHANICAL_TICK_MICROSECONDS,
            )
            .unwrap(),
        )
        .unwrap();
        let tick = reached_tick(anatomy, body.trajectory.as_slice()[0]);
        let source = admit_same_cause_vestibular_joint_source_interval(
            41,
            predecessor_body,
            body.successor,
            tick,
        )
        .unwrap();
        (source, tick)
    }

    #[test]
    fn candidate_lattice_is_derived_and_preserves_nine_quarters_capacity() {
        let anatomy = candidate_anatomy();
        assert_eq!(
            anatomy.gate_energy_quantum_zeptojoules(),
            &BigRational::new(BigInt::one(), BigInt::from(2_000_u16))
        );
        assert_eq!(anatomy.gate_dissipation_capacity_quanta(), 4_500);
    }

    #[test]
    fn gate_lattice_represents_every_reachable_plastic_support_energy() {
        let anatomy = candidate_anatomy();
        let support = definitive_virtual_reachable_support_energies_zeptojoules();
        assert_eq!(support[0], BigRational::from_integer(BigInt::one()));
        assert_eq!(
            support[1],
            BigRational::new(BigInt::from(3_u8), BigInt::from(16_u8))
        );
        for energy in support {
            assert!(
                (energy / anatomy.gate_energy_quantum_zeptojoules()).is_integer(),
                "reachable support energy is outside the receptor gate lattice"
            );
        }
    }

    #[test]
    fn functional_vestibular_anatomy_codec_round_trips_authored_primitives_exactly() {
        let anatomy = candidate_anatomy();
        let encoded = encode_functional_vestibular_anatomy(&anatomy);
        assert_eq!(encoded.len(), FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES);
        assert_eq!(&encoded[0..8], FUNCTIONAL_VESTIBULAR_ANATOMY_MAGIC);
        assert_eq!(
            &encoded[8..10],
            &FUNCTIONAL_VESTIBULAR_ANATOMY_VERSION.to_le_bytes()
        );
        assert_eq!(&encoded[10..18], &6_u64.to_le_bytes());
        assert_eq!(&encoded[18..26], &13_200_u64.to_le_bytes());
        assert_eq!(&encoded[26..34], &25_u64.to_le_bytes());
        assert_eq!(&encoded[34..42], &1_u64.to_le_bytes());
        assert_eq!(&encoded[42..58], &2_i128.to_le_bytes());
        assert_eq!(&encoded[58..74], &5_u128.to_le_bytes());
        assert_eq!(&encoded[74..82], &20_000_u64.to_le_bytes());
        assert_eq!(&encoded[82..90], &500_u64.to_le_bytes());

        let restored = decode_functional_vestibular_anatomy(&encoded).unwrap();
        assert_eq!(restored, anatomy);
        assert_eq!(
            restored.gate_energy_quantum_zeptojoules(),
            &BigRational::new(BigInt::one(), BigInt::from(2_000_u16))
        );
        assert_eq!(restored.gate_dissipation_capacity_quanta(), 4_500);
        assert_eq!(encode_functional_vestibular_anatomy(&restored), encoded);
    }

    #[test]
    fn functional_vestibular_anatomy_codec_refuses_truncation_and_trailing_bytes() {
        let encoded = encode_functional_vestibular_anatomy(&candidate_anatomy());
        assert_eq!(
            decode_functional_vestibular_anatomy(&encoded[..encoded.len() - 1]),
            Err(FunctionalVestibularAnatomyCodecError::Truncated {
                expected: FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES,
                actual: FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES - 1,
            })
        );
        let mut trailing = encoded.to_vec();
        trailing.push(0);
        assert_eq!(
            decode_functional_vestibular_anatomy(&trailing),
            Err(FunctionalVestibularAnatomyCodecError::TrailingBytes {
                expected: FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES,
                actual: FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES + 1,
            })
        );
    }

    #[test]
    fn functional_vestibular_anatomy_codec_refuses_header_and_primitive_tampering() {
        let encoded = encode_functional_vestibular_anatomy(&candidate_anatomy());
        let mut bad_magic = encoded;
        bad_magic[0] ^= 0xff;
        assert_eq!(
            decode_functional_vestibular_anatomy(&bad_magic),
            Err(FunctionalVestibularAnatomyCodecError::BadMagic)
        );

        let mut bad_version = encoded;
        bad_version[8..10].copy_from_slice(&2_u16.to_le_bytes());
        assert_eq!(
            decode_functional_vestibular_anatomy(&bad_version),
            Err(FunctionalVestibularAnatomyCodecError::BadVersion(2))
        );

        let mut zero_fast_time_constant = encoded;
        zero_fast_time_constant[10..18].fill(0);
        assert_eq!(
            decode_functional_vestibular_anatomy(&zero_fast_time_constant),
            Err(FunctionalVestibularAnatomyCodecError::InvalidCanal(
                VestibularError::ZeroTimeConstant
            ))
        );
    }

    #[test]
    fn functional_vestibular_anatomy_codec_refuses_noncanonical_exact_ratios() {
        let mut encoded = encode_functional_vestibular_anatomy(&candidate_anatomy());
        encoded[42..58].copy_from_slice(&2_i128.to_le_bytes());
        encoded[58..74].copy_from_slice(&2_u128.to_le_bytes());
        assert_eq!(
            decode_functional_vestibular_anatomy(&encoded),
            Err(FunctionalVestibularAnatomyCodecError::NoncanonicalRational(
                ExactRationalError::NonCanonicalRatio
            ))
        );
    }

    #[test]
    fn reachable_yaw_gatework_is_compatible_with_the_specialized_neuron() {
        let anatomy = candidate_anatomy();
        let (source, tick) = admitted_source(&anatomy, 64);
        let admission = source.joint_uf_source_admission().unwrap();
        let (episode, _) = source.joint_source_with_contacts();
        let shared = prepare_complete_joint_field_with_admission(episode, 0, &admission).unwrap();
        let body_perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
        let body_site = NeuronSourceSite::from_anchor(
            bind_neuron_source_anchor(episode, body_perspective).unwrap(),
        );
        let genesis = anatomy.create_neuron(body_perspective, &body_site).unwrap();
        let receptor_population = declared_geometric_territory(&body_site).unwrap();
        assert_eq!(
            genesis.anatomy().gate_dissipation_capacity_quanta(),
            4_500 * receptor_population
        );
        let settled = settle_vestibular_neuron_compatibility_interval(
            &anatomy,
            tick,
            genesis.anatomy(),
            genesis.state(),
            body_perspective,
            genesis.zero_recovery_catalysts(),
            0,
        )
        .unwrap();
        assert_eq!(
            settled.transduction.gate_work_zeptojoules,
            BigRational::new(BigInt::from(-569_i16), BigInt::from(500_u16))
        );
        // The receptor contributes -569/500 zJ. The definitive neuron's
        // distinct +1-zJ support contribution makes its settled total
        // delta-G -69/500 zJ = -276 * (1/2000 zJ).
        assert_eq!(genesis.state().gate.open_population(), 0);
        assert!(settled.successor_neuron.gate.open_population() > 0);
        assert!(settled.successor_neuron.gate.open_population() <= receptor_population);
        assert_ne!(settled.successor_neuron, *genesis.state());
    }

    #[test]
    fn phase_one_body_tick_opens_the_receptor_and_exports_exact_surplus_heat() {
        let anatomy = phase_one_virtual_vestibular_anatomy().unwrap();
        let (source, tick) = admitted_source(&anatomy, 360);
        let admission = source.joint_uf_source_admission().unwrap();
        let (episode, _) = source.joint_source_with_contacts();
        let shared = prepare_complete_joint_field_with_admission(episode, 0, &admission).unwrap();
        let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
        let site = NeuronSourceSite::from_anchor(
            bind_neuron_source_anchor(episode, perspective).unwrap(),
        );
        let genesis = anatomy.create_neuron(perspective, &site).unwrap();
        let receptor_population = declared_geometric_territory(&site).unwrap();
        let settled = settle_vestibular_neuron_compatibility_interval(
            &anatomy,
            tick,
            genesis.anatomy(),
            genesis.state(),
            perspective,
            genesis.zero_recovery_catalysts(),
            0,
        )
        .unwrap();
        assert_eq!(
            settled.successor_neuron.gate.open_population(),
            receptor_population
        );
        assert_ne!(
            settled
                .successor_neuron
                .membrane_state()
                .separated_elementary_charges(),
            0
        );
        assert!(
            settled.exported_heat_zeptojoules
                > BigRational::from_integer(BigInt::from(0))
        );
    }

    #[test]
    fn reached_cohort_factory_persists_the_typed_vestibular_lattice_and_source_site() {
        let anatomy = candidate_anatomy();
        let (source, _) = admitted_source(&anatomy, 64);
        let admission = source.joint_uf_source_admission().unwrap();
        let (episode, _) = source.joint_source_with_contacts();
        let shared = prepare_complete_joint_field_with_admission(episode, 0, &admission).unwrap();
        let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
        let expected_source_site =
            NeuronSourceSite::from_anchor(bind_neuron_source_anchor(episode, perspective).unwrap());
        let lineage = [7; 16];
        let genesis =
            create_single_vertex_vestibular_reached_cohort(&anatomy, &source, &shared, lineage)
                .unwrap();
        assert_eq!(genesis.anatomy.neuron_count(), 1);
        assert_eq!(genesis.anatomy.contact_count(), 0);
        assert_eq!(genesis.anatomy.neuron_lineages(), &[lineage]);
        assert_eq!(
            genesis.anatomy.source_sites().collect::<Vec<_>>(),
            vec![&expected_source_site]
        );
        assert_eq!(
            genesis.anatomy.neuron_anatomies()[0].gate_dissipation_capacity_quanta(),
            4_500 * declared_geometric_territory(&expected_source_site).unwrap()
        );
        assert_eq!(genesis.state.neurons().len(), 1);
        assert_eq!(genesis.zero_recovery_catalysts.len(), 1);

        let encoded = encode_reached_cohort_cell(&genesis.anatomy, &genesis.state).unwrap();
        let (restored_anatomy, restored_state) = decode_reached_cohort_cell(&encoded).unwrap();
        assert_eq!(restored_anatomy, genesis.anatomy);
        assert_eq!(restored_state, genesis.state);
    }

    #[test]
    fn ordinary_gate_lattice_conserves_exact_fractional_vestibular_work() {
        let anatomy = candidate_anatomy();
        let (source, tick) = admitted_source(&anatomy, 64);
        let admission = source.joint_uf_source_admission().unwrap();
        let (episode, _) = source.joint_source_with_contacts();
        let shared = prepare_complete_joint_field_with_admission(episode, 0, &admission).unwrap();
        let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
        let ordinary_site =
            NeuronSourceSite::from_anchor(bind_neuron_source_anchor(episode, perspective).unwrap());
        let ordinary = create_virtual_material_neuron(perspective, &ordinary_site).unwrap();
        assert_eq!(
            ordinary.anatomy().gate_dissipation_capacity_quanta(),
            36 * declared_geometric_territory(&ordinary_site).unwrap()
        );
        assert_ne!(
            ordinary.anatomy().gate_dissipation_capacity_quanta(),
            anatomy.gate_dissipation_capacity_quanta()
        );
        let settled = settle_vestibular_neuron_compatibility_interval(
            &anatomy,
            tick,
            ordinary.anatomy(),
            ordinary.state(),
            perspective,
            ordinary.zero_recovery_catalysts(),
            0,
        )
        .unwrap();
        assert_ne!(&settled.successor_neuron, ordinary.state());
    }

    #[test]
    fn mechanical_rest_and_opposing_motion_retain_exact_energy_symmetry() {
        let anatomy = candidate_anatomy();
        let rest =
            transduce_functional_vestibular_interval(&anatomy, reached_tick(&anatomy, 0)).unwrap();
        let positive =
            transduce_functional_vestibular_interval(&anatomy, reached_tick(&anatomy, 64)).unwrap();
        let negative =
            transduce_functional_vestibular_interval(&anatomy, reached_tick(&anatomy, -64))
                .unwrap();
        assert_eq!(rest.reached_tick.successor_canal, CanalState::at_rest());
        assert_eq!(
            rest.gate_work_zeptojoules,
            BigRational::from_integer(8.into())
        );
        assert_eq!(
            &positive.gate_work_zeptojoules + &negative.gate_work_zeptojoules,
            &rest.gate_work_zeptojoules * BigRational::from_integer(2.into())
        );
        assert!(positive.gate_work_zeptojoules < rest.gate_work_zeptojoules);
        assert!(negative.gate_work_zeptojoules > rest.gate_work_zeptojoules);
    }

    #[test]
    fn anatomy_without_a_representable_common_lattice_is_refused_exactly() {
        let result = FunctionalVestibularAnatomy::new(
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(25, 1).unwrap()).unwrap(),
            LocalCupulaBundleAnatomy::new(2, 5, 20_000).unwrap(),
            TipLinkInsertionGeometry::new(500).unwrap(),
            GatingSpringEnergyAnatomy::new(
                exact(1, u128::MAX),
                exact(1, u128::MAX - 1),
                ExactRational::integer(2),
                ExactRational::integer(8),
            )
            .unwrap(),
        );
        assert_eq!(
            result,
            Err(FunctionalVestibularError::EnergyLatticeUnavailable)
        );
    }

    #[test]
    fn transduction_refuses_a_tick_settled_by_different_anatomy() {
        let anatomy = candidate_anatomy();
        let foreign_canal =
            CanalAnatomy::new(6, 13_200, PositiveRatio::new(26, 1).unwrap()).unwrap();
        let foreign =
            externally_settle_tick(foreign_canal, CanalState::at_rest(), 64, anatomy.bundle)
                .unwrap();
        assert_eq!(
            transduce_functional_vestibular_interval(&anatomy, foreign),
            Err(FunctionalVestibularError::ReachedAnatomyMismatch)
        );
    }

    #[test]
    fn receptor_source_contains_no_reached_tick_settlement_call() {
        let source = include_str!("vestibular_neuron_path.rs");
        let forbidden_call = ["settle_reached_vestibular_", "bundle_tick("].concat();
        assert!(!source.contains(&forbidden_call));
    }
}
