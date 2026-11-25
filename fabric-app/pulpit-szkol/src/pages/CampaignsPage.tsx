import { useMemo } from 'react';
import { Link } from 'react-router-dom';

import { Badge, EmptyState, KpiCard, Panel, PriorityBadge, Sparkline } from '@/components/ui';
import {
  CAMPAIGN_NARRATIVE,
  campaignGroups,
  classifyCluster,
  clusterHourly,
  formatNumber,
  formatTime,
  hourOfMinutes,
  reportState,
  topTerms,
  type CampaignGroup,
  type SceneIndex,
} from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';

const PLATFORM_LABEL: Record<string, string> = {
  platform_forum: 'forum',
  platform_messenger: 'komunikator',
  platform_microblog: 'mikroblog',
  platform_video: 'wideo',
};

function CampaignCard({ group, index, t }: { group: CampaignGroup; index: SceneIndex; t: number }) {
  const h = Math.min(hourOfMinutes(t), index.scene.meta.hours - 1);
  const ids = new Set(group.clusters.map((c) => c.id));
  const hourly = useMemo(() => {
    const sum = new Array(index.scene.meta.hours).fill(0) as number[];
    for (const c of group.clusters) clusterHourly(index, c.id).forEach((v, i) => (sum[i] += v));
    return sum;
  }, [group, index]);
  const terms = useMemo(() => {
    const texts: string[] = [];
    for (const r of index.reports) {
      if (r.t > t) break;
      if (r.cl !== null && ids.has(r.cl)) texts.push(r.text);
    }
    return topTerms(texts, 6);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, t, group]);
  const nid = CAMPAIGN_NARRATIVE[group.id];
  const soc = nid ? index.scene.social[nid] : undefined;
  const reach = soc ? soc.reach.slice(0, h + 1).reduce((a, b) => a + b, 0) : 0;
  const posts = soc ? soc.posts.slice(0, h + 1).reduce((a, b) => a + b, 0) : 0;
  const bot = soc ? soc.bot.slice(Math.max(0, h - 23), h + 1).reduce((a, b) => a + b, 0) / Math.min(24, h + 1) : 0;
  const falseAlarm = group.verdict === 'prawdopodobnie fałszywy alarm';

  return (
    <Panel
      title={`${group.id}: ${group.name}`}
      right={
        <Badge className={falseAlarm ? 'bg-amber-100 text-amber-900' : 'bg-crit text-white'}>
          {falseAlarm ? 'PRAWDOPODOBNIE FAŁSZYWY ALARM' : 'WYMAGA REAKCJI'}
        </Badge>
      }
    >
      <div className="space-y-3 text-sm text-ink">
        <div className="grid grid-cols-3 gap-3">
          <KpiCard label="Zgłoszenia" value={formatNumber(group.size)} />
          <KpiCard label="Województwa" value={group.voivodeships} />
          <KpiCard label="Powiaty" value={group.counties} />
        </div>
        <div>
          <div className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-800">Wzorzec czasu (zgłoszenia na godzinę)</div>
          <Sparkline values={hourly} marker={h} label={`Zgłoszenia kampanii ${group.id} w czasie`} />
        </div>
        <div>
          <div className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-800">Wspólny motyw tekstu (najczęstsze słowa)</div>
          {terms.length === 0 ? (
            <span className="text-xs text-slate-700">Za mało zgłoszeń w tej chwili.</span>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {terms.map((x) => (
                <Badge key={x.term} className="bg-bs-100 text-bsdark">{x.term} ({x.count})</Badge>
              ))}
            </div>
          )}
        </div>
        <div>
          <div className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-800">Zasięg w mediach społecznościowych</div>
          {soc ? (
            <p>
              Narracja „{soc.name}”: {formatNumber(posts)} wpisów, szacowany zasięg {formatNumber(reach)}, średni wskaźnik botów w ostatnich 24 h {formatNumber(bot, 2)}.
              Platformy: {Object.entries(soc.platforms).filter(([p]) => PLATFORM_LABEL[p]).map(([p, n]) => `${PLATFORM_LABEL[p]} ${formatNumber(n)}`).join(', ')}.
            </p>
          ) : (
            <p className="text-slate-700">Brak powiązanej narracji w danych social.</p>
          )}
        </div>
        <table className="w-full text-xs text-ink">
          <caption className="mb-1 text-left text-xs font-bold uppercase tracking-wide text-slate-800">Klastry</caption>
          <thead>
            <tr className="text-left text-slate-800">
              <th className="py-1">Klaster</th><th>Zgł.</th><th>Woj.</th><th>Klienty automatyczne</th><th>Powtórzony link</th><th>Ocena</th>
            </tr>
          </thead>
          <tbody>
            {group.clusters.map((c) => (
              <tr key={c.id} className="even:bg-bs-50">
                <td className="py-1">#{c.id}</td>
                <td className="tabular-nums">{c.size}</td>
                <td className="tabular-nums">{c.voivodeships}</td>
                <td className="tabular-nums">{formatNumber(c.autoShare * 100)}%</td>
                <td className="tabular-nums">{formatNumber(c.linkShare * 100)}%</td>
                <td>{classifyCluster(c) === 'wymaga reakcji' ? 'wymaga reakcji' : 'fałszywy alarm'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

export function CampaignsPage() {
  const { index, t, overrides } = useScenario();
  const groups = useMemo(() => (index ? campaignGroups(index, t) : []), [index, t]);
  if (!index) return null;
  const hidden = index.scene.hiddenReal.filter((x) => x.t <= t);

  return (
    <div className="space-y-4">
      <Panel title="Jak czytać ten ekran">
        <p className="text-sm text-ink">
          Klaster to grupa podobnych zgłoszeń. Ocena „prawdopodobnie fałszywy alarm” wynika z reguły: klaster skoordynowany, w którym co najmniej połowa zgłoszeń
          pochodzi z klientów automatycznych albo z powtórzonego odnośnika. To sugestia do weryfikacji przez analityka. Nazwy kampanii K1, K2 i K3 pochodzą z katalogu
          scenariusza demonstracyjnego, w praktyce nadawałby je analityk. Zgłoszenia z fali, które mogą być realne, nie znikają z kolejki.
        </p>
      </Panel>

      {groups.length === 0 ? (
        <EmptyState text="W wybranej chwili nie wykryto jeszcze kampanii. Przesuń suwak czasu na D-2 lub później." />
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {groups.map((g) => (
            <CampaignCard key={g.id} group={g} index={index} t={t} />
          ))}
        </div>
      )}

      <Panel
        title="Realne zgłoszenia ukryte w fali"
        subtitle="Zgłoszenia krytyczne o treści wymagającej reakcji, które pojawiły się w czasie fal i nie mogą zostać wyciszone"
      >
        {hidden.length === 0 ? (
          <EmptyState text="Do wybranej chwili nie pojawiło się jeszcze żadne takie zgłoszenie." />
        ) : (
          <ul className="grid gap-2 md:grid-cols-2">
            {hidden.map((x) => {
              const r = index.reportById.get(x.id);
              if (!r) return null;
              const s = reportState(r, t, overrides);
              return (
                <li key={x.id} className="rounded-md bg-white p-3 text-sm text-ink ring-1 ring-slate-300">
                  <div className="flex items-center justify-between">
                    <Link className="font-semibold text-bs underline" to={`/kolejka?id=${x.id}`}>{x.id}</Link>
                    <PriorityBadge priority={s.priority} kind={s.decided ? 'DECYZJA' : 'AI'} />
                  </div>
                  <div className="text-xs text-slate-700">
                    {formatTime(index, r.t)} · {index.voivName.get(r.v)} · {r.sn}
                  </div>
                  <p className="mt-1">{r.text}</p>
                  <p className="mt-1 text-xs text-slate-800">
                    {x.inCluster ? 'Zgłoszenie leży w klastrze kampanii.' : 'Poza klastrem kampanii.'} {x.keep ? 'Zachowane w kolejce do oceny człowieka.' : 'Detektor wyciszyłby je w kolejce.'}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </div>
  );
}
