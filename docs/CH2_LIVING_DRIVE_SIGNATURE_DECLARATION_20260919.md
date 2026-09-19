# The living-drive signature — declaration (2026-09-19)

Declared BEFORE any result. Provenance: Joseph. The conditions below are his,
transcribed from the CH2 holdings reading protocol he wrote on 2026-08-25
("ignitions still appear behind advances, resonance stays reinforced, support
holds its band, fuel is not in sustained drain, damage stays episodic and
heals") and from his exclusions ("don't invest in pump and dumps, don't buy
zombie stocks"). Nothing here is mined, swept or fitted; every constant is
fixed in this document before the measurement runs.

## The question it answers

The measured deficit is **cross-sectional**: among the names available on a
given day, the flattened basin gate picks worse than random. So:

**Among the names available on a day, does the full living-drive signature
pick better than the rest of that day's names?**

Not "does it beat the index". Not "does it make money". Whether a body showing
the whole signature outruns bodies that do not, on the same day, decided with
only what was knowable at that close.

## The signature — all five, on the entry session's closed lane

Trailing window **W = 20 sessions** throughout; lag **L = 10 sessions**.

1. **Support holds its band** — `S_UF ≥` its own trailing-20 median.
2. **Resonance reinforced** — `R_UF ≥` its own trailing-20 median.
3. **Fuel not in sustained drain** — `B_k ≥` its value 10 sessions earlier.
4. **Damage episodic and healed** — rupture `max(0, −max(S_UF−U*, R_UF−U*))`
   is zero on this session, and was above zero on no more than 5 of the
   trailing 20.
5. **Ignitions behind the advance** — `D_k = 1` on this session and on at
   least 10 of the trailing 20.

A body must show **all five**. A body showing four is not in the set.

## The exclusions (Joseph's L5 common sense)

- **Zombie** — fewer than 250 sessions of history.
- **Pump and dump** — price up more than 50 % over the trailing 20 sessions.
- The liquidity and price floors already in use ($5 M median dollar volume
  over 20 sessions; close ≥ $5).

## Timing

Every condition is read on a closed session. The position opens at the **next**
session's close and is held a fixed number of sessions — **30 and 60**,
declared. No adaptive exits: this measures selection alone.

## The comparison

For each day, three sets drawn from the same eligible names:

- **signature** — the names showing all five conditions and passing the
  exclusions.
- **all_eligible** — every name with a lane that day passing the floors and
  exclusions (what could have been bought).
- **random_same_count** — the same number of names as the signature set,
  drawn at random from `all_eligible` that day. **200 seeds.**

## The bar

The signature ships as a candidate for further work only if its mean return
per position exceeds the 95th percentile of `random_same_count` at **both**
holds **and** in **both** halves (split 2024-03-15). Anything less is reported
as measured.

## The risk this measurement carries, stated plainly

A five-condition checklist over per-stock fields is the shape of the condemned
"spring triad" (`tfe-condemned-ideas`). The differences here: the conditions
are Joseph's written physics rather than mined thresholds, they are declared
before measurement, none is swept, and the test is cross-sectional against the
same day's alternatives rather than a return scan. If it fails, it fails as
that family has failed before, and the failure is filed as such.

## Output

`artifacts/ch4_uf/ch2_living_drive_signature_20260919.json` plus a result
section here, committed. Either answer is filed the same way.
