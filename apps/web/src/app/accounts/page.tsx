'use client';

import { AccountsManagement } from '@/components/accounts-management';
import { useAccounts } from '@/hooks/use-accounts';

export default function AccountsPage() {
  const { accounts, loading, error, togglingAccounts, refreshAccounts, toggleAccount } = useAccounts();

  return (
    <div className="container mx-auto py-8 px-4 space-y-6">
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
      <AccountsManagement
        accounts={accounts}
        loading={loading}
        error={error}
        onToggleAccount={toggleAccount}
        onRefreshAccounts={refreshAccounts}
        togglingAccounts={togglingAccounts}
      />
    </div>
  );
}