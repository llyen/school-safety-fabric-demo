import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AuthPage } from '@/components/AuthPage';
import { Layout } from '@/components/Layout';
import { useAuth } from '@/hooks/AuthContext';
import { ScenarioProvider, useScenario } from '@/hooks/ScenarioContext';
import { CampaignsPage } from '@/pages/CampaignsPage';
import { EscalationPage } from '@/pages/EscalationPage';
import { NationalPage } from '@/pages/NationalPage';
import { QueuePage } from '@/pages/QueuePage';
import { ResourcesPage } from '@/pages/ResourcesPage';

function AuthGuard({ children, requireAuth }: { children: React.ReactNode; requireAuth: boolean }) {
  const { isAuthenticated, loading } = useAuth();
  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-lav text-ink">Uwierzytelnianie…</div>;
  }
  if (requireAuth && !isAuthenticated) return <Navigate to="/auth" replace />;
  if (!requireAuth && isAuthenticated) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function SceneGate({ children }: { children: React.ReactNode }) {
  const { loading, error } = useScenario();
  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-lav text-ink">Wczytywanie sceny…</div>;
  }
  if (error) {
    return <div className="flex min-h-screen items-center justify-center bg-lav px-6 text-center text-red-800">{error}</div>;
  }
  return <>{children}</>;
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard requireAuth>
      <ScenarioProvider>
        <SceneGate>
          <Layout>{children}</Layout>
        </SceneGate>
      </ScenarioProvider>
    </AuthGuard>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/auth" element={<AuthGuard requireAuth={false}><AuthPage /></AuthGuard>} />
        <Route path="/" element={<Shell><NationalPage /></Shell>} />
        <Route path="/kolejka" element={<Shell><QueuePage /></Shell>} />
        <Route path="/kampanie" element={<Shell><CampaignsPage /></Shell>} />
        <Route path="/eskalacja" element={<Shell><EscalationPage /></Shell>} />
        <Route path="/zasoby" element={<Shell><ResourcesPage /></Shell>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
