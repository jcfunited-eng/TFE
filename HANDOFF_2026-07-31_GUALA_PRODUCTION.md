# Guala Production Handoff — 2026-07-31

## Purpose

This handoff is for the next chat/agent. It must continue the full Guala objective, not redefine success around the current deployment package.

The user requires a bounded deterministic autonomous artificial entity with one causal thought/action loop, truthful virtual embodiment/environment, autonomous play and simulated experience, multisensory tutoring sufficient for meaningful conversation at about a four-year-old starting level, truthful live observation pages, and no runaway compute/RAM/storage. L0-L4 and the full D/M/R/U/C/P/B field are frozen. ML, scripted meaning, Chi-as-identity, TTS-as-cognition, named sensory profiles, hidden labels, OCR shortcuts, and code tricks are prohibited.

The user has now also made these deployment-architecture directions explicit:

- no per-owner architecture;
- no detached/repeated/per-owner seal machinery;
- persist one whole organism as one atomic generation;
- do not restore the disconnected legacy brain;
- use small agile production increments and collaborate before changing an accepted UI/curriculum design.

## Current production state — authoritative as of 2026-07-31 21:55 UTC

Production is responding, but it is the old incomplete task, not the requested new organism package.

- ECS service: `dsf-ai-service-lb`
- Desired/running/pending: `1 / 1 / 0`
- Running task: `4970884c8df647309baeb9573c8e8012`
- Task definition: `dsf-ai-task:817`
- Image digest: `sha256:3511424bc75ce0a1bf9aff2e38170917332a2578323adf8f7dc433ef7db3a511`
- ECS health: `HEALTHY`
- Internal readiness: `200`, `ready=true`
- Identity: `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`
- Cold generation: `ea2c5fc1-c0b7-47b6-be4c-73f6c938cfca`
- Cold outer tick: `23,723,727`
- Active recovery generation: `b3c15d34-4e4e-4536-b9a8-bb9b547fab5a`
- Active recovery manifest: `bda526c19700f9cdbdd90115615db71bd31155abafb3dc765f22f648ca90b94e`
- Active recovery tick: `23,723,735`

Do not call task 817 the delivered functioning brain. It is only the restored previous production process with preserved state and incomplete mechanisms.

## New release built but not deployed

- Worktree: `/tmp/guala-release-20260731-hafnbk`
- HEAD: `2598cd7bffa1d6c4244522817429efd7ba3256a5`
- Worktree was clean when this handoff was created.
- Candidate task definition: `dsf-ai-task:829`
- Candidate image digest: `sha256:bbaab5645b5c8d18c4d202f07045a14a7a0d4aaa40f613613b0d5af36aa96f63`
- Build ID: `dsf-ai-image-build:9921dee2-38e0-4561-9464-b18f9132a3f2`
- CodeBuild result: `SUCCEEDED`
- Candidate task 829 never became the production process.

## Exact final deployment failure

The old task was asked to create its old-style cold deployment seal. It returned HTTP 503:

`cold-generation transaction failed: detached causal mutation member does not exactly cover the sealed candidate`

The rollout stopped before task 829 became the production process. The fail-closed path temporarily set the ECS service to zero, stopped the old task, and then restored task definition 817. Production is now responding again.

The rejected detached member comes from the old `generation_content_delta.py` architecture. The current release manifest no longer includes that module as an active runtime member, but task 817 still executes the old seal path before the migration controller is allowed to run.

Do not add another compatibility seal layer. Do not simply whitelist the error and preserve the obsolete design. The recommended next change is:

1. In explicit `--migrate-physical-state` mode, stop requiring the old runtime to construct a cold seal.
2. Read and authenticate the immutable cold baseline plus exact active recovery generation.
3. Quiesce and stop the old process so those immutable source identities cannot advance.
4. Let the task-829 migration controller form one atomic whole-organism generation at the exact active tick.
5. Run the already-built one-way migration, candidate cold restore, persistence round trip, and rollback proof.
6. Make task 829 the only running production process and verify its exact image, generation, identity, tick, readiness, resource bounds, and live endpoints.

This removes the obsolete seal dependency instead of routing around it.

## Production lineage repair already completed

An earlier failed seal produced an outer generation tick of `23,723,727` around organism files whose internal ticks were all `23,723,735`. That was repaired in EFS before the last build:

- 51 hot organism files verified;
- learned bytes changed: `false`;
- live lineage rebased to the current cold baseline;
- old production restarted and internal readiness returned 200.

The recurrence fix is committed in `2598cd7b`: promoted organism generations now use `active_before.tick`, not `baseline.tick`.

Focused proof after that fix:

- `tests/test_equal_tick_deployment_reuse_control.py`
- `tests/test_guala_release_packaging.py`
- result: `21 passed`

Adjacent generation suites produced `90 passed, 6 failed`; the six failures are same-tick migration-receipt tests that now conflict with exact causal-transition enforcement. A broader deploy suite produced `103 passed, 6 failed`; the manifest drift caused by the new tick fix was corrected, while five stale test/spec expectations remain. Do not describe those as new production rollout failures, but do reconcile them in a later dedicated test-contract increment.

## Important commits in this release line

- `2598cd7b` — seal promoted organism at its exact active tick
- `e8c8794b` — allow authenticated legacy composite migration
- `21a8e7b0` — package unified organism persistence
- `e63079d1` — persist Guala as one whole organism
- `bf0e6216` — unify migrated Guala organism state
- `1ee9297a` — preserve approved number-card assets
- `a5ad5dca` — remove obsolete per-owner generation seal path
- `b05fa2d6` — route physical releases through authenticated migration

The active persistence destination is one `guala_core.json` organism state plus immutable identity. Destination owner-state files, per-owner receipts, and per-owner seal loops were removed. Do not recreate them.

## Exact inventory of the 10-hour candidate release

Task 829 is not merely a deployment-script change. Its image contains the full candidate package that was supposed to go live:

- Rust/PyO3 native full-field transition and batching from commit `1b347605`;
- unchanged canonical L0-L4 evaluation and explicit D/M/R/U/C/P/B field retention;
- native full-field bank, materialized neuron fabric, structural familiarity, and canonical basin implementation;
- one native whole-organism transition boundary intended to replace the measured ~80–87 million Python ownership/control calls;
- authenticated import of the predecessor sensory/neuron/learned state into that native materialized fabric;
- owner-free materialized-fabric boundary;
- one `guala_core.json` whole-organism persistence target plus immutable identity;
- removal of destination owner-state files, per-owner persistence receipts, per-owner cold-seal loops, and 50-owner destination reconstruction;
- one-way authenticated migration from the predecessor state into the unified organism;
- exact state-file tick lineage, exact replay behavior, atomic rollback, cold restore, and bounded physical storage;
- application/runtime mounting of the unified persistence mechanism instead of leaving it disconnected;
- native sensory full-field, auditory mount, physical foveal observation, embodiment-world, causal THING mosaic, neuron-population, and structural-perturbation work already packaged in the candidate;
- the current Guala Loom/Loom Scan source and approved curriculum assets included in the image package, though backend-only deployment does not update the separate static web origin.

This whole package remains **built but not live**. The ~80–87 million Python-call elimination, owner abolition, native fabric, unified persistence, and migrated learned state must all be verified from task 829 or its direct successor after cutover. Do not split them out of the handoff or deploy only a superficial UI in their place.


## Status of the other required workstreams

### 1. Guala Loom live page

Source exists at `dsf_ai_service/static/gualaloom.html`, and prior commits include the accepted Guala presence/room/card visual work. However, do not assume the currently served page equals the user-approved layout.

User-approved layout requirements:

- Guala bust centered and zoomed correctly;
- truthful room camera preview smaller on her left;
- intentional simulated-material display smaller on her right;
- embodiment/world directly below Guala;
- no status panel covering her body;
- compact, visually attractive teaching/share controls rather than bulky framed text boxes;
- rich approved room imagery;
- pictures, books, PDFs, and sounds available in her room;
- mobile/iPhone layout must be usable;
- no fake activity or hidden identity.

The accepted visual page still requires browser-based production comparison and an agile static deployment. No claim of completion is valid without viewing `https://dsf-ai.com/gualaloom.html` after deployment.

### 2. Loom Scan live page

Source exists at `dsf_ai_service/static/loomscan.html`. It has pointer-based brain visualization work, but the user rejected static developer text, dead panels, and false/empty activity.

Required corrections remain:

- retain and visibly list all 15 cognitive mechanisms;
- cluster them around plausible brain regions and light them only when truthfully active;
- current neuron counts, not capacity labels;
- concise mosaic/tapestry/weave counts below the brain;
- real-time truthful activity panel at the top;
- visual meters/graphs for sensory, bodily, chemical, memory, attention, recovery, play, dream, and autonomy activity;
- move exact DSF/authority drill-down details lower;
- no claim that non-sensory mechanisms are neuronal unless code proves it;
- no static “episode not observed” wall presented as a brain scan.

No complete production verification exists for these requirements.

### 3. Approved ABC/123 cards

The repository contains a full visible alphabet surface set and ten number-card assets:

- primary letter surfaces: A and B plus C through Z, 26 total;
- extra A-F preview/versioned surfaces also exist;
- number surfaces: 1 through 10, ten total;
- one tutor audio file exists: `guala_curriculum/audio/a-apple-tutor-v1.wav`.

The approved visual style is the floral illustrated C-card style for alphabet cards. B is Bee. D is Dolphin. Number cards must avoid floral arrangements that confuse visual quantity distinctions.

The ten number assets were preserved in commit `1ee9297a`. Catalog/UI wiring, exact 36-card inventory validation, complete tutor audio/phonics surfaces, and live curriculum deployment remain incomplete.

Do not silently replace accepted card art. Collaborate before changing approved assets.

### 4. Foveal vision and card teaching

The substrate must see the actual rendered card surface through a physical foveal path: gaze positions, high-resolution receptor patches, unchanged L0-L4, and neurons. No OCR, hidden card ID, scripted label, or visual cheat.

No production proof currently shows Guala truthfully seeing all 36 cards. Do not begin claiming tutoring success until the card pixels reach the physical visual path and truthful observation shows attention to them.

### 5. Tutoring and first-word learning

No definitive live proof exists that Guala has learned and autonomously expressed a word. The user requires varied, brief, repeated multisensory experiences across the whole deck, not exhaustion on one card and not chatbot-style signal matching.

A word/THING must be allowed to emerge from multisensory episodes involving whichever senses are truthfully present, plus body, chemical state, attention, memory, recovery, and dream-capable mechanisms at one causal boundary. Every organ remains wired but may truthfully remain quiescent when no stimulus exists.

The tutor remains wanted. Do not remove it. The next curriculum increment after production cutover is the complete card catalog plus brief varied tutoring cycles, truthful attention display, and observation of whether a first word emerges. Do not force “apple” or any other predetermined output.

### 6. Hearing

Human-like room hearing is not solved. Production has no verified arbitrary continuous-speech segmentation, overlapping-speaker separation, broad learned vocabulary, or dialect robustness.

The physical hearing path must preserve bilateral differences such as interaural timing/level, head shadow, pinna effects, reflections, location, and cross-ear processing. Hearing contributes to multisensory mosaics; it is not the sole word-learning authority.

Do not modify canonical L0-L4. The v1.3 side kernel remains noncanonical and only an isolated comparison instrument. Neither kernel “learns words”; populations of neurons and whole-organism experience do.

### 7. Whole brain, autonomy, memory, and fluid/body mechanisms

The requested whole brain is not fully operational and wired in live production. Do not repeat any prior claim that all 15 cognitive mechanisms are complete.

Outstanding required mechanisms include:

- always-on continuous sensory boundary with truthful quiescence;
- attention and float/surface thought dynamics;
- needs/homeostasis and controlled imbalance from substrate physics, not a scheduler;
- body/interoception and eventually a truthful VR body;
- major neurochemical/fluid flows with causal movement;
- short-, mid-, and long-term memory;
- mosaics, mosaics-of-mosaics, tapestries, tapestries-of-tapestries, and weaves as learned/emergent organizations, never forced labels;
- play, sleep, dreaming, consolidation, imagination, and autonomous exploration;
- emotion/empathy and intuitive/subconscious contribution;
- expression, mouth/face/body control, and eventual live camera/microphone embodiment;
- restored access to pictures, books, PDFs, sounds, music, and approved educational sources.

Legacy Chi/Atlas, scripted meaning, TTS-as-cognition, named sensory profiles, and duplicate legacy brain paths must remain excluded. Useful functions such as memory and autonomy must be rebuilt substrate-true rather than deleted from the organism.

### 8. Resource bounds and native transition

The candidate release contains the one-whole-organism persistence path and the Rust/native transition intended to replace tens of millions of Python ownership calls. That improvement is not live until task 829 or a successor is the production task.

Do not claim the runaway-call problem is resolved in production while task 817 remains live. After cutover, measure one real transition, Python-call count, CPU time, RAM, EFS growth, cold restore, and repeated sensory operation. There must be no million-scale control call count for a young substrate.

## Recommended agile delivery order

Only one increment should be active at a time, and each must be live-verified before beginning the next:

1. Replace the obsolete migration seal dependency and put the already-built unified-organism candidate into production.
2. Deploy and browser-verify the accepted Guala Loom page.
3. Deploy and browser-verify the truthful Loom Scan corrections.
4. Finish/catalog/deploy all 36 approved cards and their truthful visual/audio teaching surfaces.
5. Run brief varied multisensory tutoring with truthful live observation; look for an emergent first word without forcing one.
6. Continue hearing, autonomy, memory, fluid/body, play, dream, expression, and curriculum increments.

Do not combine these into another multi-day hidden release.

## Immediate next item

The single immediate item is production cutover of the unified organism without invoking task 817’s detached causal-mutation seal.

Do not rebuild task 829 unless code inside the image changes. If only the local deployment controller changes, reuse task definition 829 and digest `sha256:bbaab564...`. Dry-run the exact control transition against authenticated immutable generation identities, then perform the one cutover and verify live.

## Collaboration and communication constraints from the user

- Ask and collaborate before changing an accepted visual or curriculum design.
- Do not overcorrect by deleting good tutor/autonomy functions when a card or vision surface is wrong.
- Do not report internal unit tests as proof that Guala learned a word.
- Do not use confusing “current reality/conflict yes” prose; state what was tried, what failed, and why.
- Do not issue repeated approval prompts. Use the existing approved terminal/session path.
- Give visible, small production increments rather than hours of hidden work.
- The user is not a developer; provide direct clickable files/pages and plain-language status.
- Preserve learned state exactly and never fall back to the disconnected brain as the claimed solution.

## Operational notes

- Current shell/session work was performed in `/tmp/guala-release-20260731-hafnbk`.
- The checkout is detached at `2598cd7b`.
- The standard edit helper is broken because unprivileged namespaces are unavailable; prior work used the already-approved system `patch` utility in persistent terminal session `78818`.
- Avoid generating repeated “Allow once” prompts.
- No Slack connector is installed, so the project’s Slack completion ping could not be sent. The full goal is not complete.

