#!/usr/bin/env bash
# Retired: never restart the rejected synthetic learning loop or replace state.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$ROOT/tools/run_64d_continuous_hardening.py"
