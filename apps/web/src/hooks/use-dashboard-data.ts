/**
 * Custom hook for dashboard data management and WebSocket integration
 */

import { useState, useEffect, useCallback } from 'react';
import {
  DashboardData,
  GatewayStatus,
  CanaryMonitorData,
  SystemHealthSummary,
  WebSocketState,
  GatewayStatusChangeMessage,
  GatewayControlActionMessage,
  SystemHealthMessage,
  isGatewayStatusChange,
  isGatewayControlAction,
  isSystemHealth,
  AnyWebSocketMessage,
} from '@xiaoy-mdhub/shared-types';
import { WebSocketClient, createWebSocketClient } from '@/services/websocket';
import { apiClient } from '@/services/api-client';

export interface UseDashboardDataReturn {
  data: DashboardData;
  isConnected: boolean;
  connectionState: WebSocketState;
  error: string | null;
  isLoading: boolean;
  refreshData: () => void;
}

/**
 * Hook to manage dashboard data and WebSocket connection
 */
export function useDashboardData(): UseDashboardDataReturn {
  const [client, setClient] = useState<WebSocketClient | null>(null);
  const [connectionState, setConnectionState] = useState<WebSocketState>(WebSocketState.DISCONNECTED);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [data, setData] = useState<DashboardData>({
    gateways: [],
    canary_contracts: [],
    system_health: {
      total_gateways: 0,
      healthy_gateways: 0,
      unhealthy_gateways: 0,
      recovering_gateways: 0,
      system_uptime: '0s',
      last_updated: new Date().toISOString(),
      overall_status: 'HEALTHY',
    },
    websocket_connected: false,
  });

  // Calculate system health summary from gateways
  const calculateSystemHealth = useCallback((gateways: GatewayStatus[]): SystemHealthSummary => {
    const total = gateways.length;
    const healthy = gateways.filter((g) => g.current_status === 'HEALTHY').length;
    const unhealthy = gateways.filter((g) => g.current_status === 'UNHEALTHY').length;
    const recovering = gateways.filter((g) => g.current_status === 'RECOVERING').length;

    let overallStatus: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' = 'HEALTHY';
    if (unhealthy > 0) {
      overallStatus = total === unhealthy ? 'UNHEALTHY' : 'DEGRADED';
    } else if (recovering > 0) {
      overallStatus = 'DEGRADED';
    }

    return {
      total_gateways: total,
      healthy_gateways: healthy,
      unhealthy_gateways: unhealthy,
      recovering_gateways: recovering,
      system_uptime: '0s', // TODO: Calculate actual uptime
      last_updated: new Date().toISOString(),
      overall_status: overallStatus,
    };
  }, []);

  // Update gateway status from WebSocket message
  const updateGatewayStatus = useCallback((message: GatewayStatusChangeMessage) => {
    setData((prevData: DashboardData) => {
      const existingGatewayIndex = prevData.gateways.findIndex(
        (g: GatewayStatus) => g.gateway_id === message.gateway_id
      );

      const updatedGateway: GatewayStatus = {
        gateway_id: message.gateway_id,
        gateway_type: message.gateway_type,
        current_status: message.current_status as 'HEALTHY' | 'UNHEALTHY' | 'RECOVERING' | 'DISCONNECTED',
        priority: 1, // Default priority, can be enhanced
        last_update: message.timestamp,
        connection_status: message.metadata?.connection_status || 'DISCONNECTED',
        last_tick_time: message.metadata?.last_tick_time,
        canary_status: message.metadata?.canary_status,
      };

      let updatedGateways;
      if (existingGatewayIndex >= 0) {
        updatedGateways = [...prevData.gateways];
        updatedGateways[existingGatewayIndex] = updatedGateway;
      } else {
        updatedGateways = [...prevData.gateways, updatedGateway];
      }

      // Recalculate system health summary
      const healthSummary = calculateSystemHealth(updatedGateways);

      return {
        ...prevData,
        gateways: updatedGateways,
        system_health: healthSummary,
      };
    });
  }, [calculateSystemHealth]);

  // Update system health from WebSocket message
  const updateSystemHealth = useCallback((message: SystemHealthMessage) => {
    setData((prevData: DashboardData) => ({
      ...prevData,
      system_health: {
        ...prevData.system_health,
        overall_status: message.healthy ? 'HEALTHY' : 'UNHEALTHY',
        last_updated: message.timestamp,
      },
    }));
  }, []);

  // Handle gateway control action from WebSocket message
  const handleGatewayControlAction = useCallback((message: GatewayControlActionMessage) => {
    // Update gateway status based on control action
    setData((prevData: DashboardData) => {
      const existingGatewayIndex = prevData.gateways.findIndex(
        (g: GatewayStatus) => g.gateway_id === message.gateway_id
      );

      if (existingGatewayIndex >= 0) {
        const updatedGateways = [...prevData.gateways];
        const existingGateway = updatedGateways[existingGatewayIndex];

        // Update status based on action and status
        let newStatus = existingGateway.current_status;
        let newConnectionStatus = existingGateway.connection_status;

        if (message.status === 'completed') {
          switch (message.action) {
            case 'start':
              newStatus = 'HEALTHY';
              newConnectionStatus = 'CONNECTED';
              break;
            case 'stop':
              newStatus = 'DISCONNECTED';
              newConnectionStatus = 'DISCONNECTED';
              break;
            case 'restart':
              newStatus = 'HEALTHY';
              newConnectionStatus = 'CONNECTED';
              break;
          }
        } else if (message.status === 'failed') {
          newStatus = 'UNHEALTHY';
          newConnectionStatus = 'DISCONNECTED';
        }

        updatedGateways[existingGatewayIndex] = {
          ...existingGateway,
          current_status: newStatus,
          connection_status: newConnectionStatus,
          last_update: message.timestamp,
        };

        // Recalculate system health summary
        const healthSummary = calculateSystemHealth(updatedGateways);

        return {
          ...prevData,
          gateways: updatedGateways,
          system_health: healthSummary,
        };
      }

      return prevData;
    });
  }, [calculateSystemHealth]);

  // Handle WebSocket messages
  const handleMessage = useCallback((message: AnyWebSocketMessage) => {
    try {
      if (isGatewayStatusChange(message)) {
        updateGatewayStatus(message);
      } else if (isGatewayControlAction(message)) {
        handleGatewayControlAction(message);
      } else if (isSystemHealth(message)) {
        updateSystemHealth(message);
      }
    } catch (err) {
      console.error('Error handling WebSocket message:', err);
      setError('Error processing WebSocket message');
    }
  }, [updateGatewayStatus, handleGatewayControlAction, updateSystemHealth]);

  // Handle connection state changes
  const handleStateChange = useCallback((state: WebSocketState) => {
    setConnectionState(state);
    setData((prevData: DashboardData) => ({
      ...prevData,
      websocket_connected: state === WebSocketState.CONNECTED,
    }));

    if (state === WebSocketState.ERROR) {
      setError('WebSocket connection error');
    } else if (state === WebSocketState.CONNECTED) {
      setError(null);
    }
  }, []);

  // Load initial dashboard data from API
  const loadInitialData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Fetch health data which includes gateway status
      const healthResponse = await apiClient.get<any>('/health');
      const healthData = healthResponse.data;
      
      if (healthData.gateway_manager && healthData.health_monitor) {
        const gatewayManager = healthData.gateway_manager;
        const healthMonitor = healthData.health_monitor;
        
        // Convert API gateway data to frontend format
        const gateways: GatewayStatus[] = gatewayManager.accounts?.map((account: any) => ({
          gateway_id: account.id,
          gateway_type: account.gateway_type?.toUpperCase() || 'UNKNOWN',
          current_status: account.connected ? 'HEALTHY' : 'DISCONNECTED',
          priority: account.priority || 1,
          last_update: new Date().toISOString(),
          connection_status: account.connected ? 'CONNECTED' : 'DISCONNECTED',
          last_tick_time: null,
          canary_status: null,
        })) || [];
        
        // Calculate system health from gateway data
        const systemHealth = calculateSystemHealth(gateways);
        
        setData(prevData => ({
          ...prevData,
          gateways,
          system_health: {
            ...systemHealth,
            total_gateways: gatewayManager.total_accounts || 0,
            system_uptime: '0s', // TODO: Get from API
            last_updated: new Date().toISOString(),
          },
        }));
      }
    } catch (err) {
      console.error('Failed to load initial dashboard data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  }, [calculateSystemHealth]);

  // Refresh data manually
  const refreshData = useCallback(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Load initial data on mount
  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Initialize WebSocket connection
  useEffect(() => {
    const wsClient = createWebSocketClient();
    setClient(wsClient);

    // Subscribe to message and state events
    const unsubscribeMessages = wsClient.onAny(handleMessage);
    const unsubscribeState = wsClient.onStateChange(handleStateChange);

    // Connect to WebSocket
    wsClient.connect();

    // Cleanup on unmount
    return () => {
      unsubscribeMessages();
      unsubscribeState();
      wsClient.disconnect();
    };
  }, [handleMessage, handleStateChange]);

  return {
    data,
    isConnected: connectionState === WebSocketState.CONNECTED,
    connectionState,
    error,
    isLoading,
    refreshData,
  };
}