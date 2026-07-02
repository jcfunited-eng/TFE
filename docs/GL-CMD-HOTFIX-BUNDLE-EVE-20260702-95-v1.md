# GL-CMD-HOTFIX-BUNDLE-EVE-20260702-95-v1

(Verbatim Eve CMD, as received via Joe relay 2026-07-02. Committed for record-keeping by c1a.)

---

c1a — GL-CMD-HOTFIX-BUNDLE-EVE-20260702-95-v1 — Deploy 1, single deploy.
E-signature: E3 restored (attend gauge), rhythm protection (§8 stab).
Substrate-truth: no constants; one broken state transition fixed; exception
containment; build-identity stamp. Protocol: commit → Eve reads full diff →
GO → sleep_for_deploy on her wake cycle.

BUNDLE CONTENTS (nothing else rides):
1. 842b1db — already committed, already diff-read by Eve. Rides as-is.
2. -91.A containment: wrap _save_wave_atlas at all five call sites
   (app.py:2942, 4116, 4185; engine:5731, 6837) — log "[wave] save failed
   (non-fatal):" and continue. Move save_count += 1 ahead of the wave block.
   snapshot_state must copy files even if wave throws. SIGTERM path must
   reach sys.exit(0) regardless.
3. -90 attend-mark fix as c1b rooted it: pic.times_attended += 1 moves into
   the `if not _viewed:` first-tick block; familiarity update stays at
   session end. Cite engine file:line in the commit message.
4. Build identity: bake git SHA into the image (LABEL + /BUILD_INFO file)
   and print it in the boot banner. Today's task-identity dispute never
   happens again.
PRE-DEPLOY (out-of-band, before task swap):
5. IAM: add s3:PutLifecycleConfiguration to dsf-ai-task-role (confirmed
   missing at boot, -93 item 3). ssmmessages perms for ECS exec: staged
   but NOT applied until Joe approves in chat.
ONE FORENSIC GREP (record-keeping): pull the log lines surrounding the
19:11:29/19:11:31 npz ENOENTs — name the caller. Eve's jam model predicted
[save] prints would stop; they didn't. The record gets the real mechanism.
RUNBOOK (from -91.D): expect the OLD code's shutdown wave-save to throw
once during this deploy — verify the final core save landed (gauge + S3
hourly) before the swap; .sleeping marker absence expected this once.
T-GATES: boot banner SHA == HEAD; wave_atlas.npz EXISTS on EFS after the
first do_wave save AND loads on next boot; [save] shows wave=Xs that cycle;
zero npz ENOENTs in 2h; a HEIC times_attended increments on the FIRST tick
of the next ATTENDING_VISUAL; post-restart count-diff filed (standing rule).
Report: docs/GL-RPT-HOTFIX-BUNDLE-C1-20260702-95-v1.md — failures first.
