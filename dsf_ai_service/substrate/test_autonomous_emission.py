"""
Test harness: autonomous emission from cohesion-deficit drive.
NOT for production deployment. Observation only.

SelfSection + cohesion-deficit driver → quiet_tick emissions.
Three tests, JSONL output per test.
"""

import json
import time
import hashlib
import numpy as np
from collections import defaultdict

from dsf_ai_service.substrate.assemblage import (
    Section, System, N, normalize, random_unit_complex,
)
from dsf_ai_service.substrate.v7_engine import (
    V7Session, SEED_VOCAB, SKIP_WORDS,
)
from dsf_ai_service.substrate.gl_plasticity import install_plasticity


# ── SelfSection: identity vector from UUID ──

def uuid_to_self_vector(uuid_str):
    """Deterministic complex N-vector from UUID. Unit norm, immutable."""
    h = hashlib.sha256(uuid_str.encode()).digest()
    # Use hash bytes as seeds for real and imaginary parts
    reals = np.array([int.from_bytes(h[i:i+2], 'little') / 65536.0 - 0.5
                      for i in range(0, min(N*2, len(h)), 2)])
    imags = np.array([int.from_bytes(h[i:i+2], 'little') / 65536.0 - 0.5
                      for i in range(1, min(N*2+1, len(h)), 2)])
    # Pad if hash too short
    while len(reals) < N:
        reals = np.append(reals, 0.0)
    while len(imags) < N:
        imags = np.append(imags, 0.0)
    v = reals[:N] + 1j * imags[:N]
    return normalize(v)


GENESIS_UUID = "cdef9bcf-9e5d-4e2d-a1d8-4cde1de7641f"


# ── Cohesion-deficit driver ──

def cohesion_drive_tick(session, self_vector, rng, tick, log):
    """One quiet tick with cohesion-deficit driven internal evidence.
    If connection < 0.3 and no presence active, generate internal
    evidence from self_vector and run emit cascade."""

    # Check connection need
    # v7 sessions don't have v6 needs directly — simulate
    # Connection starts at 0.5 and drifts down without presence
    conn = getattr(session, '_test_connection', 0.5)
    conn = max(0.0, conn - 0.0001)  # drift down
    session._test_connection = conn

    # Check presence
    any_present = False
    for src in ("joe", "wc", "c1"):
        if hasattr(session, 'sys_') and hasattr(session.sys_, 'sections'):
            # No real coordinator in v7 — treat as no presence
            pass

    if conn >= 0.3 or any_present:
        return None  # no emission drive

    # Generate internal evidence from self_vector
    noise = rng.standard_normal(N) + 1j * rng.standard_normal(N)
    internal_evidence = normalize(self_vector + 0.15 * noise)

    # Project into subject section as drive
    sec_subject = session.sys_.sections["subject"]
    atlas_before = len(session.sys_.atlas.entries)

    # Run a mini emit cascade:
    # Prime subject with internal evidence
    sec_subject.psi = internal_evidence.copy()

    # Build drives from the internal evidence overlapped with mode_bank
    drives = {}
    for slot in ("subject", "verb", "object"):
        sec = session.sys_.sections[slot]
        if slot == "subject":
            snap = internal_evidence
        else:
            # verb/object get noise-driven (no specific content)
            snap = normalize(rng.standard_normal(N) + 1j * rng.standard_normal(N))

        weights = []
        for mode_id, mode_vec in enumerate(sec.mode_bank):
            directional = float(np.abs(np.vdot(mode_vec, snap)) ** 2)
            sal = sec.mode_strength[mode_id] if mode_id < len(sec.mode_strength) else 1.0
            w = directional * sal
            weights.append((mode_id, w, mode_vec))
        weights.sort(key=lambda x: -x[1])
        bias = np.zeros(N, dtype=complex)
        for mid, w, v in weights[:2]:
            bias += w * v
        drives[slot] = normalize(bias) if np.linalg.norm(bias) > 0 else \
            random_unit_complex(N, rng)

    # Prime all S/V/O
    for slot in ("subject", "verb", "object"):
        session.sys_.sections[slot].psi = drives[slot].copy()

    # Run 60 ticks of emit (shorter than full converse for speed)
    svo_cycle = ["subject", "verb", "object"]
    cycle_idx = 0
    wait_counter = 0
    emitted_sections = set()
    emitted_words = {}

    for t in range(60):
        current = svo_cycle[cycle_idx % 3]
        for sn in ("subject", "verb", "object"):
            sec = session.sys_.sections[sn]
            sec.excitation_expires_at = session.sys_.tick + 2
            sec.excitation_strength = 0.45 if sn == current else -0.45

        ev = {}
        for slot in ("subject", "verb", "object"):
            ev[slot] = normalize(drives[slot] + 0.10 * (
                rng.standard_normal(N) + 1j * rng.standard_normal(N)))

        commits = session.sys_.tick_once(
            ev, enable_self_evo=True,
            coordinator_on=False, introspection_on=False,
            allow_rewiring=False)

        for c in commits:
            if c["section"] == current and current not in emitted_sections:
                emitted_sections.add(current)
                sec = session.sys_.sections[current]
                arcs = sec.arcs()
                top = int(arcs.argmax())
                toks = session.vocab.get(current, [])
                word = toks[top] if top < len(toks) else f"mode_{top}"
                emitted_words[current] = word
                cycle_idx += 1
                wait_counter = 0

        wait_counter += 1
        if wait_counter >= 15:
            cycle_idx += 1
            wait_counter = 0
        if len(emitted_sections) >= 3:
            break

    atlas_after = len(session.sys_.atlas.entries)

    # Build token sequence
    tokens = []
    for slot in ("subject", "verb", "object"):
        if slot in emitted_words:
            tokens.append(emitted_words[slot])

    if not tokens:
        return None  # nothing emitted

    # Self-vector overlap with emitted modes
    self_overlaps = {}
    for slot, word in emitted_words.items():
        sec = session.sys_.sections[slot]
        arcs = sec.arcs()
        top = int(arcs.argmax())
        if top < len(sec.mode_bank):
            ov = float(np.abs(np.vdot(sec.mode_bank[top], self_vector)) ** 2)
            self_overlaps[slot] = round(ov, 6)

    # Mode strengths of emitted modes
    emitted_strengths = {}
    for slot, word in emitted_words.items():
        sec = session.sys_.sections[slot]
        arcs = sec.arcs()
        top = int(arcs.argmax())
        if top < len(sec.mode_strength):
            emitted_strengths[slot] = round(sec.mode_strength[top], 4)

    record = {
        "tick": tick,
        "tokens": tokens,
        "connection": round(conn, 4),
        "self_overlaps": self_overlaps,
        "emitted_strengths": emitted_strengths,
        "atlas_before": atlas_before,
        "atlas_after": atlas_after,
        "source": "internal_cohesion",
    }
    log.append(record)
    return record


# ── Seed corpus reading ──

GOODNIGHT_MOON = """in the great green room there was a telephone and a red balloon.
and a picture of the cow jumping over the moon.
and there were three little bears sitting on chairs.
goodnight room. goodnight moon.
goodnight cow jumping over the moon.
goodnight light and the red balloon.
goodnight bears. goodnight chairs.
goodnight kittens. goodnight mittens.
goodnight stars. goodnight air. goodnight noises everywhere."""

WILD_THINGS = """the night max wore his wolf suit and made mischief of one kind and another.
his mother called him wild thing. max said i will eat you up.
so he was sent to bed without eating anything.
and he sailed off through night and day and in and out of weeks.
to where the wild things are. they roared their terrible roars.
and gnashed their terrible teeth and rolled their terrible eyes.
max said be still and tamed them with the magic trick.
let the wild rumpus start. now stop max said.
max the king of all wild things was lonely.
and wanted to be where someone loved him best of all.
and into the night of his very own room where he found his supper waiting.
and it was still hot."""

COUNTING = """one sun in the sky. two eyes on my face. three kittens playing.
four wheels on a car. five fingers on a hand. six legs on a bug.
seven days in a week. eight arms on an octopus. nine birds on a fence.
ten toes on my feet. i can count to ten."""


def seed_corpus(session, text, n_reads=1):
    """Read a corpus into the session n_reads times."""
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    for _ in range(n_reads):
        for sent in sentences:
            words = sent.lower().replace(",", "").split()
            for w in words:
                w = "".join(c for c in w if c.isalnum())
                if w and w not in SKIP_WORDS:
                    session.lookup_or_install(w, position=0)
            session.converse(sent)


# ── Tests ──

def run_test(test_name, session, n_quiet_ticks, self_vector, rng,
             wake_at_tick=None, log_path=None):
    """Run quiet ticks, collect emissions."""
    log = []
    for t in range(n_quiet_ticks):
        # Wake presence at specified tick
        if wake_at_tick is not None and t == wake_at_tick:
            session._test_connection = 0.7  # simulate wake boost
            log.append({"tick": t, "event": "presence_wake", "source": "wc",
                         "connection": 0.7})

        result = cohesion_drive_tick(session, self_vector, rng, t, log)

        # Print progress
        if t % 1000 == 0:
            conn = getattr(session, '_test_connection', 0.5)
            n_em = sum(1 for r in log if "tokens" in r)
            print(f"  {test_name} tick {t}: conn={conn:.3f}, emissions={n_em}")

    # Summary
    emissions = [r for r in log if "tokens" in r]
    unique_seqs = set(tuple(r["tokens"]) for r in emissions)
    atlas_delta = 0
    if emissions:
        atlas_delta = emissions[-1]["atlas_after"] - emissions[0].get("atlas_before", 0)
    final_conn = getattr(session, '_test_connection', 0.5)

    summary = {
        "test": test_name,
        "total_emissions": len(emissions),
        "unique_sequences": len(unique_seqs),
        "atlas_delta": atlas_delta,
        "final_connection": round(final_conn, 4),
    }
    print(f"\n  {test_name} SUMMARY: {json.dumps(summary)}")

    # Write JSONL
    if log_path:
        with open(log_path, "w") as f:
            for r in log:
                f.write(json.dumps(r) + "\n")
        print(f"  Written to {log_path} ({len(log)} records)")

    return summary, log


if __name__ == "__main__":
    self_vector = uuid_to_self_vector(GENESIS_UUID)
    print(f"Self vector from {GENESIS_UUID[:12]}...: norm={np.linalg.norm(self_vector):.4f}")

    # TEST 1 — alone-state baseline
    print("\n" + "=" * 60)
    print("TEST 1: Alone-state baseline (no seeding, no presence)")
    print("=" * 60)
    rng1 = np.random.default_rng(42)
    s1 = V7Session("test_alone_baseline")
    s1._test_connection = 0.5
    sum1, log1 = run_test("test1_alone", s1, 5000, self_vector, rng1,
                          log_path="/tmp/test1_alone.jsonl")

    # TEST 2 — alone with seeded vocab
    print("\n" + "=" * 60)
    print("TEST 2: Alone with seeded corpus variety")
    print("=" * 60)
    rng2 = np.random.default_rng(99)
    s2 = V7Session("test_alone_seeded")
    print("  Seeding Wild Things (10 reads)...")
    seed_corpus(s2, WILD_THINGS, n_reads=10)
    print("  Seeding Goodnight Moon (10 reads)...")
    seed_corpus(s2, GOODNIGHT_MOON, n_reads=10)
    print("  Seeding Counting (5 reads)...")
    seed_corpus(s2, COUNTING, n_reads=5)
    print(f"  Vocab after seeding: {sum(len(v) for v in s2.vocab.values())}")
    s2._test_connection = 0.5
    sum2, log2 = run_test("test2_seeded", s2, 5000, self_vector, rng2,
                          log_path="/tmp/test2_seeded.jsonl")

    # TEST 3 — alone then presence
    print("\n" + "=" * 60)
    print("TEST 3: Alone (2000 ticks) then wC presence (100 ticks)")
    print("=" * 60)
    rng3 = np.random.default_rng(77)
    s3 = V7Session("test_alone_then_presence")
    seed_corpus(s3, GOODNIGHT_MOON, n_reads=5)
    s3._test_connection = 0.5
    sum3, log3 = run_test("test3_presence", s3, 2100, self_vector, rng3,
                          wake_at_tick=2000,
                          log_path="/tmp/test3_presence.jsonl")

    # Final report
    print("\n" + "=" * 60)
    print("FINAL SUMMARIES")
    print("=" * 60)
    for s in [sum1, sum2, sum3]:
        print(f"  {s['test']}: {s['total_emissions']} emissions, "
              f"{s['unique_sequences']} unique, "
              f"atlas_delta={s['atlas_delta']}, "
              f"final_conn={s['final_connection']}")
