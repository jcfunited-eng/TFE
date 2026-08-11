//! Compact physical declaration of Guala's source-independent resting neurons.
//!
//! The declaration is not a capacity label.  Every declared cell has one
//! reversible lineage ordinal, one exact organism-relative place, and one
//! versioned quiescent neuron law.  Identical, untouched rest state is carried
//! once; a reached cell is materialized into its own complete state and can
//! never be merged back.  Selection is direct arithmetic over geography, not
//! a population scan.

use crate::complete_neuron::{
    encode_neuron_physical_cell, NeuronAnatomyCodecError, NeuronPhysicalAnatomy,
    NeuronPhysicalState,
};
use crate::declared_geometric_anatomy::DeclaredNeuronPlace;
use crate::exact_rational::ExactRational;
use crate::sparse_electrical_contact::{
    encode_sparse_electrical_cell, ElectricalContactAnatomy, SparseElectricalAnatomy,
    SparseElectricalError, SparseElectricalState,
};
use crate::virtual_material_neuron_genesis::{
    create_quiescent_virtual_material_neuron, VirtualMaterialGenesisError,
};

const MAGIC: &[u8; 8] = b"GLDRP01\0";
const VERSION: u16 = 1;

/// Six mounted receptor projection layers followed by eight intrinsic/body/
/// effector projection territories ratified in the population ledger.  These
/// are physical places and future contact boundaries, not meanings, owners,
/// services, or claims that the corresponding function is active.
pub(crate) const DEVELOPMENTAL_PROJECTION_LAYER_COUNT: usize = 14;

const PROJECTION_NAMES: [&str; DEVELOPMENTAL_PROJECTION_LAYER_COUNT] = [
    "optical receptor projection",
    "acoustic receptor projection",
    "contact receptor projection",
    "airborne chemical receptor projection",
    "oral chemical receptor projection",
    "body and balance receptor projection",
    "local sensory integration territory",
    "cross-sensory association territory",
    "body and fluid regulation territory",
    "recurrent retention territory",
    "affective reach territory",
    "prediction and ordering territory",
    "motor and effector territory",
    "articulatory effector territory",
];

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum DevelopmentalRestingPopulationError {
    ArithmeticWidth,
    AdmissionInsufficient,
    InvalidEncoding,
    InvalidPlace,
    NeuronGenesis(VirtualMaterialGenesisError),
    NeuronCodec(NeuronAnatomyCodecError),
    Electrical(SparseElectricalError),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct MaterializedRestingNeuron {
    pub(crate) population_offset: u64,
    pub(crate) lineage_ordinal: u64,
    pub(crate) place: DeclaredNeuronPlace,
    pub(crate) anatomy: NeuronPhysicalAnatomy,
    pub(crate) state: NeuronPhysicalState,
}

/// One resource-admitted population of still-quiescent cells.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct DevelopmentalRestingPopulation {
    admitted_encoded_bytes: u64,
    predecessor_encoded_bytes: u64,
    independently_diverged_cell_bytes: u64,
    minimum_sparse_contact_bytes: u64,
    future_growth_reserve_bytes: u64,
    lineage_start_ordinal: u64,
    declared_cell_count: u64,
    layer_topology_starts: [u32; DEVELOPMENTAL_PROJECTION_LAYER_COUNT],
    materialized_offsets: Box<[u64]>,
}

impl DevelopmentalRestingPopulation {
    /// Admit the largest physically representable birth population while
    /// leaving at least one additional complete cell-plus-contact unit for
    /// later DNA growth.  Every admitted cell also carries one minimum sparse
    /// contact's byte reserve, so the compact declaration can lawfully diverge
    /// without stealing another cell's state.
    pub(crate) fn admit(
        admitted_encoded_bytes: usize,
        predecessor_encoded_bytes: usize,
        lineage_start_ordinal: u64,
        occupied_places: &[DeclaredNeuronPlace],
    ) -> Result<Self, DevelopmentalRestingPopulationError> {
        if lineage_start_ordinal == 0 {
            return Err(DevelopmentalRestingPopulationError::ArithmeticWidth);
        }
        let layer_topology_starts = layer_topology_starts(occupied_places)?;
        let sample = create_quiescent_virtual_material_neuron(DeclaredNeuronPlace::new(
            DEVELOPMENTAL_PROJECTION_LAYER_COUNT as u32,
            0,
        ))
        .map_err(DevelopmentalRestingPopulationError::NeuronGenesis)?;
        let independently_diverged_cell_bytes =
            encode_neuron_physical_cell(&sample.anatomy, &sample.state)
                .map_err(DevelopmentalRestingPopulationError::NeuronCodec)?
                .len();
        let minimum_sparse_contact_bytes = measured_sparse_contact_bytes()?;
        let unit_bytes = independently_diverged_cell_bytes
            .checked_add(minimum_sparse_contact_bytes)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let descriptor_bytes = Self::fixed_encoded_bytes()?;
        let population_field_bytes = std::mem::size_of::<u64>()
            .checked_add(descriptor_bytes)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let available = admitted_encoded_bytes
            .checked_sub(predecessor_encoded_bytes)
            .and_then(|value| value.checked_sub(population_field_bytes))
            .ok_or(DevelopmentalRestingPopulationError::AdmissionInsufficient)?;
        let representable_units = available / unit_bytes;
        if representable_units <= DEVELOPMENTAL_PROJECTION_LAYER_COUNT {
            return Err(DevelopmentalRestingPopulationError::AdmissionInsufficient);
        }
        let declared_cell_count = representable_units - 1;
        let future_growth_reserve_bytes = available
            .checked_sub(
                declared_cell_count
                    .checked_mul(unit_bytes)
                    .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            )
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        if future_growth_reserve_bytes < unit_bytes {
            return Err(DevelopmentalRestingPopulationError::AdmissionInsufficient);
        }
        let declared_cell_count = u64::try_from(declared_cell_count)
            .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        lineage_start_ordinal
            .checked_add(declared_cell_count)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let population = Self {
            admitted_encoded_bytes: u64::try_from(admitted_encoded_bytes)
                .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            predecessor_encoded_bytes: u64::try_from(predecessor_encoded_bytes)
                .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            independently_diverged_cell_bytes: u64::try_from(independently_diverged_cell_bytes)
                .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            minimum_sparse_contact_bytes: u64::try_from(minimum_sparse_contact_bytes)
                .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            future_growth_reserve_bytes: u64::try_from(future_growth_reserve_bytes)
                .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            lineage_start_ordinal,
            declared_cell_count,
            layer_topology_starts,
            materialized_offsets: Box::new([]),
        };
        population.validate()?;
        Ok(population)
    }

    pub(crate) fn declared_cell_count(&self) -> u64 {
        self.declared_cell_count
    }

    pub(crate) fn resting_cell_count(&self) -> u64 {
        self.declared_cell_count - self.materialized_offsets.len() as u64
    }

    pub(crate) fn lineage_start_ordinal(&self) -> u64 {
        self.lineage_start_ordinal
    }

    pub(crate) fn lineage_end_exclusive(&self) -> u64 {
        self.lineage_start_ordinal + self.declared_cell_count
    }

    pub(crate) fn independently_diverged_cell_bytes(&self) -> u64 {
        self.independently_diverged_cell_bytes
    }

    pub(crate) fn minimum_sparse_contact_bytes(&self) -> u64 {
        self.minimum_sparse_contact_bytes
    }

    pub(crate) fn future_growth_reserve_bytes(&self) -> u64 {
        self.future_growth_reserve_bytes
    }

    /// Admit one newly grown complete cell plus its first sparse contact from
    /// the population's already-accounted future-growth material.  This does
    /// not relabel a resting cell or expand the encoded-byte envelope: the
    /// exact unit moves from future reserve to independently retained state.
    pub(crate) fn admit_one_external_growth_unit(
        &self,
    ) -> Result<Self, DevelopmentalRestingPopulationError> {
        let unit = self
            .independently_diverged_cell_bytes
            .checked_add(self.minimum_sparse_contact_bytes)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let successor = Self {
            predecessor_encoded_bytes: self
                .predecessor_encoded_bytes
                .checked_add(unit)
                .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            future_growth_reserve_bytes: self
                .future_growth_reserve_bytes
                .checked_sub(unit)
                .ok_or(DevelopmentalRestingPopulationError::AdmissionInsufficient)?,
            ..self.clone()
        };
        successor.validate()?;
        Ok(successor)
    }

    pub(crate) fn projection_name(layer: u32) -> Option<&'static str> {
        PROJECTION_NAMES.get(usize::try_from(layer).ok()?).copied()
    }

    /// Direct O(1) offset-to-place selection.  Population order interleaves
    /// the fourteen physical layers at each local topology index, so no layer
    /// is silently omitted and no population scan or semantic choice occurs.
    pub(crate) fn declared_place(
        &self,
        population_offset: u64,
    ) -> Result<DeclaredNeuronPlace, DevelopmentalRestingPopulationError> {
        if population_offset >= self.declared_cell_count {
            return Err(DevelopmentalRestingPopulationError::InvalidPlace);
        }
        let layer =
            usize::try_from(population_offset % DEVELOPMENTAL_PROJECTION_LAYER_COUNT as u64)
                .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let local_index = population_offset / DEVELOPMENTAL_PROJECTION_LAYER_COUNT as u64;
        let topology_index = u64::from(self.layer_topology_starts[layer])
            .checked_add(local_index)
            .and_then(|value| u32::try_from(value).ok())
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        Ok(DeclaredNeuronPlace::new(
            u32::try_from(layer)
                .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            topology_index,
        ))
    }

    /// Direct place-to-offset selection.  This is the inverse of
    /// `declared_place` and touches no other cell.
    pub(crate) fn population_offset(&self, place: DeclaredNeuronPlace) -> Option<u64> {
        let layer = usize::try_from(place.layer()).ok()?;
        let start = *self.layer_topology_starts.get(layer)?;
        let local = place.topology_index().checked_sub(start)?;
        let offset = u64::from(local)
            .checked_mul(DEVELOPMENTAL_PROJECTION_LAYER_COUNT as u64)?
            .checked_add(u64::try_from(layer).ok()?)?;
        (offset < self.declared_cell_count).then_some(offset)
    }

    pub(crate) fn materialized_lineage_ordinal(
        &self,
        place: DeclaredNeuronPlace,
    ) -> Option<u64> {
        let offset = self.population_offset(place)?;
        self.materialized_offsets.binary_search(&offset).ok()?;
        self.lineage_start_ordinal.checked_add(offset)
    }

    /// Claim the first still-quiescent place in one declared projection layer.
    /// The population is interleaved, so this walks only that layer's already
    /// reached prefix and never scans or instantiates the resting population.
    pub(crate) fn claim_next_in_layer(
        &self,
        layer: u32,
    ) -> Result<(Self, MaterializedRestingNeuron), DevelopmentalRestingPopulationError> {
        let layer = usize::try_from(layer)
            .map_err(|_| DevelopmentalRestingPopulationError::InvalidPlace)?;
        if layer >= DEVELOPMENTAL_PROJECTION_LAYER_COUNT {
            return Err(DevelopmentalRestingPopulationError::InvalidPlace);
        }
        let stride = DEVELOPMENTAL_PROJECTION_LAYER_COUNT as u64;
        let mut offset = u64::try_from(layer)
            .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        while offset < self.declared_cell_count {
            if self.materialized_offsets.binary_search(&offset).is_err() {
                return self.claim(offset);
            }
            offset = offset
                .checked_add(stride)
                .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        }
        Err(DevelopmentalRestingPopulationError::AdmissionInsufficient)
    }

    pub(crate) fn materialize(
        &self,
        population_offset: u64,
    ) -> Result<MaterializedRestingNeuron, DevelopmentalRestingPopulationError> {
        if self
            .materialized_offsets
            .binary_search(&population_offset)
            .is_ok()
        {
            return Err(DevelopmentalRestingPopulationError::InvalidPlace);
        }
        let place = self.declared_place(population_offset)?;
        let neuron = create_quiescent_virtual_material_neuron(place)
            .map_err(DevelopmentalRestingPopulationError::NeuronGenesis)?;
        Ok(MaterializedRestingNeuron {
            population_offset,
            lineage_ordinal: self
                .lineage_start_ordinal
                .checked_add(population_offset)
                .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            place,
            anatomy: neuron.anatomy,
            state: neuron.state,
        })
    }

    /// Move one declared cell across the source-contact boundary.  The cell's
    /// lineage and place do not change.  Only its offset leaves the shared
    /// quiescent population; the independently retained reached cell is then
    /// carried by the ordinary cohort state.
    pub(crate) fn claim(
        &self,
        population_offset: u64,
    ) -> Result<(Self, MaterializedRestingNeuron), DevelopmentalRestingPopulationError> {
        let materialized = self.materialize(population_offset)?;
        let mut offsets = self.materialized_offsets.to_vec();
        match offsets.binary_search(&population_offset) {
            Ok(_) => return Err(DevelopmentalRestingPopulationError::InvalidPlace),
            Err(index) => offsets.insert(index, population_offset),
        }
        let descriptor_growth = u64::try_from(std::mem::size_of::<u64>())
            .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let unit = self
            .independently_diverged_cell_bytes
            .checked_add(self.minimum_sparse_contact_bytes)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let released_reserve = unit
            .checked_sub(descriptor_growth)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let successor = Self {
            future_growth_reserve_bytes: self
                .future_growth_reserve_bytes
                .checked_add(released_reserve)
                .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            materialized_offsets: offsets.into_boxed_slice(),
            ..self.clone()
        };
        successor.validate()?;
        Ok((successor, materialized))
    }

    /// Return one falsely reached cell to the exact shared quiescent
    /// declaration.  This is the inverse of `claim`: it removes only the
    /// named materialized offset and restores the bytes that had been released
    /// for that cell's independent body and first sparse contact.  No other
    /// cell, lineage range, or developmental geography changes.
    pub(crate) fn release_claimed_place(
        &self,
        place: DeclaredNeuronPlace,
    ) -> Result<Self, DevelopmentalRestingPopulationError> {
        let population_offset = self
            .population_offset(place)
            .ok_or(DevelopmentalRestingPopulationError::InvalidPlace)?;
        let mut offsets = self.materialized_offsets.to_vec();
        let index = offsets
            .binary_search(&population_offset)
            .map_err(|_| DevelopmentalRestingPopulationError::InvalidPlace)?;
        offsets.remove(index);

        let descriptor_growth = u64::try_from(std::mem::size_of::<u64>())
            .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let unit = self
            .independently_diverged_cell_bytes
            .checked_add(self.minimum_sparse_contact_bytes)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let released_reserve = unit
            .checked_sub(descriptor_growth)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let successor = Self {
            future_growth_reserve_bytes: self
                .future_growth_reserve_bytes
                .checked_sub(released_reserve)
                .ok_or(DevelopmentalRestingPopulationError::InvalidEncoding)?,
            materialized_offsets: offsets.into_boxed_slice(),
            ..self.clone()
        };
        successor.validate()?;
        Ok(successor)
    }

    pub(crate) fn encode(&self) -> Result<Vec<u8>, DevelopmentalRestingPopulationError> {
        self.validate()?;
        let mut output = Vec::with_capacity(
            Self::fixed_encoded_bytes()?
                .checked_add(
                    self.materialized_offsets
                        .len()
                        .checked_mul(std::mem::size_of::<u64>())
                        .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?,
                )
                .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?,
        );
        output.extend_from_slice(MAGIC);
        output.extend_from_slice(&VERSION.to_le_bytes());
        for value in [
            self.admitted_encoded_bytes,
            self.predecessor_encoded_bytes,
            self.independently_diverged_cell_bytes,
            self.minimum_sparse_contact_bytes,
            self.future_growth_reserve_bytes,
            self.lineage_start_ordinal,
            self.declared_cell_count,
        ] {
            output.extend_from_slice(&value.to_le_bytes());
        }
        for start in self.layer_topology_starts {
            output.extend_from_slice(&start.to_le_bytes());
        }
        output.extend_from_slice(
            &u64::try_from(self.materialized_offsets.len())
                .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?
                .to_le_bytes(),
        );
        for offset in &self.materialized_offsets {
            output.extend_from_slice(&offset.to_le_bytes());
        }
        Ok(output)
    }

    pub(crate) fn decode(encoded: &[u8]) -> Result<Self, DevelopmentalRestingPopulationError> {
        let mut reader = Reader::new(encoded);
        if reader.take(MAGIC.len())? != MAGIC || reader.u16()? != VERSION {
            return Err(DevelopmentalRestingPopulationError::InvalidEncoding);
        }
        let admitted_encoded_bytes = reader.u64()?;
        let predecessor_encoded_bytes = reader.u64()?;
        let independently_diverged_cell_bytes = reader.u64()?;
        let minimum_sparse_contact_bytes = reader.u64()?;
        let future_growth_reserve_bytes = reader.u64()?;
        let lineage_start_ordinal = reader.u64()?;
        let declared_cell_count = reader.u64()?;
        let mut layer_topology_starts = [0u32; DEVELOPMENTAL_PROJECTION_LAYER_COUNT];
        for start in &mut layer_topology_starts {
            *start = reader.u32()?;
        }
        let materialized_count = usize::try_from(reader.u64()?)
            .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        if materialized_count > reader.remaining() / std::mem::size_of::<u64>() {
            return Err(DevelopmentalRestingPopulationError::InvalidEncoding);
        }
        let mut materialized_offsets = Vec::new();
        materialized_offsets
            .try_reserve_exact(materialized_count)
            .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        for _ in 0..materialized_count {
            materialized_offsets.push(reader.u64()?);
        }
        if !reader.finished() {
            return Err(DevelopmentalRestingPopulationError::InvalidEncoding);
        }
        let population = Self {
            admitted_encoded_bytes,
            predecessor_encoded_bytes,
            independently_diverged_cell_bytes,
            minimum_sparse_contact_bytes,
            future_growth_reserve_bytes,
            lineage_start_ordinal,
            declared_cell_count,
            layer_topology_starts,
            materialized_offsets: materialized_offsets.into_boxed_slice(),
        };
        population.validate()?;
        if population.encode()? != encoded {
            return Err(DevelopmentalRestingPopulationError::InvalidEncoding);
        }
        Ok(population)
    }

    fn fixed_encoded_bytes() -> Result<usize, DevelopmentalRestingPopulationError> {
        MAGIC
            .len()
            .checked_add(std::mem::size_of::<u16>())
            .and_then(|value| value.checked_add(7 * std::mem::size_of::<u64>()))
            .and_then(|value| {
                value.checked_add(DEVELOPMENTAL_PROJECTION_LAYER_COUNT * std::mem::size_of::<u32>())
            })
            .and_then(|value| value.checked_add(std::mem::size_of::<u64>()))
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)
    }

    fn validate(&self) -> Result<(), DevelopmentalRestingPopulationError> {
        let unit = self
            .independently_diverged_cell_bytes
            .checked_add(self.minimum_sparse_contact_bytes)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let descriptor_bytes = u64::try_from(
            Self::fixed_encoded_bytes()?
                .checked_add(
                    self.materialized_offsets
                        .len()
                        .checked_mul(std::mem::size_of::<u64>())
                        .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?,
                )
                .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?,
        )
        .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let resting_cells = self
            .declared_cell_count
            .checked_sub(
                u64::try_from(self.materialized_offsets.len())
                    .map_err(|_| DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            )
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let reserved_bytes = self
            .predecessor_encoded_bytes
            .checked_add(descriptor_bytes)
            .and_then(|value| value.checked_add(std::mem::size_of::<u64>() as u64))
            .and_then(|value| value.checked_add(resting_cells.checked_mul(unit)?))
            .and_then(|value| value.checked_add(self.future_growth_reserve_bytes))
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        if self.admitted_encoded_bytes == 0
            || self.predecessor_encoded_bytes >= self.admitted_encoded_bytes
            || self.independently_diverged_cell_bytes == 0
            || self.minimum_sparse_contact_bytes == 0
            || self.lineage_start_ordinal == 0
            || self.declared_cell_count < DEVELOPMENTAL_PROJECTION_LAYER_COUNT as u64
            || usize::try_from(self.declared_cell_count).is_err()
            || reserved_bytes != self.admitted_encoded_bytes
            || self
                .lineage_start_ordinal
                .checked_add(self.declared_cell_count)
                .is_none()
            || self
                .materialized_offsets
                .iter()
                .enumerate()
                .any(|(index, offset)| {
                    *offset >= self.declared_cell_count
                        || self.materialized_offsets[..index]
                            .last()
                            .is_some_and(|prior| prior >= offset)
                })
        {
            return Err(DevelopmentalRestingPopulationError::InvalidEncoding);
        }
        // Prove the final place is still representable; every earlier offset
        // then fits the same monotonic layer-local topology law.
        self.declared_place(self.declared_cell_count - 1)?;
        Ok(())
    }
}

fn layer_topology_starts(
    occupied_places: &[DeclaredNeuronPlace],
) -> Result<[u32; DEVELOPMENTAL_PROJECTION_LAYER_COUNT], DevelopmentalRestingPopulationError> {
    let mut starts = [0u32; DEVELOPMENTAL_PROJECTION_LAYER_COUNT];
    for place in occupied_places {
        let Ok(layer) = usize::try_from(place.layer()) else {
            return Err(DevelopmentalRestingPopulationError::ArithmeticWidth);
        };
        if let Some(start) = starts.get_mut(layer) {
            *start = (*start).max(
                place
                    .topology_index()
                    .checked_add(1)
                    .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?,
            );
        }
    }
    Ok(starts)
}

fn measured_sparse_contact_bytes() -> Result<usize, DevelopmentalRestingPopulationError> {
    let empty_anatomy = SparseElectricalAnatomy::new(2, Vec::new())
        .map_err(DevelopmentalRestingPopulationError::Electrical)?;
    let empty_state = SparseElectricalState::genesis(&empty_anatomy);
    let empty = encode_sparse_electrical_cell(&empty_anatomy, &empty_state)
        .map_err(DevelopmentalRestingPopulationError::Electrical)?;
    let contact = ElectricalContactAnatomy::new(0, 1, ExactRational::integer(1), 2)
        .map_err(DevelopmentalRestingPopulationError::Electrical)?;
    let one_anatomy = SparseElectricalAnatomy::new(2, vec![contact])
        .map_err(DevelopmentalRestingPopulationError::Electrical)?;
    let one_state = SparseElectricalState::genesis(&one_anatomy);
    let one = encode_sparse_electrical_cell(&one_anatomy, &one_state)
        .map_err(DevelopmentalRestingPopulationError::Electrical)?;
    one.len()
        .checked_sub(empty.len())
        .filter(|value| *value > 0)
        .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)
}

struct Reader<'a> {
    encoded: &'a [u8],
    cursor: usize,
}

impl<'a> Reader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self { encoded, cursor: 0 }
    }

    fn take(&mut self, width: usize) -> Result<&'a [u8], DevelopmentalRestingPopulationError> {
        let end = self
            .cursor
            .checked_add(width)
            .ok_or(DevelopmentalRestingPopulationError::ArithmeticWidth)?;
        let value = self
            .encoded
            .get(self.cursor..end)
            .ok_or(DevelopmentalRestingPopulationError::InvalidEncoding)?;
        self.cursor = end;
        Ok(value)
    }

    fn u16(&mut self) -> Result<u16, DevelopmentalRestingPopulationError> {
        Ok(u16::from_le_bytes(self.take(2)?.try_into().map_err(
            |_| DevelopmentalRestingPopulationError::InvalidEncoding,
        )?))
    }

    fn u32(&mut self) -> Result<u32, DevelopmentalRestingPopulationError> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().map_err(
            |_| DevelopmentalRestingPopulationError::InvalidEncoding,
        )?))
    }

    fn u64(&mut self) -> Result<u64, DevelopmentalRestingPopulationError> {
        Ok(u64::from_le_bytes(self.take(8)?.try_into().map_err(
            |_| DevelopmentalRestingPopulationError::InvalidEncoding,
        )?))
    }

    fn remaining(&self) -> usize {
        self.encoded.len().saturating_sub(self.cursor)
    }

    fn finished(&self) -> bool {
        self.cursor == self.encoded.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::complete_neuron::{decode_neuron_physical_cell, sparse_physical_state_delta};

    #[test]
    fn admission_is_exact_compact_and_leaves_one_growth_unit() {
        let occupied = [
            DeclaredNeuronPlace::new(0, 26),
            DeclaredNeuronPlace::new(5, 3),
        ];
        let population =
            DevelopmentalRestingPopulation::admit(67_000_000, 7_790_000, 87, &occupied).unwrap();
        assert!(population.declared_cell_count() > 1_000);
        assert!(
            population.future_growth_reserve_bytes()
                >= population.independently_diverged_cell_bytes()
                    + population.minimum_sparse_contact_bytes()
        );
        assert_eq!(
            population.declared_place(0).unwrap(),
            DeclaredNeuronPlace::new(0, 27)
        );
        assert_eq!(
            population.declared_place(5).unwrap(),
            DeclaredNeuronPlace::new(5, 4)
        );
        assert_eq!(
            population.declared_place(6).unwrap(),
            DeclaredNeuronPlace::new(6, 0)
        );
        let encoded = population.encode().unwrap();
        assert!(encoded.len() < 256);
        assert_eq!(
            DevelopmentalRestingPopulation::decode(&encoded).unwrap(),
            population
        );
    }

    #[test]
    fn direct_topology_selection_materializes_one_three_and_four_exact_cells() {
        let population =
            DevelopmentalRestingPopulation::admit(2_000_000, 100_000, 11, &[]).unwrap();
        for count in [1_u64, 3, 4] {
            for offset in 0..count {
                let cell = population.materialize(offset).unwrap();
                assert_eq!(population.population_offset(cell.place), Some(offset));
                assert_eq!(cell.lineage_ordinal, 11 + offset);
                assert!(sparse_physical_state_delta(&cell.state, &cell.state)
                    .unwrap()
                    .is_none());
                let encoded = encode_neuron_physical_cell(&cell.anatomy, &cell.state).unwrap();
                let (anatomy, state) = decode_neuron_physical_cell(&encoded).unwrap();
                assert_eq!(anatomy, cell.anatomy);
                assert_eq!(state, cell.state);
            }
        }

        let mut claimed = population.clone();
        for offset in 0..4 {
            let prior_resting = claimed.resting_cell_count();
            let (successor, cell) = claimed.claim(offset).unwrap();
            assert_eq!(cell.population_offset, offset);
            assert_eq!(successor.resting_cell_count(), prior_resting - 1);
            assert_eq!(
                successor.materialized_lineage_ordinal(cell.place),
                Some(cell.lineage_ordinal)
            );
            let encoded = successor.encode().unwrap();
            claimed = DevelopmentalRestingPopulation::decode(&encoded).unwrap();
        }
        assert!(claimed.claim(0).is_err());
    }

    #[test]
    fn all_projection_territories_receive_real_declared_cells() {
        let population = DevelopmentalRestingPopulation::admit(2_000_000, 100_000, 1, &[]).unwrap();
        for layer in 0..DEVELOPMENTAL_PROJECTION_LAYER_COUNT as u32 {
            let place = population.declared_place(u64::from(layer)).unwrap();
            assert_eq!(place.layer(), layer);
            assert!(DevelopmentalRestingPopulation::projection_name(layer).is_some());
        }
    }

    #[test]
    fn releasing_a_false_claim_is_the_exact_inverse_of_claiming_it() {
        let population =
            DevelopmentalRestingPopulation::admit(2_000_000, 100_000, 1, &[]).unwrap();
        let place = population.declared_place(6).unwrap();
        let offset = population.population_offset(place).unwrap();
        let (claimed, _) = population.claim(offset).unwrap();
        assert_ne!(claimed, population);
        assert_eq!(claimed.release_claimed_place(place).unwrap(), population);
    }

    #[test]
    fn next_layer_claim_walks_only_that_layers_reached_prefix() {
        let population =
            DevelopmentalRestingPopulation::admit(2_000_000, 100_000, 1, &[]).unwrap();
        let (one, first) = population.claim_next_in_layer(7).unwrap();
        let (two, second) = one.claim_next_in_layer(7).unwrap();
        assert_eq!(first.place.layer(), 7);
        assert_eq!(second.place.layer(), 7);
        assert_eq!(second.place.topology_index(), first.place.topology_index() + 1);
        assert_eq!(two.resting_cell_count(), population.resting_cell_count() - 2);
    }

    #[test]
    fn external_growth_moves_one_exact_unit_out_of_future_reserve() {
        let population =
            DevelopmentalRestingPopulation::admit(2_000_000, 100_000, 1, &[]).unwrap();
        let unit = population.independently_diverged_cell_bytes()
            + population.minimum_sparse_contact_bytes();
        let grown = population.admit_one_external_growth_unit().unwrap();
        assert_eq!(grown.resting_cell_count(), population.resting_cell_count());
        assert_eq!(grown.future_growth_reserve_bytes() + unit, population.future_growth_reserve_bytes());
        assert_eq!(grown.predecessor_encoded_bytes, population.predecessor_encoded_bytes + unit);
        assert_eq!(DevelopmentalRestingPopulation::decode(&grown.encode().unwrap()).unwrap(), grown);
    }
}
