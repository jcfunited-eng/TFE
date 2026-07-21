# TFE-RPT-UTZ-UNICORN-FORENSICS-20260721-v1

**Event:** UTZ (Utz Brands) entered by CH2 on 2026-07-14 at $7.40 (330 sh), sold manually by Joe on 2026-07-21 at $14.08 → **+$2,204.40 (+90.3%)** in 5 trading days of holding.

**Catalyst (public record):** Intersnack Group agreed to acquire Utz Brands at **$14.25/share cash** ($2.9B enterprise value, take-private with the Rice and Lissette founding family), announced **July 21, 2026** — a ~91% premium over the July 20 close. Exit at $14.08 captured 98.8% of the gap; the remaining $0.17 was deal-spread against months of close risk.

## Timeline (all verified from production data)

| Date | Price (close) | Volume | Structural state (daily tuple) |
|---|---|---|---|
| Jul 08 | 7.86 | 47,350 | S_UF 0.667, **D_k = -1**, M_k ≈ -0.009, B_k = -1 — quiescent/declining |
| Jul 09 | 7.72 | 82,501 | **IGNITION: D_k -1 → +1, M_k → +0.31, B_k -1 → -0.24, P_k = 1** |
| Jul 10–13 | 7.66–7.83 | ~90k | Field holds loaded, essentially frozen |
| **Jul 14** | 7.48 | 115,094 | **CH2 ENTRY** — argmax = Accumulate, accumulate_basin = **0.1696** (gate 0.15), break_agreement = 0.000, motion 0.866 |
| Jul 15–17 | 7.21–7.46 | 121k–193k | Price sags; field stays loaded; volume creeps to ~4× the Jul-8 base |
| Jul 20 | 7.45 | 98,503 | Position ≈ +0.7% after a week. Field unchanged. |
| **Jul 21** | **14.12** | 1,484,597 | **Overnight gap +89% on the Intersnack announcement** |

## Findings

1. **This was not momentum-chasing.** Price *fell* ~4% between ignition and announcement. Any price-momentum system would have ignored or abandoned UTZ. CH2 entered and held on field state alone — and the no-winner-capping doctrine (EXIT-A removal) is the only reason the position existed to collect the gap.
2. **The ignition preceded the public catalyst by 8 trading days.** D_k flipped out of quiescence with a fresh P_k=1 transition on Jul 9; deal announcement Jul 21 premarket. Volume roughly quadrupled off the Jul-8 base during the quiet window — consistent with pre-announcement accumulation leaking into the microstructure the tuple integrates. Consistent with, not proof of.
3. **UTZ did not stand out within its own cohort.** It was one of six CH2 entries on Jul 14, with a middle-of-pack basin magnitude (0.17 vs. cohort ~0.15–0.23). The cohort's other five went nowhere (±4% at Jul 21). The math flagged the class, not the specific winner.

## Verdict

Neither fluke-by-fiat nor proof of perception. **n = 1, consistent with the design thesis:** the machine was structurally long a quiet accumulation pattern before a private catalyst went public, because it reads field state instead of price momentum, and it kept the full payout because it refuses to cap winners. One case cannot separate perception from luck. The correct posture is to accumulate n.

## Unicorn fingerprint (to compare against future events)

Record for every future +50% CH2 event: days from ignition (P_k=1 flip) to catalyst; S_UF at entry (UTZ: exactly 0.667, the spec's strong-coupling line); accumulate_basin at entry; price drift between ignition and catalyst (UTZ: flat-to-down); volume creep multiple (UTZ: ~4×); catalyst type (UTZ: M&A take-private).

## Gaps found during this forensic

- **CH2 ledger rows do not persist the v3_basin dict** (`rationale_json->v3_basin` is null on all Jul-14 entries) — entry-time coupled-read state had to be reconstructed from `runtime_decisions_history`. Recommend CH2 ledgerInsert store the basin dict at entry (CH2 change — needs Joe's go).
- CloudWatch entry-pass logs age out in ~7 days; the ledger is the only durable record of pass decisions.

## Sources

- [Business Wire — Utz Brands and Intersnack announcement (2026-07-20/21)](https://www.businesswire.com/news/home/20260720176955/en/Utz-Brands-Inc.-and-Intersnack-Group-GmbH-Co.-KG-Announce-Agreement-to-Take-Utz-Private-and-Partnership-with-Founding-Family)
- [Utz investor relations — deal announcement](https://investors.utzsnacks.com/news/news-details/2026/Utz-Brands-Inc--and-Intersnack-Group-GmbH--Co--KG-Announce-Agreement-to-Take-Utz-Private-and-Partnership-with-Founding-Family/default.aspx)
- [SEC Form 8-K, Utz Brands FY2026](https://www.sec.gov/Archives/edgar/data/0001739566/000119312526309592/d157266dex991.htm)
- [Seeking Alpha — Utz to be acquired by Intersnack in $2.9B all-cash deal](https://seekingalpha.com/news/4615866-utz-brands-to-be-acquired-by-intersnack-in-29b-all-cash-deal-shares-rally)
