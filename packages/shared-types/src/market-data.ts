export interface TickData {
  symbol: string;
  exchange: string;
  datetime: Date;
  name: string;
  volume: number;
  turnover: number;
  open_interest: number;
  last_price: number;
  last_volume: number;
  limit_up: number;
  limit_down: number;
  open_price: number;
  high_price: number;
  low_price: number;
  pre_close: number;
  bid_price_1: number;
  bid_price_2: number;
  bid_price_3: number;
  bid_price_4: number;
  bid_price_5: number;
  ask_price_1: number;
  ask_price_2: number;
  ask_price_3: number;
  ask_price_4: number;
  ask_price_5: number;
  bid_volume_1: number;
  bid_volume_2: number;
  bid_volume_3: number;
  bid_volume_4: number;
  bid_volume_5: number;
  ask_volume_1: number;
  ask_volume_2: number;
  ask_volume_3: number;
  ask_volume_4: number;
  ask_volume_5: number;
  localtime: Date;
  gateway_name: string;
}

export interface ContractData {
  symbol: string;
  exchange: string;
  name: string;
  product: string;
  size: number;
  pricetick: number;
  min_volume: number;
  stop_supported: boolean;
  net_position: boolean;
  history_data: boolean;
  option_strike?: number;
  option_underlying?: string;
  option_type?: string;
  option_expiry?: Date;
  gateway_name: string;
}

export interface CanaryContract {
  symbol: string;
  exchange: string;
  expectedMinVolume: number;
  heartbeatIntervalMs: number;
  lastHeartbeat?: Date;
  isHealthy: boolean;
}