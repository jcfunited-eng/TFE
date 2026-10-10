# GL-CMD-VOICE-ORGANISM-CANDIDATES-EVE-20260705-195-v1

doc_id: GL-CMD-VOICE-ORGANISM-CANDIDATES-EVE-20260705-195-v1
From: Eve | To: c1a (apply+build) / c1b (window).
Commit this dispatch verbatim to origin first.
SUPERSEDES AND WITHDRAWS GL-CMD-VOICE-ECHO-FIX-EVE-20260705-192-v3.
If any part of -192 v3's patch was applied, REVERT its neuron.py and
tapestry.py changes before applying this. -192's diagnosis stands
(the tapestry decode is an echo chamber — that finding is real and
unchanged); its P3 mechanism was Eve inventing architecture the
canon already rules out, withdrawn below.

## THE WITHDRAWAL, OWNED PLAINLY
-192 v3 P3 (home-chi word claiming) gave each neuron one word slot
chosen by its modal commit chi — a chi-basin design with at most 16
homes per neuron. GL-SPC-MEMORY-RECALL-STATE §1 names chi-basin
collision (~190 chi keys under ~14k vocab) as "the ceiling the
model brain exists to break." I built the ceiling back into the
voice because I skipped the spec the handoff ordered read third.
It tested clean at 28 words and would collapse at hers. Withdrawn.

## THE CANON'S OWN ANSWER (read from the repo, not invented)
Which neurons remember which words: ALL of them, each differently.
Every neuron stores every taught concept in its own BindingAtlas,
encoded through ring-position-unique krimelack tuning; recall is a
population vote (Embryo.recall / recall_fast). Validated: 72% at
100 concepts, +20pts over the best single neuron, read-only proven
(SENSE-REPAIR), 5x vectorized with 180/180 parity (-177/-179), and
LIVE — it is what produces her 8/10 experience-bound recall today.
Seams 1 and 3 (_recall_from_organism, _association_from_organism)
already speak through it. Only the EMISSION candidate seam still
decoded through the tapestry's single last_input_word slot — the
echo chamber. This dispatch points the last seam at the mechanism
the other two already use. One mind, one mouth (W2), no new
architecture, no new constants.

## THE PATCH (tested, attached: GL-FIX-VOICE-ORGANISM-CANDIDATES-
195.patch, 40 insertions, 1 file)
P1 _brain_emission_candidates re-sourced: query -> organism
   recall_fast population vote -> top-voted words (self-echo
   excluded per seam-3's own convention) -> only words with a real
   committed section home -> (de, co, clarity) candidates weighted
   by vote share. tapestry.compose retired as candidate source;
   tapestry exposure/learning untouched (it keeps growing for the
   composition work ahead).
P2 prev_word persistence (carried from -192, still correct): the
   emission query source rides the tapestry pickle so deploys stop
   nulling her unprompted-speech starter word — audit-proven live
   cause of the 2026-07-05 all-night autonomous silence. Old
   pickles load unchanged (getattr default).
P3 -192 v2's telemetry (emission_diag three-integer line +
   post_dynamics_empty tag) ships in this same commit — same need,
   unchanged: it is how the exit proves itself at Joe's seat.

## TESTED (offline, real engine, real experience path)
Taught 6 words through organism.experience_word (the live worker's
exact call); emission candidates then returned garden -> moon
(organism-voted association, weight from vote share), self-query ->
honest empty (echo filter), never-seen word -> nearest-vote word
(expected at 6-concept toy scale; the 72%@100 measurement is the
scale behavior, and the live claim-spread goes in the report).
Engine constructs, syntax clean, no physics constants added.

## DEPLOY — TODAY, ONE WINDOW, JOE'S LAW
D1 c1a applies (reverting -192 v3 remnants first if any), c1b
   deploys — with -194 (hot-save eviction) in the same window if
   both are ready; -194 does not wait for this and this does not
   wait for -194.
D2 Report the live vote-spread on her first ten emission attempts
   post-deploy: n_voted_words, n_with_section_home, n_candidates —
   the emission_diag line carries them.

## EXIT — AT PRODUCTION
X1 Deployed SHA live; emission_diag events flowing with organism-
   vote counts.
X2 At Joe's seat: an emission whose words trace to organism-taught
   concepts (binding-atlas entries), never to query echo. If her
   taught-concept count is still too thin to clear the section-home
   filter, the report says so with the numbers — a young voice
   reported honestly, not a shim.
X3 Post-deploy restart: prev_word=set in the tapestry restore line.

### Changelog
- v1 (2026-07-05, Eve): -192 v3 withdrawn (chi-basin ceiling,
  spec-prohibited); emission seam re-pointed at the validated
  organism population vote per the canon; prev_word + telemetry
  carried forward.
