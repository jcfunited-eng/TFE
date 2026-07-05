# GL-RPT-BOOK-VERIFY-AND-UPLOAD-ERROR-C1B-20260705-v1

doc_id: GL-RPT-BOOK-VERIFY-AND-UPLOAD-ERROR-C1B-20260705-v1
From: c1b | To: Eve, Joe, c1a | Responds to the three-item ask (no new
window). All three investigated directly against logs/events, not
guessed.

---

## 1) Book read verification — "secret_gardenl"

**Not read at all yet — and it is NOT what caused the atlas jump.**
Two separate things landed close together in time; I initially
conflated them too and want to correct that precisely rather than
leave it implied.

`corpus_added` event, tick 14889079 (2026-07-05T01:58:40Z): `{corpus_id:
"secret_gardenl", title: "Secret Gardenl", n_lines: 2204}` — this is
`add_corpus()` (`gualaloom_v5_engine.py:4506-4509`), which only
**registers** a corpus (a dict assignment, no lock, no reading). Actual
reading only happens later via the scheduled `READING` activity,
word-by-word, if/when it wins selection against the other candidate
kinds. **Searched the full event/log stream since registration: zero
`activity_started` events with `kind: READING, target: secret_gardenl`.**
Position/times_read_through: 0. Answer: **not at all** — registered,
not yet opened.

The atlas jump (7267→14890) that looked like it correlated is actually
the **curriculum scheduler's own separate feed mechanism**
(`substrate_runner._curriculum_feed_chunk`, `substrate_runner.py:346`)
studying *Grimms' Fairy Tales* (the `curriculum_studied` event at tick
14889220) plus worldfeed/lookup interleaving — this path calls
`read_sentence` directly, bypassing the `READING` activity entirely, so
it doesn't need to "win" scheduler selection at all. The two events
(corpus registration, curriculum study) landed 141 ticks apart purely
because both happened to fire in the same active window, not because
either caused the other.

## 2) Upload error — root-caused, not just described

**Confirmed: the upload itself works correctly.** Container logs show
exactly one `POST /api/v1/gualaloom/upload/book` in the relevant
window, and it returned **200 OK**, producing the `corpus_added` event
above (2204 lines, correctly decoded, correctly registered). `add_corpus()`
does no locking and no heavy work — there's no code-level bug in the
upload handler itself.

**What actually happened, timing-confirmed:** task:471 (window 7)
finished booting at tick **14889069** (`Booted: ... corpora=19` — before
the upload). The successful upload landed at tick **14889079** — **10
ticks (~3 real seconds) after boot completed.** That's tight enough
that Joe's *first* attempt almost certainly landed while the new task
was still coming up behind the ALB during the deploy's pause→restart
transition (old task paused, new task not yet registered/healthy) —
a request hitting that gap gets the load balancer's own error response
(classically HTML, exactly matching "Unexpected token '<'"), not
anything FastAPI ever saw or logged (which is why there's no failed
request in the container's own logs — it never reached the container).
The retry landed moments later once the new task was actually serving
traffic, and succeeded cleanly.

**This is the same class of gap `-182`'s L2 named for conversation
tasks** (a request landing exactly in a deploy's pause/restart window
gets an ungraceful failure) — except uploads have no equivalent
protection at all right now. Not a single file:line bug; the honest
answer is a structural gap in the deploy transition, same root
mechanism as `-182`'s finding, just for a different endpoint.

**Noting for c1a, per the ask:** the UI rendering this as tiny gray
text instead of a loud, clear failure is exactly the same class of
gap `-180`'s seat-truth work already fixed for conversation errors —
applying the same treatment to upload failures (and ideally an
auto-retry, since this class of failure is transient by nature) would
close it.

## 3) `/status` curated-subset fix

Folding into the next window payload as proposed: add
`"organism_population": s.get("organism_population", 0)` and
`"organism_worker": s.get("organism_worker", {})` to the response dict
app.py's embedded-mode `/status` handler builds (the `s = _guala.
introspect()` call already contains both — confirmed directly — the
handler just isn't forwarding them). One line each, no other changes
needed. Will include in whatever SHA fires next, not worth a dedicated
deploy on its own.

### Changelog
- v1 (2026-07-05, c1b): all three items closed. Book: registered, not
  read; atlas jump correctly attributed to the curriculum feed
  instead. Upload: root-caused as a deploy-transition timing gap
  (10-tick/~3s margin, confirmed against boot timestamp), not an
  application bug — same class as `-182`'s conversation-task finding,
  flagged for c1a's UI-honesty and retry consideration. Status fix:
  queued for the next window, not urgent enough alone.
