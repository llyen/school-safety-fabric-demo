import { useState } from 'react';

import { ShieldIcon } from '@/components/ui';
import { useAuth } from '@/hooks/AuthContext';

const msLogo = (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="16"
    height="16"
    viewBox="0 0 21 21"
    className="mr-2"
  >
    <rect x="1" y="1" width="9" height="9" fill="#f25022" />
    <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
    <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
    <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
  </svg>
);

export function AuthPage() {
  const { signIn, fabricAuthEnabled } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSignIn = async () => {
    setError(null);
    setIsLoading(true);
    try {
      await signIn();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Logowanie nie powiodło się.');
    } finally {
      setIsLoading(false);
    }
  };

  const buttonLabel = isLoading
    ? fabricAuthEnabled
      ? 'Otwieram Fabric…'
      : 'Logowanie…'
    : 'Zaloguj przez Microsoft';

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-lav">
      <div className="relative flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="rounded-2xl bg-white p-8 text-ink ring-1 ring-slate-300 shadow-xl">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bs">
                <ShieldIcon />
              </div>
              <div>
                <h1 className="text-lg font-bold text-ink">Zgłoszenia szkolne</h1>
                <p className="text-xs font-semibold uppercase tracking-wider text-bs">Pulpit krajowy</p>
              </div>
            </div>

            <p className="mb-6 text-sm leading-relaxed text-slate-800">
              Aplikacja demonstracyjna dla dyżurnego krajowego, analityka RCB oraz ministra wiodącego i RZZK. Pokazuje
              zgłoszenia szkolne z całego kraju, wykrywa kampanie fałszywych alarmów, rekomenduje poziom eskalacji i zapisuje
              decyzje człowieka z audytem. System tylko sugeruje.
            </p>

            <button
              type="button"
              onClick={handleSignIn}
              disabled={isLoading}
              className="flex w-full items-center justify-center rounded-xl bg-bs px-4 py-3 text-sm font-semibold text-white transition-all hover:bg-bsdark disabled:opacity-50"
            >
              {msLogo}
              {buttonLabel}
            </button>

            {error && <p className="mt-3 text-center text-sm text-red-800">{error}</p>}

            <p className="mt-6 text-[11px] leading-relaxed text-slate-700">
              Dane w aplikacji są w całości syntetyczne i wygenerowane na potrzeby demonstracji.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
