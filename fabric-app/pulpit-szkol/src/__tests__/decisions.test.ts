import { describe, expect, it, vi } from 'vitest';

vi.mock('@/services/rayfinClient', () => ({
  isLocalBackend: () => true,
  getRayfinClient: () => {
    throw new Error('Brak klienta w testach');
  },
}));

import {
  priorityDropNeedsNote,
  saveEscalation,
  validateEscalation,
  validateReportDecision,
  type Actor,
  type EscalationDraft,
  type ReportDecisionDraft,
} from '@/services/decisions';

const dyz: Actor = { id: 'u1', name: 'Dyżurny Testowy', role: 'dyżurny krajowy' };
const min: Actor = { id: 'u2', name: 'Minister Testowy', role: 'minister wiodący' };

const decision: ReportDecisionDraft = {
  report_id: 'BS-4826',
  scene_time: '2026-10-09T08:50:00.000Z',
  ai_priority: 'KRYTYCZNY',
  previous_priority: 'KRYTYCZNY',
  new_priority: 'KRYTYCZNY',
  previous_status: 'NOWE',
  new_status: 'PRZEKAZANE',
  recipients: ['POL'],
  justification: 'Zgłoszenie wiarygodne, przekazuję Policji.',
};

const esc: EscalationDraft = {
  recommended_level: 'minister',
  chosen_level: 'minister',
  scope: 'PL',
  scene_time: '2026-10-09T08:50:00.000Z',
  campaign_24h: 200,
  campaign_voivodeships: 9,
  genuine_critical_24h: 0,
  max_kizs: 30,
  justification: 'Fala w wielu województwach.',
};

describe('walidacja decyzji o zgłoszeniu', () => {
  it('poprawna decyzja nie ma błędów', () => {
    expect(validateReportDecision(decision, dyz)).toEqual([]);
  });
  it('wymaga uzasadnienia', () => {
    expect(validateReportDecision({ ...decision, justification: 'ok' }, dyz).length).toBe(1);
  });
  it('przekazanie wymaga odbiorcy', () => {
    expect(validateReportDecision({ ...decision, recipients: [] }, dyz).join(' ')).toContain('odbiorcy');
  });
  it('nie pozwala cofnąć do statusu Nowe', () => {
    expect(validateReportDecision({ ...decision, previous_status: 'W_ANALIZIE', new_status: 'NOWE' }, dyz).join(' ')).toContain('Nowe');
  });
  it('odrzuca decyzję bez zmian', () => {
    expect(validateReportDecision({ ...decision, new_status: 'NOWE', recipients: [] }, dyz).join(' ')).toContain('nic nie zmienia');
  });
  it('obniżenie priorytetu o dwa stopnie wymaga notatki', () => {
    expect(priorityDropNeedsNote('KRYTYCZNY', 'SREDNI')).toBe(true);
    expect(priorityDropNeedsNote('KRYTYCZNY', 'WYSOKI')).toBe(false);
    expect(priorityDropNeedsNote('NISKI', 'KRYTYCZNY')).toBe(false);
  });
});

describe('walidacja eskalacji', () => {
  it('poziom ministra uruchamia tylko minister lub RZZK', () => {
    expect(validateEscalation(esc, dyz).join(' ')).toContain('minister');
    expect(validateEscalation(esc, min)).toEqual([]);
  });
  it('wojewoda wymaga wskazania województwa', () => {
    expect(validateEscalation({ ...esc, chosen_level: 'wojewoda' }, dyz).join(' ')).toContain('województwa');
    expect(validateEscalation({ ...esc, chosen_level: 'wojewoda', scope: '14' }, dyz)).toEqual([]);
  });
  it('wymaga wybrania poziomu', () => {
    expect(validateEscalation({ ...esc, chosen_level: 'brak' }, min).length).toBeGreaterThan(0);
  });
  it('zapis w pamięci dodaje skrót audytu i autora', async () => {
    const rec = await saveEscalation(esc, min);
    expect(rec.audit_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(rec.actor_name).toBe('Minister Testowy');
  });
});
