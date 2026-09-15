import assert from "node:assert/strict";
import { ch2DeadClock, CH2_DAMAGE_PCT, CH2_DEAD_SESSIONS } from "../ch2_dead_clock.mjs";

const ENTRY = 100;
const day = (i) => `2026-09-${String(i + 1).padStart(2, "0")}`;
const series = (values) => values.map((close, i) => ({ date: day(i), close }));

assert.equal(CH2_DAMAGE_PCT, 0.05);
assert.equal(CH2_DEAD_SESSIONS, 16);

// no damage at all
let r = ch2DeadClock(series([99, 98, 97, 96, 95.5]), ENTRY);
assert.deepEqual([r.dead, r.damaged, r.sessionsBelow], [false, false, 0]);

// exactly on the line counts as damage; 16 sessions below is still alive
r = ch2DeadClock(series(Array(16).fill(95)), ENTRY);
assert.deepEqual([r.dead, r.damaged, r.sessionsBelow, r.onsetDate], [false, true, 16, day(0)]);

// the 17th session below the line with no heal is DEAD
r = ch2DeadClock(series(Array(17).fill(94)), ENTRY);
assert.deepEqual([r.dead, r.sessionsBelow], [true, 17]);

// a sliding stock: new lows do NOT restart the clock (the reading's flaw)
r = ch2DeadClock(series([94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80, 79, 78]), ENTRY);
assert.deepEqual([r.dead, r.sessionsBelow, r.onsetDate], [true, 17, day(0)]);

// a heal (close back above the line) ends the episode and restarts the clock
r = ch2DeadClock(series([...Array(10).fill(94), 96, ...Array(12).fill(94)]), ENTRY);
assert.deepEqual([r.dead, r.sessionsBelow, r.onsetDate], [false, 12, day(11)]);

// heal then long second episode -> dead, onset is the second episode's start
r = ch2DeadClock(series([...Array(10).fill(94), 96, ...Array(17).fill(94)]), ENTRY);
assert.deepEqual([r.dead, r.sessionsBelow, r.onsetDate], [true, 17, day(11)]);

// currently healed -> not damaged regardless of history
r = ch2DeadClock(series([...Array(20).fill(90), 97]), ENTRY);
assert.deepEqual([r.dead, r.damaged, r.sessionsBelow], [false, false, 0]);

// unusable bars are ignored; bad inputs never sell
r = ch2DeadClock(series([94, 0, NaN, 94, 94]).concat([null]), ENTRY);
assert.deepEqual([r.damaged, r.sessionsBelow], [true, 3]);
assert.equal(ch2DeadClock(series([50]), 0).dead, false);
assert.equal(ch2DeadClock(null, ENTRY).dead, false);
assert.equal(ch2DeadClock([], ENTRY).damaged, false);

// tunable thresholds
r = ch2DeadClock(series(Array(5).fill(97)), ENTRY, { damagePct: 0.02, deadSessions: 4 });
assert.deepEqual([r.damaged, r.dead], [true, true]);

console.log("ch2 dead clock tests passed");
