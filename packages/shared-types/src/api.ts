import {
  MarketDataAccount,
  CreateAccountRequest,
  UpdateAccountRequest,
} from "./accounts";
import { Gateway, GatewayControl } from "./gateway";
import { LogEntry, LogFilter } from "./logs";
import { ApiResponse, PaginatedResponse } from "./common";

// Account Management API
export interface AccountsApi {
  getAccounts(): Promise<ApiResponse<MarketDataAccount[]>>;
  getAccount(id: string): Promise<ApiResponse<MarketDataAccount>>;
  createAccount(
    data: CreateAccountRequest,
  ): Promise<ApiResponse<MarketDataAccount>>;
  updateAccount(
    id: string,
    data: UpdateAccountRequest,
  ): Promise<ApiResponse<MarketDataAccount>>;
  deleteAccount(id: string): Promise<ApiResponse<void>>;
}

// Gateway Management API
export interface GatewaysApi {
  getGateways(): Promise<ApiResponse<Gateway[]>>;
  getGateway(id: string): Promise<ApiResponse<Gateway>>;
  controlGateway(control: GatewayControl): Promise<ApiResponse<void>>;
  getGatewayHealth(id: string): Promise<ApiResponse<any>>;
}

// Logs API
export interface LogsApi {
  getLogs(
    filter?: LogFilter,
  ): Promise<ApiResponse<PaginatedResponse<LogEntry>>>;
  clearLogs(): Promise<ApiResponse<void>>;
  exportLogs(filter?: LogFilter): Promise<ApiResponse<string>>;
}

// WebSocket Events
export interface WebSocketEvents {
  // Gateway events
  "gateway:status": Gateway;
  "gateway:heartbeat": { gatewayId: string; timestamp: Date };

  // Log events
  "log:new": LogEntry;

  // System events
  "system:status": { status: string; timestamp: Date };
  "system:error": { error: string; timestamp: Date };
}

// Authentication
export interface AuthRequest {
  username: string;
  password: string;
}

export interface AuthResponse {
  token: string;
  user: {
    username: string;
    role: string;
  };
}

export interface AuthApi {
  login(credentials: AuthRequest): Promise<ApiResponse<AuthResponse>>;
  logout(): Promise<ApiResponse<void>>;
  verifyToken(): Promise<ApiResponse<{ valid: boolean }>>;
}
