#!/usr/bin/env bash
# ==============================================================================
# tools/bootstrap_demonstrator.sh
# 
# Clean-Room Bootstrap & Automated Hardware Verification Script for DSF-AI
# Target: Windows 11 Pro / WSL2 Ubuntu on New Demonstrator Workstation
# Standard: Strict Physical Determinism, Zero Cloud Reliance, 100% Local Run
# ==============================================================================

set -euo pipefail

echo "======================================================================"
echo "    DSF-AI ARCLOOM DEMONSTRATOR: CLEAN-ROOM AUTOMATED BOOTSTRAP"
echo "======================================================================"
echo "[*] Initializing environment audit..."

# 1. Verify Platform & Architecture
ARCH="$(uname -m)"
OS="$(uname -s)"
echo "[*] Detected Host: $OS on $ARCH"

if [ "$OS" != "Linux" ]; then
    echo "[!] Error: This bootstrap script must be run inside Linux or WSL2."
    exit 1
fi

# 2. Update and Install Core Build Dependencies
echo "[*] Ensuring essential build tools are installed..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y build-essential python3 python3-pip python3-venv \
        libssl-dev pkg-config git curl jq htop
fi

# 3. Ensure Rust Toolchain Is Present
if ! command -v cargo >/dev/null 2>&1; then
    echo "[*] Installing Rust toolchain (stable, 64-bit SIMD)..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    echo "[*] Rust toolchain verified: $(cargo --version)"
fi

# 4. Create Pristine Python 3 Virtual Environment
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating pristine Python virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "[*] Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 5. Install Core Python Dependencies (Zero ML, Pure Numerics & Maturin)
echo "[*] Installing core compilation & test requirements..."
pip install --upgrade pip
pip install maturin pytest numpy boto3 requests

# 6. Compile Native Rust 8-Column Substrate Core (Release Performance)
echo "[*] Compiling guala_core in release mode (8-Column Balanced Octet)..."
maturin develop --release --manifest-path native/guala_core/Cargo.toml

# 7. Execute Comparative Physical Invariant Benchmarks
echo "[*] Running 5-Suite Physical Benchmark & Verification..."
python3 tools/benchmark_modular_column_substrate.py

# 8. Execute Multi-Phase Test Suite
echo "[*] Running Multi-Phase Deterministic Test Suite..."
PYTHONPATH=. pytest -q \
    tests/test_phase2_ternary_multimodal_organism.py \
    tests/test_phase3_homeostatic_exhaust_loop.py \
    tests/test_phase4_offline_dream_consolidation.py \
    tests/test_phase5_closed_loop_organism.py \
    tests/test_phase5_modular_column_substrate.py \
    tests/test_phase5_modular_cortical_columns.py

echo "======================================================================"
echo "    CLEAN-ROOM BOOTSTRAP COMPLETE: 100% INVARIANTS VERIFIED"
echo "    Workstation is fully prepared for air-gapped benchtop demonstration."
echo "======================================================================"
