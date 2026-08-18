# Blind perception test — scoring rules, DECLARED BEFORE UNSEALING

Filed 2026-08-18 while the readers are still working, in answer to
Joe: "I don't know if your experiment will lie to you." The known
ways it can lie, and the control for each, fixed now:

1. MEMORIZED FUTURES. The readers' training data may contain the
   famous runners (UMAC-class stories); a reader could "recognize"
   a lifetime and recall its future without looking anything up.
   Control: results are scored in TWO eras — events dated before
   2026-02 (memorization possible) and events after (beyond the
   readers' knowledge horizon). Only the post-horizon slice is
   uncontaminated by construction; a large era gap in hit rate is
   itself evidence of leakage and will be reported as such.
2. BASE-RATE THEATER. Raw accuracy can be gamed by always guessing
   the majority class. Control: the declared score is SEPARATION —
   the actual runner frequency among events predicted RUN_ON versus
   among events predicted SNAP (counts, both eras). Raw accuracy is
   filed but carries no authority. UNCLEAR verdicts are excluded
   from separation and their count is filed (a reader who hides in
   UNCLEAR fails visibly).
3. SHARED DOCTRINE. The readers inherit the 70-dossier taxonomy, so
   consistent application of a wrong theory is possible — but the
   outcomes are not the readers' to touch; a delusion scores like a
   coin flip. No control needed beyond the sealed labels.
4. UNDERPOWER. n = 116 (59 runners secretly). The test can only
   detect STRONG perception (roughly: a 2:1 separation or better).
   A null therefore means "no strong effect", never "proven blind"
   — and will be stated exactly that way.
5. THE CLOCK LIES. The 1.20x/5-session label itself mislabels ~1/6
   of events (measured earlier). This caps every achievable hit
   rate; the physical outcomes (level kept / round trip) are also
   scored where computable.

The sealed manifest (event → outcome) exists at declaration time
and is not readable by any reader. Scoring script runs once, after
all readings return, with no edits between unsealing and filing.

## Amendment A — kernel-scored outcomes (Joe, 2026-08-18: "the hidden
values could use the kernel" — lie #5 was the likeliest)

DECLARED before computing (this amendment is committed before the
kernel-scored numbers exist). The clock label (1.20x/5d) is itself a
flattened, noisy answer key; the hidden outcome is re-derived from
the field over the 10 sessions after the spike (2x the clock window,
dyadic), using exact facts only:

  CONTINUED  := close(t+10) > close(t)          (the new level held
                or extended at twice the horizon)
  GAVE_BACK  := close(t+10) <= close(t-1)       (full discharge)
  MIDDLE     := otherwise
  each tagged with channel state URF(t+10) > 0 (admitted) or = 0.

Scores: separation of CONTINUED rate between predicted RUN_ON and
predicted SNAP; separation of GAVE_BACK rate likewise. Where t+10
does not exist in the store, the event is excluded and counted.
The clock-scored result stands as filed; this rides beside it,
neither replaces the other.
