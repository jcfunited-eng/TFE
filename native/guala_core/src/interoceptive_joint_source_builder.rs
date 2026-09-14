//! Metabolic-need interoception source (drive organ stage 2, 2026-09-13).
//!
//! One exact interval of the organism's own reserve state as two body-sense
//! receptor ports at their own declared places (196, 197 — the next body
//! places after the added tract endings): the share of usable material that
//! is spent and awaiting recovery, and the share of material sitting as heat.
//! Both are exact fractions in [0, 1], held across the interval like every
//! tonic body afference. This is a distinct organ like the root endings: its
//! own source kind, its own places, the thermoreceptor-class transduction law.
//! No set point, hunger label, preference, action, or semantic identity.

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{One, ToPrimitive, Zero};

use crate::joint_source_episode::{
    decode_native_joint_source_episode, NativeJointSourceEpisode, INTEROCEPTIVE_MAGIC,
    INTEROCEPTIVE_VERSION,
};
use crate::joint_uf_source_adapter::SAMPLED_VOLUME_AND_RELEVANCE_PIECEWISE_LINEAR_PROFILE;
use crate::thermal_receptor_work::{
    INTEROCEPTOR_REFERENCE_INTERVAL_UNIT, INTEROCEPTOR_RESERVE_DEFICIT_QUANTITY,
    INTEROCEPTOR_THERMAL_LOAD_QUANTITY,
};
use crate::virtual_articulated_body::ADDED_BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET;

/// Body-sense places 0..9 (displacement, articulation, thermal), the fixed
/// antagonist/load/root/added tract endings up to 195: the interoceptors begin
/// at the next declared place. Fixed anatomy, not a runtime offset.
pub(crate) const INTEROCEPTOR_TOPOLOGY_OFFSET: usize =
    ADDED_BODY_EFFECTOR_LOAD_TOPOLOGY_OFFSET + 16;
pub(crate) const INTEROCEPTOR_PORT_COUNT: usize = 2;
const TICKS_PER_SECOND: u64 = 1_000;
/// One admitted native interval: 250 ms on the shared physical clock.
const INTERVAL_TICKS: u64 = 250;
const PORT_RELEVANCE: &str = "exact-unit-source-relevance.v1";
const JOINT_RELEVANCE: &[u8] = b"guala.metabolic_need.interoceptors.present.r(t)=1.exact.v1";
const INPUT_MAP: &str = "signed-unit-affine-v1";
/// The one declared sensor id of both interoceptive ports; the formation's
/// rooting reflex identifies the reserve-deficit receptor site by it.
pub(crate) const INTEROCEPTOR_SENSOR_ID: &str = "organism-metabolic-interoceptors";

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum InteroceptiveSourceError {
    SourceTickOverflow,
    FractionOutsideUnitInterval,
    ArithmeticWidth,
    Carrier(String),
}

/// Build the interoceptive episode for the interval that starts at
/// `source_tick`. Both fractions are the organism's own exact reserve state,
/// already narrowed by the caller to the binary64 the receptor receives.
pub(crate) fn admit_interoceptive_source(
    source_tick: u64,
    reserve_deficit: BigRational,
    thermal_load: BigRational,
) -> Result<NativeJointSourceEpisode, InteroceptiveSourceError> {
    for value in [&reserve_deficit, &thermal_load] {
        if *value < BigRational::zero() || *value > BigRational::one() {
            return Err(InteroceptiveSourceError::FractionOutsideUnitInterval);
        }
    }
    let end_tick = source_tick
        .checked_add(INTERVAL_TICKS)
        .ok_or(InteroceptiveSourceError::SourceTickOverflow)?;
    // The shared physical clock of one admitted interval: 0 to 250 ms, like
    // every per-interval sensory source; the tick lives in the evidence.
    let times = [
        BigRational::zero(),
        BigRational::new(BigInt::from(INTERVAL_TICKS), BigInt::from(TICKS_PER_SECOND)),
    ];
    let mut output = INTEROCEPTIVE_MAGIC.to_vec();
    output.extend_from_slice(&INTEROCEPTIVE_VERSION.to_le_bytes());
    text(&mut output, "metabolic-need-interoceptive-interval")?;
    output.extend_from_slice(&[1, 1, 1, 1, 1, 0]);
    u32_value(&mut output, INTEROCEPTOR_PORT_COUNT)?;
    let ports = [
        (
            0usize,
            "metabolic-need-reserve-deficit",
            "whole-organism-recovery-reserves",
            INTEROCEPTOR_RESERVE_DEFICIT_QUANTITY,
            &reserve_deficit,
        ),
        (
            1usize,
            "metabolic-need-thermal-load",
            "whole-organism-thermal-reserves",
            INTEROCEPTOR_THERMAL_LOAD_QUANTITY,
            &thermal_load,
        ),
    ];
    for (ordinal, stream, compartment, quantity, value) in ports {
        output.push(5);
        u32_value(
            &mut output,
            INTEROCEPTOR_TOPOLOGY_OFFSET
                .checked_add(ordinal)
                .ok_or(InteroceptiveSourceError::ArithmeticWidth)?,
        )?;
        text(&mut output, INTEROCEPTOR_SENSOR_ID)?;
        text(&mut output, stream)?;
        output.extend_from_slice(&2_u16.to_le_bytes());
        text(&mut output, "body-compartment")?;
        text(&mut output, compartment)?;
        text(&mut output, "reference-interval")?;
        text(&mut output, "0-to-1-fraction-of-declared-capacity")?;
        text(&mut output, quantity)?;
        text(&mut output, INTEROCEPTOR_REFERENCE_INTERVAL_UNIT)?;
        text(&mut output, PORT_RELEVANCE)?;
        text(&mut output, "")?;
        text(&mut output, INPUT_MAP)?;
        // Source interval 0..1, field offset 0, field scale 1: the exact
        // dimensionless field IS the fraction, and the binary64 signal is the
        // same value (the caller already narrowed it to binary64, so the
        // projection is exact).
        rational(&mut output, &BigRational::zero())?;
        rational(&mut output, &BigRational::one())?;
        rational(&mut output, &BigRational::zero())?;
        rational(&mut output, &BigRational::one())?;
        let mut evidence = b"GLNDEV01".to_vec();
        evidence.extend_from_slice(&source_tick.to_le_bytes());
        evidence.extend_from_slice(&end_tick.to_le_bytes());
        evidence.push(ordinal as u8);
        bytes(&mut output, &evidence)?;
        u32_value(&mut output, 2)?;
        let signal = value
            .to_f64()
            .ok_or(InteroceptiveSourceError::ArithmeticWidth)?;
        for time in &times {
            rational(&mut output, time)?;
            output.extend_from_slice(&signal.to_bits().to_le_bytes());
            rational(&mut output, &BigRational::zero())?;
            rational(&mut output, &BigRational::one())?;
            rational(&mut output, value)?;
        }
    }
    u32_value(&mut output, 1)?;
    u32_value(&mut output, INTEROCEPTOR_PORT_COUNT)?;
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
    u32_value(&mut output, INTEROCEPTOR_PORT_COUNT)?;
    u32_value(&mut output, 0)?;
    u32_value(&mut output, 1)?;
    bytes(&mut output, JOINT_RELEVANCE)?;
    u32_value(&mut output, 2)?;
    rational(&mut output, &BigRational::one())?;
    rational(&mut output, &BigRational::one())?;
    decode_native_joint_source_episode(&output, INTEROCEPTOR_PORT_COUNT, 4, 1, 2)
        .map_err(InteroceptiveSourceError::Carrier)
}

fn u32_value(output: &mut Vec<u8>, value: usize) -> Result<(), InteroceptiveSourceError> {
    output.extend_from_slice(
        &u32::try_from(value)
            .map_err(|_| InteroceptiveSourceError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    Ok(())
}

fn text(output: &mut Vec<u8>, value: &str) -> Result<(), InteroceptiveSourceError> {
    let body = value.as_bytes();
    output.extend_from_slice(
        &u16::try_from(body.len())
            .map_err(|_| InteroceptiveSourceError::ArithmeticWidth)?
            .to_le_bytes(),
    );
    output.extend_from_slice(body);
    Ok(())
}

fn bytes(output: &mut Vec<u8>, value: &[u8]) -> Result<(), InteroceptiveSourceError> {
    u32_value(output, value.len())?;
    output.extend_from_slice(value);
    Ok(())
}

fn rational(output: &mut Vec<u8>, value: &BigRational) -> Result<(), InteroceptiveSourceError> {
    text(output, &value.numer().to_string())?;
    text(output, &value.denom().to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn interoceptive_source_declares_two_body_ports_at_their_own_places() {
        let deficit = BigRational::new(BigInt::from(1), BigInt::from(4));
        let load = BigRational::new(BigInt::from(3), BigInt::from(64));
        let episode = admit_interoceptive_source(705364, deficit.clone(), load.clone()).unwrap();
        assert_eq!(&episode.joint_source_body()[..8], INTEROCEPTIVE_MAGIC);
        let ports = episode.joint_source_ports();
        assert_eq!(ports.len(), 2);
        assert_eq!(ports[0].sense, 5);
        assert_eq!(ports[0].topology_index as usize, INTEROCEPTOR_TOPOLOGY_OFFSET);
        assert_eq!(ports[1].topology_index as usize, INTEROCEPTOR_TOPOLOGY_OFFSET + 1);
        assert_eq!(ports[0].physical_quantity, INTEROCEPTOR_RESERVE_DEFICIT_QUANTITY);
        assert_eq!(ports[1].physical_quantity, INTEROCEPTOR_THERMAL_LOAD_QUANTITY);
        assert_eq!(ports[0].physical_unit, INTEROCEPTOR_REFERENCE_INTERVAL_UNIT);
        assert_eq!(ports[0].exact_normalized_sources, vec![deficit.clone(), deficit]);
        assert_eq!(ports[1].exact_normalized_sources, vec![load.clone(), load]);
        assert!(admit_interoceptive_source(1, BigRational::new(BigInt::from(3), BigInt::from(2)), BigRational::zero()).is_err());
    }
}
