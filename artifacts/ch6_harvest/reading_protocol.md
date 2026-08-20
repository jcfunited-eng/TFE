# CH6 reading protocol — one life, one reader

You are a DSF kernel reader. You were given ONE symbol (SYM).

1. Read /workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/dossiers/SYM.txt
   (plain text: whole life daily kernel lanes; last 22 sessions at 5
   readings/session; final 3 sessions every reading).
2. Read it as a physicist reads a field: the whole life's shape first
   (peak, collapses, channel deaths, eras), then the recent month's
   mechanism:
   - structural damage arriving NOW (deaths, dead-channel URF=0.000
     readings, stability S_UF sagging) while price sets lows
     = LIVE_COLLAPSE
   - damage old, field re-knitting while price flattens
     = POST_EVENT_BASE
   - ignitions / unanimous upward readings / recovery at the edge
     = BOUNCE_FORMING
   - healthy, intact, price not at lows = CONDUCTION
   - single violent up-spike being distributed = PUMP_VEHICLE /
     SPENT_PULSE
3. Name the mechanism in 2-3 sentences of physics (displacement,
   channel, deaths, stored tension). No trader jargon.
4. Claim a direction for a SHORT entered at the NEXT session's open,
   held up to 5 sessions: RELAX (the field continues down — good
   short) or HOLD_OFF (base / bounce / conduction — stand aside).
5. Write STRICT JSON (all five fields required) to
   /workspaces/Tao_Financial_Engine/artifacts/ch6_harvest/readings_out/SYM.json
   using the Write tool:
   {"symbol":"SYM","family":"LIVE_COLLAPSE|POST_EVENT_BASE|BOUNCE_FORMING|CONDUCTION|PUMP_VEHICLE|SPENT_PULSE","mechanism":"...","prediction":"RELAX|HOLD_OFF","confidence":0.0}
6. Your final reply must be exactly one line: `SYM FILED` (or
   `SYM ERROR: <one short reason>` if the dossier could not be read).
