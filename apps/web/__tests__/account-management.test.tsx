/**
 * Account Management Integration Tests
 * Tests for the complete account management page functionality
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MarketDataAccount } from '@xiaoy-mdhub/shared-types/accounts';
import AccountsPage from '../src/app/accounts/page';

// Mock the account service
jest.mock('../src/services/account-service', () => ({
  accountService: {
    getAllAccounts: jest.fn(),
    toggleAccountStatus: jest.fn(),
  },
}));

// Mock the toast hook
jest.mock('../src/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn(),
  }),
}));

// Mock Lucide React icons
jest.mock('lucide-react', () => ({
  RefreshCw: ({ className }: { className?: string }) => (
    <div data-testid="refresh-icon" className={className} />
  ),
  X: ({ className }: { className?: string }) => (
    <div data-testid="x-icon" className={className} />
  ),
}));

import { accountService } from '../src/services/account-service';

const mockAccountService = accountService as jest.Mocked<typeof accountService>;

describe('AccountsPage Integration Tests', () => {
  const mockAccounts: MarketDataAccount[] = [
    {
      id: 'ctp-main-account',
      gateway_type: 'ctp',
      settings: { userID: 'test', password: 'test', brokerID: '9999' },
      priority: 1,
      is_enabled: true,
      description: 'Primary CTP Account',
      createdAt: new Date('2023-01-01T00:00:00Z'),
      updatedAt: new Date('2023-01-01T00:00:00Z'),
    },
    {
      id: 'sopt-backup-account',
      gateway_type: 'sopt',
      settings: { username: 'test', token: 'test123' },
      priority: 2,
      is_enabled: false,
      description: 'Backup SOPT Account',
      createdAt: new Date('2023-01-01T00:00:00Z'),
      updatedAt: new Date('2023-01-01T00:00:00Z'),
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render the account management page', async () => {
    mockAccountService.getAllAccounts.mockResolvedValue(mockAccounts);

    render(<AccountsPage />);

    // Check page header
    expect(screen.getByText('Account Management')).toBeInTheDocument();
    expect(screen.getByText(/Manage your market data source accounts/)).toBeInTheDocument();

    // Check breadcrumb
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('Accounts')).toBeInTheDocument();

    // Wait for accounts to load
    await waitFor(() => {
      expect(screen.getByText('ctp-main-account')).toBeInTheDocument();
    });
  });

  it('should display accounts in a table format', async () => {
    mockAccountService.getAllAccounts.mockResolvedValue(mockAccounts);

    render(<AccountsPage />);

    await waitFor(() => {
      // Check table headers
      expect(screen.getByText('Account ID')).toBeInTheDocument();
      expect(screen.getByText('Gateway Type')).toBeInTheDocument();
      expect(screen.getByText('Description')).toBeInTheDocument();
      expect(screen.getByText('Priority')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();

      // Check account data
      expect(screen.getByText('ctp-main-account')).toBeInTheDocument();
      expect(screen.getByText('CTP')).toBeInTheDocument();
      expect(screen.getByText('Primary CTP Account')).toBeInTheDocument();
      expect(screen.getByText('Primary')).toBeInTheDocument();
      expect(screen.getByText('Enabled')).toBeInTheDocument();

      expect(screen.getByText('sopt-backup-account')).toBeInTheDocument();
      expect(screen.getByText('SOPT')).toBeInTheDocument();
      expect(screen.getByText('Backup SOPT Account')).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
      expect(screen.getByText('Disabled')).toBeInTheDocument();
    });
  });

  it('should show loading state initially', () => {
    mockAccountService.getAllAccounts.mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<AccountsPage />);

    expect(screen.getByText('Loading accounts...')).toBeInTheDocument();
  });

  it('should handle toggle switch functionality', async () => {
    mockAccountService.getAllAccounts.mockResolvedValue(mockAccounts);
    mockAccountService.toggleAccountStatus.mockResolvedValue({
      ...mockAccounts[1],
      is_enabled: true,
    });

    render(<AccountsPage />);

    await waitFor(() => {
      expect(screen.getByText('sopt-backup-account')).toBeInTheDocument();
    });

    // Find the toggle switch for the disabled account
    const toggleSwitches = screen.getAllByRole('switch');
    const disabledAccountToggle = toggleSwitches[1]; // Second account is disabled

    // Click the toggle switch
    fireEvent.click(disabledAccountToggle);

    await waitFor(() => {
      expect(mockAccountService.toggleAccountStatus).toHaveBeenCalledWith(
        'sopt-backup-account',
        true
      );
    });
  });

  it('should handle refresh button functionality', async () => {
    mockAccountService.getAllAccounts.mockResolvedValue(mockAccounts);

    render(<AccountsPage />);

    await waitFor(() => {
      expect(screen.getByText('ctp-main-account')).toBeInTheDocument();
    });

    // Clear the mock to test refresh
    mockAccountService.getAllAccounts.mockClear();
    mockAccountService.getAllAccounts.mockResolvedValue([mockAccounts[0]]);

    // Click refresh button
    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    fireEvent.click(refreshButton);

    expect(mockAccountService.getAllAccounts).toHaveBeenCalledTimes(1);
  });

  it('should display account summary', async () => {
    mockAccountService.getAllAccounts.mockResolvedValue(mockAccounts);

    render(<AccountsPage />);

    await waitFor(() => {
      expect(screen.getByText('2 accounts total')).toBeInTheDocument();
      expect(screen.getByText('1 enabled, 1 disabled')).toBeInTheDocument();
    });
  });

  it('should handle empty state', async () => {
    mockAccountService.getAllAccounts.mockResolvedValue([]);

    render(<AccountsPage />);

    await waitFor(() => {
      expect(screen.getByText('📊 No Accounts')).toBeInTheDocument();
      expect(screen.getByText('No market data accounts configured yet.')).toBeInTheDocument();
    });
  });

  it('should handle error state', async () => {
    mockAccountService.getAllAccounts.mockRejectedValue(
      new Error('Database connection failed')
    );

    render(<AccountsPage />);

    await waitFor(() => {
      expect(screen.getByText('⚠️ Error')).toBeInTheDocument();
      expect(screen.getByText('Database connection failed')).toBeInTheDocument();
    });
  });

  it('should show correct priority badges', async () => {
    const accountsWithDifferentPriorities: MarketDataAccount[] = [
      { ...mockAccounts[0], priority: 1 }, // Primary
      { ...mockAccounts[1], priority: 3 }, // High
      { ...mockAccounts[0], id: 'test-low', priority: 5 }, // Lower priority
    ];

    mockAccountService.getAllAccounts.mockResolvedValue(accountsWithDifferentPriorities);

    render(<AccountsPage />);

    await waitFor(() => {
      expect(screen.getByText('Primary')).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
      expect(screen.getByText('Priority 5')).toBeInTheDocument();
    });
  });

  it('should show different gateway type badges', async () => {
    mockAccountService.getAllAccounts.mockResolvedValue(mockAccounts);

    render(<AccountsPage />);

    await waitFor(() => {
      expect(screen.getByText('CTP')).toBeInTheDocument();
      expect(screen.getByText('SOPT')).toBeInTheDocument();
    });
  });
});