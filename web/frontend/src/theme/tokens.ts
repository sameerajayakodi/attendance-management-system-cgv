/**
 * Design tokens — the single source of truth for every color, size and metric
 * used outside the MUI theme itself.
 *
 * Ported from the LeadFlow design system so both products share one visual
 * language; the domain maps below are SAMS's own (attendance status, pipeline
 * stages, pen colours, signature verdicts).
 *
 * RULES
 *  - Pages and components NEVER hard-code hex colors: import from here.
 *  - Anything status-like renders through the chips in components/common/chips.tsx.
 *  - Fonts, radii and control sizing come from the theme (src/theme.ts), which
 *    also consumes these tokens.
 */

/* ── Typography ─────────────────────────────────────────────── */
export const FONT_SANS = "'Plus Jakarta Sans', system-ui, -apple-system, sans-serif";
export const FONT_MONO = "'JetBrains Mono', 'SFMono-Regular', monospace";

/* ── Brand ──────────────────────────────────────────────────── */
export const BRAND = {
  primary: "#10b981",
  primaryDark: "#059669",
  primaryLight: "#34d399",
} as const;

/** Solid brand color used for the logo block / tab indicator. */
export const BRAND_GRADIENT = BRAND.primaryDark;

/* ── Semantic colors (match the MUI palette exactly) ────────── */
export const SEMANTIC = {
  success: "#10b981",
  warning: "#f59e0b",
  error: "#ef4444",
  info: "#0ea5e9",
} as const;

/* ── Accent scale — decorative/categorical colors ───────────── */
export const ACCENT = {
  blue: "#3b82f6",
  sky: "#0ea5e9",
  indigo: "#6366f1",
  violet: "#8b5cf6",
  teal: "#14b8a6",
  green: "#22c55e",
  amber: "#f59e0b",
  red: "#ef4444",
  pink: "#ec4899",
  orange: "#f97316",
  slate: "#64748b",
} as const;

/** Fallback for anything colored that lost its color. */
export const NEUTRAL = ACCENT.slate;

/* ── Charts (recharts categorical series) ───────────────────── */

/**
 * The categorical series order. Hues are assigned in THIS order and never
 * cycled — a 9th series folds into "Other" rather than repeating a color.
 *
 * The order is not cosmetic: it was chosen so that every ADJACENT pair stays
 * distinguishable under protanopia/deuteranopia/tritanopia (worst adjacent CVD
 * ΔE 12.8 light / 12.0 dark, against an 8.0 target). Reordering these without
 * re-validating will quietly break colorblind readers.
 */
export const CHART_PALETTE: readonly string[] = [
  ACCENT.indigo, ACCENT.amber, ACCENT.teal, ACCENT.red,
  ACCENT.sky, ACCENT.orange, ACCENT.violet, ACCENT.green,
];

export const CHART_PALETTE_DARK: readonly string[] = [
  "#6366f1", "#d97706", "#0d9488", "#ef4444",
  "#0284c7", "#ea580c", "#8b5cf6", "#16a34a",
];

export function chartPalette(mode: "light" | "dark"): readonly string[] {
  return mode === "dark" ? CHART_PALETTE_DARK : CHART_PALETTE;
}

/**
 * Color for series `i`, by the entity's fixed position — never by its rank in
 * the current result set, so filtering a series out doesn't repaint the rest.
 */
export function seriesColor(i: number, mode: "light" | "dark" = "light"): string {
  const p = chartPalette(mode);
  return p[i % p.length];
}

/** Named series roles so the same measure is always the same color. */
export const CHART = {
  primarySeries: ACCENT.indigo,
  presentSeries: SEMANTIC.success,
  absentSeries: SEMANTIC.error,
  areaSeries: ACCENT.indigo,
  thresholdLine: ACCENT.slate,
} as const;

/** Sequential ramp for the similarity heat map — one hue, light to dark. */
export const SEQUENTIAL_BLUE: readonly string[] = [
  "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b",
];

/* ── Domain color maps ──────────────────────────────────────── */

/** Whether a student signed the sheet. The system's central verdict. */
export const ATTENDANCE_STATUS: Record<"PRESENT" | "ABSENT", { label: string; short: string; color: string }> = {
  PRESENT: { label: "Present", short: "P", color: SEMANTIC.success },
  ABSENT: { label: "Absent", short: "A", color: SEMANTIC.error },
};

/** Signature-verification outcome for one specimen. */
export const VERIFY_VERDICT: Record<"consistent" | "MISMATCH", { label: string; color: string }> = {
  consistent: { label: "Consistent", color: SEMANTIC.success },
  MISMATCH: { label: "Mismatch", color: SEMANTIC.warning },
};

/** The pen a signature was written with, as reported by the HSV ink analysis. */
export const PEN_COLOUR: Record<string, { label: string; color: string }> = {
  blue: { label: "Blue", color: ACCENT.blue },
  black: { label: "Black", color: "#334155" },
  red: { label: "Red", color: ACCENT.red },
  green: { label: "Green", color: ACCENT.green },
  dark: { label: "Dark", color: ACCENT.slate },
  none: { label: "No ink", color: ACCENT.slate },
};
export function penColour(name?: string | null) {
  return PEN_COLOUR[(name ?? "none").toLowerCase()] ?? PEN_COLOUR.none;
}

/**
 * The nine pipeline stages, coloured by the kind of work each does, so the
 * stage gallery reads as four phases rather than nine unrelated pictures.
 */
export const STAGE_PHASE: Record<string, { phase: string; color: string }> = {
  "01_acquisition": { phase: "Acquisition", color: ACCENT.slate },
  "02_greyscale": { phase: "Photometric", color: ACCENT.indigo },
  "03_illumination_correction": { phase: "Photometric", color: ACCENT.indigo },
  "04_edge-preserving_denoise": { phase: "Photometric", color: ACCENT.indigo },
  "05_binarisation": { phase: "Photometric", color: ACCENT.indigo },
  "06_skew_correction": { phase: "Geometry", color: ACCENT.violet },
  "07_rule_extraction": { phase: "Structure", color: ACCENT.teal },
  "08_table_reconstruction": { phase: "Structure", color: ACCENT.teal },
  "09_signature_analysis": { phase: "Decision", color: SEMANTIC.success },
};
export function stagePhase(slug: string) {
  return STAGE_PHASE[slug] ?? { phase: "Stage", color: NEUTRAL };
}

/** Semantic tone → token color (shared by MetaChip). */
export const TONE = {
  neutral: undefined as string | undefined,
  brand: BRAND.primary,
  success: SEMANTIC.success,
  warning: SEMANTIC.warning,
  error: SEMANTIC.error,
  info: SEMANTIC.info,
} as const;
export type Tone = keyof typeof TONE;

/**
 * Deterministic avatar background from a display name.
 *
 * Deliberately NOT the ACCENT steps: an avatar is a solid fill behind white
 * initials, so it needs deep, low-chroma tones that clear contrast on white
 * text. The bright accent steps fail that and read as toy stickers.
 */
export const AVATAR_COLORS: readonly string[] = [
  "#3f4c63", "#1d4ed8", "#0f766e", "#6d28d9", "#15803d", "#b45309", "#9f1239",
];
export function avatarColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length];
}

/** Up to two initials from a display name, for avatar circles. */
export function initials(name: string): string {
  return name.split(" ").filter(Boolean).map((w) => w[0]).join("").toUpperCase().slice(0, 2);
}

/* ── Guards ─────────────────────────────────────────────────── */

/** A color safe to pass to MUI alpha() — guards legacy palette-name strings. */
export function safeColor(c?: string | null): string {
  return c && /^(#|rgb)/i.test(c) ? c : NEUTRAL;
}

/* ── Metrics ────────────────────────────────────────────────── */
export const METRIC = {
  /** Chip label size used by every tinted status chip. */
  chipFontSize: "0.7rem",
  /** Radius scale: controls 10 (theme.shape), cards 14, dialogs 16, chips pill. */
  radiusCard: 14,
  radiusDialog: 16,
  /** Status/color dots. */
  dotSize: 8,
  /** Attendance requirement drawn as a reference line on every rate chart. */
  requiredRate: 80,
} as const;
