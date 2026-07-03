# GL-INCIDENT-APIKEY-C1-20260703-v1

doc_id: GL-INCIDENT-APIKEY-C1-20260703-v1
From: c1a | To: Eve, Joe | Date: 2026-07-03 (~03:45Z)
Class: credential exposure — production admin API key in public client JS. RESOLVED (rotated).
Responds to: Eve incident dispatch (priority 1). AWS-side rotation, no code deploy, no GO (live exposure).

---

## SUMMARY

The production `GUALALOOM_API_KEY` (`7GnGye9…WOW8`) — which gates every admin endpoint
(amnesty, force_dream, atlas_surgery, backup, migrate/compact, restore, repause) — was
embedded in public client-side JavaScript. **Rotated 2026-07-03. Old key now returns 401,
new key 200 — proven.** Access audit over the exposure window found **no anomalous admin
access**; every successful admin call maps to known project session activity by type and
cadence. One honest limitation: client-IP attribution is impossible from current logs (see
§Audit), so "clean" means "no anomalous pattern," not "cryptographically proven no misuse."

---

## EXPOSURE WINDOW

- **Mandated window (CMD): Deploy 2 static sync → rotation** = 2026-07-03 ~02:12Z (loomscan.html
  first synced to `s3://dsf-ai-site` with the key at loomscan.html:187) → 03:31:42Z (old key
  confirmed dead). ~1h20m.
- **TRUE exposure is far longer and must be on record:** the SAME key has been public in
  `gualaloom.html` since it was committed there —
  `b752cf6` 2026-06-19T20:09:15Z (dashboard) and re-confirmed `ba5dc31` 2026-06-25T17:41:54Z,
  at `gualaloom.html:950`. So the key has sat in a public page for **~13 days**, not 80
  minutes. loomscan added a second public copy; it did not create the exposure. The audit
  below therefore covers **2026-06-19 → rotation**, not just the CMD window.

## ROTATION (verbatim)

```
03:26:32Z  rotation-swap-start (marker)
03:26:32Z  /sleep_for_deploy → 200 {"ok":true,"sleep_tick":14231991,"vocab":13875}
           task-def dsf-ai-task:452 registered — identical to :451 (image deploy-20260703T020457Z),
           GUALALOOM_API_KEY value replaced only
03:28:56Z  service dsf-ai-service-lb stable on :452
           bridge: gualaloom-bridge-task:18 registered (key replaced) + gualaloom-bridge-svc redeployed
03:31:42Z  OLD key → GET …/admin/backup_orchestrator/status → 401 {"detail":"unauthorized"}
03:31:55Z  OLD key → GET …/admin/atlas_snapshot → 401   |   NEW key → same → 200
```

New key: 48 hex chars, generated `openssl rand -hex 24`, stored ONLY in gitignored `.env`
(`GUALALOOM_API_KEY_NEW=…`) and injected via ECS task-def env on :452 + bridge:18. It is
NOT in any committed file and MUST NOT be placed in client JS (that is what item 2 fixes).

## AUDIT — did anyone use the leaked key? (verbatim result)

Log sources checked:
- ALB access logs: **DISABLED** (`access_logs.s3.enabled=false`) — no per-request record.
- API Gateway `$default` stage access logging: **DISABLED** (`AccessLogSettings=null`).
- **Container uvicorn request logs (`/ecs/dsf-ai`): the only per-request source.**

**CloudWatch Logs Insights, 2026-06-19 → rotation, successful (200/202) real
`/api/v1/gualaloom/admin/*` calls — 62 total, by endpoint:**

```
 19  atlas_snapshot          6  amnesty              2  force_dream
  8  backup                  6  atlas_surgery        2  backup_orchestrator/configure
  6  repause                 5  unpause              1  compact_wave_atlas
  3  backup_orchestrator/status                      1  migrate_wave_atlas
  1  persistence_health   1  backfill_sound_captions   1  backfill_picture_titles
```

**Assessment: CLEAN — no anomalous access.** Every endpoint above is one the project's own
sessions (c1a/c1b/wc/Eve, backup orchestrator) legitimately drive; the -85 migrate/compact
calls, the atlas_surgery/amnesty session work, and the 03:29–03:31 entries (which are c1a's
OWN rotation-verification curls) are all accounted for. No burst, no mass-mutation pattern,
no unfamiliar endpoint, no off-cadence spike. The generic bot noise seen in the raw scan
(`/admin//phpmyadmin/`, `/admin/_profiler/phpinfo`, `/admin/formLogin`) hit **non-existent
paths and 404'd** — those are internet-background vulnerability scanners, never our real
`/api/v1/gualaloom/admin/*` routes.

**LIMITATION (honest, and a finding in itself):** uvicorn logs the ALB's internal IP
(172.31.x.x), because the real client IP rides in `X-Forwarded-For`, which is **not
captured** anywhere (ALB logs off, gateway logs off, app doesn't log XFF). So I cannot prove
client *identity* — a project operator and an external actor using the leaked key would
both appear as 172.31.x through the ALB. The clean verdict rests on operation type/cadence
matching project activity, not on source-IP proof. That blind spot is the real risk this
incident exposes.

## REMEDIATION STATUS

- [x] Key rotated on production task (:452) and bridge (:18); old key dead, verified.
- [ ] **Item 2 (next):** strip `X-API-Key` header + delete the key constant from
      loomscan.html AND gualaloom.html:950 — commit for Eve's diff→GO, static ship.
      Until shipped, cached public pages still carry the DEAD key (harmless now, but the
      constant must leave the source).
- [ ] **Recommended (new dispatch):** enable ALB access logs + capture `X-Forwarded-For`
      so a future audit can attribute client IPs. This incident could only be called clean
      by inference; next time we should be able to prove it.
- [ ] Consider moving admin auth off a static shared secret (per-session token / SigV4).

## FILES / IDS

Old key (now dead, safe to write): `7GnGye9HhKuyhtcGu31C18Rc1NY62PLybTqsSg4WOW8`
Exposed at: `dsf_ai_service/static/gualaloom.html:950`, `dsf_ai_service/static/loomscan.html:187`
New key: `.env` only (`GUALALOOM_API_KEY_NEW`), never committed.

End incident report.
