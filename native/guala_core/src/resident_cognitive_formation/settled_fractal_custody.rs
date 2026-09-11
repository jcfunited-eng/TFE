//! One last finalized physical delta per stable neuron. No event history.
//! Path-copying keeps an uncommitted successor isolated without copying all
//! resident leaves. Branch positions derive only from the 128-bit lineage.

use super::{FormationError, SparsePhysicalStateDelta};
use std::sync::Arc;

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub(super) struct SettledFractalCustody {
    root: Option<Arc<Node>>,
    len: usize,
}

#[derive(Debug, Eq, PartialEq)]
enum Node {
    Leaf { key: u128, delta: SparsePhysicalStateDelta },
    Branch { bit: u32, zero: Arc<Node>, one: Arc<Node> },
}

fn is_one(key: u128, bit: u32) -> bool {
    debug_assert!(bit < u128::BITS);
    key & (1_u128 << (u128::BITS - 1 - bit)) != 0
}

impl Node {
    fn leaf_for(&self, key: u128) -> (u128, &SparsePhysicalStateDelta) {
        match self {
            Self::Leaf { key, delta } => (*key, delta),
            Self::Branch { bit, zero, one } => {
                if is_one(key, *bit) { one } else { zero }.leaf_for(key)
            }
        }
    }

    fn insert(
        node: &Arc<Self>, key: u128, split: u32, delta: SparsePhysicalStateDelta,
    ) -> Arc<Self> {
        if let Self::Branch { bit, zero, one } = node.as_ref() {
            if *bit < split {
                return if is_one(key, *bit) {
                    Arc::new(Self::Branch {
                        bit: *bit, zero: zero.clone(),
                        one: Self::insert(one, key, split, delta),
                    })
                } else {
                    Arc::new(Self::Branch {
                        bit: *bit, zero: Self::insert(zero, key, split, delta),
                        one: one.clone(),
                    })
                };
            }
        }
        let leaf = Arc::new(Self::Leaf { key, delta });
        if split == u128::BITS {
            debug_assert!(matches!(node.as_ref(), Self::Leaf { key: old, .. } if *old == key));
            leaf
        } else if is_one(key, split) {
            Arc::new(Self::Branch { bit: split, zero: node.clone(), one: leaf })
        } else {
            Arc::new(Self::Branch { bit: split, zero: leaf, one: node.clone() })
        }
    }

    fn visit(
        &self,
        emit: &mut impl FnMut([u8; 16], &SparsePhysicalStateDelta) -> Result<(), FormationError>,
    ) -> Result<(), FormationError> {
        match self {
            Self::Leaf { key, delta } => emit(key.to_be_bytes(), delta),
            Self::Branch { zero, one, .. } => { zero.visit(emit)?; one.visit(emit) }
        }
    }
}

impl SettledFractalCustody {
    pub(super) fn len(&self) -> usize { self.len }

    pub(super) fn get(&self, lineage: [u8; 16]) -> Option<&SparsePhysicalStateDelta> {
        let key = u128::from_be_bytes(lineage);
        let (found, delta) = self.root.as_deref()?.leaf_for(key);
        (found == key).then_some(delta)
    }

    /// Caller supplies only a finalized coalesced real emission. A read or a
    /// continuing electrical wave may never manufacture or refresh this slot.
    pub(super) fn record(
        &mut self, lineage: [u8; 16], delta: SparsePhysicalStateDelta,
    ) -> Result<(), FormationError> {
        let key = u128::from_be_bytes(lineage);
        let (root, added) = match &self.root {
            None => (Arc::new(Node::Leaf { key, delta }), true),
            Some(root) => {
                let (old, previous) = root.leaf_for(key);
                if old == key && previous == &delta { return Ok(()); }
                (Node::insert(root, key, (old ^ key).leading_zeros(), delta), old != key)
            }
        };
        let len = self.len.checked_add(usize::from(added))
            .ok_or(FormationError::ArithmeticOverflow)?;
        self.root = Some(root);
        self.len = len;
        Ok(())
    }

    pub(super) fn visit(
        &self,
        mut emit: impl FnMut([u8; 16], &SparsePhysicalStateDelta) -> Result<(), FormationError>,
    ) -> Result<(), FormationError> {
        match self.root.as_deref() { Some(root) => root.visit(&mut emit), None => Ok(()) }
    }
}


fn validate_leaf(
    lineage: [u8; 16], delta: &SparsePhysicalStateDelta,
    cohorts: &[super::ResidentReachedCohort], topology: &super::ResidentTopologyIndex,
) -> Result<(), FormationError> {
    let flat = topology.flat_for_lineage(lineage)?;
    let (cohort, neuron, _) = topology.flat_locations[flat];
    let anatomy = &cohorts[cohort].anatomy.neuron_anatomies()[neuron];
    let maximum = anatomy.sparse_delta_coordinate_count()
        .ok_or(FormationError::ArithmeticOverflow)?;
    if delta.entries().is_empty() || delta.entries().len() > maximum
        || !crate::physical_mosaic::fractal_coordinates_fit(delta, anatomy.psi_ring_count()) {
        return Err(FormationError::NoncanonicalState);
    }
    Ok(())
}

impl SettledFractalCustody {
    pub(super) fn encode_into(
        &self, output: &mut Vec<u8>, cohorts: &[super::ResidentReachedCohort],
        topology: &super::ResidentTopologyIndex, maximum_bytes: usize,
    ) -> Result<(), FormationError> {
        super::push_length(output, self.len)?;
        self.visit(|lineage, delta| {
            validate_leaf(lineage, delta, cohorts, topology)?;
            let encoded = super::encode_sparse_physical_state_delta(delta)
                .map_err(|_| FormationError::NoncanonicalState)?;
            output.extend_from_slice(&lineage);
            super::push_length(output, encoded.len())?;
            output.extend_from_slice(&encoded);
            super::ensure_cognitive_output_budget(output, maximum_bytes)
        })?;
        super::ensure_cognitive_output_budget(output, maximum_bytes)
    }

    pub(super) fn decode_from(
        bytes: &[u8], cursor: &mut usize, cohorts: &[super::ResidentReachedCohort],
        topology: &super::ResidentTopologyIndex,
    ) -> Result<Self, FormationError> {
        let count = super::read_length(bytes, cursor)?;
        if count > topology.flat_locations.len()
            || count > bytes.len().saturating_sub(*cursor) / (16 + 8) {
            return Err(FormationError::NoncanonicalState);
        }
        let mut result = Self::default();
        let mut preceding = None;
        for _ in 0..count {
            let key_end = cursor.checked_add(16).ok_or(FormationError::ArithmeticOverflow)?;
            let lineage: [u8; 16] = bytes.get(*cursor..key_end)
                .ok_or(FormationError::NoncanonicalState)?.try_into()
                .map_err(|_| FormationError::NoncanonicalState)?;
            if preceding.is_some_and(|prior| prior >= lineage) {
                return Err(FormationError::NoncanonicalState);
            }
            preceding = Some(lineage);
            *cursor = key_end;
            let length = super::read_length(bytes, cursor)?;
            let end = cursor.checked_add(length).ok_or(FormationError::ArithmeticOverflow)?;
            let delta = super::decode_sparse_physical_state_delta(
                bytes.get(*cursor..end).ok_or(FormationError::NoncanonicalState)?,
            ).map_err(|_| FormationError::NoncanonicalState)?;
            validate_leaf(lineage, &delta, cohorts, topology)?;
            result.record(lineage, delta)?;
            *cursor = end;
        }
        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::complete_neuron::{ExactPhysicalStateDelta, PhysicalStateCoordinate, PhysicalStateDeltaEntry};

    fn delta(value: i128) -> SparsePhysicalStateDelta {
        SparsePhysicalStateDelta::from_canonical_entries(vec![
            PhysicalStateDeltaEntry::new(
                PhysicalStateCoordinate::PlasticRestLength,
                ExactPhysicalStateDelta::Rational(crate::exact_rational::ExactRational::integer(value)),
            ).unwrap(),
        ]).unwrap()
    }

    #[test]
    fn last_leaf_overwrites_without_history_and_preserves_prepared_predecessor() {
        let keys = [0_u128, 1, 2, 1 << 127, u128::MAX];
        let mut original = SettledFractalCustody::default();
        for key in keys { original.record(key.to_be_bytes(), delta(1)).unwrap(); }
        let mut reverse = SettledFractalCustody::default();
        for key in keys.into_iter().rev() { reverse.record(key.to_be_bytes(), delta(1)).unwrap(); }
        assert_eq!(original, reverse, "tree shape is canonical, not insertion order");
        let mut successor = original.clone();
        assert!(Arc::ptr_eq(original.root.as_ref().unwrap(), successor.root.as_ref().unwrap()));
        successor.record(1_u128.to_be_bytes(), delta(1)).unwrap();
        assert!(Arc::ptr_eq(original.root.as_ref().unwrap(), successor.root.as_ref().unwrap()));
        successor.record(1_u128.to_be_bytes(), delta(2)).unwrap();
        assert_eq!(original.get(1_u128.to_be_bytes()), Some(&delta(1)));
        assert_eq!(successor.get(1_u128.to_be_bytes()), Some(&delta(2)));
        assert_eq!(successor.len(), keys.len());
        assert!(successor.get(3_u128.to_be_bytes()).is_none());
        let mut visited = Vec::new();
        successor.visit(|key, _| { visited.push(u128::from_be_bytes(key)); Ok(()) }).unwrap();
        assert_eq!(visited, keys);
        fn nodes(node: &Node, preceding: Option<u32>) -> usize {
            match node {
                Node::Leaf { .. } => 1,
                Node::Branch { bit, zero, one } => {
                    assert!(*bit < 128 && preceding.is_none_or(|prior| prior < *bit));
                    1 + nodes(zero, Some(*bit)) + nodes(one, Some(*bit))
                }
            }
        }
        assert_eq!(nodes(successor.root.as_ref().unwrap(), None), 2 * keys.len() - 1);
    }
}
