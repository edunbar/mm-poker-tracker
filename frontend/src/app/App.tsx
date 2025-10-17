import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/react";
import { BrowserRouter as Router } from "react-router-dom";
import { ClerkAuthWrapper } from "../components/ClerkAuthWrapper";
import { AdminSessionProvider } from "../contexts/AdminSessionContext";
import MainLayout from "./layout/MainLayout";
import AppRoutes from "./routes";

export default function App() {
  return (
    <ClerkAuthWrapper>
      <AdminSessionProvider>
        <Router>
          <MainLayout>
            <AppRoutes />
          </MainLayout>
        </Router>
        <Analytics />
        <SpeedInsights />
      </AdminSessionProvider>
    </ClerkAuthWrapper>
  );
}
