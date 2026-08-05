# GL-CMD-COGNITION-LEARN-AUDIT-EVE-20260628-33

doc_id: GL-CMD-COGNITION-LEARN-AUDIT-EVE-20260628-33
Type: Command brief (c1 dispatch) — URGENT, substrate truth
Author: Eve (Opus 4.7, web)
Date: 2026-06-28
Phase: Substrate-truth emergency, sibling to GL-CMD-EXPERIENCE-ROUTING-FIX-EVE-20260628-32
References: GL-RPT-EXPERIENCE-ROUTING-FIX-C1-... at SHA `4e65002`

## Why this dispatch exists

c1's routing-fix report at SHA `4e65002` confirms `/experience` no
longer trains the bigram, but flags that `_guala_cognition.expose()`
is still called from `_cognition_learn()` across at least four other
paths:

- Curriculum (Gutenberg / Aesop autonomous study)
- Worldfeed (the autonomous semantic input loop)
- Sight recognition (YOLO labels on video)
- Sound recognition (Whisper transcription)
- Teacher correction (interactive correction signal)

This means the silenced bigram is being actively trained from every
autonomous substrate path. With no human interaction, the substrate
is making the cheat richer minute by minute. Same substrate self-
sabotage as `/experience` was, at multiple entry points.

## What this dispatch does

Read-only audit of every `_cognition_learn()` call site. For each:

1. What input text or label is being passed to `expose()`?
2. Should that input train v5 atlas (via `read_sentence()`)?
3. Should that input train the bigram?
4. What's the substrate-truth justification for either answer?

After audit, c1 proposes per-site disposition. Eve reviews. We ship
the disposition in a separate code-change dispatch.

NO code changes in this dispatch. Read and report.

## Substrate truth

The bigram is a corpus-trained pattern matcher that was silenced
because it produces lies on emission. The training side `expose()`
exists to feed it. If we don't want it to speak, we don't need it to
learn — UNLESS some downstream consumer needs the bigram's
co-occurrence statistics as a SIGNAL (not as a voice).

That's the substantive question per call site: is `expose()` here
feeding a future voice, or is it feeding some other signal that has
substrate-true use?

## Per-site investigation

For each of the four call paths (curriculum, worldfeed, sight, sound)
PLUS the teacher-correction path PLUS any others c1 finds:

### Required answers per site

1. **Source data:** what text/label arrives? Examples (e.g., for
   curriculum: "an Aesop sentence like 'the fox saw the grapes'";
   for sight: "a YOLO class label like 'cat'")
2. **Current behavior:** `expose()` is called with what argument
   shape? Just text? Text + metadata?
3. **v5 atlas behavior:** does the same path ALSO call
   `read_sentence()` separately, or is `expose()` the only learning
   call?
4. **Substrate-true alternative:** if expose() is the only learning
   call, what should it be? `read_sentence()` direct? Both? Neither?
5. **Downstream consumer:** anything else reading the bigram model
   state (transition probabilities, vocab) for non-emission purposes?
   If yes, name them with file/line.

## What this dispatch is NOT

- Not a code change — proposals get a separate dispatch
- Not a deletion of `expose()` — that's downstream from this audit
- Not blocking curriculum / worldfeed / vision / audio paths from
  doing their substrate work — only auditing the bigram-training side

## What I'd expect to find (Eve's prior, c1 confirms or refutes)

- **Curriculum**: Aesop / Gutenberg sentences should route to
  `read_sentence()` (v5 atlas) the same way `/experience` now does.
  No reason to train the bigram from corpus.
- **Worldfeed**: same — semantic input should write v5 atlas via
  `read_sentence()`. The worldfeed cap fix (Phase A.2b) was scoped to
  the freezing issue; the routing question is separate.
- **Sight (YOLO labels)**: labels are single words / short phrases.
  Should bind to v5 atlas via the cross-modal binding path wC built,
  not train a text bigram.
- **Sound (Whisper transcription)**: transcribed speech is the
  closest to "real conversation input." Should route through
  `read_sentence()` to v5 atlas.
- **Teacher correction**: ambiguous — depends on what "correction"
  signal does in code. Could be a recall reinforcement (not bigram-
  training). c1's read needed.

These are predictions to be confirmed against code, not conclusions.

## Verification

The deliverable is the audit report. Eve verifies by reading and
cross-referencing c1's findings against the wiring spec architecture
(v5 atlas as canonical composer, bigram silenced, organ-brain as
recall feed).

If audit finds any call site where `expose()` is feeding something
that legitimately needs bigram statistics (not for emission), c1
explicitly names what consumes them and why.

## Report

c1 authors `GL-RPT-COGNITION-LEARN-AUDIT-C1-<date>-<seq>`:
- Every `_cognition_learn()` call site with file/function/line
- The five required answers per site
- Recommended disposition per site (re-route to read_sentence /
  leave / block / delete)
- Any consumer of bigram statistics outside `say()` (which is
  silenced) with file/function/line

## Standing rules invoked

- Substrate truth: training feeds either substrate-true composition
  or it doesn't; if it doesn't, it shouldn't run
- Read actual source before signing off (Three Verifications)
- wC's `grounded_vocab_integration.py` untouched but trace from it
  freely
- Past Eve's diagnoses are hypotheses: my "expected to find" list
  above is what I think; c1's code-side read is authoritative
