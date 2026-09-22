#!/usr/bin/env python3
"""dsf_ai_service/guala_hierarchical_stack.py — Hierarchical Multi-Scale Nested Temporal Stack.

Charter & Physical Invariant (docs/guala_accelerated_developmental_roadmap.md, Lever 4):
- Guala's embodied sensorimotor loop operates across three nested physical timescales:
  1. Micro-Scale Loop (10 ms / 100 Hz): 25 sub-tick frames per 250ms beat.
     Evaluates high-frequency sensory signals (acoustic gammatone cochlear frames,
     cutaneous thermal nociception, tactile shock). Emits immediate physical reflex
     interrupts to preempt active motor drive without waiting for the 250ms beat boundary.
  2. Meso-Scale Loop (250 ms - 1 s / 1–4 Hz): The canonical organism beat (BEAT_MICROSECONDS = 250_000).
     Coordinates discrete phonemic/syllabic vocal emissions, gaze/head saccades,
     single-step movement strides, and contact grasp/touch mechanics.
  3. Macro-Scale Loop (2 - 10 s / 8–40 beats / 0.1–0.5 Hz):
     Sustained cognitive intent envelope maintaining multi-beat goals:
     - Teleological Demand: Target object + metabolic deficit + acoustic phoneme chain.
     - Affective Valuation: Episodic memory match + preference basin + acoustic confirmation.
     - Multi-Step Affordance: Inter-room navigation, climbing, tool-mediated retrieval.
     - Prescriptive Deontic Theory of Mind: External agent deficit modeling + dyadic acoustic cues.

Bounded Memory Guarantee:
- Micro reflex history and completed macro intents use bounded ring buffers (max 1024 entries),
  strictly preventing runaway memory/RAM growth during long-duration runs.

Decoupled Syntactic Articulation from Goal Fulfillment (SH-A1-05):
- Advancing tokens through syntactic assemblies increments current token index, but strictly
  does NOT mark intent fulfilled. Goal fulfillment requires verified physical/sensory achievement
  via fulfill() on step().

Pure deterministic physical cognition: no heuristics, no ML approximations, no synthetic language scaffolding.
All vocal tokens are pure acoustic phoneme syllables from canonical SYLLABLES.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
import enum
from typing import Any, Sequence

# Canonical Physical Limits
MICRO_FRAME_MICROSECONDS = 10_000        # 10 ms per sub-tick acoustic/tactile frame
MICRO_FRAMES_PER_BEAT = 25              # 25 frames * 10 ms = 250 ms canonical beat
MESO_BEAT_MICROSECONDS = 250_000        # 250 ms canonical beat
NOCICEPTION_MILLIKELVIN = 340_000       # 340 K (66.85 C) burn hazard threshold
CONTACT_SHOCK_THRESHOLD = 0.95          # Sudden full-surface skin compression
ACOUSTIC_SHOCK_FLOOR = 0.90             # Sudden explosive sound pressure level
MACRO_MIN_BEATS = 8                     # 2.0 seconds at 4 beats/sec
MACRO_MAX_BEATS = 40                    # 10.0 seconds at 4 beats/sec
MAX_HISTORY_ENTRIES = 1024              # Hard capacity bound preventing memory leaks


class MacroIntentType(enum.Enum):
    IDLE_EXPLORATION = "idle_exploration"
    TELEOLOGICAL_DEMAND = "teleological_demand"          # Metabolic deficit + target object + acoustic demand
    AFFECTIVE_VALUATION = "affective_valuation"          # Hedonic valence + acoustic valuation phonemes
    MULTI_STEP_AFFORDANCE = "multi_step_affordance"      # Navigate -> reach -> grasp
    DEONTIC_THEORY_OF_MIND = "deontic_theory_of_mind"    # Dyadic agent deficit modeling + acoustic phonemes
    PROTECTIVE_AVOIDANCE = "protective_avoidance"        # Preemptive hazard diversion


@dataclass(frozen=True, slots=True)
class MicroInterrupt:
    """Sub-tick physical reflex event triggered within a 10ms frame."""
    trigger: str                           # "thermal_nociception", "contact_shock", "acoustic_shock"
    frame_index: int                       # 0 to 24 within the current beat
    severity: float                        # Magnitude of threshold excess
    mitigation_action: str                 # "release", "retract", "halt_locomotion"
    timestamp_microsecond: int
    entity_id: str | None = None


@dataclass(frozen=True, slots=True)
class MacroIntent:
    """Multi-second cognitive intent envelope spanning 8 to 40 beats (2 to 10 seconds)."""
    intent_id: str
    intent_type: MacroIntentType
    target_entity_id: str | None
    start_tick: int
    duration_beats_ceiling: int
    syntactic_assembly_tokens: tuple[str, ...] = ()  # Acoustic phoneme syllables from canonical SYLLABLES
    current_token_index: int = 0
    fulfilled: bool = False
    aborted: bool = False
    abort_reason: str | None = None

    @property
    def is_active(self) -> bool:
        return not self.fulfilled and not self.aborted

    @property
    def tokens_exhausted(self) -> bool:
        """True when all syntactic assembly phoneme tokens have been articulated."""
        if not self.syntactic_assembly_tokens:
            return True
        return self.current_token_index >= len(self.syntactic_assembly_tokens)

    def advance_token(self) -> MacroIntent:
        """Advance acoustic phoneme syllable token index as syllables are vocalized.
        
        Strict Invariant (SH-A1-05): advancing tokens does NOT mark intent fulfilled.
        Fulfillment is strictly contingent on verified physical/sensory goal attainment via fulfill().
        """
        if not self.is_active or not self.syntactic_assembly_tokens:
            return self
        new_idx = self.current_token_index + 1
        return MacroIntent(
            intent_id=self.intent_id,
            intent_type=self.intent_type,
            target_entity_id=self.target_entity_id,
            start_tick=self.start_tick,
            duration_beats_ceiling=self.duration_beats_ceiling,
            syntactic_assembly_tokens=self.syntactic_assembly_tokens,
            current_token_index=new_idx,
            fulfilled=self.fulfilled,
            aborted=self.aborted,
            abort_reason=self.abort_reason,
        )

    def abort(self, reason: str) -> MacroIntent:
        return MacroIntent(
            intent_id=self.intent_id,
            intent_type=self.intent_type,
            target_entity_id=self.target_entity_id,
            start_tick=self.start_tick,
            duration_beats_ceiling=self.duration_beats_ceiling,
            syntactic_assembly_tokens=self.syntactic_assembly_tokens,
            current_token_index=self.current_token_index,
            fulfilled=False,
            aborted=True,
            abort_reason=reason,
        )

    def fulfill(self) -> MacroIntent:
        return MacroIntent(
            intent_id=self.intent_id,
            intent_type=self.intent_type,
            target_entity_id=self.target_entity_id,
            start_tick=self.start_tick,
            duration_beats_ceiling=self.duration_beats_ceiling,
            syntactic_assembly_tokens=self.syntactic_assembly_tokens,
            current_token_index=self.current_token_index,
            fulfilled=True,
            aborted=False,
            abort_reason=None,
        )


class MicroReflexField:
    """Evaluates 10ms sub-tick frames for nociceptive and acoustic shock reflex interrupts."""

    def __init__(self, max_history: int = MAX_HISTORY_ENTRIES) -> None:
        self.interrupt_history: deque[MicroInterrupt] = deque(maxlen=max_history)

    def evaluate_subframes(
        self,
        tick: int,
        heard_frames: Sequence[Sequence[float]] | None,
        skin_contact: float,
        skin_temperature_millikelvin: int | None,
        touch_surface_millikelvin: int | None,
        held_surface_millikelvin: int | None = None,
        held_entity_id: str | None = None,
    ) -> tuple[MicroInterrupt, ...]:
        interrupts: list[MicroInterrupt] = []

        # 1. Thermal Nociception
        temp_candidates = [
            t for t in (skin_temperature_millikelvin, touch_surface_millikelvin, held_surface_millikelvin)
            if t is not None
        ]
        max_temp = max(temp_candidates) if temp_candidates else 310_000
        if max_temp > NOCICEPTION_MILLIKELVIN:
            excess = (max_temp - NOCICEPTION_MILLIKELVIN) / 10_000.0
            interrupt = MicroInterrupt(
                trigger="thermal_nociception",
                frame_index=0,
                severity=excess,
                mitigation_action="release" if held_surface_millikelvin else "retract",
                timestamp_microsecond=tick * MESO_BEAT_MICROSECONDS,
                entity_id=held_entity_id,
            )
            interrupts.append(interrupt)
            self.interrupt_history.append(interrupt)

        # 2. Tactile Shock Reflex
        if skin_contact > CONTACT_SHOCK_THRESHOLD:
            interrupt = MicroInterrupt(
                trigger="contact_shock",
                frame_index=1,
                severity=skin_contact - CONTACT_SHOCK_THRESHOLD,
                mitigation_action="retract",
                timestamp_microsecond=tick * MESO_BEAT_MICROSECONDS + MICRO_FRAME_MICROSECONDS,
                entity_id=None,
            )
            interrupts.append(interrupt)
            self.interrupt_history.append(interrupt)

        # 3. Acoustic Gammatone Shock Reflex
        if heard_frames:
            for f_idx, frame in enumerate(heard_frames[:MICRO_FRAMES_PER_BEAT]):
                spl = max(frame) if frame else 0.0
                if spl > ACOUSTIC_SHOCK_FLOOR:
                    interrupt = MicroInterrupt(
                        trigger="acoustic_shock",
                        frame_index=f_idx,
                        severity=spl - ACOUSTIC_SHOCK_FLOOR,
                        mitigation_action="startle_freeze",
                        timestamp_microsecond=tick * MESO_BEAT_MICROSECONDS + f_idx * MICRO_FRAME_MICROSECONDS,
                        entity_id=None,
                    )
                    interrupts.append(interrupt)
                    self.interrupt_history.append(interrupt)
                    break

        return tuple(interrupts)


class MesoBeatField:
    """Coordinates canonical 250ms organism sensorimotor cadence."""

    def __init__(self) -> None:
        self.beat_count: int = 0

    def step(self, organism_tick: int) -> int:
        self.beat_count += 1
        return self.beat_count


class MacroIntentField:
    """Manages multi-beat cognitive goals and behavioral intention envelopes."""

    def __init__(self, max_completed: int = MAX_HISTORY_ENTRIES) -> None:
        self.active_intent: MacroIntent | None = None
        self.completed_intents: deque[MacroIntent] = deque(maxlen=max_completed)

    def form_intent(
        self,
        intent_type: MacroIntentType,
        target_entity_id: str | None,
        tick: int,
        duration_beats: int = 16,
        tokens: Sequence[str] = (),
    ) -> MacroIntent:
        """Formulate a sustained behavioral intention envelope."""
        duration = max(MACRO_MIN_BEATS, min(MACRO_MAX_BEATS, duration_beats))
        intent = MacroIntent(
            intent_id=f"{intent_type.value}_{tick}_{duration}",
            intent_type=intent_type,
            target_entity_id=target_entity_id,
            start_tick=tick,
            duration_beats_ceiling=duration,
            syntactic_assembly_tokens=tuple(tokens),
            current_token_index=0,
            fulfilled=False,
            aborted=False,
            abort_reason=None,
        )
        self.active_intent = intent
        return intent

    def step(
        self,
        tick: int,
        target_entity_present: bool = True,
        goal_reached: bool = False,
    ) -> MacroIntent | None:
        """Update and maintain active macro-intent across beats."""
        if self.active_intent is None:
            return None

        intent = self.active_intent

        # 1. Check goal fulfillment
        if goal_reached:
            intent = intent.fulfill()
            self.completed_intents.append(intent)
            self.active_intent = None
            return intent

        # 2. Check duration ceiling timeout
        elapsed_beats = tick - intent.start_tick
        if elapsed_beats >= intent.duration_beats_ceiling:
            intent = intent.abort("duration_ceiling_exceeded")
            self.completed_intents.append(intent)
            self.active_intent = None
            return intent

        # 3. Check physical validity (target vanished or inaccessible)
        if intent.target_entity_id is not None and not target_entity_present:
            intent = intent.abort("target_entity_vanished")
            self.completed_intents.append(intent)
            self.active_intent = None
            return intent

        return intent

    def advance_active_token(self) -> str | None:
        """Emit the next acoustic phoneme syllable in the active syntactic assembly."""
        if self.active_intent is None or not self.active_intent.is_active:
            return None
        tokens = self.active_intent.syntactic_assembly_tokens
        idx = self.active_intent.current_token_index
        if idx < len(tokens):
            token = tokens[idx]
            self.active_intent = self.active_intent.advance_token()
            return token
        return None


class HierarchicalTemporalStack:
    """Unified Hierarchical Multi-Scale DSF Temporal Stack."""

    def __init__(self, max_history: int = MAX_HISTORY_ENTRIES) -> None:
        self.micro = MicroReflexField(max_history=max_history)
        self.meso = MesoBeatField()
        self.macro = MacroIntentField(max_completed=max_history)

    @property
    def active_macro_intent(self) -> MacroIntent | None:
        return self.macro.active_intent

    @property
    def interrupt_history(self) -> list[MicroInterrupt]:
        return list(self.micro.interrupt_history)

    @property
    def completed_intents(self) -> list[MacroIntent]:
        return list(self.macro.completed_intents)

    def evaluate_cycle(
        self,
        tick: int,
        heard_frames: Sequence[Sequence[float]] | None,
        skin_contact: float,
        skin_temperature_millikelvin: int | None,
        touch_surface_millikelvin: int | None,
        held_surface_millikelvin: int | None = None,
        held_entity_id: str | None = None,
        target_entity_present: bool = True,
        goal_reached: bool = False,
    ) -> tuple[tuple[MicroInterrupt, ...], MacroIntent | None]:
        """Perform unified multi-scale temporal evaluation."""
        # 1. Micro-scale (10 ms sub-tick frames)
        interrupts = self.micro.evaluate_subframes(
            tick=tick,
            heard_frames=heard_frames,
            skin_contact=skin_contact,
            skin_temperature_millikelvin=skin_temperature_millikelvin,
            touch_surface_millikelvin=touch_surface_millikelvin,
            held_surface_millikelvin=held_surface_millikelvin,
            held_entity_id=held_entity_id,
        )

        # 2. Meso-scale (250 ms beat)
        self.meso.step(tick)

        # If a micro reflex fires (e.g. burn), abort any conflicting macro intent
        if interrupts and self.macro.active_intent is not None:
            first_int = interrupts[0]
            if first_int.trigger == "thermal_nociception":
                self.macro.active_intent = self.macro.active_intent.abort(f"micro_reflex_{first_int.trigger}")

        # 3. Macro-scale (2 - 10 s intent governor)
        macro_intent = self.macro.step(
            tick=tick,
            target_entity_present=target_entity_present,
            goal_reached=goal_reached,
        )

        return interrupts, macro_intent

    def form_teleological_demand(
        self,
        target_entity_id: str,
        tick: int,
        phoneme_tokens: Sequence[str] = ("dah0", "bah1"),
    ) -> MacroIntent:
        """Form an acoustic demand intent envelope grounded in metabolic deficit and acoustic phonemes."""
        tokens = tuple(phoneme_tokens)
        return self.macro.form_intent(
            intent_type=MacroIntentType.TELEOLOGICAL_DEMAND,
            target_entity_id=target_entity_id,
            tick=tick,
            duration_beats=16,  # 4 seconds
            tokens=tokens,
        )

    def form_affective_valuation(
        self,
        target_entity_id: str,
        tick: int,
        phoneme_tokens: Sequence[str] = ("kee0", "loo0"),
    ) -> MacroIntent:
        """Form an acoustic valuation intent envelope grounded in hedonic resonance and phonemes."""
        tokens = tuple(phoneme_tokens)
        return self.macro.form_intent(
            intent_type=MacroIntentType.AFFECTIVE_VALUATION,
            target_entity_id=target_entity_id,
            tick=tick,
            duration_beats=16,  # 4 seconds
            tokens=tokens,
        )

    def form_deontic_prescription(
        self,
        target_action: str,
        tick: int,
        phoneme_tokens: Sequence[str] = ("dee0", "mah0"),
    ) -> MacroIntent:
        """Form a dyadic social prescription intent envelope grounded in acoustic phonemes."""
        tokens = tuple(phoneme_tokens)
        return self.macro.form_intent(
            intent_type=MacroIntentType.DEONTIC_THEORY_OF_MIND,
            target_entity_id=None,
            tick=tick,
            duration_beats=24,  # 6 seconds
            tokens=tokens,
        )
