"""
Analysis Runner — structural analysis for the DSF-AI service.

Accepts (stimulus, measurement) pairs, runs the analysis pipeline,
and returns a redacted report. Internal state is encrypted via SES
and never leaves this module in plaintext.

TRADE SECRET — DO NOT DISTRIBUTE
"""

import json
import os
import hashlib
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any

from tools.derive_sppu_weights import build_field_series, run_kernel, dsf_to_coupling_profile
from uf_core.layer0 import compute_sev_series
from uf_core.layer1 import segment_gates
from uf_core.layer2 import interpret_gates

# SES/SCE imports for internal state encryption
try:
    from ses_core.envelope import Envelope
    from ses_core.aead_backend import SCESIVBackend
    SES_AVAILABLE = True
except ImportError:
    SES_AVAILABLE = False

# SES root key — in production this comes from AWS Secrets Manager
# For now use a derived key from environment or a static dev key
SES_ROOT_KEY = os.environ.get('DSF_AI_SES_ROOT_KEY', 'dsf-ai-ses-root-key-v1-CHANGE-IN-PROD')


def _encrypt_internal_state(internal_state: Dict, data_hash: str) -> Dict:
    """
    Encrypt all internal computation state into an SES envelope.
    Returns the envelope dict for storage. The plaintext is never
    returned — only the encrypted envelope.
    """
    if not SES_AVAILABLE:
        # Fallback: hash the internal state as proof it existed,
        # but don't store the plaintext
        state_json = json.dumps(internal_state, default=str)
        return {
            'ses_status': 'unavailable',
            'state_hash': hashlib.sha256(state_json.encode()).hexdigest(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

    try:
        plaintext = json.dumps(internal_state, default=str).encode('utf-8')
        # Derive a 256-bit key from root key + data hash
        root_key = hashlib.sha256(SES_ROOT_KEY.encode()).digest()
        derived_key = hashlib.sha256(root_key + data_hash.encode()).digest()
        backend = SCESIVBackend()
        nonce = os.urandom(12)

        # Associated data binds this envelope to this specific analysis
        ad = json.dumps({
            'service': 'dsf-ai',
            'purpose': 'analysis-internal-state',
            'data_hash': data_hash,
        }).encode('utf-8')

        # SCE-SIV: structural engine generates keystream from mosaic
        # extraction — the full SCE pipeline, not legacy AES-GCM
        ciphertext = backend.encrypt(
            key=derived_key,
            nonce=nonce,
            plaintext=plaintext,
            associated_data=ad,
        )

        envelope = Envelope(
            tenant_id='dsf-ai',
            environment='production',
            region='us-east-1',
            purpose='analysis-internal-state',
            version='1.0',
            algorithm='sce-siv-v1',
            created_at=datetime.now(timezone.utc).isoformat(),
            nonce=Envelope._b64encode(nonce),
            key_id=f'dsf-ai:analysis:{data_hash[:16]}',
            ciphertext=Envelope._b64encode(ciphertext),
            summary={'data_hash': data_hash, 'state_size': len(plaintext)},
        )

        return {
            'ses_status': 'encrypted',
            'envelope': envelope.to_dict(),
        }
    except Exception as e:
        # Encryption failed — hash only, never store plaintext
        state_json = json.dumps(internal_state, default=str)
        return {
            'ses_status': f'error: {str(e)}',
            'state_hash': hashlib.sha256(state_json.encode()).hexdigest(),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }


def run_analysis(pairs: List[Tuple[float, float]]) -> Dict[str, Any]:
    """
    Run the full analysis pipeline and return a redacted summary.

    The customer gets: transitions, precursors, regimes, uncertainty.
    Internal computation state never leaves this function.
    """
    # T2: Verify code integrity before every analysis
    from dsf_ai_service.integrity import verify_integrity, is_compromised
    if is_compromised():
        return {'status': 'error', 'error': 'Service integrity check failed. Contact support.'}
    integrity = verify_integrity()
    if not integrity['intact']:
        return {'status': 'error', 'error': 'Service integrity check failed. Contact support.'}
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
                'intensity': round(abs(dsf_list[i].P_k) + abs(d_curr - d_prev), 4),
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

    # ── Encrypt internal state via SES ──
    # Capture ALL internal computation state for audit
    data_hash = hashlib.sha256(
        json.dumps(pairs, default=str).encode()
    ).hexdigest()

    internal_state = {
        'sev_count': len(sev_series),
        'sev_sample': [
            {'F': s.F_norm, 'dF': s.dF, 'sigma': s.sigma, 'kappa': s.kappa}
            for s in sev_series[:5]
        ],
        'gate_count': len(gates),
        'gate_boundaries': [
            {'start': g.start_idx, 'end': g.end_idx} for g in gates
        ],
        'dsf_tuples': [
            {'D': d.D_k, 'M': d.M_k, 'U': d.U_star_k, 'B': d.B_k,
             'P': d.P_k, 'C': d.C_k, 'R': d.R_rev_k}
            for d in dsf_list
        ],
        'interp_regimes': [
            {'regime': ip.regime, 'U': ip.U_k} for ip in interps
        ],
    }

    # Encrypt — plaintext is destroyed after this
    ses_envelope = _encrypt_internal_state(internal_state, data_hash)
    del internal_state  # Explicit destruction

    # ── Build output report (redacted — no internal state) ──
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
        'ses_protected': ses_envelope.get('ses_status', 'unknown'),
    }
