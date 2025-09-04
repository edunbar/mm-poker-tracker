import React from "react";
import { Sidebar } from ".";
import { useLocation } from "react-router-dom";
import { ToastProvider } from "../../contexts/ToastContext";

const MainLayout: React.FC<React.PropsWithChildren> = ({ children }) => {
  const location = useLocation();
  const isLandingPage = location.pathname === "/";

  return (
    <ToastProvider>
      <div className="min-h-dvh bg-gray-50">
        <header className="border-b bg-white">
          <div className="w-full px-4 py-3 font-medium">HomeGame</div>
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
