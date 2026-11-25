import { entity, role, text, int, date, uuid } from '@microsoft/rayfin-core';

/**
 * Uruchomienie eskalacji (powiat, wojewoda lub kurator, minister wiodacy, RZZK).
 * System rekomenduje poziom, czlowiek wybiera. Zapisujemy migawke wskaznikow z
 * chwili decyzji, zeby uzasadnienie bylo czytelne po zmianie sytuacji.
 */
@entity()
@role('authenticated', ['create', 'read'])
export class EscalationDecision {
  @uuid() id!: string;
  /** powiat | wojewoda | minister | rzzk */
  @text({ max: 12 }) recommended_level!: string;
  @text({ max: 12 }) chosen_level!: string;
  /** Kod wojewodztwa albo PL dla zakresu krajowego. */
  @text({ max: 4 }) scope!: string;
  @text({ max: 30 }) scene_time!: string;
  @int() campaign_24h!: number;
  @int() campaign_voivodeships!: number;
  @int() genuine_critical_24h!: number;
  @int() max_kizs!: number;
  @text({ max: 1000 }) justification!: string;
  @text({ max: 20 }) actor_role!: string;
  @text({ max: 200 }) actor_id!: string;
  @text({ max: 200 }) actor_name!: string;
  @text({ max: 64 }) audit_hash!: string;
  @date() decided_at!: Date;
}
