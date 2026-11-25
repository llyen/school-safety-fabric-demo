import { entity, role, text, int, date, uuid } from '@microsoft/rayfin-core';

/**
 * Decyzja dyzurnego o zgloszeniu BS-xxxx. Wpis jest zdarzeniem audytu:
 * nie jest aktualizowany ani usuwany, a biezacy stan zgloszenia to ostatni
 * wpis dla danego report_id. Sugestia AI jest zapisywana obok decyzji,
 * ale decyzja zawsze nalezy do czlowieka.
 */
@entity()
@role('authenticated', ['create', 'read'])
export class ReportDecision {
  @uuid() id!: string;
  @text({ max: 20 }) report_id!: string;
  @int() version!: number;
  @text({ max: 30 }) scene_time!: string;
  @text({ max: 12 }) ai_priority!: string;
  @text({ max: 12 }) previous_priority!: string;
  @text({ max: 12 }) new_priority!: string;
  @text({ max: 12 }) previous_status!: string;
  @text({ max: 12 }) new_status!: string;
  /** Kody odbiorcow rozdzielone przecinkami: POL, DIR, PED, DYZ. */
  @text({ max: 60 }) recipients!: string;
  @text({ max: 1000 }) justification!: string;
  @text({ max: 20 }) actor_role!: string;
  @text({ max: 200 }) actor_id!: string;
  @text({ max: 200 }) actor_name!: string;
  @text({ max: 64 }) audit_hash!: string;
  @date() decided_at!: Date;
}
