"""Numerical event-time settlement for the existing native joint force law.

Offline Radau qualification only. No action selection, native force edits,
position projection, retained solver state, or new physical tolerance.
"""


def _event_refine():
    raise ValueError('one-sided joint event requires subdivision')


def _boundary_domain(domain, boundary):
    """Remove precisely the selected native limit row and its geometric flag."""
    flags = [list(domain[0]),list(domain[1])]
    flags[boundary['kind']][boundary['ordinal']] = False
    rows = tuple((int(t),int(i),int(s)) for t,i,s in
                 zip(domain[2],domain[3],domain[4])
                 if not (int(t) == int(mj.mjtConstraint.mjCNSTR_LIMIT_JOINT)
                         and int(i) == boundary['joint']))
    return tuple(flags[0]),tuple(flags[1]),rows,domain[5],domain[6]


def _event_operands(e, kind, ordinal):
    m = e._model
    joint = int(e._limited[ordinal])
    qa,va = int(m.jnt_qposadr[joint]),int(m.jnt_dofadr[joint])
    # The free-root/hinge layout was checked by _plain_step. Native snapshots
    # retain integration state separately; use the explicit restored q0 here.
    return (qa,va,joint,float(m.jnt_range[joint,kind]
                 +(1 if kind == 0 else -1)*m.jnt_margin[joint]))


def _changed_joint_event(e, q0, before, value):
    domains = tuple(s['snapshot']['domain'] for s in value[3])
    changed = [(kind,i) for kind in (0,1)
               for i,active in enumerate(before['domain'][kind])
               if any(active != d[kind][i] for d in domains)]
    roots = []
    for kind,ordinal in changed:
        qa,va,joint,threshold = _event_operands(e,kind,ordinal)
        after = domains[-1][kind][ordinal]
        if after == before['domain'][kind][ordinal]:
            _event_refine()  # Recrossing is not a single arrival.
        operands = (float(q0[qa]),*(float(s['qpos'][qa]) for s in value[3]),
                    *(float(s['qvel'][va]) for s in value[3]),threshold,
                    value[0]['time']-before['time'])
        try:
            certificate = _joint_root_certificate(operands,kind,after)
        except ValueError:
            _event_refine()
        if certificate['lo'] == certificate['hi'] == 0:
            # Existing exact two-cubic departure proof, including shared
            # initial release. No fake elapsed time or imposed event order.
            continue
        incoming_active = bool(before['domain'][kind][ordinal])
        interior = (-1 if kind == 0 else 1)*(1 if incoming_active else -1)
        incoming_q = math.nextafter(threshold,math.copysign(math.inf,interior))
        roots.append(dict(kind=kind,ordinal=ordinal,joint=joint,qadr=qa,vadr=va,
            threshold=threshold,incoming_active=incoming_active,incoming_q=incoming_q,
            sign=(1 if kind == 0 else -1)*(-1 if incoming_active else 1)))
    if len(roots) > 1:
        _event_refine()
    return roots[0] if roots else None


def _root_trial(probe,e,base,original_dt,before,q0,boundary,end,supply):
    interval._restore(e,base,original_dt)
    value = probe._plain_step(e,end-before['time'],supply,boundary)
    stages = value[3]
    # No mixed-force earlier quadrature nodes, hidden other events, or
    # reliance on unconverged root/intermediate dynamics.
    if any(s['snapshot']['domain'] != before['domain'] for s in stages[:2]):
        _event_refine()
    if stages[-1]['force_snapshot']['domain'] != before['domain']:
        _event_refine()
    qa,va = boundary['qadr'],boundary['vadr']
    operands = (float(q0[qa]),*(float(s['qpos'][qa]) for s in stages),
                *(float(s['qvel'][va]) for s in stages),boundary['threshold'],
                end-before['time'])
    # Both actual-position interpolation and integrated stage-velocity
    # polynomials must describe monotone arrival, even on pre-root trials.
    for polynomial in _joint_cubics(operands,boundary['kind'],
                                    not boundary['incoming_active']):
        derivative = _joint_bernstein(tuple(_Q(j)*polynomial[j]
                                       for j in range(1,len(polynomial))))
        if not all(x <= 0 for x in derivative) or not any(x < 0 for x in derivative):
            _event_refine()
    residual = boundary['sign']*(float(stages[-1]['qpos'][qa])-boundary['threshold'])
    if not math.isfinite(residual):
        raise ValueError('nonfinite joint event residual')
    return value,residual


def _locate_joint_event(probe,e,base,original_dt,before,q0,boundary,end,supply):
    start = before['time']
    lo,hi = start,end
    rlo = boundary['sign']*(float(q0[boundary['qadr']])-boundary['threshold'])
    upper,rhi = _root_trial(probe,e,base,original_dt,before,q0,boundary,hi,supply)
    # Closed native limits: entering includes equality; leaving excludes it.
    def crossed(r):
        return r < 0 if boundary['incoming_active'] else r <= 0
    if not rlo > 0 or not crossed(rhi):
        _event_refine()
    trials = 1
    # Binary64's full exponent/significand span bounds arithmetic bisection,
    # including a zero initial clock. The independent force-call cap also holds.
    for _ in range(int(np.finfo(float).nmant-np.finfo(float).minexp)+2):
        if rhi == 0 and not boundary['incoming_active']:
            lo,rlo = hi,rhi
            break
        mid = lo+(hi-lo)/2
        if not lo < mid < hi:
            break
        value,r = _root_trial(probe,e,base,original_dt,before,q0,boundary,mid,supply)
        trials += 1
        if not rhi <= r <= rlo:
            _event_refine()  # No assumed monotonicity in a noisy solved bracket.
        if crossed(r):
            hi,rhi,upper = mid,r,value
        else:
            lo,rlo = mid,r
    else:
        _event_refine()
    if ((lo != hi and math.nextafter(lo,hi) != hi)
            or hi-lo > interval.EVENT_S
            or max(abs(rlo),abs(rhi)) > interval.ANGLE_RAD):
        _event_refine()
    force_domain = upper[3][-1]['force_snapshot']['domain']
    native_domain = upper[0]['domain']
    if (native_domain[boundary['kind']][boundary['ordinal']] == boundary['incoming_active']
            or _boundary_domain(force_domain,boundary) != _boundary_domain(native_domain,boundary)):
        _event_refine()
    upper[3][-1]['joint_boundary'] = dict(boundary,
        time_bracket_s=(lo,hi),signed_position_bracket_rad=(rlo,rhi),trials=trials,
        final_collocation_residual=upper[3][-1]['collocation_residual'],
        force_input_is_one_sided_approximation=True)
    # Last bracket trial need not be the accepted upper. Restore its REAL state,
    # never the adjacent-coordinate force scratch.
    interval._restore(e,upper[0]['state'],original_dt)
    return upper


def _event_aligned_step(probe,e,dt,supply):
    """One unpublished interval, possibly split at verified joint arrivals."""
    if not math.isfinite(dt) or not 0 < dt <= e.limits.step_us/1e6:
        raise ValueError('diagnostic step must not enlarge declared timestep')
    if not math.isfinite(supply) or supply < 0:
        raise ValueError('invalid work supply')
    m,d = e._model,e._data
    initial,original_dt = interval._state(e),float(m.opt.timestep)
    end = float(d.time)+dt
    if not math.isfinite(end) or end <= float(d.time):
        raise ValueError('unrepresentable interval')
    work,impulses,stages = (0.,)*6,{},[]
    try:
        while float(d.time) < end:
            base,before,q0 = interval._state(e),interval._snapshot(e),d.qpos.copy()
            remaining = supply-work[0]
            value = probe._plain_step(e,end-before['time'],remaining)
            boundary = _changed_joint_event(e,q0,before,value)
            if boundary is not None:
                value = _locate_joint_event(probe,e,base,original_dt,before,q0,boundary,end,remaining)
            if not before['time'] < value[0]['time'] <= end:
                raise ValueError('joint event failed to advance physical clock')
            work = interval._work_add(work,value[1])
            impulses = interval._impulse_add(impulses,value[2])
            stages.extend(value[3])
            if work[0] > supply:
                raise ValueError('mechanical energy supply exhausted; no successor')
        return value[0],work,impulses,stages
    except BaseException as error:
        interval._restore(e,initial,original_dt)
        if interval._state(e).astype('<f8').tobytes() != initial.astype('<f8').tobytes():
            raise AssertionError('joint event transaction rollback differs') from error
        raise
