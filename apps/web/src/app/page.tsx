'use client';

import { Suspense, useCallback } from 'react';
import { useDashboardData } from '@/hooks/use-dashboard-data';
import { SystemHealthSummary } from '@/components/dashboard/system-health-summary';
import { GatewayStatusCard } from '@/components/dashboard/gateway-status-card';
import { CanaryMonitor } from '@/components/dashboard/canary-monitor';
import { TradingTimeStatus } from '@/components/TradingTimeStatus';
import { WebSocketState, GatewayControlAction } from '@xiaoy-mdhub/shared-types';
import { gatewayService } from '@/services/api';
import { useToast } from '@/hooks/use-toast';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

function ConnectionStatus({ state, isConnected }: { state: WebSocketState; isConnected: boolean }) {
  const getStatusColor = () => {
    switch (state) {
      case WebSocketState.CONNECTED:
        return 'bg-green-500';
      case WebSocketState.CONNECTING:
      case WebSocketState.RECONNECTING:
        return 'bg-yellow-500';
      case WebSocketState.ERROR:
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${getStatusColor()}`} />
      <Badge variant={isConnected ? 'default' : 'secondary'}>
        {state}
      </Badge>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-6 w-24" />
      </div>
      <Skeleton className="h-32 w-full" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-48 w-full" />
        ))}
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function DashboardContent() {
  const { data, isConnected, connectionState, error, refreshData } = useDashboardData();
  const { toast } = useToast();

  // Handle gateway control actions
  const handleGatewayAction = useCallback(async (action: GatewayControlAction, gatewayId: string) => {
    try {
      // Show loading toast
      const loadingToast = toast({
        title: `${action.charAt(0).toUpperCase() + action.slice(1)}ing Gateway`,
        description: `Executing ${action} action for ${gatewayId}...`,
      });

      const response = await gatewayService.controlGateway(action, gatewayId);
      
      // Dismiss loading toast
      loadingToast.dismiss();
      
      if (!response.data.success) {
        throw new Error(response.data.message || 'Control action failed');
      }
      
      // Show success toast
      toast({
        title: "Success",
        description: `Gateway ${action} action completed successfully`,
        variant: "default",
      });
      
    } catch (error: any) {
      let errorMessage = 'Unknown error occurred';
      let errorTitle = "Gateway Control Failed";
      
      // Debug logging - remove after fixing
      console.log('Full error object:', error);
      console.log('Error status:', error.status);
      console.log('Error details:', error.details);
      console.log('Error response:', error.response);
      
      // Handle different error types
      // Check for custom ApiError format first
      if (error.status === 423) {
        // Trading time restriction
        const detail = error.details?.detail || error.details;
        if (detail && detail.error === 'TRADING_TIME_RESTRICTED') {
          errorTitle = "当前不在交易时间";
          errorMessage = detail.user_message || "当前不在交易时间，请等待下次交易时段开始";
          
          const nextSession = detail.next_session;
          if (nextSession?.start_time) {
            const nextSessionTime = new Date(nextSession.start_time).toLocaleString('zh-CN', { 
              month: '2-digit', 
              day: '2-digit', 
              hour: '2-digit', 
              minute: '2-digit',
              hour12: false 
            });
            errorMessage += `\n下次交易时段: ${nextSession.name} ${nextSessionTime}`;
          }
        }
      } else if (error.status === 409) {
        // Already running
        errorTitle = "Gateway Already Running";
        errorMessage = error.details?.detail || error.message || 'Gateway is already running';
      } else if (error.status === 404) {
        // Account not found
        errorTitle = "Account Not Found";
        errorMessage = error.details?.detail || error.message || 'Account configuration not found';
      } else if (error.response && error.response.status === 423) {
        // Fallback for Axios-style error (backward compatibility)
        const detail = error.response.data?.detail;
        if (detail && detail.error === 'TRADING_TIME_RESTRICTED') {
          errorTitle = "当前不在交易时间";
          errorMessage = detail.user_message || "当前不在交易时间，请等待下次交易时段开始";
          
          const nextSession = detail.next_session;
          if (nextSession?.start_time) {
            const nextSessionTime = new Date(nextSession.start_time).toLocaleString('zh-CN', { 
              month: '2-digit', 
              day: '2-digit', 
              hour: '2-digit', 
              minute: '2-digit',
              hour12: false 
            });
            errorMessage += `\n下次交易时段: ${nextSession.name} ${nextSessionTime}`;
          }
        }
      } else if (error.response && error.response.status === 409) {
        // Already running
        errorTitle = "Gateway Already Running";
        errorMessage = error.response.data?.detail || 'Gateway is already running';
      } else if (error.response && error.response.status === 404) {
        // Account not found
        errorTitle = "Account Not Found";
        errorMessage = error.response.data?.detail || 'Account configuration not found';
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      // Debug: Log final error message
      console.log('Final error title:', errorTitle);
      console.log('Final error message:', errorMessage);
      
      // Show error toast
      toast({
        title: errorTitle,
        description: errorMessage,
        variant: "destructive",
      });
      
      console.error('Gateway control action failed:', error);
      
      // Refresh data to ensure UI reflects actual state
      refreshData();
    }
  }, [toast, refreshData]);

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold">System Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time gateway monitoring and system health
          </p>
        </div>
        <ConnectionStatus state={connectionState} isConnected={isConnected} />
      </div>

      {/* Error Display */}
      {error && (
        <Card className="p-4 border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950">
          <div className="flex items-center justify-between">
            <p className="text-red-700 dark:text-red-300">Error: {error}</p>
            <button
              onClick={refreshData}
              className="text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200"
            >
              Retry
            </button>
          </div>
        </Card>
      )}

      {/* Trading Time Status and System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <TradingTimeStatus showDetails={false} />
        </div>
        <div className="lg:col-span-2">
          <SystemHealthSummary 
            systemHealth={data.system_health}
            isConnected={isConnected}
          />
        </div>
      </div>

      {/* Gateway Status Grid */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Gateway Status</h2>
        {data.gateways.length === 0 ? (
          <Card className="p-8 text-center">
            <p className="text-muted-foreground">
              No active gateways detected
            </p>
            <p className="text-sm text-muted-foreground mt-2">
              Gateway status will appear here when connections are established
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.gateways.map((gateway: any) => (
              <GatewayStatusCard
                key={gateway.gateway_id}
                gateway={gateway}
                onAction={handleGatewayAction}
              />
            ))}
          </div>
        )}
      </div>

      {/* Canary Contract Monitor */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Canary Contract Monitor</h2>
        <CanaryMonitor
          contracts={data.canary_contracts}
          isConnected={isConnected}
        />
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <main className="min-h-screen bg-background">
      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardContent />
      </Suspense>
    </main>
  );
}
