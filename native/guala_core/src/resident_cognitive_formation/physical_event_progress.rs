//! Exact physical integration progress; no event heap, history or cognition.
//! Stable-key path copying isolates prepared successors without cloning a population.
use super::{FormationError, ResidentTopologyIndex, StablePhysicalBondReference};
use crate::elementary_charge_transfer::ChargeCarrierPhase;
use std::sync::Arc;

#[derive(Clone, Debug, Eq, PartialEq)]
enum Node<const N: usize, V> {
    Leaf {
        key: [u8; N],
        value: V,
    },
    Branch {
        bit: usize,
        zero: Arc<Self>,
        one: Arc<Self>,
    },
}

fn one<const N: usize>(key: &[u8; N], bit: usize) -> bool {
    key[bit / 8] & (1 << (7 - bit % 8)) != 0
}

impl<const N: usize, V: Clone + Eq> Node<N, V> {
    fn leaf(&self, key: &[u8; N]) -> (&[u8; N], &V) {
        match self {
            Self::Leaf { key, value } => (key, value),
            Self::Branch {
                bit,
                zero,
                one: right,
            } => if one(key, *bit) { right } else { zero }.leaf(key),
        }
    }

    fn insert(node: &mut Arc<Self>, key: [u8; N], split: usize, value: V) {
        if let Self::Branch {
            bit,
            zero,
            one: right,
        } = Arc::make_mut(node)
        {
            if *bit < split {
                Self::insert(
                    if one(&key, *bit) { right } else { zero },
                    key,
                    split,
                    value,
                );
                return;
            }
        }
        if split == N * 8 {
            *Arc::make_mut(node) = Self::Leaf { key, value };
        } else {
            let leaf = Arc::new(Self::Leaf { key, value });
            let old = node.clone();
            *node = Arc::new(if one(&key, split) {
                Self::Branch {
                    bit: split,
                    zero: old,
                    one: leaf,
                }
            } else {
                Self::Branch {
                    bit: split,
                    zero: leaf,
                    one: old,
                }
            });
        }
    }

    fn visit(
        &self,
        emit: &mut impl FnMut(&[u8; N], &V) -> Result<(), FormationError>,
    ) -> Result<(), FormationError> {
        match self {
            Self::Leaf { key, value } => emit(key, value),
            Self::Branch { zero, one, .. } => {
                zero.visit(emit)?;
                one.visit(emit)
            }
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct PhysicalMap<const N: usize, V> {
    root: Option<Arc<Node<N, V>>>,
    len: usize,
}

impl<const N: usize, V: Clone + Eq> Default for PhysicalMap<N, V> {
    fn default() -> Self {
        Self { root: None, len: 0 }
    }
}

impl<const N: usize, V: Clone + Eq> PhysicalMap<N, V> {
    fn get(&self, key: &[u8; N]) -> Option<&V> {
        let (found, value) = self.root.as_ref()?.leaf(key);
        (found == key).then_some(value)
    }

    fn put(&mut self, key: [u8; N], value: V) -> Result<(), FormationError> {
        match self.root.as_mut() {
            None => {
                self.root = Some(Arc::new(Node::Leaf { key, value }));
                self.len = 1;
            }
            Some(root) => {
                let (prior_key, prior_value) = root.leaf(&key);
                if *prior_key == key && *prior_value == value {
                    return Ok(());
                }
                let split = prior_key
                    .iter()
                    .zip(key)
                    .enumerate()
                    .find_map(|(byte, (left, right))| {
                        let difference = left ^ right;
                        (difference != 0).then(|| byte * 8 + difference.leading_zeros() as usize)
                    })
                    .unwrap_or(N * 8);
                let added = usize::from(split != N * 8);
                let len = self
                    .len
                    .checked_add(added)
                    .ok_or(FormationError::ArithmeticOverflow)?;
                Node::insert(root, key, split, value);
                self.len = len;
            }
        }
        Ok(())
    }

    fn visit(
        &self,
        mut emit: impl FnMut(&[u8; N], &V) -> Result<(), FormationError>,
    ) -> Result<(), FormationError> {
        match &self.root {
            Some(root) => root.visit(&mut emit),
            None => Ok(()),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct RecoveryProgress {
    pub(super) phase: ChargeCarrierPhase,
    pub(super) last: u64,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub(super) struct PhysicalEventProgress {
    pub(super) clock: u64,
    recovery: PhysicalMap<16, RecoveryProgress>,
    contacts: PhysicalMap<36, u64>,
}

fn bond_key(bond: StablePhysicalBondReference) -> [u8; 36] {
    let (left, right) = bond.endpoints();
    let mut key = [0; 36];
    key[..16].copy_from_slice(&left);
    key[16..32].copy_from_slice(&right);
    key[32..].copy_from_slice(&bond.parallel_ordinal().to_be_bytes());
    key
}

impl PhysicalEventProgress {
    pub(super) fn at_clock(clock: u64) -> Self {
        Self {
            clock,
            ..Self::default()
        }
    }

    /// Only a real topology-growth boundary may initialize missing participants.
    /// Current decode separately requires the complete exact identity set.
    pub(super) fn admit_topology(
        &mut self,
        topology: &ResidentTopologyIndex,
    ) -> Result<(), FormationError> {
        self.validate_members(topology)?;
        for lineage in topology.canonical_lineages.iter() {
            if self.recovery.get(lineage).is_none() {
                self.recovery.put(
                    *lineage,
                    RecoveryProgress {
                        phase: ChargeCarrierPhase::zero(),
                        last: self.clock,
                    },
                )?;
            }
        }
        for bond in topology.canonical_bonds.iter().copied() {
            let key = bond_key(bond);
            if self.contacts.get(&key).is_none() {
                self.contacts.put(key, self.clock)?;
            }
        }
        Ok(())
    }

    pub(super) fn recovery(&self, lineage: [u8; 16]) -> Result<RecoveryProgress, FormationError> {
        self.recovery
            .get(&lineage)
            .copied()
            .ok_or(FormationError::NoncanonicalState)
    }

    pub(super) fn set_recovery(
        &mut self,
        lineage: [u8; 16],
        value: RecoveryProgress,
    ) -> Result<(), FormationError> {
        if value.last > self.clock || self.recovery.get(&lineage).is_none() {
            return Err(FormationError::NoncanonicalState);
        }
        self.recovery.put(lineage, value)
    }

    pub(super) fn set_recovery_clock(
        &mut self,
        lineage: [u8; 16],
        last: u64,
    ) -> Result<(), FormationError> {
        let prior = self.recovery(lineage)?;
        self.set_recovery(lineage, RecoveryProgress { last, ..prior })
    }

    pub(super) fn set_recovery_phase(
        &mut self,
        lineage: [u8; 16],
        phase: ChargeCarrierPhase,
    ) -> Result<(), FormationError> {
        let prior = self.recovery(lineage)?;
        self.set_recovery(lineage, RecoveryProgress { phase, ..prior })
    }

    pub(super) fn contact_clock(
        &self,
        bond: StablePhysicalBondReference,
    ) -> Result<u64, FormationError> {
        self.contacts
            .get(&bond_key(bond))
            .copied()
            .ok_or(FormationError::NoncanonicalState)
    }

    pub(super) fn set_contact_clock(
        &mut self,
        bond: StablePhysicalBondReference,
        clock: u64,
    ) -> Result<(), FormationError> {
        let key = bond_key(bond);
        if clock > self.clock || self.contacts.get(&key).is_none() {
            return Err(FormationError::NoncanonicalState);
        }
        self.contacts.put(key, clock)
    }

    fn validate_members(&self, topology: &ResidentTopologyIndex) -> Result<(), FormationError> {
        self.recovery.visit(|key, value| {
            if value.last > self.clock || topology.flat_for_lineage(*key).is_err() {
                return Err(FormationError::NoncanonicalState);
            }
            Ok(())
        })?;
        self.contacts.visit(|key, last| {
            let left = key[..16]
                .try_into()
                .map_err(|_| FormationError::NoncanonicalState)?;
            let right = key[16..32]
                .try_into()
                .map_err(|_| FormationError::NoncanonicalState)?;
            let ordinal = u32::from_be_bytes(
                key[32..]
                    .try_into()
                    .map_err(|_| FormationError::NoncanonicalState)?,
            );
            let bond = StablePhysicalBondReference::new(left, right, ordinal)
                .ok_or(FormationError::NoncanonicalState)?;
            if *last > self.clock
                || bond_key(bond) != *key
                || topology.canonical_bonds.binary_search(&bond).is_err()
            {
                return Err(FormationError::NoncanonicalState);
            }
            Ok(())
        })
    }

    pub(super) fn encode_into(
        &self,
        output: &mut Vec<u8>,
        topology: &ResidentTopologyIndex,
        maximum: usize,
    ) -> Result<(), FormationError> {
        if self.recovery.len != topology.canonical_lineages.len()
            || self.contacts.len != topology.canonical_bonds.len()
        {
            return Err(FormationError::NoncanonicalState);
        }
        self.validate_members(topology)?;
        output.extend_from_slice(&self.clock.to_le_bytes());
        super::push_length(output, self.recovery.len)?;
        self.recovery.visit(|key, value| {
            output.extend_from_slice(key);
            let (numerator, denominator) = value.phase.parts();
            output.extend_from_slice(&numerator.to_le_bytes());
            output.extend_from_slice(&denominator.to_le_bytes());
            output.extend_from_slice(&value.last.to_le_bytes());
            super::ensure_cognitive_output_budget(output, maximum)
        })?;
        super::push_length(output, self.contacts.len)?;
        self.contacts.visit(|key, last| {
            output.extend_from_slice(key);
            output.extend_from_slice(&last.to_le_bytes());
            super::ensure_cognitive_output_budget(output, maximum)
        })?;
        super::ensure_cognitive_output_budget(output, maximum)
    }

    pub(super) fn decode_from(
        bytes: &[u8],
        cursor: &mut usize,
        topology: &ResidentTopologyIndex,
    ) -> Result<Self, FormationError> {
        fn take<const N: usize>(
            bytes: &[u8],
            cursor: &mut usize,
        ) -> Result<[u8; N], FormationError> {
            let end = cursor
                .checked_add(N)
                .ok_or(FormationError::ArithmeticOverflow)?;
            let value = bytes
                .get(*cursor..end)
                .ok_or(FormationError::NoncanonicalState)?
                .try_into()
                .map_err(|_| FormationError::NoncanonicalState)?;
            *cursor = end;
            Ok(value)
        }
        let mut state = Self::at_clock(u64::from_le_bytes(take(bytes, cursor)?));
        let neurons = super::read_length(bytes, cursor)?;
        if neurons != topology.canonical_lineages.len()
            || neurons > bytes.len().saturating_sub(*cursor) / 56
        {
            return Err(FormationError::NoncanonicalState);
        }
        for (expected, _) in topology.flat_by_lineage.iter() {
            let lineage = take::<16>(bytes, cursor)?;
            if lineage != *expected {
                return Err(FormationError::NoncanonicalState);
            }
            let numerator = i128::from_le_bytes(take(bytes, cursor)?);
            let denominator = u128::from_le_bytes(take(bytes, cursor)?);
            let phase = ChargeCarrierPhase::new(numerator, denominator)
                .map_err(|_| FormationError::NoncanonicalState)?;
            if phase.parts() != (numerator, denominator) {
                return Err(FormationError::NoncanonicalState);
            }
            let last = u64::from_le_bytes(take(bytes, cursor)?);
            if last > state.clock {
                return Err(FormationError::NoncanonicalState);
            }
            state
                .recovery
                .put(lineage, RecoveryProgress { phase, last })?;
        }
        let contacts = super::read_length(bytes, cursor)?;
        if contacts != topology.canonical_bonds.len()
            || contacts > bytes.len().saturating_sub(*cursor) / 44
        {
            return Err(FormationError::NoncanonicalState);
        }
        for expected in topology.canonical_bonds.iter().copied() {
            let key = take::<36>(bytes, cursor)?;
            if key != bond_key(expected) {
                return Err(FormationError::NoncanonicalState);
            }
            let last = u64::from_le_bytes(take(bytes, cursor)?);
            if last > state.clock {
                return Err(FormationError::NoncanonicalState);
            }
            state.contacts.put(key, last)?;
        }
        Ok(state)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Codec/custody support only: the settlement tests use real mounted cells.
    fn topology() -> ResidentTopologyIndex {
        let mut topology = ResidentTopologyIndex::empty();
        // Physical/cohort order is independent of lexicographic lineage order.
        topology.canonical_lineages = Box::new([[3; 16], [1; 16], [2; 16]]);
        topology.flat_by_lineage = Box::new([([1; 16], 1), ([2; 16], 2), ([3; 16], 0)]);
        topology.canonical_bonds = Box::new([
            StablePhysicalBondReference::new([1; 16], [2; 16], 0).unwrap(),
            StablePhysicalBondReference::new([1; 16], [2; 16], 1).unwrap(),
            StablePhysicalBondReference::new([2; 16], [3; 16], 0).unwrap(),
        ]);
        topology
    }

    #[test]
    fn physical_progress_exact_codec_growth_and_discard() {
        let mut topology = topology();
        let mut original = PhysicalEventProgress::at_clock(11);
        original.admit_topology(&topology).unwrap();
        original.clock = 17;
        original
            .set_recovery(
                [2; 16],
                RecoveryProgress {
                    phase: ChargeCarrierPhase::new(-2, 7).unwrap(),
                    last: 13,
                },
            )
            .unwrap();
        original
            .set_contact_clock(topology.canonical_bonds[1], 16)
            .unwrap();
        let mut bytes = Vec::new();
        original
            .encode_into(&mut bytes, &topology, usize::MAX)
            .unwrap();
        assert_eq!(bytes.len(), 24 + 56 * 3 + 44 * 3);
        let mut cursor = 0;
        let restored = PhysicalEventProgress::decode_from(&bytes, &mut cursor, &topology).unwrap();
        assert_eq!(cursor, bytes.len());
        assert_eq!(restored, original);
        assert_eq!(topology.canonical_lineages.as_ref(), &[[3; 16], [1; 16], [2; 16]],
            "codec must not reorder anatomical participants");
        assert_eq!(
            restored.contact_clock(topology.canonical_bonds[0]).unwrap(),
            11
        );
        assert_eq!(
            restored.contact_clock(topology.canonical_bonds[1]).unwrap(),
            16
        );

        let mut prepared = original.clone();
        assert!(Arc::ptr_eq(
            prepared.recovery.root.as_ref().unwrap(),
            original.recovery.root.as_ref().unwrap()
        ));
        assert!(Arc::ptr_eq(
            prepared.contacts.root.as_ref().unwrap(),
            original.contacts.root.as_ref().unwrap()
        ));
        prepared.clock = 18;
        prepared.set_recovery_clock([2; 16], 18).unwrap();
        prepared
            .set_contact_clock(topology.canonical_bonds[1], 18)
            .unwrap();
        drop(prepared);
        let mut after_discard = Vec::new();
        original
            .encode_into(&mut after_discard, &topology, usize::MAX)
            .unwrap();
        assert_eq!(
            after_discard, bytes,
            "discard must not mutate predecessor roots"
        );

        let mut grown = original.clone();
        topology.canonical_lineages = Box::new([[3; 16], [1; 16], [2; 16], [4; 16]]);
        topology.flat_by_lineage = Box::new([
            ([1; 16], 1), ([2; 16], 2), ([3; 16], 0), ([4; 16], 3),
        ]);
        topology.canonical_bonds = Box::new([
            topology.canonical_bonds[0],
            topology.canonical_bonds[1],
            topology.canonical_bonds[2],
            StablePhysicalBondReference::new([3; 16], [4; 16], 0).unwrap(),
        ]);
        grown.admit_topology(&topology).unwrap();
        assert_eq!(
            grown.recovery([2; 16]).unwrap(),
            original.recovery([2; 16]).unwrap()
        );
        assert_eq!(
            grown.contact_clock(topology.canonical_bonds[1]).unwrap(),
            16
        );
        assert_eq!(
            grown.recovery([4; 16]).unwrap(),
            RecoveryProgress {
                phase: ChargeCarrierPhase::zero(),
                last: 17,
            }
        );
        assert_eq!(
            grown.contact_clock(topology.canonical_bonds[3]).unwrap(),
            17
        );
        let unchanged = grown.clone();
        grown.admit_topology(&topology).unwrap();
        assert_eq!(grown, unchanged, "same topology adds no history");
        topology.canonical_lineages = Box::new([[3; 16], [1; 16], [2; 16], [5; 16]]);
        topology.flat_by_lineage = Box::new([
            ([1; 16], 1), ([2; 16], 2), ([3; 16], 0), ([5; 16], 3),
        ]);
        assert!(
            grown.admit_topology(&topology).is_err(),
            "equal population counts cannot replace a stable identity"
        );
    }

    #[test]
    fn physical_progress_refuses_noncanonical_or_missing_custody() {
        let topology = topology();
        let mut state = PhysicalEventProgress::at_clock(11);
        assert!(state
            .encode_into(&mut Vec::new(), &topology, usize::MAX)
            .is_err());
        state.admit_topology(&topology).unwrap();
        let mut bytes = Vec::new();
        state
            .encode_into(&mut bytes, &topology, usize::MAX)
            .unwrap();
        let decode = |bytes: &[u8]| PhysicalEventProgress::decode_from(bytes, &mut 0, &topology);
        assert!(decode(&bytes[..bytes.len() - 1]).is_err());
        let mut wrong_identity = bytes.clone();
        wrong_identity[16] = 9;
        assert!(decode(&wrong_identity).is_err());
        let mut duplicate = bytes.clone();
        duplicate[72..88].copy_from_slice(&bytes[16..32]);
        assert!(decode(&duplicate).is_err());
        let mut future_clock = bytes.clone();
        future_clock[64..72].copy_from_slice(&12u64.to_le_bytes());
        assert!(decode(&future_clock).is_err());
        let mut noncanonical_phase = bytes.clone();
        noncanonical_phase[32..48].copy_from_slice(&2i128.to_le_bytes());
        noncanonical_phase[48..64].copy_from_slice(&4u128.to_le_bytes());
        assert!(decode(&noncanonical_phase).is_err());
        let mut zero_denominator = bytes.clone();
        zero_denominator[48..64].fill(0);
        assert!(decode(&zero_denominator).is_err());
        assert!(state
            .encode_into(&mut Vec::new(), &topology, bytes.len() - 1)
            .is_err());
    }
}
