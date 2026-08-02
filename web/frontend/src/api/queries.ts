import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "./client";
import type { Overview, Session, Settings, StudentDetail, StudentRow, VerifyReport } from "../types";

export const queryKeys = {
  overview: ["overview"] as const,
  settings: ["settings"] as const,
  sessions: ["sessions"] as const,
  session: (date: string) => ["sessions", date] as const,
  students: ["students"] as const,
  student: (index: string) => ["students", index] as const,
  verify: (index: string) => ["students", index, "verify"] as const,
};

const get = async <T,>(url: string): Promise<T> => (await http.get<T>(url)).data;

export const useOverview = () =>
  useQuery({ queryKey: queryKeys.overview, queryFn: () => get<Overview>("/overview") });

export const useSettings = () =>
  useQuery({ queryKey: queryKeys.settings, queryFn: () => get<Settings>("/settings"), staleTime: Infinity });

export const useSessions = () =>
  useQuery({ queryKey: queryKeys.sessions, queryFn: () => get<Session[]>("/sessions") });

export const useSession = (date?: string) =>
  useQuery({
    queryKey: queryKeys.session(date ?? ""),
    queryFn: () => get<Session>(`/sessions/${date}`),
    enabled: Boolean(date),
  });

export const useStudents = () =>
  useQuery({ queryKey: queryKeys.students, queryFn: () => get<StudentRow[]>("/students") });

export const useStudent = (index?: string) =>
  useQuery({
    queryKey: queryKeys.student(index ?? ""),
    queryFn: () => get<StudentDetail>(`/students/${index}`),
    enabled: Boolean(index),
  });

export const useVerify = (index?: string) =>
  useQuery({
    queryKey: queryKeys.verify(index ?? ""),
    queryFn: () => get<VerifyReport>(`/students/${index}/verify`),
    enabled: Boolean(index),
  });

/** Everything a processed sheet touches, invalidated in one place. */
function invalidateAll(client: ReturnType<typeof useQueryClient>) {
  client.invalidateQueries({ queryKey: queryKeys.overview });
  client.invalidateQueries({ queryKey: queryKeys.sessions });
  client.invalidateQueries({ queryKey: queryKeys.students });
}

export function useProcessSheet() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, date }: { file: File; date?: string }) => {
      const form = new FormData();
      form.append("file", file);
      if (date) form.append("session_date", date);
      const { data } = await http.post<Session>("/sessions", form);
      return data;
    },
    onSuccess: () => invalidateAll(client),
  });
}

export function useDeleteSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (date: string) => { await http.delete(`/sessions/${date}`); },
    onSuccess: () => invalidateAll(client),
  });
}
