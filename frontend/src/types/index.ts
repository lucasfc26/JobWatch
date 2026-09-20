// ============================================
// JobWatch - Type Definitions
// ============================================

// --- Auth ---
export interface User {
  id: string;
  name: string;
  email: string;
  phone?: string;
  avatar?: string;
  timezone?: string;
  createdAt: string;
}

export interface AuthTokens {
  accessToken: string;
}

export interface AuthResponse {
  accessToken: string;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterData {
  name: string;
  email: string;
  phone: string;
  password: string;
  confirmPassword: string;
}

export interface ForgotPasswordData {
  email: string;
}

// --- Jobs ---
export type JobStatus = 'NEW' | 'VIEWED' | 'APPLIED' | 'EXPIRED';
export type JobType = 'FULL_TIME' | 'PART_TIME' | 'SEASONAL' | 'TEMPORARY';

export interface JobLocation {
  city: string;
  state: string;
  address?: string;
  distance?: number;
}

export interface Job {
  id: string;
  title: string;
  location: JobLocation;
  jobType: JobType;
  facility: string;
  description?: string;
  requirements?: string[];
  salary?: string;
  schedule?: string;
  benefits?: string[];
  externalUrl: string;
  status: JobStatus;
  searchId: string;
  foundAt: string;
  lastSeenAt?: string;
  viewedAt?: string;
  appliedAt?: string;
}

// --- Searches / Monitoring ---
export type SearchStatus = 'ACTIVE' | 'PAUSED' | 'ERROR';
export type SearchSourceType = 'AMAZON_JOBS' | 'AMAZON_WAREHOUSE' | 'JOB_API' | 'JOB_XPATH';

export interface ApiFilterRule {
  path: string;
  values: string[];
}

export interface ApiFilters {
  itemPath?: string;
  filters: ApiFilterRule[];
}

export interface ApiInspectField {
  path: string;
  type: 'string' | 'number' | 'boolean' | 'mixed';
  values: string[];
  uniqueCount: number;
}

export interface WarehouseFilters {
  zipCode: string;
  workHours?: number;
  schedule?: string[];
  length?: string;
  whenStart?: string;
  jobTitle?: string;
  employmentType?: string;
  payRateMin?: number;
  payRateMax?: number;
}

export interface ApiInspectResult {
  itemPath: string;
  itemCount: number;
  fields: ApiInspectField[];
  items: Record<string, unknown>[];
}
export type MonitoringFrequency = '5min' | '15min' | '30min' | '1h' | '2h' | '6h' | '12h' | '24h';
export type NotificationChannel = 'EMAIL' | 'PUSH' | 'SMS' | 'WHATSAPP';

export interface SearchFilters {
  keywords: string[];
  jobTypes: JobType[];
  additionalCities: string[];
}

export interface SearchConfig {
  name: string;
  location: string;
  radius: number;
  keywords: string[];
  jobTypes: JobType[];
  additionalCities: string[];
  frequency: MonitoringFrequency;
  notificationChannels: NotificationChannel[];
}

export interface Search {
  id: string;
  name: string;
  sourceType?: SearchSourceType;
  targetUrl?: string | null;
  xpath?: string | null;
  apiFilters?: ApiFilters | null;
  warehouseFilters?: WarehouseFilters | null;
  location: string;
  radius: number;
  keywords: string[];
  jobTypes: JobType[];
  additionalCities: string[];
  frequency: MonitoringFrequency;
  notificationChannels: NotificationChannel[];
  status: SearchStatus;
  lastCheckedAt?: string;
  nextCheckAt?: string;
  jobsFound: number;
  newJobsFound: number;
  createdAt: string;
  updatedAt: string;
  userId: string;
}

// --- Monitoring Execution ---
export type ExecutionStatus = 'SUCCESS' | 'ERROR' | 'RUNNING';

export interface MonitoringExecution {
  id: string;
  searchId: string;
  status: ExecutionStatus;
  jobsFound: number;
  newJobsFound: number;
  errorMessage?: string;
  executedAt: string;
  duration?: number;
}

// --- Notifications ---
export type NotificationStatus = 'SENT' | 'FAILED' | 'PENDING' | 'READ';
export type NotificationType = 'NEW_JOB' | 'MONITORING_ERROR' | 'MONITORING_PAUSED' | 'SUMMARY';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  channel: NotificationChannel;
  status: NotificationStatus;
  jobId?: string;
  searchId?: string;
  createdAt: string;
  readAt?: string;
}

// --- Dashboard ---
export interface DashboardStats {
  newJobs: number;
  availableJobs: number;
  activeSearches: number;
  lastCheckedAt?: string;
  nextCheckAt?: string;
  monitoringActive: boolean;
}

// --- API ---
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
  statusCounts?: JobStatusCounts;
}

export interface JobStatusCounts {
  all: number;
  NEW: number;
  VIEWED: number;
  APPLIED: number;
  EXPIRED: number;
}

export interface ApiError {
  message: string;
  statusCode: number;
  error?: string;
}

// --- Filters ---
export interface JobFilters {
  location?: string;
  title?: string;
  jobType?: JobType;
  status?: JobStatus;
  onlyNew?: boolean;
  searchId?: string;
  sortBy?: 'newest' | 'oldest' | 'location' | 'title';
  payRateMin?: number;
  payRateMax?: number;
  page?: number;
  limit?: number;
}

export interface NotificationFilters {
  type?: NotificationType;
  status?: NotificationStatus;
  channel?: NotificationChannel;
  read?: boolean;
  page?: number;
  limit?: number;
}

// --- Settings ---
export interface UserSettings {
  notifications: {
    email: boolean;
    push: boolean;
    sms: boolean;
    whatsapp: boolean;
    newJobAlert: boolean;
    periodicSummary: boolean;
  };
  monitoring: {
    defaultFrequency: MonitoringFrequency;
    timezone: string;
  };
}

// --- Extractor (live Camoufox run) ---
export type ExtractorStepStatus = 'pending' | 'running' | 'done' | 'skipped' | 'error';
export type ExtractorRunStatus = 'queued' | 'running' | 'done' | 'error';

export interface ExtractorStep {
  key: string;
  label: string;
  status: ExtractorStepStatus;
  detail: string;
  startedAt: number | null;
  endedAt: number | null;
}

export interface ExtractorLogLine {
  ts: number;
  line: string;
}

export interface ExtractorJob {
  externalId?: string;
  title?: string;
  url?: string;
  location?: string;
  jobType?: string;
  salary?: string;
  schedule?: string;
}

export interface ExtractorRun {
  id: string;
  status: ExtractorRunStatus;
  headless: boolean;
  error: string | null;
  filters: WarehouseFilters;
  startedAt: number;
  finishedAt: number | null;
  steps: ExtractorStep[];
  logs: ExtractorLogLine[];
  jobs: ExtractorJob[];
  frameVersion: number;
}
