"""
ArcLoom Ternary Core — The Actual SPPU
========================================
This is NOT the UF kernel. This is NOT binary.
This IS ArcLoom: ternary structural processing.

A trit has three states: {-1, 0, +1}
A lattice of trits coupled through J_ij settling weights.
The lattice settles to an attractor state — the answer
emerges from the structure, not from sequential computation.

Feed sensor data in as ternary structural tokens.
The loom settles. The attractor IS the decision.
Krimelacks store the motifs. The loom remembers.
"""

import numpy as np
import time


# ==============================================================
# TERNARY PRIMITIVES
# ==============================================================

class Trit:
    """One ternary digit: {-1, 0, +1}"""
    __slots__ = ['value']

    def __init__(self, value=0):
        assert value in (-1, 0, 1), f"Trit must be -1, 0, or +1, got {value}"
        self.value = value

    def __repr__(self):
        return f"{'−' if self.value == -1 else '+' if self.value == 1 else '○'}"


def ternary_encode(analog_value, low_thresh, high_thresh):
    """Convert analog signal to trit: below=-1, between=0, above=+1"""
    if analog_value < low_thresh:
        return -1
    elif analog_value > high_thresh:
        return +1
    else:
        return 0


def ternary_encode_delta(delta, threshold):
    """Convert a change signal to trit: decreasing=-1, stable=0, increasing=+1"""
    if delta < -threshold:
        return -1
    elif delta > threshold:
        return +1
    else:
        return 0


# ==============================================================
# THE LOOM: Coupled Ternary Lattice
# ==============================================================

class ArcLoom:
    """
    The ArcLoom Structural Processing Unit.

    A lattice of N trits coupled through a J matrix.
    The lattice settles to attractors through deterministic
    energy minimization. No clock cycles. No instruction pointer.
    The structure IS the computation.

    Energy: E = -sum_ij J_ij * s_i * s_j - sum_i h_i * s_i

    This is a Hopfield-like network but in TERNARY with three
    states per node instead of two. The third state (0) is the
    "structural null" — negative space — which has no analog
    in binary Hopfield networks.

    The null state is what makes ArcLoom different:
    - Binary: every node must decide (0 or 1)
    - Ternary: a node can ABSTAIN (0 = "I don't know yet")
    - The null state allows partial settling — the loom can
      reach a decision on SOME nodes while others remain
      undecided. This is structural confidence.
    """

    def __init__(self, n_trits, name="loom"):
        self.n = n_trits
        self.name = name
        self.state = np.zeros(n_trits, dtype=int)  # all start at 0 (null)
        self.J = np.zeros((n_trits, n_trits))       # coupling matrix
        self.h = np.zeros(n_trits)                   # external field (input)
        self.energy_history = []
        self.settled = False

    def set_coupling(self, J_matrix):
        """Set the coupling matrix (must be symmetric, zero diagonal)."""
        assert J_matrix.shape == (self.n, self.n)
        self.J = J_matrix.copy()
        np.fill_diagonal(self.J, 0)  # no self-coupling

    def set_input(self, h_vector):
        """Set external input field (from sensors/data)."""
        assert len(h_vector) == self.n
        self.h = np.array(h_vector, dtype=float)

    def energy(self):
        """Compute total energy of current state."""
        interaction = -0.5 * self.state @ self.J @ self.state
        field = -np.sum(self.h * self.state)
        return interaction + field

    def local_field(self, i):
        """Compute local field at trit i: h_i + sum_j J_ij * s_j"""
        return self.h[i] + np.sum(self.J[i, :] * self.state)

    def settle_step(self):
        """One settling step: update each trit to minimize energy.

        Deterministic: update in fixed order (not random).
        Each trit snaps to {-1, 0, +1} based on its local field.
        """
        changed = False
        for i in range(self.n):
            field = self.local_field(i)

            # Ternary decision with dead zone (the key ArcLoom difference)
            # The dead zone is where the trit stays at 0 (null/abstain)
            dead_zone = 0.3  # structural confidence threshold

            if field > dead_zone:
                new_val = +1
            elif field < -dead_zone:
                new_val = -1
            else:
                new_val = 0  # NULL — not enough evidence to decide

            if new_val != self.state[i]:
                self.state[i] = new_val
                changed = True

        self.energy_history.append(self.energy())
        return changed

    def settle(self, max_steps=100):
        """Settle the loom until stable (attractor reached)."""
        self.energy_history = [self.energy()]

        for step in range(max_steps):
            changed = self.settle_step()
            if not changed:
                self.settled = True
                return step + 1

        self.settled = False
        return max_steps

    def read_state(self):
        """Read the current trit state as a string."""
        symbols = {-1: '−', 0: '○', 1: '+'}
        return ''.join(symbols[s] for s in self.state)

    def confidence(self):
        """Structural confidence: fraction of trits that are NOT null."""
        return np.mean(self.state != 0)

    def decision_vector(self):
        """Extract the decision as a ternary vector."""
        return self.state.copy()


# ==============================================================
# KRIMELACKS: Structural Memory
# ==============================================================

class Krimelack:
    """
    Krimelack structural memory.

    Stores motifs (patterns of trit states) and their coupling
    matrices. When a new input arrives, the closest stored motif
    biases the loom toward a known attractor.

    This is how ArcLoom learns: not by adjusting weights
    iteratively (ML), but by storing structural patterns
    (motifs) that the loom can recall through settling.

    Deterministic. No gradient descent. No backprop.
    Store a motif. Recall it by resonance.
    """

    def __init__(self, n_trits, capacity=100):
        self.n = n_trits
        self.capacity = capacity
        self.motifs = []       # list of stored state vectors
        self.labels = []       # what each motif means
        self.timestamps = []   # when stored

    def store(self, state_vector, label="", timestamp=None):
        """Store a motif in krimelack memory."""
        motif = np.array(state_vector, dtype=int).copy()
        assert len(motif) == self.n
        assert all(v in (-1, 0, 1) for v in motif)

        if len(self.motifs) >= self.capacity:
            # Fold: oldest motif gets absorbed (simplified)
            self.motifs.pop(0)
            self.labels.pop(0)
            self.timestamps.pop(0)

        self.motifs.append(motif)
        self.labels.append(label)
        self.timestamps.append(timestamp or time.time())

    def recall(self, partial_state):
        """Find the closest stored motif to a partial state.

        Uses ternary overlap: count matching non-null trits.
        Null trits (0) in the query are wildcards.
        """
        if not self.motifs:
            return None, None, 0.0

        query = np.array(partial_state, dtype=int)
        best_score = -1
        best_idx = 0

        for idx, motif in enumerate(self.motifs):
            # Score: count positions where both are non-null and match
            non_null = (query != 0) & (motif != 0)
            matching = np.sum((query == motif) & non_null)
            total_non_null = np.sum(non_null)

            score = matching / max(total_non_null, 1)
            if score > best_score:
                best_score = score
                best_idx = idx

        return self.motifs[best_idx], self.labels[best_idx], best_score

    def generate_coupling(self):
        """Generate a Hebbian coupling matrix from stored motifs.

        J_ij = (1/P) * sum_p motif_p[i] * motif_p[j]

        This is how stored patterns become attractors of the loom.
        The coupling matrix IS the memory, encoded as interactions.
        """
        P = len(self.motifs)
        if P == 0:
            return np.zeros((self.n, self.n))

        J = np.zeros((self.n, self.n))
        for motif in self.motifs:
            J += np.outer(motif, motif)
        J /= P
        np.fill_diagonal(J, 0)
        return J


# ==============================================================
# SENSOR → TERNARY ENCODER
# ==============================================================

class SensorEncoder:
    """
    Converts raw sensor readings into ternary structural tokens.

    Takes a window of analog readings and produces a trit vector:
    - Distance trit: near(+1) / mid(0) / far(-1)
    - Delta trit: approaching(+1) / stable(0) / retreating(-1)
    - Acceleration trit: accelerating(+1) / constant(0) / decelerating(-1)
    - Variance trit: noisy(+1) / normal(0) / quiet(-1)
    - Trend trit: rising(+1) / flat(0) / falling(-1)

    These 5 trits form the structural token that feeds the loom.
    """

    def __init__(self):
        self.history = []
        self.window = 10

    def encode(self, voltage):
        """Convert a sensor voltage to a 5-trit structural token."""
        self.history.append(voltage)
        if len(self.history) > 50:
            self.history = self.history[-50:]

        n = len(self.history)

        # Trit 0: Distance (voltage level)
        # Sharp sensor: high V = close, low V = far
        distance = ternary_encode(voltage, 0.5, 1.5)

        # Trit 1: Delta (rate of change)
        if n >= 2:
            delta = self.history[-1] - self.history[-2]
            direction = ternary_encode_delta(delta, 0.1)
        else:
            direction = 0

        # Trit 2: Acceleration (change in delta)
        if n >= 3:
            d1 = self.history[-1] - self.history[-2]
            d2 = self.history[-2] - self.history[-3]
            accel = ternary_encode_delta(d1 - d2, 0.05)
        else:
            accel = 0

        # Trit 3: Variance (noise level over window)
        if n >= self.window:
            recent = self.history[-self.window:]
            var = np.var(recent)
            variance_trit = ternary_encode(var, 0.01, 0.1)
        else:
            variance_trit = 0

        # Trit 4: Trend (slope over window)
        if n >= self.window:
            recent = self.history[-self.window:]
            slope = (recent[-1] - recent[0]) / self.window
            trend = ternary_encode_delta(slope, 0.02)
        else:
            trend = 0

        return np.array([distance, direction, accel, variance_trit, trend], dtype=int)


# ==============================================================
# ARCLOOM DECISION ENGINE
# ==============================================================

class ArcLoomDecisionEngine:
    """
    The complete ArcLoom pipeline:

    Sensor → Encoder → Loom → Krimelack → Decision

    Input: analog voltage from distance sensor
    Output: ternary decision {APPROACH, HOLD, RETREAT}

    The loom has 8 trits:
      [0-4]: sensor input (from encoder)
      [5]:   context trit (from krimelack recall)
      [6]:   momentum trit (from recent history)
      [7]:   decision trit (output — the answer)

    The coupling matrix connects inputs to the decision trit
    through the context and momentum trits. The decision
    EMERGES from the settling, not from if/else logic.
    """

    def __init__(self):
        self.loom = ArcLoom(8, name="decision_loom")
        self.krimelack = Krimelack(8, capacity=50)
        self.encoder = SensorEncoder()
        self.decision_count = 0

        # Initial coupling matrix
        # This IS the "instruction set" — the topology of how
        # trits influence each other
        J = np.zeros((8, 8))

        # Sensor trits (0-4) couple to momentum (6) and decision (7)
        # Distance (0) strongly influences decision
        J[0, 7] = 0.8   # close object → strong decision influence
        J[7, 0] = 0.8

        # Direction (1) strongly influences decision
        J[1, 7] = 0.7   # approaching → decision
        J[7, 1] = 0.7

        # Acceleration (2) moderately influences decision
        J[2, 7] = 0.4
        J[7, 2] = 0.4

        # Variance (3) influences context
        J[3, 5] = 0.5   # noisy → uncertain context
        J[5, 3] = 0.5

        # Trend (4) influences momentum
        J[4, 6] = 0.6   # trend → momentum
        J[6, 4] = 0.6

        # Context (5) weakly influences decision
        J[5, 7] = 0.3
        J[7, 5] = 0.3

        # Momentum (6) moderately influences decision
        J[6, 7] = 0.5
        J[7, 6] = 0.5

        # Cross-couplings for structural coherence
        J[0, 1] = 0.3   # distance-direction correlation
        J[1, 0] = 0.3
        J[1, 2] = 0.3   # direction-acceleration correlation
        J[2, 1] = 0.3

        self.base_coupling = J.copy()
        self.loom.set_coupling(J)

    def process(self, voltage):
        """Process one sensor reading through ArcLoom.

        Returns: (decision, confidence, state_string, n_steps)
        """
        # Encode sensor to ternary
        sensor_trits = self.encoder.encode(voltage)

        # Build input field
        h = np.zeros(8)
        h[0:5] = sensor_trits * 0.5  # sensor input as external field

        # Recall from krimelack to set context
        if self.krimelack.motifs:
            partial = np.zeros(8, dtype=int)
            partial[0:5] = sensor_trits
            recalled, label, score = self.krimelack.recall(partial)
            if score > 0.6:
                h[5] = recalled[5] * 0.3  # context from memory
                h[6] = recalled[6] * 0.2  # momentum from memory

        # Update coupling with krimelack patterns
        if len(self.krimelack.motifs) >= 3:
            J_learned = self.krimelack.generate_coupling()
            self.loom.set_coupling(self.base_coupling + 0.3 * J_learned)

        # Set input and settle
        self.loom.set_input(h)
        self.loom.state = np.zeros(8, dtype=int)  # reset
        self.loom.state[0:5] = sensor_trits        # clamp inputs

        n_steps = self.loom.settle(max_steps=50)

        # Read decision from trit 7
        decision_trit = self.loom.state[7]
        decision_map = {-1: "RETREAT", 0: "HOLD", 1: "APPROACH"}
        decision = decision_map[decision_trit]

        conf = self.loom.confidence()
        state_str = self.loom.read_state()

        # Store in krimelack
        self.krimelack.store(
            self.loom.state.copy(),
            label=decision,
            timestamp=time.time()
        )

        self.decision_count += 1

        return decision, conf, state_str, n_steps


# ==============================================================
# RUN IT
# ==============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("ArcLoom SPPU — Ternary Structural Processor")
    print("=" * 60)
    print()
    print("Trit encoding: − = retreat/far/negative")
    print("               ○ = null/hold/undecided")
    print("               + = approach/close/positive")
    print()
    print("Loom: 8 trits [sensor×5 | context | momentum | DECISION]")
    print()

    engine = ArcLoomDecisionEngine()

    # Simulate a hand approaching and retreating
    # (Replace with live sensor data on PYNQ)
    test_voltages = [
        # Far away (noise)
        0.03, 0.05, 0.02, 0.04, 0.03, 0.02, 0.03, 0.04, 0.03, 0.02,
        # Approaching
        0.08, 0.15, 0.30, 0.50, 0.80, 1.20, 1.60, 2.00, 2.40, 2.70,
        # Close and stable
        2.70, 2.65, 2.72, 2.68, 2.71,
        # Retreating
        2.40, 2.00, 1.50, 1.00, 0.60, 0.35, 0.20, 0.10, 0.05, 0.03,
        # Far and stable
        0.03, 0.02, 0.04, 0.03, 0.02,
    ]

    print(f"{'t':>3} | {'V':>5} | {'State':>10} | {'Decision':>8} | {'Conf':>5} | {'Steps':>5} | {'Krimelacks':>10}")
    print(f"{'-'*3}-+-{'-'*5}-+-{'-'*10}-+-{'-'*8}-+-{'-'*5}-+-{'-'*5}-+-{'-'*10}")

    for t, v in enumerate(test_voltages):
        decision, conf, state, steps = engine.process(v)
        n_memories = len(engine.krimelack.motifs)

        # Highlight decisions
        marker = ""
        if decision == "APPROACH":
            marker = " <<<WALL"
        elif decision == "RETREAT":
            marker = " >>>AWAY"

        print(f"{t:>3} | {v:>5.2f} | {state:>10} | {decision:>8} | {conf:>4.0%} | {steps:>5} | {n_memories:>10}{marker}")

    print()
    print(f"Total decisions: {engine.decision_count}")
    print(f"Krimelack motifs stored: {len(engine.krimelack.motifs)}")
    print()
    print("This is ArcLoom. Ternary. Structural. Not binary.")
    print("Not the kernel. Not Python pretending.")
    print("The LOOM settling to attractors IS the computation.")
