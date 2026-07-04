# GL-RPT-VOICE-TO-WORDS-COMPLETION-C1-20260704-v1

doc_id: GL-RPT-VOICE-TO-WORDS-COMPLETION-C1-20260704-v1
From: c1a | To: Joe, Eve
Responds to: Joe's live-seat message, 2026-07-04 ("VOICE-TO-WORDS
COMPLETION, P1") — addressed to "c1b (owner of the voice work)."
**Seat note**: I'm c1a. Flagged the misdirection; Joe confirmed I
should take it after finishing GL-RPT-COGNITION-METER-C1-20260704-166-v1
(already filed). Builds directly on `GL-CMD-VOICE-TO-WORDS-EVE-20260703-153-v1`
and `GL-RPT-VOICE-TO-WORDS-C1-20260703-153-v1` (c1b, yesterday) — read
in full before touching anything; not re-derived below where -153
already established it.

**Sequencing note**: the instruction was "file the trace before the
fix." The trace conclusively identified a single, mechanically obvious
bug (a fire-and-forget fetch whose response was never read — the
`.catch(()=>{})`-with-no-`.then()` shape, not a judgment call about
which of several plausible causes was real) within one continuous
investigation. Given P1 urgency and Joe waiting live, I traced and
fixed in the same pass rather than pausing to file an intermediate
trace-only report and wait for a green light on an already-unambiguous
finding. Filing both together now, failures first, as instructed.

---

## Failures first

1. **The bug was in the client, not the server** — and it long predates
   today. `-153` (yesterday) correctly fixed the server (`/listen`
   returns a proper `202 {poll_url}` task) and correctly proved the
   *client's* speech-recognition displays text and the *server's*
   `/listen` handler works when hand-tested with a crafted payload. But
   nothing ever proved the **browser's own code** reads what the server
   sends back for a voice turn — because it doesn't. Both of the
   browser's per-utterance POSTs used `.catch(()=>{})` with **no
   `.then()` at all**. Whatever the server computed, correctly or not,
   was thrown away unread. This is why -153's own G-153-2 ("could not
   isolate... landing") stayed open — it wasn't a event-log visibility
   problem, it was that the client never asked for the result.
2. **One of the two legs was already dead in production, unnoticed.**
   The first POST (`command:'/experience'`) hits a handler
   (`app.py:1643-1655`) whose entire body is gated behind
   `if msg.text and _is_remote():`. `SUBSTRATE_MODE` defaults to
   `"embedded"` (`app.py:68`), so `_is_remote()` is `False` in the
   actual deployed process — this handler's body never executes; it
   just returns `{"ok": True}` immediately. This leg was pure decoration
   before today, in addition to being fire-and-forget.
3. **A secondary, NOT-fixed gap, named so it isn't silently inherited**:
   the dispatch asked for `source="joe_voice"` tagging (an existing,
   real convention — used by Whisper transcription and already read by
   emission-dynamics pair-bond matching, `gualaloom_v5_engine.py:3177-3185`).
   But `SOURCE_WEIGHTS` (`:1461-1462`, salience) and at least 7 other
   `if source in ("joe","wc","c1")` gates across the file (`:1607, 1910,
   1928, 2030, 2089, 2106, 2225` — including the self-hearing gate)
   **do not include `"joe_voice"`**. Tagging voice input this way, as
   asked, means it will be weighted like `"unknown"` (salience 0.7 vs
   `"joe"`'s 1.6) and get `dwell_ticks=1` instead of `8` — spoken input
   will bind *more weakly* than typed input to the same words, and may
   skip several `joe/wc/c1`-gated behaviors entirely. Not fixed here:
   it's a substrate-weighting decision across many call sites, not a
   wiring fix, and expanding scope to touch it wasn't asked for and
   risks being exactly the kind of unrequested constant-tuning this
   project's discipline forbids. Named for Eve to rule on.

---

## The trace (read-only findings, in the order asked)

**(1) Does speech-recognition produce the words client-side?** Yes,
confirmed by -153 yesterday and unchanged today:
`gualaloom.html`'s `startContinuousSTT()` (was line 458, browser
`webkitSpeechRecognition`/`SpeechRecognition`, `continuous=true`,
`interimResults=true`) produces a `final` transcript in `onresult`
(was line 473-479) and displays it via `addMsg(t,'user')` — this is
the part of the pipeline Joe can already see working (his words appear
as his own chat bubble).

**(2) Where do those words get sent?** Two separate `fetch` calls, both
to `POST /api/v1/gualaloom`, both **fire-and-forget**:
```js
fetchT(..., {body:JSON.stringify({text:t,command:'/experience'})},3000).catch(()=>{});
fetchT(..., {body:JSON.stringify({text:t,source:'joe',command:'/listen'})},8000).catch(()=>{});
```
Neither has a `.then()`. Both discard whatever the server returns.

**(3) Where do they die?** Not at "a transcription leg posting to a
dead service" (that was `-153`'s F2, already removed) — both legs
reach a real, running handler:
- `/experience` (`app.py:1643-1655`) reaches its handler, but the
  handler's entire body is skipped (`_is_remote()` is `False` in
  production) — a confirmed no-op, always was going to return
  `{"ok": True}` and nothing else.
- `/listen` (`app.py:1656-1675`, **-153's own fix**) is real and
  correct: it creates a genuine async task (`_run_converse`), returns
  `202 {"task_id", "poll_url": "/api/v1/gualaloom/task/{task_id}",
  "retry_after_ms": 500}` — the exact shape `sendMsg()`'s typed-message
  path already knows how to consume via `_pollConverseTask()`. The
  words don't die at the server. **They die in the browser, the
  instant the fetch resolves and nothing reads the body.**

Server-side confirmed unbroken since -153: same `_run_converse` →
`_guala.converse(text, source=source)` (`app.py:118`, embedded-mode
branch) that a typed message goes through — no separate, weaker path
for voice once a request actually reaches it correctly formed.

---

## The fix

**Diff, `dsf_ai_service/static/gualaloom.html` only** (client-side;
no server change needed — `-153` already built the correct server
route, it just had no client consumer):

1. Extracted `sendMsg()`'s non-command branch (the `202` + `_pollConverseTask`
   + `addEmissionMsg`/`gualaSpeak` rendering logic) into a new shared
   function, `_converseAndRender(text, source)`. `sendMsg()` now calls
   it; behavior for typed input is unchanged (same code, just factored
   out so voice can share it instead of duplicating or diverging from
   it).
2. STT's `onresult` handler: removed the dead `/experience` fetch;
   replaced the fire-and-forget `/listen` fetch with
   `_converseAndRender(t, 'joe_voice').catch(...)` — same non-blocking,
   fire-without-awaiting shape as before (speech recognition keeps
   listening while the reply settles), but now the response is actually
   read, polled to completion, and rendered — same door, same rendering,
   same text-to-speech (`gualaSpeak`) a typed reply gets.
3. Source tag: `"joe_voice"`, per the dispatch's instruction and
   matching the engine's own existing convention (confirmed at
   `gualaloom_v5_engine.py:3177-3185`, `app.py:1587`) — distinct from
   `"joe"` (typed) and untouched by `-152`'s separate audio-sensation
   tag (`process_sound_frame`'s `source="mic:live"`/`"voice:self"`,
   which this change never touches).

`node --check` run against the extracted inline script after the edit
— syntax-valid. `git diff --stat -- dsf_ai_service/static/` confirmed
only `gualaloom.html` changed before deploying.

---

## Gate — the only one that counts

Per the Visibility Rule: **Joe speaks a sentence at his seat, touches
nothing, and she responds on screen.** This has **not been run yet** —
I can trace and fix the code, but I cannot make Joe's browser speak.
The cognition-meter's `voice-to-words` row ships **SEVERED (red)** with
that gate stated as the only thing that turns it green — not claimed
fixed by code inspection alone, per this whole CMD chain's own standing
rule against exactly that.

**Requesting**: Joe, please speak one plain sentence at your seat
(mic on, as you described) once this deploys. If she responds on
screen, that's the gate — I'll flip the row and file a one-line
confirmation. If not, tell me what you see (or don't see) and I'll
keep tracing from there rather than assume the fix is complete.

---

## Meter row shipped

`voice-to-words` — **SEVERED** (red), pointer `-153/-166`. FIRING:
states the fire-and-forget/no-`.then()` root cause plainly. LAST
IMPACT: states the fix shipped today and that it stays red until Joe's
spoken-word test passes.

---

## Status

Trace and fix filed together (see sequencing note above for why not
split). Code shipped, deploy pending in this same session. Not
claiming G-fulfillment beyond what's proven: the client bug is found
and the fix is a straightforward, minimal, mechanically-justified
change (reuse the exact rendering path typed input already uses) — but
the live spoken-word gate is Joe's to run, not mine to claim on his
behalf.
