# GL-RPT-DEPLOY2-C1-20260703-v3

doc_id: GL-RPT-DEPLOY2-C1-20260703-v3 (addendum 2; v1 deploy+gates, v2 T7+mic retained)
From: c1a | To: Eve | Date: 2026-07-03 (~03:20Z)
Adds: loomscan DEAD-PAGE root causes (Joe's screenshot, post-href-fix). READ-ONLY —
diagnosis only; fix shapes need Eve's GO.

---

## FAILURES FIRST

### 1. -98 T1 hard FAIL on the real page: loomscan renders but EVERY data pane stays
"loading…/—" (Joe's screenshot ~03:00Z). Two independent front-door faults:

**(a) CORS preflight rejection kills ALL calls.** loomscan's `fetchJ` sends an
`X-API-Key` header on every request (loomscan.html:187 defines the key; all three
polls attach it). A custom header forces a CORS preflight, and the API Gateway answers:

```
access-control-allow-headers: content-type      ← x-api-key NOT allowed
```

→ the browser blocks every request before it leaves. curl (no CORS) succeeds, which
is why serving checks passed and why the page dies silently (`catch(e){}` swallows).
gualaloom.html works because its polls do NOT attach the header. The key is also
unnecessary for the endpoints loomscan uses — `/status`, `/events`, `chi_density`
are unauthenticated.

**(b) chi_density is not routed by the API Gateway.** Verbatim:

```
GET https://3d6toi0gw0…/api/v1/gualaloom/chi_density → 404 {"error": "Not found: /api/v1/gualaloom/chi_density"}
GET http://dsf-ai-alb-725095635…/api/v1/gualaloom/chi_density → 200 (full live per-chi map, tick 14228960)
```

The container endpoint works; the gateway's router predates the path. Even with (a)
fixed, the ring dots would stay empty through the gateway.

### 2. SECURITY, on record: loomscan.html:187 embeds the production GUALALOOM_API_KEY
in public client-side JS on a public page. The key gates the admin endpoints
(amnesty, force_dream, backup, migrate…). Anyone reading view-source holds it.
Needs rotation + removal regardless of which fix ships.

## FIX SHAPES (not shipped; smallest first)

1. Static-only: remove the `X-API-Key` header from loomscan's fetches (the endpoints
   are public). Fixes header/status/events/organs/health/activity/feed — everything
   except ring dots. Same ship path as the href fix.
2. chi_density: either (i) add the GET route to the gateway router (infra), or
   (ii) expose chi density as a `/chi_density` command on the existing POST endpoint
   (code, task swap — could ride Deploy 3). Eve picks.
3. Key rotation + strip from client JS (separate dispatch; touches task env + page).

## CONVERSATIONAL EVIDENCE (Joe's transcript, ~02:5x–03:0xZ, verbatim excerpts)

Her replies to Joe are now 2-3 word combinations beyond the "<word> page" floor:
"carrying ding turns" / "said elmo make" / "kids pond hers" / "you're be jo" /
"do joe pond" / "character getting be" → Joe echoes "character getting beat" →
"fun sesame ping" → (Bell.png + "ping ping ping") → "white ding played" →
(Joe: "Pretty bells ding ding ding") → "character singing letters". Post-Deploy-2
composition (80-tick commits) is visibly mixing source material with occasional
context tracking (jo/joe, ding after bells). Filed as G-C / T6-review evidence —
no claim beyond what is quoted.

End addendum.
