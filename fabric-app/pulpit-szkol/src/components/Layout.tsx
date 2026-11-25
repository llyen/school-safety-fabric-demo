import { NavLink } from 'react-router-dom';
import type { ReactNode } from 'react';

import { Button, ShieldIcon, SyntheticBanner, inputClass } from '@/components/ui';
import { dayLabel, formatTime } from '@/data/model';
import { useAuth } from '@/hooks/AuthContext';
import { STEP_MIN, useScenario } from '@/hooks/ScenarioContext';
import { USER_ROLES, type UserRole } from '@/services/decisions';

const NAV = [
  { to: '/', label: 'Obraz krajowy', end: true },
  { to: '/kolejka', label: 'Kolejka zgłoszeń' },
  { to: '/kampanie', label: 'Kampanie' },
  { to: '/eskalacja', label: 'Eskalacja i zadania' },
  { to: '/zasoby', label: 'Zasoby wsparcia' },
];

function TimeBar() {
  const { index, t, setT, playing, togglePlay, speed, setSpeed } = useScenario();
  if (!index) return null;
  const max = index.scene.meta.hours * 60 - STEP_MIN;
  const d0 = index.scene.meta.d0Hour / 24;
  const day = Math.floor(t / 1440);
  return (
    <div className="border-b border-slate-300 bg-white px-4 py-2 text-ink">
      <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-3">
        <Button variant="primary" onClick={togglePlay} className="w-24">
          {playing ? 'Pauza' : 'Odtwarzaj'}
        </Button>
        <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-800">
          Dzień
          <select
            className={`${inputClass} w-auto py-1`}
            value={day}
            onChange={(e) => setT(Number(e.target.value) * 1440 + (t % 1440))}
            aria-label="Dzień scenariusza"
          >
            {index.scene.meta.days.map((d, i) => (
              <option key={d} value={i}>
                {dayLabel(i, d0)} ({d.slice(5)})
              </option>
            ))}
          </select>
        </label>
        <input
          type="range"
          min={0}
          max={max}
          step={STEP_MIN}
          value={t}
          onChange={(e) => setT(Number(e.target.value))}
          className="min-w-[220px] flex-1 accent-bs"
          aria-label="Czas scenariusza"
        />
        <span className="w-44 text-right text-sm font-semibold tabular-nums">
          {dayLabel(day, d0)} · {formatTime(index, t)}
        </span>
        <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-slate-800">
          Tempo
          <select className={`${inputClass} w-auto py-1`} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} aria-label="Tempo odtwarzania">
            <option value={1400}>wolno</option>
            <option value={700}>normalnie</option>
            <option value={250}>szybko</option>
          </select>
        </label>
      </div>
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const { user, signOut } = useAuth();
  const { actor, setRole, writebackError } = useScenario();
  return (
    <div className="min-h-screen bg-lav text-ink">
      <header className="bg-bs text-white">
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-bsdark">
              <ShieldIcon />
            </span>
            <div className="leading-tight">
              <div className="text-base font-bold">Zgłoszenia szkolne</div>
              <div className="text-[11px] font-semibold uppercase tracking-wider text-bs-100">Pulpit krajowy</div>
            </div>
          </div>
          <nav className="flex flex-wrap gap-1" aria-label="Ekrany">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? 'bg-white text-bs' : 'bg-bs text-white hover:bg-bsdark'}`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide">
              Rola
              <select
                value={actor.role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                className="rounded-md bg-white px-2 py-1 text-sm font-normal normal-case text-ink"
                aria-label="Rola użytkownika"
              >
                {USER_ROLES.map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </label>
            <span className="max-w-[200px] truncate" title={user?.email ?? ''}>{user?.name ?? user?.email ?? 'Użytkownik'}</span>
            <button type="button" onClick={() => void signOut()} className="rounded-md bg-bsdark px-3 py-1 text-sm text-white hover:bg-black">
              Wyloguj
            </button>
          </div>
        </div>
      </header>
      <SyntheticBanner />
      <TimeBar />
      {writebackError && (
        <div role="alert" className="bg-red-100 px-4 py-2 text-center text-sm text-red-900">
          Nie udało się odczytać zapisów z bazy Rayfin: {writebackError}
        </div>
      )}
      <main className="mx-auto max-w-[1500px] space-y-4 p-4">{children}</main>
    </div>
  );
}
