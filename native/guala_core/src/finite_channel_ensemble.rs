//! Minimal typed adapter from the bounded local-contact law to one finite
//! conformational ensemble.
//!
//! The generic contact primitive already performs exact settlement.  This
//! adapter adds only channel-population identity: one declared conserved
//! moiety marks every conformational species, a closed reaction must move that
//! moiety from at least one source conformation to at least one successor
//! conformation, and the complete fixed population survives canonical restart.
//!
//! No voltage, current, rate, biological coefficient, semantic channel name,
//! activation tag, scheduler, or caller-supplied extent exists here.  Contact
//! occupancy remains an explicit external geometry input.

use crate::bounded_physical_quanta::{ConservationBoundary, PhysicalLocation, QuantumError};
use crate::localized_reaction_contacts::{
    admit_disjoint_geometry_contacts, canonical_state_bytes, decode_bound_contact_state,
    encode_bound_contact_state, settle_disjoint_contacts, BoundContactState, ContactError,
    ContactTransition, ContactWorkRequirement, DisjointContactOccupancy,
    GeometryContactObservation, LocalContactAnatomy,
};
use std::mem::size_of;

const CODEC_MAGIC: [u8; 8] = *b"GCHAN001";
const CODEC_VERSION: u32 = 1;
const CODEC_HEADER_BYTES: usize = 8 + 4 + 4 + 16;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ChannelEnsembleAnatomy<const SPECIES: usize, const MOIETIES: usize> {
    local: LocalContactAnatomy<SPECIES, MOIETIES, 1>,
    population_moiety_code: u32,
    population_moiety_index: usize,
    conformations: [bool; SPECIES],
    fixed_population: u128,
}

impl<const SPECIES: usize, const MOIETIES: usize> ChannelEnsembleAnatomy<SPECIES, MOIETIES> {
    pub(crate) fn new(
        local: LocalContactAnatomy<SPECIES, MOIETIES, 1>,
        population_moiety_code: u32,
        fixed_population: u128,
    ) -> Result<Self, ChannelError> {
        if fixed_population == 0 {
            return Err(ChannelError::ZeroChannelPopulation);
        }
        let population_moiety_index = local
            .schema()
            .moiety_codes()
            .iter()
            .position(|code| *code == population_moiety_code)
            .ok_or(ChannelError::UnknownPopulationMoiety)?;
        let mut conformations = [false; SPECIES];
        let mut conformation_count = 0_usize;
        for (species, definition) in local.schema().species().iter().enumerate() {
            match definition.conserved_moieties()[population_moiety_index] {
                0 => {}
                1 => {
                    conformations[species] = true;
                    conformation_count = conformation_count
                        .checked_add(1)
                        .ok_or(ChannelError::ResourceArithmeticOverflow)?;
                }
                _ => return Err(ChannelError::NonUnitPopulationMoiety { species }),
            }
        }
        if conformation_count < 2 {
            return Err(ChannelError::InsufficientConformationalSpecies);
        }
        let lane = &local.lanes()[0];
        if lane.conservation_boundary() != ConservationBoundary::Closed {
            return Err(ChannelError::ChannelPopulationBoundaryIsOpen);
        }
        let mut source_conformation = false;
        let mut successor_conformation = false;
        for species in 0..SPECIES {
            if conformations[species] && lane.coefficients()[species] < 0 {
                source_conformation = true;
            }
            if conformations[species] && lane.coefficients()[species] > 0 {
                successor_conformation = true;
            }
        }
        if !source_conformation || !successor_conformation {
            return Err(ChannelError::ReactionDoesNotChangeConformation);
        }
        Ok(Self {
            local,
            population_moiety_code,
            population_moiety_index,
            conformations,
            fixed_population,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ChannelEnsembleState<const SPECIES: usize, const MOIETIES: usize> {
    bound: BoundContactState<SPECIES, MOIETIES, 1>,
    population_moiety_code: u32,
    population_moiety_index: usize,
    conformations: [bool; SPECIES],
    fixed_population: u128,
}

impl<const SPECIES: usize, const MOIETIES: usize> ChannelEnsembleState<SPECIES, MOIETIES> {
    pub(crate) fn new(
        anatomy: ChannelEnsembleAnatomy<SPECIES, MOIETIES>,
        interval_index: u128,
        quantities: [u128; SPECIES],
        remainder: u128,
    ) -> Result<Self, ChannelError> {
        let bound =
            BoundContactState::new(anatomy.local, interval_index, [quantities], [remainder])?;
        Self::from_bound(
            bound,
            anatomy.population_moiety_code,
            anatomy.population_moiety_index,
            anatomy.conformations,
            anatomy.fixed_population,
        )
    }

    fn from_bound(
        bound: BoundContactState<SPECIES, MOIETIES, 1>,
        population_moiety_code: u32,
        population_moiety_index: usize,
        conformations: [bool; SPECIES],
        fixed_population: u128,
    ) -> Result<Self, ChannelError> {
        let population = population_of(&bound.quantities()[0], &conformations)?;
        if population != fixed_population {
            return Err(ChannelError::FixedPopulationMismatch {
                expected: fixed_population,
                actual: population,
            });
        }
        Ok(Self {
            bound,
            population_moiety_code,
            population_moiety_index,
            conformations,
            fixed_population,
        })
    }

    pub(crate) fn quantities(&self) -> &[u128; SPECIES] {
        &self.bound.quantities()[0]
    }

    pub(crate) fn remainder(&self) -> u128 {
        self.bound.remainders()[0]
    }

    pub(crate) fn interval_index(&self) -> u128 {
        self.bound.interval_index()
    }

    pub(crate) fn physical_location(&self) -> PhysicalLocation {
        self.bound.anatomy().lanes()[0].location()
    }

    pub(crate) fn fixed_population(&self) -> u128 {
        self.fixed_population
    }

    pub(crate) fn population_moiety_code(&self) -> u32 {
        self.population_moiety_code
    }

    pub(crate) fn is_conformation(&self, species: usize) -> Option<bool> {
        self.conformations.get(species).copied()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExternalChannelContact<const SPECIES: usize> {
    occupied_reactants: [u128; SPECIES],
}

impl<const SPECIES: usize> ExternalChannelContact<SPECIES> {
    pub(crate) fn new(occupied_reactants: [u128; SPECIES]) -> Self {
        Self { occupied_reactants }
    }

    pub(crate) fn occupied_reactants(&self) -> &[u128; SPECIES] {
        &self.occupied_reactants
    }
}

pub(crate) struct AdmittedChannelContact<
    'a,
    const SPECIES: usize,
    const MOIETIES: usize,
    const CONTACTS: usize,
> {
    predecessor: &'a ChannelEnsembleState<SPECIES, MOIETIES>,
    contact: DisjointContactOccupancy<'a, SPECIES, MOIETIES, 1, CONTACTS>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ChannelEnsembleTransition<const SPECIES: usize, const MOIETIES: usize> {
    pub(crate) successor: ChannelEnsembleState<SPECIES, MOIETIES>,
    pub(crate) extent: u128,
    pub(crate) contact_requirement: ContactWorkRequirement,
    pub(crate) adapter_resident_payload_bytes: usize,
    pub(crate) canonical_serialized_bytes: usize,
}

pub(crate) fn admit_external_channel_contact<'a, const SPECIES: usize, const MOIETIES: usize>(
    predecessor: &'a ChannelEnsembleState<SPECIES, MOIETIES>,
    external: ExternalChannelContact<SPECIES>,
) -> Result<AdmittedChannelContact<'a, SPECIES, MOIETIES, 1>, ChannelError> {
    let observation = GeometryContactObservation::new(
        predecessor.bound.anatomy().lanes()[0].location(),
        predecessor.bound.anatomy().interval(),
        predecessor.bound.interval_index(),
        external.occupied_reactants,
    );
    Ok(AdmittedChannelContact {
        predecessor,
        contact: admit_disjoint_geometry_contacts(&predecessor.bound, [observation])?,
    })
}

pub(crate) fn admit_absent_channel_contact<const SPECIES: usize, const MOIETIES: usize>(
    predecessor: &ChannelEnsembleState<SPECIES, MOIETIES>,
) -> Result<AdmittedChannelContact<'_, SPECIES, MOIETIES, 0>, ChannelError> {
    Ok(AdmittedChannelContact {
        predecessor,
        contact: admit_disjoint_geometry_contacts(&predecessor.bound, [])?,
    })
}

pub(crate) fn settle_channel_interval<
    const SPECIES: usize,
    const MOIETIES: usize,
    const CONTACTS: usize,
>(
    admitted: AdmittedChannelContact<'_, SPECIES, MOIETIES, CONTACTS>,
) -> Result<ChannelEnsembleTransition<SPECIES, MOIETIES>, ChannelError> {
    let ContactTransition {
        successor,
        extents_by_lane,
        requirement,
    } = settle_disjoint_contacts(admitted.contact)?;
    // Population conservation was admitted structurally by the closed generic
    // reaction. Recounting it here would turn validation into hot-path
    // dynamics, so the immutable binding is carried without another scan.
    let successor = ChannelEnsembleState {
        bound: successor,
        population_moiety_code: admitted.predecessor.population_moiety_code,
        population_moiety_index: admitted.predecessor.population_moiety_index,
        conformations: admitted.predecessor.conformations,
        fixed_population: admitted.predecessor.fixed_population,
    };
    Ok(ChannelEnsembleTransition {
        successor,
        extent: extents_by_lane[0],
        contact_requirement: requirement,
        adapter_resident_payload_bytes: size_of::<ChannelEnsembleState<SPECIES, MOIETIES>>(),
        canonical_serialized_bytes: canonical_channel_state_bytes::<SPECIES, MOIETIES>()?,
    })
}

pub(crate) fn canonical_channel_state_bytes<const SPECIES: usize, const MOIETIES: usize>(
) -> Result<usize, ChannelError> {
    CODEC_HEADER_BYTES
        .checked_add(canonical_state_bytes::<SPECIES, MOIETIES, 1>()?)
        .ok_or(ChannelError::ResourceArithmeticOverflow)
}

pub(crate) fn encode_channel_state<const SPECIES: usize, const MOIETIES: usize>(
    state: &ChannelEnsembleState<SPECIES, MOIETIES>,
    output: &mut [u8],
) -> Result<usize, ChannelError> {
    let required = canonical_channel_state_bytes::<SPECIES, MOIETIES>()?;
    if output.len() != required {
        return Err(ChannelError::CodecLengthMismatch {
            expected: required,
            actual: output.len(),
        });
    }
    output[0..8].copy_from_slice(&CODEC_MAGIC);
    output[8..12].copy_from_slice(&CODEC_VERSION.to_le_bytes());
    output[12..16].copy_from_slice(&state.population_moiety_code.to_le_bytes());
    output[16..32].copy_from_slice(&state.fixed_population.to_le_bytes());
    encode_bound_contact_state(&state.bound, &mut output[CODEC_HEADER_BYTES..])?;
    Ok(required)
}

pub(crate) fn decode_channel_state<const SPECIES: usize, const MOIETIES: usize>(
    input: &[u8],
) -> Result<ChannelEnsembleState<SPECIES, MOIETIES>, ChannelError> {
    let required = canonical_channel_state_bytes::<SPECIES, MOIETIES>()?;
    if input.len() != required {
        return Err(ChannelError::CodecLengthMismatch {
            expected: required,
            actual: input.len(),
        });
    }
    if input[0..8] != CODEC_MAGIC || read_u32(&input[8..12])? != CODEC_VERSION {
        return Err(ChannelError::CodecHeaderMismatch);
    }
    let population_moiety_code = read_u32(&input[12..16])?;
    let fixed_population = read_u128(&input[16..32])?;
    let bound = decode_bound_contact_state::<SPECIES, MOIETIES, 1>(&input[CODEC_HEADER_BYTES..])?;
    let anatomy =
        ChannelEnsembleAnatomy::new(*bound.anatomy(), population_moiety_code, fixed_population)?;
    ChannelEnsembleState::from_bound(
        bound,
        anatomy.population_moiety_code,
        anatomy.population_moiety_index,
        anatomy.conformations,
        anatomy.fixed_population,
    )
}

fn population_of<const SPECIES: usize>(
    quantities: &[u128; SPECIES],
    conformations: &[bool; SPECIES],
) -> Result<u128, ChannelError> {
    let mut population = 0_u128;
    for species in 0..SPECIES {
        if conformations[species] {
            population = population
                .checked_add(quantities[species])
                .ok_or(ChannelError::PopulationArithmeticOverflow)?;
        }
    }
    Ok(population)
}

fn read_u32(input: &[u8]) -> Result<u32, ChannelError> {
    let bytes: [u8; 4] = input
        .try_into()
        .map_err(|_| ChannelError::CodecHeaderMismatch)?;
    Ok(u32::from_le_bytes(bytes))
}

fn read_u128(input: &[u8]) -> Result<u128, ChannelError> {
    let bytes: [u8; 16] = input
        .try_into()
        .map_err(|_| ChannelError::CodecHeaderMismatch)?;
    Ok(u128::from_le_bytes(bytes))
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ChannelError {
    Quantum(QuantumError),
    Contact(ContactError),
    ZeroChannelPopulation,
    UnknownPopulationMoiety,
    NonUnitPopulationMoiety { species: usize },
    InsufficientConformationalSpecies,
    ChannelPopulationBoundaryIsOpen,
    ReactionDoesNotChangeConformation,
    FixedPopulationMismatch { expected: u128, actual: u128 },
    PopulationArithmeticOverflow,
    ResourceArithmeticOverflow,
    CodecLengthMismatch { expected: usize, actual: usize },
    CodecHeaderMismatch,
}

impl From<QuantumError> for ChannelError {
    fn from(value: QuantumError) -> Self {
        Self::Quantum(value)
    }
}

impl From<ContactError> for ChannelError {
    fn from(value: ContactError) -> Self {
        Self::Contact(value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::bounded_physical_quanta::{
        AdmittedContactLaneAnatomy, CompartmentSide, ExactInterval, ExactUnit, FractionLaw,
        PhysicalDimension, PhysicalLocation, SpeciesDefinition, SpeciesSchema,
    };

    const CHANNEL_MOIETY: u32 = 701;
    const LIGAND_MOIETY: u32 = 702;

    fn interval() -> ExactInterval {
        ExactInterval::new(1, 1_000, 31).unwrap()
    }

    fn schema(bound_has_ligand: bool) -> SpeciesSchema<3, 2> {
        let unit = ExactUnit::new(PhysicalDimension::MoleculeCount, 1, 1).unwrap();
        SpeciesSchema::new(
            [CHANNEL_MOIETY, LIGAND_MOIETY],
            [
                SpeciesDefinition::new(101, unit, 0, [1, 0]).unwrap(),
                SpeciesDefinition::new(102, unit, 0, [0, 1]).unwrap(),
                SpeciesDefinition::new(103, unit, 0, [1, u64::from(bound_has_ligand)]).unwrap(),
            ],
        )
        .unwrap()
    }

    fn anatomy(capacity: u128, fraction: FractionLaw) -> ChannelEnsembleAnatomy<3, 2> {
        let schema = schema(true);
        let lane = AdmittedContactLaneAnatomy::new(
            &schema,
            PhysicalLocation::new(1, 2, CompartmentSide::MembraneOuter, 3, 4, 5).unwrap(),
            interval(),
            [capacity, capacity, capacity],
            [capacity, capacity, 0],
            [-1, -1, 1],
            fraction,
            ConservationBoundary::Closed,
        )
        .unwrap();
        ChannelEnsembleAnatomy::new(
            LocalContactAnatomy::new(schema, interval(), [lane]).unwrap(),
            CHANNEL_MOIETY,
            capacity,
        )
        .unwrap()
    }

    fn state(population: u128, fraction: FractionLaw) -> ChannelEnsembleState<3, 2> {
        ChannelEnsembleState::new(
            anatomy(population, fraction),
            0,
            [population, population, 0],
            0,
        )
        .unwrap()
    }

    fn contact(state: &ChannelEnsembleState<3, 2>) -> ExternalChannelContact<3> {
        ExternalChannelContact::new([state.quantities()[0], state.quantities()[1], 0])
    }

    #[test]
    fn one_three_and_nine_member_ensembles_conserve_population() {
        for population in [1_u128, 3, 9] {
            let prior = state(population, FractionLaw::new(1, 1).unwrap());
            let transition = settle_channel_interval(
                admit_external_channel_contact(&prior, contact(&prior)).unwrap(),
            )
            .unwrap();
            assert_eq!(transition.extent, population);
            assert_eq!(transition.successor.quantities(), &[0, 0, population]);
            assert_eq!(transition.successor.fixed_population(), population);
            assert_eq!(transition.successor.interval_index(), 1);
            assert_eq!(
                transition.successor.population_moiety_code(),
                CHANNEL_MOIETY
            );
            assert_eq!(transition.successor.is_conformation(0), Some(true));
            assert_eq!(transition.successor.is_conformation(1), Some(false));
            assert_eq!(transition.successor.is_conformation(2), Some(true));
        }
    }

    #[test]
    fn finite_ligand_reservoir_reaches_material_quiescence() {
        let anatomy = anatomy(9, FractionLaw::new(1, 3).unwrap());
        let mut current = ChannelEnsembleState::new(anatomy, 0, [9, 2, 0], 0).unwrap();
        let mut total_extent = 0_u128;
        for _ in 0..30 {
            let external = contact(&current);
            let transition = settle_channel_interval(
                admit_external_channel_contact(&current, external).unwrap(),
            )
            .unwrap();
            total_extent += transition.extent;
            current = transition.successor;
        }
        assert_eq!(total_extent, 2);
        assert_eq!(current.quantities(), &[7, 0, 2]);
        let settled = *current.quantities();
        let remainder = current.remainder();
        for _ in 0..100 {
            let transition = settle_channel_interval(
                admit_external_channel_contact(&current, contact(&current)).unwrap(),
            )
            .unwrap();
            assert_eq!(transition.extent, 0);
            assert_eq!(transition.successor.quantities(), &settled);
            assert_eq!(transition.successor.remainder(), remainder);
            current = transition.successor;
        }
    }

    #[test]
    fn absent_external_contact_has_no_conformational_settlement() {
        let prior = state(3, FractionLaw::new(1, 3).unwrap());
        let transition =
            settle_channel_interval(admit_absent_channel_contact(&prior).unwrap()).unwrap();
        assert_eq!(transition.extent, 0);
        assert_eq!(transition.successor.quantities(), prior.quantities());
        assert_eq!(transition.successor.remainder(), prior.remainder());
        assert_eq!(transition.contact_requirement.observations, 0);
        assert_eq!(transition.contact_requirement.fraction_settlements, 0);
    }

    #[test]
    fn canonical_restart_preserves_fractional_cause_and_identity() {
        let prior = state(3, FractionLaw::new(1, 3).unwrap());
        let first = settle_channel_interval(
            admit_external_channel_contact(&prior, contact(&prior)).unwrap(),
        )
        .unwrap()
        .successor;
        let required = canonical_channel_state_bytes::<3, 2>().unwrap();
        let mut bytes = [0_u8; 2_048];
        encode_channel_state(&first, &mut bytes[..required]).unwrap();
        let restored = decode_channel_state::<3, 2>(&bytes[..required]).unwrap();
        assert_eq!(restored, first);
        let uninterrupted = settle_channel_interval(
            admit_external_channel_contact(&first, contact(&first)).unwrap(),
        )
        .unwrap();
        let restarted = settle_channel_interval(
            admit_external_channel_contact(&restored, contact(&restored)).unwrap(),
        )
        .unwrap();
        assert_eq!(restarted, uninterrupted);
    }

    #[test]
    fn incomplete_ligand_or_channel_conservation_is_refused() {
        let incomplete = schema(false);
        let ligand_loss = AdmittedContactLaneAnatomy::new(
            &incomplete,
            PhysicalLocation::new(1, 2, CompartmentSide::MembraneOuter, 3, 4, 5).unwrap(),
            interval(),
            [9, 9, 9],
            [9, 9, 0],
            [-1, -1, 1],
            FractionLaw::new(1, 1).unwrap(),
            ConservationBoundary::Closed,
        );
        assert_eq!(
            ligand_loss,
            Err(QuantumError::MoietyConservationMismatch { moiety: 1 })
        );

        let unit = ExactUnit::new(PhysicalDimension::MoleculeCount, 1, 1).unwrap();
        let missing_channel = SpeciesSchema::new(
            [CHANNEL_MOIETY, LIGAND_MOIETY],
            [
                SpeciesDefinition::new(101, unit, 0, [1, 0]).unwrap(),
                SpeciesDefinition::new(102, unit, 0, [0, 1]).unwrap(),
                SpeciesDefinition::new(103, unit, 0, [0, 1]).unwrap(),
            ],
        )
        .unwrap();
        let channel_loss = AdmittedContactLaneAnatomy::new(
            &missing_channel,
            PhysicalLocation::new(1, 2, CompartmentSide::MembraneOuter, 3, 4, 5).unwrap(),
            interval(),
            [9, 9, 9],
            [9, 9, 0],
            [-1, -1, 1],
            FractionLaw::new(1, 1).unwrap(),
            ConservationBoundary::Closed,
        );
        assert_eq!(
            channel_loss,
            Err(QuantumError::MoietyConservationMismatch { moiety: 0 })
        );
    }

    #[test]
    fn fixed_width_and_work_remain_constant_for_long_external_operation() {
        let population = 1_000_000_000_000_u128;
        let mut current = state(population, FractionLaw::new(1, 1_000_000_000_000).unwrap());
        let width = size_of::<ChannelEnsembleState<3, 2>>();
        let mut expected_work: Option<ContactWorkRequirement> = None;
        let mut active = 0_usize;
        for _ in 0..100_000 {
            let transition = settle_channel_interval(
                admit_external_channel_contact(&current, contact(&current)).unwrap(),
            )
            .unwrap();
            if transition.extent > 0 {
                active += 1;
            }
            if let Some(expected) = expected_work {
                assert_eq!(transition.contact_requirement, expected);
            } else {
                expected_work = Some(transition.contact_requirement);
            }
            assert_eq!(transition.adapter_resident_payload_bytes, width);
            assert_eq!(
                transition.canonical_serialized_bytes,
                canonical_channel_state_bytes::<3, 2>().unwrap()
            );
            current = transition.successor;
            assert_eq!(size_of_val(&current), width);
            assert_eq!(current.fixed_population(), population);
        }
        assert!(active > 1_000);
        assert!(current.quantities()[0] > 0);
    }

    #[test]
    fn external_contact_is_occupancy_not_extent() {
        let value = ExternalChannelContact::new([3, 2, 0]);
        assert_eq!(value.occupied_reactants(), &[3, 2, 0]);
    }

    #[test]
    fn codec_rejects_population_identity_tampering() {
        let state = state(3, FractionLaw::new(1, 3).unwrap());
        let required = canonical_channel_state_bytes::<3, 2>().unwrap();
        let mut bytes = [0_u8; 2_048];
        encode_channel_state(&state, &mut bytes[..required]).unwrap();
        bytes[12..16].copy_from_slice(&999_u32.to_le_bytes());
        assert_eq!(
            decode_channel_state::<3, 2>(&bytes[..required]),
            Err(ChannelError::UnknownPopulationMoiety)
        );
    }

    #[test]
    fn codec_rejects_fixed_population_tampering() {
        let state = state(3, FractionLaw::new(1, 3).unwrap());
        let required = canonical_channel_state_bytes::<3, 2>().unwrap();
        let mut bytes = [0_u8; 2_048];
        encode_channel_state(&state, &mut bytes[..required]).unwrap();
        bytes[16..32].copy_from_slice(&4_u128.to_le_bytes());
        assert_eq!(
            decode_channel_state::<3, 2>(&bytes[..required]),
            Err(ChannelError::FixedPopulationMismatch {
                expected: 4,
                actual: 3,
            })
        );
    }

    #[test]
    fn anatomy_rejects_open_population_boundary() {
        let schema = schema(true);
        let lane = AdmittedContactLaneAnatomy::new(
            &schema,
            PhysicalLocation::new(1, 2, CompartmentSide::MembraneOuter, 3, 4, 5).unwrap(),
            interval(),
            [9, 9, 9],
            [9, 9, 0],
            [-1, -1, 1],
            FractionLaw::new(1, 1).unwrap(),
            ConservationBoundary::ExplicitOpen(crate::bounded_physical_quanta::BoundaryFlux::new(
                0,
                [0, 0],
            )),
        )
        .unwrap();
        assert_eq!(
            ChannelEnsembleAnatomy::new(
                LocalContactAnatomy::new(schema, interval(), [lane]).unwrap(),
                CHANNEL_MOIETY,
                9,
            ),
            Err(ChannelError::ChannelPopulationBoundaryIsOpen)
        );
    }
}
