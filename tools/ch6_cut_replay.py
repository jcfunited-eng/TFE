"""CH6 cut replay — declared before measuring (2026-10-06):
alternative to each cut = keep holding under CH6's own exits from the cut day on:
 +2% bank on a daily-low touch (short), 20% anomaly stop on a daily-high touch
 (same day both -> stop), 5th-session close time exit (sessions from entry).
Gap opens beyond a level fill at the open. No costs."""
import json,subprocess,urllib.request,urllib.parse,collections
s=json.loads(json.loads(subprocess.check_output(['aws','secretsmanager','get-secret-value','--secret-id','tfe/market-data/prod','--query','SecretString','--output','json'])))
H={'APCA-API-KEY-ID':s['APCA_API_KEY_ID'],'APCA-API-SECRET-KEY':s['APCA_API_SECRET_KEY']}
b=json.load(open('artifacts/vtvr_observer/ch6_book.json'))
cuts=[c for c in b['closed'] if c['reason'].split()[0] in ('QUIET-CUT','RULES-CUT','ANOMALY-CUT')]
syms=sorted({c['symbol'] for c in cuts})
bars=collections.defaultdict(list)
for i in range(0,len(syms),50):
    tok=None
    while True:
        q={'symbols':','.join(syms[i:i+50]),'timeframe':'1Day','start':'2026-08-01','end':'2026-10-06','limit':10000,'adjustment':'split','feed':'sip'}
        if tok:q['page_token']=tok
        r=json.load(urllib.request.urlopen(urllib.request.Request('https://data.alpaca.markets/v2/stocks/bars?'+urllib.parse.urlencode(q),headers=H)))
        for k,v in r['bars'].items(): bars[k]+=v
        tok=r.get('next_page_token')
        if not tok:break
out=[]
for c in cuts:
    e=c['entry_px']; bs=sorted(bars.get(c['symbol'],[]),key=lambda x:x['t'])
    after=[x for x in bs if x['t'][:10]>c['entry_date']]       # sessions after entry
    cutd=c['exit_at'][:10]
    held=[x for x in after[:5]]                                 # sessions 1..5
    rest=[x for x in held if x['t'][:10]>=cutd]
    # on the cut day itself the cut happened at a live mark; replay from the NEXT session after the cut day
    rest=[x for x in held if x['t'][:10]>cutd]
    if len(after)<5 or not held:
        out.append((c,None,'open-window')); continue
    bank=e*0.98; stop=e*1.20; res=None
    if not rest:  # cut on/after session 5 — alt = session-5 close
        res=(e-held[-1]['c'])/e*100; why='time'
    else:
        for x in rest:
            if x['o']>=stop: res=(e-x['o'])/e*100; why='stop-gap'; break
            if x['h']>=stop: res=-20.0; why='stop'; break
            if x['o']<=bank: res=(e-x['o'])/e*100; why='bank-gap'; break
            if x['l']<=bank: res=2.0; why='bank'; break
        else:
            res=(e-rest[-1]['c'])/e*100; why='time'
    out.append((c,res,why))
done=[o for o in out if o[1] is not None]
def summ(rows,label):
    a=sum(o[0]['pnl'] for o in rows); alt=sum(o[1]/100*o[0]['shares']*o[0]['entry_px'] for o in rows)
    w=sum(o[1]>0 for o in rows)
    print(f"{label:28} n={len(rows):3} actual ${a:9.2f}  hold ${alt:9.2f}  diff ${alt-a:9.2f}  hold-winners {w}")
for k in ('QUIET-CUT','RULES-CUT','ANOMALY-CUT'):
    rows=[o for o in done if o[0]['reason'].startswith(k)]
    summ(rows,k)
    mid=sorted(o[0]['exit_at'] for o in rows)[len(rows)//2] if rows else ''
    summ([o for o in rows if o[0]['exit_at']<mid],'  first half')
    summ([o for o in rows if o[0]['exit_at']>=mid],'  second half')
    print('   ',collections.Counter(o[2] for o in rows))
summ(done,'ALL CUTS')
print('skipped (window not complete):',sum(o[1] is None for o in out))
json.dump([{'symbol':o[0]['symbol'],'reason':o[0]['reason'],'exit_at':o[0]['exit_at'],'actual_pnl':o[0]['pnl'],'hold_ret_pct':o[1],'hold_exit':o[2]} for o in out],open('artifacts/ch4_uf/ch6_cut_replay_20261006.json','w'),indent=1)
