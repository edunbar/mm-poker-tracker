import {
  BarChart3,
  BookOpen,
  CreditCard,
  Download,
  FileText,
  Home,
  Receipt,
  Shield,
  Users,
  Zap
} from "lucide-react";
import React, { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useAdminSession } from "../../contexts/AdminSessionContext";
import { adminNav, publicNav } from "../../features/admin/nav";
import { useGameTitle } from "../../shared/hooks/useGameTitle";
import { Button } from "../../shared/ui/button";
import { Input } from "../../shared/ui/input";
import { Text } from "../../shared/ui/typography";

// Icon mapping for navigation items
const getNavIcon = (label: string) => {
  switch (label) {
    case "Game Summary":
      return <BarChart3 className="w-4 h-4" />;
    case "Rule Book":
      return <BookOpen className="w-4 h-4" />;
    case "Game Ledger":
      return <Receipt className="w-4 h-4" />;
    case "PokerNow Import":
      return <Download className="w-4 h-4" />;
    case "Live Game Entry":
      return <Zap className="w-4 h-4" />;
    case "Player Verification":
      return <Users className="w-4 h-4" />;
    case "Payment Ledger":
      return <CreditCard className="w-4 h-4" />;
    case "Ledger Analysis":
      return <BarChart3 className="w-4 h-4" />;
    case "Audit Log":
      return <FileText className="w-4 h-4" />;
    default:
      return <Home className="w-4 h-4" />;
  }
};

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
    // Check if it looks like a public code (5 chars, alphanumeric)
    if (potentialCode && potentialCode.length === 5 && /^[A-Z0-9]+$/.test(potentialCode)) {
      return potentialCode;
    }
  }
  
  // For routes like /ABC123 (direct game access)
  if (pathParts.length === 1) {
    // Check if it looks like a public code (5 chars, alphanumeric)
    const potentialCode = pathParts[0];
    if (potentialCode && potentialCode.length === 5 && /^[A-Z0-9]+$/.test(potentialCode)) {
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
  const { title } = useGameTitle(currentPublicCode || '');

  const handleAdminLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (adminCode && currentPublicCode) {
      setAdminSession(adminCode, currentPublicCode);
      setAdminCode('');
      setShowAdminLogin(false);
    }
  };

  return (
    <nav className="h-full bg-card flex flex-col">
      {/* Header */}
      <div className="px-6 py-5">
        <Text variant="bodyLarge" weight="semibold" className="mb-2">{title}</Text>
        {currentPublicCode && (
          <div className="flex items-center">
            <Text variant="bodySmall" as="span" className="font-mono text-primary">{currentPublicCode}</Text>
            {hasAdminSession && (
              <>
                <span className="mx-2">•</span>
                <div className="flex items-center px-2 py-1 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors duration-150">
                  <Shield className="w-3 h-3 mr-1" />
                  <Text variant="caption" weight="medium">Admin</Text>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Navigation Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-3 py-4">
          
          {/* Public Navigation */}
          <div className="space-y-1">
            {publicNav.map((item) => {
              const path = renderPath(item.path, currentPublicCode);
              const isDisabled = !currentPublicCode && item.path.includes(':publicCode');
              const icon = getNavIcon(item.label);
              
              return (
                <div key={item.path}>
                  {isDisabled ? (
                    <div className="flex items-center px-3 py-2 cursor-not-allowed">
                      <span className="mr-3 opacity-50">{icon}</span>
                      <Text variant="bodySmall" weight="medium" color="muted">{item.label}</Text>
                    </div>
                  ) : (
                    <NavLink
                      to={path}
                      className={({ isActive }) =>
                        isActive
                          ? "flex items-center px-3 py-2 text-accent-foreground bg-accent rounded-md"
                          : "flex items-center px-3 py-2 text-foreground rounded-md hover:text-accent-foreground hover:bg-muted transition-colors duration-150"
                      }
                    >
                      <span className="mr-3">{icon}</span>
                      <Text variant="bodySmall" weight="medium">{item.label}</Text>
                    </NavLink>
                  )}
                </div>
              );
            })}
          </div>

          {/* Admin Navigation */}
          {hasAdminSession && (
            <>
              <div className="mt-10 mb-4">
                <Text variant="caption" weight="semibold" color="muted" className="px-3 uppercase tracking-wider">
                  Admin Tools
                </Text>
              </div>
              
              <div className="space-y-1">
                {adminNav.map((item) => {
                  const path = renderPath(item.path, currentPublicCode);
                  const isDisabled = !currentPublicCode && item.path.includes(':publicCode');
                  const icon = getNavIcon(item.label);
                  
                  return (
                    <div key={item.path}>
                      {isDisabled ? (
                        <div className="flex items-center px-3 py-2 cursor-not-allowed">
                          <span className="mr-3 opacity-50">{icon}</span>
                          <Text variant="bodySmall" weight="medium" color="muted">{item.label}</Text>
                        </div>
                      ) : (
                        <NavLink
                          to={path}
                          className={({ isActive }) =>
                            isActive
                              ? "flex items-center px-3 py-2 text-accent-foreground bg-accent rounded-md"
                              : "flex items-center px-3 py-2 text-foreground rounded-md hover:text-accent-foreground hover:bg-muted transition-colors duration-150"
                          }
                        >
                          <span className="mr-3">{icon}</span>
                          <Text variant="bodySmall" weight="medium">{item.label}</Text>
                        </NavLink>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Bottom Admin Login Section */}
      {!hasAdminSession && (
        <div className="px-3 py-5 border-t border-border bg-muted">
          {!showAdminLogin ? (
            <Button
              onClick={() => setShowAdminLogin(true)}
              variant="ghost"
              className="w-full justify-start px-3 py-2 hover:bg-card"
            >
              <Shield className="w-4 h-4 mr-3" />
              <Text variant="bodySmall" weight="medium">Admin Access</Text>
            </Button>
          ) : (
            <form onSubmit={handleAdminLogin} className="space-y-3">
              <Text variant="bodySmall" weight="medium">Admin Login</Text>
              <Input
                type="password"
                value={adminCode}
                onChange={(e) => setAdminCode(e.target.value)}
                placeholder="Enter admin code"
                size="sm"
                autoFocus
              />
              <div className="flex space-x-2">
                <Button
                  type="submit"
                  size="sm"
                  className="flex-1"
                >
                  <Text variant="bodySmall" weight="medium">Login</Text>
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setShowAdminLogin(false);
                    setAdminCode('');
                  }}
                  className="flex-1"
                >
                  <Text variant="bodySmall" weight="medium">Cancel</Text>
                </Button>
              </div>
            </form>
          )}
        </div>
      )}
    </nav>
  );
}
