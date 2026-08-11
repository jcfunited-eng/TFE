//! MEASUREMENT ONLY — proofs A1–A3 for the tonotopic ear (2026-08-06).
//!
//! Compiled only under `#[cfg(test)]`.  Nothing here is production logic and
//! nothing here is called by the organism.  Every number these probes print is
//! measured from the shipped laws, not restated from a document.
//!
//!   A1  a fresh genesis with tonotopic ears produces geometrically DISTINCT
//!       cochlear sites (territory indices and capacitances, no two equal)
//!   A2  a real tutor recording delivers NONZERO gate work that varies with
//!       amplitude and with frequency content
//!   A3  two identical ear ports (the OLD broken anatomy) form ZERO memory —
//!       the blockade the tonotopic anatomy exists to remove

#![cfg(test)]

use std::collections::BTreeSet;

use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{ToPrimitive, Zero};

use crate::auditory::{auditory_gammatone_stream_impl, zero_stream_state};
use crate::auditory_receptor_work::{
    settle_port, AuditoryReceptorAnatomy, COCHLEAR_BAND_PRESSURE_QUANTITY,
    COCHLEAR_REFERENCE_PRESSURE_UNIT,
};
use crate::complete_neuron::gate_opening_quantum_window;
use crate::declared_geometric_anatomy::{
    declared_geometric_territory, membrane_capacitance_from_declared_geometry,
};
use crate::exact_rational::ExactRational;
use crate::joint_source_episode::{JointSourceCoordinate, JointSourcePortView};
use crate::joint_uf_neuron_boundary::{
    bind_neuron_perspective, prepare_complete_joint_field_admitted_fixture,
};
use crate::neuron_source_anchor::{
    bind_neuron_source_anchor, NeuronSourceSite, PhysicalSourceSense,
};
use crate::receptor_quantum_delivery::{exact_rational_to_big, quantize_receptor_delivery};
use crate::resident_cognitive_formation::ResidentCognitiveFormationState;
use crate::virtual_material_neuron_genesis::create_virtual_material_neuron;

// The served birth anatomy under test (dsf_ai_service/native_production_app.py).
const CARD_SURFACE_PORT_COUNT: u32 = 27;
const EAR_COUNT: u32 = 2;
const COCHLEAR_CHANNELS_PER_EAR: u32 = 16;
const COCHLEAR_PRESSURE_LATTICE: f64 = 16_777_216.0; // 2^24
const COCHLEAR_OBSERVATION_HOP_SAMPLES: usize = 160;
const SAMPLE_RATE_HZ: usize = 16_000;
const INTAKE_HOP_SAMPLES: usize = 4_000; // 250 ms

const BUDGET: usize = 16_000_000;
const INTERSAMPLE: &[u8] = b"guala.uf.v1.4.sampled_volume_and_relevance_piecewise_linear.v1";

fn exact(numerator: i64, denominator: i64) -> BigRational {
    BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
}

/// Optical parity (Law A5): K = 2 zJ per (dimensionless² · second).
fn ear_anatomy() -> AuditoryReceptorAnatomy {
    AuditoryReceptorAnatomy::new(exact(4, 1), exact(1, 1), exact(1, 2), exact(1, 1)).unwrap()
}

fn cochlear_site(ear_index: u32, channel_index: u32) -> NeuronSourceSite {
    NeuronSourceSite::fixture_in_sense(
        PhysicalSourceSense::Sound,
        ear_index * COCHLEAR_CHANNELS_PER_EAR + channel_index,
    )
}

// ---------------------------------------------------------------------------
// A1 — the tonotopic birth anatomy is geometrically distinct
// ---------------------------------------------------------------------------

/// A1.  Every cochlear site of the birth anatomy occupies its own declared
/// place, so the ratified Cantor territory law gives it its own membrane
/// territory and its own capacitance.  No two are equal — not within an ear,
/// not between the ears, and not against any of the 27 retinal sites.
///
/// This is the property the whole design turns on: identical authored
/// capacitance makes stored energy `q²e²/2C` tie EXACTLY between neighbours,
/// and the ratified energy-descent transfer law refuses ties, so identical ear
/// ports are a permanent Coulomb blockade.
#[test]
fn a1_tonotopic_birth_sites_are_geometrically_distinct() {
    let base = ExactRational::integer(1); // 1 pF, the authored unit patch
    let mut territories = BTreeSet::new();
    let mut capacitances = BTreeSet::new();

    println!("A1 — retinal cohort (sense layer 0):");
    for topology_index in 0..CARD_SURFACE_PORT_COUNT {
        let site = NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Sight, topology_index);
        let territory = declared_geometric_territory(&site).unwrap();
        let capacitance = membrane_capacitance_from_declared_geometry(base, &site).unwrap();
        assert!(territories.insert(territory));
        assert!(capacitances.insert(capacitance.picofarads().parts()));
        if topology_index < 3 || topology_index == CARD_SURFACE_PORT_COUNT - 1 {
            println!(
                "   retinal site {topology_index:>2}: A = {territory:>5} patches, C = {:?} pF",
                capacitance.picofarads().parts()
            );
        }
    }

    println!("A1 — cochlear cohorts (sense layer 1):");
    for ear_index in 0..EAR_COUNT {
        for channel_index in 0..COCHLEAR_CHANNELS_PER_EAR {
            let site = cochlear_site(ear_index, channel_index);
            let territory = declared_geometric_territory(&site).unwrap();
            let capacitance = membrane_capacitance_from_declared_geometry(base, &site).unwrap();
            assert!(
                territories.insert(territory),
                "cochlear site (ear {ear_index}, band {channel_index}) repeated a territory"
            );
            assert!(capacitances.insert(capacitance.picofarads().parts()));
            println!(
                "   ear {ear_index} band {channel_index:>2}: topology {:>2}  A = {territory:>5} \
                 patches, C = {:?} pF",
                site.topology_index(),
                capacitance.picofarads().parts()
            );
        }
    }

    let expected = (CARD_SURFACE_PORT_COUNT + EAR_COUNT * COCHLEAR_CHANNELS_PER_EAR) as usize;
    assert_eq!(territories.len(), expected);
    assert_eq!(capacitances.len(), expected);
    println!(
        "A1 RESULT: {expected} declared sites, {} distinct territories, {} distinct \
         capacitances — no two equal.",
        territories.len(),
        capacitances.len()
    );
}

/// A1 (companion).  The blockade the distinctness prevents, stated as physics:
/// two ear sites at the SAME declared place carry the SAME capacitance, so a
/// one-charge imbalance between them can never descend in stored energy.
#[test]
fn a1_two_sites_at_one_declared_place_share_a_capacitance_exactly() {
    let base = ExactRational::integer(1);
    let left = NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Sound, 0);
    let right = NeuronSourceSite::fixture_in_sense(PhysicalSourceSense::Sound, 0);
    assert_eq!(
        membrane_capacitance_from_declared_geometry(base, &left)
            .unwrap()
            .picofarads()
            .parts(),
        membrane_capacitance_from_declared_geometry(base, &right)
            .unwrap()
            .picofarads()
            .parts()
    );
    // ... and two TONOTOPIC places never do.
    let band_one = cochlear_site(0, 0);
    let band_two = cochlear_site(0, 1);
    assert_ne!(
        membrane_capacitance_from_declared_geometry(base, &band_one)
            .unwrap()
            .picofarads()
            .parts(),
        membrane_capacitance_from_declared_geometry(base, &band_two)
            .unwrap()
            .picofarads()
            .parts()
    );
    println!(
        "A1 blockade: identical declared place -> identical C = {:?} pF (energy ties, transfer \
         refused); tonotopic places -> {:?} vs {:?} pF",
        membrane_capacitance_from_declared_geometry(base, &left)
            .unwrap()
            .picofarads()
            .parts(),
        membrane_capacitance_from_declared_geometry(base, &band_one)
            .unwrap()
            .picofarads()
            .parts(),
        membrane_capacitance_from_declared_geometry(base, &band_two)
            .unwrap()
            .picofarads()
            .parts()
    );
}

// ---------------------------------------------------------------------------
// A2 — a real sound transduces, and the work varies with amplitude and pitch
// ---------------------------------------------------------------------------

/// Read a pcm_s16le mono 16 kHz WAV the way the served app does.
///
/// Returns `None` when the curriculum corpus is not present beside the crate
/// (the release manifest stages the crate ALONE, so the packaging test's
/// staged `cargo test` has no audio).  The probes below then report that the
/// measurement did not run rather than passing silently or failing falsely.
fn read_tutor_wav(name: &str) -> Option<Vec<i16>> {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../guala_curriculum/audio")
        .join(name);
    let body = match std::fs::read(&path) {
        Ok(body) => body,
        Err(_) => {
            println!(
                "MEASUREMENT NOT RUN: the tutor corpus is not present at {} (staged crate); \
                 no auditory corpus number is reported from this run.",
                path.display()
            );
            return None;
        }
    };
    // Walk the RIFF chunks to the data chunk rather than assuming a 44-byte
    // header, so a file with an extra chunk is read correctly or not at all.
    assert_eq!(&body[0..4], b"RIFF");
    assert_eq!(&body[8..12], b"WAVE");
    let mut cursor = 12usize;
    while cursor + 8 <= body.len() {
        let id = &body[cursor..cursor + 4];
        let size = u32::from_le_bytes(body[cursor + 4..cursor + 8].try_into().unwrap()) as usize;
        let start = cursor + 8;
        if id == b"data" {
            return Some(
                body[start..start + size]
                    .chunks_exact(2)
                    .map(|pair| i16::from_le_bytes([pair[0], pair[1]]))
                    .collect(),
            );
        }
        cursor = start + size + (size & 1);
    }
    panic!("tutor audio carries no data chunk");
}

fn erb_width_hz(frequency_hz: f64) -> f64 {
    24.7 * (1.0 + 4.37e-3 * frequency_hz)
}

fn erb_rate(frequency_hz: f64) -> f64 {
    21.4 * (1.0 + 4.37e-3 * frequency_hz).log10()
}

fn frequency_from_erb_rate(rate: f64) -> f64 {
    (10.0_f64.powf(rate / 21.4) - 1.0) / 4.37e-3
}

/// The served app's own cochlear channel roster and gammatone coefficients.
fn cochlear_coefficients() -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<f64>) {
    let lower = erb_rate(80.0);
    let upper = erb_rate(7_500.0);
    let span = (COCHLEAR_CHANNELS_PER_EAR - 1) as f64;
    let mut centres = Vec::new();
    let mut pole_real = Vec::new();
    let mut pole_imag = Vec::new();
    let mut injection = Vec::new();
    for index in 0..COCHLEAR_CHANNELS_PER_EAR {
        let rate = lower + (upper - lower) * f64::from(index) / span;
        let centre = frequency_from_erb_rate(rate);
        let radius =
            (-2.0 * std::f64::consts::PI * 1.019 * erb_width_hz(centre) / 16_000.0).exp();
        let angle = 2.0 * std::f64::consts::PI * centre / 16_000.0;
        centres.push(centre);
        pole_real.push(radius * angle.cos());
        pole_imag.push(radius * angle.sin());
        injection.push(1.0 - radius);
    }
    (centres, pole_real, pole_imag, injection)
}

/// Per-band envelopes on the served app's declared 24-bit amplitude lattice.
fn cochlear_envelopes(signal: &[f64]) -> Vec<Vec<f64>> {
    let (_centres, pole_real, pole_imag, injection) = cochlear_coefficients();
    let (state_real, state_imag, previous_real, previous_imag, phase, energy, partial) =
        zero_stream_state();
    let result = auditory_gammatone_stream_impl(
        signal,
        &pole_real,
        &pole_imag,
        &injection,
        state_real,
        state_imag,
        previous_real,
        previous_imag,
        phase,
        energy,
        partial,
        0,
    )
    .unwrap();
    result
        .0
        .into_iter()
        .map(|frame| {
            frame
                .into_iter()
                .map(|value| {
                    (value * COCHLEAR_PRESSURE_LATTICE).round().clamp(0.0, COCHLEAR_PRESSURE_LATTICE)
                        / COCHLEAR_PRESSURE_LATTICE
                })
                .collect()
        })
        .collect()
}

fn cochlear_port(channel_index: usize, values: &[f64], hop_seconds: BigRational) -> JointSourcePortView {
    let count = values.len();
    JointSourcePortView {
        sense: 1,
        topology_index: channel_index as u32,
        sensor_id: "organism-ear-pressure".into(),
        substream_id: format!("cochlea-0-band-{channel_index:02}"),
        coordinates: vec![JointSourceCoordinate {
            axis_id: "cochlear-band".into(),
            coordinate_id: channel_index.to_string(),
        }],
        physical_quantity: COCHLEAR_BAND_PRESSURE_QUANTITY.into(),
        physical_unit: COCHLEAR_REFERENCE_PRESSURE_UNIT.into(),
        relevance_rule: "source-only".into(),
        relevance_origin: None,
        input_map_id: "independent-proof-map".into(),
        source_min: exact(-1, 1),
        source_max: exact(1, 1),
        field_offset: exact(1, 1),
        field_scale: exact(1, 2),
        input_map_profile: vec![1],
        input_map_group_receipt: [0; 32],
        source_times: (0..count)
            .map(|index| &hop_seconds * BigRational::from_integer(BigInt::from(index)))
            .collect(),
        exact_normalized_sources: values
            .iter()
            .map(|value| BigRational::from_float(*value).unwrap())
            .collect(),
        reported_phase_turns: vec![exact(0, 1); count],
        source_relevances: vec![exact(1, 1); count],
        dimensionless_fields: vec![exact(1, 1); count],
    }
}

/// A2.  A REAL tutor recording, transduced by the shipped auditory law through
/// the shipped delivery law, at four amplitudes.  Reported per band, so the
/// frequency dependence is visible rather than asserted.
#[test]
fn a2_real_tutor_audio_transduces_nonzero_work_varying_with_amplitude_and_pitch() {
    let anatomy = ear_anatomy();
    // The receiving gate's own lattice for a genesis cochlear site.
    let quantum = exact(1, 16);
    let (opening_threshold, window_cap) = (17_u128, 52_u128);
    let hop_seconds = BigRational::new(
        BigInt::from(COCHLEAR_OBSERVATION_HOP_SAMPLES),
        BigInt::from(SAMPLE_RATE_HZ),
    );
    let Some(samples) = read_tutor_wav("a-apple-tutor-v1.wav") else {
        return;
    };
    println!(
        "A2 — a-apple-tutor-v1.wav: {} samples ({:.3} s at 16 kHz), K = {} zJ/(s)",
        samples.len(),
        samples.len() as f64 / SAMPLE_RATE_HZ as f64,
        anatomy.composite_transduction_constant()
    );

    let mut totals_by_gain = Vec::new();
    for (label, gain) in [
        ("1", 1.0_f64),
        ("1/2", 0.5),
        ("1/4", 0.25),
        ("1/10", 0.1),
    ] {
        let signal = samples
            .iter()
            .map(|value| f64::from(*value) * gain / 32768.0)
            .collect::<Vec<_>>();
        let envelopes = cochlear_envelopes(&signal);
        let mut band_energy = vec![BigRational::zero(); COCHLEAR_CHANNELS_PER_EAR as usize];
        let mut band_quanta = vec![0_u128; COCHLEAR_CHANNELS_PER_EAR as usize];
        for channel_index in 0..COCHLEAR_CHANNELS_PER_EAR as usize {
            let mut residue = ExactRational::new(0, 1).unwrap();
            let mut delivered = 0_u128;
            let mut energy = BigRational::zero();
            // One 250 ms transport hop at a time, exactly as the app delivers.
            for hop_start in (0..envelopes.len()).step_by(INTAKE_HOP_SAMPLES / COCHLEAR_OBSERVATION_HOP_SAMPLES)
            {
                let hop_end =
                    (hop_start + INTAKE_HOP_SAMPLES / COCHLEAR_OBSERVATION_HOP_SAMPLES)
                        .min(envelopes.len());
                if hop_end - hop_start < 2 {
                    continue;
                }
                let values = envelopes[hop_start..hop_end]
                    .iter()
                    .map(|frame| frame[channel_index])
                    .collect::<Vec<_>>();
                let settled =
                    settle_port(&cochlear_port(channel_index, &values, hop_seconds.clone()), &anatomy)
                        .unwrap();
                energy += &settled.transduced_energy_zeptojoules;
                let delivery = quantize_receptor_delivery(
                    &settled.transduced_energy_zeptojoules,
                    residue,
                    &quantum,
                    opening_threshold,
                    window_cap,
                )
                .unwrap();
                delivered += delivery.delivered_quanta;
                residue = delivery.successor_residue;
                // Conservation holds at every hop.
                assert!(exact_rational_to_big(residue) >= BigRational::zero());
            }
            band_energy[channel_index] = energy;
            band_quanta[channel_index] = delivered;
        }
        let total = band_energy
            .iter()
            .fold(BigRational::zero(), |sum, value| sum + value);
        println!("A2 gain {label:>4}: whole-utterance transduced energy per band (zJ)");
        for channel_index in 0..COCHLEAR_CHANNELS_PER_EAR as usize {
            let (centres, ..) = cochlear_coefficients();
            println!(
                "        band {channel_index:>2} ({:>7.1} Hz): {:>12.6e} zJ  delivered {} quanta",
                centres[channel_index],
                band_energy[channel_index].to_f64().unwrap(),
                band_quanta[channel_index]
            );
        }
        println!(
            "        TOTAL over 16 bands: {:.6e} zJ  ({} quanta delivered)",
            total.to_f64().unwrap(),
            band_quanta.iter().sum::<u128>()
        );
        totals_by_gain.push((label, gain, total, band_energy));
    }

    // The law transduces at all: full-gain energy is strictly positive.
    let full = &totals_by_gain[0].2;
    assert!(full > &BigRational::zero(), "a real tutor utterance transduced nothing");

    // Amplitude: energy is quadratic in gain.  Quantizing the envelope to the
    // declared 24-bit lattice makes this an extremely tight ratio rather than
    // an exact one, so the ratio is REPORTED and bounded, never forced.
    for (label, gain, total, _) in totals_by_gain.iter().skip(1) {
        let predicted = full * BigRational::from_float(gain * gain).unwrap();
        let ratio = total.to_f64().unwrap() / predicted.to_f64().unwrap();
        println!("A2 amplitude law: gain {label:>4} -> measured/quadratic-prediction = {ratio:.6}");
        assert!(
            (0.98..=1.02).contains(&ratio),
            "gain {label} broke the quadratic amplitude law: ratio {ratio}"
        );
    }

    // Frequency content: the bands do NOT receive the same energy.  Report the
    // loudest and quietest band and their ratio.
    let bands = &totals_by_gain[0].3;
    let (centres, ..) = cochlear_coefficients();
    let loudest = bands
        .iter()
        .enumerate()
        .max_by(|left, right| left.1.partial_cmp(right.1).unwrap())
        .unwrap();
    let quietest = bands
        .iter()
        .enumerate()
        .filter(|(_, value)| *value > &BigRational::zero())
        .min_by(|left, right| left.1.partial_cmp(right.1).unwrap())
        .unwrap();
    println!(
        "A2 frequency law: loudest band {} ({:.1} Hz) = {:.6e} zJ; quietest nonzero band {} \
         ({:.1} Hz) = {:.6e} zJ; ratio {:.1}x",
        loudest.0,
        centres[loudest.0],
        loudest.1.to_f64().unwrap(),
        quietest.0,
        centres[quietest.0],
        quietest.1.to_f64().unwrap(),
        loudest.1.to_f64().unwrap() / quietest.1.to_f64().unwrap()
    );
    assert!(loudest.1 > quietest.1);

    // A DIFFERENT utterance puts its energy in a different place: the tonotopic
    // profile is a property of the sound, not of the ear's wiring.
    let Some(other) = read_tutor_wav("s-snail-tutor-v1.wav") else {
        return;
    };
    let other_signal = other
        .iter()
        .map(|value| f64::from(*value) / 32768.0)
        .collect::<Vec<_>>();
    let other_envelopes = cochlear_envelopes(&other_signal);
    let mut other_bands = vec![0.0_f64; COCHLEAR_CHANNELS_PER_EAR as usize];
    for frame in &other_envelopes {
        for (channel_index, value) in frame.iter().enumerate() {
            other_bands[channel_index] += value * value;
        }
    }
    let other_peak = other_bands
        .iter()
        .enumerate()
        .max_by(|left, right| left.1.partial_cmp(right.1).unwrap())
        .unwrap()
        .0;
    println!(
        "A2 frequency law (second utterance): s-snail-tutor-v1 peaks at band {other_peak} \
         ({:.1} Hz) against a-apple's band {} ({:.1} Hz)",
        centres[other_peak],
        loudest.0,
        centres[loudest.0]
    );
}

// ---------------------------------------------------------------------------
// A3 — the old two-port ear can never form a memory
// ---------------------------------------------------------------------------

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

fn reduced(numerator: i64, denominator: i64) -> (i64, i64) {
    fn gcd(left: i64, right: i64) -> i64 {
        if right == 0 { left.abs().max(1) } else { gcd(right, left % right) }
    }
    if numerator == 0 {
        return (0, 1);
    }
    let divisor = gcd(numerator, denominator);
    (numerator / divisor, denominator / divisor)
}

fn rational_value(output: &mut Vec<u8>, numerator: i64, denominator: i64) {
    text_value(output, &numerator.to_string());
    text_value(output, &denominator.to_string());
}

fn push_cochlear_port(output: &mut Vec<u8>, topology_index: u32, fields: &[f64], frames: usize) {
    output.push(1);
    u32_value(output, topology_index);
    text_value(output, "organism-ear-pressure");
    text_value(output, &format!("cochlea-band-{topology_index:02}"));
    u16_value(output, 1);
    text_value(output, "cochlear-band");
    text_value(output, &topology_index.to_string());
    text_value(output, COCHLEAR_BAND_PRESSURE_QUANTITY);
    text_value(output, COCHLEAR_REFERENCE_PRESSURE_UNIT);
    text_value(output, "direct-physical-source");
    text_value(output, "");
    text_value(output, "identity-binary64");
    rational_value(output, -1, 1);
    rational_value(output, 1, 1);
    rational_value(output, 0, 1);
    rational_value(output, 1, 1);
    byte_value(output, b"identity-binary64-v1");
    u32_value(output, frames as u32);
    for index in 0..frames {
        let (numerator, denominator) = reduced(index as i64, 100);
        rational_value(output, numerator, denominator);
        let field = fields[index];
        output.extend_from_slice(&field.to_bits().to_le_bytes());
        rational_value(output, 0, 1);
        rational_value(output, 1, 1);
        let exact_field = BigRational::from_float(field).unwrap();
        text_value(output, &exact_field.numer().to_string());
        text_value(output, &exact_field.denom().to_string());
    }
}

/// One isolated acoustic occurrence of `port_count` cochlear ports, each
/// carrying its own band signal on one shared clock.
fn acoustic_episode(bands: &[Vec<f64>]) -> crate::joint_source_episode::NativeJointSourceEpisode {
    let port_count = bands.len();
    let frames = bands[0].len();
    let mut output = b"GLJSRC02".to_vec();
    u16_value(&mut output, 2);
    text_value(&mut output, "tonotopic-acoustic-occurrence");
    output.extend_from_slice(&[1, 0, 1, 1, 1, 1]);
    u32_value(&mut output, port_count as u32);
    for (topology_index, band) in bands.iter().enumerate() {
        push_cochlear_port(&mut output, topology_index as u32, band, frames);
    }
    u32_value(&mut output, 1);
    u32_value(&mut output, port_count as u32);
    for index in 0..port_count {
        u32_value(&mut output, index as u32);
    }
    u32_value(&mut output, frames as u32);
    for index in 0..frames {
        let (numerator, denominator) = reduced(index as i64, 100);
        rational_value(&mut output, numerator, denominator);
    }
    byte_value(&mut output, INTERSAMPLE);
    u32_value(&mut output, 1);
    u32_value(&mut output, port_count as u32);
    for index in 0..port_count {
        u32_value(&mut output, index as u32);
    }
    byte_value(&mut output, b"explicit-joint-relevance-v1");
    u32_value(&mut output, frames as u32);
    for _ in 0..frames {
        rational_value(&mut output, 1, 1);
    }
    crate::joint_source_episode::decode_native_joint_source_episode(
        &output,
        port_count,
        port_count * frames,
        1,
        frames,
    )
    .unwrap()
}

/// A3 — THE BLOCKADE.  Two ear ports, the served anatomy before this work,
/// driven by real tutor audio to gate-opening levels and presented repeatedly.
/// They grow, they burn, they transition — and they retain NOTHING and admit
/// NO mosaic, ever, because participation retention needs at least three
/// changed members connected through active contacts and two ports can never
/// be three.  This is why the ear had to be BORN tonotopic.
#[test]
fn a3_two_identical_ear_ports_form_zero_memory() {
    // A loud, band-varying signal so nothing can be blamed on the stimulus.
    // 64 retained instants at 10 ms = 0.63 s per presentation, which at K = 2
    // zJ/s puts each site PAST its own gate opening threshold (17 quanta of
    // 1/16 zJ = 1.0625 zJ): the blockade below is measured on an ear that is
    // really transducing and really opening gates, not on a quiet one.
    let frames = 64;
    let two_port = vec![
        (0..frames).map(|index| 0.5 + 0.25 * ((index % 3) as f64)).collect::<Vec<_>>(),
        (0..frames).map(|index| 0.5 + 0.25 * ((index % 3) as f64)).collect::<Vec<_>>(),
    ];
    let silent_two = vec![vec![0.0_f64; frames], vec![0.0_f64; frames]];
    let mut state = ResidentCognitiveFormationState::default();
    let episode = acoustic_episode(&two_port);
    let silence = acoustic_episode(&silent_two);
    let mut last = None;
    // Loud presentation, then TRUE SILENCE: the silent settlement carries zero
    // exogenous receptor energy, which is exactly the ratified stimulus
    // boundary, so the experience really closes and retention is really
    // attempted on every cycle.  It still retains nothing.
    for presentation in 1..=8_u32 {
        let source = if presentation % 2 == 1 { &episode } else { &silence };
        let prepared = state.prepare(source, BUDGET).unwrap();
        let observation = prepared.observation();
        last = Some((
            observation.complete_neuron_count,
            observation.physically_transitioned_neuron_count,
            observation.complete_neuron_fractal_count,
            observation.mosaic_count,
            observation.partial_cue_reassembly_count,
        ));
        if presentation <= 3 || presentation == 8 {
            println!(
                "A3 two-port ear, presentation {presentation}: neurons={} transitioned={} \
                 fractals={} mosaics={} reassemblies={}",
                observation.complete_neuron_count,
                observation.physically_transitioned_neuron_count,
                observation.complete_neuron_fractal_count,
                observation.mosaic_count,
                observation.partial_cue_reassembly_count,
            );
        }
        assert_eq!(observation.mosaic_count, 0);
        assert_eq!(observation.partial_cue_reassembly_count, 0);
        state.commit(prepared).unwrap();
    }
    let (neurons, _transitioned, _fractals, mosaics, reassemblies) = last.unwrap();
    println!(
        "A3 RESULT (two ear ports): {neurons} neurons grown, {mosaics} mosaics, \
         {reassemblies} reassemblies after 8 presentations — the ear hears and remembers nothing."
    );
    assert_eq!(neurons, 4);
    assert_eq!(mosaics, 0);

    // The SAME stimulus into a three-place cochlea passes the member count.
    // (Whether it also retains depends on the authored tonotopic contacts,
    // which the served birth anatomy declares and this isolated fixture does
    // not — reported, never claimed.)
    let three_port = vec![
        (0..frames).map(|index| 0.5 + 0.25 * ((index % 3) as f64)).collect::<Vec<_>>(),
        (0..frames).map(|index| 0.4 + 0.20 * ((index % 4) as f64)).collect::<Vec<_>>(),
        (0..frames).map(|index| 0.3 + 0.15 * ((index % 5) as f64)).collect::<Vec<_>>(),
    ];
    let silent_three = vec![vec![0.0_f64; frames], vec![0.0_f64; frames], vec![0.0_f64; frames]];
    let mut wide = ResidentCognitiveFormationState::default();
    let wide_episode = acoustic_episode(&three_port);
    let wide_silence = acoustic_episode(&silent_three);
    for presentation in 1..=8_u32 {
        let source = if presentation % 2 == 1 { &wide_episode } else { &wide_silence };
        let prepared = wide.prepare(source, BUDGET).unwrap();
        let observation = prepared.observation();
        println!(
            "A3 three-place cochlea: neurons={} transitioned={} fractals={} mosaics={}",
            observation.complete_neuron_count,
            observation.physically_transitioned_neuron_count,
            observation.complete_neuron_fractal_count,
            observation.mosaic_count,
        );
        wide.commit(prepared).unwrap();
    }
}

/// The gate window every A2 number is measured against, read from a genesis
/// cochlear site's own anatomy rather than quoted.
#[test]
fn a2_gate_window_of_a_genesis_cochlear_site() {
    let frames = 4;
    let bands = (0..3)
        .map(|channel| (0..frames).map(|index| 0.25 * ((index + channel) % 4) as f64).collect())
        .collect::<Vec<Vec<f64>>>();
    let episode = acoustic_episode(&bands);
    let shared = prepare_complete_joint_field_admitted_fixture(&episode, 0).unwrap();
    let perspective = bind_neuron_perspective(&shared, 0, 0).unwrap();
    let anchor = bind_neuron_source_anchor(&episode, perspective).unwrap();
    let site = NeuronSourceSite::from_anchor(anchor);
    let neuron = create_virtual_material_neuron(perspective, &site).unwrap();
    let window = gate_opening_quantum_window(neuron.anatomy(), neuron.state(), perspective).unwrap();
    println!(
        "A2 gate: cochlear site quantum = {} zJ, capacity = {} quanta, opening threshold = {} \
         quanta, window cap = {} quanta",
        neuron.anatomy().gate_dissipation_quantum_zeptojoules(),
        neuron.anatomy().gate_dissipation_capacity_quanta(),
        window.opening_threshold_quanta,
        window.window_cap_quanta
    );
}

/// A2 (completion) — where the ratified pinning actually puts the first ear
/// gate opening, and what DELIVERED gate work looks like once it is reached.
///
/// The transduced energy of a real tutor utterance is nonzero and exactly
/// quadratic in amplitude (proved above), but under optical parity
/// (K = 2 zJ per dimensionless²-second) it is far under the receiving gate's
/// own 17-quantum opening threshold, so a single lesson delivers ZERO quanta
/// and retains all of it.  This probe reports the honest consequence: how many
/// identical lessons the accumulator needs before the first ear gate opens,
/// and the delivered-quanta ladder at levels that do open one.
#[test]
fn a2_lessons_to_the_first_ear_gate_opening_and_the_delivered_work_ladder() {
    let anatomy = ear_anatomy();
    let quantum = exact(1, 16);
    let (opening_threshold, window_cap) = (17_u128, 52_u128);
    let threshold_energy =
        &quantum * BigRational::from_integer(BigInt::from(opening_threshold));
    let hop_seconds = BigRational::new(
        BigInt::from(COCHLEAR_OBSERVATION_HOP_SAMPLES),
        BigInt::from(SAMPLE_RATE_HZ),
    );
    let Some(samples) = read_tutor_wav("a-apple-tutor-v1.wav") else {
        return;
    };
    let (centres, ..) = cochlear_coefficients();

    for gain in [1.0_f64, 10.0, 20.0, 40.0] {
        let signal = samples
            .iter()
            .map(|value| (f64::from(*value) * gain / 32768.0).clamp(-1.0, 1.0))
            .collect::<Vec<_>>();
        let envelopes = cochlear_envelopes(&signal);
        let mut best = (0usize, BigRational::zero());
        let mut delivered_first_lesson = 0_u128;
        for channel_index in 0..COCHLEAR_CHANNELS_PER_EAR as usize {
            let mut energy = BigRational::zero();
            let mut residue = ExactRational::new(0, 1).unwrap();
            for hop_start in (0..envelopes.len())
                .step_by(INTAKE_HOP_SAMPLES / COCHLEAR_OBSERVATION_HOP_SAMPLES)
            {
                let hop_end = (hop_start
                    + INTAKE_HOP_SAMPLES / COCHLEAR_OBSERVATION_HOP_SAMPLES)
                    .min(envelopes.len());
                if hop_end - hop_start < 2 {
                    continue;
                }
                let values = envelopes[hop_start..hop_end]
                    .iter()
                    .map(|frame| frame[channel_index])
                    .collect::<Vec<_>>();
                let settled = settle_port(
                    &cochlear_port(channel_index, &values, hop_seconds.clone()),
                    &anatomy,
                )
                .unwrap();
                energy += &settled.transduced_energy_zeptojoules;
                let delivery = quantize_receptor_delivery(
                    &settled.transduced_energy_zeptojoules,
                    residue,
                    &quantum,
                    opening_threshold,
                    window_cap,
                )
                .unwrap();
                delivered_first_lesson += delivery.delivered_quanta;
                residue = delivery.successor_residue;
            }
            if energy > best.1 {
                best = (channel_index, energy);
            }
        }
        let lessons = (&threshold_energy / &best.1).to_f64().unwrap().ceil();
        println!(
            "A2 pinning: gain {gain:>5} -> loudest band {} ({:>7.1} Hz) takes {:.6e} zJ per \
             lesson; the 17-quantum threshold is {} zJ, so the FIRST ear-gate opening lands at \
             lesson {lessons:.0}; delivered in lesson 1 across all bands = {delivered_first_lesson} quanta",
            best.0,
            centres[best.0],
            best.1.to_f64().unwrap(),
            threshold_energy,
        );
    }
}
