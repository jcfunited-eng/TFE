"""Decisive audit of the live spoken-form cutover boundary.

This is not a readiness scoreboard.  It proves two source facts that prevent
the existing Krimelack owner from being described as the live substrate-true
spoken-form authority:

* the production PCM settlement still invokes the recurrent-motif owner; and
* Krimelack identity is decided from sign-only projections, even though its
  exemplar custody separately retains the complete exact L0--L4 field.

The production call site already has the exact ``auditory_l5`` experience,
joint stream settlement, and verified PCM/cochlear/causal capability.  A
non-flattening learned-form owner can therefore be mounted at that one
transaction boundary after its recognition relation exists.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = (
    ROOT
    / "dsf_ai_service"
    / "v4"
    / "guala_physical_runtime_core.py"
)
KRIMELACK_KIND = (
    ROOT
    / "dsf_ai_service"
    / "substrate"
    / "auditory_krimelack_kind.py"
)
RECURRENT_MOTIF = (
    ROOT
    / "dsf_ai_service"
    / "substrate"
    / "auditory_recurrent_motif.py"
)
LIVE_MOTIF = (
    ROOT
    / "dsf_ai_service"
    / "substrate"
    / "auditory_live_motif.py"
)
WHOLE_ORGANISM_EPISODE = (
    ROOT
    / "dsf_ai_service"
    / "substrate"
    / "whole_organism_episode.py"
)
THING_MOSAIC = (
    ROOT
    / "dsf_ai_service"
    / "substrate"
    / "causal_thing_mosaic.py"
)
PASSIVE_THING_LEARNING = (
    ROOT
    / "dsf_ai_service"
    / "substrate"
    / "passive_whole_organism_thing_learning.py"
)


def _function(path: Path, name: str) -> ast.FunctionDef:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _source_segment(path: Path, node: ast.AST) -> str:
    source = path.read_text(encoding="utf-8")
    segment = ast.get_source_segment(source, node)
    assert segment is not None
    return segment


def _class_method(
    path: Path,
    class_name: str,
    method_name: str,
) -> ast.FunctionDef:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    ]
    assert len(classes) == 1
    methods = [
        node
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef) and node.name == method_name
    ]
    assert len(methods) == 1
    return methods[0]


def _attribute_calls(node: ast.AST) -> tuple[str, ...]:
    result = []
    for value in ast.walk(node):
        if not isinstance(value, ast.Call):
            continue
        function = value.func
        if isinstance(function, ast.Attribute):
            result.append(function.attr)
        elif isinstance(function, ast.Name):
            result.append(function.id)
    return tuple(result)


def test_live_pcm_settlement_exposes_the_complete_cutover_inputs_but_still_calls_recurrent_motif() -> None:
    terminal = _function(
        RUNTIME,
        "_advance_continuous_auditory_terminal_inline",
    )
    terminal_source = _source_segment(RUNTIME, terminal)
    calls = _attribute_calls(terminal)

    assert "verified_capability.verify_linkage(" in terminal_source
    assert "auditory_l5=auditory_l5" in terminal_source
    assert "joint_settlement=joint" in terminal_source
    assert "causal_settlement=settlement" in terminal_source
    assert "_auditory_full_field_transactions.stage(" in terminal_source
    assert "_auditory_full_field_transactions.complete_claim(" in (
        terminal_source
    )

    assert "_auditory_recurrent_motif_owner.fire(" in terminal_source
    assert "_auditory_recurrent_motif_owner.observe(" in terminal_source
    assert "_auditory_krimelack_live_authority" not in terminal_source
    assert "advance" not in (
        value
        for value in calls
        if value == "_auditory_krimelack_live_authority"
    )


def test_existing_krimelack_identity_is_a_reduced_sign_projection_not_full_field_equality() -> None:
    mount = _function(KRIMELACK_KIND, "_mount_component_paths")
    field_trit = _function(KRIMELACK_KIND, "_field_trit")
    mount_source = _source_segment(KRIMELACK_KIND, mount)
    trit_source = _source_segment(KRIMELACK_KIND, field_trit)

    assert "_field_trit(value)" in mount_source
    assert "_field_trit(value - prior_value)" in mount_source
    assert "return -1 if value < 0 else 1 if value > 0 else 0" in (
        trit_source
    )

    # Full evidence custody is not the same thing as full-field recognition:
    # the Krimelack path relation receives only the projected component paths.
    relation = _function(KRIMELACK_KIND, "_motif_locks")
    relation_source = _source_segment(KRIMELACK_KIND, relation)
    assert "left_value == right_value" in relation_source
    assert "Fraction" not in relation_source


def test_status_truthfully_names_the_unmounted_owner_and_the_reduced_relation() -> None:
    status = _function(RUNTIME, "auditory_l5_status")
    status_source = _source_segment(RUNTIME, status)

    assert '"active_hearing_authority": "auditory_recurrent_motif"' in (
        status_source
    )
    assert '"krimelack_live": {' in status_source
    assert '"active": False' in status_source
    assert '"retired_sign_flattened_cognition"' in status_source


def test_recurrent_motif_keeps_each_dsf_field_in_its_own_physical_temporal_lane() -> None:
    module_source = RECURRENT_MOTIF.read_text(encoding="utf-8")
    occurrence = _class_method(
        RECURRENT_MOTIF,
        "AuditoryReceptorOccurrence",
        "verify",
    )
    occurrence_source = _source_segment(RECURRENT_MOTIF, occurrence)
    peak_atoms = _function(RECURRENT_MOTIF, "_peak_atoms_from_experience")
    peak_source = _source_segment(RECURRENT_MOTIF, peak_atoms)
    neuron_id = _function(RECURRENT_MOTIF, "_peak_neuron_id")
    neuron_id_source = _source_segment(RECURRENT_MOTIF, neuron_id)

    assert (
        "COCHLEAR_CHANNEL_COUNT * 2 * len(DSF_FIELD_ORDER)"
        in module_source
    )
    assert "tuple(name for name, _value in fields) != DSF_FIELD_ORDER" in (
        occurrence_source
    )
    assert "not isinstance(value, Fraction)" in occurrence_source
    assert 'for component_kind in ("pressure", "phase")' in peak_source
    assert "for field_index, field_name in enumerate(DSF_FIELD_ORDER)" in (
        peak_source
    )
    assert "full_field_occurrences=support" in peak_source
    assert '"lane": lane.payload()' in neuron_id_source
    assert '"relation": relation.payload()' in neuron_id_source
    assert "decision_vector" not in neuron_id_source
    assert "score" not in neuron_id_source


def test_recurrent_motif_exact_loss_boundaries_are_explicit() -> None:
    receptor_mount = _function(
        RECURRENT_MOTIF,
        "receptor_experience_from_full_field_event",
    )
    receptor_source = _source_segment(RECURRENT_MOTIF, receptor_mount)
    peak_atoms = _function(RECURRENT_MOTIF, "_peak_atoms_from_experience")
    peak_source = _source_segment(RECURRENT_MOTIF, peak_atoms)
    neuron_id = _function(RECURRENT_MOTIF, "_peak_neuron_id")
    neuron_id_source = _source_segment(RECURRENT_MOTIF, neuron_id)

    assert "_authoritative_upper_basin" in receptor_source
    assert "for channel_index in upper" in receptor_source
    assert "unresolved.append(source_index)" in receptor_source
    assert "span_magnitude_relation=_order_relation(" in peak_source
    assert "same_polarity_endpoint_relation=_order_relation(" in peak_source
    assert "span_duration_relation=_order_relation(" in peak_source
    assert '"lane": lane.payload()' in neuron_id_source
    assert '"relation": relation.payload()' in neuron_id_source
    for absent_raw_identity in (
        "extrema",
        "full_field_occurrences",
        "source_time",
        "Fraction",
    ):
        assert absent_raw_identity not in neuron_id_source


def test_recurrent_motif_retains_exact_raw_witness_and_activation_support() -> None:
    peak_point = _function(RECURRENT_MOTIF, "_peak_point")
    activation = _function(RECURRENT_MOTIF, "_peak_activation")
    peak_point_source = _source_segment(RECURRENT_MOTIF, peak_point)
    activation_source = _source_segment(RECURRENT_MOTIF, activation)
    live_activation_payload = _function(LIVE_MOTIF, "_activation_payload")
    live_activation_source = _source_segment(
        LIVE_MOTIF,
        live_activation_payload,
    )

    assert "value=dict(fields)[field_name]" in peak_point_source
    assert "field_tuple_receipt_sha256=receipt" in peak_point_source
    assert "source_time=occurrence.source_time" in peak_point_source
    assert "occurrences = atom.full_field_occurrences" in activation_source
    assert "full_field_occurrences=occurrences" in activation_source
    assert "ordered_full_field_occurrence_receipt_sha256s" in (
        live_activation_source
    )
    assert "full_field_occurrence_count" in live_activation_source


def test_recurrent_motif_is_only_a_presemantic_observation_quotient() -> None:
    module_source = RECURRENT_MOTIF.read_text(encoding="utf-8")
    owner_observe = _class_method(
        RECURRENT_MOTIF,
        "AuditoryRecurrentMotifOwner",
        "observe",
    )
    owner_source = _source_segment(RECURRENT_MOTIF, owner_observe)

    assert "intentionally loses absolute level" in module_source
    assert "It is never raw-experience, word, meaning, or" in module_source
    assert "L6 identity" in module_source
    assert "source_set.intersection" in owner_source
    assert "meaning remains causal and separate" in owner_source
    for forbidden in (
        "tutor_label",
        "transcript",
        "nearest",
        "probability",
        "decision_vector",
    ):
        assert forbidden not in owner_source


def test_live_whole_organism_and_mosaic_custody_take_exact_settlement_roots_not_motif_identity() -> None:
    terminal = _function(
        RUNTIME,
        "_advance_continuous_auditory_terminal_inline",
    )
    terminal_source = _source_segment(RUNTIME, terminal)
    accept = _function(RUNTIME, "_accept_causal_settlement")
    accept_source = _source_segment(RUNTIME, accept)
    observe = _function(RUNTIME, "_observe_whole_organism_settlement")
    observe_source = _source_segment(RUNTIME, observe)
    verify_root = _function(WHOLE_ORGANISM_EPISODE, "_verify_root_field")
    verify_root_source = _source_segment(
        WHOLE_ORGANISM_EPISODE,
        verify_root,
    )
    roots = _function(THING_MOSAIC, "full_field_sensory_roots")
    roots_source = _source_segment(THING_MOSAIC, roots)
    passive_prepare = _class_method(
        PASSIVE_THING_LEARNING,
        "PassiveWholeOrganismThingLearningOwner",
        "prepare_admission",
    )
    passive_source = _source_segment(
        PASSIVE_THING_LEARNING,
        passive_prepare,
    )

    # The live joint authority proves that auditory L5 and causal settlement
    # are two views of the same PCM/cochlear/full-field transaction.
    assert "auditory_l5=auditory_l5" in terminal_source
    assert "causal_settlement=settlement" in terminal_source
    assert "joint_settlement=joint" in terminal_source

    # The whole organism receives that settlement directly. Motif identity is
    # neither substituted for it nor granted evidence authority here.
    assert "_observe_whole_organism_settlement(settlement)" in accept_source
    assert "settlement=settlement" in observe_source
    assert "recurrent_motif" not in observe_source
    assert "krimelack" not in observe_source

    # Every observed settlement substream becomes a root, and every root must
    # still contain the ordered exact seven-field tuples.
    assert "for interpretation in settlement.interpretations" in roots_source
    assert "if interpretation.state == \"observed\"" in roots_source
    assert "for substream in interpretation.substreams" in roots_source
    assert "tuples = evidence.get(\"field_tuples\")" in verify_root_source
    assert "!= DSF_FIELD_ORDER" in verify_root_source
    assert "_fraction_from_text" in verify_root_source

    # Passive mosaic learning opens the same settled custody and derives its
    # retained roots from it, with no motif result accepted as a substitute.
    assert "settlement = view.causal_settlement" in passive_source
    assert "roots = full_field_sensory_roots(settlement)" in passive_source
    assert "recurrent_motif" not in passive_source
    assert "krimelack" not in passive_source
