//! Borrowed physical-source authority for one reached neuron perspective.
//!
//! A neuron coordinate is not a sense merely because a caller names it one.
//! This boundary follows the coordinate back through the shared occurrence to
//! the exact decoded GLJSRC02 receptor port.  The returned view borrows that
//! port; no source samples, labels, field bodies, or receipts are copied into
//! neuronal state or a cognitive formation.

use std::sync::Arc;

use crate::joint_source_episode::{
    JointSourceCoordinate, JointSourcePortView, NativeJointSourceEpisode,
};
use crate::joint_uf_neuron_boundary::JointNeuronPerspective;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PhysicalSourceSense {
    Sight,
    Sound,
    Touch,
    Smell,
    Taste,
    Body,
}

impl PhysicalSourceSense {
    fn decode(value: u8) -> Option<Self> {
        match value {
            0 => Some(Self::Sight),
            1 => Some(Self::Sound),
            2 => Some(Self::Touch),
            3 => Some(Self::Smell),
            4 => Some(Self::Taste),
            5 => Some(Self::Body),
            _ => None,
        }
    }

    fn encode(self) -> u8 {
        match self {
            Self::Sight => 0,
            Self::Sound => 1,
            Self::Touch => 2,
            Self::Smell => 3,
            Self::Taste => 4,
            Self::Body => 5,
        }
    }

    /// The declared sense layer this receptor belongs to: the first coordinate
    /// of its declared place in the organism's sensory lattice.  It is the
    /// same declared encoding the site's codec already carries, read as a
    /// position rather than as a tag (see `declared_geometric_anatomy`).
    pub(crate) fn declared_layer(self) -> u8 {
        self.encode()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum NeuronSourceAnchorError {
    EpisodeDoesNotOwnSharedOccurrence,
    SourcePortAbsent,
    SourceSenseInvalid,
    InvalidSiteEncoding,
    InvalidSiteAnatomy,
    ArithmeticWidth,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct BorrowedNeuronSourceAnchor<'a> {
    source_port_index: usize,
    sense: PhysicalSourceSense,
    port: &'a JointSourcePortView,
}

/// Fixed receptor specialization mounted with a reached neuron. This is
/// compact anatomy, not an experience record: it contains no samples, clocks,
/// DSF values, neuronal state, or media.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct NeuronSourceSite {
    sense: PhysicalSourceSense,
    topology_index: u32,
    sensor_id: Box<str>,
    substream_id: Box<str>,
    coordinates: Box<[JointSourceCoordinate]>,
    physical_quantity: Box<str>,
    physical_unit: Box<str>,
}

impl NeuronSourceSite {
    pub(crate) fn from_source_port(
        port: &JointSourcePortView,
    ) -> Result<Self, NeuronSourceAnchorError> {
        let sense = PhysicalSourceSense::decode(port.sense)
            .ok_or(NeuronSourceAnchorError::SourceSenseInvalid)?;
        let site = Self {
            sense,
            topology_index: port.topology_index,
            sensor_id: port.sensor_id.clone().into_boxed_str(),
            substream_id: port.substream_id.clone().into_boxed_str(),
            coordinates: port.coordinates.clone().into_boxed_slice(),
            physical_quantity: port.physical_quantity.clone().into_boxed_str(),
            physical_unit: port.physical_unit.clone().into_boxed_str(),
        };
        if !site.valid() {
            return Err(NeuronSourceAnchorError::InvalidSiteAnatomy);
        }
        Ok(site)
    }

    pub(crate) fn from_anchor(anchor: BorrowedNeuronSourceAnchor<'_>) -> Self {
        Self {
            sense: anchor.sense(),
            topology_index: anchor.topology_index(),
            sensor_id: anchor.sensor_id().into(),
            substream_id: anchor.substream_id().into(),
            coordinates: anchor.coordinates().to_vec().into_boxed_slice(),
            physical_quantity: anchor.physical_quantity().into(),
            physical_unit: anchor.physical_unit().into(),
        }
    }

    pub(crate) fn sense(&self) -> PhysicalSourceSense {
        self.sense
    }

    pub(crate) fn topology_index(&self) -> u32 {
        self.topology_index
    }

    fn valid(&self) -> bool {
        !self.sensor_id.is_empty()
            && !self.substream_id.is_empty()
            && !self.coordinates.is_empty()
            && self.coordinates.iter().all(|coordinate| {
                !coordinate.axis_id.is_empty() && !coordinate.coordinate_id.is_empty()
            })
            && !self.physical_quantity.is_empty()
            && !self.physical_unit.is_empty()
    }

    #[cfg(test)]
    pub(crate) fn fixture(topology_index: u32) -> Self {
        Self::fixture_in_sense(PhysicalSourceSense::Sight, topology_index)
    }

    #[cfg(test)]
    pub(crate) fn fixture_in_sense(sense: PhysicalSourceSense, topology_index: u32) -> Self {
        Self {
            sense,
            topology_index,
            sensor_id: "synthetic-test-receptor".into(),
            substream_id: topology_index.to_string().into_boxed_str(),
            coordinates: vec![JointSourceCoordinate {
                axis_id: "test-coordinate".into(),
                coordinate_id: topology_index.to_string(),
            }]
            .into_boxed_slice(),
            physical_quantity: "test-only-dimensionless-coordinate".into(),
            physical_unit: "dimensionless".into(),
        }
    }
}

const NEURON_SOURCE_SITE_CODEC_MAGIC: &[u8; 8] = b"GLNSS01\0";

pub(crate) fn encode_neuron_source_site(
    site: &NeuronSourceSite,
) -> Result<Vec<u8>, NeuronSourceAnchorError> {
    if !site.valid() {
        return Err(NeuronSourceAnchorError::InvalidSiteAnatomy);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(NEURON_SOURCE_SITE_CODEC_MAGIC);
    encoded.push(site.sense.encode());
    encoded.extend_from_slice(&site.topology_index.to_le_bytes());
    push_site_text(&mut encoded, &site.sensor_id)?;
    push_site_text(&mut encoded, &site.substream_id)?;
    push_site_usize(&mut encoded, site.coordinates.len())?;
    for coordinate in &site.coordinates {
        push_site_text(&mut encoded, &coordinate.axis_id)?;
        push_site_text(&mut encoded, &coordinate.coordinate_id)?;
    }
    push_site_text(&mut encoded, &site.physical_quantity)?;
    push_site_text(&mut encoded, &site.physical_unit)?;
    Ok(encoded)
}

pub(crate) fn decode_neuron_source_site(
    encoded: &[u8],
) -> Result<NeuronSourceSite, NeuronSourceAnchorError> {
    let mut reader = SourceSiteReader::new(encoded);
    if reader.take(NEURON_SOURCE_SITE_CODEC_MAGIC.len())? != NEURON_SOURCE_SITE_CODEC_MAGIC {
        return Err(NeuronSourceAnchorError::InvalidSiteEncoding);
    }
    let sense = PhysicalSourceSense::decode(reader.u8()?)
        .ok_or(NeuronSourceAnchorError::SourceSenseInvalid)?;
    let topology_index = reader.u32()?;
    let sensor_id = reader.text()?;
    let substream_id = reader.text()?;
    let coordinate_count = reader.usize()?;
    reader.require_records(coordinate_count, 16)?;
    let mut coordinates = Vec::new();
    coordinates
        .try_reserve_exact(coordinate_count)
        .map_err(|_| NeuronSourceAnchorError::ArithmeticWidth)?;
    for _ in 0..coordinate_count {
        coordinates.push(JointSourceCoordinate {
            axis_id: reader.text()?.into(),
            coordinate_id: reader.text()?.into(),
        });
    }
    let site = NeuronSourceSite {
        sense,
        topology_index,
        sensor_id: sensor_id.into(),
        substream_id: substream_id.into(),
        coordinates: coordinates.into_boxed_slice(),
        physical_quantity: reader.text()?.into(),
        physical_unit: reader.text()?.into(),
    };
    if !reader.finished() {
        return Err(NeuronSourceAnchorError::InvalidSiteEncoding);
    }
    if !site.valid() {
        return Err(NeuronSourceAnchorError::InvalidSiteAnatomy);
    }
    Ok(site)
}

fn push_site_usize(encoded: &mut Vec<u8>, value: usize) -> Result<(), NeuronSourceAnchorError> {
    encoded.extend_from_slice(
        &u64::try_from(value)
            .map_err(|_| NeuronSourceAnchorError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

fn push_site_text(encoded: &mut Vec<u8>, value: &str) -> Result<(), NeuronSourceAnchorError> {
    push_site_usize(encoded, value.len())?;
    encoded.extend_from_slice(value.as_bytes());
    Ok(())
}

struct SourceSiteReader<'a> {
    encoded: &'a [u8],
    cursor: usize,
}

impl<'a> SourceSiteReader<'a> {
    fn new(encoded: &'a [u8]) -> Self {
        Self { encoded, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], NeuronSourceAnchorError> {
        let end = self
            .cursor
            .checked_add(count)
            .ok_or(NeuronSourceAnchorError::ArithmeticWidth)?;
        let value = self
            .encoded
            .get(self.cursor..end)
            .ok_or(NeuronSourceAnchorError::InvalidSiteEncoding)?;
        self.cursor = end;
        Ok(value)
    }

    fn require_records(
        &self,
        count: usize,
        minimum_record_bytes: usize,
    ) -> Result<(), NeuronSourceAnchorError> {
        let minimum = count
            .checked_mul(minimum_record_bytes)
            .ok_or(NeuronSourceAnchorError::ArithmeticWidth)?;
        let remaining = self
            .encoded
            .len()
            .checked_sub(self.cursor)
            .ok_or(NeuronSourceAnchorError::InvalidSiteEncoding)?;
        if minimum > remaining {
            return Err(NeuronSourceAnchorError::InvalidSiteEncoding);
        }
        Ok(())
    }

    fn usize(&mut self) -> Result<usize, NeuronSourceAnchorError> {
        usize::try_from(u64::from_le_bytes(
            self.take(8)?
                .try_into()
                .map_err(|_| NeuronSourceAnchorError::InvalidSiteEncoding)?,
        ))
        .map_err(|_| NeuronSourceAnchorError::ArithmeticWidth)
    }

    fn u8(&mut self) -> Result<u8, NeuronSourceAnchorError> {
        Ok(self.take(1)?[0])
    }

    fn u32(&mut self) -> Result<u32, NeuronSourceAnchorError> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().map_err(
            |_| NeuronSourceAnchorError::InvalidSiteEncoding,
        )?))
    }

    fn text(&mut self) -> Result<String, NeuronSourceAnchorError> {
        let length = self.usize()?;
        let value = std::str::from_utf8(self.take(length)?)
            .map_err(|_| NeuronSourceAnchorError::InvalidSiteEncoding)?;
        Ok(value.to_owned())
    }

    fn finished(&self) -> bool {
        self.cursor == self.encoded.len()
    }
}

impl<'a> BorrowedNeuronSourceAnchor<'a> {
    pub(crate) fn source_port_index(self) -> usize {
        self.source_port_index
    }

    pub(crate) fn sense(self) -> PhysicalSourceSense {
        self.sense
    }

    pub(crate) fn topology_index(self) -> u32 {
        self.port.topology_index
    }

    pub(crate) fn sensor_id(self) -> &'a str {
        &self.port.sensor_id
    }

    pub(crate) fn substream_id(self) -> &'a str {
        &self.port.substream_id
    }

    pub(crate) fn coordinates(self) -> &'a [JointSourceCoordinate] {
        &self.port.coordinates
    }

    pub(crate) fn physical_quantity(self) -> &'a str {
        &self.port.physical_quantity
    }

    pub(crate) fn physical_unit(self) -> &'a str {
        &self.port.physical_unit
    }
}

pub(crate) fn bind_neuron_source_anchor<'a>(
    episode: &'a NativeJointSourceEpisode,
    perspective: JointNeuronPerspective<'_>,
) -> Result<BorrowedNeuronSourceAnchor<'a>, NeuronSourceAnchorError> {
    let shared = perspective.shared();
    let episode_body = episode.joint_source_body();
    if !Arc::ptr_eq(&episode_body, shared.source_body())
        || episode.joint_source_authority_receipt() != shared.source_authority()
        || episode
            .joint_source_occurrences()
            .get(shared.occurrence_index())
            .is_none()
    {
        return Err(NeuronSourceAnchorError::EpisodeDoesNotOwnSharedOccurrence);
    }
    let source_port_index = *shared
        .port_indices()
        .get(perspective.coordinate_index())
        .ok_or(NeuronSourceAnchorError::SourcePortAbsent)?;
    let port = episode
        .joint_source_ports()
        .get(source_port_index)
        .ok_or(NeuronSourceAnchorError::SourcePortAbsent)?;
    let sense = PhysicalSourceSense::decode(port.sense)
        .ok_or(NeuronSourceAnchorError::SourceSenseInvalid)?;
    Ok(BorrowedNeuronSourceAnchor {
        source_port_index,
        sense,
        port,
    })
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use crate::joint_source_episode::decode_native_joint_source_episode;
    use crate::joint_uf_neuron_boundary::{
        bind_neuron_perspective, prepare_complete_joint_field_admitted_fixture,
    };

    const INTERSAMPLE: &[u8] = b"guala.uf.v1.4.sampled_volume_and_relevance_piecewise_linear.v1";

    fn u16_value(output: &mut Vec<u8>, value: u16) {
        output.extend_from_slice(&value.to_le_bytes());
    }

    fn u32_value(output: &mut Vec<u8>, value: u32) {
        output.extend_from_slice(&value.to_le_bytes());
    }

    fn text_value(output: &mut Vec<u8>, value: &str) {
        u16_value(output, value.len() as u16);
        output.extend_from_slice(value.as_bytes());
    }

    fn byte_value(output: &mut Vec<u8>, value: &[u8]) {
        u32_value(output, value.len() as u32);
        output.extend_from_slice(value);
    }

    fn rational_value(output: &mut Vec<u8>, numerator: i64, denominator: i64) {
        text_value(output, &numerator.to_string());
        text_value(output, &denominator.to_string());
    }

    fn source_port(
        output: &mut Vec<u8>,
        sense: u8,
        topology_index: u32,
        sensor: &str,
        substream: &str,
        quantity: &str,
        unit: &str,
        fields: [f64; 3],
        times: [(i64, i64); 3],
    ) {
        source_port_with_coordinates(
            output,
            sense,
            topology_index,
            sensor,
            substream,
            &[("receptor", "0")],
            quantity,
            unit,
            fields,
            times,
        );
    }

    #[allow(clippy::too_many_arguments)]
    fn source_port_with_coordinates(
        output: &mut Vec<u8>,
        sense: u8,
        topology_index: u32,
        sensor: &str,
        substream: &str,
        coordinates: &[(&str, &str)],
        quantity: &str,
        unit: &str,
        fields: [f64; 3],
        times: [(i64, i64); 3],
    ) {
        output.push(sense);
        u32_value(output, topology_index);
        text_value(output, sensor);
        text_value(output, substream);
        u16_value(output, u16::try_from(coordinates.len()).unwrap());
        for (axis, coordinate) in coordinates {
            text_value(output, axis);
            text_value(output, coordinate);
        }
        text_value(output, quantity);
        text_value(output, unit);
        text_value(output, "direct-physical-source");
        text_value(output, "");
        text_value(output, "identity-binary64");
        rational_value(output, -1, 1);
        rational_value(output, 1, 1);
        rational_value(output, 0, 1);
        rational_value(output, 1, 1);
        byte_value(output, b"identity-binary64-v1");
        u32_value(output, fields.len() as u32);
        for ((time_numerator, time_denominator), field) in times.into_iter().zip(fields.into_iter())
        {
            rational_value(output, time_numerator, time_denominator);
            output.extend_from_slice(&field.to_bits().to_le_bytes());
            rational_value(output, 0, 1);
            rational_value(output, 1, 1);
            let exact = num_rational::BigRational::from_float(field).unwrap();
            text_value(output, &exact.numer().to_string());
            text_value(output, &exact.denom().to_string());
        }
    }

    pub(crate) fn exact_episode() -> NativeJointSourceEpisode {
        let mut output = b"GLJSRC02".to_vec();
        u16_value(&mut output, 2);
        text_value(&mut output, "typed-whole-organism-occurrence");
        output.extend_from_slice(&[0, 0, 1, 1, 1, 0]);
        u32_value(&mut output, 4);
        source_port(
            &mut output,
            0,
            0,
            "left-retina",
            "foveal-receptor-0",
            "retinal-spectral-irradiance",
            "fraction-of-declared-retinal-reference-irradiance",
            [0.0, 0.5, 1.0],
            [(0, 1), (1, 1), (2, 1)],
        );
        source_port(
            &mut output,
            1,
            0,
            "left-cochlea",
            "basilar-receptor-0",
            "acoustic-pressure",
            "normalized-binary64",
            [0.0, -0.25, 0.5],
            [(0, 1), (1, 1), (2, 1)],
        );
        source_port(
            &mut output,
            1,
            1,
            "right-cochlea",
            "basilar-receptor-0",
            "acoustic-pressure",
            "normalized-binary64",
            [0.0, 0.25, 0.5],
            [(0, 1), (1, 1), (2, 1)],
        );
        source_port(
            &mut output,
            5,
            0,
            "vestibular-body",
            "yaw-cupula-0",
            "cupula-displacement",
            "normalized-binary64",
            [0.0, 0.125, 0.25],
            [(0, 1), (1, 1), (2, 1)],
        );
        u32_value(&mut output, 1);
        u32_value(&mut output, 4);
        for index in 0..4 {
            u32_value(&mut output, index);
        }
        u32_value(&mut output, 3);
        for time in 0..3 {
            rational_value(&mut output, time, 1);
        }
        byte_value(&mut output, INTERSAMPLE);
        u32_value(&mut output, 4);
        for index in 0..4 {
            u32_value(&mut output, 1);
            u32_value(&mut output, index);
        }
        byte_value(&mut output, b"explicit-joint-relevance-v1");
        u32_value(&mut output, 3);
        for _ in 0..3 {
            rational_value(&mut output, 1, 1);
        }
        decode_native_joint_source_episode(&output, 4, 12, 1, 3).unwrap()
    }

    fn optical_episode(fields: [f64; 3]) -> NativeJointSourceEpisode {
        let mut output = b"GLJSRC02".to_vec();
        u16_value(&mut output, 2);
        text_value(&mut output, "typed-optical-occurrence");
        output.extend_from_slice(&[0, 1, 1, 1, 1, 1]);
        u32_value(&mut output, 1);
        source_port(
            &mut output,
            0,
            0,
            "left-retina",
            "foveal-receptor-0",
            "retinal-spectral-irradiance",
            "fraction-of-declared-retinal-reference-irradiance",
            fields,
            [(0, 1), (1, 1), (2, 1)],
        );
        u32_value(&mut output, 1);
        u32_value(&mut output, 1);
        u32_value(&mut output, 0);
        u32_value(&mut output, 3);
        rational_value(&mut output, 0, 1);
        rational_value(&mut output, 1, 1);
        rational_value(&mut output, 2, 1);
        byte_value(&mut output, INTERSAMPLE);
        u32_value(&mut output, 1);
        u32_value(&mut output, 1);
        u32_value(&mut output, 0);
        byte_value(&mut output, b"explicit-joint-relevance-v1");
        u32_value(&mut output, 3);
        for _ in 0..3 {
            rational_value(&mut output, 1, 1);
        }
        decode_native_joint_source_episode(&output, 1, 3, 1, 3).unwrap()
    }

    pub(crate) fn exact_optical_episode() -> NativeJointSourceEpisode {
        optical_episode([0.0, 0.5, 1.0])
    }

    pub(crate) fn exact_dark_optical_episode() -> NativeJointSourceEpisode {
        optical_episode([0.0, 0.0, 0.0])
    }

    fn optical_episode_from_receptors_in_order<const RECEPTOR_COUNT: usize>(
        fields: [[f64; 3]; RECEPTOR_COUNT],
        receptor_order: &[usize],
    ) -> NativeJointSourceEpisode {
        let occurrence_vertices = (0..receptor_order.len()).collect::<Vec<_>>();
        optical_episode_from_receptors_and_occurrences(
            fields,
            receptor_order,
            &[occurrence_vertices.as_slice()],
        )
    }

    fn optical_episode_from_receptors_and_occurrences<const RECEPTOR_COUNT: usize>(
        fields: [[f64; 3]; RECEPTOR_COUNT],
        receptor_order: &[usize],
        occurrences: &[&[usize]],
    ) -> NativeJointSourceEpisode {
        assert!(!receptor_order.is_empty());
        assert!(receptor_order.iter().all(|index| *index < fields.len()));
        assert!(!occurrences.is_empty());
        let mut output = b"GLJSRC02".to_vec();
        u16_value(&mut output, 2);
        text_value(&mut output, "typed-four-receptor-optical-occurrence");
        output.extend_from_slice(&[0, 1, 1, 1, 1, 1]);
        u32_value(&mut output, u32::try_from(receptor_order.len()).unwrap());
        for receptor_index in receptor_order.iter().copied() {
            source_port(
                &mut output,
                0,
                u32::try_from(receptor_index).unwrap(),
                "left-retina",
                &format!("foveal-receptor-{receptor_index}"),
                "retinal-spectral-irradiance",
                "fraction-of-declared-retinal-reference-irradiance",
                fields[receptor_index],
                [(0, 1), (1, 1), (2, 1)],
            );
        }
        u32_value(&mut output, u32::try_from(occurrences.len()).unwrap());
        for occurrence in occurrences {
            u32_value(&mut output, u32::try_from(occurrence.len()).unwrap());
            for index in occurrence.iter().copied() {
                u32_value(&mut output, u32::try_from(index).unwrap());
            }
            u32_value(&mut output, 3);
            for time in 0..3 {
                rational_value(&mut output, time, 1);
            }
            byte_value(&mut output, INTERSAMPLE);
            u32_value(&mut output, u32::try_from(occurrence.len()).unwrap());
            for index in 0..occurrence.len() {
                u32_value(&mut output, 1);
                u32_value(&mut output, u32::try_from(index).unwrap());
            }
            byte_value(&mut output, b"explicit-joint-relevance-v1");
            u32_value(&mut output, 3);
            for _ in 0..3 {
                rational_value(&mut output, 1, 1);
            }
        }
        decode_native_joint_source_episode(
            &output,
            receptor_order.len(),
            receptor_order.len() * 3,
            occurrences.len(),
            occurrences.len() * 3,
        )
        .unwrap()
    }

    fn four_optical_episode(fields: [[f64; 3]; 4]) -> NativeJointSourceEpisode {
        optical_episode_from_receptors_in_order(fields, &[0, 1, 2, 3])
    }

    pub(crate) fn exact_four_optical_episode() -> NativeJointSourceEpisode {
        four_optical_episode([[0.0, 0.5, 1.0]; 4])
    }

    pub(crate) fn exact_four_patterned_optical_episode() -> NativeJointSourceEpisode {
        four_optical_episode([
            [0.0, 0.5, 1.0],
            [0.0, 1.0, 0.0],
            [1.0, 0.5, 0.0],
            [0.5, 0.5, 0.5],
        ])
    }

    pub(crate) fn exact_four_reordered_optical_episode() -> NativeJointSourceEpisode {
        optical_episode_from_receptors_in_order([[0.0, 0.5, 1.0]; 4], &[2, 0, 3, 1])
    }

    pub(crate) fn exact_two_of_four_optical_episode() -> NativeJointSourceEpisode {
        optical_episode_from_receptors_in_order([[0.0, 0.5, 1.0]; 4], &[0, 1])
    }

    pub(crate) fn exact_split_four_optical_episode() -> NativeJointSourceEpisode {
        optical_episode_from_receptors_and_occurrences(
            [[0.0, 0.5, 1.0]; 4],
            &[0, 1, 2, 3],
            &[&[0, 1], &[2, 3]],
        )
    }

    pub(crate) fn exact_five_optical_episode() -> NativeJointSourceEpisode {
        optical_episode_from_receptors_in_order([[0.0, 0.5, 1.0]; 5], &[0, 1, 2, 3, 4])
    }

    pub(crate) fn exact_four_dark_optical_episode() -> NativeJointSourceEpisode {
        four_optical_episode([[0.0, 0.0, 0.0]; 4])
    }

    pub(crate) fn exact_four_partial_optical_episode() -> NativeJointSourceEpisode {
        exact_four_single_optical_episode(0)
    }

    pub(crate) fn exact_four_single_optical_episode(
        reached_receptor: usize,
    ) -> NativeJointSourceEpisode {
        assert!(reached_receptor < 4);
        exact_four_subset_optical_episode(1_u8 << reached_receptor)
    }

    pub(crate) fn exact_four_subset_optical_episode(
        reached_receptors: u8,
    ) -> NativeJointSourceEpisode {
        assert!(reached_receptors != 0 && reached_receptors < 0b1111);
        let mut fields = [[0.0, 0.0, 0.0]; 4];
        for (index, field) in fields.iter_mut().enumerate() {
            if reached_receptors & (1_u8 << index) != 0 {
                *field = [0.0, 0.5, 1.0];
            }
        }
        four_optical_episode(fields)
    }

    #[test]
    fn perspectives_borrow_exact_sensory_and_body_ports_without_relabeling() {
        let episode = exact_episode();
        let shared = prepare_complete_joint_field_admitted_fixture(&episode, 0).unwrap();
        let expected = [
            (
                PhysicalSourceSense::Sight,
                0,
                "retinal-spectral-irradiance",
                "fraction-of-declared-retinal-reference-irradiance",
            ),
            (
                PhysicalSourceSense::Sound,
                0,
                "acoustic-pressure",
                "normalized-binary64",
            ),
            (
                PhysicalSourceSense::Sound,
                1,
                "acoustic-pressure",
                "normalized-binary64",
            ),
            (
                PhysicalSourceSense::Body,
                0,
                "cupula-displacement",
                "normalized-binary64",
            ),
        ];
        for (coordinate, (sense, topology_index, quantity, unit)) in
            expected.into_iter().enumerate()
        {
            let perspective = bind_neuron_perspective(&shared, coordinate, 0).unwrap();
            let anchor = bind_neuron_source_anchor(&episode, perspective).unwrap();
            assert_eq!(anchor.source_port_index(), coordinate);
            assert_eq!(anchor.sense(), sense);
            assert_eq!(anchor.topology_index(), topology_index);
            assert_eq!(anchor.physical_quantity(), quantity);
            assert_eq!(anchor.physical_unit(), unit);
            assert_eq!(anchor.coordinates().len(), 1);
            assert!(!anchor.sensor_id().is_empty());
            assert!(!anchor.substream_id().is_empty());
        }
    }

    #[test]
    fn a_different_episode_cannot_relabel_an_existing_perspective() {
        let episode = exact_episode();
        let other = exact_episode();
        let shared = prepare_complete_joint_field_admitted_fixture(&episode, 0).unwrap();
        let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
        assert_eq!(
            bind_neuron_source_anchor(&other, perspective).unwrap_err(),
            NeuronSourceAnchorError::EpisodeDoesNotOwnSharedOccurrence
        );
    }

    #[test]
    fn from_source_port_equals_the_reached_site_for_every_episode_port() {
        // Seed expression compares authored sites against reached sites by
        // exact equality, so the genesis boundary that builds sites with
        // `from_source_port` must produce values equal to the growth path that
        // builds them with `from_anchor` from the same episode port.
        for episode in [exact_episode(), exact_four_optical_episode()] {
            let shared = prepare_complete_joint_field_admitted_fixture(&episode, 0).unwrap();
            assert_eq!(shared.vertex_count(), 4);
            for coordinate in 0..shared.vertex_count() {
                let perspective = bind_neuron_perspective(&shared, coordinate, 0).unwrap();
                let anchor = bind_neuron_source_anchor(&episode, perspective).unwrap();
                let reached = NeuronSourceSite::from_anchor(anchor);
                let port = &episode.joint_source_ports()[anchor.source_port_index()];
                assert_eq!(NeuronSourceSite::from_source_port(port).unwrap(), reached);
                // For these episodes the reached coordinate order is the port
                // order, so a growth-DNA seed authored over ports [0..n) in
                // order matches the reached cohort exactly.
                assert_eq!(anchor.source_port_index(), coordinate);
            }
        }
    }

    #[test]
    fn exact_receptor_site_cold_restores_without_samples_or_relabeling() {
        let episode = exact_episode();
        let shared = prepare_complete_joint_field_admitted_fixture(&episode, 0).unwrap();
        for coordinate in 0..4 {
            let perspective = bind_neuron_perspective(&shared, coordinate, 0).unwrap();
            let site = NeuronSourceSite::from_anchor(
                bind_neuron_source_anchor(&episode, perspective).unwrap(),
            );
            let encoded = encode_neuron_source_site(&site).unwrap();
            let restored = decode_neuron_source_site(&encoded).unwrap();
            assert_eq!(restored, site);
            assert_eq!(encode_neuron_source_site(&restored).unwrap(), encoded);
            assert_eq!(
                decode_neuron_source_site(&encoded[..encoded.len() - 1]),
                Err(NeuronSourceAnchorError::InvalidSiteEncoding)
            );
        }
    }
}
