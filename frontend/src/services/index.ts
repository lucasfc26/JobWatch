// ============================================
// JobWatch - API Services
//
// Thin wrappers around the NestJS API. Each function returns data already
// shaped the way the rest of the app (hooks/pages) expects it, so backend
// response quirks (pagination envelopes, differing field names) are
// resolved here instead of leaking into components.
// ============================================

import { apiClient } from './api';
import {
  toCreateSearchDto,
  toUpdateSearchDto,
  frequencyToMinutes,
  minutesToFrequency,
  type SearchFormPayload,
} from '@/lib/searchMapping';
import type {
  User,
  AuthResponse,
  LoginCredentials,
  RegisterData,
  Job,
  JobFilters,
  Search,
  MonitoringExecution,
  Notification,
  NotificationFilters,
  DashboardStats,
  UserSettings,
  PaginatedResponse,
  ApiInspectResult,
  WarehouseFilters,
  ExtractorRun,
} from '@/types';

// --- Auth ---
export const authService = {
  login: async (data: LoginCredentials) => {
    const res = await apiClient.post<AuthResponse>('/auth/login', data);
    return res.data;
  },
  register: async (data: RegisterData) => {
    const res = await apiClient.post<AuthResponse>('/auth/register', {
      name: data.name,
      email: data.email,
      phone: data.phone,
      password: data.password,
    });
    return res.data;
  },
  me: async () => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },
};

// --- Jobs ---
export const jobsService = {
  list: async (filters?: JobFilters) => {
    const res = await apiClient.get<PaginatedResponse<Job>>('/jobs', { params: filters });
    return res.data;
  },
  get: async (id: string) => {
    const res = await apiClient.get<Job>(`/jobs/${id}`);
    return res.data;
  },
  getNew: async () => {
    const res = await apiClient.get<PaginatedResponse<Job>>('/jobs/new', { params: { limit: 20 } });
    return res.data.data;
  },
  markViewed: async (id: string) => {
    const res = await apiClient.patch<Job>(`/jobs/${id}/viewed`);
    return res.data;
  },
  markApplied: async (id: string) => {
    const res = await apiClient.patch<Job>(`/jobs/${id}/applied`);
    return res.data;
  },
  toggleFavorite: async (id: string) => {
    const res = await apiClient.patch<Job>(`/jobs/${id}/favorite`);
    return res.data;
  },
  remove: async (id: string) => {
    await apiClient.delete(`/jobs/${id}`);
    return id;
  },
  removeMany: async (ids: string[]) => {
    const res = await apiClient.post<{ deleted: number }>('/jobs/bulk-delete', { ids });
    return res.data;
  },
  removeAll: async () => {
    const res = await apiClient.post<{ deleted: number }>('/jobs/bulk-delete', { all: true });
    return res.data;
  },
  notifyWhatsapp: async (id: string) => {
    const res = await apiClient.post<{ sent: boolean; notificationId: string }>(
      `/jobs/${id}/notify-whatsapp`,
    );
    return res.data;
  },
};

// --- Searches ---
function mapExecution(execution: {
  id: string;
  searchId: string;
  status: 'RUNNING' | 'SUCCESS' | 'FAILED';
  jobsFound: number;
  newJobs: number;
  errorMessage?: string | null;
  startedAt: string;
}): MonitoringExecution {
  return {
    id: execution.id,
    searchId: execution.searchId,
    status: execution.status === 'FAILED' ? 'ERROR' : execution.status,
    jobsFound: execution.jobsFound,
    newJobsFound: execution.newJobs,
    errorMessage: execution.errorMessage ?? undefined,
    executedAt: execution.startedAt,
  };
}

export const searchesService = {
  list: async () => {
    const res = await apiClient.get<PaginatedResponse<Search>>('/searches', {
      params: { limit: 100 },
    });
    return res.data.data;
  },
  get: async (id: string) => {
    const res = await apiClient.get<Search>(`/searches/${id}`);
    return res.data;
  },
  create: async (data: SearchFormPayload) => {
    const res = await apiClient.post<Search>('/searches', toCreateSearchDto(data));
    return res.data;
  },
  update: async (id: string, data: Partial<SearchFormPayload>) => {
    const res = await apiClient.patch<Search>(`/searches/${id}`, toUpdateSearchDto(data));
    return res.data;
  },
  delete: async (id: string) => {
    await apiClient.delete(`/searches/${id}`);
  },
  pause: async (id: string) => {
    const res = await apiClient.post<Search>(`/searches/${id}/pause`);
    return res.data;
  },
  resume: async (id: string) => {
    const res = await apiClient.post<Search>(`/searches/${id}/resume`);
    return res.data;
  },
  inspectApi: async (url: string) => {
    const res = await apiClient.post<ApiInspectResult>('/searches/inspect-api', { url });
    return res.data;
  },
  runNow: async () => {
    const res = await apiClient.post<{ queued: number }>('/searches/run-now');
    return res.data;
  },
  history: async (id: string) => {
    const res = await apiClient.get<
      PaginatedResponse<{
        id: string;
        searchId: string;
        status: 'RUNNING' | 'SUCCESS' | 'FAILED';
        jobsFound: number;
        newJobs: number;
        errorMessage?: string | null;
        startedAt: string;
      }>
    >(`/searches/${id}/history`, { params: { limit: 50 } });
    return res.data.data.map(mapExecution);
  },
};

// --- Notifications ---
export const notificationsService = {
  list: async (filters?: NotificationFilters) => {
    const params = filters && {
      ...filters,
      read: filters.read === undefined ? undefined : String(filters.read),
    };
    const res = await apiClient.get<PaginatedResponse<Notification>>('/notifications', { params });
    return res.data;
  },
  markRead: async (id: string) => {
    const res = await apiClient.patch<Notification>(`/notifications/${id}/read`);
    return res.data;
  },
  remove: async (id: string) => {
    await apiClient.delete(`/notifications/${id}`);
    return id;
  },
  removeMany: async (ids: string[]) => {
    const res = await apiClient.post<{ deleted: number }>('/notifications/bulk-delete', { ids });
    return res.data;
  },
  removeAll: async () => {
    const res = await apiClient.post<{ deleted: number }>('/notifications/bulk-delete', { all: true });
    return res.data;
  },
};

// --- Dashboard ---
interface DashboardApiResponse {
  stats: { newJobs: number; availableJobs: number; activeSearches: number };
  monitoringActive: boolean;
  lastCheckedAt?: string;
  nextCheckAt?: string;
}

export const dashboardService = {
  getStats: async (): Promise<DashboardStats> => {
    const res = await apiClient.get<DashboardApiResponse>('/dashboard');
    return {
      newJobs: res.data.stats.newJobs,
      availableJobs: res.data.stats.availableJobs,
      activeSearches: res.data.stats.activeSearches,
      lastCheckedAt: res.data.lastCheckedAt,
      nextCheckAt: res.data.nextCheckAt,
      monitoringActive: res.data.monitoringActive,
    };
  },
};

// --- Users / Settings ---
interface BackendUserSettings {
  emailEnabled: boolean;
  pushEnabled: boolean;
  smsEnabled: boolean;
  whatsappEnabled: boolean;
  newJobAlertEnabled: boolean;
  periodicSummaryEnabled: boolean;
  defaultFrequencyMinutes: number;
}

function mapSettings(settings: BackendUserSettings, timezone: string): UserSettings {
  return {
    notifications: {
      email: settings.emailEnabled,
      push: settings.pushEnabled,
      sms: settings.smsEnabled,
      whatsapp: settings.whatsappEnabled,
      newJobAlert: settings.newJobAlertEnabled,
      periodicSummary: settings.periodicSummaryEnabled,
    },
    monitoring: {
      defaultFrequency: minutesToFrequency(settings.defaultFrequencyMinutes),
      timezone,
    },
  };
}

export const usersService = {
  updateProfile: async (data: { name?: string; phone?: string; timezone?: string }) => {
    const res = await apiClient.patch<User>('/users/me', data);
    return res.data;
  },
  getSettings: async (): Promise<UserSettings> => {
    const [settingsRes, meRes] = await Promise.all([
      apiClient.get<BackendUserSettings>('/users/me/settings'),
      apiClient.get<User>('/auth/me'),
    ]);
    return mapSettings(settingsRes.data, meRes.data.timezone ?? '');
  },
  updateSettings: async (data: Partial<UserSettings>): Promise<UserSettings> => {
    const payload: Record<string, unknown> = {};
    if (data.notifications) {
      if (data.notifications.email !== undefined) payload.emailEnabled = data.notifications.email;
      if (data.notifications.push !== undefined) payload.pushEnabled = data.notifications.push;
      if (data.notifications.sms !== undefined) payload.smsEnabled = data.notifications.sms;
      if (data.notifications.whatsapp !== undefined) payload.whatsappEnabled = data.notifications.whatsapp;
      if (data.notifications.newJobAlert !== undefined)
        payload.newJobAlertEnabled = data.notifications.newJobAlert;
      if (data.notifications.periodicSummary !== undefined)
        payload.periodicSummaryEnabled = data.notifications.periodicSummary;
    }
    if (data.monitoring?.timezone) payload.timezone = data.monitoring.timezone;
    if (data.monitoring?.defaultFrequency) {
      payload.defaultFrequencyMinutes = frequencyToMinutes(data.monitoring.defaultFrequency);
    }

    const res = await apiClient.patch<BackendUserSettings>('/users/me/settings', payload);
    const me = await apiClient.get<User>('/auth/me');
    return mapSettings(res.data, me.data.timezone ?? '');
  },
  changePassword: async (data: { currentPassword: string; newPassword: string }) => {
    const res = await apiClient.patch<{ message: string }>('/users/me/password', data);
    return res.data;
  },
  deleteAccount: async () => {
    await apiClient.delete('/users/me');
  },
};

// --- Extractor ---
export const extractorService = {
  start: async (filters: WarehouseFilters): Promise<ExtractorRun> => {
    const res = await apiClient.post<ExtractorRun>('/extractor/runs', filters);
    return res.data;
  },
  current: async (): Promise<ExtractorRun | null> => {
    const res = await apiClient.get<ExtractorRun | null>('/extractor/runs/current');
    return res.data || null;
  },
  frame: async (id: string): Promise<Blob> => {
    const res = await apiClient.get<Blob>(`/extractor/runs/${id}/frame`, { responseType: 'blob' });
    return res.data;
  },
};
