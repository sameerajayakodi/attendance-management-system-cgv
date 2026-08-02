import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import AppLayout from "./layout/AppLayout";

/**
 * Routes are loaded on demand.
 *
 * The dashboard needs recharts and the session view needs nothing but images —
 * bundling them together made every visitor download the charting library
 * before the first paint. Splitting per route keeps the initial payload to the
 * shell and the page actually being visited.
 */
const DashboardPage = lazy(() => import("./pages/dashboard/DashboardPage"));
const SessionsPage = lazy(() => import("./pages/sessions/SessionsPage"));
const SessionDetailPage = lazy(() => import("./pages/sessions/SessionDetailPage"));
const StudentsPage = lazy(() => import("./pages/students/StudentsPage"));
const StudentDetailPage = lazy(() => import("./pages/students/StudentDetailPage"));
const SignaturesPage = lazy(() => import("./pages/signatures/SignaturesPage"));
const PipelinePage = lazy(() => import("./pages/pipeline/PipelinePage"));

function Loading() {
  return (
    <Box sx={{ display: "grid", placeItems: "center", py: 10 }}>
      <CircularProgress size={26} />
    </Box>
  );
}

const page = (element: ReactNode) => <Suspense fallback={<Loading />}>{element}</Suspense>;

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: page(<DashboardPage />) },
      { path: "sessions", element: page(<SessionsPage />) },
      { path: "sessions/:date", element: page(<SessionDetailPage />) },
      { path: "students", element: page(<StudentsPage />) },
      { path: "students/:indexNo", element: page(<StudentDetailPage />) },
      { path: "signatures", element: page(<SignaturesPage />) },
      { path: "signatures/:indexNo", element: page(<SignaturesPage />) },
      { path: "pipeline", element: page(<PipelinePage />) },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
