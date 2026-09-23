"""Session-complete CH2 historical control, not a new structural selection law.

Retains the existing V3 entry projection and declared book exits. Uses every
SPY session, net realized wins, round-trip costs, and matched-date SPY lift.
Publication dates need not be trading dates; eligibility uses the last close
available at publication, and fills occur strictly after publication.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ch2_winner_exit_measure import (
    GATE_ACC_MIN, GATE_BREAK_MAX, GATE_BARS_MIN, DEAD_DAMAGE_PCT, DEAD_SESSIONS,
    WALL_DAYS, BRAKE_PCT, RATCHET_ENGAGE, RATCHET_GIVEBACK,
    basin_frame, verify_vectorised,
)
from ch2_holding_length_measure import LIQ_FLOOR_USD, LIQ_WINDOW, PRICE_FLOOR
ROOT=Path(__file__).resolve().parents[1]
CAPITAL=100_000.0
SLICE=2_500.0
MAX_PER_STOCK={'one_per_stock':1,'repeats_3':3}
COSTS_BPS=[0.0,10.0]
NULL_SEEDS=50
SPLIT=np.datetime64('2024-03-15','D')
FIELDS=['s_uf','r_uf','d_k','m_k','r_rev_k','u_star_k','c_k','p_k','b_k']


def simulate_book(day_signals,bars,calendar,max_per_stock,cost_bps,start,end,rng=None,random_pool=None):
    """Close-only historical control; no inference of executable stop prices."""
    calendar=np.asarray(calendar,dtype='datetime64[D]')
    if not len(calendar) or np.any(calendar[1:]<=calendar[:-1]):
        raise ValueError('calendar must be nonempty, unique and increasing')
    if cost_bps<0 or not np.isfinite(cost_bps) or max_per_stock<1:
        raise ValueError('invalid cost or capacity')
    sessions=calendar[(calendar>=start)&(calendar<=end)]
    if not len(sessions):
        raise ValueError('no sessions in evaluation window')
    for ticker,(dates,prices,eligible) in bars.items():
        if len(dates)!=len(prices) or len(prices)!=len(eligible):
            raise ValueError(f'misaligned bar arrays: {ticker}')
        if np.any(dates[1:]<=dates[:-1]) or not np.isfinite(prices).all() or np.any(prices<=0):
            raise ValueError(f'invalid bar series: {ticker}')
    cash,open_pos,closed,curve=CAPITAL,[],[],[]
    per_stock=defaultdict(int)
    leg_cost=cost_bps/20_000.0
    for day in sessions:
        still=[]
        for p in open_pos:
            dates,prices,_=bars[p['ticker']]
            k=int(np.searchsorted(dates,day))
            if k>=len(dates) or dates[k]!=day:
                raise ValueError(f"missing held-position session: {p['ticker']} {day}")
            px=float(prices[k])
            p['peak']=max(p['peak'],px)
            reason=p.get('pending_exit')
            if reason is None:
                if px<=p['brake_line']:
                    reason='brake'
                elif p['peak']>=p['entry']*(1+RATCHET_ENGAGE) and px<=p['entry']+(p['peak']-p['entry'])*(1-RATCHET_GIVEBACK):
                    reason='ratchet'
                else:
                    p['below']=p['below']+1 if px<=p['damage_line'] else 0
                    if p['below']>DEAD_SESSIONS:
                        p['pending_exit']='dead_clock'
                    elif int((day-p['entry_date'])/np.timedelta64(1,'D'))>=WALL_DAYS:
                        p['pending_exit']='wall'
            if reason is not None:
                proceeds=p['shares']*px*(1-leg_cost)
                cash+=proceeds
                per_stock[p['ticker']]-=1
                closed.append({'ticker':p['ticker'],'entry_date':str(p['entry_date']),
                    'exit_date':str(day),'reason':reason,'entry_px':p['entry'],
                    'exit_px':px,'shares':p['shares'],'pnl':proceeds-p['cost_basis'],
                    'ret':px/p['entry']-1})
            else:
                still.append(p)
        open_pos=still
        todays=day_signals.get(day,[])
        if random_pool is not None:
            if rng is None:
                raise ValueError('random control requires explicit generator')
            pool=random_pool.get(day,[])
            todays=[(str(t),0.0) for t in rng.choice(pool,size=min(len(todays),len(pool)),replace=False)] if todays and pool else []
        for ticker,_ in todays:
            if per_stock[ticker]>=max_per_stock:
                continue
            dates,prices,_=bars[ticker]
            k=int(np.searchsorted(dates,day))
            if k>=len(dates) or dates[k]!=day:
                raise ValueError(f'missing scheduled fill: {ticker} {day}')
            px=float(prices[k])
            shares=int(SLICE//(px*(1+leg_cost)))
            spend=shares*px*(1+leg_cost)
            if shares<=0 or spend>cash:
                continue
            cash-=spend
            per_stock[ticker]+=1
            open_pos.append({'ticker':ticker,'entry':px,'entry_date':day,'shares':shares,
                'cost_basis':spend,'peak':px,'below':0,'damage_line':px*(1-DEAD_DAMAGE_PCT),
                'brake_line':px*(1-BRAKE_PCT)})
        marked=0.0
        for p in open_pos:
            dates,prices,_=bars[p['ticker']]
            k=int(np.searchsorted(dates,day))
            if k>=len(dates) or dates[k]!=day:
                raise ValueError(f"missing daily mark: {p['ticker']} {day}")
            marked+=p['shares']*prices[k]
        curve.append({'date':str(day),'equity':float(cash+marked)})
    equity=np.array([CAPITAL]+[r['equity'] for r in curve])
    reasons={reason:sum(t['reason']==reason for t in closed) for reason in sorted({t['reason'] for t in closed})}
    expected_cash=CAPITAL+sum(t['pnl'] for t in closed)-sum(p['cost_basis'] for p in open_pos)
    if abs(expected_cash-cash)>1e-6:
        raise ValueError('cash reconciliation failed')
    return {'final_equity':float(equity[-1]),'return_pct':float((equity[-1]/CAPITAL-1)*100),
        'max_drawdown_pct':float(np.min(equity/np.maximum.accumulate(equity)-1)*100),
        'positions_taken':len(closed)+len(open_pos),'positions_closed':len(closed),
        'still_open':len(open_pos),'win_rate_pct':100*sum(t['pnl']>0 for t in closed)/len(closed) if closed else None,
        'mean_trade_pct':100*float(np.mean([t['ret'] for t in closed])) if closed else None,
        'exit_reasons':reasons,'cash_reconciled':True,'round_trip_cost_bps':cost_bps,
        'cash':cash,'curve':curve,'closed_trades':closed,
        'open_positions':[{**p,'entry_date':str(p['entry_date'])} for p in open_pos]}


def publication_fill_indices(dates,calendar,day):
    """Require a current known close; allow publications on exchange holidays."""
    asof=int(np.searchsorted(dates,day,side='right'))-1
    market_asof=int(np.searchsorted(calendar,day,side='right'))-1
    if asof<0 or market_asof<0:
        return None
    if dates[asof]!=calendar[market_asof]:
        raise ValueError(f'stale source at publication {day}; last bar {dates[asof]}')
    fill=asof+1
    if fill>=len(dates):
        return None
    if market_asof+1>=len(calendar) or dates[fill]!=calendar[market_asof+1]:
        raise ValueError(f'missing next-session fill after {day}')
    return asof,fill


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lanes',type=Path)
    parser.add_argument('bars',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--no-null',action='store_true',required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    pieces=[]
    lo=hi=checked=None
    for chunk in pd.read_csv(args.lanes,parse_dates=['d'],chunksize=100_000):
        if chunk[FIELDS+['bar_count']].isna().any().any() or not np.isfinite(chunk[FIELDS].to_numpy()).all():
            raise ValueError('incomplete or nonfinite source field')
        lo=chunk.d.min() if lo is None else min(lo,chunk.d.min())
        hi=chunk.d.max() if hi is None else max(hi,chunk.d.max())
        if checked is None:
            checked=verify_vectorised(chunk)
            if checked['decision_mismatches']:
                raise ValueError('vectorised decision mismatch')
        bf=basin_frame(chunk)
        ok=bf.is_acc&(bf.acc>=GATE_ACC_MIN)&(bf.brk<GATE_BREAK_MAX)&(chunk.bar_count>GATE_BARS_MIN)
        selected=chunk.loc[ok,['ticker','d']].copy()
        selected['acc']=bf.loc[ok,'acc'].values
        pieces.append(selected)
    signals=pd.concat(pieces,ignore_index=True)
    if signals.duplicated(['ticker','d']).any():
        raise ValueError('duplicate signal dates')
    lo,hi=np.datetime64(lo.date(),'D'),np.datetime64(hi.date(),'D')
    symbols=sorted(set(signals.ticker)|{'SPY'})
    market=pd.read_parquet(args.bars,columns=['Date','Symbol','Close','Volume'],filters=[('Symbol','in',symbols)])
    if market.isna().any().any() or market.duplicated(['Symbol','Date']).any():
        raise ValueError('invalid market data')
    bars={}
    for symbol,g in market.groupby('Symbol',sort=True):
        g=g.sort_values('Date')
        close=g.Close.to_numpy(dtype=float)
        dates=g.Date.to_numpy(dtype='datetime64[D]')
        liquidity=pd.Series(close*g.Volume.to_numpy(dtype=float)).rolling(LIQ_WINDOW,min_periods=LIQ_WINDOW).median().to_numpy()
        bars[symbol]=(dates,close,(liquidity>=LIQ_FLOOR_USD)&(close>=PRICE_FLOOR))
    if 'SPY' not in bars:
        raise ValueError('SPY calendar missing')
    calendar=bars['SPY'][0]
    day_signals=defaultdict(list)
    for symbol,g in signals.groupby('ticker',sort=True):
        if symbol not in bars:
            raise ValueError(f'missing signal symbol: {symbol}')
        if symbol=='SPY':
            continue
        dates,prices,eligible=bars[symbol]
        for row in g.itertuples():
            day=np.datetime64(row.d.date(),'D')
            try:
                indices=publication_fill_indices(dates,calendar,day)
            except ValueError as error:
                raise ValueError(f'{symbol}: {error}') from error
            if indices is None:
                continue
            k,j=indices
            if eligible[k] and dates[j]<=hi:
                day_signals[dates[j]].append((symbol,float(row.acc)))
    for day in day_signals:
        day_signals[day].sort(key=lambda item:(-item[1],item[0]))
    windows={'full':(lo,hi),'first_half':(lo,SPLIT-np.timedelta64(1,'D')),'second_half':(SPLIT,hi)}
    output={'scope':'Legacy V3 control; lane fidelity and historical universe membership not certified. Not current CH2 deployment parity or a new full-field strategy.',
        'source_lanes':str(args.lanes),'source_sha256':hashlib.sha256(args.lanes.read_bytes()).hexdigest(),
        'port_check':checked,'windows':{},'null_omitted':True}
    for name,(start,end) in windows.items():
        sessions=calendar[(calendar>=start)&(calendar<=end)]
        if not len(sessions):
            continue
        start,end=sessions[0],sessions[-1]
        window_signals={d:s for d,s in day_signals.items() if start<d<=end}
        spy_d,spy_c,_=bars['SPY']
        benchmark=100*(spy_c[np.searchsorted(spy_d,end)]/spy_c[np.searchsorted(spy_d,start)]-1)
        output['windows'][name]={'start':str(start),'end':str(end),'spy_return_pct':float(benchmark),'runs':{}}
        for cost in COSTS_BPS:
            for label,cap in MAX_PER_STOCK.items():
                result=simulate_book(window_signals,bars,calendar,cap,cost,start,end)
                result['lift_percentage_points']=result['return_pct']-benchmark
                key=f'{label}_{cost:g}bp_round_trip'
                output['windows'][name]['runs'][key]=result
                print(json.dumps({'window':name,'run':key,**{k:result[k] for k in ('positions_closed','win_rate_pct','return_pct','lift_percentage_points')}}),flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(output,stream,indent=2,allow_nan=False)
        stream.write('\n')


if __name__=='__main__':
    main()
