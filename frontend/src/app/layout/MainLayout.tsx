import React from "react";
import { useLocation } from "react-router-dom";
import { ThemeProvider } from "../../contexts/ThemeContext";
import { ToastProvider } from "../../contexts/ToastContext";
import { Header } from "./Header";
import { Sidebar } from ".";

const MainLayout: React.FC<React.PropsWithChildren> = ({ children }) => {
  const location = useLocation();
  const isLandingPage = location.pathname === "/";
  const isAnalyticsPage = location.pathname.includes('/analytics/');

  return (
    <ThemeProvider>
      <ToastProvider>
        <div className="min-h-dvh bg-background text-foreground flex flex-col">
          <Header />

          <div className="flex-1 flex">
            {/* Sidebar */}
            {!isLandingPage && (
              <aside className="w-64 shrink-0 hidden sm:block border-r border-border">
                <Sidebar />
              </aside>
            )}

            {/* Main Content */}
            <div className="flex-1 px-4 py-6">
              <div className={`${isAnalyticsPage ? 'w-full' : 'max-w-5xl mx-auto'} w-full`}>
                <main className="flex-1">{children}</main>
              </div>
            </div>
          </div>
        </div>
      </ToastProvider>
    </ThemeProvider>
  );
};

export default MainLayout;
