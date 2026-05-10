"""
Analysis Runner — structural analysis for the DSF-AI service.

Accepts (stimulus, measurement) pairs, runs the analysis pipeline,
and returns a redacted report. Internal state never leaves this module.

TRADE SECRET — DO NOT DISTRIBUTE
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any

from tools.derive_sppu_weights import build_field_series, run_kernel, dsf_to_coupling_profile
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates


def run_analysis(pairs: List[Tuple[float, float]]) -> Dict[str, Any]:
    """
    Run the full analysis pipeline and return a redacted summary.

    The customer gets: transitions, precursors, regimes, uncertainty.
    Internal computation state never leaves this function.
    """
    # Build field series
    series = build_field_series(pairs, name='measurement')

    # Run full kernel
    kernel_out = run_kernel(series)
    dsf_list = kernel_out['dsf']
    n_gates = kernel_out['n_gates']

    # Coupling profile (safe to expose — derived values only)
    profile = dsf_to_coupling_profile(dsf_list)

    # Run individual layers for regime analysis (internals stay here)
    df = pd.DataFrame({'measurement': series})
    sev_series = compute_sev_series(df, field_col='measurement')
    gates = segment_gates(sev_series)
    interps = interpret_gates(sev_series, gates)

    # Map indices back to stimulus values
    stim_values = sorted(set(p[0] for p in pairs))
    stim_min = min(stim_values)
    stim_max = max(stim_values)
    n_points = len(sev_series)

    def idx_to_stimulus(idx):
        if n_points <= 1:
            return stim_min
        return stim_min + idx / (n_points - 1) * (stim_max - stim_min)

    # ── Build regime map ──
    regime_spans = []
    current_regime = None
    span_start_stim = None
    for i, g in enumerate(gates):
        t_start = idx_to_stimulus(g.start_idx)
        regime = interps[i].regime if i < len(interps) else "UNKNOWN"
        if regime != current_regime:
            if current_regime is not None:
                regime_spans.append({
                    'regime': current_regime,
                    'start': round(span_start_stim, 4),
                    'end': round(t_start, 4),
                })
            current_regime = regime
            span_start_stim = t_start
    if current_regime is not None:
        regime_spans.append({
            'regime': current_regime,
            'start': round(span_start_stim, 4),
            'end': round(stim_max, 4),
        })

    # ── Find transitions ──
    transitions = []
    for i in range(1, len(dsf_list)):
        d_prev = dsf_list[i - 1].D_k
        d_curr = dsf_list[i].D_k
        if d_prev * d_curr < 0 and i < len(gates):
            t_mid = idx_to_stimulus(
                (gates[i].start_idx + gates[i].end_idx) / 2
            )
            transitions.append({
                'stimulus_value': round(t_mid, 4),
                'direction_change': f"{'+' if d_prev > 0 else '-'} → {'+' if d_curr > 0 else '-'}",
                'uncertainty': round(dsf_list[i].U_star_k, 4),
                'severity': round(abs(dsf_list[i].P_k) + abs(d_curr - d_prev), 4),
            })

    # ── Find precursor onset ──
    # Baseline sigma is the median of the first 20% of points
    n_baseline = max(5, len(sev_series) // 5)
    baseline_sigmas = [sev_series[j].sigma for j in range(min(n_baseline, len(sev_series)))]
    baseline_sigma = sorted(baseline_sigmas)[len(baseline_sigmas) // 2] if baseline_sigmas else 0

    precursor_onset = None
    threshold = max(baseline_sigma * 10, 0.01)
    # Scan from both ends to find the first elevated sigma
    for j in range(len(sev_series)):
        if sev_series[j].sigma > threshold:
            precursor_onset = round(idx_to_stimulus(j), 4)
            break

    # ── Uncertainty profile ──
    max_u = 0
    max_u_location = None
    for i, dsf in enumerate(dsf_list):
        if dsf.U_star_k > max_u and i < len(gates):
            max_u = dsf.U_star_k
            t_mid = idx_to_stimulus(
                (gates[i].start_idx + gates[i].end_idx) / 2
            )
            max_u_location = round(t_mid, 4)
    max_u = round(max_u, 4)

    # ── Build output report ──
    return {
        'status': 'ok',
        'data_points': len(pairs),
        'stimulus_range': [round(stim_min, 4), round(stim_max, 4)],
        'measurement_range': [round(float(series.min()), 6), round(float(series.max()), 6)],
        'structural_segments': n_gates,
        'transitions': transitions,
        'precursor_onset': precursor_onset,
        'regime_map': regime_spans,
        'uncertainty_peak': {
            'value': max_u,
            'location': max_u_location,
        },
        'signal_quality': {
            'strength': round(profile['coupling_strength'], 4),
            'stability': round(1.0 - profile['reversal_rate'], 4),
            'richness': round(profile['complexity'], 4),
        },
    }
