#!/usr/bin/env python3
"""tests/test_frame_aligned_kinematic_projection.py — Geometry-Only Check for Frame-Aligned Kinematic Projection.

BOUNDARY DISCLOSURE & ARCHITECTURAL CONTRACT:
1. GEOMETRY-ONLY CHECK: This test validates that the frame-aligned angular-grid projection
   conforms strictly to the mounted optical model (FOCAL_SITE_MILLIDEGREES = 375).
   A successful test establishes only that the geometric coordinate transform behaves correctly.
   It does NOT establish autonomous object recognition, does NOT demonstrate sensory disc
   discovery from raw pixels, and does NOT authorize consequence transfer between views.
2. INPUT PROVENANCE SEPARATION:
   - Tier 1 (Sensory / Kinematic): Raw focal array (sensed.focal_luminance_u8) and frame-aligned
     capture pose at the start of settlement (t0), before intra-beat motor re-aiming.
   - Tier 2 (Kinematic Transform): Exact angular-grid displacement relation:
       delta_column = -delta_capture_yaw / 375.0
       delta_row    = +delta_capture_pitch / 375.0
     preserving fractional coordinates without nearest-integer displacement rounding.
   - Tier 3 (Evaluator-Only World Truth): Target 3D coordinates and simulator object positions
     are used exclusively by test assertions to verify geometric consistency; they are
     strictly inaccessible to internal cognitive matching logic.
3. UNSUPPORTED CONTINUITY BOUNDARY:
   A discrepancy in projection or an out-of-bounds target indicates that continuity is
   unsupported by the available empirical evidence—it does not prove the presence of a distinct entity.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

import dsf_ai_service.guala_functional_loop
from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    FOCAL_COLUMNS,
    FOCAL_FIELD_MILLIDEGREES,
    FOCAL_ROWS,
    FOCAL_SITE_MILLIDEGREES,
    FunctionalOrganism,
    NOCICEPTION_MILLIKELVIN,
    _aim,
    _gaze_in_field,
)
from dsf_ai_service.guala_home_world import home_world_authority
from tests.test_guala_functional_organism import (
    IDENTITY,
    UNATTENDED,
    _hot_apple_in_reach,
)


def test_frame_aligned_angular_grid_kinematic_formula() -> None:
    """Validate exact angular grid displacement formula preserving fractional coordinates.

    In the mounted optical model:
      column = (dx + half_w) / 375.0  where dx = aim_yaw - head_yaw
      row    = (half_h - dy) / 375.0  where dy = aim_pitch - head_pitch
    Therefore, for a stationary target in the same body reference frame:
      delta_column = -delta_capture_yaw / 375.0
      delta_row    = +delta_capture_pitch / 375.0
    The vertical sign is positive because image row index increases downward.
    """
    half_w = FOCAL_FIELD_MILLIDEGREES[0] // 2  # 30,000 mdeg
    half_h = FOCAL_FIELD_MILLIDEGREES[1] // 2  # 22,500 mdeg

    # Stationary target aim bearing
    aim = (0, -40000)

    # Capture Pose 0
    head_0 = (0, -40000)
    gaze_0 = _gaze_in_field(head_0, aim)
    assert gaze_0 is not None, "Target must fall within initial focal field"

    col_0_sites = (aim[0] - head_0[0] + half_w) / float(FOCAL_SITE_MILLIDEGREES)
    row_0_sites = (half_h - (aim[1] - head_0[1])) / float(FOCAL_SITE_MILLIDEGREES)

    assert math.isclose(col_0_sites, 80.0), f"Center column must be 80.0 sites, got {col_0_sites}"
    assert math.isclose(row_0_sites, 60.0), f"Center row must be 60.0 sites, got {row_0_sites}"
    assert math.isclose(gaze_0[0], round(col_0_sites / (FOCAL_COLUMNS - 1), 6))
    assert math.isclose(gaze_0[1], round(row_0_sites / (FOCAL_ROWS - 1), 6))

    # Test suite of fractional and integer angular rotations
    test_displacements = [
        (+3750, 0),       # +3.75 degrees yaw right -> shifts column left by -10.0 sites
        (-3750, 0),       # -3.75 degrees yaw left  -> shifts column right by +10.0 sites
        (0, +3750),       # +3.75 degrees pitch up  -> shifts row down by +10.0 sites
        (0, -3750),       # -3.75 degrees pitch down -> shifts row up by -10.0 sites
        (+1875, -1875),   # Fractional 5.0 site diagonal shift
        (+562, +1125),    # Fractional non-integer site shifts: +1.49866... col, +3.0 row
    ]

    for d_yaw, d_pitch in test_displacements:
        head_k = (head_0[0] + d_yaw, head_0[1] + d_pitch)
        gaze_k = _gaze_in_field(head_k, aim)
        assert gaze_k is not None, f"Pose {head_k} should remain within focal field"

        col_k_sites = (aim[0] - head_k[0] + half_w) / float(FOCAL_SITE_MILLIDEGREES)
        row_k_sites = (half_h - (aim[1] - head_k[1])) / float(FOCAL_SITE_MILLIDEGREES)

        # Theoretical kinematic shifts
        expected_d_col = -float(d_yaw) / float(FOCAL_SITE_MILLIDEGREES)
        expected_d_row = +float(d_pitch) / float(FOCAL_SITE_MILLIDEGREES)

        actual_d_col = col_k_sites - col_0_sites
        actual_d_row = row_k_sites - row_0_sites

        assert math.isclose(actual_d_col, expected_d_col, abs_tol=1e-9), (
            f"Horizontal kinematic shift mismatch: expected {expected_d_col}, got {actual_d_col}"
        )
        assert math.isclose(actual_d_row, expected_d_row, abs_tol=1e-9), (
            f"Vertical kinematic shift mismatch: expected {expected_d_row}, got {actual_d_row}"
        )

        # Verify normalized coordinates match unrounded fractional sites
        expected_u = round(col_k_sites / (FOCAL_COLUMNS - 1), 6)
        expected_v = round(row_k_sites / (FOCAL_ROWS - 1), 6)
        assert math.isclose(gaze_k[0], expected_u, abs_tol=1e-6)
        assert math.isclose(gaze_k[1], expected_v, abs_tol=1e-6)


def test_focal_field_boundary_unsupported_continuity_cutoff() -> None:
    """Verify that when rotation exceeds the focal field bounds, projection returns None.

    Confirms the physical principle that out-of-field observations result in unsupported
    continuity rather than speculative coordinate extrapolations.
    """
    half_w = FOCAL_FIELD_MILLIDEGREES[0] // 2  # 30,000 mdeg
    half_h = FOCAL_FIELD_MILLIDEGREES[1] // 2  # 22,500 mdeg

    aim = (0, 0)

    # Just within bounds
    assert _gaze_in_field((half_w, 0), aim) is not None
    assert _gaze_in_field((-half_w, 0), aim) is not None
    assert _gaze_in_field((0, half_h), aim) is not None
    assert _gaze_in_field((0, -half_h), aim) is not None

    # Exceeding bounds by 1 millidegree -> sensory availability halts (returns None)
    assert _gaze_in_field((half_w + 1, 0), aim) is None, "Yaw exceeding half_w must halt"
    assert _gaze_in_field((-half_w - 1, 0), aim) is None, "Yaw exceeding -half_w must halt"
    assert _gaze_in_field((0, half_h + 1), aim) is None, "Pitch exceeding half_h must halt"
    assert _gaze_in_field((0, -half_h - 1), aim) is None, "Pitch exceeding -half_h must halt"


def test_frame_aligned_capture_pose_temporal_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that frame capture uses the organism pose at the start of settlement (t0).

    Directly witnesses the actual axes passed to the renderer (_world_retina_u8)
    and proves that they correspond strictly to the initial capture pose (t0),
    independent of subsequent intra-beat motor re-aiming during decide().
    """
    captured_renderer_axes: list[dict[str, Any]] = []
    orig_renderer = dsf_ai_service.guala_functional_loop._world_retina_u8

    def intercept_renderer(snapshot: Any, axes: tuple[Any, ...], sun: Any = None, pupil: bool = True) -> tuple[tuple[int, ...], Any]:
        axes_dict = {a[1]: a[3] for a in axes}
        captured_renderer_axes.append(axes_dict)
        return orig_renderer(snapshot, axes, sun=sun, pupil=pupil)

    monkeypatch.setattr(dsf_ai_service.guala_functional_loop, "_world_retina_u8", intercept_renderer)

    world = home_world_authority(identity=IDENTITY, expand_library=False)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=100)
    _hot_apple_in_reach(world, "hot-apple", NOCICEPTION_MILLIKELVIN + 25_000)

    # Initial capture pose (misaligned with target so decide() actively rotates head)
    initial_head = [15000, -20000]
    initial_eyes = [0, 0]
    organism._state["head"] = list(initial_head)
    organism._state["eyes"] = list(initial_eyes)
    organism._state["gaze_target"] = "hot-apple"

    loop = FunctionalPhysicalLoop()
    res = loop.settle(organism, world, UNATTENDED)

    # Witness Verification:
    # 1. Exactly one frame rendered during this beat
    assert len(captured_renderer_axes) == 1, "Renderer must be called exactly once per settlement"

    renderer_axes = captured_renderer_axes[0]
    # 2. Renderer received the initial pre-decide capture pose
    assert renderer_axes["neck_yaw"] == initial_head[0], (
        f"Renderer received yaw {renderer_axes['neck_yaw']}, expected capture pose {initial_head[0]}"
    )
    assert renderer_axes["neck_pitch"] == initial_head[1], (
        f"Renderer received pitch {renderer_axes['neck_pitch']}, expected capture pose {initial_head[1]}"
    )

    # 3. During decide(), organism updated head state toward target
    post_head = organism.head
    assert post_head != (initial_head[0], initial_head[1]), (
        f"Test requires head re-aiming: post_head {post_head} equals initial {initial_head}"
    )

    # 4. Prove that renderer received axes DISTINCT from post-decide state
    assert (renderer_axes["neck_yaw"], renderer_axes["neck_pitch"]) != post_head, (
        f"Temporal leakage: renderer axes {renderer_axes} match post-decide pose {post_head}"
    )
