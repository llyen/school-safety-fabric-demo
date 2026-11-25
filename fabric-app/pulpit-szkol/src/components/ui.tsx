import { useEffect, type ReactNode } from 'react';

import { PRIORITY_LABEL, STATUS_LABEL, type PriorityCode, type StatusCode } from '@/data/model';

export function ShieldIcon({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" fill="none">
      <path d="M12 2.5 4.5 5.5v6c0 4.6 3.1 8.4 7.5 10 4.4-1.6 7.5-5.4 7.5-10v-6L12 2.5Z" fill="#ffffff" />
      <path d="m8.6 12.2 2.4 2.4 4.4-4.8" stroke="#0f6b5c" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Panel({
  title,
  subtitle,
  right,
  children,
  className = '',
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-lg bg-white text-ink shadow-sm ring-1 ring-slate-300 ${className}`}>
      {(title || right) && (
        <header className="flex items-start justify-between gap-4 border-b border-slate-200 px-4 py-3">
          <div>
            {title && <h2 className="text-xs font-bold uppercase tracking-wider text-bs">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-slate-700">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Button({
  children,
  onClick,
  variant = 'default',
  disabled,
  type = 'button',
  className = '',
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: 'default' | 'primary' | 'danger' | 'ghost';
  disabled?: boolean;
  type?: 'button' | 'submit';
  className?: string;
  title?: string;
}) {
  const styles = {
    default: 'bg-white text-ink ring-1 ring-slate-400 hover:bg-bs-50',
    primary: 'bg-bs text-white font-semibold hover:bg-bsdark',
    danger: 'bg-crit text-white font-semibold hover:bg-red-800',
    ghost: 'bg-transparent text-bs font-medium hover:bg-bs-50',
  }[variant];
  return (
    <button
      type={type}
      title={title}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-md px-3 py-1.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    >
      {children}
    </button>
  );
}

export function Badge({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold ${className}`}>{children}</span>;
}

const PRI_CLASS: Record<PriorityCode, string> = {
  KRYTYCZNY: 'bg-crit text-white',
  WYSOKI: 'bg-high text-white',
  SREDNI: 'bg-mid text-white',
  NISKI: 'bg-low text-white',
};
export const PRI_SOLID: Record<PriorityCode, string> = {
  KRYTYCZNY: '#c8203c',
  WYSOKI: '#b8400c',
  SREDNI: '#1d4ed8',
  NISKI: '#4b5563',
};

/** kind: AI to sugestia systemu, DECYZJA to rozstrzygniecie dyzurnego. */
export function PriorityBadge({ priority, kind }: { priority: PriorityCode; kind?: 'AI' | 'DECYZJA' }) {
  const label = PRIORITY_LABEL[priority].toUpperCase();
  return (
    <Badge className={PRI_CLASS[priority]}>
      {kind ? `${kind}: ${label}` : label}
    </Badge>
  );
}

const STATUS_CLASS: Record<StatusCode, string> = {
  NOWE: 'bg-bs-100 text-bsdark',
  W_ANALIZIE: 'bg-amber-100 text-amber-900',
  PRZEKAZANE: 'bg-blue-100 text-blue-900',
  ZAMKNIETE: 'bg-slate-200 text-slate-900',
};
export function StatusBadge({ status }: { status: StatusCode }) {
  return <Badge className={STATUS_CLASS[status]}>{STATUS_LABEL[status]}</Badge>;
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-bold uppercase tracking-wide text-slate-800">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-slate-700">{hint}</span>}
    </label>
  );
}

export const inputClass =
  'w-full rounded-md bg-white px-3 py-2 text-sm text-ink ring-1 ring-slate-400 placeholder:text-slate-600 focus:ring-2 focus:ring-bs focus:outline-none';

export function KpiCard({
  label,
  value,
  note,
  tone = 'default',
}: {
  label: string;
  value: ReactNode;
  note?: ReactNode;
  tone?: 'default' | 'alert';
}) {
  const bar = tone === 'alert' ? 'border-crit' : 'border-bs';
  return (
    <div className={`rounded-lg border-l-4 bg-white px-4 py-3 text-ink shadow-sm ring-1 ring-slate-300 ${bar}`}>
      <div className="text-[11px] font-bold uppercase tracking-wider text-slate-800">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
      {note && <div className="mt-0.5 text-xs text-slate-700">{note}</div>}
    </div>
  );
}

export function Sparkline({
  values,
  marker,
  height = 40,
  color = '#0f6b5c',
  label,
}: {
  values: number[];
  marker?: number;
  height?: number;
  color?: string;
  label: string;
}) {
  const max = Math.max(1, ...values);
  const w = 300;
  const pts = values.map((v, i) => `${(i / Math.max(1, values.length - 1)) * w},${height - 2 - (v / max) * (height - 6)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" role="img" aria-label={label} preserveAspectRatio="none" style={{ height }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
      {marker !== undefined && values.length > 1 && (
        <line x1={(marker / (values.length - 1)) * w} x2={(marker / (values.length - 1)) * w} y1="0" y2={height} stroke="#1a2422" strokeWidth="1" vectorEffect="non-scaling-stroke" />
      )}
    </svg>
  );
}

export function BarList({
  items,
  max,
  color = '#0f6b5c',
}: {
  items: { label: string; value: number; note?: string }[];
  max?: number;
  color?: string;
}) {
  const top = max ?? Math.max(1, ...items.map((i) => i.value));
  return (
    <ul className="space-y-1.5">
      {items.map((it) => (
        <li key={it.label} className="grid grid-cols-[9rem_1fr_3.5rem] items-center gap-2 text-xs">
          <span className="truncate text-ink" title={it.label}>{it.label}</span>
          <span className="h-2.5 rounded bg-slate-200">
            <span className="block h-2.5 rounded" style={{ width: `${Math.min(100, (it.value / top) * 100)}%`, background: color }} />
          </span>
          <span className="text-right tabular-nums text-ink">{it.note ?? it.value}</span>
        </li>
      ))}
    </ul>
  );
}

export function EmptyState({ text }: { text: string }) {
  return <p className="rounded-md bg-bs-50 px-3 py-6 text-center text-sm text-slate-800">{text}</p>;
}

export function SyntheticBanner() {
  return (
    <div role="note" className="bg-amber-100 px-4 py-1.5 text-center text-xs font-semibold text-amber-900">
      Dane syntetyczne. Aplikacja demonstracyjna: brak danych osobowych, zgłaszający jest anonimowy, treści nie zawierają instrukcji operacyjnych.
    </div>
  );
}

export function Toast({ message, onDone }: { message: string | null; onDone: () => void }) {
  useEffect(() => {
    if (!message) return;
    const id = window.setTimeout(onDone, 4500);
    return () => window.clearTimeout(id);
  }, [message, onDone]);
  if (!message) return null;
  return (
    <div role="status" className="fixed bottom-4 right-4 z-50 max-w-sm rounded-md bg-ink px-4 py-3 text-sm text-white shadow-lg">
      {message}
    </div>
  );
}
