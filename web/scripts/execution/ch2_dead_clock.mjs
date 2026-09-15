/**
 * CH2 dead clock — the loss side of Joseph's exit law made able to run out.
 *
 * The nightly reading's DEAD test is "more than 16 sessions past its LAST
 * damage with no healing". On a stock that keeps sliding every new low is new
 * damage and the clock restarts, so losers rode to the -20% brake (VRTS -16%,
 * DEI -13%, AZZ -12% all read RECOVERY_ALIVE on 2026-09-11). Joseph's order
 * 2026-09-15: fix it.
 *
 * The clock here starts at the FIRST damaging close of the episode — a closed
 * session more than CH2_DAMAGE_PCT below the entry price — and only a close
 * back above that line ends the episode (heals). More than CH2_DEAD_SESSIONS
 * closed sessions below the line with no heal is DEAD. The session count is
 * Joseph's measured healing floor (healing_table.json: 53,890 damage events
 * over a decade, both halves identical — living bodies heal within 16
 * sessions in 99 of 100 cases). The damage line is the old minimum stop
 * distance: a dip that heals is weather; one that does not is not.
 *
 * Pure function over closed sessions; the sentinel supplies the bars.
 */
export const CH2_DAMAGE_PCT = 0.05;
export const CH2_DEAD_SESSIONS = 16;

/**
 * @param {{date: string, close: number}[]} closes closed sessions since entry, ascending
 * @param {number} entryPrice
 * @returns {{dead: boolean, damaged: boolean, onsetDate: string|null, sessionsBelow: number, line: number}}
 */
export function ch2DeadClock(closes, entryPrice, { damagePct = CH2_DAMAGE_PCT, deadSessions = CH2_DEAD_SESSIONS } = {}) {
  const entry = Number(entryPrice);
  if (!Number.isFinite(entry) || entry <= 0 || !Array.isArray(closes)) {
    return { dead: false, damaged: false, onsetDate: null, sessionsBelow: 0, line: NaN };
  }
  const line = entry * (1 - damagePct);
  let onsetIndex = -1;
  let onsetDate = null;
  const usable = closes.filter((c) => c && Number.isFinite(Number(c.close)) && Number(c.close) > 0);
  for (let i = 0; i < usable.length; i++) {
    const close = Number(usable[i].close);
    if (close <= line) {
      if (onsetIndex < 0) { onsetIndex = i; onsetDate = String(usable[i].date ?? ""); }
    } else {
      onsetIndex = -1;
      onsetDate = null;
    }
  }
  if (onsetIndex < 0) return { dead: false, damaged: false, onsetDate: null, sessionsBelow: 0, line };
  const sessionsBelow = usable.length - onsetIndex;
  return { dead: sessionsBelow > deadSessions, damaged: true, onsetDate, sessionsBelow, line };
}
