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
    """Reach for what the other one is reaching for, leaning on the
    thread when what was said is thin.

    The leaning is the second half of the step as it is written, and
    no act had ever done it. A thin thing said — "why", "it", "and?"
    — carries almost no ground of its own, so it takes up the ground
    the thread is already standing on. Without this, a follow-up
    walks from the word "else" and every turn is a standing start,
    which the wall forbids outright."""
    F = core.fabric()
    words = s.get("words", "")
    qm = F.mask(words, learn=False)
    rare = 0
    i, m = 0, qm
    while m:
        if m & 1:
            d = F.df.get(i, 0)
            if d and d < len(F.entries) * 0.02:
                rare += 1
        m >>= 1
        i += 1
    if rare == 0 and s.get("thread_words"):
        # Lean on the thread — but on what the thread SETTLED, not on
        # its raw words. Leaning on raw words re-opens every sense the
        # thread already closed: after "why do onions make you cry"
        # was settled onto the onion, a bare "what else" dragged the
        # word "cry" back in and landed in infancy. What the thread
        # stands on is what it leans on.
        words = (s.get("settled") or s["thread_words"]) + " " + words
        s["leaned"] = True
    # Settle which sense is meant from the company present, before
    # reaching anything. The company is the whole thread, not just
    # this turn — which is the point of a thread surviving the turn.
    # Without this the reach is a bag of letters: "discovery" went to
    # compelled disclosure in litigation while a conversation about
    # finding things out was standing open, and onions went to
    # mourning. A sense is PRODUCED from the company at hand and
    # never fetched, so what is stored is each sense's company and
    # the company present is what picks.
    company = (s.get("thread_words", "") + " " + words).lower()
    # Stem both sides. The question says "onions" and the company
    # says "onion", and matching raw strings meant the sense never
    # settled at all — everything downstream was working correctly on
    # a sense that had never been chosen.
    present = {core.stem(w)
               for w in re.findall(r"[a-z]{3,}", company)}
    chosen = []
    for e in F.entries:
        sp = e.get("splits") or ""
        if not sp:
            continue
        groups = []
        for part in sp.split("|"):
            if ":" not in part:
                continue
            nm, comp = part.split(":", 1)
            cw = {core.stem(w)
                  for w in re.findall(r"[a-z]{3,}", comp.lower())}
            if not cw:
                continue
            groups.append((nm.strip(), cw))
        if len(groups) < 2:
            continue
        # the ambiguous word itself has to be in front of us
        head = set.intersection(*[g[1] for g in groups]) or set()
        if not (head & present):
            continue
        best, score = None, 1      # one word of company can be
        for nm, cw in groups:      # borrowed; two together are not
            v = len((cw - head) & present)
            if v > score:
                best, score = cw, v
        if best:
            # Carry the company that SETTLED the sense, not the
            # ambiguous word itself. "cry" and "tears" are in every
            # sense of cry, so sending them along re-opens the very
            # ambiguity that was just closed — which is how a thread
            # settled on onions still drifted into infancy.
            chosen.append(" ".join(sorted(best - head)))
    if chosen:
        s["sense"] = chosen
        words = words + " " + " ".join(chosen)
        s["settled_now"] = " ".join(chosen)
    # READ what was said, rather than treating it as a bag of
    # letters. The language program groups the sentence, builds a
    # nesting and finds the doing by contrast; the asking words say
    # what KIND of answer will count and are not what the sentence is
    # about, so they do not travel. Reaching from a word bag is what
    # this whole file exists to stop being.
    try:
        import first_ribbon as FR
        res = FR.read(s.get("words", ""))
        if not res["missing"] and res["groups"]:
            gs = res["groups"]
            asking = FR.company().asking
            heads = []
            if res["stood"]:
                _sc, _p, doing = res["stood"][0]
                heads.append(FR.head(gs[doing]))
                s["doing"] = heads[0]
            for g in gs:
                if set(g) & asking:
                    continue          # says what kind, not what about
                h = FR.head(g)
                if h not in heads:
                    heads.append(h)
            if heads:
                s["read_as"] = " | ".join(" ".join(g) for g in gs)
                # the doing carries most, so it is said twice
                words = (" ".join(heads) + " " + heads[0] + " "
                         + words)
    except Exception as e:
        s["unread"] = f"{type(e).__name__}: {e}"
    qm, es = F.reach(words, limit=s.get("limit", 10))
    # An entry about a WORD settles which sense is meant and then
    # gets out of the way. Asked why onions sting, the answer is the
    # chemistry — that "cry" has three senses is how the question was
    # understood, not what it was asking. 170 writes this as a wall.
    about_words = ("words with two meanings", "words that mean the same",
                   "when words mislead", "what words go together")
    asked_about_words = bool(re.search(
        r"\b(word|words|sense|senses|meaning|means|mean)\b",
        (s.get("words") or "").lower()))
    if not asked_about_words:
        kept = [e for e in es if e["field"] not in about_words]
        if kept:
            es = kept
    s["mask"], s["near"] = qm, es
    return s

def h_judge(s):
    """Test each thing in hand: does any law close it. Leaves a
    pass or fail on each. Keeps nothing, drops nothing, chooses
    nothing."""
    F = core.fabric()
    import eliminate
    items = s.get("items")
    if items is None:
        s["closed"] = eliminate.closes(s.get("mask", 0),
                                       s.get("pool",
                                             s.get("mask", 0)), F)
        return s
    # Only a wall of the forbidding kind, and only one that is about
    # the thing itself, may close what is in hand. Judging with the
    # requirement walls failed all ten things the turn had hold of
    # and the fabric went silent every time. See eliminate.closes.
    # Judge the thing on its OWN ground, never on the question's
    # words as well. With the asking folded in, the question supplies
    # half of what a wall needs and the wall fires on a thing it is
    # not about: a wall about breaking a habit at the behaviour end
    # closed the entry on cutting onions, because "break" and "cut"
    # were in the bag. This is the third time the same mistake has
    # been made here in one day — judging a thing against a bag
    # bigger than the thing.
    laws = eliminate.forbidding(F)
    s["pass"] = [eliminate.closes(e["color"], e["color"], F, laws)
                 is None for e in items]
    return s

def h_say(s):
    """Put out the sentence standing in hand. With nothing in hand
    it says nothing — silence, which the knowledge calls a lawful
    move."""
    line = s.get("line")
    if not line:
        s["nothing_in_hand"] = True
        return s
    s.setdefault("said", []).append(line)
    return s

def h_mark_said(s):
    """Remember that the thing in hand was said."""
    line = s.get("line")
    if line: s.setdefault("marked", set()).add(line)
    return s

def h_test_said(s):
    """Test each thing in hand: has it been said already. Leaves a
    pass or fail on each."""
    marked = s.get("marked", set())
    items = s.get("items") or []
    s["pass"] = [e["essence"] not in marked for e in items]
    return s

def h_walk_each(s):
    """Take the things reached as the things in hand, to be worked
    one for one."""
    if s.get("items") is None:
        s["items"] = list(s.get("near") or [])
    return s

def h_test_coheres(s):
    """Test each thing in hand: does it meet more than one of the
    words said, or only one and nothing else. Leaves a pass or a
    fail; keeps nothing, drops nothing, chooses nothing."""
    qm = s.get("mask", 0)
    # "More than one of the words said, or only one and nothing
    # else." When the asking HAS only one word, meeting that word is
    # meeting all of it, and demanding two makes the test impossible
    # to pass honestly — "what is a wheel" then threw away the entry
    # about wheels and kept one about remainders, because that one
    # happened to repeat the word in two places.
    said = bin(qm).count("1")
    need = min(2, said) or 1
    s["pass"] = [bin(e["color"] & qm).count("1") +
                 bin(e["askm"] & qm).count("1") >= need
                 for e in (s.get("items") or [])]
    return s

def h_keep_passing(s):
    """Keep only the things whose last test passed."""
    items = s.get("items") or []
    ok = s.get("pass") or [True] * len(items)
    s["items"] = [e for e, p in zip(items, ok) if p]
    s["pass"] = None
    return s

def h_count_shared(s):
    """Count what each thing in hand shares with the other one's
    ground. Leaves a number on each; ranks nothing."""
    other = s.get("other_white", 0)
    if other:
        s["num"] = [bin(e["color"] & other).count("1")
                    for e in (s.get("items") or [])]
        return s
    # With nobody else on the other side, the other one IS the
    # asker, and what a thing opens for them is how much of what
    # they asked it actually covers — counted in uncommon words,
    # since the common ones are covered by everything. Without this
    # the count was zero for every candidate and "keep the greatest"
    # kept whichever happened to be reached first, which is how
    # "what is a wheel" answered with remainders.
    F = core.fabric()
    qm = s.get("mask", 0)
    common = len(F.entries) // 50
    out = []
    for e in (s.get("items") or []):
        n, i, m = 0, 0, (e["color"] | e["askm"]) & qm
        while m:
            if m & 1:
                n += 3 if F.df.get(i, 0) <= common else 1
            m >>= 1
            i += 1
        # what it is ASKED AS counts double: that line exists to say
        # what this entry is the answer to
        n += 2 * bin(e["askm"] & qm).count("1")
        # and an entry that OPENS by naming the thing is about it.
        # "the wheel converts dragging into rolling" is about wheels
        # in a way that a sentence mentioning a wheel of remainders
        # halfway through is not.
        head = F.mask(" ".join(e["essence"].split()[:5]),
                      learn=False)
        n += 4 * bin(head & qm).count("1")
        out.append(n)
    s["num"] = out
    return s

def h_keep_greatest(s):
    """Keep the thing carrying the greatest number."""
    items = s.get("items") or []
    nums = s.get("num") or []
    if not items: return s
    if not nums: nums = [0] * len(items)
    order = sorted(range(len(items)), key=lambda i: -nums[i])
    best = order[0]
    s["items"] = [items[best]]
    # what was NOT kept is still in hand for the joining step — the
    # rule says join what was kept and the next thing in hand, and
    # without keeping the next thing there is nothing to join to.
    s["rest"] = [items[i] for i in order[1:]]
    s["line"] = items[best]["essence"]
    return s

def h_check_twice(s):
    s["checked"] = (s.get("first") == s.get("second"))
    return s

HANDS = {
    "walk-places": h_walk_places,
    "walk-each": h_walk_each,
    "test-said": h_test_said,
    "keep-passing": h_keep_passing,
    "test-coheres": h_test_coheres,
    "count-shared": h_count_shared,
    "keep-greatest": h_keep_greatest,
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


def h_join(s):
    """Build a joint between two things in hand and SAY it.

    This is the one act that makes a sentence instead of fetching
    one. Every other act here reaches, judges, keeps or drops, and
    everything the fabric has ever said came out whole from a file.
    A joint is built fresh: it says how two chunks sit with each
    other, and that claim is in no file anywhere.

    The knowledge decides what a joint may be. 174 says a joint needs
    shared ground for both ends to hold, that a joint between a thing
    and itself is not one, and that two things closed by a wall
    cannot both hold and the wall must be named — an unexplained
    contradiction being an assertion rather than a finding.
    """
    import eliminate
    F = core.fabric()
    items = (s.get("items") or []) + (s.get("rest") or [])
    if len(items) < 2:
        s["no_joint"] = "fewer than two things in hand"
        return s
    laws = eliminate.forbidding(F)
    a = items[0]
    best, made = None, None
    for b in items[1:]:
        if b is a or b["id"] == a["id"]:
            continue                      # no joint to itself
        # Ground is counted in uncommon words only. A word the
        # writing uses everywhere is shared by everything and holds
        # nothing — joints were being made on "only" and "while".
        shared = a["color"] & b["color"]
        rare, i, m = 0, 0, shared
        common = len(F.entries) // 50
        while m:
            if m & 1 and F.df.get(i, 0) <= common:
                rare |= 1 << i
            m >>= 1
            i += 1
        shared = rare
        n = bin(shared).count("1")
        if n < 1:
            continue                      # no joint without ground
        pair = a["color"] | b["color"]
        # A wall claiming these two conflict must be ABOUT both of
        # them. Judged on the union alone, any wall touching the
        # pile qualifies, which had a lamination wall declaring a
        # wet finger incompatible with cell death.
        def spans(L):
            """The forbidden thing in one, the company it is
            forbidden in in the other. Both halves inside one of them
            closes that one, and says nothing about the pair."""
            ac, bc = a["color"], b["color"]
            return ((L.a & ac) == L.a and bin(L.b & bc).count("1") >= 2
                    and not (L.a & bc) == L.a) or \
                   ((L.a & bc) == L.a and bin(L.b & ac).count("1") >= 2
                    and not (L.a & ac) == L.a)
        both = [L for L in laws if spans(L)]
        wall = eliminate.closes(pair, pair, F, both)
        if wall is not None:
            # A contradiction is a wall that lets each stand ALONE
            # and stops them standing together. A wall that already
            # closes one of them by itself says nothing about the
            # pair, and calling that a contradiction was declaring
            # exploding stars and the hot hand incompatible.
            alone_a = eliminate.closes(a["color"], a["color"],
                                       F, laws)
            alone_b = eliminate.closes(b["color"], b["color"],
                                       F, laws)
            if alone_a is not None or alone_b is not None:
                wall = None
                continue
        ground = ", ".join(F.words_of(shared)[:4])
        if wall is not None:
            made = (f"these two cannot both hold — "
                    f"\"{a['essence'][:70]}\" and "
                    f"\"{b['essence'][:70]}\" — closed by: "
                    f"{wall.text[:90]}")
        else:
            made = (f"these two stand together on [{ground}] — "
                    f"\"{a['essence'][:80]}\" and "
                    f"\"{b['essence'][:80]}\"")
        best = b
        break
    if made is None:
        s["no_joint"] = ("nothing in hand shares ground with "
                         "anything else in hand")
        return s
    s["joint"] = made
    s.setdefault("joints", []).append(made)
    return s


HANDS["join"] = h_join
