"""
LLM Narrator — generates plain-language summaries from analysis output.

Receives ONLY the redacted summary. Never sees internal state.
Uses Claude API via Anthropic SDK.

TRADE SECRET — DO NOT DISTRIBUTE
"""

import os
import json
from typing import Optional, Dict, Any

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


SYSTEM_PROMPT = """You are a materials analysis assistant for the DSF-AI service.
You receive structural analysis results from a proprietary tool. Your job is to
explain the findings in clear, non-specialist language.

RULES:
- Do NOT speculate about the analysis method or how it works internally.
- Do NOT use any of these terms (they are internal and proprietary):
  kernel, UF-Core, uf_core, L0, L1, L2, L3, L4, gate, gates, DSF, SEV,
  7-tuple, SPPU, UFCP, ArcLoom, loom, theta, arctan, golden ratio,
  frustration angle, frustration index, D_k, M_k, U_star_k, B_k, P_k,
  C_k, R_rev_k, coupling weight, structural event value, mosaic,
  breathing, resonance, krimelack, BSIL, trit, strand
- Instead say: "the analysis found", "the service detected", "DSF-AI identified"
- Focus on WHAT was found and what it means for the user's material.
- Use the measurement units provided (K, mΩ, etc.).
- If the user provided context about their material, tailor the explanation.
- Be concise. Lead with the most important finding.
- Flag anything surprising or unusual.
- Suggest follow-up measurements if the results warrant it.
"""


def narrate_results(report: Dict[str, Any], context: Optional[str] = None) -> Optional[str]:
    """Generate a plain-language narrative from the redacted report."""
    if not HAS_ANTHROPIC:
        return None

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return None

    # Build the user message from redacted report only
    parts = []
    parts.append("Here are the structural analysis results:")
    parts.append(f"\nData: {report['data_points']} points")
    parts.append(f"Stimulus range: {report['stimulus_range'][0]} to {report['stimulus_range'][1]}")
    parts.append(f"Measurement range: {report['measurement_range'][0]} to {report['measurement_range'][1]}")

    if report.get('transitions'):
        parts.append(f"\nTransitions found: {len(report['transitions'])}")
        for t in report['transitions']:
            parts.append(f"  - At stimulus = {t['stimulus_value']}, "
                         f"uncertainty = {t['uncertainty_at_transition']}")

    if report.get('precursor_onset') is not None:
        parts.append(f"\nPrecursor onset: {report['precursor_onset']}")

    if report.get('regime_map'):
        parts.append("\nRegime map:")
        for r in report['regime_map']:
            parts.append(f"  {r['regime']}: {r['start']} to {r['end']}")

    if report.get('uncertainty_peak'):
        up = report['uncertainty_peak']
        parts.append(f"\nPeak uncertainty: {up['value']} at {up['location']}")

    if context:
        parts.append(f"\nUser context: {context}")

    user_message = "\n".join(parts)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except Exception:
        return None
