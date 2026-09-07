"""Fail-closed marker for the retired pre-P-005 shell.

The exact 20,248-line source exists only at immutable commit
49d9fdd60c539ef02809a35991686faca92e1720, SHA-256
f904f89178076e02901740ee3133e254d3e06459e114b7ed631b9968581ba1ea.
Historical inspection must explicitly name that commit.
"""

# No environment flag or import path can reactivate this retired application.
raise RuntimeError("retired Guala shell quarantined; use lean_production_app")
