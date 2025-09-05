import React from "react";
import { Sidebar } from ".";
import { useLocation } from "react-router-dom";
import { ToastProvider } from "../../contexts/ToastContext";
import { useAdminSession } from "../../contexts/AdminSessionContext";

const MainLayout: React.FC<React.PropsWithChildren> = ({ children }) => {
  const location = useLocation();
  const isLandingPage = location.pathname === "/";
  const { hasAdminSession, publicCode, clearAdminSession } = useAdminSession();

  return (
    <ToastProvider>
      <div className="min-h-dvh bg-gray-50">
        <header className="border-b bg-white">
          <div className="w-full px-4 py-3 font-medium flex items-center justify-between">
            <div>HomeGame</div>
            {hasAdminSession && (
              <div className="group relative">
                <div className="bg-green-500 text-white text-xs px-2 py-1 rounded opacity-60 hover:opacity-100 transition-opacity cursor-help font-medium">
                  Admin
                </div>
                <div className="absolute right-0 top-6 invisible group-hover:visible bg-gray-900 text-white text-xs rounded py-2 px-3 whitespace-nowrap z-50 shadow-lg">
                  <div className="font-medium">Admin Session Active</div>
                  <div className="text-gray-300 mt-1">Game: {publicCode}</div>
                  <button
                    onClick={clearAdminSession}
                    className="mt-2 text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded"
                  >
                    Clear Session
                  </button>
                  <div className="absolute -top-1 right-3 w-2 h-2 bg-gray-900 transform rotate-45"></div>
                </div>
              </div>
            )}
          </div>
        </header>

        <div className="w-full px-4 py-6">
          {/* Sidebar is fixed so it doesn't influence centering of main content */}
          {!isLandingPage && (
            <aside className="w-64 shrink-0 hidden sm:block fixed left-0 top-16 bottom-0 p-4">
              <Sidebar />
            </aside>
          )}

          <div className={isLandingPage ? "" : "sm:pl-72"}>
            <div className="max-w-5xl mx-auto w-full">
              <main className="flex-1">{children}</main>
            </div>
          </div>
        </div>
      </div>
    </ToastProvider>
  );
};

export default MainLayout;
