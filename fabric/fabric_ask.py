"""The asking front door. Checks the white sheet first; walks if not
filed; certifies and FILES silences automatically; re-walks filed
entries when the floors have changed since filing."""
import re, glob, os, sys, hashlib
DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "docs", "fabric_phylums"))
WHITE = os.path.join(DIR, "99_the_white.md")
def stem(w):
    for s in ("ing","ers","er","ed","es","s","ly"):
        if w.endswith(s) and len(w)-len(s)>=3: return w[:len(w)-len(s)]
    return w
def words(s):
    STOP=set("the a an is are of in on at to for with by from and or not no it its this that what why how when does do same other own there they if then than as but so out up down off over more most less very much many few all any some none each every no one two three way ways get got can could would should will shall may might must have has had been was were being you your our his her him she he them their are its into onto upon about just also even still yet too now here also make made makes".split())
    return set(stem(w) for w in re.findall(r"[a-z]+",s.lower())
               if w not in STOP and len(w)>2)
def fingerprint():
    h=hashlib.sha256()
    for f in sorted(glob.glob(os.path.join(DIR,"[0-9][0-9]_*.md"))):
        if f.endswith("99_the_white.md"): continue
        h.update(open(f,"rb").read())
    h.update(open(__file__,"rb").read())   # the walker signs too
    here=os.path.dirname(os.path.abspath(__file__))
    for extra in ("fabric_do.py","lawbook.md",
                  "follower.py"):                 # doing signs too
        p=os.path.join(here,extra)
        if os.path.exists(p): h.update(open(p,"rb").read())
    return h.hexdigest()[:12]
def load():
    es=[]
    for f in sorted(glob.glob(os.path.join(DIR,"[0-9][0-9]_*.md"))):
        if f.endswith("99_the_white.md"): continue
        name=re.sub(r"^\d+_|\.md$","",os.path.basename(f)).replace("_"," ")
        for b in re.split(r"\n(?=ESSENCE:)",open(f).read()):
            if not b.startswith("ESSENCE:"): continue
            # a faded entry has undulated back into the white as an
            # unknown — it is no longer held on the colored sheet
            if "STATE: FADED" in b: continue
            def part(t):
                m=re.search(rf"{t}:(.*?)(?=\n[A-Z-]+:|\Z)",b,re.S)
                return re.sub(r"\s+"," ",m.group(1)).strip() if m else ""
            es.append(dict(field=name,essence=part("ESSENCE"),
                           cannot=part("CANNOT"),
                           ask=part("ASKED-AS"),
                           rule=part("RULE"),
                           thread=part("THREAD"),
                           root=part("ROOT")))
    return es
def walk(qs, es):
    def wt(e): return words(e["essence"]+" "+e["cannot"]+" "+e["ask"])
    # rarity: a question's DISTINCTIVE words are those few entries hold
    df={}
    for e in es:
        for w in wt(e): df[w]=df.get(w,0)+1
    rare={w for w in qs if 0<df.get(w,0)<=8}
    missing={w for w in qs if df.get(w,0)==0}
    rel=sorted(es,key=lambda e:-len(qs&wt(e)))
    need=min(2,len(qs))
    rel=[e for e in rel[:12] if len(qs&wt(e))>=need]
    # a single floor holding EVERY known question word answers alone —
    # depth floors carry whole answers; the door must let them speak
    known=qs-missing
    direct=[e for e in rel
            if known and known<=wt(e) and len(qs&wt(e))>=2]
    # meaning check: floors that hold all the asking's words but
    # share NO company beyond those words are letter-coincidence —
    # the same word living in different houses. Company is judged
    # on a floor's own body (essence+cannot), never its ask-words.
    def body(e): return words(e["essence"]+" "+e["cannot"])
    houses=[]
    for e in direct:
        for h in houses:
            if any(len((body(e)&body(o))-qs)>=1 for o in h):
                h.append(e); break
        else:
            houses.append([e])
    houses.sort(key=len,reverse=True)
    pairs=[]
    for i,B in enumerate(rel):
        for A in rel[i+1:]:
            h=wt(B)&wt(A)
            if len(h)>=2:
                pairs.append((len(h)+len(qs&(wt(A)|wt(B))),B,A,h))
    pairs.sort(key=lambda p:-p[0])
    # a join answers only if the two floors AGREE ABOUT the question's
    # own subject: a rare question word must sit in the hinge itself,
    # not merely somewhere in either floor
    good=[p for p in pairs if p[0]>=min(6,3+len(qs)) and
          len(rare & p[3])>=1]
    return rel,direct,houses,good,rare,missing
def sig(qs): return " ".join(sorted(qs))
def _mark_answered(s):
    t=open(WHITE).read()
    t2=re.sub(rf"(ASKED-SIG: {re.escape(s)}\n  FLOORS: \w+"
              rf"(?:[^\n]|\n(?!\n))*?STATUS: )STANDING[^\n]*",
              r"\1ANSWERED — knowledge that answers it was added "
              r"later", t)
    if t2!=t: open(WHITE,"w").write(t2)
MAKE_WORDS=re.compile(r"^\s*(make|build|design|create|invent|"
                      r"give me a way|a way to|how (do|can) (i|we)|"
                      r"how to)\b",re.I)
def ask(question):
    # a want to MAKE something goes to the maker: the knowledge
    # stages possibilities and its own laws kill what they forbid
    if MAKE_WORDS.match(question):
        sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
        import maker
        print(maker.make(question)); return
    qs=words(question)
    digits=re.findall(r"\d+",question)
    if digits:
        sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
        import follower
        arr=follower.try_numbers(question)
        if arr:
            print(arr); return
        print(f"(I can see numbers here — {', '.join(digits[:4])} — "
              f"but no entry in my knowledge tells me how to do "
              f"what this asking wants. Anything below is what my "
              f"floors KNOW.)")
    if not qs:
        print("After setting aside small words and numbers, "
              "nothing remains of this question that I can match. "
              "This is a limit of how I read questions, not a fact "
              "about the answer. Nothing is recorded.")
        return
    s=sig(qs); fp=fingerprint()
    wtxt=open(WHITE).read() if os.path.exists(WHITE) else ""
    m=re.search(rf"ASKED-SIG: {re.escape(s)}\n  FLOORS: (\w+)"
                rf"[\s\S]*?STATUS: (\w+)",wtxt)
    if m and m.group(2) in ("DRAINED","ANSWERED"):
        m=None   # a settled entry is history, not a silence
    if m:
        if m.group(1)==fp:
            print("I have no knowledge that reaches this question. "
                  "It is recorded as an open question — when "
                  "knowledge that answers it is added, it will "
                  "answer.")
            return
        # knowledge changed since it was recorded — re-check quietly
    es=load(); rel,direct,houses,good,rare,missing=walk(qs,es)
    if missing:
        print(f"(words I hold no knowledge of: "
              f"{', '.join(sorted(missing)[:6])})")
    if len(houses)>1:
        def body(e): return words(e["essence"]+" "+e["cannot"])
        print(f"Your words match knowledge about "
              f"{len(houses)} different things, and I cannot tell "
              f"which you mean. Ask again with a word from the one "
              f"you meant:")
        for h in houses:
            com=sorted((body(h[0])-qs))[:5]
            print(f"  ({h[0]['field']}) {h[0]['essence']}")
            print(f"      (its other words: {' '.join(com)})")
        return
    # sideways answers: joins from relevant floors that the strict
    # bar refused — shown, never suppressed; the reader judges
    def wt(e): return words(e["essence"]+" "+e["cannot"]+" "+e["ask"])
    side=[]
    for i,B in enumerate(rel):
        for A in rel[i+1:]:
            if len(wt(B)&wt(A))>=2: side.append((B,A))
    if direct or good:
        print("Answer — from my knowledge:")
        shown=[]
        for e in direct[:3]:
            print(f"  ({e['field']}) {e['essence']}")
            shown.append(id(e))
        for sc,B,A,h in good[:1]:
            for e in (B,A):
                if id(e) not in shown:
                    print(f"  ({e['field']}) {e['essence']}")
                    shown.append(id(e))
        if m:
            _mark_answered(s)
            print("This stood as an open question until now — the "
                  "knowledge that answers it arrived, and the "
                  "record is updated.")
        return
    if side:
        print("Nothing I hold answers this directly. The nearest "
              "knowledge, in case it helps:")
        seen=set()
        for B,A in side[:2]:
            for e in (B,A):
                if id(e) in seen: continue
                seen.add(id(e))
                print(f"  ({e['field']}) {e['essence']}")
        return
    print("I have no certified answer — this is recorded as an "
          "open question. But a question asks what is possible, "
          "so here is me looking across everything I know and "
          "playing with the unknown:")
    import assembler
    df={}
    for e in es:
        for x in words(e["essence"]+" "+e["cannot"]+" "+e["ask"]):
            df[x]=df.get(x,0)+1
    lanes=assembler.play(question,es,df)
    if not lanes:
        print("  Nothing in my knowledge even touches this — the "
              "missing knowledge is the whole answer.")
    for n,(known,failed,toys) in enumerate(lanes,1):
        if len(lanes)>1:
            print(f"  Territory {n} your words touch:")
        for e in known:
            print(f"    known: ({e['field']}) {e['essence']}")
        for e in failed:
            print(f"    known to fail: {e['cannot']}")
        for s,a,b in toys:
            print(f"    unproven play: maybe "
                  f"{a['essence'].split(chr(8212))[0].strip()} "
                  f"TOGETHER WITH "
                  f"{b['essence'].split(chr(8212))[0].strip()}")
    if not m:
        with open(WHITE,"a") as f:
            f.write(f"\nENTRY: {question.strip()}\n"
                    f"  ASKED-SIG: {s}\n  FLOORS: {fp}\n"
                    f"  VERDICT: no path — certified by deterministic"
                    f" walk. Auto-filed.\n  STATUS: STANDING (white)\n")
if __name__=="__main__":
    ask(" ".join(sys.argv[1:]))
