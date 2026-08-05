//! Anatomy-bound fixed-width physical contact arithmetic.
//!
//! This module contains the scalar and one-lane laws used by
//! `localized_reaction_contacts`.  It is intentionally unmounted.  It does not
//! discover geometry, schedule reactions, evaluate DSF, or make a cognitive
//! claim.  Every admitted lane carries its complete species schema, location,
//! interval, stoichiometry, conservation boundary, capacity, contact limit,
//! fractional law, and derived integer-width proof.

use std::mem::size_of;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub(crate) enum PhysicalDimension {
    MoleculeCount = 1,
    ChargeQuantum = 2,
    VesicleCount = 3,
    ReceptorSiteCount = 4,
    IonCount = 5,
    VolumeQuantum = 6,
    AreaQuantum = 7,
}

impl PhysicalDimension {
    pub(crate) fn from_code(code: u8) -> Result<Self, QuantumError> {
        match code {
            1 => Ok(Self::MoleculeCount),
            2 => Ok(Self::ChargeQuantum),
            3 => Ok(Self::VesicleCount),
            4 => Ok(Self::ReceptorSiteCount),
            5 => Ok(Self::IonCount),
            6 => Ok(Self::VolumeQuantum),
            7 => Ok(Self::AreaQuantum),
            _ => Err(QuantumError::UnknownPhysicalDimension),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExactUnit {
    dimension: PhysicalDimension,
    numerator: u128,
    denominator: u128,
}

impl ExactUnit {
    pub(crate) fn new(
        dimension: PhysicalDimension,
        numerator: u128,
        denominator: u128,
    ) -> Result<Self, QuantumError> {
        if numerator == 0 || denominator == 0 {
            return Err(QuantumError::ZeroUnitScale);
        }
        if gcd(numerator, denominator) != 1 {
            return Err(QuantumError::NonCanonicalRatio);
        }
        Ok(Self {
            dimension,
            numerator,
            denominator,
        })
    }

    pub(crate) fn dimension(&self) -> PhysicalDimension {
        self.dimension
    }

    pub(crate) fn numerator(&self) -> u128 {
        self.numerator
    }

    pub(crate) fn denominator(&self) -> u128 {
        self.denominator
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct SpeciesDefinition<const MOIETIES: usize> {
    code: u32,
    unit: ExactUnit,
    charge_per_quantum: i64,
    conserved_moieties: [u64; MOIETIES],
}

impl<const MOIETIES: usize> SpeciesDefinition<MOIETIES> {
    pub(crate) fn new(
        code: u32,
        unit: ExactUnit,
        charge_per_quantum: i64,
        conserved_moieties: [u64; MOIETIES],
    ) -> Result<Self, QuantumError> {
        if code == 0 {
            return Err(QuantumError::ZeroSpeciesCode);
        }
        Ok(Self {
            code,
            unit,
            charge_per_quantum,
            conserved_moieties,
        })
    }

    pub(crate) fn code(&self) -> u32 {
        self.code
    }

    pub(crate) fn unit(&self) -> ExactUnit {
        self.unit
    }

    pub(crate) fn charge_per_quantum(&self) -> i64 {
        self.charge_per_quantum
    }

    pub(crate) fn conserved_moieties(&self) -> &[u64; MOIETIES] {
        &self.conserved_moieties
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct SpeciesSchema<const SPECIES: usize, const MOIETIES: usize> {
    moiety_codes: [u32; MOIETIES],
    species: [SpeciesDefinition<MOIETIES>; SPECIES],
}

impl<const SPECIES: usize, const MOIETIES: usize> SpeciesSchema<SPECIES, MOIETIES> {
    pub(crate) fn new(
        moiety_codes: [u32; MOIETIES],
        species: [SpeciesDefinition<MOIETIES>; SPECIES],
    ) -> Result<Self, QuantumError> {
        if SPECIES == 0 {
            return Err(QuantumError::EmptySpeciesSet);
        }
        for index in 0..MOIETIES {
            if moiety_codes[index] == 0 {
                return Err(QuantumError::ZeroMoietyCode);
            }
            if index > 0 && moiety_codes[index] < moiety_codes[index - 1] {
                return Err(QuantumError::NonCanonicalMoietyOrder);
            }
            for prior in 0..index {
                if moiety_codes[index] == moiety_codes[prior] {
                    return Err(QuantumError::DuplicateMoietyCode);
                }
            }
        }
        for index in 0..SPECIES {
            if index > 0 && species[index].code < species[index - 1].code {
                return Err(QuantumError::NonCanonicalSpeciesOrder);
            }
            for prior in 0..index {
                if species[index].code == species[prior].code {
                    return Err(QuantumError::DuplicateSpeciesCode);
                }
            }
        }
        Ok(Self {
            moiety_codes,
            species,
        })
    }

    pub(crate) fn moiety_codes(&self) -> &[u32; MOIETIES] {
        &self.moiety_codes
    }

    pub(crate) fn species(&self) -> &[SpeciesDefinition<MOIETIES>; SPECIES] {
        &self.species
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ExactInterval {
    numerator: u128,
    denominator: u128,
    phase_code: u32,
}

impl ExactInterval {
    pub(crate) fn new(
        numerator: u128,
        denominator: u128,
        phase_code: u32,
    ) -> Result<Self, QuantumError> {
        if numerator == 0 || denominator == 0 {
            return Err(QuantumError::ZeroInterval);
        }
        if phase_code == 0 {
            return Err(QuantumError::ZeroPhaseCode);
        }
        if gcd(numerator, denominator) != 1 {
            return Err(QuantumError::NonCanonicalRatio);
        }
        Ok(Self {
            numerator,
            denominator,
            phase_code,
        })
    }

    pub(crate) fn numerator(&self) -> u128 {
        self.numerator
    }

    pub(crate) fn denominator(&self) -> u128 {
        self.denominator
    }

    pub(crate) fn phase_code(&self) -> u32 {
        self.phase_code
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
#[repr(u8)]
pub(crate) enum CompartmentSide {
    Cytosol = 1,
    Extracellular = 2,
    MembraneInner = 3,
    MembraneOuter = 4,
    VesicleInterior = 5,
    SynapticCleft = 6,
}

impl CompartmentSide {
    pub(crate) fn from_code(code: u8) -> Result<Self, QuantumError> {
        match code {
            1 => Ok(Self::Cytosol),
            2 => Ok(Self::Extracellular),
            3 => Ok(Self::MembraneInner),
            4 => Ok(Self::MembraneOuter),
            5 => Ok(Self::VesicleInterior),
            6 => Ok(Self::SynapticCleft),
            _ => Err(QuantumError::UnknownCompartmentSide),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct PhysicalLocation {
    region_code: u32,
    compartment_code: u32,
    side: CompartmentSide,
    control_volume_code: u32,
    lane_code: u32,
    site_code: u32,
}

impl PhysicalLocation {
    pub(crate) fn new(
        region_code: u32,
        compartment_code: u32,
        side: CompartmentSide,
        control_volume_code: u32,
        lane_code: u32,
        site_code: u32,
    ) -> Result<Self, QuantumError> {
        if region_code == 0
            || compartment_code == 0
            || control_volume_code == 0
            || lane_code == 0
            || site_code == 0
        {
            return Err(QuantumError::ZeroLocationCode);
        }
        Ok(Self {
            region_code,
            compartment_code,
            side,
            control_volume_code,
            lane_code,
            site_code,
        })
    }

    pub(crate) fn region_code(&self) -> u32 {
        self.region_code
    }

    pub(crate) fn compartment_code(&self) -> u32 {
        self.compartment_code
    }

    pub(crate) fn side(&self) -> CompartmentSide {
        self.side
    }

    pub(crate) fn control_volume_code(&self) -> u32 {
        self.control_volume_code
    }

    pub(crate) fn lane_code(&self) -> u32 {
        self.lane_code
    }

    pub(crate) fn site_code(&self) -> u32 {
        self.site_code
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct BoundaryFlux<const MOIETIES: usize> {
    charge_change: i128,
    moiety_changes: [i128; MOIETIES],
}

impl<const MOIETIES: usize> BoundaryFlux<MOIETIES> {
    pub(crate) fn new(charge_change: i128, moiety_changes: [i128; MOIETIES]) -> Self {
        Self {
            charge_change,
            moiety_changes,
        }
    }

    pub(crate) fn charge_change(&self) -> i128 {
        self.charge_change
    }

    pub(crate) fn moiety_changes(&self) -> &[i128; MOIETIES] {
        &self.moiety_changes
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ConservationBoundary<const MOIETIES: usize> {
    Closed,
    ExplicitOpen(BoundaryFlux<MOIETIES>),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct FractionLaw {
    numerator: u128,
    denominator: u128,
}

impl FractionLaw {
    pub(crate) fn new(numerator: u128, denominator: u128) -> Result<Self, QuantumError> {
        if numerator == 0 || denominator == 0 {
            return Err(QuantumError::ZeroFraction);
        }
        if numerator > denominator {
            return Err(QuantumError::FractionExceedsUnity);
        }
        if gcd(numerator, denominator) != 1 {
            return Err(QuantumError::NonCanonicalRatio);
        }
        Ok(Self {
            numerator,
            denominator,
        })
    }

    pub(crate) fn numerator(&self) -> u128 {
        self.numerator
    }

    pub(crate) fn denominator(&self) -> u128 {
        self.denominator
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct FractionWidthProof {
    maximum_eligible_extent: u128,
    maximum_accumulator: u128,
    required_bits: u32,
}

impl FractionWidthProof {
    pub(crate) fn maximum_eligible_extent(&self) -> u128 {
        self.maximum_eligible_extent
    }

    pub(crate) fn maximum_accumulator(&self) -> u128 {
        self.maximum_accumulator
    }

    pub(crate) fn required_bits(&self) -> u32 {
        self.required_bits
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct AdmittedContactLaneAnatomy<const SPECIES: usize, const MOIETIES: usize> {
    schema: SpeciesSchema<SPECIES, MOIETIES>,
    location: PhysicalLocation,
    interval: ExactInterval,
    capacities: [u128; SPECIES],
    contact_limits: [u128; SPECIES],
    coefficients: [i64; SPECIES],
    fraction: FractionLaw,
    conservation_boundary: ConservationBoundary<MOIETIES>,
    width_proof: FractionWidthProof,
}

impl<const SPECIES: usize, const MOIETIES: usize> AdmittedContactLaneAnatomy<SPECIES, MOIETIES> {
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn new(
        schema: &SpeciesSchema<SPECIES, MOIETIES>,
        location: PhysicalLocation,
        interval: ExactInterval,
        capacities: [u128; SPECIES],
        contact_limits: [u128; SPECIES],
        coefficients: [i64; SPECIES],
        fraction: FractionLaw,
        conservation_boundary: ConservationBoundary<MOIETIES>,
    ) -> Result<Self, QuantumError> {
        if capacities.contains(&0) {
            return Err(QuantumError::ZeroCapacity);
        }
        let has_reactant = coefficients.iter().any(|coefficient| *coefficient < 0);
        let has_product = coefficients.iter().any(|coefficient| *coefficient > 0);
        if !has_reactant || !has_product {
            return Err(QuantumError::ReactionDoesNotTransferMaterial);
        }
        for species in 0..SPECIES {
            if coefficients[species] < 0 {
                if contact_limits[species] == 0 || contact_limits[species] > capacities[species] {
                    return Err(QuantumError::InvalidReactantContactLimit { species });
                }
            } else if contact_limits[species] != 0 {
                return Err(QuantumError::ContactLimitOnNonReactant { species });
            }
        }
        verify_conservation(schema, &coefficients, conservation_boundary)?;
        let maximum_eligible_extent =
            maximum_anatomical_extent(&capacities, &contact_limits, &coefficients)?;
        let maximum_accumulator = fraction
            .numerator
            .checked_mul(maximum_eligible_extent)
            .and_then(|value| value.checked_add(fraction.denominator - 1))
            .ok_or(QuantumError::IntegerWidthExceeded)?;
        let required_bits = if maximum_accumulator == 0 {
            1
        } else {
            u128::BITS - maximum_accumulator.leading_zeros()
        };
        for species in 0..SPECIES {
            u128::from(coefficients[species].unsigned_abs())
                .checked_mul(maximum_eligible_extent)
                .ok_or(QuantumError::IntegerWidthExceeded)?;
        }
        Ok(Self {
            schema: *schema,
            location,
            interval,
            capacities,
            contact_limits,
            coefficients,
            fraction,
            conservation_boundary,
            width_proof: FractionWidthProof {
                maximum_eligible_extent,
                maximum_accumulator,
                required_bits,
            },
        })
    }

    pub(crate) fn schema(&self) -> &SpeciesSchema<SPECIES, MOIETIES> {
        &self.schema
    }

    pub(crate) fn location(&self) -> PhysicalLocation {
        self.location
    }

    pub(crate) fn interval(&self) -> ExactInterval {
        self.interval
    }

    pub(crate) fn capacities(&self) -> &[u128; SPECIES] {
        &self.capacities
    }

    pub(crate) fn contact_limits(&self) -> &[u128; SPECIES] {
        &self.contact_limits
    }

    pub(crate) fn coefficients(&self) -> &[i64; SPECIES] {
        &self.coefficients
    }

    pub(crate) fn fraction(&self) -> FractionLaw {
        self.fraction
    }

    pub(crate) fn conservation_boundary(&self) -> ConservationBoundary<MOIETIES> {
        self.conservation_boundary
    }

    pub(crate) fn width_proof(&self) -> FractionWidthProof {
        self.width_proof
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ContactLaneState<const SPECIES: usize> {
    quantities: [u128; SPECIES],
    remainder: u128,
}

impl<const SPECIES: usize> ContactLaneState<SPECIES> {
    pub(crate) fn new<const MOIETIES: usize>(
        anatomy: &AdmittedContactLaneAnatomy<SPECIES, MOIETIES>,
        quantities: [u128; SPECIES],
        remainder: u128,
    ) -> Result<Self, QuantumError> {
        if quantities
            .iter()
            .zip(anatomy.capacities.iter())
            .any(|(quantity, capacity)| quantity > capacity)
        {
            return Err(QuantumError::InventoryExceedsCapacity);
        }
        if remainder >= anatomy.fraction.denominator {
            return Err(QuantumError::RemainderOutsideBoundRelation);
        }
        Ok(Self {
            quantities,
            remainder,
        })
    }

    pub(crate) fn quantities(&self) -> &[u128; SPECIES] {
        &self.quantities
    }

    pub(crate) fn remainder(&self) -> u128 {
        self.remainder
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LaneSettlement<const SPECIES: usize> {
    pub(crate) successor: ContactLaneState<SPECIES>,
    pub(crate) extent: u128,
}

pub(crate) fn validate_contact_occupancy<const SPECIES: usize, const MOIETIES: usize>(
    anatomy: &AdmittedContactLaneAnatomy<SPECIES, MOIETIES>,
    state: &ContactLaneState<SPECIES>,
    occupied_reactants: &[u128; SPECIES],
) -> Result<(), QuantumError> {
    for species in 0..SPECIES {
        if anatomy.coefficients[species] < 0 {
            if occupied_reactants[species] > anatomy.contact_limits[species]
                || occupied_reactants[species] > state.quantities[species]
            {
                return Err(QuantumError::ContactOccupancyUnavailable { species });
            }
        } else if occupied_reactants[species] != 0 {
            return Err(QuantumError::NonReactantOccupancy { species });
        }
    }
    Ok(())
}

pub(crate) fn settle_bound_lane<const SPECIES: usize, const MOIETIES: usize>(
    anatomy: &AdmittedContactLaneAnatomy<SPECIES, MOIETIES>,
    predecessor: &ContactLaneState<SPECIES>,
    occupied_reactants: &[u128; SPECIES],
) -> Result<LaneSettlement<SPECIES>, QuantumError> {
    validate_contact_occupancy(anatomy, predecessor, occupied_reactants)?;
    let eligible_extent = maximum_reached_extent(anatomy, predecessor, occupied_reactants)?;
    if eligible_extent > anatomy.width_proof.maximum_eligible_extent {
        return Err(QuantumError::WidthAdmissionViolated);
    }
    let accumulator = anatomy
        .fraction
        .numerator
        .checked_mul(eligible_extent)
        .and_then(|value| value.checked_add(predecessor.remainder))
        .ok_or(QuantumError::WidthAdmissionViolated)?;
    if accumulator > anatomy.width_proof.maximum_accumulator {
        return Err(QuantumError::WidthAdmissionViolated);
    }
    let extent = accumulator / anatomy.fraction.denominator;
    let remainder = accumulator % anatomy.fraction.denominator;
    let mut quantities = predecessor.quantities;
    for species in 0..SPECIES {
        let coefficient = anatomy.coefficients[species];
        let change = u128::from(coefficient.unsigned_abs())
            .checked_mul(extent)
            .ok_or(QuantumError::WidthAdmissionViolated)?;
        quantities[species] = if coefficient < 0 {
            quantities[species]
                .checked_sub(change)
                .ok_or(QuantumError::ReactantUnavailable { species })?
        } else {
            quantities[species]
                .checked_add(change)
                .ok_or(QuantumError::WidthAdmissionViolated)?
        };
        if quantities[species] > anatomy.capacities[species] {
            return Err(QuantumError::DestinationCapacityExceeded { species });
        }
    }
    Ok(LaneSettlement {
        successor: ContactLaneState {
            quantities,
            remainder,
        },
        extent,
    })
}

fn maximum_anatomical_extent<const SPECIES: usize>(
    capacities: &[u128; SPECIES],
    contact_limits: &[u128; SPECIES],
    coefficients: &[i64; SPECIES],
) -> Result<u128, QuantumError> {
    let mut maximum: Option<u128> = None;
    for species in 0..SPECIES {
        let coefficient = coefficients[species];
        let candidate = if coefficient < 0 {
            Some(contact_limits[species] / u128::from(coefficient.unsigned_abs()))
        } else if coefficient > 0 {
            Some(capacities[species] / u128::from(coefficient.unsigned_abs()))
        } else {
            None
        };
        if let Some(candidate) = candidate {
            maximum = Some(maximum.map_or(candidate, |prior| prior.min(candidate)));
        }
    }
    let maximum = maximum.ok_or(QuantumError::ReactionDoesNotTransferMaterial)?;
    if maximum == 0 {
        return Err(QuantumError::NoAdmissibleReactionExtent);
    }
    Ok(maximum)
}

fn maximum_reached_extent<const SPECIES: usize, const MOIETIES: usize>(
    anatomy: &AdmittedContactLaneAnatomy<SPECIES, MOIETIES>,
    state: &ContactLaneState<SPECIES>,
    occupied_reactants: &[u128; SPECIES],
) -> Result<u128, QuantumError> {
    let mut maximum: Option<u128> = None;
    for species in 0..SPECIES {
        let coefficient = anatomy.coefficients[species];
        let candidate = if coefficient < 0 {
            Some(occupied_reactants[species] / u128::from(coefficient.unsigned_abs()))
        } else if coefficient > 0 {
            let free = anatomy.capacities[species]
                .checked_sub(state.quantities[species])
                .ok_or(QuantumError::InventoryExceedsCapacity)?;
            Some(free / u128::from(coefficient.unsigned_abs()))
        } else {
            None
        };
        if let Some(candidate) = candidate {
            maximum = Some(maximum.map_or(candidate, |prior| prior.min(candidate)));
        }
    }
    maximum.ok_or(QuantumError::ReactionDoesNotTransferMaterial)
}

fn verify_conservation<const SPECIES: usize, const MOIETIES: usize>(
    schema: &SpeciesSchema<SPECIES, MOIETIES>,
    coefficients: &[i64; SPECIES],
    boundary: ConservationBoundary<MOIETIES>,
) -> Result<(), QuantumError> {
    let mut charge_change = 0_i128;
    let mut moiety_changes = [0_i128; MOIETIES];
    for species in 0..SPECIES {
        let coefficient = i128::from(coefficients[species]);
        charge_change = charge_change
            .checked_add(
                coefficient
                    .checked_mul(i128::from(schema.species[species].charge_per_quantum))
                    .ok_or(QuantumError::ConservationArithmeticOverflow)?,
            )
            .ok_or(QuantumError::ConservationArithmeticOverflow)?;
        for moiety in 0..MOIETIES {
            let amount = i128::from(schema.species[species].conserved_moieties[moiety]);
            moiety_changes[moiety] = moiety_changes[moiety]
                .checked_add(
                    coefficient
                        .checked_mul(amount)
                        .ok_or(QuantumError::ConservationArithmeticOverflow)?,
                )
                .ok_or(QuantumError::ConservationArithmeticOverflow)?;
        }
    }
    let declared = match boundary {
        ConservationBoundary::Closed => BoundaryFlux::new(0, [0; MOIETIES]),
        ConservationBoundary::ExplicitOpen(flux) => flux,
    };
    if charge_change != declared.charge_change {
        return Err(QuantumError::ChargeConservationMismatch);
    }
    for moiety in 0..MOIETIES {
        if moiety_changes[moiety] != declared.moiety_changes[moiety] {
            return Err(QuantumError::MoietyConservationMismatch { moiety });
        }
    }
    Ok(())
}

pub(crate) fn resident_lane_payload_bytes<const SPECIES: usize, const MOIETIES: usize>() -> usize {
    size_of::<AdmittedContactLaneAnatomy<SPECIES, MOIETIES>>()
        + size_of::<ContactLaneState<SPECIES>>()
}

fn gcd(mut left: u128, mut right: u128) -> u128 {
    while right != 0 {
        let remainder = left % right;
        left = right;
        right = remainder;
    }
    left
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum QuantumError {
    EmptySpeciesSet,
    ZeroUnitScale,
    ZeroInterval,
    ZeroFraction,
    ZeroSpeciesCode,
    ZeroMoietyCode,
    ZeroPhaseCode,
    ZeroLocationCode,
    ZeroCapacity,
    NonCanonicalRatio,
    DuplicateSpeciesCode,
    DuplicateMoietyCode,
    NonCanonicalSpeciesOrder,
    NonCanonicalMoietyOrder,
    UnknownPhysicalDimension,
    UnknownCompartmentSide,
    FractionExceedsUnity,
    ReactionDoesNotTransferMaterial,
    InvalidReactantContactLimit { species: usize },
    ContactLimitOnNonReactant { species: usize },
    NoAdmissibleReactionExtent,
    IntegerWidthExceeded,
    ConservationArithmeticOverflow,
    ChargeConservationMismatch,
    MoietyConservationMismatch { moiety: usize },
    InventoryExceedsCapacity,
    RemainderOutsideBoundRelation,
    ContactOccupancyUnavailable { species: usize },
    NonReactantOccupancy { species: usize },
    WidthAdmissionViolated,
    ReactantUnavailable { species: usize },
    DestinationCapacityExceeded { species: usize },
}

#[cfg(test)]
mod tests {
    use super::*;

    fn unit() -> ExactUnit {
        ExactUnit::new(PhysicalDimension::MoleculeCount, 1, 1).unwrap()
    }

    fn schema() -> SpeciesSchema<2, 1> {
        SpeciesSchema::new(
            [91],
            [
                SpeciesDefinition::new(11, unit(), -1, [1]).unwrap(),
                SpeciesDefinition::new(12, unit(), -1, [1]).unwrap(),
            ],
        )
        .unwrap()
    }

    fn lane(fraction: FractionLaw) -> AdmittedContactLaneAnatomy<2, 1> {
        AdmittedContactLaneAnatomy::new(
            &schema(),
            PhysicalLocation::new(1, 2, CompartmentSide::Cytosol, 3, 4, 5).unwrap(),
            ExactInterval::new(1, 1_000, 7).unwrap(),
            [100, 100],
            [100, 0],
            [-1, 1],
            fraction,
            ConservationBoundary::Closed,
        )
        .unwrap()
    }

    #[test]
    fn canonical_schema_and_units_are_exact() {
        let value = schema();
        assert_eq!(value.moiety_codes(), &[91]);
        assert_eq!(value.species()[0].code(), 11);
        assert_eq!(
            value.species()[0].unit().dimension(),
            PhysicalDimension::MoleculeCount
        );
        assert_eq!(value.species()[0].unit().numerator(), 1);
        assert_eq!(value.species()[0].unit().denominator(), 1);
        assert_eq!(value.species()[0].charge_per_quantum(), -1);
        assert_eq!(value.species()[0].conserved_moieties(), &[1]);
        assert_eq!(
            PhysicalDimension::from_code(1).unwrap(),
            PhysicalDimension::MoleculeCount
        );
        assert_eq!(
            CompartmentSide::from_code(1).unwrap(),
            CompartmentSide::Cytosol
        );
    }

    #[test]
    fn noncanonical_or_duplicate_schema_is_refused() {
        assert_eq!(
            ExactUnit::new(PhysicalDimension::MoleculeCount, 2, 2),
            Err(QuantumError::NonCanonicalRatio)
        );
        let repeated = SpeciesDefinition::new(11, unit(), 0, [1]).unwrap();
        assert_eq!(
            SpeciesSchema::new([91], [repeated, repeated]),
            Err(QuantumError::DuplicateSpeciesCode)
        );
        let first = SpeciesDefinition::new(12, unit(), 0, [1]).unwrap();
        let second = SpeciesDefinition::new(11, unit(), 0, [1]).unwrap();
        assert_eq!(
            SpeciesSchema::new([91], [first, second]),
            Err(QuantumError::NonCanonicalSpeciesOrder)
        );
        assert_eq!(
            SpeciesSchema::<1, 2>::new(
                [92, 91],
                [SpeciesDefinition::new(11, unit(), 0, [1, 1]).unwrap()],
            ),
            Err(QuantumError::NonCanonicalMoietyOrder)
        );
    }

    #[test]
    fn closed_charge_and_moiety_imbalance_is_refused() {
        let result = AdmittedContactLaneAnatomy::new(
            &schema(),
            PhysicalLocation::new(1, 2, CompartmentSide::Cytosol, 3, 4, 5).unwrap(),
            ExactInterval::new(1, 1, 7).unwrap(),
            [100, 100],
            [100, 0],
            [-1, 2],
            FractionLaw::new(1, 1).unwrap(),
            ConservationBoundary::Closed,
        );
        assert_eq!(result, Err(QuantumError::ChargeConservationMismatch));
    }

    #[test]
    fn closed_moiety_imbalance_is_refused_when_charge_balances() {
        let neutral_schema = SpeciesSchema::new(
            [91],
            [
                SpeciesDefinition::new(11, unit(), 0, [1]).unwrap(),
                SpeciesDefinition::new(12, unit(), 0, [2]).unwrap(),
            ],
        )
        .unwrap();
        let result = AdmittedContactLaneAnatomy::new(
            &neutral_schema,
            PhysicalLocation::new(1, 2, CompartmentSide::Cytosol, 3, 4, 5).unwrap(),
            ExactInterval::new(1, 1, 7).unwrap(),
            [100, 100],
            [100, 0],
            [-1, 1],
            FractionLaw::new(1, 1).unwrap(),
            ConservationBoundary::Closed,
        );
        assert_eq!(
            result,
            Err(QuantumError::MoietyConservationMismatch { moiety: 0 })
        );
    }

    #[test]
    fn explicit_open_flux_is_exactly_checked() {
        let admitted = AdmittedContactLaneAnatomy::new(
            &schema(),
            PhysicalLocation::new(1, 2, CompartmentSide::Cytosol, 3, 4, 5).unwrap(),
            ExactInterval::new(1, 1, 7).unwrap(),
            [100, 100],
            [100, 0],
            [-1, 2],
            FractionLaw::new(1, 1).unwrap(),
            ConservationBoundary::ExplicitOpen(BoundaryFlux::new(-1, [1])),
        )
        .unwrap();
        match admitted.conservation_boundary() {
            ConservationBoundary::ExplicitOpen(flux) => {
                assert_eq!(flux.charge_change(), -1);
                assert_eq!(flux.moiety_changes(), &[1]);
            }
            ConservationBoundary::Closed => panic!("expected explicit open boundary"),
        }
    }

    #[test]
    fn width_is_proved_during_anatomy_admission() {
        let value = lane(FractionLaw::new(1, 3).unwrap());
        assert_eq!(value.width_proof().maximum_eligible_extent(), 100);
        assert_eq!(value.width_proof().maximum_accumulator(), 102);
        assert_eq!(value.width_proof().required_bits(), 7);
        assert_eq!(value.fraction().numerator(), 1);
        assert_eq!(value.fraction().denominator(), 3);
    }

    #[test]
    fn unrepresentable_width_is_refused_at_anatomy_admission() {
        let result = AdmittedContactLaneAnatomy::new(
            &schema(),
            PhysicalLocation::new(1, 2, CompartmentSide::Cytosol, 3, 4, 5).unwrap(),
            ExactInterval::new(1, 1, 7).unwrap(),
            [u128::MAX, u128::MAX],
            [u128::MAX, 0],
            [-1, 1],
            FractionLaw::new(1, 2).unwrap(),
            ConservationBoundary::Closed,
        );
        assert_eq!(result, Err(QuantumError::IntegerWidthExceeded));
    }

    #[test]
    fn remainder_is_internal_to_one_bound_lane_transition() {
        let anatomy = lane(FractionLaw::new(1, 3).unwrap());
        let mut state = ContactLaneState::new(&anatomy, [1, 0], 0).unwrap();
        for expected in [0, 0, 1] {
            let settled = settle_bound_lane(&anatomy, &state, &[1, 0]).unwrap();
            assert_eq!(settled.extent, expected);
            state = settled.successor;
        }
        assert_eq!(state.quantities(), &[0, 1]);
        assert_eq!(state.remainder(), 0);
    }

    #[test]
    fn occupancy_cannot_name_product_or_unavailable_reactant() {
        let anatomy = lane(FractionLaw::new(1, 1).unwrap());
        let state = ContactLaneState::new(&anatomy, [2, 0], 0).unwrap();
        assert_eq!(
            validate_contact_occupancy(&anatomy, &state, &[3, 0]),
            Err(QuantumError::ContactOccupancyUnavailable { species: 0 })
        );
        assert_eq!(
            validate_contact_occupancy(&anatomy, &state, &[1, 1]),
            Err(QuantumError::NonReactantOccupancy { species: 1 })
        );
    }

    #[test]
    fn lane_identity_and_interval_fields_are_exact() {
        let value = lane(FractionLaw::new(1, 1).unwrap());
        let location = value.location();
        assert_eq!(location.region_code(), 1);
        assert_eq!(location.compartment_code(), 2);
        assert_eq!(location.side(), CompartmentSide::Cytosol);
        assert_eq!(location.control_volume_code(), 3);
        assert_eq!(location.lane_code(), 4);
        assert_eq!(location.site_code(), 5);
        assert_eq!(value.interval().numerator(), 1);
        assert_eq!(value.interval().denominator(), 1_000);
        assert_eq!(value.interval().phase_code(), 7);
        assert_eq!(value.capacities(), &[100, 100]);
        assert_eq!(value.contact_limits(), &[100, 0]);
        assert_eq!(value.coefficients(), &[-1, 1]);
        assert!(resident_lane_payload_bytes::<2, 1>() > 0);
    }
}
