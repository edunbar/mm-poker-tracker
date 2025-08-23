import React from "react";

const MainLayout: React.FC<React.PropsWithChildren> = ({ children }) => {
  return (
    <div className="min-h-dvh bg-gray-50">
      <header className="border-b bg-white">
        <div className="max-w-5xl mx-auto px-4 py-3 font-medium">
          Poker Tracker
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-6">{children}</main>
    </div>
  );
};

export default MainLayout;
