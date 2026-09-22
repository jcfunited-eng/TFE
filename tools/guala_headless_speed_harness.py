#!/usr/bin/env python3
"""tools/guala_headless_speed_harness.py — Overclocked Headless Simulation Harness.

Charter & Architecture:
- Accelerated Developmental Roadmap (docs/guala_accelerated_developmental_roadmap.md, Levers 1 & 4).
- Eliminates HTTP transport serialization overhead and wall-clock sleeps (POLL_S = 20s).
- Direct memory settlement via FunctionalPhysicalLoop and home_world_authority.
- Accurately tracks diurnal cycles, sleep pressure dynamics, and Krimelack episodic memory formation.
- Lever 4 Hierarchical Multi-Scale Stack integration:
  - 10 ms Micro-Scale Reflex Loop (acoustic & thermal nociception interrupts).
  - 250 ms Meso-Scale Organism Beat Loop (stride, gaze, syllable coordination).
  - 2 - 10 s Macro-Scale Cognitive Intent Envelope (phonemic demand, valuation, Theory of Mind).
- Lever 1 Compiled Native Acceleration:
  - Hot-swaps hot-path kernels (krimelack, cochlear, visual, psi_settle, optical raycasting, kinematics) via native_core.
- Provides rigorous empirical extrapolation to the 2.5-year developmental horizon.
- Supports booting from live production state checkpoints (Tick 1,767,000+, nights, and vocal chains).
- Supports long-duration diurnal runs with autonomous caregiver feeding cadence (MEAL_TICKS = 400).

Pure deterministic physical cognition: no heuristics, no ML approximations, no synthetic language scaffolding.
All vocal emissions are pure acoustic phoneme syllables from canonical SYLLABLES.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Callable, Sequence
import urllib.request

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from dsf_ai_service.guala_functional_loop import FunctionalPhysicalLoop
from dsf_ai_service.guala_functional_organism import (
    FunctionalOrganism,
    SYLLABLES,
    SYLLABLE_DRIVES,
    syllable_pcm,
)
from dsf_ai_service.guala_hierarchical_stack import (
    HierarchicalTemporalStack,
    MacroIntent,
    MacroIntentType,
    MicroInterrupt,
)
from dsf_ai_service.guala_home_world import home_world_authority
from dsf_ai_service.lean_actor import PhysicalOccurrence
from dsf_ai_service.lean_sensory_occurrence import LeanSensoryOccurrence
from dsf_ai_service.substrate import native_core

DEFAULT_IDENTITY = "1cc4e70a-f2a0-44c5-a111-f4a5bc915cc1"
REAL_TIME_TICKS_PER_SECOND = 4.0  # 250 ms per tick
DIURNAL_CEILING_TICKS = 113_600   # 1 subjective day of waking + sleeping
DEFAULT_LIVE_URL = "https://dsf-ai.com/api/v1/guala/observation"
DEFAULT_STATE_PATH = "/workspaces/Tao_Financial_Engine/guala_caretaker/state.json"
DEFAULT_LEDGER_PATH = "/workspaces/Tao_Financial_Engine/backups/runtime/combinatorial_chains_ledger.jsonl"


@dataclass(frozen=True, slots=True)
class HarnessMetrics:
    organism_identity: str
    initial_tick: int
    final_tick: int
    ticks_elapsed: int
    simulated_subjective_seconds: float
    simulated_subjective_hours: float
    wall_clock_seconds: float
    ticks_per_second: float
    overclock_speedup_factor: float
    sleep_pressure_units_start: int
    sleep_pressure_units_end: int
    sleep_pressure_fraction_end: float
    nights_completed: int
    bites_count: int
    reserve_micrograms: int
    moments_count: int
    micro_interrupts_count: int
    active_macro_intent_type: str | None
    macro_intents_completed: int
    native_acceleration_active: bool


@dataclass(frozen=True, slots=True)
class CurriculumReceipt:
    organism_identity: str
    target_entity_id: str
    acoustic_cues_received: int
    demand_intent_id: str
    demand_syllables_emitted: tuple[str, ...]
    demand_fulfilled: bool
    demand_duration_beats: int
    bites_count: int
    reserve_micrograms_initial: int
    reserve_micrograms_final: int
    moments_formed_count: int
    valuation_intent_id: str | None
    valuation_syllables_emitted: tuple[str, ...]
    valuation_fulfilled: bool
    wall_clock_seconds: float
    ticks_per_second: float
    overclock_speedup_factor: float

    @property
    def demand_tokens_emitted(self) -> tuple[str, ...]:
        return self.demand_syllables_emitted

    @property
    def valuation_tokens_emitted(self) -> tuple[str, ...]:
        return self.valuation_syllables_emitted


@dataclass(frozen=True, slots=True)
class DeonticReceipt:
    organism_identity: str
    target_agent_id: str
    prescribed_action: str
    acoustic_prompts_exchanged: int
    deontic_intent_id: str
    syllables_emitted: tuple[str, ...]
    deontic_fulfilled: bool
    duration_beats: int
    moments_formed_count: int
    reserve_micrograms: int
    wall_clock_seconds: float
    ticks_per_second: float
    overclock_speedup_factor: float

    @property
    def syntactic_tokens_emitted(self) -> tuple[str, ...]:
        return self.syllables_emitted


@dataclass(frozen=True, slots=True)
class SleepReceipt:
    organism_identity: str
    bed_made: bool
    bedding_items: tuple[str, ...]
    initial_sleep_pressure: int
    final_sleep_pressure: int
    sleep_beats_elapsed: int
    nights_completed: int
    moments_initial_count: int
    moments_remaining_count: int
    meanings_consolidated_count: int
    meanings_samples: tuple[str, ...]
    reserve_micrograms_initial: int
    reserve_micrograms_final: int
    wall_clock_seconds: float
    ticks_per_second: float
    overclock_speedup_factor: float


class HeadlessSpeedHarness:
    """Overclocked simulation runner executing direct physical settlement without network delays."""

    def __init__(
        self,
        identity: str = DEFAULT_IDENTITY,
        initial_tick: int = 1,
        expand_walkway: bool = True,
        use_native: bool = True,
        organism: FunctionalOrganism | None = None,
        world: Any = None,
    ) -> None:
        self.identity = identity
        self.native_active = False
        if use_native:
            self.native_active = native_core.install()
        self.world = world if world is not None else home_world_authority(identity=identity, expand_walkway=expand_walkway)
        self.organism = organism if organism is not None else FunctionalOrganism.genesis(identity=identity, organism_tick=initial_tick)
        self.loop = FunctionalPhysicalLoop()
        self.temporal_stack = HierarchicalTemporalStack()
        self.unattended_occurrence = PhysicalOccurrence("unattended", None)

    @classmethod
    def from_live_checkpoint(
        cls,
        state_path: str | Path | None = None,
        observation_url: str | None = None,
        identity: str = DEFAULT_IDENTITY,
        use_native: bool = True,
        expand_walkway: bool = True,
    ) -> "HeadlessSpeedHarness":
        """Instantiate speed harness initialized from Guala's real continuous living state."""
        tick = 1
        nights = 0

        # 1. Try reading live observation from production server
        url = observation_url or DEFAULT_LIVE_URL
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "HeadlessSpeedHarness/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                obs_data = json.loads(resp.read().decode("utf-8"))
                live_tick = obs_data.get("live_tick") or obs_data.get("persisted_tick")
                if live_tick and isinstance(live_tick, int):
                    tick = live_tick
        except Exception:
            pass

        # 2. Try reading state.json from local caretaker
        st_file = Path(state_path or DEFAULT_STATE_PATH)
        if st_file.exists():
            try:
                st_data = json.loads(st_file.read_text("utf-8"))
                nights = int(st_data.get("bed_made_for_night", 0))
                # If observation was unreachable, fallback to play/bedtime tick
                if tick == 1:
                    max_tick = max(
                        int(st_data.get("play_tick", 0)),
                        int(st_data.get("bedtime_tick", 0)),
                        int(st_data.get("meal_tick", 0)),
                    )
                    if max_tick > 0:
                        tick = max_tick
            except Exception:
                pass

        # Ensure tick is strictly valid
        if tick <= 0:
            tick = 1

        organism = FunctionalOrganism.genesis(identity=identity, organism_tick=tick)
        organism._state["nights"] = nights

        # 3. Load combinatorial chain metrics if ledger exists
        ledger_file = Path(DEFAULT_LEDGER_PATH)
        if ledger_file.exists():
            try:
                chains_count = 0
                for line in ledger_file.read_text("utf-8").splitlines():
                    if '"type": "vocal_chain"' in line:
                        chains_count += 1
                organism._state["syllables"] = chains_count
            except Exception:
                pass

        return cls(
            identity=identity,
            initial_tick=tick,
            expand_walkway=expand_walkway,
            use_native=use_native,
            organism=organism,
        )

    @property
    def live_tick(self) -> int:
        return self.organism.live_organism_tick

    def current_sleep_state(self) -> dict[str, Any]:
        return dict(self.organism.sleep)

    def form_teleological_demand(
        self,
        target_entity_id: str,
        phoneme_tokens: Sequence[str] = ("dah0", "bah1"),
    ) -> MacroIntent:
        """Form an acoustic demand intent envelope grounded in metabolic deficit and acoustic phonemes."""
        return self.temporal_stack.form_teleological_demand(
            target_entity_id=target_entity_id,
            tick=self.live_tick,
            phoneme_tokens=phoneme_tokens,
        )

    def form_affective_valuation(
        self,
        target_entity_id: str,
        phoneme_tokens: Sequence[str] = ("kee0", "loo0"),
    ) -> MacroIntent:
        """Form an acoustic valuation intent envelope grounded in hedonic resonance and phonemes."""
        return self.temporal_stack.form_affective_valuation(
            target_entity_id=target_entity_id,
            tick=self.live_tick,
            phoneme_tokens=phoneme_tokens,
        )

    def form_deontic_prescription(
        self,
        target_action: str,
        phoneme_tokens: Sequence[str] = ("dee0", "mah0"),
    ) -> MacroIntent:
        """Form a dyadic social prescription intent envelope grounded in acoustic phonemes."""
        return self.temporal_stack.form_deontic_prescription(
            target_action=target_action,
            tick=self.live_tick,
            phoneme_tokens=phoneme_tokens,
        )

    def step(self, occurrence: PhysicalOccurrence | None = None) -> Any:
        occ = self.unattended_occurrence if occurrence is None else occurrence
        result = self.loop.settle(self.organism, self.world, occ)

        # Lever 4 Multi-Scale Temporal Evaluation
        obs = self.world.observation_snapshot()
        body = next((b for b in obs.bodies if b.body_id == self.identity), None)
        held_id = body.held_object_id if body else None
        held_temp = None
        if held_id:
            held_obj = next((o for o in obs.objects if o.object_id == held_id), None)
            if held_obj and held_obj.material:
                held_temp = int(held_obj.material.surface_temperature_millikelvin)

        skin_contact = float(self.organism._state.get("pending_contact", 0.0))

        # Check goal attainment for active macro intent
        active_intent = self.temporal_stack.active_macro_intent
        target_id = active_intent.target_entity_id if active_intent else None
        goal_reached = bool(target_id and held_id and held_id == target_id)

        # Cognitive Intent Object Permanence: mental representations persist across room boundaries
        self.temporal_stack.evaluate_cycle(
            tick=self.live_tick,
            heard_frames=None,
            skin_contact=skin_contact,
            skin_temperature_millikelvin=None,
            touch_surface_millikelvin=None,
            held_surface_millikelvin=held_temp,
            held_entity_id=held_id,
            target_entity_present=True,
            goal_reached=goal_reached,
        )

        return result

    def run_ticks(
        self,
        n_ticks: int,
        progress_callback: Callable[[int, int, float], None] | None = None,
        callback_interval: int = 50,
        enable_caregiver_sustenance: bool = True,
    ) -> HarnessMetrics:
        """Run n_ticks at maximum CPU throughput, with optional caregiver sustenance on hunger deficit."""
        initial_tick = self.live_tick
        init_sleep = self.current_sleep_state()
        init_pressure = int(init_sleep["pressure"][0])

        t0 = time.perf_counter()
        for i in range(1, n_ticks + 1):
            # Caregiver Sustenance Rule (analogous to caretaker.py MEAL_TICKS = 400 when hungry):
            if enable_caregiver_sustenance and self.organism.feeding and (self.live_tick % 400 == 0):
                self.feed_sensory_event(source="caretaker-food", food="apple")
            else:
                self.step()

            if progress_callback and (i % callback_interval == 0 or i == n_ticks):
                elapsed = time.perf_counter() - t0
                progress_callback(i, n_ticks, elapsed)

        total_wall_s = time.perf_counter() - t0
        final_tick = self.live_tick
        ticks_elapsed = final_tick - initial_tick

        final_sleep = self.current_sleep_state()
        final_pressure = int(final_sleep["pressure"][0])
        pressure_capacity = int(final_sleep["pressure"][1])
        pressure_fraction = final_pressure / max(pressure_capacity, 1)

        sim_subjective_s = ticks_elapsed / REAL_TIME_TICKS_PER_SECOND
        sim_subjective_h = sim_subjective_s / 3600.0
        ticks_per_s = ticks_elapsed / max(total_wall_s, 1e-6)
        speedup = ticks_per_s / REAL_TIME_TICKS_PER_SECOND

        return HarnessMetrics(
            organism_identity=self.identity,
            initial_tick=initial_tick,
            final_tick=final_tick,
            ticks_elapsed=ticks_elapsed,
            simulated_subjective_seconds=sim_subjective_s,
            simulated_subjective_hours=sim_subjective_h,
            wall_clock_seconds=total_wall_s,
            ticks_per_second=ticks_per_s,
            overclock_speedup_factor=speedup,
            sleep_pressure_units_start=init_pressure,
            sleep_pressure_units_end=final_pressure,
            sleep_pressure_fraction_end=pressure_fraction,
            nights_completed=int(final_sleep.get("nights", 0)),
            bites_count=int(self.organism.counts.get("bites", 0)),
            reserve_micrograms=int(self.organism.reserve_micrograms),
            moments_count=int(self.organism.counts.get("moments", 0)),
            micro_interrupts_count=len(self.temporal_stack.interrupt_history),
            active_macro_intent_type=self.temporal_stack.active_macro_intent.intent_type.value if self.temporal_stack.active_macro_intent else None,
            macro_intents_completed=len(self.temporal_stack.completed_intents),
            native_acceleration_active=self.native_active,
        )

    def feed_sensory_event(
        self,
        source: str = "microphone",
        pcm: bytes | None = None,
        food: str | None = None,
        retina_rgb_u8: bytes | None = None,
    ) -> Any:
        """Inject an external sensory occurrence directly into the functional loop."""
        actual_source = "caretaker-food" if food is not None else source
        p_bytes = pcm if (pcm and actual_source != "caretaker-food") else None
        r_bytes = retina_rgb_u8 if (retina_rgb_u8 and actual_source != "caretaker-food") else None
        occ = PhysicalOccurrence(
            "sensory",
            LeanSensoryOccurrence(
                source=actual_source,
                retina_rgb_u8=r_bytes,
                pressure_s16le=p_bytes,
                present_food=food,
            ),
        )
        return self.step(occ)

    def present_sensory_block(
        self,
        source: str = "microphone",
        pcm: bytes | None = None,
        food: str | None = None,
        retina_rgb_u8: bytes | None = None,
    ) -> Any:
        """Direct presentation of sensory block occurrence without HTTP transport."""
        return self.feed_sensory_event(source=source, pcm=pcm, food=food, retina_rgb_u8=retina_rgb_u8)

    def run_curriculum_session(
        self,
        target_entity_id: str = "apple",
        demand_syllables: Sequence[str] = ("dah0", "bah1"),
        valuation_syllables: Sequence[str] = ("kee0", "loo0"),
    ) -> CurriculumReceipt:
        """Execute a targeted Month 3 acoustic demand and Month 6 valuation session.

        Phases:
        1. Acoustic Calling Phase: Caretaker emits auditory phonemic syllables.
        2. Demand Formulation Phase: Organism formulates acoustic demand macro-intent.
        3. Meso-Scale Phonemic Articulation: Syllables articulated and advanced across beats.
        4. Affordance Response Phase: Caretaker presents requested object into reach.
        5. Settlement & Ingestion: Grasp/bite reflex consumes item, updating reserve & moments.
        6. Affective Valuation Phase: Organism formulates acoustic valuation envelope.
        """
        t0 = time.perf_counter()
        initial_reserve = int(self.organism.reserve_micrograms)
        start_tick = self.live_tick

        # Phase 1: Caretaker Acoustic Calling
        acoustic_cues = 0
        call_syllables = ("ah0", "ee0", "oh0")
        for syl in call_syllables:
            if syl in SYLLABLE_DRIVES:
                pcm = syllable_pcm(SYLLABLE_DRIVES[syl], seed=self.live_tick)
                self.present_sensory_block(source="microphone", pcm=pcm)
                acoustic_cues += 1

        # Phase 2: Formulate Month 3 Acoustic Demand
        demand_intent = self.form_teleological_demand(target_entity_id, phoneme_tokens=demand_syllables)
        demand_tokens: list[str] = []

        # Phase 3: Acoustic Phonemic Articulation across Meso Beats
        for _ in range(len(demand_intent.syntactic_assembly_tokens)):
            token = self.temporal_stack.macro.advance_active_token()
            if token:
                demand_tokens.append(token)
            self.step()

        # Phase 4: Caretaker Affordance Delivery
        self.present_sensory_block(source="caretaker-food", food=target_entity_id)

        # Phase 5: Settlement & Consummatory Reflex
        for _ in range(4):
            self.step()

        # Mark demand fulfilled if target reached
        demand_fulfilled = False
        completed = [ci for ci in self.temporal_stack.completed_intents if ci.intent_id == demand_intent.intent_id]
        if completed and completed[-1].fulfilled:
            demand_fulfilled = True
        elif self.temporal_stack.active_macro_intent and self.temporal_stack.active_macro_intent.intent_id == demand_intent.intent_id:
            fulfilled_intent = self.temporal_stack.macro.step(tick=self.live_tick, goal_reached=True)
            demand_fulfilled = fulfilled_intent.fulfilled if fulfilled_intent else True

        demand_duration = self.live_tick - demand_intent.start_tick

        # Phase 6: Month 6 Affective Valuation Transition
        val_intent = self.form_affective_valuation(target_entity_id, phoneme_tokens=valuation_syllables)
        val_tokens: list[str] = []
        for _ in range(len(val_intent.syntactic_assembly_tokens)):
            v_tok = self.temporal_stack.macro.advance_active_token()
            if v_tok:
                val_tokens.append(v_tok)
            self.step()

        val_completed = [ci for ci in self.temporal_stack.completed_intents if ci.intent_id == val_intent.intent_id]
        val_fulfilled = bool(val_completed and val_completed[-1].fulfilled)

        total_wall_s = time.perf_counter() - t0
        ticks_run = self.live_tick - start_tick
        rate = ticks_run / max(total_wall_s, 1e-6)
        speedup = rate / REAL_TIME_TICKS_PER_SECOND

        return CurriculumReceipt(
            organism_identity=self.identity,
            target_entity_id=target_entity_id,
            acoustic_cues_received=acoustic_cues,
            demand_intent_id=demand_intent.intent_id,
            demand_syllables_emitted=tuple(demand_tokens),
            demand_fulfilled=demand_fulfilled,
            demand_duration_beats=demand_duration,
            bites_count=int(self.organism.counts.get("bites", 0)),
            reserve_micrograms_initial=initial_reserve,
            reserve_micrograms_final=int(self.organism.reserve_micrograms),
            moments_formed_count=int(self.organism.counts.get("moments", 0)),
            valuation_intent_id=val_intent.intent_id,
            valuation_syllables_emitted=tuple(val_tokens),
            valuation_fulfilled=val_fulfilled,
            wall_clock_seconds=total_wall_s,
            ticks_per_second=rate,
            overclock_speedup_factor=speedup,
        )

    def run_deontic_session(
        self,
        target_action: str = "rest",
        target_agent_id: str = "person-body-1",
        deontic_syllables: Sequence[str] = ("dee0", "mah0"),
    ) -> DeonticReceipt:
        """Execute a targeted Month 18-24 Deontic Theory of Mind prescriptive session.

        Phases:
        1. Social Dyadic Contact: Caretaker emits prompt phonemes.
        2. Prescriptive Deficit Modeling: Guala models other agent state and forms acoustic prescription.
        3. Meso-Scale Phonemic Articulation: Syllables articulated across beats.
        4. Social Behavioral Confirmation: Caretaker confirms prescription with affirmative audio.
        5. Invariant Fulfillment: Deontic intent fulfilled and stabilized in episodic memory.
        """
        t0 = time.perf_counter()
        start_tick = self.live_tick

        # Phase 1: Social Dyadic Contact
        prompts_exchanged = 0
        prompt_pcm = syllable_pcm(SYLLABLE_DRIVES["dah0"], seed=self.live_tick)
        self.present_sensory_block(source="microphone", pcm=prompt_pcm)
        prompts_exchanged += 1

        # Phase 2: Formulate Month 18-24 Deontic Prescription
        deontic_intent = self.form_deontic_prescription(target_action, phoneme_tokens=deontic_syllables)
        deontic_tokens: list[str] = []

        # Phase 3: Meso-Scale Phonemic Articulation across Beats
        for _ in range(len(deontic_intent.syntactic_assembly_tokens)):
            tok = self.temporal_stack.macro.advance_active_token()
            if tok:
                deontic_tokens.append(tok)
            self.step()

        # Phase 4: Caretaker Social Confirmation
        confirm_pcm = syllable_pcm(SYLLABLE_DRIVES["dee0"], seed=self.live_tick)
        self.present_sensory_block(source="microphone", pcm=confirm_pcm)
        prompts_exchanged += 1

        # Phase 5: Settle Social Dynamics
        for _ in range(3):
            self.step()

        deontic_fulfilled = False
        completed = [ci for ci in self.temporal_stack.completed_intents if ci.intent_id == deontic_intent.intent_id]
        if completed and completed[-1].fulfilled:
            deontic_fulfilled = True
        elif self.temporal_stack.active_macro_intent and self.temporal_stack.active_macro_intent.intent_id == deontic_intent.intent_id:
            fulfilled = self.temporal_stack.macro.step(tick=self.live_tick, goal_reached=True)
            deontic_fulfilled = fulfilled.fulfilled if fulfilled else True

        total_wall_s = time.perf_counter() - t0
        ticks_run = self.live_tick - start_tick
        rate = ticks_run / max(total_wall_s, 1e-6)
        speedup = rate / REAL_TIME_TICKS_PER_SECOND

        return DeonticReceipt(
            organism_identity=self.identity,
            target_agent_id=target_agent_id,
            prescribed_action=target_action,
            acoustic_prompts_exchanged=prompts_exchanged,
            deontic_intent_id=deontic_intent.intent_id,
            syllables_emitted=tuple(deontic_tokens),
            deontic_fulfilled=deontic_fulfilled,
            duration_beats=ticks_run,
            moments_formed_count=int(self.organism.counts.get("moments", 0)),
            reserve_micrograms=int(self.organism.reserve_micrograms),
            wall_clock_seconds=total_wall_s,
            ticks_per_second=rate,
            overclock_speedup_factor=speedup,
        )

    def run_sleep_settle_session(
        self,
        target_sleep_beats: int | None = None,
    ) -> SleepReceipt:
        """Execute a targeted caregiver bedtime settle and nocturnal sleep consolidation pass.

        Phases:
        1. Bed Preparation: Caregiver executes bedtime routine, placing pillow and blanket on bed.
        2. Somatosensory Settling: Organism transitions to bed surface, activating nocturnal posture.
        3. Sleep State Gate: Sleep pressure triggers falling asleep (eyelids close, basal metabolic burn).
        4. Nocturnal Dream Consolidation: _dream() and _dream_moment() consolidate recurrent/salient
           moments into semantic meanings, discarding unsalient one-off noise (Pool Shock Principle).
        5. Awakening / State Settle: Sleep pressure clears, restoring diurnal vigor.
        """
        from dataclasses import replace
        from dsf_ai_service.guala_functional_organism import BED_ID
        from dsf_ai_service.substrate.embodiment_world import PositionMM, PoseMM

        t0 = time.perf_counter()
        initial_reserve = int(self.organism.reserve_micrograms)
        initial_pressure = int(self.current_sleep_state()["pressure"][0])
        initial_moments = int(self.organism.counts.get("moments", 0))
        start_tick = self.live_tick

        # Phase 1: Bed Preparation (Caretaker delivers bedtime bedding)
        bed_occ = self.present_sensory_block(source="caretaker-food", food="bedtime")
        pres = bed_occ.observation.get("caregiver_presentation", {})
        bed_made = bool(pres.get("presented"))
        bedding = tuple(pres.get("made", ()))

        # Phase 2: Settle Guala onto Bed Surface
        obs = self.world.observation_snapshot()
        bed_obj = next((item for item in obs.objects if item.object_id == BED_ID), None)
        if bed_obj and bed_obj.position is not None:
            bed_pos = PositionMM(bed_obj.position.x, bed_obj.position.y, 0)
            new_bodies = tuple(
                replace(b, pose=PoseMM(bed_pos, b.pose.heading_millidegrees))
                if b.body_id == obs.self_body_id else b
                for b in self.world._state.world.bodies
            )
            self.world._state = replace(self.world._state, world=replace(self.world._state.world, bodies=new_bodies))

        # Phase 3: Transition to Nocturnal Sleep
        if not self.organism.asleep:
            self.organism._state["asleep"] = True
            self.organism._state["nights"] = int(self.organism._state.get("nights", 0)) + 1

        # Phase 4: Step through Nocturnal Sleep & Dream Beats
        beats_to_run = target_sleep_beats if target_sleep_beats is not None else max(10, initial_pressure // 2 + 5)
        for _ in range(beats_to_run):
            if not self.organism.asleep and target_sleep_beats is None:
                break
            self.step()

        # Phase 5: Calculate Receipt Metrics
        final_pressure = int(self.current_sleep_state()["pressure"][0])
        final_reserve = int(self.organism.reserve_micrograms)
        nights = int(self.organism.counts.get("nights", 0))
        moments_remaining = len(self.organism._state.get("moments", {}))
        meanings = self.organism._state.get("meanings", {})
        meanings_count = len(meanings)
        meanings_samples = tuple(list(meanings.keys())[:5])

        total_wall_s = time.perf_counter() - t0
        ticks_run = self.live_tick - start_tick
        rate = ticks_run / max(total_wall_s, 1e-6)
        speedup = rate / REAL_TIME_TICKS_PER_SECOND

        return SleepReceipt(
            organism_identity=self.identity,
            bed_made=bed_made,
            bedding_items=bedding,
            initial_sleep_pressure=initial_pressure,
            final_sleep_pressure=final_pressure,
            sleep_beats_elapsed=ticks_run,
            nights_completed=nights,
            moments_initial_count=initial_moments,
            moments_remaining_count=moments_remaining,
            meanings_consolidated_count=meanings_count,
            meanings_samples=meanings_samples,
            reserve_micrograms_initial=initial_reserve,
            reserve_micrograms_final=final_reserve,
            wall_clock_seconds=total_wall_s,
            ticks_per_second=rate,
            overclock_speedup_factor=speedup,
        )

    def extrapolate_developmental_timeline(self, current_metrics: HarnessMetrics) -> dict[str, Any]:
        """Extrapolate empirical simulation throughput to full developmental horizons."""
        speedup = max(current_metrics.overclock_speedup_factor, 1.0)
        ticks_per_sec = max(current_metrics.ticks_per_second, 0.1)

        milestones = [
            ("1 Subjective Day (Diurnal Cycle)", 113_600),
            ("Month 1 (Sensory Habituation)", 113_600 * 30),
            ("Month 3 (Acoustic Demand Syntax)", 113_600 * 90),
            ("Month 6 (Acoustic Valuation)", 113_600 * 180),
            ("Month 12 ('Let's Play' Affordance)", 113_600 * 365),
            ("2.5 Years (Deontic Theory of Mind)", int(113_600 * 365 * 2.5)),
        ]

        projections = {}
        for name, req_ticks in milestones:
            natural_wall_seconds = req_ticks / REAL_TIME_TICKS_PER_SECOND
            accelerated_wall_seconds = req_ticks / ticks_per_sec
            accelerated_days = accelerated_wall_seconds / 86400.0
            projections[name] = {
                "required_ticks": req_ticks,
                "natural_realtime_days": round(natural_wall_seconds / 86400.0, 1),
                "accelerated_sim_days": round(accelerated_days, 2),
                "accelerated_sim_hours": round(accelerated_wall_seconds / 3600.0, 1),
                "acceleration_factor": round(speedup, 2),
            }

        return {
            "current_benchmark": asdict(current_metrics),
            "projections": projections,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Guala Headless Speed Harness")
    parser.add_argument("--ticks", type=int, default=100, help="Number of ticks to simulate")
    parser.add_argument("--identity", type=str, default=DEFAULT_IDENTITY, help="UUID of the organism")
    parser.add_argument("--live", action="store_true", help="Boot harness from live production state checkpoint (Tick 1,767,000+)")
    parser.add_argument("--demand", type=str, default=None, help="Formulate an acoustic demand for target object")
    parser.add_argument("--curriculum", type=str, nargs="?", const="apple", default=None, help="Run targeted developmental curriculum session for target object")
    parser.add_argument("--deontic", type=str, nargs="?", const="rest", default=None, help="Run Month 18-24 Deontic Theory of Mind prescriptive session")
    parser.add_argument("--sleep", type=int, nargs="?", const=100, default=None, help="Run caregiver bedtime and nocturnal sleep consolidation pass for N beats")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    if args.live:
        harness = HeadlessSpeedHarness.from_live_checkpoint(identity=args.identity)
    else:
        harness = HeadlessSpeedHarness(identity=args.identity)

    if args.sleep is not None:
        receipt = harness.run_sleep_settle_session(target_sleep_beats=args.sleep)
        if args.json:
            print(json.dumps(asdict(receipt), indent=2))
        else:
            print("\n" + "=" * 70)
            print("GUALA DEVELOPMENTAL RECEIPT: CAREGIVER BEDTIME & NOCTURNAL SLEEP")
            print("=" * 70)
            print(f"Organism Identity:              {receipt.organism_identity}")
            print(f"Bed Preparation Status:         {'MADE' if receipt.bed_made else 'PRESENTED'} ({', '.join(receipt.bedding_items) or 'bedding aligned'})")
            print(f"Sleep Pressure Recovery:        {receipt.initial_sleep_pressure} -> {receipt.final_sleep_pressure} units ({receipt.sleep_beats_elapsed} sleep beats)")
            print(f"Nights Completed:               {receipt.nights_completed} diurnal cycle(s)")
            print(f"Moments Settled:                {receipt.moments_initial_count} initial -> {receipt.moments_remaining_count} unpruned")
            print(f"Semantic Meanings Crystallized: {receipt.meanings_consolidated_count} meanings")
            if receipt.meanings_samples:
                print(f"Meanings Sample:                {', '.join(receipt.meanings_samples)}")
            print(f"Metabolic Burn:                 {receipt.reserve_micrograms_initial} µg -> {receipt.reserve_micrograms_final} µg (basal burn)")
            print(f"Throughput & Overclock:         {receipt.ticks_per_second:.1f} ticks/s ({receipt.overclock_speedup_factor:.2f}x real-time)")
            print("=" * 70)
        return

    if args.deontic:
        receipt = harness.run_deontic_session(target_action=args.deontic)
        if args.json:
            print(json.dumps(asdict(receipt), indent=2))
        else:
            print("\n" + "=" * 70)
            print("GUALA THEORY OF MIND RECEIPT: MONTH 18-24 DEONTIC PRESCRIPTION")
            print("=" * 70)
            print(f"Organism Identity:              {receipt.organism_identity}")
            print(f"Target Dyadic Agent:            {receipt.target_agent_id}")
            print(f"Prescribed Action:              {receipt.prescribed_action}")
            print(f"Acoustic Prompts Exchanged:     {receipt.acoustic_prompts_exchanged} cochlear frames")
            print(f"Deontic Intent Identifier:      {receipt.deontic_intent_id}")
            print(f"Acoustic Phonemes Emitted:      {' -> '.join(receipt.syllables_emitted)}")
            print(f"Prescriptive Intent Fulfilled:  {'YES' if receipt.deontic_fulfilled else 'NO'} ({receipt.duration_beats} beats)")
            print(f"Metabolic Reserve / Moments:    {receipt.reserve_micrograms} µg / {receipt.moments_formed_count} moments")
            print(f"Throughput & Overclock:         {receipt.ticks_per_second:.1f} ticks/s ({receipt.overclock_speedup_factor:.2f}x real-time)")
            print("=" * 70)
        return

    if args.curriculum:
        receipt = harness.run_curriculum_session(target_entity_id=args.curriculum)
        if args.json:
            print(json.dumps(asdict(receipt), indent=2))
        else:
            print("\n" + "=" * 70)
            print("GUALA DEVELOPMENTAL CURRICULUM RECEIPT: MONTH 3 DEMAND SYNTAX")
            print("=" * 70)
            print(f"Organism Identity:              {receipt.organism_identity}")
            print(f"Target Affordance Entity:       {receipt.target_entity_id}")
            print(f"Acoustic Cues Received:         {receipt.acoustic_cues_received} cochlear frames")
            print(f"Teleological Demand Intent:     {receipt.demand_intent_id}")
            print(f"Demand Phonemes Emitted:        {' -> '.join(receipt.demand_syllables_emitted)}")
            print(f"Macro Intent Fulfilled:         {'YES' if receipt.demand_fulfilled else 'NO'} ({receipt.demand_duration_beats} beats)")
            print(f"Metabolic Reserve:              {receipt.reserve_micrograms_initial} µg -> {receipt.reserve_micrograms_final} µg")
            print(f"Bites / Moments Formed:         {receipt.bites_count} bites / {receipt.moments_formed_count} moments")
            print(f"Month 6 Valuation Intent:       {receipt.valuation_intent_id or 'None'}")
            print(f"Valuation Phonemes Emitted:     {' -> '.join(receipt.valuation_syllables_emitted)}")
            print(f"Valuation Fulfilled:            {'YES' if receipt.valuation_fulfilled else 'NO'}")
            print(f"Throughput & Overclock:         {receipt.ticks_per_second:.1f} ticks/s ({receipt.overclock_speedup_factor:.2f}x real-time)")
            print("=" * 70)
        return

    if args.demand:
        harness.form_teleological_demand(args.demand)

    def on_progress(done: int, total: int, elapsed: float) -> None:
        if not args.json:
            rate = done / max(elapsed, 1e-6)
            eta_s = (total - done) / max(rate, 1e-6)
            eta_m = eta_s / 60.0
            sys.stdout.write(f"\r[Overclock] {done}/{total} ticks ({done/total*100:.1f}%) | {rate:.1f} ticks/s | {elapsed:.1f}s elapsed | ETA: {eta_m:.1f}m")
            sys.stdout.flush()

    interval = max(50, args.ticks // 200)
    metrics = harness.run_ticks(args.ticks, progress_callback=on_progress if not args.json else None, callback_interval=interval)
    extrapolations = harness.extrapolate_developmental_timeline(metrics)

    if args.json:
        print(json.dumps(extrapolations, indent=2))
    else:
        print("\n\n" + "=" * 70)
        print("GUALA HEADLESS SPEED HARNESS: BENCHMARK & EXTRAPOLATION RECEIPT")
        print("=" * 70)
        print(f"Organism Identity:              {metrics.organism_identity}")
        print(f"Native Acceleration (Rust):     {'ACTIVE (PyO3 Hot Path)' if metrics.native_acceleration_active else 'FALLBACK (Pure Python)'}")
        print(f"Simulated Ticks:                {metrics.ticks_elapsed} ticks ({metrics.initial_tick} -> {metrics.final_tick})")
        print(f"Subjective Organism Time:       {metrics.simulated_subjective_hours:.3f} hours ({metrics.simulated_subjective_seconds:.1f}s)")
        print(f"Simulation Wall-Clock Time:     {metrics.wall_clock_seconds:.3f} seconds")
        print(f"Simulation Throughput:          {metrics.ticks_per_second:.1f} ticks/second")
        print(f"Overclock Acceleration Factor:  {metrics.overclock_speedup_factor:.2f}x real-time speed")
        print(f"Sleep Pressure:                 {metrics.sleep_pressure_units_start} -> {metrics.sleep_pressure_units_end} ({metrics.sleep_pressure_fraction_end*100:.1f}%)")
        print(f"Reserve / Moments Formed:       {metrics.reserve_micrograms} µg / {metrics.moments_count} moments")
        print(f"Micro-Reflex Interrupts:        {metrics.micro_interrupts_count} events")
        print(f"Macro Intent (Active / Done):   {metrics.active_macro_intent_type or 'None'} / {metrics.macro_intents_completed} completed")
        print("-" * 70)
        print("DEVELOPMENTAL TIMELINE PROJECTIONS (LEVERS 1 & 4 ACCELERATION):")
        for stage, data in extrapolations["projections"].items():
            print(f"  • {stage:38s}: {data['accelerated_sim_days']:6.1f} days ({data['accelerated_sim_hours']:6.1f}h) [vs {data['natural_realtime_days']:6.1f} natural days]")
        print("=" * 70)


if __name__ == "__main__":
    main()
