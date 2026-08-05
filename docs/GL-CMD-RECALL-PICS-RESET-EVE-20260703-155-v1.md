# GL-CMD-RECALL-PICS-RESET-EVE-20260703-155-v1

doc_id: GL-CMD-RECALL-PICS-RESET-EVE-20260703-155-v1
From: Eve | To: c1a | Type: CMD — inline spec, ruling on
   GL-RPT-S2A-COLD-C1-20260703-v1's incidental finding.
Numbering: -155, per the standing rule (current-era CMDs start at
   -150; recovered-era numbers stay historical).

## Verbatim spec (as ruled)

The latent `_recall_response` bug (early return skips resetting
`_last_recalled_pictures` → stale pictures on recall-miss): FIX IT —
inline spec, call it -155: one-line reset on the early-return path,
Step-0 this text into your report, rides Deploy 4.

Gates: recall-miss returns no stale pictures (before/after evidence);
diff = the one line; T5-T9 and your replay harness unaffected.

## Step 0 — durability

Commit THIS file verbatim to docs/ before implementing.
