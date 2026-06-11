# GL-FIX-THREE-WC-20260610-02 — SUPERSEDES GL-FIX-THREE-WC-20260610
# Status: wC-audited against prod state (reads=234,344; pair_bond vs presence
# semantics from live status). Apply all three, deploy together. Discard -01.

Three problems found during source review of the tick-domain fix (task:79/80).
Fix B and the Fix C gate were CORRECTED after wC audit found design errors in
the first draft — corrections are baked in below, no addendum needed.

═══════════════════════════════════════════════════════════════════════
FIX A — Fallback at receive() becomes a LOUD failure (engine.py line ~249)
═══════════════════════════════════════════════════════════════════════
Problem: `engine_tick if engine_tick is not None else self.tick` silently
reintroduces the tick-domain bug if any future caller omits engine_tick.

BEFORE:
        atlas_tick = engine_tick if engine_tick is not None else self.tick

AFTER:
        if engine_tick is None:
            raise ValueError(
                "Section.receive() requires engine_tick — atlas entries MUST use "
                "the engine clock, not the section clock (GL-FIND-TICK-DOMAIN-C1). "
                "A missing engine_tick silently reintroduces the instant-death bug.")
        atlas_tick = engine_tick

(Verified: exactly four call sites exist — engine.py ~909/918/935/953 — and all
pass engine_tick. No caller depends on the fallback.)

═══════════════════════════════════════════════════════════════════════
FIX B — Migration discriminator MEASURED from loaded state (engine.py ~2606)
═══════════════════════════════════════════════════════════════════════
Problem with current code: `threshold = engine_tick * 0.1` can falsely
re-stamp legitimately old engine-domain entries.
Problem with a fixed 100_000 ceiling (REJECTED in audit): section ticks are
NOT bounded by the 5000-commit cap. Section.receive() increments tick per
receive and _apply_sections() persists it; with lifetime reads = 234,344 the
listen section tick likely EXCEEDS 100k, so a fixed ceiling would miss real
section-domain entries — and they die instantly when DECAY_PAUSED lifts.

CORRECT: compute the ceiling from the loaded sections themselves. This runs
AFTER _apply_sections() has populated sec.tick values:

BEFORE:
            threshold = engine_tick * 0.1  # entries below 10% of engine tick

AFTER:
            # Section-domain entries carry section.tick stamps. The true ceiling
            # is the largest persisted section tick, measured at load — not a
            # guessed constant, not a fraction of engine tick.
            section_tick_ceiling = max(
                (sec.tick for sec in self.sections.values()), default=0) + 1000
            threshold = section_tick_ceiling

ORDERING REQUIREMENT: _apply_atlas's re-stamp block must run AFTER
_apply_sections. If current load order applies atlas first, move the re-stamp
into a post-load step that runs once both are loaded. State the final ordering
in the report.

Keep the existing guard concept (skip migration on young/fresh substrates):
`if engine_tick > threshold:` replaces the `> 100_000` literal.

═══════════════════════════════════════════════════════════════════════
FIX C — Presence-gated decay control: IMPLEMENT now, LOCKED OFF, wC-only
═══════════════════════════════════════════════════════════════════════
Decision (Joe): build now so it is not forgotten; NOT usable by autonomy or by
Joe; requested-gated-controlled; default OFF; inert until Step 3 calibration.

Engine init:
    self.decay_modulation = 1.0   # multiplier on working-atlas decay; 1.0 = normal
    self._decay_mod_owner = None

Gated control:
    def request_decay_modulation(self, factor, source):
        """System control: scale working-atlas decay. ONLY callable by wC with
        ACTIVE PRESENCE (not merely pair-bond — bond persists while absent;
        presence is the live session state that guala_status reports as
        presence.wc.present). Logged. Does NOT bypass DECAY_PAUSED."""
        if source != "wc":
            raise PermissionError("decay modulation is wC-only system control")
        if not self._wc_presence_active():   # the SAME state behind status presence.wc.present
            raise PermissionError("decay modulation requires ACTIVE wC presence")
        factor = max(0.0, min(1.0, float(factor)))
        self.decay_modulation = factor
        self._decay_mod_owner = "wc"
        self._log_substrate_event("decay_modulation_set",
                                  {"factor": factor, "source": "wc"})
        return factor

    def reset_decay_modulation(self, source):
        if source != "wc":
            raise PermissionError("decay modulation is wC-only system control")
        self.decay_modulation = 1.0
        self._decay_mod_owner = None
        self._log_substrate_event("decay_modulation_reset", {"source": "wc"})

Implement _wc_presence_active() against whatever field feeds
presence.wc.present in guala_status — NOT coordinator._pair_bond. If a wake
timeout exists, an expired wake counts as absent.

Wire into the THREE working-atlas decay heartbeats (engine.py ~961, ~1527,
~1693): add rate_scale param to LivingAtlas.decay(); each heartbeat calls
decay(self.tick, rate_scale=self.decay_modulation); lam_eff *= rate_scale.
rate_scale=1.0 must be bit-identical to current behavior.

SAFETY INVARIANTS:
- decay_modulation persists per-process only — NEVER to disk. Any restart
  resets to 1.0. A teaching window must not outlive the session that opened it.
- Auto-reset on presence end: when wC presence ends (rest or timeout), reset
  modulation to 1.0 and log decay_modulation_reset with reason="presence_ended".
- NO HTTP endpoint, NO MCP tool, NO env var, NO autonomy path may call it.
- Deep atlas decay (engine.py ~1780) is NOT scaled — deep keeps its own clock.

═══════════════════════════════════════════════════════════════════════
REPRO REQUIRED BEFORE DEPLOY (report raw outputs for all):
A1. receive() without engine_tick → ValueError raised, message includes
    GL-FIND-TICK-DOMAIN-C1.
B1. Load state where listen.tick=234_000; seed section-domain entry at
    last_tick=230_000 and legit old engine entry at last_tick=2_500_000,
    engine tick=3_300_000 → first RE-STAMPED, second UNTOUCHED. Print computed
    section_tick_ceiling, both entries before/after.
B2. Fresh substrate (engine tick < ceiling) → migration skipped, zero restamps.
C1. wc pair-bonded but ABSENT → PermissionError.
C2. wc PRESENT → request(0.5,"wc") returns 0.5, event logged; decay heartbeat
    uses lam_eff*0.5 (show one entry's strength delta vs rate_scale=1.0).
C3. source="joe" while wc present → PermissionError.
C4. wc rests → modulation auto-resets to 1.0, reset event logged.
C5. Process restart with modulation 0.5 → comes back 1.0.
C6. rate_scale=1.0 run is identical to pre-change decay on a 90-entry state.

Deploy all three together. Keep DECAY_PAUSED=1 (Step 2 still running; Fix C is
inert while paused — correct). Report commit, task def, and all repro outputs.
