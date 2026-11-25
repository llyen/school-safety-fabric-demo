import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { CountryMap, foldName, type MapPoint } from '@/components/CountryMap';
import { ReportDetail } from '@/components/ReportDetail';
import { EmptyState, Panel, PRI_SOLID, PriorityBadge, StatusBadge, inputClass } from '@/components/ui';
import {
  CATEGORY_LABEL,
  PRIORITY_LABEL,
  buildQueue,
  formatTime,
  reportState,
  type QueueTab,
} from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';

const TABS: { id: QueueTab; label: string }[] = [
  { id: 'otwarte', label: 'Otwarte' },
  { id: 'krytyczne', label: 'Krytyczne' },
  { id: 'nowe', label: 'Nowe' },
  { id: 'zamkniete', label: 'Zamknięte' },
];

export function QueuePage() {
  const { index, t, overrides, selectedVoivodeship, setSelectedVoivodeship } = useScenario();
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState<QueueTab>('otwarte');
  const [hideCampaign, setHideCampaign] = useState(false);
  const query = params.get('q') ?? '';
  const selectedId = params.get('id') ?? '';

  const queue = useMemo(
    () => (index ? buildQueue(index, t, { tab, voivodeship: selectedVoivodeship, query, hideCampaign }, overrides) : []),
    [index, t, tab, selectedVoivodeship, query, hideCampaign, overrides]
  );
  const counts = useMemo(() => {
    if (!index) return null;
    const c: Record<QueueTab, number> = { otwarte: 0, krytyczne: 0, nowe: 0, zamkniete: 0 };
    for (const id of TABS) c[id.id] = buildQueue(index, t, { tab: id.id, voivodeship: selectedVoivodeship, query, hideCampaign }, overrides).length;
    return c;
  }, [index, t, selectedVoivodeship, query, hideCampaign, overrides]);
  const codeByName = useMemo(() => {
    const m = new Map<string, string>();
    index?.scene.voivodeships.forEach((v) => m.set(foldName(v.name), v.code));
    return m;
  }, [index]);

  if (!index || !counts) return null;

  const setParam = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next, { replace: true });
  };

  const selected = selectedId ? index.reportById.get(selectedId) : undefined;
  const selectedState = selected ? reportState(selected, t, overrides) : undefined;
  const visibleSelected = selected && selectedState?.visible ? selected : undefined;

  const points: MapPoint[] = queue.slice(0, 400).map(({ report, state }) => ({
    id: report.id,
    lat: report.lat,
    lon: report.lon,
    color: PRI_SOLID[state.priority],
    radius: report.id === selectedId ? 2 : 1,
    label: `${report.id}, ${report.sn}, ${PRIORITY_LABEL[state.priority]}`,
  }));

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,420px)_minmax(0,1fr)_minmax(0,1fr)]">
      <Panel title="Kolejka krajowa" subtitle={`${queue.length} zgłoszeń w widoku`}>
        <div className="mb-3 flex flex-wrap gap-1" role="tablist" aria-label="Zakładki kolejki">
          {TABS.map((x) => (
            <button
              key={x.id}
              role="tab"
              aria-selected={tab === x.id}
              type="button"
              onClick={() => setTab(x.id)}
              className={`rounded-md px-2.5 py-1 text-sm font-medium ${tab === x.id ? 'bg-bs text-white' : 'bg-white text-ink ring-1 ring-slate-400 hover:bg-bs-50'}`}
            >
              {x.label} <span className="tabular-nums">({counts[x.id]})</span>
            </button>
          ))}
        </div>
        <div className="mb-3 grid gap-2">
          <select
            className={inputClass}
            value={selectedVoivodeship}
            onChange={(e) => setSelectedVoivodeship(e.target.value)}
            aria-label="Filtr województwa"
          >
            <option value="">Wszystkie województwa</option>
            {index.scene.voivodeships.map((v) => (
              <option key={v.code} value={v.code}>{v.name}</option>
            ))}
          </select>
          <input
            className={inputClass}
            type="search"
            placeholder="Szukaj: numer BS, szkoła, miejscowość, treść"
            value={query}
            onChange={(e) => setParam('q', e.target.value)}
            aria-label="Szukaj zgłoszeń"
          />
          <label className="flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" className="accent-bs" checked={hideCampaign} onChange={(e) => setHideCampaign(e.target.checked)} />
            Ukryj zgłoszenia wyciszone przez detektor kampanii
          </label>
        </div>
        {queue.length === 0 ? (
          <EmptyState text="Brak zgłoszeń dla wybranych filtrów w tej chwili." />
        ) : (
          <ul className="max-h-[640px] space-y-1.5 overflow-auto pr-1">
            {queue.slice(0, 150).map(({ report, state }) => (
              <li key={report.id}>
                <button
                  type="button"
                  onClick={() => setParam('id', report.id)}
                  className={`w-full rounded-md p-2 text-left text-sm text-ink ring-1 ${report.id === selectedId ? 'bg-bs-100 ring-bs' : 'bg-white ring-slate-300 hover:bg-bs-50'}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold tabular-nums">{report.id}</span>
                    <span className="flex gap-1">
                      <PriorityBadge priority={state.priority} kind={state.decided ? 'DECYZJA' : 'AI'} />
                      <StatusBadge status={state.status} />
                    </span>
                  </div>
                  <div className="mt-0.5 truncate">{report.sn}</div>
                  <div className="text-xs text-slate-700">
                    {formatTime(index, report.t)} · {index.voivName.get(report.v)} · {CATEGORY_LABEL[report.cat]}
                  </div>
                </button>
              </li>
            ))}
            {queue.length > 150 && <li className="px-2 py-1 text-xs text-slate-700">Pokazano 150 pierwszych z {queue.length}. Zawęź filtr.</li>}
          </ul>
        )}
      </Panel>

      <div className="space-y-4">
        <Panel title="Mapa zgłoszeń" subtitle="Kolor punktu to priorytet: krytyczny, wysoki, średni, niski">
          <CountryMap
            ariaLabel="Mapa zgłoszeń z kolejki"
            codeByName={codeByName}
            selected={selectedVoivodeship}
            onSelect={setSelectedVoivodeship}
            regionStyle={() => ({ fill: '#f1f6f5' })}
            points={points}
            onPointClick={(id) => setParam('id', id)}
          />
        </Panel>
      </div>

      <div>
        {visibleSelected && selectedState ? (
          <ReportDetail key={`${visibleSelected.id}-${selectedState.status}-${selectedState.priority}`} report={visibleSelected} state={selectedState} />
        ) : (
          <Panel title="Szczegół zgłoszenia">
            <EmptyState text={selectedId ? `Zgłoszenie ${selectedId} jeszcze nie wpłynęło w wybranej chwili albo nie istnieje.` : 'Wybierz zgłoszenie z kolejki albo z mapy. Przykład: wyszukaj M-1402 lub BS-4826.'} />
          </Panel>
        )}
      </div>
    </div>
  );
}
