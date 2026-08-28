"""SOFTWARE RULES — emitted by the compute fabric

Written by the compute fabric from its own knowledge.
Every rule below was read out of a knowledge entry's
own words; none was hand-written here. Each check
quotes the law it enforces and names where it came
from, so a person can argue with the law rather than
with the code.
"""
LAWS = [
    {'kind': 'requires', 'needs': ['repair'], 'then': ['cloth', 'compression', 'maximum', 'message', 'patch', 'prepayment', 'spare'], 'law': 'no repair without prepayment — a message at maximum compression has no spare cloth to patch with;', 'source': 'computing information'},
    {'kind': 'requires', 'needs': ['read'], 'then': ['acces', 'cross', 'enemy', 'full', 'hand', 'key', 'lock', 'possession', 'text', 'though', 'view'], 'law': 'no reading without the key, though the locked text crosses enemy hands in full view — possession is not access;', 'source': 'computing information'},
    {'kind': 'requires', 'needs': ['fault', 'halv', 'honest', 'surviv', 'work'], 'then': ['half', 'say', 'test', 'which'], 'law': 'no fault survives honest halving — but no halving works without a test that says WHICH half.', 'source': 'software development'},
    {'kind': 'requires', 'needs': ['bold', 'change'], 'then': ['back', 'caution', 'impossible', 'improvement', 'stop', 'swell', 'undo', 'until', 'where'], 'law': 'no bold change without a way back — where undo is impossible, caution swells until improvement stops.', 'source': 'software development'},
    {'kind': 'requires', 'needs': ['move'], 'then': ['memory', 'only', 'outside', 'past', 'rule', 'stand', 'state', 'surviv', 'where'], 'law': 'no move without a rule, and no memory outside the state — its past survives only as where it stands now, or not at all.', 'source': 'computer science'},
    {'kind': 'requires', 'needs': ['below', 'message', 'squeez', 'surprise'], 'then': ['los'], 'law': 'no squeezing a message below its surprise without loss.', 'source': 'computer science'},
    {'kind': 'requires', 'needs': ['safe', 'shar'], 'then': ['turn'], 'law': 'no safe sharing without turns.', 'source': 'computer science'},
    {'kind': 'forbids', 'needs': ['new'], 'then': ['cost', 'known', 'message', 'receiv', 'send', 'transf', 'whatev', 'written', 'zero'], 'law': 'no news in the known — a message the receiver could have written transfers zero, whatever it cost to send.', 'source': 'computing information'},
    {'kind': 'forbids', 'needs': ['message'], 'then': ['alway', 'lamp', 'noth', 'say', 'signal', 'state'], 'law': 'no message from a one-state signal — the lamp that is always on says nothing.', 'source': 'computing information'},
    {'kind': 'forbids', 'needs': ['fill', 'gap', 'machine'], 'then': ['anyth', 'know', 'left', 'mean', 'single', 'time', 'undone', 'unsaid'], 'law': 'no machine fills a gap with "you know what I mean" — anything left unsaid is left undone, every single time.', 'source': 'software development'},
    {'kind': 'forbids', 'needs': ['clutt', 'harmles'], 'then': ['change', 'cost', 'future', 'noth', 'piece', 'read', 'system', 'tax', 'test', 'today', 'work'], 'law': 'no harmless clutter in a working system — a piece that costs nothing today still taxes every future reading, test, and change.', 'source': 'software development'},
    {'kind': 'forbids', 'needs': ['machine', 'special'], 'then': ['anoth', 'answ', 'computable', 'impossible', 'noth', 'private'], 'law': 'no special machine with private answers — nothing computable on one and impossible on another;', 'source': 'computer science'},
    {'kind': 'forbids', 'needs': ['information'], 'then': ['already', 'carri', 'certainty', 'length', 'message', 'sure', 'zero'], 'law': 'no information from certainty — the already-sure message carries zero at any length;', 'source': 'computer science'},
]

def check(record):
    """record: {"tags": set of words describing what
    this transaction has and is. Returns the laws it
    violates, each with its own words."""
    tags = {t.lower() for t in record.get('tags', [])}
    found = []
    for L in LAWS:
        has = all(n in tags for n in L['needs'])
        if not has: continue
        if L['kind'] == 'requires':
            if not any(t in tags for t in L['then']):
                found.append((L['law'], L['source']))
        else:
            if any(t in tags for t in L['then']):
                found.append((L['law'], L['source']))
    return found

def audit(records):
    """A running audit: every record, every law."""
    report = []
    for r in records:
        v = check(r)
        if v:
            report.append((r.get('id', '?'), v))
    return report

