from __future__ import annotations

import inspect

import pytest

from tools.isolated_auditory_direct_full_field_topology import (
    COMPONENT_COUNT,
    COMPONENT_ORDER,
    DirectFullFieldTopology,
    _change_masks,
    _digest,
    topology_from_events,
)


def test_change_masks_keep_all_64_component_positions_in_time_order() -> None:
    first = tuple(0 for _value in range(COMPONENT_COUNT))
    second = tuple(
        1 if index in {0, 31, 32, 63} else 0
        for index in range(COMPONENT_COUNT)
    )
    third = tuple(
        2 if index in {31, 63} else value
        for index, value in enumerate(second)
    )

    assert _change_masks((first, second, second, third)) == (
        (1 << 0) | (1 << 31) | (1 << 32) | (1 << 63),
        (1 << 31) | (1 << 63),
    )


def test_change_mask_grid_is_bounded_and_rejects_flattening() -> None:
    with pytest.raises(ValueError, match="tuple-index grid"):
        _change_masks(((0,) * (COMPONENT_COUNT - 1),))
    with pytest.raises(ValueError, match="tuple-index grid"):
        _change_masks(((0,) * COMPONENT_COUNT, (False,) * COMPONENT_COUNT))


def test_topology_authority_excludes_frame_duration_from_identity() -> None:
    topology_payload = {
        "change_masks_hex": ["0000000000000001"],
        "component_order": list(COMPONENT_ORDER),
        "schema": "guala.audit.auditory_joint_l4_change_mask_topology.v1",
    }
    provisional = DirectFullFieldTopology(
        frame_count=100,
        change_masks=(1,),
        component_order=COMPONENT_ORDER,
        left_event_receipt_sha256="1" * 64,
        right_event_receipt_sha256="2" * 64,
        full_field_witness_root_sha256="3" * 64,
        topology_root_sha256=_digest(topology_payload),
        authority_receipt_sha256="0" * 64,
    )
    value = DirectFullFieldTopology(
        frame_count=provisional.frame_count,
        change_masks=provisional.change_masks,
        component_order=provisional.component_order,
        left_event_receipt_sha256=provisional.left_event_receipt_sha256,
        right_event_receipt_sha256=provisional.right_event_receipt_sha256,
        full_field_witness_root_sha256=(
            provisional.full_field_witness_root_sha256
        ),
        topology_root_sha256=provisional.topology_root_sha256,
        authority_receipt_sha256=_digest(provisional.payload()),
    )

    value.verify()
    assert value.topology_key() == (1,)
    assert "frame_count" not in topology_payload


def test_adapter_never_reads_receptor_experience_or_occurrences() -> None:
    source = inspect.getsource(topology_from_events)

    assert ".experience" not in source
    assert ".occurrences" not in source
    assert "AuditoryReceptorFullFieldEvent" in source
