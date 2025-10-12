import { Route, Routes, useParams } from "react-router-dom";
import { GamePageWrapper } from "../components/GamePageWrapper";
import ProtectedRoute from "../components/ProtectedRoute";
import AuditPage from "../features/admin/pages/AuditPage";
import GameLedgerPage from "../features/admin/pages/GameLedgerPage";
import LedgerAnalysisPage from "../features/admin/pages/LedgerAnalysisPage";
import LiveGameIngestPage from "../features/admin/pages/LiveGameIngestPage";
import GameIngestPage from "../features/admin/pages/SessionIngestPage";
import AdvancedAnalyticsPage from "../features/game/pages/AdvancedAnalyticsPage";
import GameSummaryPage from "../features/game/pages/GameSummaryPage";
import PaymentLedgerPage from "../features/payment/pages/PaymentLedgerPage";
import RuleBookPage from "../features/rules/pages/RuleBookPage";
import LandingPage from "../pages/Landing/LandingPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/:publicCode" element={<GameSummaryPageWrapper />} />
      <Route path="/ingest/:publicCode" element={<GameIngestPageWrapper />} />
      <Route path="/live/:publicCode" element={<LiveGameIngestPageWrapper />} />
      <Route path="/ledger/:publicCode" element={<GameLedgerPageWrapper />} />
      <Route path="/summary/:publicCode" element={<GameSummaryPageWrapper />} />
      <Route path="/rules/:publicCode" element={<RuleBookPageWrapper />} />
      <Route path="/analytics/:publicCode" element={<AdvancedAnalyticsPageWrapper />} />
      <Route path="/ledger-analysis/:publicCode" element={<LedgerAnalysisPageWrapper />} />
      <Route path="/audit/:publicCode" element={<AuditPageWrapper />} />
      <Route path="/payments/:publicCode" element={<PaymentLedgerPageWrapper />} />
    </Routes>
  );
}

function GameSummaryPageWrapper() {
  const { publicCode } = useParams();
  return (
    <GamePageWrapper publicCode={publicCode || ""}>
      <GameSummaryPage publicCode={publicCode || ""} />
    </GamePageWrapper>
  );
}

function RuleBookPageWrapper() {
  const { publicCode } = useParams();
  return (
    <GamePageWrapper publicCode={publicCode || ""}>
      <RuleBookPage publicCode={publicCode || ""} />
    </GamePageWrapper>
  );
}

function AdvancedAnalyticsPageWrapper() {
  const { publicCode } = useParams();
  return (
    <GamePageWrapper publicCode={publicCode || ""}>
      <AdvancedAnalyticsPage publicCode={publicCode || ""} />
    </GamePageWrapper>
  );
}

function PaymentLedgerPageWrapper() {
  const { publicCode } = useParams();
  return (
    <GamePageWrapper publicCode={publicCode || ""}>
      <PaymentLedgerPage />
    </GamePageWrapper>
  );
}

function GameLedgerPageWrapper() {
  const { publicCode } = useParams();
  return (
    <GamePageWrapper publicCode={publicCode || ""}>
      <GameLedgerPage />
    </GamePageWrapper>
  );
}

function GameIngestPageWrapper() {
  const { publicCode } = useParams();
  return (
    <GamePageWrapper publicCode={publicCode || ""}>
      <ProtectedRoute requireAdmin={true}>
        <GameIngestPage />
      </ProtectedRoute>
    </GamePageWrapper>
  );
}

function LiveGameIngestPageWrapper() {
  const { publicCode } = useParams();
  return (
    <GamePageWrapper publicCode={publicCode || ""}>
      <ProtectedRoute requireAdmin={true}>
        <LiveGameIngestPage />
      </ProtectedRoute>
    </GamePageWrapper>
  );
}

function LedgerAnalysisPageWrapper() {
  const { publicCode } = useParams();
  return (
    <GamePageWrapper publicCode={publicCode || ""}>
      <ProtectedRoute requireAdmin={true}>
        <LedgerAnalysisPage />
      </ProtectedRoute>
    </GamePageWrapper>
  );
}

function AuditPageWrapper() {
  const { publicCode } = useParams();
  return (
    <GamePageWrapper publicCode={publicCode || ""}>
      <ProtectedRoute requireAdmin={true}>
        <AuditPage />
      </ProtectedRoute>
    </GamePageWrapper>
  );
}
