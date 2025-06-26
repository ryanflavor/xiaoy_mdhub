/**
 * Custom hook for dashboard data management and WebSocket integration
 */

import { useState, useEffect, useCallback } from 'react';
import {
  DashboardData,
  GatewayStatus,
  CanaryMonitorData,
  CanaryContractConfig,
  SystemHealthSummary,
  WebSocketState,
  GatewayStatusChangeMessage,
  GatewayControlActionMessage,
  SystemHealthMessage,
  CanaryTickUpdateMessage,
  isGatewayStatusChange,
  isGatewayControlAction,
  isSystemHealth,
  isCanaryTickUpdate,
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

      // Map connection status to our status format
      let mappedStatus: 'HEALTHY' | 'UNHEALTHY' | 'RECOVERING' | 'DISCONNECTED';
      if (message.current_status === 'connected' || message.current_status === '连接成功') {
        mappedStatus = 'HEALTHY';
      } else if (message.current_status === 'connecting') {
        mappedStatus = 'RECOVERING';
      } else if (message.current_status === 'disconnected' || message.current_status === '连接断开') {
        mappedStatus = 'DISCONNECTED';
      } else {
        mappedStatus = message.current_status as 'HEALTHY' | 'UNHEALTHY' | 'RECOVERING' | 'DISCONNECTED';
      }

      const updatedGateway: GatewayStatus = {
        gateway_id: message.gateway_id,
        gateway_type: message.gateway_type.toLowerCase() as 'ctp' | 'sopt',
        current_status: mappedStatus,
        priority: 1, // Default priority, can be enhanced
        last_update: message.timestamp,
        connection_status: mappedStatus === 'HEALTHY' ? 'CONNECTED' : 'DISCONNECTED',
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

  // Update canary contract data from WebSocket message
  const updateCanaryTick = useCallback((message: CanaryTickUpdateMessage) => {
    setData((prevData: DashboardData) => {
      const existingContractIndex = prevData.canary_contracts.findIndex(
        (c: CanaryMonitorData) => c.contract_symbol === message.contract_symbol
      );

      const updatedContract: CanaryMonitorData = {
        contract_symbol: message.contract_symbol,
        tick_count_1min: message.tick_count_1min,
        last_tick_time: message.last_tick_time,
        status: message.status,
        threshold_seconds: message.threshold_seconds,
      };

      let updatedContracts;
      if (existingContractIndex >= 0) {
        updatedContracts = [...prevData.canary_contracts];
        updatedContracts[existingContractIndex] = updatedContract;
      } else {
        updatedContracts = [...prevData.canary_contracts, updatedContract];
      }

      return {
        ...prevData,
        canary_contracts: updatedContracts,
      };
    });
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
      } else if (isCanaryTickUpdate(message)) {
        updateCanaryTick(message);
      }
    } catch (err) {
      console.error('Error handling WebSocket message:', err);
      setError('Error processing WebSocket message');
    }
  }, [updateGatewayStatus, handleGatewayControlAction, updateSystemHealth, updateCanaryTick]);

  // Handle connection state changes
  const handleStateChange = useCallback((state: WebSocketState) => {
    setConnectionState(state);
    setData((prevData: DashboardData) => ({
      ...prevData,
      websocket_connected: state === WebSocketState.CONNECTED,
    }));

    if (state === WebSocketState.ERROR) {
      setError('WebSocket 连接错误');
    } else if (state === WebSocketState.CONNECTED) {
      setError(null);
    } else if (state === WebSocketState.RECONNECTING) {
      setError('正在重新连接...');
    } else if (state === WebSocketState.DISCONNECTED) {
      setError('WebSocket 连接已断开');
    }
  }, []);

  // Transform health response to dashboard data format
  const transformHealthResponse = useCallback((healthData: any): Partial<DashboardData> => {
    const gateways = healthData.gateway_manager?.accounts || [];
    const healthy = gateways.filter((g: any) => g.connected === true).length;
    const connecting = 0; // No connecting status in current API
    const disconnected = gateways.filter((g: any) => g.connected === false).length;
    
    // Transform gateways to frontend format
    const transformedGateways: GatewayStatus[] = gateways.map((gateway: any) => ({
      gateway_id: gateway.id, // API uses 'id' field, not 'gateway_id'
      current_status: gateway.connected ? 'HEALTHY' : 'DISCONNECTED', // API uses 'connected' boolean
      gateway_type: gateway.gateway_type?.toLowerCase() || 'ctp',
      connection_duration: gateway.connection_duration,
      last_update: new Date().toISOString(), // No last_tick_time in API response
      connection_status: gateway.connected ? 'CONNECTED' : 'DISCONNECTED',
      priority: gateway.priority || 1,
      last_tick_time: null, // Not available in health API
      canary_status: null // Not available in health API
    }));

    // Transform canary contracts - use new canary_monitor_data if available
    let canaryContracts: CanaryMonitorData[] = [];
    
    if (healthData.health_monitor?.canary_monitor_data) {
      // Use the new detailed canary monitor data from health_monitor
      canaryContracts = healthData.health_monitor.canary_monitor_data;
    } else if (healthData.canary_config) {
      // Generate from canary config if monitor data not available
      const config: CanaryContractConfig = healthData.canary_config;
      const allContracts = [...config.ctp_contracts, ...config.sopt_contracts];
      
      canaryContracts = allContracts.map((symbol: string) => ({
        contract_symbol: symbol,
        status: 'INACTIVE' as const, // Default status for config-only data
        last_tick_time: new Date().toISOString(),
        tick_count_1min: 0, // Will be updated via WebSocket
        threshold_seconds: config.heartbeat_timeout_seconds
      }));
    } else {
      // Legacy fallback
      canaryContracts = healthData.health_monitor?.canary_contracts?.map((symbol: string) => ({
        contract_symbol: symbol,
        status: 'INACTIVE' as const,
        last_tick_time: healthData.health_monitor.last_health_check || new Date().toISOString(),
        tick_count_1min: 0,
        threshold_seconds: 60
      })) || [];
    }

    return {
      gateways: transformedGateways,
      system_health: {
        total_gateways: gateways.length,
        healthy_gateways: healthy,
        unhealthy_gateways: disconnected,
        recovering_gateways: connecting,
        system_uptime: '0s', // TODO: Get from API
        last_updated: new Date().toISOString(),
        overall_status: healthy === gateways.length ? 'HEALTHY' : 
                       healthy > 0 ? 'DEGRADED' : 'UNHEALTHY'
      },
      canary_contracts: canaryContracts
    };
  }, []);

  // Load initial dashboard data from API
  const loadInitialData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('🔄 Loading dashboard data...');
      console.log('📡 API Base URL:', process.env.NEXT_PUBLIC_API_BASE_URL);
      
      // Fetch health data which includes gateway status
      const healthResponse = await apiClient.get<any>('/health');
      const healthData = healthResponse.data;
      
      console.log('📊 Raw health data:', healthData);
      console.log('🔧 Gateway accounts:', healthData?.gateway_manager?.accounts);
      
      // Transform API response to dashboard format
      const transformedData = transformHealthResponse(healthData);
      
      console.log('✨ Transformed data:', transformedData);
      console.log('🚪 Gateways count:', transformedData.gateways?.length);
      
      setData(prevData => ({
        ...prevData,
        ...transformedData
      }));
    } catch (err) {
      console.error('❌ Failed to load initial dashboard data:', err);
      setError('Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  }, [transformHealthResponse]);

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