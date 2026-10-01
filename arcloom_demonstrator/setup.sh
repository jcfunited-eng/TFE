#!/usr/bin/env bash
# ==============================================================================
# arcloom_demonstrator/setup.sh
#
# Standalone Bootstrap for ArcLoom Neuromorphic Demonstrator
# Portable Evaluation Package: Zero Financial Files, Standalone Package
# Prerequisites: gcc/clang (C toolchain), Rust/Cargo (>=1.75.0), Python 3.10+
# ==============================================================================

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "======================================================================"
echo "    ARCLOOM TERNARY NEUROMORPHIC HARDWARE DEMONSTRATOR"
echo "    Standalone Setup & Verification (DARPA / AFRL Evaluation Package)"
echo "======================================================================"

# 1. Check Platform
echo "[*] Verifying host environment: $(uname -s) $(uname -m)"

# 2. Verify System Build Prerequisites (Non-mutating check)
echo "[*] Checking system build prerequisites..."
for cmd in gcc python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "[ERROR] Required build prerequisite '$cmd' not found on PATH." >&2
        echo "Please install build prerequisites (build-essential, python3, python3-venv, python3-pip) prior to running setup." >&2
        exit 1
    fi
done

# 3. Verify Rust Toolchain (Non-mutating check)
if ! command -v cargo >/dev/null 2>&1; then
    echo "[ERROR] Cargo/Rust toolchain not found on PATH." >&2
    echo "Please install Rust (>=1.75.0) via your system package manager or rustup before running setup." >&2
    exit 1
fi
echo "[*] Rust compiler verified: $(cargo --version)"

# 4. Create Pristine Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[*] Creating dedicated Python virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "[*] Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

# 5. Install Pinned Build & Test Dependencies (Locked versions, Zero ML)
echo "[*] Installing pinned build and test dependencies (maturin==1.14.1, pytest==9.1.1, numpy==2.4.6)..."
pip install --quiet maturin==1.14.1 pytest==9.1.1 numpy==2.4.6

# 6. Compile guala_core Native Substrate (Release mode, Locked Build)
echo "[*] Compiling guala_core native substrate wheel (--release --locked)..."
maturin build --release --manifest-path native/guala_core/Cargo.toml --locked --out target/wheels
pip install --force-reinstall --quiet target/wheels/*.whl

# Ensure flat extension module layout for isolated subprocess dynamic linking
SP_DIR="$(python3 -c 'import site; print(site.getsitepackages()[0])')"
if [ -d "$SP_DIR/guala_core" ]; then
    cp "$SP_DIR"/guala_core/guala_core.*.so "$SP_DIR"/
    rm -rf "$SP_DIR/guala_core"
fi

# 7. Assert Module Actually Loaded from Isolated Package Environment & Identify Hash
echo "[*] Verifying isolated environment module custody and exported capabilities..."
python3 -c "
import sys, hashlib
import guala_core

mod_file = getattr(guala_core, '__file__', None)
assert mod_file is not None, 'guala_core __file__ is None'
print(f'[*] Loaded module path: {mod_file}')

assert hasattr(guala_core, 'ArcLoomNeuron'), 'guala_core missing ArcLoomNeuron export'
assert hasattr(guala_core, 'ModularSubstrate64D'), 'guala_core missing ModularSubstrate64D export'

with open(mod_file, 'rb') as f:
    digest = hashlib.sha256(f.read()).hexdigest()
print(f'[*] Loaded module SHA-256: {digest}')
print(f'[*] Confirmed ArcLoomNeuron and ModularSubstrate64D symbols present in loaded binary.')
"

# 8. Run Invariant Verification Tests
echo "[*] Executing Demonstrator Invariant Verification Suite..."
python3 -m pytest -q tests/test_octal_column_invariants.py tests/test_arcloom_causal_action_witness.py tests/test_arcloom_engineered_neuron.py

echo ""
echo "======================================================================"
echo "    ARCLOOM COMPONENT DEMONSTRATOR READY (COMPONENT CONSOLE FUNCTIONING;"
echo "    OPEN A10/A11 INTEGRATION REMAINS FORMAL REFUSAL GATE)"
echo "    Run: python3 run_demonstrator.py"
echo "    Run: python3 benchmark_octal_substrate.py"
echo "======================================================================"
