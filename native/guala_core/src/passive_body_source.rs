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
            if body.axis(axis) != axis.anatomy().neutral
                || [BodyEffectorDirection::TowardMinimum, BodyEffectorDirection::TowardMaximum]
                    .into_iter().any(|direction| {
                        body.antagonist_activation(BodyEffectorTerminal::new(axis, direction)) != 0
                    })
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
    /// Full-field expansion has its own working-memory admission at its caller.
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
