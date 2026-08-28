"""RULES FOR: create an accounting system with audit trail and reconciliation

Written by the compute fabric from its own knowledge.
Every rule below was read out of a knowledge entry's
own words; none was hand-written here. Each check
quotes the law it enforces and names where it came
from, so a person can argue with the law rather than
with the code.
"""
LAWS = [
    {'kind': 'requires', 'needs': ['alone', 'coercion', 'cost', 'extract', 'force', 'guard', 'long', 'need', 'rul'], 'then': ['end'], 'law': 'no ruling by force alone for long — coercion costs more than it extracts, and the guards need guarding, without end.', 'source': 'power governance'},
    {'kind': 'requires', 'needs': ['state'], 'then': ['revenue'], 'law': 'no state without revenue.', 'source': 'power governance'},
    {'kind': 'requires', 'needs': ['sentence'], 'then': ['assert', 'false', 'heap', 'list', 'nam', 'noth', 'true', 'verb', 'world'], 'law': 'no sentence without a verb — a heap of names lists the world and asserts nothing, so nothing in it can be true or false.', 'source': 'grammar and sentences'},
    {'kind': 'requires', 'needs': ['story'], 'then': ['between', 'frame', 'goe', 'ground', 'hop', 'listen', 'settl', 'stand', 'time', 'tomorrow', 'yesterday'], 'law': 'no story without a settled time frame the listener can stand in — hop between yesterday and tomorrow and the ground goes.', 'source': 'grammar and sentences'},
    {'kind': 'requires', 'needs': ['relation'], 'then': ['big', 'drop', 'lie', 'little', 'mark', 'noth', 'one', 'say', 'side', 'word'], 'law': 'no relation without a marker — drop the little words and the big ones lie side by side saying nothing about each other.', 'source': 'grammar and sentences'},
    {'kind': 'requires', 'needs': ['pronoun'], 'then': ['antecedent', 'grammar', 'listen', 'noth', 'perfect', 'recov', 'say', 'told'], 'law': 'no pronoun without an antecedent the listener can recover — "he told him it was his" is perfect grammar and says nothing.', 'source': 'grammar and sentences'},
    {'kind': 'requires', 'needs': ['writ'], 'then': ['group', 'gues', 'mark', 'read', 'somehow', 'word'], 'law': 'no writing without grouping — the reader will group the words somehow, and with no marks the grouping is a guess.', 'source': 'grammar and sentences'},
    {'kind': 'requires', 'needs': ['content'], 'then': ['cloth', 'cost', 'exist', 'fact', 'fast', 'free', 'regist', 'say', 'thing', 'trust', 'wrong'], 'law': 'no content without clothing — no register-free way to say a thing exists, and wrong clothes cost trust faster than a wrong fact does.', 'source': 'grammar and sentences'},
    {'kind': 'requires', 'needs': ['clarity'], 'then': ['backward', 'decod', 'know', 'open', 'place', 'read', 'sentence', 'stand'], 'law': 'no clarity without a place to stand — open with what the reader does not yet know and the sentence decodes backwards.', 'source': 'grammar and sentences'},
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
    {'kind': 'forbids', 'needs': ['did', 'who'], 'then': ['bag', 'die', 'english', 'rol', 'shuffle', 'word'], 'law': 'no who-did-what in a bag of English words — shuffle them and the roles die;', 'source': 'grammar and sentences'},
    {'kind': 'forbids', 'needs': ['doer', 'plural'], 'then': ['bird', 'english', 'half', 'sing', 'singular', 'standard', 'verb', 'work'], 'law': 'no plural doer with a singular verb in standard English — "the birds sings" does not half-work;', 'source': 'grammar and sentences'},
    {'kind': 'forbids', 'needs': ['nest', 'unlimit'], 'then': ['deep', 'four', 'head', 'legal', 'lost'], 'law': 'And no unlimited nesting in a head: four deep is legal and lost.', 'source': 'grammar and sentences'},
    {'kind': 'forbids', 'needs': ['false', 'true'], 'then': ['check', 'command', 'noth', 'obey', 'refuse'], 'law': 'no true-or-false in a command — you can obey it or refuse it, but there is nothing there to check.', 'source': 'grammar and sentences'},
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

