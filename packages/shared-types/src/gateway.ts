import { GatewayType, Status } from './common';

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
  action: 'start' | 'stop' | 'restart' | 'hard_restart';
  gatewayId: string;
}

export interface GatewayHealthCheck {
  gatewayId: string;
  isHealthy: boolean;
  lastCheck: Date;
  checkType: 'connection' | 'heartbeat' | 'canary';
  details?: Record<string, any>;
}