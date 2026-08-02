import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { createAppTheme } from "./theme";
import { useUiStore } from "./store/useUiStore";
import { router } from "./router";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false, retry: 1, staleTime: 30_000 },
  },
});

function Root() {
  const mode = useUiStore((s) => s.mode);
  return (
    <ThemeProvider theme={createAppTheme(mode)}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ThemeProvider>
  );
}

/**
 * Vite re-executes this module on every hot update, and calling createRoot a
 * second time on the same container is an error. Caching the root on the
 * container makes a hot update re-render the existing tree instead.
 */
const container = document.getElementById("root")! as HTMLElement & {
  _reactRoot?: ReturnType<typeof createRoot>;
};
container._reactRoot ??= createRoot(container);
container._reactRoot.render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
