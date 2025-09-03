import React from "react";
import { BrowserRouter as Router } from "react-router-dom";
import MainLayout from "./layout/MainLayout";
import AppRoutes from "./routes";
import { AdminSessionProvider } from "../contexts/AdminSessionContext";

export default function App() {
  return (
    <AdminSessionProvider>
      <Router>
        <MainLayout>
          <AppRoutes />
        </MainLayout>
      </Router>
    </AdminSessionProvider>
  );
}
