import { BaseEntity } from "./common";

/**
 * Market Data Account interface representing account configurations for different gateway types.
 * This interface defines the structure for persisting market data account configurations
 * in the database and sharing types between frontend and backend.
 */
export interface MarketDataAccount extends BaseEntity {
  /** Gateway type identifier - determines which trading gateway to use */
  gateway_type: "ctp" | "sopt";
  /** JSON object containing gateway-specific configuration settings */
  settings: AccountSettings;
  /** Priority level for account usage (lower number = higher priority, 1 = primary) */
  priority: number;
  /** Flag indicating whether this account should be used by the service */
  is_enabled: boolean;
  /** Optional user-friendly description or name for the account */
  description?: string;
}

/**
 * Connection settings for trading gateways
 */
export interface ConnectSetting {
  // Chinese field names (new format)
  交易服务器?: string;
  行情服务器?: string;
  用户名?: string;
  密码?: string;
  经纪商代码?: string;
  授权编码?: string;
  产品信息?: string;
  产品名称?: string;
  
  // English field names (legacy support)
  userID?: string;
  password?: string;
  brokerID?: string;
  authCode?: string;
  appID?: string;
  mdAddress?: string;
  tdAddress?: string;
  username?: string;
  token?: string;
  serverAddress?: string;
  timeout?: number;
  
  /** Additional gateway-specific parameters */
  [key: string]: any;
}

/**
 * Gateway information
 */
export interface GatewayInfo {
  gateway_class: string;
  gateway_name: string;
}

/**
 * Account settings interface for vnpy gateway configurations.
 * Supports both new unified format and legacy flat format.
 */
export interface AccountSettings {
  // New unified account format
  broker?: string;
  connect_setting?: ConnectSetting;
  gateway?: GatewayInfo;
  market?: string;
  name?: string;
  
  // Legacy flat structure support for backward compatibility
  userID?: string;
  password?: string;
  brokerID?: string;
  authCode?: string;
  appID?: string;
  mdAddress?: string;
  tdAddress?: string;
  username?: string;
  token?: string;
  serverAddress?: string;
  timeout?: number;
  
  /** Additional gateway-specific parameters */
  [key: string]: any;
}

/**
 * Request interface for creating a new market data account
 */
export interface CreateAccountRequest {
  /** Gateway type identifier */
  gateway_type: "ctp" | "sopt";
  /** Gateway-specific configuration settings */
  settings: AccountSettings;
  /** Priority level (lower = higher priority) */
  priority: number;
  /** Whether the account should be enabled */
  is_enabled: boolean;
  /** Optional description */
  description?: string;
  /** Whether to validate connection before creating account */
  validate_connection?: boolean;
  /** Allow validation outside trading hours */
  allow_non_trading_validation?: boolean;
  /** Use real vnpy gateway API login validation instead of basic connectivity test */
  use_real_api_validation?: boolean;
}

/**
 * Request interface for updating an existing market data account
 */
export interface UpdateAccountRequest {
  /** Updated gateway type */
  gateway_type?: "ctp" | "sopt";
  /** Updated gateway settings */
  settings?: Partial<AccountSettings>;
  /** Updated priority level */
  priority?: number;
  /** Updated enabled status */
  is_enabled?: boolean;
  /** Updated description */
  description?: string;
}

/**
 * Request interface for account validation
 */
export interface AccountValidationRequest {
  /** Account identifier for validation */
  account_id: string;
  /** Gateway type (ctp or sopt) */
  gateway_type: "ctp" | "sopt";
  /** Account settings to validate */
  settings: AccountSettings;
  /** Validation timeout in seconds */
  timeout_seconds?: number;
  /** Allow validation outside trading hours */
  allow_non_trading_validation?: boolean;
  /** Use real vnpy gateway API login validation */
  use_real_api_validation?: boolean;
}

/**
 * Response interface for account validation
 */
export interface AccountValidationResponse {
  /** Whether validation was successful */
  success: boolean;
  /** Validation result message */
  message: string;
  /** Account identifier */
  account_id: string;
  /** Gateway type */
  gateway_type: string;
  /** Validation timestamp */
  timestamp: string;
  /** Additional validation details */
  details: {
    /** Error code if validation failed */
    error_code?: string;
    /** User-friendly error message */
    user_friendly_message?: string;
    /** Validation type performed */
    validation_type?: string;
    /** Whether trading time validation was performed */
    is_trading_time?: boolean;
    /** Connection test results */
    connection_results?: Array<{
      server_type: string;
      host: string;
      port: number;
      status: string;
      connect_time?: number;
      error?: string;
    }>;
    /** Validation logs for real API validation */
    logs?: string[];
    /** Validation recommendations */
    recommendations?: string[];
    /** Troubleshooting steps */
    troubleshooting_steps?: string[];
    /** Additional details */
    [key: string]: any;
  };
}
