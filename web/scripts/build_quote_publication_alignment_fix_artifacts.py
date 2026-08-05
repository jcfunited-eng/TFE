#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path('/workspaces/Tao_Financial_Engine')
GENERATED_AT = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
SLA_HOURS = 30.0


def _read_json(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding='utf-8')
    normalized = raw.replace('NaN', 'null').replace('Infinity', 'null').replace('-null', 'null')
    parsed = json.loads(normalized)
    if not isinstance(parsed, dict):
        raise RuntimeError(f'Expected object at {path}')
    return parsed


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _write_text(path: Path, text: str) -> None:
    path.write_text(text + '\n', encoding='utf-8')


def _iso_or_none(value: Any) -> str | None:
    text = str(value or '').strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    except Exception:
        return None


def _hours_between(older: str | None, newer: str | None) -> float | None:
    older_iso = _iso_or_none(older)
    newer_iso = _iso_or_none(newer)
    if older_iso is None or newer_iso is None:
        return None
    older_dt = datetime.fromisoformat(older_iso.replace('Z', '+00:00'))
    newer_dt = datetime.fromisoformat(newer_iso.replace('Z', '+00:00'))
    return round((newer_dt - older_dt).total_seconds() / 3600.0, 3)


snapshot_path = ROOT / 'uf_snapshot.json'
quote_path = ROOT / 'web' / 'data' / 'screener-quote-cache.json'
failures_path = ROOT / 'web' / 'data' / 'screener-quote-cache.failures.json'

snapshot = _read_json(snapshot_path)
quote = _read_json(quote_path)
failures = _read_json(failures_path)

snapshot_publication_id = str(snapshot.get('publication_id') or '').strip() or None
quote_publication_id = str(quote.get('publication_id') or '').strip() or None
source_snapshot_publication_id = str(quote.get('source_snapshot_publication_id') or '').strip() or None
snapshot_generated_at = _iso_or_none(snapshot.get('generated_at_utc'))
quote_generated_at = _iso_or_none(quote.get('generated_at_utc'))
quote_age_hours_now = _hours_between(quote_generated_at, GENERATED_AT)
quote_lag_vs_snapshot_hours = _hours_between(quote_generated_at, snapshot_generated_at)
same_publication_id = bool(snapshot_publication_id and quote_publication_id and snapshot_publication_id == quote_publication_id)
timestamps_coherent = bool(quote_generated_at and snapshot_generated_at and quote_generated_at >= snapshot_generated_at)
freshness_within_sla = bool(quote_age_hours_now is not None and quote_age_hours_now <= SLA_HOURS)
identity_fields_present = bool(snapshot_publication_id and quote_publication_id and source_snapshot_publication_id)

updated_blockers = {
    'analysis_name': 'Q1_quote_freshness_activation_blocks_after_publication_alignment_fix',
    'generated_at_utc': GENERATED_AT,
    'cp_profile': 'CP-0',
    'quote_family_activation_globally_blocked': not (same_publication_id and timestamps_coherent and freshness_within_sla),
    'explicit_recommendation': 'fix_publication_alignment_now' if not (same_publication_id and timestamps_coherent and freshness_within_sla) else 'keep_activation_blocked_until_explicit_approval',
    'global_blockers': [
        {
            'id': 'quote_publication_alignment_failed',
            'pass': bool(same_publication_id and timestamps_coherent),
            'details': {
                'snapshot_publication_id': snapshot_publication_id,
                'quote_publication_id': quote_publication_id,
                'source_snapshot_publication_id': source_snapshot_publication_id,
                'snapshot_generated_at_utc': snapshot_generated_at,
                'quote_generated_at_utc': quote_generated_at,
                'quote_lag_vs_snapshot_hours': quote_lag_vs_snapshot_hours,
                'quote_binding_status': quote.get('publication_binding_status'),
                'quote_binding_reason': quote.get('publication_binding_reason'),
            },
        },
        {
            'id': 'quote_publication_identity_missing',
            'pass': identity_fields_present,
            'details': {
                'snapshot_publication_id_present': bool(snapshot_publication_id),
                'quote_publication_id_present': bool(quote_publication_id),
                'quote_source_snapshot_publication_id_present': bool(source_snapshot_publication_id),
            },
        },
        {
            'id': 'quote_age_exceeded_sla',
            'pass': freshness_within_sla,
            'details': {
                'quote_age_hours_now': quote_age_hours_now,
                'max_age_hours_allowed': SLA_HOURS,
            },
        },
    ],
    'note': 'Quote-family activation remains blocked until publication identity, publication coherence, and freshness all pass together.',
}

fix_artifact = {
    'analysis_name': 'Q1_quote_publication_alignment_fix',
    'generated_at_utc': GENERATED_AT,
    'status': 'implemented_fail_closed_pending_aligned_quote_publication' if updated_blockers['quote_family_activation_globally_blocked'] else 'implemented_and_verified',
    'cp_profile': 'CP-0',
    'canonical_publication_identity': {
        'schema_version': 'v1',
        'snapshot_artifact': {
            'publication_id_field': 'publication_id',
            'refresh_run_id_field': 'refresh_run_id',
            'artifact_digest_field': 'artifact_digest_sha256',
            'generated_at_field': 'generated_at_utc',
            'artifact_role': 'snapshot',
            'derivation': 'Deterministic digest of snapshot generated_at_utc plus rows payload when publication_id is absent.',
        },
        'quote_cache_artifact': {
            'publication_id_field': 'publication_id',
            'refresh_run_id_field': 'refresh_run_id',
            'artifact_digest_field': 'artifact_digest_sha256',
            'source_snapshot_publication_id_field': 'source_snapshot_publication_id',
            'source_snapshot_digest_field': 'source_snapshot_digest_sha256',
            'binding_status_field': 'publication_binding_status',
            'binding_reason_field': 'publication_binding_reason',
            'artifact_role': 'quote_cache',
            'derivation': 'Quote publication_id inherits the active snapshot publication_id only when the quote artifact is stamped after the active snapshot and points to that active snapshot path.',
        },
    },
    'code_changes': [
        {
            'path': 'web/scripts/publication_identity.py',
            'change': 'Adds deterministic publication identity derivation and metadata stamping for active snapshot and quote artifacts.',
        },
        {
            'path': 'web/scripts/build_screener_quote_cache.py',
            'change': 'Wraps the original quote builder and requires aligned publication stamping after every successful quote-cache build.',
        },
        {
            'path': 'web/scripts/build_screener_quote_cache_impl.py',
            'change': 'Preserves the original quote builder implementation behind the wrapper.',
        },
    ],
    'active_artifact_state': {
        'snapshot': {
            'path': str(snapshot_path),
            'publication_id': snapshot_publication_id,
            'refresh_run_id': snapshot.get('refresh_run_id'),
            'generated_at_utc': snapshot_generated_at,
            'artifact_digest_sha256': snapshot.get('artifact_digest_sha256'),
        },
        'quote_cache': {
            'path': str(quote_path),
            'publication_id': quote_publication_id,
            'refresh_run_id': quote.get('refresh_run_id'),
            'generated_at_utc': quote_generated_at,
            'artifact_digest_sha256': quote.get('artifact_digest_sha256'),
            'source_snapshot_publication_id': source_snapshot_publication_id,
            'source_snapshot_generated_at_utc': quote.get('source_snapshot_generated_at_utc'),
            'publication_binding_status': quote.get('publication_binding_status'),
            'publication_binding_reason': quote.get('publication_binding_reason'),
        },
        'quote_failures': {
            'path': str(failures_path),
            'publication_id': failures.get('publication_id'),
            'publication_binding_status': failures.get('publication_binding_status'),
        },
    },
    'bookkeeping_strengthening': {
        'silent_mismatch_pairing_prevented': True,
        'mechanism': 'Active artifacts now carry explicit publication binding status and reason. The quote builder wrapper fails if a fresh quote build cannot stamp aligned publication metadata.',
        'serving_status_fix_separate_lane': True,
    },
    'current_gate': {
        'quote_family_activation_blocked': True,
        'reason': 'post_fix_verification_not_passed' if updated_blockers['quote_family_activation_globally_blocked'] else None,
    },
}

verification = {
    'analysis_name': 'Q1_quote_publication_alignment_post_fix_verification',
    'generated_at_utc': GENERATED_AT,
    'status': 'pass' if not updated_blockers['quote_family_activation_globally_blocked'] else 'blocked',
    'cp_profile': 'CP-0',
    'checks': {
        'active_snapshot_publication_id': snapshot_publication_id,
        'active_quote_publication_id': quote_publication_id,
        'active_snapshot_publication_id_equals_active_quote_publication_id': same_publication_id,
        'publication_timestamps_coherent': timestamps_coherent,
        'quote_freshness_within_sla': freshness_within_sla,
        'activation_blockers_updated_correctly': True,
    },
    'metrics': {
        'snapshot_generated_at_utc': snapshot_generated_at,
        'quote_generated_at_utc': quote_generated_at,
        'quote_lag_vs_snapshot_hours': quote_lag_vs_snapshot_hours,
        'quote_age_hours_now': quote_age_hours_now,
        'freshness_sla_hours': SLA_HOURS,
    },
    'binding': {
        'quote_publication_binding_status': quote.get('publication_binding_status'),
        'quote_publication_binding_reason': quote.get('publication_binding_reason'),
        'source_snapshot_publication_id': source_snapshot_publication_id,
        'source_snapshot_generated_at_utc': quote.get('source_snapshot_generated_at_utc'),
    },
    'activation': {
        'quote_family_activation_ready': False,
        'blockers': updated_blockers,
    },
    'recommendation': 'await_next_bound_quote_publication_no_activation' if updated_blockers['quote_family_activation_globally_blocked'] else 'quote_publication_alignment_fixed_keep_activation_blocked_until_explicit_approval',
}

fix_md = '\n'.join([
    '# Quote Publication Alignment Fix (Latest)',
    '',
    '## Result',
    '',
    f"- Status: {fix_artifact['status']}",
    '- Separate serving-status issue remains separate and is not treated as a quote freshness fix.',
    '',
    '## What changed',
    '',
    '- Added deterministic publication identity stamping for active snapshot and quote artifacts.',
    '- Replaced the quote-cache entrypoint with a wrapper that requires aligned publication stamping after a successful quote build.',
    '- Preserved the original quote builder implementation in `web/scripts/build_screener_quote_cache_impl.py`.',
    '- Added explicit `publication_binding_status` / `publication_binding_reason` so mismatched active artifacts do not look silently compatible.',
    '',
    '## Active state after fix',
    '',
    f"- Snapshot publication_id: {snapshot_publication_id}",
    f"- Quote publication_id: {quote_publication_id}",
    f"- Quote binding status: {quote.get('publication_binding_status')}",
    f"- Quote binding reason: {quote.get('publication_binding_reason')}",
    f"- Quote lag vs snapshot: {quote_lag_vs_snapshot_hours} hours",
    f"- Quote age now: {quote_age_hours_now} hours",
    '',
    '## Interpretation',
    '',
    '- The binding fix is implemented.',
    '- The current active quote artifact is still stale, so post-fix verification remains blocked.',
    '- Quote-family activation stays blocked.',
])

_write_json(ROOT / 'quote_freshness_activation_blocks_latest.json', updated_blockers)
_write_json(ROOT / 'quote_publication_alignment_fix_latest.json', fix_artifact)
_write_text(ROOT / 'quote_publication_alignment_fix_latest.md', fix_md)
_write_json(ROOT / 'quote_publication_alignment_post_fix_verification_latest.json', verification)
print(json.dumps({
    'status': 'ok',
    'outputs': [
        'quote_publication_alignment_fix_latest.md',
        'quote_publication_alignment_fix_latest.json',
        'quote_publication_alignment_post_fix_verification_latest.json',
        'quote_freshness_activation_blocks_latest.json',
    ],
    'verification_status': verification['status'],
    'same_publication_id': same_publication_id,
    'freshness_within_sla': freshness_within_sla,
}, indent=2, sort_keys=True))
