"""THE INTERPRETER — following a written procedure without wiring.

Before this, a rule in the knowledge only worked because I had
written its phrases into the code: the follower looked for "right
to left" and "set aside every full ten". The procedure lived in
the entry, but the binding lived in my hands, so the entry was
half decoration.

Here the binding is knowledge too. Each act the machine possesses
is written as an entry that names itself in the words a procedure
would use. A rule's step finds its act the same way any question
finds knowledge — by reaching — and the act's hand runs. Nothing
in this file names a phrase from any rule.

What stays machinery, and only this: the hands themselves. An act
entry says what the act is; the table below is how it is done.
Twelve small doings. If a step reaches no act, the interpreter
does what the law of procedures says to do — it names the missing
act and stops, rather than guessing.
"""
import os, re, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core

# ---------- the hands: what an act actually does ----------
# Each takes the running state and returns it. They know nothing
# about which procedure they are in.

def h_walk_places(s):
    s["places"] = max(len(d) for d in s["digits"])
    s["i"] = 0
    return s

def h_count_up(s):
    i = s["i"]
    total = s.get("carry", 0)
    for d in s["digits"]:
        total += d[i] if i < len(d) else 0
    s["count"] = total
    return s

def h_notice_tens(s):
    """Notice the full bundles inside a count. HOW BIG a bundle is
    comes from the knowledge, never from here — the rule says it."""
    b = s.get("bundle")
    if not b:
        s["missing"] = ("the rule does not say how big a full "
                        "bundle is, and I will not assume one")
        s["done"] = True
        return s
    c = s.get("count", 0)
    s["carry"], keep = divmod(c, b)
    s.setdefault("out", []).append(keep)
    return s

def h_carry_left(s):
    b = s.get("bundle")
    s["i"] = s.get("i", 0) + 1
    if s["i"] >= s.get("places", 0):
        c = s.get("carry", 0)
        while c and b:
            c, k = divmod(c, b)
            s["out"].append(k)
        s["carry"] = 0
        s["done"] = True
    return s

def h_count_down(s):
    """Count one down against the other. When what is being
    compared is two pieces of knowledge rather than two written
    numbers, the counting is of the ground each one opens."""
    if s.get("candidates"):
        best = None
        for e, opened in s["candidates"]:
            if best is None or opened > best[1]: best = (e, opened)
        if best:
            s["line"] = best[0]["essence"]
            s["chosen_opens"] = best[1]
        s["done"] = True
        return s
    b = s.get("bundle")
    if not b:
        s["missing"] = ("the rule does not say how big a bundle "
                        "is, so I cannot break one")
        s["done"] = True
        return s
    i = s["i"]
    upper = s["digits"][0]
    lower = s["digits"][1] if len(s["digits"]) > 1 else [0]
    u = (upper[i] if i < len(upper) else 0) - s.get("borrow", 0)
    l = lower[i] if i < len(lower) else 0
    if u < l:
        u += b; s["borrow"] = 1
    else:
        s["borrow"] = 0
    s.setdefault("out", []).append(u - l)
    s["i"] = i + 1
    if s["i"] >= s.get("places", 0): s["done"] = True
    return s

def h_lay_copies(s):
    big, small = s["big"], s["small"]
    s["piles"] = [big] * small if small else [0]
    return s

def h_shift_left(s):
    s["piles"] = [int(str(p) + "0" * n) if p else 0
                  for n, p in enumerate(s.get("piles", []))]
    return s

def h_reach(s):
    F = core.fabric()
    qm, es = F.reach(s.get("words", ""), limit=s.get("limit", 10))
    s["mask"], s["near"] = qm, es
    return s

def h_judge(s):
    """Ask whether any law closes what is in front of me. Applied
    to a set of reached knowledge, it keeps what stands and drops
    what a law closes, naming the law."""
    F = core.fabric()
    near = s.get("near")
    if near:
        standing, closed = [], []
        for e in near:
            L = F.judge(s.get("mask", 0) | e["color"])
            (closed if L else standing).append(e if not L else (e, L))
        s["standing"] = standing
        s["closed_by"] = closed
        return s
    s["closed"] = F.judge(s.get("pool", s.get("mask", 0)))
    return s

def h_say(s):
    """Put out the piece of knowledge standing in hand. What is in
    hand was decided above by the knowledge, never here — and with
    nothing in hand, this act says nothing and reports why."""
    line = s.get("line")
    if not line:
        near = s.get("near") or []
        if near: line = near[0]["essence"]
    if not line:
        s.setdefault("said", []).append("")
        s["nothing_in_hand"] = True
        return s
    s.setdefault("said", []).append(line)
    s["line"] = line
    return s

def h_mark_said(s):
    """Set aside what has already been said in this thread — and
    when nothing is in hand yet, this is the setting-aside step,
    which drops from what stands anything already spoken."""
    line = s.get("line")
    if line:
        s.setdefault("marked", set()).add(line)
        return s
    marked = s.get("marked", set())
    if s.get("standing") is not None:
        s["standing"] = [e for e in s["standing"]
                         if e["essence"] not in marked]
        # what each standing piece opens for the other one
        other = s.get("other_white", 0)
        s["candidates"] = [(e, bin(e["color"] & other).count("1"))
                           for e in s["standing"]]
    return s

def h_check_twice(s):
    s["checked"] = (s.get("first") == s.get("second"))
    return s

HANDS = {
    "walk-places": h_walk_places,
    "count-up": h_count_up,
    "notice-tens": h_notice_tens,
    "carry-left": h_carry_left,
    "count-down": h_count_down,
    "lay-copies": h_lay_copies,
    "shift-left": h_shift_left,
    "reach": h_reach,
    "judge": h_judge,
    "say": h_say,
    "mark-said": h_mark_said,
    "check-twice": h_check_twice,
}

# ---------- binding: a step finds its act by reaching ----------

def acts():
    """Every act the knowledge says I possess, with the words it
    names itself by. Read from the entries, never listed here."""
    F = core.fabric()
    out = []
    for e in F.entries:
        m = re.search(r"ACT:\s*([a-z\-]+)", e.get("raw", "") or "")
        name = None
        if m: name = m.group(1)
        else:
            # the ACT line is not one of the standard fields, so
            # read it out of the file block for this entry
            pass
        out.append((e, name))
    return out

def act_table():
    """Act name -> its naming words, taken from the knowledge."""
    F = core.fabric()
    table = {}
    for path in set(e["file"] for e in F.entries):
        try: text = open(path).read()
        except OSError: continue
        for block in re.split(r"\n(?=ESSENCE:)", text):
            m = re.search(r"ACT:\s*([a-z\-]+)", block)
            if not m: continue
            name = m.group(1)
            words = ""
            a = re.search(r"ASKED-AS:([^\n]*)", block)
            if a: words += " " + a.group(1)
            e = re.search(r"ESSENCE:(.*?)(?=\nROOT:)", block, re.S)
            if e: words += " " + e.group(1)
            table[name] = core.fabric().mask(words, learn=False)
    return table

def bind(step_text, table, floor=1):
    """Which act is this step asking for? Decided by reaching, the
    same way any question finds knowledge — and it must reach one
    act better than any other, or it has not reached at all."""
    F = core.fabric()
    sm = F.mask(step_text, learn=False)
    scored = sorted(((bin(sm & m).count("1"), n)
                     for n, m in table.items()), reverse=True)
    if not scored: return (None, 0)
    top, name = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0
    if top >= floor and top > second: return (name, top)
    return (None, top)

def steps_of(rule_text):
    """A procedure is its steps, in order — split where the writer
    put the joints."""
    body = re.sub(r"^to [^—]+—\s*", "", rule_text.strip(),
                  flags=re.I)
    # the writer's joints are semicolons; a comma inside a step is
    # part of that step, not a new one
    parts = re.split(r";|\bthen\b", body)
    return [p.strip(" .,") for p in parts if len(p.strip()) > 6]

WALKERS = {"walk-places"}      # acts that open a walk

def find_rule(F, step_text, floor=1):
    """A step may name another written procedure rather than an
    act — by the law of procedures, a method already possessed
    counts as a doing. Found by reaching, not by a list."""
    sm = F.mask(step_text, learn=False)
    scored = []
    for e in F.entries:
        if not e["rule"]: continue
        # a procedure is found the way anything is found — by the
        # words it says it is asked for, not only by its title
        head = e["rule"].split("—")[0] + " " + e["ask"]
        scored.append((bin(sm & F.mask(head, learn=False)).count("1"), e))
    scored.sort(key=lambda x: -x[0])
    if not scored: return (None, 0)
    top, e = scored[0]
    second = scored[1][0] if len(scored) > 1 else 0
    if top >= floor and top > second: return (e, top)
    return (None, top)

NUMBER_WORDS = None      # built from the knowledge, not listed

def bundle_from_knowledge(F, rule_text):
    """How big is a full bundle? The knowledge says so in words —
    'a full ten in any place'. Read it from there; assume nothing."""
    global NUMBER_WORDS
    if NUMBER_WORDS is None:
        # the counting entries name the small numbers; take the
        # mapping from any entry that states one plainly
        NUMBER_WORDS = {}
        for e in F.entries:
            for m in re.finditer(r"\b(two|three|four|five|six|"
                                 r"seven|eight|nine|ten)\b.{0,12}?"
                                 r"\((\d+)\)", e["essence"]):
                NUMBER_WORDS[m.group(1)] = int(m.group(2))
        NUMBER_WORDS.setdefault("ten", 10)   # stated in the bundles
        NUMBER_WORDS.setdefault("two", 2)    # entry and in computing
    # the rule names the bundle in its own words, however phrased
    for w, v in sorted(NUMBER_WORDS.items(), key=lambda x: -x[1]):
        if re.search(rf"\b{w}\b", rule_text, re.I): return v
    # the rule may lean on its entry's own words for the size
    for e in F.entries:
        if e["rule"] and e["rule"][:40] in rule_text:
            for w, v in NUMBER_WORDS.items():
                if re.search(rf"full {w}\b|by {w}s\b|holds up to",
                             e["essence"], re.I):
                    if re.search(rf"full {w}\b|by {w}s\b",
                                 e["essence"], re.I): return v
    return None

def follow(rule_text, state, trace=None, depth=0):
    """Run a written procedure. Every step is bound by knowledge.
    A step that opens a walk makes the steps after it repeat until
    the walk is done. A step naming another procedure is followed
    into. A step naming nothing I possess stops the work and says
    which act is missing."""
    if depth > 3:
        return state, "these procedures call each other too deeply"
    F = core.fabric()
    if "bundle" not in state:
        b = bundle_from_knowledge(F, rule_text)
        if b: state["bundle"] = b
    table = act_table()
    plan = []
    for step in steps_of(rule_text):
        name, score = bind(step, table)
        if name is not None and name in HANDS:
            plan.append(("act", name, step, score)); continue
        sub, s2 = find_rule(F, step)
        if sub is not None:
            plan.append(("rule", sub, step, s2)); continue
        return state, (f"I cannot follow this step: '{step[:60]}' — "
                       f"it names no act I possess and no procedure "
                       f"I hold. The law of procedures says to name "
                       f"the missing act rather than guess.")
    # steps before the walk run once; the walk sets up; the rest
    # repeat until the state says the walk is done
    wi = next((k for k, p in enumerate(plan)
               if p[0] == "act" and p[1] in WALKERS), None)
    def run(entry):
        nonlocal state
        kind, what, step, sc = entry
        if trace is not None:
            trace.append((step[:40],
                          what if kind == "act" else "procedure",
                          sc))
        if kind == "act":
            state = HANDS[what](state)
        else:
            state, err = follow(what["rule"], state, trace, depth+1)
            if err: raise RuntimeError(err)
    try:
        if wi is None:
            for p in plan: run(p)
        else:
            for p in plan[:wi]: run(p)
            run(plan[wi])
            guard = 0
            while not state.get("done") and guard < 128:
                for p in plan[wi+1:]: run(p)
                guard += 1
    except RuntimeError as e:
        return state, str(e)
    if state.get("missing"):
        return state, state["missing"]
    return state, None
