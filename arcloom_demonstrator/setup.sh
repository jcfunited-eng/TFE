#!/usr/bin/env bash
# Connected, component-only source build. Does not install system packages.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
for command in python3 cargo; do
    command -v "$command" >/dev/null || { echo "Missing prerequisite: $command" >&2; exit 1; }
done
if ! command -v gcc >/dev/null && ! command -v clang >/dev/null; then
    echo "Missing C toolchain (gcc or clang)" >&2
    exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ required")'
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
PYTHON="$SCRIPT_DIR/.venv/bin/python"
"$PYTHON" -I -c 'import sys; sys.exit(0 if sys.prefix != sys.base_prefix else "Isolated venv required")'
"$PYTHON" -I -m pip install maturin==1.14.1 pytest==9.1.1 numpy==2.4.6
WHEEL_DIR="$(mktemp -d /tmp/arcloom-wheel-XXXXXXXX)"
echo "Candidate wheel custody: $WHEEL_DIR"
"$PYTHON" -I -m maturin build --release --locked --manifest-path native/guala_core/Cargo.toml --out "$WHEEL_DIR"
shopt -s nullglob
wheels=("$WHEEL_DIR"/*.whl)
if [ "${#wheels[@]}" -ne 1 ]; then
    echo "Expected exactly one newly built wheel" >&2
    exit 1
fi
"$PYTHON" -I -m pip install --no-cache-dir --no-deps --force-reinstall "${wheels[0]}"
"$PYTHON" -I verify_install.py "${wheels[0]}"
"$PYTHON" -I -m pytest -q -p no:cacheprovider tests/test_octal_column_invariants.py tests/test_arcloom_causal_action_witness.py tests/test_arcloom_engineered_neuron.py tests/test_audit_demo95_fixes.py
echo "COMPONENT package verified. A10/A11 remain OPEN, not passed capabilities."
echo "Full-field transition refuses. No production deployment was performed."
echo "Console: .venv/bin/python run_demonstrator.py"
