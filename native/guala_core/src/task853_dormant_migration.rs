//! One-time task-853 dormant-lineage migration boundary.
//!
//! This module authenticates the exact production `GLMFAB03` predecessor,
//! extracts only its historically retained lineage and four-field source key,
//! and creates an otherwise empty current cognitive genesis. The predecessor
//! bytes and executable mounted state never enter the result.

use crate::materialized_fabric::inspect_authenticated_glmfab03_legacy_ports;
use crate::resident_cognitive_formation::{
    DormantLineageSeed, FormationError, ResidentCognitiveFormationState,
};
use std::fmt;

pub(crate) const TASK853_IDENTITY: &str = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1";
pub(crate) const TASK853_ORGANISM_TICK: u64 = 23_723_846;
pub(crate) const TASK853_GLMFAB03_SHA256: [u8; 32] = [
    0xb1, 0xf5, 0x38, 0xe2, 0x5d, 0x0b, 0xf5, 0x95, 0x84, 0x26, 0x61, 0x72, 0xcc, 0xb4, 0x73, 0xb2,
    0xb2, 0xdb, 0x6a, 0xd7, 0xdd, 0xf1, 0xfc, 0x1f, 0x7f, 0xfa, 0x54, 0x2b, 0xd2, 0xcc, 0x7e, 0x14,
];
pub(crate) const TASK853_FABRIC_GENERATION: u64 = 13;
pub(crate) const TASK853_MOUNTED_GENERATION: u64 = 2;
pub(crate) const TASK853_NEXT_LINEAGE_ORDINAL: u64 = 97;
pub(crate) const TASK853_DORMANT_LINEAGE_SEED_COUNT: usize = 96;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct Task853DormantMigration {
    cognitive_genesis: ResidentCognitiveFormationState,
    legacy_fabric_receipt: [u8; 32],
    legacy_fabric_generation: u64,
    legacy_mounted_generation: u64,
    dormant_lineage_seed_count: usize,
}

impl Task853DormantMigration {
    pub(crate) fn cognitive_genesis(&self) -> &ResidentCognitiveFormationState {
        &self.cognitive_genesis
    }

    pub(crate) fn into_cognitive_genesis(self) -> ResidentCognitiveFormationState {
        self.cognitive_genesis
    }

    pub(crate) fn legacy_fabric_receipt(&self) -> [u8; 32] {
        self.legacy_fabric_receipt
    }

    pub(crate) fn legacy_fabric_generation(&self) -> u64 {
        self.legacy_fabric_generation
    }

    pub(crate) fn legacy_mounted_generation(&self) -> u64 {
        self.legacy_mounted_generation
    }

    pub(crate) fn dormant_lineage_seed_count(&self) -> usize {
        self.dormant_lineage_seed_count
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum Task853DormantMigrationError {
    LegacyReceiptMismatch,
    IdentityMismatch,
    OrganismTickMismatch,
    LegacyInspection(String),
    FabricGenerationMismatch,
    MountedGenerationMismatch,
    NextLineageOrdinalMismatch,
    DormantLineageSeedCountMismatch,
    CognitiveGenesis(FormationError),
}

impl fmt::Display for Task853DormantMigrationError {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::LegacyReceiptMismatch => {
                write!(output, "legacy receipt is not the exact task-853 receipt")
            }
            Self::IdentityMismatch => {
                write!(
                    output,
                    "organism identity is not the exact task-853 identity"
                )
            }
            Self::OrganismTickMismatch => {
                write!(output, "organism tick is not the exact task-853 tick")
            }
            Self::LegacyInspection(error) => {
                write!(output, "exact task-853 GLMFAB03 inspection failed: {error}")
            }
            Self::FabricGenerationMismatch => {
                write!(output, "task-853 fabric generation changed")
            }
            Self::MountedGenerationMismatch => {
                write!(output, "task-853 mounted generation changed")
            }
            Self::NextLineageOrdinalMismatch => {
                write!(output, "task-853 next lineage ordinal changed")
            }
            Self::DormantLineageSeedCountMismatch => {
                write!(output, "task-853 dormant lineage roster changed")
            }
            Self::CognitiveGenesis(error) => {
                write!(output, "task-853 cognitive genesis failed: {error}")
            }
        }
    }
}

impl std::error::Error for Task853DormantMigrationError {}

/// Authenticate and consume exactly the task-853 `GLMFAB03` predecessor.
///
/// The returned state contains only sorted dormant lineage seeds. It contains
/// no predecessor body, mounted state, DSF body, compatibility arena, pointer,
/// owner, lock, database key, restore route, or fallback authority.
pub(crate) fn migrate_task853_to_dormant_cognitive_genesis(
    legacy_glmfab03: &[u8],
    expected_legacy_receipt: [u8; 32],
    organism_identity: &str,
    organism_tick: u64,
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<Task853DormantMigration, Task853DormantMigrationError> {
    if expected_legacy_receipt != TASK853_GLMFAB03_SHA256 {
        return Err(Task853DormantMigrationError::LegacyReceiptMismatch);
    }
    if organism_identity != TASK853_IDENTITY {
        return Err(Task853DormantMigrationError::IdentityMismatch);
    }
    if organism_tick != TASK853_ORGANISM_TICK {
        return Err(Task853DormantMigrationError::OrganismTickMismatch);
    }

    let inspected = inspect_authenticated_glmfab03_legacy_ports(
        legacy_glmfab03,
        expected_legacy_receipt,
        max_state_bytes,
        max_working_bytes,
    )
    .map_err(Task853DormantMigrationError::LegacyInspection)?;

    if inspected.fabric_generation != TASK853_FABRIC_GENERATION {
        return Err(Task853DormantMigrationError::FabricGenerationMismatch);
    }
    if inspected.mounted_generation != TASK853_MOUNTED_GENERATION {
        return Err(Task853DormantMigrationError::MountedGenerationMismatch);
    }
    if inspected.next_lineage_ordinal != TASK853_NEXT_LINEAGE_ORDINAL {
        return Err(Task853DormantMigrationError::NextLineageOrdinalMismatch);
    }
    if inspected.neurons.len() != TASK853_DORMANT_LINEAGE_SEED_COUNT {
        return Err(Task853DormantMigrationError::DormantLineageSeedCountMismatch);
    }

    let dormant_lineage_seeds = inspected
        .neurons
        .into_iter()
        .map(|neuron| {
            DormantLineageSeed::new(
                neuron.sense,
                neuron.topology_index,
                &neuron.sensor_id,
                &neuron.substream_id,
                neuron.lineage,
            )
            .map_err(Task853DormantMigrationError::CognitiveGenesis)
        })
        .collect::<Result<Vec<_>, _>>()?;

    let cognitive_genesis = ResidentCognitiveFormationState::from_genesis_parts(
        0,
        inspected.next_lineage_ordinal,
        Vec::new(),
        dormant_lineage_seeds,
    )
    .map_err(Task853DormantMigrationError::CognitiveGenesis)?;

    Ok(Task853DormantMigration {
        cognitive_genesis,
        legacy_fabric_receipt: TASK853_GLMFAB03_SHA256,
        legacy_fabric_generation: inspected.fabric_generation,
        legacy_mounted_generation: inspected.mounted_generation,
        dormant_lineage_seed_count: TASK853_DORMANT_LINEAGE_SEED_COUNT,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const ADMITTED: usize = 8 * 1024 * 1024;

    #[test]
    fn wrong_receipt_is_rejected_before_legacy_decode() {
        let error = migrate_task853_to_dormant_cognitive_genesis(
            b"not a predecessor",
            [0; 32],
            TASK853_IDENTITY,
            TASK853_ORGANISM_TICK,
            ADMITTED,
            ADMITTED,
        )
        .unwrap_err();
        assert_eq!(error, Task853DormantMigrationError::LegacyReceiptMismatch);
    }

    #[test]
    fn wrong_identity_is_rejected_before_legacy_decode() {
        let error = migrate_task853_to_dormant_cognitive_genesis(
            b"not a predecessor",
            TASK853_GLMFAB03_SHA256,
            "00000000-0000-0000-0000-000000000000",
            TASK853_ORGANISM_TICK,
            ADMITTED,
            ADMITTED,
        )
        .unwrap_err();
        assert_eq!(error, Task853DormantMigrationError::IdentityMismatch);
    }

    #[test]
    fn wrong_tick_is_rejected_before_legacy_decode() {
        let error = migrate_task853_to_dormant_cognitive_genesis(
            b"not a predecessor",
            TASK853_GLMFAB03_SHA256,
            TASK853_IDENTITY,
            TASK853_ORGANISM_TICK - 1,
            ADMITTED,
            ADMITTED,
        )
        .unwrap_err();
        assert_eq!(error, Task853DormantMigrationError::OrganismTickMismatch);
    }
}
