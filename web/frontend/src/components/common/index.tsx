import { useEffect, useState, type ReactNode } from "react";
import {
  alpha, Box, Button, Card, CardContent, CircularProgress, Dialog, DialogActions,
  DialogContent, DialogTitle, InputAdornment, Skeleton, Stack, TextField,
  Typography, type ButtonProps,
} from "@mui/material";
import InboxRoundedIcon from "@mui/icons-material/InboxRounded";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";

export { DrawerShell } from "./DrawerShell";
export {
  TintChip, AttendanceChip, VerdictChip, PenChip, PhaseChip,
  MetaChip, ColorDot, StatusSquare,
} from "./chips";

/**
 * The system's one "primary CTA" button — a pill with a soft brand-tinted glow.
 * Used for every top-level action in a page header so they read as one pattern,
 * distinct from ordinary contained buttons.
 */
export function PrimaryButton({ sx, ...props }: ButtonProps) {
  return (
    <Button
      variant="contained"
      {...props}
      sx={[
        {
          borderRadius: 99,
          px: 2.5,
          fontWeight: 700,
          boxShadow: (t) => `0 4px 12px ${alpha(t.palette.primary.main, 0.32)}`,
          "&:hover": { boxShadow: (t) => `0 6px 16px ${alpha(t.palette.primary.main, 0.4)}` },
        },
        ...(Array.isArray(sx) ? sx : [sx]),
      ]}
    />
  );
}

export function PageHeader({ title, subtitle, actions }: {
  title: string; subtitle?: string; actions?: ReactNode;
}) {
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      justifyContent="space-between"
      alignItems={{ xs: "flex-start", sm: "center" }}
      spacing={1.5}
      sx={{ mb: 3 }}
    >
      <Box>
        <Typography variant="h5">{title}</Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>{subtitle}</Typography>
        )}
      </Box>
      {actions && <Stack direction="row" spacing={1}>{actions}</Stack>}
    </Stack>
  );
}

export function EmptyState({ message, hint, action }: { message: string; hint?: string; action?: ReactNode }) {
  return (
    <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
      <InboxRoundedIcon sx={{ fontSize: 44, mb: 1, opacity: 0.5 }} />
      <Typography variant="body1" sx={{ mb: hint ? 0.5 : action ? 2 : 0 }}>{message}</Typography>
      {hint && <Typography variant="body2" sx={{ mb: action ? 2 : 0, opacity: 0.85 }}>{hint}</Typography>}
      {action}
    </Box>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : String(error ?? "Something went wrong");
  return (
    <Box sx={{ textAlign: "center", py: 8, color: "text.secondary" }}>
      <ErrorOutlineRoundedIcon color="error" sx={{ fontSize: 44, mb: 1, opacity: 0.8 }} />
      <Typography variant="body1" sx={{ mb: 0.5 }}>Could not load this view</Typography>
      <Typography variant="body2" sx={{ mb: onRetry ? 2 : 0, opacity: 0.85 }}>{message}</Typography>
      {onRetry && <Button variant="outlined" size="small" onClick={onRetry}>Try again</Button>}
    </Box>
  );
}

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Box sx={{ p: 2 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} height={44} sx={{ my: 0.5 }} />
      ))}
    </Box>
  );
}

export function ConfirmDialog({ open, title, message, confirmLabel = "Delete", onConfirm, onClose, loading }: {
  open: boolean; title: string; message: string; confirmLabel?: string;
  onConfirm: () => void; onClose: () => void; loading?: boolean;
}) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary">{message}</Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} disabled={loading}>Cancel</Button>
        <Button
          color="error"
          variant="contained"
          onClick={onConfirm}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={14} color="inherit" /> : undefined}
        >
          {confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

/** Search input that only reports upward after the user stops typing. */
export function DebouncedSearchInput({ value, onChange, placeholder = "Search…", width = 260, delay = 250 }: {
  value: string; onChange: (v: string) => void; placeholder?: string; width?: number; delay?: number;
}) {
  const [local, setLocal] = useState(value);
  useEffect(() => setLocal(value), [value]);
  useEffect(() => {
    const timer = setTimeout(() => { if (local !== value) onChange(local); }, delay);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [local, delay]);

  return (
    <TextField
      value={local}
      onChange={(e) => setLocal(e.target.value)}
      placeholder={placeholder}
      sx={{ width }}
      slotProps={{
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <SearchRoundedIcon sx={{ fontSize: 18 }} />
            </InputAdornment>
          ),
        },
      }}
    />
  );
}

/**
 * A headline number with its label and an accent glyph.
 *
 * The value is a number, not a gauge or a donut: a proportion is read faster
 * from a figure than from an angle, and the tile stays legible at any width.
 */
export function StatTile({ title, value, unit, icon, color, loading, hint, onClick }: {
  title: string;
  value: ReactNode;
  unit?: string;
  icon: ReactNode;
  color: string;
  loading?: boolean;
  hint?: string;
  onClick?: () => void;
}) {
  return (
    <Card
      onClick={onClick}
      sx={{
        flex: "1 1 190px",
        minWidth: 170,
        cursor: onClick ? "pointer" : "default",
        transition: "transform .15s ease",
        "&:hover": onClick ? { transform: "translateY(-2px)" } : undefined,
      }}
    >
      <CardContent>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box sx={{ minWidth: 0 }}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ fontWeight: 600, letterSpacing: "0.01em", display: "block", mb: 0.5 }}
            >
              {title}
            </Typography>
            {loading ? (
              <Skeleton width={64} height={40} />
            ) : (
              <Stack direction="row" alignItems="baseline" spacing={0.5}>
                <Typography variant="h3" sx={{ lineHeight: 1 }}>{value}</Typography>
                {unit && (
                  <Typography variant="subtitle2" color="text.secondary" sx={{ fontWeight: 700 }}>{unit}</Typography>
                )}
              </Stack>
            )}
            {hint && (
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.75 }}>
                {hint}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              color,
              display: "flex",
              p: 1,
              borderRadius: 2,
              bgcolor: (t) => alpha(color, t.palette.mode === "dark" ? 0.15 : 0.08),
            }}
          >
            {icon}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

/** Section heading used inside cards and drawers. */
export function SectionLabel({ children, sx }: { children: ReactNode; sx?: object }) {
  return (
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", display: "block", mb: 1, ...sx }}
    >
      {children}
    </Typography>
  );
}

/** A label/value pair, the layout every detail panel uses. */
export function FieldRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2} sx={{ py: 0.75 }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Box sx={{ textAlign: "right", minWidth: 0 }}>
        {typeof value === "string" || typeof value === "number"
          ? <Typography variant="body2" sx={{ fontWeight: 600 }}>{value}</Typography>
          : value}
      </Box>
    </Stack>
  );
}
