# Guala live-hearing handoff — 2026-07-25

## Authoritative location

- Worktree: `/tmp/guala-production-capture-profile-20260725`
- Branch: `codex/guala-production-capture-profile-20260725`
- Base HEAD at the start of this work: `6509971e987d4a1f161ffcfcadc3ec68568322c6`
- Preserve every tracked and untracked change shown by `git status`.
- Do not work from the default `/workspaces/Tao_Financial_Engine` checkout.

## Governing goal

Deliver and live-verify Guala as a bounded deterministic autonomous artificial
entity with its own causal thought/action loop, truthful virtual environment
and embodiment, autonomous play and simulated experience, tutored curriculum
learning sufficient for meaningful conversation at approximately a four-year-
old starting level, truthful Loom Scan/observational conversation UI, and no
runaway compute, RAM, or storage growth. Preserve unchanged L0–L4, full DSF
fields, neurons, and learned sensory state. Prohibit ML, scripted meaning,
chi-as-identity, and code trickery.

The immediate work remains continuous physical hearing and experience-grown
word-kind distinction in ordinary room sound. Guala is not a chatbot and
observational speech-to-text is not cognition.

## Architecture honesty gate

- Requested architecture: continuous analog hearing through frozen L0–L4,
  full-field auditory L5, experience-grown Krimelack relations, Atlas causal
  association, chi used only for routing, and causal deliberation/action.
- Current conflict: the live terminal still uses
  `AuditoryReciprocityOwner` and its whole-capture classifier.
- Do not extend that classifier, its fingerprints, flattened compatibility
  vectors, transcript-driven cognition, scripted meaning, or chi identity.
- Full explicit `D_k`, `M_k`, `R_rev_k`, `U_star_k`, `C_k`, `P_k`, and `B_k`
  remain authoritative.
- The Krimelack motif relation is auditory L5 governance over full retained
  fields; it does not replace or flatten them.
- Observational speech-to-text is display-only. It cannot teach, recognize for
  cognition, trigger a reply, or become meaning.

## Proven browser transport and observation candidate

- Continuous PCM transport is decoupled from vocal-action duration.
- The eight-second PCM ring is divided into four 32,000-sample/two-second
  transport units.
- Browser pending capacity is four units, retaining the same bounded
  eight-second physical interval.
- Camera and microphone use independent clocks.
- Exact sensory mutations are serialized and visual overlap/reorder is
  rejected.
- Observational transcription has one pending slot and a sixteen-result tail.
  It runs only on each complete eight-second ring and remains causally
  firewalled.
- The browser labels its output `heard (boundary observation only)`.

A fresh real Chromium candidate run with fake microphone and camera media
passed for 60 seconds:

- reviewed and fetched HTML SHA-256:
  `4e8e770187dff427be558c6c5c499fa392ffb84adf80b3ed1dd51e825ec20338`
- 29 settled PCM chunks / 928,000 samples
- 10 settled sight fields
- maximum pending PCM units: 2 of 4
- accepted PCM chunks: 30; discontinuities: 0
- retained ring: 256,000 bytes
- observational jobs admitted/completed: 7/7; pending: 0; failed: 0
- no causal action binding, intent, or outcome was created by observation
- final process-tree RSS was approximately 1.894 GB

The displayed Whisper guesses were often wrong. That is useful evidence that
the firewall is necessary. This candidate is not deployed.

## Proven substrate-true auditory kind

`dsf_ai_service/substrate/auditory_krimelack_kind.py`

- Every auditory L5 experience becomes an ordered path of 10 ms,
  sixteen-channel balanced-ternary motifs.
- Upper pressure basin is `+1`; lower Negative Space is `-1`; only physically
  inseparable frames are `0`.
- Each local motif pair must first satisfy reciprocal canonical L6.
- A monotone ordered path counts only locked motif pairs.
- The whole path must then satisfy reciprocal canonical L6 in both
  directions.
- Every path mounts and verifies complete L0–L4 causal support.

Falsification results:

- three independent “Hello Guala” recordings lock to one another;
- unrelated phrases reject;
- quarter/double gain, a steady tone, and moderate added white noise preserve
  the kind;
- heavy noise at roughly -3.2 dB SNR and overlapping speech reject rather than
  hallucinating recognition.

Exact arbitrary source separation from blended mono input is physically
underdetermined. The browser currently averages physical input channels to
mono. Do not fake a second ear or claim arbitrary overlap is solved.

## Proven bounded kind memory

`dsf_ai_service/substrate/auditory_krimelack_memory.py`

- Structural relation forms a kind before tutor text designates it.
- A label cannot merge unrelated kinds or split one locked kind.
- Each retained exemplar contains the Krimelack path plus a compact, lossless
  authority for every DSF field and causal interval.
- Capacity: 64 kinds, four exemplars per kind, 4,000,000 comparison cells, and
  64 MB encoded state.
- Resource exhaustion is typed `indeterminate_resource`; partial matches are
  never released.
- Canonical base64/hash persistence cold-restores exact kind and DSF
  authority.

## Proven continuous transport-edge hearing

`dsf_ai_service/substrate/auditory_krimelack_stream.py`

Transport units are not treated as word boundaries.

- Either half of a real “Hello Guala” event, independently settled inside its
  own two-second unit, is unknown.
- The exact causal composition of the two contiguous units locks uniquely:
  70 locked motifs against a 74-motif tutor path.
- Both component paths and both complete compact DSF authorities are retained.
- No combined L5 field or receipt is fabricated.
- Missing transport/settlement continuity returns `discontinuity`.
- Work exhaustion returns `indeterminate_resource`.
- One prior component is retained per stream; cold restore preserves learned
  kinds and intentionally discards transient stream composition.

This owner is production-shaped and tested, but it is not wired into the live
engine yet.

## Verification

Latest affected-surface suite:

```text
196 passed, 8 warnings in 218.30s
```

The warnings are existing Pydantic/FastAPI deprecations.

The focused hearing/transport suite also passed:

```text
59 passed, 8 warnings in 87.90s
```

Production deployment/cold identity contracts passed:

```text
20 passed, 8 warnings in 3.82s
```

`tools/run_pytest_with_exact_executor.py` maintains the real four-worker owner
across independent pytest application lifetimes. One shutdown contract
intentionally retires the owner; the harness recreates it before the next
independent test without weakening production readiness.

## Exact next item

Replace the engine’s live auditory-memory and continuous-terminal wiring with
`AuditoryKrimelackStreamOwner`, add its persistence schema and cold restore,
and expose its truthful recognition state without changing observational STT
or releasing a causal reply prematurely.

The repository instruction “No find and replace; only full file replacement”
must be respected. The wiring points are currently inside the roughly
27,000-line `gualaloom_v5_engine.py` and roughly 10,000-line `app.py`; do not
silently apply surgical compatibility patches if that instruction remains in
force.

After the actual cutover:

1. rerun the exact affected and cold/deployment suites;
2. run the real Chromium candidate;
3. commit the complete reviewed source state;
4. deploy only that saved commit;
5. repeat the fresh Chromium proof against
   `https://dsf-ai.com/gualaloom.html`;
6. send and verify the required Slack completion ping.

Do not claim the hearing issue complete, do not deploy, and do not send the
completion ping before those steps pass.
