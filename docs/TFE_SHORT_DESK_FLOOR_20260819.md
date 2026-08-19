# The short-desk floor — standing practice every real short book obeys
Filed 2026-08-19, at Joseph's demand that known best practice arrive
BEFORE failures, not after. These are not edge and need no decade
proof — they are the floor. Status marked per item.

1. LIQUIDITY: never exceed ~1% of a name's normal-day traded money;
   assume you exit on a NORMAL day, not the spike day.
   [DONE tonight — law in both engines and the gate]
2. DEAD SHELLS: serial reverse-split stocks are untradable — no
   borrow, no depth, violent gaps. Never touched.
   [DONE tonight — the 1000x ban]
3. BORROW: shorting requires shares to borrow. Low-float spiking
   micro-caps are routinely unborrowable or cost 50-300%/year in
   fees. A paper book that ignores this overstates every win.
   [NEXT: model a borrow-fee haircut by liquidity class on every
   short's P&L; refuse names in the classic no-borrow class
   (tiny float + fresh spike). Implementable from float + volume.]
4. OVERNIGHT GAPS: a short entered at the close carries unlimited
   overnight risk with no rule able to act until morning. Cap the
   book's TOTAL overnight exposure to spiking names, not just per
   position. [NEXT: portfolio-level cap, e.g. total spike-name
   exposure ≤ 25% of equity — constant to be ratified by Joseph.]
5. SHORT-SALE RESTRICTION: a stock down 10% on the day triggers a
   rule where shorts fill only on upticks — fills get worse exactly
   when the fade wants in. [NEXT: refuse entries on SSR days or
   model degraded fills.]
6. HALTS: volatile micro-caps halt repeatedly (limit-up/limit-down);
   a halted stock can reopen far through any stop. Already partly
   real in our gap accounting; the reading should flag names that
   halted during the spike day. [NEXT: halt count from intraday
   gaps in the bar record.]
7. CROWDING/SQUEEZE CORRELATION: many small shorts in the same
   hot sector are ONE position in a squeeze. Cap same-sector
   concurrent shorts. [NEXT: needs sector mapping — propose 3.]
8. EARNINGS AND NEWS: a spike on real news (earnings, FDA, contract)
   is repricing, not exhaust — different animal from a no-news pump.
   The sound-structure rule partly covers this (HAE/FLXS/UGI were
   earnings pops); a news check would name it directly.
   [PARTIAL — via Rule 3; news feed integration possible.]
9. EXECUTION PRICES: market orders in thin names fill far from the
   print. Real fills happen inside the spread you can see, sized to
   the depth that exists. Our 1% law is the proxy; slippage haircut
   on top for names under $1M/day. [NEXT: flat 0.5% haircut on
   entries/exits below $1M normal-day money.]
10. KNOWN-LOSS ORDERS: never carry a position into a session that
    already shows a loss beyond the cut line in pre-market — cut at
    first available price, never wait for the scheduled check.
    [DONE in practice tonight on TNON; make it engine law: a
    pre-market mark beyond the cut line cuts at the open.]
