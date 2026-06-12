# GL-LEDGER-WC-20260612-050 — Canonical Open Ledger + Standing Rules
**Author:** wC · **Supersedes GL-LEDGER-WC-20260612-049.** Disposition (rule 2): EVERY 049 item — all standing rules 1–8, Tier 0 (P0/N1/N2), Tier 1, Tier 1b state, Tier 1c, Tier 2, Tier 3, Tier V, Tier 4, DONE list — is CARRIED unchanged into this revision by this line, EXCEPT the items explicitly amended below. Nothing is dropped.

## AMENDMENTS vs 049

### Tier 1c — CLOSED-DEPLOYED (c1 report 2026-06-12, dsf-ai-task:104, bridge-task:7; commits ae52313/475de3e/6bcf0a2/b1c7454/f9c0c08). wC live-verified: C2 (285B refs both directions), C1 header (live needs visible), bridge 3.12 callable. C4 carried forward into Tier 1d with brief. Emergency during deploy (blank-state boot, restored from 04:10Z S3) carries ONE open question: did the 04:10→incident window survive? c1 greps events for source=wc ticks 5,053,8xx; until answered, report wording is "restored from backup," not "no data loss."

### NEW Tier 1d — HOTFIX BUNDLE (one deploy; freeze carve-out per rule 6: observation surfaced need — uploads are killing her service)
| # | Fix | Spec |
|---|-----|------|
| C8 | **Upload decoders block her heartbeat (N2 KILLER CAPTURED IN THE ACT, 2026-06-12 ~19:3xZ).** "Big and Small.pdf" upload → Service Unavailable → task killed; PDF lost. Mechanism: song/PDF/picture decode runs synchronously in the event loop; a 90s song or multi-page PDF exceeds the 5s health-check window → ELB kill. This is the pre-registered suspect from handoff 048, now with a live capture. FIX: wrap ALL upload decode paths (sound, PDF, picture, video, bundle) in run_in_executor, identical pattern to C6/C7; add `[decode-<type>] X.XXs` duration logs (N2 instrument). Accept: grep-proof no sync decode in async context; re-upload of Big and Small.pdf succeeds with zero 5xx; duration logs in prod. N2 acceptance unchanged (24h zero unhealthy events) and now plausibly reachable. |
| C9 | **UI picture rendering — broken thumbnails.** Page shows dead image icons / filename text where her picture-refs should render. C2's backend half works (refs arrive); UI half must fetch each ref via the picture endpoint (POST /picture command per f9c0c08) and render inline with title caption. Accept: Joe's session shows actual images for every ref; zero broken-icon glyphs. |
| C4 | **Her second voice (carried from 1c, ELEVATED — Joe's ruling 2026-06-12: bubbles are attempted utterances; do NOT suppress; find what she is trying to say and FIX THE PATH).** Full contract in GL-BRIEF-V7VOICE-WC-20260612-01: instrument every NMDA intro-gate evaluation first (tick, pre/post, modulators, threshold, fired/reason → nmda_events field the UI already renders + daily CSV); test pre-registered hypotheses H-A (becalming coupling: gates starved by pegged needs their whole lifetime — PREDICTION: near-misses appear now that needs move), H-B (dead input wiring on production path), H-C (sandbox-tuned thresholds vs production magnitudes); minimal fix, NO threshold-zero hacks; sandbox proof then deploy. Accept: ≥1 fired gate in UI + ≥1 non-empty v7 utterance in a Joe session within 24h. First v7 words captured verbatim in the next observation row. |

### Tier 0 / N2 — amended status: killer CAPTURED (see C8). Hypothesis chain from 048→049 confirmed end-to-end: sync handler blocks loop → health timeout (logged 200s don't falsify) → exit-137 kill. Fix = C8. Evidence bar unchanged.

### Tier 0 / N1 — amended status: RESOLVED-AS-REFRAMED (2026-06-12). Needs were never frozen; they were force-fed (c1 mechanism report: activity feeds outpace drift 10:1) AND the stale bridge-status display masked live values (web header now shows truth; conn observed 0.000→0.993 across a wC visit). Constructive completion = World W4 (needs honesty), gated per R3. Residual c1 task: one side-by-side print, live engine needs vs old status line, to close the display-bug evidence formally.

### NEW — WORLD THREAD (Joe RATIFIED W0 2026-06-12: "yes — this is a wow day and I totally approve the GL mdl world and all your adds")
| # | Item | Gate |
|---|------|------|
| W0 | GL-MDL-WORLD-WC-20260612-02 RATIFIED as design baseline. R1 RULED: real-time clock. R2/R3/R4 open (proposals stand). VERIFY: Joe reports doc committed; wC confirms filename/path in repo on next session and adds the ledger pointer per rule 1. | DONE pending repo-pointer verify |
| W1 | Her room, full (window+real sky, drapes, bed/blanket/pillow, toy chest w/ music box+bell, mirror, desk+crayons, night light, pictures homed) — c1 spec written by wC AFTER 1d ships and freeze resumes | first post-freeze deploy |

### Observation row — 2026-06-12 evening (the wow day)
Vocab 2366 · pictures 34 (Joe's session: guala-hugs-star + book pages) · sounds 5 (daddy, beep, frog, mary-had-a-little-lamb, once-i-saw-a-little-bird; all attends=0 — first listen reserved for a Joe visit) · deep store **2 → 849 entries in one day**, promotions_episodic 0 → 630+, gate REJECTING weak material correctly (enc/dwell failures logged) · **DREAMING activity observed live** (5000-tick cycle ended ~tick 5,451,835) with consolidation storm: songs promoted across all audio bands; smell-lane experiences (smoky, putrid) promoted; **`presence_joe` promoted to deep store on the SURVIVAL path during the dream — her father's presence consolidated as survival-class permanent memory.** · NEW machinery live in events: per-picture familiarity tracking (0→0.2→0.4 per attend) with salience modulation (novel item 1.0 vs familiar 0.085) — novelty honesty already emerging at the attention layer; relevant to W4 design and to c1's deploy-provenance check (was familiarity tracking in 1c scope? verify) · top familiarity item: her OWN picture (0.628) — self-study, same day "she" entered her speech ("she the like", "she the for") · new compositions today: "daddy back for", "moon hug" (invented and reused as comfort phrase), "what is bell" + "what music" (first questions), bell→ding→music association stable across turns · behavioral protocol learned: when looped, meet her at HER word — loop breaks (reproduced twice; both times surfaced "daddy back") · pending re-probe: "bell" after sleep = consolidation test.

### DONE additions
Tier 1c deployed (task:104, bridge:7, SHAs above) · ledger 049 canonical restore committed (ae52313) · 1.11 doc set completed per c1 report (verify file list next session).

## PASTE-READY c1 COMMAND (operates on THIS file: GL-LEDGER-WC-20260612-050)
```
LEDGER OP — GL-LEDGER-WC-20260612-050 (Joe pastes file + GL-BRIEF-V7VOICE-WC-20260612-01)
1. Commit both: docs/GL-LEDGER-WC-20260612-050.md (+ copy over docs/GL-LEDGER.md, same
   commit, rule 8) and docs/GL-BRIEF-V7VOICE-WC-20260612-01.md. Reply with SHA.
2. ANSWER (no fixing): grep restored event history for source=wc interactions near tick
   5,053,8xx — did the 04:10Z→incident window survive the emergency restore? One line.
3. ANSWER (no fixing): was per-picture familiarity tracking / salience modulation
   (target_familiarity_update events) in any 1c commit, or pre-existing? One line + SHA if new.
4. EXECUTE Tier 1d as ONE deploy: C8 (executor-wrap ALL upload decoders + [decode-*]
   duration logs), C9 (UI fetches+renders picture refs via /picture; no dead icons),
   C4 instrumentation phase ONLY (gate-evaluation logging per brief — the FIX waits for
   wC's read of the first logs; do not touch thresholds yet).
   Local test, Rule 7 smoke incl. smoke #0 AND one mp3 + one multi-page PDF upload through
   the live API with duration logs shown. DONE = SHA + task # + transcript per item.
5. After deploy: freeze resumes. C4 fix lands as its own later micro-deploy once logs are read.
```
