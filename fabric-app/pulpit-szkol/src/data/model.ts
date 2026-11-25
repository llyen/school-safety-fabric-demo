/* Model domenowy pulpitu: typy sceny, status zgloszenia w czasie, KPI, progi eskalacji,
   klasyfikacja kampanii. Funkcje sa czyste, zeby dalo sie je testowac bez UI. */

export const BOUNDS = { minLat: 49.0, maxLat: 54.9, minLon: 14.1, maxLon: 24.2 };

export function project(lat: number, lon: number): { x: number; y: number } {
  return {
    x: ((lon - BOUNDS.minLon) / (BOUNDS.maxLon - BOUNDS.minLon)) * 100,
    y: 100 - ((lat - BOUNDS.minLat) / (BOUNDS.maxLat - BOUNDS.minLat)) * 100,
  };
}

/* ------------------------------ typy ------------------------------ */

export type PriorityCode = 'NISKI' | 'SREDNI' | 'WYSOKI' | 'KRYTYCZNY';
export type StatusCode = 'NOWE' | 'W_ANALIZIE' | 'PRZEKAZANE' | 'ZAMKNIETE';
export type RecipientCode = 'POL' | 'DIR' | 'PED' | 'DYZ';

export const PRIORITIES: PriorityCode[] = ['NISKI', 'SREDNI', 'WYSOKI', 'KRYTYCZNY'];
export const PRIORITY_LABEL: Record<PriorityCode, string> = {
  NISKI: 'Niski',
  SREDNI: 'Średni',
  WYSOKI: 'Wysoki',
  KRYTYCZNY: 'Krytyczny',
};
export const PRIORITY_RANK: Record<PriorityCode, number> = {
  NISKI: 1,
  SREDNI: 2,
  WYSOKI: 3,
  KRYTYCZNY: 4,
};
export const STATUS_LABEL: Record<StatusCode, string> = {
  NOWE: 'Nowe',
  W_ANALIZIE: 'W analizie',
  PRZEKAZANE: 'Przekazane',
  ZAMKNIETE: 'Zamknięte',
};
export const STATUSES: StatusCode[] = ['NOWE', 'W_ANALIZIE', 'PRZEKAZANE', 'ZAMKNIETE'];
export const RECIPIENT_LABEL: Record<string, string> = {
  POL: 'Policja',
  DIR: 'Dyrekcja szkoły',
  PED: 'Pedagog/psycholog',
  DYZ: 'Dyżurnet.pl (NASK)',
};
export const CATEGORY_LABEL: Record<string, string> = {
  BRON: 'Niebezpieczne narzędzie lub broń',
  GROZBY: 'Groźby lub zapowiedź ataku',
  TRESCI_SIEC: 'Niepokojące treści w sieci',
  PRZEMOC: 'Przemoc lub nękanie',
  SAMOUSZKODZENIE: 'Ktoś może zrobić sobie krzywdę',
  INNE: 'Inne zagrożenie',
};
export const SIGNAL_LABEL: Record<string, string> = {
  weapon_mention: 'wzmianka o narzędziu lub broni',
  specific_time: 'wskazany konkretny czas',
  imminence: 'bezpośrednie zagrożenie',
};

export interface Voivodeship {
  code: string;
  name: string;
  lat: number;
  lon: number;
  pop: number;
}
export interface County {
  code: string;
  name: string;
  v: string;
  pop: number;
  students: number;
  lat: number;
  lon: number;
}
export interface School {
  id: string;
  name: string;
  type: string;
  v: string;
  c: string;
  loc: string;
  students: number;
  lat: number;
  lon: number;
}
export type Handoff = [number | null, string, number, string, number | null, string | null, number | null];
export interface Report {
  id: string;
  n: number;
  t: number;
  sch: string;
  sn: string;
  v: string;
  c: string;
  lat: number;
  lon: number;
  cat: string;
  text: string;
  link: number;
  client: string;
  ai: { cat: string; pri: PriorityCode; score: number; sig: string[]; conf: number; rec: string };
  dec: { t: number | null; pri: PriorityCode; status: StatusCode; officer: string; rec: string; queue: number; delay: number };
  ho: Handoff[];
  t1: number | null;
  tc: number | null;
  cl: number | null;
  flag: number;
  keep: number;
  guard: number;
}
export interface Cluster {
  id: number;
  size: number;
  counties: number;
  voivodeships: number;
  schools: number;
  spanH: number;
  perHour: number;
  linkShare: number;
  tokenShare: number;
  autoShare: number;
  latency: number;
  first: number;
  last: number;
  coordinated: number;
  camp: string | null;
}
export interface TaskEvent {
  t: number;
  status: string;
  id: string;
  spo: string;
  div: string;
  level: string;
  title: string;
  due: number | null;
  [k: string]: string | number | null;
}
export interface Scene {
  meta: { start: string; hours: number; d0Hour: number; days: string[]; patrolDays: string[]; synthetic: boolean; source: string };
  voivodeships: Voivodeship[];
  counties: County[];
  kizs: Record<'kizs' | 'c_signals' | 'c_campaign' | 'c_hotline' | 'c_backlog' | 'c_disorder', Record<string, number[]>>;
  national: {
    campaign_24h: number[];
    campaign_voivodeships_24h: number[];
    genuine_critical_24h: number[];
    voivodeships_112_over_1_5: number[];
    disorder_24h: number[];
    kizs_national_mean: number[];
    rec: { rec_minister: boolean[]; rec_rzzk: boolean[]; rec_voivode_any: boolean[] };
  };
  hotline: Record<'load' | 'calls' | 'school' | 'wait' | 'abandoned', Record<string, number[]>>;
  social: Record<string, { name: string; posts: number[]; reach: number[]; bot: number[]; newAcc: number[]; accounts: number[]; platforms: Record<string, number> }>;
  kizsCounty: Record<string, { kizs: number[]; reports: number[] }>;
  clusters: Cluster[];
  campaigns: { id: string; name: string; coordinated: number }[];
  hiddenReal: { id: string; t: number; v: string; c: string; keep: number; inCluster: number }[];
  escalations: { id: string; t: number; level: string; scope: string; type: string; actor: string; desc: string }[];
  tasks: TaskEvent[];
  readiness: { t: number; div: string; status: string; comment: string; forces: string }[];
  admin: { code: string; name: string; ministry: string; inScenario: number }[];
  spo: { code: string; name: string; inScenario: number }[];
  recipients: { code: string; name: string; level: string; div: string }[];
  support: Record<string, Record<string, number>>;
  patrol: Record<string, { perShift: number[]; util: number[] }>;
  resources: {
    supportDeficitD0: {
      county_code: string;
      county_name: string;
      voivodeship_code: string;
      pedagog: number;
      psycholog: number;
      deficit_before_min: number;
      deficit_after_min: number;
    }[];
    patrolDeficitD0: {
      county_code: string;
      county_name: string;
      voivodeship_code: string;
      dem_status_quo: number;
      cap_patrol: number;
      moved_in: number;
      cap_after: number;
    }[];
    supportDaily: {
      date: string;
      cases: number;
      coverage_status_quo: number;
      deficit_counties_status_quo: number;
    }[];
    patrolDaily: {
      date: string;
      coverage_status_quo: number;
      coverage_after_reallocation: number;
      deficit_counties_status_quo: number;
      deficit_counties_after_reallocation: number;
    }[];
  };
}

export interface SceneIndex {
  scene: Scene;
  reports: Report[];
  schools: School[];
  reportById: Map<string, Report>;
  schoolById: Map<string, School>;
  voivName: Map<string, string>;
  countyById: Map<string, County>;
  startMs: number;
}

export function indexScene(scene: Scene, reports: Report[], schools: School[]): SceneIndex {
  return {
    scene,
    reports,
    schools,
    reportById: new Map(reports.map((r) => [r.id, r])),
    schoolById: new Map(schools.map((s) => [s.id, s])),
    voivName: new Map(scene.voivodeships.map((v) => [v.code, v.name])),
    countyById: new Map(scene.counties.map((c) => [c.code, c])),
    startMs: Date.parse(scene.meta.start),
  };
}

/* --------------------------- czas sceny --------------------------- */

const fmtDay = new Intl.DateTimeFormat('pl-PL', { timeZone: 'Europe/Warsaw', day: '2-digit', month: 'short' });
const fmtHm = new Intl.DateTimeFormat('pl-PL', { timeZone: 'Europe/Warsaw', hour: '2-digit', minute: '2-digit' });
const fmtIso = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Europe/Warsaw',
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
});

export function minutesToDate(idx: SceneIndex, minutes: number): Date {
  return new Date(idx.startMs + minutes * 60000);
}
export function formatTime(idx: SceneIndex, minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) return 'brak';
  const d = minutesToDate(idx, minutes);
  return `${fmtDay.format(d)} ${fmtHm.format(d)}`;
}
export function formatIso(idx: SceneIndex, minutes: number): string {
  return fmtIso.format(minutesToDate(idx, minutes));
}
/** Etykieta dnia wzgledem D0: D-3 ... D+7. */
export function dayLabel(dayIndex: number, d0Day = 3): string {
  const d = dayIndex - d0Day;
  return d === 0 ? 'D0' : d > 0 ? `D+${d}` : `D${d}`;
}
export function formatNumber(n: number, digits = 0): string {
  return new Intl.NumberFormat('pl-PL', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(n);
}
export function bsNumber(id: string): string {
  return id;
}

/* ------------------- status zgloszenia w chwili T ------------------- */

export interface UserDecision {
  report_id: string;
  version: number;
  at: number;
  new_priority: PriorityCode;
  new_status: StatusCode;
  recipients: string[];
}

export interface ReportState {
  visible: boolean;
  status: StatusCode;
  /** Priorytet z decyzji dyzurnego. Brak, dopoki dyzurny nie zdecydowal. */
  decisionPriority: PriorityCode | null;
  /** Priorytet wyswietlany: decyzja, a bez niej sugestia AI. */
  priority: PriorityCode;
  decided: boolean;
  recipients: string[];
  overridden: boolean;
}

export function latestUserDecisions(list: UserDecision[]): Map<string, UserDecision> {
  const m = new Map<string, UserDecision>();
  for (const d of list) {
    const cur = m.get(d.report_id);
    if (!cur || d.version > cur.version) m.set(d.report_id, d);
  }
  return m;
}

export function reportState(r: Report, t: number, overrides?: Map<string, UserDecision>): ReportState {
  if (t < r.t) {
    return { visible: false, status: 'NOWE', decisionPriority: null, priority: r.ai.pri, decided: false, recipients: [], overridden: false };
  }
  const o = overrides?.get(r.id);
  if (o && t >= o.at) {
    return {
      visible: true,
      status: o.new_status,
      decisionPriority: o.new_priority,
      priority: o.new_priority,
      decided: true,
      recipients: o.recipients,
      overridden: true,
    };
  }
  const decT = r.dec.t;
  let status: StatusCode = 'NOWE';
  let recipients: string[] = [];
  if (decT !== null && t >= decT) {
    status = 'W_ANALIZIE';
    if (r.t1 !== null && t >= r.t1) {
      status = 'PRZEKAZANE';
      recipients = r.ho.filter((h) => h[0] !== null && t >= h[0]).map((h) => h[1]);
      if (r.tc !== null && t >= r.tc) status = 'ZAMKNIETE';
    }
  }
  const decided = decT !== null && t >= decT;
  return {
    visible: true,
    status,
    decisionPriority: decided ? r.dec.pri : null,
    priority: decided ? r.dec.pri : r.ai.pri,
    decided,
    recipients,
    overridden: false,
  };
}

export type QueueTab = 'otwarte' | 'krytyczne' | 'nowe' | 'zamkniete';

export function matchesTab(s: ReportState, tab: QueueTab): boolean {
  if (!s.visible) return false;
  switch (tab) {
    case 'otwarte':
      return s.status !== 'ZAMKNIETE';
    case 'krytyczne':
      return s.status !== 'ZAMKNIETE' && s.priority === 'KRYTYCZNY';
    case 'nowe':
      return s.status === 'NOWE';
    case 'zamkniete':
      return s.status === 'ZAMKNIETE';
  }
}

export interface QueueFilter {
  tab: QueueTab;
  voivodeship: string;
  query: string;
  hideCampaign: boolean;
}

/** Kolejka: wyzszy priorytet pierwszy, w obrebie priorytetu starsze zgloszenia wyzej. */
export function buildQueue(
  idx: SceneIndex,
  t: number,
  f: QueueFilter,
  overrides?: Map<string, UserDecision>
): { report: Report; state: ReportState }[] {
  const q = f.query.trim().toLowerCase();
  const out: { report: Report; state: ReportState }[] = [];
  for (const r of idx.reports) {
    if (r.t > t) break;
    if (f.voivodeship && r.v !== f.voivodeship) continue;
    if (f.hideCampaign && isSuppressed(r)) continue;
    const state = reportState(r, t, overrides);
    if (!matchesTab(state, f.tab)) continue;
    if (q) {
      const hay = `${r.id} ${r.sn} ${idx.schoolById.get(r.sch)?.loc ?? ''} ${r.text}`.toLowerCase();
      if (!hay.includes(q)) continue;
    }
    out.push({ report: r, state });
  }
  out.sort((a, b) => {
    if (f.tab === 'zamkniete') return b.report.t - a.report.t;
    const d = PRIORITY_RANK[b.state.priority] - PRIORITY_RANK[a.state.priority];
    return d !== 0 ? d : a.report.t - b.report.t;
  });
  return out;
}

/** Zgloszenie z fali, ktore detektor kampanii wyciszylby w kolejce (bez ochrony czlowieka). */
export function isSuppressed(r: Report): boolean {
  return r.flag === 1 && r.keep === 0;
}

/* ------------------------------- KPI ------------------------------- */

export interface Kpi {
  open: number;
  criticalNoDecision: number;
  criticalNoDecisionFiltered: number;
  campaignShare24h: number;
  campaignReports24h: number;
  reports24h: number;
  overloadedVoivodeships: number;
  maxLoad: number;
  medianToHandoffMin: number | null;
}

export function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const s = [...values].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export function hourOfMinutes(t: number): number {
  return Math.floor(t / 60);
}

export function kpiAt(idx: SceneIndex, t: number, overrides?: Map<string, UserDecision>): Kpi {
  let open = 0;
  let crit = 0;
  let critF = 0;
  let rep24 = 0;
  let camp24 = 0;
  const toHandoff: number[] = [];
  for (const r of idx.reports) {
    if (r.t > t) break;
    const s = reportState(r, t, overrides);
    if (s.status !== 'ZAMKNIETE') open++;
    if (r.ai.pri === 'KRYTYCZNY' && !s.decided) {
      crit++;
      if (!isSuppressed(r)) critF++;
    }
    if (t - r.t < 24 * 60) {
      rep24++;
      if (r.flag === 1) camp24++;
      if (r.t1 !== null && r.t1 <= t) toHandoff.push(r.t1 - r.t);
    }
  }
  const h = Math.min(hourOfMinutes(t), idx.scene.meta.hours - 1);
  const loads = Object.values(idx.scene.hotline.load).map((a) => a[h] ?? 0);
  return {
    open,
    criticalNoDecision: crit,
    criticalNoDecisionFiltered: critF,
    campaignShare24h: rep24 ? camp24 / rep24 : 0,
    campaignReports24h: camp24,
    reports24h: rep24,
    overloadedVoivodeships: loads.filter((x) => x > 1.5).length,
    maxLoad: loads.length ? Math.max(...loads) : 0,
    medianToHandoffMin: median(toHandoff),
  };
}

/* -------------------------- KIZS i kartogram -------------------------- */

export const KIZS_BANDS = [
  { min: 0, label: 'poniżej 15', fill: '#dcefe0' },
  { min: 15, label: '15 do 30', fill: '#f6e7b4' },
  { min: 30, label: '30 do 45', fill: '#f8c9a0' },
  { min: 45, label: '45 i więcej', fill: '#f2a3ad' },
];
export function kizsBand(value: number) {
  let band = KIZS_BANDS[0];
  for (const b of KIZS_BANDS) if (value >= b.min) band = b;
  return band;
}
export function kizsAt(idx: SceneIndex, code: string, h: number): number {
  return idx.scene.kizs.kizs[code]?.[Math.min(h, idx.scene.meta.hours - 1)] ?? 0;
}
export function countyKizs(idx: SceneIndex, code: string, h: number): number {
  const day = Math.min(Math.floor(h / 24), idx.scene.meta.days.length - 1);
  return idx.scene.kizsCounty[code]?.kizs[day] ?? 0;
}

/* ----------------------------- eskalacja ----------------------------- */

export type EscalationLevel = 'brak' | 'powiat' | 'wojewoda' | 'minister' | 'rzzk';
export const ESCALATION_ORDER: EscalationLevel[] = ['brak', 'powiat', 'wojewoda', 'minister', 'rzzk'];
export const ESCALATION_LABEL: Record<EscalationLevel, string> = {
  brak: 'Bez eskalacji',
  powiat: 'Powiat (starosta)',
  wojewoda: 'Wojewoda i kurator',
  minister: 'Minister wiodący',
  rzzk: 'RZZK',
};

/** Progi odwzorowuja notebooks\03_kizs_escalation.py. Zmiana wymaga zmiany testu regresyjnego. */
export const THRESHOLDS = {
  powiatUndecidedMin: 10,
  voivodeKizs: 45,
  voivodeConsecutiveHours: 2,
  ministerCampaign24h: 150,
  ministerVoivodeships: 8,
  rzzkCampaign24h: 400,
  rzzkVoivodeships: 12,
  rzzkGenuineCritical: 1,
  rzzkOverloaded112: 1,
  rzzkDisorder: 10,
};

export interface EscalationInputs {
  campaign24h: number;
  campaignVoivodeships: number;
  genuineCritical24h: number;
  overloaded112: number;
  disorder24h: number;
}

export function ministerRecommended(i: EscalationInputs): boolean {
  return i.campaign24h >= THRESHOLDS.ministerCampaign24h && i.campaignVoivodeships >= THRESHOLDS.ministerVoivodeships;
}
export function rzzkRecommended(i: EscalationInputs): boolean {
  return (
    i.campaign24h >= THRESHOLDS.rzzkCampaign24h &&
    i.campaignVoivodeships >= THRESHOLDS.rzzkVoivodeships &&
    (i.genuineCritical24h >= THRESHOLDS.rzzkGenuineCritical ||
      i.overloaded112 >= THRESHOLDS.rzzkOverloaded112 ||
      i.disorder24h >= THRESHOLDS.rzzkDisorder)
  );
}
export function voivodeRecommended(series: number[], h: number): boolean {
  const n = THRESHOLDS.voivodeConsecutiveHours;
  if (h < n - 1) return false;
  for (let k = 0; k < n; k++) if ((series[h - k] ?? 0) < THRESHOLDS.voivodeKizs) return false;
  return true;
}

export interface EscalationRecommendation {
  level: EscalationLevel;
  inputs: EscalationInputs;
  voivodeships: string[];
  counties: { code: string; count: number }[];
  checks: { level: EscalationLevel; met: boolean; rule: string; value: string }[];
}

export function escalationInputsAt(idx: SceneIndex, h: number): EscalationInputs {
  const n = idx.scene.national;
  const i = Math.min(h, idx.scene.meta.hours - 1);
  return {
    campaign24h: n.campaign_24h[i] ?? 0,
    campaignVoivodeships: n.campaign_voivodeships_24h[i] ?? 0,
    genuineCritical24h: n.genuine_critical_24h[i] ?? 0,
    overloaded112: n.voivodeships_112_over_1_5[i] ?? 0,
    disorder24h: n.disorder_24h[i] ?? 0,
  };
}

export function recommendEscalation(idx: SceneIndex, t: number, overrides?: Map<string, UserDecision>): EscalationRecommendation {
  const h = Math.min(hourOfMinutes(t), idx.scene.meta.hours - 1);
  const inputs = escalationInputsAt(idx, h);
  const voivodeships = idx.scene.voivodeships
    .filter((v) => voivodeRecommended(idx.scene.kizs.kizs[v.code] ?? [], h))
    .map((v) => v.code);
  const byCounty = new Map<string, number>();
  for (const r of idx.reports) {
    if (r.t > t) break;
    if (r.ai.pri !== 'KRYTYCZNY' || r.keep !== 1) continue;
    const s = reportState(r, t, overrides);
    if (s.decided) continue;
    if (t - r.t > THRESHOLDS.powiatUndecidedMin) byCounty.set(r.c, (byCounty.get(r.c) ?? 0) + 1);
  }
  const counties = [...byCounty.entries()].map(([code, count]) => ({ code, count })).sort((a, b) => b.count - a.count);
  const minister = ministerRecommended(inputs);
  const rzzk = rzzkRecommended(inputs);
  let level: EscalationLevel = 'brak';
  if (counties.length) level = 'powiat';
  if (voivodeships.length) level = 'wojewoda';
  if (minister) level = 'minister';
  if (rzzk) level = 'rzzk';
  const T = THRESHOLDS;
  return {
    level,
    inputs,
    voivodeships,
    counties,
    checks: [
      { level: 'powiat', met: counties.length > 0, rule: `co najmniej 1 zachowane zgłoszenie krytyczne bez decyzji dłużej niż ${T.powiatUndecidedMin} min`, value: `${counties.length} powiatów` },
      { level: 'wojewoda', met: voivodeships.length > 0, rule: `wskaźnik zagrożenia województwa co najmniej ${T.voivodeKizs} przez ${T.voivodeConsecutiveHours} kolejne godziny`, value: `${voivodeships.length} województw` },
      { level: 'minister', met: minister, rule: `fala co najmniej ${T.ministerCampaign24h} zgłoszeń w 24 h w co najmniej ${T.ministerVoivodeships} województwach`, value: `${inputs.campaign24h} zgłoszeń, ${inputs.campaignVoivodeships} woj.` },
      { level: 'rzzk', met: rzzk, rule: `fala co najmniej ${T.rzzkCampaign24h} zgłoszeń w co najmniej ${T.rzzkVoivodeships} województwach i co najmniej jeden warunek: realne zgłoszenie krytyczne, przeciążone 112 albo ${T.rzzkDisorder} zdarzeń porządkowych`, value: `${inputs.campaign24h} zgłoszeń, ${inputs.campaignVoivodeships} woj., realne krytyczne ${inputs.genuineCritical24h}, 112 powyżej 1,5 w ${inputs.overloaded112} woj., zdarzenia ${inputs.disorder24h}` },
    ],
  };
}

/* ------------------------------ kampanie ------------------------------ */

export type CampaignVerdict = 'prawdopodobnie fałszywy alarm' | 'wymaga reakcji';

export function classifyCluster(c: Pick<Cluster, 'coordinated' | 'autoShare' | 'linkShare'>): CampaignVerdict {
  return c.coordinated && (c.autoShare >= 0.5 || c.linkShare >= 0.5) ? 'prawdopodobnie fałszywy alarm' : 'wymaga reakcji';
}

const STOP = new Set(['który', 'która', 'które', 'jest', 'oraz', 'tego', 'jego', 'tylko', 'wszyscy', 'była', 'było', 'będzie', 'przez', 'żeby', 'albo', 'żeby', 'jeszcze', 'podobno', 'ponoć']);

/** Najczestsze slowa zgloszen z klastra: wspolny motyw tekstu. */
export function topTerms(texts: string[], n = 6): { term: string; count: number }[] {
  const m = new Map<string, number>();
  for (const t of texts) {
    const seen = new Set(t.toLowerCase().split(/[^\p{L}]+/u).filter((w) => w.length >= 5 && !STOP.has(w)));
    for (const w of seen) m.set(w, (m.get(w) ?? 0) + 1);
  }
  return [...m.entries()].map(([term, count]) => ({ term, count })).sort((a, b) => b.count - a.count || a.term.localeCompare(b.term)).slice(0, n);
}

export const CAMPAIGN_NARRATIVE: Record<string, string> = { K1: 'N1', K2: 'N2', K3: 'N3' };

export function clusterHourly(idx: SceneIndex, clusterId: number): number[] {
  const arr = new Array(idx.scene.meta.hours).fill(0) as number[];
  for (const r of idx.reports) if (r.cl === clusterId) arr[Math.min(hourOfMinutes(r.t), arr.length - 1)]++;
  return arr;
}

export interface CampaignGroup {
  id: string;
  name: string;
  clusters: Cluster[];
  verdict: CampaignVerdict;
  size: number;
  voivodeships: number;
  counties: number;
}

export function campaignGroups(idx: SceneIndex, t: number): CampaignGroup[] {
  const out: CampaignGroup[] = [];
  for (const camp of idx.scene.campaigns) {
    if (camp.id === 'R') continue;
    const cls = idx.scene.clusters.filter((c) => c.camp === camp.id && c.first <= t);
    if (!cls.length) continue;
    const verdict = cls.some((c) => classifyCluster(c) === 'prawdopodobnie fałszywy alarm') ? 'prawdopodobnie fałszywy alarm' : 'wymaga reakcji';
    const clusterIds = new Set(cls.map((c) => c.id));
    const vs = new Set<string>();
    const cs = new Set<string>();
    let size = 0;
    for (const r of idx.reports) {
      if (r.t > t) break;
      if (r.cl !== null && clusterIds.has(r.cl)) {
        size++;
        vs.add(r.v);
        cs.add(r.c);
      }
    }
    out.push({ id: camp.id, name: camp.name, clusters: cls, verdict, size, voivodeships: vs.size, counties: cs.size });
  }
  return out;
}

/* ------------------------------- zadania ------------------------------- */

export interface TaskState {
  id: string;
  spo: string;
  div: string;
  title: string;
  status: string;
  due: number | null;
  lastChange: number;
  draft?: string;
}

export function tasksAt(idx: SceneIndex, t: number): TaskState[] {
  const m = new Map<string, TaskState>();
  for (const e of idx.scene.tasks) {
    if (e.t > t) continue;
    const prev = m.get(e.id);
    if (prev && prev.lastChange > e.t) continue;
    const draft = typeof e.draft_text === 'string' ? e.draft_text : typeof e.message_draft === 'string' ? e.message_draft : prev?.draft;
    m.set(e.id, { id: e.id, spo: e.spo, div: e.div, title: e.title, status: e.status, due: e.due, lastChange: e.t, draft });
  }
  return [...m.values()].sort((a, b) => a.id.localeCompare(b.id));
}

/* ------------------------------- zasoby ------------------------------- */

export interface CountyResources {
  code: string;
  name: string;
  v: string;
  pedagog: number;
  psycholog: number;
  mobile: number;
  perShift: number;
  utilization: number;
  per10kStudents: number;
}

export function resourcesAt(idx: SceneIndex, t: number): CountyResources[] {
  const day = Math.min(Math.floor(t / 1440), idx.scene.meta.patrolDays.length - 1);
  return idx.scene.counties.map((c) => {
    const s = idx.scene.support[c.code] ?? {};
    const p = idx.scene.patrol[c.code];
    const ped = s.pedagog ?? 0;
    const psy = s.psycholog ?? 0;
    return {
      code: c.code,
      name: c.name,
      v: c.v,
      pedagog: ped,
      psycholog: psy,
      mobile: s.zespol_mobilny ?? 0,
      perShift: p?.perShift[day] ?? 0,
      utilization: p?.util[day] ?? 0,
      per10kStudents: c.students ? ((ped + psy) / c.students) * 10000 : 0,
    };
  });
}

/* -------------------------------- audyt -------------------------------- */

function cyrb53(str: string, seed: number): number {
  let h1 = 0xdeadbeef ^ seed;
  let h2 = 0x41c6ce57 ^ seed;
  for (let i = 0; i < str.length; i++) {
    const ch = str.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return 4294967296 * (2097151 & h2) + (h1 >>> 0);
}

/** Skrot kontrolny wpisu audytu (64 znaki szesnastkowe). To kontrola spojnosci, nie podpis kryptograficzny. */
export function auditHash(payload: unknown): string {
  const text = JSON.stringify(payload);
  return [1, 2, 3, 4].map((s) => cyrb53(text, s).toString(16).padStart(14, '0').slice(-16).padStart(16, '0')).join('');
}
