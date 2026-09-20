// ============================================
// JobWatch - Routes Configuration
// ============================================

import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthLayout } from '@/components/layouts/AuthLayout';
import { AppLayout } from '@/components/layouts/AppLayout';
import { useAuth } from '@/context/AuthContext';
import { Spinner } from '@/components/ui/Spinner';

// Lazy loaded pages
const LoginPage = lazy(() => import('@/pages/Login').then((m) => ({ default: m.LoginPage })));
const RegisterPage = lazy(() => import('@/pages/Register').then((m) => ({ default: m.RegisterPage })));
const ForgotPasswordPage = lazy(() => import('@/pages/ForgotPassword').then((m) => ({ default: m.ForgotPasswordPage })));
const DashboardPage = lazy(() => import('@/pages/Dashboard').then((m) => ({ default: m.DashboardPage })));
const JobsPage = lazy(() => import('@/pages/Jobs').then((m) => ({ default: m.JobsPage })));
const JobDetailsPage = lazy(() => import('@/pages/JobDetails').then((m) => ({ default: m.JobDetailsPage })));
const SearchesPage = lazy(() => import('@/pages/Searches').then((m) => ({ default: m.SearchesPage })));
const SearchNewPage = lazy(() => import('@/pages/SearchNew').then((m) => ({ default: m.SearchNewPage })));
const SearchDetailsPage = lazy(() => import('@/pages/SearchDetails').then((m) => ({ default: m.SearchDetailsPage })));
const NotificationsPage = lazy(() => import('@/pages/Notifications').then((m) => ({ default: m.NotificationsPage })));
const ExtractorPage = lazy(() => import('@/pages/Extractor').then((m) => ({ default: m.ExtractorPage })));
const SettingsPage = lazy(() => import('@/pages/Settings').then((m) => ({ default: m.SettingsPage })));

function SuspenseWrapper() {
  return (
    <div className="flex h-screen items-center justify-center bg-surface">
      <Spinner size="lg" />
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <SuspenseWrapper />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return <>{children}</>;
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <SuspenseWrapper />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;

  return <>{children}</>;
}

export function AppRoutes() {
  return (
    <Suspense fallback={<SuspenseWrapper />}>
      <Routes>
        {/* Public routes */}
        <Route element={<PublicRoute><AuthLayout /></PublicRoute>}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        </Route>

        {/* Protected routes */}
        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/jobs/:id" element={<JobDetailsPage />} />
          <Route path="/searches" element={<SearchesPage />} />
          <Route path="/searches/new" element={<SearchNewPage />} />
          <Route path="/searches/:id" element={<SearchDetailsPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/extractor" element={<ExtractorPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Suspense>
  );
}
