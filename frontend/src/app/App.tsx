import { BrowserRouter as Router } from "react-router-dom";
import { AdminSessionProvider } from "../contexts/AdminSessionContext";
import MainLayout from "./layout/MainLayout";
import AppRoutes from "./routes";

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
