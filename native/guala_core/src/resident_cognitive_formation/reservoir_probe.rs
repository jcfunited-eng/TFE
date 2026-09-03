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
use crate::articulated_body_joint_source_builder::admit_articulated_body_consequence_source;
use crate::complete_neuron::RecoveryLaneAddress;
use crate::exact_rational::ExactRational;
use crate::joint_uf_source_adapter::admitted_episode_with_authored_intervals;
use crate::recovery_fluid_contact::ReachedRecoveryFluidAnatomy;
use crate::vestibular_neuron_path::FUNCTIONAL_VESTIBULAR_ANATOMY_CODEC_BYTES;
use crate::virtual_articulated_body::{
    settle_body_effector_drives, AdmittedBodyEffectorDrives, ArticulatedBodyState,
    BodyEffectorDrive, ARTICULATED_BODY_STATE_BYTES, BODY_AXES,
};
use num_rational::BigRational;
use num_traits::Zero;
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
                let transition = settle_body_effector_drives(&body, &admitted)
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
                articulated_body = Some(transition.successor);
                Some(json!({
                    "reached_terminal_count": transition.reached_terminal_count,
                    "consequences": consequences,
                    "sensory_return": sensory_return,
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

/// Run the proposed one-carrier transduction through the complete copied-body
/// three-clock settlement, then repeat after physically severing every learned
/// L11/L12 bridge. The switch exists only in the test build; both successors
/// are disposable in-memory copies.
fn integrated_motor_transduction_falsifier_json(
    state: &ResidentCognitiveFormationState,
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    super::TEST_ONE_CARRIER_ORDERING_MOTOR_TRANSDUCTION
        .store(true, std::sync::atomic::Ordering::Relaxed);
    let connected = retained_frontier_motor_range_json(state, articulated_body, 3);
    super::TEST_ONE_CARRIER_ORDERING_MOTOR_TRANSDUCTION
        .store(false, std::sync::atomic::Ordering::Relaxed);

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
    super::TEST_ONE_CARRIER_ORDERING_MOTOR_TRANSDUCTION
        .store(true, std::sync::atomic::Ordering::Relaxed);
    let disconnected = retained_frontier_motor_range_json(&severed, articulated_body, 3);
    super::TEST_ONE_CARRIER_ORDERING_MOTOR_TRANSDUCTION
        .store(false, std::sync::atomic::Ordering::Relaxed);
    json!({
        "production_compiled": false,
        "connected": connected,
        "severed": disconnected,
        "severed_bridge_count": removed.len(),
    })
}

fn one_clock_body_return_falsifier_json(
    state: &ResidentCognitiveFormationState,
    articulated_body: Option<&ArticulatedBodyState>,
) -> Value {
    super::TEST_ONE_CARRIER_ORDERING_MOTOR_TRANSDUCTION
        .store(true, std::sync::atomic::Ordering::Relaxed);
    let connected = retained_frontier_motor_range_json(state, articulated_body, 1);
    super::TEST_ONE_CARRIER_ORDERING_MOTOR_TRANSDUCTION
        .store(false, std::sync::atomic::Ordering::Relaxed);
    json!({
        "production_compiled": false,
        "scope": "one connected motor clock plus its exact proprioceptive return",
        "connected": connected,
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
    json!({
        "axis_count": axes.len(),
        "limit_count": limit_count,
        "lung_air_microlitres": body.lung_air_microlitres(),
        "proprioception_initialized": body.proprioception_initialized(),
        "acoustic_state_quiescent": body.articulatory_acoustic_state().is_quiescent(),
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
        let record = if cognitive.is_empty() {
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
            let motor_bridge_active_range =
                (!skip_ranges).then(|| motor_bridge_active_range_json(&state));
            let motor_bridge_gradient_population_range =
                (!skip_ranges).then(|| motor_bridge_gradient_population_range_json(&state));
            let retained_frontier_motor_range = (!skip_ranges)
                .then(|| retained_frontier_motor_range_json(&state, articulated_body.as_ref(), 3));
            let motor_inward_preparation_energy_range =
                motor_inward_preparation_energy_range_json(&state);
            let integrated_motor_transduction_falsifier = (!body_return_only).then(|| {
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
                        "carrier_phase": format!("{phase_numerator}/{phase_denominator}"),
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
