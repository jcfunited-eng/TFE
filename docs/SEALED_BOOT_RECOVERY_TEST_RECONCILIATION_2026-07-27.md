# Sealed boot recovery test reconciliation — 2026-07-27

`dsf_ai_service/substrate/test_no_silent_s3_restore.py` previously required
`_gl_init` to call `_recover_from_local_generations` after a load failure.
That requirement is obsolete: `_recover_from_local_generations` is an
unauthenticated local fallback and now intentionally raises.

The complete test file was replaced. It now proves that `_gl_init` calls
neither the unauthenticated local fallback nor mutable flat S3 restore. The
existing guards still prove that any remaining S3 restore reference is
human-only and force-gated.

Production boot remains the authenticated path: immutable deployment baseline,
HMAC-authenticated live recovery overlay, exact load, and loud failure if the
engine state is invalid. No production code was changed.
