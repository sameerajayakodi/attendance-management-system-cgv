import type { ReactElement } from "react";
import SpaceDashboardRoundedIcon from "@mui/icons-material/SpaceDashboardRounded";
import DocumentScannerRoundedIcon from "@mui/icons-material/DocumentScannerRounded";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import DrawRoundedIcon from "@mui/icons-material/DrawRounded";
import TuneRoundedIcon from "@mui/icons-material/TuneRounded";

export interface MenuItem {
  label: string;
  path: string;
  icon: ReactElement;
}

/** The navigation mirrors the three command-line programs, plus the pipeline. */
export const MENU: MenuItem[] = [
  { label: "Dashboard", path: "/", icon: <SpaceDashboardRoundedIcon fontSize="small" /> },
  { label: "Signing sheets", path: "/sessions", icon: <DocumentScannerRoundedIcon fontSize="small" /> },
  { label: "Students", path: "/students", icon: <GroupsRoundedIcon fontSize="small" /> },
  { label: "Signatures", path: "/signatures", icon: <DrawRoundedIcon fontSize="small" /> },
  { label: "Pipeline", path: "/pipeline", icon: <TuneRoundedIcon fontSize="small" /> },
];
