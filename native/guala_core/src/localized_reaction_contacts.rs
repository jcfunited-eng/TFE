//! Geometry-observed, anatomy-bound, disjoint local contact transitions.
//!
//! This unmounted module accepts physical contact occupancy observations and
//! verifies them against the complete predecessor anatomy and state.  It does
//! not derive geometry.  Successful observations are canonicalized by exact
//! physical location and borrow the predecessor they name, so they cannot be
//! rebound to another state.  A transition derives all extents locally; callers
//! cannot supply an extent or a reaction priority.

use crate::bounded_physical_quanta::{
    settle_bound_lane, validate_contact_occupancy, AdmittedContactLaneAnatomy, BoundaryFlux,
    CompartmentSide, ConservationBoundary, ContactLaneState, ExactInterval, ExactUnit, FractionLaw,
    PhysicalDimension, PhysicalLocation, QuantumError, SpeciesDefinition, SpeciesSchema,
};
use std::mem::size_of;

const CODEC_MAGIC: [u8; 8] = *b"GQCONT01";
const CODEC_VERSION: u32 = 1;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct LocalContactAnatomy<
    const SPECIES: usize,
    const MOIETIES: usize,
    const LANES: usize,
> {
    schema: SpeciesSchema<SPECIES, MOIETIES>,
    interval: ExactInterval,
    lanes: [AdmittedContactLaneAnatomy<SPECIES, MOIETIES>; LANES],
}

impl<const SPECIES: usize, const MOIETIES: usize, const LANES: usize>
    LocalContactAnatomy<SPECIES, MOIETIES, LANES>
{
    pub(crate) fn new(
        schema: SpeciesSchema<SPECIES, MOIETIES>,
        interval: ExactInterval,
        lanes: [AdmittedContactLaneAnatomy<SPECIES, MOIETIES>; LANES],
    ) -> Result<Self, ContactError> {
        if LANES == 0 {
            return Err(ContactError::EmptyLaneSet);
        }
        for lane in 0..LANES {
            if lanes[lane].schema() != &schema {
                return Err(ContactError::SpeciesSchemaMismatch);
            }
            if lanes[lane].interval() != interval {
                return Err(ContactError::IntervalMismatch);
            }
            if lane > 0 && lanes[lane].location() <= lanes[lane - 1].location() {
                return if lanes[lane].location() == lanes[lane - 1].location() {
                    Err(ContactError::DuplicatePhysicalLocation)
                } else {
                    Err(ContactError::NonCanonicalLaneOrder)
                };
            }
        }
        Ok(Self {
            schema,
            interval,
            lanes,
        })
    }

    pub(crate) fn schema(&self) -> &SpeciesSchema<SPECIES, MOIETIES> {
        &self.schema
    }

    pub(crate) fn interval(&self) -> ExactInterval {
        self.interval
    }

    pub(crate) fn lanes(&self) -> &[AdmittedContactLaneAnatomy<SPECIES, MOIETIES>; LANES] {
        &self.lanes
    }
}

/// The anatomy is physically part of this candidate state.  There is no
/// separate anatomy argument at transition time that can reinterpret it.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct BoundContactState<const SPECIES: usize, const MOIETIES: usize, const LANES: usize>
{
    anatomy: LocalContactAnatomy<SPECIES, MOIETIES, LANES>,
    interval_index: u128,
    quantities: [[u128; SPECIES]; LANES],
    remainders: [u128; LANES],
}

impl<const SPECIES: usize, const MOIETIES: usize, const LANES: usize>
    BoundContactState<SPECIES, MOIETIES, LANES>
{
    pub(crate) fn new(
        anatomy: LocalContactAnatomy<SPECIES, MOIETIES, LANES>,
        interval_index: u128,
        quantities: [[u128; SPECIES]; LANES],
        remainders: [u128; LANES],
    ) -> Result<Self, ContactError> {
        for lane in 0..LANES {
            ContactLaneState::new(&anatomy.lanes[lane], quantities[lane], remainders[lane])?;
        }
        Ok(Self {
            anatomy,
            interval_index,
            quantities,
            remainders,
        })
    }

    pub(crate) fn anatomy(&self) -> &LocalContactAnatomy<SPECIES, MOIETIES, LANES> {
        &self.anatomy
    }

    pub(crate) fn interval_index(&self) -> u128 {
        self.interval_index
    }

    pub(crate) fn quantities(&self) -> &[[u128; SPECIES]; LANES] {
        &self.quantities
    }

    pub(crate) fn remainders(&self) -> &[u128; LANES] {
        &self.remainders
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct GeometryContactObservation<const SPECIES: usize> {
    location: PhysicalLocation,
    interval: ExactInterval,
    interval_index: u128,
    occupied_reactants: [u128; SPECIES],
}

impl<const SPECIES: usize> GeometryContactObservation<SPECIES> {
    pub(crate) fn new(
        location: PhysicalLocation,
        interval: ExactInterval,
        interval_index: u128,
        occupied_reactants: [u128; SPECIES],
    ) -> Self {
        Self {
            location,
            interval,
            interval_index,
            occupied_reactants,
        }
    }

    pub(crate) fn location(&self) -> PhysicalLocation {
        self.location
    }

    pub(crate) fn occupied_reactants(&self) -> &[u128; SPECIES] {
        &self.occupied_reactants
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ContactWorkRequirement {
    pub(crate) observations: usize,
    pub(crate) lanes: usize,
    pub(crate) species: usize,
    pub(crate) clock_comparisons: usize,
    pub(crate) location_comparisons: usize,
    pub(crate) admission_species_visits: usize,
    pub(crate) transition_lane_visits: usize,
    pub(crate) state_species_copies: usize,
    pub(crate) state_remainder_copies: usize,
    pub(crate) extent_slot_initializations: usize,
    pub(crate) transition_species_visits: usize,
    pub(crate) fraction_settlements: usize,
    pub(crate) successor_clock_steps: usize,
    pub(crate) successor_anatomy_payload_bytes: usize,
    pub(crate) resident_state_payload_bytes: usize,
    pub(crate) occupancy_payload_bytes: usize,
    pub(crate) transition_payload_bytes: usize,
    pub(crate) canonical_serialized_bytes: usize,
}

pub(crate) struct DisjointContactOccupancy<
    'a,
    const SPECIES: usize,
    const MOIETIES: usize,
    const LANES: usize,
    const CONTACTS: usize,
> {
    predecessor: &'a BoundContactState<SPECIES, MOIETIES, LANES>,
    occupied_by_lane: [Option<[u128; SPECIES]>; LANES],
    requirement: ContactWorkRequirement,
}

impl<
        'a,
        const SPECIES: usize,
        const MOIETIES: usize,
        const LANES: usize,
        const CONTACTS: usize,
    > DisjointContactOccupancy<'a, SPECIES, MOIETIES, LANES, CONTACTS>
{
    pub(crate) fn requirement(&self) -> ContactWorkRequirement {
        self.requirement
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ContactTransition<const SPECIES: usize, const MOIETIES: usize, const LANES: usize>
{
    pub(crate) successor: BoundContactState<SPECIES, MOIETIES, LANES>,
    pub(crate) extents_by_lane: [u128; LANES],
    pub(crate) requirement: ContactWorkRequirement,
}

pub(crate) fn admit_disjoint_geometry_contacts<
    'a,
    const SPECIES: usize,
    const MOIETIES: usize,
    const LANES: usize,
    const CONTACTS: usize,
>(
    predecessor: &'a BoundContactState<SPECIES, MOIETIES, LANES>,
    observations: [GeometryContactObservation<SPECIES>; CONTACTS],
) -> Result<DisjointContactOccupancy<'a, SPECIES, MOIETIES, LANES, CONTACTS>, ContactError> {
    if CONTACTS > LANES {
        return Err(ContactError::MoreContactsThanLanes);
    }
    let requirement = derive_contact_requirement::<SPECIES, MOIETIES, LANES, CONTACTS>()?;
    let mut occupied_by_lane = [None; LANES];
    for observation in observations {
        if observation.interval != predecessor.anatomy.interval
            || observation.interval_index != predecessor.interval_index
        {
            return Err(ContactError::ObservationClockMismatch);
        }
        let mut reached_lane: Option<usize> = None;
        for lane in 0..LANES {
            if predecessor.anatomy.lanes[lane].location() == observation.location {
                reached_lane = Some(lane);
            }
        }
        let lane = reached_lane.ok_or(ContactError::UnknownPhysicalLocation)?;
        if occupied_by_lane[lane].is_some() {
            return Err(ContactError::OverlappingContact);
        }
        let lane_state = ContactLaneState::new(
            &predecessor.anatomy.lanes[lane],
            predecessor.quantities[lane],
            predecessor.remainders[lane],
        )?;
        validate_contact_occupancy(
            &predecessor.anatomy.lanes[lane],
            &lane_state,
            &observation.occupied_reactants,
        )?;
        occupied_by_lane[lane] = Some(observation.occupied_reactants);
    }
    Ok(DisjointContactOccupancy {
        predecessor,
        occupied_by_lane,
        requirement,
    })
}

pub(crate) fn settle_disjoint_contacts<
    const SPECIES: usize,
    const MOIETIES: usize,
    const LANES: usize,
    const CONTACTS: usize,
>(
    occupancy: DisjointContactOccupancy<'_, SPECIES, MOIETIES, LANES, CONTACTS>,
) -> Result<ContactTransition<SPECIES, MOIETIES, LANES>, ContactError> {
    let next_interval = occupancy
        .predecessor
        .interval_index
        .checked_add(1)
        .ok_or(ContactError::IntervalIndexOverflow)?;
    let mut quantities = occupancy.predecessor.quantities;
    let mut remainders = occupancy.predecessor.remainders;
    let mut extents_by_lane = [0_u128; LANES];
    for lane in 0..LANES {
        if let Some(occupied_reactants) = occupancy.occupied_by_lane[lane] {
            let lane_state = ContactLaneState::new(
                &occupancy.predecessor.anatomy.lanes[lane],
                occupancy.predecessor.quantities[lane],
                occupancy.predecessor.remainders[lane],
            )?;
            let settlement = settle_bound_lane(
                &occupancy.predecessor.anatomy.lanes[lane],
                &lane_state,
                &occupied_reactants,
            )?;
            quantities[lane] = *settlement.successor.quantities();
            remainders[lane] = settlement.successor.remainder();
            extents_by_lane[lane] = settlement.extent;
        }
    }
    Ok(ContactTransition {
        successor: BoundContactState {
            anatomy: occupancy.predecessor.anatomy,
            interval_index: next_interval,
            quantities,
            remainders,
        },
        extents_by_lane,
        requirement: occupancy.requirement,
    })
}

pub(crate) fn derive_contact_requirement<
    const SPECIES: usize,
    const MOIETIES: usize,
    const LANES: usize,
    const CONTACTS: usize,
>() -> Result<ContactWorkRequirement, ContactError> {
    if SPECIES == 0 {
        return Err(ContactError::Quantum(QuantumError::EmptySpeciesSet));
    }
    if LANES == 0 {
        return Err(ContactError::EmptyLaneSet);
    }
    let location_comparisons = CONTACTS
        .checked_mul(LANES)
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    // Admission reconstructs and validates one bound lane state: two S-wide
    // passes. Transition reconstructs it and then validates, derives extent,
    // and applies the successor: four S-wide passes.
    let admission_species_visits = CONTACTS
        .checked_mul(SPECIES)
        .and_then(|value| value.checked_mul(2))
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let state_species_copies = LANES
        .checked_mul(SPECIES)
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let transition_species_visits = CONTACTS
        .checked_mul(SPECIES)
        .and_then(|value| value.checked_mul(4))
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    Ok(ContactWorkRequirement {
        observations: CONTACTS,
        lanes: LANES,
        species: SPECIES,
        clock_comparisons: CONTACTS
            .checked_mul(2)
            .ok_or(ContactError::ResourceArithmeticOverflow)?,
        location_comparisons,
        admission_species_visits,
        transition_lane_visits: LANES,
        state_species_copies,
        state_remainder_copies: LANES,
        extent_slot_initializations: LANES,
        transition_species_visits,
        fraction_settlements: CONTACTS,
        successor_clock_steps: 1,
        successor_anatomy_payload_bytes: size_of::<LocalContactAnatomy<SPECIES, MOIETIES, LANES>>(),
        resident_state_payload_bytes: size_of::<BoundContactState<SPECIES, MOIETIES, LANES>>(),
        occupancy_payload_bytes: size_of::<
            DisjointContactOccupancy<'static, SPECIES, MOIETIES, LANES, CONTACTS>,
        >(),
        transition_payload_bytes: size_of::<ContactTransition<SPECIES, MOIETIES, LANES>>(),
        canonical_serialized_bytes: canonical_state_bytes::<SPECIES, MOIETIES, LANES>()?,
    })
}

pub(crate) fn canonical_state_bytes<
    const SPECIES: usize,
    const MOIETIES: usize,
    const LANES: usize,
>() -> Result<usize, ContactError> {
    let header = 8_usize + 4 + 8 + 8 + 8;
    let moiety_schema = MOIETIES
        .checked_mul(4)
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let one_species = 4_usize
        .checked_add(1 + 16 + 16 + 8)
        .and_then(|value| value.checked_add(MOIETIES.checked_mul(8)?))
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let species_schema = SPECIES
        .checked_mul(one_species)
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let interval = 16_usize + 16 + 4;
    let species_u128_bytes = SPECIES
        .checked_mul(16)
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let species_i64_bytes = SPECIES
        .checked_mul(8)
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let moiety_i128_bytes = MOIETIES
        .checked_mul(16)
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let one_lane = (4_usize + 4 + 1 + 4 + 4 + 4)
        .checked_add(species_u128_bytes)
        .and_then(|value| value.checked_add(species_u128_bytes))
        .and_then(|value| value.checked_add(species_i64_bytes))
        .and_then(|value| value.checked_add(16 + 16 + 1 + 16))
        .and_then(|value| value.checked_add(moiety_i128_bytes))
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let lanes = LANES
        .checked_mul(one_lane)
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let state_inventory_bytes = LANES
        .checked_mul(SPECIES)
        .and_then(|value| value.checked_mul(16))
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let state_remainder_bytes = LANES
        .checked_mul(16)
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    let state = 16_usize
        .checked_add(state_inventory_bytes)
        .and_then(|value| value.checked_add(state_remainder_bytes))
        .ok_or(ContactError::ResourceArithmeticOverflow)?;
    header
        .checked_add(moiety_schema)
        .and_then(|value| value.checked_add(species_schema))
        .and_then(|value| value.checked_add(interval))
        .and_then(|value| value.checked_add(lanes))
        .and_then(|value| value.checked_add(state))
        .ok_or(ContactError::ResourceArithmeticOverflow)
}

pub(crate) fn encode_bound_contact_state<
    const SPECIES: usize,
    const MOIETIES: usize,
    const LANES: usize,
>(
    state: &BoundContactState<SPECIES, MOIETIES, LANES>,
    output: &mut [u8],
) -> Result<usize, ContactError> {
    let required = canonical_state_bytes::<SPECIES, MOIETIES, LANES>()?;
    if output.len() != required {
        return Err(ContactError::CodecLengthMismatch {
            expected: required,
            actual: output.len(),
        });
    }
    let mut writer = Writer::new(output);
    writer.bytes(&CODEC_MAGIC)?;
    writer.u32(CODEC_VERSION)?;
    writer.u64(u64::try_from(SPECIES).map_err(|_| ContactError::ResourceArithmeticOverflow)?)?;
    writer.u64(u64::try_from(MOIETIES).map_err(|_| ContactError::ResourceArithmeticOverflow)?)?;
    writer.u64(u64::try_from(LANES).map_err(|_| ContactError::ResourceArithmeticOverflow)?)?;
    for code in state.anatomy.schema.moiety_codes() {
        writer.u32(*code)?;
    }
    for species in state.anatomy.schema.species() {
        writer.u32(species.code())?;
        writer.u8(species.unit().dimension() as u8)?;
        writer.u128(species.unit().numerator())?;
        writer.u128(species.unit().denominator())?;
        writer.i64(species.charge_per_quantum())?;
        for amount in species.conserved_moieties() {
            writer.u64(*amount)?;
        }
    }
    encode_interval(&mut writer, state.anatomy.interval)?;
    for lane in state.anatomy.lanes {
        encode_location(&mut writer, lane.location())?;
        for value in lane.capacities() {
            writer.u128(*value)?;
        }
        for value in lane.contact_limits() {
            writer.u128(*value)?;
        }
        for value in lane.coefficients() {
            writer.i64(*value)?;
        }
        writer.u128(lane.fraction().numerator())?;
        writer.u128(lane.fraction().denominator())?;
        match lane.conservation_boundary() {
            ConservationBoundary::Closed => {
                writer.u8(0)?;
                writer.i128(0)?;
                for _ in 0..MOIETIES {
                    writer.i128(0)?;
                }
            }
            ConservationBoundary::ExplicitOpen(flux) => {
                writer.u8(1)?;
                writer.i128(flux.charge_change())?;
                for value in flux.moiety_changes() {
                    writer.i128(*value)?;
                }
            }
        }
    }
    writer.u128(state.interval_index)?;
    for lane in state.quantities {
        for value in lane {
            writer.u128(value)?;
        }
    }
    for remainder in state.remainders {
        writer.u128(remainder)?;
    }
    if writer.position != required {
        return Err(ContactError::CodecInternalLengthMismatch);
    }
    Ok(required)
}

pub(crate) fn decode_bound_contact_state<
    const SPECIES: usize,
    const MOIETIES: usize,
    const LANES: usize,
>(
    input: &[u8],
) -> Result<BoundContactState<SPECIES, MOIETIES, LANES>, ContactError> {
    let required = canonical_state_bytes::<SPECIES, MOIETIES, LANES>()?;
    if input.len() != required {
        return Err(ContactError::CodecLengthMismatch {
            expected: required,
            actual: input.len(),
        });
    }
    if SPECIES == 0 {
        return Err(ContactError::Quantum(QuantumError::EmptySpeciesSet));
    }
    if LANES == 0 {
        return Err(ContactError::EmptyLaneSet);
    }
    let mut reader = Reader::new(input);
    if reader.array::<8>()? != CODEC_MAGIC || reader.u32()? != CODEC_VERSION {
        return Err(ContactError::CodecHeaderMismatch);
    }
    if reader.u64()?
        != u64::try_from(SPECIES).map_err(|_| ContactError::ResourceArithmeticOverflow)?
        || reader.u64()?
            != u64::try_from(MOIETIES).map_err(|_| ContactError::ResourceArithmeticOverflow)?
        || reader.u64()?
            != u64::try_from(LANES).map_err(|_| ContactError::ResourceArithmeticOverflow)?
    {
        return Err(ContactError::CodecShapeMismatch);
    }
    let mut moiety_codes = [0_u32; MOIETIES];
    for code in &mut moiety_codes {
        *code = reader.u32()?;
    }
    let first_species = decode_species::<MOIETIES>(&mut reader)?;
    let mut species = [first_species; SPECIES];
    for item in species.iter_mut().skip(1) {
        *item = decode_species::<MOIETIES>(&mut reader)?;
    }
    let schema = SpeciesSchema::new(moiety_codes, species)?;
    let interval = decode_interval(&mut reader)?;
    let first_lane = decode_lane(&mut reader, &schema, interval)?;
    let mut lanes = [first_lane; LANES];
    for lane in lanes.iter_mut().skip(1) {
        *lane = decode_lane(&mut reader, &schema, interval)?;
    }
    let anatomy = LocalContactAnatomy::new(schema, interval, lanes)?;
    let interval_index = reader.u128()?;
    let mut quantities = [[0_u128; SPECIES]; LANES];
    for lane in &mut quantities {
        for value in lane {
            *value = reader.u128()?;
        }
    }
    let mut remainders = [0_u128; LANES];
    for remainder in &mut remainders {
        *remainder = reader.u128()?;
    }
    if reader.position != required {
        return Err(ContactError::CodecInternalLengthMismatch);
    }
    BoundContactState::new(anatomy, interval_index, quantities, remainders)
}

fn encode_interval(writer: &mut Writer<'_>, interval: ExactInterval) -> Result<(), ContactError> {
    writer.u128(interval.numerator())?;
    writer.u128(interval.denominator())?;
    writer.u32(interval.phase_code())
}

fn decode_interval(reader: &mut Reader<'_>) -> Result<ExactInterval, ContactError> {
    Ok(ExactInterval::new(
        reader.u128()?,
        reader.u128()?,
        reader.u32()?,
    )?)
}

fn encode_location(
    writer: &mut Writer<'_>,
    location: PhysicalLocation,
) -> Result<(), ContactError> {
    writer.u32(location.region_code())?;
    writer.u32(location.compartment_code())?;
    writer.u8(location.side() as u8)?;
    writer.u32(location.control_volume_code())?;
    writer.u32(location.lane_code())?;
    writer.u32(location.site_code())
}

fn decode_location(reader: &mut Reader<'_>) -> Result<PhysicalLocation, ContactError> {
    Ok(PhysicalLocation::new(
        reader.u32()?,
        reader.u32()?,
        CompartmentSide::from_code(reader.u8()?)?,
        reader.u32()?,
        reader.u32()?,
        reader.u32()?,
    )?)
}

fn decode_species<const MOIETIES: usize>(
    reader: &mut Reader<'_>,
) -> Result<SpeciesDefinition<MOIETIES>, ContactError> {
    let code = reader.u32()?;
    let dimension = PhysicalDimension::from_code(reader.u8()?)?;
    let unit = ExactUnit::new(dimension, reader.u128()?, reader.u128()?)?;
    let charge = reader.i64()?;
    let mut moieties = [0_u64; MOIETIES];
    for amount in &mut moieties {
        *amount = reader.u64()?;
    }
    Ok(SpeciesDefinition::new(code, unit, charge, moieties)?)
}

fn decode_lane<const SPECIES: usize, const MOIETIES: usize>(
    reader: &mut Reader<'_>,
    schema: &SpeciesSchema<SPECIES, MOIETIES>,
    interval: ExactInterval,
) -> Result<AdmittedContactLaneAnatomy<SPECIES, MOIETIES>, ContactError> {
    let location = decode_location(reader)?;
    let mut capacities = [0_u128; SPECIES];
    for value in &mut capacities {
        *value = reader.u128()?;
    }
    let mut contact_limits = [0_u128; SPECIES];
    for value in &mut contact_limits {
        *value = reader.u128()?;
    }
    let mut coefficients = [0_i64; SPECIES];
    for value in &mut coefficients {
        *value = reader.i64()?;
    }
    let fraction = FractionLaw::new(reader.u128()?, reader.u128()?)?;
    let boundary_tag = reader.u8()?;
    let charge_change = reader.i128()?;
    let mut moiety_changes = [0_i128; MOIETIES];
    for value in &mut moiety_changes {
        *value = reader.i128()?;
    }
    let boundary = match boundary_tag {
        0 if charge_change == 0 && moiety_changes.iter().all(|value| *value == 0) => {
            ConservationBoundary::Closed
        }
        0 => return Err(ContactError::NonCanonicalClosedBoundary),
        1 => ConservationBoundary::ExplicitOpen(BoundaryFlux::new(charge_change, moiety_changes)),
        _ => return Err(ContactError::UnknownBoundaryTag),
    };
    Ok(AdmittedContactLaneAnatomy::new(
        schema,
        location,
        interval,
        capacities,
        contact_limits,
        coefficients,
        fraction,
        boundary,
    )?)
}

struct Writer<'a> {
    output: &'a mut [u8],
    position: usize,
}

impl<'a> Writer<'a> {
    fn new(output: &'a mut [u8]) -> Self {
        Self {
            output,
            position: 0,
        }
    }

    fn bytes(&mut self, bytes: &[u8]) -> Result<(), ContactError> {
        let end = self
            .position
            .checked_add(bytes.len())
            .ok_or(ContactError::ResourceArithmeticOverflow)?;
        let destination = self
            .output
            .get_mut(self.position..end)
            .ok_or(ContactError::CodecTruncated)?;
        destination.copy_from_slice(bytes);
        self.position = end;
        Ok(())
    }

    fn u8(&mut self, value: u8) -> Result<(), ContactError> {
        self.bytes(&[value])
    }

    fn u32(&mut self, value: u32) -> Result<(), ContactError> {
        self.bytes(&value.to_le_bytes())
    }

    fn u64(&mut self, value: u64) -> Result<(), ContactError> {
        self.bytes(&value.to_le_bytes())
    }

    fn i64(&mut self, value: i64) -> Result<(), ContactError> {
        self.bytes(&value.to_le_bytes())
    }

    fn u128(&mut self, value: u128) -> Result<(), ContactError> {
        self.bytes(&value.to_le_bytes())
    }

    fn i128(&mut self, value: i128) -> Result<(), ContactError> {
        self.bytes(&value.to_le_bytes())
    }
}

struct Reader<'a> {
    input: &'a [u8],
    position: usize,
}

impl<'a> Reader<'a> {
    fn new(input: &'a [u8]) -> Self {
        Self { input, position: 0 }
    }

    fn array<const LENGTH: usize>(&mut self) -> Result<[u8; LENGTH], ContactError> {
        let end = self
            .position
            .checked_add(LENGTH)
            .ok_or(ContactError::ResourceArithmeticOverflow)?;
        let source = self
            .input
            .get(self.position..end)
            .ok_or(ContactError::CodecTruncated)?;
        let mut bytes = [0_u8; LENGTH];
        bytes.copy_from_slice(source);
        self.position = end;
        Ok(bytes)
    }

    fn u8(&mut self) -> Result<u8, ContactError> {
        Ok(self.array::<1>()?[0])
    }

    fn u32(&mut self) -> Result<u32, ContactError> {
        Ok(u32::from_le_bytes(self.array()?))
    }

    fn u64(&mut self) -> Result<u64, ContactError> {
        Ok(u64::from_le_bytes(self.array()?))
    }

    fn i64(&mut self) -> Result<i64, ContactError> {
        Ok(i64::from_le_bytes(self.array()?))
    }

    fn u128(&mut self) -> Result<u128, ContactError> {
        Ok(u128::from_le_bytes(self.array()?))
    }

    fn i128(&mut self) -> Result<i128, ContactError> {
        Ok(i128::from_le_bytes(self.array()?))
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ContactError {
    Quantum(QuantumError),
    EmptyLaneSet,
    SpeciesSchemaMismatch,
    IntervalMismatch,
    DuplicatePhysicalLocation,
    NonCanonicalLaneOrder,
    MoreContactsThanLanes,
    ObservationClockMismatch,
    UnknownPhysicalLocation,
    OverlappingContact,
    IntervalIndexOverflow,
    ResourceArithmeticOverflow,
    CodecLengthMismatch { expected: usize, actual: usize },
    CodecHeaderMismatch,
    CodecShapeMismatch,
    CodecTruncated,
    CodecInternalLengthMismatch,
    NonCanonicalClosedBoundary,
    UnknownBoundaryTag,
}

impl From<QuantumError> for ContactError {
    fn from(value: QuantumError) -> Self {
        Self::Quantum(value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    type Anatomy = LocalContactAnatomy<2, 1, 2>;
    type State = BoundContactState<2, 1, 2>;

    fn schema() -> SpeciesSchema<2, 1> {
        let unit = ExactUnit::new(PhysicalDimension::MoleculeCount, 1, 1).unwrap();
        SpeciesSchema::new(
            [501],
            [
                SpeciesDefinition::new(101, unit, 0, [1]).unwrap(),
                SpeciesDefinition::new(102, unit, 0, [1]).unwrap(),
            ],
        )
        .unwrap()
    }

    fn interval() -> ExactInterval {
        ExactInterval::new(1, 1_000, 77).unwrap()
    }

    fn location(lane: u32) -> PhysicalLocation {
        PhysicalLocation::new(1, 2, CompartmentSide::Cytosol, 3, lane, lane + 10).unwrap()
    }

    fn lane(
        schema: &SpeciesSchema<2, 1>,
        lane_code: u32,
        capacities: [u128; 2],
        fraction: FractionLaw,
    ) -> AdmittedContactLaneAnatomy<2, 1> {
        AdmittedContactLaneAnatomy::new(
            schema,
            location(lane_code),
            interval(),
            capacities,
            [capacities[0], 0],
            [-1, 1],
            fraction,
            ConservationBoundary::Closed,
        )
        .unwrap()
    }

    fn anatomy(fraction: FractionLaw) -> Anatomy {
        let schema = schema();
        LocalContactAnatomy::new(
            schema,
            interval(),
            [
                lane(
                    &schema,
                    11,
                    [2_000_000_000_000, 2_000_000_000_000],
                    fraction,
                ),
                lane(
                    &schema,
                    12,
                    [2_000_000_000_000, 2_000_000_000_000],
                    fraction,
                ),
            ],
        )
        .unwrap()
    }

    fn state(fraction: FractionLaw) -> State {
        BoundContactState::new(anatomy(fraction), 9, [[12, 0], [15, 0]], [0, 0]).unwrap()
    }

    fn observation(state: &State, lane: usize, occupied: u128) -> GeometryContactObservation<2> {
        GeometryContactObservation::new(
            state.anatomy().lanes()[lane].location(),
            state.anatomy().interval(),
            state.interval_index(),
            [occupied, 0],
        )
    }

    #[test]
    fn disjoint_contacts_settle_from_one_bound_predecessor() {
        let prior = state(FractionLaw::new(1, 1).unwrap());
        let contacts = admit_disjoint_geometry_contacts(
            &prior,
            [observation(&prior, 0, 4), observation(&prior, 1, 5)],
        )
        .unwrap();
        let result = settle_disjoint_contacts(contacts).unwrap();
        assert_eq!(result.extents_by_lane, [4, 5]);
        assert_eq!(result.successor.quantities(), &[[8, 4], [10, 5]]);
        assert_eq!(prior.quantities(), &[[12, 0], [15, 0]]);
        assert_eq!(result.successor.interval_index(), 10);
    }

    #[test]
    fn contact_order_only_changes_observation_storage_not_successor() {
        let prior = state(FractionLaw::new(1, 1).unwrap());
        let forward = settle_disjoint_contacts(
            admit_disjoint_geometry_contacts(
                &prior,
                [observation(&prior, 0, 4), observation(&prior, 1, 5)],
            )
            .unwrap(),
        )
        .unwrap();
        let reversed = settle_disjoint_contacts(
            admit_disjoint_geometry_contacts(
                &prior,
                [observation(&prior, 1, 5), observation(&prior, 0, 4)],
            )
            .unwrap(),
        )
        .unwrap();
        assert_eq!(forward, reversed);
    }

    #[test]
    fn overlapping_location_is_refused_without_priority() {
        let prior = state(FractionLaw::new(1, 1).unwrap());
        assert!(matches!(
            admit_disjoint_geometry_contacts(
                &prior,
                [observation(&prior, 0, 4), observation(&prior, 0, 3)],
            ),
            Err(ContactError::OverlappingContact)
        ));
        assert_eq!(prior.quantities(), &[[12, 0], [15, 0]]);
    }

    #[test]
    fn wrong_anatomy_location_or_clock_cannot_be_substituted() {
        let prior = state(FractionLaw::new(1, 1).unwrap());
        let alien_location =
            PhysicalLocation::new(9, 9, CompartmentSide::Extracellular, 9, 9, 9).unwrap();
        let alien = GeometryContactObservation::new(
            alien_location,
            prior.anatomy().interval(),
            prior.interval_index(),
            [1, 0],
        );
        assert!(matches!(
            admit_disjoint_geometry_contacts(&prior, [alien]),
            Err(ContactError::UnknownPhysicalLocation)
        ));
        let wrong_clock = GeometryContactObservation::new(
            prior.anatomy().lanes()[0].location(),
            prior.anatomy().interval(),
            prior.interval_index() + 1,
            [1, 0],
        );
        assert!(matches!(
            admit_disjoint_geometry_contacts(&prior, [wrong_clock]),
            Err(ContactError::ObservationClockMismatch)
        ));
    }

    #[test]
    fn lane_admitted_under_another_species_schema_is_refused() {
        let first_schema = schema();
        let admitted_lane = lane(
            &first_schema,
            11,
            [100, 100],
            FractionLaw::new(1, 1).unwrap(),
        );
        let ion_unit = ExactUnit::new(PhysicalDimension::IonCount, 1, 1).unwrap();
        let other_schema = SpeciesSchema::new(
            [501],
            [
                SpeciesDefinition::new(101, ion_unit, 0, [1]).unwrap(),
                SpeciesDefinition::new(102, ion_unit, 0, [1]).unwrap(),
            ],
        )
        .unwrap();
        assert_eq!(
            LocalContactAnatomy::new(other_schema, interval(), [admitted_lane]),
            Err(ContactError::SpeciesSchemaMismatch)
        );
    }

    #[test]
    fn anatomy_lane_order_is_structurally_canonical() {
        let value = schema();
        let later = lane(&value, 12, [100, 100], FractionLaw::new(1, 1).unwrap());
        let earlier = lane(&value, 11, [100, 100], FractionLaw::new(1, 1).unwrap());
        assert_eq!(
            LocalContactAnatomy::new(value, interval(), [later, earlier]),
            Err(ContactError::NonCanonicalLaneOrder)
        );
    }

    #[test]
    fn requirement_counts_every_declared_success_path_pass() {
        let requirement = derive_contact_requirement::<2, 1, 2, 2>().unwrap();
        assert_eq!(requirement.observations, 2);
        assert_eq!(requirement.lanes, 2);
        assert_eq!(requirement.species, 2);
        assert_eq!(requirement.clock_comparisons, 4);
        assert_eq!(requirement.location_comparisons, 4);
        assert_eq!(requirement.admission_species_visits, 8);
        assert_eq!(requirement.transition_lane_visits, 2);
        assert_eq!(requirement.state_species_copies, 4);
        assert_eq!(requirement.state_remainder_copies, 2);
        assert_eq!(requirement.extent_slot_initializations, 2);
        assert_eq!(requirement.transition_species_visits, 16);
        assert_eq!(requirement.fraction_settlements, 2);
        assert_eq!(requirement.successor_clock_steps, 1);
        assert_eq!(
            requirement.successor_anatomy_payload_bytes,
            size_of::<Anatomy>()
        );
        assert_eq!(requirement.resident_state_payload_bytes, size_of::<State>());
        assert!(requirement.occupancy_payload_bytes > 0);
        assert!(requirement.transition_payload_bytes > 0);
        assert_eq!(
            requirement.canonical_serialized_bytes,
            canonical_state_bytes::<2, 1, 2>().unwrap()
        );
    }

    #[test]
    fn empty_shapes_have_no_false_resource_requirement() {
        assert_eq!(
            derive_contact_requirement::<0, 0, 1, 0>(),
            Err(ContactError::Quantum(QuantumError::EmptySpeciesSet))
        );
        assert_eq!(
            derive_contact_requirement::<1, 0, 0, 0>(),
            Err(ContactError::EmptyLaneSet)
        );
    }

    #[test]
    fn exact_codec_restart_preserves_anatomy_state_and_successor() {
        let prior = state(FractionLaw::new(1, 3).unwrap());
        let required = canonical_state_bytes::<2, 1, 2>().unwrap();
        let mut storage = [0_u8; 2_048];
        assert!(required <= storage.len());
        encode_bound_contact_state(&prior, &mut storage[..required]).unwrap();
        let restored = decode_bound_contact_state::<2, 1, 2>(&storage[..required]).unwrap();
        assert_eq!(restored, prior);
        let uninterrupted = settle_disjoint_contacts(
            admit_disjoint_geometry_contacts(&prior, [observation(&prior, 0, 6)]).unwrap(),
        )
        .unwrap();
        let restored_observation = observation(&restored, 0, 6);
        let after_restart = settle_disjoint_contacts(
            admit_disjoint_geometry_contacts(&restored, [restored_observation]).unwrap(),
        )
        .unwrap();
        assert_eq!(after_restart, uninterrupted);
    }

    #[test]
    fn codec_rejects_tampered_structural_identity() {
        let prior = state(FractionLaw::new(1, 3).unwrap());
        let required = canonical_state_bytes::<2, 1, 2>().unwrap();
        let mut storage = [0_u8; 2_048];
        encode_bound_contact_state(&prior, &mut storage[..required]).unwrap();
        // Header (36), one moiety code (4), species code (4), then dimension.
        storage[44] = 255;
        assert!(matches!(
            decode_bound_contact_state::<2, 1, 2>(&storage[..required]),
            Err(ContactError::Quantum(
                QuantumError::UnknownPhysicalDimension
            ))
        ));
    }

    #[test]
    fn active_age_keeps_payload_and_work_constant() {
        let fraction = FractionLaw::new(1, 1_000_000_000_000).unwrap();
        let anatomy = anatomy(fraction);
        let mut current =
            BoundContactState::new(anatomy, 0, [[1_000_000_000_000, 0], [1, 0]], [0, 0]).unwrap();
        let expected = derive_contact_requirement::<2, 1, 2, 1>().unwrap();
        let width = size_of::<State>();
        let mut total_extent = 0_u128;
        let mut active_intervals = 0_usize;
        for _ in 0..100_000 {
            let occupied = current.quantities()[0][0];
            let reached = observation(&current, 0, occupied);
            let occupancy = admit_disjoint_geometry_contacts(&current, [reached]).unwrap();
            assert_eq!(occupancy.requirement(), expected);
            let transition = settle_disjoint_contacts(occupancy).unwrap();
            total_extent += transition.extents_by_lane[0];
            if transition.extents_by_lane[0] > 0 {
                active_intervals += 1;
            }
            current = transition.successor;
            assert_eq!(size_of_val(&current), width);
        }
        assert!(total_extent > 0);
        assert!(active_intervals > 1_000);
        assert!(current.quantities()[0][0] > 0);
    }

    #[test]
    fn no_contact_advances_clock_without_inventing_reaction() {
        let prior = state(FractionLaw::new(1, 3).unwrap());
        let occupancy = admit_disjoint_geometry_contacts::<2, 1, 2, 0>(&prior, []).unwrap();
        let result = settle_disjoint_contacts(occupancy).unwrap();
        assert_eq!(result.extents_by_lane, [0, 0]);
        assert_eq!(result.successor.quantities(), prior.quantities());
        assert_eq!(result.successor.remainders(), prior.remainders());
        assert_eq!(result.successor.interval_index(), 10);
    }

    #[test]
    fn observation_accessors_are_exact() {
        let prior = state(FractionLaw::new(1, 1).unwrap());
        let value = observation(&prior, 0, 3);
        assert_eq!(value.location(), prior.anatomy().lanes()[0].location());
        assert_eq!(value.occupied_reactants(), &[3, 0]);
        assert_eq!(prior.anatomy().schema(), &schema());
    }
}
