//! Real-body migration proof (test code, never compiled into production).
//!
//! Reads one actual persisted production envelope (GUALA_REAL_BODY env),
//! extracts its cognitive image, decodes the retired format, migrates to
//! the current format, and proves structural equality plus decode of the
//! migrated bytes. No-op when the env var is absent.

use super::ResidentCognitiveFormationState;
use std::fs;
use std::path::PathBuf;

#[test]
fn real_production_body_migrates_losslessly() {
    let Some(path) = std::env::var_os("GUALA_REAL_BODY") else {
        return;
    };
    let body = fs::read(PathBuf::from(path)).expect("real body readable");
    let (organism_tick, cognitive) = super::reservoir_probe::parse_envelope(&body);
    let budget = 32_000_000usize;
    let decoded = ResidentCognitiveFormationState::decode(&cognitive, budget)
        .expect("live v12 cognitive image decodes");
    let migrated =
        ResidentCognitiveFormationState::migrate_to_current_format(&cognitive, budget)
            .expect("migration to current format");
    let redecoded = ResidentCognitiveFormationState::decode(&migrated, budget)
        .expect("migrated image decodes");
    assert_eq!(decoded, redecoded, "migration must be lossless");
    println!(
        "REAL_BODY_MIGRATION tick={} old_cognitive_bytes={} new_cognitive_bytes={} cohorts={} mosaics={}",
        organism_tick,
        cognitive.len(),
        migrated.len(),
        redecoded.cohorts.len(),
        redecoded.mosaics.len(),
    );
}
