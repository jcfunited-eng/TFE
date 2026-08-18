import assert from "node:assert/strict";
import {
  easternClock,
  isCh3EodCloseWindow,
  isCh3RearmWindowEastern,
  isDailyEntryWindow,
  isDaemonMarketWindow,
  isRegularMarketSession,
  marketDateEastern,
  regularSessionMinutesElapsed,
} from "../market_clock.mjs";

const summerOpen = new Date("2026-08-18T13:30:00Z");
const winterOpen = new Date("2026-12-18T14:30:00Z");
assert.equal(easternClock(summerOpen).minuteOfDay, 570);
assert.equal(easternClock(winterOpen).minuteOfDay, 570);
assert.equal(isRegularMarketSession(summerOpen), true);
assert.equal(isRegularMarketSession(winterOpen), true);
assert.equal(isRegularMarketSession(new Date("2026-12-18T13:30:00Z")), false);
assert.equal(isDaemonMarketWindow(new Date("2026-08-18T13:00:00Z")), true);
assert.equal(isDaemonMarketWindow(new Date("2026-12-18T14:00:00Z")), true);

assert.equal(isDailyEntryWindow(new Date("2026-08-18T13:45:00Z")), true);
assert.equal(isDailyEntryWindow(new Date("2026-12-18T14:45:00Z")), true);
assert.equal(isDailyEntryWindow(new Date("2026-12-18T13:45:00Z")), false);

assert.equal(isCh3RearmWindowEastern(new Date("2026-08-18T14:16:00Z")), true);
assert.equal(isCh3RearmWindowEastern(new Date("2026-12-18T15:16:00Z")), true);
assert.equal(isCh3RearmWindowEastern(new Date("2026-08-18T18:00:00Z")), false);
assert.equal(isCh3RearmWindowEastern(new Date("2026-12-18T19:00:00Z")), false);

assert.equal(isCh3EodCloseWindow(new Date("2026-08-18T19:30:00Z")), true);
assert.equal(isCh3EodCloseWindow(new Date("2026-12-18T20:30:00Z")), true);
assert.equal(isCh3EodCloseWindow(new Date("2026-12-18T19:30:00Z")), false);

assert.equal(regularSessionMinutesElapsed(new Date("2026-08-18T14:30:00Z")), 60);
assert.equal(regularSessionMinutesElapsed(new Date("2026-12-18T15:30:00Z")), 60);
assert.equal(marketDateEastern(new Date("2026-08-19T02:00:00Z")), "2026-08-18");

console.log("market clock tests passed");
