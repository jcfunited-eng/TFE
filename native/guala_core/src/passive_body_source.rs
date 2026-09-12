//! Exact, transient position samples from already-settled passive body steps.
//! This is sensory input custody, never an action sequence or resident cognition.

use crate::virtual_articulated_body::{
    ArticulatedBodyState, ArticulatedBodyTransition, BodyAxis, BodyEffectorDirection,
    BodyEffectorTerminal, BODY_AXES,
};

pub(crate) const PASSIVE_BODY_SOURCE_MAGIC: &[u8; 8] = b"GLBPTR01";
const HEADER_BYTES: usize = 8 + 8 + 4 + 1;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PassiveBodySourceError {
    InvalidClock,
    InvalidAxes,
    InvalidPosition,
    InvalidLength,
    IncompleteTrajectory,
    NewMotorWork,
    ArithmeticWidth,
    ResourceUnavailable,
}

/// Row-major physical positions. No repeated timestamps, zero-load arrays,
/// motor directions, desired values, or learned-state fields are retained.
#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PassiveBodyTrajectory {
    axes: Vec<BodyAxis>,
    positions: Vec<i32>,
    expected_frames: usize,
}

fn axis_has_passive_motion(body: &ArticulatedBodyState, axis: BodyAxis) -> bool {
    body.axis(axis) != axis.anatomy().neutral
        || [BodyEffectorDirection::TowardMinimum, BodyEffectorDirection::TowardMaximum]
            .into_iter().any(|direction| {
                body.antagonist_activation(BodyEffectorTerminal::new(axis, direction)) != 0
            })
}

/// Acoustic silence does not imply that the instrument's controls are at rest.
pub(crate) fn has_passive_body_motion(body: &ArticulatedBodyState) -> bool {
    BODY_AXES.into_iter().any(|axis| axis_has_passive_motion(body, axis))
}

fn encoded_length(axes: usize, frames: usize) -> Result<usize, PassiveBodySourceError> {
    axes.checked_mul(frames)
        .and_then(|samples| samples.checked_mul(std::mem::size_of::<i32>()))
        .and_then(|bytes| bytes.checked_add(axes))
        .and_then(|bytes| bytes.checked_add(HEADER_BYTES))
        .ok_or(PassiveBodySourceError::ArithmeticWidth)
}

impl PassiveBodyTrajectory {
    /// The caller derives frame_count from the existing renderer's admitted
    /// sample count and one-ms mechanical cadence, before running that renderer.
    /// max_capture_bytes is a supplied resource bound, not a cognitive limit.
    pub(crate) fn begin(
        body: &ArticulatedBodyState,
        frame_count: usize,
        max_capture_bytes: usize,
    ) -> Result<Option<Self>, PassiveBodySourceError> {
        if frame_count < 2 {
            return Ok(None);
        }
        if u32::try_from(frame_count).is_err() {
            return Err(PassiveBodySourceError::ArithmeticWidth);
        }
        let mut axes = Vec::new();
        axes.try_reserve_exact(BODY_AXES.len())
            .map_err(|_| PassiveBodySourceError::ResourceUnavailable)?;
        for axis in BODY_AXES {
            if axis_has_passive_motion(body, axis)
            {
                axes.push(axis);
            }
        }
        if axes.is_empty() {
            return Ok(None);
        }
        if encoded_length(axes.len(), frame_count)? > max_capture_bytes {
            return Err(PassiveBodySourceError::ResourceUnavailable);
        }
        let sample_count = axes.len().checked_mul(frame_count)
            .ok_or(PassiveBodySourceError::ArithmeticWidth)?;
        let mut positions = Vec::new();
        positions.try_reserve_exact(sample_count)
            .map_err(|_| PassiveBodySourceError::ResourceUnavailable)?;
        positions.extend(axes.iter().map(|axis| body.axis(*axis)));
        Ok(Some(Self { axes, positions, expected_frames: frame_count }))
    }

    /// Observe an existing no-drive settlement; never perform mechanics here.
    pub(crate) fn append_quiescent(
        &mut self,
        transition: &ArticulatedBodyTransition,
    ) -> Result<(), PassiveBodySourceError> {
        if self.frame_count() >= self.expected_frames {
            return Err(PassiveBodySourceError::InvalidLength);
        }
        if transition.reached_terminal_count != 0
            || transition.proprioceptive_consequences.iter().any(|consequence| {
                consequence.toward_minimum_carriers != 0
                    || consequence.toward_maximum_carriers != 0
                    || consequence.opposed_carriers_per_terminal != 0
                    || consequence.stalled_carriers != 0
            })
        {
            return Err(PassiveBodySourceError::NewMotorWork);
        }
        // With no new drive, a previously neutral/inactive axis cannot
        // acquire passive motion. Refuse an omitted reached axis.
        if transition.proprioceptive_consequences.iter()
            .any(|consequence| self.axes.binary_search_by_key(
                &(consequence.axis as u8), |axis| *axis as u8,
            ).is_err())
        {
            return Err(PassiveBodySourceError::InvalidAxes);
        }
        self.positions.extend(self.axes.iter().map(|axis| transition.successor.axis(*axis)));
        Ok(())
    }

    pub(crate) fn axes(&self) -> &[BodyAxis] { &self.axes }
    pub(crate) fn frame_count(&self) -> usize { self.positions.len() / self.axes.len() }

    pub(crate) fn position(&self, frame: usize, axis: usize) -> Option<i32> {
        if frame >= self.frame_count() || axis >= self.axes.len() {
            return None;
        }
        frame.checked_mul(self.axes.len()).and_then(|index| index.checked_add(axis))
            .and_then(|index| self.positions.get(index)).copied()
    }

    /// Consume the transient capture into the one pending sensory payload.
    /// source_tick is the original impulse's source epoch, not the pending
    /// return's completed organism tick. Samples never advance either owner.
    pub(crate) fn into_compact(
        self,
        source_tick: u64,
        max_output_bytes: usize,
    ) -> Result<Vec<u8>, PassiveBodySourceError> {
        if self.frame_count() != self.expected_frames || self.frame_count() < 2 {
            return Err(PassiveBodySourceError::IncompleteTrajectory);
        }
        let frames = u32::try_from(self.frame_count())
            .map_err(|_| PassiveBodySourceError::ArithmeticWidth)?;
        source_tick.checked_add(u64::from(frames))
            .ok_or(PassiveBodySourceError::InvalidClock)?;
        let length = encoded_length(self.axes.len(), self.frame_count())?;
        if length > max_output_bytes {
            return Err(PassiveBodySourceError::ResourceUnavailable);
        }
        let axis_count = u8::try_from(self.axes.len())
            .map_err(|_| PassiveBodySourceError::InvalidAxes)?;
        let mut encoded = Vec::new();
        encoded.try_reserve_exact(length)
            .map_err(|_| PassiveBodySourceError::ResourceUnavailable)?;
        encoded.extend_from_slice(PASSIVE_BODY_SOURCE_MAGIC);
        encoded.extend_from_slice(&source_tick.to_le_bytes());
        encoded.extend_from_slice(&frames.to_le_bytes());
        encoded.push(axis_count);
        encoded.extend(self.axes.iter().map(|axis| *axis as u8));
        for position in self.positions {
            encoded.extend_from_slice(&position.to_le_bytes());
        }
        Ok(encoded)
    }

    /// Parse only after physical frame/byte admission supplied by the caller.
    /// Production admits the complete ordinary source workspace at startup.
    pub(crate) fn from_compact(
        encoded: &[u8],
        maximum_frames: usize,
        maximum_bytes: usize,
    ) -> Result<(u64, Self), PassiveBodySourceError> {
        if encoded.len() < HEADER_BYTES || encoded.len() > maximum_bytes
            || encoded.get(..8) != Some(PASSIVE_BODY_SOURCE_MAGIC.as_slice())
        {
            return Err(PassiveBodySourceError::InvalidLength);
        }
        let source_tick = u64::from_le_bytes(encoded[8..16].try_into()
            .map_err(|_| PassiveBodySourceError::InvalidLength)?);
        let frames = usize::try_from(u32::from_le_bytes(encoded[16..20].try_into()
            .map_err(|_| PassiveBodySourceError::InvalidLength)?))
            .map_err(|_| PassiveBodySourceError::ArithmeticWidth)?;
        let axis_count = usize::from(encoded[20]);
        if frames < 2 || frames > maximum_frames || axis_count == 0 || axis_count > BODY_AXES.len() {
            return Err(PassiveBodySourceError::InvalidLength);
        }
        if encoded_length(axis_count, frames)? != encoded.len() {
            return Err(PassiveBodySourceError::InvalidLength);
        }
        source_tick.checked_add(u64::try_from(frames)
            .map_err(|_| PassiveBodySourceError::ArithmeticWidth)?)
            .ok_or(PassiveBodySourceError::InvalidClock)?;
        let ordinals = &encoded[HEADER_BYTES..HEADER_BYTES + axis_count];
        if ordinals.windows(2).any(|pair| pair[0] >= pair[1]) {
            return Err(PassiveBodySourceError::InvalidAxes);
        }
        let mut axes = Vec::new();
        axes.try_reserve_exact(axis_count)
            .map_err(|_| PassiveBodySourceError::ResourceUnavailable)?;
        for ordinal in ordinals {
            let axis = *BODY_AXES.get(usize::from(*ordinal))
                .ok_or(PassiveBodySourceError::InvalidAxes)?;
            if axis as u8 != *ordinal {
                return Err(PassiveBodySourceError::InvalidAxes);
            }
            axes.push(axis);
        }
        let sample_count = axis_count.checked_mul(frames)
            .ok_or(PassiveBodySourceError::ArithmeticWidth)?;
        let mut positions = Vec::new();
        positions.try_reserve_exact(sample_count)
            .map_err(|_| PassiveBodySourceError::ResourceUnavailable)?;
        for (index, bytes) in encoded[HEADER_BYTES + axis_count..].chunks_exact(4).enumerate() {
            let value = i32::from_le_bytes(bytes.try_into()
                .map_err(|_| PassiveBodySourceError::InvalidLength)?);
            let anatomy = axes[index % axis_count].anatomy();
            if !(anatomy.minimum..=anatomy.maximum).contains(&value) {
                return Err(PassiveBodySourceError::InvalidPosition);
            }
            positions.push(value);
        }
        Ok((source_tick, Self {
            axes, positions, expected_frames: frames,
        }))
    }
}


#[cfg(test)]
mod tests {
    use super::*;
    use num_bigint::BigInt;
    use num_rational::BigRational;
    use num_traits::{One, Zero};
    use crate::articulated_body_joint_source_builder::{
        admit_articulated_body_consequence_source, admit_passive_body_trajectory_source,
        exact_moved_effector_terminal,
    };
    use crate::joint_uf_neuron_boundary::{
        bind_neuron_perspective, prepare_complete_joint_field_with_admission,
    };
    use crate::joint_uf_source_adapter::JointUfSourceAdmission;
    use crate::proprioceptive_receptor_work::{
        derive_effector_load_receptor_sample_range_work, ProprioceptiveReceptorAnatomy,
        validate_passive_body_source_port,
    };
    use crate::virtual_articulated_body::{
        settle_body_effector_drives, AdmittedBodyEffectorDrives, BodyEffectorDrive,
        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
    };
    use crate::virtual_articulatory_body::settle_native_articulatory_interval;

    #[test]
    fn silent_controls_without_new_impulse_still_return_real_motion() {
        // A valid quiet physical state, not a cue/learning fixture. No new
        // drive or pressure is needed for a displaced control to return.
        let neutral = ArticulatedBodyState::at_neutral();
        let axis = BodyAxis::VocalTractSection0Area;
        let mut axes = *neutral.axes();
        axes[axis.index()] += 1;
        let quiet = ArticulatedBodyState::from_physical_state(
            axes, neutral.lung_air_microlitres(), true,
        ).unwrap();
        assert!(quiet.articulatory_system_is_quiescent());
        assert!(has_passive_body_motion(&quiet));
        assert!(!has_passive_body_motion(&neutral));
        let rendered = settle_native_articulatory_interval(quiet, &[], 0, 4_000).unwrap();
        assert!(rendered.radiated_pressure_pcm.iter().all(|value| *value == 0));
        let trace = rendered.passive_body_trajectory.unwrap();
        assert_eq!(trace.axes(), &[axis]);
        assert_eq!(trace.frame_count(), 250);
        assert_eq!(trace.position(0, 0), Some(axis.anatomy().neutral + 1));
        assert_eq!(trace.position(1, 0), Some(axis.anatomy().neutral));
    }

    /// Component proof only. Mature neuronal delivery and production remain
    /// separate acceptance obligations; this test cannot prove learned speech.
    #[test]
    fn existing_passive_steps_roundtrip_without_new_motor_authority() {
        const FRAMES: usize = 250;
        const COMPACT_LIMIT: usize = 21 + 45 + 4 * 45 * FRAMES;
        let axis = BodyAxis::VocalTractSection0Area;
        let neutral = ArticulatedBodyState::at_neutral();
        assert!(PassiveBodyTrajectory::begin(&neutral, FRAMES, COMPACT_LIMIT).unwrap().is_none());
        let mut dose_payloads = Vec::new();
        for dose in [32, 128] {
            let drive = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
                terminal: BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMaximum),
                outward_elementary_carriers: dose,
            }]).unwrap();
            let impulse = settle_body_effector_drives(
                &neutral, &drive, BODY_SETTLEMENT_CLOCK_MICROSECONDS,
            ).unwrap();
            let initial = admit_articulated_body_consequence_source(
                42, &impulse.proprioceptive_consequences,
            ).unwrap();
            let mut capture = PassiveBodyTrajectory::begin(
                &impulse.successor, FRAMES, COMPACT_LIMIT,
            ).unwrap().unwrap();
            assert_eq!(capture.append_quiescent(&impulse), Err(PassiveBodySourceError::NewMotorWork));
            let mut rendered = settle_native_articulatory_interval(
                impulse.successor.clone(), &impulse.proprioceptive_consequences, 0, 4_000,
            ).unwrap();
            assert!(rendered.radiated_pressure_pcm.iter().all(|value| *value == 0));
            let trajectory = rendered.passive_body_trajectory.take().unwrap();
            assert_eq!(trajectory.axes(), &[axis]);
            assert_eq!(trajectory.frame_count(), FRAMES);
            let mut mechanical = impulse.successor.clone();
            for frame in 0..FRAMES {
                if frame != 0 {
                    mechanical = settle_body_effector_drives(
                        &mechanical, &AdmittedBodyEffectorDrives::quiescent(),
                        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
                    ).unwrap().successor;
                }
                assert_eq!(trajectory.position(frame, 0), Some(mechanical.axis(axis)));
            }
            assert_eq!(rendered.successor_body.axis(axis), mechanical.axis(axis));
            for direction in [BodyEffectorDirection::TowardMinimum, BodyEffectorDirection::TowardMaximum] {
                let terminal = BodyEffectorTerminal::new(axis, direction);
                assert_eq!(rendered.successor_body.antagonist_activation(terminal),
                    mechanical.antagonist_activation(terminal));
            }
            let encoded = trajectory.clone().into_compact(42, COMPACT_LIMIT).unwrap();
            assert_eq!(encoded.len(), 21 + 1 + 4 * FRAMES);
            assert!(PassiveBodyTrajectory::from_compact(&encoded, FRAMES - 1, COMPACT_LIMIT).is_err());
            assert!(PassiveBodyTrajectory::from_compact(&encoded, FRAMES, encoded.len() - 1).is_err());
            let (tick, cold) = PassiveBodyTrajectory::from_compact(&encoded, FRAMES, COMPACT_LIMIT).unwrap();
            assert_eq!(tick, 42);
            assert_eq!(cold, trajectory);
            let warm_source = admit_passive_body_trajectory_source(tick, &trajectory).unwrap();
            let cold_source = admit_passive_body_trajectory_source(tick, &cold).unwrap();
            assert_eq!(warm_source.joint_source_body(), cold_source.joint_source_body());
            assert_eq!(cold.into_compact(tick, COMPACT_LIMIT).unwrap(), encoded);
            let ports = warm_source.joint_source_ports();
            assert_eq!(ports.len(), 4);
            assert_eq!(warm_source.joint_source_occurrences().len(), 1);
            for (port, original) in ports.iter().zip(initial.joint_source_ports()) {
                assert_eq!(port.source_times.len(), FRAMES);
                assert_eq!(port.source_times[0], BigRational::new(BigInt::from(43), BigInt::from(1000)));
                assert_eq!(port.source_times[FRAMES - 1], BigRational::new(BigInt::from(292), BigInt::from(1000)));
                assert_eq!(port.body_proprioceptor_terminal, original.body_proprioceptor_terminal);
                assert_eq!(port.topology_index, original.topology_index);
                assert_eq!(port.sensor_id, original.sensor_id);
                assert_eq!(port.substream_id, original.substream_id);
                assert_eq!(port.coordinates, original.coordinates);
                assert_eq!(port.physical_quantity, original.physical_quantity);
                assert_eq!(port.physical_unit, original.physical_unit);
                assert_eq!(exact_moved_effector_terminal(port).unwrap(), None);
            }
            for frame in 0..FRAMES {
                assert_eq!(&ports[0].exact_normalized_sources[frame]
                    + &ports[1].exact_normalized_sources[frame], BigRational::one());
                assert!(ports[2].exact_normalized_sources[frame].is_zero());
                assert!(ports[3].exact_normalized_sources[frame].is_zero());
            }
            let admission = JointUfSourceAdmission::new(BigRational::new(
                BigInt::from(FRAMES - 1), BigInt::from(1000),
            )).unwrap();
            let shared = prepare_complete_joint_field_with_admission(
                &warm_source, 0, &admission,
            ).unwrap();
            let anatomy = ProprioceptiveReceptorAnatomy::new(
                BigRational::one(), BigRational::one(), BigRational::one(), BigRational::one(),
            ).unwrap();
            for ending in [2, 3] {
                let load = derive_effector_load_receptor_sample_range_work(
                    &warm_source, bind_neuron_perspective(&shared, ending, 0).unwrap(),
                    &anatomy, 0, FRAMES - 1,
                ).unwrap();
                assert!(load.transduced_energy_zeptojoules.is_zero());
                assert_eq!(load.elementary_reaction_energy_zeptojoules,
                    BigRational::new(BigInt::one(), BigInt::from(1000)));
            }
            let mut invalid = ports[2].clone();
            invalid.exact_normalized_sources[1] = BigRational::one();
            assert!(validate_passive_body_source_port(&invalid).is_err());
            dose_payloads.push(encoded);
        }
        assert_ne!(dose_payloads[0], dose_payloads[1]);
    }
}
