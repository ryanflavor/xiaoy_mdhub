/**
 * Account Service - API operations for market data accounts
 * Implements the dedicated service layer pattern as per coding standards
 */

import { MarketDataAccount, UpdateAccountRequest } from '@xiaoy-mdhub/shared-types/accounts';
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
}

// Export a singleton instance for convenience
export const accountService = new AccountService();