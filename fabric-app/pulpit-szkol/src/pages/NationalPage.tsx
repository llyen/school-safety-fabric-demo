import { useMemo } from 'react';
import { Link } from 'react-router-dom';

import { CountryMap, foldName, type MapPoint } from '@/components/CountryMap';
import { BarList, Badge, KpiCard, Panel, PRI_SOLID, Sparkline } from '@/components/ui';
import {
  KIZS_BANDS,
  PRIORITIES,
  PRIORITY_LABEL,
  PRIORITY_RANK,
  countyKizs,
  dayLabel,
  formatNumber,
  formatTime,
  hourOfMinutes,
  kizsAt,
  kizsBand,
  kpiAt,
  reportState,
  type PriorityCode,
} from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';

export function NationalPage() {
  const { index, t, overrides, selectedVoivodeship: sel, setSelectedVoivodeship: setSel, setT } = useScenario();
  const h = Math.min(hourOfMinutes(t), (index?.scene.meta.hours ?? 1) - 1);

  const kpi = useMemo(() => (index ? kpiAt(index, t, overrides) : null), [index, t, overrides]);

  const codeByName = useMemo(() => {
    const m = new Map<string, string>();
    index?.scene.voivodeships.forEach((v) => m.set(foldName(v.name), v.code));
    return m;
  }, [index]);

  const perReport = useMemo(() => {
    if (!index) return null;
    const bySchool = new Map<string, { open: number; top: PriorityCode; total: number }>();
    const openByV = new Map<string, number>();
    const critPoints: MapPoint[] = [];
    for (const r of index.reports) {
      if (r.t > t) break;
      const s = reportState(r, t, overrides);
      if (s.status !== 'ZAMKNIETE') {
        openByV.set(r.v, (openByV.get(r.v) ?? 0) + 1);
      }
      const cur = bySchool.get(r.sch) ?? { open: 0, top: 'NISKI' as PriorityCode, total: 0 };
      cur.total++;
      if (s.status !== 'ZAMKNIETE') {
        cur.open++;
        if (PRIORITY_RANK[s.priority] > PRIORITY_RANK[cur.top]) cur.top = s.priority;
      }
      bySchool.set(r.sch, cur);
      if (s.status !== 'ZAMKNIETE' && s.priority === 'KRYTYCZNY' && !sel) {
        critPoints.push({ id: r.id, lat: r.lat, lon: r.lon, color: PRI_SOLID.KRYTYCZNY, radius: 0.9, label: `${r.id}, ${r.sn}` });
      }
    }
    return { bySchool, openByV, critPoints };
  }, [index, t, overrides, sel]);

  if (!index || !kpi || !perReport) return null;
  const sc = index.scene;
  const selName = sel ? index.voivName.get(sel) : '';

  const countiesOfSel = sel
    ? sc.counties.filter((c) => c.v === sel).map((c) => ({ c, k: countyKizs(index, c.code, h) })).sort((a, b) => b.k - a.k)
    : [];
  const schoolsOfSel = sel
    ? index.schools
        .filter((s) => s.v === sel && perReport.bySchool.has(s.id))
        .map((s) => ({ s, info: perReport.bySchool.get(s.id)! }))
    : [];
  const points: MapPoint[] = sel
    ? schoolsOfSel.map(({ s, info }) => ({
        id: s.id,
        lat: s.lat,
        lon: s.lon,
        color: PRI_SOLID[info.open ? info.top : 'NISKI'],
        radius: info.open ? 1.4 : 0.8,
        label: `${s.name}, ${s.loc}: zgłoszeń ${info.total}, otwartych ${info.open}`,
      }))
    : perReport.critPoints;

  const national = sc.national;
  const dayBars = sc.meta.days.map((d, i) => ({
    label: `${dayLabel(i, sc.meta.d0Hour / 24)} (${d.slice(5)})`,
    value: Math.max(...national.campaign_24h.slice(i * 24, i * 24 + 24)),
  }));
  const escShown = sc.escalations.filter((e) => e.t <= t).slice(-4);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <KpiCard label="Otwarte zgłoszenia" value={formatNumber(kpi.open)} note="bez zamkniętych, wg decyzji dyżurnych" />
        <KpiCard
          label="Krytyczne bez decyzji"
          value={formatNumber(kpi.criticalNoDecision)}
          tone={kpi.criticalNoDecision > 0 ? 'alert' : 'default'}
          note={`po odfiltrowaniu kampanii: ${formatNumber(kpi.criticalNoDecisionFiltered)}`}
        />
        <KpiCard label="Przypisane do kampanii" value={`${formatNumber(kpi.campaignShare24h * 100)}%`} note={`${formatNumber(kpi.campaignReports24h)} z ${formatNumber(kpi.reports24h)} w ostatnich 24 h`} />
        <KpiCard
          label="Obciążenie 112"
          value={`${formatNumber(kpi.overloadedVoivodeships)} woj.`}
          tone={kpi.overloadedVoivodeships > 0 ? 'alert' : 'default'}
          note={`powyżej 1,5 zdolności, maksimum ${formatNumber(kpi.maxLoad, 2)}`}
        />
        <KpiCard
          label="Czas do przekazania"
          value={kpi.medianToHandoffMin === null ? 'brak' : `${formatNumber(kpi.medianToHandoffMin)} min`}
          note="mediana z ostatnich 24 h"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,4fr)]">
        <Panel
          title="Wskaźnik zagrożenia szkolnego"
          subtitle={sel ? `Województwo ${selName}: szkoły z zgłoszeniami, kolor wg najwyższego otwartego priorytetu` : 'Kartogram 16 województw. Kliknij województwo, aby zejść do powiatów i szkół.'}
          right={sel ? <button type="button" className="text-sm font-medium text-bs underline" onClick={() => setSel('')}>Cała Polska</button> : undefined}
        >
          <CountryMap
            ariaLabel="Mapa Polski z kartogramem wskaźnika zagrożenia szkolnego"
            codeByName={codeByName}
            selected={sel}
            onSelect={setSel}
            regionStyle={(code) => {
              const v = kizsAt(index, code, h);
              return { fill: kizsBand(v).fill, label: sel ? undefined : formatNumber(v) };
            }}
            points={points}
          />
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink">
            <span className="font-bold uppercase tracking-wide text-slate-800">Wskaźnik</span>
            {KIZS_BANDS.map((b) => (
              <span key={b.label} className="flex items-center gap-1.5">
                <span className="inline-block h-3 w-5 rounded-sm ring-1 ring-slate-500" style={{ background: b.fill }} />
                {b.label}
              </span>
            ))}
            <span className="ml-auto flex items-center gap-3">
              {PRIORITIES.slice().reverse().map((p) => (
                <span key={p} className="flex items-center gap-1">
                  <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: PRI_SOLID[p] }} />
                  {PRIORITY_LABEL[p]}
                </span>
              ))}
            </span>
          </div>
          {!sel && <p className="mt-2 text-xs text-slate-700">Punkty: otwarte zgłoszenia o priorytecie krytycznym ({formatNumber(perReport.critPoints.length)}).</p>}
        </Panel>

        <div className="space-y-4">
          {sel ? (
            <>
              <Panel title={`Powiaty: ${selName}`} subtitle="Wskaźnik dzienny powiatu i liczba zgłoszeń w dniu">
                <ul className="max-h-72 space-y-1 overflow-auto pr-1">
                  {countiesOfSel.map(({ c, k }) => {
                    const day = Math.min(Math.floor(h / 24), sc.meta.days.length - 1);
                    const n = sc.kizsCounty[c.code]?.reports[day] ?? 0;
                    return (
                      <li key={c.code} className="flex items-center justify-between rounded px-2 py-1 text-sm text-ink even:bg-bs-50">
                        <span>{c.name}</span>
                        <span className="flex items-center gap-2 tabular-nums">
                          <span className="text-xs text-slate-700">{n} zgł.</span>
                          <span className="rounded px-1.5 py-0.5 text-xs font-semibold text-ink" style={{ background: kizsBand(k).fill }}>{formatNumber(k, 1)}</span>
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </Panel>
              <Panel title="Szkoły z otwartymi zgłoszeniami" subtitle="Posortowane wg priorytetu. Przejście do kolejki z filtrem szkoły.">
                <ul className="max-h-72 space-y-1 overflow-auto pr-1">
                  {schoolsOfSel
                    .filter((x) => x.info.open > 0)
                    .sort((a, b) => PRIORITY_RANK[b.info.top] - PRIORITY_RANK[a.info.top] || b.info.open - a.info.open)
                    .slice(0, 40)
                    .map(({ s, info }) => (
                      <li key={s.id} className="flex items-center justify-between gap-2 rounded px-2 py-1 text-sm even:bg-bs-50">
                        <Link className="truncate font-medium text-bs underline" to={`/kolejka?q=${encodeURIComponent(s.name)}`} title={s.name}>
                          {s.name}, {s.loc}
                        </Link>
                        <span className="flex shrink-0 items-center gap-2 text-xs tabular-nums text-ink">
                          {info.open} otw.
                          <Badge className={info.top === 'KRYTYCZNY' ? 'bg-crit text-white' : info.top === 'WYSOKI' ? 'bg-high text-white' : info.top === 'SREDNI' ? 'bg-mid text-white' : 'bg-low text-white'}>{PRIORITY_LABEL[info.top]}</Badge>
                        </span>
                      </li>
                    ))}
                  {schoolsOfSel.every((x) => x.info.open === 0) && <li className="text-sm text-slate-800">Brak otwartych zgłoszeń w tym momencie.</li>}
                </ul>
              </Panel>
            </>
          ) : (
            <Panel title="Najwyższy wskaźnik" subtitle="Dziesięć województw o najwyższym wskaźniku w wybranej chwili">
              <BarList
                items={sc.voivodeships
                  .map((v) => ({ label: v.name, value: kizsAt(index, v.code, h), open: perReport.openByV.get(v.code) ?? 0 }))
                  .sort((a, b) => b.value - a.value)
                  .slice(0, 10)
                  .map((x) => ({ label: x.label, value: x.value, note: `${formatNumber(x.value, 1)} · ${x.open} otw.` }))}
                max={100}
              />
            </Panel>
          )}
        </div>
      </div>

      <Panel title="Oś czasu D-3 do D+7" subtitle="Suwak w pasku nad ekranem przesuwa czas całej aplikacji. Pionowa kreska to wybrana chwila.">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <div className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-800">Zgłoszenia z fal, 24 h kroczące</div>
            <Sparkline values={national.campaign_24h} marker={h} label="Zgłoszenia przypisane do kampanii w ostatnich 24 godzinach" />
          </div>
          <div>
            <div className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-800">Maksymalny wskaźnik województwa</div>
            <Sparkline values={sc.national.kizs_national_mean.map((_, i) => Math.max(...sc.voivodeships.map((v) => sc.kizs.kizs[v.code][i] ?? 0)))} marker={h} color="#c8203c" label="Maksymalny wskaźnik zagrożenia wśród województw" />
          </div>
          <div>
            <div className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-800">Województwa z 112 powyżej 1,5</div>
            <Sparkline values={national.voivodeships_112_over_1_5} marker={h} color="#b8400c" label="Liczba województw z przeciążonym numerem 112" />
          </div>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-800">Szczyt fali w dniu</div>
            <BarList items={dayBars} />
          </div>
          <div>
            <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-800">Ostatnie decyzje eskalacyjne scenariusza</div>
            {escShown.length === 0 ? (
              <p className="text-sm text-slate-800">Do tej chwili nie było decyzji eskalacyjnych.</p>
            ) : (
              <ul className="space-y-1 text-sm text-ink">
                {escShown.map((e) => (
                  <li key={e.id}>
                    <button type="button" onClick={() => setT(Math.floor(e.t / STEP) * STEP)} className="text-left underline decoration-bs">
                      {formatTime(index, e.t)}
                    </button>{' '}
                    <span className="font-semibold">{e.level}</span> ({e.scope}): {e.desc}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-700">Wskaźnik wyliczono w notebooku 03 (okno 6 h, składniki: sygnały, kampanie, obciążenie 112, zaległości, zdarzenia porządkowe). Wartości pochodzą z danych syntetycznych.</p>
      </Panel>
    </div>
  );
}

const STEP = 15;
