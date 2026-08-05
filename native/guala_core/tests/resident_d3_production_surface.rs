use guala_core::{
    create_native_resident_d3_genesis, decode_native_joint_source_episode,
    transition_native_resident_d3, HippocampalColdObject, HippocampalColdPort,
};
use std::collections::BTreeMap;

const IDENTITY: &str = "12345678-9abc-4def-8123-456789abcdef";
const ENVELOPE_BYTES: usize = 1_048_576;
const FABRIC_BYTES: usize = 1_048_000;

#[derive(Default)]
struct ExternalColdCustody {
    objects: BTreeMap<[u8; 32], Box<[u8]>>,
}

impl HippocampalColdPort for ExternalColdCustody {
    fn read_object(&self, address: [u8; 32]) -> Result<Option<Box<[u8]>>, String> {
        Ok(self.objects.get(&address).cloned())
    }

    fn publish_atomic(&mut self, objects: &[HippocampalColdObject]) -> Result<(), String> {
        for object in objects {
            if let Some(existing) = self.objects.get(&object.address()) {
                if existing.as_ref() != object.body() {
                    return Err("immutable cold object collision".to_owned());
                }
            }
        }
        for object in objects {
            self.objects
                .entry(object.address())
                .or_insert_with(|| object.body().to_vec().into_boxed_slice());
        }
        Ok(())
    }
}

fn text(output: &mut Vec<u8>, value: &str) {
    output.extend_from_slice(&u16::try_from(value.len()).unwrap().to_le_bytes());
    output.extend_from_slice(value.as_bytes());
}

fn rational(output: &mut Vec<u8>, numerator: i64, denominator: i64) {
    text(output, &numerator.to_string());
    text(output, &denominator.to_string());
}

fn source_port(output: &mut Vec<u8>, topology: u32, values: [(i64, f64); 2]) {
    output.push(0);
    output.extend_from_slice(&topology.to_le_bytes());
    text(output, &format!("retina-{topology}"));
    text(output, "luminance");
    output.extend_from_slice(&1_u16.to_le_bytes());
    text(output, "receptor");
    text(output, &topology.to_string());
    text(output, "light");
    text(output, "normalized");
    text(output, "direct");
    text(output, "");
    text(output, "affine");
    rational(output, -1, 1);
    rational(output, 1, 1);
    rational(output, 1, 1);
    rational(output, 1, 1);
    output.extend_from_slice(&1_u32.to_le_bytes());
    output.push(u8::try_from(topology).unwrap());
    output.extend_from_slice(&2_u32.to_le_bytes());
    for (time, signal) in values {
        rational(output, time, 1);
        output.extend_from_slice(&signal.to_bits().to_le_bytes());
        rational(output, 0, 1);
        rational(output, 1, 1);
        rational(output, (1.0 + signal) as i64, 1);
    }
}

fn source_occurrence(output: &mut Vec<u8>, port_index: u32) {
    output.extend_from_slice(&1_u32.to_le_bytes());
    output.extend_from_slice(&port_index.to_le_bytes());
    output.extend_from_slice(&2_u32.to_le_bytes());
    rational(output, 1, 1);
    rational(output, 2, 1);
    let intersample = b"guala.uf.v1.4.sampled_volume_and_relevance_piecewise_linear.v1";
    output.extend_from_slice(&u32::try_from(intersample.len()).unwrap().to_le_bytes());
    output.extend_from_slice(intersample);
    output.extend_from_slice(&1_u32.to_le_bytes());
    output.extend_from_slice(&1_u32.to_le_bytes());
    output.extend_from_slice(&0_u32.to_le_bytes());
    output.extend_from_slice(&1_u32.to_le_bytes());
    output.push(1);
    output.extend_from_slice(&2_u32.to_le_bytes());
    rational(output, 1, 1);
    rational(output, 1, 1);
}

fn exact_source(episode: &str, reverse: bool) -> guala_core::NativeJointSourceEpisode {
    let mut body = b"GLJSRC02".to_vec();
    body.extend_from_slice(&2_u16.to_le_bytes());
    text(&mut body, episode);
    body.extend_from_slice(&[0, 1, 1, 1, 1, 1]);
    body.extend_from_slice(&2_u32.to_le_bytes());
    let first = if reverse {
        [(1, 1.0), (2, 0.0)]
    } else {
        [(1, 0.0), (2, 1.0)]
    };
    let second = if reverse {
        [(1, 0.0), (2, 1.0)]
    } else {
        [(1, 1.0), (2, 0.0)]
    };
    source_port(&mut body, 0, first);
    source_port(&mut body, 1, second);
    body.extend_from_slice(&2_u32.to_le_bytes());
    source_occurrence(&mut body, 0);
    source_occurrence(&mut body, 1);
    decode_native_joint_source_episode(&body, 2, 4, 2, 4).unwrap()
}

#[test]
fn normal_library_surface_requires_external_cold_and_survives_restart() {
    let genesis =
        create_native_resident_d3_genesis(IDENTITY, 0, None, ENVELOPE_BYTES, FABRIC_BYTES).unwrap();
    let first_source = exact_source("production-d3-first", false);
    let absent = transition_native_resident_d3(
        genesis.clone(),
        &first_source,
        None,
        ENVELOPE_BYTES,
        FABRIC_BYTES,
    )
    .unwrap_err();
    assert_eq!(absent, "external hippocampal cold custody is required");

    let mut cold = ExternalColdCustody::default();
    let first = transition_native_resident_d3(
        genesis,
        &first_source,
        Some(&mut cold),
        ENVELOPE_BYTES,
        FABRIC_BYTES,
    )
    .unwrap();
    assert_eq!(first.python_callback_count(), 0);
    assert!(!first.successor().is_empty());
    let capital = first.observation().cognitive_capital().unwrap();
    assert_eq!(
        capital.successor_state_receipt(),
        first.observation().state_receipt()
    );
    assert_eq!(capital.organism_tick(), first.observation().organism_tick());
    assert!(capital.evidence().is_empty());

    let second_source = exact_source("production-d3-second", true);
    let restarted = transition_native_resident_d3(
        first.successor().to_vec(),
        &second_source,
        Some(&mut cold),
        ENVELOPE_BYTES,
        FABRIC_BYTES,
    )
    .unwrap();
    assert_eq!(restarted.python_callback_count(), 0);
    assert_ne!(
        restarted.observation().state_receipt(),
        first.observation().state_receipt()
    );
    assert_eq!(restarted.observation().cognitive_mosaic_count(), 0);
    assert_eq!(restarted.observation().partial_cue_reassembly_count(), 0);
    assert_eq!(
        restarted.observation().dynamic_formation_relation_count(),
        0
    );
    assert_eq!(restarted.observation().dynamic_linear_formation_count(), 0);
    assert_eq!(restarted.observation().dynamic_web_formation_count(), 0);
    assert_eq!(restarted.observation().dynamic_formation_prior_count(), 0);
    assert_eq!(
        restarted
            .observation()
            .dynamic_formation_active_bond_count(),
        0
    );
    assert_eq!(restarted.observation().tapestry_activity_count(), 0);
    assert_eq!(restarted.observation().deeper_tapestry_activity_count(), 0);
    assert_eq!(restarted.observation().generative_recombination_count(), 0);
}
