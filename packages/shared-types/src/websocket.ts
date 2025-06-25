/**
 * WebSocket message types and interfaces for real-time communication
 */

import { LogLevel } from './common';

/**
 * WebSocket event types
 */
export enum WebSocketEventType {
  // Connection events
  CONNECTION = 'connection',
  DISCONNECTION = 'disconnection',
  
  // Gateway events
  GATEWAY_STATUS_CHANGE = 'gateway_status_change',
  GATEWAY_RECOVERY_STATUS = 'gateway_recovery_status',
  GATEWAY_CONTROL_ACTION = 'gateway_control_action',
  
  // System events
  SYSTEM_LOG = 'system_log',
  SYSTEM_HEALTH = 'system_health',
  
  // Control events
  PING = 'ping',
  PONG = 'pong',
  ERROR = 'error',
  SHUTDOWN = 'shutdown'
}

/**
 * Base WebSocket message interface
 */
export interface WebSocketMessage {
  event_type?: WebSocketEventType | string;
  type?: string; // For ping/pong compatibility
  timestamp: string;
}

/**
 * Connection event message
 */
export interface ConnectionMessage extends WebSocketMessage {
  event_type: WebSocketEventType.CONNECTION;
  status: 'connected' | 'disconnected';
  client_id: string;
  message: string;
}

/**
 * Gateway status change event
 */
export interface GatewayStatusChangeMessage extends WebSocketMessage {
  event_type: WebSocketEventType.GATEWAY_STATUS_CHANGE;
  gateway_id: string;
  gateway_type: 'ctp' | 'sopt';
  previous_status: string;
  current_status: string;
  metadata?: Record<string, any>;
}

/**
 * Gateway recovery status event
 */
export interface GatewayRecoveryStatusMessage extends WebSocketMessage {
  event_type: WebSocketEventType.GATEWAY_RECOVERY_STATUS;
  gateway_id: string;
  recovery_status: string;
  attempt: number;
  message: string;
  metadata?: Record<string, any>;
}

/**
 * Gateway control action event
 */
export interface GatewayControlActionMessage extends WebSocketMessage {
  event_type: WebSocketEventType.GATEWAY_CONTROL_ACTION;
  gateway_id: string;
  action: 'start' | 'stop' | 'restart';
  status: 'initiated' | 'completed' | 'failed';
  message: string;
  metadata?: Record<string, any>;
}

/**
 * System log levels (imported from common)
 */

/**
 * System log event
 */
export interface SystemLogMessage extends WebSocketMessage {
  event_type: WebSocketEventType.SYSTEM_LOG;
  level: LogLevel;
  message: string;
  source: string;
  metadata?: {
    logger_name?: string;
    module?: string;
    function?: string;
    line?: number;
    [key: string]: any;
  };
}

/**
 * System health event
 */
export interface SystemHealthMessage extends WebSocketMessage {
  event_type: WebSocketEventType.SYSTEM_HEALTH;
  healthy: boolean;
  services: {
    [serviceName: string]: {
      healthy: boolean;
      message?: string;
    };
  };
}

/**
 * Ping message for connection health check
 */
export interface PingMessage extends WebSocketMessage {
  type: 'ping';
}

/**
 * Pong response message
 */
export interface PongMessage extends WebSocketMessage {
  type: 'pong';
}

/**
 * Error message
 */
export interface ErrorMessage extends WebSocketMessage {
  event_type: WebSocketEventType.ERROR;
  message: string;
  code?: string;
}

/**
 * Shutdown message
 */
export interface ShutdownMessage extends WebSocketMessage {
  event_type: WebSocketEventType.SHUTDOWN;
  message: string;
}

/**
 * Union type for all WebSocket messages
 */
export type AnyWebSocketMessage = 
  | ConnectionMessage
  | GatewayStatusChangeMessage
  | GatewayRecoveryStatusMessage
  | GatewayControlActionMessage
  | SystemLogMessage
  | SystemHealthMessage
  | PingMessage
  | PongMessage
  | ErrorMessage
  | ShutdownMessage
  | DashboardUpdateMessage;

/**
 * WebSocket connection state
 */
export enum WebSocketState {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  RECONNECTING = 'RECONNECTING',
  DISCONNECTED = 'DISCONNECTED',
  ERROR = 'ERROR'
}

/**
 * WebSocket client configuration
 */
export interface WebSocketConfig {
  url: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  pingInterval?: number;
  pongTimeout?: number;
}

/**
 * Type guard functions
 */
export const isGatewayStatusChange = (msg: AnyWebSocketMessage): msg is GatewayStatusChangeMessage => {
  return msg.event_type === WebSocketEventType.GATEWAY_STATUS_CHANGE;
};

export const isGatewayRecoveryStatus = (msg: AnyWebSocketMessage): msg is GatewayRecoveryStatusMessage => {
  return msg.event_type === WebSocketEventType.GATEWAY_RECOVERY_STATUS;
};

export const isGatewayControlAction = (msg: AnyWebSocketMessage): msg is GatewayControlActionMessage => {
  return msg.event_type === WebSocketEventType.GATEWAY_CONTROL_ACTION;
};

export const isSystemLog = (msg: AnyWebSocketMessage): msg is SystemLogMessage => {
  return msg.event_type === WebSocketEventType.SYSTEM_LOG;
};

export const isSystemHealth = (msg: AnyWebSocketMessage): msg is SystemHealthMessage => {
  return msg.event_type === WebSocketEventType.SYSTEM_HEALTH;
};

export const isPing = (msg: AnyWebSocketMessage): msg is PingMessage => {
  return msg.type === 'ping';
};

export const isPong = (msg: AnyWebSocketMessage): msg is PongMessage => {
  return msg.type === 'pong';
};

/**
 * Dashboard-specific types for UI components
 */

/**
 * Gateway status for dashboard display
 */
export interface GatewayStatus {
  gateway_id: string;
  gateway_type: 'ctp' | 'sopt';
  current_status: 'HEALTHY' | 'UNHEALTHY' | 'RECOVERING' | 'DISCONNECTED';
  priority: number;
  last_update: string;
  connection_status: 'CONNECTED' | 'DISCONNECTED';
  last_tick_time?: string;
  canary_status?: 'ACTIVE' | 'INACTIVE';
}

/**
 * Canary contract monitor data for dashboard
 */
export interface CanaryMonitorData {
  contract_symbol: string;
  last_tick_time: string;
  tick_count_1min: number;
  status: 'ACTIVE' | 'STALE' | 'INACTIVE';
  threshold_seconds: number;
}

/**
 * System health summary for dashboard
 */
export interface SystemHealthSummary {
  total_gateways: number;
  healthy_gateways: number;
  unhealthy_gateways: number;
  recovering_gateways: number;
  system_uptime: string;
  last_updated: string;
  overall_status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
}

/**
 * Dashboard data aggregated from WebSocket events
 */
export interface DashboardData {
  gateways: GatewayStatus[];
  canary_contracts: CanaryMonitorData[];
  system_health: SystemHealthSummary;
  websocket_connected: boolean;
}

/**
 * Dashboard WebSocket event for aggregated data updates
 */
export interface DashboardUpdateMessage extends WebSocketMessage {
  event_type: 'dashboard_update';
  data: Partial<DashboardData>;
}