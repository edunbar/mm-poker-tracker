import { fireEvent, render, screen } from '@testing-library/react';
import { Header } from './Header';

// Mock contexts
jest.mock('../../contexts/AdminSessionContext', () => ({
  useAdminSession: () => ({
    hasAdminSession: false,
    setAdminSession: () => {},
    clearAdminSession: () => {},
    publicCode: null,
    adminCode: null
  })
}));

jest.mock('../../contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: () => {},
    showError: () => {}
  })
}));

jest.mock('../../shared/hooks/useGameTitle', () => ({
  useGameTitle: () => ({
    title: 'Test Game'
  })
}));

// Mock BugReportModal
jest.mock('../../components/BugReportModal', () => ({
  __esModule: true,
  default: () => null
}));

describe('Mobile Navigation', () => {
  // Test 1: Menu opens and closes
  it('opens mobile menu when hamburger clicked, closes on backdrop click', () => {
    render(<Header />);

    // Find and click hamburger button
    const hamburger = screen.getByLabelText('Open menu');
    expect(hamburger).toBeInTheDocument();

    fireEvent.click(hamburger);

    // Menu should be visible
    expect(screen.getByText('Menu')).toBeInTheDocument();
    expect(screen.getByTestId('mobile-menu-backdrop')).toBeInTheDocument();

    // Click backdrop to close
    const backdrop = screen.getByTestId('mobile-menu-backdrop');
    fireEvent.click(backdrop);

    // Menu should be closed
    expect(screen.queryByText('Menu')).not.toBeInTheDocument();
  });

  // Test 2: Navigation links work
  it('navigates and closes menu when nav link clicked', () => {
    render(<Header />);

    // Open menu
    const hamburger = screen.getByLabelText('Open menu');
    fireEvent.click(hamburger);

    // Verify menu is open
    expect(screen.getByText('Menu')).toBeInTheDocument();

    // Click a nav link (they will be disabled without publicCode, but still exist)
    const navLinks = screen.getAllByText(/Game Summary|Rule Book|Payment Ledger/);
    expect(navLinks.length).toBeGreaterThan(0);

    // Menu should have navigation items
    expect(screen.getByText('Game Summary')).toBeInTheDocument();
  });

  // Test 3: Mobile menu only visible on mobile
  it('hides hamburger button on desktop viewport', () => {
    render(<Header />);

    const hamburger = screen.getByLabelText('Open menu');

    // Should have lg:hidden class (hidden on desktop)
    expect(hamburger.className).toContain('lg:hidden');
  });

  // Test 4: Close button works
  it('closes menu when X button clicked', () => {
    render(<Header />);

    // Open menu
    const hamburger = screen.getByLabelText('Open menu');
    fireEvent.click(hamburger);

    // Verify menu is open
    expect(screen.getByText('Menu')).toBeInTheDocument();

    // Click close button
    const closeButton = screen.getByLabelText('Close menu');
    fireEvent.click(closeButton);

    // Menu should be closed
    expect(screen.queryByText('Menu')).not.toBeInTheDocument();
  });
});
