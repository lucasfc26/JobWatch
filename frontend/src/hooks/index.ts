// ============================================
// JobWatch - TanStack Query Hooks
// ============================================

import { useEffect, useRef, useState } from 'react';
import { keepPreviousData, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ExtractorRun, JobFilters, NotificationFilters, UserSettings, WarehouseFilters } from '@/types';
import type { SearchFormPayload } from '@/lib/searchMapping';
import {
  jobsService,
  searchesService,
  notificationsService,
  dashboardService,
  usersService,
  extractorService,
} from '@/services';
import { REFRESH_INTERVAL } from '@/lib/constants';

// --- Dashboard ---
export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: dashboardService.getStats,
    refetchInterval: REFRESH_INTERVAL,
  });
}

// --- Jobs ---
export function useJobs(filters?: JobFilters, enabled = true) {
  return useQuery({
    queryKey: ['jobs', filters],
    queryFn: () => jobsService.list(filters),
    placeholderData: keepPreviousData,
    enabled,
  });
}

export function useNewJobs() {
  return useQuery({
    queryKey: ['jobs', 'new'],
    queryFn: jobsService.getNew,
    refetchInterval: REFRESH_INTERVAL,
  });
}

export function useJob(id: string) {
  return useQuery({
    queryKey: ['jobs', id],
    queryFn: () => jobsService.get(id),
    enabled: !!id,
  });
}

export function useMarkJobViewed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => jobsService.markViewed(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useMarkJobApplied() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => jobsService.markApplied(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  });
}

function invalidateJobs(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['jobs'] });
  qc.invalidateQueries({ queryKey: ['dashboard'] });
  qc.invalidateQueries({ queryKey: ['notifications'] });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => jobsService.remove(id),
    onSuccess: () => invalidateJobs(qc),
  });
}

export function useDeleteJobs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => jobsService.removeMany(ids),
    onSuccess: () => invalidateJobs(qc),
  });
}

export function useDeleteAllJobs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => jobsService.removeAll(),
    onSuccess: () => invalidateJobs(qc),
  });
}

export function useNotifyJobWhatsapp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => jobsService.notifyWhatsapp(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

// --- Searches ---
export function useSearches() {
  return useQuery({
    queryKey: ['searches'],
    queryFn: searchesService.list,
  });
}

export function useSearch(id: string) {
  return useQuery({
    queryKey: ['searches', id],
    queryFn: () => searchesService.get(id),
    enabled: !!id,
  });
}

export function useSearchHistory(id: string) {
  return useQuery({
    queryKey: ['searches', id, 'history'],
    queryFn: () => searchesService.history(id),
    enabled: !!id,
  });
}

export function useCreateSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: SearchFormPayload) => searchesService.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['searches'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useInspectApi() {
  return useMutation({
    mutationFn: (url: string) => searchesService.inspectApi(url),
  });
}

export function useUpdateSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SearchFormPayload> }) =>
      searchesService.update(id, data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['searches'] });
      qc.invalidateQueries({ queryKey: ['searches', variables.id] });
    },
  });
}

export function useDeleteSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => searchesService.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['searches'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useToggleSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'pause' | 'resume' }) =>
      action === 'pause' ? searchesService.pause(id) : searchesService.resume(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['searches'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useForceScan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => searchesService.runNow(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['searches'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      qc.invalidateQueries({ queryKey: ['jobs'] });
      qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

// --- Notifications ---
export function useNotifications(filters?: NotificationFilters) {
  return useQuery({
    queryKey: ['notifications', filters],
    queryFn: () => notificationsService.list(filters),
    refetchInterval: REFRESH_INTERVAL,
  });
}

function invalidateNotifications(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['notifications'] });
  qc.invalidateQueries({ queryKey: ['dashboard'] });
  qc.invalidateQueries({ queryKey: ['jobs'] });
}

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationsService.markRead(id),
    onSuccess: () => invalidateNotifications(qc),
  });
}

export function useDeleteNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => notificationsService.remove(id),
    onSuccess: () => invalidateNotifications(qc),
  });
}

export function useDeleteNotifications() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (ids: string[]) => notificationsService.removeMany(ids),
    onSuccess: () => invalidateNotifications(qc),
  });
}

export function useDeleteAllNotifications() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsService.removeAll(),
    onSuccess: () => invalidateNotifications(qc),
  });
}

// --- Settings ---
export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: usersService.getSettings,
  });
}

export function useUpdateSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<UserSettings>) => usersService.updateSettings(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['settings'] }),
  });
}

// --- User Profile ---
export function useUpdateProfile() {
  return useMutation({
    mutationFn: (data: { name?: string; phone?: string; timezone?: string }) =>
      usersService.updateProfile(data),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: { currentPassword: string; newPassword: string }) =>
      usersService.changePassword(data),
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: () => usersService.deleteAccount(),
  });
}

// --- Extractor ---
const EXTRACTOR_POLL_MS = 1200;

export function useExtractorRun() {
  return useQuery({
    queryKey: ['extractor', 'run'],
    queryFn: extractorService.current,
    staleTime: 0,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' || status === 'queued' ? EXTRACTOR_POLL_MS : false;
    },
  });
}

export function useStartExtractorRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (filters: WarehouseFilters) => extractorService.start(filters),
    onSuccess: (run: ExtractorRun) => qc.setQueryData(['extractor', 'run'], run),
  });
}

export function useExtractorFrame(runId: string | undefined, version: number | undefined) {
  const [url, setUrl] = useState<string | null>(null);
  const currentUrl = useRef<string | null>(null);

  const replaceUrl = (next: string | null) => {
    if (currentUrl.current) URL.revokeObjectURL(currentUrl.current);
    currentUrl.current = next;
    setUrl(next);
  };

  useEffect(() => {
    if (!runId || !version) {
      replaceUrl(null);
      return;
    }
    let cancelled = false;
    extractorService
      .frame(runId)
      .then((blob) => {
        if (!cancelled) replaceUrl(URL.createObjectURL(blob));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, version]);

  useEffect(
    () => () => {
      if (currentUrl.current) URL.revokeObjectURL(currentUrl.current);
    },
    [],
  );

  return url;
}
