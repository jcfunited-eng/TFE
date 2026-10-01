#!/usr/bin/env bash
# ==============================================================================
# arcloom_demonstrator/setup.sh
#
# Standalone Bootstrap for ArcLoom Neuromorphic Demonstrator
# Portable Evaluation Package: Zero Financial Files, Standalone Package
# Platform: Linux x86_64 POSIX terminal (termios/tty)
# Dependencies: Standard C Toolchain, Rust/Cargo 1.75+, Python 3.10+, PyO3
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
if [ "$(uname -s)" != "Linux" ]; then
    echo "[!] Warning: ArcLoom demonstrator console is designed for Linux POSIX termios."
fi

# 2. Check/Install Core Build Dependencies if running on Debian/Ubuntu with network access
if command -v apt-get >/dev/null 2>&1 && [ "${EUID:-$(id -u)}" -eq 0 ]; then
    echo "[*] Ensuring system build packages (build-essential, python3, curl)..."
    apt-get update -y && apt-get install -y build-essential python3 python3-pip python3-venv curl
fi

# 3. Check Rust Toolchain
if ! command -v cargo >/dev/null 2>&1; then
    echo "[*] Cargo not found. Bootstrapping Rust toolchain (stable)..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    # shellcheck disable=SC1091
    source "$HOME/.cargo/env"
else
    echo "[*] Rust compiler verified: $(cargo --version)"
fi

# 4. Create Dedicated Python Virtual Environment
if [ ! -d ".venv" ]; then
    echo "[*] Creating dedicated Python virtual environment (.venv)..."
    python3 -m venv .venv
fi

echo "[*] Activating virtual environment..."
# shellcheck disable=SC1091
source .venv/bin/activate

# 5. Install Minimal Compilation & Numeric Dependencies (Zero ML)
echo "[*] Installing build requirements (maturin, pytest, numpy)..."
pip install --upgrade pip
pip install maturin pytest numpy

# 6. Compile guala_core Native Rust Core (Release mode)
echo "[*] Compiling guala_core native SIMD substrate (Release mode)..."
maturin develop --release --manifest-path native/guala_core/Cargo.toml

# 7. Run Invariant Verification Tests
echo "[*] Executing Demonstrator Invariant Verification Suite..."
python3 -m pytest -q tests/test_octal_column_invariants.py tests/test_arcloom_causal_action_witness.py tests/test_arcloom_engineered_neuron.py

echo ""
echo "======================================================================"
echo "    ARCLOOM DEMONSTRATOR READY FOR EVALUATION"
echo "    Run: python3 run_demonstrator.py"
echo "    Run: python3 benchmark_octal_substrate.py"
echo "======================================================================"
