// Simple admin navigation metadata used by the app sidebar.
// Add new admin pages here with a display label and a route path.
export const publicNav = [
  { label: "Game Summary", path: "/summary/:publicCode" },
  { label: "Advanced Analytics", path: "/analytics/:publicCode" },
  { label: "Hand Analytics", path: "/session-analytics/:publicCode" },
  { label: "Game Ledger", path: "/ledger/:publicCode" },
  { label: "Payment Ledger", path: "/payments/:publicCode" },
  { label: "Rule Book", path: "/rules/:publicCode" },
];

export const adminNav = [
  { label: "PokerNow Import", path: "/ingest/:publicCode" },
  { label: "Live Game Entry", path: "/live/:publicCode" },
  { label: "Ledger Analysis", path: "/ledger-analysis/:publicCode" },
  { label: "Audit Log", path: "/audit/:publicCode" },
];
