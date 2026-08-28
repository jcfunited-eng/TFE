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
    STOP=set("the a an is are of in on at to for with by from and or not no it its this that what why how when does do same other own there they if then than as but so out up down off over more most less very much many few all any some none each every no one two three".split())
    return set(stem(w) for w in re.findall(r"[a-z]+",s.lower())
               if w not in STOP and len(w)>3)
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
            def part(t):
                m=re.search(rf"{t}:(.*?)(?=\n[A-Z-]+:|\Z)",b,re.S)
                return re.sub(r"\s+"," ",m.group(1)).strip() if m else ""
            es.append(dict(field=name,essence=part("ESSENCE"),
                           cannot=part("CANNOT"),
                           ask=part("ASKED-AS"),
                           rule=part("RULE")))
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
def ask(question):
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
        print("TRANSLATOR'S SILENCE — after dropping small words "
              "and numbers, nothing of this asking remains that my "
              "floors could hear. This is my translator's limit, "
              "not a certified impossibility; nothing is filed.")
        return
    s=sig(qs); fp=fingerprint()
    wtxt=open(WHITE).read() if os.path.exists(WHITE) else ""
    m=re.search(rf"ASKED-SIG: {re.escape(s)}\n  FLOORS: (\w+)"
                rf"[\s\S]*?STATUS: (\w+)",wtxt)
    if m and m.group(2)=="DRAINED":
        m=None   # a drained entry is history, not a silence
    if m:
        if m.group(1)==fp:
            print("FROM THE WHITE: no floor of mine reaches this "
                  "asking — walked, certified, and my floors have "
                  "not changed since. It stands as a purchase order "
                  "for a floor not yet bought. Not-held is not "
                  "impossible.")
            return
        print("(filed in the white, but my floors HAVE changed — "
              "re-walking…)")
    es=load(); rel,direct,houses,good,rare,missing=walk(qs,es)
    if missing:
        print(f"(words my floors have never heard: "
              f"{', '.join(sorted(missing)[:6])})")
    if len(houses)>1:
        def body(e): return words(e["essence"]+" "+e["cannot"])
        print(f"SPLIT — your words live in {len(houses)} different "
              f"houses of my knowledge, and I cannot tell which you "
              f"mean. Say it with one house's company:")
        for h in houses:
            com=sorted((body(h[0])-qs))[:5]
            print(f"  [{h[0]['field']}] {h[0]['essence'][:80]}")
            print(f"      (this house's company: {' '.join(com)})")
        return
    # sideways answers: joins from relevant floors that the strict
    # bar refused — shown, never suppressed; the reader judges
    def wt(e): return words(e["essence"]+" "+e["cannot"]+" "+e["ask"])
    side=[]
    for i,B in enumerate(rel):
        for A in rel[i+1:]:
            if len(wt(B)&wt(A))>=2: side.append((B,A))
    if direct or good:
        if direct:
            print(f"ANSWER — {len(direct)} floor(s) hold this "
                  f"directly:")
            for e in direct[:3]:
                print(f"  [{e['field']}] {e['essence'][:100]}")
        if good:
            print(f"ANSWER — {len(good)} strong joins from "
                  f"{len(rel)} floors:")
            for sc,B,A,h in good[:3]:
                print(f"  [{B['field']}] {B['essence'][:80]}")
                print(f"  x [{A['field']}] {A['essence'][:80]}")
        if m: print("(this asking has DRAINED from the white — "
                    "update its entry to DRAINED)")
        return
    if side:
        print("SIDEWAYS ANSWER — nothing meets your question head-on,"
              " but these joins touch it at an angle. You judge:")
        for B,A in side[:3]:
            print(f"  [{B['field']}] {B['essence'][:80]}")
            print(f"  x [{A['field']}] {A['essence'][:80]}")
        return
    print("TRUE SILENCE — no floor of mine reaches this asking. "
          "Filing it to the white as a purchase order for a floor "
          "not yet bought (two signatures required to stand). "
          "Not-held is not impossible.")
    if not m:
        with open(WHITE,"a") as f:
            f.write(f"\nENTRY: {question.strip()}\n"
                    f"  ASKED-SIG: {s}\n  FLOORS: {fp}\n"
                    f"  VERDICT: no path — certified by deterministic"
                    f" walk. Auto-filed.\n  STATUS: STANDING (white)\n")
if __name__=="__main__":
    ask(" ".join(sys.argv[1:]))
