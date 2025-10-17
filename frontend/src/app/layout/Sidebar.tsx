import axios from "axios";
import {
  BarChart3,
  BookOpen,
  CreditCard,
  Download,
  FileText,
  Home,
  LogOut,
  Radio,
  Receipt,
  Shield,
  Spade,
  Users,
  Zap
} from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { API_BASE_URL } from "../../config/api";
import { useAdminSession } from "../../contexts/AdminSessionContext";
import { adminNav, publicNav } from "../../features/admin/nav";
import { useGameTitle } from "../../shared/hooks/useGameTitle";
import { Text } from "../../shared/ui/typography";
import { getActiveLiveGame, type ActiveLiveGame } from "../../utils/liveGameStorage";

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
    case "Live Game":
      return <Radio className="w-4 h-4" />;
    case "Player Verification":
      return <Users className="w-4 h-4" />;
    case "Payment Ledger":
      return <CreditCard className="w-4 h-4" />;
    case "Ledger Analysis":
      return <BarChart3 className="w-4 h-4" />;
    case "Audit Log":
      return <FileText className="w-4 h-4" />;
    case "Hand Analytics":
      return <Spade className="w-4 h-4" />;
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

  // For live game routes like /live-game/ABC123/HQKS or /live/ABC123/HQKS/admin
  if (pathParts[0] === 'live-game' || pathParts[0] === 'live') {
    if (pathParts.length >= 2) {
      const potentialCode = pathParts[1];
      // Check if it looks like a public code (5 chars, alphanumeric)
      if (potentialCode && potentialCode.length === 5 && /^[A-Z0-9]+$/.test(potentialCode)) {
        return potentialCode;
      }
    }
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
  const { hasAdminSession: hasAdminSessionForGame, clearAdminSession, getAdminCode } = useAdminSession();
  const location = useLocation();
  const [alertCount, setAlertCount] = useState(0);

  // Use state to track active live game and listen for changes
  const [activeLiveGame, setActiveLiveGame] = useState<ActiveLiveGame | null>(() => getActiveLiveGame());

  // Listen for localStorage changes
  useEffect(() => {
    const handleStorageChange = (event: CustomEvent) => {
      setActiveLiveGame(event.detail);
    };

    window.addEventListener('activeLiveGameChanged' as any, handleStorageChange);
    return () => {
      window.removeEventListener('activeLiveGameChanged' as any, handleStorageChange);
    };
  }, []);

  // Get public code from URL or from active live game
  const urlPublicCode = extractPublicCodeFromPath(location.pathname);
  const currentPublicCode = urlPublicCode || activeLiveGame?.publicCode || null;
  const { title } = useGameTitle(currentPublicCode || '');
  const hasAdminSession = currentPublicCode ? hasAdminSessionForGame(currentPublicCode) : false;

  const fetchAlertCount = useCallback(async () => {
    if (!currentPublicCode) return;

    try {
      const adminCode = getAdminCode(currentPublicCode);
      const headers = adminCode ? { 'X-Admin-Code': adminCode } : {};
      const response = await axios.get(
        `${API_BASE_URL}/api/games/${currentPublicCode}/alerts/status`,
        { headers }
      );
      setAlertCount(response.data.players_with_violations || 0);
    } catch {
      // Silently fail - show 0 if not authorized or error
      setAlertCount(0);
    }
  }, [currentPublicCode, getAdminCode]);

  useEffect(() => {
    if (currentPublicCode) {
      fetchAlertCount();
    }
  }, [currentPublicCode, fetchAlertCount]);

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
                <div className="relative group">
                  <div className="flex items-center px-2 py-1 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors duration-150 cursor-pointer">
                    <Shield className="w-3 h-3 mr-1" />
                    <Text variant="caption" weight="medium">Admin</Text>
                  </div>

                  {/* Hover overlay with logout button */}
                  <div className="absolute top-0 left-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity duration-150 bg-destructive text-destructive-foreground rounded-md px-2 py-1 flex items-center cursor-pointer"
                       onClick={() => clearAdminSession(currentPublicCode || undefined)}>
                    <LogOut className="w-3 h-3 mr-1" />
                    <Text variant="caption" weight="medium">Leave</Text>
                  </div>
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
            {/* Active Live Game - shown when user is participating in a live game */}
            {activeLiveGame && (
              <NavLink
                to={`/live-game/${activeLiveGame.publicCode}/${activeLiveGame.joinCode}`}
                className={({ isActive }) =>
                  isActive
                    ? "flex items-center px-3 py-2 text-accent-foreground bg-accent rounded-md"
                    : "flex items-center px-3 py-2 text-foreground rounded-md hover:text-accent-foreground hover:bg-muted transition-colors duration-150"
                }
              >
                <span className="mr-3">
                  <Radio className="w-4 h-4" />
                </span>
                <Text variant="bodySmall" weight="medium">Live Game</Text>
              </NavLink>
            )}

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
                      {item.label === "Payment Ledger" && alertCount > 0 && (
                        <span className="ml-auto bg-red-500 text-white rounded-full px-2 py-0.5 text-xs font-medium">
                          {alertCount}
                        </span>
                      )}
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
                          {item.label === "Payment Ledger" && alertCount > 0 && (
                            <span className="ml-auto bg-red-500 text-white rounded-full px-2 py-0.5 text-xs font-medium">
                              {alertCount}
                            </span>
                          )}
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

    </nav>
  );
}
