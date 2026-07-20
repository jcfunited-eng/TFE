"""
Visual Krimelack — Phase 2
GUALALOOM-V7-AUTONOMY-WC-2026-06-06

AdaptingFoveaKrimelack + SaccadeController + chi-binding profile identity.
No CNN, no embeddings, no pre-trained vision. Fovea krimelack does perception.
"""

import hashlib
import hmac
import json
import math
import numpy as np
from dataclasses import dataclass, field


# =========================================================================
# Constants (modeling-validated)
# =========================================================================
OMEGA_0 = 5.0
KAPPA_MAX = 50.0
WINDING_PHASE = 2 * math.pi
DT = 0.02  # substrate time step

COFIRE_OVERLAP_THRESHOLD = 0.85  # tunable — type-vs-instance discrimination
G32_FIRING_THRESHOLD = 0.55      # cosine on angle (from synthesis model)
GATE_INERTIA = 0.6
COUPLING_STRENGTH = 0.15


# =========================================================================
# AdaptingFoveaKrimelack
# =========================================================================
@dataclass
class AdaptingFoveaKrimelack:
    """Photoresistor krimelack with sensitivity adaptation.
    omega(t) = omega_0 + kappa_eff * s(t), kappa_eff = kappa_max * adapt_state.
    Adaptation: sustained bright → adapt_state decays → coupling drops.
    Removal → adapt_state recovers slowly (asymmetric).

    Pixel intensity is the photoresistor signal itself.  The canonical
    visual equation advances phase from omega, not from the tick-to-tick
    derivative of intensity.  Event records retain the actual intensity
    present at each winding transition."""
    omega_0: float = OMEGA_0
    kappa_max: float = KAPPA_MAX
    adapt_tau: float = 12.0       # seconds at strong signal to half-adapt
    recover_tau: float = 60.0     # seconds to recover (asymmetric, slow)
    phase: float = 0.0
    winding_count: int = 0
    events: list = field(default_factory=list)
    adapt_state: float = 1.0

    def tick(self, intensity, t):
        kappa_eff = self.kappa_max * self.adapt_state
        omega = self.omega_0 + kappa_eff * intensity
        self.phase += omega * DT
        while self.phase >= WINDING_PHASE:
            self.winding_count += 1
            self.phase -= WINDING_PHASE
            self.events.append({"t": t, "dw": +1, "s": intensity})
        while self.phase <= -WINDING_PHASE:
            self.winding_count -= 1
            self.phase += WINDING_PHASE
            self.events.append({"t": t, "dw": -1, "s": intensity})
        # Sustained brightness desensitizes the receptor.
        if intensity > 0.1:
            self.adapt_state -= self.adapt_state * (intensity / self.adapt_tau) * DT
        else:
            self.adapt_state += (1.0 - self.adapt_state) * DT / self.recover_tau
        self.adapt_state = max(0.05, min(1.0, self.adapt_state))

    def intervals(self):
        if len(self.events) < 2:
            return []
        return [self.events[i+1]["t"] - self.events[i]["t"]
                for i in range(len(self.events) - 1)]

    def reset(self):
        self.phase = 0.0
        self.events = []
        self.adapt_state = 1.0


# =========================================================================
# SaccadeController — peripheral salience, novelty-driven
# =========================================================================
class SaccadeController:
    def __init__(self, image, seed=None):
        self.image = image
        self.h, self.w = image.shape
        self.rng = np.random.default_rng(seed)
        self.fixated = set()
        self.n_rows = 4
        self.n_cols = 4
        self.h_step = max(1, self.h // self.n_rows)
        self.w_step = max(1, self.w // self.n_cols)

    def pick(self):
        """Pick next fixation based on peripheral salience + novelty."""
        g = np.zeros((self.n_rows, self.n_cols))
        for r in range(self.n_rows):
            for c in range(self.n_cols):
                r0, r1 = r * self.h_step, min((r+1) * self.h_step, self.h)
                c0, c1 = c * self.w_step, min((c+1) * self.w_step, self.w)
                region = self.image[r0:r1, c0:c1]
                g[r, c] = np.std(region) if region.size > 0 else 0.0

        candidates = []
        for r in range(self.n_rows):
            for c in range(self.n_cols):
                if (r, c) not in self.fixated:
                    score = g[r, c] + 0.01 * self.rng.random()
                    candidates.append((score, r, c))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        _, r, c = candidates[0]
        self.fixated.add((r, c))
        cy = r * self.h_step + self.h_step // 2
        cx = c * self.w_step + self.w_step // 2
        cy = max(0, min(self.h - 1, cy + self.rng.integers(-1, 2)))
        cx = max(0, min(self.w - 1, cx + self.rng.integers(-1, 2)))
        return (cy, cx)


# =========================================================================
# VisualPerceptFragment
# =========================================================================
@dataclass
class VisualPerceptFragment:
    fixation_coord: tuple
    event_ticks: list    # Temporal projection used by chi interval geometry
    event_records: list  # Full native records: time, winding direction, signal
    winding_count: int
    source_id: str       # label only, NOT identity
    born_tick: int


VISUAL_FRAGMENT_RECEIPT_SCHEMA = "guala.native_sight_fragment.v1"
_VISUAL_DSF_UNKNOWN_REASON = (
    "native_visual_fragment_has_no_ratified_full_field_operator")


def _receipt_digest(payload):
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def visual_fragment_receipt(fragment):
    """Preserve one native foveal output without inventing missing DSF fields."""
    payload = {
        "schema": VISUAL_FRAGMENT_RECEIPT_SCHEMA,
        "fixation_coord": [
            int(fragment.fixation_coord[0]),
            int(fragment.fixation_coord[1]),
        ],
        "events": [
            {
                "t": int(event["t"]),
                "dw": int(event["dw"]),
                "s": float(event["s"]),
            }
            for event in fragment.event_records
        ],
        "winding_count": int(fragment.winding_count),
        "source_id": str(fragment.source_id),
        "born_tick": int(fragment.born_tick),
        "dsf": {
            "status": "unknown",
            "reason": _VISUAL_DSF_UNKNOWN_REASON,
        },
    }
    return {**payload, "receipt_sha256": _receipt_digest(payload)}


def validate_visual_fragment_receipt(receipt):
    """Fail closed unless a stored foveal receipt is complete and untampered."""
    if not isinstance(receipt, dict):
        return False
    expected_keys = {
        "schema", "fixation_coord", "events", "winding_count",
        "source_id", "born_tick", "dsf", "receipt_sha256",
    }
    if set(receipt) != expected_keys:
        return False
    if receipt.get("schema") != VISUAL_FRAGMENT_RECEIPT_SCHEMA:
        return False
    fixation = receipt.get("fixation_coord")
    if (not isinstance(fixation, list) or len(fixation) != 2
            or any(isinstance(value, bool) or not isinstance(value, int)
                   for value in fixation)):
        return False
    if (not isinstance(receipt.get("source_id"), str)
            or not receipt["source_id"]):
        return False
    for name in ("winding_count", "born_tick"):
        value = receipt.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            return False
    if receipt.get("dsf") != {
            "status": "unknown", "reason": _VISUAL_DSF_UNKNOWN_REASON}:
        return False
    events = receipt.get("events")
    if not isinstance(events, list):
        return False
    previous_t = None
    for event in events:
        if not isinstance(event, dict) or set(event) != {"t", "dw", "s"}:
            return False
        t = event.get("t")
        dw = event.get("dw")
        signal = event.get("s")
        if (isinstance(t, bool) or not isinstance(t, int)
                or dw not in (-1, 1) or isinstance(dw, bool)
                or isinstance(signal, bool)
                or not isinstance(signal, (int, float))
                or not math.isfinite(float(signal))
                or (previous_t is not None and t < previous_t)):
            return False
        previous_t = t
    supplied_digest = receipt.get("receipt_sha256")
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
        return False
    payload = {
        key: receipt[key]
        for key in expected_keys
        if key != "receipt_sha256"
    }
    try:
        actual_digest = _receipt_digest(payload)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(supplied_digest, actual_digest)


# =========================================================================
# Chi-binding profile — substrate-native identity
# =========================================================================
def chi_binding_profile(fragment_or_intervals):
    """Multiset of binned inter-event intervals, normalized.
    Accepts VisualPerceptFragment or raw interval list."""
    if isinstance(fragment_or_intervals, VisualPerceptFragment):
        events = fragment_or_intervals.event_ticks
        if len(events) < 2:
            return {}
        intervals = [events[i+1] - events[i] for i in range(len(events) - 1)]
    else:
        intervals = fragment_or_intervals
    if not intervals:
        return {}
    profile = {}
    for iv in intervals:
        b = int(iv)
        profile[b] = profile.get(b, 0) + 1
    total = sum(profile.values())
    return {b: c / total for b, c in profile.items()}


def aggregate_profiles(profiles):
    """Aggregate multiple chi-binding profiles into one viewing profile."""
    combined = {}
    for p in profiles:
        for b, w in p.items():
            combined[b] = combined.get(b, 0) + w
    total = sum(combined.values())
    if total > 0:
        return {b: w / total for b, w in combined.items()}
    return {}


def chi_overlap(p1, p2):
    """Sum of min(weight) over shared bins. 1.0 = identical, 0.0 = disjoint."""
    all_bins = set(p1) | set(p2)
    return sum(min(p1.get(b, 0), p2.get(b, 0)) for b in all_bins)


# =========================================================================
# VisualMotif
# =========================================================================
@dataclass
class VisualMotif:
    motif_id: int
    section: str = "sight"
    chi_profile: dict = field(default_factory=dict)
    cluster_state: list = field(default_factory=list)
    angle: list = field(default_factory=list)  # founding G32 token — IMMUTABLE
    n_firings: int = 0
    source_history: list = field(default_factory=list)
    founded_at_tick: int = 0

    def __post_init__(self):
        """Keep source associations, never a lifetime encounter ledger.

        Older saved motifs can contain the same source once per viewing
        (especially millions of repeated ``camera_stream`` frames).  Preserve
        every distinct source and its most-recent ordering while collapsing
        those duplicate encounters.  ``n_firings`` remains the scalar exposure
        count, so learning strength is not lost.
        """
        seen = set()
        compacted_reversed = []
        for source_id in reversed(self.source_history):
            if source_id in seen:
                continue
            seen.add(source_id)
            compacted_reversed.append(source_id)
        self.source_history = list(reversed(compacted_reversed))

    def observe_source(self, source_id):
        """Associate this motif with a source and retain recency once."""
        try:
            self.source_history.remove(source_id)
        except ValueError:
            pass
        self.source_history.append(source_id)


# =========================================================================
# View a picture — saccaded foveation producing fragments
# =========================================================================
def view_picture(image, source_id, born_tick, seed=None,
                 n_fixations=12, ticks_per_fixation=300):
    """Run saccade controller + fovea krimelack on image.
    Returns list of VisualPerceptFragments."""
    sacc = SaccadeController(image, seed=seed)
    krim = AdaptingFoveaKrimelack()
    fragments = []
    t = born_tick

    for _ in range(n_fixations):
        fixation = sacc.pick()
        if fixation is None:
            break
        krim.reset()
        start_t = t
        for _ in range(ticks_per_fixation):
            jitter_r = sacc.rng.integers(-1, 2)
            jitter_c = sacc.rng.integers(-1, 2)
            r = max(0, min(image.shape[0] - 1, fixation[0] + jitter_r))
            c = max(0, min(image.shape[1] - 1, fixation[1] + jitter_c))
            intensity = float(image[r, c])
            krim.tick(intensity, t)
            t += 1

        frag = VisualPerceptFragment(
            fixation_coord=fixation,
            event_ticks=[event["t"] for event in krim.events],
            event_records=[
                {
                    "t": event["t"],
                    "dw": event["dw"],
                    "s": event["s"],
                }
                for event in krim.events
            ],
            winding_count=krim.winding_count,
            source_id=source_id,
            born_tick=start_t,
        )
        fragments.append(frag)

    return fragments


# =========================================================================
# Sight section — commit-or-fire with chi-profile identity
# =========================================================================
class SightSection:
    """Manages visual motifs with chi-profile-based identity."""

    def __init__(self):
        self.motifs = []
        self._next_id = 0

    def process_viewing(self, fragments, source_id, tick):
        """Process fragments from one viewing. Returns (motif, is_new, overlap)."""
        # Aggregate per-fixation profiles into viewing profile
        per_frag_profiles = [chi_binding_profile(f) for f in fragments]
        viewing_profile = aggregate_profiles(per_frag_profiles)
        if not viewing_profile:
            return None, False, 0.0

        # Compute simple G32-like token from fragment stats
        intensities = []
        for f in fragments:
            if f.event_ticks:
                intensities.append(len(f.event_ticks))
        mean_rate = np.mean(intensities) if intensities else 0
        coherence = 1.0 / (1.0 + np.std(intensities)) if intensities else 0
        g_token = [mean_rate / 100.0, coherence, 0.5, 0.5]  # simplified

        # Find best match by chi-profile overlap
        best_match = None
        best_overlap = 0.0
        for m in self.motifs:
            ov = chi_overlap(viewing_profile, m.chi_profile)
            if ov > best_overlap:
                best_overlap = ov
                best_match = m

        if best_match is not None and best_overlap >= COFIRE_OVERLAP_THRESHOLD:
            # Fire existing motif
            best_match.n_firings += 1
            best_match.observe_source(source_id)
            # Cluster dynamics
            state = np.array(best_match.cluster_state)
            g = np.array(g_token[:len(state)])
            new_state = GATE_INERTIA * state + (1 - GATE_INERTIA) * g
            best_match.cluster_state = new_state.tolist()
            return best_match, False, best_overlap
        else:
            # Commit new motif
            mid = self._next_id
            self._next_id += 1
            motif = VisualMotif(
                motif_id=mid,
                chi_profile=viewing_profile,
                cluster_state=list(g_token),
                angle=list(g_token),
                n_firings=1,
                source_history=[source_id],
                founded_at_tick=tick,
            )
            self.motifs.append(motif)
            return motif, True, best_overlap

    def snapshot(self):
        return {
            "n_motifs": len(self.motifs),
            "motifs": [{"motif_id": m.motif_id,
                        "n_firings": m.n_firings,
                        "n_sources": len(m.source_history),
                        "founded_at_tick": m.founded_at_tick}
                       for m in self.motifs],
        }
