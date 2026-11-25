import { useMemo, useState } from 'react';

import { Badge, Button, Field, Panel, PriorityBadge, StatusBadge, Toast, inputClass } from '@/components/ui';
import {
  CATEGORY_LABEL,
  PRIORITIES,
  PRIORITY_LABEL,
  RECIPIENT_LABEL,
  SIGNAL_LABEL,
  STATUSES,
  STATUS_LABEL,
  formatIso,
  formatTime,
  PRIORITY_RANK,
  type PriorityCode,
  type Report,
  type ReportState,
  type StatusCode,
} from '@/data/model';
import { useScenario } from '@/hooks/ScenarioContext';
import { priorityDropNeedsNote, saveReportDecision, validateReportDecision } from '@/services/decisions';

const RECIPIENTS = ['POL', 'DIR', 'PED', 'DYZ'] as const;

export function ReportDetail({ report, state }: { report: Report; state: ReportState }) {
  const { index, t, actor, reportDecisions, refresh } = useScenario();
  const [priority, setPriority] = useState<PriorityCode>(state.priority);
  const [status, setStatus] = useState<StatusCode>(state.status);
  const [recipients, setRecipients] = useState<string[]>(state.recipients.filter((r) => RECIPIENTS.includes(r as (typeof RECIPIENTS)[number])));
  const [justification, setJustification] = useState('');
  const [errors, setErrors] = useState<string[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const mine = useMemo(() => reportDecisions.filter((d) => d.report_id === report.id).sort((a, b) => a.version - b.version), [reportDecisions, report.id]);
  if (!index) return null;
  const school = index.schoolById.get(report.sch);
  const county = index.countyById.get(report.c);

  const draft = {
    report_id: report.id,
    scene_time: new Date(index.startMs + t * 60000).toISOString(),
    ai_priority: report.ai.pri,
    previous_priority: state.priority,
    new_priority: priority,
    previous_status: state.status,
    new_status: status,
    recipients,
    justification,
  };

  const submit = async () => {
    const errs = validateReportDecision(draft, actor);
    if (priorityDropNeedsNote(state.priority, priority) && justification.trim().length < 30) {
      errs.push('Obniżenie priorytetu o dwa stopnie lub więcej wymaga uzasadnienia na co najmniej 30 znaków.');
    }
    setErrors(errs);
    if (errs.length) return;
    setSaving(true);
    try {
      await saveReportDecision(draft, actor, reportDecisions);
      await refresh();
      setJustification('');
      setToast(`Zapisano decyzję dla ${report.id}.`);
    } catch (e) {
      setErrors([e instanceof Error ? e.message : String(e)]);
    } finally {
      setSaving(false);
    }
  };

  const toggle = (code: string) => setRecipients((r) => (r.includes(code) ? r.filter((x) => x !== code) : [...r, code]));
  const currentRank = STATUSES.indexOf(state.status);

  return (
    <Panel
      title={`Zgłoszenie ${report.id}`}
      subtitle={`${formatTime(index, report.t)} · ${CATEGORY_LABEL[report.cat] ?? report.cat}`}
      right={
        <div className="flex flex-wrap justify-end gap-1.5">
          <PriorityBadge priority={report.ai.pri} kind="AI" />
          {state.decisionPriority && <PriorityBadge priority={state.decisionPriority} kind="DECYZJA" />}
          <StatusBadge status={state.status} />
        </div>
      }
    >
      <div className="space-y-4 text-sm text-ink">
        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-slate-800">Szkoła</div>
          <div>{report.sn}</div>
          <div className="text-xs text-slate-700">
            {school?.loc}, powiat {county?.name}, woj. {index.voivName.get(report.v)}
            {school ? `, uczniów w szkole: ${school.students}` : ''}
          </div>
        </div>
        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-slate-800">Treść zgłoszenia (anonimowa)</div>
          <blockquote className="mt-1 rounded-md bg-bs-50 p-3 text-ink">{report.text}</blockquote>
          {report.link ? <p className="mt-1 text-xs text-slate-700">Zgłoszenie zawiera odnośnik, treść nie jest wyświetlana.</p> : null}
        </div>

        <div className="rounded-md bg-white p-3 ring-1 ring-bs">
          <div className="flex items-center justify-between">
            <div className="text-xs font-bold uppercase tracking-wide text-bs">Sugestia AI (tylko sugestia)</div>
            <span className="text-xs tabular-nums text-slate-800">pewność {(report.ai.conf * 100).toFixed(0)}%, wynik {report.ai.score.toFixed(2)}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <PriorityBadge priority={report.ai.pri} kind="AI" />
            <span>Kategoria: {CATEGORY_LABEL[report.ai.cat] ?? report.ai.cat}</span>
            <span>Odbiorca: {RECIPIENT_LABEL[report.ai.rec] ?? report.ai.rec}</span>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {report.ai.sig.length === 0 ? (
              <span className="text-xs text-slate-700">Brak wykrytych sygnałów.</span>
            ) : (
              report.ai.sig.map((s) => (
                <Badge key={s} className="bg-bs-100 text-bsdark">{SIGNAL_LABEL[s] ?? s}</Badge>
              ))
            )}
          </div>
          {report.cl !== null && (
            <p className="mt-2 text-xs text-slate-800">
              Zgłoszenie należy do klastra podobnych zgłoszeń nr {report.cl}.{' '}
              {report.keep ? 'Zostało zachowane w kolejce do oceny człowieka.' : 'Detektor kampanii wyciszyłby je w kolejce, dyżurny może je przywrócić.'}
            </p>
          )}
        </div>

        <div>
          <div className="text-xs font-bold uppercase tracking-wide text-slate-800">Przebieg</div>
          <ul className="mt-1 space-y-0.5 text-xs text-ink">
            <li>{formatTime(index, report.t)}: zgłoszenie wpłynęło, status Nowe</li>
            {report.dec.t !== null && report.dec.t <= t && (
              <li>
                {formatTime(index, report.dec.t)}: decyzja dyżurnego {report.dec.officer}, priorytet {PRIORITY_LABEL[report.dec.pri]}, opóźnienie {report.dec.delay.toFixed(0)} min (kolejka {report.dec.queue})
              </li>
            )}
            {report.ho.filter((x) => x[0] !== null && x[0] <= t).map((x, i) => (
              <li key={i}>{formatTime(index, x[0])}: przekazano do {RECIPIENT_LABEL[x[1]] ?? x[1]}{x[3] ? ` (${x[3]})` : ''}</li>
            ))}
            {report.tc !== null && report.tc <= t && <li>{formatTime(index, report.tc)}: zamknięte</li>}
          </ul>
        </div>

        <form
          className="space-y-3 rounded-md bg-lav p-3"
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <div className="text-xs font-bold uppercase tracking-wide text-bs">Decyzja dyżurnego</div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Priorytet" hint={`Sugestia AI: ${PRIORITY_LABEL[report.ai.pri]}`}>
              <select className={inputClass} value={priority} onChange={(e) => setPriority(e.target.value as PriorityCode)}>
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>{PRIORITY_LABEL[p]}</option>
                ))}
              </select>
            </Field>
            <Field label="Status">
              <select className={inputClass} value={status} onChange={(e) => setStatus(e.target.value as StatusCode)}>
                {STATUSES.map((s, i) => (
                  <option key={s} value={s} disabled={i < currentRank}>{STATUS_LABEL[s]}</option>
                ))}
              </select>
            </Field>
          </div>
          <fieldset>
            <legend className="mb-1 text-xs font-bold uppercase tracking-wide text-slate-800">Przekazanie do</legend>
            <div className="flex flex-wrap gap-3">
              {RECIPIENTS.map((code) => (
                <label key={code} className="flex items-center gap-1.5 text-sm">
                  <input type="checkbox" className="accent-bs" checked={recipients.includes(code)} onChange={() => toggle(code)} />
                  {RECIPIENT_LABEL[code]}
                </label>
              ))}
              <Button variant="ghost" onClick={() => setRecipients([report.ai.rec])} className="py-0">
                Zastosuj sugestię AI
              </Button>
            </div>
          </fieldset>
          <Field label="Uzasadnienie (wymagane)" hint="Zapisywane w audycie razem z osobą i czasem. Nie wpisuj danych osobowych.">
            <textarea className={inputClass} rows={3} value={justification} maxLength={1000} onChange={(e) => setJustification(e.target.value)} />
          </Field>
          {errors.length > 0 && (
            <ul role="alert" className="list-disc rounded-md bg-red-100 py-2 pl-7 pr-3 text-sm text-red-900">
              {errors.map((e) => <li key={e}>{e}</li>)}
            </ul>
          )}
          <div className="flex items-center gap-3">
            <Button type="submit" variant="primary" disabled={saving}>Zapisz decyzję</Button>
            <span className="text-xs text-slate-700">
              {actor.name}, rola: {actor.role}. {PRIORITY_RANK[priority] < PRIORITY_RANK[report.ai.pri] ? 'Wybrany priorytet jest niższy niż sugestia AI.' : ''}
            </span>
          </div>
        </form>

        {mine.length > 0 && (
          <div>
            <div className="text-xs font-bold uppercase tracking-wide text-slate-800">Audyt zapisanych decyzji</div>
            <ul className="mt-1 space-y-2 text-xs text-ink">
              {mine.map((d) => (
                <li key={d.id} className="rounded-md bg-white p-2 ring-1 ring-slate-300">
                  <div className="font-semibold">
                    v{d.version} · {d.actor_name} ({d.actor_role}) · czas sceny {formatIso(index, (Date.parse(d.scene_time) - index.startMs) / 60000)}
                  </div>
                  <div>
                    Priorytet {PRIORITY_LABEL[d.previous_priority]} na {PRIORITY_LABEL[d.new_priority]}, status {STATUS_LABEL[d.previous_status]} na {STATUS_LABEL[d.new_status]}
                    {d.recipients ? `, odbiorcy: ${d.recipients}` : ''}
                  </div>
                  <div>Uzasadnienie: {d.justification}</div>
                  <div className="text-slate-700">Skrót kontrolny {d.audit_hash.slice(0, 16)}…</div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <Toast message={toast} onDone={() => setToast(null)} />
    </Panel>
  );
}
