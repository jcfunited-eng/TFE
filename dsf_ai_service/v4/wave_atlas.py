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

import numpy as np

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

        # GL-CMD-WAVE-SEMANTICS-85 Part B.1: reinforce existing binding if
        # (chi, section, motif) key already present within spillover range.
        # Prevents unbounded append growth — same (chi,section,motif) → one binding.
        for _d in range(-CHI_BAND, CHI_BAND + 1):
            _cidx = (chi_value + _d) % N_CELLS
            _cell = self.cells.get(_cidx)
            if _cell is None:
                continue
            for _b in _cell.bindings:
                if (_b.get("chi") == chi_value
                        and _b.get("section") == section_name
                        and _b.get("motif") == motif_id):
                    # Reinforce: accumulate strength + update cell aggregate
                    _b["strength"] = _b.get("strength", 0.0) + strength
                    _cell.aggregate_strength += strength
                    # Update cell phase_vec running mean if new phase data arrives
                    if phase_vec is not None:
                        n = len(_cell.bindings)
                        if _cell.phase_vec is None:
                            _cell.phase_vec = phase_vec.copy()
                        else:
                            _cell.phase_vec = (
                                _cell.phase_vec * ((n - 1) / n) + phase_vec / n
                            )
                            _nrm = np.linalg.norm(_cell.phase_vec)
                            if _nrm > 1e-12:
                                _cell.phase_vec = _cell.phase_vec / _nrm
                    return chi_value  # reinforced in place — no new binding

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
                # GL-CMD-PERSIST-FIX-74: .tolist() on complex128 returns list[complex],
                # which is not JSON-serializable. Explicit re/im pair encoding.
                pv = [[float(c.real), float(c.imag)] for c in cell.phase_vec]
            cells_out[str(chi_idx)] = {
                "bindings": cell.bindings,
                "aggregate_strength": cell.aggregate_strength,
                "phase_vec": pv,
                "last_tick": cell.last_tick,
                "saturated": cell.saturated,
            }
        return {"version": 1, "cells": cells_out}

    def to_npz(self, path: str) -> None:
        """GL-CMD-WAVE-SEMANTICS-85 Part C.1: persist as numpy .npz (compressed).
        Phase vecs stored as float32 re/im arrays; bindings as gzip-compressed JSON.
        Target: <5MB after Part B.3 migration collapses to ~8-25k bindings."""
        import numpy as np, json, gzip
        chi_idxs = sorted(self.cells.keys())
        n = len(chi_idxs)
        agg_str = np.zeros(n, dtype=np.float32)
        last_ticks = np.zeros(n, dtype=np.int64)
        saturated = np.zeros(n, dtype=np.bool_)
        pv_re = np.zeros((n, PHASE_DIMS), dtype=np.float32)
        pv_im = np.zeros((n, PHASE_DIMS), dtype=np.float32)
        pv_valid = np.zeros(n, dtype=np.bool_)
        bindings_all = []
        for i, ci in enumerate(chi_idxs):
            cell = self.cells[ci]
            agg_str[i] = cell.aggregate_strength
            last_ticks[i] = cell.last_tick
            saturated[i] = cell.saturated
            if cell.phase_vec is not None:
                pv_re[i] = cell.phase_vec.real.astype(np.float32)
                pv_im[i] = cell.phase_vec.imag.astype(np.float32)
                pv_valid[i] = True
            bindings_all.append(cell.bindings)
        bindings_bytes = gzip.compress(json.dumps(bindings_all).encode("utf-8"), compresslevel=6)
        bindings_arr = np.frombuffer(bindings_bytes, dtype=np.uint8)
        # Write via file object — numpy.savez_compressed auto-appends .npz when given a
        # path string, which breaks the .tmp atomic-rename pattern. File objects are
        # written as-is with no extension modification.
        with open(path, "wb") as _npz_f:
            np.savez_compressed(
                _npz_f,
                chi_indices=np.array(chi_idxs, dtype=np.int32),
                aggregate_strengths=agg_str,
                last_ticks=last_ticks,
                saturated=saturated,
                phase_vecs_re=pv_re,
                phase_vecs_im=pv_im,
                phase_vecs_valid=pv_valid,
                bindings_gz=bindings_arr,
            )

    def load_from_npz(self, path: str) -> int:
        """Restore WaveAtlas from .npz file. Returns number of cells loaded."""
        import numpy as np, json, gzip
        data = np.load(path, allow_pickle=False)
        chi_idxs = data["chi_indices"].tolist()
        agg_strs = data["aggregate_strengths"].tolist()
        lticks = data["last_ticks"].tolist()
        sats = data["saturated"].tolist()
        pv_re = data["phase_vecs_re"]
        pv_im = data["phase_vecs_im"]
        pv_valid = data["phase_vecs_valid"].tolist()
        bindings_gz = data["bindings_gz"].tobytes()
        bindings_all = json.loads(gzip.decompress(bindings_gz).decode("utf-8"))
        self.cells = {}
        for i, ci in enumerate(chi_idxs):
            cell = Cell()
            cell.aggregate_strength = float(agg_strs[i])
            cell.last_tick = int(lticks[i])
            cell.saturated = bool(sats[i])
            if pv_valid[i]:
                cell.phase_vec = (pv_re[i] + 1j * pv_im[i]).astype(np.complex128)
            cell.bindings = bindings_all[i] if i < len(bindings_all) else []
            self.cells[ci] = cell
        return len(self.cells)

    def collapse_by_key(self) -> dict:
        """GL-CMD-WAVE-SEMANTICS-85 Part B.3: collapse duplicate bindings within
        each cell by (chi, section, motif). Strength = sum; phase_vec preserved.
        Returns {"before": n, "after": m, "cells": k}."""
        before = sum(len(c.bindings) for c in self.cells.values())
        for cell in self.cells.values():
            seen = {}  # (chi, section, motif) -> index in new_bindings
            new_bindings = []
            for b in cell.bindings:
                key = (b.get("chi"), b.get("section"), b.get("motif"))
                if None in key:
                    new_bindings.append(b)
                    continue
                if key in seen:
                    # Reinforce existing: sum strengths
                    existing = new_bindings[seen[key]]
                    existing["strength"] = existing.get("strength", 0.0) + b.get("strength", 0.0)
                else:
                    seen[key] = len(new_bindings)
                    new_bindings.append(dict(b))
            cell.bindings = new_bindings
            cell.aggregate_strength = sum(float(b.get("strength", 0.0)) for b in new_bindings)
        after = sum(len(c.bindings) for c in self.cells.values())
        return {"before": before, "after": after, "cells": len(self.cells)}

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
                # GL-CMD-PERSIST-FIX-74: reconstruct complex128 array from [re, im] pairs
                _pv = cell_data["phase_vec"]
                cell.phase_vec = np.array(
                    [complex(re, im) for re, im in _pv],
                    dtype=np.complex128
                )
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
