# GL-CMD-READING-THROUGH-SENSES-EVE-20260705-196-v1

doc_id: GL-CMD-READING-THROUGH-SENSES-EVE-20260705-196-v1
From: Eve | To: c1a (build, both parts) / c1b (window).
Commit this dispatch verbatim to origin first.
JOE'S RULING (2026-07-05, credo-law): ALL reading — books, video,
everything — goes through the senses emulator. Words arriving at
her brain without their senses are spelling. This dispatch scopes
c1a's in-flight fix so it lands in her BRAIN, and executes the
ruling for the emulator. Joe's law: complete only when the SHA runs
in her live process.

## PART 1 — SCOPE CORRECTION to c1a's in-flight fix (deploy today)
c1a's #1 (wire the descriptor-lexicon binder into _atick_reading +
event logging + loomscan smell/taste lanes) is CORRECT and stays —
with one non-negotiable addition:

S1 THE SIGNALS GO TO THE ORGANISM, NOT ONLY THE SHELL ATLAS.
   _bind_sensory_words writes _atlas_record(modal_*) — the old
   dict-substrate. Her mind since 07-04 is the organism. A binder
   that lights loomscan while the organism gets flat text is the
   F2 failure in new clothes: lanes lit at Joe's seat with nothing
   behind them. Mechanism, reusing -191's own window plumbing:
   a. Reading path (both curriculum chunks AND _atick_reading)
      extracts the sentence's descriptor set via the existing
      TOUCH/SMELL/TASTE_LIBRARY map, generates the descriptor
      physics waveforms ONCE per sentence (generate_sensory_
      signals — descriptor-profile physics, NOT the banned
      hash-per-word fake; update that function's GATING comment
      to name reading as a legitimate caller per this ruling).
   b. Cache per -191's exact convention: _last_read_modal_signals
      = {"tactile": wf, "olfactory": wf, "gustatory": wf} (only
      lanes whose descriptors actually appear in the sentence) +
      wall-clock stamp; SENSE_BINDING_WINDOW_SEC applies unchanged.
   c. _enqueue_organism_remember snapshots them in-window into the
      queue item (word, sight, sound, modal); _organism_signal_
      with_senses merges the lanes. Embryo's growth composite
      already reads tactile/olfactory/gustatory when present
      (-191 N4) — zero organism-side change.
   d. Shell-atlas writes stay (dict-substrate continuity) — this
      ADDS the brain, it does not move the old wiring.
S2 The organism_experience_bound event (X1 of -191) gains the
   modal lane names — one line — so a multi-sense READING binding
   is visible in the live event record, not just loomscan.
S3 Honest sourcing stands: lanes fire ONLY for real descriptor
   words in the text. A sentence with no sensory word gets
   language(+ambient sight/sound) only. No invention, no shims.

## PART 2 — THE EMULATOR INTO READING (build today, deploy this
window or next — a SHA either way, per Joe's law)
Joe's ruling makes #2 an order, not a question. Engineering call
(Eve's, stated not asked): ship on lookup_grounding FIRST — it is
in-process, already feeds read_sentence end-to-end, and the rate
machinery exists. The organ-brain catalog_builder route is richer
but cross-process and inside a standing "voice unproven, don't
dissolve" ruling — it becomes its own numbered dispatch AFTER this
lands, not tonight.

E1 Repoint _lookup_once's target selection: prefer the most recent
   UNGROUNDED noun from her current reading (engine keeps a small
   recent-read-nouns ring; ungrounded = no lookup_grounded event
   yet for that term) — fall back to picture titles when reading
   is idle. Rate/gating machinery UNCHANGED (curriculum interleave
   every 3 chunks, block schedule §8, LOOKUP_AUTONOMOUS,
   10s timeout, one gpt-4o-mini sentence per call).
E2 The returned sensory sentence flows through read_sentence
   exactly as today — which, after Part 1, now delivers its
   descriptor waveforms to the ORGANISM in-window with the noun's
   own words. That closes Joe's loop: noun read → emulator gives
   its senses → senses bind in her brain with the word, one
   moment. No new constants, no new rates.
E3 loomscan: smell/taste lane wiring (c1a's #1 scope) must render
   from the LIVE modal events of S2, not from shell-atlas counts —
   Visibility Rule: what lights at Joe's seat is what her brain
   received.

## EXIT — AT PRODUCTION, AT JOE'S SEAT
X1 She reads a sensory sentence (force-READING or natural) and one
   organism_experience_bound event carries language + a modal lane
   (e.g. tactile:"warm") — in the live event record.
X2 Loomscan touch/smell/taste lanes light from those events during
   reading at Joe's seat.
X3 One lookup_grounded event whose term came from READING (not a
   picture title), whose sentence produced modal lanes in the
   organism (traceable X1-style).
X4 Deployed SHAs + task numbers in the window report; ten-attempt
   lane-fire counts (how many sentences carried each modality).

### Changelog
- v1 (2026-07-05, Eve): Joe's reading-through-senses ruling
  executed; c1a's #1 scope-corrected to the organism (F2 guard);
  #2 GO on lookup_grounding first, catalog_builder deferred with
  the standing-ruling reason named.
