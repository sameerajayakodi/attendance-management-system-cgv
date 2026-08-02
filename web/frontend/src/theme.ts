import { createTheme, darken, lighten, type Theme } from "@mui/material/styles";
import { BRAND, SEMANTIC, FONT_SANS, FONT_MONO, BRAND_GRADIENT, METRIC, safeColor } from "./theme/tokens";

// Re-exported so pages can import either from "../theme" or "../theme/tokens".
export { FONT_SANS, FONT_MONO, BRAND_GRADIENT };

/**
 * App theme — the single place that decides how controls LOOK.
 * Design language: flat unified surfaces, compact controls, badge-style chips,
 * black/white primary buttons, emerald brand accents.
 *
 * Sizing contract (do not override per-page):
 *  - TextField/Select/Table/Chip/Switch default to "small"
 *  - radius: controls 10 · cards 14 · dialogs 16 · buttons 6
 *  - table row: 0.84rem / header 0.75rem
 */
export function createAppTheme(mode: "light" | "dark"): Theme {
  const dark = mode === "dark";
  const border = dark ? "rgba(255,255,255,0.08)" : "rgba(15,23,42,0.08)";

  // Unified background — paper and default share the same color.
  const bgDefault = dark ? "#000000" : "#ffffff";
  const bgSurface = dark ? "#121214" : "#f8f9fb";

  return createTheme({
    palette: {
      mode,
      primary: { main: BRAND.primary, dark: BRAND.primaryDark, light: BRAND.primaryLight },
      secondary: { main: dark ? "#ffffff" : "#000000" },
      success: { main: SEMANTIC.success },
      warning: { main: SEMANTIC.warning },
      error: { main: SEMANTIC.error },
      info: { main: SEMANTIC.info },
      background: { default: bgDefault, paper: bgDefault },
      text: dark
        ? { primary: "#f4f4f5", secondary: "#a1a1aa" }
        : { primary: "#18181b", secondary: "#71717a" },
      divider: border,
    },
    typography: {
      fontFamily: FONT_SANS,
      h3: { fontWeight: 800, fontSize: "2rem", letterSpacing: "-0.03em" },
      h4: { fontWeight: 800, fontSize: "1.65rem", letterSpacing: "-0.03em" },
      h5: { fontWeight: 700, fontSize: "1.3rem", letterSpacing: "-0.02em" },
      h6: { fontWeight: 700, fontSize: "1rem", letterSpacing: "-0.01em" },
      subtitle2: { fontWeight: 700, fontSize: "0.82rem" },
      body1: { fontSize: "0.88rem" },
      body2: { fontSize: "0.82rem" },
      caption: { fontSize: "0.72rem" },
      button: { textTransform: "none", fontWeight: 600, fontSize: "0.82rem" },
      overline: { fontWeight: 600, letterSpacing: "0.01em", textTransform: "none" },
    },
    shape: { borderRadius: 10 },
    components: {
      MuiCssBaseline: {
        styleOverrides: `
          ::-webkit-scrollbar { width: 5px; height: 5px; }
          ::-webkit-scrollbar-track { background: transparent; }
          ::-webkit-scrollbar-thumb { background: ${dark ? "rgba(148,163,184,0.25)" : "rgba(15,23,42,0.10)"}; border-radius: 99px; }
          ::-webkit-scrollbar-thumb:hover { background: ${dark ? "rgba(148,163,184,0.4)" : "rgba(15,23,42,0.18)"}; }
          ::selection { background: rgba(59,130,246,0.25); }
          @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `,
      },
      MuiPaper: {
        styleOverrides: {
          root: { backgroundImage: "none" },
          outlined: { borderRadius: METRIC.radiusCard, borderColor: border },
        },
      },
      // Cards are flat — no border, no shadow, unified with background.
      MuiCard: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            border: "none",
            borderRadius: METRIC.radiusCard,
            boxShadow: "none",
            backgroundColor: bgSurface,
          },
        },
      },
      MuiCardContent: {
        styleOverrides: { root: { padding: 18, "&:last-child": { paddingBottom: 18 } } },
      },
      // ── Compact controls everywhere by default ──
      MuiTextField: { defaultProps: { size: "small" } },
      MuiFormControl: { defaultProps: { size: "small" } },
      MuiSelect: { defaultProps: { size: "small" } },
      MuiSwitch: { defaultProps: { size: "small" } },
      MuiCheckbox: { defaultProps: { size: "small" } },
      MuiRadio: { defaultProps: { size: "small" } },
      MuiTable: { defaultProps: { size: "small" } },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 10,
            fontSize: "0.85rem",
            transition: "box-shadow .15s ease, border-color .15s ease",
            "&.Mui-focused .MuiInputAdornment-root .MuiSvgIcon-root": { color: BRAND.primary },
          },
        },
      },
      MuiInputLabel: { styleOverrides: { root: { fontSize: "0.85rem" } } },
      MuiMenuItem: {
        styleOverrides: { root: { fontSize: "0.85rem", borderRadius: 8, marginInline: 4, minHeight: 34 } },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 6, paddingInline: 18, paddingBlock: 6, textTransform: "none", fontWeight: 600 },
          sizeSmall: { paddingInline: 12, paddingBlock: 4, fontSize: "0.78rem" },
          sizeLarge: { paddingBlock: 9, fontSize: "0.9rem" },
          // Signature look: contained buttons are black (light) or white (dark) —
          // the brand emerald stays for accents, not CTAs.
          containedPrimary: {
            backgroundColor: dark ? "#f4f4f5" : "#18181b",
            color: dark ? "#000000" : "#ffffff",
            "&:hover": { backgroundColor: dark ? "rgba(244,244,245,0.9)" : "rgba(24,24,27,0.9)" },
            "&.Mui-disabled": {
              backgroundColor: dark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)",
              color: dark ? "rgba(255,255,255,0.3)" : "rgba(0,0,0,0.3)",
            },
          },
          containedSecondary: {
            backgroundColor: dark ? "#f4f4f5" : "#18181b",
            color: dark ? "#000000" : "#ffffff",
            "&:hover": { backgroundColor: dark ? "rgba(244,244,245,0.9)" : "rgba(24,24,27,0.9)" },
          },
        },
      },
      MuiIconButton: { styleOverrides: { root: { borderRadius: 10 } } },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontSize: "0.75rem",
            fontWeight: 600,
            letterSpacing: "0.01em",
            color: dark ? "#94a3b8" : "#64748b",
            whiteSpace: "nowrap",
            padding: "10px 16px",
            borderBottom: `2px solid ${border}`,
          },
          root: { fontSize: "0.84rem", padding: "9px 16px", borderBottom: `1px solid ${border}` },
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: {
            transition: "background .15s ease",
            "&.MuiTableRow-hover:hover": { backgroundColor: "rgba(59,130,246,0.04)" },
          },
        },
      },
      MuiChip: {
        defaultProps: { size: "small" },
        styleOverrides: {
          root: { fontWeight: 600, borderRadius: 100 },
          sizeSmall: { height: 26, fontSize: METRIC.chipFontSize },
          label: { paddingInline: 11 },
        },
      },
      MuiDialog: { styleOverrides: { paper: { borderRadius: METRIC.radiusDialog, backgroundImage: "none" } } },
      MuiDialogTitle: { styleOverrides: { root: { fontSize: "1.05rem", fontWeight: 700 } } },
      MuiDrawer: {
        styleOverrides: { paper: { borderRight: `1px solid ${border}`, backgroundColor: bgDefault } },
      },
      MuiListItemButton: { styleOverrides: { root: { borderRadius: 10 } } },
      MuiTab: {
        styleOverrides: { root: { textTransform: "none", fontWeight: 600, fontSize: "0.84rem", minHeight: 42 } },
      },
      MuiTabs: {
        styleOverrides: {
          root: { minHeight: 42 },
          indicator: { height: 3, borderRadius: 3, background: BRAND_GRADIENT },
        },
      },
      MuiDivider: { styleOverrides: { root: { borderColor: border } } },
      MuiAlert: { styleOverrides: { root: { borderRadius: 10, fontSize: "0.82rem" } } },
      MuiTooltip: { defaultProps: { arrow: true } },
      MuiSkeleton: { defaultProps: { animation: "wave" } },
      MuiAvatar: { styleOverrides: { root: { fontWeight: 700 } } },
      MuiLinearProgress: { styleOverrides: { root: { borderRadius: 99, height: 6 } } },
    },
  });
}

/**
 * The ONE status-chip formula. Every status-like chip in the app must use this
 * (directly or via components/common/chips.tsx) so chips stay identical.
 *
 * The fill is SOLID — an opaque deep step of the token hue, with white text.
 * Two things make that read as enterprise rather than toy: the fill is stepped
 * down from the raw hue (a raw #10b981 behind white text is both neon AND fails
 * contrast), and the label is compact. Alpha tints are deliberately not used —
 * over striped table rows and hover states a translucent chip shifts color with
 * whatever is behind it.
 *
 * Charts still render the raw hue — there, color IS the data channel.
 */
export function tintSx(color: string | undefined | null, theme: Theme) {
  const c = safeColor(color);
  const dark = theme.palette.mode === "dark";
  // Stepped so white text clears ~4.5:1 on every token hue, amber included.
  const fill = darken(c, dark ? 0.24 : 0.3);
  return {
    backgroundColor: fill,
    color: "#fff",
    border: "1px solid transparent",
    fontWeight: 600,
    fontSize: METRIC.chipFontSize,
    letterSpacing: "0.01em",
    "& .MuiChip-icon": { color: "#fff", fontSize: 13 },
    "& .MuiChip-deleteIcon": { color: "rgba(255,255,255,0.65)", "&:hover": { color: "#fff" } },
  };
}

/**
 * The DEAD-STATE chip: not applicable, skipped, no data.
 *
 * Deliberately hollow and hueless. Every live chip is a solid fill, so a state
 * that no longer applies must not compete with them.
 */
export function mutedChipSx(theme: Theme) {
  const dark = theme.palette.mode === "dark";
  const fg = dark ? "#8b8b93" : "#9ca0a8";
  return {
    backgroundColor: "transparent",
    color: fg,
    border: `1px solid ${dark ? "rgba(255,255,255,0.14)" : "rgba(15,23,42,0.14)"}`,
    fontWeight: 500,
    fontSize: METRIC.chipFontSize,
    letterSpacing: "0.01em",
    "& .MuiChip-icon": { color: fg, fontSize: 13 },
  };
}

/**
 * A token hue stepped to readable "ink" for the current mode. Used where a hue
 * must carry meaning as TEXT rather than as a fill, so those never disagree
 * with each other on what a colour means.
 */
export function chipInk(color: string | undefined | null, theme: Theme) {
  const c = safeColor(color);
  return theme.palette.mode === "dark" ? lighten(c, 0.34) : darken(c, 0.34);
}
