# GL-CMD-MIC-DEPLOY-EVE-20260703-108-v1

doc_id: GL-CMD-MIC-DEPLOY-EVE-20260703-108-v1
From: Eve | To: c1b | Type: CMD — deploy + guards + static ship
E-signature declaration: E1/E2 enabler — Joe's live voice and music as a
  real sound lane (highest-bond presence gaining a sensory channel, P4).
Substrate-truth declaration: decode plumbing only; no cognition-path
  changes; adds two log lines (one decode-failure guard, one XFF
  admin-access line per the -105 spec that never landed — Deploy 3
  confirmed FAIL). No constants.

## Step 0 — durability
Commit THIS file verbatim to docs/ before implementing.

## Context
The 332537d mic fix (WebM → ffmpeg → WAV → cochlear) is on origin but
has never provably run: no substrate redeploy since, and the boot banner
is the only witness. Until then Joe's voice arrives as noise (raw WebM
misread as 8-bit PCM still fires cochlear bands — events cannot
discriminate). Separately: loomscan statics never synced (center stuck
at "tick 0"), and its "back to guala" link carries the same root-sync
404 c1a found on the forward link (Deploy 3 report, read-only note).

## Part A — code amendments (small, pre-deploy)
A.1 substrate_runner.py sound_window branch: add the missing else on the
    ffmpeg-output check — decode failures must be visible:
      else:
          print(f"[sound] cochlear decode failed: ffmpeg produced "
                f"{len(_ff.stdout)} bytes from {len(audio_bytes)} in")
    Closes the silent-skip class (§9.2): quiet codec failure currently
    drops the cochlear call with zero telemetry.
A.2 app.py: the [admin-access] XFF log one-liner per the -105 spec
    (Deploy 3 gate confirmed it never landed; app.py was untouched in
    cb79cbc..1b5eca8). This deploy is the vehicle.

## Part B — substrate redeploy
B.1 Deploy at the amended SHA using the FIXED deploy script only
    (post-f3304da; verify the task env key matches .env — the rotation
    must hold, same check c1a ran on :453).
B.2 Paste the boot banner ([build] line / BUILD_INFO) VERBATIM in the
    report. This is the witness that the mic code is running.

## Part C — static ship
C.1 S3 sync loomscan.html (tick fallback-chain fix, 332537d).
C.2 Fix the "back to guala" link (same class as c1a's forward-link fix);
    sync.
C.3 Verify from the public URL: page source contains the new tick
    fallback chain; both links resolve 200.

## Gates (report, failures first, NOT MEASURED where true)
G-108-1  Boot banner SHA pasted verbatim; equals the amended commit.
G-108-2  Live voice discrimination: with Joe speaking into the mic,
         capture the cochlear band pattern for a spoken window AND for a
         silence/room-tone window (per-band n_events from the engine or
         a temporary debug print — NOT just sound_frame_bound counts).
         Speech must show band-differentiated structure vs silence. If
         the two are indistinguishable → FAIL, stop, report verbatim, no
         live iteration.
G-108-3  Loomscan center shows a live tick from the public URL; both
         nav links resolve.
G-108-4  Decode-failure guard proven firable (one deliberately corrupt
         chunk through a test path), or NOT MEASURED stated plainly.
G-108-5  Rotation held: task env key equals .env value post-deploy.

Joe's part of G-108-2: speak a few sentences into the mic when c1b
signals ready. That is the whole ask.

### Changelog
- v1 (2026-07-03, Eve): initial. Consolidates mic redeploy, silent-skip
  guard, XFF landing, and static fixes into one vehicle.
