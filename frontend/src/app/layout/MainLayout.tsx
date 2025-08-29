import React from "react";
import { Sidebar } from ".";

const MainLayout: React.FC<React.PropsWithChildren> = ({ children }) => {
  return (
    <div className="min-h-dvh bg-gray-50">
      <header className="border-b bg-white">
        <div className="w-full px-4 py-3 font-medium">Poker Tracker</div>
      </header>

      <div className="w-full px-4 py-6">
        {/* Sidebar is fixed so it doesn't influence centering of main content */}
        <aside className="w-64 shrink-0 hidden sm:block fixed left-0 top-16 bottom-0 p-4">
          <Sidebar />
        </aside>

        <div className="sm:pl-72">
          <div className="max-w-5xl mx-auto w-full">
            <main className="flex-1">{children}</main>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MainLayout;
