---
name: incident-response
description: Emergency and runaway-process discipline for Guala/TFE work — the binding incident order (containment, analysis, repair, restore, cleanup, documentation) AND the bench rules that stop MY OWN diagnostic work from becoming a second incident. Load the moment any alarm fires, any process runs away, any live system is contained, or before starting ANY soak/trace/census run on the shared machine.
---

# Incident response — established 2026-08-31/09-01 (the memory-runaway night)

## THE BINDING ORDER (Sol's, ratified by the incident; never reorder)
1. CONTAINMENT — stop the harm first. For production: drain to 0/0/0,
   verify zero writers, preserve state; never restart a task as a "fix".
   A known-old task definition is NOT an admissible rollback until its
   decoder has proven it reads the current body format (the 1400 rollback
   refused the V41 body; identity survived only because refusal-not-genesis
   protection held).
2. ANALYSIS — on copies, never on the patient. Prove cause; withdraw
   hypotheses in writing when the trace kills them. "Exact cause" means a
   named container/call path, not a factor.
3. REPAIR — smallest law-true fix; falsifier test written WITH it.
4. RESTORE — only after repeated bounded-life proof (windows well past the
   observed onset; the six-minute false plateau fooled everyone once) AND
   a newest-body cold restart. Restore proposals go through the ledger for
   the other lane's CONCUR first.
5. CLEANUP — every diagnostic container, process, volume, scratch bucket
   swept; evidence volumes retained read-only and named.
6. DOCUMENTATION — attempt history with failures preserved (rejected
   attempts stay recorded as rejected, never relabeled); ledger updated at
   every state change; controls/mitigations (alarms, auto-containment)
   updated last.

## MEASUREMENT TRUTHS (paid for in wasted hours)
- docker stats MemUsage includes file cache — custodian staging writes make
  healthy processes look like leaks. Judge by VmRSS from /proc.
- The PID you hold is probably a wrapper. `$!` after `env ... &`, docker
  inspect .State.Pid from another namespace, `pgrep | head -1` — all burned
  me tonight. Verify the PID's VmRSS is plausibly the real process (an
  organism is GBs, a wrapper is ~2MB) before trusting one sample.
- For containers: sample from INSIDE (`docker exec <c> awk '/VmRSS/...'
  /proc/1/status`).
- A flat line from a corpse proves nothing: verify boot (health 200, tick
  read) before sampling, and verify liveness again at the end.
- heaptrack names allocation SITES, never OWNERS; "leaked" includes
  everything alive at exit. Owner identification needs a census (count
  in/out on the suspect type) or a size probe (log container lens per beat
  — the cheapest and the one that found the keeper).
- Python-side retention shows up as native heap and hides from Rust-focused
  tracing; custody staying small while RSS grows means a resident-only,
  never-encoded container — look in the serving layer too.

## MY-OWN-PROCESS RULES (mandatory for every bench run)
- HARD CAP + AUTO-KILL on every soak/trace/census: --memory cap on
  containers, an explicit RSS threshold kill in every sampling loop, and a
  bounded iteration count. No unattended run without all three.
- KILL BY PID, NEVER BY PATTERN: `pkill -f <pattern>` matched my own shell
  twice tonight (the command text contains the pattern) and killed my own
  ledger write mid-commit. Find the PID in one command, kill it in the
  NEXT command.
- LAUNCH VIA SCRIPT FILES with `cd` baked in — I dropped the cd four
  consecutive times re-pasting an inline launch and ran the wrong code.
- REGISTER AND SWEEP: before ending any work block, list what you started
  (docker ps, ps aux | grep uvicorn) and stop everything not actively
  measuring. A 23GB forgotten process nearly took down the shared box and
  Sol's work with it.
- One heavyweight run per question. Parallel soaks compete for the box and
  contaminate each other's slopes.
- Scratch cloud resources (buckets, prefixes) are created named-for-the-
  incident and deleted at cleanup; NEVER point bench custody at the
  production mirror — the store's keys collide and its pruning deletes
  real backups.
- The kill-it-now order from Joe overrides any running measurement,
  always, immediately.

## VERDICT DISCIPLINE
- Call runs by SLOPE early (minutes) but gate ships by full windows.
- An invalid run is reported as invalid, never spun ("flat line from a
  corpse"). Method errors go in the ledger with the result.
- When your own fix fails its proof (v1 advancement filter), say so in
  the first sentence, kill the run, and state the corrected law.
