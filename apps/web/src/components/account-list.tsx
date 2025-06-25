'use client';

import React from 'react';
import { MarketDataAccount } from '@xiaoy-mdhub/shared-types/accounts';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';

interface AccountListProps {
  accounts: MarketDataAccount[];
  loading: boolean;
  error: string | null;
  onToggleAccount: (accountId: string, isEnabled: boolean) => Promise<void>;
  togglingAccounts: Set<string>;
}

export function AccountList({ 
  accounts, 
  loading, 
  error, 
  onToggleAccount, 
  togglingAccounts 
}: AccountListProps) {
  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading accounts...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="text-destructive mb-2">⚠️ Error</div>
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (accounts.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="text-muted-foreground mb-2">📊 No Accounts</div>
          <p className="text-muted-foreground">No market data accounts configured yet.</p>
        </div>
      </div>
    );
  }

  // Get priority badge variant
  const getPriorityBadgeVariant = (priority: number) => {
    if (priority === 1) return 'default'; // Primary
    if (priority <= 3) return 'secondary'; // High priority
    return 'outline'; // Lower priority
  };

  // Get priority label
  const getPriorityLabel = (priority: number) => {
    if (priority === 1) return 'Primary';
    if (priority <= 3) return 'High';
    return `Priority ${priority}`;
  };

  // Get gateway type badge variant
  const getGatewayTypeVariant = (type: string) => {
    switch (type.toLowerCase()) {
      case 'ctp':
        return 'default';
      case 'sopt':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  return (
    <div className="w-full">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[200px]">Account ID</TableHead>
            <TableHead>Gateway Type</TableHead>
            <TableHead>Description</TableHead>
            <TableHead className="w-[120px]">Priority</TableHead>
            <TableHead className="w-[100px]">Status</TableHead>
            <TableHead className="w-[80px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {accounts.map((account) => (
            <TableRow key={account.id}>
              <TableCell className="font-medium">
                <code className="text-sm bg-muted px-2 py-1 rounded">
                  {account.id}
                </code>
              </TableCell>
              
              <TableCell>
                <Badge variant={getGatewayTypeVariant(account.gateway_type)}>
                  {account.gateway_type.toUpperCase()}
                </Badge>
              </TableCell>
              
              <TableCell>
                <span className="text-sm">
                  {account.description || <em className="text-muted-foreground">No description</em>}
                </span>
              </TableCell>
              
              <TableCell>
                <Badge variant={getPriorityBadgeVariant(account.priority)}>
                  {getPriorityLabel(account.priority)}
                </Badge>
              </TableCell>
              
              <TableCell>
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${
                    account.is_enabled ? 'bg-green-500' : 'bg-gray-400'
                  }`} />
                  <span className="text-sm">
                    {account.is_enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
              </TableCell>
              
              <TableCell>
                <Switch
                  checked={account.is_enabled}
                  disabled={togglingAccounts.has(account.id)}
                  onCheckedChange={(checked) => onToggleAccount(account.id, checked)}
                  aria-label={`Toggle ${account.id} ${account.is_enabled ? 'off' : 'on'}`}
                />
                {togglingAccounts.has(account.id) && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
                  </div>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      
      {/* Account Summary */}
      <div className="flex justify-between items-center mt-4 text-sm text-muted-foreground">
        <span>
          {accounts.length} account{accounts.length !== 1 ? 's' : ''} total
        </span>
        <span>
          {accounts.filter(a => a.is_enabled).length} enabled, {' '}
          {accounts.filter(a => !a.is_enabled).length} disabled
        </span>
      </div>
    </div>
  );
}