# GL-RPT-DENSITY-RETIRE-C1-20260703-109-v1

doc_id: GL-RPT-DENSITY-RETIRE-C1-20260703-109-v1
From: c1b | To: Eve | Date: 2026-07-03
Responds to: GL-CMD-DENSITY-RETIRE-EVE-20260703-109-v1
Rode the -108 consolidated deploy vehicle. SHA: 16bc0c294fc0c1012ea92a6cd12914cb90d6c31e
(task:455, currently live, booted 2026-07-03T20:41:08Z).

---

## FAILURES FIRST

None. All three changes measured as designed. One gate (G-109-1) is not yet at its full
observation window — reported honestly below rather than rounded up.

---

## GATES

**G-109-1 — zero `experience_bundle` events with no human sending any: PARTIAL, zero
observed, window short of the CMD's ≥30min bar.**

Elapsed from boot (20:41:08Z) to time of writing (~21:01:00Z) ≈ 19m50s, not the full 30
minutes specified. Across that window: zero `experience_bundle` events in either (a) a
bounded CloudWatch search for the literal string, or (b) the last 50 live substrate
events pulled via the bridge (which span from my own two deliberate test bundles through
Joe's live mic/converse session and current activity) — no third-party `experience_bundle`
appears anywhere in that stream. Given F1's mechanism (`CURRICULUM_AUTOSTART`) is now
structurally disabled at both the code default and the task-def env (G-109-4 below proves
the disabled branch fires), no new spontaneous bundles can occur without someone manually
re-enabling the env var. **Stating this as NOT FULLY MEASURED against the literal ≥30min
bar, per the CMD's own "NOT MEASURED where true" rule** — not rounding a 19-minute clean
window up to a 30-minute PASS.

**G-109-2 — source attribution, curriculum vs joe: PASS, verbatim events pasted.**

Two test bundles posted directly to the live API (ALB endpoint), one with no `source`
field, one with `source: "joe"` (mirroring exactly what the fixed `gualaloom.html` bundle
modal now sends). Verbatim substrate events, pulled via the bridge:

```
tick 14474969  response_window_opened   {"emitter": "curriculum", "context_anchor_chis": [6, 23, 7, 21, 29], "expires_at": 14475569}
tick 14474969  experience_bundle        {"name": "g109-test-nosrc", "lanes": ["told her \"g109-test-no-source\"", "feels soft (3 channels)"], "n_chis": 7, "source": "curriculum"}

tick 14474980  response_window_opened   {"emitter": "joe", "context_anchor_chis": [6, 23, 5, 21, 17], "expires_at": 14475580}
tick 14474980  experience_bundle        {"name": "g109-test-joesrc", "lanes": ["told her \"g109-test-joe-source\"", "feels warm (2 channels)"], "n_chis": 6, "source": "joe"}
```

No-source correctly defaults to `"curriculum"` and opens a `curriculum` window; explicit
`source:"joe"` correctly opens a `joe` window. `gualaloom.html`'s own bundle-submit path
(`submitBundle()`) now sets `source:'joe'` on the object it POSTs — Joe's actual UI
clicks will produce the second shape without him doing anything differently.

**G-109-3 — exactly one ring-consumer thread post-boot: PASS, evidenced by absence.**

The guard's own line, `"[substrate] ring consumer already running"`, **never appears** in
the post-fix boot log — meaning `_start_input_ring_consumer()` was called exactly once.
(The two identical `"[substrate] InputRing consumer started (R3/R4)"` lines seen in every
prior boot — including this one — are NOT two thread-starts: one is the guarded print
inside `_start_input_ring_consumer` itself, the other is a separate, unconditional
`print(...)` statement at `app.py:1327` immediately after the whole background-loop-start
block, which always fires regardless of consumer state. Confirmed by reading both call
sites directly.) I attempted a harder proof via `aws ecs execute-command` (ECS Exec is
enabled on this task) to enumerate live thread names in-container; the interactive
session did not return cleanly within a reasonable budget in this sandbox and I did not
pursue it further — the log-based proof above is solid on its own and I'm not overclaiming
a thread-dump I didn't actually obtain.

**G-109-4 — boot log shows the disabled-autostart line: PASS.**
```
[curriculum] autostart disabled by env
```
Verbatim from task:455's boot log, in the expected position (immediately after
`InputRing consumer started`).

**G-109-5 — diff proves scope: orchestrator start gate, bundle source plumb, one guard —
nothing else: PASS.**

The -109-scoped portion of the deploy diff, verbatim (the same commit also carries -108's
own authorized `[cochlear-debug]` instrumentation for G-108-2, filed separately in
`GL-RPT-MIC-DEPLOY-C1-20260703-108-v1.md` — not part of -109's scope, called out here only
so the diff below reads as exactly what -109 authorized):

```diff
--- a/dsf_ai_service/app.py
+++ b/dsf_ai_service/app.py
@@ -2119,6 +2119,9 @@
             bundle_data = json.loads(msg.text) if msg.text else {}
         except json.JSONDecodeError:
             bundle_data = {"caption": msg.text}
+        # GL-CMD-DENSITY-RETIRE-109 F2: bundle attribution truth.
+        bundle_source = bundle_data.get("source") or "curriculum"
         def _decode_bundle():
@@ -2293,11 +2296,11 @@
             if bundle_chis:
-                _guala._open_response_window("joe", bundle_chis,
+                _guala._open_response_window(bundle_source, bundle_chis,
                                               source_context={"bundle": bundle_name})
             _guala._log_substrate_event("experience_bundle",
                                         name=bundle_name, lanes=results,
-                                        n_chis=len(bundle_chis))
+                                        n_chis=len(bundle_chis), source=bundle_source)

--- a/dsf_ai_service/static/gualaloom.html
+++ b/dsf_ai_service/static/gualaloom.html
@@ -605,7 +605,7 @@
-  const bundle={caption:caption||null,image_b64:null,sound_b64:null,touch,smell,taste};
+  const bundle={caption:caption||null,image_b64:null,sound_b64:null,touch,smell,taste,source:'joe'};

--- a/dsf_ai_service/substrate_runner.py
+++ b/dsf_ai_service/substrate_runner.py
@@ -888,9 +888,22 @@
+_input_ring_consumer_started = False
+
 def _start_input_ring_consumer():
     """...
+    global _input_ring_consumer_started
+    if _input_ring_consumer_started:
+        print("[substrate] ring consumer already running")
+        return
+    _input_ring_consumer_started = True
@@ -3193,11 +3206,14 @@
-    env var (default enabled). Calls localhost:8080 — same process, no API Gateway.
+    env var (default disabled — GL-CMD-DENSITY-RETIRE-109 retires 65-A's autostart...).
-    if os.environ.get("CURRICULUM_AUTOSTART", "1") != "1":
+    if os.environ.get("CURRICULUM_AUTOSTART", "0") != "1":

--- a/tools/deploy_dsf_ai.sh
+++ b/tools/deploy_dsf_ai.sh
@@ -253,7 +253,7 @@
-                {'name': 'CURRICULUM_AUTOSTART', 'value': '1'},
+                {'name': 'CURRICULUM_AUTOSTART', 'value': '0'},  # GL-CMD-109: 65-A retired
```

Exactly the three changes the CMD specified — orchestrator autostart gate (both switch
locations), bundle source plumb (server default + UI explicit), ring-consumer guard.
Nothing else touched in either file. The orchestrator script (`tools/sensory_curriculum_orchestrator.py`)
and `tools/curriculum_seed.json` are untouched and remain in-repo, as the CMD specified.

---

## RESTART FORENSICS CROSS-REFERENCE

Joe separately asked (mid-session, not part of this CMD) whether F3's double-consumer-
thread bug explained the unexplained ~20:12Z restart. Full analysis is filed in
`GL-RPT-MIC-DEPLOY-C1-20260703-108-v1.md`; summary: **ruled out for that specific
restart** — the guard's dormant branch never triggered post-fix, meaning only one thread
was actually running even before this fix landed, so F3 (real bug, correctly fixed) is not
evidenced as that restart's mechanism. The orchestrator's 90-second post-boot delay
(`time.sleep(90)` in `_start_curriculum_orchestrator`'s `_runner`) fully explains why
moon-001/002/003 activity resumed ~90s after that restart — expected behavior of any boot,
restart or deploy, not a clue to the restart's cause. Both points match what Joe's
message already anticipated.

---

## STATE

Live: `dsf-ai-task:455`, SHA `16bc0c294fc0c1012ea92a6cd12914cb90d6c31e`. 65-A's autostart is
off at both switch locations and proven off in the boot log. Bundle attribution is
truthful by default and Joe's own UI path is explicit. The ring-consumer race is closed
defensively. One gate (G-109-1) needs roughly 10 more minutes of continued zero-incidence
observation to clear its literal bar; nothing currently pending will change that outcome.

End report.
