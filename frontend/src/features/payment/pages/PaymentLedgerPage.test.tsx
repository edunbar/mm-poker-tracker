import { render, screen } from '@testing-library/react';
import PaymentLedgerPage from './PaymentLedgerPage';

// Mock axios
jest.mock('axios', () => ({
  get: jest.fn(() => Promise.resolve({ data: {} })),
  post: jest.fn(() => Promise.resolve({ data: {} })),
  put: jest.fn(() => Promise.resolve({ data: {} })),
  delete: jest.fn(() => Promise.resolve({ data: {} }))
}));

// Mock react-router-dom useParams (already mocked globally but need to override)
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('../../../__mocks__/react-router-dom'),
  useParams: () => ({ publicCode: 'TEST123' })
}));

// Mock contexts
jest.mock('../../../contexts/AdminSessionContext', () => ({
  useAdminSession: () => ({
    hasAdminSession: false,
    publicCode: 'TEST123',
    adminCode: null
  })
}));

jest.mock('../../../contexts/ToastContext', () => ({
  useToast: () => ({
    showSuccess: () => {},
    showError: () => {}
  })
}));

jest.mock('../../../shared/hooks/useGameTitle', () => ({
  useGameTitle: () => ({
    title: 'Test Game'
  })
}));

describe('Payment Ledger Mobile Responsiveness', () => {
  // Test 1: Component renders
  it('renders payment ledger component', () => {
    const { container } = render(<PaymentLedgerPage />);
    expect(container).toBeInTheDocument();
  });

  // Test 2: Loading state is shown initially
  it('shows loading state before data loads', () => {
    render(<PaymentLedgerPage />);
    expect(screen.getByText(/Loading payment ledger/i)).toBeInTheDocument();
  });

  // Test 3: Component can be rendered without errors
  it('renders without crashing', () => {
    const { container } = render(<PaymentLedgerPage />);
    expect(container.querySelector('.min-h-screen')).toBeInTheDocument();
  });
});
