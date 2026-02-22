"""
uf_core
-------

Unified Framework (UF) kernel package for the Tao Financial Engine.

This package will contain:
- L0–L4 kernel implementations (UF-Spec v1.4.0)
- Schema, memory, tapestry, and SES modules
- Validation utilities

WARNING:
All kernel behavior implemented here MUST remain aligned with the
Overleaf UF-Spec v1.4.0 (L0–L4, Section 11, Section 13, Section 23).
"""

from . import config

__all__ = ["config"]
