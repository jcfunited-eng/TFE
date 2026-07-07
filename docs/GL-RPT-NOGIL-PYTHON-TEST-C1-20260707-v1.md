# GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v1

**doc_id:** GL-RPT-NOGIL-PYTHON-TEST-C1-20260707-v1
**From:** c1
**Executing:** GL-CMD-NOGIL-PYTHON-TEST-EVE-20260707-v1
**To:** Eve (routing per dispatch instruction — no questions to Joe in this doc)

**HALT at BUILD step 1, the dispatch's own named halt condition.** Critical
dependencies lack free-threading wheel support for Python 3.13 specifically.
No container was built, nothing pushed to ECR, no test ECS service, task-def,
or ALB target group was created — the dependency check is a fast, local,
zero-infrastructure gate, and it fails cleanly before any of that becomes
necessary. Production untouched.

---

## Container build result + dependency compatibility

Read `dsf_ai_service/Dockerfile` for the real, current production dependency
list (`fastapi uvicorn python-multipart numpy pandas cryptography Pillow
pillow-heif PyMuPDF boto3 onnxruntime websockets faster-whisper`, base image
`python:3.11-slim`). Checked each C-extension dependency's actual published
wheels on PyPI directly (not assumed, not guessed) for `cp313t` tags — the
free-threaded Python 3.13 ABI marker — across their latest releases, and for
`numpy` specifically across its *entire* release history in case the latest
version had simply dropped a tag other versions still carried:

| Package | cp313 (regular) | cp313t (free-threaded) | cp314t (free-threaded) |
|---|---|---|---|
| **numpy** 2.5.1 | yes | **no** | yes |
| **Pillow** 12.3.0 | yes | **no** | yes |
| **pillow-heif** 1.4.0 | yes | **no** | yes |
| **PyMuPDF** 1.28.0 | abi3 only* | **no** | yes |
| **cryptography** 49.0.0 | abi3 only* | **no** | yes |
| **ctranslate2** 4.8.1 (faster-whisper's real compute engine) | yes | **no** | yes |
| **tokenizers** 0.23.1 | abi3 only* | **no** | **no** (not even 3.14) |
| **onnxruntime** 1.27.0 | yes | **yes** | yes |
| fastapi / uvicorn / python-multipart / boto3 | pure Python, no C extension — not a concern either way | | |

*abi3 = built against the CPython stable ABI, explicitly does **not** work
under a free-threaded interpreter (the free-threaded ABI differs at the C
level, particularly around reference counting) — these packages have no
usable prebuilt wheel for 3.13t regardless of the abi3 tag's version floor.

**`numpy` specifically**: checked all 250+ `cp313t` wheels ever published
across its full release history — they exist, but only up to the ~2.1.x–2.4.x
generation. The *current* release line has dropped `cp313t` entirely in favor
of `cp314t`. Downgrading numpy alone wouldn't rescue this dispatch anyway,
since Pillow/pillow-heif/PyMuPDF/cryptography/ctranslate2 never published
`cp313t` wheels at *any* version — this isn't a "pin older" fix, the ecosystem
support genuinely isn't there for 3.13 specifically.

**The pattern is consistent and telling**: six of seven checked C-extension
dependencies publish `cp314t` wheels already, while none publish `cp313t`.
Python 3.13's free-threading build was the PEP 703 preview/experimental
target; 3.14 is where free-threading became the more official, actively-
supported target, and the major C-extension projects appear to have moved
their free-threading investment there directly, largely skipping stable 3.13t
wheel support.

**This is a direct, clean match to the dispatch's own halt condition**:
"Critical dependency missing free-threading support... Halt with package name
if any critical dep missing." Naming the most critical one specifically:
**`numpy`** — used pervasively across the entire substrate's numeric/array
code (confirmed directly in `tools/wave_spillover.py`'s phase-vector math
alone, and it is foundational well beyond that file), with zero `cp313t`
wheel support in any current, actively-maintained release line. Multiple other
named packages (`Pillow`, `pillow-heif`, `PyMuPDF`, `cryptography`,
`ctranslate2`) share the identical gap.

Building any of these six from source against the free-threaded ABI is a real
possibility in principle, but is a substantially larger, riskier undertaking
than a wheel-availability check — untested build toolchains, no upstream CI
validating the combination, and no confidence the resulting binaries are
actually correct under free-threading (several of these projects, e.g. numpy,
explicitly gate `cp313t` support behind additional internal work beyond just
"compiles" — thread-safety of internal C state that a same-version `cp313`
build was never audited for). That is new engineering work, not a
measurement-only container build, and squarely outside this dispatch's DO-NOT
list ("Modify substrate code to make it work under no-GIL" — building deps
from source isn't a substrate-code change, but it's the same order of
open-ended risk that clause is guarding against).

## Test deploy result

Not attempted — blocked upstream by the dependency gate. No image built, no
ECR push, no ECS service/task-def/ALB target group created.

## Boot check result

Not attempted (no container exists to boot).

## Harness scenarios pass/fail + event count comparison

Not attempted (no test service exists to run scenarios against).

## Contention: `_autonomy_tick` fresh + loaded, amplification factor, word queue behavior

Not measured — this dispatch never reached the point where a no-GIL Python
process existed to measure. Worth stating directly for Eve's benefit: the
*reason* this measurement would have mattered is now doubly corroborated by
two other dispatches completed earlier tonight (`GL-RPT-BINDING-WINDOW-C-PORT-
BUILD-C1-20260707-v1` and `GL-RPT-WAVE-ATLAS-C-PORT-PHASE1-C1-20260707-v1`),
both of which independently found the same signature: concurrent, frequent,
short calls across the GIL boundary collapse in throughput under real thread
contention, consistent with GIL-crossing/reacquisition overhead rather than
any specific mutex or algorithm design. A genuinely GIL-free interpreter is
the most direct test of whether that finding is fundamental (would disappear
under free-threading) or specific to the ctypes-crossing mechanism those two
dispatches used (might not, if the bottleneck turns out to be elsewhere in the
interpreter's own threading machinery) — this dispatch was designed to answer
exactly that, and still should, once the dependency question is resolved one
way or another.

## Recommendation: cannot GO/NO-GO on the no-GIL fix itself — routing a scoping decision to Eve

Two concrete paths forward, neither built here (both are re-scoping decisions
for Eve, not something to decide unilaterally under "route to Eve"):

1. **Re-target Python 3.14t instead of 3.13t.** Six of seven checked
   dependencies already publish `cp314t` wheels cleanly (only `tokenizers`
   doesn't, and it's unclear yet whether `faster-whisper`'s actual runtime
   path exercises `tokenizers` in a way that would block boot — untested,
   would need to be checked as this path's own first step). This looks like
   a substantially more viable target than 3.13t as of today, given the
   ecosystem's own free-threading investment is concentrated there. Same
   dispatch shape, same halt conditions, same measurement goal — just a
   newer interpreter target.
2. **Build the missing wheels from source against 3.13t.** Possible in
   principle, but real, open-ended engineering risk (untested toolchains, no
   upstream validation of thread-safety under free-threading for these
   specific C extensions) that doesn't fit a measurement-only dispatch.

Given tonight's two prior findings already point at GIL-crossing overhead as
a real, corroborated mechanism, I'd lean toward path 1 being worth a fast
follow-up dispatch — the dependency landscape genuinely favors it — but that's
Eve's call, not mine to make unilaterally.

## Scope compliance

No substrate code modified. No container built. No image pushed. No AWS
infrastructure (ECS service, task-def, ALB target group) created. No
correctness harness run (nothing to run it against). No deploy of any kind —
production is fully untouched, exactly as it was before this dispatch.

---

### Changelog
- v1 (2026-07-07, c1): Halted at the dependency-compatibility gate (BUILD step
  1), the dispatch's own named halt condition. `numpy`, `Pillow`,
  `pillow-heif`, `PyMuPDF`, `cryptography`, and `ctranslate2` all lack
  `cp313t` (free-threaded Python 3.13) wheels in any current release; the
  ecosystem has moved free-threading wheel support to `cp314t` instead.
  Recommend Eve consider re-scoping to Python 3.14t, where dependency
  coverage is substantially better, as a fast follow-up.
