//! Exact source-authored joint occurrences for Guala's native organism.
//!
//! `GLJSRC02` carries only the sensory source side of the ratified joint field:
//! exact time, typed receptor vertices, declared groups, the field coordinates,
//! and explicit joint relevance.  It never derives an occurrence from matching
//! clocks, promotes port-local relevance to joint relevance, or invents neuronal
//! contacts.  Resident neuronal contact state is joined later by native prepare.

use std::collections::BTreeSet;
use std::sync::Arc;

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Zero};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

use crate::sha256::sha256;

const MAGIC: &[u8; 8] = b"GLJSRC02";
const VERSION: u16 = 2;
const SENSE_COUNT: usize = 6;

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) struct JointSourceCoordinate {
    pub(crate) axis_id: String,
    pub(crate) coordinate_id: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct JointSourcePortView {
    pub(crate) sense: u8,
    pub(crate) topology_index: u32,
    pub(crate) sensor_id: String,
    pub(crate) substream_id: String,
    pub(crate) coordinates: Vec<JointSourceCoordinate>,
    pub(crate) physical_quantity: String,
    pub(crate) physical_unit: String,
    pub(crate) relevance_rule: String,
    pub(crate) relevance_origin: Option<String>,
    pub(crate) input_map_id: String,
    pub(crate) source_min: BigRational,
    pub(crate) source_max: BigRational,
    pub(crate) field_offset: BigRational,
    pub(crate) field_scale: BigRational,
    pub(crate) input_map_profile: Vec<u8>,
    pub(crate) input_map_group_receipt: [u8; 32],
    pub(crate) source_times: Vec<BigRational>,
    pub(crate) exact_normalized_sources: Vec<BigRational>,
    pub(crate) reported_phase_turns: Vec<BigRational>,
    pub(crate) source_relevances: Vec<BigRational>,
    pub(crate) dimensionless_fields: Vec<BigRational>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct JointSourceOccurrenceView {
    pub(crate) port_indices: Vec<usize>,
    pub(crate) source_times: Vec<BigRational>,
    pub(crate) joint_intersample_profile: Vec<u8>,
    pub(crate) groups: Vec<Vec<usize>>,
    pub(crate) joint_relevance_profile: Vec<u8>,
    pub(crate) joint_relevances: Vec<BigRational>,
    pub(crate) authority_receipt: [u8; 32],
}

#[derive(Debug)]
struct Storage {
    payload: Arc<[u8]>,
    authority_receipt: [u8; 32],
    sense_states: [u8; SENSE_COUNT],
    ports: Vec<JointSourcePortView>,
    occurrences: Vec<JointSourceOccurrenceView>,
    sample_count: usize,
    occurrence_frame_count: usize,
}

#[pyclass(frozen, module = "guala_core")]
#[derive(Clone)]
pub struct NativeJointSourceEpisode {
    storage: Arc<Storage>,
}

#[pymethods]
impl NativeJointSourceEpisode {
    pub(crate) fn joint_source_sample_count(&self) -> usize {
        self.storage.sample_count
    }

    pub(crate) fn joint_source_occurrence_frame_count(&self) -> usize {
        self.storage.occurrence_frame_count
    }

    #[getter]
    fn schema(&self) -> &'static str {
        "guala.native.exact_joint_source_episode.v2"
    }

    #[getter]
    fn payload_sha256(&self) -> String {
        hex_digest(&self.storage.authority_receipt)
    }

    #[getter]
    fn port_count(&self) -> usize {
        self.storage.ports.len()
    }

    #[getter]
    fn source_sample_count(&self) -> usize {
        self.storage.sample_count
    }

    #[getter]
    fn occurrence_count(&self) -> usize {
        self.storage.occurrences.len()
    }

    #[getter]
    fn occurrence_frame_count(&self) -> usize {
        self.storage.occurrence_frame_count
    }

    #[getter]
    fn python_callback_count(&self) -> usize {
        0
    }

    fn as_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.storage.payload)
    }
}

impl NativeJointSourceEpisode {
    pub(crate) fn joint_source_ports(&self) -> &[JointSourcePortView] {
        &self.storage.ports
    }

    pub(crate) fn joint_source_occurrences(&self) -> &[JointSourceOccurrenceView] {
        &self.storage.occurrences
    }

    pub(crate) fn joint_source_authority_receipt(&self) -> [u8; 32] {
        self.storage.authority_receipt
    }

    pub(crate) fn joint_source_body(&self) -> Arc<[u8]> {
        Arc::clone(&self.storage.payload)
    }

    #[allow(dead_code)]
    pub(crate) fn sense_states(&self) -> [u8; SENSE_COUNT] {
        self.storage.sense_states
    }
}

#[pyfunction]
fn settle_native_joint_source_episode(
    candidate_payload: Vec<u8>,
    admitted_port_count: usize,
    admitted_sample_count: usize,
    admitted_occurrence_count: usize,
    admitted_occurrence_frame_count: usize,
) -> PyResult<NativeJointSourceEpisode> {
    decode_native_joint_source_episode_owned(
        candidate_payload,
        admitted_port_count,
        admitted_sample_count,
        admitted_occurrence_count,
        admitted_occurrence_frame_count,
    )
    .map_err(PyValueError::new_err)
}

pub fn decode_native_joint_source_episode(
    candidate_payload: &[u8],
    admitted_port_count: usize,
    admitted_sample_count: usize,
    admitted_occurrence_count: usize,
    admitted_occurrence_frame_count: usize,
) -> Result<NativeJointSourceEpisode, String> {
    decode_native_joint_source_episode_owned(
        candidate_payload.to_vec(),
        admitted_port_count,
        admitted_sample_count,
        admitted_occurrence_count,
        admitted_occurrence_frame_count,
    )
}

fn decode_native_joint_source_episode_owned(
    candidate_payload: Vec<u8>,
    admitted_port_count: usize,
    admitted_sample_count: usize,
    admitted_occurrence_count: usize,
    admitted_occurrence_frame_count: usize,
) -> Result<NativeJointSourceEpisode, String> {
    let parsed = Parser::new(
        &candidate_payload,
        admitted_port_count,
        admitted_sample_count,
        admitted_occurrence_count,
        admitted_occurrence_frame_count,
    )
    .parse()?;
    Ok(NativeJointSourceEpisode {
        storage: Arc::new(Storage {
            authority_receipt: sha256(&candidate_payload),
            payload: Arc::from(candidate_payload),
            sense_states: parsed.sense_states,
            ports: parsed.ports,
            occurrences: parsed.occurrences,
            sample_count: parsed.sample_count,
            occurrence_frame_count: parsed.occurrence_frame_count,
        }),
    })
}

pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NativeJointSourceEpisode>()?;
    module.add_function(wrap_pyfunction!(
        settle_native_joint_source_episode,
        module
    )?)?;
    Ok(())
}

struct ParsedEpisode {
    sense_states: [u8; SENSE_COUNT],
    ports: Vec<JointSourcePortView>,
    occurrences: Vec<JointSourceOccurrenceView>,
    sample_count: usize,
    occurrence_frame_count: usize,
}

struct Parser<'a> {
    bytes: &'a [u8],
    offset: usize,
    admitted_port_count: usize,
    admitted_sample_count: usize,
    admitted_occurrence_count: usize,
    admitted_occurrence_frame_count: usize,
}

impl<'a> Parser<'a> {
    fn new(
        bytes: &'a [u8],
        admitted_port_count: usize,
        admitted_sample_count: usize,
        admitted_occurrence_count: usize,
        admitted_occurrence_frame_count: usize,
    ) -> Self {
        Self {
            bytes,
            offset: 0,
            admitted_port_count,
            admitted_sample_count,
            admitted_occurrence_count,
            admitted_occurrence_frame_count,
        }
    }

    fn parse(mut self) -> Result<ParsedEpisode, String> {
        if self.take(MAGIC.len())? != MAGIC {
            return Err("joint-source episode magic is not GLJSRC02".into());
        }
        if self.u16()? != VERSION {
            return Err("unsupported joint-source episode version".into());
        }
        self.identifier("assembly_id")?;
        let mut sense_states = [0u8; SENSE_COUNT];
        for state in &mut sense_states {
            *state = self.u8()?;
            if *state > 3 {
                return Err("joint-source sense state is outside its typed enum".into());
            }
        }

        let port_count = self.u32()? as usize;
        if port_count != self.admitted_port_count {
            return Err("joint-source port count differs from caller-derived admission".into());
        }
        let mut ports = Vec::new();
        ports
            .try_reserve_exact(port_count)
            .map_err(|_| "joint-source port allocation failed".to_string())?;
        let mut keys = BTreeSet::new();
        let mut topology_indices: [Vec<u32>; SENSE_COUNT] = Default::default();
        let mut sample_count = 0usize;
        for _ in 0..port_count {
            let port = self.port()?;
            sample_count = sample_count
                .checked_add(port.source_times.len())
                .ok_or_else(|| "joint-source sample count overflow".to_string())?;
            if sample_count > self.admitted_sample_count {
                return Err("joint-source samples exceed caller-derived admission".into());
            }
            if !keys.insert((
                port.sense,
                port.sensor_id.clone(),
                port.substream_id.clone(),
            )) {
                return Err("joint-source episode repeats a physical receptor".into());
            }
            if sense_states[port.sense as usize] != 0 {
                return Err("non-observed sense contains a fabricated receptor".into());
            }
            topology_indices[port.sense as usize].push(port.topology_index);
            ports.push(port);
        }
        if sample_count != self.admitted_sample_count {
            return Err("joint-source sample count differs from caller-derived admission".into());
        }
        for sense in 0..SENSE_COUNT {
            topology_indices[sense].sort_unstable();
            if sense_states[sense] == 0 && topology_indices[sense].is_empty() {
                return Err("observed sense has no physical receptor".into());
            }
            if topology_indices[sense]
                .iter()
                .copied()
                .ne(0..topology_indices[sense].len() as u32)
            {
                return Err("joint-source topology is incomplete or reordered".into());
            }
        }

        let occurrence_count = self.u32()? as usize;
        if occurrence_count != self.admitted_occurrence_count {
            return Err(
                "joint-source occurrence count differs from caller-derived admission".into(),
            );
        }
        if (port_count == 0) != (occurrence_count == 0) {
            return Err("joint-source occurrences must partition every admitted port".into());
        }
        let mut occurrences = Vec::new();
        occurrences
            .try_reserve_exact(occurrence_count)
            .map_err(|_| "joint-source occurrence allocation failed".to_string())?;
        let mut port_seen = vec![false; port_count];
        let mut prior_first_port: Option<usize> = None;
        let mut occurrence_frame_count = 0usize;
        for _ in 0..occurrence_count {
            let occurrence_start = self.offset;
            let vertex_count = self.u32()? as usize;
            if vertex_count == 0 {
                return Err("joint-source occurrence has no vertex".into());
            }
            let mut port_indices = Vec::new();
            port_indices
                .try_reserve_exact(vertex_count)
                .map_err(|_| "joint-source occurrence vertex allocation failed".to_string())?;
            let mut prior_port: Option<usize> = None;
            for _ in 0..vertex_count {
                let port_index = self.u32()? as usize;
                if port_index >= ports.len() {
                    return Err("joint-source occurrence port is outside admitted vertices".into());
                }
                if prior_port.is_some_and(|prior| port_index <= prior) {
                    return Err("joint-source occurrence ports are not strictly increasing".into());
                }
                if port_seen[port_index] {
                    return Err("joint-source occurrence repeats an admitted port".into());
                }
                port_seen[port_index] = true;
                prior_port = Some(port_index);
                port_indices.push(port_index);
            }
            let first_port = port_indices[0];
            if prior_first_port.is_some_and(|prior| first_port <= prior) {
                return Err("joint-source occurrences are not in canonical port order".into());
            }
            prior_first_port = Some(first_port);

            let frame_count = self.u32()? as usize;
            if frame_count == 0 {
                return Err("joint-source occurrence has no frame".into());
            }
            occurrence_frame_count = occurrence_frame_count
                .checked_add(frame_count)
                .ok_or_else(|| "joint-source occurrence frame count overflow".to_string())?;
            if occurrence_frame_count > self.admitted_occurrence_frame_count {
                return Err(
                    "joint-source occurrence frames exceed caller-derived admission".into(),
                );
            }
            let mut source_times = Vec::new();
            source_times
                .try_reserve_exact(frame_count)
                .map_err(|_| "joint-source occurrence time allocation failed".to_string())?;
            let mut prior_time: Option<BigRational> = None;
            for _ in 0..frame_count {
                let time = self.rational("joint_timestamp")?;
                if prior_time.as_ref().is_some_and(|prior| time <= *prior) {
                    return Err("joint-source occurrence times do not increase strictly".into());
                }
                prior_time = Some(time.clone());
                source_times.push(time);
            }
            for port_index in &port_indices {
                if ports[*port_index].source_times != source_times {
                    return Err(
                        "joint-source occurrence time differs from a referenced port".into(),
                    );
                }
            }

            let joint_intersample_profile = self.bytes()?;

            let group_count = self.u32()? as usize;
            if group_count == 0 {
                return Err("joint-source occurrence has no declared physical group".into());
            }
            let mut groups = Vec::new();
            groups
                .try_reserve_exact(group_count)
                .map_err(|_| "joint-source group allocation failed".to_string())?;
            let mut local_seen = vec![false; vertex_count];
            let mut prior_group: Option<Vec<usize>> = None;
            for _ in 0..group_count {
                let member_count = self.u32()? as usize;
                if member_count == 0 {
                    return Err("joint-source occurrence group is empty".into());
                }
                let mut members = Vec::new();
                members
                    .try_reserve_exact(member_count)
                    .map_err(|_| "joint-source group member allocation failed".to_string())?;
                let mut prior_member: Option<usize> = None;
                for _ in 0..member_count {
                    let member = self.u32()? as usize;
                    if member >= vertex_count {
                        return Err("joint-source group member is outside local vertices".into());
                    }
                    if prior_member.is_some_and(|prior| member <= prior) {
                        return Err("joint-source group members are not strictly increasing".into());
                    }
                    if local_seen[member] {
                        return Err("joint-source groups overlap".into());
                    }
                    local_seen[member] = true;
                    prior_member = Some(member);
                    members.push(member);
                }
                if prior_group.as_ref().is_some_and(|prior| members <= *prior) {
                    return Err("joint-source groups are not in canonical member order".into());
                }
                prior_group = Some(members.clone());
                groups.push(members);
            }
            if local_seen.iter().any(|seen| !seen) {
                return Err("joint-source groups do not partition local vertices".into());
            }

            let joint_relevance_profile = self.bytes()?;
            let relevance_count = self.u32()? as usize;
            if relevance_count != frame_count {
                return Err("joint-source joint relevance does not cover every frame".into());
            }
            let mut joint_relevances = Vec::new();
            joint_relevances
                .try_reserve_exact(relevance_count)
                .map_err(|_| "joint-source relevance allocation failed".to_string())?;
            for _ in 0..relevance_count {
                let relevance = self.rational("joint_relevance")?;
                if relevance < BigRational::zero() || relevance > BigRational::one() {
                    return Err("joint-source joint relevance is outside [0,1]".into());
                }
                joint_relevances.push(relevance);
            }
            let occurrence_end = self.offset;
            occurrences.push(JointSourceOccurrenceView {
                port_indices,
                source_times,
                joint_intersample_profile,
                groups,
                joint_relevance_profile,
                joint_relevances,
                authority_receipt: sha256(&self.bytes[occurrence_start..occurrence_end]),
            });
        }
        if occurrence_frame_count != self.admitted_occurrence_frame_count {
            return Err(
                "joint-source occurrence frame count differs from caller-derived admission".into(),
            );
        }
        if port_seen.iter().any(|seen| !seen) {
            return Err("joint-source occurrences do not partition admitted ports".into());
        }
        if self.offset != self.bytes.len() {
            return Err("joint-source episode has trailing bytes".into());
        }
        Ok(ParsedEpisode {
            sense_states,
            ports,
            occurrences,
            sample_count,
            occurrence_frame_count,
        })
    }

    fn port(&mut self) -> Result<JointSourcePortView, String> {
        let sense = self.u8()?;
        if sense as usize >= SENSE_COUNT {
            return Err("joint-source receptor sense is outside topology".into());
        }
        let topology_index = self.u32()?;
        let sensor_id = self.identifier("sensor_id")?;
        let substream_id = self.identifier("substream_id")?;

        let coordinate_count = self.u16()? as usize;
        if coordinate_count == 0 {
            return Err("joint-source receptor has no physical coordinate".into());
        }
        let mut coordinate_axes = BTreeSet::new();
        let mut coordinates = Vec::new();
        coordinates
            .try_reserve_exact(coordinate_count)
            .map_err(|_| "joint-source coordinate allocation failed".to_string())?;
        let mut group_authority = Vec::new();
        push_authority_text(&mut group_authority, "guala.joint_source.group.v1")?;
        for _ in 0..coordinate_count {
            let axis = self.identifier("axis_id")?;
            let coordinate = self.identifier("coordinate_id")?;
            if !coordinate_axes.insert(axis.clone()) {
                return Err("joint-source receptor repeats a coordinate axis".into());
            }
            push_authority_text(&mut group_authority, &axis)?;
            push_authority_text(&mut group_authority, &coordinate)?;
            coordinates.push(JointSourceCoordinate {
                axis_id: axis,
                coordinate_id: coordinate,
            });
        }
        let physical_quantity = self.identifier("physical_quantity")?;
        let physical_unit = self.identifier("physical_unit")?;
        let relevance_rule = self.identifier("relevance_rule")?;
        for value in [&physical_quantity, &physical_unit, &relevance_rule] {
            push_authority_text(&mut group_authority, value)?;
        }
        let relevance_origin = self.optional_identifier("relevance_origin")?;
        push_authority_text(
            &mut group_authority,
            relevance_origin.as_deref().unwrap_or(""),
        )?;

        let map_id = self.identifier("map_id")?;
        let source_min = self.rational("source_min")?;
        let source_max = self.rational("source_max")?;
        let field_offset = self.rational("field_offset")?;
        let field_scale = self.rational("field_scale")?;
        if source_max <= source_min {
            return Err("joint-source input interval is empty".into());
        }
        if field_scale.is_zero() {
            return Err("joint-source input map is not invertible".into());
        }
        let profile = self.bytes()?;
        push_authority_text(&mut group_authority, &map_id)?;
        for value in [&source_min, &source_max, &field_offset, &field_scale] {
            push_authority_rational(&mut group_authority, value)?;
        }
        push_authority_bytes(&mut group_authority, &profile)?;
        let input_map_group_receipt = sha256(&group_authority);

        let sample_count = self.u32()? as usize;
        if sample_count == 0 {
            return Err("joint-source receptor has no samples".into());
        }
        let mut source_times = Vec::new();
        let mut exact_normalized_sources = Vec::new();
        let mut reported_phase_turns = Vec::new();
        let mut source_relevances = Vec::new();
        let mut dimensionless_fields = Vec::new();
        source_times
            .try_reserve_exact(sample_count)
            .map_err(|_| "joint-source time allocation failed".to_string())?;
        exact_normalized_sources
            .try_reserve_exact(sample_count)
            .map_err(|_| "joint-source normalized-source allocation failed".to_string())?;
        reported_phase_turns
            .try_reserve_exact(sample_count)
            .map_err(|_| "joint-source reported-phase allocation failed".to_string())?;
        source_relevances
            .try_reserve_exact(sample_count)
            .map_err(|_| "joint-source relevance allocation failed".to_string())?;
        dimensionless_fields
            .try_reserve_exact(sample_count)
            .map_err(|_| "joint-source field allocation failed".to_string())?;
        let mut prior_time: Option<BigRational> = None;
        for _ in 0..sample_count {
            let timestamp = self.rational("timestamp")?;
            if prior_time.as_ref().is_some_and(|prior| timestamp <= *prior) {
                return Err("joint-source times do not increase strictly".into());
            }
            prior_time = Some(timestamp.clone());
            let signal = f64::from_bits(self.u64()?);
            if !signal.is_finite() || !(-1.0..=1.0).contains(&signal) {
                return Err("joint-source signal is outside normalized binary64".into());
            }
            let phase_turns = self.rational("phase_turns")?;
            let relevance = self.rational("relevance")?;
            let dimensionless_field = self.rational("dimensionless_field")?;
            let exact_signal = BigRational::from_float(signal)
                .ok_or_else(|| "joint-source signal is not exact binary64".to_string())?;
            let expected = &field_offset + &field_scale * &exact_signal;
            if dimensionless_field != expected {
                return Err("joint-source field differs from its physical input map".into());
            }
            source_times.push(timestamp);
            exact_normalized_sources.push(exact_signal);
            reported_phase_turns.push(phase_turns);
            source_relevances.push(relevance);
            dimensionless_fields.push(dimensionless_field);
        }

        Ok(JointSourcePortView {
            sense,
            topology_index,
            sensor_id,
            substream_id,
            coordinates,
            physical_quantity,
            physical_unit,
            relevance_rule,
            relevance_origin,
            input_map_id: map_id,
            source_min,
            source_max,
            field_offset,
            field_scale,
            input_map_profile: profile,
            input_map_group_receipt,
            source_times,
            exact_normalized_sources,
            reported_phase_turns,
            source_relevances,
            dimensionless_fields,
        })
    }

    fn rational(&mut self, label: &str) -> Result<BigRational, String> {
        let numerator_text = self.text()?;
        let denominator_text = self.text()?;
        let numerator = canonical_integer(&numerator_text, label)?;
        let denominator = canonical_integer(&denominator_text, label)?;
        if denominator <= BigInt::zero() {
            return Err(format!("{label} denominator is not positive"));
        }
        let value = BigRational::new(numerator, denominator);
        if value.numer().to_string() != numerator_text
            || value.denom().to_string() != denominator_text
        {
            return Err(format!("{label} is not in reduced canonical form"));
        }
        Ok(value)
    }

    fn identifier(&mut self, label: &str) -> Result<String, String> {
        let value = self.text()?;
        if value.is_empty() || value.trim() != value {
            return Err(format!("{label} is not a canonical identifier"));
        }
        Ok(value)
    }

    fn optional_identifier(&mut self, label: &str) -> Result<Option<String>, String> {
        let value = self.text()?;
        if value.is_empty() {
            return Ok(None);
        }
        if value.trim() != value {
            return Err(format!("{label} is not a canonical identifier"));
        }
        Ok(Some(value))
    }

    fn text(&mut self) -> Result<String, String> {
        let length = self.u16()? as usize;
        std::str::from_utf8(self.take(length)?)
            .map(str::to_owned)
            .map_err(|_| "joint-source text is not UTF-8".into())
    }

    fn bytes(&mut self) -> Result<Vec<u8>, String> {
        let length = self.u32()? as usize;
        if length == 0 {
            return Err("joint-source byte record is empty".into());
        }
        Ok(self.take(length)?.to_vec())
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
            .ok_or_else(|| "joint-source length overflow".to_string())?;
        if end > self.bytes.len() {
            return Err("joint-source episode ended before its declared structure".into());
        }
        let result = &self.bytes[self.offset..end];
        self.offset = end;
        Ok(result)
    }
}

fn canonical_integer(value: &str, label: &str) -> Result<BigInt, String> {
    let parsed = value
        .parse::<BigInt>()
        .map_err(|_| format!("{label} is not an integer"))?;
    if parsed.to_string() != value {
        return Err(format!("{label} integer is not canonical"));
    }
    Ok(parsed)
}

fn push_authority_text(output: &mut Vec<u8>, value: &str) -> Result<(), String> {
    let bytes = value.as_bytes();
    let length = u32::try_from(bytes.len())
        .map_err(|_| "joint-source authority text is too large".to_string())?;
    output.extend_from_slice(&length.to_le_bytes());
    output.extend_from_slice(bytes);
    Ok(())
}

fn push_authority_bytes(output: &mut Vec<u8>, value: &[u8]) -> Result<(), String> {
    let length = u32::try_from(value.len())
        .map_err(|_| "joint-source authority bytes are too large".to_string())?;
    output.extend_from_slice(&length.to_le_bytes());
    output.extend_from_slice(value);
    Ok(())
}

fn push_authority_rational(output: &mut Vec<u8>, value: &BigRational) -> Result<(), String> {
    push_authority_text(output, &value.numer().to_string())?;
    push_authority_text(output, &value.denom().to_string())
}

fn hex_digest(value: &[u8; 32]) -> String {
    value.iter().map(|byte| format!("{byte:02x}")).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn push_u16(output: &mut Vec<u8>, value: u16) {
        output.extend_from_slice(&value.to_le_bytes());
    }

    fn push_u32(output: &mut Vec<u8>, value: u32) {
        output.extend_from_slice(&value.to_le_bytes());
    }

    fn short_text(output: &mut Vec<u8>, value: &str) {
        push_u16(output, value.len() as u16);
        output.extend_from_slice(value.as_bytes());
    }

    fn bytes(output: &mut Vec<u8>, value: &[u8]) {
        push_u32(output, value.len() as u32);
        output.extend_from_slice(value);
    }

    fn rational(output: &mut Vec<u8>, numerator: i64, denominator: i64) {
        short_text(output, &numerator.to_string());
        short_text(output, &denominator.to_string());
    }

    fn port(output: &mut Vec<u8>) {
        output.push(0);
        push_u32(output, 0);
        short_text(output, "retina");
        short_text(output, "pixel-0");
        push_u16(output, 1);
        short_text(output, "receptor");
        short_text(output, "0");
        short_text(output, "light");
        short_text(output, "normalized");
        short_text(output, "direct");
        short_text(output, "");
        short_text(output, "affine");
        rational(output, -1, 1);
        rational(output, 1, 1);
        rational(output, 1, 1);
        rational(output, 1, 2);
        bytes(output, &[7]);
        push_u32(output, 2);
        for (time, signal, phase, field, local_relevance) in [
            (0, 0.0_f64, (0, 1), (1, 1), (1, 1)),
            (1, 1.0, (1, 4), (3, 2), (0, 1)),
        ] {
            rational(output, time, 1);
            output.extend_from_slice(&signal.to_bits().to_le_bytes());
            rational(output, phase.0, phase.1);
            rational(output, local_relevance.0, local_relevance.1);
            rational(output, field.0, field.1);
        }
    }

    fn candidate(include_occurrence: bool) -> Vec<u8> {
        let mut output = MAGIC.to_vec();
        push_u16(&mut output, VERSION);
        short_text(&mut output, "assembly");
        output.extend_from_slice(&[0, 1, 1, 1, 1, 1]);
        push_u32(&mut output, 1);
        port(&mut output);
        push_u32(&mut output, usize::from(include_occurrence) as u32);
        if include_occurrence {
            push_u32(&mut output, 1);
            push_u32(&mut output, 0);
            push_u32(&mut output, 2);
            rational(&mut output, 0, 1);
            rational(&mut output, 1, 1);
            bytes(&mut output, &[6, 5, 4]);
            push_u32(&mut output, 1);
            push_u32(&mut output, 1);
            push_u32(&mut output, 0);
            bytes(&mut output, &[9, 8, 7]);
            push_u32(&mut output, 2);
            rational(&mut output, 1, 4);
            rational(&mut output, 3, 4);
        }
        output
    }

    #[test]
    fn source_authored_occurrence_retains_t_v_g_f_and_joint_relevance() {
        let payload = candidate(true);
        let parsed = Parser::new(&payload, 1, 2, 1, 2).parse().unwrap();
        assert_eq!(parsed.sense_states, [0, 1, 1, 1, 1, 1]);
        assert_eq!(parsed.sample_count, 2);
        assert_eq!(parsed.occurrence_frame_count, 2);
        assert_eq!(parsed.ports.len(), 1);
        assert_eq!(parsed.occurrences.len(), 1);
        assert_eq!(parsed.occurrences[0].port_indices, [0]);
        assert_eq!(parsed.occurrences[0].groups, [vec![0]]);
        assert_eq!(parsed.occurrences[0].joint_intersample_profile, [6, 5, 4]);
        assert_eq!(parsed.occurrences[0].joint_relevance_profile, [9, 8, 7]);
        assert_eq!(
            parsed.occurrences[0].joint_relevances,
            [
                BigRational::new(1.into(), 4.into()),
                BigRational::new(3.into(), 4.into())
            ]
        );
        assert_eq!(
            parsed.ports[0].source_relevances,
            [BigRational::one(), BigRational::zero()]
        );
        assert_ne!(
            parsed.ports[0].source_relevances,
            parsed.occurrences[0].joint_relevances
        );
    }

    #[test]
    fn equal_port_clocks_without_an_explicit_occurrence_are_rejected() {
        let payload = candidate(false);
        assert!(Parser::new(&payload, 1, 2, 0, 0).parse().is_err());
    }

    #[test]
    fn v1_magic_and_caller_extent_mismatch_are_rejected() {
        let payload = candidate(true);
        let mut prior = payload.clone();
        prior[..8].copy_from_slice(b"GLJSRC01");
        assert!(Parser::new(&prior, 1, 2, 1, 2).parse().is_err());
        assert!(Parser::new(&payload, 2, 2, 1, 2).parse().is_err());
        assert!(Parser::new(&payload, 1, 3, 1, 2).parse().is_err());
        assert!(Parser::new(&payload, 1, 2, 2, 2).parse().is_err());
        assert!(Parser::new(&payload, 1, 2, 1, 3).parse().is_err());
    }

    #[test]
    fn occurrence_receipt_is_exact_and_rebuild_stable() {
        let payload = candidate(true);
        let left = Parser::new(&payload, 1, 2, 1, 2).parse().unwrap();
        let right = Parser::new(&payload, 1, 2, 1, 2).parse().unwrap();
        assert_eq!(
            left.occurrences[0].authority_receipt,
            right.occurrences[0].authority_receipt
        );
        assert_ne!(left.occurrences[0].authority_receipt, [0; 32]);
    }
}
