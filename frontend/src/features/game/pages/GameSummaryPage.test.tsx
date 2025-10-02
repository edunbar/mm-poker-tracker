import { render, screen } from '@testing-library/react';
import GameSummaryPage from './GameSummaryPage';

// Mock API hook
jest.mock('../api/getPlayerSummaries', () => ({
  usePlayerSummaries: () => ({
    data: null,
    isLoading: true,
    error: null
  })
}));

describe('Game Summary Mobile Responsiveness', () => {
  // Test 1: Component renders
  it('renders game summary component', () => {
    const { container } = render(<GameSummaryPage publicCode="TEST123" />);
    expect(container).toBeInTheDocument();
  });

  // Test 2: Loading state is shown
  it('shows loading state before data loads', () => {
    render(<GameSummaryPage publicCode="TEST123" />);
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });

  // Test 3: Page has responsive padding
  it('main container has responsive padding classes', () => {
    const { container } = render(<GameSummaryPage publicCode="TEST123" />);
    const html = container.innerHTML;

    // Check for responsive padding (px-4 md:px-6 lg:px-8)
    expect(html).toMatch(/px-4/);
    expect(html).toMatch(/md:px-6/);
    expect(html).toMatch(/lg:px-8/);
  });
});
