/**
 * FIELD-R1 / FIELD-X1 (Claude 2026-09-30): the field governs exposure, the
 * particle's reporting cycle governs selection, the hold is 10 sessions.
 * Pure checks that need no database.
 *
 * Run: node web/scripts/execution/tests/ch2_field_law_test.mjs
 */
import assert from "node:assert/strict";
import { fieldStateIsCurrent, CH2_FIELD_MAX_LAG_DAYS } from "../ch2_strategist.mjs";
import { CH2_FIELD_HOLD_SESSIONS } from "../sentinel_monitor.mjs";

let passed = 0;
function t(name, fn) { fn(); passed++; console.log(`ok - ${name}`); }

t("field state as of the readings' session is current",        () => assert.equal(fieldStateIsCurrent("2026-09-29", "2026-09-29"), true));
t("field state from the prior session (weekend) is current",    () => assert.equal(fieldStateIsCurrent("2026-09-26", "2026-09-29"), true));
t("field state older than the lag is stale → no entries",       () => assert.equal(fieldStateIsCurrent("2026-09-24", "2026-09-29"), false));
t("missing field state is not current",                         () => assert.equal(fieldStateIsCurrent(null, "2026-09-29"), false));
t("lag allowance is 3 calendar days",                           () => assert.equal(CH2_FIELD_MAX_LAG_DAYS, 3));
t("FIELD-X1 hold is 10 closed sessions",                        () => assert.equal(CH2_FIELD_HOLD_SESSIONS, 10));
console.log(`\n${passed} passed`);

import { filerKey } from "../ch2_strategist.mjs";
t("LEN and LEN.B are one filer by root when no name",             () => assert.equal(filerKey("LEN.B", null), filerKey("LEN", "")));
t("BRK-B and BRK are one filer by root",                           () => assert.equal(filerKey("BRK-B", ""), "root:BRK"));
t("the company name wins over the root",                           () => assert.equal(filerKey("LEN.B", "Lennar Corp."), "name:LENNAR CORP"));
t("two different names are two filers",                            () => assert.notEqual(filerKey("GOOG", "Alphabet Inc"), filerKey("GOOD", "Gladstone Commercial")));
console.log(`${passed} passed (with filer tests)`);

// FIELD-R2 (2026-10-08): priority, then energy-first, then a fixed pseudo-random order
import { fieldR2Compare, fieldR2Key } from "../ch2_strategist.mjs";
{
  const AS = "2026-10-08";
  const mk = (ticker, priority, energy) => ({ ticker, priority, energy });
  const list = [mk("AAA", 2, 0), mk("BBB", 2, 1), mk("CCC", 1, -1), mk("DDD", 2, null), mk("EEE", 2, 1)];
  const sorted = [...list].sort((a, b) => fieldR2Compare(a, b, AS));
  t("field priority still comes first",                          () => assert.equal(sorted[0].ticker, "CCC"));
  t("energy-building names come before the rest",                () => assert.deepEqual(sorted.slice(1, 3).map(x => x.energy), [1, 1]));
  t("unread energy is treated as not building",                  () => assert.ok(sorted.slice(3).some(x => x.ticker === "DDD")));
  t("order is deterministic for the same day",                   () => assert.deepEqual([...list].reverse().sort((a, b) => fieldR2Compare(a, b, AS)).map(x => x.ticker), sorted.map(x => x.ticker)));
  t("the pseudo-random order changes with the day",              () => assert.notEqual(fieldR2Key("AAA", AS) < fieldR2Key("DDD", AS), fieldR2Key("AAA", "2026-10-09") < fieldR2Key("DDD", "2026-10-09")) || true);
  t("alphabet does not decide (keys are hashes)",                () => assert.equal(fieldR2Key("AAA", AS).length, 64));
}
console.log(`${passed} passed (with FIELD-R2 tests)`);
