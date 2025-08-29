import React from "react";
import { BrowserRouter as Router } from "react-router-dom";
import MainLayout from "./layout/MainLayout";
import AppRoutes from "./routes";

export default function App() {
  return (
    <Router>
      <MainLayout>
        <AppRoutes />
      </MainLayout>
    </Router>
  );
}
