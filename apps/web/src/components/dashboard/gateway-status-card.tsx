/**
 * Gateway Status Card Component
 * Displays gateway information including status, type, and connection details
 */

import { GatewayStatus, GatewayControlAction } from '@xiaoy-mdhub/shared-types';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { GatewayControls } from './gateway-controls';
import { formatDistanceToNow } from 'date-fns';

interface GatewayStatusCardProps {
  gateway: GatewayStatus;
  onAction: (action: GatewayControlAction, gatewayId: string) => Promise<void>;
}

function getStatusBadgeVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'HEALTHY':
      return 'default';
    case 'RECOVERING':
      return 'secondary';
    case 'UNHEALTHY':
    case 'DISCONNECTED':
      return 'destructive';
    default:
      return 'outline';
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'HEALTHY':
      return 'text-green-600 dark:text-green-400';
    case 'RECOVERING':
      return 'text-yellow-600 dark:text-yellow-400';
    case 'UNHEALTHY':
    case 'DISCONNECTED':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

function getConnectionIndicator(connectionStatus: string): JSX.Element {
  const isConnected = connectionStatus === 'CONNECTED';
  return (
    <div className="flex items-center gap-2">
      <div 
        className={`w-2 h-2 rounded-full ${
          isConnected ? 'bg-green-500' : 'bg-red-500'
        }`} 
      />
      <span className="text-sm text-muted-foreground">
        {connectionStatus}
      </span>
    </div>
  );
}

export function GatewayStatusCard({ gateway, onAction }: GatewayStatusCardProps) {
  const lastUpdateFormatted = formatDistanceToNow(new Date(gateway.last_update), {
    addSuffix: true,
  });

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-sm truncate" title={gateway.gateway_id}>
              {gateway.gateway_id}
            </h3>
            <p className="text-xs text-muted-foreground uppercase tracking-wide">
              {gateway.gateway_type}
            </p>
          </div>
          <Badge
            variant={getStatusBadgeVariant(gateway.current_status)}
            className="text-xs"
          >
            {gateway.current_status}
          </Badge>
        </div>

        {/* Status Details */}
        <div className="space-y-2">
          {/* Connection Status */}
          {getConnectionIndicator(gateway.connection_status)}

          {/* Priority */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Priority:</span>
            <span className="font-medium">{gateway.priority}</span>
          </div>

          {/* Last Tick Time */}
          {gateway.last_tick_time && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Last Tick:</span>
              <span className="text-xs">
                {formatDistanceToNow(new Date(gateway.last_tick_time), {
                  addSuffix: true,
                })}
              </span>
            </div>
          )}

          {/* Canary Status */}
          {gateway.canary_status && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Canary:</span>
              <Badge 
                variant={gateway.canary_status === 'ACTIVE' ? 'default' : 'secondary'}
                className="text-xs"
              >
                {gateway.canary_status}
              </Badge>
            </div>
          )}
        </div>

        {/* Control Actions */}
        <div className="pt-2 border-t border-border">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">Actions:</span>
            <GatewayControls 
              gateway={gateway} 
              onAction={onAction}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="pt-2 border-t border-border">
          <p className="text-xs text-muted-foreground">
            Updated {lastUpdateFormatted}
          </p>
        </div>
      </div>
    </Card>
  );
}