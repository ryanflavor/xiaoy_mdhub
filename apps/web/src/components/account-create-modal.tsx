'use client';

import React from 'react';
import { MarketDataAccount, AccountSettings } from '@xiaoy-mdhub/shared-types/accounts';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { AccountForm } from './account-form';
import { accountService } from '@/services/account-service';
import { useToast } from '@/hooks/use-toast';

interface AccountCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAccountCreated: (account: MarketDataAccount) => void;
}

export function AccountCreateModal({ isOpen, onClose, onAccountCreated }: AccountCreateModalProps) {
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
      const validationRequest = {
        account_id: accountId,
        gateway_type: gatewayType as "ctp" | "sopt",
        settings,
        timeout_seconds: 30,
        allow_non_trading_validation: validationOptions?.allowNonTradingValidation ?? false,
        use_real_api_validation: validationOptions?.useRealApiValidation ?? false,
      };
      
      // Debug: Log validation request
      console.log('🚀 Sending Validation Request:', {
        account_id: validationRequest.account_id,
        gateway_type: validationRequest.gateway_type,
        allow_non_trading_validation: validationRequest.allow_non_trading_validation,
        use_real_api_validation: validationRequest.use_real_api_validation,
        validationOptions: validationOptions
      });
      
      const result = await accountService.validateAccount(validationRequest);
      
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

  const handleSubmit = (newAccount: MarketDataAccount) => {
    onAccountCreated(newAccount);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Account</DialogTitle>
        </DialogHeader>
        
        <AccountForm
          mode="create"
          onSubmit={handleSubmit}
          onCancel={onClose}
          onValidate={handleValidate}
        />
      </DialogContent>
    </Dialog>
  );
}