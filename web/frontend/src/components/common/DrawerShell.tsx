import { Box, Drawer, IconButton, Stack, Typography } from "@mui/material";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import type { ReactNode } from "react";

/**
 * The right-side slide-over used for every create/edit/detail flow.
 *
 * Small centre-screen Dialogs are deliberately not used: a drawer keeps the
 * list behind it visible, gives a form room to breathe, and reads as production
 * software rather than a prompt.
 */
export function DrawerShell({
  open,
  title,
  subtitle,
  onClose,
  footer,
  children,
  width = { xs: "100%", sm: 460 },
}: {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  footer?: ReactNode;
  children: ReactNode;
  width?: object | number | string;
}) {
  return (
    <Drawer anchor="right" open={open} onClose={onClose} slotProps={{ paper: { sx: { width } } }}>
      <Stack sx={{ height: "100%" }}>
        <Stack
          direction="row"
          alignItems="flex-start"
          justifyContent="space-between"
          sx={{ px: 3, py: 2, borderBottom: "1px solid", borderColor: "divider" }}
        >
          <Box>
            <Typography variant="h6">{title}</Typography>
            {subtitle && (
              <Typography variant="caption" color="text.secondary">{subtitle}</Typography>
            )}
          </Box>
          <IconButton size="small" onClick={onClose} aria-label="Close">
            <CloseRoundedIcon fontSize="small" />
          </IconButton>
        </Stack>

        <Box sx={{ flex: 1, overflowY: "auto", px: 4, py: 3.5 }}>{children}</Box>

        {footer && (
          <Stack
            direction="row"
            spacing={1.5}
            justifyContent="flex-end"
            sx={{ px: 4, py: 3, borderTop: "1px solid", borderColor: "divider" }}
          >
            {footer}
          </Stack>
        )}
      </Stack>
    </Drawer>
  );
}
