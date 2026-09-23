import numpy as np
import pytest
from tools.ch2_book_simulation import simulate_book, publication_fill_indices, CAPITAL


def replay(prices, *, cost=0, signals=None):
    dates=np.arange(np.datetime64('2026-01-01'),np.datetime64('2026-01-01')+len(prices))
    bars={'X':(dates,np.array(prices,dtype=float),np.ones(len(prices),dtype=bool))}
    signals={dates[1]:[('X',1)]} if signals is None else signals
    return simulate_book(signals,bars,dates,1,cost,dates[0],dates[-1])


def test_exit_and_mark_occur_without_new_signals():
    r=replay([100,100,70,90])
    assert len(r['curve'])==4
    assert r['positions_closed']==1
    assert r['closed_trades'][0]['exit_date']=='2026-01-03'
    assert r['exit_reasons']=={'brake':1}
    assert r['final_equity']==CAPITAL-750
    assert r['cash_reconciled']


def test_dead_clock_counts_all_sessions_and_fills_next_close():
    r=replay([100,100]+[94]*17+[93])
    assert r['exit_reasons']=={'dead_clock':1}
    assert r['closed_trades'][0]['exit_date']=='2026-01-20'
    assert r['closed_trades'][0]['exit_px']==93


def test_unclosed_positions_are_not_counted_as_wins():
    r=replay([100,100,110])
    assert r['positions_closed']==0
    assert r['still_open']==1
    assert r['win_rate_pct'] is None
    assert r['final_equity']==CAPITAL+250


def test_roundtrip_cost_is_split_between_legs_and_net_wr_used(monkeypatch):
    import tools.ch2_book_simulation as module
    monkeypatch.setattr(module,'WALL_DAYS',1)
    r=replay([100,100,100.04,100.05],cost=10)
    trade=r['closed_trades'][0]
    assert trade['ret']>0
    assert trade['pnl']<0
    assert r['win_rate_pct']==0
    expected=trade['shares']*(100.05*(1-.0005)-100*(1+.0005))
    assert trade['pnl']==pytest.approx(expected)


def test_no_entry_window_still_has_complete_cash_curve():
    r=replay([100,110,90],signals={})
    assert [x['equity'] for x in r['curve']]==[CAPITAL]*3
    assert r['positions_taken']==0


def test_missing_held_session_is_not_silently_forward_filled():
    dates=np.array(['2026-01-01','2026-01-02','2026-01-05'],dtype='datetime64[D]')
    bars={'X':(dates[:2],np.array([100.,100.]),np.ones(2,dtype=bool))}
    with pytest.raises(ValueError,match='missing held-position'):
        simulate_book({dates[1]:[('X',1)]},bars,dates,1,0,dates[0],dates[-1])


def test_holiday_publication_uses_previous_session_then_next_fill():
    dates=np.array(['2026-07-02','2026-07-06'],dtype='datetime64[D]')
    assert publication_fill_indices(dates,dates,np.datetime64('2026-07-03'))==(0,1)


def test_stale_source_is_not_mistaken_for_holiday():
    dates=np.array(['2026-03-24','2026-07-06'],dtype='datetime64[D]')
    calendar=np.array(['2026-03-24','2026-07-02','2026-07-06'],dtype='datetime64[D]')
    with pytest.raises(ValueError,match='stale source'):
        publication_fill_indices(dates,calendar,np.datetime64('2026-07-03'))
