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
 * Account settings interface for vnpy gateway configurations.
 * This interface supports both CTP and SOPT gateway types with their specific parameters.
 */
export interface AccountSettings {
  // CTP specific settings
  /** User ID for CTP authentication */
  userID?: string;
  /** Password for CTP authentication */
  password?: string;
  /** Broker ID for CTP connection */
  brokerID?: string;
  /** Authentication code for CTP */
  authCode?: string;
  /** Application ID for CTP */
  appID?: string;
  /** Market data server address for CTP */
  mdAddress?: string;
  /** Trading server address for CTP */
  tdAddress?: string;

  // SOPT specific settings
  /** Username for SOPT authentication */
  username?: string;
  /** Token for SOPT authentication */
  token?: string;
  /** Server address for SOPT connection */
  serverAddress?: string;

  // Common optional settings
  /** Connection timeout in seconds */
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
}

/**
 * Request interface for updating an existing market data account
 */
export interface UpdateAccountRequest {
  /** Updated gateway settings */
  settings?: Partial<AccountSettings>;
  /** Updated priority level */
  priority?: number;
  /** Updated enabled status */
  is_enabled?: boolean;
  /** Updated description */
  description?: string;
}
