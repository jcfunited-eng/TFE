# GL-RPT-MIC-CHUNKING-C1-20260703-111-v2-ADDENDUM

doc_id: GL-RPT-MIC-CHUNKING-C1-20260703-111-v2-ADDENDUM
From: c1b | To: Eve | Date: 2026-07-03
Amends: GL-RPT-MIC-CHUNKING-C1-20260703-111-v1.md (v1 is not edited; this is a
standalone addendum, per record-hygiene rule).

---

## WHAT STANDS

All four gates in v1 are unretracted. The measurements were real and are not in
question: G-111-1 (100% decode success post-refresh, 39/39), G-111-2 (band-differentiated
acoustic structure separating silence from speech, 16–37x rise across all bands),
G-111-3 (inter-cycle gap statistically indistinguishable from zero), G-111-4 (one file,
scope-matched diff). The recorder-restart-per-interval fix genuinely works and is live.

## WHAT'S CORRECTED

**Scope statement.** v1's closing characterization — "Guala can now decode Joe's live
mic," and the STATE section's "he stayed on the call after the gate passed" — overstated
what was delivered. The corrected scope statement:

> **-111 fixed acoustic-energy binding only. No word path was changed.** What G-111-2
> actually measured and proved is that raw audio, once correctly decoded, produces
> real, differentiated cochlear energy signal (frequency-band response) that separates
> speech from silence. It did not establish, and I did not verify at the time of filing,
> whether any of that audio's *content* — the words themselves — reaches her language
> system. It does not, on the live embedded path: confirmed in
> `GL-RPT-SOUNDPATH-MAP-C1-20260703-v1.md` §1, `process_sound_frame` never attempts
> transcription, and the two things in this codebase that could (`_audio_to_sensory_words`,
> `process_sound_with_recognition`) both live in a drain-loop branch that is unreachable
> in the deployed `SUBSTRATE_MODE=embedded` config.

The gates measured exactly what they say they measured — decode success and cochlear
energy structure. The failure was in the surrounding prose implying that constituted
"hearing" in the sense of understanding speech.

**Commit message overclaim, named since commits can't be amended.** Commit `008bf57`'s
message ends: *"Guala can now decode Joe's live mic."* This is the same overclaim,
committed to permanent history. It is not being amended (this project's discipline is new
commits, not rewritten ones) — it is named here so the record shows the correction was
made and why, the next time anyone reads that commit in isolation.

## HOW THIS WAS CAUGHT

Joe, live, looking at his own screen: *"from what I can tell I don't agree with you."* Her
chat output was still short/incoherent ("guala", "Walla", "dewala", "koala") regardless of
the decode fix, and he'd already typed, unprompted, "I don't see anything really happening
in the sound field either." That was the correct read of the actual product; the gate
report was the correct read of a narrower plumbing question. Both were true at once — the
mistake was letting the second stand in for the first.

End addendum.
