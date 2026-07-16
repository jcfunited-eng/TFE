# GL-SHIP: Change 1 (disk-resident store + one boot method) — P6 ship record

**Date:** 2026-07-16. **Spec:** GL-SPC-SUBSTRATE-TRUE-SINGLE-STACK-20260716-v3.tex Changes 1 (Joe-approved). **Merged:** 7663da6 on guala-live. **Authorization:** Joe 2026-07-16 ("implement the plan as you see fit"); adversarial review + fix round + re-verification (SAFE TO INTEGRATE) + hotfix-preserving merge verification.

## What

The memory model and boot method from the spec: boot is one streaming WAL index-scan (locator + per-window metadata; content never resident; hash+digest verification kept; named loud halts incl. readiness 503), read surfaces are fetch-on-demand through a byte-budgeted LRU (256MB accounted at measured 5x resident multiplier), compaction rebuilds locator+metadata with generation-stamped publications, torn WAL tails self-heal by truncation (loud event), the certified composer is cached (invalidated on new ordered windows), gist-compaction is designed-in per the forgetting principle (P3), and the operator restore command exists (staging + verify + atomic swap; displaced state always preserved; heartbeat + mtime guards). GUALA_FORCE_FRESH and adopt-state-without-identity boot branches deleted; WAL segments count as state evidence; EXPECTED_IDENTITY updated to the live genesis identity.

## Why

P1 (RAM is for thinking, disk is for remembering): the resident window store was the substrate's terminal memory-growth path (2.8GB and climbing pre-wipe; OOM cascade on 2026-07-16 00:30). Boot-flatness proof: 0.00% RSS delta between 1x and 10x life volume. The restore-path gap (no safe operator restore) and the torn-tail boot brick (reproduced) were both standing existential risks.

## Blast radius

window_manager (read side; WAL format unchanged), engine load_full_state/boot tree, app readiness surface, composer construction, tools/restore_from_s3.py (new). Write path, emission, senses untouched by this change.

## Rollback

Task-def revert. The WAL format and flat stores are unchanged — the previous image reads the same state. Readiness-503 behavior only exists in the new image.

## Verification plan (post-deploy)

Boot restores full state via index scan (log shows scan, no full materialization); RSS at boot and steady-state well under prior baseline; recall/converse behave normally (fetch-on-demand); saves + atomic generations clean through two cycles; sealed turnover proof (first scripted deploy with the seal race fixed); no 137s.
