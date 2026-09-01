# Guala speech repair attempt 41 — multi-hop self-hearing observation

Production source before this repair: task 1406, commit
`6bbdbaf3ec376f081a0d974855f3bc98ec41f6a9`. The organism and the synchronized
browser camera/microphone were healthy and advancing. No production state was
written during this analysis.

## Live failure

The live browser committed four synchronized 250 ms audiovisual hops per
request. Native vocal pressure was present and the bounded WAV endpoint served
the exact recorded bytes, but the public articulation record reported:

- `pressure_sample_count = 16000`;
- `self_hearing_hop_count = 0`;
- `self_hearing_receptor_ingress_count = 0`;
- `status = native_typed_articulation_emitted_self_hearing_not_proven`.

The exact live pressure was not silent and motor discharge was real, but the
page remained unmounted.

## Exact cause

Rust stores one emitted acoustic consequence per physical hop. The next hop
authenticates that exact pressure and body trajectory, composes it with the
external pre-cochlear pressure, advances all mounted ears, consumes it, and
may replace it with that hop's newly emitted pressure. That physics is correct
and remains unchanged.

Python retained each native causal interval but then concatenated every
emission in the whole four-hop HTTP request and hashed the 16,000-sample
aggregate as though it were one physical discharge. The consumed evidence is
correctly hop-local at 4,000 samples. Therefore no consumed receipt could
equal the synthetic aggregate hash or sample count. This was observation
blindness, not absent self-hearing.

The one-hop copied-body proof in attempt 39 passed because its request had one
emission and the immediate action-consequence hop returned that same pressure;
the request aggregate happened to equal the physical hop. It did not falsify
the browser's four-hop boundary. This missing matrix row is now permanent.

## Bounded repair and impact

Only `dsf_ai_service/native_production_app.py` changes in production behavior.
It groups already-returned native intervals by the physical hop that emitted
them, hashes each hop separately, and selects the newest exact emission whose
same hash and full sample count were consumed once through every mounted ear.
The WAV cache receives those same selected bytes. If no exact receipt exists,
the newest emission remains honestly unproven.

The evidence lists live only during one request and are discarded after the
replace-only public observation/cache update. They never enter the organism,
select an action, change timing, cause a retry, or affect persistence. No L0-L4,
DSF, neuron, formation, motor, vocal-body, cochlear, world, storage, or restore
law changes.

New falsifiers require the newest exact all-ear hop to win and prohibit a
concatenated multi-hop hash from being accepted. The focused speech/runtime
suite is `63 passed` with all production sensory authorizations enabled.

## Required copied-body gate before release

Build one immutable image from the clean repair commit, clone the immutable
tick-358454 production body with every original file hash exact, drive a
four-hop audiovisual-shaped intake, and require one 4,000-sample pressure hash
to return through all 34 ears while layer-13 recruitment remains zero. The
selected WAV bytes and hash must match, memory/storage must remain bounded,
and cold restart must preserve the newest body without replaying the consumed
pressure. Production must remain task 1406 until every row passes.
