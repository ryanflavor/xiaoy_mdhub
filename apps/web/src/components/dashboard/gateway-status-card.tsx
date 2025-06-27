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
    <Card className="p-3 hover:shadow-md transition-shadow h-full">
      <div className="space-y-2 h-full flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <h3 className="font-medium text-sm leading-tight break-words" title={gateway.gateway_id}>
              {gateway.gateway_id}
            </h3>
            <div className="flex items-center gap-1 mt-1 flex-wrap">
              <Badge variant="outline" className="text-xs px-1 py-0">
                {gateway.gateway_type}
              </Badge>
              <Badge variant="outline" className="text-xs px-1 py-0">
                P{gateway.priority}
              </Badge>
            </div>
          </div>
          <Badge
            variant={getStatusBadgeVariant(gateway.current_status)}
            className="text-xs px-2 py-1 ml-2 flex-shrink-0"
          >
            {gateway.current_status === 'HEALTHY' ? '✓' : 
             gateway.current_status === 'RECOVERING' ? '↻' : 
             gateway.current_status === 'UNHEALTHY' ? '⚠' : '✕'}
          </Badge>
        </div>

        {/* Status Indicator */}
        <div className="flex items-center gap-2">
          {getConnectionIndicator(gateway.connection_status)}
          {gateway.canary_status && (
            <Badge 
              variant={gateway.canary_status === 'ACTIVE' ? 'default' : 'secondary'}
              className="text-xs px-1 py-0"
            >
              🐤
            </Badge>
          )}
        </div>

        {/* Last Tick Time - compact */}
        {gateway.last_tick_time && (
          <div className="text-xs text-muted-foreground break-words">
            {formatDistanceToNow(new Date(gateway.last_tick_time), {
              addSuffix: true,
            })}
          </div>
        )}

        {/* Control Actions - compact */}
        <div className="pt-1 border-t border-border mt-auto">
          <GatewayControls 
            gateway={gateway} 
            onAction={onAction}
            compact={true}
          />
        </div>
      </div>
    </Card>
  );
}