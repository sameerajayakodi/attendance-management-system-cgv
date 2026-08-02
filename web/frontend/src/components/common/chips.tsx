import { Box, Chip, useTheme, type ChipProps } from "@mui/material";
import type { ReactElement, ReactNode } from "react";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import { tintSx, mutedChipSx } from "../../theme";
import {
  ATTENDANCE_STATUS, VERIFY_VERDICT, METRIC, NEUTRAL, TONE,
  penColour, safeColor, stagePhase, type Tone,
} from "../../theme/tokens";
import type { AttendanceStatus } from "../../types";

/**
 * The app's chip family — the ONLY way to render chips, so size, weight and
 * tint stay identical everywhere. Two visual languages, one size each:
 *   • Tinted chips  → a live STATE (present/absent, verdict, pen). weight 600, solid.
 *   • MetaChip      → a LABEL / category / count. neutral badge.
 * Size always comes from the theme default (26px tall, 0.7rem).
 */

/* ── Status (solid fill, white label) ───────────────────────── */

/** Low-level status chip: any label + any token color (hex/rgb). */
export function TintChip({ color, muted, ...chip }:
  Omit<ChipProps, "color"> & { color: string; muted?: boolean }) {
  const theme = useTheme();
  return <Chip {...chip} sx={{ ...(muted ? mutedChipSx(theme) : tintSx(safeColor(color), theme)), ...chip.sx }} />;
}

/**
 * The system's central verdict: did this student sign?
 *
 * The glyph is not decoration — it is the second channel. Present and absent
 * are a green/red pair, which is exactly the pair red-green colour blindness
 * collapses, so the tick and cross carry the meaning on their own.
 */
export function AttendanceChip({ status, withIcon = true }: { status: AttendanceStatus; withIcon?: boolean }) {
  const m = ATTENDANCE_STATUS[status];
  const icon = status === "PRESENT"
    ? <CheckRoundedIcon sx={{ fontSize: 14 }} />
    : <CloseRoundedIcon sx={{ fontSize: 14 }} />;
  return <TintChip label={m.label} color={m.color} icon={withIcon ? icon : undefined} />;
}

/** Signature-verification outcome for one specimen. */
export function VerdictChip({ verdict }: { verdict: string }) {
  const m = VERIFY_VERDICT[verdict as keyof typeof VERIFY_VERDICT] ?? VERIFY_VERDICT.consistent;
  return <TintChip label={m.label} color={m.color} muted={verdict === "consistent"} />;
}

/**
 * The pen a signature was written with, as named by the HSV ink analysis.
 *
 * Absent rows carry no pen: whatever hue the analysis measured in an empty cell
 * came from residual noise, and showing it would imply a signature that is not
 * there.
 */
export function PenChip({ colour }: { colour?: string | null }) {
  if (!colour || colour === "none") return <MetaChip label="No ink" muted />;
  const m = penColour(colour);
  return <TintChip label={m.label} color={m.color} />;
}

/** Which phase of the pipeline a stage image belongs to. */
export function PhaseChip({ slug }: { slug: string }) {
  const m = stagePhase(slug);
  return <TintChip label={m.phase} color={m.color} />;
}

/* ── Meta (label) ───────────────────────────────────────────── */

/**
 * Label chip for categories, counts and designations.
 *
 * A TONED MetaChip is literally a TintChip — same solid fill, same white label —
 * so a colour never means two different things. An untoned one is a solid
 * neutral badge: same shape and weight, no hue, because a row of metadata must
 * stay quiet.
 */
export function MetaChip({ label, tone = "neutral", icon, muted, ...rest }:
  { label: ReactNode; tone?: Tone; icon?: ReactElement; muted?: boolean } &
  Omit<ChipProps, "label" | "icon" | "color" | "variant">) {
  const theme = useTheme();
  const color = TONE[tone];
  const dark = theme.palette.mode === "dark";
  return (
    <Chip
      {...rest}
      label={label}
      icon={icon}
      sx={{
        ...(muted
          ? mutedChipSx(theme)
          : color
          ? tintSx(color, theme)
          : {
              // Opaque, not an alpha wash — these sit on striped/hovered rows.
              backgroundColor: dark ? "#2a2a30" : "#eceef2",
              color: dark ? "#e4e4e7" : "#3f3f46",
              border: "1px solid transparent",
              fontWeight: 600,
              fontSize: METRIC.chipFontSize,
              letterSpacing: "0.01em",
              "& .MuiChip-icon": { color: dark ? "#a1a1aa" : "#71717a", fontSize: 13 },
            }),
        ...rest.sx,
      }}
    />
  );
}

/* ── Primitives ─────────────────────────────────────────────── */

/** Small colored dot (status indicator in dense rows and legends). */
export function ColorDot({ color, size = METRIC.dotSize }: { color?: string | null; size?: number }) {
  return (
    <Box sx={{ width: size, height: size, borderRadius: "50%", bgcolor: safeColor(color) ?? NEUTRAL, flexShrink: 0 }} />
  );
}

/**
 * One cell of the attendance matrix: a solid square carrying its own letter.
 *
 * The letter is the accessibility channel — the matrix is a wall of green and
 * red, and without it the whole figure would depend on hue alone.
 */
export function StatusSquare({ status, size = 34, title }:
  { status: AttendanceStatus; size?: number; title?: string }) {
  const theme = useTheme();
  const m = ATTENDANCE_STATUS[status];
  return (
    <Box
      title={title}
      sx={{
        width: size, height: size, borderRadius: 1.5, flexShrink: 0,
        display: "grid", placeItems: "center",
        bgcolor: tintSx(m.color, theme).backgroundColor,
        color: "#fff", fontWeight: 800, fontSize: size * 0.42,
      }}
    >
      {m.short}
    </Box>
  );
}
