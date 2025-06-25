import { GatewayType, Status } from "./common";

export interface Gateway {
  id: string;
  name: string;
  type: GatewayType;
  status: Status;
  priority: number;
  isEnabled: boolean;
  lastHeartbeat: Date | null;
  connectionInfo: ConnectionInfo;
  accountId: string;
}

export interface ConnectionInfo {
  host: string;
  port: number;
  connected: boolean;
  connectedAt?: Date;
  disconnectedAt?: Date;
  connectionAttempts: number;
  lastError?: string;
}

export interface GatewayControl {
  action: "start" | "stop" | "restart" | "hard_restart";
  gatewayId: string;
}

// Enhanced control types for interactive dashboard
export type GatewayControlAction = 'start' | 'stop' | 'restart';
export type ButtonState = 'idle' | 'loading' | 'success' | 'error';

export interface GatewayControlRequest {
  gateway_id: string;
  action: GatewayControlAction;
}

export interface GatewayControlResponse {
  success: boolean;
  message: string;
  gateway_id: string;
  action: GatewayControlAction;
  timestamp: string;
}

export interface GatewayHealthCheck {
  gatewayId: string;
  isHealthy: boolean;
  lastCheck: Date;
  checkType: "connection" | "heartbeat" | "canary";
  details?: Record<string, any>;
}
