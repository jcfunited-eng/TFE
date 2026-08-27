//! Exact directional proprioception for one settled world-root yaw.
//!
//! The vestibular canal remains its own specialized receptor.  These two
//! fixed antagonist endings report only which root-yaw direction physically
//! moved during the interval, so developmental motor anatomy never infers
//! direction from a label, topology parity, or transient sign.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Zero};

use crate::joint_source_episode::{decode_native_joint_source_episode, NativeJointSourceEpisode};
use crate::joint_uf_source_adapter::SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE;
use crate::proprioceptive_receptor_work::{
    ROOT_YAW_DIRECTIONAL_MOTION_QUANTITY, ROOT_YAW_DIRECTIONAL_MOTION_UNIT,
};
use crate::virtual_body_yaw_motion::{
    RootYawDirection, RootYawProprioceptorTerminal,
    ROOT_YAW_PROPRIOCEPTOR_TOPOLOGY_OFFSET,
};

const VERSION: u16 = 5;
const TICKS_PER_SECOND: u64 = 1_000;
const PORT_RELEVANCE: &str = "guala.root_yaw.directional_ending.present.r(t)=1.exact.v1";
const JOINT_RELEVANCE: &[u8] = b"guala.root_yaw.antagonist_pair.present.r(t)=1.exact.v1";
const INPUT_MAP: &str = "root-yaw-directional-motion-presence-v1";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum RootYawJointSourceError {
    SourceTickOverflow,
    QuiescentMotion,
    ArithmeticWidth,
    Carrier(String),
}

pub(crate) fn admit_root_yaw_proprioceptive_source(
    source_tick: u64,
    signed_displacement_millidegrees: i32,
) -> Result<NativeJointSourceEpisode, RootYawJointSourceError> {
    if signed_displacement_millidegrees == 0 {
        return Err(RootYawJointSourceError::QuiescentMotion);
    }
    let successor_tick = source_tick
        .checked_add(1)
        .ok_or(RootYawJointSourceError::SourceTickOverflow)?;
    let times = [
        BigRational::new(BigInt::from(source_tick), BigInt::from(TICKS_PER_SECOND)),
        BigRational::new(BigInt::from(successor_tick), BigInt::from(TICKS_PER_SECOND)),
    ];
    let moved_direction = if signed_displacement_millidegrees.is_negative() {
        RootYawDirection::Negative
    } else {
        RootYawDirection::Positive
    };

    let mut output = b"GLJSRC05".to_vec();
    output.extend_from_slice(&VERSION.to_le_bytes());
    text(&mut output, "root-yaw-proprioceptive-interval")?;
    output.extend_from_slice(&[1, 1, 1, 1, 1, 0]);
    u32_value(&mut output, 2)?;
    for direction in [RootYawDirection::Negative, RootYawDirection::Positive] {
        let terminal = RootYawProprioceptorTerminal::new(direction);
        output.push(5);
        u32_value(
            &mut output,
            ROOT_YAW_PROPRIOCEPTOR_TOPOLOGY_OFFSET
                .checked_add(terminal.ordinal())
                .ok_or(RootYawJointSourceError::ArithmeticWidth)?,
        )?;
        output.push(1);
        output.push(direction as u8);
        text(&mut output, "root-yaw-proprioceptors")?;
        text(
            &mut output,
            match direction {
                RootYawDirection::Negative => "negative-directional-ending",
                RootYawDirection::Positive => "positive-directional-ending",
            },
        )?;
        output.extend_from_slice(&1_u16.to_le_bytes());
        text(&mut output, "world-root-yaw")?;
        text(&mut output, "directional-motion-ending")?;
        text(&mut output, ROOT_YAW_DIRECTIONAL_MOTION_QUANTITY)?;
        text(&mut output, ROOT_YAW_DIRECTIONAL_MOTION_UNIT)?;
        text(&mut output, PORT_RELEVANCE)?;
        text(&mut output, "")?;
        text(&mut output, INPUT_MAP)?;
        rational(&mut output, &BigRational::zero())?;
        rational(&mut output, &BigRational::one())?;
        rational(&mut output, &BigRational::zero())?;
        rational(&mut output, &BigRational::one())?;
        let mut evidence = b"GLRYEV01".to_vec();
        evidence.extend_from_slice(&source_tick.to_le_bytes());
        evidence.extend_from_slice(&successor_tick.to_le_bytes());
        evidence.extend_from_slice(&signed_displacement_millidegrees.to_le_bytes());
        evidence.push(direction as u8);
        bytes(&mut output, &evidence)?;
        u32_value(&mut output, 2)?;
        for (index, time) in times.iter().enumerate() {
            let present = index == 1 && direction == moved_direction;
            let exact = if present {
                BigRational::one()
            } else {
                BigRational::zero()
            };
            rational(&mut output, time)?;
            output.extend_from_slice(&(if present { 1.0_f64 } else { 0.0_f64 }).to_bits().to_le_bytes());
            rational(&mut output, &BigRational::zero())?;
            rational(&mut output, &BigRational::one())?;
            rational(&mut output, &exact)?;
        }
    }
    u32_value(&mut output, 1)?;
    u32_value(&mut output, 2)?;
    u32_value(&mut output, 0)?;
    u32_value(&mut output, 1)?;
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

    decode_native_joint_source_episode(&output, 2, 4, 1, 2)
        .map_err(RootYawJointSourceError::Carrier)
}

fn u32_value(output: &mut Vec<u8>, value: usize) -> Result<(), RootYawJointSourceError> {
    output.extend_from_slice(
        &u32::try_from(value)
            .map_err(|_| RootYawJointSourceError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

fn text(output: &mut Vec<u8>, value: &str) -> Result<(), RootYawJointSourceError> {
    output.extend_from_slice(
        &u16::try_from(value.len())
            .map_err(|_| RootYawJointSourceError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    output.extend_from_slice(value.as_bytes());
    Ok(())
}

fn bytes(output: &mut Vec<u8>, value: &[u8]) -> Result<(), RootYawJointSourceError> {
    if value.is_empty() {
        return Err(RootYawJointSourceError::ArithmeticWidth);
    }
    u32_value(output, value.len())?;
    output.extend_from_slice(value);
    Ok(())
}

fn rational(output: &mut Vec<u8>, value: &BigRational) -> Result<(), RootYawJointSourceError> {
    text(output, &value.numer().to_string())?;
    text(output, &value.denom().to_string())
}
