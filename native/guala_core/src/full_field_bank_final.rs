//! Final one-call immutable native bank for one complete six-sense L0--L4
//! causal boundary.
//!
//! The caller supplies one typed physical episode.  Rust validates its exact
//! affine transduction, settles every admitted port through the unchanged
//! canonical L0--L4 implementation, builds every exact seven-field tuple and
//! basin, and returns one immutable bank.  There are no per-layer owners,
//! Python callbacks, OCR fields, labels, compatibility vectors, or hidden
//! identity channels.

use std::collections::{BTreeMap, BTreeSet};
use std::mem::size_of;
use std::sync::Arc;

use num_bigint::{BigInt, BigUint};
use num_rational::BigRational;
use num_traits::{Signed, ToPrimitive, Zero};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::canonical_basin::generate_port_basin;
use crate::canonical_l0_l4::{
    current_canonical_kernel_config_payload, settle_current_canonical_port,
};
use crate::sha256::sha256;

const CANDIDATE_MAGIC: &[u8; 8] = b"GLNEPI03";
const BANK_MAGIC: &[u8; 8] = b"GLNBK003";
const SCHEMA_VERSION: u16 = 3;
const SENSES: [&str; 6] = ["sight", "sound", "touch", "smell", "taste", "body"];
const MAX_SIGHT_PORTS: usize = 162;
const MAX_SOUND_PORTS: usize = 64;
const MAX_OTHER_PORTS: usize = 16;
const MAX_PORTS: usize = MAX_SIGHT_PORTS + MAX_SOUND_PORTS + 4 * MAX_OTHER_PORTS;
const MAX_SAMPLES_PER_PORT: usize = 2_048;
const MAX_SAMPLES_PER_SETTLEMENT: usize = 32_768;
const FIELD_NAMES: [&str; 7] = ["D_k", "M_k", "R_rev_k", "U_star_k", "C_k", "P_k", "B_k"];
const SIGNED_UNIT_MAP_ID: &str = "signed-unit-affine-v1";
const SIGNED_UNIT_PROFILE: &[u8] = b"guala.live.native_sensory.F_equals_1_plus_s_over_2.v1";
const LIVE_SENSORY_PROFILE: &[u8] = b"guala.live.native_sensory_l0_l4.profile.v1";

#[derive(Clone, Debug, Eq, PartialEq)]
struct RationalText {
    numerator: String,
    denominator: String,
    value: BigRational,
}

#[derive(Clone, Debug)]
struct Coordinate {
    axis_id: String,
    coordinate_id: String,
}

#[derive(Clone, Debug)]
struct InputMap {
    map_id: String,
    source_min: RationalText,
    source_max: RationalText,
    field_offset: RationalText,
    field_scale: RationalText,
    profile_payload: Arc<[u8]>,
}

#[derive(Clone, Debug)]
struct SourceSample {
    timestamp: RationalText,
    signal_bits: u64,
    phase_turns: RationalText,
    relevance: RationalText,
    dimensionless_field: RationalText,
    field_bits: u64,
    relevance_bits: u64,
}

#[derive(Clone, Debug)]
struct CandidatePort {
    sense: u8,
    topology_index: u32,
    sensor_id: String,
    substream_id: String,
    coordinates: Vec<Coordinate>,
    physical_quantity: String,
    physical_unit: String,
    relevance_rule: String,
    relevance_origin: Option<String>,
    input_map: InputMap,
    samples: Vec<SourceSample>,
}

#[derive(Clone, Debug)]
struct Record {
    digest: [u8; 32],
    payload: Arc<[u8]>,
}

#[derive(Clone, Debug)]
struct ParsedCandidate {
    candidate_digest: [u8; 32],
    config_digest: [u8; 32],
    episode_id: String,
    sense_states: [u8; 6],
    ports: Vec<CandidatePort>,
    records: Vec<Record>,
    record_indices: BTreeMap<[u8; 32], usize>,
    sample_count: usize,
}

#[derive(Clone, Debug)]
struct SettledPort {
    sense: u8,
    topology_index: u32,
    sensor_id: String,
    substream_id: String,
    input_map_group_receipt: [u8; 32],
    source_times: Vec<BigRational>,
    dimensionless_fields: Vec<BigRational>,
    source_digest: [u8; 32],
    adapter_digest: [u8; 32],
    trace_digest: [u8; 32],
    tuple_digests: Vec<[u8; 32]>,
    basin_digest: [u8; 32],
    gates: Vec<(usize, usize)>,
    rows: Vec<[u64; 7]>,
}

#[derive(Debug)]
struct StoredPort {
    sense: u8,
    topology_index: u32,
    sensor_id: String,
    substream_id: String,
    input_map_group_receipt: [u8; 32],
    source_times: Vec<BigRational>,
    dimensionless_fields: Vec<BigRational>,
    trace_digest: [u8; 32],
    tuple_digests: Vec<[u8; 32]>,
    basin_digest: [u8; 32],
    rows: Vec<[u64; 7]>,
}

#[derive(Debug)]
struct BankStorage {
    payload: Arc<[u8]>,
    payload_digest: [u8; 32],
    config_digest: [u8; 32],
    candidate_digest: [u8; 32],
    root_digest: [u8; 32],
    port_count: usize,
    sample_count: usize,
    field_row_count: usize,
    record_count: usize,
    sense_states: [u8; 6],
    ports: Vec<StoredPort>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct RegeneratedDsfDelivery {
    pub(crate) candidate_receipt: [u8; 32],
    pub(crate) bank_receipt: [u8; 32],
    pub(crate) kernel_config_receipt: [u8; 32],
    pub(crate) port_index: u64,
    pub(crate) tuple_index: u64,
    pub(crate) trace_receipt: [u8; 32],
    pub(crate) tuple_receipt: [u8; 32],
    pub(crate) basin_receipt: [u8; 32],
    pub(crate) coordinate_bits: [u64; 7],
}

/// Owns one regenerated bank directly. Callers borrow this same bank across
/// all neuron delivery checks, without cloning or reparsing it.
#[derive(Debug)]
pub(crate) struct RegeneratedFullFieldBank {
    storage: BankStorage,
}

impl RegeneratedFullFieldBank {
    pub(crate) fn candidate_receipt(&self) -> [u8; 32] {
        self.storage.candidate_digest
    }

    pub(crate) fn bank_receipt(&self) -> [u8; 32] {
        self.storage.payload_digest
    }

    pub(crate) fn kernel_config_receipt(&self) -> [u8; 32] {
        self.storage.config_digest
    }

    pub(crate) fn bank_bytes(&self) -> &[u8] {
        &self.storage.payload
    }

    pub(crate) fn port_count(&self) -> usize {
        self.storage.port_count
    }

    pub(crate) fn sample_count(&self) -> usize {
        self.storage.sample_count
    }

    pub(crate) fn field_row_count(&self) -> usize {
        self.storage.field_row_count
    }

    pub(crate) fn delivery(
        &self,
        port_index: u64,
        tuple_index: u64,
    ) -> Result<RegeneratedDsfDelivery, &'static str> {
        let port_position = usize::try_from(port_index)
            .map_err(|_| "regenerated bank port index is outside the bank")?;
        let tuple_position = usize::try_from(tuple_index)
            .map_err(|_| "regenerated bank tuple index is outside the port")?;
        let port = self
            .storage
            .ports
            .get(port_position)
            .ok_or("regenerated bank port index is outside the bank")?;
        let tuple_receipt = *port
            .tuple_digests
            .get(tuple_position)
            .ok_or("regenerated bank tuple index is outside the port")?;
        let coordinate_bits = *port
            .rows
            .get(tuple_position)
            .ok_or("regenerated bank tuple row is missing")?;
        Ok(RegeneratedDsfDelivery {
            candidate_receipt: self.storage.candidate_digest,
            bank_receipt: self.storage.payload_digest,
            kernel_config_receipt: self.storage.config_digest,
            port_index,
            tuple_index,
            trace_receipt: port.trace_digest,
            tuple_receipt,
            basin_receipt: port.basin_digest,
            coordinate_bits,
        })
    }
}

/// Caller acceptance bounds for one regenerated bank. The bank-byte limit is
/// checked against the exact serialized length before the bank output allocation.
/// It is not a complete transient-RAM ceiling: settlement records are created
/// first, under the admitted candidate byte bound and the intrinsic 290-port,
/// 32768-sample, and per-port 2048-sample topology laws.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct FullFieldRegenerationBudget {
    pub(crate) max_candidate_bytes: u64,
    pub(crate) max_bank_bytes: u64,
    pub(crate) max_port_count: u64,
    pub(crate) max_sample_count: u64,
    pub(crate) max_field_row_count: u64,
}

impl FullFieldRegenerationBudget {
    fn unbounded() -> Self {
        Self {
            max_candidate_bytes: u64::MAX,
            max_bank_bytes: u64::MAX,
            max_port_count: u64::MAX,
            max_sample_count: u64::MAX,
            max_field_row_count: u64::MAX,
        }
    }
}

pub(crate) fn regenerate_full_field_bank(
    candidate_payload: &[u8],
    budget: FullFieldRegenerationBudget,
) -> Result<RegeneratedFullFieldBank, String> {
    let candidate_bytes = u64::try_from(candidate_payload.len())
        .map_err(|_| "native candidate input length overflow".to_string())?;
    if candidate_bytes > budget.max_candidate_bytes {
        return Err("native candidate exceeds caller-derived input budget".into());
    }
    settle_candidate(candidate_payload, budget).map(|storage| RegeneratedFullFieldBank { storage })
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct MaterializedPortView {
    pub(crate) sense: u8,
    pub(crate) topology_index: u32,
    pub(crate) rows: Vec<[u64; 7]>,
}

#[pyclass(frozen, module = "guala_core")]
#[derive(Clone)]
pub struct NativeL0L4FullFieldBank {
    storage: Arc<BankStorage>,
}

#[pymethods]
impl NativeL0L4FullFieldBank {
    #[getter]
    fn schema(&self) -> &'static str {
        "guala.native.immutable_canonical_l0_l4_full_field_bank.v3"
    }

    #[getter]
    fn payload_sha256(&self) -> String {
        hex_digest(&self.storage.payload_digest)
    }

    #[getter]
    fn kernel_config_sha256(&self) -> String {
        hex_digest(&self.storage.config_digest)
    }

    #[getter]
    fn episode_input_sha256(&self) -> String {
        hex_digest(&self.storage.candidate_digest)
    }

    #[getter]
    fn root_sha256(&self) -> String {
        hex_digest(&self.storage.root_digest)
    }

    #[getter]
    fn port_count(&self) -> usize {
        self.storage.port_count
    }

    #[getter]
    fn source_sample_count(&self) -> usize {
        self.storage.sample_count
    }

    #[getter]
    fn field_row_count(&self) -> usize {
        self.storage.field_row_count
    }

    #[getter]
    fn record_count(&self) -> usize {
        self.storage.record_count
    }

    #[getter]
    fn python_callback_count(&self) -> usize {
        0
    }

    fn as_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.storage.payload)
    }

    fn field_row_bits(&self, port_index: usize, row_index: usize) -> PyResult<Vec<u64>> {
        let port = self
            .storage
            .ports
            .get(port_index)
            .ok_or_else(|| PyValueError::new_err("port index is outside the bank"))?;
        port.rows
            .get(row_index)
            .map(|row| row.to_vec())
            .ok_or_else(|| PyValueError::new_err("field row index is outside the port"))
    }

    fn field_names(&self) -> Vec<&'static str> {
        FIELD_NAMES.to_vec()
    }
}

impl NativeL0L4FullFieldBank {
    pub(crate) fn materialized_sense_states(&self) -> [u8; 6] {
        self.storage.sense_states
    }

    pub(crate) fn materialized_ports(&self) -> Vec<MaterializedPortView> {
        self.storage
            .ports
            .iter()
            .map(|port| MaterializedPortView {
                sense: port.sense,
                topology_index: port.topology_index,
                rows: port.rows.clone(),
            })
            .collect()
    }
}

#[pyfunction]
pub fn settle_native_l0_l4_full_field_batch(
    candidate_payload: Vec<u8>,
) -> PyResult<NativeL0L4FullFieldBank> {
    settle_candidate(&candidate_payload, FullFieldRegenerationBudget::unbounded())
        .map(|storage| NativeL0L4FullFieldBank {
            storage: Arc::new(storage),
        })
        .map_err(PyValueError::new_err)
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NativeL0L4FullFieldBank>()?;
    module.add_function(wrap_pyfunction!(
        settle_native_l0_l4_full_field_batch,
        module
    )?)?;
    Ok(())
}

fn settle_candidate(
    payload: &[u8],
    budget: FullFieldRegenerationBudget,
) -> Result<BankStorage, String> {
    let mut parsed =
        Parser::new(payload, budget.max_port_count, budget.max_sample_count).parse()?;
    if u64::try_from(parsed.ports.len())
        .map_err(|_| "native regenerated port count overflow".to_string())?
        > budget.max_port_count
    {
        return Err("native regenerated bank exceeds caller-derived port budget".into());
    }
    if u64::try_from(parsed.sample_count)
        .map_err(|_| "native regenerated sample count overflow".to_string())?
        > budget.max_sample_count
    {
        return Err("native regenerated bank exceeds caller-derived sample budget".into());
    }
    let mut settled_ports = Vec::with_capacity(parsed.ports.len());
    let mut field_row_count = 0usize;
    for port in &parsed.ports {
        let sense = SENSES[port.sense as usize];
        let calibration_payload = calibration_record(port);
        let calibration_digest = mount_record(
            &mut parsed.records,
            &mut parsed.record_indices,
            Arc::from(calibration_payload),
        )?;
        let relevance_payload = relevance_record(port);
        let relevance_digest = mount_record(
            &mut parsed.records,
            &mut parsed.record_indices,
            Arc::from(relevance_payload),
        )?;
        mount_record(
            &mut parsed.records,
            &mut parsed.record_indices,
            Arc::clone(&port.input_map.profile_payload),
        )?;
        let source_payload = source_record(
            port,
            &parsed.episode_id,
            &calibration_digest,
            &relevance_digest,
        );
        let source_digest = mount_record(
            &mut parsed.records,
            &mut parsed.record_indices,
            Arc::from(source_payload),
        )?;
        let adapter_payload = adapter_record(port, &source_digest);
        let adapter_digest = mount_record(
            &mut parsed.records,
            &mut parsed.record_indices,
            Arc::from(adapter_payload),
        )?;
        let field_bits: Vec<u64> = port.samples.iter().map(|value| value.field_bits).collect();
        let relevance_bits: Vec<u64> = port
            .samples
            .iter()
            .map(|value| value.relevance_bits)
            .collect();
        let legacy_map = is_signed_unit_map(&port.input_map);
        let map_json = if legacy_map {
            b"{}".to_vec()
        } else {
            input_map_json(&port.input_map)
        };
        let settled = settle_current_canonical_port(
            &field_bits,
            &relevance_bits,
            sense,
            &port.substream_id,
            &hex_digest(&adapter_digest),
            &hex_digest(&source_digest),
            &map_json,
            legacy_map,
        )?;
        let basin = generate_port_basin(
            sense,
            &port.substream_id,
            &settled.trace_digest,
            settled.l0_count,
            &settled.l1_gates,
            &settled.l2_regimes,
            settled.l3_count,
            &settled.l4_rows_bits,
        )?;
        mount_record(
            &mut parsed.records,
            &mut parsed.record_indices,
            Arc::from(settled.trace_payload),
        )?;
        for tuple_payload in basin.tuple_payloads {
            mount_record(
                &mut parsed.records,
                &mut parsed.record_indices,
                Arc::from(tuple_payload),
            )?;
        }
        mount_record(
            &mut parsed.records,
            &mut parsed.record_indices,
            Arc::from(basin.basin_payload),
        )?;
        field_row_count = field_row_count
            .checked_add(settled.l4_rows_bits.len())
            .ok_or_else(|| "native field row count overflow".to_string())?;
        if u64::try_from(field_row_count)
            .map_err(|_| "native regenerated field-row count overflow".to_string())?
            > budget.max_field_row_count
        {
            return Err("native regenerated bank exceeds caller-derived field-row budget".into());
        }
        settled_ports.push(SettledPort {
            sense: port.sense,
            topology_index: port.topology_index,
            sensor_id: port.sensor_id.clone(),
            substream_id: port.substream_id.clone(),
            input_map_group_receipt: {
                let mut payload = input_map_json(&port.input_map);
                payload.extend_from_slice(&sha256(&port.input_map.profile_payload));
                sha256(&payload)
            },
            source_times: port
                .samples
                .iter()
                .map(|sample| sample.timestamp.value.clone())
                .collect(),
            dimensionless_fields: port
                .samples
                .iter()
                .map(|sample| sample.dimensionless_field.value.clone())
                .collect(),
            source_digest,
            adapter_digest,
            trace_digest: settled.trace_digest,
            tuple_digests: basin.tuple_digests,
            basin_digest: basin.basin_digest,
            gates: settled.l1_gates,
            rows: settled.l4_rows_bits,
        });
    }
    if u64::try_from(field_row_count)
        .map_err(|_| "native regenerated field-row count overflow".to_string())?
        > budget.max_field_row_count
    {
        return Err("native regenerated bank exceeds caller-derived field-row budget".into());
    }
    let root = root_record(
        &parsed.episode_id,
        &parsed.candidate_digest,
        &parsed.config_digest,
        &parsed.sense_states,
        &settled_ports,
    );
    let root_digest = mount_record(
        &mut parsed.records,
        &mut parsed.record_indices,
        Arc::from(root),
    )?;
    let output = bank_payload(
        &parsed,
        root_digest,
        field_row_count,
        &settled_ports,
        budget.max_bank_bytes,
    )?;
    let payload_digest = sha256(&output);
    let ports = settled_ports
        .into_iter()
        .map(|port| StoredPort {
            sense: port.sense,
            topology_index: port.topology_index,
            sensor_id: port.sensor_id,
            substream_id: port.substream_id,
            input_map_group_receipt: port.input_map_group_receipt,
            source_times: port.source_times,
            dimensionless_fields: port.dimensionless_fields,
            trace_digest: port.trace_digest,
            tuple_digests: port.tuple_digests,
            basin_digest: port.basin_digest,
            rows: port.rows,
        })
        .collect();
    Ok(BankStorage {
        payload: Arc::from(output),
        payload_digest,
        config_digest: parsed.config_digest,
        candidate_digest: parsed.candidate_digest,
        root_digest,
        port_count: parsed.ports.len(),
        sample_count: parsed.sample_count,
        field_row_count,
        record_count: parsed.records.len(),
        sense_states: parsed.sense_states,
        ports,
    })
}

struct Parser<'a> {
    bytes: &'a [u8],
    offset: usize,
    max_port_count: u64,
    max_sample_count: u64,
    records: Vec<Record>,
    record_indices: BTreeMap<[u8; 32], usize>,
}

impl<'a> Parser<'a> {
    fn new(bytes: &'a [u8], max_port_count: u64, max_sample_count: u64) -> Self {
        Self {
            bytes,
            offset: 0,
            max_port_count,
            max_sample_count,
            records: Vec::new(),
            record_indices: BTreeMap::new(),
        }
    }

    fn parse(mut self) -> Result<ParsedCandidate, String> {
        let candidate_digest = sha256(self.bytes);
        if self.take(8)? != CANDIDATE_MAGIC {
            return Err("native episode magic is not GLNEPI03".into());
        }
        if self.u16()? != SCHEMA_VERSION {
            return Err("unsupported native episode version".into());
        }
        let config = self.bytes()?;
        if config.as_ref() != current_canonical_kernel_config_payload().as_slice() {
            return Err("native episode names a noncanonical L0-L4 configuration".into());
        }
        let config_digest = mount_record(&mut self.records, &mut self.record_indices, config)?;
        let episode_id = self.identifier("episode_id")?;
        let mut sense_states = [0u8; 6];
        for state in &mut sense_states {
            *state = self.u8()?;
            if *state > 3 {
                return Err("sense state is outside the canonical enum".into());
            }
        }
        let port_count = self.u32()? as usize;
        if port_count > MAX_PORTS {
            return Err("native episode exceeds the ratified 290-port topology".into());
        }
        if u64::try_from(port_count)
            .map_err(|_| "native regenerated port count overflow".to_string())?
            > self.max_port_count
        {
            return Err("native regenerated bank exceeds caller-derived port budget".into());
        }
        let mut ports = Vec::new();
        ports
            .try_reserve_exact(port_count)
            .map_err(|_| "native candidate port allocation failed".to_string())?;
        let mut sample_count = 0usize;
        let mut keys = BTreeSet::new();
        let mut indices: [Vec<u32>; 6] = Default::default();
        for _ in 0..port_count {
            let admitted_samples = u64::try_from(sample_count)
                .map_err(|_| "native regenerated sample count overflow".to_string())?;
            let remaining_samples = self
                .max_sample_count
                .checked_sub(admitted_samples)
                .ok_or_else(|| {
                    "native regenerated bank exceeds caller-derived sample budget".to_string()
                })?;
            let port = self.port(remaining_samples)?;
            sample_count = sample_count
                .checked_add(port.samples.len())
                .ok_or_else(|| "native settlement sample count overflow".to_string())?;
            if sample_count > MAX_SAMPLES_PER_SETTLEMENT {
                return Err("native episode exceeds the ratified 32768-sample settlement".into());
            }
            if !keys.insert((
                port.sense,
                port.sensor_id.clone(),
                port.substream_id.clone(),
            )) {
                return Err("native episode repeats a sensory substream".into());
            }
            if sense_states[port.sense as usize] != 0 {
                return Err("a non-observed sense contains a fabricated port".into());
            }
            indices[port.sense as usize].push(port.topology_index);
            ports.push(port);
        }
        for sense in 0..6 {
            let limit = match sense {
                0 => MAX_SIGHT_PORTS,
                1 => MAX_SOUND_PORTS,
                _ => MAX_OTHER_PORTS,
            };
            if indices[sense].len() > limit {
                return Err(format!(
                    "{} topology exceeds its ratified {limit}-port boundary",
                    SENSES[sense]
                ));
            }
            indices[sense].sort_unstable();
            if sense_states[sense] == 0 && indices[sense].is_empty() {
                return Err("an observed sense has no physical port".into());
            }
            if indices[sense]
                .iter()
                .copied()
                .ne(0..indices[sense].len() as u32)
            {
                return Err("sense topology indices are not complete and ordered".into());
            }
        }
        if self.offset != self.bytes.len() {
            return Err("native episode has trailing bytes".into());
        }
        Ok(ParsedCandidate {
            candidate_digest,
            config_digest,
            episode_id,
            sense_states,
            ports,
            records: self.records,
            record_indices: self.record_indices,
            sample_count,
        })
    }

    fn port(&mut self, remaining_sample_budget: u64) -> Result<CandidatePort, String> {
        let sense = self.u8()?;
        if sense as usize >= SENSES.len() {
            return Err("port sense is outside the six-sense topology".into());
        }
        let topology_index = self.u32()?;
        let sensor_id = self.identifier("sensor_id")?;
        let substream_id = self.identifier("substream_id")?;
        let coordinate_count = self.u16()? as usize;
        if coordinate_count == 0 {
            return Err("native coordinate topology is empty".into());
        }
        let mut coordinates = Vec::new();
        coordinates
            .try_reserve_exact(coordinate_count)
            .map_err(|_| "native coordinate allocation failed".to_string())?;
        let mut axes = BTreeSet::new();
        for _ in 0..coordinate_count {
            let axis_id = self.identifier("axis_id")?;
            let coordinate_id = self.identifier("coordinate_id")?;
            if !axes.insert(axis_id.clone()) {
                return Err("native substream repeats a coordinate axis".into());
            }
            coordinates.push(Coordinate {
                axis_id,
                coordinate_id,
            });
        }
        let physical_quantity = self.identifier("physical_quantity")?;
        let physical_unit = self.identifier("physical_unit")?;
        let relevance_rule = self.identifier("relevance_rule")?;
        let relevance_origin = self.optional_identifier("relevance_origin")?;
        let input_map = InputMap {
            map_id: self.identifier("map_id")?,
            source_min: self.rational("source_min")?,
            source_max: self.rational("source_max")?,
            field_offset: self.rational("field_offset")?,
            field_scale: self.rational("field_scale")?,
            profile_payload: self.bytes()?,
        };
        validate_input_map(&input_map)?;
        let sample_count = self.u32()? as usize;
        if sample_count == 0 || sample_count > MAX_SAMPLES_PER_PORT {
            return Err("port exceeds the ratified 2048-sample boundary".into());
        }
        if u64::try_from(sample_count)
            .map_err(|_| "native regenerated sample count overflow".to_string())?
            > remaining_sample_budget
        {
            return Err("native regenerated bank exceeds caller-derived sample budget".into());
        }
        let mut samples = Vec::new();
        samples
            .try_reserve_exact(sample_count)
            .map_err(|_| "native sample allocation failed".to_string())?;
        let mut prior_time: Option<BigRational> = None;
        for _ in 0..sample_count {
            let timestamp = self.rational("timestamp")?;
            if prior_time
                .as_ref()
                .is_some_and(|prior| timestamp.value <= *prior)
            {
                return Err("native source times do not increase strictly".into());
            }
            prior_time = Some(timestamp.value.clone());
            let signal_bits = self.u64()?;
            let signal_value = f64::from_bits(signal_bits);
            if !signal_value.is_finite() || !(-1.0..=1.0).contains(&signal_value) {
                return Err("native signal is nonfinite or outside [-1,1]".into());
            }
            let phase_turns = self.rational("phase_turns")?;
            let relevance = self.rational("relevance")?;
            let dimensionless_field = self.rational("dimensionless_field")?;
            let field_bits = self.u64()?;
            let relevance_bits = self.u64()?;
            validate_sample(
                &input_map,
                signal_bits,
                &relevance,
                &dimensionless_field,
                field_bits,
                relevance_bits,
            )?;
            samples.push(SourceSample {
                timestamp,
                signal_bits,
                phase_turns,
                relevance,
                dimensionless_field,
                field_bits,
                relevance_bits,
            });
        }
        Ok(CandidatePort {
            sense,
            topology_index,
            sensor_id,
            substream_id,
            coordinates,
            physical_quantity,
            physical_unit,
            relevance_rule,
            relevance_origin,
            input_map,
            samples,
        })
    }

    fn rational(&mut self, name: &str) -> Result<RationalText, String> {
        let numerator = self.text()?;
        let denominator = self.text()?;
        let numerator_value = canonical_integer(&numerator, &format!("{name} numerator"))?;
        let denominator_value = canonical_integer(&denominator, &format!("{name} denominator"))?;
        if denominator_value <= BigInt::zero() {
            return Err(format!("{name} denominator is not positive"));
        }
        let value = BigRational::new(numerator_value, denominator_value);
        if value.numer().to_string() != numerator || value.denom().to_string() != denominator {
            return Err(format!("{name} is not in reduced canonical form"));
        }
        Ok(RationalText {
            numerator,
            denominator,
            value,
        })
    }

    fn identifier(&mut self, name: &str) -> Result<String, String> {
        let value = self.text()?;
        if value.is_empty() || value.trim() != value {
            return Err(format!("{name} is not a nonempty canonical identifier"));
        }
        Ok(value)
    }

    fn optional_identifier(&mut self, name: &str) -> Result<Option<String>, String> {
        let value = self.text()?;
        if value.is_empty() {
            return Ok(None);
        }
        if value.trim() != value {
            return Err(format!("{name} is not a canonical identifier"));
        }
        Ok(Some(value))
    }

    fn text(&mut self) -> Result<String, String> {
        let length = self.u16()? as usize;
        std::str::from_utf8(self.take(length)?)
            .map(str::to_owned)
            .map_err(|_| "native episode text is not UTF-8".into())
    }

    fn bytes(&mut self) -> Result<Arc<[u8]>, String> {
        let length = self.u32()? as usize;
        if length == 0 {
            return Err("native episode byte record is empty".into());
        }
        Ok(Arc::from(self.take(length)?))
    }

    fn u8(&mut self) -> Result<u8, String> {
        Ok(self.take(1)?[0])
    }

    fn u16(&mut self) -> Result<u16, String> {
        Ok(u16::from_le_bytes(
            self.take(2)?.try_into().expect("length checked"),
        ))
    }

    fn u32(&mut self) -> Result<u32, String> {
        Ok(u32::from_le_bytes(
            self.take(4)?.try_into().expect("length checked"),
        ))
    }

    fn u64(&mut self) -> Result<u64, String> {
        Ok(u64::from_le_bytes(
            self.take(8)?.try_into().expect("length checked"),
        ))
    }

    fn take(&mut self, length: usize) -> Result<&'a [u8], String> {
        let end = self
            .offset
            .checked_add(length)
            .ok_or_else(|| "native episode length overflow".to_string())?;
        if end > self.bytes.len() {
            return Err("native episode ended before its declared structure".into());
        }
        let value = &self.bytes[self.offset..end];
        self.offset = end;
        Ok(value)
    }
}

fn validate_input_map(map: &InputMap) -> Result<(), String> {
    if map.source_max.value <= map.source_min.value {
        return Err("kernel input map source interval is empty".into());
    }
    if map.field_scale.value.is_zero() {
        return Err("kernel input map is not invertible".into());
    }
    for source in [&map.source_min.value, &map.source_max.value] {
        if &map.field_offset.value + &map.field_scale.value * source <= BigRational::zero() {
            return Err("kernel input map does not remain positive for L0".into());
        }
    }
    Ok(())
}

fn validate_sample(
    map: &InputMap,
    signal_bits: u64,
    relevance: &RationalText,
    field: &RationalText,
    field_bits: u64,
    relevance_bits: u64,
) -> Result<(), String> {
    let signal = rational_from_f64_bits(signal_bits)?;
    if signal < map.source_min.value || signal > map.source_max.value {
        return Err("native signal left its exact input-map calibration".into());
    }
    let expected = &map.field_offset.value + &map.field_scale.value * signal;
    if field.value != expected {
        return Err("dimensionless field differs from the exact affine map".into());
    }
    if relevance.value < BigRational::zero()
        || relevance.value > BigRational::from_integer(1.into())
    {
        return Err("source relevance is outside [0,1]".into());
    }
    if rational_to_f64_bits(&field.value)? != field_bits {
        return Err("field binary64 differs from exact nearest-even transduction".into());
    }
    if rational_to_f64_bits(&relevance.value)? != relevance_bits {
        return Err("relevance binary64 differs from its exact authority".into());
    }
    Ok(())
}

fn rational_from_f64_bits(bits: u64) -> Result<BigRational, String> {
    let value = f64::from_bits(bits);
    if !value.is_finite() {
        return Err("binary64 value is nonfinite".into());
    }
    if value == 0.0 {
        return Ok(BigRational::zero());
    }
    let negative = bits >> 63 != 0;
    let exponent_bits = ((bits >> 52) & 0x7ff) as i32;
    let fraction_bits = bits & ((1u64 << 52) - 1);
    let (mantissa, exponent) = if exponent_bits == 0 {
        (fraction_bits, -1074)
    } else {
        ((1u64 << 52) | fraction_bits, exponent_bits - 1023 - 52)
    };
    let mut numerator = BigInt::from(mantissa);
    let mut denominator = BigInt::from(1u8);
    if exponent >= 0 {
        numerator <<= exponent as usize;
    } else {
        denominator <<= (-exponent) as usize;
    }
    if negative {
        numerator = -numerator;
    }
    Ok(BigRational::new(numerator, denominator))
}

fn rational_to_f64_bits(value: &BigRational) -> Result<u64, String> {
    if value.is_zero() {
        return Ok(0);
    }
    let negative = value.is_negative();
    let numerator = value
        .numer()
        .abs()
        .to_biguint()
        .ok_or_else(|| "rational numerator cannot become unsigned".to_string())?;
    let denominator = value
        .denom()
        .to_biguint()
        .ok_or_else(|| "rational denominator cannot become unsigned".to_string())?;
    let mut exponent = numerator.bits() as i32 - denominator.bits() as i32;
    let below = if exponent >= 0 {
        numerator < (&denominator << exponent as usize)
    } else {
        (&numerator << (-exponent) as usize) < denominator
    };
    if below {
        exponent -= 1;
    }
    let sign = if negative { 1u64 << 63 } else { 0 };
    if exponent < -1022 {
        let fraction = round_scaled(&numerator, &denominator, 1074)?
            .to_u64()
            .ok_or_else(|| "subnormal binary64 significand overflow".to_string())?;
        if fraction == 0 {
            return Ok(sign);
        }
        if fraction >= (1u64 << 52) {
            return Ok(sign | (1u64 << 52));
        }
        return Ok(sign | fraction);
    }
    if exponent > 1023 {
        return Err("rational overflows finite binary64".into());
    }
    let mut significand = round_scaled(&numerator, &denominator, 52 - exponent)?;
    if significand.bits() > 53 {
        exponent += 1;
        significand = BigUint::from(1u64 << 52);
    }
    if exponent > 1023 {
        return Err("rational rounds beyond finite binary64".into());
    }
    let encoded = significand
        .to_u64()
        .ok_or_else(|| "normal binary64 significand overflow".to_string())?;
    if encoded < (1u64 << 52) || encoded >= (1u64 << 53) {
        return Err("normal binary64 significand is outside its exact range".into());
    }
    Ok(sign | (((exponent + 1023) as u64) << 52) | (encoded - (1u64 << 52)))
}

fn round_scaled(numerator: &BigUint, denominator: &BigUint, shift: i32) -> Result<BigUint, String> {
    let (scaled_numerator, scaled_denominator) = if shift >= 0 {
        (numerator << shift as usize, denominator.clone())
    } else {
        (numerator.clone(), denominator << (-shift) as usize)
    };
    let quotient = &scaled_numerator / &scaled_denominator;
    let remainder = &scaled_numerator % &scaled_denominator;
    let twice = &remainder << 1usize;
    let odd = (&quotient & BigUint::from(1u8)) == BigUint::from(1u8);
    Ok(
        if twice > scaled_denominator || (twice == scaled_denominator && odd) {
            quotient + BigUint::from(1u8)
        } else {
            quotient
        },
    )
}

fn is_signed_unit_map(map: &InputMap) -> bool {
    map.map_id == SIGNED_UNIT_MAP_ID
        && map.source_min.value == BigRational::from_integer((-1).into())
        && map.source_max.value == BigRational::from_integer(1.into())
        && map.field_offset.value == BigRational::from_integer(1.into())
        && map.field_scale.value == BigRational::new(1.into(), 2.into())
        && map.profile_payload.as_ref() == SIGNED_UNIT_PROFILE
}

fn input_map_json(map: &InputMap) -> Vec<u8> {
    let mut output = String::new();
    output.push('{');
    json_key(&mut output, "field_offset");
    json_string(&mut output, &fraction_text(&map.field_offset));
    output.push(',');
    json_key(&mut output, "field_scale");
    json_string(&mut output, &fraction_text(&map.field_scale));
    output.push(',');
    json_key(&mut output, "forward");
    json_string(&mut output, "F=field_offset+field_scale*s");
    output.push(',');
    json_key(&mut output, "inverse");
    json_string(&mut output, "s=(F-field_offset)/field_scale");
    output.push(',');
    json_key(&mut output, "map_id");
    json_string(&mut output, &map.map_id);
    output.push(',');
    json_key(&mut output, "source_max");
    json_string(&mut output, &fraction_text(&map.source_max));
    output.push(',');
    json_key(&mut output, "source_min");
    json_string(&mut output, &fraction_text(&map.source_min));
    output.push('}');
    output.into_bytes()
}

fn calibration_record(port: &CandidatePort) -> Vec<u8> {
    let mut output = String::new();
    output.push('{');
    json_key(&mut output, "physical_quantity");
    json_string(&mut output, &port.physical_quantity);
    output.push(',');
    json_key(&mut output, "physical_unit");
    json_string(&mut output, &port.physical_unit);
    output.push(',');
    json_key(&mut output, "range");
    json_string(&mut output, "[-1,1]");
    output.push(',');
    json_key(&mut output, "schema");
    json_string(&mut output, "guala.live.native_sensory_calibration.v1");
    output.push(',');
    json_key(&mut output, "sense");
    json_string(&mut output, SENSES[port.sense as usize]);
    output.push(',');
    json_key(&mut output, "sensor_id");
    json_string(&mut output, &port.sensor_id);
    output.push(',');
    json_key(&mut output, "substream_id");
    json_string(&mut output, &port.substream_id);
    output.push('}');
    output.into_bytes()
}

fn relevance_record(port: &CandidatePort) -> Vec<u8> {
    let mut output = String::new();
    output.push('{');
    json_key(&mut output, "origin_substream_id");
    json_string(
        &mut output,
        port.relevance_origin
            .as_deref()
            .unwrap_or(&port.substream_id),
    );
    output.push(',');
    json_key(&mut output, "relevance");
    output.push('[');
    for (index, sample) in port.samples.iter().enumerate() {
        if index != 0 {
            output.push(',');
        }
        json_string(&mut output, &fraction_text(&sample.relevance));
    }
    output.push(']');
    output.push(',');
    json_key(&mut output, "rule");
    json_string(&mut output, &port.relevance_rule);
    output.push(',');
    json_key(&mut output, "schema");
    json_string(&mut output, "guala.live.native_sensory.source_relevance.v2");
    output.push(',');
    json_key(&mut output, "sense");
    json_string(&mut output, SENSES[port.sense as usize]);
    output.push(',');
    json_key(&mut output, "sensor_id");
    json_string(&mut output, &port.sensor_id);
    output.push(',');
    json_key(&mut output, "substream_id");
    json_string(&mut output, &port.substream_id);
    output.push('}');
    output.into_bytes()
}

fn source_record(
    port: &CandidatePort,
    episode_id: &str,
    calibration_digest: &[u8; 32],
    relevance_digest: &[u8; 32],
) -> Vec<u8> {
    let profile_digest = sha256(LIVE_SENSORY_PROFILE);
    let mut output = String::new();
    output.push('{');
    json_key(&mut output, "calibration_receipt_sha256");
    json_string(&mut output, &hex_digest(calibration_digest));
    output.push(',');
    json_key(&mut output, "evidence_id");
    json_string(
        &mut output,
        &format!(
            "evidence-{episode_id}-{}-{}",
            SENSES[port.sense as usize], port.topology_index
        ),
    );
    output.push(',');
    json_key(&mut output, "lane_id");
    json_string(&mut output, SENSES[port.sense as usize]);
    output.push(',');
    json_key(&mut output, "physical_unit");
    json_string(&mut output, &port.physical_unit);
    output.push(',');
    json_key(&mut output, "port_id");
    json_string(&mut output, &port.substream_id);
    output.push(',');
    json_key(&mut output, "port_kind");
    json_string(&mut output, &port.physical_quantity);
    output.push(',');
    json_key(&mut output, "profile_binding_sha256");
    json_string(&mut output, &hex_digest(&profile_digest));
    output.push(',');
    json_key(&mut output, "relevance_receipt_sha256");
    json_string(&mut output, &hex_digest(relevance_digest));
    output.push(',');
    json_key(&mut output, "samples");
    output.push('[');
    for (index, sample) in port.samples.iter().enumerate() {
        if index != 0 {
            output.push(',');
        }
        output.push('{');
        json_key(&mut output, "phase_turns");
        json_string(&mut output, &fraction_text(&sample.phase_turns));
        output.push(',');
        json_key(&mut output, "relevance");
        json_string(&mut output, &fraction_text(&sample.relevance));
        output.push(',');
        json_key(&mut output, "signal");
        json_string(
            &mut output,
            &big_rational_text(
                &rational_from_f64_bits(sample.signal_bits)
                    .expect("validated finite binary64 source must remain representable"),
            ),
        );
        output.push(',');
        json_key(&mut output, "source_index");
        output.push_str(&index.to_string());
        output.push(',');
        json_key(&mut output, "timestamp");
        json_string(&mut output, &fraction_text(&sample.timestamp));
        output.push('}');
    }
    output.push(']');
    output.push(',');
    json_key(&mut output, "schema");
    json_string(&mut output, "glew.provider.source_evidence_stream.v1");
    output.push(',');
    json_key(&mut output, "source_epoch");
    json_string(&mut output, episode_id);
    output.push('}');
    output.into_bytes()
}

fn adapter_record(port: &CandidatePort, source_digest: &[u8; 32]) -> Vec<u8> {
    let signed_unit = is_signed_unit_map(&port.input_map);
    let mut output = String::new();
    output.push('{');
    json_key(&mut output, "adapter_id");
    json_string(&mut output, "guala-live-native-sensory");
    output.push(',');
    json_key(&mut output, "adapter_profile_receipt_sha256");
    json_string(
        &mut output,
        &hex_digest(&sha256(&port.input_map.profile_payload)),
    );
    output.push(',');
    json_key(&mut output, "kernel_input_map");
    if signed_unit {
        output.push_str(
            "{\"forward\":\"F=1+s/2\",\"inverse\":\"s=2*(F-1)\",\"range\":\"[1/2,3/2]\"}",
        );
    } else {
        output.push_str(
            std::str::from_utf8(&input_map_json(&port.input_map))
                .expect("input-map JSON is constructed UTF-8"),
        );
    }
    output.push(',');
    json_key(&mut output, "lane_id");
    json_string(&mut output, SENSES[port.sense as usize]);
    output.push(',');
    json_key(&mut output, "native_relevance_rule");
    json_string(&mut output, "exact_source_relevance_identity");
    output.push(',');
    json_key(&mut output, "port_id");
    json_string(&mut output, &port.substream_id);
    output.push(',');
    json_key(&mut output, "samples");
    output.push('[');
    for (index, sample) in port.samples.iter().enumerate() {
        if index != 0 {
            output.push(',');
        }
        output.push('{');
        json_key(&mut output, "dimensionless_field");
        json_string(&mut output, &fraction_text(&sample.dimensionless_field));
        output.push(',');
        json_key(&mut output, "l0_relevance");
        json_string(&mut output, &fraction_text(&sample.relevance));
        output.push(',');
        json_key(&mut output, "source_index");
        output.push_str(&index.to_string());
        output.push(',');
        json_key(&mut output, "timestamp");
        json_string(&mut output, &fraction_text(&sample.timestamp));
        output.push('}');
    }
    output.push(']');
    output.push(',');
    json_key(&mut output, "schema");
    json_string(
        &mut output,
        if signed_unit {
            "glew.provider.kernel_native_input_result.v2"
        } else {
            "glew.provider.kernel_native_input_result.v3"
        },
    );
    output.push(',');
    json_key(&mut output, "source_stream_receipt_sha256");
    json_string(&mut output, &hex_digest(source_digest));
    output.push('}');
    output.into_bytes()
}

fn root_record(
    episode_id: &str,
    candidate_digest: &[u8; 32],
    config_digest: &[u8; 32],
    states: &[u8; 6],
    ports: &[SettledPort],
) -> Vec<u8> {
    let mut output = Vec::new();
    output.extend_from_slice(b"GLROOT03");
    push_text(&mut output, episode_id);
    output.extend_from_slice(candidate_digest);
    output.extend_from_slice(config_digest);
    output.extend_from_slice(states);
    push_u32(&mut output, ports.len());
    for port in ports {
        output.push(port.sense);
        push_u32(&mut output, port.topology_index as usize);
        push_text(&mut output, &port.sensor_id);
        push_text(&mut output, &port.substream_id);
        output.extend_from_slice(&port.source_digest);
        output.extend_from_slice(&port.adapter_digest);
        output.extend_from_slice(&port.trace_digest);
        push_u32(&mut output, port.tuple_digests.len());
        for digest in &port.tuple_digests {
            output.extend_from_slice(digest);
        }
        output.extend_from_slice(&port.basin_digest);
    }
    output
}

struct BankOutputWriter {
    bytes: Vec<u8>,
    planned_length: usize,
}

impl BankOutputWriter {
    fn new(planned_length: usize, max_bank_bytes: u64) -> Result<Self, String> {
        let length_u64 = u64::try_from(planned_length)
            .map_err(|_| "native regenerated bank length overflow".to_string())?;
        if length_u64 > max_bank_bytes {
            return Err("native regenerated bank exceeds caller-derived output budget".into());
        }
        let mut bytes = Vec::new();
        bytes
            .try_reserve_exact(planned_length)
            .map_err(|_| "native regenerated bank allocation failed".to_string())?;
        Ok(Self {
            bytes,
            planned_length,
        })
    }

    fn append(&mut self, value: &[u8]) -> Result<(), String> {
        let end = self
            .bytes
            .len()
            .checked_add(value.len())
            .ok_or_else(|| "native regenerated bank length overflow".to_string())?;
        if end > self.planned_length {
            return Err("native regenerated bank length derivation drifted".into());
        }
        self.bytes.extend_from_slice(value);
        Ok(())
    }

    fn byte(&mut self, value: u8) -> Result<(), String> {
        self.append(&[value])
    }

    fn u16(&mut self, value: u16) -> Result<(), String> {
        self.append(&value.to_le_bytes())
    }

    fn u32(&mut self, value: u32) -> Result<(), String> {
        self.append(&value.to_le_bytes())
    }

    fn usize_u32(&mut self, value: usize) -> Result<(), String> {
        self.u32(
            u32::try_from(value)
                .map_err(|_| "native regenerated bank u32 length overflow".to_string())?,
        )
    }

    fn text(&mut self, value: &str) -> Result<(), String> {
        self.u16(
            u16::try_from(value.len())
                .map_err(|_| "native regenerated bank text length overflow".to_string())?,
        )?;
        self.append(value.as_bytes())
    }

    fn bytes(&mut self, value: &[u8]) -> Result<(), String> {
        self.usize_u32(value.len())?;
        self.append(value)
    }

    fn finish(self) -> Result<Vec<u8>, String> {
        if self.bytes.len() != self.planned_length {
            return Err("native regenerated bank length derivation drifted".into());
        }
        Ok(self.bytes)
    }
}

fn bank_payload(
    parsed: &ParsedCandidate,
    root_digest: [u8; 32],
    field_row_count: usize,
    ports: &[SettledPort],
    max_bank_bytes: u64,
) -> Result<Vec<u8>, String> {
    let length = bank_payload_length(parsed, ports)?;
    let mut output = BankOutputWriter::new(length, max_bank_bytes)?;
    output.append(BANK_MAGIC)?;
    output.u16(SCHEMA_VERSION)?;
    output.append(&parsed.config_digest)?;
    output.append(&parsed.candidate_digest)?;
    output.append(&root_digest)?;
    output.text(&parsed.episode_id)?;
    output.append(&parsed.sense_states)?;
    output.usize_u32(parsed.sample_count)?;
    output.usize_u32(field_row_count)?;
    output.usize_u32(ports.len())?;
    for port in ports {
        output.byte(port.sense)?;
        output.u32(port.topology_index)?;
        output.text(&port.sensor_id)?;
        output.text(&port.substream_id)?;
        output.append(&port.trace_digest)?;
        output.append(&port.basin_digest)?;
        output.usize_u32(port.tuple_digests.len())?;
        for digest in &port.tuple_digests {
            output.append(digest)?;
        }
        output.usize_u32(port.gates.len())?;
        for (start, end) in &port.gates {
            output.usize_u32(*start)?;
            output.usize_u32(*end)?;
        }
        output.usize_u32(port.rows.len())?;
        for row in &port.rows {
            for bits in row {
                output.append(&bits.to_le_bytes())?;
            }
        }
    }
    output.usize_u32(parsed.records.len())?;
    for record in &parsed.records {
        output.append(&record.digest)?;
        output.bytes(&record.payload)?;
    }
    output.finish()
}

fn bank_payload_length(parsed: &ParsedCandidate, ports: &[SettledPort]) -> Result<usize, String> {
    let mut length = 8_usize
        .checked_add(2)
        .and_then(|value| value.checked_add(32 * 3))
        .and_then(|value| value.checked_add(2))
        .and_then(|value| value.checked_add(parsed.episode_id.len()))
        .and_then(|value| value.checked_add(6))
        .and_then(|value| value.checked_add(4 * 3))
        .ok_or_else(|| "native regenerated bank length overflow".to_string())?;
    for port in ports {
        length = length
            .checked_add(1 + 4 + 2 + 2 + 32 + 32 + 4 + 4 + 4)
            .and_then(|value| value.checked_add(port.sensor_id.len()))
            .and_then(|value| value.checked_add(port.substream_id.len()))
            .and_then(|value| {
                port.tuple_digests
                    .len()
                    .checked_mul(32)
                    .and_then(|bytes| value.checked_add(bytes))
            })
            .and_then(|value| {
                port.gates
                    .len()
                    .checked_mul(8)
                    .and_then(|bytes| value.checked_add(bytes))
            })
            .and_then(|value| {
                port.rows
                    .len()
                    .checked_mul(FIELD_NAMES.len() * size_of::<u64>())
                    .and_then(|bytes| value.checked_add(bytes))
            })
            .ok_or_else(|| "native regenerated bank length overflow".to_string())?;
    }
    length = length
        .checked_add(4)
        .ok_or_else(|| "native regenerated bank length overflow".to_string())?;
    for record in &parsed.records {
        length = length
            .checked_add(32 + 4)
            .and_then(|value| value.checked_add(record.payload.len()))
            .ok_or_else(|| "native regenerated bank length overflow".to_string())?;
    }
    Ok(length)
}

fn mount_record(
    records: &mut Vec<Record>,
    indices: &mut BTreeMap<[u8; 32], usize>,
    payload: Arc<[u8]>,
) -> Result<[u8; 32], String> {
    let digest = sha256(&payload);
    if let Some(index) = indices.get(&digest).copied() {
        if records[index].payload.as_ref() != payload.as_ref() {
            return Err("SHA-256 collision at the immutable record arena".into());
        }
    } else {
        indices.insert(digest, records.len());
        records.push(Record { digest, payload });
    }
    Ok(digest)
}

fn canonical_integer(value: &str, name: &str) -> Result<BigInt, String> {
    if value.is_empty()
        || value.starts_with('+')
        || (value.starts_with('0') && value.len() > 1)
        || (value.starts_with("-0"))
    {
        return Err(format!("{name} is not canonical"));
    }
    value
        .parse::<BigInt>()
        .map_err(|_| format!("{name} is not an integer"))
}

fn fraction_text(value: &RationalText) -> String {
    format!("{}/{}", value.numerator, value.denominator)
}

fn big_rational_text(value: &BigRational) -> String {
    format!("{}/{}", value.numer(), value.denom())
}

fn push_u32(output: &mut Vec<u8>, value: usize) {
    output.extend_from_slice(&(value as u32).to_le_bytes());
}

fn push_text(output: &mut Vec<u8>, value: &str) {
    output.extend_from_slice(&(value.len() as u16).to_le_bytes());
    output.extend_from_slice(value.as_bytes());
}

fn push_bytes(output: &mut Vec<u8>, value: &[u8]) {
    push_u32(output, value.len());
    output.extend_from_slice(value);
}

fn json_key(output: &mut String, value: &str) {
    json_string(output, value);
    output.push(':');
}

fn json_string(output: &mut String, value: &str) {
    output.push('"');
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{08}' => output.push_str("\\b"),
            '\u{0c}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            character if character <= '\u{1f}' => {
                use std::fmt::Write;
                write!(output, "\\u{:04x}", character as u32).expect("String writes cannot fail");
            }
            character => output.push(character),
        }
    }
    output.push('"');
}

fn hex_digest(value: &[u8; 32]) -> String {
    let mut output = String::with_capacity(64);
    for byte in value {
        use std::fmt::Write;
        write!(&mut output, "{byte:02x}").expect("String writes cannot fail");
    }
    output
}

#[cfg(test)]
mod tests {
    use super::*;

    fn rational(value: i64, denominator: i64) -> RationalText {
        let value = BigRational::new(value.into(), denominator.into());
        RationalText {
            numerator: value.numer().to_string(),
            denominator: value.denom().to_string(),
            value,
        }
    }

    fn push_fixture_rational(output: &mut Vec<u8>, value: &BigRational) {
        push_text(output, &value.numer().to_string());
        push_text(output, &value.denom().to_string());
    }

    // Adapted from the repository's physical sight fixture in
    // tests/test_native_l0_l4_full_field_bank.py through the production GLNEPI03
    // field order. It retains the exact two admitted samples and no trace bytes.
    fn legitimate_candidate_fixture() -> Vec<u8> {
        let mut output = Vec::new();
        output.extend_from_slice(CANDIDATE_MAGIC);
        output.extend_from_slice(&SCHEMA_VERSION.to_le_bytes());
        push_bytes(&mut output, &current_canonical_kernel_config_payload());
        push_text(&mut output, "episode-1");
        output.extend_from_slice(&[0, 1, 1, 1, 1, 1]);
        push_u32(&mut output, 1);

        output.push(0);
        push_u32(&mut output, 0);
        push_text(&mut output, "retina");
        push_text(&mut output, "retina-0");
        output.extend_from_slice(&2_u16.to_le_bytes());
        push_text(&mut output, "row");
        push_text(&mut output, "0");
        push_text(&mut output, "column");
        push_text(&mut output, "0");
        push_text(&mut output, "optical_intensity");
        push_text(&mut output, "normalized_binary64");
        push_text(&mut output, "exact-unit-source-relevance.v1");
        push_text(&mut output, "");
        push_text(&mut output, SIGNED_UNIT_MAP_ID);
        for value in [
            BigRational::from_integer((-1).into()),
            BigRational::from_integer(1.into()),
            BigRational::from_integer(1.into()),
            BigRational::new(1.into(), 2.into()),
        ] {
            push_fixture_rational(&mut output, &value);
        }
        push_bytes(&mut output, SIGNED_UNIT_PROFILE);

        let samples = [(0_i64, 0_i64, 0.25_f64), (1_i64, 1_i64, -0.5_f64)];
        push_u32(&mut output, samples.len());
        for (timestamp, phase_quarters, signal) in samples {
            push_fixture_rational(&mut output, &BigRational::from_integer(timestamp.into()));
            output.extend_from_slice(&signal.to_bits().to_le_bytes());
            push_fixture_rational(
                &mut output,
                &BigRational::new(phase_quarters.into(), 4.into()),
            );
            push_fixture_rational(&mut output, &BigRational::from_integer(1.into()));
            let exact_signal =
                rational_from_f64_bits(signal.to_bits()).expect("fixture signal is finite");
            let dimensionless_field =
                BigRational::from_integer(1.into()) + exact_signal / BigInt::from(2);
            push_fixture_rational(&mut output, &dimensionless_field);
            output.extend_from_slice(
                &rational_to_f64_bits(&dimensionless_field)
                    .expect("fixture field is finite")
                    .to_le_bytes(),
            );
            output.extend_from_slice(&1.0_f64.to_bits().to_le_bytes());
        }
        output
    }

    fn regeneration_budget(candidate: &[u8]) -> FullFieldRegenerationBudget {
        FullFieldRegenerationBudget {
            max_candidate_bytes: candidate.len() as u64,
            max_bank_bytes: u64::MAX,
            max_port_count: u64::MAX,
            max_sample_count: u64::MAX,
            max_field_row_count: u64::MAX,
        }
    }

    #[test]
    fn regenerated_view_matches_native_bank_and_every_settled_field() {
        let candidate = legitimate_candidate_fixture();
        let regenerated = regenerate_full_field_bank(&candidate, regeneration_budget(&candidate))
            .expect("regenerated");
        let native = settle_native_l0_l4_full_field_batch(candidate.clone())
            .expect("native full-field bank");

        assert_eq!(regenerated.bank_bytes(), native.storage.payload.as_ref());
        assert_eq!(regenerated.bank_receipt(), native.storage.payload_digest);
        assert_eq!(
            regenerated.candidate_receipt(),
            native.storage.candidate_digest
        );
        assert_eq!(
            regenerated.kernel_config_receipt(),
            native.storage.config_digest
        );
        assert_eq!(
            regenerated.kernel_config_receipt(),
            sha256(&current_canonical_kernel_config_payload())
        );
        assert_eq!(
            hex_digest(&regenerated.bank_receipt()),
            native.payload_sha256()
        );
        assert_eq!(
            hex_digest(&regenerated.candidate_receipt()),
            native.episode_input_sha256()
        );
        assert_eq!(
            hex_digest(&regenerated.kernel_config_receipt()),
            native.kernel_config_sha256()
        );

        let port = &native.storage.ports[0];
        assert!(!port.rows.is_empty());
        assert_eq!(port.rows.len(), port.tuple_digests.len());
        for tuple_index in 0..port.rows.len() {
            let delivery = regenerated
                .delivery(0, tuple_index as u64)
                .expect("settled delivery");
            assert_eq!(delivery.candidate_receipt, regenerated.candidate_receipt());
            assert_eq!(delivery.bank_receipt, regenerated.bank_receipt());
            assert_eq!(
                delivery.kernel_config_receipt,
                regenerated.kernel_config_receipt()
            );
            assert_eq!(delivery.port_index, 0);
            assert_eq!(delivery.tuple_index, tuple_index as u64);
            assert_eq!(delivery.trace_receipt, port.trace_digest);
            assert_eq!(delivery.tuple_receipt, port.tuple_digests[tuple_index]);
            assert_eq!(delivery.basin_receipt, port.basin_digest);
            assert_eq!(delivery.coordinate_bits, port.rows[tuple_index]);
            for field_index in 0..FIELD_NAMES.len() {
                assert_eq!(
                    delivery.coordinate_bits[field_index],
                    port.rows[tuple_index][field_index]
                );
            }
        }
    }

    #[test]
    fn regenerated_delivery_indices_fail_closed() {
        let candidate = legitimate_candidate_fixture();
        let regenerated = regenerate_full_field_bank(&candidate, regeneration_budget(&candidate))
            .expect("regenerated");
        assert!(regenerated.delivery(u64::MAX, 0).is_err());
        assert!(regenerated
            .delivery(regenerated.storage.ports.len() as u64, 0)
            .is_err());
        assert!(regenerated.delivery(0, u64::MAX).is_err());
        assert!(regenerated
            .delivery(0, regenerated.storage.ports[0].rows.len() as u64)
            .is_err());
    }

    #[test]
    fn regenerated_bank_rejects_input_over_caller_budget_before_settlement() {
        let candidate = legitimate_candidate_fixture();
        assert_eq!(
            regenerate_full_field_bank(
                &candidate,
                FullFieldRegenerationBudget {
                    max_candidate_bytes: candidate.len() as u64 - 1,
                    ..regeneration_budget(&candidate)
                },
            )
            .unwrap_err(),
            "native candidate exceeds caller-derived input budget"
        );
        regenerate_full_field_bank(&candidate, regeneration_budget(&candidate))
            .expect("exact caller-derived budget");
    }

    #[test]
    fn exact_rational_binary64_rounding_matches_edge_values() {
        for value in [
            0.0,
            f64::from_bits(1),
            f64::MIN_POSITIVE,
            0.5,
            1.0,
            1.5,
            f64::MAX,
        ] {
            let exact = rational_from_f64_bits(value.to_bits()).expect("exact rational");
            assert_eq!(
                rational_to_f64_bits(&exact).expect("rounded bits"),
                value.to_bits()
            );
        }
    }

    #[test]
    fn signed_unit_map_is_exactly_identified() {
        let map = InputMap {
            map_id: SIGNED_UNIT_MAP_ID.into(),
            source_min: rational(-1, 1),
            source_max: rational(1, 1),
            field_offset: rational(1, 1),
            field_scale: rational(1, 2),
            profile_payload: Arc::from(SIGNED_UNIT_PROFILE),
        };
        assert!(is_signed_unit_map(&map));
    }

    #[test]
    fn topology_bound_is_derived_from_ratified_sense_limits() {
        assert_eq!(MAX_PORTS, 290);
        assert_eq!(MAX_SAMPLES_PER_PORT, 2_048);
        assert_eq!(MAX_SAMPLES_PER_SETTLEMENT, 32_768);
    }
}
