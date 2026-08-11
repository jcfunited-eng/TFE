//! Sparse electrical contacts whose endpoints live in different resident
//! neuron cohorts.
//!
//! Cohorts keep their own recovery-fluid reservoirs and local contact state.
//! This fabric carries only stable neuron lineages, exact sparse contact
//! anatomy, and each contact's unresolved carrier phase.  It therefore lets
//! an external receptor physically reach an intrinsic neuron without merging
//! their bodies, copying a DSF result, scanning the resting population, or
//! introducing a semantic/database relationship.

use crate::exact_rational::ExactRational;
use crate::sparse_electrical_contact::{
    decode_sparse_electrical_cell, encode_sparse_electrical_cell,
    ElectricalContactAnatomy, SparseElectricalAnatomy, SparseElectricalError,
    SparseElectricalState,
};

const MAGIC: &[u8; 8] = b"GLREF01\0";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ResidentElectricalFabric {
    lineages: Box<[[u8; 16]]>,
    anatomy: SparseElectricalAnatomy,
    state: SparseElectricalState,
}

impl Default for ResidentElectricalFabric {
    fn default() -> Self {
        let anatomy = SparseElectricalAnatomy::new(1, Vec::new())
            .expect("one empty resident electrical vertex is valid");
        let state = SparseElectricalState::genesis(&anatomy);
        Self {
            lineages: Box::new([]),
            anatomy,
            state,
        }
    }
}

impl ResidentElectricalFabric {
    pub(crate) fn lineages(&self) -> &[[u8; 16]] {
        &self.lineages
    }

    pub(crate) fn contact_count(&self) -> usize {
        self.anatomy.contact_count()
    }

    pub(crate) fn anatomy(&self) -> &SparseElectricalAnatomy {
        &self.anatomy
    }

    pub(crate) fn state(&self) -> &SparseElectricalState {
        &self.state
    }

    pub(crate) fn contact_endpoints(
        &self,
    ) -> impl ExactSizeIterator<Item = (usize, usize)> + '_ {
        self.anatomy.contact_endpoints()
    }

    pub(crate) fn contains_contact(
        &self,
        left_lineage: [u8; 16],
        right_lineage: [u8; 16],
    ) -> bool {
        let Some(left) = self.lineages.iter().position(|lineage| *lineage == left_lineage) else {
            return false;
        };
        let Some(right) = self.lineages.iter().position(|lineage| *lineage == right_lineage) else {
            return false;
        };
        self.anatomy.contact_endpoints().any(|(a, b)| {
            (a == left && b == right) || (a == right && b == left)
        })
    }

    pub(crate) fn append_contact(
        &self,
        left_lineage: [u8; 16],
        right_lineage: [u8; 16],
        conductance_picosiemens: ExactRational,
    ) -> Result<Self, SparseElectricalError> {
        if left_lineage == [0; 16] || right_lineage == [0; 16] || left_lineage == right_lineage {
            return Err(SparseElectricalError::InvalidEndpoint);
        }
        let mut lineages = self.lineages.to_vec();
        let mut member = |lineage: [u8; 16]| {
            if let Some(index) = lineages.iter().position(|retained| *retained == lineage) {
                index
            } else {
                let index = lineages.len();
                lineages.push(lineage);
                index
            }
        };
        let left = member(left_lineage);
        let right = member(right_lineage);
        let neuron_count = lineages.len();
        let widened = self.anatomy.extend_neuron_count(neuron_count.max(1))?;
        let widened_state = SparseElectricalState::from_contact_states(
            &widened,
            self.state.contact_states().to_vec(),
        )?;
        let successor_anatomy = widened.append_contacts(vec![ElectricalContactAnatomy::new(
            left,
            right,
            conductance_picosiemens,
            neuron_count,
        )?])?;
        let successor_state = widened_state.append_genesis_contacts(&successor_anatomy)?;
        Ok(Self {
            lineages: lineages.into_boxed_slice(),
            anatomy: successor_anatomy,
            state: successor_state,
        })
    }

    pub(crate) fn with_contact_states(
        &self,
        contact_states: Vec<crate::sparse_electrical_contact::ElectricalContactState>,
    ) -> Result<Self, SparseElectricalError> {
        Ok(Self {
            lineages: self.lineages.clone(),
            anatomy: self.anatomy.clone(),
            state: SparseElectricalState::from_contact_states(&self.anatomy, contact_states)?,
        })
    }

    pub(crate) fn encode(&self) -> Result<Vec<u8>, SparseElectricalError> {
        if self.lineages.is_empty() {
            if self.contact_count() != 0 {
                return Err(SparseElectricalError::AnatomyStateWidth);
            }
            return Ok(Vec::new());
        }
        if self.lineages.len() != self.anatomy.neuron_count()
            || self.lineages.iter().enumerate().any(|(index, lineage)| {
                *lineage == [0; 16] || self.lineages[..index].contains(lineage)
            })
        {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        let electrical = encode_sparse_electrical_cell(&self.anatomy, &self.state)?;
        let mut encoded = Vec::new();
        encoded.extend_from_slice(MAGIC);
        encoded.extend_from_slice(
            &u64::try_from(self.lineages.len())
                .map_err(|_| SparseElectricalError::ArithmeticWidth)?
                .to_le_bytes(),
        );
        for lineage in &self.lineages {
            encoded.extend_from_slice(lineage);
        }
        encoded.extend_from_slice(
            &u64::try_from(electrical.len())
                .map_err(|_| SparseElectricalError::ArithmeticWidth)?
                .to_le_bytes(),
        );
        encoded.extend_from_slice(&electrical);
        Ok(encoded)
    }

    pub(crate) fn decode(encoded: &[u8]) -> Result<Self, SparseElectricalError> {
        if encoded.is_empty() {
            return Ok(Self::default());
        }
        let mut cursor = 0usize;
        let mut take = |count: usize| {
            let end = cursor
                .checked_add(count)
                .ok_or(SparseElectricalError::ArithmeticWidth)?;
            let value = encoded
                .get(cursor..end)
                .ok_or(SparseElectricalError::InvalidEncoding)?;
            cursor = end;
            Ok::<_, SparseElectricalError>(value)
        };
        if take(MAGIC.len())? != MAGIC {
            return Err(SparseElectricalError::InvalidEncoding);
        }
        let count = usize::try_from(u64::from_le_bytes(
            take(8)?
                .try_into()
                .map_err(|_| SparseElectricalError::InvalidEncoding)?,
        ))
        .map_err(|_| SparseElectricalError::ArithmeticWidth)?;
        if count == 0 {
            return Err(SparseElectricalError::InvalidEncoding);
        }
        let mut lineages = Vec::new();
        lineages
            .try_reserve_exact(count)
            .map_err(|_| SparseElectricalError::ArithmeticWidth)?;
        for _ in 0..count {
            lineages.push(
                take(16)?
                    .try_into()
                    .map_err(|_| SparseElectricalError::InvalidEncoding)?,
            );
        }
        if lineages.iter().enumerate().any(|(index, lineage)| {
            *lineage == [0; 16] || lineages[..index].contains(lineage)
        }) {
            return Err(SparseElectricalError::InvalidEncoding);
        }
        let electrical_length = usize::try_from(u64::from_le_bytes(
            take(8)?
                .try_into()
                .map_err(|_| SparseElectricalError::InvalidEncoding)?,
        ))
        .map_err(|_| SparseElectricalError::ArithmeticWidth)?;
        let electrical = take(electrical_length)?;
        if cursor != encoded.len() {
            return Err(SparseElectricalError::InvalidEncoding);
        }
        let (anatomy, state) = decode_sparse_electrical_cell(electrical)?;
        if anatomy.neuron_count() != lineages.len() {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        Ok(Self {
            lineages: lineages.into_boxed_slice(),
            anatomy,
            state,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_and_one_contact_round_trip_exactly() {
        assert_eq!(
            ResidentElectricalFabric::decode(&ResidentElectricalFabric::default().encode().unwrap())
                .unwrap(),
            ResidentElectricalFabric::default()
        );
        let fabric = ResidentElectricalFabric::default()
            .append_contact(
                [1; 16],
                [2; 16],
                ExactRational::integer(500),
            )
            .unwrap();
        let encoded = fabric.encode().unwrap();
        assert_eq!(ResidentElectricalFabric::decode(&encoded).unwrap(), fabric);
    }
}
