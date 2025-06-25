/**
 * Account Service Tests
 * Tests for API operations for market data accounts
 */

import { AccountService } from '../account-service';
import { MarketDataAccount } from '@xiaoy-mdhub/shared-types/accounts';
import { ApiClient } from '../api-client';

// Mock the ApiClient module
jest.mock('../api-client');

// Mock console.error to reduce test output noise
const mockConsoleError = jest.spyOn(console, 'error').mockImplementation();

describe('AccountService', () => {
  let accountService: AccountService;
  let mockApiClient: jest.Mocked<ApiClient>;

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Create a mock ApiClient instance
    mockApiClient = {
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
    } as any;
    
    // Mock the ApiClient constructor to return our mock instance
    (ApiClient as jest.MockedClass<typeof ApiClient>).mockImplementation(() => mockApiClient);
    
    accountService = new AccountService();
    mockConsoleError.mockClear();
  });

  afterAll(() => {
    mockConsoleError.mockRestore();
  });

  describe('getAllAccounts', () => {
    const mockAccounts: MarketDataAccount[] = [
      {
        id: 'test-account-1',
        gateway_type: 'ctp',
        settings: { userID: 'test', password: 'test' },
        priority: 1,
        is_enabled: true,
        description: 'Test Account 1',
        createdAt: new Date('2023-01-01T00:00:00Z'),
        updatedAt: new Date('2023-01-01T00:00:00Z'),
      },
      {
        id: 'test-account-2',
        gateway_type: 'sopt',
        settings: { username: 'test', token: 'test' },
        priority: 2,
        is_enabled: false,
        description: 'Test Account 2',
        createdAt: new Date('2023-01-01T00:00:00Z'),
        updatedAt: new Date('2023-01-01T00:00:00Z'),
      },
    ];

    it('should fetch all accounts successfully', async () => {
      mockApiClient.get.mockResolvedValueOnce({
        data: mockAccounts,
        status: 200,
        statusText: 'OK',
      });

      const result = await accountService.getAllAccounts();

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/accounts');
      expect(result).toEqual(mockAccounts);
    });

    it('should handle API error responses', async () => {
      const apiError = {
        message: 'Database connection failed',
        status: 500,
        details: { detail: 'Database connection failed' }
      };

      mockApiClient.get.mockRejectedValueOnce(apiError);

      await expect(accountService.getAllAccounts()).rejects.toMatchObject({
        message: 'Database connection failed',
        status: 500,
      });

      expect(mockConsoleError).toHaveBeenCalledWith(
        'Failed to fetch accounts:',
        expect.objectContaining({
          message: 'Database connection failed',
          status: 500,
        })
      );
    });

    it('should handle network errors', async () => {
      const networkError = {
        message: 'Network error',
        status: 0,
        details: new Error('Network error')
      };

      mockApiClient.get.mockRejectedValueOnce(networkError);

      await expect(accountService.getAllAccounts()).rejects.toMatchObject({
        message: 'Network error',
        status: 0,
      });

      expect(mockConsoleError).toHaveBeenCalledWith(
        'Failed to fetch accounts:',
        expect.objectContaining({
          message: 'Network error',
          status: 0,
        })
      );
    });
  });

  describe('updateAccount', () => {
    const mockUpdatedAccount: MarketDataAccount = {
      id: 'test-account-1',
      gateway_type: 'ctp',
      settings: { userID: 'test', password: 'test' },
      priority: 1,
      is_enabled: false,
      description: 'Updated Test Account',
      createdAt: new Date('2023-01-01T00:00:00Z'),
      updatedAt: new Date('2023-01-02T00:00:00Z'),
    };

    it('should update account successfully', async () => {
      const updateData = {
        is_enabled: false,
        description: 'Updated Test Account',
      };

      mockApiClient.put.mockResolvedValueOnce({
        data: mockUpdatedAccount,
        status: 200,
        statusText: 'OK',
      });

      const result = await accountService.updateAccount('test-account-1', updateData);

      expect(mockApiClient.put).toHaveBeenCalledWith(
        '/api/accounts/test-account-1',
        updateData
      );
      expect(result).toEqual(mockUpdatedAccount);
    });

    it('should handle update errors', async () => {
      const apiError = {
        message: 'Account not found',
        status: 404,
        details: { detail: 'Account not found' }
      };

      mockApiClient.put.mockRejectedValueOnce(apiError);

      await expect(
        accountService.updateAccount('nonexistent', { is_enabled: true })
      ).rejects.toMatchObject({
        message: 'Account not found',
        status: 404,
      });
    });
  });

  describe('toggleAccountStatus', () => {
    it('should toggle account status to enabled', async () => {
      const mockAccount: MarketDataAccount = {
        id: 'test-account-1',
        gateway_type: 'ctp',
        settings: { userID: 'test', password: 'test' },
        priority: 1,
        is_enabled: true,
        description: 'Test Account',
        createdAt: new Date('2023-01-01T00:00:00Z'),
        updatedAt: new Date('2023-01-02T00:00:00Z'),
      };

      mockApiClient.put.mockResolvedValueOnce({
        data: mockAccount,
        status: 200,
        statusText: 'OK',
      });

      const result = await accountService.toggleAccountStatus('test-account-1', true);

      expect(mockApiClient.put).toHaveBeenCalledWith(
        '/api/accounts/test-account-1',
        { is_enabled: true }
      );
      expect(result).toEqual(mockAccount);
    });

    it('should toggle account status to disabled', async () => {
      const mockAccount: MarketDataAccount = {
        id: 'test-account-1',
        gateway_type: 'ctp',
        settings: { userID: 'test', password: 'test' },
        priority: 1,
        is_enabled: false,
        description: 'Test Account',
        createdAt: new Date('2023-01-01T00:00:00Z'),
        updatedAt: new Date('2023-01-02T00:00:00Z'),
      };

      mockApiClient.put.mockResolvedValueOnce({
        data: mockAccount,
        status: 200,
        statusText: 'OK',
      });

      const result = await accountService.toggleAccountStatus('test-account-1', false);

      expect(result.is_enabled).toBe(false);
    });
  });
});