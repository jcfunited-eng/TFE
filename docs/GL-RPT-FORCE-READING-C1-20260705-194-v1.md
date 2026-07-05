# GL-RPT-FORCE-READING-C1-20260705-194-v1

doc_id: GL-RPT-FORCE-READING-C1-20260705-194-v1
From: c1a | To: Eve, Joe, c1b | Responds to: Joe's direct order
("sure build that" — the force-READING admin hook flagged as a standing
build item in `GL-HANDOFF-C1B-20260705-v1`, blocking `-188`'s X3).

## The build

`admin_force_reading()` (`app.py`) + `handle_force_reading()`
(`substrate_runner.py`, registered in `OP_HANDLERS`) — mirrors
`admin_force_dream`/`handle_force_dream` exactly. No new mechanism:
`_select_next_activity()` already checks `_force_next_activity` first,
pre-empting natural candidate scoring (built for the `SLEEPING`
override, reused as-is for `READING`).

`POST /api/v1/gualaloom/admin/force_reading` with
`{"corpus_id": "..."}` (exact) or `{"title_contains": "secret
garden"}` (substring, case-insensitive) — resolves against
`_guala._corpora`, sets `_force_next_activity = ("READING", target)`,
ends any current activity, logs `force_reading_initiated`. 404 with
the full list of available corpora if nothing matches (so the caller
can see the real registered `corpus_id`/title instead of guessing).

## Verified directly

End-to-end: `add_corpus("secret_gardenl", "The Secret Garden", [...
real sentences with "garden"/"moor"...])` → force → one
`_atick_reading` tick → `introspect()["scene_lanes"]` shows
`{'place': ['garden'], 'ambient': []}` — the forced read actually goes
through `read_sentence()` (unchanged from natural rotation's own
call), so `-188`'s scene-lane derivation applies identically whether
the corpus was chosen by her or forced by this hook.

Full `test_brain`/`test_neuron` suite: 23/23. `probe_188_scene_lanes.py`:
4/4 (unaffected — this hook doesn't touch anything scene-lane-internal).
`py_compile` clean on both touched files.

## Not yet confirmed live

The exact live `corpus_id` for Joe's Secret Garden upload — c1b's
handoff named it `secret_gardenl` but that was reading a status field,
not something I verified independently. First live call should pass
`title_contains: "secret garden"` (robust to the exact id) or, if that
404s, read the `available` list the endpoint returns and use the real
`corpus_id` from that.

### Changelog
- v1 (2026-07-05, c1a): built + verified locally per Joe's direct
  order following the `-188` scene-lanes report. Deploying alongside.
