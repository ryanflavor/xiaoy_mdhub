/**
 * Account Service - API operations for market data accounts
 * Implements the dedicated service layer pattern as per coding standards
 */

import { 
  MarketDataAccount, 
  UpdateAccountRequest, 
  CreateAccountRequest, 
  AccountSettings,
  AccountValidationRequest,
  AccountValidationResponse
} from '@xiaoy-mdhub/shared-types/accounts';
import { ApiClient, ApiResponse, ApiError } from './api-client';

export class AccountService {
  private apiClient: ApiClient;

  constructor() {
    this.apiClient = new ApiClient();
  }

  /**
   * Fetch all accounts from the backend API
   * @returns Promise with array of MarketDataAccount objects
   */
  async getAllAccounts(): Promise<MarketDataAccount[]> {
    try {
      const response: ApiResponse<MarketDataAccount[]> = await this.apiClient.get('/api/accounts');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch accounts:', error);
      throw error;
    }
  }

  /**
   * Update an existing account
   * @param accountId - The ID of the account to update
   * @param updateData - Partial account data to update
   * @returns Promise with updated MarketDataAccount object
   */
  async updateAccount(
    accountId: string, 
    updateData: UpdateAccountRequest
  ): Promise<MarketDataAccount> {
    try {
      const response: ApiResponse<MarketDataAccount> = await this.apiClient.put(
        `/api/accounts/${accountId}`,
        updateData
      );
      return response.data;
    } catch (error) {
      console.error(`Failed to update account ${accountId}:`, error);
      throw error;
    }
  }

  /**
   * Toggle the enabled status of an account
   * @param accountId - The ID of the account to toggle
   * @param isEnabled - The new enabled status
   * @returns Promise with updated MarketDataAccount object
   */
  async toggleAccountStatus(
    accountId: string, 
    isEnabled: boolean
  ): Promise<MarketDataAccount> {
    return this.updateAccount(accountId, { is_enabled: isEnabled });
  }

  /**
   * Create a new account
   * @param accountData - The account data to create
   * @returns Promise with created MarketDataAccount object
   */
  async createAccount(accountData: CreateAccountRequest & { id: string }): Promise<MarketDataAccount> {
    try {
      const response: ApiResponse<MarketDataAccount> = await this.apiClient.post(
        '/api/accounts',
        accountData
      );
      return response.data;
    } catch (error) {
      console.error('Failed to create account:', error);
      throw error;
    }
  }

  /**
   * Delete an account
   * @param accountId - The ID of the account to delete
   * @returns Promise that resolves when deletion is complete
   */
  async deleteAccount(accountId: string): Promise<void> {
    try {
      await this.apiClient.delete(`/api/accounts/${accountId}`);
    } catch (error) {
      console.error(`Failed to delete account ${accountId}:`, error);
      throw error;
    }
  }

  /**
   * Validate account credentials
   * @param validationRequest - Complete validation request with all options
   * @returns Promise with validation result
   */
  async validateAccount(
    validationRequest: AccountValidationRequest
  ): Promise<AccountValidationResponse> {
    try {
      const response: ApiResponse<AccountValidationResponse> = await this.apiClient.post(
        '/api/accounts/validate',
        validationRequest
      );
      return response.data;
    } catch (error) {
      console.error('Failed to validate account:', error);
      throw error;
    }
  }

  /**
   * Validate account credentials (legacy method for backward compatibility)
   * @param accountId - The account identifier for validation
   * @param gatewayType - The gateway type (ctp or sopt)
   * @param settings - The account settings to validate
   * @param timeoutSeconds - Validation timeout in seconds
   * @param allowNonTradingValidation - Allow validation outside trading hours
   * @param useRealApiValidation - Use real API validation instead of basic connectivity
   * @returns Promise with validation result
   */
  async validateAccountLegacy(
    accountId: string,
    gatewayType: "ctp" | "sopt",
    settings: AccountSettings,
    timeoutSeconds: number = 30,
    allowNonTradingValidation: boolean = false,
    useRealApiValidation: boolean = false
  ): Promise<AccountValidationResponse> {
    return this.validateAccount({
      account_id: accountId,
      gateway_type: gatewayType,
      settings,
      timeout_seconds: timeoutSeconds,
      allow_non_trading_validation: allowNonTradingValidation,
      use_real_api_validation: useRealApiValidation
    });
  }
}

// Export a singleton instance for convenience
export const accountService = new AccountService();