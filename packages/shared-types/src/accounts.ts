import { BaseEntity, GatewayType, Status } from './common';

export interface MarketDataAccount extends BaseEntity {
  gatewayType: GatewayType;
  settings: AccountSettings;
  priority: number;
  isEnabled: boolean;
  description?: string;
  status: Status;
  lastHeartbeat?: Date;
}

export interface AccountSettings {
  // CTP specific settings
  userid?: string;
  password?: string;
  brokerid?: string;
  auth_code?: string;
  appid?: string;
  md_address?: string;
  td_address?: string;
  
  // SOPT specific settings
  username?: string;
  token?: string;
  server_address?: string;
  
  // Common settings
  host: string;
  port: number;
  timeout?: number;
}

export interface CreateAccountRequest {
  gatewayType: GatewayType;
  settings: AccountSettings;
  priority: number;
  isEnabled: boolean;
  description?: string;
}

export interface UpdateAccountRequest {
  settings?: Partial<AccountSettings>;
  priority?: number;
  isEnabled?: boolean;
  description?: string;
}