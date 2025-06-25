/**
 * Canary Contract Monitor Component
 * Displays canary contract heartbeat monitoring and tick data
 */

import { CanaryMonitorData } from '@xiaoy-mdhub/shared-types';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';

interface CanaryMonitorProps {
  contracts: CanaryMonitorData[];
  isConnected: boolean;
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'ACTIVE':
      return 'text-green-600 dark:text-green-400';
    case 'STALE':
      return 'text-yellow-600 dark:text-yellow-400';
    case 'INACTIVE':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

function getStatusBadgeVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'ACTIVE':
      return 'default';
    case 'STALE':
      return 'secondary';
    case 'INACTIVE':
      return 'destructive';
    default:
      return 'outline';
  }
}

function getTickActivityLevel(tickCount: number): { level: string; color: string; description: string } {
  if (tickCount >= 50) {
    return {
      level: 'HIGH',
      color: 'text-green-600 dark:text-green-400',
      description: 'Very active',
    };
  } else if (tickCount >= 20) {
    return {
      level: 'MEDIUM',
      color: 'text-yellow-600 dark:text-yellow-400',
      description: 'Moderate activity',
    };
  } else if (tickCount > 0) {
    return {
      level: 'LOW',
      color: 'text-orange-600 dark:text-orange-400',
      description: 'Low activity',
    };
  } else {
    return {
      level: 'NONE',
      color: 'text-red-600 dark:text-red-400',
      description: 'No activity',
    };
  }
}

function CanaryContractCard({ contract }: { contract: CanaryMonitorData }) {
  const lastTickFormatted = formatDistanceToNow(new Date(contract.last_tick_time), {
    addSuffix: true,
  });

  const tickActivity = getTickActivityLevel(contract.tick_count_1min);

  return (
    <Card className="p-4">
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h4 className="font-semibold text-sm">
              {contract.contract_symbol}
            </h4>
            <p className="text-xs text-muted-foreground">
              Canary Contract
            </p>
          </div>
          <Badge
            variant={getStatusBadgeVariant(contract.status)}
            className="text-xs"
          >
            {contract.status}
          </Badge>
        </div>

        {/* Tick Activity */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Tick Activity</span>
            <div className="flex items-center gap-2">
              <div 
                className={`w-2 h-2 rounded-full ${
                  contract.status === 'ACTIVE' ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                }`} 
              />
              <span className={`text-xs font-medium ${tickActivity.color}`}>
                {tickActivity.level}
              </span>
            </div>
          </div>

          {/* Tick Count */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Ticks (1 min):</span>
            <span className={`font-medium ${tickActivity.color}`}>
              {contract.tick_count_1min}
            </span>
          </div>

          {/* Tick Activity Description */}
          <p className="text-xs text-muted-foreground">
            {tickActivity.description}
          </p>
        </div>

        {/* Timing Information */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Last Tick:</span>
            <span className="text-xs">
              {lastTickFormatted}
            </span>
          </div>

          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Threshold:</span>
            <span className="text-xs">
              {contract.threshold_seconds}s
            </span>
          </div>
        </div>

        {/* Visual Heartbeat */}
        <div className="pt-2 border-t border-border">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Heartbeat:</span>
            <div className="flex gap-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className={`w-1 h-4 rounded ${
                    contract.status === 'ACTIVE' && i < Math.min(5, Math.ceil(contract.tick_count_1min / 10))
                      ? 'bg-green-500'
                      : 'bg-gray-300 dark:bg-gray-600'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

export function CanaryMonitor({ contracts, isConnected }: CanaryMonitorProps) {
  const activeContracts = contracts.filter(c => c.status === 'ACTIVE').length;
  const totalContracts = contracts.length;

  return (
    <div className="space-y-4">
      {/* Overview */}
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold">Canary Contract Overview</h3>
            <p className="text-sm text-muted-foreground">
              Monitoring {totalContracts} contracts, {activeContracts} active
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div 
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} 
            />
            <Badge variant={isConnected ? 'default' : 'secondary'} className="text-xs">
              {isConnected ? 'Live' : 'Offline'}
            </Badge>
          </div>
        </div>

        {/* Summary Stats */}
        {totalContracts > 0 && (
          <div className="mt-4 grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-lg font-bold text-green-600 dark:text-green-400">
                {activeContracts}
              </div>
              <div className="text-xs text-muted-foreground uppercase tracking-wide">
                Active
              </div>
            </div>
            <div>
              <div className="text-lg font-bold text-yellow-600 dark:text-yellow-400">
                {contracts.filter(c => c.status === 'STALE').length}
              </div>
              <div className="text-xs text-muted-foreground uppercase tracking-wide">
                Stale
              </div>
            </div>
            <div>
              <div className="text-lg font-bold text-red-600 dark:text-red-400">
                {contracts.filter(c => c.status === 'INACTIVE').length}
              </div>
              <div className="text-xs text-muted-foreground uppercase tracking-wide">
                Inactive
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Contract Cards */}
      {contracts.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-muted-foreground">
            No canary contracts configured
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            Canary contracts help monitor data flow health and connectivity
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {contracts.map((contract) => (
            <CanaryContractCard
              key={contract.contract_symbol}
              contract={contract}
            />
          ))}
        </div>
      )}
    </div>
  );
}