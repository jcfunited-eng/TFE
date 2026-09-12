//! Sparse exact proprioceptive source admission for the articulated body.
//!
//! One settled body transition becomes ordinary typed body-sense evidence for
//! the next organism interval. Every reached axis contributes its two fixed
//! antagonist proprioceptive endings. Their explicit afferent anatomy is
//! paired with, but never substituted for, the motor neuron's efferent mount;
//! topology indices and descriptive text select neither one.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, ToPrimitive, Zero};

use crate::passive_body_source::PassiveBodyTrajectory;
use crate::joint_source_episode::{
    decode_native_joint_source_episode, JointSourcePortView,
    NativeJointSourceEpisode,
};
use crate::joint_uf_source_adapter::SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE;
use crate::proprioceptive_receptor_work::{
    ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY, ARTICULATED_AXIS_SPAN_FRACTION_UNIT,
    PASSIVE_BODY_EVIDENCE_MAGIC,
    DISCHARGED_EFFECTOR_CARRIER_FRACTION_UNIT, EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY,
};
use crate::virtual_articulated_body::{
    ArticulatedBodyState, BodyAxis, BodyEffectorDirection, BodyEffectorTerminal,
    BodyProprioceptiveConsequence, BodyProprioceptorTerminal, BODY_AXES,
};

const VERSION: u16 = 3;
const TICKS_PER_SECOND: u64 = 1_000;
const PORT_RELEVANCE: &str = "guala.body.proprioceptor.present.r(t)=1.exact.v1";
const JOINT_RELEVANCE: &[u8] = b"guala.body.antagonist_pair.present.r(t)=1.exact.v1";
const INPUT_MAP: &str = "antagonist-length-over-articulated-axis-span-v1";
const EVIDENCE_MAGIC: &[u8; 8] = b"GLBPEV01";
const CONSEQUENCE_VERSION: u16 = 4;

const CONSEQUENCE_MAGIC: &[u8; 8] = b"GLJSRC04";
const LOAD_PORT_RELEVANCE: &str = "guala.body.effector_load.present.r(t)=1.exact.v1";
const LOAD_INPUT_MAP: &str = "reacted-over-discharged-effector-carriers-v1";

/// Startup-only maximum encoded metadata, excluding temporal samples.
/// Uses the existing encoder's fields and fixed body anatomy, not a body
/// transition or a synthetic source. The four-ending form also bounds v3.
pub(crate) fn articulated_source_metadata_bytes() -> usize {
    let longest_axis = BODY_AXES.iter()
        .map(|axis| axis.anatomical_name().len()).max().expect("fixed body anatomy");
    let text_lengths = [
        "articulated-body-effector-load-receptor".len()
            .max("articulated-body-proprioceptor".len()),
        longest_axis + 1 + "toward-minimum".len().max("toward-maximum".len()) + "-load".len(),
        "body-antagonist-proprioceptor-terminal".len().max("body-effector-load-terminal".len()),
        (BODY_AXES.len() * 2 - 1).to_string().len(),
        ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY.len()
            .max(EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY.len()),
        ARTICULATED_AXIS_SPAN_FRACTION_UNIT.len()
            .max(DISCHARGED_EFFECTOR_CARRIER_FRACTION_UNIT.len()),
        PORT_RELEVANCE.len().max(LOAD_PORT_RELEVANCE.len()),
        0, // no relevance-origin identifier
        INPUT_MAP.len().max(LOAD_INPUT_MAP.len()),
    ];
    // sense/topology/presence/axis/direction; coordinate count; identifiers;
    // four 0/1 maps; GLBPEV01 profile; sample count. The passive26-byte
    // profile is smaller than the existing118-byte impulse profile.
    let evidence_bytes = 8 + 8 + 8 + 1 + 1 + 4 + 4 + 4 + 5 * 16;
    let port = 1 + 4 + 1 + 1 + 1 + 2
        + text_lengths.into_iter().map(|length| 2 + length).sum::<usize>()
        + 4 * (2 + 1 + 2 + 1) + 4 + evidence_bytes + 4;
    let occurrence = 4 + 4 * 4 + 4
        + 4 + SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE.len()
        + 4 + 4 + 4 * 4 + 4 + JOINT_RELEVANCE.len() + 4;
    let episode = 8 + 2 + 2
        + "articulated-body-position-and-load-interval".len()
            .max("articulated-body-proprioceptive-interval".len())
        + 6 + 4 + 4;
    episode + BODY_AXES.len() * (4 * port + occurrence)
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum ArticulatedBodyJointSourceError {
    SourceTickOverflow,
    EmptyConsequences,
    NoncanonicalConsequences,
    ArithmeticWidth,
    NonFiniteCoordinate,
    ResourceUnavailable,
    Carrier(String),
}

/// Recover the newly discharged motor terminal whose admitted activation
/// moved an axis in its own direction. Passive tissue return and movement
/// dominated by retained opposing activation are sensed without being
/// relabeled as motor causes. The four position/load endings for an axis carry
/// the same consequence, so the caller deduplicates the returned terminal.
pub(crate) fn exact_moved_effector_terminal(
    port: &JointSourcePortView,
) -> Result<Option<BodyEffectorTerminal>, ArticulatedBodyJointSourceError> {
    let evidence = port.input_map_profile.as_slice();
    if evidence.get(..EVIDENCE_MAGIC.len()) != Some(EVIDENCE_MAGIC) {
        return Ok(None);
    }
    const FIXED_PREFIX: usize = 8 + 8 + 8 + 1 + 1 + 4 + 4 + 4;
    const EVIDENCE_BYTES: usize = FIXED_PREFIX + 5 * 16;
    if evidence.len() != EVIDENCE_BYTES {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    let terminal = port
        .body_proprioceptor_terminal
        .ok_or(ArticulatedBodyJointSourceError::NoncanonicalConsequences)?;
    if evidence[24] != terminal.axis() as u8 || evidence[25] != terminal.direction() as u8 {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    let read_i32 = |offset: usize| {
        i32::from_le_bytes(
            evidence[offset..offset + 4]
                .try_into()
                .expect("checked body-evidence width"),
        )
    };
    let read_u128 = |offset: usize| {
        u128::from_le_bytes(
            evidence[offset..offset + 16]
                .try_into()
                .expect("checked body-evidence width"),
        )
    };
    let predecessor = read_i32(26);
    let successor = read_i32(30);
    let signed_displacement = read_i32(34);
    let toward_minimum = read_u128(38);
    let toward_maximum = read_u128(54);
    let opposed = read_u128(70);
    let applied = read_u128(86);
    let stalled = read_u128(102);
    if successor.checked_sub(predecessor) != Some(signed_displacement)
        || opposed != toward_minimum.min(toward_maximum)
        || applied != u128::from(signed_displacement.unsigned_abs())
    {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    let (direction, net) = match toward_minimum.cmp(&toward_maximum) {
        core::cmp::Ordering::Greater => (
            BodyEffectorDirection::TowardMinimum,
            toward_minimum - toward_maximum,
        ),
        core::cmp::Ordering::Less => (
            BodyEffectorDirection::TowardMaximum,
            toward_maximum - toward_minimum,
        ),
        core::cmp::Ordering::Equal => {
            if stalled != 0 {
                return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
            }
            return Ok(None);
        }
    };
    if stalled > net {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    let newly_admitted = net - stalled;
    if newly_admitted == 0
        || signed_displacement == 0
        || (signed_displacement < 0) != (direction == BodyEffectorDirection::TowardMinimum)
    {
        return Ok(None);
    }
    Ok(Some(BodyEffectorTerminal::new(terminal.axis(), direction)))
}

pub(crate) fn admit_articulated_body_proprioceptive_source(
    source_tick: u64,
    consequences: &[BodyProprioceptiveConsequence],
) -> Result<NativeJointSourceEpisode, ArticulatedBodyJointSourceError> {
    if consequences.is_empty() {
        return Err(ArticulatedBodyJointSourceError::EmptyConsequences);
    }
    if consequences
        .windows(2)
        .any(|pair| pair[0].axis >= pair[1].axis)
    {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    for consequence in consequences {
        let anatomy = consequence.axis.anatomy();
        if consequence.unit != anatomy.unit
            || !(anatomy.minimum..=anatomy.maximum).contains(&consequence.predecessor_position)
            || !(anatomy.minimum..=anatomy.maximum).contains(&consequence.successor_position)
            || consequence
                .successor_position
                .checked_sub(consequence.predecessor_position)
                != Some(consequence.signed_displacement)
            || consequence.applied_displacement_quanta
                != u128::from(consequence.signed_displacement.unsigned_abs())
            || consequence.opposed_carriers_per_terminal
                != consequence
                    .toward_minimum_carriers
                    .min(consequence.toward_maximum_carriers)
            || consequence.stalled_carriers
                > consequence
                    .toward_minimum_carriers
                    .abs_diff(consequence.toward_maximum_carriers)
        {
            return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
        }
    }

    let successor_tick = source_tick
        .checked_add(1)
        .ok_or(ArticulatedBodyJointSourceError::SourceTickOverflow)?;
    let times = [
        BigRational::new(BigInt::from(source_tick), BigInt::from(TICKS_PER_SECOND)),
        BigRational::new(BigInt::from(successor_tick), BigInt::from(TICKS_PER_SECOND)),
    ];
    let port_count = consequences
        .len()
        .checked_mul(2)
        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?;
    let sample_count = port_count
        .checked_mul(2)
        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?;
    let occurrence_frame_count = consequences
        .len()
        .checked_mul(2)
        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?;

    let mut output = b"GLJSRC03".to_vec();
    output.extend_from_slice(&VERSION.to_le_bytes());
    text(&mut output, "articulated-body-proprioceptive-interval")?;
    output.extend_from_slice(&[1, 1, 1, 1, 1, 0]);
    u32_value(&mut output, port_count)?;
    for consequence in consequences {
        for direction in [
            BodyEffectorDirection::TowardMinimum,
            BodyEffectorDirection::TowardMaximum,
        ] {
            let terminal = BodyProprioceptorTerminal::new(consequence.axis, direction);
            output.push(5);
            u32_value(&mut output, terminal.proprioceptor_topology_index())?;
            output.push(1);
            output.push(
                u8::try_from(consequence.axis.index())
                    .map_err(|_| ArticulatedBodyJointSourceError::ArithmeticWidth)?,
            );
            output.push(direction as u8);
            text(&mut output, "articulated-body-proprioceptor")?;
            text(
                &mut output,
                &format!(
                    "{}-{}",
                    consequence.axis.anatomical_name(),
                    match direction {
                        BodyEffectorDirection::TowardMinimum => "toward-minimum",
                        BodyEffectorDirection::TowardMaximum => "toward-maximum",
                    }
                ),
            )?;
            output.extend_from_slice(&1_u16.to_le_bytes());
            text(&mut output, "body-antagonist-proprioceptor-terminal")?;
            text(&mut output, &terminal.ordinal().to_string())?;
            text(&mut output, ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY)?;
            text(&mut output, ARTICULATED_AXIS_SPAN_FRACTION_UNIT)?;
            text(&mut output, PORT_RELEVANCE)?;
            text(&mut output, "")?;
            text(&mut output, INPUT_MAP)?;
            rational(&mut output, &BigRational::zero())?;
            rational(&mut output, &BigRational::one())?;
            rational(&mut output, &BigRational::zero())?;
            rational(&mut output, &BigRational::one())?;
            let evidence = exact_evidence(source_tick, successor_tick, consequence, terminal);
            bytes(&mut output, &evidence)?;
            u32_value(&mut output, 2)?;
            for (time, position) in times.iter().zip([
                consequence.predecessor_position,
                consequence.successor_position,
            ]) {
                let exact = normalized_antagonist_length(consequence.axis, position, direction)?;
                let projection = exact
                    .to_f64()
                    .filter(|value| value.is_finite() && (0.0..=1.0).contains(value))
                    .ok_or(ArticulatedBodyJointSourceError::NonFiniteCoordinate)?;
                rational(&mut output, time)?;
                output.extend_from_slice(&projection.to_bits().to_le_bytes());
                rational(&mut output, &BigRational::zero())?;
                rational(&mut output, &BigRational::one())?;
                rational(&mut output, &exact)?;
            }
        }
    }

    u32_value(&mut output, consequences.len())?;
    for axis_ordinal in 0..consequences.len() {
        u32_value(&mut output, 2)?;
        u32_value(&mut output, axis_ordinal * 2)?;
        u32_value(&mut output, axis_ordinal * 2 + 1)?;
        u32_value(&mut output, 2)?;
        for time in &times {
            rational(&mut output, time)?;
        }
        bytes(
            &mut output,
            SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE,
        )?;
        u32_value(&mut output, 1)?;
        u32_value(&mut output, 2)?;
        u32_value(&mut output, 0)?;
        u32_value(&mut output, 1)?;
        bytes(&mut output, JOINT_RELEVANCE)?;
        u32_value(&mut output, 2)?;
        rational(&mut output, &BigRational::one())?;
        rational(&mut output, &BigRational::one())?;
    }

    decode_native_joint_source_episode(
        &output,
        port_count,
        sample_count,
        consequences.len(),
        occurrence_frame_count,
    )
    .map_err(ArticulatedBodyJointSourceError::Carrier)
}

/// Admit position and reacted load as distinct simultaneous physical endings.
/// The load fraction is exact: opposed carriers plus any stop-stalled net
/// drive, divided by the carriers discharged through that terminal.  Nothing
/// is scored, thresholded, or inferred from an action label.
pub(crate) fn admit_articulated_body_consequence_source(
    source_tick: u64,
    consequences: &[BodyProprioceptiveConsequence],
) -> Result<NativeJointSourceEpisode, ArticulatedBodyJointSourceError> {
    if consequences.is_empty() {
        return Err(ArticulatedBodyJointSourceError::EmptyConsequences);
    }
    if consequences
        .windows(2)
        .any(|pair| pair[0].axis >= pair[1].axis)
    {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    for consequence in consequences {
        let anatomy = consequence.axis.anatomy();
        if consequence.unit != anatomy.unit
            || !(anatomy.minimum..=anatomy.maximum).contains(&consequence.predecessor_position)
            || !(anatomy.minimum..=anatomy.maximum).contains(&consequence.successor_position)
            || consequence.successor_position - consequence.predecessor_position
                != consequence.signed_displacement
        {
            return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
        }
    }

    let successor_tick = source_tick
        .checked_add(1)
        .ok_or(ArticulatedBodyJointSourceError::SourceTickOverflow)?;
    let times = [
        BigRational::new(BigInt::from(source_tick), BigInt::from(TICKS_PER_SECOND)),
        BigRational::new(BigInt::from(successor_tick), BigInt::from(TICKS_PER_SECOND)),
    ];
    let port_count = consequences
        .len()
        .checked_mul(4)
        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?;
    let sample_count = port_count
        .checked_mul(2)
        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?;
    let occurrence_frame_count = consequences
        .len()
        .checked_mul(2)
        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?;

    let mut output = CONSEQUENCE_MAGIC.to_vec();
    output.extend_from_slice(&CONSEQUENCE_VERSION.to_le_bytes());
    text(&mut output, "articulated-body-position-and-load-interval")?;
    output.extend_from_slice(&[1, 1, 1, 1, 1, 0]);
    u32_value(&mut output, port_count)?;
    for consequence in consequences {
        for load_ending in [false, true] {
            for direction in [
                BodyEffectorDirection::TowardMinimum,
                BodyEffectorDirection::TowardMaximum,
            ] {
                let terminal = BodyProprioceptorTerminal::new(consequence.axis, direction);
                let evidence = exact_evidence(source_tick, successor_tick, consequence, terminal);
                encode_position_load_port_header(
                    &mut output, consequence.axis, direction, load_ending, &evidence,
                )?;
                u32_value(&mut output, 2)?;
                let load = reactive_load_fraction(consequence, direction)?;
                for (time, position) in times.iter().zip([
                    consequence.predecessor_position,
                    consequence.successor_position,
                ]) {
                    let exact = if load_ending {
                        load.clone()
                    } else {
                        normalized_antagonist_length(consequence.axis, position, direction)?
                    };
                    let projection = exact
                        .to_f64()
                        .filter(|value| value.is_finite() && (0.0..=1.0).contains(value))
                        .ok_or(ArticulatedBodyJointSourceError::NonFiniteCoordinate)?;
                    rational(&mut output, time)?;
                    output.extend_from_slice(&projection.to_bits().to_le_bytes());
                    rational(&mut output, &BigRational::zero())?;
                    rational(&mut output, &BigRational::one())?;
                    rational(&mut output, &exact)?;
                }
            }
        }
    }

    u32_value(&mut output, consequences.len())?;
    for axis_ordinal in 0..consequences.len() {
        u32_value(&mut output, 4)?;
        for port in axis_ordinal * 4..axis_ordinal * 4 + 4 {
            u32_value(&mut output, port)?;
        }
        u32_value(&mut output, 2)?;
        for time in &times {
            rational(&mut output, time)?;
        }
        bytes(
            &mut output,
            SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE,
        )?;
        u32_value(&mut output, 1)?;
        u32_value(&mut output, 4)?;
        for group_member in 0..4 {
            u32_value(&mut output, group_member)?;
        }
        bytes(&mut output, JOINT_RELEVANCE)?;
        u32_value(&mut output, 2)?;
        rational(&mut output, &BigRational::one())?;
        rational(&mut output, &BigRational::one())?;
    }

    decode_native_joint_source_episode(
        &output,
        port_count,
        sample_count,
        consequences.len(),
        occurrence_frame_count,
    )
    .map_err(ArticulatedBodyJointSourceError::Carrier)
}

/// Expand one compact passive trajectory into the existing full joint field.
/// Production admits the complete coexisting input set once at startup.
/// This encoder checks its physical shape and reserves its bounded output;
/// it does not re-account the runtime budget per return. No motor receipt.
pub(crate) fn admit_passive_body_trajectory_source(
    source_tick: u64,
    trajectory: &PassiveBodyTrajectory,
) -> Result<NativeJointSourceEpisode, ArticulatedBodyJointSourceError> {
    let axes = trajectory.axes();
    let frames = trajectory.frame_count();
    if axes.is_empty() || frames < 2
        || frames > crate::virtual_articulatory_body::MAX_PASSIVE_BODY_FRAMES
    {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    let start = source_tick.checked_add(1)
        .ok_or(ArticulatedBodyJointSourceError::SourceTickOverflow)?;
    let end = source_tick.checked_add(u64::try_from(frames)
        .map_err(|_| ArticulatedBodyJointSourceError::ArithmeticWidth)?)
        .ok_or(ArticulatedBodyJointSourceError::SourceTickOverflow)?;
    let ports = axes.len() * 4;
    let samples = ports * frames;
    let occurrence_frames = axes.len() * frames;

    // Metadata is built once per physical ending and reused in the encoding.
    // Its roster is bounded by the body's 45 axes, independently of payload.
    let mut headers = Vec::new();
    headers.try_reserve_exact(ports)
        .map_err(|_| ArticulatedBodyJointSourceError::ResourceUnavailable)?;
    for axis in axes {
        for load in [false, true] {
            for direction in [
                BodyEffectorDirection::TowardMinimum,
                BodyEffectorDirection::TowardMaximum,
            ] {
                let mut witness = [0_u8; 26];
                witness[..8].copy_from_slice(PASSIVE_BODY_EVIDENCE_MAGIC);
                witness[8..16].copy_from_slice(&start.to_le_bytes());
                witness[16..24].copy_from_slice(&end.to_le_bytes());
                witness[24] = *axis as u8;
                witness[25] = direction as u8;
                let mut header = Vec::new();
                encode_position_load_port_header(&mut header, *axis, direction, load, &witness)?;
                u32_value(&mut header, frames)?;
                headers.push(header);
            }
        }
    }
    let mut output = CONSEQUENCE_MAGIC.to_vec();
    output.extend_from_slice(&CONSEQUENCE_VERSION.to_le_bytes());
    text(&mut output, "articulated-body-position-and-load-interval")?;
    output.extend_from_slice(&[1, 1, 1, 1, 1, 0]);
    u32_value(&mut output, ports)?;
    // Decimal u64 time numerator: at most 20 chars, denominator: at most
    // four (1000). Each rational has two u16 string lengths. Position/span
    // uses differences of i32 values: at most ten chars in each component.
    // A port frame is time + binary64 + phase 0/1 + relevance 1/1 + position.
    const TIME_BYTES: usize = 2 + 20 + 2 + 4;
    const FRACTION_BYTES: usize = 2 + 10 + 2 + 10;
    const UNIT_RATIONAL_BYTES: usize = 2 + 1 + 2 + 1;
    const PORT_FRAME_BYTES: usize =
        TIME_BYTES + 8 + 2 * UNIT_RATIONAL_BYTES + FRACTION_BYTES;
    let occurrence_header_bytes = 4 + 4 * 4 + 4
        + 4 + SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE.len()
        + 4 + 4 + 4 * 4 + 4 + JOINT_RELEVANCE.len() + 4;
    let bound = headers.iter().try_fold(output.len() + 4, |total, header| {
        total.checked_add(header.len())
    }).and_then(|total| total.checked_add(samples.checked_mul(PORT_FRAME_BYTES)?))
        .and_then(|total| total.checked_add(axes.len().checked_mul(occurrence_header_bytes)?))
        .and_then(|total| total.checked_add(
            occurrence_frames.checked_mul(TIME_BYTES + UNIT_RATIONAL_BYTES)?))
        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?;
    output.try_reserve_exact(bound - output.len())
        .map_err(|_| ArticulatedBodyJointSourceError::ResourceUnavailable)?;
    let mut times = Vec::new();
    times.try_reserve_exact(frames)
        .map_err(|_| ArticulatedBodyJointSourceError::ResourceUnavailable)?;
    for frame in 0..frames {
        times.push(BigRational::new(BigInt::from(start + frame as u64),
            BigInt::from(TICKS_PER_SECOND)));
    }
    let zero = BigRational::zero();
    let one = BigRational::one();
    for (port_index, header) in headers.into_iter().enumerate() {
        output.extend_from_slice(&header);
        let axis_index = port_index / 4;
        let load = port_index % 4 >= 2;
        let direction = if port_index % 2 == 0 {
            BodyEffectorDirection::TowardMinimum
        } else {
            BodyEffectorDirection::TowardMaximum
        };
        for (frame, time) in times.iter().enumerate() {
            let value = if load { zero.clone() } else {
                normalized_antagonist_length(
                    axes[axis_index],
                    trajectory.position(frame, axis_index)
                        .ok_or(ArticulatedBodyJointSourceError::NoncanonicalConsequences)?,
                    direction,
                )?
            };
            let projection = value.to_f64().filter(|value| value.is_finite()
                && (0.0..=1.0).contains(value))
                .ok_or(ArticulatedBodyJointSourceError::NonFiniteCoordinate)?;
            rational(&mut output, time)?;
            output.extend_from_slice(&projection.to_bits().to_le_bytes());
            rational(&mut output, &zero)?;
            rational(&mut output, &one)?;
            rational(&mut output, &value)?;
        }
    }
    u32_value(&mut output, axes.len())?;
    for axis_index in 0..axes.len() {
        u32_value(&mut output, 4)?;
        for port in axis_index * 4..axis_index * 4 + 4 {
            u32_value(&mut output, port)?;
        }
        u32_value(&mut output, frames)?;
        for time in &times { rational(&mut output, time)?; }
        bytes(&mut output, SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE)?;
        u32_value(&mut output, 1)?;
        u32_value(&mut output, 4)?;
        for member in 0..4 { u32_value(&mut output, member)?; }
        bytes(&mut output, JOINT_RELEVANCE)?;
        u32_value(&mut output, frames)?;
        for _ in 0..frames { rational(&mut output, &one)?; }
    }
    crate::joint_source_episode::decode_native_joint_source_episode_owned(
        output, ports, samples, axes.len(), occurrence_frames,
    ).map_err(ArticulatedBodyJointSourceError::Carrier)
}

fn encode_position_load_port_header(
    output: &mut Vec<u8>,
    axis: BodyAxis,
    direction: BodyEffectorDirection,
    load_ending: bool,
    evidence: &[u8],
) -> Result<(), ArticulatedBodyJointSourceError> {
    let terminal = BodyProprioceptorTerminal::new(axis, direction);
    output.push(5);
    u32_value(
        output,
        if load_ending {
            terminal.load_topology_index()
        } else {
            terminal.proprioceptor_topology_index()
        },
    )?;
    output.push(1);
    output.push(
        u8::try_from(axis.index())
            .map_err(|_| ArticulatedBodyJointSourceError::ArithmeticWidth)?,
    );
    output.push(direction as u8);
    text(
        output,
        if load_ending {
            "articulated-body-effector-load-receptor"
        } else {
            "articulated-body-proprioceptor"
        },
    )?;
    let direction_name = match direction {
        BodyEffectorDirection::TowardMinimum => "toward-minimum",
        BodyEffectorDirection::TowardMaximum => "toward-maximum",
    };
    text(
        output,
        &if load_ending {
            format!(
                "{}-{direction_name}-load",
                axis.anatomical_name()
            )
        } else {
            format!("{}-{direction_name}", axis.anatomical_name())
        },
    )?;
    output.extend_from_slice(&1_u16.to_le_bytes());
    text(
        output,
        if load_ending {
            "body-effector-load-terminal"
        } else {
            // GLJSRC04 extends the occurrence with load endings;
            // it does not rename the already-mounted GLJSRC03
            // length receptor.
            "body-antagonist-proprioceptor-terminal"
        },
    )?;
    text(output, &terminal.ordinal().to_string())?;
    text(
        output,
        if load_ending {
            EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
        } else {
            ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY
        },
    )?;
    text(
        output,
        if load_ending {
            DISCHARGED_EFFECTOR_CARRIER_FRACTION_UNIT
        } else {
            ARTICULATED_AXIS_SPAN_FRACTION_UNIT
        },
    )?;
    text(
        output,
        if load_ending {
            LOAD_PORT_RELEVANCE
        } else {
            PORT_RELEVANCE
        },
    )?;
    text(output, "")?;
    text(
        output,
        if load_ending {
            LOAD_INPUT_MAP
        } else {
            INPUT_MAP
        },
    )?;
    rational(output, &BigRational::zero())?;
    rational(output, &BigRational::one())?;
    rational(output, &BigRational::zero())?;
    rational(output, &BigRational::one())?;
    bytes(output, evidence)?;

    Ok(())
}

/// Observe the complete fixed-capacity body once without inventing motion.
/// This gives every terminal a stable receptor site before any motor ancestry
/// can reach it. The roster is bounded at 74 ports and contains no history.
pub(crate) fn admit_complete_articulated_body_state_source(
    source_tick: u64,
    state: &ArticulatedBodyState,
) -> Result<NativeJointSourceEpisode, ArticulatedBodyJointSourceError> {
    let consequences = BODY_AXES
        .iter()
        .copied()
        .map(|axis| {
            let position = state.axis(axis);
            BodyProprioceptiveConsequence {
                axis,
                unit: axis.anatomy().unit,
                predecessor_position: position,
                successor_position: position,
                signed_displacement: 0,
                toward_minimum_carriers: 0,
                toward_maximum_carriers: 0,
                opposed_carriers_per_terminal: 0,
                applied_displacement_quanta: 0,
                stalled_carriers: 0,
            }
        })
        .collect::<Vec<_>>();
    admit_articulated_body_proprioceptive_source(source_tick, &consequences)
}

fn normalized_antagonist_length(
    axis: BodyAxis,
    position: i32,
    direction: BodyEffectorDirection,
) -> Result<BigRational, ArticulatedBodyJointSourceError> {
    let anatomy = axis.anatomy();
    let span = i64::from(anatomy.maximum) - i64::from(anatomy.minimum);
    if span <= 0 {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    let toward_minimum_length = i64::from(position) - i64::from(anatomy.minimum);
    let length = match direction {
        BodyEffectorDirection::TowardMinimum => toward_minimum_length,
        BodyEffectorDirection::TowardMaximum => span - toward_minimum_length,
    };
    Ok(BigRational::new(BigInt::from(length), BigInt::from(span)))
}

fn reactive_load_fraction(
    consequence: &BodyProprioceptiveConsequence,
    direction: BodyEffectorDirection,
) -> Result<BigRational, ArticulatedBodyJointSourceError> {
    let discharged = match direction {
        BodyEffectorDirection::TowardMinimum => consequence.toward_minimum_carriers,
        BodyEffectorDirection::TowardMaximum => consequence.toward_maximum_carriers,
    };
    if discharged == 0 {
        return Ok(BigRational::zero());
    }
    let carries_stall = match direction {
        BodyEffectorDirection::TowardMinimum => {
            consequence.toward_minimum_carriers > consequence.toward_maximum_carriers
        }
        BodyEffectorDirection::TowardMaximum => {
            consequence.toward_maximum_carriers > consequence.toward_minimum_carriers
        }
    };
    let reacted = consequence
        .opposed_carriers_per_terminal
        .checked_add(if carries_stall {
            consequence.stalled_carriers
        } else {
            0
        })
        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?;
    if reacted > discharged {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    Ok(BigRational::new(
        BigInt::from(reacted),
        BigInt::from(discharged),
    ))
}

fn exact_evidence(
    source_tick: u64,
    successor_tick: u64,
    consequence: &BodyProprioceptiveConsequence,
    terminal: BodyProprioceptorTerminal,
) -> Vec<u8> {
    let mut output = EVIDENCE_MAGIC.to_vec();
    output.extend_from_slice(&source_tick.to_le_bytes());
    output.extend_from_slice(&successor_tick.to_le_bytes());
    output.push(consequence.axis as u8);
    output.push(terminal.direction() as u8);
    output.extend_from_slice(&consequence.predecessor_position.to_le_bytes());
    output.extend_from_slice(&consequence.successor_position.to_le_bytes());
    output.extend_from_slice(&consequence.signed_displacement.to_le_bytes());
    output.extend_from_slice(&consequence.toward_minimum_carriers.to_le_bytes());
    output.extend_from_slice(&consequence.toward_maximum_carriers.to_le_bytes());
    output.extend_from_slice(&consequence.opposed_carriers_per_terminal.to_le_bytes());
    output.extend_from_slice(&consequence.applied_displacement_quanta.to_le_bytes());
    output.extend_from_slice(&consequence.stalled_carriers.to_le_bytes());
    output
}

fn u32_value(output: &mut Vec<u8>, value: usize) -> Result<(), ArticulatedBodyJointSourceError> {
    output.extend_from_slice(
        &u32::try_from(value)
            .map_err(|_| ArticulatedBodyJointSourceError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

fn text(output: &mut Vec<u8>, value: &str) -> Result<(), ArticulatedBodyJointSourceError> {
    output.extend_from_slice(
        &u16::try_from(value.len())
            .map_err(|_| ArticulatedBodyJointSourceError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    output.extend_from_slice(value.as_bytes());
    Ok(())
}

fn bytes(output: &mut Vec<u8>, value: &[u8]) -> Result<(), ArticulatedBodyJointSourceError> {
    if value.is_empty() {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    u32_value(output, value.len())?;
    output.extend_from_slice(value);
    Ok(())
}

fn rational(
    output: &mut Vec<u8>,
    value: &BigRational,
) -> Result<(), ArticulatedBodyJointSourceError> {
    text(output, &value.numer().to_string())?;
    text(output, &value.denom().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::virtual_articulated_body::{
        settle_body_effector_drives, AdmittedBodyEffectorDrives, ArticulatedBodyState, BodyAxis,
        BodyEffectorDrive, BodyEffectorTerminal, BODY_SETTLEMENT_CLOCK_MICROSECONDS,
    };

    #[test]
    fn sparse_body_consequence_becomes_typed_antagonist_proprioception() {
        let terminal = BodyEffectorTerminal::new(
            BodyAxis::LeftElbowFlexion,
            BodyEffectorDirection::TowardMaximum,
        );
        let transition = settle_body_effector_drives(
            &ArticulatedBodyState::at_neutral(),
            &AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
                terminal,
                outward_elementary_carriers: 10,
            }])
            .unwrap(),
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .unwrap();
        let episode = admit_articulated_body_proprioceptive_source(
            42,
            &transition.proprioceptive_consequences,
        )
        .unwrap();
        assert_eq!(&episode.joint_source_body()[..8], b"GLJSRC03");
        assert_eq!(episode.joint_source_ports().len(), 2);
        assert_eq!(episode.joint_source_occurrences().len(), 1);
        assert_eq!(
            episode.joint_source_ports()[0]
                .body_proprioceptor_terminal
                .unwrap()
                .axis(),
            BodyAxis::LeftElbowFlexion
        );
        assert_eq!(
            episode.joint_source_ports()[1].body_proprioceptor_terminal,
            Some(BodyProprioceptorTerminal::new(
                BodyAxis::LeftElbowFlexion,
                BodyEffectorDirection::TowardMaximum,
            ))
        );
    }

    #[test]
    fn anatomical_stop_becomes_a_distinct_exact_load_ending() {
        let terminal = BodyEffectorTerminal::new(
            BodyAxis::LeftGripAperture,
            BodyEffectorDirection::TowardMaximum,
        );
        let reach_stop = settle_body_effector_drives(
            &ArticulatedBodyState::at_neutral(),
            &AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
                terminal,
                outward_elementary_carriers: 100_000,
            }])
            .unwrap(),
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .unwrap();
        let stopped = settle_body_effector_drives(
            &reach_stop.successor,
            &AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
                terminal,
                outward_elementary_carriers: 240,
            }])
            .unwrap(),
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .unwrap();
        let episode =
            admit_articulated_body_consequence_source(43, &stopped.proprioceptive_consequences)
                .unwrap();
        assert_eq!(&episode.joint_source_body()[..8], b"GLJSRC04");
        assert_eq!(episode.joint_source_ports().len(), 4);
        assert_eq!(episode.joint_source_occurrences().len(), 1);
        assert_eq!(
            episode.joint_source_ports()[0].coordinates[0].axis_id,
            "body-antagonist-proprioceptor-terminal"
        );
        assert_eq!(
            episode.joint_source_ports()[2].coordinates[0].axis_id,
            "body-effector-load-terminal"
        );
        let toward_minimum_load = &episode.joint_source_ports()[2];
        let toward_maximum_load = &episode.joint_source_ports()[3];
        assert_eq!(
            toward_minimum_load.physical_quantity,
            EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
        );
        assert_eq!(
            toward_maximum_load.topology_index,
            u32::try_from(
                BodyProprioceptorTerminal::new(terminal.axis(), terminal.direction())
                    .load_topology_index(),
            )
            .unwrap()
        );
        assert_eq!(
            toward_minimum_load.exact_normalized_sources,
            vec![BigRational::zero(), BigRational::zero()]
        );
        assert_eq!(
            toward_maximum_load.exact_normalized_sources,
            vec![BigRational::one(), BigRational::one()]
        );
    }

    #[test]
    fn exact_body_evidence_names_only_the_effector_that_moved_the_axis() {
        let terminal = BodyEffectorTerminal::new(
            BodyAxis::VocalTractSection3Area,
            BodyEffectorDirection::TowardMaximum,
        );
        let transition = settle_body_effector_drives(
            &ArticulatedBodyState::at_neutral(),
            &AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
                terminal,
                outward_elementary_carriers: 7,
            }])
            .unwrap(),
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .unwrap();
        let episode =
            admit_articulated_body_consequence_source(44, &transition.proprioceptive_consequences)
                .unwrap();

        let mut moved = episode
            .joint_source_ports()
            .iter()
            .map(exact_moved_effector_terminal)
            .collect::<Result<Vec<_>, _>>()
            .unwrap()
            .into_iter()
            .flatten()
            .collect::<Vec<_>>();
        moved.sort_unstable();
        moved.dedup();

        assert_eq!(moved, vec![terminal]);
    }

    #[test]
    fn exact_body_evidence_refuses_coincidence_and_corruption() {
        let axis = BodyAxis::VocalTractSection3Area;
        let transition = settle_body_effector_drives(
            &ArticulatedBodyState::at_neutral(),
            &AdmittedBodyEffectorDrives::admit(vec![
                BodyEffectorDrive {
                    terminal: BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum),
                    outward_elementary_carriers: 7,
                },
                BodyEffectorDrive {
                    terminal: BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMaximum),
                    outward_elementary_carriers: 7,
                },
            ])
            .unwrap(),
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .unwrap();
        let episode =
            admit_articulated_body_consequence_source(45, &transition.proprioceptive_consequences)
                .unwrap();
        assert!(episode
            .joint_source_ports()
            .iter()
            .map(exact_moved_effector_terminal)
            .collect::<Result<Vec<_>, _>>()
            .unwrap()
            .into_iter()
            .all(|terminal| terminal.is_none()));

        let mut corrupted = episode.joint_source_ports()[0].clone();
        corrupted.input_map_profile[24] = BodyAxis::JawOpening as u8;
        assert_eq!(
            exact_moved_effector_terminal(&corrupted),
            Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences)
        );
    }

    #[test]
    fn passive_tissue_return_is_sensed_but_never_named_as_a_motor_cause() {
        let axis = BodyAxis::GlottalAperture;
        let neutral = ArticulatedBodyState::at_neutral();
        let mut axes = *neutral.axes();
        axes[axis.index()] = axis.anatomy().minimum;
        let predecessor =
            ArticulatedBodyState::from_physical_state(axes, neutral.lung_air_microlitres(), true)
                .unwrap();
        let transition = settle_body_effector_drives(
            &predecessor,
            &AdmittedBodyEffectorDrives::quiescent(),
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .unwrap();
        assert!(transition.proprioceptive_consequences[0].signed_displacement > 0);
        let episode =
            admit_articulated_body_consequence_source(46, &transition.proprioceptive_consequences)
                .unwrap();
        assert!(episode
            .joint_source_ports()
            .iter()
            .map(exact_moved_effector_terminal)
            .collect::<Result<Vec<_>, _>>()
            .unwrap()
            .into_iter()
            .all(|terminal| terminal.is_none()));
    }

    #[test]
    fn empty_or_reordered_consequences_are_refused() {
        assert!(matches!(
            admit_articulated_body_proprioceptive_source(0, &[]),
            Err(ArticulatedBodyJointSourceError::EmptyConsequences)
        ));
    }

    #[test]
    fn complete_neutral_body_source_has_one_stable_pair_per_axis() {
        let episode =
            admit_complete_articulated_body_state_source(7, &ArticulatedBodyState::at_neutral())
                .unwrap();
        assert_eq!(episode.joint_source_ports().len(), BODY_AXES.len() * 2);
        assert_eq!(episode.joint_source_occurrences().len(), BODY_AXES.len());
        for (ordinal, port) in episode.joint_source_ports().iter().enumerate() {
            let terminal = port.body_proprioceptor_terminal.unwrap();
            assert_eq!(
                port.topology_index,
                u32::try_from(terminal.proprioceptor_topology_index()).unwrap()
            );
            assert_eq!(terminal.ordinal(), ordinal);
        }
        let torso_minimum = &episode.joint_source_ports()[0].exact_normalized_sources;
        let torso_maximum = &episode.joint_source_ports()[1].exact_normalized_sources;
        assert_eq!(torso_minimum[0], BigRational::new(2.into(), 5.into()));
        assert_eq!(torso_maximum[0], BigRational::new(3.into(), 5.into()));
        assert_eq!(torso_minimum[0], torso_minimum[1]);
        assert_eq!(torso_maximum[0], torso_maximum[1]);
        assert_eq!(&torso_minimum[0] + &torso_maximum[0], BigRational::one());
    }
}
