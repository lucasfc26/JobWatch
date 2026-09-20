import { NavLink } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useDashboard, useNotifications, useSearches } from '@/hooks';
import { LogoMark } from '@/components/brand/Logo';
import { Icon } from '@/components/ui/Icon';
import { cn } from '@/lib/utils';

const operations = [
  { to: '/dashboard', label: 'Dashboard', icon: 'speed' },
  { to: '/jobs', label: 'Vagas', icon: 'work_outline', badge: 'jobs' },
  { to: '/searches', label: 'Monitoramentos', icon: 'radar', badge: 'searches' },
  { to: '/notifications', label: 'Notificações', icon: 'notifications', badge: 'notifications' },
  { to: '/extractor', label: 'Extrator', icon: 'smart_toy' },
] as const;

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout } = useAuth();
  const { data: stats } = useDashboard();
  const { data: searches } = useSearches();
  const { data: notifications } = useNotifications({ status: 'SENT' });

  const counts = {
    jobs: stats?.availableJobs ?? 0,
    searches: searches?.filter((item) => item.status === 'ACTIVE').length ?? 0,
    notifications: notifications?.data?.filter((item) => item.status === 'SENT').length ?? 0,
  };

  const badgeClass: Record<string, string> = {
    jobs: 'bg-primary-container/20 border-primary-container/30 text-primary',
    searches: 'bg-secondary-container/20 border-secondary-container/30 text-secondary',
    notifications: 'bg-tertiary-container/20 border-tertiary-container/40 text-tertiary',
  };

  return (
    <>
      {open && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-background/60 backdrop-blur-sm lg:hidden"
          onClick={onClose}
          aria-label="Fechar menu"
        />
      )}
      <aside
        className={cn(
          'fixed left-0 top-0 z-50 flex h-full w-72 flex-col justify-between border-r border-outline-variant/30 bg-surface-container-lowest select-none',
          'transition-transform duration-200 lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
      >
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex h-16 items-center justify-between border-b border-outline-variant/20 px-space-md">
            <div className="flex min-w-0 items-center gap-space-sm">
              <LogoMark />
              <div className="flex min-w-0 flex-col">
                <span className="font-headline-sm text-headline-sm truncate leading-tight tracking-tight text-on-surface">
                  JobWatch
                </span>
                <span className="font-mono-sm text-mono-sm leading-tight text-on-surface-variant">Radar de Vagas</span>
              </div>
            </div>
            <span className="inline-flex items-center gap-1 rounded-full border border-outline-variant/30 bg-surface-container-high px-space-xs py-0.5 font-mono-sm text-mono-sm text-on-surface-variant">
              <span className="h-1.5 w-1.5 rounded-full bg-secondary" />
              v1.2
            </span>
          </div>

          <div className="px-space-md py-space-sm">
            <span className="mb-space-xs block font-label-caps text-label-caps uppercase tracking-wider text-outline">
              Operações
            </span>
          </div>

          <nav className="flex-1 space-y-1 overflow-y-auto px-space-sm">
            {operations.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center justify-between rounded-lg px-space-sm py-space-sm transition-all duration-150',
                    isActive
                      ? 'bg-surface-container-high font-semibold text-primary shadow-[inset_3px_0_0_0] shadow-primary'
                      : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <div className="flex items-center gap-space-sm">
                      <Icon
                        name={item.icon}
                        filled={isActive}
                        className={cn(
                          'text-[20px] transition-colors',
                          isActive ? 'text-primary' : 'text-on-surface-variant group-hover:text-on-surface',
                        )}
                      />
                      <span className="font-body-md text-body-md">{item.label}</span>
                    </div>
                    {item.to === '/dashboard' ? (
                      stats?.monitoringActive ? (
                        <span className="relative flex h-2 w-2">
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                          <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                        </span>
                      ) : null
                    ) : 'badge' in item && counts[item.badge] > 0 ? (
                      <span
                        className={cn(
                          'inline-flex items-center justify-center rounded-full border px-space-xs py-0.5 font-mono-sm text-mono-sm',
                          badgeClass[item.badge],
                        )}
                      >
                        {counts[item.badge]}
                      </span>
                    ) : null}
                  </>
                )}
              </NavLink>
            ))}

            <div className="px-space-xs pb-space-xs pt-space-sm">
              <span className="block font-label-caps text-label-caps uppercase tracking-wider text-outline">Sistema</span>
            </div>
            <NavLink
              to="/settings"
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'group flex items-center justify-between rounded-lg px-space-sm py-space-sm transition-all duration-150',
                  isActive
                    ? 'bg-surface-container-high font-semibold text-primary shadow-[inset_3px_0_0_0] shadow-primary'
                    : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface',
                )
              }
            >
              {({ isActive }) => (
                <div className="flex items-center gap-space-sm">
                  <Icon
                    name="tune"
                    filled={isActive}
                    className={cn(
                      'text-[20px] transition-colors',
                      isActive ? 'text-primary' : 'text-on-surface-variant group-hover:text-on-surface',
                    )}
                  />
                  <span className="font-body-md text-body-md">Configurações</span>
                </div>
              )}
            </NavLink>
          </nav>
        </div>

        <div className="flex flex-col gap-space-sm border-t border-outline-variant/20 p-space-sm">
          <div className="rounded-lg border border-outline-variant/20 bg-surface-container-low p-space-sm">
            <div className="mb-1 flex items-center justify-between">
              <span className="font-label-caps text-label-caps uppercase text-on-surface-variant">Engine Status</span>
              <span
                className={cn(
                  'inline-flex items-center gap-1 font-mono-sm text-mono-sm',
                  stats?.monitoringActive ? 'text-primary' : 'text-tertiary',
                )}
              >
                <span
                  className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    stats?.monitoringActive ? 'animate-pulse bg-primary' : 'bg-tertiary',
                  )}
                />
                {stats?.monitoringActive ? 'Online' : 'Pausado'}
              </span>
            </div>
            <div className="flex items-center justify-between font-mono-data text-mono-data text-on-surface-variant">
              <span>Buscas ativas</span>
              <span className="font-semibold text-on-surface">{stats?.activeSearches ?? 0}</span>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-lg bg-surface-container-low/40 p-space-xs">
            <div className="flex min-w-0 items-center gap-space-sm">
              <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary">
                <Icon name="person" className="text-[18px] text-on-primary" />
              </div>
              <div className="flex min-w-0 flex-col">
                <span className="truncate font-body-md text-body-md font-semibold leading-tight text-on-surface">
                  {user?.name}
                </span>
                <span className="truncate font-mono-sm text-mono-sm leading-tight text-on-surface-variant">
                  {user?.email}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={logout}
              className="rounded p-1 text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-error"
              title="Encerrar Sessão"
            >
              <Icon name="logout" className="text-[20px]" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
