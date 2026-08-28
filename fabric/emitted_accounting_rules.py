"""ACCOUNTING RULES — emitted by the compute fabric

Written by the compute fabric from its own knowledge.
Every rule below was read out of a knowledge entry's
own words; none was hand-written here. Each check
quotes the law it enforces and names where it came
from, so a person can argue with the law rather than
with the code.
"""
LAWS = [
    {'kind': 'requires', 'needs': ['deal'], 'then': ['agre', 'agree', 'different', 'meet', 'mind', 'noth', 'people', 'thing'], 'law': 'No deal without a meeting of minds: two people agreeing to different things have agreed to nothing.', 'source': 'law agreements'},
    {'kind': 'requires', 'needs': ['measurement'], 'then': ['noth', 'numb', 'say', 'standard', 'unit'], 'law': 'no measurement without a standard — a number with no unit says nothing.', 'source': 'evidence measurement'},
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
    {'kind': 'forbids', 'needs': ['law', 'rule'], 'then': ['alone', 'bend', 'memory', 'remember', 'rul', 'strongest', 'toward', 'unwritten'], 'law': 'no rule of law from memory alone — unwritten rules bend toward the strongest rememberer.', 'source': 'law agreements'},
    {'kind': 'forbids', 'needs': ['medicine', 'tell'], 'then': ['com', 'recovery', 'regardles'], 'law': 'Without the untouched twin, no telling the medicine from the recovery that was coming regardless.', 'source': 'evidence measurement'},
    {'kind': 'forbids', 'needs': ['learn'], 'then': ['break', 'claim', 'compatible', 'fail', 'fortune', 'knowledge', 'live', 'outcome', 'result', 'sentenc', 'tell', 'test'], 'law': 'no learning from a test that could not fail, and no knowledge in a claim compatible with every outcome — fortune-tellers live on sentences no result can break.', 'source': 'evidence measurement'},
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

