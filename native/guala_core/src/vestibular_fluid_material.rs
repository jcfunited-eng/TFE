//! Conserved local material for vestibular hair-cell transduction and
//! dark-cell potassium return.
//!
//! Hair-cell apical K+/Ca2+ entry, hair-cell basolateral K+ exit, hair-bundle
//! PMCA2 Ca2+/H+ exchange, dark-cell Na+/K+-ATPase, dark-cell NKCC1, and
//! dark-cell apical K+ secretion settle atomically from one predecessor. Every
//! event is a signed physical reaction extent; this law supplies neither
//! guessed kinetics nor a recovery command.

use core::mem::size_of;

const MATERIAL_QUANTITY_COUNT: usize = 21;
const CODEC_BYTES: usize = MATERIAL_QUANTITY_COUNT * size_of::<u128>();

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum VestibularMaterialPool {
    EndolymphPotassium,
    HairCellPotassium,
    PerilymphPotassium,
    DarkCellPotassium,
    EndolymphCalcium,
    HairCellCalcium,
    PerilymphSodium,
    DarkCellSodium,
    PerilymphChloride,
    DarkCellChloride,
    DarkCellAtp,
    DarkCellWater,
    DarkCellAdp,
    DarkCellHydrogenPhosphate,
    DarkCellProton,
    EndolymphProton,
    HairCellAtp,
    HairCellWater,
    HairCellAdp,
    HairCellHydrogenPhosphate,
    HairCellProton,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum VestibularFluidMaterialError {
    ChargePartitionMismatch,
    InsufficientMaterial(VestibularMaterialPool),
    ArithmeticWidth,
    InvalidRestart,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct VestibularFluidMaterial {
    endolymph_potassium_ions: u128,
    hair_cell_potassium_ions: u128,
    perilymph_potassium_ions: u128,
    dark_cell_potassium_ions: u128,
    endolymph_calcium_ions: u128,
    hair_cell_calcium_ions: u128,
    perilymph_sodium_ions: u128,
    dark_cell_sodium_ions: u128,
    perilymph_chloride_ions: u128,
    dark_cell_chloride_ions: u128,
    dark_cell_atp_ions: u128,
    dark_cell_water_molecules: u128,
    dark_cell_adp_ions: u128,
    dark_cell_hydrogen_phosphate_ions: u128,
    dark_cell_protons: u128,
    endolymph_protons: u128,
    hair_cell_atp_ions: u128,
    hair_cell_water_molecules: u128,
    hair_cell_adp_ions: u128,
    hair_cell_hydrogen_phosphate_ions: u128,
    hair_cell_protons: u128,
}

impl VestibularFluidMaterial {
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn new(
        endolymph_potassium_ions: u128,
        hair_cell_potassium_ions: u128,
        perilymph_potassium_ions: u128,
        dark_cell_potassium_ions: u128,
        endolymph_calcium_ions: u128,
        hair_cell_calcium_ions: u128,
        perilymph_sodium_ions: u128,
        dark_cell_sodium_ions: u128,
        perilymph_chloride_ions: u128,
        dark_cell_chloride_ions: u128,
        dark_cell_atp_ions: u128,
        dark_cell_water_molecules: u128,
        dark_cell_adp_ions: u128,
        dark_cell_hydrogen_phosphate_ions: u128,
        dark_cell_protons: u128,
        endolymph_protons: u128,
        hair_cell_atp_ions: u128,
        hair_cell_water_molecules: u128,
        hair_cell_adp_ions: u128,
        hair_cell_hydrogen_phosphate_ions: u128,
        hair_cell_protons: u128,
    ) -> Self {
        Self {
            endolymph_potassium_ions,
            hair_cell_potassium_ions,
            perilymph_potassium_ions,
            dark_cell_potassium_ions,
            endolymph_calcium_ions,
            hair_cell_calcium_ions,
            perilymph_sodium_ions,
            dark_cell_sodium_ions,
            perilymph_chloride_ions,
            dark_cell_chloride_ions,
            dark_cell_atp_ions,
            dark_cell_water_molecules,
            dark_cell_adp_ions,
            dark_cell_hydrogen_phosphate_ions,
            dark_cell_protons,
            endolymph_protons,
            hair_cell_atp_ions,
            hair_cell_water_molecules,
            hair_cell_adp_ions,
            hair_cell_hydrogen_phosphate_ions,
            hair_cell_protons,
        }
    }

    pub(crate) fn quantities(self) -> [u128; MATERIAL_QUANTITY_COUNT] {
        [
            self.endolymph_potassium_ions,
            self.hair_cell_potassium_ions,
            self.perilymph_potassium_ions,
            self.dark_cell_potassium_ions,
            self.endolymph_calcium_ions,
            self.hair_cell_calcium_ions,
            self.perilymph_sodium_ions,
            self.dark_cell_sodium_ions,
            self.perilymph_chloride_ions,
            self.dark_cell_chloride_ions,
            self.dark_cell_atp_ions,
            self.dark_cell_water_molecules,
            self.dark_cell_adp_ions,
            self.dark_cell_hydrogen_phosphate_ions,
            self.dark_cell_protons,
            self.endolymph_protons,
            self.hair_cell_atp_ions,
            self.hair_cell_water_molecules,
            self.hair_cell_adp_ions,
            self.hair_cell_hydrogen_phosphate_ions,
            self.hair_cell_protons,
        ]
    }

    pub(crate) fn resident_bytes() -> usize {
        size_of::<Self>()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct SignedCationPartition {
    pub(crate) outward_potassium_ions: i128,
    pub(crate) outward_calcium_ions: i128,
}

impl SignedCationPartition {
    pub(crate) fn new(outward_potassium_ions: i128, outward_calcium_ions: i128) -> Self {
        Self {
            outward_potassium_ions,
            outward_calcium_ions,
        }
    }

    pub(crate) fn outward_elementary_charges(self) -> Result<i128, VestibularFluidMaterialError> {
        self.outward_potassium_ions
            .checked_add(
                self.outward_calcium_ions
                    .checked_mul(2)
                    .ok_or(VestibularFluidMaterialError::ArithmeticWidth)?,
            )
            .ok_or(VestibularFluidMaterialError::ArithmeticWidth)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct VestibularFluidTransition {
    pub(crate) predecessor: VestibularFluidMaterial,
    pub(crate) successor: VestibularFluidMaterial,
    pub(crate) apical_partition: SignedCationPartition,
    pub(crate) apical_outward_elementary_charges: i128,
    pub(crate) hair_basolateral_outward_potassium_ions: i128,
    pub(crate) dark_na_k_atpase_forward_cycles: i128,
    pub(crate) dark_nkcc1_inward_cycles: i128,
    pub(crate) dark_apical_outward_potassium_ions: i128,
    pub(crate) hair_bundle_pmca_forward_cycles: i128,
    pub(crate) hair_bundle_pmca_outward_elementary_charges: i128,
    pub(crate) resident_state_bytes: usize,
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn settle_vestibular_fluid_material(
    predecessor: VestibularFluidMaterial,
    apical_outward_elementary_charges: i128,
    apical_partition: SignedCationPartition,
    hair_basolateral_outward_potassium_ions: i128,
    dark_na_k_atpase_forward_cycles: i128,
    dark_nkcc1_inward_cycles: i128,
    dark_apical_outward_potassium_ions: i128,
    hair_bundle_pmca_forward_cycles: i128,
) -> Result<VestibularFluidTransition, VestibularFluidMaterialError> {
    if apical_partition.outward_elementary_charges()? != apical_outward_elementary_charges {
        return Err(VestibularFluidMaterialError::ChargePartitionMismatch);
    }

    let pump_twice = checked_mul(dark_na_k_atpase_forward_cycles, 2)?;
    let pump_thrice = checked_mul(dark_na_k_atpase_forward_cycles, 3)?;
    let nkcc_twice = checked_mul(dark_nkcc1_inward_cycles, 2)?;
    let pmca_twice = checked_mul(hair_bundle_pmca_forward_cycles, 2)?;

    let endolymph_potassium_delta = checked_add(
        apical_partition.outward_potassium_ions,
        dark_apical_outward_potassium_ions,
    )?;
    let hair_cell_potassium_delta = checked_sub(
        checked_neg(apical_partition.outward_potassium_ions)?,
        hair_basolateral_outward_potassium_ions,
    )?;
    let perilymph_potassium_delta = checked_sub(
        checked_sub(hair_basolateral_outward_potassium_ions, pump_twice)?,
        dark_nkcc1_inward_cycles,
    )?;
    let dark_cell_potassium_delta = checked_sub(
        checked_add(pump_twice, dark_nkcc1_inward_cycles)?,
        dark_apical_outward_potassium_ions,
    )?;
    let endolymph_calcium_delta = checked_add(
        apical_partition.outward_calcium_ions,
        hair_bundle_pmca_forward_cycles,
    )?;
    let hair_cell_calcium_delta = checked_sub(
        checked_neg(apical_partition.outward_calcium_ions)?,
        hair_bundle_pmca_forward_cycles,
    )?;
    let perilymph_sodium_delta = checked_sub(pump_thrice, dark_nkcc1_inward_cycles)?;
    let dark_cell_sodium_delta = checked_add(checked_neg(pump_thrice)?, dark_nkcc1_inward_cycles)?;
    let perilymph_chloride_delta = checked_neg(nkcc_twice)?;

    let successor = VestibularFluidMaterial {
        endolymph_potassium_ions: apply_signed_delta(
            predecessor.endolymph_potassium_ions,
            endolymph_potassium_delta,
            VestibularMaterialPool::EndolymphPotassium,
        )?,
        hair_cell_potassium_ions: apply_signed_delta(
            predecessor.hair_cell_potassium_ions,
            hair_cell_potassium_delta,
            VestibularMaterialPool::HairCellPotassium,
        )?,
        perilymph_potassium_ions: apply_signed_delta(
            predecessor.perilymph_potassium_ions,
            perilymph_potassium_delta,
            VestibularMaterialPool::PerilymphPotassium,
        )?,
        dark_cell_potassium_ions: apply_signed_delta(
            predecessor.dark_cell_potassium_ions,
            dark_cell_potassium_delta,
            VestibularMaterialPool::DarkCellPotassium,
        )?,
        endolymph_calcium_ions: apply_signed_delta(
            predecessor.endolymph_calcium_ions,
            endolymph_calcium_delta,
            VestibularMaterialPool::EndolymphCalcium,
        )?,
        hair_cell_calcium_ions: apply_signed_delta(
            predecessor.hair_cell_calcium_ions,
            hair_cell_calcium_delta,
            VestibularMaterialPool::HairCellCalcium,
        )?,
        perilymph_sodium_ions: apply_signed_delta(
            predecessor.perilymph_sodium_ions,
            perilymph_sodium_delta,
            VestibularMaterialPool::PerilymphSodium,
        )?,
        dark_cell_sodium_ions: apply_signed_delta(
            predecessor.dark_cell_sodium_ions,
            dark_cell_sodium_delta,
            VestibularMaterialPool::DarkCellSodium,
        )?,
        perilymph_chloride_ions: apply_signed_delta(
            predecessor.perilymph_chloride_ions,
            perilymph_chloride_delta,
            VestibularMaterialPool::PerilymphChloride,
        )?,
        dark_cell_chloride_ions: apply_signed_delta(
            predecessor.dark_cell_chloride_ions,
            nkcc_twice,
            VestibularMaterialPool::DarkCellChloride,
        )?,
        dark_cell_atp_ions: apply_signed_delta(
            predecessor.dark_cell_atp_ions,
            checked_neg(dark_na_k_atpase_forward_cycles)?,
            VestibularMaterialPool::DarkCellAtp,
        )?,
        dark_cell_water_molecules: apply_signed_delta(
            predecessor.dark_cell_water_molecules,
            checked_neg(dark_na_k_atpase_forward_cycles)?,
            VestibularMaterialPool::DarkCellWater,
        )?,
        dark_cell_adp_ions: apply_signed_delta(
            predecessor.dark_cell_adp_ions,
            dark_na_k_atpase_forward_cycles,
            VestibularMaterialPool::DarkCellAdp,
        )?,
        dark_cell_hydrogen_phosphate_ions: apply_signed_delta(
            predecessor.dark_cell_hydrogen_phosphate_ions,
            dark_na_k_atpase_forward_cycles,
            VestibularMaterialPool::DarkCellHydrogenPhosphate,
        )?,
        dark_cell_protons: apply_signed_delta(
            predecessor.dark_cell_protons,
            dark_na_k_atpase_forward_cycles,
            VestibularMaterialPool::DarkCellProton,
        )?,
        endolymph_protons: apply_signed_delta(
            predecessor.endolymph_protons,
            checked_neg(hair_bundle_pmca_forward_cycles)?,
            VestibularMaterialPool::EndolymphProton,
        )?,
        hair_cell_atp_ions: apply_signed_delta(
            predecessor.hair_cell_atp_ions,
            checked_neg(hair_bundle_pmca_forward_cycles)?,
            VestibularMaterialPool::HairCellAtp,
        )?,
        hair_cell_water_molecules: apply_signed_delta(
            predecessor.hair_cell_water_molecules,
            checked_neg(hair_bundle_pmca_forward_cycles)?,
            VestibularMaterialPool::HairCellWater,
        )?,
        hair_cell_adp_ions: apply_signed_delta(
            predecessor.hair_cell_adp_ions,
            hair_bundle_pmca_forward_cycles,
            VestibularMaterialPool::HairCellAdp,
        )?,
        hair_cell_hydrogen_phosphate_ions: apply_signed_delta(
            predecessor.hair_cell_hydrogen_phosphate_ions,
            hair_bundle_pmca_forward_cycles,
            VestibularMaterialPool::HairCellHydrogenPhosphate,
        )?,
        hair_cell_protons: apply_signed_delta(
            predecessor.hair_cell_protons,
            pmca_twice,
            VestibularMaterialPool::HairCellProton,
        )?,
    };

    Ok(VestibularFluidTransition {
        predecessor,
        successor,
        apical_partition,
        apical_outward_elementary_charges,
        hair_basolateral_outward_potassium_ions,
        dark_na_k_atpase_forward_cycles,
        dark_nkcc1_inward_cycles,
        dark_apical_outward_potassium_ions,
        hair_bundle_pmca_forward_cycles,
        hair_bundle_pmca_outward_elementary_charges: hair_bundle_pmca_forward_cycles,
        resident_state_bytes: VestibularFluidMaterial::resident_bytes(),
    })
}

fn checked_add(left: i128, right: i128) -> Result<i128, VestibularFluidMaterialError> {
    left.checked_add(right)
        .ok_or(VestibularFluidMaterialError::ArithmeticWidth)
}

fn checked_sub(left: i128, right: i128) -> Result<i128, VestibularFluidMaterialError> {
    left.checked_sub(right)
        .ok_or(VestibularFluidMaterialError::ArithmeticWidth)
}

fn checked_mul(value: i128, factor: i128) -> Result<i128, VestibularFluidMaterialError> {
    value
        .checked_mul(factor)
        .ok_or(VestibularFluidMaterialError::ArithmeticWidth)
}

fn checked_neg(value: i128) -> Result<i128, VestibularFluidMaterialError> {
    value
        .checked_neg()
        .ok_or(VestibularFluidMaterialError::ArithmeticWidth)
}

fn apply_signed_delta(
    predecessor: u128,
    delta: i128,
    pool: VestibularMaterialPool,
) -> Result<u128, VestibularFluidMaterialError> {
    if delta < 0 {
        predecessor
            .checked_sub(delta.unsigned_abs())
            .ok_or(VestibularFluidMaterialError::InsufficientMaterial(pool))
    } else {
        predecessor
            .checked_add(delta as u128)
            .ok_or(VestibularFluidMaterialError::ArithmeticWidth)
    }
}

pub(crate) fn encode_vestibular_fluid_material(
    state: VestibularFluidMaterial,
) -> [u8; CODEC_BYTES] {
    let mut output = [0_u8; CODEC_BYTES];
    for (index, value) in state.quantities().into_iter().enumerate() {
        let start = index * size_of::<u128>();
        output[start..start + size_of::<u128>()].copy_from_slice(&value.to_le_bytes());
    }
    output
}

pub(crate) fn decode_vestibular_fluid_material(
    encoded: &[u8],
) -> Result<VestibularFluidMaterial, VestibularFluidMaterialError> {
    if encoded.len() != CODEC_BYTES {
        return Err(VestibularFluidMaterialError::InvalidRestart);
    }
    let mut values = [0_u128; MATERIAL_QUANTITY_COUNT];
    for (index, value) in values.iter_mut().enumerate() {
        let start = index * size_of::<u128>();
        *value = u128::from_le_bytes(
            encoded[start..start + size_of::<u128>()]
                .try_into()
                .map_err(|_| VestibularFluidMaterialError::InvalidRestart)?,
        );
    }
    Ok(VestibularFluidMaterial::new(
        values[0], values[1], values[2], values[3], values[4], values[5], values[6], values[7],
        values[8], values[9], values[10], values[11], values[12], values[13], values[14],
        values[15], values[16], values[17], values[18], values[19], values[20],
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::elementary_charge_membrane::MembraneCapacitance;
    use crate::exact_rational::ExactRational;
    use crate::local_membrane_conductance_balance::{
        settle_local_membrane_conductances_with_active_transport, LocalConductancePath,
        LocalMembraneConductanceState,
    };

    fn material() -> VestibularFluidMaterial {
        VestibularFluidMaterial::new(
            200_000, 200_000, 200_000, 200_000, 1_000, 1_000, 200_000, 200_000, 400_000, 400_000,
            100_000, 100_000, 10_000, 10_000, 10_000, 100_000, 100_000, 100_000, 10_000, 10_000,
            10_000,
        )
    }

    fn proof_capacitance() -> MembraneCapacitance {
        MembraneCapacitance::new(ExactRational::new(801_088_317, 250_000_000).unwrap()).unwrap()
    }

    fn path(conductance: i128, reversal: i128) -> LocalConductancePath {
        LocalConductancePath::new(
            ExactRational::integer(conductance),
            ExactRational::integer(reversal),
        )
        .unwrap()
    }

    fn potassium_total(state: VestibularFluidMaterial) -> u128 {
        let q = state.quantities();
        q[0] + q[1] + q[2] + q[3]
    }

    fn calcium_total(state: VestibularFluidMaterial) -> u128 {
        let q = state.quantities();
        q[4] + q[5]
    }

    fn sodium_total(state: VestibularFluidMaterial) -> u128 {
        let q = state.quantities();
        q[6] + q[7]
    }

    fn chloride_total(state: VestibularFluidMaterial) -> u128 {
        let q = state.quantities();
        q[8] + q[9]
    }

    fn adenylate_total(state: VestibularFluidMaterial) -> u128 {
        let q = state.quantities();
        q[10] + q[12] + q[16] + q[18]
    }

    fn phosphoryl_total(state: VestibularFluidMaterial) -> u128 {
        let q = state.quantities();
        3 * q[10] + 2 * q[12] + q[13] + 3 * q[16] + 2 * q[18] + q[19]
    }

    fn signed_charge(state: VestibularFluidMaterial) -> i128 {
        let q = state.quantities();
        (q[0] + q[1] + q[2] + q[3] + 2 * q[4] + 2 * q[5] + q[6] + q[7] + q[14] + q[15] + q[20])
            as i128
            - (q[8] + q[9] + 4 * q[10] + 3 * q[12] + 2 * q[13] + 4 * q[16] + 3 * q[18] + 2 * q[19])
                as i128
    }

    #[test]
    fn exact_dark_cell_stoichiometry_closes_the_local_potassium_cycle() {
        let electrical = settle_local_membrane_conductances_with_active_transport(
            proof_capacitance(),
            LocalMembraneConductanceState::<2>::genesis(-1_000_000),
            &[path(240, 0), path(240, -100)],
            1_000,
            1,
        )
        .unwrap();
        assert_eq!(
            electrical.outward_elementary_charges_by_path,
            [-74_898, 74_898]
        );
        assert_eq!(electrical.conductive_outward_elementary_charges, 0);
        assert_eq!(electrical.active_transport_outward_elementary_charges, 1);
        assert_eq!(electrical.net_outward_elementary_charges, 1);

        let predecessor = material();
        let transition = settle_vestibular_fluid_material(
            predecessor,
            electrical.outward_elementary_charges_by_path[0],
            SignedCationPartition::new(-74_896, -1),
            electrical.outward_elementary_charges_by_path[1],
            24_966,
            24_966,
            74_898,
            1,
        )
        .unwrap();
        let q = transition.successor.quantities();

        assert_eq!(q[0..4], [200_002, 199_998, 200_000, 200_000]);
        assert_eq!(q[4..6], [1_000, 1_000]);
        assert_eq!(q[6..10], [249_932, 150_068, 350_068, 449_932]);
        assert_eq!(q[10..15], [75_034, 75_034, 34_966, 34_966, 34_966]);
        assert_eq!(q[15..21], [99_999, 99_999, 99_999, 10_001, 10_001, 10_002]);
        assert_eq!(transition.hair_bundle_pmca_outward_elementary_charges, 1);
        assert_eq!(
            potassium_total(predecessor),
            potassium_total(transition.successor)
        );
        assert_eq!(
            calcium_total(predecessor),
            calcium_total(transition.successor)
        );
        assert_eq!(
            sodium_total(predecessor),
            sodium_total(transition.successor)
        );
        assert_eq!(
            chloride_total(predecessor),
            chloride_total(transition.successor)
        );
        assert_eq!(
            adenylate_total(predecessor),
            adenylate_total(transition.successor)
        );
        assert_eq!(
            phosphoryl_total(predecessor),
            phosphoryl_total(transition.successor)
        );
        assert_eq!(
            signed_charge(predecessor),
            signed_charge(transition.successor)
        );
    }

    #[test]
    fn signed_reaction_extents_reverse_the_complete_transition() {
        let origin = material();
        let forward = settle_vestibular_fluid_material(
            origin,
            -10,
            SignedCationPartition::new(-8, -1),
            6,
            2,
            2,
            6,
            1,
        )
        .unwrap();
        let restored = settle_vestibular_fluid_material(
            forward.successor,
            10,
            SignedCationPartition::new(8, 1),
            -6,
            -2,
            -2,
            -6,
            -1,
        )
        .unwrap();
        assert_eq!(restored.successor, origin);
    }

    #[test]
    fn zero_reaction_extents_are_exactly_quiescent() {
        let predecessor = material();
        let transition = settle_vestibular_fluid_material(
            predecessor,
            0,
            SignedCationPartition::new(0, 0),
            0,
            0,
            0,
            0,
            0,
        )
        .unwrap();
        assert_eq!(transition.successor, predecessor);
    }

    #[test]
    fn mismatch_or_insufficient_material_refuses_the_whole_successor() {
        let predecessor = material();
        assert_eq!(
            settle_vestibular_fluid_material(
                predecessor,
                -10,
                SignedCationPartition::new(-10, -1),
                0,
                0,
                0,
                0,
                0,
            ),
            Err(VestibularFluidMaterialError::ChargePartitionMismatch)
        );

        let no_atp = VestibularFluidMaterial::new(
            100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 0, 100, 0, 0, 0, 100, 100, 100, 0, 0,
            0,
        );
        assert_eq!(
            settle_vestibular_fluid_material(
                no_atp,
                0,
                SignedCationPartition::new(0, 0),
                0,
                1,
                0,
                0,
                0,
            ),
            Err(VestibularFluidMaterialError::InsufficientMaterial(
                VestibularMaterialPool::DarkCellAtp
            ))
        );
        assert_eq!(no_atp.quantities()[0], 100);
    }

    #[test]
    fn restart_and_residency_are_fixed() {
        let state = material();
        let encoded = encode_vestibular_fluid_material(state);
        assert_eq!(encoded.len(), 336);
        assert_eq!(encoded.len(), VestibularFluidMaterial::resident_bytes());
        assert_eq!(decode_vestibular_fluid_material(&encoded).unwrap(), state);
        assert_eq!(
            decode_vestibular_fluid_material(&encoded[..encoded.len() - 1]),
            Err(VestibularFluidMaterialError::InvalidRestart)
        );
    }

    #[test]
    fn fixed_state_does_not_grow_with_transition_count() {
        let mut state = material();
        for _ in 0..100_000 {
            let forward = settle_vestibular_fluid_material(
                state,
                -10,
                SignedCationPartition::new(-8, -1),
                6,
                2,
                2,
                6,
                1,
            )
            .unwrap();
            let reverse = settle_vestibular_fluid_material(
                forward.successor,
                10,
                SignedCationPartition::new(8, 1),
                -6,
                -2,
                -2,
                -6,
                -1,
            )
            .unwrap();
            state = reverse.successor;
        }
        assert_eq!(state, material());
        assert_eq!(VestibularFluidMaterial::resident_bytes(), 336);
    }
}
