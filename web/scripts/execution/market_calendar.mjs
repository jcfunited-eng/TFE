/**
 * Deterministic US equity holiday calendar.
 *
 * Dates are computed with UTC calendar arithmetic and evaluated against the
 * America/New_York civil date. No host locale or host time zone participates.
 */

import { easternClock, marketDateEastern } from "./market_clock.mjs";

function utcDate(year, month, day) {
  return new Date(Date.UTC(year, month - 1, day));
}

/** Fixed-date observance: Saturday -> Friday; Sunday -> Monday. */
function observed(month, day, year) {
  const date = utcDate(year, month, day);
  const weekday = date.getUTCDay();
  if (weekday === 6) date.setUTCDate(date.getUTCDate() - 1);
  if (weekday === 0) date.setUTCDate(date.getUTCDate() + 1);
  return date;
}

/** Nth occurrence of weekday in month. weekday: 0=Sun..6=Sat. */
function nthWeekday(year, month, weekday, occurrence) {
  const first = utcDate(year, month, 1);
  const day = 1 + ((weekday - first.getUTCDay() + 7) % 7) + ((occurrence - 1) * 7);
  return utcDate(year, month, day);
}

/** Last occurrence of weekday in month. */
function lastWeekday(year, month, weekday) {
  const last = new Date(Date.UTC(year, month, 0));
  const difference = (last.getUTCDay() - weekday + 7) % 7;
  return utcDate(year, month, last.getUTCDate() - difference);
}

/** Easter Sunday via the Anonymous Gregorian algorithm. */
function easter(year) {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + (2 * e) + (2 * i) - h - k) % 7;
  const m = Math.floor((a + (11 * h) + (22 * l)) / 451);
  const month = Math.floor((h + l - (7 * m) + 114) / 31);
  const day = ((h + l - (7 * m) + 114) % 31) + 1;
  return utcDate(year, month, day);
}

function goodFriday(year) {
  const date = easter(year);
  date.setUTCDate(date.getUTCDate() - 2);
  return date;
}

function dateKey(date) {
  return `${String(date.getUTCFullYear()).padStart(4, "0")}-${String(date.getUTCMonth() + 1).padStart(2, "0")}-${String(date.getUTCDate()).padStart(2, "0")}`;
}

export function nyseHolidays(year) {
  if (!Number.isInteger(year) || year < 1900 || year > 9999) {
    throw new RangeError("NYSE holiday year must be an integer from 1900 through 9999");
  }
  return [
    { date: dateKey(observed(1, 1, year)), name: "New Year's Day" },
    { date: dateKey(nthWeekday(year, 1, 1, 3)), name: "MLK Jr. Day" },
    { date: dateKey(nthWeekday(year, 2, 1, 3)), name: "Presidents' Day" },
    { date: dateKey(goodFriday(year)), name: "Good Friday" },
    { date: dateKey(lastWeekday(year, 5, 1)), name: "Memorial Day" },
    { date: dateKey(observed(6, 19, year)), name: "Juneteenth" },
    { date: dateKey(observed(7, 4, year)), name: "Independence Day" },
    { date: dateKey(nthWeekday(year, 9, 1, 1)), name: "Labor Day" },
    { date: dateKey(nthWeekday(year, 11, 4, 4)), name: "Thanksgiving" },
    { date: dateKey(observed(12, 25, year)), name: "Christmas" },
  ];
}

let cachedYear = null;
let holidayNames = new Map();

function ensureCache(year) {
  if (cachedYear === year) return;
  holidayNames = new Map();
  // Adjacent years bind observances that cross a civil-year boundary.
  for (const candidateYear of [year - 1, year, year + 1]) {
    for (const holiday of nyseHolidays(candidateYear)) {
      holidayNames.set(holiday.date, holiday.name);
    }
  }
  cachedYear = year;
}

export function isMarketHoliday(now = new Date()) {
  const clock = easternClock(now);
  ensureCache(clock.year);
  return holidayNames.has(clock.dateKey);
}

export function isTradingDay(now = new Date()) {
  const clock = easternClock(now);
  if (clock.weekday === "Sat" || clock.weekday === "Sun") return false;
  ensureCache(clock.year);
  return !holidayNames.has(clock.dateKey);
}

export function getHolidayName(now = new Date()) {
  const clock = easternClock(now);
  ensureCache(clock.year);
  return holidayNames.get(marketDateEastern(now)) ?? null;
}
