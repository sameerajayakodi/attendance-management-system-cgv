import {
  Box, Divider, Drawer, IconButton, List, ListItemButton, ListItemIcon,
  ListItemText, Stack, Tooltip, Typography, useMediaQuery, useTheme,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import DarkModeRoundedIcon from "@mui/icons-material/DarkModeRounded";
import LightModeRoundedIcon from "@mui/icons-material/LightModeRounded";
import DocumentScannerRoundedIcon from "@mui/icons-material/DocumentScannerRounded";
import { useState } from "react";
import { MENU } from "./menu";
import { useUiStore } from "../store/useUiStore";
import { BRAND_GRADIENT } from "../theme/tokens";

const EXPANDED = 262;
const COLLAPSED = 68;

function Brand({ expanded }: { expanded: boolean }) {
  return (
    <Stack direction="row" alignItems="center" spacing={1.5} sx={{ px: expanded ? 2.5 : 1.5, py: 2.25 }}>
      <Box
        sx={{
          width: 34, height: 34, borderRadius: 2.5, flexShrink: 0,
          display: "grid", placeItems: "center",
          background: BRAND_GRADIENT, color: "#fff",
        }}
      >
        <DocumentScannerRoundedIcon sx={{ fontSize: 19 }} />
      </Box>
      {expanded && (
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle2" sx={{ lineHeight: 1.15 }}>SAMS</Typography>
          <Typography variant="caption" color="text.secondary" noWrap>
            Attendance from signing sheets
          </Typography>
        </Box>
      )}
    </Stack>
  );
}

function SidebarMenu({ expanded, onNavigate }: { expanded: boolean; onNavigate?: () => void }) {
  const { pathname } = useLocation();

  return (
    <List sx={{ px: expanded ? 1.25 : 0.75, py: 0 }}>
      {MENU.map((item) => {
        const selected = item.path === "/"
          ? pathname === "/"
          : pathname === item.path || pathname.startsWith(`${item.path}/`);
        const button = (
          <ListItemButton
            key={item.path}
            component={NavLink}
            to={item.path}
            onClick={onNavigate}
            selected={selected}
            sx={{
              mb: 0.5,
              minHeight: 40,
              justifyContent: expanded ? "flex-start" : "center",
              px: expanded ? 1.5 : 1,
              "&.Mui-selected": {
                bgcolor: (t) => alpha(t.palette.primary.main, t.palette.mode === "dark" ? 0.16 : 0.1),
                color: "primary.dark",
                "& .MuiListItemIcon-root": { color: "primary.dark" },
                "&:hover": {
                  bgcolor: (t) => alpha(t.palette.primary.main, t.palette.mode === "dark" ? 0.22 : 0.14),
                },
              },
            }}
          >
            <ListItemIcon sx={{ minWidth: expanded ? 34 : 0, color: "text.secondary" }}>
              {item.icon}
            </ListItemIcon>
            {expanded && (
              <ListItemText
                primary={item.label}
                slotProps={{ primary: { fontSize: "0.85rem", fontWeight: selected ? 700 : 500 } }}
              />
            )}
          </ListItemButton>
        );
        return expanded ? button : (
          <Tooltip key={item.path} title={item.label} placement="right">
            <span>{button}</span>
          </Tooltip>
        );
      })}
    </List>
  );
}

export default function AppLayout() {
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));
  const { mode, sidebarExpanded, toggleMode, toggleSidebar } = useUiStore();
  const [mobileOpen, setMobileOpen] = useState(false);

  const expanded = isDesktop ? sidebarExpanded : true;
  const width = isDesktop ? (sidebarExpanded ? EXPANDED : COLLAPSED) : EXPANDED;

  const content = (
    <Stack sx={{ height: "100%" }}>
      <Brand expanded={expanded} />
      <Divider />
      <Box sx={{ flex: 1, overflowY: "auto", py: 1.5 }}>
        <SidebarMenu expanded={expanded} onNavigate={() => setMobileOpen(false)} />
      </Box>
      <Divider />
      <Stack
        direction={expanded ? "row" : "column"}
        alignItems="center"
        justifyContent="space-between"
        spacing={1}
        sx={{ px: expanded ? 2 : 1, py: 1.5 }}
      >
        {expanded && (
          <Typography variant="caption" color="text.secondary" noWrap>
            CS402.3 · Prototype
          </Typography>
        )}
        <Stack direction={expanded ? "row" : "column"} spacing={0.5}>
          <Tooltip title={mode === "light" ? "Dark mode" : "Light mode"}>
            <IconButton size="small" onClick={toggleMode}>
              {mode === "light"
                ? <DarkModeRoundedIcon sx={{ fontSize: 18 }} />
                : <LightModeRoundedIcon sx={{ fontSize: 18 }} />}
            </IconButton>
          </Tooltip>
          {isDesktop && (
            <Tooltip title={sidebarExpanded ? "Collapse" : "Expand"}>
              <IconButton size="small" onClick={toggleSidebar}>
                <MenuRoundedIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Tooltip>
          )}
        </Stack>
      </Stack>
    </Stack>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Drawer
        variant={isDesktop ? "permanent" : "temporary"}
        open={isDesktop ? true : mobileOpen}
        onClose={() => setMobileOpen(false)}
        sx={{
          width: isDesktop ? width : 0,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width,
            boxSizing: "border-box",
            transition: "width .18s ease",
            overflowX: "hidden",
          },
        }}
      >
        {content}
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, px: { xs: 2, md: 4 }, py: { xs: 2.5, md: 3.5 } }}>
        {!isDesktop && (
          <IconButton onClick={() => setMobileOpen(true)} sx={{ mb: 1.5 }} aria-label="Open navigation">
            <MenuRoundedIcon />
          </IconButton>
        )}
        <Box sx={{ animation: "fadeInUp .22s ease" }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
