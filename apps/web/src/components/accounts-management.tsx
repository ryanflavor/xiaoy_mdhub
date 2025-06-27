'use client';

import React, { useState, useMemo } from 'react';
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
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Plus, 
  Edit, 
  Trash2, 
  RefreshCw, 
  Info,
  ChevronUp,
  ChevronDown,
  Settings
} from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { AccountCreateModal } from './account-create-modal';
import { AccountEditModal } from './account-edit-modal';
import { AccountDeleteDialog } from './account-delete-dialog';

interface AccountsManagementProps {
  accounts: MarketDataAccount[];
  loading: boolean;
  error: string | null;
  onToggleAccount: (accountId: string, isEnabled: boolean) => Promise<void>;
  onRefreshAccounts: () => Promise<void>;
  togglingAccounts: Set<string>;
}

export function AccountsManagement({ 
  accounts, 
  loading, 
  error, 
  onToggleAccount, 
  onRefreshAccounts,
  togglingAccounts 
}: AccountsManagementProps) {
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState<MarketDataAccount | null>(null);
  const [localAccounts, setLocalAccounts] = useState<MarketDataAccount[]>(accounts);

  // Update local accounts when props change
  React.useEffect(() => {
    setLocalAccounts(accounts);
  }, [accounts]);

  // Separate accounts by gateway type
  const { ctpAccounts, soptAccounts } = useMemo(() => {
    const ctp = localAccounts.filter(account => account.gateway_type.toLowerCase() === 'ctp');
    const sopt = localAccounts.filter(account => account.gateway_type.toLowerCase() === 'sopt');
    
    // Sort by priority (lower number = higher priority)
    const sortByPriority = (a: MarketDataAccount, b: MarketDataAccount) => a.priority - b.priority;
    
    return {
      ctpAccounts: ctp.sort(sortByPriority),
      soptAccounts: sopt.sort(sortByPriority)
    };
  }, [localAccounts]);

  const handleAccountCreated = (newAccount: MarketDataAccount) => {
    setLocalAccounts(prev => [...prev, newAccount]);
    onRefreshAccounts(); // Refresh from server to ensure consistency
  };

  const handleAccountUpdated = (updatedAccount: MarketDataAccount) => {
    setLocalAccounts(prev => 
      prev.map(account => 
        account.id === updatedAccount.id ? updatedAccount : account
      )
    );
    onRefreshAccounts(); // Refresh from server to ensure consistency
  };

  const handleAccountDeleted = (accountId: string) => {
    setLocalAccounts(prev => prev.filter(account => account.id !== accountId));
    onRefreshAccounts(); // Refresh from server to ensure consistency
  };

  const handleEditAccount = (account: MarketDataAccount) => {
    setSelectedAccount(account);
    setEditModalOpen(true);
  };

  const handleDeleteAccount = (account: MarketDataAccount) => {
    setSelectedAccount(account);
    setDeleteDialogOpen(true);
  };

  const getPriorityBadgeVariant = (priority: number) => {
    if (priority === 1) return 'default'; // Primary
    if (priority <= 3) return 'secondary'; // High priority
    return 'outline'; // Lower priority
  };

  const getPriorityLabel = (priority: number) => {
    if (priority === 1) return 'Primary';
    if (priority <= 3) return 'High';
    return `Priority ${priority}`;
  };

  const renderAccountsTable = (accountsList: MarketDataAccount[], gatewayType: string) => {
    if (accountsList.length === 0) {
      return (
        <div className="flex items-center justify-center py-8">
          <div className="text-center">
            <Settings className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No {gatewayType.toUpperCase()} accounts configured</p>
            <Button 
              onClick={() => setCreateModalOpen(true)} 
              variant="outline" 
              size="sm" 
              className="mt-2"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add {gatewayType.toUpperCase()} Account
            </Button>
          </div>
        </div>
      );
    }

    return (
      <div className="w-full">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[200px]">Account ID</TableHead>
              <TableHead>Account Details</TableHead>
              <TableHead className="w-[120px]">
                <div className="flex items-center gap-1">
                  Priority
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger>
                        <Info className="h-3 w-3 text-muted-foreground" />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Lower number = higher priority</p>
                        <p>Priority 1 = Primary account</p>
                        <p>Used for failover ordering</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </TableHead>
              <TableHead className="w-[100px]">Status</TableHead>
              <TableHead className="w-[180px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {accountsList.map((account) => (
              <TableRow key={account.id}>
                <TableCell className="font-medium">
                  <code className="text-sm bg-muted px-2 py-1 rounded">
                    {account.id}
                  </code>
                </TableCell>
                
                <TableCell>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{account.settings?.name || account.settings?.broker || 'Unnamed'}</span>
                      <Badge variant="outline" className="text-xs">
                        {account.settings?.market || 'Unknown Market'}
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {account.settings?.broker || 'No broker specified'}
                    </div>
                    {account.description && (
                      <div className="text-xs text-muted-foreground">
                        {account.description}
                      </div>
                    )}
                  </div>
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
                  <div className="flex items-center space-x-2">
                    <Switch
                      checked={account.is_enabled}
                      disabled={togglingAccounts.has(account.id)}
                      onCheckedChange={(checked) => onToggleAccount(account.id, checked)}
                      aria-label={`Toggle ${account.id} ${account.is_enabled ? 'off' : 'on'}`}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditAccount(account)}
                    >
                      <Edit className="h-3 w-3" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteAccount(account)}
                      className="text-red-600 hover:text-red-700"
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        
        {/* Account Summary */}
        <div className="flex justify-between items-center mt-4 text-sm text-muted-foreground">
          <span>
            {accountsList.length} {gatewayType.toUpperCase()} account{accountsList.length !== 1 ? 's' : ''} total
          </span>
          <span>
            {accountsList.filter(a => a.is_enabled).length} enabled, {' '}
            {accountsList.filter(a => !a.is_enabled).length} disabled
          </span>
        </div>
      </div>
    );
  };

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
          <Button onClick={onRefreshAccounts} variant="outline" className="mt-2">
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Account Management</h2>
          <p className="text-muted-foreground">
            Manage CTP and SOPT trading accounts with priority-based failover
          </p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={onRefreshAccounts} variant="outline" size="sm">
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button onClick={() => setCreateModalOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Account
          </Button>
        </div>
      </div>

      {/* Accounts by Gateway Type */}
      <Tabs defaultValue="ctp" className="w-full">
        <TabsList>
          <TabsTrigger value="ctp" className="flex items-center gap-2">
            CTP Accounts
            <Badge variant="secondary" className="ml-1">
              {ctpAccounts.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="sopt" className="flex items-center gap-2">
            SOPT Accounts
            <Badge variant="secondary" className="ml-1">
              {soptAccounts.length}
            </Badge>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="ctp">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                CTP Accounts (期货期权)
                <Badge variant="outline">Futures & Options</Badge>
              </CardTitle>
              <CardDescription>
                Manage your CTP gateway accounts for futures and options trading
              </CardDescription>
            </CardHeader>
            <CardContent>
              {renderAccountsTable(ctpAccounts, 'ctp')}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sopt">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                SOPT Accounts (个股期权)
                <Badge variant="outline">Stock Options</Badge>
              </CardTitle>
              <CardDescription>
                Manage your SOPT gateway accounts for individual stock options trading
              </CardDescription>
            </CardHeader>
            <CardContent>
              {renderAccountsTable(soptAccounts, 'sopt')}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Modals and Dialogs */}
      <AccountCreateModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onAccountCreated={handleAccountCreated}
      />

      <AccountEditModal
        account={selectedAccount}
        isOpen={editModalOpen}
        onClose={() => {
          setEditModalOpen(false);
          setSelectedAccount(null);
        }}
        onAccountUpdated={handleAccountUpdated}
      />

      <AccountDeleteDialog
        account={selectedAccount}
        isOpen={deleteDialogOpen}
        onClose={() => {
          setDeleteDialogOpen(false);
          setSelectedAccount(null);
        }}
        onAccountDeleted={handleAccountDeleted}
      />
    </div>
  );
}