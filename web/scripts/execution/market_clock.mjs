/**
 * One deterministic New York market clock.
 *
 * Civil market times are expressed in America/New_York. Intl performs the
 * IANA time-zone conversion, so the same 09:30 boundary is correct in both
 * EST and EDT without maintaining a UTC-offset table.
 */

export const EASTERN_TIME_ZONE = "America/New_York";
export const REGULAR_OPEN_MINUTE_ET = 9 * 60 + 30;
export const REGULAR_CLOSE_MINUTE_ET = 16 * 60;
export const DAEMON_START_MINUTE_ET = 9 * 60;
export const DAEMON_END_MINUTE_ET = 16 * 60 + 30;
export const DAILY_ENTRY_START_MINUTE_ET = 9 * 60 + 45;
export const DAILY_ENTRY_END_MINUTE_ET = 10 * 60 + 15;
export const CH3_REARM_END_MINUTE_ET = 14 * 60;
export const CH3_EOD_CLOSE_MINUTE_ET = 15 * 60 + 30;

const formatter = new Intl.DateTimeFormat("en-US", {
  timeZone: EASTERN_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  weekday: "short",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

function integerPart(parts, type) {
  const value = Number(parts.find((part) => part.type === type)?.value);
  if (!Number.isInteger(value)) throw new Error(`Eastern clock did not provide ${type}`);
  return value;
}

export function easternClock(now = new Date()) {
  if (!(now instanceof Date) || !Number.isFinite(now.getTime())) {
    throw new TypeError("market clock requires a valid Date");
  }
  const parts = formatter.formatToParts(now);
  const year = integerPart(parts, "year");
  const month = integerPart(parts, "month");
  const day = integerPart(parts, "day");
  const hour = integerPart(parts, "hour");
  const minute = integerPart(parts, "minute");
  const second = integerPart(parts, "second");
  const weekday = parts.find((part) => part.type === "weekday")?.value ?? "";
  return {
    year,
    month,
    day,
    hour,
    minute,
    second,
    weekday,
    minuteOfDay: hour * 60 + minute,
    dateKey: `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
  };
}

export function marketDateEastern(now = new Date()) {
  return easternClock(now).dateKey;
}

export function isDaemonMarketWindow(now = new Date()) {
  const minute = easternClock(now).minuteOfDay;
  return minute >= DAEMON_START_MINUTE_ET && minute <= DAEMON_END_MINUTE_ET;
}

export function isRegularMarketSession(now = new Date()) {
  const minute = easternClock(now).minuteOfDay;
  return minute >= REGULAR_OPEN_MINUTE_ET && minute <= REGULAR_CLOSE_MINUTE_ET;
}

export function isDailyEntryWindow(now = new Date()) {
  const minute = easternClock(now).minuteOfDay;
  return minute >= DAILY_ENTRY_START_MINUTE_ET && minute <= DAILY_ENTRY_END_MINUTE_ET;
}

export function isCh3RearmWindowEastern(now = new Date()) {
  const minute = easternClock(now).minuteOfDay;
  return minute > DAILY_ENTRY_END_MINUTE_ET && minute < CH3_REARM_END_MINUTE_ET;
}

export function isCh3EodCloseWindow(now = new Date()) {
  const minute = easternClock(now).minuteOfDay;
  return minute >= CH3_EOD_CLOSE_MINUTE_ET && minute <= REGULAR_CLOSE_MINUTE_ET;
}

export function regularSessionMinutesElapsed(now = new Date()) {
  return Math.max(1, Math.min(390, easternClock(now).minuteOfDay - REGULAR_OPEN_MINUTE_ET));
}
