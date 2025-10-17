import React from "react";
import { useLocation } from "react-router-dom";
import { ThemeProvider } from "../../contexts/ThemeContext";
import { ToastProvider } from "../../contexts/ToastContext";
import { Header } from "./Header";
import { Sidebar } from ".";

const MainLayout: React.FC<React.PropsWithChildren> = ({ children }) => {
  const location = useLocation();

  // Helper function to determine if current route should show game sidebar
  const shouldShowSidebar = (pathname: string): boolean => {
    // Never show on these routes (user dashboard and auth pages)
    const noSidebarRoutes = [
      '/',
      '/login',
      '/register',
      '/sign-in',
      '/sign-up',
      '/forgot-password',
      '/reset-password',
      '/my-games',
      '/claim-game',
      '/create-game',
      '/settings'
    ];

    if (noSidebarRoutes.includes(pathname)) {
      return false;
    }

    // Show sidebar for all game-specific routes (with publicCode)
    return true;
  };

  const showSidebar = shouldShowSidebar(location.pathname);
  const isAnalyticsPage = location.pathname.includes('/analytics/');

  return (
    <ThemeProvider>
      <ToastProvider>
        <div className="min-h-dvh bg-background text-foreground flex flex-col">
          <Header />

          <div className="flex-1 flex">
            {/* Sidebar - only shown on game-specific routes */}
            {showSidebar && (
              <aside className="w-64 shrink-0 hidden sm:block border-r border-border">
                <Sidebar />
              </aside>
            )}

            {/* Main Content */}
            <div className="flex-1 px-4 py-6">
              <div className={`${!showSidebar || isAnalyticsPage ? 'w-full' : 'max-w-5xl mx-auto'} w-full`}>
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
