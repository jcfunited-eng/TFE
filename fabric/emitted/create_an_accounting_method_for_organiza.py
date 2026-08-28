"""RULES FOR: create an accounting method for organizational finances that utilized risked bases accounting rules with LLM support for analysis, account creation, account management, and reconciliation with real time running audit reports and views - which means could it reach out to the internet for the data the

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
    {'kind': 'requires', 'needs': ['see'], 'then': ['interpret'], 'law': 'no seeing without interpreting.', 'source': 'the mind'},
    {'kind': 'requires', 'needs': ['choos'], 'then': ['cannot', 'cas', 'circuit', 'damag', 'feel', 'injury', 'lunch', 'mind', 'pick', 'rest', 'unsure', 'verdict'], 'law': 'And no choosing without feeling: minds with the verdict-circuits damaged cannot pick a lunch (UNSURE — rests on few injury cases).', 'source': 'the mind'},
    {'kind': 'requires', 'needs': ['around', 'corn', 'see'], 'then': ['bend', 'bounce'], 'law': 'no seeing around a corner without a bend or a bounce.', 'source': 'light seeing'},
    {'kind': 'requires', 'needs': ['focus', 'len'], 'then': ['len', 'light', 'slow', 'somewhere'], 'law': 'No lens that focuses without slowing light somewhere — the slowing IS the lens.', 'source': 'light seeing'},
    {'kind': 'requires', 'needs': ['shadow'], 'then': ['deni', 'path', 'straight'], 'law': 'no shadow without a denied straight path;', 'source': 'light seeing'},
    {'kind': 'requires', 'needs': ['read'], 'then': ['know', 'light', 'stood', 'where'], 'law': 'no reading one without knowing where the light stood.', 'source': 'light seeing'},
    {'kind': 'requires', 'needs': ['blue', 'sky'], 'then': ['air', 'black', 'daytime', 'moon', 'sky'], 'law': "No blue sky without air — the moon's daytime sky is black.", 'source': 'light seeing'},
    {'kind': 'requires', 'needs': ['distance'], 'then': ['betray', 'dimm', 'dimnes', 'far', 'hid', 'range'], 'law': 'No distance without dimming — and no hiding range: dimness betrays how far.', 'source': 'light seeing'},
    {'kind': 'requires', 'needs': ['move'], 'then': ['memory', 'only', 'outside', 'past', 'rule', 'stand', 'state', 'surviv', 'where'], 'law': 'no move without a rule, and no memory outside the state — its past survives only as where it stands now, or not at all.', 'source': 'computer science'},
    {'kind': 'requires', 'needs': ['below', 'message', 'squeez', 'surprise'], 'then': ['los'], 'law': 'no squeezing a message below its surprise without loss.', 'source': 'computer science'},
    {'kind': 'requires', 'needs': ['safe', 'shar'], 'then': ['turn'], 'law': 'no safe sharing without turns.', 'source': 'computer science'},
    {'kind': 'requires', 'needs': ['entry'], 'then': ['entry', 'equal', 'opposite'], 'law': 'no entry without an equal and opposite entry.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['period', 'revenue'], 'then': ['performance', 'period'], 'law': 'no revenue in a period without performance in that period.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['expense', 'period'], 'then': ['benefit', 'consum', 'period'], 'law': 'No expense in a period without the benefit consumed in that period.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['revenue'], 'then': ['obligation', 'satisfi'], 'law': 'no revenue without a satisfied obligation.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['control'], 'then': ['separation'], 'law': 'no control without separation.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['audit'], 'then': ['trail'], 'law': 'no audit without a trail.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['adjustment'], 'then': ['author', 'reason', 'stat'], 'law': 'No adjustment without a stated reason and an author.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['reconciliation'], 'then': ['independent', 'second', 'source'], 'law': 'no reconciliation without an independent second source.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['bas', 'judgment', 'risk'], 'then': ['both', 'likelihood', 'size'], 'law': 'no risk-based judgment without both size and likelihood.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['estimate'], 'then': ['basi', 'stat'], 'law': 'no estimate without a stated basis.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['collect', 'sal', 'tax'], 'then': ['fil', 'remit'], 'law': 'No sales tax collected without a filing that remits it.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['fil', 'time'], 'then': ['book', 'clos', 'first', 'underly'], 'law': 'no timely filing without the underlying books closed first.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['integration'], 'then': ['declar', 'direction', 'flow'], 'law': 'No integration without a declared direction of flow.', 'source': 'accounting control'},
    {'kind': 'requires', 'needs': ['accountable', 'action'], 'then': ['actor', 'identifi'], 'law': 'no accountable action without an identified actor.', 'source': 'accounting control'},
    {'kind': 'forbids', 'needs': ['new'], 'then': ['cost', 'known', 'message', 'receiv', 'send', 'transf', 'whatev', 'written', 'zero'], 'law': 'no news in the known — a message the receiver could have written transfers zero, whatever it cost to send.', 'source': 'computing information'},
    {'kind': 'forbids', 'needs': ['message'], 'then': ['alway', 'lamp', 'noth', 'say', 'signal', 'state'], 'law': 'no message from a one-state signal — the lamp that is always on says nothing.', 'source': 'computing information'},
    {'kind': 'forbids', 'needs': ['cue', 'decision', 'delet', 'habit', 'only', 'overwrit'], 'then': ['rival', 'routine'], 'law': 'no deleting a habit by decision — only overwriting it, cue by cue, with a rival routine.', 'source': 'the mind'},
    {'kind': 'forbids', 'needs': ['bia', 'see'], 'then': ['feel', 'inside', 'like', 'objectivity'], 'law': 'no seeing your own bias from inside — it feels like objectivity.', 'source': 'the mind'},
    {'kind': 'forbids', 'needs': ['felt', 'happines', 'lift', 'permanent'], 'then': ['becom', 'gain', 'level', 'new', 'time', 'zero'], 'law': 'no permanent lift of felt happiness from a one-time gain — the new level becomes the new zero.', 'source': 'the mind'},
    {'kind': 'forbids', 'needs': ['atom', 'see'], 'then': ['glassmak', 'light', 'limit', 'wave'], 'law': 'no seeing atoms with light — the limit is the wave, not the glassmaker.', 'source': 'light seeing'},
    {'kind': 'forbids', 'needs': ['machine', 'special'], 'then': ['anoth', 'answ', 'computable', 'impossible', 'noth', 'private'], 'law': 'no special machine with private answers — nothing computable on one and impossible on another;', 'source': 'computer science'},
    {'kind': 'forbids', 'needs': ['information'], 'then': ['already', 'carri', 'certainty', 'length', 'message', 'sure', 'zero'], 'law': 'no information from certainty — the already-sure message carries zero at any length;', 'source': 'computer science'},
    {'kind': 'forbids', 'needs': ['balanc', 'ledg'], 'then': ['post', 'sid', 'single'], 'law': 'No balanced ledger in single-sided posting.', 'source': 'accounting control'},
    {'kind': 'forbids', 'needs': ['revenue'], 'then': ['arrangement', 'unsign'], 'law': 'No revenue in an unsigned arrangement.', 'source': 'accounting control'},
    {'kind': 'forbids', 'needs': ['payment', 'safe'], 'then': ['hand', 'pair'], 'law': 'No safe payment in one pair of hands.', 'source': 'accounting control'},
    {'kind': 'forbids', 'needs': ['balance', 'cash', 'trust'], 'then': ['account', 'unreconcil'], 'law': 'No trusted cash balance in an unreconciled account.', 'source': 'accounting control'},
    {'kind': 'forbids', 'needs': ['assurance'], 'then': ['exposure', 'ignor', 'sampl', 'where'], 'law': 'No assurance from sampling that ignores where the exposure is.', 'source': 'accounting control'},
    {'kind': 'forbids', 'needs': ['single', 'truth'], 'then': ['mast'], 'law': 'no single truth in two masters.', 'source': 'accounting control'},
    {'kind': 'forbids', 'needs': ['identity'], 'then': ['copi', 'reus', 'secret'], 'law': 'No identity from a secret that can be copied and reused.', 'source': 'accounting control'},
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

