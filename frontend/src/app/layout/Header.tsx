import {
  BarChart3,
  BookOpen,
  Bug,
  CreditCard,
  Download,
  FileText,
  Home,
  LogOut,
  Menu,
  Receipt,
  Shield,
  Spade,
  User,
  Users,
  X,
  Zap
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { submitBugReport, type BugReportData } from '../../api/bugReport';
import BugReportModal from '../../components/BugReportModal';
import { useAdminSession } from '../../contexts/AdminSessionContext';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import { adminNav, publicNav } from '../../features/admin/nav';
import { useGameTitle } from '../../shared/hooks/useGameTitle';
import { Button } from '../../shared/ui/button';
import { Input } from '../../shared/ui/input';
import { Text } from '../../shared/ui/typography';

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
    case "Hand Analytics":
      return <Spade className="w-4 h-4" />;
    case "Advanced Analytics":
      return <BarChart3 className="w-4 h-4" />;
    default:
      return <Home className="w-4 h-4" />;
  }
};

function renderPath(path: string, currentPublicCode: string | null) {
  if (!currentPublicCode) {
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

export function Header() {
  const { hasAdminSession, setAdminSession, clearAdminSession, publicCode: contextPublicCode } = useAdminSession();
  const { isAuthenticated, isLoading, user, logout } = useAuth();
  const { showSuccess, showError } = useToast();
  const location = useLocation();
  const [isBugReportModalOpen, setIsBugReportModalOpen] = useState(false);
  const [showAdminLogin, setShowAdminLogin] = useState(false);
  const [adminCode, setAdminCode] = useState('');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  // Get public code from URL first (prioritize current page), then fall back to admin session context
  const urlPublicCode = extractPublicCodeFromPath(location.pathname);
  const currentPublicCode = urlPublicCode || contextPublicCode;
  const { title } = useGameTitle(currentPublicCode || '');

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  const handleAdminLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (adminCode && currentPublicCode) {
      setAdminSession(adminCode, currentPublicCode);
      setAdminCode('');
      setShowAdminLogin(false);
    }
  };

  const handleBugReportSubmit = async (data: BugReportData) => {
    try {
      await submitBugReport(data);
      showSuccess('Success', 'Bug report submitted successfully! Thank you for your feedback.');
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Failed to submit bug report:', error);
      showError('Error', 'Failed to submit bug report. Please try again later.');
      throw error; // Re-throw to prevent modal from closing
    }
  };

  return (
    <>
      <header className="border-b border-border bg-card">
        <div className="w-full px-4 py-3 font-medium flex items-center justify-between text-card-foreground">
          <Text variant="bodyLarge" weight="semibold">HomeGame</Text>

          <div className="flex items-center gap-2">
            {/* Mobile Menu Button */}
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="lg:hidden flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            {/* Admin Login Button - Only show when not logged in as admin and in game context */}
            {!hasAdminSession && currentPublicCode && (
              <button
                onClick={() => setShowAdminLogin(true)}
                className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
                title="Admin login"
              >
                <Shield className="h-4 w-4" />
                <Text variant="bodySmall" as="span" className="hidden sm:inline">Admin Login</Text>
              </button>
            )}

            {/* User Authentication */}
            {!isLoading && (
              <>
                {!isAuthenticated ? (
                  <>
                    <Link
                      to="/login"
                      className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
                    >
                      <Text variant="bodySmall" as="span" className="hidden sm:inline">Log in</Text>
                    </Link>
                    <Link
                      to="/register"
                      className="flex items-center gap-2 px-3 py-2 text-sm bg-primary text-primary-foreground hover:bg-primary/90 rounded-md transition-colors"
                    >
                      <Text variant="bodySmall" as="span">Sign up</Text>
                    </Link>
                  </>
                ) : (
                  <div className="relative">
                    <button
                      onClick={() => setShowUserMenu(!showUserMenu)}
                      className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
                      title={user?.email}
                    >
                      <User className="h-4 w-4" />
                      <Text variant="bodySmall" as="span" className="hidden sm:inline max-w-[150px] truncate">
                        {user?.email}
                      </Text>
                    </button>

                    {showUserMenu && (
                      <>
                        <div
                          className="fixed inset-0 z-10"
                          onClick={() => setShowUserMenu(false)}
                        />
                        <div className="absolute right-0 mt-2 w-48 bg-card border border-border rounded-md shadow-lg z-20">
                          <div className="py-1">
                            <div className="px-4 py-2 border-b border-border">
                              <Text variant="bodySmall" weight="medium">{user?.displayName}</Text>
                              <Text variant="caption" color="muted">{user?.email}</Text>
                            </div>
                            <Link
                              to="/my-games"
                              onClick={() => setShowUserMenu(false)}
                              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                            >
                              <Home className="h-4 w-4" />
                              <Text variant="bodySmall">My Games</Text>
                            </Link>
                            <Link
                              to="/claim-game"
                              onClick={() => setShowUserMenu(false)}
                              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                            >
                              <Shield className="h-4 w-4" />
                              <Text variant="bodySmall">Claim Game</Text>
                            </Link>
                            <div className="border-t border-border my-1" />
                            <button
                              onClick={() => {
                                logout();
                                setShowUserMenu(false);
                              }}
                              className="w-full flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                            >
                              <LogOut className="h-4 w-4" />
                              <Text variant="bodySmall">Log out</Text>
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Bug Report Button */}
            <button
              onClick={() => setIsBugReportModalOpen(true)}
              className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
              title="Report a bug"
            >
              <Bug className="h-4 w-4" />
              <Text variant="bodySmall" as="span" className="hidden sm:inline">Report Bug</Text>
            </button>
          </div>
        </div>
      </header>

      {/* Bug Report Modal */}
      <BugReportModal
        isOpen={isBugReportModalOpen}
        onClose={() => setIsBugReportModalOpen(false)}
        onSubmit={handleBugReportSubmit}
      />

      {/* Admin Login Modal */}
      {showAdminLogin && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card text-card-foreground rounded-lg shadow-xl border border-border max-w-md w-full mx-4">
            <div className="flex items-center justify-between p-6 border-b border-border">
              <Text variant="bodyLarge" weight="semibold">Admin Login</Text>
              <Button
                onClick={() => {
                  setShowAdminLogin(false);
                  setAdminCode('');
                }}
                variant="ghost"
                size="icon-sm"
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="w-6 h-6" />
              </Button>
            </div>

            <form onSubmit={handleAdminLogin} className="p-6 space-y-4">
              <div>
                <Text variant="bodySmall" weight="medium" as="label" className="block mb-2">
                  Admin Code
                </Text>
                <Input
                  type="password"
                  value={adminCode}
                  onChange={(e) => setAdminCode(e.target.value)}
                  placeholder="Enter admin code"
                  autoFocus
                />
              </div>

              <div className="flex justify-end space-x-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowAdminLogin(false);
                    setAdminCode('');
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={!adminCode}
                >
                  Login
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Mobile Menu Drawer */}
      {isMobileMenuOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/50 z-40 lg:hidden"
            onClick={() => setIsMobileMenuOpen(false)}
            data-testid="mobile-menu-backdrop"
          />

          {/* Drawer */}
          <div className="fixed right-0 top-0 h-full w-[280px] bg-card border-l border-border z-50 lg:hidden overflow-y-auto">
            {/* Header */}
            <div className="px-6 py-5 border-b border-border">
              <div className="flex items-center justify-between mb-4">
                <Text variant="bodyLarge" weight="semibold">Menu</Text>
                <button
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="p-2 text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded-md transition-colors"
                  aria-label="Close menu"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {currentPublicCode && (
                <div>
                  <Text variant="bodySmall" weight="medium" className="mb-1">{title}</Text>
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
                               onClick={clearAdminSession}>
                            <LogOut className="w-3 h-3 mr-1" />
                            <Text variant="caption" weight="medium">Leave</Text>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Navigation Content */}
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
        </>
      )}
    </>
  );
}