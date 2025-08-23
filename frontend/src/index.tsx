import React from "react";
import { createRoot } from "react-dom/client";
import App from "./app/App";
import "./index.css";
import { QueryProvider } from "./app/providers/QueryProvider";
import AppErrorBoundary from "./app/errors/AppErrorBoundary";

const container = document.getElementById("root");
if (!container) throw new Error("Root element #root not found");

const root = createRoot(container);
root.render(
  <React.StrictMode>
    <AppErrorBoundary>
      <QueryProvider>
        <App />
      </QueryProvider>
    </AppErrorBoundary>
  </React.StrictMode>
);
