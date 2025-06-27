'use client';

import React, { useState } from 'react';
import { MarketDataAccount } from '@xiaoy-mdhub/shared-types/accounts';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Loader2, AlertTriangle } from 'lucide-react';
import { accountService } from '@/services/account-service';
import { useToast } from '@/hooks/use-toast';

interface AccountDeleteDialogProps {
  account: MarketDataAccount | null;
  isOpen: boolean;
  onClose: () => void;
  onAccountDeleted: (accountId: string) => void;
}

export function AccountDeleteDialog({ account, isOpen, onClose, onAccountDeleted }: AccountDeleteDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const { toast } = useToast();

  const handleDelete = async () => {
    if (!account) return;

    setIsDeleting(true);
    try {
      await accountService.deleteAccount(account.id);
      
      toast({
        title: "Account deleted",
        description: `Account ${account.id} has been deleted successfully`,
      });
      
      onAccountDeleted(account.id);
      onClose();
    } catch (error: any) {
      toast({
        title: "Error deleting account",
        description: error?.message || 'Failed to delete account',
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  if (!account) return null;

  return (
    <AlertDialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            Delete Account
          </AlertDialogTitle>
          <AlertDialogDescription className="space-y-2">
            <p>
              Are you sure you want to delete the account <strong>{account.id}</strong>?
            </p>
            <p className="text-sm text-muted-foreground">
              <strong>Account Details:</strong>
            </p>
            <ul className="text-sm text-muted-foreground space-y-1 ml-4">
              <li>• Gateway: {account.gateway_type.toUpperCase()}</li>
              <li>• Broker: {account.settings?.broker || 'N/A'}</li>
              <li>• Priority: {account.priority}</li>
              <li>• Status: {account.is_enabled ? 'Enabled' : 'Disabled'}</li>
              {account.description && <li>• Description: {account.description}</li>}
            </ul>
            <p className="text-red-600 font-medium mt-3">
              This action cannot be undone. The account configuration will be permanently removed.
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction 
            onClick={handleDelete}
            disabled={isDeleting}
            className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
          >
            {isDeleting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Account'
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}