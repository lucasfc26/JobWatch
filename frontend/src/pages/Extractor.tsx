import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useExtractorFrame, useExtractorRun, useStartExtractorRun } from '@/hooks';
import { useToast } from '@/context/ToastContext';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Icon } from '@/components/ui/Icon';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Spinner } from '@/components/ui/Spinner';
import { WAREHOUSE_HOURS, WAREHOUSE_LENGTHS, WAREHOUSE_SCHEDULES, WAREHOUSE_STARTS } from '@/lib/constants';
import { cn, getErrorMessage } from '@/lib/utils';
import type { ExtractorRun, ExtractorStep, ExtractorStepStatus, WarehouseFilters } from '@/types';

interface FormState {
  zipCode: string;
  jobTitle: string;
  workHours: string;
  length: string;
  whenStart: string;
  schedule: string[];
}

const INITIAL_FORM: FormState = { zipCode: '', jobTitle: '', workHours: '', length: '', whenStart: '', schedule: [] };

const STEP_ICONS: Record<string, string> = {
  launch: 'rocket_launch',
  navigate: 'language',
  overlays: 'tab_close',
  zip: 'edit_location',
  hours: 'schedule',
  schedule: 'event_available',
  length: 'timelapse',
  when: 'calendar_month',
  title: 'edit',
  results: 'hourglass_top',
  collect: 'view_list',
  details: 'ads_click',
  filter: 'filter_alt',
  close: 'power_settings_new',
};

const RUN_BADGE: Record<ExtractorRun['status'], { label: string; variant: 'info' | 'success' | 'danger' }> = {
  queued: { label: 'Na fila', variant: 'info' },
  running: { label: 'Executando', variant: 'info' },
  done: { label: 'Concluída', variant: 'success' },
  error: { label: 'Falhou', variant: 'danger' },
};

function isActive(run: ExtractorRun | null | undefined) {
  return run?.status === 'running' || run?.status === 'queued';
}

function formatClock(ts: number) {
  return new Date(ts).toLocaleTimeString('pt-BR', { hour12: false });
}

function formatDuration(ms: number) {
  const seconds = Math.max(0, Math.round(ms / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${String(seconds % 60).padStart(2, '0')}s`;
}

function useNow(active: boolean) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [active]);
  return now;
}

export function ExtractorPage() {
  const { toast } = useToast();
  const { data: run } = useExtractorRun();
  const start = useStartExtractorRun();
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const frameUrl = useExtractorFrame(run?.id, run?.frameVersion);
  const running = isActive(run) || start.isPending;
  const now = useNow(isActive(run));

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  const toggleSchedule = (value: string) =>
    update('schedule', form.schedule.includes(value) ? form.schedule.filter((item) => item !== value) : [...form.schedule, value]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const zipCode = form.zipCode.trim();
    if (!zipCode) {
      toast('Informe o CEP ou endereço');
      return;
    }
    const filters: WarehouseFilters = {
      zipCode,
      workHours: form.workHours ? Number(form.workHours) : undefined,
      schedule: form.schedule,
      length: form.length || undefined,
      whenStart: form.whenStart || undefined,
      jobTitle: form.jobTitle.trim() || undefined,
    };
    start.mutate(filters, {
      onError: (error) => toast(getErrorMessage(error, 'Não foi possível iniciar o extrator')),
    });
  };

  return (
    <div className="space-y-space-lg">
      <div>
        <h1 className="font-headline-lg text-headline-lg tracking-tight text-on-surface">Extrator</h1>
        <p className="mt-1 font-body-md text-body-md text-on-surface-variant">
          Acompanhe ao vivo o Camoufox abrindo o hiring.amazon.com, preenchendo os filtros, coletando as vagas e fechando.
        </p>
      </div>

      <div className="grid gap-space-md lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)]">
        <Card className="h-fit space-y-space-md p-space-lg">
          <h2 className="font-headline-sm text-headline-sm text-on-surface">Parâmetros da extração</h2>
          <form onSubmit={handleSubmit} className="space-y-space-md">
            <Input
              label="Zip Code or Address"
              placeholder="94547"
              value={form.zipCode}
              onChange={(event) => update('zipCode', event.target.value)}
              disabled={running}
            />
            <Input
              label="Job Search"
              placeholder="Warehouse Associate"
              value={form.jobTitle}
              onChange={(event) => update('jobTitle', event.target.value)}
              disabled={running}
            />
            <Select
              label="Work Hours"
              options={WAREHOUSE_HOURS.map((item) => ({ value: item.value, label: item.label }))}
              value={form.workHours}
              onChange={(event) => update('workHours', event.target.value)}
              disabled={running}
            />
            <div className="space-y-2">
              <p className="font-label-caps text-label-caps uppercase text-on-surface-variant">Schedule</p>
              <div className="flex flex-wrap gap-2">
                {WAREHOUSE_SCHEDULES.map((item) => {
                  const active = form.schedule.includes(item.value);
                  return (
                    <button
                      key={item.value}
                      type="button"
                      disabled={running}
                      onClick={() => toggleSchedule(item.value)}
                      className={cn(
                        'rounded-full px-3 py-1.5 font-body-sm text-body-sm font-medium transition-colors disabled:opacity-60',
                        active
                          ? 'bg-primary text-on-primary'
                          : 'bg-surface-container-high text-on-surface-variant hover:text-on-surface',
                      )}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>
            <Select
              label="When Start"
              options={WAREHOUSE_STARTS.map((item) => ({ value: item.value, label: item.label }))}
              value={form.whenStart}
              onChange={(event) => update('whenStart', event.target.value)}
              disabled={running}
            />
            <Select
              label="Length (Duration)"
              options={WAREHOUSE_LENGTHS.map((item) => ({ value: item.value, label: item.label }))}
              value={form.length}
              onChange={(event) => update('length', event.target.value)}
              disabled={running}
            />
            <Button type="submit" size="lg" className="w-full" loading={running} icon={<Icon name="play_arrow" className="text-[20px]" />}>
              {running ? 'Extraindo…' : 'Executar extração'}
            </Button>
          </form>
        </Card>

        <div className="min-w-0 space-y-space-md">
          {run ? (
            <>
              <RunSummary run={run} now={now} />
              <div className="grid gap-space-md xl:grid-cols-2">
                <StepTimeline steps={run.steps} now={now} />
                <BrowserPreview run={run} frameUrl={frameUrl} />
              </div>
              <LogConsole run={run} />
              {run.status === 'done' && <Results run={run} />}
            </>
          ) : (
            <Card className="flex flex-col items-center justify-center gap-space-sm p-space-xl text-center">
              <Icon name="smart_toy" className="text-[40px] text-outline" />
              <p className="font-body-md text-body-md text-on-surface-variant">
                Preencha os parâmetros e execute para ver o fluxo do Camoufox aqui.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function RunSummary({ run, now }: { run: ExtractorRun; now: number }) {
  const badge = RUN_BADGE[run.status];
  const elapsed = (run.finishedAt ?? now) - run.startedAt;
  const doneSteps = run.steps.filter((step) => step.status === 'done' || step.status === 'skipped').length;
  const progress = Math.round((doneSteps / run.steps.length) * 100);

  return (
    <Card className="space-y-space-sm">
      <div className="flex flex-wrap items-center justify-between gap-space-sm">
        <div className="flex flex-wrap items-center gap-space-sm">
          <Badge variant={badge.variant}>{badge.label}</Badge>
          <span className="font-mono-data text-mono-data text-on-surface-variant">
            {run.filters.zipCode}
            {run.filters.jobTitle ? ` · ${run.filters.jobTitle}` : ''}
          </span>
        </div>
        <div className="flex items-center gap-space-sm font-mono-data text-mono-data text-on-surface-variant">
          <Badge variant="neutral">{run.headless ? 'headless' : 'janela visível'}</Badge>
          <span className="inline-flex items-center gap-1">
            <Icon name="timer" className="text-[16px]" />
            {formatDuration(elapsed)}
          </span>
        </div>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-container-high">
        <div
          className={cn('h-full rounded-full transition-all duration-500', run.status === 'error' ? 'bg-error' : 'bg-primary')}
          style={{ width: `${progress}%` }}
        />
      </div>
      {run.error && (
        <p className="rounded-lg border border-error/30 bg-error-container/15 px-space-sm py-space-xs font-body-sm text-body-sm text-error">
          {run.error}
        </p>
      )}
    </Card>
  );
}

function StepIcon({ status, stepKey }: { status: ExtractorStepStatus; stepKey: string }) {
  if (status === 'running') return <Spinner size="sm" className="text-secondary" />;
  if (status === 'done') return <Icon name="check_circle" filled className="text-[20px] text-primary" />;
  if (status === 'error') return <Icon name="error" filled className="text-[20px] text-error" />;
  if (status === 'skipped') return <Icon name="remove_circle_outline" className="text-[20px] text-outline" />;
  return <Icon name={STEP_ICONS[stepKey] ?? 'radio_button_unchecked'} className="text-[20px] text-outline/60" />;
}

function StepTimeline({ steps, now }: { steps: ExtractorStep[]; now: number }) {
  return (
    <Card className="space-y-space-sm">
      <h2 className="font-headline-sm text-headline-sm text-on-surface">Fluxo</h2>
      <ol className="space-y-0">
        {steps.map((step, index) => {
          const duration =
            step.startedAt !== null ? (step.endedAt ?? (step.status === 'running' ? now : step.startedAt)) - step.startedAt : null;
          return (
            <li key={step.key} className="relative flex gap-space-sm pb-space-sm last:pb-0">
              {index < steps.length - 1 && (
                <span className="absolute left-[9px] top-6 h-[calc(100%-16px)] w-px bg-outline-variant/40" aria-hidden />
              )}
              <span className="relative z-10 mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center bg-surface-container-low">
                <StepIcon status={step.status} stepKey={step.key} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-space-sm">
                  <span
                    className={cn(
                      'font-body-md text-body-md',
                      step.status === 'pending' || step.status === 'skipped'
                        ? 'text-on-surface-variant'
                        : 'font-semibold text-on-surface',
                      step.status === 'error' && 'text-error',
                    )}
                  >
                    {step.label}
                  </span>
                  {duration !== null && step.status !== 'skipped' && (
                    <span className="flex-shrink-0 font-mono-sm text-mono-sm text-outline">{formatDuration(duration)}</span>
                  )}
                </div>
                {step.detail && (
                  <p className="break-words font-mono-sm text-mono-sm text-on-surface-variant">{step.detail}</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}

function BrowserPreview({ run, frameUrl }: { run: ExtractorRun; frameUrl: string | null }) {
  const closed = run.status === 'done' || run.status === 'error';
  return (
    <Card className="space-y-space-sm">
      <div className="flex items-center justify-between">
        <h2 className="font-headline-sm text-headline-sm text-on-surface">Navegador</h2>
        <span className="font-mono-sm text-mono-sm text-outline">
          {closed ? 'Camoufox fechado' : 'Camoufox aberto'}
        </span>
      </div>
      <div className="flex aspect-video items-center justify-center overflow-hidden rounded-xl border border-outline-variant/30 bg-surface-container-lowest">
        {frameUrl ? (
          <img src={frameUrl} alt="Última captura da tela do Camoufox" className="h-full w-full object-contain" />
        ) : (
          <div className="flex flex-col items-center gap-space-xs text-outline">
            <Icon name="web" className="text-[32px]" />
            <span className="font-body-sm text-body-sm">Aguardando a primeira captura…</span>
          </div>
        )}
      </div>
      <p className="font-body-sm text-body-sm text-on-surface-variant">
        Última captura da tela, atualizada a cada etapa. A última imagem fica visível após o navegador fechar.
      </p>
    </Card>
  );
}

function LogConsole({ run }: { run: ExtractorRun }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = containerRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [run.logs.length]);

  return (
    <Card className="space-y-space-sm">
      <h2 className="font-headline-sm text-headline-sm text-on-surface">Log do extrator</h2>
      <div
        ref={containerRef}
        className="max-h-64 overflow-y-auto rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-space-sm font-mono-sm text-mono-sm"
      >
        {run.logs.length === 0 ? (
          <span className="text-outline">Sem mensagens ainda…</span>
        ) : (
          run.logs.map((entry, index) => (
            <div key={`${entry.ts}-${index}`} className="flex gap-space-sm">
              <span className="flex-shrink-0 text-outline">{formatClock(entry.ts)}</span>
              <span className="break-words text-on-surface-variant">{entry.line.replace(/^\[[a-z]+\]\s*/i, '')}</span>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function Results({ run }: { run: ExtractorRun }) {
  return (
    <Card className="space-y-space-sm">
      <div className="flex items-center justify-between">
        <h2 className="font-headline-sm text-headline-sm text-on-surface">Vagas extraídas</h2>
        <Badge variant={run.jobs.length ? 'success' : 'neutral'}>{run.jobs.length}</Badge>
      </div>
      {run.jobs.length === 0 ? (
        <p className="font-body-md text-body-md text-on-surface-variant">Nenhuma vaga encontrada com esses filtros.</p>
      ) : (
        <ul className="divide-y divide-outline-variant/20">
          {run.jobs.map((job, index) => (
            <li key={job.externalId || job.url || index} className="flex items-start justify-between gap-space-sm py-space-sm">
              <div className="min-w-0">
                <p className="font-body-md text-body-md font-semibold text-on-surface">{job.title || 'Sem título'}</p>
                <p className="font-mono-sm text-mono-sm text-on-surface-variant">
                  {[job.location, job.jobType, job.salary, job.schedule].filter(Boolean).join(' · ')}
                </p>
              </div>
              {job.url && (
                <a
                  href={job.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex-shrink-0 rounded-lg p-1.5 text-on-surface-variant hover:bg-surface-container-high hover:text-primary"
                  aria-label="Abrir vaga"
                >
                  <Icon name="open_in_new" className="text-[18px]" />
                </a>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
