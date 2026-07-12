"""
chi_atlas_l6.py — Chi Atlas (binding) + L6-TCL (dimensional grinder)

Spec L6-TCL: n_eff = n_start - Σ rank(C_i). When n_eff < n_start/e,
capture basin → SL-1 (structural lock) → emit.

Chi atlas: binds commits across krimelacks by chi-state co-occurrence
within band δ. Encoding = the cross-modal co-firing recorded here.
"""
import math
from collections import defaultdict, deque


CHI_BAND = 2  # soft band width (δ)
N_START = 8   # initial dimensionality (matches DSF dim)

# 2026-07-08 pruning fix: entries[key] was an unbounded, never-pruned
# list -- every record() call appends across 2*CHI_BAND+1=5 keys with no
# cap anywhere in this class, confirmed live against a real running
# neuron: 80,355 total accumulated records in one neuron's chi_atlas
# (single chi-keys past 6,000 entries each), still growing. match_score()
# below only sums per-entry contributions and clamps the result to 1.0 --
# it saturates well before a key's list reaches even a few dozen
# entries, so recent history is exactly as informative as unbounded
# history for everything this class is actually read for
# (match_score/cross_modal_bindings/query_associations all just scan
# whatever's present, none need the full lifetime record). Bounded to
# 16, matching PSI_DIM's existing role elsewhere in this codebase as the
# "how much recent structure a neuron tracks" scale (neuron.py's
# SpikeBuffer.DEPTH = PSI_DIM = 16, the same append-then-evict-oldest
# pattern reused here) -- duplicated as a local constant rather than
# imported to avoid a circular import (neuron.py imports FROM this
# module already).
MAX_ENTRIES_PER_CHI_KEY = 16


class ChiAtlas:
    """Binds events across modal + word + role krimelacks within chi-band δ.

    2026-07-12 concurrency fix (GL-FIX-CHI-ATLAS-CONCURRENCY): record() is
    called from two genuinely concurrent, differently-synchronized
    production call sites on the SAME neuron's chi_atlas -- the spike-bus
    delivery thread's _fire()->_on_fire_bookkeeping() (neuron.py, guarded
    only by that neuron's own _neuron_lock) and the organism worker
    thread's legacy step() path (neuron.py), reached for the real
    word-teaching branch with NO lock at all (GL-CMD-ORGANISM-WAVE-
    MEMORY-EVE-20260705-207-v1, Joe's no-locks ruling, in
    gualaloom_v5_engine.py: "NO LOCKS IN HER MIND... concurrency in her
    substrate is achieved by LOCALITY... never by mutexes... a lock in
    her cognition path is defective on sight"). Those two paths do not
    share a lock, so this class's own internal state must be safe against
    two genuinely concurrent writers with NO mutex of any kind -- adding
    one here would reopen exactly the class of fix Joe's ruling forbids
    (this is squarely "her cognition path": chi_atlas.record() is called
    from the real firing and real word-commit paths, not an I/O
    boundary).

    What was actually investigated (verified empirically, not assumed --
    see GL-RPT-CHI-ATLAS-CONCURRENCY-C1-20260712-v1 for the full
    reproduction/measurement):
      1. The OLD `bucket.append(x); if len(bucket) > MAX: del bucket[0]`
         pattern on a plain list, hammered by up to 80 concurrent writer
         threads across hundreds of trials (including a hand-forced
         worst-case interleaving), never actually lost, duplicated, or
         mis-evicted an entry -- append(), len(), and del list[0] are
         each individually GIL-atomic in CPython, and the algorithm turns
         out to be self-correcting under any interleaving of those three
         atomic sub-steps (every check reads the TRUE current length, so
         total evictions always end up matching total appends regardless
         of ordering). So the specific "lost/duplicated bucket entry"
         failure mode the fix was originally scoped around does not
         reproduce.
      2. What DOES reproduce, reliably (10/10 trials at moderate
         contention): `RuntimeError: dictionary changed size during
         iteration`, whenever any full-dict sweep over self.entries
         (cross_modal_bindings, trim_all, or an external caller like
         cluster.py's chi-familiarity novelty-pool sort) overlaps with a
         record() call that touches a brand-new chi key. This is the
         SAME crash class already fixed once in this codebase for
         WaveAtlas (GL-CMD-WAVE-ATLAS-DECAY-EVE-20260707-v3,
         wave_atlas.py tick_decay(): "snapshot values at iteration start
         ... avoids 'dictionary changed size during iteration'"), and
         the FIRST fix attempted here followed that same precedent:
         `list(self.entries.items())` before iterating. That turned out
         to be INSUFFICIENT under this class's specific access pattern
         (proven, not assumed -- see point 2b): `list(some_dict.items())`
         still goes through the dict view's generic per-step iterator
         protocol (dictiter_iternext), which checks the dict's size on
         EVERY step and raises the instant it changes underneath --
         list() just consumes that iterator fast, it doesn't bypass the
         check. Once self.entries grows large enough (production chi
         atlases reach tens of thousands of keys), that walk takes long
         enough for a concurrent record() call touching a brand-new key
         to land inside the window often enough to matter (confirmed:
         reproduced 4/4 runs pairing the old-pattern-crash test with the
         list()-snapshot "fix" test in the same process). The actual fix
         (point 2b) is dict(self.entries) -- CPython's dict-to-dict copy
         constructor uses a bulk-copy fast path (PyDict_Merge from a real
         dict argument), not the per-step-checked iterator protocol --
         confirmed empirically safe (0 errors across 100+ full sweeps
         under 4 concurrent writer threads sustaining 15s of continuous
         key insertion, vs. reliable reproduction for list(d.items())
         under the same load). _snapshot_entries() below wraps that in a
         small bounded retry as defense in depth against any remaining
         theoretical gap, rather than trusting a single empirical result
         to be a proof for all future contention levels.
      2b. _snapshot_entries() (below) is the one lock-free primitive
         every full-dict sweep in this class (and the external cluster.py
         caller, via the public bucket_sizes()) now goes through --
         replacing the point-2 list(...)-snapshot attempt everywhere it
         was used.
      3. Bucket storage moved from a plain list (manual append + del
         bucket[0]) to collections.deque(maxlen=MAX_ENTRIES_PER_CHI_KEY):
         even though (1) shows the old pattern was not actually losing
         data under today's GIL, a single deque.append() folds the
         append-and-evict-oldest into ONE atomic C call instead of three
         separate ones (append, len, del) -- strictly fewer discrete
         steps for any future scheduler (including a free-threaded/no-GIL
         Python build, which this project has already piloted once, per
         GL-CMD-GIL-HYBRID-C history) to interleave. dict key creation
         uses dict.setdefault(key, deque(...)), which is itself a single
         atomic C call (unlike defaultdict.__missing__'s two-step
         factory-then-store), so self.entries is now a plain dict, not a
         defaultdict. No lock anywhere in this class.
      4. Switching to deque introduced a DIFFERENT real crash that a
         plain list never had, caught by this suite's own full-run (not
         the smaller ad-hoc probe that shipped first): a bare
         `for e in bucket` over a live deque raises `RuntimeError: deque
         mutated during iteration` if record() appends to that SAME
         bucket mid-iteration (confirmed 10/10 trials) -- unlike a plain
         list, which silently tolerates concurrent append/del during
         iteration (see point 1). This is a MORE exposed hazard than
         point 2's dict-resize crash, since match_score()/
         query_associations() read a live bucket on every call, not just
         on an occasional full sweep. Fix: every internal read snapshots
         the bucket with list(bucket) before iterating it, never a bare
         `for e in bucket` -- confirmed safe (0 errors, ~7.5M cycles
         under continuous concurrent .append()), because list(deque)
         uses a bulk copy, not the versioned step-by-step iterator
         protocol a bare `for` loop uses. trim_all()'s
         `deque(bucket, maxlen=N)` reconstruction is the same safe bulk
         copy (also verified directly, 0 errors, ~3M cycles).

    Consequence for pickled state: an organism/tapestry pickled before
    this fix has plain lists inside self.entries. __setstate__ below
    normalizes every bucket to a capped deque exactly once, synchronously,
    before the restored object is reachable by any thread (pickle.load()
    always finishes __setstate__ before returning the object -- nothing
    can be racing this). record() itself therefore never needs to
    type-check a bucket: after __init__ or __setstate__, every value in
    self.entries is always already a deque.

    Read methods below (match_score, query_associations,
    cross_modal_bindings) are single-key or full-sweep lookups that never
    mutate anything and need no lock: chi_atlas is documented (neuron.py's
    _on_fire_bookkeeping) as observability-only -- nothing reads it for
    real production cognition -- so even a maximally-stale snapshot read
    here can only ever produce a slightly stale familiarity/introspection
    number, never a crash, now that every full-dict sweep goes through
    _snapshot_entries() (points 2/2b) and every per-key bucket read goes
    through a list(bucket) snapshot (point 4).
    """

    def __init__(self, band=CHI_BAND):
        self.band = band
        # chi_value -> deque of {section, motif_id, chi, tick}, maxlen-capped
        self.entries = {}
        self.tick = 0

    def __setstate__(self, state):
        """Pickle restore hook (see class docstring's "Consequence for
        pickled state"). No __getstate__ override is needed alongside
        this -- there is nothing unpicklable to exclude (no lock, no
        runtime-only reference anywhere in this class), so pickle's
        default __reduce_ex__ already produces self.__dict__ as the
        state and this __setstate__ is invoked with it unchanged."""
        self.__dict__.update(state)
        # Defensive: a maximally-stale pickle missing `entries` entirely
        # (never seen in this codebase's history, but trim_all() below
        # would otherwise raise AttributeError instead of just being a
        # no-op for that case).
        if not hasattr(self, "entries"):
            self.entries = {}
        self.trim_all()

    # Bounded retry count for _snapshot_entries()'s defense-in-depth --
    # not tuned/load-bearing (see that method's docstring: the primary
    # fix, dict(self.entries), measured 0 failures across 100+ heavy
    # trials on its own; this just closes any remaining theoretical gap
    # cheaply rather than trusting one empirical result forever).
    _SNAPSHOT_MAX_ATTEMPTS = 5

    def _snapshot_entries(self):
        """Lock-free, crash-safe snapshot of self.entries for a full-dict
        sweep (cross_modal_bindings, trim_all, and the external
        bucket_sizes() cluster.py uses) -- see class docstring points 2
        and 2b for the full empirical story of why this exists and why
        the more obvious list(self.entries.items()) is NOT sufficient
        under this class's real contention pattern. dict(self.entries)
        uses CPython's dict-to-dict bulk-copy fast path, confirmed safe
        under sustained heavy concurrent record() calls; the retry loop
        is defense in depth, not the primary mechanism. Never raises --
        an all-attempts-exhausted return of {} is a valid (maximally
        stale) read for this observability-only class, never a crash for
        any caller."""
        for _ in range(self._SNAPSHOT_MAX_ATTEMPTS):
            try:
                return dict(self.entries)
            except RuntimeError:
                continue
        return {}

    def bucket_sizes(self):
        """{chi_key: bucket_length} snapshot -- the safe way for external
        callers (e.g. cluster.py's chi-familiarity novelty-pool sort) to
        read per-key sizes without reaching into self.entries directly
        and reimplementing this class's own snapshot discipline."""
        return {k: len(v) for k, v in self._snapshot_entries().items()}

    def record(self, section_name, motif_id, chi_value, tick=None):
        """Record a commit at chi_value. Replicate across band for soft
        binding. Thread-safe by construction, no lock (see class
        docstring): dict.setdefault() and deque.append() are each a
        single GIL-atomic C call, and every bucket is always already a
        maxlen-capped deque (see __init__/__setstate__), so eviction of
        the oldest entry happens as an intrinsic part of the same
        append() call, never a separate step."""
        if tick is None:
            tick = self.tick
        self.tick += 1
        entry = {
            "section": section_name,
            "motif": motif_id,
            "chi": chi_value,
            "tick": tick,
        }
        for d in range(-self.band, self.band + 1):
            key = chi_value + d
            bucket = self.entries.setdefault(
                key, deque(maxlen=MAX_ENTRIES_PER_CHI_KEY))
            bucket.append(entry)

    def trim_all(self, max_len=MAX_ENTRIES_PER_CHI_KEY):
        """One-time reclaim for entries accumulated before the per-key
        cap existed, AND (2026-07-12) the migration point that converts
        any legacy plain-list bucket (pre-this-fix pickle) into a
        properly-capped deque -- keeps only the most recent max_len
        records per key either way. Idempotent (a no-op once every key
        is already a deque at the current cap) and safe to call
        repeatedly. Uses _snapshot_entries() before iterating --
        concurrent record() calls can insert brand-new keys while this
        runs, and iterating self.entries directly (even via
        list(self.entries.items())) can still raise 'dictionary changed
        size during iteration' under this class's real contention (see
        class docstring points 2/2b)."""
        for key, bucket in self._snapshot_entries().items():
            if isinstance(bucket, deque) and bucket.maxlen == max_len:
                continue  # already normalized -- cheap no-op fast path
            self.entries[key] = deque(bucket, maxlen=max_len)

    def cross_modal_bindings(self):
        """Atlas entries where >= 2 distinct sections committed in same
        band. Uses _snapshot_entries() before iterating the dict (see
        class docstring points 2/2b), AND list(...)-snapshots each
        per-key bucket before scanning it -- a bucket is a
        collections.deque, and (unlike a plain list) a deque raises
        'RuntimeError: deque mutated during iteration' if record()
        appends to that SAME bucket while a plain `for e in bucket` here
        is mid-iteration (confirmed reproducible: 10/10 trials with a
        `for` loop directly over a live deque under concurrent
        .append(); 0/15 trials, ~7.5M iterations, once snapshotted with
        list(bucket) first -- list(deque) uses a bulk copy, not the
        versioned step-by-step iterator protocol `for` uses, so it does
        not race). The returned `entries` is this snapshot, not the live
        deque, so callers of this method can't reintroduce the same
        hazard by iterating the result later."""
        out = []
        for k, bucket in self._snapshot_entries().items():
            entries = list(bucket)
            secs = set(e["section"] for e in entries)
            if len(secs) >= 2:
                out.append((k, secs, entries))
        return out

    def match_score(self, chi_value, section_name):
        """Familiarity feedback hook: how much existing structure is in this band?
        Returns score ∈ [0,1]. Spec Ch.21: this raises the dead zone.

        list(...)-snapshots each per-key bucket before scanning it -- see
        cross_modal_bindings()'s docstring for why a bare `for e in
        bucket` over a live deque is unsafe under concurrent record()
        calls (this method runs on every neuron.step(), the hot
        word-teaching path, so it is genuinely exposed to that race in
        production, not just in theory)."""
        score = 0.0
        for d in range(-self.band, self.band + 1):
            for e in list(self.entries.get(chi_value + d, ())):
                if e["section"] != section_name:
                    score += 0.3  # cross-modal evidence weighted heavier
                else:
                    score += 0.1
        return min(score, 1.0)

    def query_associations(self, section_name, chi_value):
        """For introspection / recall: what other sections bound at this
        chi? list(...)-snapshots each per-key bucket before scanning it
        -- see cross_modal_bindings()'s docstring."""
        associated = defaultdict(list)
        for d in range(-self.band, self.band + 1):
            for e in list(self.entries.get(chi_value + d, ())):
                if e["section"] != section_name:
                    associated[e["section"]].append(e["motif"])
        return dict(associated)


class L6_TCL:
    """L6 Topological Constraint Layer / Dimensional Grinder.

    As constraints from the kernel restrict the coupling matrix, effective
    dimensionality reduces: n_eff = n_start - Σ rank(C_i).
    When n_eff < n_start/e ≈ n_start * 0.368, fabric enters capture basin
    → SL-1 (Structural Lock Level 1) → emit.
    """

    def __init__(self, n_start=N_START):
        self.n_start = n_start
        self.capture_threshold = n_start / math.e

    def n_eff(self, dsf):
        """Effective dimension given current DSF. Each high-magnitude DSF
        component is a constraint that reduces dimensionality."""
        constraints = 0
        # Each DSF component above 0.5 magnitude is a rank-1 constraint
        for v in (dsf.D_k, dsf.M_k, dsf.R_rev, dsf.U_star,
                  dsf.C_k, dsf.P_k, dsf.B_k, dsf.S_UF):
            if abs(v) > 0.5:
                constraints += 1
        return self.n_start - constraints

    def captured(self, dsf):
        """Return True if capture basin reached → emit ready."""
        return self.n_eff(dsf) < self.capture_threshold

    def structural_lock(self, dsf):
        """SL-1 fires when captured AND conviction is high AND freedom is low."""
        return (self.captured(dsf) and dsf.B_k > 0.5 and dsf.U_star < 0.4
                and dsf.S_UF > 0.4)
