import axios from "axios";

/**
 * The API is served under the same origin: in development Vite proxies /api to
 * the Python process (see vite.config.ts), and in production the built bundle
 * is served next to it. Nothing here needs to know which.
 */
export const http = axios.create({ baseURL: "/api", timeout: 120_000 });

/** FastAPI reports failures as {detail: "..."} — surface that, not "Request failed". */
http.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail;
    if (typeof detail === "string") error.message = detail;
    return Promise.reject(error);
  },
);

/** Absolute URL for an image the API serves. */
export function mediaUrl(path: string | null | undefined, version?: string): string | undefined {
  if (!path) return undefined;
  return version ? `${path}${path.includes("?") ? "&" : "?"}v=${encodeURIComponent(version)}` : path;
}
