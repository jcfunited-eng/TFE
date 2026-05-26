/**
 * web/scripts/execution/market_calendar.mjs
 * US stock market holiday calendar — computed, never needs updating.
 *
 * NYSE/NASDAQ observed holidays. The market is CLOSED on these days.
 * No entries, no exits (except catastrophic), no sentinel audits.
 *
 * All 10 NYSE holidays are computed algorithmically:
 *   - Fixed-date holidays observe Fri if Sat, Mon if Sun
 *   - Floating holidays use Nth-weekday-of-month rules
 *   - Good Friday uses the Anonymous Gregorian Easter algorithm
 *
 * Source: NYSE holiday calendar (nyse.com/markets/hours-calendars)
 */

// ── Holiday computation ─────────────────────────────────────────────────

/** Observed date: if Sat → Fri, if Sun → Mon */
function observed(month, day, year) {
  const d = new Date(year, month - 1, day);
  const dow = d.getDay();
  if (dow === 6) return new Date(year, month - 1, day - 1); // Sat → Fri
  if (dow === 0) return new Date(year, month - 1, day + 1); // Sun → Mon
  return d;
}

/** Nth occurrence of a weekday in a month (1-indexed). weekday: 0=Sun..6=Sat */
function nthWeekday(year, month, weekday, n) {
  const first = new Date(year, month - 1, 1);
  let dayOfMonth = 1 + ((weekday - first.getDay() + 7) % 7);
  dayOfMonth += (n - 1) * 7;
  return new Date(year, month - 1, dayOfMonth);
}

/** Last occurrence of a weekday in a month */
function lastWeekday(year, month, weekday) {
  const last = new Date(year, month, 0); // last day of month
  const diff = (last.getDay() - weekday + 7) % 7;
  return new Date(year, month - 1, last.getDate() - diff);
}

/**
 * Easter date via Anonymous Gregorian algorithm.
 * Returns Date for Easter Sunday of the given year.
 */
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
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day);
}

/** Good Friday = 2 days before Easter Sunday */
function goodFriday(year) {
  const e = easter(year);
  return new Date(e.getFullYear(), e.getMonth(), e.getDate() - 2);
}

/** Format Date as "YYYY-MM-DD" */
function fmt(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * Compute all NYSE holidays for a given year.
 * Returns array of { date: "YYYY-MM-DD", name: string }
 */
export function nyseHolidays(year) {
  return [
    { date: fmt(observed(1, 1, year)),                   name: "New Year's Day" },
    { date: fmt(nthWeekday(year, 1, 1, 3)),              name: "MLK Jr. Day" },
    { date: fmt(nthWeekday(year, 2, 1, 3)),              name: "Presidents' Day" },
    { date: fmt(goodFriday(year)),                        name: "Good Friday" },
    { date: fmt(lastWeekday(year, 5, 1)),                name: "Memorial Day" },
    { date: fmt(observed(6, 19, year)),                   name: "Juneteenth" },
    { date: fmt(observed(7, 4, year)),                    name: "Independence Day" },
    { date: fmt(nthWeekday(year, 9, 1, 1)),              name: "Labor Day" },
    { date: fmt(nthWeekday(year, 11, 4, 4)),             name: "Thanksgiving" },
    { date: fmt(observed(12, 25, year)),                  name: "Christmas" },
  ];
}

// ── Build lookup caches ─────────────────────────────────────────────────
// Pre-compute current year and next year. Cache is rebuilt if year changes.
let _cachedYear = 0;
let _holidaySet = new Set();
let _holidayNames = {};

function ensureCache(year) {
  if (_cachedYear === year) return;
  _holidaySet = new Set();
  _holidayNames = {};
  for (const y of [year, year + 1]) {
    for (const h of nyseHolidays(y)) {
      _holidaySet.add(h.date);
      _holidayNames[h.date] = h.name;
    }
  }
  _cachedYear = year;
}

// ── Public API (unchanged signatures) ───────────────────────────────────

/**
 * Check if a given date is a US market holiday.
 * @param {Date} [now] — date to check (defaults to current time)
 * @returns {boolean} true if the market is closed for a holiday
 */
export function isMarketHoliday(now = new Date()) {
  const etStr = now.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
  const year = parseInt(etStr.slice(0, 4), 10);
  ensureCache(year);
  return _holidaySet.has(etStr);
}

/**
 * Check if today is a market trading day (not weekend, not holiday).
 * @param {Date} [now] — date to check
 * @returns {boolean} true if the market should be open today
 */
export function isTradingDay(now = new Date()) {
  const dayET = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
  const day = dayET.getDay(); // 0=Sun, 6=Sat
  if (day === 0 || day === 6) return false;
  if (isMarketHoliday(now)) return false;
  return true;
}

/**
 * Get the holiday name if today is a holiday, or null.
 * @param {Date} [now]
 * @returns {string|null}
 */
export function getHolidayName(now = new Date()) {
  const etStr = now.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
  const year = parseInt(etStr.slice(0, 4), 10);
  ensureCache(year);
  return _holidayNames[etStr] ?? null;
}
