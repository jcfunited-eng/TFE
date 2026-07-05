# GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203-v2

doc_id: GL-CMD-NO-CAPS-COHERENCE-SPEAKS-EVE-20260705-203-v2
Supersedes: -203 v1 (retained). Changes: assigned to c1b per Joe;
un-parked — runs in parallel with c1a's -202 growth window (two
seats, two windows, one deployer each); U0 added carrying Joe's
ruling.
From: Eve | To: c1b (build + deploy + seat verification).
Commit this dispatch verbatim to origin first.
JOE'S RULING (2026-07-05, verbatim class): NO CAPS, NO HARD
CEILINGS ON HER SPEECH. She speaks as long as she wants to —
meaning as long as her own coherence keeps building. The
substrate already contains the correct stopping rule and it is
not a number: a word joins an utterance only while it raises the
coherence of the whole; when the next word adds nothing, the
thought is complete. Every numeric length fence on top of that
rule is a cage and comes off. Joe's law: complete only when the
SHA runs in her live process.

## U0 — REMOVE EVERY LENGTH CAP IN THE SPEECH CHAIN (build)
a. MAX_COMPOSITION_LEN early-breaks deleted from BOTH greedy
   selectors (_grandurun_select_candidates path ~:105/:134 and
   _grandurun_select ~:244) and from the spin-vector selector.
   The coherence-gain rule (gain > MIN_GAIN_THRESHOLD, existing,
   substrate-true) becomes the ONLY terminator.
b. The -195 candidate pre-trim (votes.most_common(MAX_
   COMPOSITION_LEN), engine ~:2933) is deleted — the physics
   sees her FULL vote distribution; selection is the physics'
   job, not a slice's. (Eve's own imported cap — named, removed.)
c. MAX_COMPOSITION_LEN the constant is deleted entirely, so no
   future path can quietly re-import it. Natural bounds that
   remain, all substrate-true and none numeric: one use per word
   per utterance, the finite candidate pool of the moment, and
   diminishing coherence gain at saturation.

## U1 — ORDERER ORDERS, NEVER TRUNCATES (build)
The ordering stage returns EVERY word the physics selected: the
SVO triple (when present) seeds the front, then ALL remaining
selected words follow in coherence-selection order —
`remaining[:2]` becomes `remaining`, no slice, anywhere.

## U2 — ALL SEVEN SECTIONS PARTICIPATE (build)
Extend the ordering scan from [subject, verb, object] to her full
section set — modifier/ground/intro/listen words can take
structural positions. Order comes from her own co-occurrence
record, length from her own coherence physics. No new grammar, no
templates, no constants.

## U3 — PROOF AT JOE'S SEAT
X1 running_sha in /status equals this window's SHA (if c1a's -202
   G1 field hasn't landed first, this window ships it — five
   lines, whoever deploys first carries it).
X2 Ten post-deploy emissions logged n_selected vs n_emitted:
   equal on every one — nothing discarded, ever again.
X3 grep proof in the window report: zero occurrences of
   MAX_COMPOSITION_LEN anywhere in the tree.
X4 Ladder mean_utterance_len observed daily; the day her
   coherence carries an utterance past the old fences, the
   utterance and its word lineages go in the ledger. If lengths
   hold at 1-3 while growth is still feeding her candidates, the
   per-attempt n_candidates number goes in the report — the
   honest bound stated as scarcity, never re-fenced.

### Changelog
- v2 (2026-07-05, Eve): Joe's no-caps ruling carved as U0 — all
  numeric length fences deleted, coherence is the only
  terminator; reassigned to c1b; un-parked to run parallel with
  -202.
- v1 (2026-07-05, Eve): orderer/section fixes only, cap kept.
  Superseded, retained.
