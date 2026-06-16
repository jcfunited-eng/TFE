"""
Hypothesis: amnesty-before-dream sets last_tick to T_amnesty,
then ~5000 ticks of paused dream pass without decay calls,
then unpause fires decay with dt = ~5000 on unreinforced entries.

Production constants (from gualaloom_v6_living_atlas.py):
"""
import math

DECAY_LAMBDA = 0.0001      # per tick
SLOW_DIV = 12              # slow channel divisor
DWELL_GATE_META = 4
META_K = 2.0

# Observed from substrate status (c1's Step 5 post-dream readout):
PRE_UNPAUSE_TOTAL = 14800.71
PRE_UNPAUSE_09_10_BAND = 9102    # approx, from handoff baseline; band was repopulated by dream

# Observed after unpause + 1200 ticks of decay:
POST_UNPAUSE_TOTAL = 8439.68
POST_UNPAUSE_09_10_BAND = 10

# Population breakdown (current status):
N_FAST = 19131
N_SLOW = 1108
N_RELEASED = 20631    # released = True → fast channel

# === Test 1: What dt does the observed loss imply? ===
# If lam_eff = DECAY_LAMBDA = 1e-4 (fast channel, rc=0, legacy entry),
# and the average strong entry went from ~1.0 to ~0.6 (mid 0.5-0.7 band):
mult_observed_strong = 0.6  # 1.0 → 0.6 for strong bindings
lam_eff_fast = DECAY_LAMBDA
dt_implied = math.log(1.0 / mult_observed_strong) / lam_eff_fast
print(f"=== Test 1: implied dt at fast-channel λ ===")
print(f"  Observed strong-binding multiplier: {mult_observed_strong}")
print(f"  λ (fast, rc=0):                     {lam_eff_fast}")
print(f"  Implied dt:                         {dt_implied:.0f} ticks")
print(f"  Implied dt at slow channel (λ/12):  {dt_implied * 12:.0f} ticks")
print()

# === Test 2: What if amnesty happened, then 5000 ticks of paused dream, then unpause? ===
# Amnesty at T. Dream runs T → T+5000 with DECAY_PAUSED=1 (no decay calls).
# Unpause at T+5000. First decay call sees dt = 5000 for unreinforced entries.
# Decay called every 10 ticks. last_tick updated each call.
#
# After unpause:
#   tick T+5010 (first decay call): dt = 5010, mult = exp(-1e-4 * 5010) = 0.606
#   tick T+5020 (second call):       dt = 10,  mult = exp(-1e-4 * 10)   = 0.9990
#   ... subsequent calls all dt=10 ...

T_amnesty = 100000
T_dream_end = T_amnesty + 5000     # 5000 ticks of dream while paused
T_observation = T_dream_end + 1200  # 1200 ticks after unpause (c1's monitoring)

# Per-entry strength simulation (start at 1.0, never reinforced after amnesty)
strength = 1.0
last_tick = T_amnesty
cur = T_dream_end  # unpause fires here
print(f"=== Test 2: simulate cascade on unreinforced fast-channel entry ===")
print(f"  T_amnesty:    {T_amnesty}")
print(f"  T_dream_end:  {T_dream_end}  (last_tick still = T_amnesty, no decay during pause)")
print(f"  Unpause fires at T_dream_end")
print()
# Simulate decay sweeps every 10 ticks for 1200 ticks
n_sweeps = 0
while cur < T_observation:
    cur += 10
    dt = max(0, cur - last_tick)
    if dt > 0:
        lam_eff = DECAY_LAMBDA  # fast channel, rc=0
        strength *= math.exp(-lam_eff * dt)
        last_tick = cur
        n_sweeps += 1
        if n_sweeps <= 3 or n_sweeps == 120:
            print(f"  sweep {n_sweeps}: cur={cur}, dt={dt}, strength={strength:.4f}")

print(f"\n  Final strength after {n_sweeps} sweeps: {strength:.4f}")
print(f"  Observed strong-binding multiplier:  {mult_observed_strong}")
print(f"  Match? {abs(strength - mult_observed_strong) < 0.05}")
print()

# === Test 3: with proposed fix — keep last_tick fresh during pause ===
# Same scenario but during pause, decay is called with rate_scale=0.0.
# This updates last_tick each sweep without applying multiplier.
strength = 1.0
last_tick = T_amnesty
cur = T_amnesty
print(f"=== Test 3: WITH FIX — rate_scale=0.0 during pause ===")
# During pause: 5000 ticks of "rate_scale=0" sweeps
while cur < T_dream_end:
    cur += 10
    dt = max(0, cur - last_tick)
    if dt > 0:
        rate_scale = 0.0
        lam_eff = DECAY_LAMBDA * rate_scale
        strength *= math.exp(-lam_eff * dt)  # exp(0) = 1
        last_tick = cur
# Now unpause: rate_scale = 1.0
n_sweeps = 0
while cur < T_observation:
    cur += 10
    dt = max(0, cur - last_tick)
    if dt > 0:
        rate_scale = 1.0
        lam_eff = DECAY_LAMBDA * rate_scale
        strength *= math.exp(-lam_eff * dt)
        last_tick = cur
        n_sweeps += 1
print(f"  Final strength after fix:        {strength:.4f}")
print(f"  Expected normal slow decay (1200 ticks @ fast λ): {math.exp(-DECAY_LAMBDA * 1200):.4f}")
print()

# === Test 4: aggregate impact — what fraction of strong bindings would cascade? ===
print(f"=== Test 4: aggregate predicted strength loss ===")
# Assume 9102 strong (1.0) bindings, all on fast channel pre-cascade
# (released=True after dream consolidation puts them on fast channel — see release_to_fast)
n_strong = 9102
pre_total = n_strong * 1.0
post_per_entry = math.exp(-DECAY_LAMBDA * (1200 + 5000))  # full gap
post_total = n_strong * post_per_entry
print(f"  Pre  total (strong band): {pre_total:.0f}")
print(f"  Post total (after cascade): {post_total:.0f}")
print(f"  Loss: {pre_total - post_total:.0f}")
print(f"  % retained: {post_total / pre_total * 100:.1f}%")
print()
print(f"  Actual observed total loss: {PRE_UNPAUSE_TOTAL - POST_UNPAUSE_TOTAL:.0f}")
print(f"  Model predicted (strong band only): {pre_total - post_total:.0f}")
