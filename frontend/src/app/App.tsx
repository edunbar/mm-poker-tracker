import React from "react";
import MainLayout from "./layout/MainLayout";
import GameIngestPage from "features/game/pages/GameIngestPage";

export default function App() {
  return (
    <MainLayout>
      <GameIngestPage />
    </MainLayout>
  );
}
