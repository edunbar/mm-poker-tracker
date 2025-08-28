import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "../pages/Landing/LandingPage";
import GameIngestPage from "../features/admin/pages/GameIngestPage";
import GameSummaryPage from "../features/game/pages/GameSummaryPage";
import { useParams } from "react-router-dom";

export default function AppRoutes() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/ingest/:publicCode" element={<GameIngestPage />} />
        <Route
          path="/summary/:publicCode"
          element={<GameSummaryPageWrapper />}
        />
      </Routes>
    </Router>
  );
}

function GameSummaryPageWrapper() {
  const { publicCode } = useParams();
  return <GameSummaryPage publicCode={publicCode || ""} />;
}
