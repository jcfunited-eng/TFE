//! Measurement-only probe (test code, never compiled into production).
//!
//! Decodes persisted `CURRENT` generation envelopes (`*.glorun` bodies) and
//! dumps every cohort's recovery-fluid reservoir, per-lane recovery state,
//! dissipation ledgers, and DNA-expression state as JSON, so an external
//! driver can measure per-lesson fuel burn on the exact production physics.
//!
//! Driven via environment variables:
//!   GUALA_PROBE_IN  = directory containing envelope body files (sorted by name)
//!   GUALA_PROBE_OUT = output path for the JSON report
//! When GUALA_PROBE_IN is absent the test is a no-op (ordinary `cargo test`
//! runs are unaffected).

use super::ResidentCognitiveFormationState;
use crate::articulated_body_joint_source_builder::{
    admit_articulated_body_consequence_source, exact_moved_effector_terminal,
};
use crate::complete_neuron::RecoveryLaneAddress;
use crate::exact_rational::ExactRational;
use crate::joint_uf_source_adapter::admitted_episode_with_authored_intervals;
use crate::recovery_fluid_contact::ReachedRecoveryFluidAnatomy;
use crate::vestibular_neuron_path::FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES;
use crate::virtual_articulated_body::{
    settle_body_effector_drives, AdmittedBodyEffectorDrives, ArticulatedBodyState, BodyAxis,
    BodyEffectorDirection, BodyEffectorDrive, BodyEffectorTerminal, ARTICULATED_BODY_STATE_BYTES,
    BODY_AXES, BODY_SETTLEMENT_CLOCK_MICROSECONDS,
};
use crate::virtual_articulatory_body::settle_native_articulatory_interval;
use num_bigint::BigInt;
use num_rational::BigRational;
use num_traits::{ToPrimitive, Zero};
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;

const ENVELOPE_MAGIC: &[u8; 8] = b"GLORUN01";
const PRE_VESTIBULAR_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB07";
const PRE_ARTICULATED_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB08";
const PRE_PHONATORY_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB09";
const PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB10";
const CURRENT_FABRIC_MAGIC: &[u8; 8] = b"GLMFAB11";
const CANAL_STATE_BYTES: usize = 32;
const IDENTITY_BYTES: usize = 36;

fn take<'a>(bytes: &'a [u8], cursor: &mut usize, count: usize) -> &'a [u8] {
    let slice = &bytes[*cursor..*cursor + count];
    *cursor += count;
    slice
}

fn take_u16(bytes: &[u8], cursor: &mut usize) -> u16 {
    u16::from_le_bytes(take(bytes, cursor, 2).try_into().unwrap())
}

fn take_u32(bytes: &[u8], cursor: &mut usize) -> u32 {
    u32::from_le_bytes(take(bytes, cursor, 4).try_into().unwrap())
}

fn take_u64(bytes: &[u8], cursor: &mut usize) -> u64 {
    u64::from_le_bytes(take(bytes, cursor, 8).try_into().unwrap())
}

/// Parses the raw envelope exactly as `organism_runtime::parse_current_envelope`
/// does (same magics, same layout) and returns the organism tick, cognitive
/// bytes, and exact articulated body when that body exists in the fabric.
fn parse_envelope_with_body(bytes: &[u8]) -> (u64, Vec<u8>, Option<ArticulatedBodyState>) {
    let mut cursor = 0usize;
    assert_eq!(
        take(bytes, &mut cursor, 8),
        ENVELOPE_MAGIC,
        "envelope magic"
    );
    assert_eq!(take_u16(bytes, &mut cursor), 1, "envelope version");
    let _identity = take(bytes, &mut cursor, IDENTITY_BYTES);
    let organism_tick = take_u64(bytes, &mut cursor);
    let fabric_len = take_u32(bytes, &mut cursor) as usize;
    let fabric = take(bytes, &mut cursor, fabric_len);
    assert_eq!(cursor, bytes.len(), "envelope trailing bytes");

    let mut fc = 0usize;
    let fabric_magic = take(fabric, &mut fc, 8);
    assert!(
        fabric_magic == PRE_VESTIBULAR_FABRIC_MAGIC
            || fabric_magic == PRE_ARTICULATED_FABRIC_MAGIC
            || fabric_magic == PRE_PHONATORY_FABRIC_MAGIC
            || fabric_magic == PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC
            || fabric_magic == CURRENT_FABRIC_MAGIC,
        "fabric magic"
    );
    let fabric_version = take_u16(fabric, &mut fc);
    assert_eq!(
        fabric_version,
        if fabric_magic == CURRENT_FABRIC_MAGIC {
            11
        } else if fabric_magic == PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC {
            10
        } else if fabric_magic == PRE_PHONATORY_FABRIC_MAGIC {
            9
        } else if fabric_magic == PRE_ARTICULATED_FABRIC_MAGIC {
            8
        } else {
            7
        },
        "fabric version"
    );
    let _generation = take_u64(fabric, &mut fc);
    let joint_len = take_u32(fabric, &mut fc) as usize;
    let cognitive_len = take_u32(fabric, &mut fc) as usize;
    if fabric_magic == CURRENT_FABRIC_MAGIC
        || fabric_magic == PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC
        || fabric_magic == PRE_PHONATORY_FABRIC_MAGIC
        || fabric_magic == PRE_ARTICULATED_FABRIC_MAGIC
    {
        let _vestibular_anatomy = take(fabric, &mut fc, FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES);
        let _canal_state = take(fabric, &mut fc, CANAL_STATE_BYTES);
        let _vestibular_source_tick = take_u64(fabric, &mut fc);
    }
    let mut articulated_body = None;
    if fabric_magic == CURRENT_FABRIC_MAGIC
        || fabric_magic == PRE_ACOUSTIC_FLIGHT_FABRIC_MAGIC
        || fabric_magic == PRE_PHONATORY_FABRIC_MAGIC
    {
        let body_bytes = if fabric_magic == PRE_PHONATORY_FABRIC_MAGIC {
            ARTICULATED_BODY_STATE_BYTES
        } else {
            ArticulatedBodyState::encoded_length_from_prefix(&fabric[fc..])
                .expect("articulated body prefix")
        };
        let body = take(fabric, &mut fc, body_bytes);
        articulated_body = Some(ArticulatedBodyState::decode(body).expect("articulated body"));
    }
    if fabric_magic == CURRENT_FABRIC_MAGIC {
        let acoustic_len = take_u32(fabric, &mut fc) as usize;
        let _in_flight_acoustic = take(fabric, &mut fc, acoustic_len);
    }
    let _joint = take(fabric, &mut fc, joint_len);
    let cognitive = take(fabric, &mut fc, cognitive_len).to_vec();
    assert_eq!(fc, fabric.len(), "fabric trailing bytes");
    (organism_tick, cognitive, articulated_body)
}

pub(super) fn parse_envelope(bytes: &[u8]) -> (u64, Vec<u8>) {
    let (organism_tick, cognitive, _) = parse_envelope_with_body(bytes);
    (organism_tick, cognitive)
}

#[derive(Default)]
struct LaneTotals {
    fuel: u128,
    spent: u128,
    heat: u128,
    fuel_capacity: u128,
    min_neuron_fuel: Option<u128>,
    max_neuron_fuel: Option<u128>,
}

impl LaneTotals {
    fn add(&mut self, fuel: u128, spent: u128, heat: u128, fuel_capacity: u128) {
        self.fuel += fuel;
        self.spent += spent;
        self.heat += heat;
        self.fuel_capacity += fuel_capacity;
        self.min_neuron_fuel = Some(self.min_neuron_fuel.map_or(fuel, |m| m.min(fuel)));
        self.max_neuron_fuel = Some(self.max_neuron_fuel.map_or(fuel, |m| m.max(fuel)));
    }

    fn to_json(&self) -> Value {
        json!({
            "fuel": self.fuel.to_string(),
            "spent": self.spent.to_string(),
            "heat": self.heat.to_string(),
            "fuel_capacity": self.fuel_capacity.to_string(),
            "min_neuron_fuel": self.min_neuron_fuel.map(|v| v.to_string()),
            "max_neuron_fuel": self.max_neuron_fuel.map(|v| v.to_string()),
        })
    }
}

fn cohort_json(cohort: &super::ResidentReachedCohort) -> Value {
    let anatomies = cohort.anatomy.neuron_anatomies();
    let mounts = cohort
        .anatomy
        .mounts()
        .iter()
        .zip(cohort.anatomy.neuron_lineages())
        .zip(anatomies)
        .zip(cohort.state.neurons())
        .map(|(((mount, lineage), anatomy), state)| {
            let capacitance = anatomy.capacitance().picofarads();
            let potential = state
                .membrane_state()
                .potential_millivolts(anatomy.capacitance())
                .expect("probe membrane potential");
            let psi_winding_counts =
                state
                    .psi
                    .rings()
                    .iter()
                    .fold([0_u64; 3], |mut counts, ring| {
                        counts[usize::from((ring.winding() as i8 + 1) as u8)] += 1;
                        counts
                    });
            json!({
                "lineage": lineage
                    .iter()
                    .map(|byte| format!("{byte:02x}"))
                    .collect::<String>(),
                "layer": mount.place().layer(),
                "topology_index": mount.place().topology_index(),
                "source_site": mount.source_site().map(|site| format!("{:?}", site)),
                "gate_population": anatomy.gate_population().to_string(),
                "open_gate_population": state.gate.open_population().to_string(),
                "intracellular_carriers": state.carrier_reservoirs().intracellular().to_string(),
                "extracellular_carriers": state.carrier_reservoirs().extracellular().to_string(),
                "psi_winding_counts": {
                    "negative": psi_winding_counts[0],
                    "quiescent": psi_winding_counts[1],
                    "positive": psi_winding_counts[2],
                },
                "capacitance_picofarads": exact_json(capacitance),
                "membrane_potential_millivolts": exact_json(potential),
                "gate_reversal_potential_millivolts": exact_json(
                    anatomy.gate_reversal_potential_millivolts(),
                ),
            })
        })
        .collect::<Vec<_>>();
    let fluid_anatomy =
        ReachedRecoveryFluidAnatomy::derive(anatomies).expect("derive fluid anatomy");
    let (fuel_capacity, spent_capacity, heat_capacity) =
        fluid_anatomy.reservoir_anatomy().capacities();
    let (fuel, spent, heat) = cohort.state.recovery_fluid().physical_parts();

    let mut psi = LaneTotals::default();
    let mut gate = LaneTotals::default();
    let mut plastic = LaneTotals::default();
    let mut psi_dissipated = 0u128;
    let mut psi_dissipation_capacity = 0u128;
    let mut gate_dissipated = 0u128;
    let mut gate_dissipation_capacity = 0u128;
    let mut plastic_dissipated = 0u128;
    let mut plastic_dissipation_capacity = 0u128;
    let mut dna_substrate = 0u128;
    let mut dna_fuel = 0u128;
    let mut dna_product = 0u128;
    let mut dna_waste = 0u128;

    let mut gate_open_population = 0u128;
    let mut neurons_with_open_gates = 0usize;
    let mut neurons_with_nonzero_residue = 0usize;
    let mut residues: Vec<String> = Vec::new();
    let mut neurons_owing_return_work = 0usize;
    let mut return_work_residues: Vec<String> = Vec::new();
    for (anatomy, state) in anatomies.iter().zip(cohort.state.neurons().iter()) {
        gate_open_population += state.gate.open_population();
        if state.gate.open_population() != 0 {
            neurons_with_open_gates += 1;
        }
        let residue = state.receptor_quantum_residue.energy();
        if !residue.is_zero() {
            neurons_with_nonzero_residue += 1;
        }
        residues.push(format!("{}/{}", residue.numer(), residue.denom()));
        let (owed_numerator, owed_denominator) = state.membrane_return_work_residue.parts();
        if owed_numerator != 0 {
            neurons_owing_return_work += 1;
        }
        return_work_residues.push(format!("{owed_numerator}/{owed_denominator}"));
        let _ = anatomy;
    }
    for (anatomy, state) in anatomies.iter().zip(cohort.state.neurons().iter()) {
        for index in 0..anatomy.psi_ring_count() {
            let address = RecoveryLaneAddress::Psi(index);
            let lane_state = state.recovery.lane(address).expect("psi lane state");
            let lane_anatomy = anatomy
                .recovery_anatomy()
                .lane(address)
                .expect("psi lane anatomy");
            let (lane_fuel, lane_spent, lane_heat) = lane_state.physical_parts();
            // Aggregate psi lanes per neuron; min/max here is per-lane.
            psi.add(
                lane_fuel,
                lane_spent,
                lane_heat,
                lane_anatomy.capacities().0,
            );
            psi_dissipation_capacity += anatomy
                .probe_psi_ring_dissipation_capacity_quanta(index)
                .expect("psi ring capacity");
        }
        for ring in state.psi.rings() {
            psi_dissipated += ring.dissipated_quanta();
        }
        {
            let lane_state = state
                .recovery
                .lane(RecoveryLaneAddress::Gate)
                .expect("gate lane state");
            let lane_anatomy = anatomy
                .recovery_anatomy()
                .lane(RecoveryLaneAddress::Gate)
                .expect("gate lane anatomy");
            let (lane_fuel, lane_spent, lane_heat) = lane_state.physical_parts();
            gate.add(
                lane_fuel,
                lane_spent,
                lane_heat,
                lane_anatomy.capacities().0,
            );
            gate_dissipated += state.gate.dissipated_quanta();
            gate_dissipation_capacity += anatomy.gate_dissipation_capacity_quanta();
        }
        {
            let lane_state = state
                .recovery
                .lane(RecoveryLaneAddress::Plastic)
                .expect("plastic lane state");
            let lane_anatomy = anatomy
                .recovery_anatomy()
                .lane(RecoveryLaneAddress::Plastic)
                .expect("plastic lane anatomy");
            let (lane_fuel, lane_spent, lane_heat) = lane_state.physical_parts();
            plastic.add(
                lane_fuel,
                lane_spent,
                lane_heat,
                lane_anatomy.capacities().0,
            );
            plastic_dissipated += state.plastic.probe_dissipated_quanta();
            plastic_dissipation_capacity += anatomy.probe_plastic_dissipation_capacity_quanta();
        }
        let (substrate, dna_lane_fuel, product, waste) = state.dna_expression.probe_parts();
        dna_substrate += substrate;
        dna_fuel += dna_lane_fuel;
        dna_product += product;
        dna_waste += waste;
    }

    // Law 2 diagnosis (measurement only): the exact separated membrane charge
    // of every neuron and the retained sub-charge phase of every authored
    // chain contact, so an external driver can see whether inter-neuron
    // settlement is still moving WHOLE elementary charges or only carrying
    // sub-charge phase.
    let membrane_separated_elementary_charges = cohort
        .state
        .neurons()
        .iter()
        .map(|state| {
            state
                .membrane_state()
                .separated_elementary_charges()
                .to_string()
        })
        .collect::<Vec<String>>();
    let contact_carrier_phases = cohort
        .state
        .electrical()
        .contact_states()
        .iter()
        .map(|contact| {
            let (numerator, denominator) = contact.carrier_phase().parts();
            format!("{numerator}/{denominator}")
        })
        .collect::<Vec<String>>();

    // Experience-evidence detail (measurement only): the sparse resident
    // indices the retention law actually persisted, so an external driver can see per
    // hop when the retained original appeared and whether it carries any
    // electrical participation.
    fn experience_json(evidence: Option<&super::ResidentExperienceEvidence>) -> Value {
        match evidence {
            None => json!(null),
            Some(evidence) => {
                let gate_work_count = evidence.gate_work_perturbed_neurons.count();
                let active_contact_count = evidence.active_electrical_contacts.count();
                let member_delta_count = evidence.retained_members().map(<[_]>::len);
                json!({
                    "gate_work_perturbed_count": gate_work_count,
                    "active_electrical_contact_count": active_contact_count,
                    "post_experience_rest": evidence.is_retained(),
                    "member_delta_count": member_delta_count,
                })
            }
        }
    }
    let pending_experience_detail = experience_json(cohort.pending_experience.as_ref());
    let retained_experience_detail = experience_json(cohort.retained_experience.as_ref());
    let pending_recurrence_detail = match cohort.pending_recurrence.as_ref() {
        None => json!(null),
        Some(evidence) => json!({
            "gate_work_perturbed_count": evidence
                .gate_work_perturbed_neurons
                .count(),
            "active_recurrence_contact_count": evidence
                .active_recurrence_contacts
                .count(),
        }),
    };

    let dark_rest_fuel_split = json!({
        "available": false,
        "reason": "retired mixed-unit authored feed; powered exact-energy contact not yet mounted"
    });

    // Recognition verdict (measurement only): replay EXACTLY the admission
    // decision `settle_resident_recurrence_interval` makes — same retained
    // experience, same learned state, same current cohort state, same
    // recurrence bits — and report the physics' own refusal variant instead
    // of inferring one.
    let recognition = match cohort.retained_experience.as_ref() {
        Some(retained) => {
            let recurrence = cohort.pending_recurrence.as_ref();
            let original =
                super::original_settlement(&cohort.anatomy, retained).expect("original settlement");
            let actual = super::recurrence_settlement(
                &cohort.anatomy,
                retained,
                &[],
                cohort.state.as_ref().clone(),
                recurrence.map_or_else(
                    || vec![None; cohort.anatomy.neuron_count()].into_boxed_slice(),
                    |evidence| {
                        evidence
                            .receptor_excitation_zeptojoules
                            .to_dense(cohort.anatomy.neuron_count())
                            .expect("canonical recurrence excitation indices")
                    },
                ),
                recurrence.map_or_else(
                    || vec![false; cohort.anatomy.neuron_count()].into_boxed_slice(),
                    |evidence| {
                        evidence
                            .gate_work_perturbed_neurons
                            .to_dense(cohort.anatomy.neuron_count())
                            .expect("canonical recurrence gate-work indices")
                    },
                ),
                recurrence.map_or_else(
                    || vec![false; cohort.anatomy.contact_count()].into_boxed_slice(),
                    |evidence| {
                        evidence
                            .active_recurrence_contacts
                            .to_dense(cohort.anatomy.contact_count())
                            .expect("canonical recurrence contact indices")
                    },
                ),
            )
            .expect("recurrence settlement");
            let verdict = match crate::physical_mosaic::admit_physical_mosaic(
                &cohort.anatomy,
                &original,
                &actual,
            ) {
                Ok(_) => "admitted".to_string(),
                Err(error) => format!("{error:?}"),
            };
            json!({
                "retained_experience": true,
                "pending_recurrence": recurrence.is_some(),
                "pending_experience": cohort.pending_experience.is_some(),
                "verdict": verdict,
            })
        }
        None => json!({
            "retained_experience": cohort.retained_experience.is_some(),
            "pending_recurrence": cohort.pending_recurrence.is_some(),
            "pending_experience": cohort.pending_experience.is_some(),
            "verdict": "no retained experience",
        }),
    };

    json!({
        "neuron_count": cohort.anatomy.neuron_count(),
        "mounts": mounts,
        "recognition": recognition,
        "pending_experience_detail": pending_experience_detail,
        "retained_experience_detail": retained_experience_detail,
        "pending_recurrence_detail": pending_recurrence_detail,
        "membrane_separated_elementary_charges": membrane_separated_elementary_charges,
        "contact_carrier_phases": contact_carrier_phases,
        "gate_state": {
            "total_open_population": gate_open_population.to_string(),
            "neurons_with_open_gates": neurons_with_open_gates,
        },
        "receptor_quantum_residues": {
            "neurons_with_nonzero_residue": neurons_with_nonzero_residue,
            "residues_zeptojoules": residues,
        },
        // The sub-quantum membrane-return work each neuron has done and not
        // yet been billed a whole dissipation quantum for (exact rest-cost
        // law, 2026-08-06).  Bounded by the gate's own dissipation quantum.
        "membrane_return_work_residues": {
            "neurons_owing_return_work": neurons_owing_return_work,
            "owed_zeptojoules": return_work_residues,
        },
        "reservoir": {
            "available_energy_zeptojoules": exact_json(fuel),
            "spent_energy_zeptojoules": exact_json(spent),
            "thermal_energy_zeptojoules": exact_json(heat),
            "available_energy_capacity_zeptojoules": exact_json(fuel_capacity),
            "spent_energy_capacity_zeptojoules": exact_json(spent_capacity),
            "thermal_energy_capacity_zeptojoules": exact_json(heat_capacity),
        },
        "measured_fed_dark_rest_fuel_split": dark_rest_fuel_split,
        "lanes": {
            "psi": psi.to_json(),
            "gate": gate.to_json(),
            "plastic": plastic.to_json(),
        },
        "dissipation": {
            "psi_dissipated": psi_dissipated.to_string(),
            "psi_capacity": psi_dissipation_capacity.to_string(),
            "gate_dissipated": gate_dissipated.to_string(),
            "gate_capacity": gate_dissipation_capacity.to_string(),
            "plastic_dissipated": plastic_dissipated.to_string(),
            "plastic_capacity": plastic_dissipation_capacity.to_string(),
        },
        "dna_expression": {
            "substrate_quanta": dna_substrate.to_string(),
            "fuel_quanta": dna_fuel.to_string(),
            "expressed_product_quanta": dna_product.to_string(),
            "waste_quanta": dna_waste.to_string(),
        },
    })
}

fn exact_json(value: ExactRational) -> Value {
    let (numerator, denominator) = value.parts();
    json!({
        "numerator": numerator.to_string(),
        "denominator": denominator.to_string(),
    })
}

fn wide_exact_json(value: &BigRational) -> Value {
    json!({
        "numerator": value.numer().to_string(),
        "denominator": value.denom().to_string(),
    })
}

/// Measurement-only lower-bound model for the articulated body's missing
/// passive tissue.  This is deliberately not a production implementation:
/// it asks which exact, elapsed-time laws can release the copied body's
/// stopped axes without overshoot, and where repeated motor work overwhelms
/// that return.  One native mechanical step is one millisecond.  Backward
/// Euler is used because each step is an exact convex combination of the
/// current position and the anatomical neutral; it cannot manufacture an
/// overshoot.  Motor carriers remain explicit signed lattice displacements.
fn copied_body_passive_mechanics_range_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let time_constants_ms = [1_i64, 2, 4, 8, 16, 32, 64, 128, 256, 512];
    let observation_durations_ms = [1_u64, 4, 16, 64, 250, 1_000];
    let sustained_carriers_per_ms = [1_i64, 2, 4, 8, 16];
    let powers = |tau_ms: i64, elapsed_ms: u64| {
        let exponent = u32::try_from(elapsed_ms).expect("bounded harness duration");
        (
            BigInt::from(tau_ms).pow(exponent),
            BigInt::from(tau_ms + 1).pow(exponent),
        )
    };
    let exact_position_json =
        |position: i32, neutral: i32, decay_numerator: &BigInt, decay_denominator: &BigInt| {
            let numerator = BigInt::from(neutral) * decay_denominator
                + BigInt::from(position - neutral) * decay_numerator;
            json!({
                "numerator": numerator.to_string(),
                "denominator": decay_denominator.to_string(),
                "form": "unreduced exact rational",
            })
        };
    let moved_at_least_one =
        |position: i32, neutral: i32, decay_numerator: &BigInt, decay_denominator: &BigInt| {
            BigInt::from((i64::from(position) - i64::from(neutral)).unsigned_abs())
                * (decay_denominator - decay_numerator)
                >= *decay_denominator
        };

    let copied_axes = BODY_AXES
        .into_iter()
        .map(|axis| {
            let anatomy = axis.anatomy();
            (axis, anatomy, body.axis(axis))
        })
        .collect::<Vec<_>>();
    let stopped_non_neutral_axes = copied_axes
        .iter()
        .filter(|(_, anatomy, position)| {
            (*position == anatomy.minimum || *position == anatomy.maximum)
                && *position != anatomy.neutral
        })
        .map(|(axis, _, _)| format!("{axis:?}"))
        .collect::<Vec<_>>();

    let mut candidates = Vec::new();
    for tau_ms in time_constants_ms {
        let (decay_250_numerator, decay_250_denominator) = powers(tau_ms, 250);
        let (decay_64_numerator, decay_64_denominator) = powers(tau_ms, 64);
        let (decay_186_numerator, decay_186_denominator) = powers(tau_ms, 186);
        let (decay_2_000_numerator, decay_2_000_denominator) = powers(tau_ms, 2_000);
        let mut invariant_failures = Vec::new();
        let mut stopped_release = Vec::new();
        let mut first_visible_release_ms = Vec::new();
        if decay_250_numerator != &decay_64_numerator * &decay_186_numerator
            || decay_250_denominator != &decay_64_denominator * &decay_186_denominator
        {
            invariant_failures.push("elapsed_composition_failed".to_string());
        }
        for (axis, anatomy, predecessor) in &copied_axes {
            if (*predecessor == anatomy.minimum || *predecessor == anatomy.maximum)
                && *predecessor != anatomy.neutral
            {
                stopped_release.push(json!({
                    "axis": format!("{axis:?}"),
                    "predecessor": predecessor,
                    "neutral": anatomy.neutral,
                    "after_250_ms": exact_position_json(
                        *predecessor,
                        anatomy.neutral,
                        &decay_250_numerator,
                        &decay_250_denominator,
                    ),
                    "released_at_least_one_position_quantum": moved_at_least_one(
                        *predecessor,
                        anatomy.neutral,
                        &decay_250_numerator,
                        &decay_250_denominator,
                    ),
                }));
                let (at_1_000_numerator, at_1_000_denominator) = powers(tau_ms, 1_000);
                let first = if !moved_at_least_one(
                    *predecessor,
                    anatomy.neutral,
                    &at_1_000_numerator,
                    &at_1_000_denominator,
                ) {
                    None
                } else {
                    let mut below = 0_u64;
                    let mut at_or_above = 1_000_u64;
                    while below + 1 < at_or_above {
                        let midpoint = below + (at_or_above - below) / 2;
                        let (numerator, denominator) = powers(tau_ms, midpoint);
                        if moved_at_least_one(
                            *predecessor,
                            anatomy.neutral,
                            &numerator,
                            &denominator,
                        ) {
                            at_or_above = midpoint;
                        } else {
                            below = midpoint;
                        }
                    }
                    Some(at_or_above)
                };
                first_visible_release_ms.push(json!({
                    "axis": format!("{axis:?}"),
                    "first_at_least_one_quantum_ms": first,
                }));
            }
        }

        let zero_toward_maximum_span_axes = BODY_AXES
            .into_iter()
            .filter(|axis| axis.anatomy().neutral == axis.anatomy().maximum)
            .map(|axis| format!("{axis:?}"))
            .collect::<Vec<_>>();
        let neutral_pulse = json!({
            "toward_maximum_zero_span_axes": zero_toward_maximum_span_axes,
            "shared_nonzero_span_displacement_after_one_ms": {
                "numerator": tau_ms.to_string(),
                "denominator": (tau_ms + 1).to_string(),
            },
            "shared_nonzero_span_displacement_after_250_ms": {
                "numerator": decay_250_numerator.to_string(),
                "denominator": decay_250_denominator.to_string(),
            },
            "remains_exactly_nonzero_after_one_ms": true,
        });

        let mut sustained = Vec::new();
        for carriers_per_ms in sustained_carriers_per_ms {
            for direction in [-1_i64, 1_i64] {
                let mut hit_stop = Vec::new();
                let mut minimum_positive_span = None::<i32>;
                for (axis, anatomy, _) in &copied_axes {
                    let directional_span = if direction.is_negative() {
                        anatomy.neutral - anatomy.minimum
                    } else {
                        anatomy.maximum - anatomy.neutral
                    };
                    if directional_span == 0 {
                        hit_stop.push(format!("{axis:?}:zero_directional_span"));
                        continue;
                    }
                    minimum_positive_span = Some(
                        minimum_positive_span
                            .map_or(directional_span, |current| current.min(directional_span)),
                    );
                    let displacement_numerator = BigInt::from(tau_ms * carriers_per_ms)
                        * (&decay_2_000_denominator - &decay_2_000_numerator);
                    if displacement_numerator
                        >= BigInt::from(directional_span) * &decay_2_000_denominator
                    {
                        hit_stop.push(format!("{axis:?}"));
                    }
                }
                let maximum_normalized_displacement = minimum_positive_span.map(|span| {
                    json!({
                        "numerator": (BigInt::from(tau_ms * carriers_per_ms)
                            * (&decay_2_000_denominator - &decay_2_000_numerator)).to_string(),
                        "denominator": (BigInt::from(span)
                            * &decay_2_000_denominator).to_string(),
                        "minimum_positive_directional_span": span,
                    })
                });
                sustained.push(json!({
                    "carriers_per_ms": carriers_per_ms,
                    "direction": if direction.is_negative() { "toward_minimum" } else { "toward_maximum" },
                    "duration_ms": 2_000,
                    "would_press_anatomical_stop_axes_without_clamp": hit_stop,
                    "maximum_normalized_displacement": maximum_normalized_displacement,
                }));
            }
        }

        let duration_samples = observation_durations_ms
            .into_iter()
            .map(|elapsed_ms| {
                let (decay_numerator, decay_denominator) = powers(tau_ms, elapsed_ms);
                let visibly_released_stops = copied_axes
                    .iter()
                    .filter(|(_, anatomy, predecessor)| {
                        (*predecessor == anatomy.minimum || *predecessor == anatomy.maximum)
                            && *predecessor != anatomy.neutral
                    })
                    .filter(|(_, anatomy, predecessor)| {
                        moved_at_least_one(
                            *predecessor,
                            anatomy.neutral,
                            &decay_numerator,
                            &decay_denominator,
                        )
                    })
                    .count();
                json!({
                    "elapsed_ms": elapsed_ms,
                    "visibly_released_stopped_axes": visibly_released_stops,
                })
            })
            .collect::<Vec<_>>();
        candidates.push(json!({
            "passive_time_constant_ms": tau_ms,
            "invariant_failures": invariant_failures,
            "stopped_release": stopped_release,
            "first_visible_release": first_visible_release_ms,
            "duration_samples": duration_samples,
            "neutral_one_carrier_pulse": neutral_pulse,
            "sustained_drive": sustained,
        }));
    }
    json!({
        "production_compiled": false,
        "model_authority": "measurement-only lower bound; not authorized production mechanics",
        "native_mechanical_step_microseconds": 1_000,
        "equation": "q[n+1] = clamp((tau*(q[n]+u[n]) + neutral)/(tau+1))",
        "evaluation": "exact integer powers and inequalities; no floating point and no rational normalization",
        "copied_axis_count": copied_axes.len(),
        "copied_stopped_non_neutral_axes": stopped_non_neutral_axes,
        "time_constants_ms": time_constants_ms,
        "observation_durations_ms": observation_durations_ms,
        "sustained_carriers_per_ms": sustained_carriers_per_ms,
        "candidate_count": candidates.len(),
        "candidates": candidates,
    })
}

#[derive(Clone)]
struct ProbeAntagonistTissue {
    position: i64,
    minimum: i64,
    neutral: i64,
    maximum: i64,
    activation_units: [u128; 2],
    admitted_work: BigRational,
    dissipated_work: BigRational,
    stopped_load_quanta: u128,
}

impl ProbeAntagonistTissue {
    fn from_axis(body: &ArticulatedBodyState, axis: BodyAxis) -> Self {
        let anatomy = axis.anatomy();
        Self {
            position: i64::from(body.axis(axis)),
            minimum: i64::from(anatomy.minimum),
            neutral: i64::from(anatomy.neutral),
            maximum: i64::from(anatomy.maximum),
            activation_units: [0; 2],
            admitted_work: BigRational::zero(),
            dissipated_work: BigRational::zero(),
            stopped_load_quanta: 0,
        }
    }

    fn at_neutral(axis: BodyAxis) -> Self {
        let anatomy = axis.anatomy();
        Self {
            position: i64::from(anatomy.neutral),
            minimum: i64::from(anatomy.minimum),
            neutral: i64::from(anatomy.neutral),
            maximum: i64::from(anatomy.maximum),
            activation_units: [0; 2],
            admitted_work: BigRational::zero(),
            dissipated_work: BigRational::zero(),
            stopped_load_quanta: 0,
        }
    }

    fn direction_index(direction: BodyEffectorDirection) -> usize {
        match direction {
            BodyEffectorDirection::TowardMinimum => 0,
            BodyEffectorDirection::TowardMaximum => 1,
        }
    }

    fn directional_span(&self, direction: BodyEffectorDirection) -> u128 {
        match direction {
            BodyEffectorDirection::TowardMinimum => (self.neutral - self.minimum) as u128,
            BodyEffectorDirection::TowardMaximum => (self.maximum - self.neutral) as u128,
        }
    }

    fn admit(
        &mut self,
        direction: BodyEffectorDirection,
        carriers: u128,
        work_per_carrier: &BigRational,
        activation_lifetime_ms: u128,
        coupling_numerator: u128,
        coupling_denominator: u128,
    ) {
        let total_work = work_per_carrier * BigInt::from(carriers);
        self.admitted_work += &total_work;
        // Work custody closes at this boundary. The terminal activation is a
        // bounded material conformation (integer cross-bridge quanta), not a
        // repeatedly divided rational energy reservoir. Retaining a rational
        // fraction per millisecond was rejected because its denominator grew
        // with lifetime. The exact released work is therefore dissipated once
        // by the body transaction while the admitted conformation persists.
        self.dissipated_work += &total_work;
        let coupled_carriers = carriers.saturating_mul(coupling_numerator) / coupling_denominator;
        if coupled_carriers == 0 {
            self.stopped_load_quanta = self.stopped_load_quanta.saturating_add(carriers);
            return;
        }
        let index = Self::direction_index(direction);
        let capacity_units = self
            .directional_span(direction)
            .saturating_mul(activation_lifetime_ms);
        let requested_units = coupled_carriers.saturating_mul(activation_lifetime_ms);
        let available_units = capacity_units.saturating_sub(self.activation_units[index]);
        let admitted_units = requested_units.min(available_units);
        self.activation_units[index] = self.activation_units[index].saturating_add(admitted_units);
        self.stopped_load_quanta = self
            .stopped_load_quanta
            .saturating_add(carriers.saturating_sub(admitted_units / activation_lifetime_ms));
    }

    fn step_one_ms(&mut self, activation_lifetime_ms: u128, response_time_ms: u128) {
        let equivalent = |units: u128| {
            if units == 0 {
                0
            } else {
                1 + (units - 1) / activation_lifetime_ms
            }
        };
        let toward_minimum = equivalent(self.activation_units[0]);
        let toward_maximum = equivalent(self.activation_units[1]);
        let signed_activation = if toward_maximum >= toward_minimum {
            i128::try_from(toward_maximum - toward_minimum).expect("bounded positive activation")
        } else {
            -i128::try_from(toward_minimum - toward_maximum).expect("bounded negative activation")
        };
        let unclamped_target = i128::from(self.neutral) + signed_activation;
        let target =
            unclamped_target.clamp(i128::from(self.minimum), i128::from(self.maximum)) as i64;
        self.stopped_load_quanta = self
            .stopped_load_quanta
            .saturating_add(unclamped_target.abs_diff(i128::from(target)));
        let gap = self.position.abs_diff(target);
        if gap != 0 {
            let response = u64::try_from(response_time_ms).expect("bounded response time");
            let step = 1 + (gap - 1) / response;
            if target > self.position {
                self.position += i64::try_from(step).expect("bounded positive body step");
            } else {
                self.position -= i64::try_from(step).expect("bounded negative body step");
            }
        }
        for index in 0..2 {
            let before_units = self.activation_units[index];
            if before_units == 0 {
                continue;
            }
            let expired_units = 1 + (before_units - 1) / activation_lifetime_ms;
            self.activation_units[index] -= expired_units;
        }
    }

    fn work_closes(&self) -> bool {
        self.admitted_work == self.dissipated_work
    }
}

fn copied_body_antagonist_activation_range_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let activation_lifetimes_ms = [4_u128, 8, 16, 32, 64, 128, 256];
    let response_times_ms = [1_u128, 2, 4, 8, 16, 32, 64];
    let coupling_fractions = [(1_u128, 2_u128), (3, 4), (1, 1)];
    let learned = [
        (
            BodyAxis::VocalTractSection0Area,
            BodyEffectorDirection::TowardMaximum,
            BigRational::new(
                BigInt::parse_bytes(b"166767809696532795445407", 10).unwrap(),
                BigInt::parse_bytes(b"1100000000000000000000000", 10).unwrap(),
            ),
        ),
        (
            BodyAxis::VocalTractSection7Area,
            BodyEffectorDirection::TowardMinimum,
            BigRational::new(
                BigInt::parse_bytes(b"36616220961176220112151901", 10).unwrap(),
                BigInt::parse_bytes(b"237050000000000000000000000", 10).unwrap(),
            ),
        ),
    ];
    let stopped_axes = BODY_AXES
        .into_iter()
        .filter(|axis| {
            let anatomy = axis.anatomy();
            let position = body.axis(*axis);
            position != anatomy.neutral
                && (position == anatomy.minimum || position == anatomy.maximum)
        })
        .collect::<Vec<_>>();
    let mut candidates = Vec::new();
    let mut accepted_count = 0usize;
    for activation_lifetime_ms in activation_lifetimes_ms {
        for response_time_ms in response_times_ms {
            for (coupling_numerator, coupling_denominator) in coupling_fractions {
                let mut failures = Vec::new();
                let mut releases = Vec::new();
                for axis in &stopped_axes {
                    let mut tissue = ProbeAntagonistTissue::from_axis(body, *axis);
                    let predecessor = tissue.position;
                    tissue.step_one_ms(activation_lifetime_ms, response_time_ms);
                    let after_one = tissue.position;
                    let gap = predecessor.abs_diff(tissue.neutral);
                    if after_one == predecessor {
                        failures.push(format!("{axis:?}:did_not_release_in_one_ms"));
                    }
                    if gap > 1 && after_one == tissue.neutral {
                        failures.push(format!("{axis:?}:teleported_to_neutral"));
                    }
                    for _ in 1..16 {
                        tissue.step_one_ms(activation_lifetime_ms, response_time_ms);
                    }
                    if !tissue.work_closes() {
                        failures.push(format!("{axis:?}:legacy_release_work_did_not_close"));
                    }
                    releases.push(json!({
                        "axis": format!("{axis:?}"),
                        "predecessor": predecessor,
                        "after_one_ms": after_one,
                        "after_sixteen_ms": tissue.position,
                    }));
                }

                let mut pulse_results = Vec::new();
                for (axis, direction, work) in &learned {
                    let mut tissue = ProbeAntagonistTissue::at_neutral(*axis);
                    tissue.admit(
                        *direction,
                        1,
                        work,
                        activation_lifetime_ms,
                        coupling_numerator,
                        coupling_denominator,
                    );
                    let mut visible_ms = 0_u64;
                    let mut first_position = tissue.position;
                    for elapsed in 0..=512_u64 {
                        tissue.step_one_ms(activation_lifetime_ms, response_time_ms);
                        if elapsed == 0 {
                            first_position = tissue.position;
                        }
                        if tissue.position != tissue.neutral {
                            visible_ms += 1;
                        }
                    }
                    if first_position == tissue.neutral {
                        failures.push(format!("{axis:?}:one_carrier_twitch_absent"));
                    }
                    if !(16..=250).contains(&visible_ms) {
                        failures.push(format!(
                            "{axis:?}:visible_duration_{visible_ms}_outside_16_250"
                        ));
                    }
                    if tissue.position != tissue.neutral {
                        failures.push(format!("{axis:?}:did_not_return_by_512_ms"));
                    }
                    if !tissue.work_closes() {
                        failures.push(format!("{axis:?}:pulse_work_did_not_close"));
                    }
                    pulse_results.push(json!({
                        "axis": format!("{axis:?}"),
                        "direction": format!("{direction:?}"),
                        "first_position": first_position,
                        "visible_duration_ms": visible_ms,
                        "returned_by_512_ms": tissue.position == tissue.neutral,
                        "work_closed": tissue.work_closes(),
                    }));
                }

                let (axis, _, work) = &learned[0];
                let mut opposed = ProbeAntagonistTissue::at_neutral(*axis);
                opposed.admit(
                    BodyEffectorDirection::TowardMinimum,
                    8,
                    work,
                    activation_lifetime_ms,
                    coupling_numerator,
                    coupling_denominator,
                );
                opposed.admit(
                    BodyEffectorDirection::TowardMaximum,
                    8,
                    work,
                    activation_lifetime_ms,
                    coupling_numerator,
                    coupling_denominator,
                );
                opposed.step_one_ms(activation_lifetime_ms, response_time_ms);
                if opposed.position != opposed.neutral {
                    failures.push("opposed_drive_moved_axis".to_string());
                }
                if !opposed.work_closes() {
                    failures.push("opposed_drive_work_did_not_close".to_string());
                }

                let mut sustained = Vec::new();
                for rate in [1_u128, 2, 4, 8, 16] {
                    for (axis, direction, work) in &learned {
                        let mut tissue = ProbeAntagonistTissue::at_neutral(*axis);
                        for _ in 0..1_000 {
                            tissue.admit(
                                *direction,
                                rate,
                                work,
                                activation_lifetime_ms,
                                coupling_numerator,
                                coupling_denominator,
                            );
                            tissue.step_one_ms(activation_lifetime_ms, response_time_ms);
                        }
                        let at_stop =
                            tissue.position == tissue.minimum || tissue.position == tissue.maximum;
                        if rate == 1 && at_stop {
                            failures.push(format!("{axis:?}:one_per_ms_pinned"));
                        }
                        if at_stop && tissue.stopped_load_quanta == 0 {
                            failures.push(format!("{axis:?}:stop_without_load"));
                        }
                        if !tissue.work_closes() {
                            failures.push(format!("{axis:?}:sustained_work_did_not_close"));
                        }
                        sustained.push(json!({
                            "axis": format!("{axis:?}"),
                            "carriers_per_ms": rate.to_string(),
                            "position_after_1000_ms": tissue.position,
                            "at_stop": at_stop,
                            "stopped_load_quanta": tissue.stopped_load_quanta.to_string(),
                            "work_closed": tissue.work_closes(),
                        }));
                    }
                }

                let composition_axis = stopped_axes[0];
                let mut whole = ProbeAntagonistTissue::from_axis(body, composition_axis);
                let mut split = whole.clone();
                for _ in 0..250 {
                    whole.step_one_ms(activation_lifetime_ms, response_time_ms);
                }
                for _ in 0..64 {
                    split.step_one_ms(activation_lifetime_ms, response_time_ms);
                }
                for _ in 0..186 {
                    split.step_one_ms(activation_lifetime_ms, response_time_ms);
                }
                if whole.position != split.position
                    || whole.activation_units != split.activation_units
                    || whole.dissipated_work != split.dissipated_work
                {
                    failures.push("64_plus_186_did_not_equal_250".to_string());
                }
                let accepted = failures.is_empty();
                accepted_count += usize::from(accepted);
                candidates.push(json!({
                    "activation_lifetime_ms": activation_lifetime_ms.to_string(),
                    "response_time_ms": response_time_ms.to_string(),
                    "coupling": format!("{coupling_numerator}/{coupling_denominator}"),
                    "accepted": accepted,
                    "failures": failures,
                    "legacy_stop_release": releases,
                    "learned_one_carrier_pulses": pulse_results,
                    "opposed_drive_position": opposed.position,
                    "sustained_drive": sustained,
                    "duration_composition_position": whole.position,
                }));
            }
        }
    }
    json!({
        "production_compiled": false,
        "model_authority": "test-only bounded antagonist activation range",
        "native_mechanical_step_microseconds": 1_000,
        "activation_equation": "input carriers establish bounded terminal tension; ceil(active_units/lifetime) defines equilibrium displacement; active units and exact work decay together",
        "body_equation": "position advances ceil(|target-position|/response_time) toward clamped neutral-plus-net-antagonist-equilibrium",
        "work_equation": "admitted exact terminal work = retained activation work + explicit dissipated work",
        "activation_lifetimes_ms": activation_lifetimes_ms.map(|value| value.to_string()),
        "response_times_ms": response_times_ms.map(|value| value.to_string()),
        "coupling_fractions": coupling_fractions.map(|(n, d)| format!("{n}/{d}")),
        "candidate_count": candidates.len(),
        "accepted_count": accepted_count,
        "candidates": candidates,
    })
}

fn motor_reachability_json(state: &ResidentCognitiveFormationState) -> Value {
    let mut successor = state.clone();
    let externally_reached = successor
        .cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
                .filter_map(|(mount, lineage)| mount.source_site().is_some().then_some(*lineage))
        })
        .collect::<Vec<_>>();
    let motor_before = successor
        .cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
                .zip(cohort.state.neurons())
                .filter_map(|((mount, lineage), neuron)| {
                    (mount.place().layer() == 12).then_some((
                        *lineage,
                        neuron.gate.open_population(),
                        neuron.membrane_state().separated_elementary_charges(),
                    ))
                })
        })
        .collect::<Vec<_>>();
    let mut changed = std::collections::BTreeSet::new();
    let unchanged_developmental_resting_neuron_count = successor
        .resting_population
        .as_ref()
        .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
        .unwrap_or(0);
    let topology_index = successor.topology_index.clone();
    let observation = super::settle_internal_contact_interval(
        &mut successor.cohorts,
        &mut successor.electrical_fabric,
        &topology_index,
        None,
        &[],
        &externally_reached,
        &externally_reached,
        &externally_reached,
        &mut changed,
        successor.generation,
        unchanged_developmental_resting_neuron_count,
        &mut None,
        &std::collections::BTreeMap::new(),
        &[],
        &[],
        crate::exact_rational::ExactRational::integer(0),
        false,
    )
    .expect("maximal external frontier settles");
    let pending_post_quiescence_candidates = successor
        .cohorts
        .iter()
        .filter_map(|cohort| cohort.pending_experience.as_ref())
        .map(|experience| experience.pending_members().map_or(0, <[_]>::len))
        .sum::<usize>();
    let motor_after = successor
        .cohorts
        .iter()
        .flat_map(|cohort| {
            cohort
                .anatomy
                .mounts()
                .iter()
                .zip(cohort.anatomy.neuron_lineages())
                .zip(cohort.state.neurons())
                .filter_map(|((mount, lineage), neuron)| {
                    (mount.place().layer() == 12).then_some((
                        *lineage,
                        neuron.gate.open_population(),
                        neuron.membrane_state().separated_elementary_charges(),
                    ))
                })
        })
        .collect::<Vec<_>>();
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    json!({
        "external_receptor_count": externally_reached.len(),
        "dsf_delivery_count": observation.dsf_delivery_count,
        "physically_changed_neuron_count": changed.len(),
        "emitted_fractal_count": 0,
        "pending_post_quiescence_candidate_count": pending_post_quiescence_candidates,
        "motor_before": motor_before.into_iter().map(|(lineage, gate, charge)| json!({
            "lineage": lineage_hex(lineage),
            "open_gate_population": gate.to_string(),
            "membrane_charge": charge.to_string(),
        })).collect::<Vec<_>>(),
        "motor_after": motor_after.into_iter().map(|(lineage, gate, charge)| json!({
            "lineage": lineage_hex(lineage),
            "open_gate_population": gate.to_string(),
            "membrane_charge": charge.to_string(),
        })).collect::<Vec<_>>(),
        "motor_unit_recruitments": observation.motor_unit_recruitments.into_iter().map(|event| json!({
            "lineage": lineage_hex(event.neuron_lineage),
            "topology_index": event.topology_index,
            "outward_elementary_carriers": event.outward_elementary_carriers.to_string(),
            "body_afferent_paths": event.body_afferent_paths.into_iter().map(|path| json!({
                "body_regulation_lineage": lineage_hex(path.body_regulation_lineage),
                "integration_lineage": lineage_hex(path.integration_lineage),
                "receptor_lineage": lineage_hex(path.receptor_lineage),
                "receptor_sense_layer": path.receptor_site.sense().declared_layer(),
                "receptor_topology_index": path.receptor_site.topology_index(),
                "sensor_id": path.receptor_site.sensor_id(),
                "substream_id": path.receptor_site.substream_id(),
            })).collect::<Vec<_>>(),
            "preparation_transfers": event.preparation_transfers.into_iter().map(|preparation| json!({
                "sender": lineage_hex(preparation.transfer.sender),
                "sender_layer": preparation.sender_layer,
                "receiver": lineage_hex(preparation.transfer.receiver),
                "parallel_ordinal": preparation.transfer.bond.parallel_ordinal(),
                "transferred_whole_carriers": preparation.transfer.transferred_whole_carriers.to_string(),
            })).collect::<Vec<_>>(),
        })).collect::<Vec<_>>(),
    })
}

fn mounted_neuron_electrical_json(
    state: &ResidentCognitiveFormationState,
    lineage: [u8; 16],
) -> Value {
    for cohort in &state.cohorts {
        for (((mount, candidate), anatomy), neuron) in cohort
            .anatomy
            .mounts()
            .iter()
            .zip(cohort.anatomy.neuron_lineages())
            .zip(cohort.anatomy.neuron_anatomies())
            .zip(cohort.state.neurons())
        {
            if *candidate != lineage {
                continue;
            }
            let potential = neuron
                .membrane_state()
                .potential_millivolts(anatomy.capacitance())
                .expect("range-probe potential");
            let pump = crate::complete_neuron::membrane_gradient_pump_charge_bound(
                anatomy,
                neuron,
                super::WORLD_MECHANICAL_TICK_MICROSECONDS,
            )
            .expect("range-probe pump bound");
            return json!({
                "layer": mount.place().layer(),
                "membrane_charge": neuron.separated_elementary_charges().to_string(),
                "capacitance_picofarads": exact_json(anatomy.capacitance().picofarads()),
                "membrane_potential_millivolts": exact_json(potential),
                "open_gate_population": neuron.gate.open_population().to_string(),
                "one_clock_active_pump_bound": pump.charges.to_string(),
            });
        }
    }
    panic!("range-probe lineage absent")
}

fn mounted_neuron_ternary_winding_state_json(
    state: &ResidentCognitiveFormationState,
    lineage: [u8; 16],
) -> Value {
    for cohort in &state.cohorts {
        let Some(neuron_index) = cohort
            .anatomy
            .neuron_lineages()
            .iter()
            .position(|candidate| *candidate == lineage)
        else {
            continue;
        };
        let ordered_windings = cohort.state.neurons()[neuron_index]
            .psi
            .rings()
            .iter()
            .map(|ring| ring.winding() as i8)
            .collect::<Vec<_>>();
        let counts = ordered_windings
            .iter()
            .fold([0_u64; 3], |mut counts, winding| {
                counts[usize::from((*winding + 1) as u8)] += 1;
                counts
            });
        return json!({
            "ordered_windings": ordered_windings,
            "summary_counts": {
                "negative": counts[0],
                "quiescent": counts[1],
                "positive": counts[2],
            },
        });
    }
    panic!("ternary-range lineage absent")
}

fn apply_probe_gradient_population(
    state: &mut ResidentCognitiveFormationState,
    lineage: [u8; 16],
    effective_population: u32,
) -> Value {
    if effective_population <= 1 {
        return json!({
            "effective_population": effective_population,
            "additional_interval_microseconds": 0,
            "returned_elementary_charges": "0",
            "pumped_elementary_charges": "0",
            "pump_work_zeptojoules": exact_json(ExactRational::integer(0)),
        });
    }
    let additional_interval_microseconds = super::WORLD_MECHANICAL_TICK_MICROSECONDS
        .checked_mul(effective_population - 1)
        .expect("probe population interval");
    for cohort in &mut state.cohorts {
        let Some(neuron_index) = cohort
            .anatomy
            .neuron_lineages()
            .iter()
            .position(|candidate| *candidate == lineage)
        else {
            continue;
        };
        let prepared = crate::reached_neuron_cohort::prepare_reached_cohort_membrane_pumps(
            &cohort.anatomy,
            &cohort.state,
            &[neuron_index],
            additional_interval_microseconds,
            ExactRational::integer(0),
        )
        .expect("probe population-gradient settlement");
        let observation =
            crate::reached_neuron_cohort::apply_prepared_reached_cohort_membrane_pumps(
                std::sync::Arc::make_mut(&mut cohort.state),
                prepared,
            );
        return json!({
            "effective_population": effective_population,
            "additional_interval_microseconds": additional_interval_microseconds,
            "returned_elementary_charges": observation.returned_elementary_charges.to_string(),
            "pumped_elementary_charges": observation.pumped_elementary_charges.to_string(),
            "pump_work_zeptojoules": exact_json(
                observation.membrane_gradient_work_zeptojoules,
            ),
            "environment_energy_delivered_zeptojoules": exact_json(
                observation.environment_energy_delivered_zeptojoules,
            ),
        });
    }
    panic!("probe population-gradient lineage absent")
}

/// Test the one existing area-mismatch hypothesis without changing production
/// physics. One ordinary one-channel pump integrated for `N` identical channel
/// times is the current law's exact static-predecessor equivalent of `N`
/// parallel identical pump sites over one clock; its reversal-side and finite
/// reservoir bounds remain intact. The range is diagnostic only. It asks
/// whether restoring membrane-area-proportional gradient throughput can turn
/// an already-physical causal seed into forward L11 -> L12 carrier transport.
fn motor_bridge_gradient_population_range_json(state: &ResidentCognitiveFormationState) -> Value {
    let topology = state.topology_index.clone();
    let mut routes = state
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = state.electrical_fabric.lineages()[left];
            let right_lineage = state.electrical_fabric.lineages()[right];
            match (
                topology.layer_of(left_lineage),
                topology.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some((left_lineage, right_lineage)),
                (Some(12), Some(11)) => Some((right_lineage, left_lineage)),
                _ => None,
            }
        })
        .collect::<Vec<_>>();
    routes.sort_unstable();
    routes.dedup();
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let populations = [1_u32, 4, 16, 64, 256, 1_024, 4_096, 8_192];
    let mut route_results = Vec::new();
    for (ordering, motor) in routes {
        let mut founders = state
            .electrical_fabric
            .contact_endpoints()
            .filter_map(|(left, right)| {
                let left_lineage = state.electrical_fabric.lineages()[left];
                let right_lineage = state.electrical_fabric.lineages()[right];
                if left_lineage == ordering
                    && matches!(topology.layer_of(right_lineage), Some(7 | 10))
                {
                    Some(right_lineage)
                } else if right_lineage == ordering
                    && matches!(topology.layer_of(left_lineage), Some(7 | 10))
                {
                    Some(left_lineage)
                } else {
                    None
                }
            })
            .collect::<Vec<_>>();
        founders.sort_unstable();
        founders.dedup();
        let modes = [
            ("ordering_seeded", vec![ordering]),
            ("founding_pair_seeded", founders.clone()),
        ];
        let mut mode_results = Vec::new();
        for (mode, seeds) in modes {
            let mut population_results = Vec::new();
            for effective_population in populations {
                let mut successor = state.clone();
                let mut residency = None;
                let mut samples = Vec::new();
                for active_clock in 1_u64..=3 {
                    let pump = seeds
                        .iter()
                        .copied()
                        .map(|lineage| {
                            json!({
                                "lineage": lineage_hex(lineage),
                                "settlement": apply_probe_gradient_population(
                                    &mut successor,
                                    lineage,
                                    effective_population,
                                ),
                            })
                        })
                        .collect::<Vec<_>>();
                    let mut changed = std::collections::BTreeSet::new();
                    let unchanged_developmental_resting_neuron_count = successor
                        .resting_population
                        .as_ref()
                        .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
                        .unwrap_or(0);
                    let observation = super::settle_internal_contact_interval(
                        &mut successor.cohorts,
                        &mut successor.electrical_fabric,
                        &topology,
                        None,
                        &[],
                        &seeds,
                        &seeds,
                        &seeds,
                        &mut changed,
                        successor.generation + active_clock,
                        unchanged_developmental_resting_neuron_count,
                        &mut residency,
                        &std::collections::BTreeMap::new(),
                        &[],
                        &[],
                        ExactRational::integer(0),
                        false,
                    )
                    .expect("population-range contact settlement");
                    let signed_transfer = observation
                        .settled_directed_transfers
                        .iter()
                        .filter_map(|transfer| {
                            if transfer.sender == ordering && transfer.receiver == motor {
                                i128::try_from(transfer.transferred_whole_carriers).ok()
                            } else if transfer.sender == motor && transfer.receiver == ordering {
                                i128::try_from(transfer.transferred_whole_carriers)
                                    .ok()
                                    .and_then(i128::checked_neg)
                            } else {
                                None
                            }
                        })
                        .sum::<i128>();
                    samples.push(json!({
                        "active_clock": active_clock,
                        "pump": pump,
                        "ordering": mounted_neuron_electrical_json(&successor, ordering),
                        "motor": mounted_neuron_electrical_json(&successor, motor),
                        "signed_ordering_to_motor_whole_carriers": signed_transfer.to_string(),
                        "motor_recruited": observation.motor_unit_recruitments
                            .iter()
                            .any(|event| event.neuron_lineage == motor),
                    }));
                }
                population_results.push(json!({
                    "effective_population": effective_population,
                    "samples": samples,
                }));
            }
            mode_results.push(json!({
                "mode": mode,
                "seed_lineages": seeds.into_iter().map(lineage_hex).collect::<Vec<_>>(),
                "population_results": population_results,
            }));
        }
        route_results.push(json!({
            "ordering_lineage": lineage_hex(ordering),
            "motor_lineage": lineage_hex(motor),
            "ordering_capacitance_picofarads": mounted_neuron_electrical_json(state, ordering)
                ["capacitance_picofarads"].clone(),
            "modes": mode_results,
        }));
    }
    json!({
        "retained_causal_frontier_span": 3,
        "effective_population_range": populations,
        "routes": route_results,
    })
}

/// Exercise every learned layer-11/layer-12 route in the exact copied body
/// across one through eight consecutive active ordering clocks. This is a
/// diagnostic range, not an authored stimulus and not production code: it
/// asks whether the already-existing neuron/pump/contact physics can ever
/// turn an active ordering endpoint into forward motor preparation within the
/// organism's retained three-frontier causal span. Quiet/background traffic
/// continues to settle exactly as it does in the copied body.
fn motor_bridge_active_range_json(state: &ResidentCognitiveFormationState) -> Value {
    let topology = state.topology_index.clone();
    let mut routes = state
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = state.electrical_fabric.lineages()[left];
            let right_lineage = state.electrical_fabric.lineages()[right];
            match (
                topology.layer_of(left_lineage),
                topology.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some((left_lineage, right_lineage)),
                (Some(12), Some(11)) => Some((right_lineage, left_lineage)),
                _ => None,
            }
        })
        .collect::<Vec<_>>();
    routes.sort_unstable();
    routes.dedup();

    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let mut results = Vec::new();
    for (ordering, motor) in routes {
        let mut successor = state.clone();
        let mut causal_seeds = successor
            .electrical_fabric
            .contact_endpoints()
            .filter_map(|(left, right)| {
                let left_lineage = successor.electrical_fabric.lineages()[left];
                let right_lineage = successor.electrical_fabric.lineages()[right];
                if left_lineage == ordering
                    && matches!(topology.layer_of(right_lineage), Some(7 | 10))
                {
                    Some(right_lineage)
                } else if right_lineage == ordering
                    && matches!(topology.layer_of(left_lineage), Some(7 | 10))
                {
                    Some(left_lineage)
                } else {
                    None
                }
            })
            .collect::<Vec<_>>();
        causal_seeds.sort_unstable();
        causal_seeds.dedup();
        let mut residency = None;
        let mut samples = vec![json!({
            "active_clock": 0,
            "ordering": mounted_neuron_electrical_json(&successor, ordering),
            "motor": mounted_neuron_electrical_json(&successor, motor),
            "signed_ordering_to_motor_whole_carriers": "0",
            "motor_recruited": false,
        })];
        for active_clock in 1_u64..=8 {
            let mut changed = std::collections::BTreeSet::new();
            let unchanged_developmental_resting_neuron_count = successor
                .resting_population
                .as_ref()
                .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
                .unwrap_or(0);
            let topology = successor.topology_index.clone();
            let observation = super::settle_internal_contact_interval(
                &mut successor.cohorts,
                &mut successor.electrical_fabric,
                &topology,
                None,
                &[],
                &causal_seeds,
                &causal_seeds,
                &causal_seeds,
                &mut changed,
                successor.generation + active_clock,
                unchanged_developmental_resting_neuron_count,
                &mut residency,
                &std::collections::BTreeMap::new(),
                &[],
                &[],
                ExactRational::integer(0),
                false,
            )
            .expect("active ordering range settles");
            let signed_transfer = observation
                .settled_directed_transfers
                .iter()
                .filter_map(|transfer| {
                    if transfer.sender == ordering && transfer.receiver == motor {
                        i128::try_from(transfer.transferred_whole_carriers).ok()
                    } else if transfer.sender == motor && transfer.receiver == ordering {
                        i128::try_from(transfer.transferred_whole_carriers)
                            .ok()
                            .and_then(i128::checked_neg)
                    } else {
                        None
                    }
                })
                .sum::<i128>();
            let motor_recruited = observation
                .motor_unit_recruitments
                .iter()
                .any(|event| event.neuron_lineage == motor);
            samples.push(json!({
                "active_clock": active_clock,
                "ordering": mounted_neuron_electrical_json(&successor, ordering),
                "motor": mounted_neuron_electrical_json(&successor, motor),
                "signed_ordering_to_motor_whole_carriers": signed_transfer.to_string(),
                "motor_recruited": motor_recruited,
                "changed_neuron_count": changed.len(),
            }));
        }
        results.push(json!({
            "ordering_lineage": lineage_hex(ordering),
            "motor_lineage": lineage_hex(motor),
            "causal_seed_lineages": causal_seeds.into_iter().map(lineage_hex).collect::<Vec<_>>(),
            "samples": samples,
        }));
    }
    json!({
        "maximum_active_clocks": 8,
        "retained_causal_frontier_span": 3,
        "routes": results,
    })
}

/// Follow only the copied body's own retained electrical frontier.  Unlike the
/// older bridge ranges this supplies no authored or synthetic seed: the first
/// clock begins with exactly the persisted active frontier, later clocks begin
/// with only the physical successor frontier produced by the preceding clock.
/// Three clocks match the organism's bounded retained causal-frontier span.
fn retained_frontier_motor_range_json(
    state: &ResidentCognitiveFormationState,
    initial_articulated_body: Option<&ArticulatedBodyState>,
    maximum_clocks: u64,
) -> Value {
    let mut successor = state.clone();
    let mut articulated_body = initial_articulated_body.cloned();
    let mut frontier = successor.active_electrical_frontier.to_vec();
    let mut residency = None;
    let mut learned_ordering_lineages = successor
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = successor.electrical_fabric.lineages()[left];
            let right_lineage = successor.electrical_fabric.lineages()[right];
            match (
                successor.topology_index.layer_of(left_lineage),
                successor.topology_index.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some(left_lineage),
                (Some(12), Some(11)) => Some(right_lineage),
                _ => None,
            }
        })
        .collect::<Vec<_>>();
    learned_ordering_lineages.sort_unstable();
    learned_ordering_lineages.dedup();
    let ordering_to_motor = successor
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = successor.electrical_fabric.lineages()[left];
            let right_lineage = successor.electrical_fabric.lineages()[right];
            match (
                successor.topology_index.layer_of(left_lineage),
                successor.topology_index.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some((left_lineage, right_lineage)),
                (Some(12), Some(11)) => Some((right_lineage, left_lineage)),
                _ => None,
            }
        })
        .collect::<std::collections::BTreeMap<_, _>>();
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let mut clocks = Vec::new();
    for active_clock in 1_u64..=maximum_clocks {
        let mut reached_lineages = frontier
            .iter()
            .flat_map(|entry| entry.affected_lineages().into_iter().flatten())
            .collect::<Vec<_>>();
        reached_lineages.sort_unstable();
        reached_lineages.dedup();
        let topology = successor.topology_index.clone();
        let mut relevant_lineages = learned_ordering_lineages.clone();
        for ordering in &learned_ordering_lineages {
            let ordering_flat = topology
                .flat_for_lineage(*ordering)
                .expect("learned ordering lineage present");
            relevant_lineages.extend(
                topology.neighbours_by_flat[ordering_flat]
                    .iter()
                    .map(|flat| topology.flat_locations[*flat].2),
            );
        }
        relevant_lineages.sort_unstable();
        relevant_lineages.dedup();
        let predecessor_electrical = successor
            .cohorts
            .iter()
            .flat_map(|cohort| {
                cohort
                    .anatomy
                    .neuron_lineages()
                    .iter()
                    .copied()
                    .zip(cohort.anatomy.neuron_anatomies())
                    .zip(cohort.state.neurons())
            })
            .filter_map(|((lineage, anatomy), neuron)| {
                relevant_lineages
                    .contains(&lineage)
                    .then(|| (lineage, (anatomy.clone(), neuron.clone())))
            })
            .collect::<std::collections::BTreeMap<_, _>>();
        let mut changed = std::collections::BTreeSet::new();
        let unchanged_developmental_resting_neuron_count = successor
            .resting_population
            .as_ref()
            .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
            .unwrap_or(0);
        let observation = super::settle_internal_contact_interval(
            &mut successor.cohorts,
            &mut successor.electrical_fabric,
            &topology,
            successor.vocal_articulatory_effector_lineage,
            &frontier,
            &reached_lineages,
            &reached_lineages,
            &[],
            &mut changed,
            successor.generation + active_clock,
            unchanged_developmental_resting_neuron_count,
            &mut residency,
            &std::collections::BTreeMap::new(),
            &[],
            &[],
            ExactRational::integer(0),
            false,
        )
        .expect("retained copied-body frontier settles");
        let bridge_transfers = observation
            .settled_directed_transfers
            .iter()
            .filter_map(|transfer| {
                let sender_layer = topology.layer_of(transfer.sender)?;
                let receiver_layer = topology.layer_of(transfer.receiver)?;
                (matches!((sender_layer, receiver_layer), (11, 12) | (12, 11))).then(|| {
                    json!({
                        "sender": lineage_hex(transfer.sender),
                        "sender_layer": sender_layer,
                        "receiver": lineage_hex(transfer.receiver),
                        "receiver_layer": receiver_layer,
                        "transferred_whole_carriers": transfer
                            .transferred_whole_carriers
                            .to_string(),
                    })
                })
            })
            .collect::<Vec<_>>();
        let ordering_incident_transfers = observation
            .settled_directed_transfers
            .iter()
            .filter_map(|transfer| {
                (learned_ordering_lineages.contains(&transfer.sender)
                    || learned_ordering_lineages.contains(&transfer.receiver))
                .then(|| {
                    let (sender_anatomy, sender_state) = predecessor_electrical
                        .get(&transfer.sender)
                        .expect("incident sender predecessor present");
                    let (receiver_anatomy, receiver_state) = predecessor_electrical
                        .get(&transfer.receiver)
                        .expect("incident receiver predecessor present");
                    let released =
                        crate::sparse_electrical_contact::probe_directed_contact_work_zeptojoules(
                            sender_anatomy,
                            sender_state,
                            receiver_anatomy,
                            receiver_state,
                            transfer.transferred_whole_carriers,
                        );
                    json!({
                        "sender": lineage_hex(transfer.sender),
                        "sender_layer": topology.layer_of(transfer.sender),
                        "receiver": lineage_hex(transfer.receiver),
                        "receiver_layer": topology.layer_of(transfer.receiver),
                        "transferred_whole_carriers": transfer
                            .transferred_whole_carriers
                            .to_string(),
                        "single_edge_released_work_zeptojoules": released
                            .as_ref()
                            .ok()
                            .map(wide_exact_json),
                        "single_edge_work_error": released.err().map(|error| format!("{error:?}")),
                    })
                })
            })
            .collect::<Vec<_>>();
        // Test-only three-terminal energy range.  For each real L11 -> L7
        // whole-carrier event, preserve the exact number leaving L11 but
        // redirect a bounded range of those same carriers into its one
        // learned L12 motor.  No carrier or work is added.  This asks whether
        // a lean, directed, energy-descending transducer is physically
        // possible before any production law or retained state is authored.
        let split_extents = [1_u128, 2, 4, 8, 16, 24, 32, 48, 64];
        let mut three_terminal_route_range = Vec::new();
        for transfer in &observation.settled_directed_transfers {
            if topology.layer_of(transfer.sender) != Some(11)
                || topology.layer_of(transfer.receiver) != Some(7)
            {
                continue;
            }
            let Some(motor) = ordering_to_motor.get(&transfer.sender).copied() else {
                continue;
            };
            let (ordering_anatomy, ordering_state) = predecessor_electrical
                .get(&transfer.sender)
                .expect("ordering predecessor present");
            let (founding_anatomy, founding_state) = predecessor_electrical
                .get(&transfer.receiver)
                .expect("founding predecessor present");
            let (motor_anatomy, motor_state) = predecessor_electrical
                .get(&motor)
                .expect("motor predecessor present");
            let before_work = crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                ordering_anatomy,
                ordering_state,
            )
            .expect("ordering predecessor work")
                + crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                    founding_anatomy,
                    founding_state,
                )
                .expect("founding predecessor work")
                + crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                    motor_anatomy,
                    motor_state,
                )
                .expect("motor predecessor work");
            let total = transfer.transferred_whole_carriers;
            let samples = split_extents
                .iter()
                .copied()
                .filter(|split| *split <= total)
                .map(|split| {
                    let ordering_successor =
                        crate::complete_neuron::settle_membrane_pump_transport(
                            ordering_anatomy,
                            ordering_state,
                            i128::try_from(total).expect("ordering transfer width"),
                            None,
                            super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                        )
                        .expect("ordering split sender");
                    let founding_successor =
                        crate::complete_neuron::settle_membrane_pump_transport(
                            founding_anatomy,
                            founding_state,
                            -i128::try_from(total - split).expect("founding transfer width"),
                            None,
                            super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                        )
                        .expect("founding split receiver");
                    let motor_successor = crate::complete_neuron::settle_membrane_pump_transport(
                        motor_anatomy,
                        motor_state,
                        -i128::try_from(split).expect("motor transfer width"),
                        None,
                        super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                    )
                    .expect("motor split receiver");
                    let after_work =
                        crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                            ordering_anatomy,
                            &ordering_successor,
                        )
                        .expect("ordering successor work")
                            + crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                                founding_anatomy,
                                &founding_successor,
                            )
                            .expect("founding successor work")
                            + crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                                motor_anatomy,
                                &motor_successor,
                            )
                            .expect("motor successor work");
                    let work_released = &before_work - &after_work;
                    let terminal = crate::complete_neuron::settle_efferent_terminal_transport(
                        motor_anatomy,
                        &motor_successor,
                        split,
                        super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                    )
                    .expect("split-prepared motor terminal");
                    json!({
                        "split_to_motor_carriers": split.to_string(),
                        "remaining_to_founding_carriers": (total - split).to_string(),
                        "strict_energy_descent": work_released > BigRational::zero(),
                        "released_work_zeptojoules": wide_exact_json(&work_released),
                        "terminal_discharged_carriers": terminal
                            .as_ref()
                            .map(|(_, carriers, _)| carriers.to_string()),
                        "terminal_released_work_zeptojoules": terminal
                            .as_ref()
                            .map(|(_, _, work)| wide_exact_json(work)),
                    })
                })
                .collect::<Vec<_>>();
            three_terminal_route_range.push(json!({
                "ordering": lineage_hex(transfer.sender),
                "founding_receiver": lineage_hex(transfer.receiver),
                "motor": lineage_hex(motor),
                "original_ordering_outward_carriers": total.to_string(),
                "samples": samples,
            }));
        }
        let respiratory_efferent_carriers = observation
            .articulatory_unit_recruitments
            .iter()
            .try_fold(0_u128, |total, event| {
                total.checked_add(event.outward_elementary_carriers)
            })
            .expect("copied-body respiratory carrier width");
        let body_transition = match articulated_body.take() {
            None => None,
            Some(body) => {
                let learned_axes = observation
                    .motor_unit_recruitments
                    .iter()
                    .filter(|recruitment| {
                        recruitment
                            .preparation_transfers
                            .iter()
                            .any(|preparation| preparation.sender_layer == 11)
                    })
                    .map(|recruitment| recruitment.body_effector_terminal.axis())
                    .collect::<std::collections::BTreeSet<_>>();
                let mut carriers_by_terminal = std::collections::BTreeMap::<_, u128>::new();
                for recruitment in &observation.motor_unit_recruitments {
                    let carriers = carriers_by_terminal
                        .entry(recruitment.body_effector_terminal)
                        .or_default();
                    *carriers = carriers
                        .checked_add(recruitment.outward_elementary_carriers)
                        .expect("body carrier aggregation width");
                }
                let admitted = AdmittedBodyEffectorDrives::admit(
                    carriers_by_terminal
                        .into_iter()
                        .map(
                            |(terminal, outward_elementary_carriers)| BodyEffectorDrive {
                                terminal,
                                outward_elementary_carriers,
                            },
                        )
                        .collect(),
                )
                .expect("copied-body motor admissions");
                let transition = settle_body_effector_drives(
                    &body,
                    &admitted,
                    BODY_SETTLEMENT_CLOCK_MICROSECONDS,
                )
                .expect("copied-body motor settlement");
                let learned_consequences = transition
                    .proprioceptive_consequences
                    .iter()
                    .copied()
                    .filter(|consequence| learned_axes.contains(&consequence.axis))
                    .collect::<Vec<_>>();
                let sensory_return = if learned_consequences.is_empty() || active_clock != 1 {
                    None
                } else {
                    let source = admit_articulated_body_consequence_source(
                        state.generation + active_clock,
                        &learned_consequences,
                    )
                    .expect("copied-body proprioceptive return source");
                    let reached_load_receptors = source
                        .joint_source_ports()
                        .iter()
                        .filter(|port| {
                            port.physical_quantity
                                == crate::proprioceptive_receptor_work::EFFECTOR_REACTIVE_LOAD_FRACTION_QUANTITY
                                && port
                                    .exact_normalized_sources
                                    .iter()
                                    .any(|sample| sample > &BigRational::zero())
                        })
                        .map(|port| {
                            let site = super::NeuronSourceSite::from_source_port(port)
                                .expect("copied-body load source site");
                            let (cohort_index, neuron_index, lineage) = successor
                                .topology_index
                                .source_location(&site)
                                .expect("copied-body load source lookup")
                                .expect("copied-body load receptor must be mounted");
                            let predecessor = &successor.cohorts[cohort_index].state.neurons()
                                [neuron_index];
                            (
                                cohort_index,
                                neuron_index,
                                lineage,
                                port.body_proprioceptor_terminal,
                                predecessor.receptor_quantum_residue.energy(),
                                predecessor.gate.open_population(),
                            )
                        })
                        .collect::<Vec<_>>();
                    let intervals = vec![(1_i64, 1_000_i64); learned_consequences.len()];
                    let admitted = admitted_episode_with_authored_intervals(&source, &intervals)
                        .expect("copied-body proprioceptive return admission");
                    let (returned_successor, returned) = successor
                        .clone()
                        .advance_admitted_transition(
                            &admitted,
                            usize::MAX,
                            false,
                            ExactRational::integer(0),
                        )
                        .expect("copied-body proprioceptive return settlement");
                    let load_receptor_returns = reached_load_receptors
                        .into_iter()
                        .map(|(cohort_index, neuron_index, lineage, terminal, before, gate_before)| {
                            let after = &returned_successor.cohorts[cohort_index].state.neurons()
                                [neuron_index];
                            let successor_residue = after.receptor_quantum_residue.energy();
                            json!({
                                "lineage": lineage_hex(lineage),
                                "terminal": format!("{terminal:?}"),
                                "predecessor_residue_zeptojoules": wide_exact_json(&before),
                                "successor_residue_zeptojoules": wide_exact_json(&successor_residue),
                                "residue_changed": successor_residue != before,
                                "predecessor_open_gate_population": gate_before.to_string(),
                                "successor_open_gate_population": after.gate.open_population().to_string(),
                            })
                        })
                        .collect::<Vec<_>>();
                    Some(json!({
                        "port_count": source.joint_source_ports().len(),
                        "occurrence_count": source.joint_source_occurrences().len(),
                        "sample_count": source.joint_source_sample_count(),
                        "nonzero_load_receptor_returns": load_receptor_returns,
                        "externally_perturbed_body_receptor_count": returned
                            .externally_perturbed_body_receptor_count,
                        "physically_transitioned_neuron_count": returned
                            .physically_transitioned_neuron_count,
                        "dsf_delivery_count": returned.dsf_delivery_count,
                    }))
                };
                let consequences = transition
                .proprioceptive_consequences
                .iter()
                .map(|consequence| json!({
                    "axis": format!("{:?}", consequence.axis),
                    "predecessor_position": consequence.predecessor_position,
                    "successor_position": consequence.successor_position,
                    "signed_displacement": consequence.signed_displacement,
                    "toward_minimum_carriers": consequence.toward_minimum_carriers.to_string(),
                    "toward_maximum_carriers": consequence.toward_maximum_carriers.to_string(),
                    "applied_displacement_quanta": consequence
                        .applied_displacement_quanta
                        .to_string(),
                    "stalled_carriers": consequence.stalled_carriers.to_string(),
                }))
                .collect::<Vec<_>>();
                let acoustic = settle_native_articulatory_interval(
                    transition.successor,
                    &transition.proprioceptive_consequences,
                    respiratory_efferent_carriers,
                    4_000,
                )
                .expect("copied-body acoustic settlement");
                let acoustic_peak = acoustic
                    .radiated_pressure_pcm
                    .iter()
                    .map(|sample| sample.unsigned_abs())
                    .max()
                    .unwrap_or(0);
                let acoustic_nonzero_samples = acoustic
                    .radiated_pressure_pcm
                    .iter()
                    .filter(|sample| **sample != 0)
                    .count();
                articulated_body = Some(acoustic.successor_body);
                Some(json!({
                    "reached_terminal_count": transition.reached_terminal_count,
                    "consequences": consequences,
                    "sensory_return": sensory_return,
                    "respiratory_efferent_carriers": respiratory_efferent_carriers.to_string(),
                    "acoustic_peak_pressure": acoustic_peak,
                    "acoustic_nonzero_samples": acoustic_nonzero_samples,
                }))
            }
        };
        let motor_recruitments = observation
            .motor_unit_recruitments
            .iter()
            .map(|event| {
                json!({
                    "lineage": lineage_hex(event.neuron_lineage),
                    "terminal": format!("{:?}", event.body_effector_terminal),
                    "outward_elementary_carriers":
                        event.outward_elementary_carriers.to_string(),
                    "preparation_transfers": event
                        .preparation_transfers
                        .iter()
                        .map(|preparation| json!({
                            "sender": lineage_hex(preparation.transfer.sender),
                            "sender_layer": preparation.sender_layer,
                            "receiver": lineage_hex(preparation.transfer.receiver),
                            "transferred_whole_carriers": preparation
                                .transfer
                                .transferred_whole_carriers
                                .to_string(),
                        }))
                        .collect::<Vec<_>>(),
                })
            })
            .collect::<Vec<_>>();
        let next_frontier = observation.next_active_frontier.clone();
        let articulatory_recruitments = observation
            .articulatory_unit_recruitments
            .iter()
            .map(|event| {
                json!({
                    "lineage": lineage_hex(event.neuron_lineage),
                    "topology_index": event.topology_index,
                    "outward_elementary_carriers": event.outward_elementary_carriers.to_string(),
                    "preparation_transfers": event
                        .preparation_transfers
                        .iter()
                        .map(|preparation| json!({
                            "sender": lineage_hex(preparation.transfer.sender),
                            "sender_layer": preparation.sender_layer,
                            "receiver": lineage_hex(preparation.transfer.receiver),
                            "transferred_whole_carriers": preparation
                                .transfer
                                .transferred_whole_carriers
                                .to_string(),
                        }))
                        .collect::<Vec<_>>(),
                })
            })
            .collect::<Vec<_>>();
        clocks.push(json!({
            "clock": active_clock,
            "input_frontier_count": frontier.len(),
            "input_lineage_count": reached_lineages.len(),
            "changed_neuron_count": changed.len(),
            "settled_transfer_count": observation.settled_directed_transfers.len(),
            "bridge_transfers": bridge_transfers,
            "ordering_incident_transfers": ordering_incident_transfers,
            "three_terminal_route_range": three_terminal_route_range,
            "input_frontier_ordering_lineages": learned_ordering_lineages
                .iter()
                .copied()
                .filter(|lineage| reached_lineages.contains(lineage))
                .map(lineage_hex)
                .collect::<Vec<_>>(),
            "motor_recruitment_count": motor_recruitments.len(),
            "motor_recruitments": motor_recruitments,
            "articulated_body_transition": body_transition,
            "root_yaw_recruitment_count": observation.root_yaw_unit_recruitments.len(),
            "root_translation_recruitment_count":
                observation.root_translation_unit_recruitments.len(),
            "articulatory_recruitment_count":
                observation.articulatory_unit_recruitments.len(),
            "articulatory_recruitments": articulatory_recruitments,
            "next_frontier_count": next_frontier.len(),
        }));
        frontier = next_frontier;
    }
    json!({
        "synthetic_seed_count": 0,
        "maximum_clocks": maximum_clocks,
        "initial_frontier_count": state.active_electrical_frontier.len(),
        "clocks": clocks,
    })
}

/// Energy-only feasibility range for one future directional synaptic boundary.
/// It does not claim the inward transport is currently authored: it moves a
/// bounded range of whole carriers on a disposable copied neuron, measures the
/// exact retained membrane-plus-gradient work change, and then asks the
/// already-live efferent terminal law whether that prepared state can return
/// them as output.
fn motor_inward_preparation_energy_range_json(state: &ResidentCognitiveFormationState) -> Value {
    let topology = state.topology_index.clone();
    let mut motor_lineages = state
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left_lineage = state.electrical_fabric.lineages()[left];
            let right_lineage = state.electrical_fabric.lineages()[right];
            match (
                topology.layer_of(left_lineage),
                topology.layer_of(right_lineage),
            ) {
                (Some(11), Some(12)) => Some(right_lineage),
                (Some(12), Some(11)) => Some(left_lineage),
                _ => None,
            }
        })
        .collect::<Vec<_>>();
    motor_lineages.sort_unstable();
    motor_lineages.dedup();
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let extents = [1_u128, 2, 4, 8, 16, 24, 32, 64];
    let motors = motor_lineages
        .into_iter()
        .map(|motor_lineage| {
            let (anatomy, predecessor) = state
                .cohorts
                .iter()
                .find_map(|cohort| {
                    cohort
                        .anatomy
                        .neuron_lineages()
                        .iter()
                        .position(|lineage| *lineage == motor_lineage)
                        .map(|index| {
                            (
                                &cohort.anatomy.neuron_anatomies()[index],
                                &cohort.state.neurons()[index],
                            )
                        })
                })
                .expect("learned motor lineage present");
            let predecessor_work =
                crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                    anatomy,
                    predecessor,
                )
                .expect("predecessor motor work");
            let samples = extents
                .iter()
                .copied()
                .map(|extent| {
                    let inward = -i128::try_from(extent).expect("probe extent width");
                    let prepared = crate::complete_neuron::settle_membrane_pump_transport(
                        anatomy,
                        predecessor,
                        inward,
                        None,
                        super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                    )
                    .expect("probe inward preparation");
                    let prepared_work =
                        crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
                            anatomy, &prepared,
                        )
                        .expect("prepared motor work");
                    let work_delta = &prepared_work - &predecessor_work;
                    let discharge = crate::complete_neuron::settle_efferent_terminal_transport(
                        anatomy,
                        &prepared,
                        extent,
                        super::WORLD_MECHANICAL_TICK_MICROSECONDS,
                    )
                    .expect("prepared terminal discharge");
                    json!({
                        "inward_elementary_carriers": extent.to_string(),
                        "work_delta_zeptojoules": wide_exact_json(&work_delta),
                        "work_increased": work_delta > BigRational::zero(),
                        "prepared_membrane_charge": prepared
                            .separated_elementary_charges()
                            .to_string(),
                        "terminal_discharged_carriers": discharge
                            .as_ref()
                            .map(|(_, carriers, _)| carriers.to_string()),
                        "terminal_released_work_zeptojoules": discharge
                            .as_ref()
                            .map(|(_, _, work)| wide_exact_json(work)),
                    })
                })
                .collect::<Vec<_>>();
            json!({
                "motor_lineage": lineage_hex(motor_lineage),
                "predecessor_membrane_charge": predecessor
                    .separated_elementary_charges()
                    .to_string(),
                "samples": samples,
            })
        })
        .collect::<Vec<_>>();
    json!({
        "authored_transport": false,
        "purpose": "exact energy feasibility only",
        "inward_extent_range": extents,
        "motors": motors,
    })
}

fn severed_learned_motor_copy(
    state: &ResidentCognitiveFormationState,
) -> (ResidentCognitiveFormationState, usize) {
    let layer_of = |lineage| state.topology_index.layer_of(lineage);
    let removed = state
        .electrical_fabric
        .contact_endpoints()
        .filter_map(|(left, right)| {
            let left = state.electrical_fabric.lineages()[left];
            let right = state.electrical_fabric.lineages()[right];
            matches!(
                (layer_of(left), layer_of(right)),
                (Some(11), Some(12)) | (Some(12), Some(11))
            )
            .then_some(if left < right {
                (left, right)
            } else {
                (right, left)
            })
        })
        .collect::<std::collections::BTreeSet<_>>();
    let mut severed = state.clone();
    severed.electrical_fabric = severed
        .electrical_fabric
        .without_contact_pairs(&removed)
        .expect("test bridge severing");
    let keep_frontier = |entry: &super::ActiveElectricalFrontierEntry| {
        let Some(sender) = entry.sender() else {
            return true;
        };
        let receiver = entry.receiver();
        let pair = if sender < receiver {
            (sender, receiver)
        } else {
            (receiver, sender)
        };
        !removed.contains(&pair)
    };
    severed.active_electrical_frontier = severed
        .active_electrical_frontier
        .iter()
        .copied()
        .filter(keep_frontier)
        .collect::<Vec<_>>()
        .into_boxed_slice();
    severed.preceding_active_electrical_frontier = severed
        .preceding_active_electrical_frontier
        .iter()
        .copied()
        .filter(keep_frontier)
        .collect::<Vec<_>>()
        .into_boxed_slice();
    severed.older_active_electrical_frontier = severed
        .older_active_electrical_frontier
        .iter()
        .copied()
        .filter(keep_frontier)
        .collect::<Vec<_>>()
        .into_boxed_slice();
    severed.topology_index = std::sync::Arc::new(
        super::ResidentTopologyIndex::build(&severed.cohorts, &severed.electrical_fabric)
            .expect("test severed topology"),
    );
    (severed, removed.len())
}

/// Run the production one-carrier transduction through the complete copied-body
/// three-clock settlement, then repeat after physically severing every learned
/// L11/L12 bridge. Both successors are disposable in-memory copies.
fn integrated_motor_transduction_falsifier_json(
    state: &ResidentCognitiveFormationState,
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    let connected = retained_frontier_motor_range_json(state, articulated_body, 3);
    let (severed, severed_bridge_count) = severed_learned_motor_copy(state);
    let disconnected = retained_frontier_motor_range_json(&severed, articulated_body, 3);
    json!({
        "production_compiled": true,
        "connected": connected,
        "severed": disconnected,
        "severed_bridge_count": severed_bridge_count,
    })
}

fn allocate_source_work_by_learned_conductance(
    source_work: &BigRational,
    source_path_conductance: ExactRational,
    routes: &[([u8; 16], ExactRational)],
) -> std::collections::BTreeMap<[u8; 16], BigRational> {
    let exact_to_wide = |value: ExactRational| {
        let (numerator, denominator) = value.parts();
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    };
    let learned_conductance = routes
        .iter()
        .map(|(_, conductance)| exact_to_wide(*conductance))
        .filter(|conductance| conductance > &BigRational::zero())
        .fold(BigRational::zero(), |sum, conductance| sum + conductance);
    let source_conductance = exact_to_wide(source_path_conductance);
    let total_conductance = &source_conductance + learned_conductance;
    let mut allocated = std::collections::BTreeMap::new();
    if source_work <= &BigRational::zero()
        || source_conductance <= BigRational::zero()
        || total_conductance.is_zero()
    {
        return allocated;
    }
    for (motor, conductance) in routes {
        let conductance = exact_to_wide(*conductance);
        if conductance <= BigRational::zero() {
            continue;
        }
        *allocated.entry(*motor).or_insert_with(BigRational::zero) +=
            source_work * conductance / &total_conductance;
    }
    allocated
}

fn effective_conductance_for_bond(
    state: &ResidentCognitiveFormationState,
    bond: crate::physical_mosaic::StablePhysicalBondReference,
) -> ExactRational {
    let topology = state
        .topology_index
        .contacts
        .iter()
        .copied()
        .find(|entry| entry.stable_bond == bond)
        .expect("range-probe source bond remains mounted");
    let edge = super::materialize_resident_contact_edge(
        topology,
        &state.cohorts,
        &state.electrical_fabric,
    )
    .expect("range-probe source contact materializes");
    edge.anatomy
        .effective_conductance(&edge.state)
        .expect("range-probe source contact state matches anatomy")
}

fn source_work_permutation_falsifier_json() -> Value {
    let lineage = |suffix: u8| {
        let mut value = [0_u8; 16];
        value[15] = suffix;
        value
    };
    let source_a = BigRational::new(BigInt::from(3_u8), BigInt::from(7_u8));
    let source_b = BigRational::new(BigInt::from(5_u8), BigInt::from(11_u8));
    let total_forward = &source_a + &source_b;
    let total_reversed = &source_b + &source_a;
    let routes_forward = vec![
        (lineage(1), ExactRational::integer(2)),
        (lineage(2), ExactRational::integer(3)),
        (lineage(1), ExactRational::integer(5)),
        (lineage(3), ExactRational::integer(0)),
    ];
    let routes_reversed = routes_forward.iter().copied().rev().collect::<Vec<_>>();
    let source_conductance = ExactRational::integer(7);
    let forward = allocate_source_work_by_learned_conductance(
        &total_forward,
        source_conductance,
        &routes_forward,
    );
    let reversed = allocate_source_work_by_learned_conductance(
        &total_reversed,
        source_conductance,
        &routes_reversed,
    );
    let encode = |allocated: &std::collections::BTreeMap<[u8; 16], BigRational>| {
        allocated
            .iter()
            .map(|(motor, work)| {
                json!({
                    "motor_suffix": motor[15],
                    "allocated_source_work_zeptojoules": wide_exact_json(work),
                })
            })
            .collect::<Vec<_>>()
    };
    let allocated_total = forward
        .values()
        .cloned()
        .fold(BigRational::zero(), |sum, work| sum + work);
    let retained_source_heat = &total_forward - &allocated_total;
    json!({
        "multiple_sources": 2,
        "multiple_branches": routes_forward.len(),
        "converging_contacts_on_motor_one": 2,
        "zero_conductance_motor_absent": !forward.contains_key(&lineage(3)),
        "source_order_and_branch_order_invariant": forward == reversed,
        "allocated_plus_retained_heat_equals_source_work":
            &allocated_total + &retained_source_heat == total_forward,
        "retained_source_heat_zeptojoules": wide_exact_json(&retained_source_heat),
        "forward": encode(&forward),
        "reversed": encode(&reversed),
    })
}

/// Candidate 47E's conservation-correct motor settlement on one disposable
/// copied neuron.  The mounted pump determines direction and its whole-carrier
/// bound.  Existing recovery material pays as much of the exact stored-work
/// increase as it can; exact work released by the connected L11 source pays
/// only the shortfall.  That source contribution is therefore unavailable for
/// heat export.  No source carrier enters L12 and available+spent recovery
/// material is unchanged.
fn source_work_assisted_motor_sample_json(
    cohort: &super::ResidentReachedCohort,
    motor_neuron: usize,
    offered_source_work: &BigRational,
    interval_microseconds: u32,
    exhaust_motor_carriers: bool,
) -> Value {
    let exact_to_wide = |value: ExactRational| {
        let (numerator, denominator) = value.parts();
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    };
    let wide_to_exact = |value: &BigRational| {
        Some(ExactRational::new(value.numer().to_i128()?, value.denom().to_u128()?).ok()?)
    };
    let anatomy = &cohort.anatomy.neuron_anatomies()[motor_neuron];
    let resident_predecessor = &cohort.state.neurons()[motor_neuron];
    let exhausted_predecessor = exhaust_motor_carriers.then(|| {
        crate::complete_neuron::with_held_membrane_and_carriers(
            resident_predecessor,
            resident_predecessor.membrane_state(),
            0,
            0,
        )
    });
    let predecessor = exhausted_predecessor
        .as_ref()
        .unwrap_or(resident_predecessor);
    let reservoir_anatomy = cohort.anatomy.recovery_fluid_reservoir_anatomy();
    let predecessor_reservoir = cohort.state.recovery_fluid();
    let (_, spent_capacity, _) = reservoir_anatomy.capacities();
    let (available, spent, thermal) = predecessor_reservoir.physical_parts();
    let local_budget =
        exact_to_wide(available).min(exact_to_wide(spent_capacity) - exact_to_wide(spent));
    let source_budget = offered_source_work.clone().max(BigRational::zero());
    let total_budget = &local_budget + &source_budget;
    let bound = crate::complete_neuron::membrane_gradient_pump_charge_bound(
        anatomy,
        predecessor,
        interval_microseconds,
    )
    .expect("copied motor pump bound");
    let predecessor_work =
        crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(anatomy, predecessor)
            .expect("copied motor predecessor work");
    let direction_negative = bound.charges.is_negative();
    let full_magnitude = bound.charges.unsigned_abs();
    let reversal = anatomy.gate_reversal_potential_millivolts();
    let predecessor_drive = predecessor
        .membrane_state()
        .potential_millivolts(anatomy.capacitance())
        .expect("copied motor predecessor potential")
        .checked_sub(reversal)
        .expect("copied motor predecessor drive");
    let predecessor_sign = predecessor_drive.parts().0.signum();

    let mut lower = 0_u128;
    let mut upper = full_magnitude;
    let mut accepted_state = predecessor.clone();
    let mut accepted_work = BigRational::zero();
    let mut accepted_local = BigRational::zero();
    let mut accepted_source = BigRational::zero();
    while lower < upper {
        let middle = lower + (upper - lower + 1) / 2;
        let magnitude = match i128::try_from(middle) {
            Ok(value) => value,
            Err(_) => {
                upper = middle - 1;
                continue;
            }
        };
        let signed = if direction_negative {
            -magnitude
        } else {
            magnitude
        };
        let candidate = crate::complete_neuron::settle_membrane_pump_transport(
            anatomy,
            predecessor,
            signed,
            (middle == full_magnitude)
                .then_some(bound.successor_phase)
                .flatten(),
            interval_microseconds,
        )
        .expect("copied motor candidate transport");
        let successor_drive = candidate
            .membrane_state()
            .potential_millivolts(anatomy.capacitance())
            .expect("copied motor successor potential")
            .checked_sub(reversal)
            .expect("copied motor successor drive");
        let successor_sign = successor_drive.parts().0.signum();
        let stays_on_reversal_side = successor_sign == 0 || successor_sign == predecessor_sign;
        let successor_work = crate::complete_neuron::membrane_and_gradient_work_zeptojoules_wide(
            anatomy, &candidate,
        )
        .expect("copied motor successor work");
        let work = successor_work - &predecessor_work;
        if !stays_on_reversal_side || work <= BigRational::zero() || work > total_budget {
            upper = middle - 1;
            continue;
        }
        let local = work.clone().min(local_budget.clone());
        let source = &work - &local;
        let Some(local_exact) = wide_to_exact(&local) else {
            upper = middle - 1;
            continue;
        };
        let Ok(successor_available) = available.checked_sub(local_exact) else {
            upper = middle - 1;
            continue;
        };
        let Ok(successor_spent) = spent.checked_add(local_exact) else {
            upper = middle - 1;
            continue;
        };
        if crate::recovery_fluid_contact::RecoveryFluidReservoirState::new(
            reservoir_anatomy,
            successor_available,
            successor_spent,
            thermal,
        )
        .is_err()
        {
            upper = middle - 1;
            continue;
        }
        lower = middle;
        accepted_state = candidate;
        accepted_work = work;
        accepted_local = local;
        accepted_source = source;
    }

    let terminal = crate::complete_neuron::settle_efferent_terminal_transport(
        anatomy,
        &accepted_state,
        lower,
        interval_microseconds,
    )
    .expect("copied motor terminal settlement");
    let source_heat_remaining = &source_budget - &accepted_source;
    let recovery_material_before = exact_to_wide(available) + exact_to_wide(spent);
    let recovery_material_after = recovery_material_before.clone();
    json!({
        "interval_microseconds": interval_microseconds,
        "motor_carriers_artificially_exhausted": exhaust_motor_carriers,
        "offered_source_work_zeptojoules": wide_exact_json(&source_budget),
        "local_recovery_work_contribution_zeptojoules": wide_exact_json(&accepted_local),
        "source_work_contribution_zeptojoules": wide_exact_json(&accepted_source),
        "source_heat_remaining_zeptojoules": wide_exact_json(&source_heat_remaining),
        "pumped_elementary_carriers": if direction_negative {
            format!("-{}", lower)
        } else {
            lower.to_string()
        },
        "pump_work_zeptojoules": wide_exact_json(&accepted_work),
        "work_conservation_exact": accepted_work == accepted_local + accepted_source,
        "recovery_material_before_zeptojoules": wide_exact_json(&recovery_material_before),
        "recovery_material_after_zeptojoules": wide_exact_json(&recovery_material_after),
        "recovery_material_conserved": recovery_material_before == recovery_material_after,
        "terminal_discharged_carriers": terminal
            .as_ref()
            .map(|(_, carriers, _)| carriers.to_string()),
    })
}

/// Measurement-only candidate-47E regime map. The copied body's retained
/// frontier supplies each L11 founding event and its exact released work. The
/// connected L12 motor keeps its own carrier material and uses source work
/// only as a conserved contribution to its mounted reversal-gradient pump.
/// No production state is changed.
fn source_work_to_motor_reservoir_range_json(state: &ResidentCognitiveFormationState) -> Value {
    let lineage_hex = |lineage: [u8; 16]| {
        lineage
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>()
    };
    let exact_to_wide = |value: ExactRational| {
        let (numerator, denominator) = value.parts();
        BigRational::new(BigInt::from(numerator), BigInt::from(denominator))
    };

    let mut learned_routes =
        std::collections::BTreeMap::<[u8; 16], Vec<([u8; 16], ExactRational)>>::new();
    for ((left, right), (anatomy, contact_state)) in
        state.electrical_fabric.contact_endpoints().zip(
            state
                .electrical_fabric
                .anatomy()
                .contact_anatomies()
                .iter()
                .zip(state.electrical_fabric.state().contact_states()),
        )
    {
        let left_lineage = state.electrical_fabric.lineages()[left];
        let right_lineage = state.electrical_fabric.lineages()[right];
        let route = match (
            state.topology_index.layer_of(left_lineage),
            state.topology_index.layer_of(right_lineage),
        ) {
            (Some(11), Some(12)) => Some((left_lineage, right_lineage)),
            (Some(12), Some(11)) => Some((right_lineage, left_lineage)),
            _ => None,
        };
        if let Some((ordering, motor)) = route {
            learned_routes.entry(ordering).or_default().push((
                motor,
                anatomy
                    .effective_conductance(contact_state)
                    .expect("copied learned-contact state matches anatomy"),
            ));
        }
    }
    for routes in learned_routes.values_mut() {
        routes.sort_unstable_by_key(|(motor, _)| *motor);
    }

    let mut successor = state.clone();
    let mut frontier = successor.active_electrical_frontier.to_vec();
    let mut residency = None;
    let mut route_results = Vec::new();
    for active_clock in 1_u64..=3 {
        let mut reached_lineages = frontier
            .iter()
            .flat_map(|entry| entry.affected_lineages().into_iter().flatten())
            .collect::<Vec<_>>();
        reached_lineages.sort_unstable();
        reached_lineages.dedup();
        let predecessor = successor.clone();
        let topology = successor.topology_index.clone();
        let mut changed = std::collections::BTreeSet::new();
        let resting = successor
            .resting_population
            .as_ref()
            .map(|population| usize::try_from(population.resting_cell_count()).unwrap())
            .unwrap_or(0);
        let observation = super::settle_internal_contact_interval(
            &mut successor.cohorts,
            &mut successor.electrical_fabric,
            &topology,
            successor.vocal_articulatory_effector_lineage,
            &frontier,
            &reached_lineages,
            &reached_lineages,
            &[],
            &mut changed,
            successor.generation + active_clock,
            resting,
            &mut residency,
            &std::collections::BTreeMap::new(),
            &[],
            &[],
            ExactRational::integer(0),
            false,
        )
        .expect("copied retained frontier settles for source-work range");

        let mut bad_bridge_extent = std::collections::BTreeMap::<[u8; 16], u128>::new();
        for transfer in &observation.settled_directed_transfers {
            if topology.layer_of(transfer.sender) == Some(11)
                && topology.layer_of(transfer.receiver) == Some(12)
            {
                *bad_bridge_extent.entry(transfer.sender).or_default() = bad_bridge_extent
                    .get(&transfer.sender)
                    .copied()
                    .unwrap_or(0)
                    .checked_add(transfer.transferred_whole_carriers)
                    .expect("test bridge extent width");
            }
        }

        let mut motor_work =
            std::collections::BTreeMap::<[u8; 16], (usize, usize, BigRational, Vec<Value>)>::new();
        for (ordering, diverted_extent) in bad_bridge_extent {
            let source_edges = observation
                .settled_directed_transfers
                .iter()
                .filter(|transfer| {
                    transfer.sender == ordering && topology.layer_of(transfer.receiver) == Some(7)
                })
                .collect::<Vec<_>>();
            if source_edges.len() != 1 {
                route_results.push(json!({
                    "active_clock": active_clock,
                    "ordering_lineage": lineage_hex(ordering),
                    "error": "candidate requires an order-independent multi-source reconciliation",
                    "source_edge_count": source_edges.len(),
                }));
                continue;
            }
            let source = source_edges[0];
            let original_extent = source
                .transferred_whole_carriers
                .checked_add(diverted_extent)
                .expect("original source extent width");
            let ordering_flat = predecessor
                .topology_index
                .flat_for_lineage(ordering)
                .expect("ordering lineage present");
            let receiver_flat = predecessor
                .topology_index
                .flat_for_lineage(source.receiver)
                .expect("source receiver lineage present");
            let (ordering_cohort, ordering_neuron, _) =
                predecessor.topology_index.flat_locations[ordering_flat];
            let (receiver_cohort, receiver_neuron, _) =
                predecessor.topology_index.flat_locations[receiver_flat];
            let source_work =
                crate::sparse_electrical_contact::probe_directed_contact_work_zeptojoules(
                    &predecessor.cohorts[ordering_cohort]
                        .anatomy
                        .neuron_anatomies()[ordering_neuron],
                    &predecessor.cohorts[ordering_cohort].state.neurons()[ordering_neuron],
                    &predecessor.cohorts[receiver_cohort]
                        .anatomy
                        .neuron_anatomies()[receiver_neuron],
                    &predecessor.cohorts[receiver_cohort].state.neurons()[receiver_neuron],
                    original_extent,
                )
                .expect("copied source work is exact");
            let source_conductance = effective_conductance_for_bond(&predecessor, source.bond);
            let routes = learned_routes
                .get(&ordering)
                .expect("observed bridge has retained learned route");
            let allocation = allocate_source_work_by_learned_conductance(
                &source_work,
                source_conductance,
                routes,
            );
            for (motor, branch_share) in allocation {
                let motor_flat = predecessor
                    .topology_index
                    .flat_for_lineage(motor)
                    .expect("learned motor lineage present");
                let (motor_cohort, motor_neuron, _) =
                    predecessor.topology_index.flat_locations[motor_flat];
                let motor_conductance = routes
                    .iter()
                    .filter(|(candidate, _)| *candidate == motor)
                    .fold(BigRational::zero(), |sum, (_, conductance)| {
                        sum + exact_to_wide(*conductance)
                    });
                let contribution = json!({
                    "active_clock": active_clock,
                    "ordering_lineage": lineage_hex(ordering),
                    "ordering_psi_ternary_winding_state":
                        mounted_neuron_ternary_winding_state_json(&predecessor, ordering),
                    "founding_receiver_lineage": lineage_hex(source.receiver),
                    "original_source_carriers": original_extent.to_string(),
                    "source_released_work_zeptojoules": wide_exact_json(&source_work),
                    "source_path_effective_conductance_picosiemens":
                        exact_json(source_conductance),
                    "motor_lineage": lineage_hex(motor),
                    "learned_contact_effective_conductance_picosiemens":
                        wide_exact_json(&motor_conductance),
                    "parallel_conductance_zeptojoules_share": wide_exact_json(&branch_share),
                });
                let entry = motor_work.entry(motor).or_insert_with(|| {
                    (motor_cohort, motor_neuron, BigRational::zero(), Vec::new())
                });
                assert_eq!(entry.0, motor_cohort, "motor cohort is stable");
                assert_eq!(entry.1, motor_neuron, "motor index is stable");
                entry.2 += &branch_share;
                entry.3.push(contribution);
            }
        }
        for (motor, (motor_cohort, motor_neuron, total_source_work, contributions)) in motor_work {
            let cohort = &predecessor.cohorts[motor_cohort];
            let predecessor_reservoir = cohort.state.recovery_fluid();
            let reservoir_anatomy = cohort.anatomy.recovery_fluid_reservoir_anatomy();
            let (available_capacity, spent_capacity, _) = reservoir_anatomy.capacities();
            let (available, spent, thermal) = predecessor_reservoir.physical_parts();
            let scales = [(0_i64, 1_i64), (1, 4), (1, 2), (1, 1), (2, 1), (4, 1)];
            let intervals = [62_500_u32, 125_000, 250_000, 500_000];
            let samples = scales
                .into_iter()
                .flat_map(|(scale_numerator, scale_denominator)| {
                    intervals.into_iter().map({
                        let total_source_work = total_source_work.clone();
                        move |interval_microseconds| {
                            let offered = total_source_work.clone() * BigInt::from(scale_numerator)
                                / BigInt::from(scale_denominator);
                            let mut sample = source_work_assisted_motor_sample_json(
                                cohort,
                                motor_neuron,
                                &offered,
                                interval_microseconds,
                                false,
                            );
                            sample["source_scale"] =
                                json!(format!("{scale_numerator}/{scale_denominator}"));
                            sample
                        }
                    })
                })
                .collect::<Vec<_>>();
            let exhausted_motor_carriers = source_work_assisted_motor_sample_json(
                cohort,
                motor_neuron,
                &total_source_work,
                250_000,
                true,
            );
            route_results.push(json!({
                "active_clock": active_clock,
                "motor_lineage": lineage_hex(motor),
                "contributing_route_count": contributions.len(),
                "contributing_routes": contributions,
                "total_source_work_zeptojoules": wide_exact_json(&total_source_work),
                "predecessor_available_work_zeptojoules": exact_json(available),
                "predecessor_spent_work_zeptojoules": exact_json(spent),
                "predecessor_thermal_work_zeptojoules": exact_json(thermal),
                "available_capacity_zeptojoules": exact_json(available_capacity),
                "spent_capacity_zeptojoules": exact_json(spent_capacity),
                "exhausted_motor_carriers_control": exhausted_motor_carriers,
                "samples": samples,
            }));
        }
        frontier = observation.next_active_frontier;
    }
    json!({
        "measurement_only": true,
        "production_compiled": false,
        "candidate": "47F absolute source/load conductance splits source work",
        "source_carriers_enter_motor": false,
        "a0116_transition_work_phase_reused": false,
        "recovery_material_created": false,
        "source_work_diverted_from_heat_when_spent": true,
        "synthetic_order_invariance": source_work_permutation_falsifier_json(),
        "route_results": route_results,
    })
}

fn wide_exact_from_json(value: &Value) -> BigRational {
    let numerator = value["numerator"]
        .as_str()
        .expect("exact JSON numerator")
        .parse::<BigInt>()
        .expect("exact JSON numerator integer");
    let denominator = value["denominator"]
        .as_str()
        .expect("exact JSON denominator")
        .parse::<BigInt>()
        .expect("exact JSON denominator integer");
    BigRational::new(numerator, denominator)
}

fn lineage_from_hex(value: &str) -> [u8; 16] {
    assert_eq!(value.len(), 32, "lineage hex width");
    let mut lineage = [0_u8; 16];
    for (index, byte) in lineage.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&value[index * 2..index * 2 + 2], 16)
            .expect("lineage hex byte");
    }
    lineage
}

fn mounted_neuron_location(
    state: &ResidentCognitiveFormationState,
    lineage: [u8; 16],
) -> (usize, usize) {
    let flat = state
        .topology_index
        .flat_for_lineage(lineage)
        .expect("mounted lineage");
    let (cohort, neuron, _) = state.topology_index.flat_locations[flat];
    (cohort, neuron)
}

fn with_replaced_mounted_neuron(
    state: &ResidentCognitiveFormationState,
    lineage: [u8; 16],
    replacement: crate::complete_neuron::NeuronPhysicalState,
) -> ResidentCognitiveFormationState {
    let (cohort_index, neuron_index) = mounted_neuron_location(state, lineage);
    let mut successor = state.clone();
    successor.cohorts[cohort_index].state = successor.cohorts[cohort_index]
        .state
        .with_replaced_neurons(&[(neuron_index, replacement)])
        .expect("one in-range neuron replacement")
        .into();
    successor
}

fn transduced_gate_sample_json(
    anatomy: &crate::complete_neuron::NeuronPhysicalAnatomy,
    predecessor: &crate::complete_neuron::NeuronPhysicalState,
    offered_work: &BigRational,
    interval_microseconds: u32,
    maximum_events: u32,
    exhaust_intracellular_carriers: bool,
    exhaust_gate_dissipation: bool,
) -> (Value, crate::complete_neuron::NeuronPhysicalState) {
    let mut current = predecessor.clone();
    let mut first_open_event = None;
    let mut first_outward_event = None;
    let mut peak_outward = 0_i128;
    let mut all_offer_balances_close = true;
    let mut all_gate_input_balances_close = true;
    let mut all_carrier_balances_close = true;
    let mut maximum_residue_numerator_bytes = 0_usize;
    let mut maximum_residue_denominator_bytes = 0_usize;
    let mut total_accepted = BigRational::zero();
    let mut total_source_heat = BigRational::zero();
    let mut total_delivered = BigRational::zero();
    let mut total_residue_narrowing_heat = BigRational::zero();
    let mut total_gate_exported_heat = BigRational::zero();
    let mut checkpoints = Vec::new();

    for event in 1..=maximum_events {
        let predecessor_residue = current.receptor_quantum_residue.energy().clone();
        let predecessor_carriers = if exhaust_intracellular_carriers {
            current.carrier_reservoirs().extracellular()
        } else {
            current
                .carrier_reservoirs()
                .total()
                .expect("copied motor carrier total")
        };
        let settled = crate::complete_neuron::probe_transduced_gate_work_interval(
            anatomy,
            &current,
            offered_work.clone(),
            interval_microseconds,
            exhaust_intracellular_carriers,
            exhaust_gate_dissipation,
        )
        .expect("candidate-47H isolated gate settlement");
        let successor_residue = settled
            .successor
            .receptor_quantum_residue
            .energy()
            .clone();
        let successor_carriers = settled
            .successor
            .carrier_reservoirs()
            .total()
            .expect("candidate motor carrier total");
        all_offer_balances_close &= *offered_work
            == &settled.accepted_work_zeptojoules + &settled.source_heat_zeptojoules;
        all_gate_input_balances_close &= predecessor_residue
            + &settled.accepted_work_zeptojoules
            == &settled.delivered_gate_work_zeptojoules
                + &successor_residue
                + &settled.residue_narrowing_heat_zeptojoules;
        all_carrier_balances_close &= predecessor_carriers == successor_carriers;
        total_accepted += &settled.accepted_work_zeptojoules;
        total_source_heat += &settled.source_heat_zeptojoules;
        total_delivered += &settled.delivered_gate_work_zeptojoules;
        total_residue_narrowing_heat += &settled.residue_narrowing_heat_zeptojoules;
        total_gate_exported_heat += &settled.gate_exported_heat_zeptojoules;
        maximum_residue_numerator_bytes = maximum_residue_numerator_bytes.max(
            successor_residue.numer().to_signed_bytes_le().len(),
        );
        maximum_residue_denominator_bytes = maximum_residue_denominator_bytes.max(
            successor_residue.denom().to_signed_bytes_le().len(),
        );
        let open_population = settled.successor.probe_gate_open_population();
        if open_population > 0 && first_open_event.is_none() {
            first_open_event = Some(event);
        }
        if settled.local_outward_elementary_charges > 0 && first_outward_event.is_none() {
            first_outward_event = Some(event);
        }
        peak_outward = peak_outward.max(settled.local_outward_elementary_charges);
        if event == 1
            || event == maximum_events
            || Some(event) == first_open_event
            || Some(event) == first_outward_event
        {
            checkpoints.push(json!({
                "event": event,
                "open_gate_population": open_population.to_string(),
                "local_outward_elementary_charges":
                    settled.local_outward_elementary_charges.to_string(),
                "successor_residue_zeptojoules": wide_exact_json(&successor_residue),
            }));
        }
        current = settled.successor;
    }

    let final_residue = current.receptor_quantum_residue.energy().clone();
    (
        json!({
            "interval_microseconds": interval_microseconds,
            "maximum_events": maximum_events,
            "offered_work_per_event_zeptojoules": wide_exact_json(offered_work),
            "intracellular_carriers_artificially_exhausted":
                exhaust_intracellular_carriers,
            "gate_dissipation_artificially_exhausted": exhaust_gate_dissipation,
            "first_open_event": first_open_event,
            "first_positive_outward_event": first_outward_event,
            "peak_local_outward_elementary_charges": peak_outward.to_string(),
            "final_open_gate_population": current.probe_gate_open_population().to_string(),
            "final_residue_zeptojoules": wide_exact_json(&final_residue),
            "total_accepted_work_zeptojoules": wide_exact_json(&total_accepted),
            "total_source_heat_zeptojoules": wide_exact_json(&total_source_heat),
            "total_delivered_gate_work_zeptojoules": wide_exact_json(&total_delivered),
            "total_residue_narrowing_heat_zeptojoules":
                wide_exact_json(&total_residue_narrowing_heat),
            "total_gate_exported_heat_zeptojoules":
                wide_exact_json(&total_gate_exported_heat),
            "all_offer_balances_close_exactly": all_offer_balances_close,
            "all_gate_input_balances_close_exactly": all_gate_input_balances_close,
            "all_carrier_balances_close_exactly": all_carrier_balances_close,
            "maximum_residue_numerator_bytes": maximum_residue_numerator_bytes,
            "maximum_residue_denominator_bytes": maximum_residue_denominator_bytes,
            "checkpoints": checkpoints,
        }),
        current,
    )
}

/// Candidate-47H dynamic regime map over the immutable task-1429 body. This
/// calls only test-compiled neuron physics, carries the exact motor state over
/// repeated arrivals, and never presents a stimulus to the organism.
fn temporal_gate_work_range_json(
    state: &ResidentCognitiveFormationState,
    original_cognitive_bytes: &[u8],
) -> Value {
    let predecessor_bytes = state.encode(usize::MAX).expect("encode untouched V41 body");
    let untouched_v41_round_trip_exact = predecessor_bytes == original_cognitive_bytes;
    let source_census = source_work_to_motor_reservoir_range_json(state);
    let route_results = source_census["route_results"]
        .as_array()
        .expect("candidate-47F copied route results");
    let scales = [(0_i64, 1_i64), (1, 4), (1, 2), (1, 1), (2, 1), (4, 1)];
    let intervals = [62_500_u32, 125_000, 250_000, 500_000];
    let mut samples = Vec::new();
    let mut cold_continuation = Vec::new();
    let mut cold_tested_motors = std::collections::BTreeSet::new();

    for route in route_results {
        if route.get("error").is_some() {
            samples.push(route.clone());
            continue;
        }
        let motor_hex = route["motor_lineage"]
            .as_str()
            .expect("candidate motor lineage");
        let motor = lineage_from_hex(motor_hex);
        let active_clock = route["active_clock"]
            .as_u64()
            .expect("candidate active clock");
        let source_work = wide_exact_from_json(&route["total_source_work_zeptojoules"]);
        let (cohort_index, neuron_index) = mounted_neuron_location(state, motor);
        let cohort = &state.cohorts[cohort_index];
        let anatomy = &cohort.anatomy.neuron_anatomies()[neuron_index];
        let predecessor = &cohort.state.neurons()[neuron_index];

        for (scale_numerator, scale_denominator) in scales {
            let offered = &source_work * BigInt::from(scale_numerator)
                / BigInt::from(scale_denominator);
            for interval_microseconds in intervals {
                let (sample, _) = transduced_gate_sample_json(
                    anatomy,
                    predecessor,
                    &offered,
                    interval_microseconds,
                    256,
                    false,
                    false,
                );
                samples.push(json!({
                    "active_clock": active_clock,
                    "motor_lineage": motor_hex,
                    "source_scale": format!("{scale_numerator}/{scale_denominator}"),
                    "sample": sample,
                }));
            }
        }

        let (zero_work, _) = transduced_gate_sample_json(
            anatomy,
            predecessor,
            &BigRational::zero(),
            250_000,
            256,
            false,
            false,
        );
        let (exhausted_carriers, _) = transduced_gate_sample_json(
            anatomy,
            predecessor,
            &source_work,
            250_000,
            256,
            true,
            false,
        );
        let (exhausted_gate, _) = transduced_gate_sample_json(
            anatomy,
            predecessor,
            &source_work,
            250_000,
            256,
            false,
            true,
        );
        samples.push(json!({
            "active_clock": active_clock,
            "motor_lineage": motor_hex,
            "controls": {
                "zero_work": zero_work,
                "exhausted_intracellular_carriers": exhausted_carriers,
                "exhausted_gate_dissipation": exhausted_gate,
            },
        }));

        let is_vocal = motor_hex.ends_with("00c5") || motor_hex.ends_with("04fb");
        if is_vocal && cold_tested_motors.insert(motor) {
            let (uninterrupted, _) = transduced_gate_sample_json(
                anatomy,
                predecessor,
                &source_work,
                250_000,
                256,
                false,
                false,
            );
            let uninterrupted_crossing = uninterrupted["first_positive_outward_event"].as_u64();
            if let Some(crossing) = uninterrupted_crossing {
                let split = u32::try_from(crossing.saturating_sub(1)).unwrap();
                let (_, midpoint_neuron) = transduced_gate_sample_json(
                    anatomy,
                    predecessor,
                    &source_work,
                    250_000,
                    split,
                    false,
                    false,
                );
                let midpoint_state = with_replaced_mounted_neuron(state, motor, midpoint_neuron);
                let midpoint_bytes = midpoint_state
                    .encode(usize::MAX)
                    .expect("encode sub-threshold copied body");
                let cold_state = ResidentCognitiveFormationState::decode(
                    &midpoint_bytes,
                    usize::MAX,
                )
                .expect("cold-decode sub-threshold copied body");
                let (cold_cohort, cold_neuron) = mounted_neuron_location(&cold_state, motor);
                let cold_anatomy = &cold_state.cohorts[cold_cohort]
                    .anatomy
                    .neuron_anatomies()[cold_neuron];
                let cold_predecessor = &cold_state.cohorts[cold_cohort].state.neurons()[cold_neuron];
                let (continued, _) = transduced_gate_sample_json(
                    cold_anatomy,
                    cold_predecessor,
                    &source_work,
                    250_000,
                    256 - split,
                    false,
                    false,
                );
                let continued_relative = continued["first_positive_outward_event"].as_u64();
                cold_continuation.push(json!({
                    "motor_lineage": motor_hex,
                    "uninterrupted_first_positive_outward_event": crossing,
                    "cold_split_after_event": split,
                    "midpoint_encoded_bytes": midpoint_bytes.len(),
                    "midpoint_reencode_exact": cold_state
                        .encode(usize::MAX)
                        .expect("re-encode cold midpoint") == midpoint_bytes,
                    "continued_relative_first_positive_outward_event": continued_relative,
                    "cold_absolute_first_positive_outward_event":
                        continued_relative.map(|relative| u64::from(split) + relative),
                    "crossing_preserved_across_cold_restore":
                        continued_relative.map(|relative| u64::from(split) + relative)
                            == Some(crossing),
                }));
            } else {
                cold_continuation.push(json!({
                    "motor_lineage": motor_hex,
                    "uninterrupted_first_positive_outward_event": Value::Null,
                    "crossing_preserved_across_cold_restore": false,
                    "reason": "no outward event within 256 repeated real-work events",
                }));
            }
        }
    }

    let (severed, severed_bridge_count) = severed_learned_motor_copy(state);
    let severed_route_count = source_work_to_motor_reservoir_range_json(&severed)
        ["route_results"]
        .as_array()
        .map_or(0, Vec::len);
    json!({
        "measurement_only": true,
        "production_compiled": false,
        "candidate": "47H intrinsic receiving-gate temporal work integration",
        "copied_body_cognitive_format": "GLCOG041",
        "untouched_v41_round_trip_exact": untouched_v41_round_trip_exact,
        "source_carriers_enter_motor": false,
        "a0116_transition_work_phase_reused": false,
        "recovery_material_created": false,
        "persistent_schema_bytes_added": 0,
        "maximum_repeated_events": 256,
        "source_scales": ["0/1", "1/4", "1/2", "1/1", "2/1", "4/1"],
        "interval_microseconds": intervals,
        "samples": samples,
        "cold_continuation": cold_continuation,
        "severed_bridge_count": severed_bridge_count,
        "severed_route_count": severed_route_count,
        "permutation_falsifier_inherited_from_47f":
            source_census["synthetic_order_invariance"].clone(),
    })
}

fn source_work_motor_candidate_falsifier_json(state: &ResidentCognitiveFormationState) -> Value {
    let connected = source_work_to_motor_reservoir_range_json(state);
    let (severed, severed_bridge_count) = severed_learned_motor_copy(state);
    let disconnected = source_work_to_motor_reservoir_range_json(&severed);
    let severed_route_count = disconnected["route_results"].as_array().map_or(0, Vec::len);
    json!({
        "connected": connected,
        "severed": disconnected,
        "severed_bridge_count": severed_bridge_count,
        "severed_route_count": severed_route_count,
    })
}

/// Sweep the candidate source across the exact copied body's respiratory
/// carrier extent and the three physical articulator coordinates already
/// implicated by its learned vocal routes.  This is measurement-only: every
/// altered posture is a disposable in-memory control and no named sound,
/// target waveform, or production state is authored.
fn copied_body_l13_acoustic_range_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let current_glottis = body.axis(BodyAxis::GlottalAperture);
    let section_zero = body.axis(BodyAxis::VocalTractSection0Area);
    let section_seven = body.axis(BodyAxis::VocalTractSection7Area);
    let controls = [
        ("copied", current_glottis, section_zero, section_seven),
        (
            "glottis-minimum",
            BodyAxis::GlottalAperture.anatomy().minimum,
            section_zero,
            section_seven,
        ),
        (
            "glottis-neutral",
            BodyAxis::GlottalAperture.anatomy().neutral,
            section_zero,
            section_seven,
        ),
        (
            "glottis-maximum",
            BodyAxis::GlottalAperture.anatomy().maximum,
            section_zero,
            section_seven,
        ),
        (
            "learned-section-0-minus-one",
            current_glottis,
            section_zero.saturating_sub(1),
            section_seven,
        ),
        (
            "learned-section-0-plus-one",
            current_glottis,
            section_zero.saturating_add(1),
            section_seven,
        ),
        (
            "learned-section-7-minus-one",
            current_glottis,
            section_zero,
            section_seven.saturating_sub(1),
        ),
        (
            "learned-section-7-plus-one",
            current_glottis,
            section_zero,
            section_seven.saturating_add(1),
        ),
    ];
    let samples = controls
        .into_iter()
        .map(|(name, glottis, section_zero, section_seven)| {
            let mut axes = *body.axes();
            axes[BodyAxis::GlottalAperture.index()] = glottis;
            axes[BodyAxis::VocalTractSection0Area.index()] = section_zero;
            axes[BodyAxis::VocalTractSection7Area.index()] = section_seven;
            let control = ArticulatedBodyState::from_physical_state(
                axes,
                body.lung_air_microlitres(),
                body.proprioception_initialized(),
            )
            .and_then(|control| {
                control.with_articulatory_acoustic_state(body.articulatory_acoustic_state())
            })
            .expect("copied-body acoustic range posture");
            let work_range = [0_u128, 1, 2, 4, 8, 16]
                .into_iter()
                .map(|carriers| {
                    let transition =
                        settle_native_articulatory_interval(control.clone(), &[], carriers, 4_000)
                            .expect("copied-body acoustic range settlement");
                    let peak = transition
                        .radiated_pressure_pcm
                        .iter()
                        .map(|sample| sample.unsigned_abs())
                        .max()
                        .unwrap_or(0);
                    let nonzero = transition
                        .radiated_pressure_pcm
                        .iter()
                        .filter(|sample| **sample != 0)
                        .count();
                    json!({
                        "respiratory_efferent_carriers": carriers.to_string(),
                        "applied_respiratory_carriers": transition.applied_motor_quanta.to_string(),
                        "stalled_respiratory_carriers": transition.stalled_motor_quanta.to_string(),
                        "peak_pressure": peak,
                        "nonzero_pressure_samples": nonzero,
                    })
                })
                .collect::<Vec<_>>();
            json!({
                "control": name,
                "glottal_aperture": glottis,
                "learned_section_0_area": section_zero,
                "learned_section_7_area": section_seven,
                "work_range": work_range,
            })
        })
        .collect::<Vec<_>>();
    json!({
        "measurement_only": true,
        "input_body_round_trip_exact": ArticulatedBodyState::decode(
            &body.encode().expect("copied body range encoding")
        ).expect("copied body range decoding") == *body,
        "controls": samples,
    })
}

fn one_clock_body_return_falsifier_json(
    state: &ResidentCognitiveFormationState,
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    let connected = retained_frontier_motor_range_json(state, articulated_body, 1);
    json!({
        "production_compiled": true,
        "scope": "one connected motor clock plus its exact proprioceptive return",
        "connected": connected,
    })
}

fn artificial_neutral_unpin_control_json(
    state: &ResidentCognitiveFormationState,
    body: Option<&ArticulatedBodyState>,
) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let mut neutral_axes = *body.axes();
    for axis in BODY_AXES {
        let anatomy = axis.anatomy();
        let position = body.axis(axis);
        if (position == anatomy.minimum || position == anatomy.maximum)
            && position != anatomy.neutral
        {
            neutral_axes[axis.index()] = anatomy.neutral;
        }
    }
    let unpinned = ArticulatedBodyState::from_physical_state(
        neutral_axes,
        body.lung_air_microlitres(),
        body.proprioception_initialized(),
    )
    .expect("artificial neutral-axis control")
    .with_articulatory_acoustic_state(body.articulatory_acoustic_state())
    .expect("preserve copied acoustic state in artificial control");
    let forced_axis_changes = BODY_AXES
        .into_iter()
        .filter_map(|axis| {
            let before = body.axis(axis);
            let after = unpinned.axis(axis);
            (before != after).then(|| {
                json!({
                    "axis": format!("{axis:?}"),
                    "copied_position": before,
                    "artificial_position": after,
                })
            })
        })
        .collect::<Vec<_>>();
    let learned_bridge_replay = retained_frontier_motor_range_json(state, Some(&unpinned), 1);
    json!({
        "production_compiled": true,
        "control_only": true,
        "prohibited_as_repair": true,
        "purpose": "isolate whether copied retained and one-carrier learned motor traffic move when only pathological accumulated stops are artificially unpinned",
        "forced_axis_change_count": forced_axis_changes.len(),
        "forced_axis_changes": forced_axis_changes,
        "lung_air_preserved": unpinned.lung_air_microlitres() == body.lung_air_microlitres(),
        "proprioception_flag_preserved":
            unpinned.proprioception_initialized() == body.proprioception_initialized(),
        "acoustic_state_preserved":
            unpinned.articulatory_acoustic_state() == body.articulatory_acoustic_state(),
        "one_carrier_learned_bridge_replay": learned_bridge_replay,
    })
}

/// Exercise the compiled V8 body law on the exact decoded production body.
/// This changes only disposable in-memory copies. It does not neutralize the
/// input body, author a motor meaning, or bypass the ordinary body codec and
/// proprioceptive evidence boundary.
fn candidate_antagonist_tissue_proof_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return json!({"error": "copied body absent"});
    };
    let stopped_axes = BODY_AXES
        .into_iter()
        .filter(|axis| {
            let anatomy = axis.anatomy();
            let position = body.axis(*axis);
            position != anatomy.neutral
                && (position == anatomy.minimum || position == anatomy.maximum)
        })
        .collect::<Vec<_>>();
    let mut released = body.clone();
    let mut first_release = std::collections::BTreeMap::new();
    let mut returned_to_neutral_at_ms = None;
    for elapsed_ms in 1_u64..=4_096 {
        let transition = settle_body_effector_drives(
            &released,
            &AdmittedBodyEffectorDrives::quiescent(),
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .expect("candidate copied-body passive settlement");
        for axis in &stopped_axes {
            if transition.successor.axis(*axis) != body.axis(*axis) {
                first_release.entry(*axis).or_insert(elapsed_ms);
            }
        }
        released = transition.successor;
        if BODY_AXES
            .iter()
            .all(|axis| released.axis(*axis) == axis.anatomy().neutral)
            && BODY_AXES.iter().all(|axis| {
                [
                    BodyEffectorDirection::TowardMinimum,
                    BodyEffectorDirection::TowardMaximum,
                ]
                .into_iter()
                .all(|direction| {
                    released.antagonist_activation(BodyEffectorTerminal::new(*axis, direction)) == 0
                })
            })
        {
            returned_to_neutral_at_ms = Some(elapsed_ms);
            break;
        }
    }

    let learned_terminals = [
        BodyEffectorTerminal::new(
            BodyAxis::VocalTractSection0Area,
            BodyEffectorDirection::TowardMaximum,
        ),
        BodyEffectorTerminal::new(
            BodyAxis::VocalTractSection7Area,
            BodyEffectorDirection::TowardMinimum,
        ),
    ];
    let one_carrier_twitches = learned_terminals.map(|terminal| {
        let neutral = ArticulatedBodyState::at_neutral();
        let drive = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
            terminal,
            outward_elementary_carriers: 1,
        }])
        .expect("candidate learned one-carrier admission");
        let first =
            settle_body_effector_drives(&neutral, &drive, BODY_SETTLEMENT_CLOCK_MICROSECONDS)
                .expect("candidate learned one-carrier settlement");
        let source =
            admit_articulated_body_consequence_source(1, &first.proprioceptive_consequences)
                .expect("candidate one-carrier body source");
        let mut exact_motor_causes = source
            .joint_source_ports()
            .iter()
            .map(exact_moved_effector_terminal)
            .collect::<Result<Vec<_>, _>>()
            .expect("candidate exact moved-terminal evidence")
            .into_iter()
            .flatten()
            .map(|cause| format!("{cause:?}"))
            .collect::<Vec<_>>();
        exact_motor_causes.sort_unstable();
        exact_motor_causes.dedup();
        let cold = ArticulatedBodyState::decode(
            &first.successor.encode().expect("candidate twitch encodes"),
        )
        .expect("candidate twitch cold decodes");
        let cold_exact = cold == first.successor;
        let first_position = first.successor.axis(terminal.axis());
        let first_activation = first.successor.antagonist_activation(terminal);
        let mut successor = cold;
        let mut returned_at_ms = None;
        for elapsed_ms in 2_u64..=512 {
            successor = settle_body_effector_drives(
                &successor,
                &AdmittedBodyEffectorDrives::quiescent(),
                BODY_SETTLEMENT_CLOCK_MICROSECONDS,
            )
            .expect("candidate twitch relaxation")
            .successor;
            if successor.axis(terminal.axis()) == terminal.axis().anatomy().neutral
                && successor.antagonist_activation(terminal) == 0
            {
                returned_at_ms = Some(elapsed_ms);
                break;
            }
        }
        json!({
            "terminal": format!("{terminal:?}"),
            "first_position": first_position,
            "first_activation_units": first_activation,
            "moved_on_first_ms": first_position != terminal.axis().anatomy().neutral,
            "exact_motor_causes": exact_motor_causes,
            "cold_restore_exact": cold_exact,
            "returned_to_neutral_at_ms": returned_at_ms,
        })
    });

    let axis = BodyAxis::VocalTractSection0Area;
    let minimum = BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMinimum);
    let maximum = BodyEffectorTerminal::new(axis, BodyEffectorDirection::TowardMaximum);
    let opposed = settle_body_effector_drives(
        &ArticulatedBodyState::at_neutral(),
        &AdmittedBodyEffectorDrives::admit(vec![
            BodyEffectorDrive {
                terminal: minimum,
                outward_elementary_carriers: 8,
            },
            BodyEffectorDrive {
                terminal: maximum,
                outward_elementary_carriers: 8,
            },
        ])
        .expect("candidate equal-antagonist admission"),
        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
    )
    .expect("candidate equal-antagonist settlement");

    let mut sustained = ArticulatedBodyState::at_neutral();
    let one_per_ms = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
        terminal: maximum,
        outward_elementary_carriers: 1,
    }])
    .expect("candidate sustained admission");
    let mut sustained_stall = 0_u128;
    for _ in 0..1_000 {
        let transition = settle_body_effector_drives(
            &sustained,
            &one_per_ms,
            BODY_SETTLEMENT_CLOCK_MICROSECONDS,
        )
        .expect("candidate sustained settlement");
        sustained_stall = sustained_stall
            .checked_add(
                transition
                    .proprioceptive_consequences
                    .iter()
                    .map(|consequence| consequence.stalled_carriers)
                    .sum::<u128>(),
            )
            .expect("candidate sustained stall width");
        sustained = transition.successor;
    }

    let saturation = settle_body_effector_drives(
        &ArticulatedBodyState::at_neutral(),
        &AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
            terminal: maximum,
            outward_elementary_carriers: 100_000,
        }])
        .expect("candidate saturation admission"),
        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
    )
    .expect("candidate saturation settlement");

    let composition_drive = AdmittedBodyEffectorDrives::admit(vec![BodyEffectorDrive {
        terminal: maximum,
        outward_elementary_carriers: 1,
    }])
    .expect("candidate composition admission");
    let neutral = ArticulatedBodyState::at_neutral();
    let whole = settle_body_effector_drives(&neutral, &composition_drive, 250_000)
        .expect("candidate whole duration")
        .successor;
    let first = settle_body_effector_drives(&neutral, &composition_drive, 64_000)
        .expect("candidate split first duration")
        .successor;
    let split =
        settle_body_effector_drives(&first, &AdmittedBodyEffectorDrives::quiescent(), 186_000)
            .expect("candidate split second duration")
            .successor;

    json!({
        "production_law_compiled_in_test": true,
        "input_body_encoded_bytes": body.encode().expect("candidate input body encodes").len(),
        "v8_roundtrip_exact": ArticulatedBodyState::decode(
            &body.encode().expect("candidate copied body encodes")
        ).expect("candidate copied body decodes") == *body,
        "stopped_non_neutral_axes": stopped_axes
            .iter()
            .map(|axis| format!("{axis:?}"))
            .collect::<Vec<_>>(),
        "all_stops_released_on_first_ms": first_release.len() == stopped_axes.len()
            && first_release.values().all(|elapsed| *elapsed == 1),
        "first_release_ms": first_release
            .into_iter()
            .map(|(axis, elapsed)| (format!("{axis:?}"), elapsed))
            .collect::<std::collections::BTreeMap<_, _>>(),
        "all_axes_returned_to_neutral_at_ms": returned_to_neutral_at_ms,
        "learned_one_carrier_twitches": one_carrier_twitches,
        "equal_antagonists_position_unchanged": opposed.successor.axis(axis) == axis.anatomy().neutral,
        "equal_antagonists_activation_zero": opposed.successor.antagonist_activation(minimum) == 0
            && opposed.successor.antagonist_activation(maximum) == 0,
        "sustained_one_per_ms_position": sustained.axis(axis),
        "sustained_one_per_ms_is_interior": sustained.axis(axis) > axis.anatomy().minimum
            && sustained.axis(axis) < axis.anatomy().maximum,
        "sustained_one_per_ms_total_stall": sustained_stall.to_string(),
        "saturation_stalled_carriers": saturation.proprioceptive_consequences[0]
            .stalled_carriers.to_string(),
        "duration_64_plus_186_equals_250": split == whole,
    })
}

fn articulated_body_axis_census_json(body: Option<&ArticulatedBodyState>) -> Value {
    let Some(body) = body else {
        return Value::Null;
    };
    let axes = BODY_AXES
        .into_iter()
        .map(|axis| {
            let anatomy = axis.anatomy();
            let position = body.axis(axis);
            json!({
                "axis": format!("{axis:?}"),
                "minimum": anatomy.minimum,
                "neutral": anatomy.neutral,
                "maximum": anatomy.maximum,
                "position": position,
                "at_minimum": position == anatomy.minimum,
                "at_maximum": position == anatomy.maximum,
                "at_neutral": position == anatomy.neutral,
            })
        })
        .collect::<Vec<_>>();
    let limit_count = axes
        .iter()
        .filter(|axis| {
            axis["at_minimum"].as_bool() == Some(true) || axis["at_maximum"].as_bool() == Some(true)
        })
        .count();
    let quiescent = settle_body_effector_drives(
        body,
        &AdmittedBodyEffectorDrives::quiescent(),
        BODY_SETTLEMENT_CLOCK_MICROSECONDS,
    )
    .expect("copied-body quiescent settlement");
    json!({
        "axis_count": axes.len(),
        "limit_count": limit_count,
        "lung_air_microlitres": body.lung_air_microlitres(),
        "proprioception_initialized": body.proprioception_initialized(),
        "acoustic_state_quiescent": body.articulatory_acoustic_state().is_quiescent(),
        "quiescent_successor_equals_predecessor": quiescent.successor == *body,
        "quiescent_reached_terminal_count": quiescent.reached_terminal_count,
        "quiescent_consequence_count": quiescent.proprioceptive_consequences.len(),
        "axes": axes,
    })
}

#[test]
fn reservoir_probe_dump() {
    let Ok(input) = std::env::var("GUALA_PROBE_IN") else {
        return;
    };
    let out_path = std::env::var("GUALA_PROBE_OUT").expect("GUALA_PROBE_OUT must be set");
    let mut entries: Vec<PathBuf> = fs::read_dir(&input)
        .expect("read probe input directory")
        .map(|entry| entry.expect("dir entry").path())
        .filter(|path| path.extension().map_or(false, |ext| ext == "glorun"))
        .collect();
    entries.sort();
    let mut records = Vec::new();
    for path in &entries {
        let bytes = fs::read(path).expect("read envelope");
        let (organism_tick, cognitive, articulated_body) = parse_envelope_with_body(&bytes);
        let body_mechanics_range_only =
            std::env::var_os("GUALA_PROBE_BODY_MECHANICS_RANGE_ONLY").is_some();
        let artificial_unpin_only = std::env::var_os("GUALA_PROBE_ARTIFICIAL_UNPIN_ONLY").is_some();
        let motor_work_range_only = std::env::var_os("GUALA_PROBE_MOTOR_WORK_RANGE_ONLY").is_some();
        let source_work_motor_range_only =
            std::env::var_os("GUALA_PROBE_SOURCE_WORK_MOTOR_RANGE_ONLY").is_some();
        let temporal_gate_work_range_only =
            std::env::var_os("GUALA_PROBE_TEMPORAL_GATE_WORK_ONLY").is_some();
        let antagonist_activation_range_only =
            std::env::var_os("GUALA_PROBE_ANTAGONIST_ACTIVATION_RANGE_ONLY").is_some();
        let candidate_tissue_proof_only =
            std::env::var_os("GUALA_PROBE_CANDIDATE_TISSUE_PROOF_ONLY").is_some();
        let record = if temporal_gate_work_range_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for temporal gate-work range");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "temporal_gate_work_range":
                    temporal_gate_work_range_json(&state, &cognitive),
            })
        } else if source_work_motor_range_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for source-work motor range");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "source_work_to_motor_reservoir_range":
                    source_work_motor_candidate_falsifier_json(&state),
            })
        } else if candidate_tissue_proof_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for candidate tissue proof");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "candidate_antagonist_tissue_proof":
                    candidate_antagonist_tissue_proof_json(articulated_body.as_ref()),
                "connected_and_severed_motor_transduction":
                    integrated_motor_transduction_falsifier_json(
                        &state,
                        articulated_body.as_ref(),
                    ),
                "copied_body_l13_acoustic_range":
                    copied_body_l13_acoustic_range_json(articulated_body.as_ref()),
            })
        } else if body_mechanics_range_only {
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "copied_body_passive_mechanics_range":
                    copied_body_passive_mechanics_range_json(articulated_body.as_ref()),
            })
        } else if antagonist_activation_range_only {
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "copied_body_antagonist_activation_range":
                    copied_body_antagonist_activation_range_json(articulated_body.as_ref()),
            })
        } else if artificial_unpin_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for artificial unpin control");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "artificial_neutral_unpin_control":
                    artificial_neutral_unpin_control_json(&state, articulated_body.as_ref()),
            })
        } else if motor_work_range_only {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state for motor-work range");
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "motor_inward_preparation_energy_range":
                    motor_inward_preparation_energy_range_json(&state),
                "retained_frontier_motor_work_range":
                    retained_frontier_motor_range_json(
                        &state,
                        articulated_body.as_ref(),
                        1,
                    ),
            })
        } else if cognitive.is_empty() {
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "cognitive": "absent",
                "cohorts": [],
            })
        } else {
            let state = ResidentCognitiveFormationState::decode(&cognitive, usize::MAX)
                .expect("decode cognitive state");
            let cohorts: Vec<Value> = state.cohorts.iter().map(cohort_json).collect();
            let motor_reachability = motor_reachability_json(&state);
            let skip_ranges = std::env::var_os("GUALA_PROBE_SKIP_RANGES").is_some();
            let body_return_only = std::env::var_os("GUALA_PROBE_BODY_RETURN_ONLY").is_some();
            let production_body_range_only =
                std::env::var_os("GUALA_PROBE_PRODUCTION_BODY_RANGE_ONLY").is_some();
            let motor_bridge_active_range = (!skip_ranges && !production_body_range_only)
                .then(|| motor_bridge_active_range_json(&state));
            let motor_bridge_gradient_population_range = (!skip_ranges
                && !production_body_range_only)
                .then(|| motor_bridge_gradient_population_range_json(&state));
            let retained_frontier_motor_range = (!skip_ranges || production_body_range_only)
                .then(|| retained_frontier_motor_range_json(&state, articulated_body.as_ref(), 3));
            let motor_inward_preparation_energy_range =
                motor_inward_preparation_energy_range_json(&state);
            let integrated_motor_transduction_falsifier =
                (!body_return_only && !production_body_range_only).then(|| {
                    integrated_motor_transduction_falsifier_json(&state, articulated_body.as_ref())
                });
            let one_clock_body_return_falsifier = body_return_only
                .then(|| one_clock_body_return_falsifier_json(&state, articulated_body.as_ref()));
            // BOUNDARY CENSUS (bridge campaign): contact counts by exact
            // layer pair — the L11->L12 number is the bridge's scoreboard.
            let mut boundary_counts = std::collections::BTreeMap::<String, u64>::new();
            {
                let layer_of = |lineage: [u8; 16]| {
                    state.cohorts.iter().find_map(|cohort| {
                        cohort
                            .anatomy
                            .mounts()
                            .iter()
                            .zip(cohort.anatomy.neuron_lineages())
                            .find_map(|(mount, candidate)| {
                                (*candidate == lineage).then(|| mount.place().layer())
                            })
                    })
                };
                for (left, right) in state.electrical_fabric.contact_endpoints() {
                    let a = layer_of(state.electrical_fabric.lineages()[left]);
                    let b = layer_of(state.electrical_fabric.lineages()[right]);
                    if let (Some(a), Some(b)) = (a, b) {
                        let (low, high) = if a <= b { (a, b) } else { (b, a) };
                        *boundary_counts.entry(format!("{low}->{high}")).or_default() += 1;
                    }
                }
            }
            let mounted = state
                .cohorts
                .iter()
                .flat_map(|cohort| {
                    cohort
                        .anatomy
                        .mounts()
                        .iter()
                        .zip(cohort.anatomy.neuron_lineages())
                        .map(|(mount, lineage)| (*lineage, mount.place().layer()))
                })
                .collect::<Vec<_>>();
            let electrical_fabric = state
                .electrical_fabric
                .contact_endpoints()
                .zip(
                    state
                        .electrical_fabric
                        .anatomy()
                        .contact_anatomies()
                        .iter()
                        .zip(state.electrical_fabric.state().contact_states()),
                )
                .map(|((left, right), (anatomy, contact_state))| {
                    let left_lineage = state.electrical_fabric.lineages()[left];
                    let right_lineage = state.electrical_fabric.lineages()[right];
                    let layer = |lineage| {
                        mounted.iter().find_map(|(candidate, layer)| {
                            (*candidate == lineage).then_some(*layer)
                        })
                    };
                    let lineage_hex = |lineage: [u8; 16]| {
                        lineage
                            .iter()
                            .map(|byte| format!("{byte:02x}"))
                            .collect::<String>()
                    };
                    let (phase_numerator, phase_denominator) =
                        contact_state.carrier_phase().parts();
                    json!({
                        "left_lineage": lineage_hex(left_lineage),
                        "left_layer": layer(left_lineage),
                        "right_lineage": lineage_hex(right_lineage),
                        "right_layer": layer(right_lineage),
                        "conductance_picosiemens": exact_json(anatomy.conductance_picosiemens()),
                        "effective_conductance_picosiemens": exact_json(
                            anatomy
                                .effective_conductance(contact_state)
                                .expect("probe contact state matches anatomy"),
                        ),
                        "carrier_phase": format!("{phase_numerator}/{phase_denominator}"),
                        "conducting_channel_population": contact_state
                            .conducting_channel_population()
                            .to_string(),
                        "transition_work_phase": exact_json(
                            contact_state.transition_work_phase(),
                        ),
                    })
                })
                .collect::<Vec<_>>();
            let lineage_hex = |lineage: [u8; 16]| {
                lineage
                    .iter()
                    .map(|byte| format!("{byte:02x}"))
                    .collect::<String>()
            };
            let retained_mosaics = state
                .mosaics
                .iter()
                .map(|retained| {
                    json!({
                        "recurrent_lineage": retained.recurrent_lineage.map(lineage_hex),
                        "member_lineages": retained
                            .mosaic
                            .member_lineages()
                            .iter()
                            .copied()
                            .map(lineage_hex)
                            .collect::<Vec<_>>(),
                        "original_bonds": retained
                            .mosaic
                            .original_bonds()
                            .iter()
                            .map(|bond| {
                                let (left, right) = bond.endpoints();
                                json!({
                                    "left": lineage_hex(left),
                                    "right": lineage_hex(right),
                                    "parallel_ordinal": bond.parallel_ordinal(),
                                })
                            })
                            .collect::<Vec<_>>(),
                        "recurrence_bonds": retained
                            .mosaic
                            .recurrence_bonds()
                            .iter()
                            .map(|bond| {
                                let (left, right) = bond.endpoints();
                                json!({
                                    "left": lineage_hex(left),
                                    "right": lineage_hex(right),
                                    "parallel_ordinal": bond.parallel_ordinal(),
                                })
                            })
                            .collect::<Vec<_>>(),
                    })
                })
                .collect::<Vec<_>>();
            json!({
                "file": path.file_name().unwrap().to_string_lossy(),
                "organism_tick": organism_tick,
                "articulated_body_axis_census":
                    articulated_body_axis_census_json(articulated_body.as_ref()),
                "generation": state.generation,
                "unexpressed_electrical_seed_count": state.unexpressed_electrical_seeds.len(),
                "dormant_lineage_seed_count": state.dormant_lineage_seeds.len(),
                "electrical_fabric": electrical_fabric,
                "retained_mosaics": retained_mosaics,
                "motor_reachability": motor_reachability,
                "motor_bridge_active_range": motor_bridge_active_range,
                "motor_bridge_gradient_population_range": motor_bridge_gradient_population_range,
                "retained_frontier_motor_range": retained_frontier_motor_range,
                "motor_inward_preparation_energy_range":
                    motor_inward_preparation_energy_range,
                "integrated_motor_transduction_falsifier":
                    integrated_motor_transduction_falsifier,
                "one_clock_body_return_falsifier": one_clock_body_return_falsifier,
                "boundary_contact_counts": boundary_counts.iter().map(|(k,v)| (k.clone(), json!(v))).collect::<serde_json::Map<_,_>>(),
                "cohorts": cohorts,
            })
        };
        records.push(record);
    }
    fs::write(
        &out_path,
        serde_json::to_string_pretty(&json!({ "records": records })).expect("serialize"),
    )
    .expect("write probe output");
}
