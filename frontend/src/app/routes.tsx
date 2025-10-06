import { Route, Routes, useParams } from "react-router-dom";
import { GamePageWrapper } from "../components/GamePageWrapper";
import ProtectedRoute from "../components/ProtectedRoute";
import AuditPage from "../features/admin/pages/AuditPage";
import GameLedgerPage from "../features/admin/pages/GameLedgerPage";
import LedgerAnalysisPage from "../features/admin/pages/LedgerAnalysisPage";
import LiveGameIngestPage from "../features/admin/pages/LiveGameIngestPage";
import GameIngestPage from "../features/admin/pages/SessionIngestPage";
import ClaimGamePage from "../features/auth/pages/ClaimGamePage";
import CreateGamePage from "../features/auth/pages/CreateGamePage";
import ForgotPasswordPage from "../features/auth/pages/ForgotPasswordPage";
import LoginPage from "../features/auth/pages/LoginPage";
import MyGamesPage from "../features/auth/pages/MyGamesPage";
import RegisterPage from "../features/auth/pages/RegisterPage";
import ResetPasswordPage from "../features/auth/pages/ResetPasswordPage";
import AdvancedAnalyticsPage from "../features/game/pages/AdvancedAnalyticsPage";
import GameSummaryPage from "../features/game/pages/GameSummaryPage";
import PaymentLedgerPage from "../features/payment/pages/PaymentLedgerPage";
import RuleBookPage from "../features/rules/pages/RuleBookPage";
import LandingPage from "../pages/Landing/LandingPage";
import SettingsPage from "../pages/SettingsPage";
import JoinLiveGamePage from "../pages/JoinLiveGamePage";
import LiveGamePlayerView from "../pages/LiveGamePlayerView";
import LiveGameAdminView from "../pages/LiveGameAdminView";
import LiveGamePage from "../pages/LiveGamePage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/my-games" element={
        <ProtectedRoute requireAuth={true}>
          <MyGamesPage />
        </ProtectedRoute>
      } />
      <Route path="/claim-game" element={
        <ProtectedRoute requireAuth={true}>
          <ClaimGamePage />
        </ProtectedRoute>
      } />
      <Route path="/create-game" element={
        <ProtectedRoute requireAuth={true}>
          <CreateGamePage />
        </ProtectedRoute>
      } />
      <Route path="/settings" element={
        <ProtectedRoute requireAuth={true}>
          <SettingsPage />
        </ProtectedRoute>
      } />
      <Route path="/join-live/:joinCode" element={<JoinLiveGamePage />} />
      <Route path="/live-game/:publicCode/:joinCode" element={
        <ProtectedRoute requireAuth={true}>
          <LiveGamePlayerView />
        </ProtectedRoute>
      } />
      <Route path="/live/:publicCode/:joinCode/admin" element={
        <ProtectedRoute requireAuth={true}>
          <LiveGameAdminView />
        </ProtectedRoute>
      } />
      <Route path="/manage-live/:publicCode" element={
        <ProtectedRoute requireAdmin={true}>
          <LiveGamePage />
        </ProtectedRoute>
      } />
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
