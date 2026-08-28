//! Exact directional proprioception for one settled world-root translation.
//!
//! Four fixed endings report the signed x/y displacement that the world
//! actually applied. They do not carry a requested destination or infer an
//! action from metadata.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, Zero};

use crate::joint_source_episode::{decode_native_joint_source_episode, NativeJointSourceEpisode};
use crate::joint_uf_source_adapter::SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE;
use crate::proprioceptive_receptor_work::{
    ROOT_TRANSLATION_DIRECTIONAL_MOTION_QUANTITY, ROOT_TRANSLATION_DIRECTIONAL_MOTION_UNIT,
};
use crate::root_translation_terminal::{
    RootTranslationAxis, RootTranslationDirection, RootTranslationProprioceptorTerminal,
    ROOT_TRANSLATION_PROPRIOCEPTOR_TOPOLOGY_OFFSET,
};

const VERSION: u16 = 6;
const TICKS_PER_SECOND: u64 = 1_000;
const PORT_RELEVANCE: &str =
    "guala.root_translation.directional_ending.present.r(t)=1.exact.v1";
const JOINT_RELEVANCE: &[u8] =
    b"guala.root_translation.antagonist_pairs.present.r(t)=1.exact.v1";
const INPUT_MAP: &str = "root-translation-directional-motion-presence-v1";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum RootTranslationJointSourceError {
    SourceTickOverflow,
    QuiescentMotion,
    ArithmeticWidth,
    Carrier(String),
}

pub(crate) fn admit_root_translation_proprioceptive_source(
    source_tick: u64,
    signed_x_millimetres: i32,
    signed_y_millimetres: i32,
) -> Result<NativeJointSourceEpisode, RootTranslationJointSourceError> {
    if signed_x_millimetres == 0 && signed_y_millimetres == 0 {
        return Err(RootTranslationJointSourceError::QuiescentMotion);
    }
    let successor_tick = source_tick
        .checked_add(1)
        .ok_or(RootTranslationJointSourceError::SourceTickOverflow)?;
    let times = [
        BigRational::new(BigInt::from(source_tick), BigInt::from(TICKS_PER_SECOND)),
        BigRational::new(BigInt::from(successor_tick), BigInt::from(TICKS_PER_SECOND)),
    ];

    let mut output = b"GLJSRC06".to_vec();
    output.extend_from_slice(&VERSION.to_le_bytes());
    text(&mut output, "root-translation-proprioceptive-interval")?;
    output.extend_from_slice(&[1, 1, 1, 1, 1, 0]);
    u32_value(&mut output, 4)?;
    for axis in [RootTranslationAxis::X, RootTranslationAxis::Y] {
        let signed = match axis {
            RootTranslationAxis::X => signed_x_millimetres,
            RootTranslationAxis::Y => signed_y_millimetres,
        };
        for direction in [
            RootTranslationDirection::Negative,
            RootTranslationDirection::Positive,
        ] {
            let terminal = RootTranslationProprioceptorTerminal::new(axis, direction);
            output.push(5);
            u32_value(
                &mut output,
                ROOT_TRANSLATION_PROPRIOCEPTOR_TOPOLOGY_OFFSET
                    .checked_add(terminal.ordinal())
                    .ok_or(RootTranslationJointSourceError::ArithmeticWidth)?,
            )?;
            output.push(1);
            output.push(axis as u8);
            output.push(direction as u8);
            text(&mut output, "root-translation-proprioceptors")?;
            text(
                &mut output,
                match (axis, direction) {
                    (RootTranslationAxis::X, RootTranslationDirection::Negative) => {
                        "x-negative-directional-ending"
                    }
                    (RootTranslationAxis::X, RootTranslationDirection::Positive) => {
                        "x-positive-directional-ending"
                    }
                    (RootTranslationAxis::Y, RootTranslationDirection::Negative) => {
                        "y-negative-directional-ending"
                    }
                    (RootTranslationAxis::Y, RootTranslationDirection::Positive) => {
                        "y-positive-directional-ending"
                    }
                },
            )?;
            output.extend_from_slice(&1_u16.to_le_bytes());
            text(&mut output, "world-root-translation")?;
            text(&mut output, "directional-motion-ending")?;
            text(&mut output, ROOT_TRANSLATION_DIRECTIONAL_MOTION_QUANTITY)?;
            text(&mut output, ROOT_TRANSLATION_DIRECTIONAL_MOTION_UNIT)?;
            text(&mut output, PORT_RELEVANCE)?;
            text(&mut output, "")?;
            text(&mut output, INPUT_MAP)?;
            rational(&mut output, &BigRational::zero())?;
            rational(&mut output, &BigRational::one())?;
            rational(&mut output, &BigRational::zero())?;
            rational(&mut output, &BigRational::one())?;
            let mut evidence = b"GLRTEV01".to_vec();
            evidence.extend_from_slice(&source_tick.to_le_bytes());
            evidence.extend_from_slice(&successor_tick.to_le_bytes());
            evidence.extend_from_slice(&signed_x_millimetres.to_le_bytes());
            evidence.extend_from_slice(&signed_y_millimetres.to_le_bytes());
            evidence.push(axis as u8);
            evidence.push(direction as u8);
            bytes(&mut output, &evidence)?;
            u32_value(&mut output, 2)?;
            for (index, time) in times.iter().enumerate() {
                let present = index == 1
                    && signed != 0
                    && ((signed.is_negative()
                        && direction == RootTranslationDirection::Negative)
                        || (signed.is_positive()
                            && direction == RootTranslationDirection::Positive));
                let exact = if present {
                    BigRational::one()
                } else {
                    BigRational::zero()
                };
                rational(&mut output, time)?;
                output.extend_from_slice(
                    &(if present { 1.0_f64 } else { 0.0_f64 })
                        .to_bits()
                        .to_le_bytes(),
                );
                rational(&mut output, &BigRational::zero())?;
                rational(&mut output, &BigRational::one())?;
                rational(&mut output, &exact)?;
            }
        }
    }
    u32_value(&mut output, 1)?;
    u32_value(&mut output, 4)?;
    for port in 0..4 {
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
    for port in 0..4 {
        u32_value(&mut output, port)?;
    }
    bytes(&mut output, JOINT_RELEVANCE)?;
    u32_value(&mut output, 2)?;
    rational(&mut output, &BigRational::one())?;
    rational(&mut output, &BigRational::one())?;

    decode_native_joint_source_episode(&output, 4, 8, 1, 2)
        .map_err(RootTranslationJointSourceError::Carrier)
}

fn u32_value(
    output: &mut Vec<u8>,
    value: usize,
) -> Result<(), RootTranslationJointSourceError> {
    output.extend_from_slice(
        &u32::try_from(value)
            .map_err(|_| RootTranslationJointSourceError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

fn text(
    output: &mut Vec<u8>,
    value: &str,
) -> Result<(), RootTranslationJointSourceError> {
    output.extend_from_slice(
        &u16::try_from(value.len())
            .map_err(|_| RootTranslationJointSourceError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    output.extend_from_slice(value.as_bytes());
    Ok(())
}

fn bytes(
    output: &mut Vec<u8>,
    value: &[u8],
) -> Result<(), RootTranslationJointSourceError> {
    if value.is_empty() {
        return Err(RootTranslationJointSourceError::ArithmeticWidth);
    }
    u32_value(output, value.len())?;
    output.extend_from_slice(value);
    Ok(())
}

fn rational(
    output: &mut Vec<u8>,
    value: &BigRational,
) -> Result<(), RootTranslationJointSourceError> {
    text(output, &value.numer().to_string())?;
    text(output, &value.denom().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_translation_source_marks_only_the_two_moved_directional_endings() {
        let source = admit_root_translation_proprioceptive_source(41, 3, -2).unwrap();
        assert_eq!(source.joint_source_ports().len(), 4);
        let successors = source
            .joint_source_ports()
            .iter()
            .map(|port| port.exact_normalized_sources[1].clone())
            .collect::<Vec<_>>();
        assert_eq!(
            successors,
            vec![
                BigRational::zero(),
                BigRational::one(),
                BigRational::one(),
                BigRational::zero(),
            ]
        );
        for port in source.joint_source_ports() {
            assert!(port.root_translation_proprioceptor_terminal.is_some());
        }
    }

    #[test]
    fn quiescent_translation_has_no_invented_source() {
        assert!(matches!(
            admit_root_translation_proprioceptive_source(41, 0, 0),
            Err(RootTranslationJointSourceError::QuiescentMotion)
        ));
    }
}
