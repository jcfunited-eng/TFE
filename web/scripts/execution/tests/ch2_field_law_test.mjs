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
