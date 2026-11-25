import { entity, role, text, date, uuid } from '@microsoft/rayfin-core';

/**
 * Status zadania dzialu administracji lub SPO. Zmiana statusu to nowy wpis,
 * obowiazuje najnowszy dla pary task_id.
 */
@entity()
@role('authenticated', ['create', 'read'])
export class TaskStatus {
  @uuid() id!: string;
  @text({ max: 20 }) task_id!: string;
  @text({ max: 10 }) admin_division!: string;
  @text({ max: 10 }) spo_code!: string;
  /** zlecone | w_toku | wykonane | opoznione | zablokowane */
  @text({ max: 20 }) status!: string;
  @text({ max: 500 }) comment?: string;
  @text({ max: 20 }) actor_role!: string;
  @text({ max: 200 }) actor_id!: string;
  @text({ max: 200 }) actor_name!: string;
  @date() changed_at!: Date;
}
