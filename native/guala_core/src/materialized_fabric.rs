//! One-way native custody for the active joint-neuron state.
//!
//! Version 4 writes no familiarity classes, imported pseudo-mosaics, owner
//! records, or compatibility database. Versions 2 and 3 remain readable only
//! long enough to extract their mounted joint-neuron bytes; every legacy class
//! and pseudo-mosaic is structurally skipped and can never be written again.

use crate::joint_source_episode::NativeJointSourceEpisode;
use crate::mounted_joint_fractal::{
    convert_gljnft02_after_authenticated_outer_receipt, inspect_canonical_gljnft02_legacy_ports,
    transition_mounted_joint_dsf, LegacyMountedNeuronPortInspection, MountedJointDsfSummary,
};
use crate::sha256::sha256;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::sync::Arc;

const STATE_MAGIC: &[u8; 8] = b"GLMFAB04";
const VERSION: u16 = 4;
const PRIOR_STATE_MAGIC: &[u8; 8] = b"GLMFAB03";
const PRIOR_VERSION: u16 = 3;
const LEGACY_STATE_MAGIC: &[u8; 8] = b"GLMFAB02";
const LEGACY_VERSION: u16 = 2;
const FIELD_WIDTH: usize = 7;

#[derive(Clone, Debug, Eq, PartialEq, Default)]
pub(crate) struct Fabric {
    pub(crate) generation: u64,
    pub(crate) joint_dsf_state: Vec<u8>,
}

#[pyclass(frozen, module = "guala_core")]
pub struct NativeMaterializedFabricTransition {
    payload: Arc<[u8]>,
    payload_digest: [u8; 32],
    outcome: &'static str,
    mosaic: Option<[u8; 32]>,
    mosaic_count: usize,
    evidence_count: u64,
    joint_field_count: usize,
    joint_neuron_count: usize,
    dsf_delivery_count: usize,
    recurrent_dsf_delivery_count: usize,
    joint_transition_receipt: Option<[u8; 32]>,
    episode_relation_candidate_receipt: Option<[u8; 32]>,
}

#[pymethods]
impl NativeMaterializedFabricTransition {
    #[getter]
    fn schema(&self) -> &'static str {
        "guala.native.owner_free_materialized_fabric.v4"
    }
    #[getter]
    fn state_sha256(&self) -> String {
        hex_digest(&self.payload_digest)
    }
    #[getter]
    fn outcome(&self) -> &'static str {
        self.outcome
    }
    #[getter]
    fn mosaic_sha256(&self) -> Option<String> {
        self.mosaic.as_ref().map(hex_digest)
    }
    #[getter]
    fn mosaic_count(&self) -> usize {
        self.mosaic_count
    }
    #[getter]
    fn materialized_neuron_count(&self) -> usize {
        0
    }
    #[getter]
    fn materialized_body_count(&self) -> usize {
        0
    }
    #[getter]
    fn evidence_count(&self) -> u64 {
        self.evidence_count
    }
    #[getter]
    fn joint_field_count(&self) -> usize {
        self.joint_field_count
    }
    #[getter]
    fn joint_neuron_count(&self) -> usize {
        self.joint_neuron_count
    }
    #[getter]
    fn dsf_delivery_count(&self) -> usize {
        self.dsf_delivery_count
    }
    #[getter]
    fn recurrent_dsf_delivery_count(&self) -> usize {
        self.recurrent_dsf_delivery_count
    }
    #[getter]
    fn joint_transition_sha256(&self) -> Option<String> {
        self.joint_transition_receipt.as_ref().map(hex_digest)
    }
    #[getter]
    fn episode_relation_candidate_sha256(&self) -> Option<String> {
        self.episode_relation_candidate_receipt
            .as_ref()
            .map(hex_digest)
    }
    #[getter]
    fn python_callback_count(&self) -> usize {
        0
    }
    fn as_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.payload)
    }
}

#[pyfunction]
#[pyo3(signature = (
    prior_state,
    source,
    max_state_bytes=67_108_864,
    max_working_bytes=67_108_864
))]
fn transition_materialized_fabric(
    py: Python<'_>,
    prior_state: Option<Vec<u8>>,
    source: PyRef<'_, NativeJointSourceEpisode>,
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> PyResult<NativeMaterializedFabricTransition> {
    if max_state_bytes == 0 || max_working_bytes == 0 {
        return Err(PyValueError::new_err(
            "materialized state or working memory is not admitted",
        ));
    }
    let joint_source = source.clone();
    let result = py
        .allow_threads(move || -> Result<_, String> {
            let mut state = match prior_state {
                Some(payload) => parse_state(&payload, max_state_bytes)?,
                None => Fabric::default(),
            };
            let prepared = transition_mounted_joint_dsf(
                &state.joint_dsf_state,
                &joint_source,
                max_state_bytes,
                max_working_bytes,
            )?;
            let (joint_state, joint) = prepared.into_serialized_parts();
            state.joint_dsf_state = joint_state;
            state.generation = state
                .generation
                .checked_add(1)
                .ok_or("materialized generation overflow")?;
            let payload = encode_current_fabric(&state)?;
            if payload.len() > max_state_bytes {
                return Err(format!(
                    "materialized fabric requires {} bytes, admitted {max_state_bytes}",
                    payload.len()
                ));
            }
            let evidence_count = u64::try_from(joint.dsf_delivery_count)
                .map_err(|_| "joint evidence count exceeds u64")?;
            Ok((payload, evidence_count, joint))
        })
        .map_err(PyValueError::new_err)?;
    let (payload, evidence_count, joint) = result;
    let outcome = if joint.transition_receipt.is_some() {
        "joint_dsf_deliveries_settled_without_neuronal_cognition"
    } else {
        "joint_field_not_reached"
    };
    let payload_digest = sha256(&payload);
    Ok(NativeMaterializedFabricTransition {
        payload: Arc::from(payload),
        payload_digest,
        outcome,
        mosaic: None,
        mosaic_count: 0,
        evidence_count,
        joint_field_count: joint.joint_field_count,
        joint_neuron_count: joint.joint_neuron_count,
        dsf_delivery_count: joint.dsf_delivery_count,
        recurrent_dsf_delivery_count: joint.recurrent_dsf_delivery_count,
        joint_transition_receipt: joint.transition_receipt,
        episode_relation_candidate_receipt: joint.episode_relation_candidate_receipt,
    })
}

#[pyfunction]
#[pyo3(signature = (
    prior_state,
    max_state_bytes=67_108_864,
    max_working_bytes=67_108_864
))]
fn migrate_materialized_fabric(
    py: Python<'_>,
    prior_state: Vec<u8>,
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> PyResult<NativeMaterializedFabricTransition> {
    let _ = (py, prior_state, max_state_bytes, max_working_bytes);
    Err(PyValueError::new_err(
        "unauthenticated materialized migration is retired; use the authenticated task-853 migration boundary",
    ))
}

#[derive(Debug, Eq, PartialEq)]
pub(crate) struct AuthenticatedLegacyFabricMigration {
    pub(crate) current_fabric: Vec<u8>,
    pub(crate) legacy_fabric_receipt: [u8; 32],
    pub(crate) summary: MountedJointDsfSummary,
}

/// Authenticate exactly one GLMFAB03 predecessor and pass it through the same
/// canonical legacy parser, mounted-field validator, and one-way encoder used
/// by the separately named materialized migration callable. GLMFAB04 and
/// GLORUN inputs cannot enter because schema admission precedes migration.
pub(crate) fn migrate_authenticated_glmfab03_to_current(
    payload: &[u8],
    expected_content_sha256: [u8; 32],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<AuthenticatedLegacyFabricMigration, String> {
    if payload.len() > max_state_bytes {
        return Err("GLMFAB03 input exceeds admitted storage".into());
    }
    if payload.len() < PRIOR_STATE_MAGIC.len() + std::mem::size_of::<u16>()
        || &payload[..PRIOR_STATE_MAGIC.len()] != PRIOR_STATE_MAGIC
        || u16::from_le_bytes(
            payload[PRIOR_STATE_MAGIC.len()..PRIOR_STATE_MAGIC.len() + 2]
                .try_into()
                .expect("fixed prior materialized version"),
        ) != PRIOR_VERSION
    {
        return Err("materialized source evidence is not GLMFAB03".into());
    }
    if expected_content_sha256 == [0; 32] || sha256(payload) != expected_content_sha256 {
        return Err("GLMFAB03 content SHA-256 does not bind the exact body".into());
    }
    let (current_fabric, summary) =
        convert_glmfab03_after_authenticated_receipt(payload, max_state_bytes, max_working_bytes)?;
    Ok(AuthenticatedLegacyFabricMigration {
        current_fabric,
        legacy_fabric_receipt: expected_content_sha256,
        summary,
    })
}

/// Called only after `migrate_authenticated_glmfab03_to_current` has matched
/// the externally supplied SHA-256 against the complete GLMFAB03 body.
fn convert_glmfab03_after_authenticated_receipt(
    prior_state: &[u8],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<(Vec<u8>, MountedJointDsfSummary), String> {
    let mut state = parse_state(prior_state, max_state_bytes)?;
    let (current_joint, summary) = convert_gljnft02_after_authenticated_outer_receipt(
        &state.joint_dsf_state,
        max_state_bytes,
        max_working_bytes,
    )?;
    state.joint_dsf_state = current_joint;
    let payload = encode_current_fabric(&state)?;
    if payload.len() > max_state_bytes {
        return Err(format!(
            "materialized fabric requires {} bytes, admitted {max_state_bytes}",
            payload.len()
        ));
    }
    Ok((payload, summary))
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NativeMaterializedFabricTransition>()?;
    module.add_class::<NativeAuthenticatedLegacyFabricInspection>()?;
    // Cutover gate, not a compatibility promise: ordinary Python boot still
    // imports these two historical GLMFAB callables today. The resident-runtime
    // cutover must remove those imports and tests in the same change that
    // deregisters both exports; only their private Rust mechanics may remain.
    module.add_function(wrap_pyfunction!(transition_materialized_fabric, module)?)?;
    module.add_function(wrap_pyfunction!(migrate_materialized_fabric, module)?)?;
    module.add_function(wrap_pyfunction!(
        inspect_authenticated_legacy_materialized_fabric,
        module
    )?)?;
    Ok(())
}

pub(crate) fn encode_current_fabric(state: &Fabric) -> Result<Vec<u8>, String> {
    let mut output = Vec::new();
    output.extend_from_slice(STATE_MAGIC);
    output.extend_from_slice(&VERSION.to_le_bytes());
    output.extend_from_slice(&state.generation.to_le_bytes());
    push_u32(&mut output, state.joint_dsf_state.len())?;
    output.extend_from_slice(&state.joint_dsf_state);
    Ok(output)
}

/// Restore only the current writable materialized-fabric schema. Historical
/// schemas remain available solely through the separately named one-way
/// migration boundary above; an organism runtime must never acquire fallback
/// authority by passing through that decoder.
pub(crate) fn restore_current_fabric(
    payload: &[u8],
    max_state_bytes: usize,
) -> Result<Fabric, String> {
    if payload.len() < STATE_MAGIC.len() + std::mem::size_of::<u16>() {
        return Err("current materialized state ended early".into());
    }
    if &payload[..STATE_MAGIC.len()] != STATE_MAGIC
        || u16::from_le_bytes(
            payload[STATE_MAGIC.len()..STATE_MAGIC.len() + 2]
                .try_into()
                .expect("fixed current materialized version"),
        ) != VERSION
    {
        return Err("current materialized state is not GLMFAB04".into());
    }
    parse_state(payload, max_state_bytes)
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct AuthenticatedLegacyFabricInspection {
    pub(crate) fabric_generation: u64,
    pub(crate) mounted_generation: u64,
    pub(crate) next_lineage_ordinal: u64,
    pub(crate) neurons: Vec<LegacyMountedNeuronPortInspection>,
}

#[pyclass(frozen, module = "guala_core")]
pub struct NativeAuthenticatedLegacyFabricInspection {
    fabric_generation: u64,
    mounted_generation: u64,
    next_lineage_ordinal: u64,
    neurons: Vec<LegacyMountedNeuronPortInspection>,
}

#[pymethods]
impl NativeAuthenticatedLegacyFabricInspection {
    #[getter]
    fn schema(&self) -> &'static str {
        "guala.native.authenticated_legacy_fabric_inspection.v1"
    }

    #[getter]
    fn fabric_generation(&self) -> u64 {
        self.fabric_generation
    }

    #[getter]
    fn mounted_generation(&self) -> u64 {
        self.mounted_generation
    }

    #[getter]
    fn next_lineage_ordinal(&self) -> u64 {
        self.next_lineage_ordinal
    }

    #[getter]
    fn neuron_count(&self) -> usize {
        self.neurons.len()
    }

    #[getter]
    fn neurons(&self) -> Vec<(String, u8, u32, String, String)> {
        self.neurons
            .iter()
            .map(|neuron| {
                (
                    hex_lineage(&neuron.lineage),
                    neuron.sense,
                    neuron.topology_index,
                    neuron.sensor_id.clone(),
                    neuron.substream_id.clone(),
                )
            })
            .collect()
    }

    #[getter]
    fn python_callback_count(&self) -> usize {
        0
    }
}

#[pyfunction]
#[pyo3(signature = (
    payload,
    expected_content_sha256,
    max_state_bytes=67_108_864,
    max_working_bytes=536_870_912
))]
fn inspect_authenticated_legacy_materialized_fabric(
    py: Python<'_>,
    payload: Vec<u8>,
    expected_content_sha256: Vec<u8>,
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> PyResult<NativeAuthenticatedLegacyFabricInspection> {
    if expected_content_sha256.len() != 32 {
        return Err(PyValueError::new_err(
            "authenticated legacy fabric SHA-256 must contain exactly 32 bytes",
        ));
    }
    let expected_content_sha256: [u8; 32] = expected_content_sha256
        .try_into()
        .expect("checked SHA-256 width");
    let inspected = py
        .allow_threads(move || {
            inspect_authenticated_glmfab03_legacy_ports(
                &payload,
                expected_content_sha256,
                max_state_bytes,
                max_working_bytes,
            )
        })
        .map_err(PyValueError::new_err)?;
    Ok(NativeAuthenticatedLegacyFabricInspection {
        fabric_generation: inspected.fabric_generation,
        mounted_generation: inspected.mounted_generation,
        next_lineage_ordinal: inspected.next_lineage_ordinal,
        neurons: inspected.neurons,
    })
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct BorrowedGlmfab03<'a> {
    generation: u64,
    joint_fractal_state: &'a [u8],
}

/// Parse exactly GLMFAB03 while borrowing its mounted body. This uses the same
/// bounded Parser and legacy-arena skip helpers as the materialized-fabric
/// restore path, but cannot allocate or migrate a fabric body.
fn borrow_glmfab03(payload: &[u8]) -> Result<BorrowedGlmfab03<'_>, String> {
    let mut parser = Parser::new(payload);
    if parser.take(PRIOR_STATE_MAGIC.len())? != PRIOR_STATE_MAGIC || parser.u16()? != PRIOR_VERSION
    {
        return Err("materialized source evidence is not GLMFAB03".into());
    }
    let generation = parser.u64()?;
    skip_legacy_classes(&mut parser)?;
    skip_legacy_mosaics(&mut parser)?;
    let joint_fractal_state = parser.bytes()?;
    if !parser.finished() {
        return Err("materialized state has trailing bytes".into());
    }
    Ok(BorrowedGlmfab03 {
        generation,
        joint_fractal_state,
    })
}

/// Authenticate and inspect the exact production D2 fabric without migrating
/// it. The bounded GLMFAB parser borrows past the rejected compatibility arenas,
/// and the shared GLJNFT02 decoder performs the mounted physics validation.
/// Only the two independent schema generations, lineage, and four historically
/// retained port-key fields leave this boundary.
pub(crate) fn inspect_authenticated_glmfab03_legacy_ports(
    payload: &[u8],
    expected_content_sha256: [u8; 32],
    max_state_bytes: usize,
    max_working_bytes: usize,
) -> Result<AuthenticatedLegacyFabricInspection, String> {
    if payload.len() > max_state_bytes {
        return Err("GLMFAB03 input exceeds admitted storage".into());
    }
    if expected_content_sha256 == [0; 32] || sha256(payload) != expected_content_sha256 {
        return Err("GLMFAB03 content SHA-256 does not bind the exact body".into());
    }
    let fabric = borrow_glmfab03(payload)?;
    let mounted = inspect_canonical_gljnft02_legacy_ports(
        fabric.joint_fractal_state,
        max_state_bytes,
        max_working_bytes,
    )?;
    Ok(AuthenticatedLegacyFabricInspection {
        fabric_generation: fabric.generation,
        mounted_generation: mounted.generation,
        next_lineage_ordinal: mounted.next_lineage_ordinal,
        neurons: mounted.neurons,
    })
}

fn parse_state(payload: &[u8], max_state_bytes: usize) -> Result<Fabric, String> {
    if payload.len() > max_state_bytes {
        return Err(format!(
            "materialized prior state requires {} bytes, admitted {max_state_bytes}",
            payload.len()
        ));
    }
    let mut parser = Parser::new(payload);
    let magic = parser.take(8)?;
    let version = parser.u16()?;
    let current = magic == STATE_MAGIC && version == VERSION;
    let prior = magic == PRIOR_STATE_MAGIC && version == PRIOR_VERSION;
    let legacy = magic == LEGACY_STATE_MAGIC && version == LEGACY_VERSION;
    if !current && !prior && !legacy {
        return Err("unsupported materialized state version".into());
    }
    let generation = parser.u64()?;
    let joint_dsf_state = if current {
        parser.bytes()?.to_vec()
    } else {
        skip_legacy_classes(&mut parser)?;
        skip_legacy_mosaics(&mut parser)?;
        if prior {
            parser.bytes()?.to_vec()
        } else {
            Vec::new()
        }
    };
    if !parser.finished() {
        return Err("materialized state has trailing bytes".into());
    }
    Ok(Fabric {
        generation,
        joint_dsf_state,
    })
}

fn skip_legacy_classes(parser: &mut Parser<'_>) -> Result<(), String> {
    let count = parser.u32()? as usize;
    parser.feasible(count, 57)?;
    for _ in 0..count {
        parser.take(32)?;
        parser.take(1)?;
        parser.take(4)?;
        parser.take(8)?;
        parser.skip_digests()?;
        parser.skip_rows()?;
        parser.skip_rows()?;
    }
    Ok(())
}

fn skip_legacy_mosaics(parser: &mut Parser<'_>) -> Result<(), String> {
    let count = parser.u32()? as usize;
    parser.feasible(count, 48)?;
    for _ in 0..count {
        parser.take(32)?;
        parser.take(8)?;
        parser.skip_digests()?;
        parser.skip_digests()?;
    }
    Ok(())
}

struct Parser<'a> {
    payload: &'a [u8],
    offset: usize,
}

impl<'a> Parser<'a> {
    fn new(payload: &'a [u8]) -> Self {
        Self { payload, offset: 0 }
    }
    fn finished(&self) -> bool {
        self.offset == self.payload.len()
    }
    fn feasible(&self, count: usize, minimum: usize) -> Result<(), String> {
        let required = count
            .checked_mul(minimum)
            .ok_or("materialized count overflow")?;
        if required > self.payload.len().saturating_sub(self.offset) {
            return Err("materialized count exceeds remaining bytes".into());
        }
        Ok(())
    }
    fn take(&mut self, count: usize) -> Result<&'a [u8], String> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or("materialized length overflow")?;
        if end > self.payload.len() {
            return Err("materialized state ended early".into());
        }
        let value = &self.payload[self.offset..end];
        self.offset = end;
        Ok(value)
    }
    fn u16(&mut self) -> Result<u16, String> {
        Ok(u16::from_le_bytes(self.take(2)?.try_into().unwrap()))
    }
    fn u32(&mut self) -> Result<u32, String> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }
    fn u64(&mut self) -> Result<u64, String> {
        Ok(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))
    }
    fn bytes(&mut self) -> Result<&'a [u8], String> {
        let count = self.u32()? as usize;
        self.take(count)
    }
    fn skip_digests(&mut self) -> Result<(), String> {
        let count = self.u32()? as usize;
        let bytes = count
            .checked_mul(32)
            .ok_or("legacy digest count overflow")?;
        self.take(bytes)?;
        Ok(())
    }
    fn skip_rows(&mut self) -> Result<(), String> {
        let count = self.u32()? as usize;
        let bytes = count
            .checked_mul(FIELD_WIDTH * std::mem::size_of::<u64>())
            .ok_or("legacy row count overflow")?;
        self.take(bytes)?;
        Ok(())
    }
}

fn push_u32(output: &mut Vec<u8>, value: usize) -> Result<(), String> {
    output.extend_from_slice(
        &u32::try_from(value)
            .map_err(|_| "materialized cardinality exceeds u32")?
            .to_le_bytes(),
    );
    Ok(())
}

fn hex_digest(value: &[u8; 32]) -> String {
    let mut output = String::with_capacity(64);
    for byte in value {
        use std::fmt::Write;
        write!(&mut output, "{byte:02x}").expect("String writes cannot fail");
    }
    output
}

fn hex_lineage(value: &[u8; 16]) -> String {
    let mut output = String::with_capacity(32);
    for byte in value {
        use std::fmt::Write;
        write!(&mut output, "{byte:02x}").expect("String writes cannot fail");
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    fn minimal_gljnft02() -> Vec<u8> {
        let mut mounted = b"GLJNFT02".to_vec();
        mounted.extend_from_slice(&2u16.to_le_bytes());
        mounted.extend_from_slice(&13u64.to_le_bytes());
        mounted.extend_from_slice(&1u64.to_le_bytes());
        mounted.extend_from_slice(&[0; 32]);
        mounted.push(0);
        mounted.extend_from_slice(&0u32.to_le_bytes());
        mounted.extend_from_slice(&0u32.to_le_bytes());
        mounted.push(0);
        mounted
    }

    fn glmfab03(mounted: &[u8]) -> Vec<u8> {
        let mut fabric = PRIOR_STATE_MAGIC.to_vec();
        fabric.extend_from_slice(&PRIOR_VERSION.to_le_bytes());
        fabric.extend_from_slice(&17u64.to_le_bytes());
        fabric.extend_from_slice(&0u32.to_le_bytes());
        fabric.extend_from_slice(&0u32.to_le_bytes());
        push_u32(&mut fabric, mounted.len()).unwrap();
        fabric.extend_from_slice(mounted);
        fabric
    }

    fn hex_lineage(value: &[u8; 16]) -> String {
        let mut output = String::with_capacity(32);
        for byte in value {
            use std::fmt::Write;
            write!(&mut output, "{byte:02x}").expect("String writes cannot fail");
        }
        output
    }

    #[test]
    fn current_state_contains_only_generation_and_joint_bytes() {
        let state = Fabric {
            generation: 9,
            joint_dsf_state: vec![1, 2, 3],
        };
        let encoded = encode_current_fabric(&state).unwrap();
        assert_eq!(parse_state(&encoded, encoded.len()).unwrap(), state);
        assert_eq!(&encoded[..8], STATE_MAGIC);
    }

    #[test]
    fn authenticated_glmfab03_migration_is_one_way_and_schema_exact() {
        let prior = glmfab03(&minimal_gljnft02());
        let migrated =
            migrate_authenticated_glmfab03_to_current(&prior, sha256(&prior), prior.len(), 1)
                .unwrap();
        assert_eq!(&migrated.current_fabric[..8], STATE_MAGIC);
        assert_eq!(migrated.legacy_fabric_receipt, sha256(&prior));
        assert_eq!(migrated.summary.generation, 13);
        assert_eq!(migrated.summary.transition_receipt, None);
        let parsed = parse_state(&migrated.current_fabric, migrated.current_fabric.len()).unwrap();
        assert_eq!(&parsed.joint_dsf_state[..8], b"GLJDSF03");

        let current = migrated.current_fabric;
        assert_eq!(
            migrate_authenticated_glmfab03_to_current(
                &current,
                sha256(&current),
                current.len(),
                1,
            )
            .unwrap_err(),
            "materialized source evidence is not GLMFAB03"
        );
    }

    #[test]
    fn outer_receipt_authentication_precedes_nested_conversion() {
        let malformed_inner = glmfab03(b"not-a-mounted-state");
        let mut wrong_receipt = sha256(&malformed_inner);
        wrong_receipt[0] ^= 1;
        assert_eq!(
            migrate_authenticated_glmfab03_to_current(
                &malformed_inner,
                wrong_receipt,
                malformed_inner.len(),
                1,
            )
            .unwrap_err(),
            "GLMFAB03 content SHA-256 does not bind the exact body"
        );
        assert_eq!(
            migrate_authenticated_glmfab03_to_current(
                &malformed_inner,
                sha256(&malformed_inner),
                malformed_inner.len(),
                1,
            )
            .unwrap_err(),
            "mounted source evidence is not GLJNFT02"
        );
    }

    #[test]
    fn authenticated_glmfab03_inspector_is_schema_exact_and_read_only() {
        let mounted = minimal_gljnft02();
        let prior = glmfab03(&mounted);
        let inspected =
            inspect_authenticated_glmfab03_legacy_ports(&prior, sha256(&prior), prior.len(), 1)
                .unwrap();
        assert_eq!(inspected.fabric_generation, 17);
        assert_eq!(inspected.mounted_generation, 13);
        assert_eq!(inspected.next_lineage_ordinal, 1);
        assert!(inspected.neurons.is_empty());

        let mut wrong_content_sha256 = sha256(&prior);
        wrong_content_sha256[0] ^= 1;
        assert_eq!(
            inspect_authenticated_glmfab03_legacy_ports(
                &prior,
                wrong_content_sha256,
                prior.len(),
                1,
            )
            .unwrap_err(),
            "GLMFAB03 content SHA-256 does not bind the exact body"
        );

        let current = encode_current_fabric(&Fabric {
            generation: 13,
            joint_dsf_state: mounted.clone(),
        })
        .unwrap();
        assert_eq!(
            inspect_authenticated_glmfab03_legacy_ports(
                &current,
                sha256(&current),
                current.len(),
                1,
            )
            .unwrap_err(),
            "materialized source evidence is not GLMFAB03"
        );

        let mut current_mounted = mounted;
        current_mounted[..8].copy_from_slice(b"GLJNFT03");
        current_mounted[8..10].copy_from_slice(&3u16.to_le_bytes());
        let wrong_inner = glmfab03(&current_mounted);
        assert_eq!(
            inspect_authenticated_glmfab03_legacy_ports(
                &wrong_inner,
                sha256(&wrong_inner),
                wrong_inner.len(),
                1,
            )
            .unwrap_err(),
            "mounted source evidence is not GLJNFT02"
        );
    }

    #[test]
    fn authenticated_glmfab03_inspector_refuses_size_malformed_and_trailing_bytes() {
        let prior = glmfab03(&minimal_gljnft02());
        assert_eq!(
            inspect_authenticated_glmfab03_legacy_ports(
                &prior,
                sha256(&prior),
                prior.len() - 1,
                1,
            )
            .unwrap_err(),
            "GLMFAB03 input exceeds admitted storage"
        );

        let malformed = prior[..22].to_vec();
        assert!(inspect_authenticated_glmfab03_legacy_ports(
            &malformed,
            sha256(&malformed),
            malformed.len(),
            1,
        )
        .unwrap_err()
        .contains("ended early"));

        let mut trailing = prior;
        trailing.push(0);
        assert_eq!(
            inspect_authenticated_glmfab03_legacy_ports(
                &trailing,
                sha256(&trailing),
                trailing.len(),
                1,
            )
            .unwrap_err(),
            "materialized state has trailing bytes"
        );

        let mut mounted_trailing = minimal_gljnft02();
        mounted_trailing.push(0);
        let malformed_inner = glmfab03(&mounted_trailing);
        assert_eq!(
            inspect_authenticated_glmfab03_legacy_ports(
                &malformed_inner,
                sha256(&malformed_inner),
                malformed_inner.len(),
                1,
            )
            .unwrap_err(),
            "joint-DSF state has trailing bytes"
        );
    }

    #[test]
    #[ignore = "requires GUALA_TASK853_GLMFAB03 to name the authenticated extraction"]
    fn authenticated_task853_glmfab03_exposes_only_legacy_lineage_and_port_key() {
        let path = std::env::var("GUALA_TASK853_GLMFAB03")
            .expect("GUALA_TASK853_GLMFAB03 must name the extracted body");
        let body = std::fs::read(path).expect("read authenticated task-853 body");
        let expected_content_sha256 = [
            0xb1, 0xf5, 0x38, 0xe2, 0x5d, 0x0b, 0xf5, 0x95, 0x84, 0x26, 0x61, 0x72, 0xcc, 0xb4,
            0x73, 0xb2, 0xb2, 0xdb, 0x6a, 0xd7, 0xdd, 0xf1, 0xfc, 0x1f, 0x7f, 0xfa, 0x54, 0x2b,
            0xd2, 0xcc, 0x7e, 0x14,
        ];
        let inspected = inspect_authenticated_glmfab03_legacy_ports(
            &body,
            expected_content_sha256,
            body.len(),
            256 * 1024 * 1024,
        )
        .unwrap();
        assert_eq!(inspected.fabric_generation, 13);
        assert_eq!(inspected.mounted_generation, 2);
        assert_eq!(inspected.next_lineage_ordinal, 97);
        assert!(!inspected.neurons.is_empty());
        let mut lineages = std::collections::BTreeSet::new();
        for value in &inspected.neurons {
            assert!(lineages.insert(value.lineage));
            assert!(!value.sensor_id.is_empty());
            assert!(!value.substream_id.is_empty());
            println!(
                "{}\t{}\t{}\t{}\t{}",
                hex_lineage(&value.lineage),
                value.sense,
                value.topology_index,
                value.sensor_id,
                value.substream_id,
            );
        }
        println!(
            "task853_glmfab03_generation={}",
            inspected.fabric_generation
        );
        println!(
            "task853_gljnft02_generation={}",
            inspected.mounted_generation
        );
        println!("task853_legacy_neuron_count={}", inspected.neurons.len());
    }

    #[test]
    fn prior_empty_compatibility_arenas_are_discarded_one_way() {
        let mut prior = Vec::new();
        prior.extend_from_slice(PRIOR_STATE_MAGIC);
        prior.extend_from_slice(&PRIOR_VERSION.to_le_bytes());
        prior.extend_from_slice(&7_u64.to_le_bytes());
        prior.extend_from_slice(&0_u32.to_le_bytes());
        prior.extend_from_slice(&0_u32.to_le_bytes());
        prior.extend_from_slice(&3_u32.to_le_bytes());
        prior.extend_from_slice(&[4, 5, 6]);
        let parsed = parse_state(&prior, prior.len()).unwrap();
        assert_eq!(parsed.generation, 7);
        assert_eq!(parsed.joint_dsf_state, [4, 5, 6]);
        let upgraded = encode_current_fabric(&parsed).unwrap();
        assert_eq!(&upgraded[..8], STATE_MAGIC);
        assert!(!upgraded.windows(8).any(|value| value == PRIOR_STATE_MAGIC));
    }

    #[test]
    fn prior_populated_compatibility_arenas_cannot_survive_upgrade() {
        let mut prior = Vec::new();
        prior.extend_from_slice(PRIOR_STATE_MAGIC);
        prior.extend_from_slice(&PRIOR_VERSION.to_le_bytes());
        prior.extend_from_slice(&7_u64.to_le_bytes());
        prior.extend_from_slice(&1_u32.to_le_bytes());
        prior.extend_from_slice(&[1; 32]);
        prior.push(0);
        prior.extend_from_slice(&4_u32.to_le_bytes());
        prior.extend_from_slice(&9_u64.to_le_bytes());
        prior.extend_from_slice(&1_u32.to_le_bytes());
        prior.extend_from_slice(&[2; 32]);
        prior.extend_from_slice(&1_u32.to_le_bytes());
        prior.extend_from_slice(&[3; FIELD_WIDTH * 8]);
        prior.extend_from_slice(&1_u32.to_le_bytes());
        prior.extend_from_slice(&[4; FIELD_WIDTH * 8]);
        prior.extend_from_slice(&1_u32.to_le_bytes());
        prior.extend_from_slice(&[5; 32]);
        prior.extend_from_slice(&10_u64.to_le_bytes());
        prior.extend_from_slice(&1_u32.to_le_bytes());
        prior.extend_from_slice(&[1; 32]);
        prior.extend_from_slice(&1_u32.to_le_bytes());
        prior.extend_from_slice(&[1; 32]);
        prior.extend_from_slice(&3_u32.to_le_bytes());
        prior.extend_from_slice(&[4, 5, 6]);
        let parsed = parse_state(&prior, prior.len()).unwrap();
        assert_eq!(parsed.joint_dsf_state, [4, 5, 6]);
        let upgraded = encode_current_fabric(&parsed).unwrap();
        assert_eq!(upgraded.len(), 8 + 2 + 8 + 4 + 3);
        assert_eq!(&upgraded[22..], &[4, 5, 6]);
    }
}
