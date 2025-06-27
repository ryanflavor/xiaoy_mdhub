'use client';

import React from 'react';
import { MarketDataAccount, AccountSettings } from '@xiaoy-mdhub/shared-types/accounts';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { AccountForm } from './account-form';
import { accountService } from '@/services/account-service';
import { useToast } from '@/hooks/use-toast';

interface AccountEditModalProps {
  account: MarketDataAccount | null;
  isOpen: boolean;
  onClose: () => void;
  onAccountUpdated: (account: MarketDataAccount) => void;
}

export function AccountEditModal({ account, isOpen, onClose, onAccountUpdated }: AccountEditModalProps) {
  const { toast } = useToast();

  const handleValidate = async (
    accountId: string, 
    gatewayType: string, 
    settings: AccountSettings, 
    validationOptions?: {
      allowNonTradingValidation?: boolean;
      useRealApiValidation?: boolean;
    }
  ): Promise<boolean> => {
    try {
      const result = await accountService.validateAccount({
        account_id: accountId,
        gateway_type: gatewayType as "ctp" | "sopt",
        settings,
        timeout_seconds: 30,
        allow_non_trading_validation: validationOptions?.allowNonTradingValidation || false,
        use_real_api_validation: validationOptions?.useRealApiValidation || false,
      });
      
      if (result.success) {
        const validationType = result.details.validation_type === "REAL_API_LOGIN" ? " (Real API)" : " (Network Test)";
        toast({
          title: "Validation successful" + validationType,
          description: result.message,
        });
        return true;
      } else {
        const errorDetails = result.details.user_friendly_message || result.message;
        toast({
          title: "Validation failed",
          description: errorDetails,
          variant: "destructive",
        });
        return false;
      }
    } catch (error: any) {
      toast({
        title: "Validation error",
        description: error?.message || 'Failed to validate account',
        variant: "destructive",
      });
      return false;
    }
  };

  const handleSubmit = (updatedAccount: MarketDataAccount) => {
    onAccountUpdated(updatedAccount);
    onClose();
  };

  if (!account) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit Account: {account.id}</DialogTitle>
        </DialogHeader>
        
        <AccountForm
          account={account}
          mode="edit"
          onSubmit={handleSubmit}
          onCancel={onClose}
          onValidate={handleValidate}
        />
      </DialogContent>
    </Dialog>
  );
}