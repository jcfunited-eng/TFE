"""Numerical joint-event resolution; no force or anatomical law.

Only sampled intervals containing several changed joint boundaries reach this
algebra. Binary stage evidence defines two exact rational cubics. Their roots
are numerical-path evidence, never an enclosure of continuum motion.
"""
from fractions import Fraction as _Q


def _joint_poly(c, x):
    value = _Q(0)
    for a in reversed(c):
        value = value*x+a
    return value


def _joint_bernstein(c):
    n = len(c)-1
    return tuple(sum(c[j]*_Q(math.comb(k,j),math.comb(n,j))
                     for j in range(k+1)) for k in range(n+1))


def _joint_lagrange(nodes, j):
    c = [_Q(1)]
    for k,x in enumerate(nodes):
        if k == j: continue
        out = [_Q(0)]*(len(c)+1)
        for i,v in enumerate(c):
            out[i] -= v*x/(nodes[j]-x)
            out[i+1] += v/(nodes[j]-x)
        c = out
    return tuple(c)


def _joint_cubics(operands, kind, after):
    q0,q1,q2,q3,v1,v2,v3,threshold,h = map(_Q,operands)
    sign = (1 if kind == 0 else -1)*(1 if after else -1)
    nodes = tuple(_Q(float(x)) for x in C)
    integrated = [sign*(q0-threshold),_Q(0),_Q(0),_Q(0)]
    for j,v in enumerate((v1,v2,v3)):
        for power,a in enumerate(_joint_lagrange(nodes,j)):
            integrated[power+1] += sign*h*v*a/(power+1)
    position = [_Q(0)]*4
    for j,q in enumerate((q0,q1,q2,q3)):
        for power,a in enumerate(_joint_lagrange((_Q(0),)+nodes,j)):
            position[power] += sign*(q-threshold)*a
    return tuple(position),tuple(integrated)


def _joint_root(c, shift=_Q(0), clip=False):
    derivative = _joint_bernstein(tuple(_Q(j)*c[j] for j in range(1,len(c))))
    if not (all(v <= 0 for v in derivative) and any(v < 0 for v in derivative)):
        raise ValueError('joint numerical cubic is not certified monotone')
    lo,hi = _Q(0),_Q(1)
    a,b = _joint_poly(c,lo)+shift,_joint_poly(c,hi)+shift
    if clip and a < 0: return lo,lo
    if clip and b > 0: return hi,hi
    if not a >= 0 >= b: raise ValueError('joint numerical cubic lacks root signs')
    if a == 0: return lo,lo
    if b == 0: return hi,hi
    # Binary64 stage inputs: at most one subdivision per significand bit.
    for _ in range(int(np.finfo(float).nmant)+1):
        mid = (lo+hi)/2
        value = _joint_poly(c,mid)+shift
        if value == 0: return mid,mid
        if value > 0: lo = mid
        else: hi = mid
    return lo,hi


def _joint_root_certificate(operands, kind, after):
    position,integrated = _joint_cubics(operands,kind,after)
    # Equality at the actual predecessor can be a genuinely shared departure,
    # not several unseen events to be separated. Prove negative sign throughout
    # the open interval by the Bernstein convex hull of p(x)/x in BOTH cubics.
    departure = all(p[0] == 0 and all(v <= 0 for v in _joint_bernstein(p[1:]))
                    and _joint_poly(p,_Q(1)) < 0 for p in (position,integrated))
    if departure:
        return dict(lo=_Q(0),hi=_Q(0),polynomials=(position,integrated))
    envelope = max(abs(v) for v in _joint_bernstein(tuple(
        a-b for a,b in zip(position,integrated))))
    lo = _joint_root(integrated,-envelope,True)[0]
    hi = _joint_root(integrated,envelope,True)[1]
    for p in (position,integrated):
        a,b = _joint_root(p)
        if not lo <= a <= b <= hi:
            raise ValueError('joint numerical root constructions not enclosed')
    return dict(lo=lo,hi=hi,polynomials=(position,integrated))


def _joint_same_roots(a, b):
    if a['lo'] == a['hi'] == b['lo'] == b['hi']:
        return True
    # Exact proportional cubics certify a shared root; overlapping numerical
    # brackets alone cannot certify coincidence.
    for x,y in zip(a['polynomials'],b['polynomials']):
        scale = next((i for i,v in enumerate(x) if v),None)
        if scale is None or not y[scale] or any(
                u*y[scale] != v*x[scale] for u,v in zip(x,y)):
            return False
    return True


def joint_sample_resolution(before, stage_domains, operands):
    """Refuse a merged sampled bin unless its joint roots are proven shared.

    `operands` carries only changed physical joint coordinates/velocities and
    anatomical limits from this same solved step. No semantic action labels.
    """
    samples = (before,*stage_domains)
    result = dict(resolved=True,groups=[])
    for index,(left,right) in enumerate(zip(samples,samples[1:])):
        changed = [(kind,i) for kind in (0,1)
                   if left[kind] != right[kind]
                   for i,(a,b) in enumerate(zip(left[kind],right[kind])) if a != b]
        if len(changed) < 2: continue
        row = dict(from_sample=index,to_sample=index+1,joints=changed,
                   coincident=False,roots=[],failure=None)
        result['groups'].append(row)
        roots = []
        try:
            for kind,i in changed:
                root = _joint_root_certificate(operands[(kind,i)],kind,right[kind][i])
                roots.append(root)
                row['roots'].append(dict(kind=kind,ordinal=i,
                    normalized_bracket=[str(root['lo']),str(root['hi'])]))
            row['coincident'] = all(_joint_same_roots(roots[0],r) for r in roots[1:])
        except ValueError as error:
            row['failure'] = str(error)
        result['resolved'] = result['resolved'] and row['coincident']
    return result
