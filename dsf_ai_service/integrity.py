"""
T2 Integrity Check — Code Tampering Detection

Computes SHA-256 hashes of all critical source files at startup.
On each analysis request, verifies hashes haven't changed.
If tampered: refuses to run, logs the violation.

TRADE SECRET — DO NOT DISTRIBUTE
"""

import hashlib
import os
import json
from datetime import datetime, timezone
from typing import Dict, Optional

# Files that constitute the trade secret implementation
# If ANY of these change after startup, the system is compromised
CRITICAL_FILES = [
    'uf_core/layer0.py',
    'uf_core/layer1.py',
    'uf_core/layer2.py',
    'uf_core/layer3.py',
    'uf_core/layer4.py',
    'uf_core/config.py',
    'ses_core/aead_backend.py',
    'ses_core/envelope.py',
    'ses_core/key_derivation.py',
    'tools/derive_sppu_weights.py',
    'dsf_ai_service/kernel_runner.py',
    'dsf_ai_service/cluster_screener.py',
]

# Set at startup, checked on every request
_startup_hashes: Optional[Dict[str, str]] = None
_integrity_status: str = 'not_initialized'
_tamper_log: list = []


def _hash_file(path: str) -> str:
    """SHA-256 hash of a file's contents."""
    h = hashlib.sha256()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return 'FILE_MISSING'
    except Exception as e:
        return f'ERROR:{str(e)}'


def _find_project_root() -> str:
    """Find the project root directory."""
    # Try common locations
    for candidate in ['/app', '/workspaces/Tao_Financial_Engine', os.getcwd()]:
        if os.path.exists(os.path.join(candidate, 'uf_core')):
            return candidate
    return os.getcwd()


def initialize_integrity():
    """Call once at startup. Records hashes of all critical files."""
    global _startup_hashes, _integrity_status

    root = _find_project_root()
    hashes = {}

    for rel_path in CRITICAL_FILES:
        full_path = os.path.join(root, rel_path)
        hashes[rel_path] = _hash_file(full_path)

    _startup_hashes = hashes
    _integrity_status = 'initialized'

    # Count missing files (acceptable if running in Lambda without full repo)
    missing = sum(1 for h in hashes.values() if h == 'FILE_MISSING')
    present = len(hashes) - missing

    return {
        'status': 'initialized',
        'files_checked': len(hashes),
        'files_present': present,
        'files_missing': missing,
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }


def verify_integrity() -> Dict:
    """
    Verify all critical files match their startup hashes.
    Returns: {intact: bool, violations: [...]}

    Call this before every analysis. If intact is False,
    refuse to run — the code has been tampered with.
    """
    global _integrity_status

    if _startup_hashes is None:
        # Auto-initialize on first call
        initialize_integrity()

    root = _find_project_root()
    violations = []

    for rel_path, expected_hash in _startup_hashes.items():
        if expected_hash == 'FILE_MISSING':
            continue  # Can't check files that weren't there at startup

        full_path = os.path.join(root, rel_path)
        current_hash = _hash_file(full_path)

        if current_hash != expected_hash:
            violation = {
                'file': rel_path,
                'expected': expected_hash[:16] + '...',
                'actual': current_hash[:16] + '...',
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
            violations.append(violation)
            _tamper_log.append(violation)

    if violations:
        _integrity_status = 'COMPROMISED'
        return {
            'intact': False,
            'status': 'COMPROMISED',
            'violations': violations,
            'action': 'REFUSING_ALL_OPERATIONS',
        }

    _integrity_status = 'verified'
    return {
        'intact': True,
        'status': 'verified',
        'files_checked': len(_startup_hashes),
    }


def get_integrity_status() -> str:
    """Get current integrity status."""
    return _integrity_status


def is_compromised() -> bool:
    """Quick check — has tampering been detected?"""
    return _integrity_status == 'COMPROMISED'
