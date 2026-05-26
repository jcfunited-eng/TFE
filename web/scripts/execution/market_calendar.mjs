/**
 * web/scripts/execution/market_calendar.mjs
 * US stock market holiday calendar.
 *
 * NYSE/NASDAQ observed holidays. The market is CLOSED on these days.
 * No entries, no exits (except catastrophic), no sentinel audits.
 *
 * Holidays that fall on Saturday are observed Friday.
 * Holidays that fall on Sunday are observed Monday.
 *
 * Source: NYSE holiday calendar (nyse.com/markets/hours-calendars)
 */

// Holidays stored as "YYYY-MM-DD" strings for fast lookup.
// Covers 2026-2027. Extend annually.
const MARKET_HOLIDAYS = new Set([
  // 2026
  "2026-01-01", // New Year's Day
  "2026-01-19", // MLK Jr. Day
  "2026-02-16", // Presidents' Day
  "2026-04-03", // Good Friday
  "2026-05-25", // Memorial Day
  "2026-06-19", // Juneteenth
  "2026-07-03", // Independence Day (observed — July 4 is Saturday)
  "2026-09-07", // Labor Day
  "2026-11-26", // Thanksgiving
  "2026-12-25", // Christmas

  // 2027
  "2027-01-01", // New Year's Day
  "2027-01-18", // MLK Jr. Day
  "2027-02-15", // Presidents' Day
  "2027-03-26", // Good Friday
  "2027-05-31", // Memorial Day
  "2027-06-18", // Juneteenth (observed — June 19 is Saturday)
  "2027-07-05", // Independence Day (observed — July 4 is Sunday)
  "2027-09-06", // Labor Day
  "2027-11-25", // Thanksgiving
  "2027-12-24", // Christmas (observed — Dec 25 is Saturday)
]);

/**
 * Check if a given date is a US market holiday.
 * @param {Date} [now] — date to check (defaults to current time)
 * @returns {boolean} true if the market is closed for a holiday
 */
export function isMarketHoliday(now = new Date()) {
  // Format as YYYY-MM-DD in US Eastern time (UTC-5 or UTC-4 DST)
  // Use UTC and offset manually since Intl may not be available in all envs
  const eastern = new Date(now.getTime() - 5 * 60 * 60 * 1000); // approximate EST
  // Better: use the actual date in ET
  const etStr = now.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
  return MARKET_HOLIDAYS.has(etStr);
}

/**
 * Check if today is a market trading day (not weekend, not holiday).
 * @param {Date} [now] — date to check
 * @returns {boolean} true if the market should be open today
 */
export function isTradingDay(now = new Date()) {
  // Get day of week in Eastern time
  const etDay = parseInt(
    new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", weekday: "narrow" })
      .formatToParts(now)
      .find(p => p.type === "weekday")?.value ?? "0",
    10
  );
  // Simpler: just get the day directly
  const dayET = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
  const day = dayET.getDay(); // 0=Sun, 6=Sat

  if (day === 0 || day === 6) return false; // weekend
  if (isMarketHoliday(now)) return false;   // holiday
  return true;
}

/**
 * Get the holiday name if today is a holiday, or null.
 * @param {Date} [now]
 * @returns {string|null}
 */
export function getHolidayName(now = new Date()) {
  const etStr = now.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
  const names = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "MLK Jr. Day",
    "2026-02-16": "Presidents' Day",
    "2026-04-03": "Good Friday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-11-26": "Thanksgiving",
    "2026-12-25": "Christmas",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "MLK Jr. Day",
    "2027-02-15": "Presidents' Day",
    "2027-03-26": "Good Friday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth (observed)",
    "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day",
    "2027-11-25": "Thanksgiving",
    "2027-12-24": "Christmas (observed)",
  };
  return names[etStr] ?? null;
}
