import { useAdminSession } from '../../contexts/AdminSessionContext';

export function Header() {
  const { hasAdminSession: _hasAdminSession, publicCode: _publicCode, clearAdminSession: _clearAdminSession } = useAdminSession();

  return (
    <header className="border-b border-border bg-card">
      <div className="w-full px-4 py-3 font-medium flex items-center justify-between text-card-foreground">
        <div className="text-lg font-semibold">HomeGame</div>
      </div>
    </header>
  );
}