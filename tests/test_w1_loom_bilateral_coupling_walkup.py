from dsf_ai_service.substrate.canonical_l6 import canonical_l6_direction
from tools.probe_w1_loom_bilateral_coupling_walkup import (
    _fission,
    _recurrent,
    _settle,
    _transition_cells,
)


def test_transition_cells_retain_causal_order_and_exact_event_magnitude() -> None:
    ascending = _transition_cells(
        ("physical-edge",),
        (
            (0, 1, 0, 2, 0, 4),
            (0, -1, 0, -3, 0, -2),
        ),
    )
    reordered = _transition_cells(
        ("physical-edge",),
        (
            (0, 4, 0, 2, 0, 1),
            (0, -2, 0, -3, 0, -1),
        ),
    )

    assert ascending
    assert reordered
    assert ascending != reordered


def test_recurrence_uses_canonical_l6_and_causal_fission() -> None:
    shared = ("shared",)
    down_only = ("down",)
    go_only = ("go",)
    left_only = ("left",)
    memories = {
        "down": _recurrent(
            (
                frozenset((shared, down_only)),
                frozenset((shared, down_only)),
                frozenset((shared, down_only)),
                frozenset((shared, down_only)),
                frozenset((shared,)),
            )
        ),
        "go": _recurrent(
            (
                frozenset((shared, go_only)),
                frozenset((shared, go_only)),
                frozenset((shared, go_only)),
                frozenset((shared, go_only)),
                frozenset((shared,)),
            )
        ),
        "left": _recurrent(
            (
                frozenset((shared, left_only)),
                frozenset((shared, left_only)),
                frozenset((shared, left_only)),
                frozenset((shared, left_only)),
                frozenset((shared,)),
            )
        ),
    }

    assert canonical_l6_direction(
        dimensions=5,
        matching_non_null=4,
        matching_quiescent=0,
    ).locked
    assert _fission(memories) == {
        "down": frozenset((down_only,)),
        "go": frozenset((go_only,)),
        "left": frozenset((left_only,)),
    }


def test_settlement_refuses_unknown_and_ambiguous_populations() -> None:
    memories = {
        "down": frozenset((("down-a",), ("down-b",))),
        "go": frozenset((("go-a",), ("go-b",))),
    }

    assert _settle(memories, frozenset())["state"] == "unknown"
    assert _settle(
        memories,
        frozenset(
            (
                ("down-a",),
                ("down-b",),
                ("go-a",),
                ("go-b",),
            )
        ),
    )["state"] == "ambiguous"
