import { useMemo, useState } from 'react';

import { Badge, Button, EmptyState, Field, KpiCard, Panel, Toast, inputClass } from '@/components/ui';
import {
  ESCALATION_LABEL,
  ESCALATION_ORDER,
  formatNumber,
  formatTime,
  kizsAt,
  hourOfMinutes,
  kpiAt,
  recommendEscalation,
  tasksAt,
  type EscalationLevel,
  type TaskState,
} from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';
import {
  ESCALATION_ROLES,
  TASK_STATUSES,
  saveDraft,
  saveEscalation,
  saveTaskStatus,
  validateEscalation,
} from '@/services/decisions';

const DIVISIONS = ['XV', 'XIX', 'X', 'XIII'];
const SPOS = ['SPO-1', 'SPO-3', 'SPO-12', 'SPO-16'];
const DRAFT_KEY = 'SPO-3-komunikat';

const STATUS_CLASS: Record<string, string> = {
  zlecone: 'bg-bs-100 text-bsdark',
  w_toku: 'bg-amber-100 text-amber-900',
  wykonane: 'bg-green-100 text-green-900',
  opoznione: 'bg-red-100 text-red-900',
  zablokowane: 'bg-red-100 text-red-900',
};

function TaskRow({ task, effective, divisionName }: { task: TaskState; effective: string; divisionName: string }) {
  const { actor, refresh, index, t } = useScenario();
  const [status, setStatus] = useState(effective);
  const [comment, setComment] = useState('');
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  if (!index) return null;
  const save = async () => {
    setErr(null);
    try {
      await saveTaskStatus({ task_id: task.id, admin_division: task.div, spo_code: task.spo, status, comment }, actor);
      await refresh();
      setComment('');
      setMsg(`Zapisano status zadania ${task.id}.`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  };
  const overdue = task.due !== null && task.due < t && effective !== 'wykonane';
  return (
    <li className="rounded-md bg-white p-2 text-sm text-ink ring-1 ring-slate-300">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <span className="font-semibold">{task.id}</span> <span className="text-xs text-slate-700">({task.spo}, dział {task.div}: {divisionName})</span>
          <div>{task.title}</div>
          <div className="text-xs text-slate-700">Termin: {formatTime(index, task.due)}{overdue ? ', po terminie' : ''}</div>
        </div>
        <Badge className={STATUS_CLASS[effective] ?? 'bg-slate-200 text-slate-900'}>{effective}</Badge>
      </div>
      <div className="mt-2 flex flex-wrap items-end gap-2">
        <select className={`${inputClass} w-auto py-1`} value={status} onChange={(e) => setStatus(e.target.value)} aria-label={`Status zadania ${task.id}`}>
          {TASK_STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <input className={`${inputClass} min-w-[180px] flex-1 py-1`} placeholder="Komentarz (wymagany przy zablokowaniu)" value={comment} maxLength={500} onChange={(e) => setComment(e.target.value)} aria-label={`Komentarz do zadania ${task.id}`} />
        <Button onClick={() => void save()} disabled={status === effective && !comment}>Zapisz</Button>
      </div>
      {err && <p role="alert" className="mt-1 text-xs text-red-800">{err}</p>}
      <Toast message={msg} onDone={() => setMsg(null)} />
    </li>
  );
}

export function EscalationPage() {
  const { index, t, overrides, actor, escalations, taskStatuses, drafts, refresh, selectedVoivodeship } = useScenario();
  const rec = useMemo(() => (index ? recommendEscalation(index, t, overrides) : null), [index, t, overrides]);
  const kpi = useMemo(() => (index ? kpiAt(index, t, overrides) : null), [index, t, overrides]);
  const [level, setLevel] = useState<EscalationLevel>('brak');
  const [scope, setScope] = useState('PL');
  const [just, setJust] = useState('');
  const [errs, setErrs] = useState<string[]>([]);
  const [toast, setToast] = useState<string | null>(null);

  const tasks = useMemo(() => (index ? tasksAt(index, t) : []), [index, t]);
  const [draftBody, setDraftBody] = useState<string | null>(null);
  const [draftComment, setDraftComment] = useState('');
  const [draftErr, setDraftErr] = useState<string | null>(null);

  if (!index || !rec || !kpi) return null;
  const h = Math.min(hourOfMinutes(t), index.scene.meta.hours - 1);
  const maxKizs = Math.max(...index.scene.voivodeships.map((v) => kizsAt(index, v.code, h)));
  const effectiveLevel = level === 'brak' ? rec.level : level;
  const divName = (code: string) => index.scene.admin.find((a) => a.code === code)?.name ?? '';

  const latestStatus = new Map<string, string>();
  [...taskStatuses].sort((a, b) => a.changed_at.getTime() - b.changed_at.getTime()).forEach((s) => latestStatus.set(s.task_id, s.status));
  const eff = (task: TaskState) => latestStatus.get(task.id) ?? task.status;

  const draftsForKey = drafts.filter((d) => d.draft_key === DRAFT_KEY).sort((a, b) => b.version - a.version);
  const latestDraft = draftsForKey[0];

  const generated =
    `Komunikat dla rodziców, uczniów i mediów (szkic do zatwierdzenia przez człowieka).\n` +
    `W ostatnich 24 godzinach do systemu zgłoszeń szkolnych wpłynęło wiele zgłoszeń o podobnej treści z różnych województw. ` +
    `Analiza wskazuje, że część z nich pochodzi z zautomatyzowanych źródeł i jest prawdopodobnie fałszywa. ` +
    `Każde zgłoszenie jest nadal oceniane przez dyżurnego, a zgłoszenia wskazujące realne zagrożenie trafiają do Policji. ` +
    `Prosimy o korzystanie wyłącznie z komunikatów gov.pl i kuratoriów oraz o zgłaszanie zagrożeń przez numer 112 albo szkolną aplikację zgłoszeń. ` +
    `Nie rozpowszechniamy niezweryfikowanych nagrań i wiadomości. Komunikat zostanie zaktualizowany po kolejnej weryfikacji.`;
  const body = draftBody ?? latestDraft?.body ?? generated;

  const onEscalate = async () => {
    const draft = {
      recommended_level: rec.level,
      chosen_level: level,
      scope,
      scene_time: new Date(index.startMs + t * 60000).toISOString(),
      campaign_24h: rec.inputs.campaign24h,
      campaign_voivodeships: rec.inputs.campaignVoivodeships,
      genuine_critical_24h: rec.inputs.genuineCritical24h,
      max_kizs: maxKizs,
      justification: just,
    };
    const e = validateEscalation(draft, actor);
    setErrs(e);
    if (e.length) return;
    try {
      await saveEscalation(draft, actor);
      await refresh();
      setJust('');
      setToast(`Uruchomiono eskalację: ${ESCALATION_LABEL[level]}.`);
    } catch (x) {
      setErrs([x instanceof Error ? x.message : String(x)]);
    }
  };

  const onDraft = async (status: 'szkic' | 'zatwierdzony' | 'odrzucony') => {
    setDraftErr(null);
    try {
      await saveDraft({ draft_key: DRAFT_KEY, status, body, comment: draftComment }, actor, drafts);
      await refresh();
      setDraftBody(null);
      setDraftComment('');
      setToast(`Komunikat SPO-3: ${status}.`);
    } catch (x) {
      setDraftErr(x instanceof Error ? x.message : String(x));
    }
  };

  const ready = index.scene.readiness.filter((r) => r.t <= t);
  const spoTasks = (code: string) => tasks.filter((x) => x.spo === code);
  const divTasks = (code: string) => tasks.filter((x) => x.div === code);

  return (
    <div className="space-y-4">
      <Toast message={toast} onDone={() => setToast(null)} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Rekomendacja eskalacji" subtitle="Powiat, wojewoda i kurator, minister wiodący, RZZK. System rekomenduje, człowiek decyduje.">
          <div className="space-y-3 text-sm text-ink">
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-800">Rekomendowany poziom</span>
              <Badge className={rec.level === 'brak' ? 'bg-slate-200 text-slate-900' : 'bg-crit text-white'}>{ESCALATION_LABEL[rec.level].toUpperCase()}</Badge>
            </div>
            <ul className="space-y-1.5">
              {rec.checks.map((c) => (
                <li key={c.level} className={`rounded-md p-2 ring-1 ${c.met ? 'bg-red-50 ring-crit' : 'bg-white ring-slate-300'}`}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold">{ESCALATION_LABEL[c.level]}</span>
                    <Badge className={c.met ? 'bg-crit text-white' : 'bg-slate-200 text-slate-900'}>{c.met ? 'PRÓG PRZEKROCZONY' : 'poniżej progu'}</Badge>
                  </div>
                  <div className="text-xs text-slate-800">Próg: {c.rule}</div>
                  <div className="text-xs tabular-nums">Teraz: {c.value}</div>
                </li>
              ))}
            </ul>
            {rec.voivodeships.length > 0 && (
              <p>Województwa powyżej progu wojewódzkiego: {rec.voivodeships.map((c) => index.voivName.get(c)).join(', ')}.</p>
            )}
            {rec.counties.length > 0 && (
              <p>Powiaty z zachowanym zgłoszeniem krytycznym bez decyzji ponad 10 min: {rec.counties.slice(0, 8).map((x) => `${index.countyById.get(x.code)?.name ?? x.code} (${x.count})`).join(', ')}{rec.counties.length > 8 ? ` i ${rec.counties.length - 8} kolejnych` : ''}.</p>
            )}
          </div>
        </Panel>

        <Panel title="Uruchomienie eskalacji" subtitle="Zapis do audytu z migawką wskaźników">
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              void onEscalate();
            }}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Poziom" hint={`Rekomendacja: ${ESCALATION_LABEL[rec.level]}`}>
                <select className={inputClass} value={level} onChange={(e) => setLevel(e.target.value as EscalationLevel)}>
                  {ESCALATION_ORDER.map((l) => <option key={l} value={l}>{l === 'brak' ? 'Wybierz poziom' : ESCALATION_LABEL[l]}</option>)}
                </select>
              </Field>
              <Field label="Zakres">
                <select className={inputClass} value={scope} onChange={(e) => setScope(e.target.value)}>
                  <option value="PL">Cały kraj</option>
                  {index.scene.voivodeships.map((v) => <option key={v.code} value={v.code}>{v.name}</option>)}
                </select>
              </Field>
            </div>
            <Field label="Uzasadnienie (wymagane)">
              <textarea className={inputClass} rows={3} maxLength={1000} value={just} onChange={(e) => setJust(e.target.value)} />
            </Field>
            {errs.length > 0 && (
              <ul role="alert" className="list-disc rounded-md bg-red-100 py-2 pl-7 pr-3 text-sm text-red-900">
                {errs.map((x) => <li key={x}>{x}</li>)}
              </ul>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <Button type="submit" variant="danger">Uruchom eskalację</Button>
              <span className="text-xs text-slate-800">
                Rola: {actor.role}. Poziomy minister i RZZK: {ESCALATION_ROLES.join(', ')}. Wybrany filtr województwa w kolejce: {selectedVoivodeship ? index.voivName.get(selectedVoivodeship) : 'brak'}.
              </span>
            </div>
          </form>
          {escalations.length > 0 && (
            <div className="mt-4">
              <div className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-800">Zapisane eskalacje</div>
              <ul className="space-y-1.5 text-xs text-ink">
                {escalations.map((e) => (
                  <li key={e.id} className="rounded-md bg-white p-2 ring-1 ring-slate-300">
                    <div className="font-semibold">{ESCALATION_LABEL[e.chosen_level as EscalationLevel]} ({e.scope}), rekomendacja {ESCALATION_LABEL[e.recommended_level as EscalationLevel]}</div>
                    <div>{e.actor_name} ({e.actor_role}), czas sceny {formatTime(index, (Date.parse(e.scene_time) - index.startMs) / 60000)}</div>
                    <div>Migawka: fala {e.campaign_24h} zgł. w {e.campaign_voivodeships} woj., realne krytyczne {e.genuine_critical_24h}, maksymalny wskaźnik {e.max_kizs}</div>
                    <div>Uzasadnienie: {e.justification}</div>
                    <div className="text-slate-700">Skrót kontrolny {e.audit_hash.slice(0, 16)}…</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Panel>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <KpiCard label="Poziom do rozważenia" value={ESCALATION_LABEL[effectiveLevel]} />
        <KpiCard label="Fala w 24 h" value={formatNumber(rec.inputs.campaign24h)} note={`${rec.inputs.campaignVoivodeships} województw`} />
        <KpiCard label="Realne krytyczne w 24 h" value={rec.inputs.genuineCritical24h} />
        <KpiCard label="Krytyczne bez decyzji" value={kpi.criticalNoDecision} tone={kpi.criticalNoDecision ? 'alert' : 'default'} />
      </div>

      <Panel title="Zadania działów administracji" subtitle="Checklista z zapisem statusu. Źródło początkowe: zdarzenia scenariusza, nadpisywane zapisami z aplikacji.">
        <div className="grid gap-4 lg:grid-cols-2">
          {DIVISIONS.map((code) => {
            const list = divTasks(code);
            return (
              <div key={code}>
                <h3 className="mb-1 text-xs font-bold uppercase tracking-wide text-bs">Dział {code}: {divName(code)}</h3>
                {list.length === 0 ? <EmptyState text="Brak zleconych zadań w tej chwili." /> : (
                  <ul className="space-y-2">{list.map((x) => <TaskRow key={`${x.id}-${eff(x)}`} task={x} effective={eff(x)} divisionName={divName(x.div)} />)}</ul>
                )}
              </div>
            );
          })}
        </div>
        {tasks.some((x) => !DIVISIONS.includes(x.div)) && (
          <p className="mt-3 text-xs text-slate-800">Zadania działów spoza listy kontrolnej ({tasks.filter((x) => !DIVISIONS.includes(x.div)).map((x) => `${x.id}: dział ${x.div}`).join(', ')}) widoczne są w checkliście SPO poniżej.</p>
        )}
      </Panel>

      <Panel title="Checklista SPO" subtitle="SPO-1, SPO-3, SPO-12 i SPO-16">
        <div className="grid gap-4 lg:grid-cols-2">
          {SPOS.map((code) => {
            const list = spoTasks(code);
            const meta = index.scene.spo.find((s) => s.code === code);
            return (
              <div key={code}>
                <h3 className="mb-1 text-xs font-bold uppercase tracking-wide text-bs">{code}: {meta?.name}</h3>
                {list.length === 0 ? <EmptyState text="Brak zleconych zadań w tej chwili." /> : (
                  <ul className="space-y-2">{list.map((x) => <TaskRow key={`${x.id}-${eff(x)}-spo`} task={x} effective={eff(x)} divisionName={divName(x.div)} />)}</ul>
                )}
              </div>
            );
          })}
        </div>
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Szkic komunikatu SPO-3" subtitle="Szkic przygotowuje system. Publikacja wymaga zatwierdzenia przez człowieka.">
          <div className="space-y-3 text-sm text-ink">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wide text-slate-800">Stan</span>
              <Badge className={latestDraft?.status === 'zatwierdzony' ? 'bg-green-100 text-green-900' : latestDraft?.status === 'odrzucony' ? 'bg-red-100 text-red-900' : 'bg-amber-100 text-amber-900'}>
                {(latestDraft?.status ?? 'szkic wygenerowany, niezapisany').toUpperCase()}
              </Badge>
              {latestDraft && <span className="text-xs text-slate-700">v{latestDraft.version}, {latestDraft.actor_name}</span>}
            </div>
            <textarea className={inputClass} rows={9} maxLength={2000} value={body} onChange={(e) => setDraftBody(e.target.value)} aria-label="Treść komunikatu SPO-3" />
            <input className={inputClass} placeholder="Komentarz do decyzji (opcjonalnie)" maxLength={500} value={draftComment} onChange={(e) => setDraftComment(e.target.value)} aria-label="Komentarz do komunikatu" />
            {draftErr && <p role="alert" className="rounded-md bg-red-100 px-3 py-2 text-red-900">{draftErr}</p>}
            <div className="flex flex-wrap gap-2">
              <Button onClick={() => void onDraft('szkic')}>Zapisz szkic</Button>
              <Button variant="primary" onClick={() => void onDraft('zatwierdzony')}>Zatwierdź (człowiek)</Button>
              <Button onClick={() => void onDraft('odrzucony')}>Odrzuć</Button>
            </div>
            <p className="text-xs text-slate-700">Aplikacja nie publikuje komunikatu. Zatwierdzenie jest zapisem decyzji, a kanał publikacji jest poza zakresem demonstracji.</p>
          </div>
        </Panel>

        <Panel title="Deklaracje gotowości działów" subtitle="Zdarzenia scenariusza do wybranej chwili">
          {ready.length === 0 ? <EmptyState text="Do tej chwili nie wpłynęły deklaracje gotowości." /> : (
            <ul className="space-y-1.5 text-sm text-ink">
              {ready.map((r) => (
                <li key={`${r.div}-${r.t}`} className="rounded-md bg-white p-2 ring-1 ring-slate-300">
                  <span className="font-semibold">Dział {r.div}</span>: {r.status} <span className="text-xs text-slate-700">({formatTime(index, r.t)})</span>
                  <div className="text-xs text-slate-800">{r.comment}. {r.forces}</div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}
