//! Authenticated lineage-preserving, ordered full-gate delivery preparation.
//!
//! This test-gated D3 seam performs no receptor, gate, membrane, recovery,
//! plasticity, or neuronal state transition. It binds the already mounted D2
//! lineages to every exact GLJSRC02 occurrence, evaluates each occurrence once,
//! proves MathLoom capacity across every reached UF gate, and exposes occurrence
//! order and gate order without merging independent sensory clocks. Physical
//! settlement remains unavailable until its numerical anatomy and transduction
//! laws are ratified.

use std::collections::{BTreeMap, BTreeSet};

use crate::joint_source_episode::{JointSourcePortView, NativeJointSourceEpisode};
use crate::joint_uf_neuron_boundary::{
    bind_neuron_perspective, prepare_complete_joint_field, required_mathloom_positions,
    JointNeuronBoundaryError, JointNeuronPerspective, SharedCompleteJointField,
};
use crate::mounted_joint_fractal::PreparedMountedGeneration;

const AUTHENTICATED_D2_LINEAGE_COUNT: usize = 96;

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
struct SourcePortIdentity {
    sense: u8,
    topology_index: u32,
    sensor_id: String,
    substream_id: String,
}

impl SourcePortIdentity {
    fn from_port(port: &JointSourcePortView) -> Self {
        Self {
            sense: port.sense,
            topology_index: port.topology_index,
            sensor_id: port.sensor_id.clone(),
            substream_id: port.substream_id.clone(),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct OrderedLineageBinding {
    lineage: [u8; 16],
    occurrence_index: usize,
    coordinate_index: usize,
    source_port_index: usize,
}

impl OrderedLineageBinding {
    pub(crate) fn lineage(self) -> [u8; 16] {
        self.lineage
    }

    pub(crate) fn occurrence_index(self) -> usize {
        self.occurrence_index
    }

    pub(crate) fn coordinate_index(self) -> usize {
        self.coordinate_index
    }

    pub(crate) fn source_port_index(self) -> usize {
        self.source_port_index
    }
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct OrderedGateDelivery<'a> {
    occurrence: &'a OrderedOccurrenceDeliveryPlan,
    gate_index: usize,
}

impl<'a> OrderedGateDelivery<'a> {
    pub(crate) fn occurrence_index(self) -> usize {
        self.occurrence.occurrence_index
    }

    pub(crate) fn gate_index(self) -> usize {
        self.gate_index
    }

    pub(crate) fn bindings(self) -> &'a [OrderedLineageBinding] {
        &self.occurrence.bindings
    }

    pub(crate) fn perspective(
        self,
        binding: OrderedLineageBinding,
    ) -> Result<JointNeuronPerspective<'a>, OrderedGateDeliveryError> {
        if binding.occurrence_index != self.occurrence.occurrence_index
            || self
                .occurrence
                .bindings
                .get(binding.coordinate_index)
                .copied()
                != Some(binding)
        {
            return Err(OrderedGateDeliveryError::BindingOutsideOccurrence);
        }
        bind_neuron_perspective(
            &self.occurrence.shared,
            binding.coordinate_index,
            self.gate_index,
        )
        .map_err(OrderedGateDeliveryError::JointField)
    }
}

pub(crate) struct OrderedGateDeliveryIter<'a> {
    occurrence: &'a OrderedOccurrenceDeliveryPlan,
    next_gate_index: usize,
}

impl<'a> Iterator for OrderedGateDeliveryIter<'a> {
    type Item = OrderedGateDelivery<'a>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.next_gate_index >= self.occurrence.gate_count() {
            return None;
        }
        let gate_index = self.next_gate_index;
        self.next_gate_index += 1;
        Some(OrderedGateDelivery {
            occurrence: self.occurrence,
            gate_index,
        })
    }

    fn size_hint(&self) -> (usize, Option<usize>) {
        let remaining = self
            .occurrence
            .gate_count()
            .saturating_sub(self.next_gate_index);
        (remaining, Some(remaining))
    }
}

impl ExactSizeIterator for OrderedGateDeliveryIter<'_> {}

#[derive(Clone, Debug)]
pub(crate) struct OrderedOccurrenceDeliveryPlan {
    occurrence_index: usize,
    shared: SharedCompleteJointField,
    bindings: Box<[OrderedLineageBinding]>,
    required_mathloom_positions: usize,
}

impl OrderedOccurrenceDeliveryPlan {
    pub(crate) fn occurrence_index(&self) -> usize {
        self.occurrence_index
    }

    pub(crate) fn lineage_count(&self) -> usize {
        self.bindings.len()
    }

    pub(crate) fn gate_count(&self) -> usize {
        self.shared.result().gates.len()
    }

    pub(crate) fn required_mathloom_positions(&self) -> usize {
        self.required_mathloom_positions
    }

    pub(crate) fn bindings(&self) -> &[OrderedLineageBinding] {
        &self.bindings
    }

    pub(crate) fn ordered_gates(&self) -> OrderedGateDeliveryIter<'_> {
        OrderedGateDeliveryIter {
            occurrence: self,
            next_gate_index: 0,
        }
    }
}

#[derive(Clone, Debug)]
pub(crate) struct OrderedEpisodeDeliveryPlan {
    occurrences: Box<[OrderedOccurrenceDeliveryPlan]>,
    required_mathloom_positions: usize,
}

impl OrderedEpisodeDeliveryPlan {
    pub(crate) fn occurrence_count(&self) -> usize {
        self.occurrences.len()
    }

    pub(crate) fn lineage_count(&self) -> usize {
        self.occurrences
            .iter()
            .map(OrderedOccurrenceDeliveryPlan::lineage_count)
            .sum()
    }

    pub(crate) fn required_mathloom_positions(&self) -> usize {
        self.required_mathloom_positions
    }

    pub(crate) fn ordered_occurrences(&self) -> &[OrderedOccurrenceDeliveryPlan] {
        &self.occurrences
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) enum OrderedGateDeliveryError {
    JointField(JointNeuronBoundaryError),
    SourceAuthorityChanged,
    MountedFieldShapeChanged,
    MountedLineageChanged,
    DuplicateMountedLineage,
    DuplicateMountedSourceIdentity,
    AuthenticatedRosterCardinality { expected: usize, observed: usize },
    SourceOccurrenceCardinality,
    SourceLineageAbsent,
    DuplicateReachedLineage,
    DuplicateReachedSourcePort,
    BindingOutsideOccurrence,
}

fn mounted_lineages(
    mounted: &PreparedMountedGeneration,
) -> Result<BTreeMap<SourcePortIdentity, [u8; 16]>, OrderedGateDeliveryError> {
    let mut by_source = BTreeMap::new();
    let mut lineages = BTreeSet::new();
    for field in mounted.fields() {
        for neuron in field.neurons() {
            let perspective = neuron.perspective();
            let source_port = field
                .source_ports()
                .get(perspective.vertex_index)
                .ok_or(OrderedGateDeliveryError::MountedFieldShapeChanged)?;
            let lineage = neuron.successor().neuron_lineage;
            if lineage != perspective.neuron_lineage {
                return Err(OrderedGateDeliveryError::MountedLineageChanged);
            }
            if !lineages.insert(lineage) {
                return Err(OrderedGateDeliveryError::DuplicateMountedLineage);
            }
            if by_source
                .insert(SourcePortIdentity::from_port(source_port), lineage)
                .is_some()
            {
                return Err(OrderedGateDeliveryError::DuplicateMountedSourceIdentity);
            }
        }
    }
    if by_source.len() != AUTHENTICATED_D2_LINEAGE_COUNT {
        return Err(OrderedGateDeliveryError::AuthenticatedRosterCardinality {
            expected: AUTHENTICATED_D2_LINEAGE_COUNT,
            observed: by_source.len(),
        });
    }
    Ok(by_source)
}

fn preflight_occurrence(
    occurrence_index: usize,
    shared: SharedCompleteJointField,
    bindings: Vec<OrderedLineageBinding>,
) -> Result<OrderedOccurrenceDeliveryPlan, OrderedGateDeliveryError> {
    if shared.vertex_count() != bindings.len() || bindings.is_empty() {
        return Err(OrderedGateDeliveryError::SourceOccurrenceCardinality);
    }
    let mut required_positions = 1usize;
    for (coordinate_index, binding) in bindings.iter().copied().enumerate() {
        if binding.occurrence_index != occurrence_index
            || binding.coordinate_index != coordinate_index
        {
            return Err(OrderedGateDeliveryError::SourceOccurrenceCardinality);
        }
    }
    for gate_index in 0..shared.result().gates.len() {
        for binding in bindings.iter().copied() {
            let perspective =
                bind_neuron_perspective(&shared, binding.coordinate_index, gate_index)
                    .map_err(OrderedGateDeliveryError::JointField)?;
            for local_frame_index in 0..perspective.local_sev_len() {
                perspective
                    .local_sev(local_frame_index)
                    .map_err(OrderedGateDeliveryError::JointField)?;
            }
            required_positions = required_positions.max(
                required_mathloom_positions(perspective)
                    .map_err(OrderedGateDeliveryError::JointField)?,
            );
        }
    }
    Ok(OrderedOccurrenceDeliveryPlan {
        occurrence_index,
        shared,
        bindings: bindings.into_boxed_slice(),
        required_mathloom_positions: required_positions,
    })
}

fn preflight_episode(
    occurrence_inputs: Vec<(SharedCompleteJointField, Vec<OrderedLineageBinding>)>,
) -> Result<OrderedEpisodeDeliveryPlan, OrderedGateDeliveryError> {
    let mut occurrences = Vec::new();
    occurrences
        .try_reserve_exact(occurrence_inputs.len())
        .map_err(|_| OrderedGateDeliveryError::SourceOccurrenceCardinality)?;
    let mut lineages = BTreeSet::new();
    let mut source_ports = BTreeSet::new();
    let mut required_positions = 1usize;
    for (occurrence_index, (shared, bindings)) in occurrence_inputs.into_iter().enumerate() {
        for binding in bindings.iter().copied() {
            if !lineages.insert(binding.lineage) {
                return Err(OrderedGateDeliveryError::DuplicateReachedLineage);
            }
            if !source_ports.insert(binding.source_port_index) {
                return Err(OrderedGateDeliveryError::DuplicateReachedSourcePort);
            }
        }
        let occurrence = preflight_occurrence(occurrence_index, shared, bindings)?;
        required_positions = required_positions.max(occurrence.required_mathloom_positions());
        occurrences.push(occurrence);
    }
    if lineages.len() != AUTHENTICATED_D2_LINEAGE_COUNT {
        return Err(OrderedGateDeliveryError::AuthenticatedRosterCardinality {
            expected: AUTHENTICATED_D2_LINEAGE_COUNT,
            observed: lineages.len(),
        });
    }
    Ok(OrderedEpisodeDeliveryPlan {
        occurrences: occurrences.into_boxed_slice(),
        required_mathloom_positions: required_positions,
    })
}

pub(crate) fn prepare_authenticated_ordered_gate_delivery(
    mounted: &PreparedMountedGeneration,
    source: &NativeJointSourceEpisode,
) -> Result<OrderedEpisodeDeliveryPlan, OrderedGateDeliveryError> {
    if mounted.source_authority() != source.joint_source_authority_receipt()
        || mounted.source_body() != source.joint_source_body().as_ref()
    {
        return Err(OrderedGateDeliveryError::SourceAuthorityChanged);
    }
    let mounted_lineages = mounted_lineages(mounted)?;
    let mut occurrence_inputs = Vec::new();
    occurrence_inputs
        .try_reserve_exact(source.joint_source_occurrences().len())
        .map_err(|_| OrderedGateDeliveryError::SourceOccurrenceCardinality)?;
    for occurrence_index in 0..source.joint_source_occurrences().len() {
        let shared = prepare_complete_joint_field(source, occurrence_index)
            .map_err(OrderedGateDeliveryError::JointField)?;
        let mut bindings = Vec::new();
        bindings
            .try_reserve_exact(shared.vertex_count())
            .map_err(|_| OrderedGateDeliveryError::SourceOccurrenceCardinality)?;
        for (coordinate_index, source_port_index) in
            shared.port_indices().iter().copied().enumerate()
        {
            let source_port = source
                .joint_source_ports()
                .get(source_port_index)
                .ok_or(OrderedGateDeliveryError::MountedFieldShapeChanged)?;
            let lineage = mounted_lineages
                .get(&SourcePortIdentity::from_port(source_port))
                .copied()
                .ok_or(OrderedGateDeliveryError::SourceLineageAbsent)?;
            bindings.push(OrderedLineageBinding {
                lineage,
                occurrence_index,
                coordinate_index,
                source_port_index,
            });
        }
        occurrence_inputs.push((shared, bindings));
    }
    preflight_episode(occurrence_inputs)
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use num_rational::BigRational;

    use super::*;
    use crate::joint_uf_neuron_boundary::{
        prepare_complete_joint_field_fixture, settle_shared_dsf_mathloom, MathLoomAnatomy,
    };
    use crate::joint_uf_source_adapter::EvaluatedJointSourceOccurrence;
    use crate::joint_uf_v1_4::{
        evaluate_with_physical_bounds, JointIntersampleLaw, JointUfCoordinateBounds, JointUfInput,
        JointUfPhysicalBounds,
    };

    fn lineage(ordinal: u64) -> [u8; 16] {
        let mut value = [0u8; 16];
        value[..8].copy_from_slice(b"GLNLINE1");
        value[8..].copy_from_slice(&ordinal.to_be_bytes());
        value
    }

    fn occurrence_fixture(
        occurrence_index: usize,
        source_port_start: usize,
        coordinate_count: usize,
    ) -> (SharedCompleteJointField, Vec<OrderedLineageBinding>) {
        let frames = 6usize;
        let fields = (0..frames)
            .map(|frame| {
                (0..coordinate_count)
                    .map(|coordinate| {
                        ((frame + 1) as f64 * (source_port_start + coordinate + 1) as f64) / 997.0
                    })
                    .collect::<Vec<_>>()
            })
            .collect::<Vec<_>>();
        let result = evaluate_with_physical_bounds(
            JointUfInput {
                times: (0..frames)
                    .map(|value| BigRational::from_integer(value.into()))
                    .collect(),
                fields,
                relevance: vec![1.0; frames],
                intersample_law: JointIntersampleLaw::SampledVolumeAndRelevancePiecewiseLinear,
            },
            JointUfPhysicalBounds::new(
                vec![JointUfCoordinateBounds::new(0.0, 1.0).unwrap(); coordinate_count],
                BigRational::from_integer(5.into()),
            )
            .unwrap(),
        )
        .unwrap();
        let source_port_indices =
            (source_port_start..source_port_start + coordinate_count).collect::<Vec<_>>();
        let shared = prepare_complete_joint_field_fixture(
            Arc::from(&b"ordered-episode-source"[..]),
            [7u8; 32],
            occurrence_index,
            EvaluatedJointSourceOccurrence {
                port_indices: source_port_indices.clone(),
                groups: vec![(0..coordinate_count).collect()],
                field: result,
            },
        )
        .unwrap();
        let bindings = source_port_indices
            .into_iter()
            .enumerate()
            .map(
                |(coordinate_index, source_port_index)| OrderedLineageBinding {
                    lineage: lineage((source_port_index + 1) as u64),
                    occurrence_index,
                    coordinate_index,
                    source_port_index,
                },
            )
            .collect();
        (shared, bindings)
    }

    fn two_clock_episode() -> OrderedEpisodeDeliveryPlan {
        preflight_episode(vec![
            occurrence_fixture(0, 0, 64),
            occurrence_fixture(1, 64, 32),
        ])
        .unwrap()
    }

    #[test]
    fn independent_sight_and_sound_clocks_retain_all_ninety_six_lineages() {
        let plan = two_clock_episode();
        assert_eq!(plan.occurrence_count(), 2);
        assert_eq!(plan.lineage_count(), 96);
        assert_eq!(plan.ordered_occurrences()[0].lineage_count(), 64);
        assert_eq!(plan.ordered_occurrences()[1].lineage_count(), 32);
        let lineages = plan
            .ordered_occurrences()
            .iter()
            .flat_map(|occurrence| occurrence.bindings())
            .map(|binding| binding.lineage())
            .collect::<BTreeSet<_>>();
        assert_eq!(lineages.len(), 96);
    }

    #[test]
    fn every_occurrence_delivers_every_gate_once_in_causal_order() {
        let plan = two_clock_episode();
        for occurrence in plan.ordered_occurrences() {
            let observed = occurrence
                .ordered_gates()
                .map(|gate| {
                    assert_eq!(gate.occurrence_index(), occurrence.occurrence_index());
                    for binding in gate.bindings().iter().copied() {
                        let perspective = gate.perspective(binding).unwrap();
                        assert_eq!(perspective.coordinate_index(), binding.coordinate_index());
                        assert!(perspective.local_sev_len() > 0);
                    }
                    gate.gate_index()
                })
                .collect::<Vec<_>>();
            assert_eq!(observed, (0..occurrence.gate_count()).collect::<Vec<_>>());
        }
    }

    #[test]
    fn episode_preflight_width_retains_all_seven_fields() {
        let plan = two_clock_episode();
        let anatomy = MathLoomAnatomy::new(plan.required_mathloom_positions()).unwrap();
        for occurrence in plan.ordered_occurrences() {
            for gate in occurrence.ordered_gates() {
                for binding in gate.bindings().iter().copied() {
                    let delivery =
                        settle_shared_dsf_mathloom(gate.perspective(binding).unwrap(), anatomy)
                            .unwrap();
                    assert_eq!(delivery.constraints().len(), 7);
                    assert_eq!(
                        delivery.perspective().coordinate_index(),
                        binding.coordinate_index()
                    );
                }
            }
        }
    }

    #[test]
    fn duplicate_or_incomplete_episode_rosters_are_refused() {
        let sight = occurrence_fixture(0, 0, 64);
        let mut sound = occurrence_fixture(1, 64, 32);
        sound.1[31].lineage = sound.1[30].lineage;
        assert_eq!(
            preflight_episode(vec![sight, sound]).unwrap_err(),
            OrderedGateDeliveryError::DuplicateReachedLineage
        );

        assert_eq!(
            preflight_episode(vec![occurrence_fixture(0, 0, 64)]).unwrap_err(),
            OrderedGateDeliveryError::AuthenticatedRosterCardinality {
                expected: 96,
                observed: 64,
            }
        );
    }

    #[test]
    fn a_binding_cannot_cross_between_independent_occurrences() {
        let plan = two_clock_episode();
        let sight_gate = plan.ordered_occurrences()[0]
            .ordered_gates()
            .next()
            .unwrap();
        let sound_binding = plan.ordered_occurrences()[1].bindings()[0];
        assert_eq!(
            sight_gate.perspective(sound_binding).unwrap_err(),
            OrderedGateDeliveryError::BindingOutsideOccurrence
        );
    }
}
