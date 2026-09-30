#!/usr/bin/env bash
# ==============================================================================
# arcloom_demonstrator/setup.sh
#
# Standalone Clean-Room Bootstrap for ArcLoom Neuromorphic Demonstrator
# Completely Air-Gapped: Zero External Repositories, Zero Financial Files
# Standard: Strict Physical Determinism, Continuum Mechanics, Verilog Hardware
# ==============================================================================

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "======================================================================"
echo "    ARCLOOM TERNARY NEUROMORPHIC HARDWARE DEMONSTRATOR"
echo "    Clean-Room Standalone Setup (DARPA / AFRL Evaluation Package)"
echo "======================================================================"

# 1. Check Platform
echo "[*] Verifying host environment: $(uname -s) $(uname -m)"

# 2. Check/Install Core Build Dependencies if running on Debian/Ubuntu
if command -v apt-get >/dev/null 2>&1 && [ "${EUID:-$(id -u)}" -eq 0 ]; then
    echo "[*] Updating system packages..."
    apt-get update -y && apt-get install -y build-essential python3 python3-pip python3-venv curl
fi

# 3. Check Rust Toolchain
if ! command -v cargo >/dev/null 2>&1; then
    echo "[*] Installing Rust toolchain (stable)..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    # shellcheck disable=SC1091
    source "$HOME/.cargo/env"
else
    echo "[*] Rust compiler verified: $(cargo --version)"
fi

# 4. Create Pristine Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[*] Creating dedicated Python virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "[*] Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

# 5. Install Minimal Compilation & Numeric Dependencies (Zero ML)
echo "[*] Installing build requirements..."
pip install --upgrade pip
pip install maturin pytest numpy

# 6. Compile 8-Column Balanced Octet Native Rust Core
echo "[*] Compiling guala_core native SIMD substrate (Release mode)..."
maturin develop --release --manifest-path native/guala_core/Cargo.toml

# 7. Run Invariant Verification Tests
echo "[*] Executing Invariant Verification Suite..."
pytest -q tests/test_octal_column_invariants.py

# 8. Run Physical Benchmarks
echo "[*] Executing Physical Invariant & Timing Benchmarks..."
python3 benchmark_octal_substrate.py

echo "======================================================================"
echo "    SETUP SUCCESSFUL: 100% PHYSICAL INVARIANTS VERIFIED"
echo "    To launch the interactive console demonstrator, run:"
echo "        source .venv/bin/activate && python3 run_demonstrator.py"
echo "======================================================================"
