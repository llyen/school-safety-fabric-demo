import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import {
  indexScene,
  latestUserDecisions,
  type Report,
  type Scene,
  type SceneIndex,
  type School,
  type UserDecision,
} from '@/data/model';
import { useAuth } from '@/hooks/AuthContext';
import {
  listDrafts,
  listEscalations,
  listReportDecisions,
  listTaskStatuses,
  toUserDecisions,
  type Actor,
  type CommsDraftRecord,
  type EscalationRecord,
  type ReportDecisionRecord,
  type TaskStatusRecord,
  type UserRole,
} from '@/services/decisions';

export const STEP_MIN = 15;

interface ScenarioValue {
  index: SceneIndex | null;
  loading: boolean;
  error: string | null;
  /** Czas sceny w minutach od poczatku okna (D-3 00:00). */
  t: number;
  setT: (t: number) => void;
  playing: boolean;
  togglePlay: () => void;
  speed: number;
  setSpeed: (ms: number) => void;
  actor: Actor;
  setRole: (role: UserRole) => void;
  reportDecisions: ReportDecisionRecord[];
  overrides: Map<string, UserDecision>;
  escalations: EscalationRecord[];
  taskStatuses: TaskStatusRecord[];
  drafts: CommsDraftRecord[];
  refresh: () => Promise<void>;
  writebackError: string | null;
  selectedVoivodeship: string;
  setSelectedVoivodeship: (code: string) => void;
}

const ScenarioContext = createContext<ScenarioValue | undefined>(undefined);
const ROLE_KEY = 'szkoly.role';

async function getJson<T>(name: string): Promise<T> {
  const r = await fetch(`${import.meta.env.BASE_URL}data/${name}`);
  if (!r.ok) throw new Error(`Nie udało się wczytać pliku ${name} (HTTP ${r.status}).`);
  return (await r.json()) as T;
}

export function ScenarioProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [index, setIndex] = useState<SceneIndex | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [t, setTState] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(700);
  const [role, setRoleState] = useState<UserRole>(() => (localStorage.getItem(ROLE_KEY) as UserRole) || 'dyżurny krajowy');
  const [reportDecisions, setReportDecisions] = useState<ReportDecisionRecord[]>([]);
  const [escalations, setEscalations] = useState<EscalationRecord[]>([]);
  const [taskStatuses, setTaskStatuses] = useState<TaskStatusRecord[]>([]);
  const [drafts, setDrafts] = useState<CommsDraftRecord[]>([]);
  const [writebackError, setWritebackError] = useState<string | null>(null);
  const [selectedVoivodeship, setSelectedVoivodeship] = useState('');
  const timer = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getJson<Scene>('scene.json'), getJson<Report[]>('reports.json'), getJson<School[]>('schools.json')])
      .then(([scene, reports, schools]) => {
        if (cancelled) return;
        setIndex(indexScene(scene, reports, schools));
        // Start w D0 o 10:00: BS-4826 czeka jeszcze na decyzje dyzurnego.
        setTState((scene.meta.d0Hour + 10) * 60);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refresh = useCallback(async () => {
    try {
      const [a, b, c, d] = await Promise.all([listReportDecisions(), listEscalations(), listTaskStatuses(), listDrafts()]);
      setReportDecisions(a);
      setEscalations(b);
      setTaskStatuses(c);
      setDrafts(d);
      setWritebackError(null);
    } catch (e: unknown) {
      setWritebackError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const maxT = index ? index.scene.meta.hours * 60 - STEP_MIN : 0;

  useEffect(() => {
    if (!playing || !index) return;
    timer.current = window.setInterval(() => {
      setTState((x) => (x + 60 > maxT ? 0 : x + 60));
    }, speed);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [playing, speed, index, maxT]);

  const setT = useCallback(
    (v: number) => {
      setPlaying(false);
      setTState(Math.max(0, Math.min(v, maxT)));
    },
    [maxT]
  );

  const setRole = useCallback((r: UserRole) => {
    setRoleState(r);
    localStorage.setItem(ROLE_KEY, r);
  }, []);

  const actor: Actor = useMemo(
    () => ({ id: user?.id ?? 'local-user', name: user?.name ?? user?.email ?? 'Użytkownik demonstracyjny', role }),
    [user, role]
  );

  const overrides = useMemo(() => {
    if (!index) return new Map<string, UserDecision>();
    const toMin = (iso: string) => (Date.parse(iso) - index.startMs) / 60000;
    return latestUserDecisions(toUserDecisions(reportDecisions, toMin));
  }, [index, reportDecisions]);

  const value: ScenarioValue = useMemo(
    () => ({
      index, loading, error, t, setT, playing,
      togglePlay: () => setPlaying((p) => !p),
      speed, setSpeed, actor, setRole, reportDecisions, overrides, escalations, taskStatuses, drafts,
      refresh, writebackError, selectedVoivodeship, setSelectedVoivodeship,
    }),
    [index, loading, error, t, setT, playing, speed, actor, setRole, reportDecisions, overrides, escalations, taskStatuses, drafts, refresh, writebackError, selectedVoivodeship]
  );

  return <ScenarioContext.Provider value={value}>{children}</ScenarioContext.Provider>;
}

export function useScenario(): ScenarioValue {
  const ctx = useContext(ScenarioContext);
  if (!ctx) throw new Error('useScenario musi być użyte wewnątrz ScenarioProvider');
  return ctx;
}
