import { entity, role, text, int, date, uuid } from '@microsoft/rayfin-core';

/**
 * Szkic komunikatu SPO-3. Szkic przygotowuje system, publikacja wymaga
 * zatwierdzenia przez czlowieka. Zatwierdzenie i odrzucenie to nowe wpisy.
 */
@entity()
@role('authenticated', ['create', 'read'])
export class CommsDraft {
  @uuid() id!: string;
  @text({ max: 40 }) draft_key!: string;
  @int() version!: number;
  /** szkic | zatwierdzony | odrzucony */
  @text({ max: 20 }) status!: string;
  @text({ max: 2000 }) body!: string;
  @text({ max: 500 }) comment?: string;
  @text({ max: 20 }) actor_role!: string;
  @text({ max: 200 }) actor_id!: string;
  @text({ max: 200 }) actor_name!: string;
  @date() changed_at!: Date;
}
