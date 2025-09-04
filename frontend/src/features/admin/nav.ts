// Simple admin navigation metadata used by the app sidebar.
// Add new admin pages here with a display label and a route path.
export const publicNav = [
  { label: "Game Summary", path: "/summary/:publicCode" },
  { label: "Game Ledger", path: "/ledger/:publicCode" },
];

export const adminNav = [
  { label: "PokerNow Import", path: "/ingest/:publicCode" },
  { label: "Live Game Entry", path: "/live/:publicCode" },
  { label: "Player Verification", path: "/players/:publicCode" },
  { label: "Payment Ledger", path: "/payments/:publicCode" },
  { label: "Ledger Analysis", path: "/ledger-analysis/:publicCode" },
  { label: "Audit Log", path: "/audit/:publicCode" },
];
