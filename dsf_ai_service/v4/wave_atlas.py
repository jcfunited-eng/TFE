"""
wave_atlas.py — WaveAtlas: lock-free cell-array atlas for Guala substrate.

GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1 Phase 1.
Ships behind env flag WAVE_ATLAS_ENABLED=1. LivingAtlas still serves all reads.

Cell array: 262,144 positions, lazy-allocated as a dict.
Write path: spillover via shared wave_spillover.spill_write.
Subdivision: trigger detection + log in Phase 1. Firing in Phase 1a.
"""

import os
import sys
import logging

# ─── Shared constants + spillover (tools/ in both dev and container) ──────────
_tools = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools')
if os.path.isdir(_tools) and _tools not in sys.path:
    sys.path.insert(0, _tools)

from wave_constants import (
    SATURATION_THRESHOLD, CHI_BAND, SUBDIVISION_TRIGGER, N_CELLS, PHASE_DIMS
)
from wave_spillover import Cell, spill_write, _commit_cell  # noqa: F401

_log = logging.getLogger("gualaloom")


class WaveAtlas:
    """Lock-free wave atlas. Parallel write target during Phase 1; read-only
    consumers migrate in Phase 2.

    Interface matches LivingAtlas.record() so existing callsites work unchanged
    once the flag is enabled.
    """

    def __init__(self):
        # Lazy-allocated cell dict. Key = chi_value % N_CELLS.
        self.cells: dict = {}
        self._subdivision_count = 0

    # ──────────────────────────────────────────────────────────────────────────
    # Write path
    # ──────────────────────────────────────────────────────────────────────────

    def record(
        self,
        section_name: str,
        motif_id: int,
        chi_value: int,
        tick=None,
        salience: float = 1.0,
        dwell_ticks: int = 0,
        arousal: float = 0.5,
        valence: float = 0.0,
        surprise: float = 0.0,
        need_pressure: float = 0.0,
        sensory_refs=None,
        episode_ref=None,
        source: str = "corpus",
        bundle_id=None,
        presence=None,
        location=None,
        sky_state=None,
        polarity: int = 1,
        phase_vec=None,
        function_score: float = 0.0,
        **_extra,
    ) -> int:
        """Record a binding at chi_value via spillover. Returns final_chi.

        phase_vec: 16-dim complex numpy array from krimelack transduction.
                   None for bindings without phase data (old atlas migrations).
        function_score: [0,1] derived from krimelack signature. 0 = content,
                        1 = function word. Stored on binding for recall ranking.
        """
        binding = {
            "section": section_name,
            "motif": motif_id,
            "chi": chi_value,
            "salience": salience,
            "function_score": function_score,
            "source": source,
            "polarity": polarity,
        }
        if tick is not None:
            binding["tick"] = tick
        if dwell_ticks:
            binding["dwell_ticks"] = dwell_ticks
        if episode_ref is not None:
            binding["episode_ref"] = episode_ref
        if bundle_id is not None:
            binding["bundle_id"] = bundle_id

        # Strength for spillover resistance = salience-scaled (mirrors LivingAtlas impulse)
        strength = max(0.05, 0.05 * salience)
        binding["strength"] = strength

        final_chi, hops = spill_write(
            self.cells,
            chi_value,
            phase_vec,
            binding,
            _on_subdivide=self._on_subdivide,
        )

        if hops > 0:
            _log.debug(
                "[WaveAtlas] spillover %d hops: chi %d → %d (section=%s)",
                hops, chi_value, final_chi, section_name,
            )

        return final_chi

    # ──────────────────────────────────────────────────────────────────────────
    # Read path
    # ──────────────────────────────────────────────────────────────────────────

    def read_near(self, chi_value: int, radius: int = 5) -> list:
        """Return all bindings in cells[chi_value ± radius]. No lock, O(radius)."""
        out = []
        for d in range(-radius, radius + 1):
            cell = self.cells.get((chi_value + d) % N_CELLS)
            if cell is not None:
                out.extend(cell.bindings)
        return out

    # ──────────────────────────────────────────────────────────────────────────
    # Boot rebuild
    # ──────────────────────────────────────────────────────────────────────────

    def rebuild_from(self, living_atlas) -> None:
        """One-time boot rebuild from LivingAtlas.

        Bindings are direct-committed at each entry's actual chi key (no spillover)
        to preserve the existing LivingAtlas layout. Phase_vec is None for all
        migrated bindings (no phase data captured before Phase 1).
        """
        n_cells_before = len(self.cells)
        n_bindings = 0

        for chi_k, entries in living_atlas.entries.items():
            idx = int(chi_k) % N_CELLS
            cell = self.cells.get(idx)
            if cell is None:
                cell = Cell()
                self.cells[idx] = cell
            for e in entries:
                cell.bindings.append(e)
                cell.aggregate_strength += float(e.get("strength", 0.05))
                n_bindings += 1
            cell.saturated = cell.aggregate_strength > SATURATION_THRESHOLD

        n_cells = len(self.cells) - n_cells_before
        print(
            f"[GualaLoom] WaveAtlas rebuilt from LivingAtlas: "
            f"{n_cells} cells, {n_bindings} bindings"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Persistence (64-C: save/load to skip rebuild on subsequent boots)
    # ──────────────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize WaveAtlas for EFS persistence. Phase_vec stored as list."""
        import numpy as np
        cells_out = {}
        for chi_idx, cell in self.cells.items():
            pv = None
            if cell.phase_vec is not None:
                pv = cell.phase_vec.tolist()  # complex list: [[re, im], ...]
            cells_out[str(chi_idx)] = {
                "bindings": cell.bindings,
                "aggregate_strength": cell.aggregate_strength,
                "phase_vec": pv,
                "last_tick": cell.last_tick,
                "saturated": cell.saturated,
            }
        return {"version": 1, "cells": cells_out}

    def load_from_dict(self, state: dict) -> int:
        """Restore WaveAtlas from persisted dict. Returns number of cells loaded."""
        import numpy as np
        self.cells = {}
        for chi_str, cell_data in state.get("cells", {}).items():
            chi_idx = int(chi_str)
            cell = Cell()
            cell.bindings = cell_data["bindings"]
            cell.aggregate_strength = cell_data["aggregate_strength"]
            if cell_data.get("phase_vec") is not None:
                cell.phase_vec = np.array(cell_data["phase_vec"], dtype=np.complex128)
            cell.last_tick = cell_data.get("last_tick", 0)
            cell.saturated = cell_data.get("saturated", False)
            self.cells[chi_idx] = cell
        return len(self.cells)

    # ──────────────────────────────────────────────────────────────────────────
    # Subdivision (Phase 1: detect + log; Phase 1a: fire)
    # ──────────────────────────────────────────────────────────────────────────

    def _on_subdivide(self, chi_center: int) -> None:
        self._subdivision_count += 1
        _log.info(
            "[WaveAtlas] subdivision triggered at chi=%d (total=%d) — "
            "Phase 1: logged only, firing in Phase 1a",
            chi_center, self._subdivision_count,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Diagnostics
    # ──────────────────────────────────────────────────────────────────────────

    def cell_count(self) -> int:
        return len(self.cells)

    def binding_count(self) -> int:
        return sum(len(c.bindings) for c in self.cells.values())

    def subdivision_count(self) -> int:
        return self._subdivision_count
