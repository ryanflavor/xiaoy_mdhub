'use client';

import { useState, useEffect, useCallback } from 'react';
import { MarketDataAccount } from '@xiaoy-mdhub/shared-types/accounts';
import { accountService } from '@/services/account-service';
import { useToast } from '@/hooks/use-toast';

interface UseAccountsState {
  accounts: MarketDataAccount[];
  loading: boolean;
  error: string | null;
  togglingAccounts: Set<string>;
}

interface UseAccountsActions {
  refreshAccounts: () => Promise<void>;
  toggleAccount: (accountId: string, isEnabled: boolean) => Promise<void>;
}

export function useAccounts(): UseAccountsState & UseAccountsActions {
  const [state, setState] = useState<UseAccountsState>({
    accounts: [],
    loading: true,
    error: null,
    togglingAccounts: new Set(),
  });
  
  const { toast } = useToast();

  // Fetch accounts from the API
  const refreshAccounts = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      const accounts = await accountService.getAllAccounts();
      setState(prev => ({ ...prev, accounts, loading: false }));
    } catch (error: any) {
      const errorMessage = error?.message || 'Failed to fetch accounts';
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: errorMessage 
      }));
      
      toast({
        title: "Error loading accounts",
        description: errorMessage,
        variant: "destructive",
      });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Toggle account enabled status with optimistic updates
  const toggleAccount = useCallback(async (accountId: string, isEnabled: boolean) => {
    try {
      // Add to toggling set
      setState(prev => ({
        ...prev,
        togglingAccounts: new Set([...Array.from(prev.togglingAccounts), accountId])
      }));

      // Optimistic update
      setState(prev => ({
        ...prev,
        accounts: prev.accounts.map(account =>
          account.id === accountId
            ? { ...account, is_enabled: isEnabled }
            : account
        )
      }));

      // Make API call
      const updatedAccount = await accountService.toggleAccountStatus(accountId, isEnabled);
      
      // Update with server response
      setState(prev => ({
        ...prev,
        accounts: prev.accounts.map(account =>
          account.id === accountId ? updatedAccount : account
        ),
        togglingAccounts: new Set(Array.from(prev.togglingAccounts).filter(id => id !== accountId))
      }));

      // Show success toast
      toast({
        title: "Account updated",
        description: `${accountId} has been ${isEnabled ? 'enabled' : 'disabled'}`,
      });

    } catch (error: any) {
      // Rollback optimistic update
      setState(prev => ({
        ...prev,
        accounts: prev.accounts.map(account =>
          account.id === accountId
            ? { ...account, is_enabled: !isEnabled }
            : account
        ),
        togglingAccounts: new Set(Array.from(prev.togglingAccounts).filter(id => id !== accountId))
      }));

      const errorMessage = error?.message || 'Failed to update account';
      
      toast({
        title: "Error updating account",
        description: errorMessage,
        variant: "destructive",
      });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Load accounts on mount
  useEffect(() => {
    refreshAccounts();
  }, [refreshAccounts]);

  return {
    ...state,
    refreshAccounts,
    toggleAccount,
  };
}