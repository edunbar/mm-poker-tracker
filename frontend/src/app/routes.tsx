import { Routes, Route } from "react-router-dom";
import LandingPage from "../pages/Landing/LandingPage";
import GameIngestPage from "../features/admin/pages/SessionIngestPage";
import LiveGameIngestPage from "../features/admin/pages/LiveGameIngestPage";
import GameLedgerPage from "../features/admin/pages/GameLedgerPage";
import PaymentLedgerPage from "../features/admin/pages/PaymentLedgerPage";
import VerifiedUsersPage from "../features/admin/pages/VerifiedUsersPage";
import GameSummaryPage from "../features/game/pages/GameSummaryPage";
import AuditPage from "../features/admin/pages/AuditPage";
import LedgerAnalysisPage from "../features/admin/pages/LedgerAnalysisPage";
import ProtectedRoute from "../components/ProtectedRoute";
import { useParams } from "react-router-dom";

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
