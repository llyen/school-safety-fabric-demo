import {
  auditHash,
  PRIORITY_RANK,
  type EscalationLevel,
  type PriorityCode,
  type StatusCode,
  type UserDecision,
} from '@/data/model';

import { getRayfinClient, isLocalBackend } from './rayfinClient';

/**
 * Zapis zwrotny. Zasady:
 * 1. Wpisy sa append-only: zmiana to nowy wpis, obowiazuje najnowszy.
 * 2. AI tylko sugeruje, decyzje podejmuje i uzasadnia czlowiek.
 * 3. Kazda decyzja ma aktora, czas, poprzednia i nowa wartosc, uzasadnienie i skrot kontrolny.
 * Bez backendu Rayfin (localhost) wpisy trafiaja do pamieci, zeby dalo sie pokazac aplikacje offline.
 */

export type UserRole = 'dyżurny krajowy' | 'analityk RCB' | 'minister wiodący' | 'RZZK';
export const USER_ROLES: UserRole[] = ['dyżurny krajowy', 'analityk RCB', 'minister wiodący', 'RZZK'];
/** Poziomy, ktore moze uruchomic dana rola. Egzekwowane w interfejsie, nie w bazie. */
export const ESCALATION_ROLES: UserRole[] = ['minister wiodący', 'RZZK'];

export interface Actor {
  id: string;
  name: string;
  role: UserRole;
}

export const MIN_JUSTIFICATION = 10;

export interface ReportDecisionRecord {
  id: string;
  report_id: string;
  version: number;
  scene_time: string;
  ai_priority: PriorityCode;
  previous_priority: PriorityCode;
  new_priority: PriorityCode;
  previous_status: StatusCode;
  new_status: StatusCode;
  recipients: string;
  justification: string;
  actor_role: string;
  actor_id: string;
  actor_name: string;
  audit_hash: string;
  decided_at: Date;
}

export interface EscalationRecord {
  id: string;
  recommended_level: string;
  chosen_level: string;
  scope: string;
  scene_time: string;
  campaign_24h: number;
  campaign_voivodeships: number;
  genuine_critical_24h: number;
  max_kizs: number;
  justification: string;
  actor_role: string;
  actor_id: string;
  actor_name: string;
  audit_hash: string;
  decided_at: Date;
}

export interface TaskStatusRecord {
  id: string;
  task_id: string;
  admin_division: string;
  spo_code: string;
  status: string;
  comment?: string;
  actor_role: string;
  actor_id: string;
  actor_name: string;
  changed_at: Date;
}

export interface CommsDraftRecord {
  id: string;
  draft_key: string;
  version: number;
  status: 'szkic' | 'zatwierdzony' | 'odrzucony';
  body: string;
  comment?: string;
  actor_role: string;
  actor_id: string;
  actor_name: string;
  changed_at: Date;
}

const memory = {
  ReportDecision: [] as ReportDecisionRecord[],
  EscalationDecision: [] as EscalationRecord[],
  TaskStatus: [] as TaskStatusRecord[],
  CommsDraft: [] as CommsDraftRecord[],
};

type EntityName = keyof typeof memory;

interface EntityApi {
  select(fields: string[]): { orderBy(o: Record<string, string>): { execute(): Promise<unknown[]> } };
  create(payload: unknown): Promise<unknown>;
}

function entityApi(name: EntityName): EntityApi {
  return (getRayfinClient().data as unknown as Record<string, EntityApi>)[name];
}

const FIELDS: Record<EntityName, string[]> = {
  ReportDecision: ['id', 'report_id', 'version', 'scene_time', 'ai_priority', 'previous_priority', 'new_priority', 'previous_status', 'new_status', 'recipients', 'justification', 'actor_role', 'actor_id', 'actor_name', 'audit_hash', 'decided_at'],
  EscalationDecision: ['id', 'recommended_level', 'chosen_level', 'scope', 'scene_time', 'campaign_24h', 'campaign_voivodeships', 'genuine_critical_24h', 'max_kizs', 'justification', 'actor_role', 'actor_id', 'actor_name', 'audit_hash', 'decided_at'],
  TaskStatus: ['id', 'task_id', 'admin_division', 'spo_code', 'status', 'comment', 'actor_role', 'actor_id', 'actor_name', 'changed_at'],
  CommsDraft: ['id', 'draft_key', 'version', 'status', 'body', 'comment', 'actor_role', 'actor_id', 'actor_name', 'changed_at'],
};
const ORDER: Record<EntityName, string> = {
  ReportDecision: 'decided_at',
  EscalationDecision: 'decided_at',
  TaskStatus: 'changed_at',
  CommsDraft: 'changed_at',
};

async function list<T>(name: EntityName): Promise<T[]> {
  if (isLocalBackend()) return [...(memory[name] as unknown as T[])];
  const rows = await entityApi(name).select(FIELDS[name]).orderBy({ [ORDER[name]]: 'desc' }).execute();
  return rows as T[];
}

async function insert<T extends { id: string }>(name: EntityName, record: T): Promise<T> {
  if (isLocalBackend()) {
    (memory[name] as unknown as T[]).unshift(record);
    return record;
  }
  const { id: _ignored, ...payload } = record;
  void _ignored;
  return (await entityApi(name).create(payload)) as T;
}

/* ----------------------- decyzja o zgloszeniu ----------------------- */

export interface ReportDecisionDraft {
  report_id: string;
  scene_time: string;
  ai_priority: PriorityCode;
  previous_priority: PriorityCode;
  new_priority: PriorityCode;
  previous_status: StatusCode;
  new_status: StatusCode;
  recipients: string[];
  justification: string;
}

export function validateReportDecision(d: ReportDecisionDraft, actor: Actor): string[] {
  const errors: string[] = [];
  if (d.justification.trim().length < MIN_JUSTIFICATION)
    errors.push(`Uzasadnienie musi mieć co najmniej ${MIN_JUSTIFICATION} znaków.`);
  if (d.justification.length > 1000) errors.push('Uzasadnienie nie może przekraczać 1000 znaków.');
  if (d.new_status === 'PRZEKAZANE' && d.recipients.length === 0)
    errors.push('Status „Przekazane” wymaga wskazania co najmniej jednego odbiorcy.');
  if (d.new_status === 'NOWE' && d.previous_status !== 'NOWE')
    errors.push('Zgłoszenia nie można cofnąć do statusu „Nowe”.');
  if (!actor.name.trim()) errors.push('Brak danych osoby podejmującej decyzję.');
  if (
    d.new_priority === d.previous_priority &&
    d.new_status === d.previous_status &&
    d.recipients.length === 0
  )
    errors.push('Decyzja nic nie zmienia: wybierz priorytet, status albo odbiorcę.');
  return errors;
}

/** Zmiana priorytetu o wiecej niz jeden stopien w dol wymaga mocniejszego uzasadnienia. */
export function priorityDropNeedsNote(from: PriorityCode, to: PriorityCode): boolean {
  return PRIORITY_RANK[from] - PRIORITY_RANK[to] >= 2;
}

export async function saveReportDecision(
  d: ReportDecisionDraft,
  actor: Actor,
  existing: ReportDecisionRecord[]
): Promise<ReportDecisionRecord> {
  const errors = validateReportDecision(d, actor);
  if (errors.length) throw new Error(errors.join(' '));
  const version = existing.filter((e) => e.report_id === d.report_id).reduce((m, e) => Math.max(m, e.version), 0) + 1;
  const decided_at = new Date();
  const base = {
    report_id: d.report_id,
    version,
    scene_time: d.scene_time,
    ai_priority: d.ai_priority,
    previous_priority: d.previous_priority,
    new_priority: d.new_priority,
    previous_status: d.previous_status,
    new_status: d.new_status,
    recipients: d.recipients.join(','),
    justification: d.justification.trim(),
    actor_role: actor.role,
    actor_id: actor.id,
    actor_name: actor.name,
  };
  const record: ReportDecisionRecord = {
    id: crypto.randomUUID(),
    ...base,
    audit_hash: auditHash({ ...base, at: decided_at.toISOString() }),
    decided_at,
  };
  return insert('ReportDecision', record);
}

export const listReportDecisions = () => list<ReportDecisionRecord>('ReportDecision');

/** Przeksztalca zapisy w nakladke na stan zgloszen. Czas decyzji to czas sceny, nie zegar ukladu. */
export function toUserDecisions(records: ReportDecisionRecord[], sceneMinutes: (iso: string) => number): UserDecision[] {
  return records.map((r) => ({
    report_id: r.report_id,
    version: r.version,
    at: sceneMinutes(r.scene_time),
    new_priority: r.new_priority,
    new_status: r.new_status,
    recipients: r.recipients ? r.recipients.split(',') : [],
  }));
}

/* ---------------------------- eskalacja ---------------------------- */

export interface EscalationDraft {
  recommended_level: EscalationLevel;
  chosen_level: EscalationLevel;
  scope: string;
  scene_time: string;
  campaign_24h: number;
  campaign_voivodeships: number;
  genuine_critical_24h: number;
  max_kizs: number;
  justification: string;
}

export function validateEscalation(d: EscalationDraft, actor: Actor): string[] {
  const errors: string[] = [];
  if (d.chosen_level === 'brak') errors.push('Wybierz poziom eskalacji do uruchomienia.');
  if (d.justification.trim().length < MIN_JUSTIFICATION)
    errors.push(`Uzasadnienie musi mieć co najmniej ${MIN_JUSTIFICATION} znaków.`);
  if ((d.chosen_level === 'minister' || d.chosen_level === 'rzzk') && !ESCALATION_ROLES.includes(actor.role))
    errors.push('Poziom ministra wiodącego i RZZK uruchamia minister wiodący albo przedstawiciel RZZK.');
  if (d.chosen_level === 'wojewoda' && d.scope === 'PL') errors.push('Eskalacja do wojewody wymaga wskazania województwa.');
  return errors;
}

export async function saveEscalation(d: EscalationDraft, actor: Actor): Promise<EscalationRecord> {
  const errors = validateEscalation(d, actor);
  if (errors.length) throw new Error(errors.join(' '));
  const decided_at = new Date();
  const base = {
    recommended_level: d.recommended_level,
    chosen_level: d.chosen_level,
    scope: d.scope,
    scene_time: d.scene_time,
    campaign_24h: d.campaign_24h,
    campaign_voivodeships: d.campaign_voivodeships,
    genuine_critical_24h: d.genuine_critical_24h,
    max_kizs: Math.round(d.max_kizs),
    justification: d.justification.trim(),
    actor_role: actor.role,
    actor_id: actor.id,
    actor_name: actor.name,
  };
  const record: EscalationRecord = {
    id: crypto.randomUUID(),
    ...base,
    audit_hash: auditHash({ ...base, at: decided_at.toISOString() }),
    decided_at,
  };
  return insert('EscalationDecision', record);
}
export const listEscalations = () => list<EscalationRecord>('EscalationDecision');

/* ------------------------------ zadania ------------------------------ */

export const TASK_STATUSES = ['zlecone', 'w_toku', 'wykonane', 'opoznione', 'zablokowane'] as const;

export async function saveTaskStatus(
  input: { task_id: string; admin_division: string; spo_code: string; status: string; comment?: string },
  actor: Actor
): Promise<TaskStatusRecord> {
  if (!TASK_STATUSES.includes(input.status as (typeof TASK_STATUSES)[number]))
    throw new Error('Nieznany status zadania.');
  if (input.status === 'zablokowane' && (input.comment ?? '').trim().length < MIN_JUSTIFICATION)
    throw new Error('Zablokowane zadanie wymaga komentarza z przyczyną (co najmniej 10 znaków).');
  const record: TaskStatusRecord = {
    id: crypto.randomUUID(),
    ...input,
    comment: input.comment?.trim() || undefined,
    actor_role: actor.role,
    actor_id: actor.id,
    actor_name: actor.name,
    changed_at: new Date(),
  };
  return insert('TaskStatus', record);
}
export const listTaskStatuses = () => list<TaskStatusRecord>('TaskStatus');

/* --------------------------- komunikat SPO-3 --------------------------- */

export async function saveDraft(
  input: { draft_key: string; status: CommsDraftRecord['status']; body: string; comment?: string },
  actor: Actor,
  existing: CommsDraftRecord[]
): Promise<CommsDraftRecord> {
  if (input.body.trim().length < 40) throw new Error('Treść komunikatu musi mieć co najmniej 40 znaków.');
  if (input.body.length > 2000) throw new Error('Treść komunikatu nie może przekraczać 2000 znaków.');
  if (input.status === 'zatwierdzony' && !ESCALATION_ROLES.includes(actor.role))
    throw new Error('Komunikat zatwierdza minister wiodący albo przedstawiciel RZZK. System przygotowuje tylko szkic.');
  const version = existing.filter((e) => e.draft_key === input.draft_key).reduce((m, e) => Math.max(m, e.version), 0) + 1;
  const record: CommsDraftRecord = {
    id: crypto.randomUUID(),
    ...input,
    comment: input.comment?.trim() || undefined,
    version,
    actor_role: actor.role,
    actor_id: actor.id,
    actor_name: actor.name,
    changed_at: new Date(),
  };
  return insert('CommsDraft', record);
}
export const listDrafts = () => list<CommsDraftRecord>('CommsDraft');

/** Reset pamieci, tylko dla testow. */
export function resetMemory(): void {
  for (const k of Object.keys(memory) as EntityName[]) memory[k].length = 0;
}
