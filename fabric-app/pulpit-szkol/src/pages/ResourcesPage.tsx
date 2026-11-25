import { useMemo } from 'react';

import { Badge, BarList, EmptyState, KpiCard, Panel, inputClass } from '@/components/ui';
import { formatNumber, resourcesAt } from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';

export function ResourcesPage() {
  const { index, t, selectedVoivodeship, setSelectedVoivodeship } = useScenario();
  const rows = useMemo(() => (index ? resourcesAt(index, t) : []), [index, t]);
  if (!index) return null;

  const filtered = rows.filter((r) => !selectedVoivodeship || r.v === selectedVoivodeship);
  const totals = filtered.reduce(
    (a, r) => ({ ped: a.ped + r.pedagog, psy: a.psy + r.psycholog, mob: a.mob + r.mobile, pat: a.pat + r.perShift }),
    { ped: 0, psy: 0, mob: 0, pat: 0 }
  );
  const lowest = [...filtered].filter((r) => r.per10kStudents > 0 || r.pedagog + r.psycholog === 0).sort((a, b) => a.per10kStudents - b.per10kStudents).slice(0, 10);
  const busiest = [...filtered].sort((a, b) => b.utilization - a.utilization).slice(0, 10);
  const inScope = (code: string) => !selectedVoivodeship || code === selectedVoivodeship;
  const supportDef = index.scene.resources.supportDeficitD0.filter((x) => inScope(x.voivodeship_code));
  const patrolDef = index.scene.resources.patrolDeficitD0.filter((x) => inScope(x.voivodeship_code));
  const dayIdx = Math.min(Math.floor(t / 1440), index.scene.resources.patrolDaily.length - 1);
  const pd = index.scene.resources.patrolDaily[dayIdx];
  const sd = index.scene.resources.supportDaily[Math.min(dayIdx, index.scene.resources.supportDaily.length - 1)];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select className={`${inputClass} w-auto`} value={selectedVoivodeship} onChange={(e) => setSelectedVoivodeship(e.target.value)} aria-label="Filtr województwa">
          <option value="">Cały kraj</option>
          {index.scene.voivodeships.map((v) => <option key={v.code} value={v.code}>{v.name}</option>)}
        </select>
        <span className="text-xs text-slate-800">Liczby obsady pochodzą z danych syntetycznych. Rozstawienie jest rekomendacją, nie rozkazem.</span>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <KpiCard label="Pedagodzy" value={formatNumber(totals.ped)} />
        <KpiCard label="Psychologowie" value={formatNumber(totals.psy)} />
        <KpiCard label="Zespoły mobilne" value={formatNumber(totals.mob)} />
        <KpiCard label="Patrole na zmianę (dzień sceny)" value={formatNumber(totals.pat)} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Najniższe pokrycie pedagogami i psychologami" subtitle="Specjaliści na 10 tys. uczniów w powiecie">
          {lowest.length === 0 ? <EmptyState text="Brak danych dla wybranego zakresu." /> : (
            <BarList items={lowest.map((r) => ({ label: `${r.name} (${index.voivName.get(r.v)})`, value: r.per10kStudents, text: formatNumber(r.per10kStudents, 1) }))} />
          )}
        </Panel>
        <Panel title="Największe obciążenie patroli" subtitle="Wykorzystanie zdolności patrolowej w dniu sceny, 1,00 to pełne wykorzystanie">
          {busiest.length === 0 ? <EmptyState text="Brak danych dla wybranego zakresu." /> : (
            <BarList items={busiest.map((r) => ({ label: `${r.name} (${index.voivName.get(r.v)})`, value: r.utilization, text: formatNumber(r.utilization, 2) }))} />
          )}
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Rekomendacja rozstawienia: patrole" subtitle="Powiaty z deficytem w D0 i liczba patroli do przesunięcia (min) według planu z analizy">
          {patrolDef.length === 0 ? <EmptyState text="Brak powiatów z deficytem w wybranym zakresie." /> : (
            <table className="w-full text-xs text-ink">
              <thead><tr className="text-left text-slate-800"><th className="py-1">Powiat</th><th>Popyt</th><th>Zdolność</th><th>Przesunąć</th><th>Po</th></tr></thead>
              <tbody>
                {patrolDef.map((x) => (
                  <tr key={x.county_code} className="even:bg-bs-50">
                    <td className="py-1">{x.county_name} <span className="text-slate-700">({index.voivName.get(x.voivodeship_code)})</span></td>
                    <td className="tabular-nums">{formatNumber(x.dem_status_quo)}</td>
                    <td className="tabular-nums">{formatNumber(x.cap_patrol)}</td>
                    <td className="tabular-nums">{formatNumber(x.moved_in)}</td>
                    <td className="tabular-nums">{formatNumber(x.cap_after)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
        <Panel title="Rekomendacja rozstawienia: wsparcie psychologiczne" subtitle="Powiaty z największym deficytem w D0 (minuty pracy specjalistów)">
          {supportDef.length === 0 ? <EmptyState text="Brak powiatów w wybranym zakresie." /> : (
            <table className="w-full text-xs text-ink">
              <thead><tr className="text-left text-slate-800"><th className="py-1">Powiat</th><th>Pedagodzy</th><th>Psycholodzy</th><th>Deficyt przed</th><th>Po</th></tr></thead>
              <tbody>
                {supportDef.map((x) => (
                  <tr key={x.county_code} className="even:bg-bs-50">
                    <td className="py-1">{x.county_name} <span className="text-slate-700">({index.voivName.get(x.voivodeship_code)})</span></td>
                    <td className="tabular-nums">{x.pedagog}</td>
                    <td className="tabular-nums">{x.psycholog}</td>
                    <td className="tabular-nums">{formatNumber(x.deficit_before_min)}</td>
                    <td className="tabular-nums">{formatNumber(x.deficit_after_min)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
      </div>

      <Panel title="Podsumowanie dnia" subtitle={pd ? pd.date : ''}>
        {pd && sd ? (
          <div className="flex flex-wrap gap-2 text-sm text-ink">
            <Badge className="bg-bs-100 text-bsdark">Patrole: pokrycie {formatNumber(pd.coverage_status_quo * 100, 0)}% przed, {formatNumber(pd.coverage_after_reallocation * 100, 0)}% po przesunięciu</Badge>
            <Badge className="bg-bs-100 text-bsdark">Powiaty z deficytem patroli: {pd.deficit_counties_status_quo} przed, {pd.deficit_counties_after_reallocation} po</Badge>
            <Badge className="bg-bs-100 text-bsdark">Wsparcie: {sd.cases} spraw, pokrycie {formatNumber(sd.coverage_status_quo * 100, 0)}%, deficytowe powiaty {sd.deficit_counties_status_quo}</Badge>
          </div>
        ) : <EmptyState text="Brak danych dziennych." />}
      </Panel>
    </div>
  );
}
