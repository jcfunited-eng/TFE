# Session handoff — Claude, 2026-09-02 (for a fresh chat)

Read with: .claude/skills/guala-development + incident-response skills, the
memory index, and collaborative_todo.md TAIL (the last ~30 entries carry
everything below in detail). This file is the fast rehydration.

## Where everything stands

PRODUCTION: healthy on task 1408 (44347ee1). Memory runaway RESOLVED
(steady 4-5% vs the old 85-96%). Auto-containment armed (65%/2min ->
drain). Sol's lane: speech causality, exclusively. My lanes: VR/environment
+ isolated copied bodies + reviewer of Sol's work. Only live cutovers need
announcement/serialization. Two-lane review is standing law.

## Live threads, in priority order

1. VOICE BENCH (active this hour): artifact page "Toy Vocal Organ"
   https://claude.ai/code/artifact/aaecbef7-96ff-4f62-a218-124e9b268064
   (redeploy: pass that URL as `url` from any new chat; source file was
   scratchpad/toy-vocal-organ-artifact.html — recreate from the artifact
   via action:"read" if scratchpad is gone). Deterministic source-filter
   reference voice. JOE'S VERDICT LADDER (each named a physical fix):
   buzz -> no closure; bad flute -> closure too smooth, needs the snap;
   toy-keyboard synth -> static note, utterances must MOVE; old chinese
   man -> human at last, wrong age + rising-tone contours; young man
   thrown up in the air -> rising quality SURVIVES three fixes (contour
   flatten, onset-glide removal, child scaling). CURRENT STATE: bench v8
   has a visible version stamp (rules out stale cache) and a LAYER TEST —
   the same ahh built one ingredient per button (1 bare, 2 +fall,
   3 +jitter, 4 +shimmer, 5 +breath, 6 +swell). AWAITING: Joe presses 1-6
   and names the number where it goes wrong. Suspects if rising persists
   on v8: the amplitude swell (a crescendo reads as upward motion) and
   the per-period white jitter (reads scrappy/rough; natural jitter is
   smooth drift, not per-cycle jumps). Confirmed-good ingredients are in
   the ledger entry "reference voice bench crossed into a person".
   Companion instrument: /tmp/guala_vowel_distinctness_scorer.py.

2. SOL'S SPEECH LANE: rebuilding the voice source; my review notes filed
   in ledger: valve-never-closes diagnosis (confirmed: 0 closed samples
   in 16k; collision physics EXISTS in prod code, regime never reaches
   closure), closure-necessary-not-sufficient concession, per-stage
   numeric gates, and the 18:11 collision-lineage bench recommendation.
   S-017 blocker hypothesis filed: S-015 affective-pairing starvation two
   layers down (bare contact delivers layer-8 without layer-7; pairing
   never fires — also answers Joe's touch-chemistry requirement).

3. R1 HONEST STAKES (Sol-assigned, analysis COMPLETE, verdict filed):
   docs/GUALA_R1_STAKES_CURRENT_REALITY_VERDICT_20260901.md. One line:
   energy economy is conserved-closed — spending/recycle/interoception
   ACTIVE and truth-coupled; income ABSENT (retired 2026-08-11 because
   authored-integer energy was untruthful; conversion law survives, bolt-
   on marked rcf:9470); deficit signal dead code; deficit->excitability
   absent; growth catalysis hardcoded zero. EATING WORLD HALF BUILT +
   falsified (branch env/honest-eating-world-half-20260901, commits
   3a2f6331 bite law + 3e904905 drinking law): apple=80g food, cup=200g
   water, exact depletion/conservation proven; organism socket is SOL'S
   (in rcf) — handed back, awaiting Sol review to connect halves. Joe's
   gut-principle for the socket: digestion = slow interior compartment
   with continuous interoceptive afference, not a conversion event.

4. THE BIG PICTURE DOCS: docs/GUALA_SELF_CAUSED_ACTION_BRAIN_COMPARISON_
   20260901.md (built new-brain-first; akinetic phenotype; rungs R1-R6 =
   A-004..A-010 on Joe's master list — the list is in the ledger, entry
   "FYI you should know we were working off this list" region). The
   decisive unrun experiment: the readiness bridge -> choice witness.
   Joe's mood: project near scrapping over pace + polish-vs-alive;
   ratified direction = less shell more law; loop experiment on a
   STRIPPED bench body when the time comes.

## My parked branches (all local, none pushed, none deployed)

- speed/world-receipt-tail-20260901 (021c31a0): receptor short-circuits,
  proven byte-identical, ~6.4ms/beat.
- env/world-w1-house-20260901 (e3cf7151): 6m rooms + clearance law +
  posters/ball/blanket; BOOT-PROVEN on bench.
- env/honest-eating-world-half-20260901: bite + drink laws (see above).
- env/participant-decouple-20260901 (a23c34df riders): door fix — WORKS
  combined with Sol's 5fcecdeb coexistence rework (proven: turn, approach,
  felt touch on the copy); needs Sol to fold riders in.
- cleanup/shell-dead-mass-20260901 (ca91d5d0): 337 dead files removed,
  import-proven; archives on /mnt/tfebackup/guala-archive/.
- incident/motor-trace-window-fix (6fc079e1): REJECTED by Sol, history only.

## Standing cautions for the fresh session

- Anthropic safeguard flags keep killing dense sessions ([cyber] class,
  false positives on this work). Keep sessions focused; the ledger is the
  continuity spine — file everything there.
- Register-and-sweep every bench process/container (incident-response
  skill). Kill by PID in a separate command, never pkill patterns.
- Physical vocabulary only with Joe (no "thinks/feels"); short verdict-
  first replies; code-fenced reports; his ear-verdicts are the best
  debugging instrument this project has — take wrong-words literally.
- Deploy nothing without a coordinated window; Sol reviews everything of
  mine; I verify everything of Sol's.
