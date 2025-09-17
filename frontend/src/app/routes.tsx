import { Route, Routes, useParams } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute";
import AuditPage from "../features/admin/pages/AuditPage";
import GameLedgerPage from "../features/admin/pages/GameLedgerPage";
import LedgerAnalysisPage from "../features/admin/pages/LedgerAnalysisPage";
import LiveGameIngestPage from "../features/admin/pages/LiveGameIngestPage";
import PaymentLedgerPage from "../features/admin/pages/PaymentLedgerPage";
import GameIngestPage from "../features/admin/pages/SessionIngestPage";
import VerifiedUsersPage from "../features/admin/pages/VerifiedUsersPage";
import AdvancedAnalyticsPage from "../features/game/pages/AdvancedAnalyticsPage";
import GameSummaryPage from "../features/game/pages/GameSummaryPage";
import RuleBookPage from "../features/rules/pages/RuleBookPage";
import LandingPage from "../pages/Landing/LandingPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/:publicCode" element={<GameSummaryPageWrapper />} />
      <Route path="/ingest/:publicCode" element={
        <ProtectedRoute requireAdmin={true}>
          <GameIngestPage />
        </ProtectedRoute>
      } />
      <Route path="/live/:publicCode" element={
        <ProtectedRoute requireAdmin={true}>
          <LiveGameIngestPage />
        </ProtectedRoute>
      } />
      <Route path="/ledger/:publicCode" element={<GameLedgerPage />} />
      <Route path="/players/:publicCode" element={
        <ProtectedRoute requireAdmin={true}>
          <VerifiedUsersPage />
        </ProtectedRoute>
      } />
      <Route path="/summary/:publicCode" element={<GameSummaryPageWrapper />} />
      <Route path="/rules/:publicCode" element={<RuleBookPageWrapper />} />
      <Route path="/analytics/:publicCode" element={<AdvancedAnalyticsPageWrapper />} />
      <Route path="/ledger-analysis/:publicCode" element={
        <ProtectedRoute requireAdmin={true}>
          <LedgerAnalysisPage />
        </ProtectedRoute>
      } />
      <Route path="/audit/:publicCode" element={
        <ProtectedRoute requireAdmin={true}>
          <AuditPage />
        </ProtectedRoute>
      } />
      <Route path="/payments/:publicCode" element={
        <ProtectedRoute requireAdmin={true}>
          <PaymentLedgerPage />
        </ProtectedRoute>
      } />
    </Routes>
  );
}

function GameSummaryPageWrapper() {
  const { publicCode } = useParams();
  return <GameSummaryPage publicCode={publicCode || ""} />;
}

function RuleBookPageWrapper() {
  const { publicCode } = useParams();
  return <RuleBookPage publicCode={publicCode || ""} />;
}

function AdvancedAnalyticsPageWrapper() {
  const { publicCode } = useParams();
  return <AdvancedAnalyticsPage publicCode={publicCode || ""} />;
}
