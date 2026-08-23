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
    encode_sparse_electrical_cell_v1, encode_sparse_electrical_cell_v2,
    sparse_electrical_cell_format, ElectricalContactAnatomy, SparseElectricalAnatomy,
    SparseElectricalCellFormat, SparseElectricalError, SparseElectricalState,
};
use std::collections::BTreeSet;

const MAGIC: &[u8; 8] = b"GLREF01\0";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct ResidentElectricalFabric {
    lineages: Box<[[u8; 16]]>,
    anatomy: SparseElectricalAnatomy,
    state: SparseElectricalState,
    cell_format: SparseElectricalCellFormat,
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
            cell_format: SparseElectricalCellFormat::V3,
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
        self.append_contacts(&[(
            left_lineage,
            right_lineage,
            conductance_picosiemens,
        )])
    }

    /// Append one reached set of authored cross-cohort contacts while copying
    /// the resident fabric exactly once.  A causal interval may physically
    /// mount several inputs on one already-existing motor route; rebuilding
    /// the complete retained fabric once per input repeats representation, not
    /// physics.
    pub(crate) fn append_contacts(
        &self,
        additions: &[([u8; 16], [u8; 16], ExactRational)],
    ) -> Result<Self, SparseElectricalError> {
        if additions.is_empty() {
            return Ok(self.clone());
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
        let mut indexed = Vec::with_capacity(additions.len());
        for (left_lineage, right_lineage, conductance) in additions.iter().copied() {
            if left_lineage == [0; 16]
                || right_lineage == [0; 16]
                || left_lineage == right_lineage
            {
                return Err(SparseElectricalError::InvalidEndpoint);
            }
            let left = member(left_lineage);
            let right = member(right_lineage);
            indexed.push((left, right, conductance));
        }
        let neuron_count = lineages.len();
        let widened = self.anatomy.extend_neuron_count(neuron_count.max(1))?;
        let widened_state = SparseElectricalState::from_contact_states(
            &widened,
            self.state.contact_states().to_vec(),
        )?;
        let contacts = indexed
            .into_iter()
            .map(|(left, right, conductance)| {
                ElectricalContactAnatomy::new(left, right, conductance, neuron_count)
            })
            .collect::<Result<Vec<_>, _>>()?;
        let successor_anatomy = widened.append_contacts(contacts)?;
        let successor_state = widened_state.append_genesis_contacts(&successor_anatomy)?;
        Ok(Self {
            lineages: lineages.into_boxed_slice(),
            anatomy: successor_anatomy,
            state: successor_state,
            cell_format: SparseElectricalCellFormat::V3,
        })
    }

    /// Apply one already-settled sparse contact projection without cloning the
    /// complete resident fabric.  Physical anatomy and lineage ownership do
    /// not change during an ordinary interval.
    pub(crate) fn replace_contact_states(
        &mut self,
        replacements: Vec<(
            usize,
            crate::sparse_electrical_contact::ElectricalContactState,
        )>,
    ) -> Result<(), SparseElectricalError> {
        self.state.replace_contact_states(replacements)
    }

    /// Remove every cross-cohort contact incident to a physically retired
    /// lineage while preserving every unrelated contact and its exact retained
    /// carrier phase.  Endpoint indices are rebuilt from the surviving stable
    /// lineages; no contact is redirected.
    pub(crate) fn without_lineages(
        &self,
        retired: &[[u8; 16]],
    ) -> Result<Self, SparseElectricalError> {
        if retired.is_empty() {
            return Ok(self.clone());
        }
        let retired = retired.iter().copied().collect::<BTreeSet<_>>();
        let mut kept = Vec::new();
        for ((left, right), (contact, state)) in self.contact_endpoints().zip(
            self.anatomy
                .contact_anatomies()
                .iter()
                .copied()
                .zip(self.state.contact_states().iter().cloned()),
        ) {
            let left_lineage = self.lineages[left];
            let right_lineage = self.lineages[right];
            if retired.contains(&left_lineage) || retired.contains(&right_lineage) {
                continue;
            }
            kept.push((left_lineage, right_lineage, contact.conductance_picosiemens(), state));
        }
        if kept.is_empty() {
            return Ok(Self::default());
        }

        let mut lineages = Vec::<[u8; 16]>::new();
        for (left, right, _, _) in &kept {
            if !lineages.contains(left) {
                lineages.push(*left);
            }
            if !lineages.contains(right) {
                lineages.push(*right);
            }
        }
        let neuron_count = lineages.len();
        let mut contacts = Vec::with_capacity(kept.len());
        let mut states = Vec::with_capacity(kept.len());
        for (left, right, conductance, state) in kept {
            let left = lineages
                .iter()
                .position(|lineage| *lineage == left)
                .ok_or(SparseElectricalError::InvalidEndpoint)?;
            let right = lineages
                .iter()
                .position(|lineage| *lineage == right)
                .ok_or(SparseElectricalError::InvalidEndpoint)?;
            contacts.push(ElectricalContactAnatomy::new(
                left,
                right,
                conductance,
                neuron_count,
            )?);
            states.push(state);
        }
        let anatomy = SparseElectricalAnatomy::new(neuron_count, contacts)?;
        let state = SparseElectricalState::from_contact_states(&anatomy, states)?;
        Ok(Self {
            lineages: lineages.into_boxed_slice(),
            anatomy,
            state,
            cell_format: SparseElectricalCellFormat::V3,
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
        let electrical = match self.cell_format {
            SparseElectricalCellFormat::V1 => {
                encode_sparse_electrical_cell_v1(&self.anatomy, &self.state)
            }
            SparseElectricalCellFormat::V2 => {
                encode_sparse_electrical_cell_v2(&self.anatomy, &self.state)
            }
            SparseElectricalCellFormat::V3 => {
                encode_sparse_electrical_cell(&self.anatomy, &self.state)
            }
        }?;
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
        let cell_format = sparse_electrical_cell_format(electrical)?;
        let (anatomy, state) = decode_sparse_electrical_cell(electrical)?;
        if anatomy.neuron_count() != lineages.len() {
            return Err(SparseElectricalError::AnatomyStateWidth);
        }
        Ok(Self {
            lineages: lineages.into_boxed_slice(),
            anatomy,
            state,
            cell_format,
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

    #[test]
    fn retiring_one_lineage_preserves_unrelated_contact_state_exactly() {
        let fabric = ResidentElectricalFabric::default()
            .append_contact([1; 16], [2; 16], ExactRational::integer(500))
            .unwrap()
            .append_contact([3; 16], [4; 16], ExactRational::integer(700))
            .unwrap();
        let kept_state = fabric.state().contact_states()[1].clone();
        let successor = fabric.without_lineages(&[[1; 16]]).unwrap();
        assert_eq!(successor.lineages(), &[[3; 16], [4; 16]]);
        assert_eq!(successor.contact_count(), 1);
        assert_eq!(successor.state().contact_states(), &[kept_state]);
    }

    #[test]
    fn sparse_contact_replacement_changes_only_validated_resident_indices() {
        let mut fabric = ResidentElectricalFabric::default()
            .append_contact([1; 16], [2; 16], ExactRational::integer(500))
            .unwrap()
            .append_contact([3; 16], [4; 16], ExactRational::integer(700))
            .unwrap();
        let predecessor = fabric.clone();
        let replacement =
            crate::sparse_electrical_contact::ElectricalContactState::from_channel_parts(
                fabric.anatomy().contact_anatomies()[1],
                fabric.state().contact_states()[1].carrier_phase(),
                1,
                ExactRational::new(1, 2).unwrap(),
            )
            .unwrap();

        assert!(fabric
            .replace_contact_states(vec![(1, replacement.clone()), (1, replacement.clone())])
            .is_err());
        assert_eq!(fabric, predecessor);

        fabric
            .replace_contact_states(vec![(1, replacement.clone())])
            .unwrap();
        assert_eq!(
            fabric.state().contact_states()[0],
            predecessor.state().contact_states()[0]
        );
        assert_eq!(fabric.state().contact_states()[1], replacement);
    }
}
