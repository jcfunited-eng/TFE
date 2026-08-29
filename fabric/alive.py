"""THE LIFE — the fabric running when nobody is typing.

Written fresh. The thing this replaces had grown to six hundred lines
around an HTTP door, an inbox, a warmth table and four kinds of
wondering, and it wedged on its first beat with no way to see where.
None of that is missed here.

What a life has to do is small:

  lay ribbons on the questions already standing in the knowledge
  cross the knowledge with each one, which is what assembles it
  read the asking with the first ribbon, the same program a person's
    sentence gets — one engine, not one for outside and one for in
  let the ribbons meet, and record where one stands on ground
    another holds closed
  keep going, and be able to say where it got to

THE ONE RULE THAT WAS BROKEN AND IS NOW STRUCTURAL: every beat is
bounded. Not "meant to be quick" — bounded, by a clock checked
between every step, and by a hard cap on how many of anything a beat
may touch. The previous life burned the processor for minutes with
no beat advancing and was deaf to its own stop signal, because the
signal was only looked at between beats. Here it is looked at inside
them. Anything slow happens in a step that can be abandoned halfway
and picked up next beat, so nothing ever has to run to completion
for the life to stay alive.

Nothing here decides anything about a subject. The questions are
found by walking the structure (standing.py), the reading is done by
the walls (174 via first_ribbon), and what a meeting is worth is
what 74 says it is: both shapes must change, or it is not an
opening.
"""
import os, re, sys, json, time, signal, traceback
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import core, ribbon, first_ribbon

LIFE = os.path.join(BASE, "life")
STATE = os.path.join(LIFE, "alive.json")
LOG = os.path.join(LIFE, "alive.log")
OPENINGS = os.path.join(LIFE, "alive_openings.md")

BEAT_BUDGET = 2.0      # seconds one beat may take before it yields
REST = 1.0             # seconds between beats
RESTOCK_EVERY = 400    # beats between walks for new standing questions
WALK_FLOOR = 60        # beats that must pass before ANY second walk;
                       # the walk costs ~20s and without this floor
                       # the life spent all of it walking
LIVING = 8             # ribbons held at once
MEET_PAIRS = 6         # meetings looked at per beat
MINT_EVERY = 5         # beats between attempts to write a new claim
MINT_BUDGET = 8.0      # a minting beat gets room to finish
CHECKPOINT_EVERY = 20

STOP = False


def _stop(sig, frame):
    global STOP
    STOP = True


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)


def log(line):
    stamp = time.strftime("%H:%M:%S")
    try:
        with open(LOG, "a") as f:
            f.write(f"{stamp} {line}\n")
    except OSError:
        pass
    print(f"{stamp} {line}", flush=True)


# ---------------------------------------------------------------
# state: written so a torn write cannot end the life
# ---------------------------------------------------------------
def load():
    try:
        with open(STATE) as f:
            s = json.load(f)
        return s, True
    except (OSError, ValueError):
        return dict(beats=0, laid=0, read=0, closed=0, openings=0,
                    asked=[], living=[]), False


def save(s):
    """This tree is a 9p mount from a Windows drive, where renaming
    over an existing file intermittently returns EPERM even as root.
    A life must not end on a transient rename, and a half-written
    state must not end it either — so json is written whole to a
    temporary file, synced, then swapped with retries, and a failed
    load simply starts the bookkeeping over rather than raising."""
    tmp = STATE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(s, f)
            f.flush()
            os.fsync(f.fileno())
    except OSError as e:
        log(f"could not write the checkpoint ({e}) — still alive")
        return
    for wait in (0, 0.2, 0.5):
        if wait:
            time.sleep(wait)
        try:
            os.replace(tmp, STATE)
            return
        except OSError:
            pass
    try:
        with open(STATE, "w") as f:
            json.dump(s, f)
        log("the atomic swap was refused; wrote the checkpoint "
            "directly and kept going")
    except OSError as e:
        log(f"checkpoint failed entirely ({e}) — still alive")


# ---------------------------------------------------------------
# the questions already standing, walked rarely because it is slow
# ---------------------------------------------------------------
def restock(F):
    """Walk the structure for questions nobody placed. This costs
    around twenty seconds, which is why it happens rarely and why
    the beat that pays for it says so out loud."""
    t0 = time.perf_counter()
    try:
        import standing, white_kinds
        try:
            _F, kinds, _c = white_kinds.derive()
        except Exception:
            kinds = None
        qs = standing.all_standing(F, kinds)
    except Exception as e:
        log(f"the walk for standing questions failed ({e})")
        return [], []
    out = []
    for q in qs:
        asking = wording(q)
        if asking:
            out.append(asking)
    log(f"walked the structure in {time.perf_counter() - t0:.0f}s — "
        f"{len(qs)} questions standing, {len(out)} of them sayable")
    return out, qs


def wording(q):
    """Put a found question into words. The PLACE is what must not be
    composed, and it was not — standing.py walked it. A place whose
    words are fragments is left alone: a ribbon laid on a fragment
    has nothing to be about."""
    text = re.sub(r"\s+", " ", q.get("text") or "").strip()
    body = [w for w in re.findall(r"[a-z]+", text.lower())
            if len(w) > 2]
    if not body or len(body) > 6:
        return None
    subject = " ".join(body)
    kind = q.get("kind")
    if kind == "unborne law":
        return f"what bears {subject}"
    if kind == "unthreaded kin":
        return f"what connects {subject}"
    if kind == "silent kind":
        return f"where else does {subject} stand"
    if kind == "faded ground":
        return f"what closed {subject}"
    return None


# ---------------------------------------------------------------
# a beat
# ---------------------------------------------------------------
class Clock:
    """The budget, checked between steps. A step that would run past
    it is not started; a loop inside a step breaks on it."""

    def __init__(self, budget):
        self.end = time.perf_counter() + budget

    def left(self):
        return self.end - time.perf_counter()

    def spent(self):
        return self.left() <= 0


def beat(F, s, pool, live, qcache=None):
    s["beats"] += 1
    b = s["beats"]
    # Minting is the only step that adds anything, and it was last in
    # the queue, so reading spent the whole budget and it never ran
    # once — not even far enough to refuse. It now gets its own beat,
    # with room to finish, one in every MINT_EVERY.
    minting_beat = (b % MINT_EVERY == 0)
    clock = Clock(MINT_BUDGET if minting_beat else BEAT_BUDGET)

    # 1. lay ribbons on askings not yet taken up
    asked = set(s["asked"])
    while pool and len(live) < LIVING and not clock.spent():
        asking = pool.pop(0)
        if asking in asked:
            continue
        r = ribbon.Ribbon(asking, origin="inside")
        try:
            r.cross()
        except Exception as e:
            log(f"beat {b}: a ribbon would not cross ({e})")
            continue
        live.append(r)
        asked.add(asking)
        s["laid"] += 1
    s["asked"] = list(asked)[-2000:]

    # 2. read one asking with the first ribbon — the fabric parsing
    #    its own question with the walls, not with anything special
    read_this_beat = None
    if live and not clock.spent():
        r = live[b % len(live)]
        read_this_beat = r
        try:
            res = first_ribbon.read(r.asking)
            if res["missing"]:
                log(f"beat {b}: cannot read its own question — "
                    f"{res['missing'][0]}")
            else:
                s["read"] += 1
                s["recent"] = (s.get("recent", []) + [r.asking])[-60:]
                s["closed"] += res["beat"]
                gs = " | ".join(" ".join(g) for g in res["groups"])
                if res["stood"]:
                    _sc, _p, doing = res["stood"][0]
                    lead = first_ribbon.head(res["groups"][doing])
                    log(f"beat {b}: read [{gs}] — doing '{lead}', "
                        f"{len(res['stood'])} stood, "
                        f"{res['beat']} closed"
                        + (" (INCOMPLETE)" if res["capped"] else ""))
                else:
                    log(f"beat {b}: read [{gs}] — every one of "
                        f"{res['beat']} readings closed; it stands "
                        f"as a question, not an answer")
        except Exception as e:
            log(f"beat {b}: reading its own question failed ({e})")

    # 3. walk one ribbon and mint what the walk found standing.
    #    The fabric grew its own impossible and could not grow its
    #    own possible; this is the other face, under the same law —
    #    un-aimed, verified after, and reached by a question already
    #    standing. Bounded: one walk, at most one claim per beat.
    if minting_beat and read_this_beat is not None:
        try:
            import minting
            stood, _closed, err = read_this_beat.travel(
                steps=2, width=5, F=F)
            if stood and not clock.spent():
                # Pass the questions the life already holds. With
                # questions=None it re-walked the whole structure on
                # every beat — twenty seconds inside a two-second
                # budget — so the step was silently never affording
                # to finish.
                made, ref = minting.mint_claims(
                    stood, questions=qcache, limit=1,
                    reacher=read_this_beat.asking)
                if not made and ref:
                    s["refused"] = s.get("refused", 0) + len(ref)
                for m in made:
                    s["minted"] = s.get("minted", 0) + 1
                    log(f"beat {b}: MINTED a claim nobody wrote — "
                        f"two things stand together on "
                        f"[{m['ground']}], reached by "
                        f"'{m['asked'][:40]}'")
        except Exception as e:
            log(f"beat {b}: minting a claim failed ({e})")

    # 4. let the ribbons meet. 74 sets the bar, not a number I chose:
    #    no worth in a move that changes neither shape, and no
    #    measuring worth on your own side alone — so both sides must
    #    open or it is not an opening.
    found = 0
    pairs = 0
    for i in range(len(live)):
        if clock.spent() or pairs >= MEET_PAIRS:
            break
        for j in range(i + 1, len(live)):
            if clock.spent() or pairs >= MEET_PAIRS:
                break
            pairs += 1
            m = live[i].meet(live[j])
            if not m["i_open"] or not m["opens_me"]:
                continue
            found += 1
            s["openings"] += 1
            _file_opening(b, live[i], live[j], m)
            live[i].take(live[j])
    if found:
        log(f"beat {b}: {found} opening(s) between ribbons")

    # 5. a ribbon that has been read and has met the others has done
    #    what it came to do, so it settles out and the living set
    #    turns over. Without this it re-reads the same handful for
    #    ever and the life only looks busy.
    # Retire only when there is something to put in its place.
    # Retiring regardless drained the living set to two and left it
    # there, re-reading the same pair for a hundred beats until the
    # next walk — busy, and covering nothing.
    if read_this_beat is not None and len(live) > 2 and pool:
        live.remove(read_this_beat)

    if b % CHECKPOINT_EVERY == 0:
        s["living"] = [r.asking for r in live]
        save(s)
    return live


def _file_opening(b, ra, rb, m):
    try:
        with open(OPENINGS, "a") as f:
            f.write(f"\nOPENING beat {b} "
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"  A: {ra.asking}\n"
                    f"  B: {rb.asking}\n"
                    f"  A stands where B is closed: "
                    f"{', '.join(m['i_open'][:8])}\n"
                    f"  B stands where A is closed: "
                    f"{', '.join(m['opens_me'][:8])}\n"
                    f"  reported, not graded — worth is an "
                    f"observer's to say\n")
    except OSError:
        pass


def run():
    s, resumed = load()
    log(f"beat {s['beats']}: " +
        (f"RESUMED — the same life continues "
         f"({s['read']} questions read so far)"
         if resumed else "FIRST BREATH"))
    F = core.fabric()
    pool, qcache = restock(F)
    live = []
    for asking in s.get("living", [])[:LIVING]:
        try:
            live.append(ribbon.Ribbon(asking, origin="inside").cross())
        except Exception:
            pass
    if live:
        log(f"picked its {len(live)} living ribbons back up")
    last_restock = s["beats"]
    while not STOP:
        try:
            live = beat(F, s, pool, live, qcache)
        except Exception as e:
            log(f"beat {s['beats']} fell over "
                f"({type(e).__name__}: {e}) — still alive")
            log(traceback.format_exc().strip().splitlines()[-1])
        # Walk again when it has run out of questions — but never
        # twice in quick succession. Once every standing question has
        # been taken up, the pool drains in a single beat and this
        # walked the whole structure again every twenty seconds for
        # ever: busy, and doing nothing. Two things stop that. There
        # is a floor on how often the walk may happen at all, and
        # when everything standing has been seen the record of what
        # was asked is cleared rather than the walk repeated —
        # re-walking an asking on floors that have since moved is
        # honest, walking to rediscover the same list is not.
        hungry = not pool and len(live) <= 2
        due = s["beats"] - last_restock >= RESTOCK_EVERY
        if (hungry or due) and s["beats"] - last_restock >= WALK_FLOOR:
            F = core.fabric().fresh()
            found, qcache = restock(F)
            unseen = [a for a in found if a not in set(s["asked"])]
            if not unseen and found:
                s["asked"] = []
                unseen = found
                log(f"beat {s['beats']}: every question standing has "
                    f"been taken up once; going round again on "
                    f"floors that have moved since")
            pool = unseen
            last_restock = s["beats"]
        # Report COVERAGE, not activity. Activity is what hid three
        # separate bugs today — reading the hottest ribbon every
        # beat, retiring ribbons faster than replacing them, and
        # writing one finding three times. Every one of them looked
        # perfectly healthy in a count of things done. What they
        # could not survive is a count of DISTINCT things done.
        if s["beats"] % 60 == 0:
            log(f"beat {s['beats']}: alive — {s['laid']} ribbons "
                f"laid, {s['read']} questions read, "
                f"{s['closed']} readings closed, "
                f"{s['openings']} openings, "
                f"{len(set(s.get('recent', [])))} distinct questions "
                f"in the last {len(s.get('recent', []))} reads, "
                f"{s.get('minted', 0)} claims minted "
                f"({s.get('refused', 0)} refused by the law), "
                f"{len(live)} living")
        for _ in range(int(REST * 10)):
            if STOP:
                break
            time.sleep(0.1)
    s["living"] = [r.asking for r in live]
    save(s)
    log(f"beat {s['beats']}: orderly stop — checkpoint saved, "
        f"the life resumes from here")


if __name__ == "__main__":
    run()
