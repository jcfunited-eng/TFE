"""
wave_spillover.py — canonical spillover write function + Cell dataclass.

Shared between tools/wave_atlas_validator.py and dsf_ai_service/v4/wave_atlas.py.
Both import Cell and spill_write from here so the algorithm is never duplicated.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Callable

try:
    from wave_constants import (
        SATURATION_THRESHOLD, CHI_BAND, SUBDIVISION_TRIGGER, N_CELLS
    )
except ImportError:
    # Fallback when imported from a path that can't see tools/ directly.
    SATURATION_THRESHOLD = 5.0
    CHI_BAND = 5
    SUBDIVISION_TRIGGER = 8
    N_CELLS = 262144


@dataclass
class Cell:
    bindings: List[dict] = field(default_factory=list)
    aggregate_strength: float = 0.0
    # 16-dim complex, running unit-norm mean of all written phase vectors.
    # None until first write with a non-None phase_vec.
    phase_vec: Optional[np.ndarray] = None
    last_tick: int = 0
    saturated: bool = False


def spill_write(
    cells: Dict[int, Cell],
    chi_target: int,
    phase_vec_in: Optional[np.ndarray],
    binding: Optional[dict] = None,
    sat_thresh: float = SATURATION_THRESHOLD,
    chi_band: int = CHI_BAND,
    subdiv_trigger: int = SUBDIVISION_TRIGGER,
    _hop: int = 0,
    _hop_limit: int = 512,
    _on_subdivide: Optional[Callable[[int], None]] = None,
) -> Tuple[int, int]:
    """Spillover write per GL-SPC-WAVE-BAND-ATTENTION-EVE-20260630-59v1 §1.2.

    Returns (final_chi, hops) where hops = number of recursive steps taken.
    Commits the binding at final_chi via _commit_cell.

    Args:
        cells:         mutable dict[int, Cell] — the WaveAtlas cell store.
        chi_target:    requested write position (wraps mod N_CELLS).
        phase_vec_in:  16-dim complex phase vector, or None for phase-less writes.
        binding:       dict of binding fields; passed through to cell.bindings.
        _on_subdivide: callback(chi_center) fired when hops >= subdiv_trigger.
    """
    idx = int(chi_target) % N_CELLS
    cell = cells.get(idx)

    # Empty or unsaturated: commit here
    if cell is None or not cell.saturated:
        _commit_cell(cells, idx, phase_vec_in, binding, sat_thresh)
        return idx, _hop

    # Saturated: scan ±chi_band for best neighbor by phase affinity
    best_idx: Optional[int] = None
    best_affinity = -1.0
    norm_in = np.linalg.norm(phase_vec_in) if phase_vec_in is not None else 0.0

    for d in range(-chi_band, chi_band + 1):
        if d == 0:
            continue
        n_idx = (idx + d) % N_CELLS
        n = cells.get(n_idx)
        if n is None:
            coherence = 1.0
            resistance = 0.0
        else:
            if (phase_vec_in is not None and n.phase_vec is not None
                    and norm_in > 1e-12):
                norm_n = np.linalg.norm(n.phase_vec)
                coherence = (
                    abs(np.vdot(phase_vec_in, n.phase_vec))
                    / (norm_in * norm_n + 1e-12)
                    if norm_n > 1e-12 else 1.0
                )
            else:
                coherence = 1.0  # unknown phase → treat as fully compatible
            resistance = n.aggregate_strength
        affinity = coherence / (1.0 + resistance)
        if affinity > best_affinity:
            best_affinity, best_idx = affinity, n_idx

    if best_idx is None:
        # Shouldn't happen (chi_band > 0), but guard
        _commit_cell(cells, idx, phase_vec_in, binding, sat_thresh)
        return idx, _hop

    # Best neighbor is also saturated: recurse (wave propagates outward)
    best_cell = cells.get(best_idx)
    if best_cell is not None and best_cell.saturated:
        if _hop + 1 >= _hop_limit:
            _commit_cell(cells, best_idx, phase_vec_in, binding, sat_thresh)
            return best_idx, _hop + 1
        return spill_write(
            cells, best_idx, phase_vec_in, binding,
            sat_thresh, chi_band, subdiv_trigger,
            _hop + 1, _hop_limit, _on_subdivide,
        )

    # About to commit at best_idx: check subdivision trigger
    if _hop >= subdiv_trigger and _on_subdivide is not None:
        _on_subdivide(idx)

    _commit_cell(cells, best_idx, phase_vec_in, binding, sat_thresh)
    return best_idx, _hop + 1


def _commit_cell(
    cells: Dict[int, Cell],
    idx: int,
    phase_vec_in: Optional[np.ndarray],
    binding: Optional[dict],
    sat_thresh: float,
) -> None:
    """Create or update cell at idx. Updates running phase mean and saturation flag."""
    cell = cells.get(idx)
    if cell is None:
        cell = Cell()
        cells[idx] = cell

    strength = 1.0 if binding is None else float(binding.get("strength", 1.0))
    cell.bindings.append(binding if binding is not None else {})
    cell.aggregate_strength += strength

    # Running unit-norm mean of phase vectors (stable magnitude, good coherence signal)
    if phase_vec_in is not None:
        n = len(cell.bindings)
        if cell.phase_vec is None:
            cell.phase_vec = phase_vec_in.copy()
        else:
            # Incremental mean: mean_n = mean_{n-1} * (n-1)/n + x/n
            cell.phase_vec = cell.phase_vec * ((n - 1) / n) + phase_vec_in / n
        nrm = np.linalg.norm(cell.phase_vec)
        if nrm > 1e-12:
            cell.phase_vec = cell.phase_vec / nrm

    cell.saturated = cell.aggregate_strength > sat_thresh
