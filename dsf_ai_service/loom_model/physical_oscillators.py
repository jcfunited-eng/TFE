"""Nonsemantic oscillator primitives for the physical Loom organism.

These classes preserve the durable oscillator geometry formerly hosted by the
word-authored Krimelack module without importing its vocabulary, role priors,
named sensory profiles, Atlas coupling, or symbolic transduction.

The structural graph keeps its existing type tags and field names.  That is a
persistence compatibility boundary, not a claim that ``label`` or the legacy
type-tag spelling has semantic authority.
"""

from __future__ import annotations

import math
from collections import deque


EVENTS_MAXLEN = 256


class PhysicalSignalOscillator:
    """Bounded winding oscillator driven only by numeric physical samples."""

    def __init__(
        self,
        omega_0: float = 2.0,
        kappa: float = 80.0,
        dt: float = 0.04,
        threshold: float = math.pi / 3,
        label: str = "physical_signal",
    ):
        self.omega_0 = omega_0
        self.kappa = kappa
        self.dt = dt
        self.threshold = threshold
        self.label = label
        self.n_events = 0
        self.reset()

    def reset(self) -> None:
        self.phase = 0.0
        self.t = 0.0
        self.winding = 0
        self.events = deque(maxlen=EVENTS_MAXLEN)

    def feed(self, signal_array) -> None:
        """Advance the oscillator with numeric samples.

        The arithmetic and mutation order are identical to the physical part
        of the retired language transducer so restored oscillator state can
        continue without a formula or binary64 transition change.
        """
        if not hasattr(self, "n_events"):
            self.n_events = 0
        for sample in signal_array:
            signal = float(sample)
            omega = self.omega_0 + self.kappa * signal
            delta_phase = (omega - self.omega_0) * self.dt
            self.phase += delta_phase
            self.t += self.dt
            while self.phase >= self.threshold:
                self.phase -= self.threshold
                self.winding += 1
                self.events.append(
                    {"t": self.t, "dw": +1, "s": signal}
                )
                self.n_events += 1
            while self.phase <= -self.threshold:
                self.phase += self.threshold
                self.winding -= 1
                self.events.append(
                    {"t": self.t, "dw": -1, "s": signal}
                )
                self.n_events += 1

    def fingerprint(self):
        """Return the bounded physical event-stream fingerprint."""
        event_count = len(self.events)
        if event_count == 0:
            return (0, 0, 0.0, 0, 0, 0, 0)
        mean_signal = (
            sum(event["s"] for event in self.events) / event_count
        )
        maximum_time = max(event["t"] for event in self.events)
        quadrants = [0, 0, 0, 0]
        for event in self.events:
            index = min(
                3,
                int(event["t"] / (maximum_time / 4 + 1e-9)),
            )
            quadrants[index] += 1
        return (
            event_count,
            self.winding,
            mean_signal,
            quadrants[0],
            quadrants[1],
            quadrants[2],
            quadrants[3],
        )


class PhysicalBaseOscillator(PhysicalSignalOscillator):
    """Persistence-compatible base oscillator for historical graph nodes."""

    def __init__(
        self,
        omega_0: float = 2.0,
        kappa: float = 80.0,
        dt: float = 0.04,
        threshold: float = math.pi / 3,
        label: str = "unnamed",
    ):
        super().__init__(
            omega_0=omega_0,
            kappa=kappa,
            dt=dt,
            threshold=threshold,
            label=label,
        )


class PhysicalModalOscillator(PhysicalSignalOscillator):
    """State-compatible physical modal oscillator without named profiles."""

    _OMEGA_OFFSETS = {
        "sight": 2.0,
        "sound": 2.3,
        "smell": 2.6,
        "taste": 2.9,
        "touch": 3.2,
    }

    def __init__(self, modality: str):
        super().__init__(
            omega_0=self._OMEGA_OFFSETS.get(modality, 2.0),
            kappa=60.0,
            dt=0.04,
            threshold=math.pi / 3,
            label=modality,
        )
        self.modality = modality


class PhysicalSensoryOscillatorBank:
    """Durable physical modal oscillator container.

    The bank performs no word lookup and exposes no named-profile firing
    operation.  Each modality advances only when a physical path explicitly
    feeds its oscillator.
    """

    MODALITIES = ("sight", "sound", "smell", "taste", "touch")

    def __init__(self):
        self.krimelacks = {
            modality: PhysicalModalOscillator(modality)
            for modality in self.MODALITIES
        }


__all__ = [
    "EVENTS_MAXLEN",
    "PhysicalBaseOscillator",
    "PhysicalModalOscillator",
    "PhysicalSensoryOscillatorBank",
    "PhysicalSignalOscillator",
]
