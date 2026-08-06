//! SCRATCH MEASUREMENT ONLY — not production logic, not a law, not shipped.
//!
//! Compiled only under `#[cfg(test)]`. Every function here observes existing
//! production code; nothing here is called by the organism. Written for the
//! auditory transduction design study (2026-08-06) to replace quoted claims
//! with measured ones.

#![cfg(test)]

use num_bigint::BigInt;
use num_rational::BigRational;

use crate::complete_neuron::gate_opening_quantum_window;
use crate::exact_rational::ExactRational;
use crate::joint_source_episode::{decode_native_joint_source_episode, NativeJointSourceEpisode};
use crate::joint_uf_neuron_boundary::{
    bind_neuron_perspective, prepare_complete_joint_field_admitted_fixture,
};
use crate::neuron_source_anchor::{bind_neuron_source_anchor, NeuronSourceSite};
use crate::optical_receptor_work::{exact_rational_to_big, quantize_optical_delivery};
use crate::resident_cognitive_formation::ResidentCognitiveFormationState;
use crate::virtual_material_neuron_genesis::create_virtual_material_neuron;

const INTERSAMPLE: &[u8] = b"guala.uf.v1.4.sampled_volume_and_relevance_piecewise_linear.v1";
const BUDGET: usize = 16_000_000;

/// The served production names for an ear port
/// (dsf_ai_service/native_production_app.py:135-136, 922-923).
const SERVED_EAR_QUANTITY: &str = "normalized_physical_excitation";
const SERVED_EAR_UNIT: &str = "normalized_binary64";

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

#[allow(clippy::too_many_arguments)]
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
    output.push(sense);
    u32_value(output, topology_index);
    text_value(output, sensor);
    text_value(output, substream);
    u16_value(output, 1);
    text_value(output, "ear");
    text_value(output, "0");
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
    for ((time_numerator, time_denominator), field) in times.into_iter().zip(fields.into_iter()) {
        rational_value(output, time_numerator, time_denominator);
        output.extend_from_slice(&field.to_bits().to_le_bytes());
        rational_value(output, 0, 1);
        rational_value(output, 1, 1);
        let exact = BigRational::from_float(field).unwrap();
        text_value(output, &exact.numer().to_string());
        text_value(output, &exact.denom().to_string());
    }
}

/// One isolated acoustic occurrence carrying the SERVED ear port names, shaped
/// exactly like `neuron_source_anchor::tests::optical_episode` but on sense 1.
fn acoustic_episode(fields: [f64; 3]) -> NativeJointSourceEpisode {
    let mut output = b"GLJSRC02".to_vec();
    u16_value(&mut output, 2);
    text_value(&mut output, "typed-acoustic-occurrence");
    output.extend_from_slice(&[1, 0, 1, 1, 1, 1]);
    u32_value(&mut output, 1);
    source_port(
        &mut output,
        1,
        0,
        "organism-ear-pressure",
        "ear-0",
        SERVED_EAR_QUANTITY,
        SERVED_EAR_UNIT,
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

fn exact(numerator: i64, denominator: i64) -> BigRational {
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

/// MEASUREMENT 1 — the defect. Sound amplitude has exactly zero physical
/// effect: the successor body is byte-identical to genesis at every amplitude,
/// and no neuron is grown, transitioned, or perturbed.
#[test]
fn measured_sound_amplitude_has_exactly_zero_physical_effect() {
    let genesis = ResidentCognitiveFormationState::default();
    let genesis_bytes = genesis.encode(BUDGET).unwrap();
    let mut successors = Vec::new();
    for amplitude in [1.0_f64, 0.5, 0.1] {
        let source = acoustic_episode([0.0, -amplitude, amplitude]);
        let prepared = genesis.prepare(&source, BUDGET).unwrap();
        let observation = prepared.observation();
        println!(
            "amplitude {amplitude:>4}: neurons={} transitioned={} fractals={} mosaics={} \
             reassembly={}",
            observation.complete_neuron_count,
            observation.physically_transitioned_neuron_count,
            observation.complete_neuron_fractal_count,
            observation.mosaic_count,
            observation.partial_cue_reassembly_count,
        );
        let successor = genesis.encode_successor(&prepared, BUDGET).unwrap();
        let differing = genesis_bytes
            .iter()
            .zip(successor.iter())
            .enumerate()
            .filter(|(_, (a, b))| a != b)
            .map(|(index, _)| index)
            .collect::<Vec<_>>();
        println!(
            "   body bytes {} -> {}, differing byte offsets from genesis: {:?}",
            genesis_bytes.len(),
            successor.len(),
            differing
        );
        assert_eq!(observation.complete_neuron_count, 0);
        assert_eq!(observation.physically_transitioned_neuron_count, 0);
        assert_eq!(observation.complete_neuron_fractal_count, 0);
        assert_eq!(observation.mosaic_count, 0);
        successors.push(successor);
    }
    assert_eq!(successors[0], successors[1]);
    assert_eq!(successors[1], successors[2]);
    println!("all three amplitudes produced byte-identical successor bodies");
}

/// MEASUREMENT 2 — the receiving gate's own opening window for an EAR site at
/// genesis, on the gate's own dissipation lattice. These are the numbers any
/// auditory delivery law must be commensurate with.
#[test]
fn measured_ear_gate_opening_window_at_genesis() {
    let source = acoustic_episode([0.0, 0.5, 1.0]);
    let shared = prepare_complete_joint_field_admitted_fixture(&source, 0).unwrap();
    let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
    let anchor = bind_neuron_source_anchor(&source, perspective).unwrap();
    let site = NeuronSourceSite::from_anchor(anchor);
    let neuron = create_virtual_material_neuron(perspective, &site).unwrap();
    let window =
        gate_opening_quantum_window(neuron.anatomy(), neuron.state(), perspective).unwrap();
    let quantum = neuron.anatomy().gate_dissipation_quantum_zeptojoules().clone();
    let capacity = neuron.anatomy().gate_dissipation_capacity_quanta();
    println!(
        "ear gate: quantum={} zJ  capacity={} quanta  opening_threshold={} quanta  \
         window_cap={} quanta",
        quantum, capacity, window.opening_threshold_quanta, window.window_cap_quanta
    );
    println!(
        "  threshold energy = {} zJ   cap energy = {} zJ",
        &quantum * BigRational::from_integer(window.opening_threshold_quanta.into()),
        &quantum * BigRational::from_integer(window.window_cap_quanta.into())
    );
}

/// The proposed auditory receptor law, evaluated with the existing ratified
/// delivery machinery and NOTHING else. `integrated_square_seconds` is the
/// exact trapezoidal integral of s(t)^2 over the interval; `k` is the single
/// composite acoustic transduction constant in zJ per (dimensionless^2 second).
fn acoustic_transduced_energy(k: &BigRational, integrated_square_seconds: &BigRational)
    -> BigRational
{
    k * integrated_square_seconds
}

/// MEASUREMENT 3 — commensurability of the proposed law against the measured
/// tutor corpus, using the UNCHANGED ratified delivery machinery.
///
/// The composite constant `k` is pinned by the receiving gate's own lattice:
/// full-scale sound (|s| == 1) sustained over one reference settlement interval
/// delivers exactly the gate's own window cap. No number is chosen.
#[test]
fn measured_auditory_commensurability_against_the_real_tutor_corpus() {
    let quantum = exact(1, 16);
    let opening_threshold_quanta = 17_u128;
    let window_cap_quanta = 52_u128;
    let cap_energy = &quantum * BigRational::from_integer(window_cap_quanta.into());

    for (label, reference_interval) in [("250ms hop", exact(1, 4)), ("1500ms dwell", exact(3, 2))] {
        // Pinning: k * (|s|=1 over T) = cap energy, and integral(1^2 dt) = T.
        let k = &cap_energy / &reference_interval;
        println!("\n== reference interval {label}: k = {k} zJ per s^2-second");

        // Measured tutor corpus (36 recordings, scratchpad measure_ear_energy.py):
        // mean whole-utterance integral(s^2 dt), served decimation.
        for (name, integrated) in [
            ("mean tutor utterance", exact(34_694, 1_000_000)),
            ("quietest tutor utterance", exact(13_932, 1_000_000)),
            ("loudest tutor utterance", exact(52_718, 1_000_000)),
        ] {
            let energy = acoustic_transduced_energy(&k, &integrated);
            let quanta = (&energy / &quantum).floor().to_integer();
            println!(
                "   {name:<26} integral(s^2 dt)={} s  ->  {} zJ  = {} quanta \
                 (threshold {opening_threshold_quanta})",
                integrated, energy, quanta
            );
        }

        // Amplitude ladder on a full 250 ms hop of a pure full-scale-scaled
        // signal: integral(s^2 dt) = a^2 * T.
        for amplitude in [exact(1, 1), exact(1, 2), exact(1, 10)] {
            let integrated = &amplitude * &amplitude * exact(1, 4);
            let energy = acoustic_transduced_energy(&k, &integrated);
            let quanta = (&energy / &quantum).floor().to_integer();
            println!("   amplitude {amplitude} over 250 ms -> {energy} zJ = {quanta} quanta");
        }
    }
}

/// MEASUREMENT 4 — the ratified delivery machinery accepts the acoustic
/// integrand unchanged: exact conservation at every step, silence delivers
/// nothing and erases nothing, and a sub-threshold sequence integrates to an
/// opening. Nothing in `quantize_optical_delivery` was modified.
#[test]
fn measured_acoustic_energy_conserves_through_the_ratified_delivery_machinery() {
    let quantum = exact(1, 16);
    let k = &(&quantum * BigRational::from_integer(52.into())) / exact(1, 4);
    // Six 250 ms hops of the measured a-apple-tutor-v1 utterance, then silence.
    let hops: &[(i64, i64)] = &[
        (7_248, 100_000_000_000),
        (3_258_264, 1_000_000_000),
        (2_041_631, 1_000_000_000),
        (1_769_687, 1_000_000_000),
        (5_122_242, 1_000_000_000),
        (3_495_013, 1_000_000_000),
        (0, 1),
        (0, 1),
    ];
    let mut residue = ExactRational::new(0, 1).unwrap();
    let mut delivered_total = BigRational::zero();
    let mut exact_total = BigRational::zero();
    let mut opened = 0_u32;
    for (index, (numerator, denominator)) in hops.iter().enumerate() {
        let integrated = exact(*numerator, *denominator);
        let energy = acoustic_transduced_energy(&k, &integrated);
        exact_total += &energy;
        let delivery = quantize_optical_delivery(
            &energy,
            residue,
            &quantum,
            17,
            52,
        )
        .unwrap();
        delivered_total += &delivery.delivered_energy_zeptojoules;
        residue = delivery.successor_residue;
        let residue_big = exact_rational_to_big(residue);
        assert!(residue_big >= BigRational::zero());
        // Bit-exact conservation at EVERY step.
        assert_eq!(&delivered_total + &residue_big, exact_total);
        if delivery.delivered_quanta > 0 {
            opened += 1;
        }
        println!(
            "hop {index}: energy={} zJ delivered={} quanta retained={} zJ",
            energy, delivery.delivered_quanta, residue_big
        );
    }
    println!(
        "openings={opened}  delivered_total={} zJ  retained={} zJ",
        delivered_total,
        exact_rational_to_big(residue)
    );
}

/// MEASUREMENT 5 — how many repeated card lessons the proposed law needs
/// before the first ear gate opens, at each candidate pinning, using the
/// measured tutor corpus and the unchanged delivery machinery. Residue is
/// carried across lessons because the ratified accumulator has no decay term.
#[test]
fn measured_lessons_to_the_first_ear_gate_opening() {
    let quantum = exact(1, 16);
    let cap_energy = &quantum * BigRational::from_integer(52.into());
    for (label, reference_interval) in [("250ms hop", exact(1, 4)), ("1500ms dwell", exact(3, 2))] {
        let k = &cap_energy / &reference_interval;
        for (corpus, integrated) in [
            ("mean tutor utterance", exact(34_694, 1_000_000)),
            ("quietest tutor utterance", exact(13_932, 1_000_000)),
            ("loudest tutor utterance", exact(52_718, 1_000_000)),
        ] {
            let per_lesson = &k * &integrated;
            let mut residue = ExactRational::new(0, 1).unwrap();
            let mut lesson = 0_u32;
            let mut first_opening = None;
            while lesson < 512 && first_opening.is_none() {
                lesson += 1;
                let delivery =
                    quantize_optical_delivery(&per_lesson, residue, &quantum, 17, 52).unwrap();
                residue = delivery.successor_residue;
                if delivery.delivered_quanta > 0 {
                    first_opening = Some((lesson, delivery.delivered_quanta));
                }
            }
            match first_opening {
                Some((lesson, quanta)) => println!(
                    "{label:<13} {corpus:<26} first ear-gate opening at lesson {lesson} \
                     ({quanta} quanta delivered)"
                ),
                None => println!("{label:<13} {corpus:<26} no opening within 512 lessons"),
            }
        }
    }
}

use num_traits::Zero;
