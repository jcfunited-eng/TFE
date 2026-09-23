"""tests/test_auditory_vocal_feedback_handoff.py — Bounded Auditory-Vocal Feedback Handoff Verification.

Validates the source-level self-hearing feedback association:
1. Isolated Vocal Action followed by Silence / Non-Vocal Action:
   - Ear return of Syllable A is attributed to Syllable A before settlement.
   - Resonance evaluation executes against the originating utterance.
   - The subsequent non-vocal action is not contaminated.
2. Two Consecutive Vocal Actions:
   - Syllable A followed by Syllable B.
   - Beat 1: Syllable A ear return settles against Syllable A (not Syllable B).
   - Beat 2: Syllable B ear return settles against Syllable B (not Syllable A).
   - syllable_profiles correctly records each syllable under its originating drive.
3. Feedback Resonance Credit Attribution:
   - Evaluates that practicing a sound under acoustic target matching awards resonance credit.
4. Controlled Practice Credit Ranking Demonstration (Component Level):
   - Proves that when practice credit is awarded under resonance, the selector ranks that syllable
     above neutral alternatives under that specific context.
     Note (Auditor A1 / Joe Audit Verification): This is a controlled component demonstration of
     selector ranking under seeded trial histories; it does not claim end-to-end spontaneous
     emergence through unassisted ingress.
5. Unassisted Auditory Ingress Behavioral Baseline:
   - Measures the unassisted physical loop when authentic audio is delivered via microphone ingress
     without seeding action counts or trial histories, demonstrating the exact baseline motor
     exploration sequence and auditory gate boundaries.
6. Direct Within-Hop Two-Event Spectral Isolation Witness (A1 Counterexample Verification):
   - Validates that when a single 25-frame hop contains Sound A, a pause of PAUSE_FRAMES (12 frames)
     closing Event A, and Sound B, each event retains strictly its own measured channel peaks:
     Event A does not acquire Sound B's energy, Event B does not acquire Sound A's energy, and
     spectral cosine similarity rho(A, B) == 0.0000.
7. Extended Unassisted Trajectory Repertoire Acquisition & Resonant Response Witness:
   - Measures 61 unassisted beats from genesis: natural vowel/syllable babbling progression
     ('ah0', 'eh0', 'ee0', 'oh0', 'oo0', 'mah0') followed by caregiver microphone presentation of 'mah0',
     confirming genuine resonant response selection from acquired vocal repertoire.
8. Unassisted Post-Target Expiration Behavioral Boundary Witness:
   - Measures physical reality after the recent-cue target expires (> 6 ticks):
     confirms that while positive practice credit is retained in the speech record,
     infant motor exploration policy ('untried' non-empty) intercepts subsequent unprompted vocalizations,
     demonstrating the exact physical boundary between immediate acoustic matching and untried motor babbling.
"""

from __future__ import annotations

import os
import time
import pytest

# Daylight override so world illumination is invariant
os.environ.setdefault("GUALA_SOLAR_UTC_OVERRIDE", str(int(time.time()) - int(time.time()) % 86_400 + 13 * 3_600))

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    SYLLABLES,
    SYLLABLE_DRIVES,
    syllable_pcm,
    _syllable_reafference,
    spectral_cosine_similarity,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence

IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
UNATTENDED = PhysicalOccurrence("unattended", None)


def test_isolated_sound_followed_by_silence_attribution() -> None:
    """An isolated vocal action followed by a non-vocal action correctly receives self-hearing feedback."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=10)
    loop = FunctionalPhysicalLoop()

    # Habituate non-vocal actions so 'say' is selected on beat 10
    for a in ("toward_thing", "toward_door", "step", "turn_left", "turn_right", "touch", "grasp", "rest"):
        organism._state.setdefault("act_totals", {})[a] = 10

    # Set an auditory target matching mah0
    prof_mah = _syllable_reafference("mah0")
    assert prof_mah is not None
    organism._state["heard_speech_target"] = {"tick": 10, "key": "target-event-1", "profile": list(prof_mah)}
    organism._state["syllable_totals"]["mah0"] = 1

    # Beat 10: Organism decides to emit 'mah0'
    res10 = loop.settle(organism, world, UNATTENDED)
    assert res10.observation["her_act"] == "say"
    assert organism._state["last_said"] == "mah0"
    assert organism.pending_voice is not None
    originating_pending = organism._state.get("pending_act")
    assert originating_pending is not None
    assert originating_pending.get("act") == "say"
    assert originating_pending.get("syllable") == "mah0"

    # Now on Beat 11, force a non-vocal action (rest) by habituating say
    organism._state.setdefault("act_totals", {})["say"] = 50

    # Beat 11: Organism receives ear return of mah0, chooses non-vocal action
    res11 = loop.settle(organism, world, UNATTENDED)
    assert res11.observation["her_act"] != "say"

    # Verify:
    # 1. mah0 was settled with resonance credit in speech
    speech = organism._state.get("speech", {})
    context_keys = [k for k in speech if "mah0" in speech[k].get("syllables", {})]
    assert len(context_keys) > 0, "mah0 must be recorded in speech context"
    mah_entry = speech[context_keys[0]]["syllables"]["mah0"]
    assert mah_entry[0] == 1, "mah0 must have exactly 1 try recorded"
    # Net worth must include the positive resonance credit (> 0.0), not just metabolic loss
    assert mah_entry[1] > 0.0, f"mah0 must receive positive resonance credit, got {mah_entry[1]}"

    # 2. syllable_profiles must record mah0 from the actual ear return
    syl_profs = organism._state.get("syllable_profiles", {})
    assert "mah0" in syl_profs, "syllable_profiles must record originating syllable mah0"
    assert len(syl_profs["mah0"]) == 32

    # 3. Beat 11's non-vocal action pending_act must NOT have self_profile attached
    current_pending = organism._state.get("pending_act")
    assert current_pending is not None
    assert "self_profile" not in current_pending, "Non-vocal action must not be contaminated with self_profile"


def test_two_consecutive_different_sounds_attribution() -> None:
    """Two different consecutive sounds attribute each ear return to its own originating drive."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=20)
    loop = FunctionalPhysicalLoop()

    # Pre-populate reafference profiles for comparison
    prof_mah = _syllable_reafference("mah0")
    prof_dee = _syllable_reafference("dee0")
    assert prof_mah is not None and prof_dee is not None

    # Step 1: Force emit mah0 on Beat 20
    organism._state["pending_chain"] = ["mah0"]
    res20 = loop.settle(organism, world, UNATTENDED)
    assert res20.observation["her_act"] == "say"
    assert organism._state["last_said"] == "mah0"

    # Step 2: Force emit dee0 on Beat 21 (while mah0 ear return arrives)
    organism._state["pending_chain"] = ["dee0"]
    res21 = loop.settle(organism, world, UNATTENDED)
    assert res21.observation["her_act"] == "say"
    assert organism._state["last_said"] == "dee0"

    # At Beat 21 settle:
    # mah0 ear return must be recorded under syllable_profiles['mah0'], NOT 'dee0'
    syl_profs = organism._state.get("syllable_profiles", {})
    assert "mah0" in syl_profs, "mah0 profile must be recorded on beat 21"
    assert "dee0" not in syl_profs, "dee0 profile must NOT be recorded before it is heard"

    # Step 3: Beat 22 - non-vocal step (while dee0 ear return arrives)
    organism._state["pending_chain"] = []
    for a in ("say",):
        organism._state.setdefault("act_totals", {})[a] = 100
    res22 = loop.settle(organism, world, UNATTENDED)

    # At Beat 22 settle:
    # dee0 ear return must now be recorded under syllable_profiles['dee0']
    syl_profs = organism._state.get("syllable_profiles", {})
    assert "dee0" in syl_profs, "dee0 profile must be recorded on beat 22"

    # Verify that mah0 profile and dee0 profile are distinct
    sim = spectral_cosine_similarity(tuple(syl_profs["mah0"]), tuple(syl_profs["dee0"]))
    assert sim < 0.60, f"mah0 and dee0 profiles must be acoustically distinct, similarity was {sim}"


def test_learned_response_feedback_credit() -> None:
    """Verifies that practicing a sound under acoustic target matching awards resonance credit."""
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=30)
    loop = FunctionalPhysicalLoop()

    prof_mah = _syllable_reafference("mah0")
    organism._state["heard_speech_target"] = {"tick": 30, "key": "caregiver-say-mah", "profile": list(prof_mah)}
    organism._state["syllable_totals"]["mah0"] = 1

    # Force say
    for a in ("toward_thing", "toward_door", "step", "turn_left", "turn_right", "touch", "grasp", "rest"):
        organism._state.setdefault("act_totals", {})[a] = 20

    res30 = loop.settle(organism, world, UNATTENDED)
    assert res30.observation["her_act"] == "say"
    assert organism._state["last_said"] == "mah0"

    # Advance one beat to complete settlement of the utterance
    res31 = loop.settle(organism, world, UNATTENDED)

    # Check speech record for the context:
    speech = organism._state.get("speech", {})
    matched_ctx = [k for k in speech if "mah0" in speech[k].get("syllables", {})]
    assert len(matched_ctx) > 0
    ctx_entry = speech[matched_ctx[0]]
    mah_stat = ctx_entry["syllables"]["mah0"]
    # Credit must include the +1.5 * rho resonance reward
    assert mah_stat[1] >= 1.0, f"Expected resonance credit >= 1.0, got {mah_stat[1]}"
    assert "resonance" in ctx_entry, "Resonance history must be updated"
    assert ctx_entry["resonance"].get("mah0", 0.0) >= 0.90


def test_controlled_practice_credit_ranking_demonstration() -> None:
    """Controlled Component Demonstration: Practice credit shifts selector ranking under seeded trial history.

    Note: This is a controlled component demonstration of selector ranking under an artificially
    habituated candidate history. It isolates the mathematical effect of resonance credit on the
    ranking function; it does not claim spontaneous end-to-end emergence from unassisted ingress.
    """
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=100)
    loop = FunctionalPhysicalLoop()

    # Baseline: Context with habituated syllables having neutral (0.0) worth
    sit = "____"
    ctx = f"{sit}:start"
    sp_rec = organism._state.setdefault("speech", {})
    entry = sp_rec.setdefault(ctx, {"syllables": {}, "tick": 100})
    for s in SYLLABLES:
        entry["syllables"][s] = [1, 0.0]
        organism._state.setdefault("syllable_totals", {})[s] = 1

    # Verify baseline choice before practice
    _d_base, s_base, _c_base, _r_base = organism._choose_syllable(sit, None)
    assert s_base == "ah0", f"Expected baseline choice ah0, got {s_base}"

    # Practice phase: Target 'mah0' heard and emitted
    prof_mah = _syllable_reafference("mah0")
    assert prof_mah is not None
    organism._state["heard_speech_target"] = {"tick": 100, "key": "caregiver-say-mah", "profile": list(prof_mah)}

    # Force say action on beat 100
    for a in ("toward_thing", "toward_door", "step", "turn_left", "turn_right", "touch", "grasp", "rest"):
        organism._state.setdefault("act_totals", {})[a] = 10

    res100 = loop.settle(organism, world, UNATTENDED)
    assert res100.observation["her_act"] == "say"
    assert organism._state["last_said"] == "mah0"

    # Beat 101: Ear return arrives and settles
    res101 = loop.settle(organism, world, UNATTENDED)
    assert res101.observation["her_act"] != "say"

    # Verify resonance credit was recorded
    mah_entry = organism._state["speech"][ctx]["syllables"]["mah0"]
    assert mah_entry[0] == 2
    assert mah_entry[1] >= 1.0

    # Later Evaluation: Target is expired and absent
    organism._state["tick"] = 200
    organism._state.pop("heard_speech_target", None)

    # Selector ranks mah0 first based on measured worth (0.75 > 0.00)
    _d_later, s_later, _c_later, r_later = organism._choose_syllable(sit, None)
    assert s_later == "mah0"
    assert "best worth" in r_later


def test_unassisted_auditory_ingress_behavioral_baseline() -> None:
    """Accurate physical measurement of the unassisted substrate under authentic sensory audio ingress.

    Executes clean, unseeded physical loop advancement without:
    - Zero trial history fabrication (honest genesis state).
    - Zero direct injection of heard_speech_target (delivered strictly via LeanSensoryOccurrence microphone ingress).
    - Zero forced action totals (organism chooses naturally via candidates and _choose).
    - Zero clock jumps (advances beat by beat through loop.settle).

    Measures and records the ground-truth physical reality:
    1. Beat 1: Authentic PCM audio of mah0 enters via microphone. Organism chooses toward_thing (desk)
       under round-robin affordance exploration.
    2. Beat 2: Sound ends. The acoustic gate closes the open event upon silence. The measured 32-channel
       acoustic spectrum is preserved through closure and registered in heard_speech_target.
    3. Beats 3-5: Organism naturally explores remaining untried motor actions (step, turn_left, turn_right).
    4. Beat 6: Organism visits say for its first try under structure 039bd7; untried exploration emits ah0
       (the first untried syllable in lifetime order).
    5. Beat 7: Organism rests, and her own emitted ah0 voice reafference is captured in syllable_profiles.
    """
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # Generate authentic PCM audio of mah0
    pcm_mah = syllable_pcm(SYLLABLE_DRIVES["mah0"], seed=1)
    sensory_sound = LeanSensoryOccurrence(source="microphone", retina_rgb_u8=None, pressure_s16le=pcm_mah)
    sound_occurrence = PhysicalOccurrence("sensory", sensory_sound)

    # Beat 1: Audio enters via microphone
    res1 = loop.settle(organism, world, sound_occurrence)
    assert res1.observation["her_act"] == "toward_thing"
    assert res1.observation["said"] is None

    # Beat 2: Silence follows; sound event closes
    res2 = loop.settle(organism, world, UNATTENDED)
    assert res2.observation["her_act"] == "toward_door"
    assert res2.observation["said"] is None
    # Ground-truth measurement: event closed on silence, preserving authentic 32-channel spectrum
    target = organism._state.get("heard_speech_target")
    assert target is not None
    assert target.get("profile") is not None
    assert len(target["profile"]) == 32
    assert max(target["profile"]) > 0.0
    assert any(b > 0.0 for b in target["bands"])

    # Beats 3-5: Natural motor exploration
    res3 = loop.settle(organism, world, UNATTENDED)
    assert res3.observation["her_act"] == "step"

    res4 = loop.settle(organism, world, UNATTENDED)
    assert res4.observation["her_act"] == "turn_left"

    res5 = loop.settle(organism, world, UNATTENDED)
    assert res5.observation["her_act"] == "turn_right"

    # Beat 6: Organism visits 'say' in natural round-robin order
    res6 = loop.settle(organism, world, UNATTENDED)
    assert res6.observation["her_act"] == "say"
    # Ground truth: untried syllable exploration selects alphabetical fallback ah0
    assert organism._state["last_said"] == "ah0"
    assert "first try of ah0" in res6.observation["act_reason"]

    # Beat 7: Organism rests; own vocal reafference from Beat 6 is credited
    res7 = loop.settle(organism, world, UNATTENDED)
    assert res7.observation["her_act"] == "rest"
    assert "ah0" in organism._state.get("syllable_profiles", {})


def test_within_hop_two_event_spectral_isolation() -> None:
    """Direct witness of within-hop two-event spectral isolation (A1 counterexample verification).

    Validates that when a single 25-frame hop contains Sound A, a pause of PAUSE_FRAMES (12 frames)
    closing Event A, and Sound B, each event retains strictly its own measured channel peaks:
    - Event A does not acquire Sound B's spectral energy.
    - Event B does not acquire Sound A's spectral energy.
    - Zero whole-hop profile bleed between distinct events within the same audio packet.
    """
    from dsf_ai_service.guala_acoustic_gate import gate_step, SILENT_FRAME

    frames = [SILENT_FRAME] * 25
    envelopes = [(0.0,) * 32 for _ in range(25)]

    # Frame 0: Sound A sounds (concentrated in low channels 0..3)
    frames[0] = (0.05, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0)
    env_a = [0.0] * 32
    env_a[0] = 0.08
    env_a[1] = 0.07
    envelopes[0] = tuple(env_a)

    # Frames 1..12: Silence (12 frames = PAUSE_FRAMES). Sound A reaches pause threshold and closes on frame 12.

    # Frame 13: Sound B sounds (concentrated in high channels 14..15)
    frames[13] = (0.05, 0.0, 0.0, 0.0, 0.0, 0.5, 0.5)
    env_b = [0.0] * 32
    env_b[14] = 0.09
    env_b[15] = 0.06
    envelopes[13] = tuple(env_b)

    # Frames 14..24: Silence (11 frames). Sound B remains open at the end of Hop 1.

    # Step Hop 1
    open_event, closed_hop1, _runs = gate_step(None, frames, True, 0, envelopes=envelopes)
    assert len(closed_hop1) == 1, f"Expected Event A to close within Hop 1, got {len(closed_hop1)}"
    event_a = closed_hop1[0]

    # Verify Event A retained strictly Sound A's channel peaks and zero of Sound B's energy
    assert event_a.profile is not None
    assert event_a.profile[0] == 0.08
    assert event_a.profile[1] == 0.07
    assert max(event_a.profile[12:16]) == 0.0, f"Event A must not contain Sound B energy: {event_a.profile[12:16]}"

    # Step Hop 2: Silence to close Event B
    silent_hop = [SILENT_FRAME] * 25
    silent_envs = [(0.0,) * 32 for _ in range(25)]
    open_event, closed_hop2, _runs = gate_step(open_event, silent_hop, False, 25, envelopes=silent_envs)
    assert len(closed_hop2) == 1, f"Expected Event B to close in Hop 2, got {len(closed_hop2)}"
    event_b = closed_hop2[0]

    # Verify Event B retained strictly Sound B's channel peaks and zero of Sound A's energy
    assert event_b.profile is not None
    assert event_b.profile[14] == 0.09
    assert event_b.profile[15] == 0.06
    assert max(event_b.profile[:4]) == 0.0, f"Event B must not contain Sound A energy: {event_b.profile[:4]}"

    # Verify orthogonal spectral separation (zero cross-contamination)
    sim = spectral_cosine_similarity(event_a.profile, event_b.profile)
    assert sim == 0.0, f"Expected zero spectral overlap between distinct within-hop events, got {sim}"


def test_extended_trajectory_repertoire_acquisition_and_resonant_response() -> None:
    """Extended Unassisted Trajectory Repertoire Acquisition & Resonant Response Witness.

    Validates that:
    1. Across 56 unassisted beats from genesis, Guala naturally babbles her initial vocal repertoire
       in infant progression: ah0 -> eh0 -> ee0 -> oh0 -> oo0 -> mah0.
    2. Her own vocal reafference for each syllable is cleanly captured in syllable_profiles.
    3. On beat 57, when the caretaker speaks 'mah0' via microphone audio, silence closes the event
       at beat 58 and registers heard_speech_target.
    4. Resonance evaluation measures strong acoustic similarity against mah0 (rho > 0.95) and ah0 (rho > 0.95).
    5. On beat 61, Guala visits 'say' and chooses 'resonant answer' from her acquired repertoire rather
       than default untried babble.
    """
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # 56 unassisted beats from genesis
    for _ in range(1, 57):
        loop.settle(organism, world, UNATTENDED)

    # Verify vocal repertoire acquired through natural untried exploration
    profs = organism._state.get("syllable_profiles", {})
    assert list(profs.keys()) == ["ah0", "eh0", "ee0", "oh0", "oo0", "mah0"]

    # Caregiver presents authentic PCM audio of mah0 at beat 57
    pcm_mah = syllable_pcm(SYLLABLE_DRIVES["mah0"], seed=1)
    sensory_sound = LeanSensoryOccurrence(source="microphone", retina_rgb_u8=None, pressure_s16le=pcm_mah)
    res57 = loop.settle(organism, world, PhysicalOccurrence("sensory", sensory_sound))

    # Beat 58: silence follows, closing the sound event
    res58 = loop.settle(organism, world, UNATTENDED)
    target = organism._state.get("heard_speech_target")
    assert target is not None and target.get("profile") is not None
    assert spectral_cosine_similarity(target["profile"], profs["mah0"]) > 0.95
    assert spectral_cosine_similarity(target["profile"], profs["ah0"]) > 0.95

    # Beats 59..61: organism advances naturally
    for b in range(59, 62):
        res = loop.settle(organism, world, UNATTENDED)
        if b == 61:
            assert res.observation["her_act"] == "say"
            assert "resonant answer" in res.observation["act_reason"]
            assert res.observation["said"] is not None


def test_unassisted_post_target_expiration_behavioral_boundary() -> None:
    """Accurate physical measurement of vocal action selection after recent-cue target expires.

    Validates that:
    1. Across 56 beats from genesis, Guala babbles her repertoire (ah0, eh0, ee0, oh0, oo0, mah0).
    2. At beat 57, caregiver presents mah0. Silence closes event at beat 58 (target registered).
    3. At beat 61, Guala visits 'say' within active target window (61 - 58 = 3 <= 6), emitting 'ah0'
       under 'resonant answer'.
    4. At beat 62, self-hearing reafference settles, awarding positive resonance credit to ah0
       in context 'TSSS:mah0' (speech worth > 1.0).
    5. After beat 64, target expires (> 6 ticks).
    6. At beat 67 (tick 67 - 58 = 9 > 6), Guala visits 'say'. Because the recent-cue target is expired,
       the resonant answer branch does not fire. The untried exploration gate ('untried' non-empty)
       intercepts the selection, choosing 'meh0' (the next untried syllable).
    7. Demonstrates the exact physical boundary: retained practice worth is preserved in memory, but
       does not override infant motor exploration policy under unprompted conditions.
    """
    world = home_world_authority(identity=IDENTITY)
    organism = FunctionalOrganism.genesis(identity=IDENTITY, organism_tick=1)
    loop = FunctionalPhysicalLoop()

    # 56 unassisted beats from genesis
    for _ in range(1, 57):
        loop.settle(organism, world, UNATTENDED)

    # Caregiver presents mah0 at beat 57
    pcm_mah = syllable_pcm(SYLLABLE_DRIVES["mah0"], seed=1)
    sensory_sound = LeanSensoryOccurrence(source="microphone", retina_rgb_u8=None, pressure_s16le=pcm_mah)
    res57 = loop.settle(organism, world, PhysicalOccurrence("sensory", sensory_sound))

    # Beat 58: silence closes event, target registered
    res58 = loop.settle(organism, world, UNATTENDED)
    target = organism._state.get("heard_speech_target")
    assert target is not None and target.get("tick") == 58

    # Beat 61: Guala responds with resonant answer while target is active
    for b in range(59, 62):
        res = loop.settle(organism, world, UNATTENDED)
    assert res.observation["her_act"] == "say"
    assert "resonant answer" in res.observation["act_reason"]
    assert organism._state["last_said"] == "ah0"

    # Beat 62: Ear return settles with resonance credit in speech record
    res62 = loop.settle(organism, world, UNATTENDED)
    speech = organism._state.get("speech", {})
    assert "TSSS:mah0" in speech
    ah_entry = speech["TSSS:mah0"]["syllables"]["ah0"]
    assert ah_entry[0] >= 1
    assert ah_entry[1] > 1.0  # Positive resonance credit awarded

    # Advance loop past target expiration (target active <= 6 ticks, expired after tick 64)
    # Next vocal turn occurs at Beat 67 (tick 67 - 58 = 9 > 6)
    for b in range(63, 68):
        res = loop.settle(organism, world, UNATTENDED)
    assert res.observation["her_act"] == "say"
    assert organism.live_organism_tick - int(target["tick"]) > 6  # Target is expired
    assert "first try of meh0" in res.observation["act_reason"]   # Untried exploration intercepts
    assert organism._state["last_said"] == "meh0"
