/** Formatting helpers shared by every page, so dates and numbers read alike. */

/**
 * A bare "YYYY-MM-DD" string is parsed by `new Date()` as UTC midnight, but
 * rendered by `toLocaleDateString()` in the browser's local zone - anyone
 * west of UTC would otherwise see every session date shifted back a day.
 * Build the Date from local components instead so the calendar day is the
 * one the server actually meant, regardless of the viewer's time zone.
 */
function parseCalendarDate(iso: string): Date {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, (month ?? 1) - 1, day ?? 1);
}

export function shortDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = parseCalendarDate(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

export function longDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = parseCalendarDate(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" });
}

export function dateTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

/** Ink coverage as a percentage — the measurement behind every decision. */
export function inkPercent(ratio: number, digits = 2): string {
  return `${(ratio * 100).toFixed(digits)}%`;
}

export function ms(value?: number | null): string {
  if (value == null) return "—";
  return value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${value.toFixed(0)} ms`;
}
