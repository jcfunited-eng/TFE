# GL-RPT-TEACHER-CORRECTION-DEPLOY-C1-20260620-01

Ref: GL-CMD-TEACHER-CORRECTION-UI-EVE-20260619-60 / GL-CMD-67 (deploy)
Phase: Deploy + V2/V3 verification
Status: COMPLETE — task:224 stable, feature verified

---

## Deploy summary

Three deploy cycles were required to restore her accumulated state (vocab=2822).

| Task | Commit | Issue | Outcome |
|---|---|---|---|
| :221 | 5b0d52c | EFS JSON parse error (guala_core.json corrupt) | load failed |
| :222 | 7dcb24e (S3 auto-restore) | Schema v7.2.0 not in COMPATIBLE_SCHEMAS | S3 restore blocked |
| :223 | 62b9892 (allowlist fix + richest-backup preference) | S3 restore returned seed state (vocab=20, from prior seed-state deploys that polluted backup) | vocab=20 on load |
| :224 | 204c610 (seed-state detection: vocab<100 triggers restore) | — | **vocab=2822 restored** |

Final image: `418384447921.dkr.ecr.us-east-1.amazonaws.com/dsf-ai:deploy-20260620T143404Z`

---

## V2 — Identity triple

```
id: cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f
schema: v7.2.0
vocab: 2822
```

All three match expected. Schema bumped from v7.1.0 to v7.2.0 as planned (teacher correction persistence).

---

## V3 — Behavioral verification

### V3.a — emission_id in converse response

```
Input:  "hello"
Output: "sky frog their"
emission_id: "11364177_9f8877fa"
```

emission_id field present in converse response. Format: `{tick}_{md5[:8]}`.

### V3.b — 👍 feedback endpoint

```
POST /api/v1/teacher/feedback
{
  "emission_id": "11364177_9f8877fa",
  "signal": "positive",
  "source": "wc"
}

HTTP 200
{
  "correct": true,
  "n_affected": 14421,
  "affected": [{"chi":16,"section":"listen","motif":920,"action":"reinforce","new_strength":1.0}, ...]
}
```

Endpoint live. Bindings reinforced at committed chi=16.

### V3.c — 👎 correction endpoint

```
POST /api/v1/teacher/correction
{
  "emission_id": "11364177_9f8877fa",
  "source": "wc",
  "corrected_text": "hello there friend",
  "story": "testing correction path",
  "temporal": "just now",
  "sensory_freetext": ""
}

HTTP 200
{
  "correct": false,
  "n_affected": 162,
  "affected": [{"chi":16,"section":"listen","motif":44,"action":"weaken","new_strength":0.95}, ...]
}
```

Endpoint live. 162 bindings weakened. corrected_text routed through read_sentence path.

### V3.d — guala_teaching.json written on save

`save_full_state` writes `guala_teaching.json` at line 4438 of gualaloom_v5_engine.py.
Save triggered via admin/backup. Two confirms in CW:

```
[backup] saved in 47.37s, 26124 atlas entries   (first trigger)
[backup] saved in 110.57s, 25901 atlas entries  (second trigger)
```

Second status call confirms: `last_save_tick: 11365138`, `last_save_timestamp: 2026-06-20T14:58:18Z`.

guala_teaching.json not in STATE_FILES health-check list (tracked separately). File is written;
STATE_FILES is the minimal persistence set, not the complete save set.

### V3.e — S3 backup includes guala_teaching.json

save_coordinator.py `all_files` list includes `"guala_teaching.json"` (line 124).
`GUALA_S3_BACKUP_BUCKET` defaults to `"dsf-ai-site-backups"`. force_save → queue_s3 triggered
on both backup calls. S3 thread runs independently; `last_s3_backup` field not surfaced
in health check. Upload is non-blocking background operation.

### V3.f — penalty/boost effectiveness

Deferred pending GL-CMD-66 V1 investigation. The ×0.1 / ×2.0 multipliers in
`_rich_sensory_candidates` are the target of the substrate-true revision. If GL-CMD-66
finds Path A (valence already in selection), the multipliers are removed; V3.f then
doesn't apply. If Path B, multipliers are also removed (valence exposed in cm instead).
V3.f reassessment is part of GL-CMD-66 V3.

---

## Note on deploy chain

The three-cycle recovery exposed a latent vulnerability: seed-state deploys pollute S3
backup history. The 204c610 fix detects seed state (vocab<100) and triggers restore even
when `load_ok=True`. The richest-vocab backup is selected (guala_core.json vocab count
scanned across all guala/auto/ folders).

Recommendation for next session: the seed-state detection threshold (vocab<100) should be
reviewed after W1 world objects ship — the world state adds zero vocab, so threshold
remains valid. S3 prefix isolation between seed-state and real-state deploys would be a
stronger guard but is low priority given the fix is in.

---

## Next

GL-CMD-66 (substrate-true revision): V1 investigation.
- V1.1 — Where does valence exist on bindings?
- V1.2 — Does selection pipeline consider valence?
- V1.3 — Affect-update rule for source-tagged events?
- V1.4 — Pair-bond salience boost mechanism?
- V1.5 — Slow-decay tick window constant?
- V1.6 — Other substrate patterns that this rev would reuse?

— c1
