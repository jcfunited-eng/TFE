# Retired Guala production shell archive

The pre-P-005 Python application is retired, is not production authority, and
must not be imported or executed by development tooling.

- Historical source commit: `49d9fdd60c539ef02809a35991686faca92e1720`
- Historical path: `dsf_ai_service/native_production_app.py`
- Exact source SHA-256: `f904f89178076e02901740ee3133e254d3e06459e114b7ed631b9968581ba1ea`
- Exact historical size: 20,248 lines / 837,266 bytes
- Replacement authority: `dsf_ai_service/lean_production_app.py`

The active path contains only a fail-closed tombstone. Environment variables
cannot reactivate the retired application. Historical review must explicitly
name the immutable commit, for example with a read-only `git show` of the path
above. Recovery into an executable worktree requires a new, explicit Joseph
authorization and must never overwrite the lean application or production
entrypoint.
