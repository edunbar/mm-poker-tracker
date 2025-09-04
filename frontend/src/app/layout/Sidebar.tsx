import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { adminNav, publicNav } from "../../features/admin/nav";
import { useAdminSession } from "../../contexts/AdminSessionContext";

const ACTIVE = "bg-emerald-600 text-white";
const INACTIVE = "text-gray-700 hover:bg-gray-50";

function renderPath(path: string, currentPublicCode: string | null) {
  // Replace :publicCode with actual public code from URL or context
  if (!currentPublicCode) {
    // If no public code available, return path without replacement (will be disabled)
    return path;
  }
  return path.replace(":publicCode", currentPublicCode);
}

// Helper function to extract public code from URL pathname
function extractPublicCodeFromPath(pathname: string): string | null {
  const pathParts = pathname.split('/').filter(part => part.length > 0);
  
  // Skip if we're on the landing page
  if (pathParts.length === 0) {
    return null;
  }
  
  // For routes like /ingest/ABC123, /summary/ABC123, /payments/ABC123, etc.
  if (pathParts.length >= 2) {
    const potentialCode = pathParts[1];
    // Check if it looks like a public code (6 chars, alphanumeric)
    if (potentialCode.length === 6 && /^[A-Z0-9]+$/.test(potentialCode)) {
      return potentialCode;
    }
  }
  
  // For routes like /ABC123 (direct game access)
  if (pathParts.length === 1) {
    // Check if it looks like a public code (6 chars, alphanumeric)
    const potentialCode = pathParts[0];
    if (potentialCode.length === 6 && /^[A-Z0-9]+$/.test(potentialCode)) {
      return potentialCode;
    }
  }
  
  return null;
}

export default function Sidebar() {
  const { hasAdminSession, setAdminSession, publicCode: contextPublicCode } = useAdminSession();
  const [showAdminLogin, setShowAdminLogin] = useState(false);
  const [adminCode, setAdminCode] = useState('');
  const location = useLocation();

  // Get public code from URL first (prioritize current page), then fall back to admin session context
  const urlPublicCode = extractPublicCodeFromPath(location.pathname);
  const currentPublicCode = urlPublicCode || contextPublicCode;

  const handleAdminLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (adminCode && currentPublicCode) {
      setAdminSession(adminCode, currentPublicCode);
      setAdminCode('');
      setShowAdminLogin(false);
    }
  };

  return (
    <nav className="shadow-sm ring-1 ring-gray-100 rounded-lg bg-white p-3">
      <div className="text-sm font-semibold mb-3">Game Views</div>

      <ul className="space-y-2">
        {publicNav.map((item) => {
          const path = renderPath(item.path, currentPublicCode);
          const isDisabled = !currentPublicCode && item.path.includes(':publicCode');
          
          return (
            <li key={item.path}>
              {isDisabled ? (
                <div className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-400 cursor-not-allowed">
                  {item.label}
                </div>
              ) : (
                <NavLink
                  to={path}
                  className={({ isActive }) =>
                    `block px-3 py-2 rounded-lg text-sm font-medium ${
                      isActive ? ACTIVE : INACTIVE
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              )}
            </li>
          );
        })}
      </ul>

      {hasAdminSession ? (
        <>
          <div className="text-sm font-semibold mb-3 mt-6">Admin</div>
          <ul className="space-y-2">
            {adminNav.map((item) => {
              const path = renderPath(item.path, currentPublicCode);
              const isDisabled = !currentPublicCode && item.path.includes(':publicCode');
              
              return (
                <li key={item.path}>
                  {isDisabled ? (
                    <div className="block px-3 py-2 rounded-lg text-sm font-medium text-gray-400 cursor-not-allowed">
                      {item.label}
                    </div>
                  ) : (
                    <NavLink
                      to={path}
                      className={({ isActive }) =>
                        `block px-3 py-2 rounded-lg text-sm font-medium ${
                          isActive ? ACTIVE : INACTIVE
                        }`
                      }
                    >
                      {item.label}
                    </NavLink>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      ) : (
        <div className="mt-6">
          {!showAdminLogin ? (
            <button
              onClick={() => setShowAdminLogin(true)}
              className="w-full px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100"
            >
              Admin Login
            </button>
          ) : (
            <form onSubmit={handleAdminLogin} className="space-y-2">
              <div className="text-sm font-semibold">Admin Login</div>
              <input
                type="password"
                value={adminCode}
                onChange={(e) => setAdminCode(e.target.value)}
                placeholder="Enter admin code"
                className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
              <div className="flex gap-1">
                <button
                  type="submit"
                  className="flex-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Login
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAdminLogin(false);
                    setAdminCode('');
                  }}
                  className="flex-1 px-2 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      )}
    </nav>
  );
}
