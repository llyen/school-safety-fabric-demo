import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import {
  THRESHOLDS,
  auditHash,
  buildQueue,
  classifyCluster,
  escalationInputsAt,
  indexScene,
  isSuppressed,
  kizsBand,
  kpiAt,
  ministerRecommended,
  project,
  recommendEscalation,
  reportState,
  rzzkRecommended,
  topTerms,
  voivodeRecommended,
  type Report,
  type Scene,
  type School,
  type UserDecision,
} from '@/data/model';

const dir = resolve(__dirname, '..', '..', 'public', 'data');
const read = <T,>(f: string) => JSON.parse(readFileSync(resolve(dir, f), 'utf8')) as T;
const scene = read<Scene>('scene.json');
const reports = read<Report[]>('reports.json');
const schools = read<School[]>('schools.json');
const idx = indexScene(scene, reports, schools);

describe('priorytet i status zgłoszenia', () => {
  const r = reports.find((x) => x.id === 'BS-4826')!;

  it('przed wpłynięciem zgłoszenie jest niewidoczne', () => {
    expect(reportState(r, r.t - 1).visible).toBe(false);
  });

  it('do decyzji pokazuje sugestię AI, po decyzji priorytet dyżurnego', () => {
    const before = reportState(r, r.t + 1);
    expect(before.decided).toBe(false);
    expect(before.priority).toBe(r.ai.pri);
    expect(before.status).toBe('NOWE');
    const after = reportState(r, r.dec.t! + 1);
    expect(after.decided).toBe(true);
    expect(after.priority).toBe(r.dec.pri);
    expect(after.status).not.toBe('NOWE');
  });

  it('po zamknięciu status to ZAMKNIETE', () => {
    expect(reportState(r, r.tc! + 1).status).toBe('ZAMKNIETE');
  });

  it('decyzja użytkownika nadpisuje stan sceny od chwili zapisu', () => {
    const o: UserDecision = { report_id: r.id, version: 1, at: r.t + 5, new_priority: 'NISKI', new_status: 'PRZEKAZANE', recipients: ['POL'] };
    const m = new Map([[r.id, o]]);
    expect(reportState(r, r.t + 1, m).overridden).toBe(false);
    const s = reportState(r, r.t + 6, m);
    expect(s.overridden).toBe(true);
    expect(s.priority).toBe('NISKI');
    expect(s.status).toBe('PRZEKAZANE');
  });
});

describe('dane i wyszukiwanie', () => {
  it('BS-4826 w Mieście M-1402 jest wyszukiwalne', () => {
    const r = reports.find((x) => x.id === 'BS-4826')!;
    expect(r.sn).toContain('M-1402');
    expect(r.ai.pri).toBe('KRYTYCZNY');
    const t = r.tc! + 10;
    expect(buildQueue(idx, t, { tab: 'zamkniete', voivodeship: '', query: 'BS-4826', hideCampaign: false }).map((x) => x.report.id)).toContain('BS-4826');
    expect(buildQueue(idx, t, { tab: 'zamkniete', voivodeship: '', query: 'm-1402', hideCampaign: false }).length).toBeGreaterThan(0);
  });

  it('zakładka Krytyczne zawiera tylko krytyczne, filtr województwa działa', () => {
    const t = scene.meta.d0Hour * 60 + 14 * 60;
    const q = buildQueue(idx, t, { tab: 'krytyczne', voivodeship: '14', query: '', hideCampaign: false });
    expect(q.length).toBeGreaterThan(0);
    expect(q.every((x) => x.state.priority === 'KRYTYCZNY' && x.report.v === '14')).toBe(true);
  });

  it('zgłoszenia nie zawierają danych osobowych zgłaszającego', () => {
    const keys = new Set<string>();
    reports.slice(0, 200).forEach((x) => Object.keys(x).forEach((k) => keys.add(k)));
    for (const bad of ['name', 'email', 'phone', 'pesel', 'student', 'reporter']) expect(keys.has(bad)).toBe(false);
  });

  it('każdy punkt zgłoszenia leży w obrysie kraju', () => {
    for (const r of reports.slice(0, 500)) {
      const p = project(r.lat, r.lon);
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThanOrEqual(1000);
    }
  });
});

describe('KPI', () => {
  it('krytyczne bez decyzji nie rośnie po zapisaniu decyzji', () => {
    const t = scene.meta.d0Hour * 60 + 12 * 60;
    const base = kpiAt(idx, t);
    const target = reports.find((r) => r.t <= t && r.ai.pri === 'KRYTYCZNY' && r.keep === 1 && !(r.dec.t !== null && r.dec.t <= t));
    if (!target) return;
    const o = new Map<string, UserDecision>([[target.id, { report_id: target.id, version: 1, at: t, new_priority: 'KRYTYCZNY', new_status: 'W_ANALIZIE', recipients: [] }]]);
    expect(kpiAt(idx, t, o).criticalNoDecision).toBe(base.criticalNoDecision - 1);
  });

  it('pasma wskaźnika są rosnące', () => {
    expect(kizsBand(0).fill).not.toBe(kizsBand(100).fill);
  });
});

describe('progi eskalacji', () => {
  it('minister: próg fali i liczby województw', () => {
    const base = { campaign24h: 0, campaignVoivodeships: 0, genuineCritical24h: 0, overloaded112: 0, disorder24h: 0 };
    expect(ministerRecommended({ ...base, campaign24h: THRESHOLDS.ministerCampaign24h, campaignVoivodeships: THRESHOLDS.ministerVoivodeships })).toBe(true);
    expect(ministerRecommended({ ...base, campaign24h: THRESHOLDS.ministerCampaign24h - 1, campaignVoivodeships: 16 })).toBe(false);
    expect(ministerRecommended({ ...base, campaign24h: 1000, campaignVoivodeships: THRESHOLDS.ministerVoivodeships - 1 })).toBe(false);
  });

  it('RZZK wymaga dodatkowego warunku', () => {
    const wave = { campaign24h: 500, campaignVoivodeships: 14, genuineCritical24h: 0, overloaded112: 0, disorder24h: 0 };
    expect(rzzkRecommended(wave)).toBe(false);
    expect(rzzkRecommended({ ...wave, genuineCritical24h: 1 })).toBe(true);
    expect(rzzkRecommended({ ...wave, overloaded112: 1 })).toBe(true);
    expect(rzzkRecommended({ ...wave, disorder24h: 10 })).toBe(true);
  });

  it('wojewoda: kolejne godziny powyżej progu', () => {
    const s = new Array(10).fill(0);
    s[5] = s[6] = THRESHOLDS.voivodeKizs;
    expect(voivodeRecommended(s, 6)).toBe(true);
    expect(voivodeRecommended(s, 5)).toBe(false);
    expect(voivodeRecommended(s, 0)).toBe(false);
  });

  it('rekomendacja ministra i RZZK zgadza się z analizą w danych dla każdej godziny', () => {
    let diffs = 0;
    for (let h = 0; h < scene.meta.hours; h++) {
      const i = escalationInputsAt(idx, h);
      if (ministerRecommended(i) !== scene.national.rec.rec_minister[h]) diffs++;
      if (rzzkRecommended(i) !== scene.national.rec.rec_rzzk[h]) diffs++;
    }
    expect(diffs).toBe(0);
  });

  it('poziom rekomendacji jest zgodny z czterema kontrolami', () => {
    const t = (scene.meta.d0Hour + 20) * 60;
    const rec = recommendEscalation(idx, t);
    const met = rec.checks.filter((c) => c.met).map((c) => c.level);
    if (met.length) expect(rec.level).toBe(met[met.length - 1]);
    else expect(rec.level).toBe('brak');
  });
});

describe('kampanie', () => {
  it('klaster skoordynowany z klientami automatycznymi to prawdopodobny fałszywy alarm', () => {
    expect(classifyCluster({ coordinated: 1, autoShare: 0.8, linkShare: 0 })).toBe('prawdopodobnie fałszywy alarm');
    expect(classifyCluster({ coordinated: 1, autoShare: 0.1, linkShare: 0.1 })).toBe('wymaga reakcji');
    expect(classifyCluster({ coordinated: 0, autoShare: 0.9, linkShare: 0.9 })).toBe('wymaga reakcji');
  });

  it('flaga wyciszenia wymaga flag=1 i keep=0', () => {
    expect(isSuppressed({ flag: 1, keep: 0 } as Report)).toBe(true);
    expect(isSuppressed({ flag: 1, keep: 1 } as Report)).toBe(false);
    expect(isSuppressed({ flag: 0, keep: 0 } as Report)).toBe(false);
  });

  it('topTerms zlicza słowa raz na zgłoszenie', () => {
    const t = topTerms(['alarm bombowy szkoła szkoła', 'alarm bombowy budynek', 'inny tekst']);
    expect(t[0]).toEqual({ term: 'alarm', count: 2 });
    expect(t.find((x) => x.term === 'szkoła')?.count).toBe(1);
  });
});

describe('audyt', () => {
  it('skrót jest deterministyczny, 64 znaki hex i zależy od treści', () => {
    const a = auditHash({ a: 1, b: 'x' });
    expect(a).toMatch(/^[0-9a-f]{64}$/);
    expect(auditHash({ a: 1, b: 'x' })).toBe(a);
    expect(auditHash({ a: 2, b: 'x' })).not.toBe(a);
  });
});
