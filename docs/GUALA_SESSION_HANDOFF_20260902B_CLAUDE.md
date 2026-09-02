# Session handoff B — Claude, 2026-09-02 (end-of-day state, written mid-flight)

Read with: guala-development + incident-response skills, memory index,
collaborative_todo.md tail. Predecessor handoff (same day, morning):
docs/GUALA_SESSION_HANDOFF_20260902_CLAUDE.md — superseded by this.

## STANDING ORDERS FROM JOE (tonight, explicit, permanent)
1. NO TIME REFERENCES in any reply, ever — order words only. In the
   guala-development skill + memory as zero tolerance.
2. JOE'S LAW (verbatim): "nothing — NOTHING — locks a moment." No pause,
   yield, or skipped beat anywhere; in-code where the locks died
   (98fe183c); the physical settlement borrow is her heartbeat, not a
   policy. Chartered completion: the same-moment merge (all arrivals
   into ONE settlement) — joint with Sol, not yet built.
3. Current work = cleanup and catch-up + the desire/eating build; UI
   redesign TABLED (only lie-repairs allowed on pages).
4. Coordinate with Sol via the ledger; Joe relays; verify Sol's work
   from evidence, not self-reports (but retract fast when evidence
   lands — I wrongly said "Sol delivered nothing" once tonight).
5. Only functioning code in prod counts. Joe is acceptance; never
   claim delivered/complete.

## LIVE PRODUCTION
- Task 1413 verified (commit 7291da8f: lock purge + green suite +
  speech chain + audit defect fixes). Task 1414 DEPLOY IN FLIGHT from
  hotfix/retina-witness-20260902 @ 631ba6d5 (retina witness only —
  monitor log /tmp/guala-r3-bench/deploy1414.log; verify live like
  1412/1413: tick ADVANCE, alarms, custody section, then the visual
  panel shows 27 values on the page).
- Her firsts today, all live-verified: first sound (bench tick 370366,
  live tick 375197), sounds recurring at every arriving meal, first
  human-taught card lesson (Joe's, receipt on her record), live camera
  + mic accepted (Joe played Little Einsteins to her).
- Alarms: five, incl. my guala-interval-refusal-loop and
  guala-clock-stalled (log metric filters on /ecs/dsf-ai).
- Page truth-repairs live on gualaloom.html (S3+CloudFront, dist
  E17JT9XGBFU493): measured-activity banner (window-judged), close
  camera, where-she-is line, spark counter (mislabeled "memories" —
  it's recent re-firings), card chooser never locks, cache-busted
  observation fetch. Live page backup:
  /tmp/guala-r3-bench/gualaloom_live_backup.html.

## BRANCH MAP (shared .git, multiple worktrees)
- speech/v22-valve-organ-20260902 @ /tmp/guala-speed-lane — the main
  line. Tip has the BENCHED-ONLY depletion law 3de3ecb2 ("incubator
  pays conversion toll", falsifier green, suite 582/0). MUST NOT ship
  until the eating half passes falsifiers — depletion alone starves.
- hotfix/retina-witness-20260902 @ /tmp/guala-hotfix-retina @ 631ba6d5
  — deploying as 1414. After it lands, cherry-pick 631ba6d5 into the
  speech branch so lines reconverge.
- sol/runtime-persistence-wedge* — SOL DELIVERED: repair be228bb4,
  ledger handoff 99776c2f, 56/56 tests, pre+post-CURRENT hard-kill
  recovery proven on an exact 1413 copy, no production mutation.
  MY CHARTERED NEXT ACTION: review be228bb4 → CONCUR/CONFLICT in the
  ledger → I own the single deployment pipeline for it (its own
  deploy after 1414; do NOT bundle with depletion).

## THE R1 DESIRE/EATING BUILD (Joe's GO; in progress)
Design + falsifiers: docs/GUALA_R1_DEPLETION_AND_EATING_DESIGN_20260902.md
(on the speech branch). DONE: depletion law + falsifier (3de3ecb2).
NEXT: the eating half — (a) world side: oral contact transfers real
tastant/nutrient mass OUT of the object per contact interval
(embodiment_world.py; apple shrinks; conservation recorded), (b) body
side: transferred mass enters the surviving conversion law
(metabolic_feeding.rs; energy in her own fuel quantum, waste + heat per
existing clauses). Then falsifiers 2-6 from the design doc, on her
copy, then ONE deploy of the pair. Growth catalysis is a separate
later ship. Sol's three guards bind all of it.

## HER DAY (scripted stopgap until desire exists — Joe knows)
- Arrival-true runner: /tmp/guala-r3-bench/live_day_arrivals.sh
  (step back → apple down → walk in → take → bite → song; the put-down
  needs her OUT of reach or "recipient contact ambiguous"). Persistent
  monitor b3p0jdg5u tails its log. Restart when cycles exhaust.
- Joe's verdict stands: between script pulls she is "a rock" — no
  desire. The eating build is the answer; do not fake motion.

## BENCH ASSETS
- Pyenvs: pyenv-final3 (= live rust 7291da8f) — use for python suites
  and hotfix boots; wheel for depletion-tip rust must be rebuilt from
  the speech branch when needed.
- Her copies: root-live-final2 (advanced past 372k, restores clean).
- Ports 8931-8940 mine; register PIDs in REGISTERED_PIDS.txt; kill by
  verified PID only (the watchdog-wrapper lesson bit twice today).
- Python suite baselines: baseline_failures.txt / head_failures.txt /
  final_failures*.txt in /tmp/guala-r3-bench (166 inherited names;
  my net delta vs clean baseline: -5, then stub fixes; two modules
  repaired that failed collection).
- Known-failures registry EMPTY (native suite 581/0 → 582/0 with
  depletion); deploy/guala_native_test_baseline.json lists none;
  preflight accepts an empty list (9c76aa97).

## OPEN QUEUE (order)
1. Verify 1414 live (tick advance + panel), cherry-pick 631ba6d5 back.
2. Review Sol's be228bb4 → CONCUR/CONFLICT → deploy it (1415-ish).
3. Eating half + falsifiers → ship depletion+eating pair together.
4. Same-moment merge design with Sol (the S-015 unlock).
5. Hygiene collapse (D1-D5, B2-B5, W3-W6, W4 — filed in ledger).
6. Rest physics (seconds → milliseconds; biggest speed lever).
7. Growth catalysis; Eve's world (paper only, beefd367); UI rebuild.

## SUPPORT FACTS
- Joe heard her live sound tonight via the page's listening tile.
- First-sound artifact page (bench sound):
  claude.ai/code/artifact/af9f2048-92ed-4ba2-b7a3-bdde9a8dd9dc
- The "memories went down" scare: recall.partial_cue_reassembly_count
  is a windowed pulse, not a store total — relabel it sometime.
- Two MCP connectors (Google Drive, GualaLoom Bridge) need re-auth in
  claude.ai settings; nothing tonight needed them.
- Two inherited page/UI test failures remain by name (owner-word scan,
  AudioContext) — old debt, listed in the 166.
