# Guala memory-runaway repair attempt 01 — 2026-08-31

Status: `CAUSE_AND_EXACT_COPIED_BODY_ALLOCATOR_BOUNDARY_PROVED_CANDIDATE_NOT_BUILT`

## Immutable scope

- Production source: `bdd7c001333ae497756f1cea67f113c74383dc90`.
- Production image: `sha256:f6cacca867283e1b3f32657e86964938350c9b425ee00cf36ec3d57522f21904`.
- Production task definition: `dsf-ai-task:1402`.
- Organism identity: `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`.
- L0-L4, full joint seven-field DSF delivery, neurons, learned state,
  sensory state, and organism identity are immutable.
- No speech or environment cutover is permitted during this incident.
- Observation remains read-only and cannot pause, restart, or govern the
  organism.

## Live incident evidence

CloudWatch entered ALARM at 2026-08-31 21:22:57 UTC after three five-minute
averages above 85%: 85.0763%, 90.4921%, and 95.9926%. ECS replaced the task
at 21:21 UTC; the alarm subsequently returned to OK only because the new
process began from low RSS.

The stopped task `5d77fea0e4bb48bca1205bed98d5090c` was explicitly killed with
exit 137 and `OutOfMemoryError: container killed due to memory usage`. The
task limit is 16,384 MiB. Task 1402 repeatedly climbs to the limit and is
replaced.

The current replacement had these read-only `/proc/1` observations:

| UTC | VmRSS | RssAnon | VmData | attribution |
|---|---:|---:|---:|---|
| 21:54:58 | 7,976,076 KiB | 7,936,432 KiB | 8,311,652 KiB | PID 1 Uvicorn |
| 21:55:14 | 8,139,036 KiB | 8,099,392 KiB | 8,311,652 KiB | 8,099,912 KiB private anonymous PSS |
| 22:03:23 | 9,505,740 KiB | 9,466,096 KiB | 9,679,132 KiB | 9,065,936 KiB anonymous mappings |

There is one organism process and no growing child. This excludes ECS agent
memory, filesystem cache, the browser observer, and a separate worker.

The public organism body remained about 107.5 MB while process RSS grew:
tick 357744, state bytes 107,538,216, identity unchanged. The failure is
process-resident working memory, not persisted-body cardinality.

## Independent copied-body reproduction

Claude reproduced the incident from a private tick-356896 copy with no
external visitors: VmRSS reached 24,336,372 KiB in about 73 minutes. Contacts,
future scheduled contacts, and persisted body size remained bounded. This
proves unattended lived intervals are sufficient.

Claude also proved `InFlightAcousticConsequence` is not itself an unbounded
container: construction and concatenation enforce
`MAX_IN_FLIGHT_ACOUSTIC_SAMPLES`.

Sol's controls use the same immutable source body volume
`guala_glottal_proof_356896_IGGkvC`, cloned into separate writable volumes.
The source body identity, tick, neurons, formations, contacts, and body state
were already copied and hashed in speech repair attempt 34. These controls do
not write the source volume or production.

## Hypothesis history

### H1 — observer or request accumulation

Rejected. The isolated copy grows without visitors. Production growth is PID
1 private anonymous memory, and the observer has no mutation path.

### H2 — persisted cognition or structural graph runaway

Rejected for this incident shape. Persisted body bytes remain near 107.5 MB;
live contact and scheduled-event counts remain stable; restart removes the
RAM growth while restoring the same identity and current body.

### H3 — unbounded in-flight acoustic buffer

Rejected. The buffer has an enforced sample cap in both construction and
`followed_by`. Its presence increases work but cannot explain unbounded
buffer cardinality.

### H4 — one never-ending accumulated observation vector

Rejected after source tracing. `build_admitted_trajectory` starts a new local
aggregate on every call and installs only that call's observation into the
new unsealed state. The open trajectory boundary is architecturally relevant,
but the observation vectors are replaced rather than appended process-wide.

### H5 — off-lock checkpoint snapshot is the necessary leak

Rejected by copied-body control. With
`GUALA_CHECKPOINT_EVERY_INTERVALS=1000000`, the copy performed zero custodian
checkpoints and still grew from about 682,512 KiB RSS to 1,514,888 KiB RSS in
22 lived intervals. Repeated per-interval working allocation is sufficient.

### H6 — freed native/Python allocator pages remain resident after each
high-allocation lived interval

Active and supported, not yet the final repair. A copied body with a
process-local two-second `malloc_trim(0)` diagnostic reached a 1,129,352 KiB
high-water mark and fell to 786,184 KiB RSS after freed pages were returned.
At 37 lived intervals it was 1,302,664 KiB RSS versus 1,514,888 KiB after only
22 intervals in the no-custodian/no-trim control. This proves a material
allocator-retention component, but the manual trim thread is diagnostic only
and is not an accepted production design.

### H7 — continuous vocal/self-hearing activity is the accelerator

Active and supported. Task 1400 rose much more slowly: about 7.7% to 17.7%
over roughly 3.5 hours. Task 1402 rises roughly 190 MB/minute and carries the
fixed vocal consequence across unattended intervals. The acoustic body is
bounded, but it causes additional lived cochlear/body work and much larger
per-interval transient allocations. This distinguishes an accelerator from
an unbounded acoustic container.

### H8 — conventional leaked allocation

Rejected. A clean heaptrack trace exited normally after 183.70 seconds and
reported 69,349,488 allocation calls, 1.00 GB peak heap, 1.54 GB peak RSS,
but only 3.62 MB still leaked. A second checkpoint-suppressed trace covered
46 unattended intervals and reported 13,843,229 allocation calls, 323.71 MB
peak heap, 528.30 MB peak RSS, and 3.60 MB leaked. The fatal live shape is
freed-page retention after extreme exact-arithmetic churn, not a conventional
growing set of live allocations.

The checkpoint-suppressed trace attributed recurring work to the native
joint-source parser, exact BigInt/BigRational operations, full-field
conversion, topology preparation, and cognitive energy summaries. The one
shutdown checkpoint separately exercised the 107 MB body encoder. No DSF
field, neuron, or retained formation was flattened or removed.

### H9 — the fixed vocal consequence renews the expensive self-hearing path

Confirmed as the accelerator. The exact copied production body reached a
steady `hop_count=17` for one nominal 250 ms unattended interval. The
in-flight byte container was consumed, but its self-hearing transition caused
another fixed glottal discharge, so the next interval again carried a full
17-hop acoustic consequence. One measured interval took 49,399.6 ms, of which
9,013.0 ms was native settlement and 40,151.3 ms remained outside the named
transport stages. Thus the byte container is bounded while the physical
feedback is self-renewing. This is both a compute accelerator and the source
of repeated high transient heap peaks.

## Exact copied-production-body correction

The former volume named `guala_glottal_proof_356896_IGGkvC` remains a useful
older copy, but it was not accepted as the incident's current-production
proof. An initial disposable restore test also omitted
`GUALA_NATIVE_ORGANISM_ROOT`; the application therefore created a tick-0 body
at its default path instead of reading the mounted copy. That harness result
is rejected and must never be cited as organism loss.

The accepted copy was streamed read-only from the running task without
pausing or writing it: `CURRENT` and `world.glworld` came through ECS Exec,
and the two CURRENT-referenced immutable generation bodies came from the S3
object mirror. Canonical pointer parsing proved:

- identity `1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1`;
- tick `357918`;
- state bytes `107,538,168`;
- state SHA-256
  `3c064c56d9099dbf0f7f96d72e56a16fedc8ea9e02cf21e7c5160a0cd3ea2c45`;
- predecessor
  `ea9a3d6107488a9f3935467a4987fc9e5ba25f234e65e3d788d1d2ef02a6c9a8`;
- exact production image
  `sha256:f6cacca867283e1b3f32657e86964938350c9b425ee00cf36ec3d57522f21904`.

Cold restore of that copy reported the same tick and state hash, 1,812
retained neurons, 153 mosaics, and articulated-body SHA-256
`59a4821137f216d90b674b52702f543268faff89839e9edef33b7d6596690871`.

## Bounded allocator-return proof on the exact copy

The exact production image was run with jemalloc as the process allocator,
one arena, no retained virtual extents, and zero dirty/muzzy decay. No
organism code or body field changed. Once the 17-hop acoustic feedback regime
was reached, RSS samples across lived intervals 21 through 24 were 2.215,
2.265, 2.203, 2.641, and 2.323 GiB: a repeating working band rather than the
former monotonic climb to the 6 GiB control limit. The process completed
ordinary native transitions and repeated four-interval custody throughout.

The control exited normally (`exit=0`, `OOMKilled=false`). Its newest CURRENT
was tick `358012`, 107,639,912 bytes, SHA-256
`818d002f40c1a50b22b46987813d41378fbe4077cc0e46565b328405959b356b`.
A new process using the exact production image and `CURRENT_only` restore
returned that exact tick, hash, byte count, identity, 1,812 neurons, and 153
mosaics. No previous body was recovered.

This proves the allocator-return boundary independently. It does not excuse
the 17-hop self-renewing vocal feedback; the candidate must also replace that
legacy fixed consequence with a finite non-renewing physical discharge while
preserving audible pressure and self-hearing.

## Causal-impact boundary before repair

Any accepted repair must prove all of the following on an exact body copy:

1. same organism identity, predecessor tick, neurons, contacts, formations,
   full DSF fields, learned sensory state, articulated body, and world;
2. ordinary unattended thought/action physics continues rather than being
   paused to hide RSS growth;
3. emitted pressure and exact self-hearing remain bounded physical state;
4. four-interval durable custody remains current-only and cold-restorable;
5. repeated lived intervals reach an RSS plateau below the task ceiling;
6. restart restores the newest published body rather than an older body;
7. no observer, timer, phoneme, word, TTS, semantic table, or Python cognition
   authority enters the organism;
8. the repair removes the causal allocation pattern or establishes an exact
   allocator-return law; it may not merely restart the task before OOM.

No production mutation is authorized by this document. Causal analysis and
the exact copied-body allocator proof are complete. Candidate construction
may now begin from the exact production source, followed by a combined copied-
body proof of finite pressure, self-hearing, bounded RSS, custody, and cold
restart before any cutover.
