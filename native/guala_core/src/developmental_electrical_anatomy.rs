//! Explicit growth-DNA electrical anatomy for a finite neuron cohort.
//!
//! This boundary never chooses a contact. It carries already-authored physical
//! source sites and exact contact material, then resolves that anatomy against
//! the same reached sites without using storage order, DSF values, coordinates,
//! simultaneous activity, similarity, or semantics. A missing or partial seed
//! is unavailable rather than inferred.

use crate::exact_rational::ExactRational;
use crate::neuron_source_anchor::{
    decode_neuron_source_site, encode_neuron_source_site, NeuronSourceSite,
};
use crate::sparse_electrical_contact::{
    ElectricalContactAnatomy, SparseElectricalAnatomy, SparseElectricalError,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DevelopmentalElectricalError {
    EmptySeed,
    DuplicateSeedSite,
    DuplicateReachedSite,
    ReachedAnatomyMismatch,
    InvalidContact(SparseElectricalError),
    InvalidEncoding,
    ArithmeticWidth,
}

impl From<SparseElectricalError> for DevelopmentalElectricalError {
    fn from(value: SparseElectricalError) -> Self {
        Self::InvalidContact(value)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DevelopmentalElectricalContact {
    left_seed_neuron: usize,
    right_seed_neuron: usize,
    conductance_picosiemens: ExactRational,
}

impl DevelopmentalElectricalContact {
    pub(crate) fn new(
        left_seed_neuron: usize,
        right_seed_neuron: usize,
        conductance_picosiemens: ExactRational,
        seed_neuron_count: usize,
    ) -> Result<Self, DevelopmentalElectricalError> {
        ElectricalContactAnatomy::new(
            left_seed_neuron,
            right_seed_neuron,
            conductance_picosiemens,
            seed_neuron_count,
        )?;
        Ok(Self {
            left_seed_neuron,
            right_seed_neuron,
            conductance_picosiemens,
        })
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct DevelopmentalElectricalSeed {
    source_sites: Box<[NeuronSourceSite]>,
    contacts: Box<[DevelopmentalElectricalContact]>,
}

impl DevelopmentalElectricalSeed {
    pub(crate) fn new(
        source_sites: Vec<NeuronSourceSite>,
        contacts: Vec<DevelopmentalElectricalContact>,
    ) -> Result<Self, DevelopmentalElectricalError> {
        if source_sites.is_empty() {
            return Err(DevelopmentalElectricalError::EmptySeed);
        }
        if has_duplicates(&source_sites) {
            return Err(DevelopmentalElectricalError::DuplicateSeedSite);
        }
        for contact in &contacts {
            ElectricalContactAnatomy::new(
                contact.left_seed_neuron,
                contact.right_seed_neuron,
                contact.conductance_picosiemens,
                source_sites.len(),
            )?;
        }
        Ok(Self {
            source_sites: source_sites.into_boxed_slice(),
            contacts: contacts.into_boxed_slice(),
        })
    }

    /// Resolve the authored anatomy into the caller's reached storage order.
    /// Every seed member must be present exactly once and no extra member is
    /// accepted. Only indices are remapped; topology and material are retained.
    pub(crate) fn resolve(
        &self,
        reached_source_sites: &[NeuronSourceSite],
    ) -> Result<SparseElectricalAnatomy, DevelopmentalElectricalError> {
        if reached_source_sites.len() != self.source_sites.len() {
            return Err(DevelopmentalElectricalError::ReachedAnatomyMismatch);
        }
        if has_duplicates(reached_source_sites) {
            return Err(DevelopmentalElectricalError::DuplicateReachedSite);
        }

        let mut reached_indices = Vec::new();
        reached_indices
            .try_reserve_exact(self.source_sites.len())
            .map_err(|_| DevelopmentalElectricalError::ReachedAnatomyMismatch)?;
        for seed_site in &self.source_sites {
            let reached_index = reached_source_sites
                .iter()
                .position(|reached_site| reached_site == seed_site)
                .ok_or(DevelopmentalElectricalError::ReachedAnatomyMismatch)?;
            reached_indices.push(reached_index);
        }

        let contacts = self
            .contacts
            .iter()
            .map(|contact| {
                ElectricalContactAnatomy::new(
                    reached_indices[contact.left_seed_neuron],
                    reached_indices[contact.right_seed_neuron],
                    contact.conductance_picosiemens,
                    reached_source_sites.len(),
                )
                .map_err(DevelopmentalElectricalError::InvalidContact)
            })
            .collect::<Result<Vec<_>, _>>()?;
        SparseElectricalAnatomy::new(reached_source_sites.len(), contacts)
            .map_err(DevelopmentalElectricalError::InvalidContact)
    }

    pub(crate) fn source_sites(&self) -> &[NeuronSourceSite] {
        &self.source_sites
    }

    pub(crate) fn encode(&self) -> Result<Vec<u8>, DevelopmentalElectricalError> {
        let mut encoded = Vec::new();
        encoded.extend_from_slice(DEVELOPMENTAL_SEED_MAGIC);
        push_usize(&mut encoded, self.source_sites.len())?;
        for site in &self.source_sites {
            let site = encode_neuron_source_site(site)
                .map_err(|_| DevelopmentalElectricalError::InvalidEncoding)?;
            push_usize(&mut encoded, site.len())?;
            encoded.extend_from_slice(&site);
        }
        push_usize(&mut encoded, self.contacts.len())?;
        for contact in &self.contacts {
            push_usize(&mut encoded, contact.left_seed_neuron)?;
            push_usize(&mut encoded, contact.right_seed_neuron)?;
            let (numerator, denominator) = contact.conductance_picosiemens.parts();
            encoded.extend_from_slice(&numerator.to_le_bytes());
            encoded.extend_from_slice(&denominator.to_le_bytes());
        }
        Ok(encoded)
    }

    pub(crate) fn decode(encoded: &[u8]) -> Result<Self, DevelopmentalElectricalError> {
        let mut reader = SeedReader::new(encoded);
        if reader.take(DEVELOPMENTAL_SEED_MAGIC.len())? != DEVELOPMENTAL_SEED_MAGIC {
            return Err(DevelopmentalElectricalError::InvalidEncoding);
        }
        let site_count = reader.usize()?;
        if site_count == 0 {
            return Err(DevelopmentalElectricalError::InvalidEncoding);
        }
        reader.require_records(site_count, 8)?;
        let mut source_sites = Vec::new();
        source_sites
            .try_reserve_exact(site_count)
            .map_err(|_| DevelopmentalElectricalError::ArithmeticWidth)?;
        for _ in 0..site_count {
            let length = reader.usize()?;
            source_sites.push(
                decode_neuron_source_site(reader.take(length)?)
                    .map_err(|_| DevelopmentalElectricalError::InvalidEncoding)?,
            );
        }
        let contact_count = reader.usize()?;
        reader.require_records(contact_count, 48)?;
        let mut contacts = Vec::new();
        contacts
            .try_reserve_exact(contact_count)
            .map_err(|_| DevelopmentalElectricalError::ArithmeticWidth)?;
        for _ in 0..contact_count {
            let left = reader.usize()?;
            let right = reader.usize()?;
            let conductance = ExactRational::new(reader.i128()?, reader.u128()?)
                .map_err(|_| DevelopmentalElectricalError::InvalidEncoding)?;
            contacts.push(DevelopmentalElectricalContact::new(
                left,
                right,
                conductance,
                site_count,
            )?);
        }
        if !reader.finished() {
            return Err(DevelopmentalElectricalError::InvalidEncoding);
        }
        let seed = Self::new(source_sites, contacts)?;
        if seed.encode()? != encoded {
            return Err(DevelopmentalElectricalError::InvalidEncoding);
        }
        Ok(seed)
    }
}

const DEVELOPMENTAL_SEED_MAGIC: &[u8; 8] = b"GLDES01\0";

fn push_usize(encoded: &mut Vec<u8>, value: usize) -> Result<(), DevelopmentalElectricalError> {
    encoded.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| DevelopmentalElectricalError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

struct SeedReader<'a> {
    encoded: &'a [u8],
    cursor: usize,
}

impl<'a> SeedReader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self { encoded, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], DevelopmentalElectricalError> {
        let end = self
            .cursor
            .checked_add(count)
            .ok_or(DevelopmentalElectricalError::ArithmeticWidth)?;
        let result = self
            .encoded
            .get(self.cursor..end)
            .ok_or(DevelopmentalElectricalError::InvalidEncoding)?;
        self.cursor = end;
        Ok(result)
    }

    fn usize(&mut self) -> Result<usize, DevelopmentalElectricalError> {
        usize::try_from(u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| DevelopmentalElectricalError::InvalidEncoding)?,
        ))
        .map_err(|_| DevelopmentalElectricalError::ArithmeticWidth)
    }

    fn i128(&mut self) -> Result<i128, DevelopmentalElectricalError> {
        Ok(i128::from_le_bytes(self.take(16)?.try_into().map_err(
            |_| DevelopmentalElectricalError::InvalidEncoding,
        )?))
    }

    fn u128(&mut self) -> Result<u128, DevelopmentalElectricalError> {
        Ok(u128::from_le_bytes(self.take(16)?.try_into().map_err(
            |_| DevelopmentalElectricalError::InvalidEncoding,
        )?))
    }

    fn require_records(
        &self,
        count: usize,
        minimum_bytes: usize,
    ) -> Result<(), DevelopmentalElectricalError> {
        let required = count
            .checked_mul(minimum_bytes)
            .ok_or(DevelopmentalElectricalError::ArithmeticWidth)?;
        if self.encoded.len().saturating_sub(self.cursor) < required {
            return Err(DevelopmentalElectricalError::InvalidEncoding);
        }
        Ok(())
    }

    fn finished(&self) -> bool {
        self.cursor == self.encoded.len()
    }
}

fn has_duplicates(source_sites: &[NeuronSourceSite]) -> bool {
    source_sites
        .iter()
        .enumerate()
        .any(|(index, site)| source_sites[..index].contains(site))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sparse_electrical_contact::{
        decode_sparse_electrical_cell, encode_sparse_electrical_cell, SparseElectricalState,
    };

    fn seed(neuron_count: usize) -> DevelopmentalElectricalSeed {
        let sites = (0..neuron_count)
            .map(|index| NeuronSourceSite::fixture(u32::try_from(index).unwrap()))
            .collect::<Vec<_>>();
        let contacts = (1..neuron_count)
            .map(|right| {
                DevelopmentalElectricalContact::new(
                    right - 1,
                    right,
                    ExactRational::integer(1),
                    neuron_count,
                )
                .unwrap()
            })
            .collect::<Vec<_>>();
        DevelopmentalElectricalSeed::new(sites, contacts).unwrap()
    }

    #[test]
    fn one_neuron_seed_is_exactly_contact_free() {
        let seed = seed(1);
        let reached = vec![NeuronSourceSite::fixture(0)];
        let resolved = seed.resolve(&reached).unwrap();
        assert_eq!(resolved.neuron_count(), 1);
        assert_eq!(resolved.contact_count(), 0);
    }

    #[test]
    fn three_neuron_seed_retains_only_its_two_authored_contacts() {
        let seed = seed(3);
        let reached = (0..3).map(NeuronSourceSite::fixture).collect::<Vec<_>>();
        let resolved = seed.resolve(&reached).unwrap();
        assert_eq!(
            resolved.contact_endpoints().collect::<Vec<_>>(),
            [(0, 1), (1, 2)]
        );
    }

    #[test]
    fn four_neuron_resolution_does_not_derive_topology_from_storage_order() {
        let seed = seed(4);
        let mut reached = (0..4).map(NeuronSourceSite::fixture).collect::<Vec<_>>();
        reached.reverse();
        let resolved = seed.resolve(&reached).unwrap();
        let source_pairs = resolved
            .contact_endpoints()
            .map(|(left, right)| {
                let mut pair = [
                    reached[left].topology_index(),
                    reached[right].topology_index(),
                ];
                pair.sort_unstable();
                pair
            })
            .collect::<Vec<_>>();
        assert_eq!(source_pairs, [[0, 1], [1, 2], [2, 3]]);
    }

    #[test]
    fn partial_or_substituted_anatomy_is_unavailable() {
        let seed = seed(4);
        assert_eq!(
            seed.resolve(&[
                NeuronSourceSite::fixture(0),
                NeuronSourceSite::fixture(1),
                NeuronSourceSite::fixture(2),
            ]),
            Err(DevelopmentalElectricalError::ReachedAnatomyMismatch)
        );
        assert_eq!(
            seed.resolve(&[
                NeuronSourceSite::fixture(0),
                NeuronSourceSite::fixture(1),
                NeuronSourceSite::fixture(2),
                NeuronSourceSite::fixture(9),
            ]),
            Err(DevelopmentalElectricalError::ReachedAnatomyMismatch)
        );
    }

    #[test]
    fn expressed_four_neuron_anatomy_cold_restores_exactly() {
        let seed = seed(4);
        let reached = (0..4).map(NeuronSourceSite::fixture).collect::<Vec<_>>();
        let anatomy = seed.resolve(&reached).unwrap();
        let state = SparseElectricalState::genesis(&anatomy);
        let encoded = encode_sparse_electrical_cell(&anatomy, &state).unwrap();
        let (restored_anatomy, restored_state) = decode_sparse_electrical_cell(&encoded).unwrap();
        assert_eq!(restored_anatomy, anatomy);
        assert_eq!(restored_state, state);
        assert_eq!(
            encode_sparse_electrical_cell(&restored_anatomy, &restored_state).unwrap(),
            encoded
        );
    }

    #[test]
    fn unexpressed_four_neuron_seed_cold_restores_exactly() {
        let seed = seed(4);
        let encoded = seed.encode().unwrap();
        let restored = DevelopmentalElectricalSeed::decode(&encoded).unwrap();
        assert_eq!(restored, seed);
        assert_eq!(restored.encode().unwrap(), encoded);
    }
}
