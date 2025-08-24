import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "../pages/Landing/LandingPage";
import GameIngestPage from "../features/game/pages/GameIngestPage";

export default function AppRoutes() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/ingest" element={<GameIngestPage />} />
      </Routes>
    </Router>
  );
}
