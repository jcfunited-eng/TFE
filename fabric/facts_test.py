"""DO THE KNOWN LAWS FALL OUT — the test of the function class.

Nothing here writes a law down. Each case parameterises one of the
three facts, runs the same walker, and checks the number that comes
out against what is known to be true. If a law has to be typed in for
it to appear, the class is wrong.

The phylums are the parameterisations. Cooling and depreciation are
the SAME instance of entropy with different units, which is the claim
being tested: that the other phylums are outcomes of the maths.
"""
import os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import facts


def close(a, b, tol=0.02):
    return a is not None and abs(a - b) <= tol * max(1.0, abs(b))


def cases():
    out = []

    # ENTROPY, on heat. A thing in a cold room ends at the room.
    s = facts.run(facts.entropy(k=1.0), x0=90.0, env=20.0)
    out.append(("a hot thing in a room at 20 ends at 20",
                facts.settles_at(s), 20.0))

    # the SAME instance, on value. Nothing about money is written.
    s = facts.run(facts.entropy(k=0.6), x0=1000.0, env=0.0,
                  steps=2000)
    out.append(("a value with nothing holding it ends at nothing",
                facts.settles_at(s), 0.0))

    # entropy never returns all it took: halving time is fixed
    # one halving-time for k=1 is 0.6931 of time, not 69.31 -- my
    # arithmetic, not the class's
    s = facts.run(facts.entropy(k=1.0), x0=100.0, env=0.0,
                  dt=0.0001, steps=6931)
    out.append(("what is left after one halving-time of decay",
                s[-1], 50.0))

    # GREED against a limited supply settles AT the supply
    s = facts.run(facts.greed(rate=1.0, supply=500.0), x0=5.0,
                  steps=2000)
    out.append(("a taker on a supply of 500 settles at 500",
                facts.settles_at(s), 500.0))

    # TWO takers of ONE supply: together they still only reach it
    h = facts.run_together([facts.greed(1.0, 500.0),
                            facts.greed(0.8, 500.0)],
                           [5.0, 5.0], steps=3000)
    out.append(("two takers of one supply of 500, added together",
                h[-1][0] + h[-1][1], 500.0))

    # the faster taker holds more of it than the slower one
    out.append(("and the faster taker holds more than the slower",
                1.0 if h[-1][0] > h[-1][1] else 0.0, 1.0))

    # COHESION: attraction against loosening settles part-way, and
    # a thing is ONE when attraction beats loosening
    s = facts.run(facts.cohesion(attract=1.0, loosen=1.0), x0=0.0)
    out.append(("attraction equal to loosening holds half together",
                facts.settles_at(s), 0.5))
    s = facts.run(facts.cohesion(attract=3.0, loosen=1.0), x0=0.0)
    out.append(("attraction three times the loosening: three quarters",
                facts.settles_at(s), 0.75))

    # ENTROPY AND COHESION TOGETHER: a bond in a warm place. The
    # warmer the surroundings, the less holds together -- which is
    # melting, and no one wrote melting down.
    for env, name in ((0.2, "cool"), (2.0, "warm")):
        s = facts.run(facts.cohesion(attract=1.0, loosen=env), x0=0.5)
        out.append(("what holds together when it is " + name,
                    facts.settles_at(s), 1.0 / (1.0 + env)))
    return out


def grade():
    rows, good = [], 0
    for name, got, want in cases():
        ok = close(got, want)
        good += ok
        rows.append((name, got, want, ok))
    return rows, good


if __name__ == "__main__":
    rows, good = grade()
    for name, got, want, ok in rows:
        print("  %-4s %-52s got %-9s want %s"
              % ("ok" if ok else "FAIL", name,
                 ("%.3f" % got) if got is not None else "none", want))
    print("\n  LAWS THAT FELL OUT: %d/%d" % (good, len(rows)))
