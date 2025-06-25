/**
 * System Health Summary Component
 * Displays overall system health metrics and gateway distribution
 */

import { SystemHealthSummary as SystemHealthData } from '@xiaoy-mdhub/shared-types';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDistanceToNow } from 'date-fns';

interface SystemHealthSummaryProps {
  systemHealth: SystemHealthData;
  isConnected: boolean;
}

function getOverallStatusColor(status: string): string {
  switch (status) {
    case 'HEALTHY':
      return 'text-green-600 dark:text-green-400';
    case 'DEGRADED':
      return 'text-yellow-600 dark:text-yellow-400';
    case 'UNHEALTHY':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

function getOverallStatusBadge(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'HEALTHY':
      return 'default';
    case 'DEGRADED':
      return 'secondary';
    case 'UNHEALTHY':
      return 'destructive';
    default:
      return 'outline';
  }
}

function getHealthPercentage(healthy: number, total: number): number {
  if (total === 0) return 100;
  return Math.round((healthy / total) * 100);
}

export function SystemHealthSummary({ systemHealth, isConnected }: SystemHealthSummaryProps) {
  const {
    total_gateways,
    healthy_gateways,
    unhealthy_gateways,
    recovering_gateways,
    overall_status,
    last_updated,
  } = systemHealth;

  const healthPercentage = getHealthPercentage(healthy_gateways, total_gateways);
  const lastUpdatedFormatted = formatDistanceToNow(new Date(last_updated), {
    addSuffix: true,
  });

  return (
    <Card className="p-6">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold">System Health</h2>
            <Badge
              variant={getOverallStatusBadge(overall_status)}
              className="text-sm"
            >
              {overall_status}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <div 
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`} 
            />
            <span className="text-sm text-muted-foreground">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Health Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Total Gateways */}
          <div className="text-center">
            <div className="text-2xl font-bold text-foreground">
              {total_gateways}
            </div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              Total Gateways
            </div>
          </div>

          {/* Healthy Gateways */}
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {healthy_gateways}
            </div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              Healthy
            </div>
          </div>

          {/* Unhealthy Gateways */}
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {unhealthy_gateways}
            </div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              Unhealthy
            </div>
          </div>

          {/* Recovering Gateways */}
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {recovering_gateways}
            </div>
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              Recovering
            </div>
          </div>
        </div>

        {/* Health Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">System Health</span>
            <span className="text-sm text-muted-foreground">
              {healthPercentage}%
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                healthPercentage >= 80
                  ? 'bg-green-500'
                  : healthPercentage >= 50
                  ? 'bg-yellow-500'
                  : 'bg-red-500'
              }`}
              style={{ width: `${healthPercentage}%` }}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <span className="text-xs text-muted-foreground">
            Last updated {lastUpdatedFormatted}
          </span>
          {!isConnected && (
            <Badge variant="destructive" className="text-xs">
              Real-time updates disabled
            </Badge>
          )}
        </div>
      </div>
    </Card>
  );
}