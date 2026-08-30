"""THE THREE FACTS AS AN ALGORITHMIC FUNCTION CLASS.

Joe, 2026-08-30: "there are only 3 facts in this universe — Entropy,
Cohesion, and Greed ... if it were me doing it I would create an
algorithmic function class."

Not three subroutines that print sentences. A FAMILY of functions,
parameterised. This is why maths runs through every phylum: the maths
IS the function class, and a phylum is only a choice of parameters and
units. Entropy on heat is cooling; on concentration, diffusion; on a
bond, decay; on value, depreciation. One operator, four instances.

  ENTROPY   d/dt of a held quantity is proportional to the difference
            between it and what it touches, always toward level, and
            never returning all it took.
                x' = -k (x - e)

  COHESION  what attracts binds; binding is an attraction against a
            loosening, and a thing becomes ONE when the first beats
            the second.
                b' = a(x)(1 - b) - u b        one when b -> 1

  GREED     a taker grows by what it takes, at a rate set by what is
            there to take, and two takers of one thing subtract from
            each other.
                x' = r x (s - sum of takers) / s

Nothing below names heat, or a market, or bread. Those are
parameterisations. If a known law has to be typed in for it to appear,
the class is wrong -- so the test at the bottom asks whether the laws
fall OUT.

MINE, ON TRIAL: the three forms above. The facts are Joe's; writing
them as those particular equations is my construct and is the first
thing to argue with.
"""


# ---------------------------------------------------------------
# the class: three operators, parameterised
# ---------------------------------------------------------------

def entropy(k):
    """A difference levels. Returns the rate for a held quantity
    against what surrounds it."""
    def f(x, env=0.0, **_):
        return -k * (x - env)
    f.fact, f.arg = "entropy", dict(k=k)
    return f


def cohesion(attract, loosen):
    """What attracts binds against what loosens. Returns the rate for
    how strongly a thing holds together, between nothing and one."""
    def f(b, x=1.0, **_):
        return attract * x * (1.0 - b) - loosen * b
    f.fact, f.arg = "cohesion", dict(attract=attract, loosen=loosen)
    return f


def greed(rate, supply):
    """A taker grows by what it takes, limited by what is left, and
    two takers of one supply subtract from each other."""
    def f(x, others=0.0, **_):
        left = (supply - x - others) / supply if supply else 0.0
        return rate * x * left
    f.fact, f.arg = "greed", dict(rate=rate, supply=supply)
    return f


CLASS = dict(entropy=entropy, cohesion=cohesion, greed=greed)


# ---------------------------------------------------------------
# running an instance: the same walker for every parameterisation
# ---------------------------------------------------------------

def run(f, x0, steps=400, dt=0.05, **kw):
    """One walker for the whole class. It knows nothing about which
    fact it is running or what the numbers are called."""
    x, out = float(x0), [float(x0)]
    for _ in range(steps):
        x = x + dt * f(x, **kw)
        out.append(x)
    return out


def run_together(fs, x0s, steps=400, dt=0.05, env=0.0):
    """Several takers of one supply, or several things touching. Each
    sees the others -- which is the whole of contention."""
    xs = [float(v) for v in x0s]
    hist = [list(xs)]
    for _ in range(steps):
        new = []
        for i, f in enumerate(fs):
            others = sum(xs[j] for j in range(len(xs)) if j != i)
            new.append(xs[i] + dt * f(xs[i], others=others, env=env))
        xs = new
        hist.append(list(xs))
    return hist


def settles_at(series, tol=1e-4):
    """Where a run ends up, if it ends up anywhere."""
    a, b = series[-2], series[-1]
    return b if abs(b - a) < tol else None
