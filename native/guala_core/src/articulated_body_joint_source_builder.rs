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

use crate::joint_source_episode::{decode_native_joint_source_episode, NativeJointSourceEpisode};
use crate::joint_uf_source_adapter::SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE;
use crate::proprioceptive_receptor_work::{
    ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY, ARTICULATED_AXIS_SPAN_FRACTION_UNIT,
    DISCHARGED_EFFECTOR_CARRIER_FRACTION_UNIT, EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY,
};
use crate::virtual_articulated_body::{
    ArticulatedBodyState, BodyEffectorDirection, BodyProprioceptiveConsequence,
    BodyProprioceptorTerminal, BODY_AXES, BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET,
    BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET,
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

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum ArticulatedBodyJointSourceError {
    SourceTickOverflow,
    EmptyConsequences,
    NoncanonicalConsequences,
    ArithmeticWidth,
    NonFiniteCoordinate,
    Carrier(String),
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
            u32_value(
                &mut output,
                BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET
                    .checked_add(terminal.ordinal())
                    .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?,
            )?;
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
                let exact = normalized_antagonist_length(consequence, position, direction)?;
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
    if consequences.windows(2).any(|pair| pair[0].axis >= pair[1].axis) {
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
                output.push(5);
                let topology_offset = if load_ending {
                    BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET
                } else {
                    BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET
                };
                u32_value(
                    &mut output,
                    topology_offset
                        .checked_add(terminal.ordinal())
                        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?,
                )?;
                output.push(1);
                output.push(
                    u8::try_from(consequence.axis.index())
                        .map_err(|_| ArticulatedBodyJointSourceError::ArithmeticWidth)?,
                );
                output.push(direction as u8);
                text(
                    &mut output,
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
                    &mut output,
                    &if load_ending {
                        format!("{}-{direction_name}-load", consequence.axis.anatomical_name())
                    } else {
                        format!("{}-{direction_name}", consequence.axis.anatomical_name())
                    },
                )?;
                output.extend_from_slice(&1_u16.to_le_bytes());
                text(
                    &mut output,
                    if load_ending {
                        "body-effector-load-terminal"
                    } else {
                        // GLJSRC04 extends the occurrence with load endings;
                        // it does not rename the already-mounted GLJSRC03
                        // length receptor.
                        "body-antagonist-proprioceptor-terminal"
                    },
                )?;
                text(&mut output, &terminal.ordinal().to_string())?;
                text(
                    &mut output,
                    if load_ending {
                        EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
                    } else {
                        ANTAGONIST_PROPRIOCEPTOR_LENGTH_QUANTITY
                    },
                )?;
                text(
                    &mut output,
                    if load_ending {
                        DISCHARGED_EFFECTOR_CARRIER_FRACTION_UNIT
                    } else {
                        ARTICULATED_AXIS_SPAN_FRACTION_UNIT
                    },
                )?;
                text(
                    &mut output,
                    if load_ending { LOAD_PORT_RELEVANCE } else { PORT_RELEVANCE },
                )?;
                text(&mut output, "")?;
                text(&mut output, if load_ending { LOAD_INPUT_MAP } else { INPUT_MAP })?;
                rational(&mut output, &BigRational::zero())?;
                rational(&mut output, &BigRational::one())?;
                rational(&mut output, &BigRational::zero())?;
                rational(&mut output, &BigRational::one())?;
                let evidence = exact_evidence(source_tick, successor_tick, consequence, terminal);
                bytes(&mut output, &evidence)?;
                u32_value(&mut output, 2)?;
                let load = reactive_load_fraction(consequence, direction)?;
                for (time, position) in times.iter().zip([
                    consequence.predecessor_position,
                    consequence.successor_position,
                ]) {
                    let exact = if load_ending {
                        load.clone()
                    } else {
                        normalized_antagonist_length(consequence, position, direction)?
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
        bytes(&mut output, SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE)?;
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
    consequence: &BodyProprioceptiveConsequence,
    position: i32,
    direction: BodyEffectorDirection,
) -> Result<BigRational, ArticulatedBodyJointSourceError> {
    let anatomy = consequence.axis.anatomy();
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
        .checked_add(if carries_stall { consequence.stalled_carriers } else { 0 })
        .ok_or(ArticulatedBodyJointSourceError::ArithmeticWidth)?;
    if reacted > discharged {
        return Err(ArticulatedBodyJointSourceError::NoncanonicalConsequences);
    }
    Ok(BigRational::new(BigInt::from(reacted), BigInt::from(discharged)))
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
        BodyEffectorDrive, BodyEffectorTerminal,
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
        )
        .unwrap();
        let stopped = settle_body_effector_drives(
            &reach_stop.successor,
            &AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
                terminal,
                outward_elementary_carriers: 240,
            }])
            .unwrap(),
        )
        .unwrap();
        let episode = admit_articulated_body_consequence_source(
            43,
            &stopped.proprioceptive_consequences,
        )
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
            u32::try_from(BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET + terminal.ordinal()).unwrap()
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
            assert_eq!(
                port.topology_index,
                (BODY_PROPRIOCEPTOR_TOPOLOGY_OFFSET + ordinal) as u32
            );
            assert_eq!(port.body_proprioceptor_terminal.unwrap().ordinal(), ordinal);
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
