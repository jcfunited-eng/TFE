"""
UF-Spec v1.4.0 — Section 13 Validation Utilities
================================================

Module: noise_model.py
Purpose:
    Provide mathematically clean and deterministic noise-generation
    utilities for UF Section 13 validation (Noise Robustness).

This module DOES NOT modify or inject noise into UF data structures.
It only produces noise vectors. Integration happens in val_noise.py.
"""

import numpy as np


# ----------------------------------------------------------------------------
# Utility: seeded RNG
# ----------------------------------------------------------------------------

def _rng(seed: int = None):
    """
    Return a NumPy random Generator instance.
    If seed is None, an unpredictable generator is used.
    """
    if seed is None:
        return np.random.default_rng()
    return np.random.default_rng(seed)


# ----------------------------------------------------------------------------
# 1) Gaussian additive noise
# ----------------------------------------------------------------------------

def gaussian_noise(length: int, sigma: float, seed: int = None) -> np.ndarray:
    """
    Generate Gaussian additive noise:
        ε_t ~ N(0, sigma^2)

    Args:
        length : number of samples
        sigma  : standard deviation of noise
        seed   : optional seed for reproducibility

    Returns:
        np.ndarray of shape (length,)
    """
    gen = _rng(seed)
    return gen.normal(loc=0.0, scale=sigma, size=length)


# ----------------------------------------------------------------------------
# 2) Multiplicative noise (percentage noise)
# ----------------------------------------------------------------------------

def multiplicative_noise(length: int, sigma: float, seed: int = None) -> np.ndarray:
    """
    Generate multiplicative noise:
        F_t' = F_t * (1 + ε_t)

    where ε_t ~ N(0, sigma^2)

    Args:
        length : number of samples
        sigma  : standard deviation of multiplicative factor
        seed   : optional seed

    Returns:
        np.ndarray of multiplicative noise factors (1 + ε_t)
    """
    gen = _rng(seed)
    eps = gen.normal(loc=0.0, scale=sigma, size=length)
    return 1.0 + eps


# ----------------------------------------------------------------------------
# 3) Uniform additive noise (optional stress test)
# ----------------------------------------------------------------------------

def uniform_noise(length: int, magnitude: float, seed: int = None) -> np.ndarray:
    """
    Generate uniform additive noise in range [-magnitude, +magnitude].

    Args:
        length    : number of samples
        magnitude : half-width of uniform range
        seed      : optional seed

    Returns:
        np.ndarray of shape (length,)
    """
    gen = _rng(seed)
    return gen.uniform(low=-magnitude, high=magnitude, size=length)


# ----------------------------------------------------------------------------
# 4) Zero-noise convenience function
# ----------------------------------------------------------------------------

def zero_noise(length: int) -> np.ndarray:
    """Return a zero-noise vector."""
    return np.zeros(length, dtype=float)
