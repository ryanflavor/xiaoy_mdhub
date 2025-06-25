'use client';

import { RefreshCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AccountList } from '@/components/account-list';
import { useAccounts } from '@/hooks/use-accounts';

export default function AccountsPage() {
  const { accounts, loading, error, togglingAccounts, refreshAccounts, toggleAccount } = useAccounts();

  return (
    <div className="container mx-auto py-8 px-4 space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Account Management</h1>
          <p className="text-muted-foreground">
            Manage your market data source accounts and enable/disable them for the live data pool.
          </p>
        </div>
        
        <Button
          onClick={refreshAccounts}
          disabled={loading}
          variant="outline"
          size="sm"
          className="flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>
      
      {/* Breadcrumb Navigation */}
      <nav className="flex" aria-label="Breadcrumb">
        <ol className="inline-flex items-center space-x-1 md:space-x-3">
          <li className="inline-flex items-center">
            <a href="/" className="inline-flex items-center text-sm font-medium text-muted-foreground hover:text-foreground">
              Home
            </a>
          </li>
          <li>
            <div className="flex items-center">
              <span className="mx-2 text-muted-foreground">/</span>
              <span className="text-sm font-medium text-foreground">Accounts</span>
            </div>
          </li>
        </ol>
      </nav>

      {/* Main Content Area */}
      <Card>
        <CardHeader>
          <CardTitle>Market Data Accounts</CardTitle>
          <CardDescription>
            Configure and manage your market data source accounts. Toggle the switch to enable or disable accounts for the live data pool.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AccountList
            accounts={accounts}
            loading={loading}
            error={error}
            onToggleAccount={toggleAccount}
            togglingAccounts={togglingAccounts}
          />
        </CardContent>
      </Card>
    </div>
  );
}