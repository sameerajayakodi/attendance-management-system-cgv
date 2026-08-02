import { create } from "zustand";
import { persist } from "zustand/middleware";

type Mode = "light" | "dark";

interface UiState {
  mode: Mode;
  sidebarExpanded: boolean;
  toggleMode: () => void;
  toggleSidebar: () => void;
}

/** Colour mode and sidebar width survive a reload — both are user preferences. */
export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      mode: "light",
      sidebarExpanded: true,
      toggleMode: () => set((s) => ({ mode: s.mode === "light" ? "dark" : "light" })),
      toggleSidebar: () => set((s) => ({ sidebarExpanded: !s.sidebarExpanded })),
    }),
    { name: "sams-ui" },
  ),
);
