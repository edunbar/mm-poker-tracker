import React from "react";
import MainLayout from "./layout/MainLayout";
import AppRoutes from "./routes";

export default function App() {
  return (
    <MainLayout>
      <AppRoutes />
    </MainLayout>
  );
}
