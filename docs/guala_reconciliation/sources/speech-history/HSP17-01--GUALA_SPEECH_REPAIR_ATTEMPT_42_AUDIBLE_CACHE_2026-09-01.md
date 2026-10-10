# Guala speech repair attempt 42 — retain the proven audible pressure

Production source before this repair: task 1407, commit
`3c353a6c26b2b7f13d805d80013e4f982a562ac1`. Task 1407 live-proved the
attempt-41 hop boundary: one 4,000-sample emitted pressure returned on exactly
one successor hop through all 34 ears. The identical pressure nevertheless
returned HTTP 404 from the playback endpoint seconds later.

## Exact cause and prior history

Commit `562208344559fed9f2e2f3c4c3e398a918ac8e28` introduced cross-request
self-hearing before exact hop-local selection existed. It appended every
consumed in-flight acoustic pressure to the human-listening cache. Attempt 41
now selects and stores the exact emitted hop directly, making that older cache
write redundant.

The live unattended and browser-fed process continued consuming later
pressures. Those non-articulation entries displaced the last proven emitted
pressure from the four-entry bounded cache in about one second. The durable
observer still truthfully reported its last proven articulation, but the
process-local PCM body named by that report no longer existed, so the page
could not activate audible playback.

## Exact bounded repair and impact

The cache now changes only when a selected native articulation supplies its
exact emitted PCM body. A later quiet or self-hearing-only intake leaves the
cache unchanged. The public observer and WAV endpoint both locate the body by
the articulation's exact SHA-256 within the bounded history rather than
assuming it occupies the newest slot.

The cache remains count-bounded to four entries, byte-bounded per entry, and
byte-bounded in total. It is process-local, replace-only observation state. It
does not enter the organism, hearing, action, cognition, persistence, world,
or timing law. Restart clears it and cannot replay an old discharge. No L0-L4,
DSF, neuron, motor, vocal-body, cochlear, or learned state changes.

Falsifiers require a non-articulation intake to preserve the prior exact PCM,
require a matching articulation to remain discoverable behind a newer cache
entry, and retain the existing count/byte limits and wrong-hash rejection.

## Local test record before copied-body proof

The direct pressure, live audiovisual capture, and no-ML/TTS set passed 19/19.
The broader speech/UI command produced five failures and three fixture errors;
the identical command on deployed task-1407 commit `3c353a6c` produced the
exact same named eight failures. Four are the pre-existing held-contact tutor
fixture defect and four require a TypeScript package absent from both local
worktrees. The candidate had 32 passing tests versus the baseline's 30 because
of its two new cache falsifiers. No new failure was accepted.

Two harness errors are also retained. The first command named a nonexistent
`tests/test_native_articulatory_physics.py`, so pytest ran zero tests. The first
baseline comparison requested a not-yet-created working directory and the
process did not start. Both commands were corrected without changing source.
