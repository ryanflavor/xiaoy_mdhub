// Trading time and market status types

export interface TradingTimeRange {
  start: string; // HH:MM format
  end: string;   // HH:MM format
}

export interface TradingSession {
  name: string;
  ranges: TradingTimeRange[];
  market_type: 'CTP' | 'SOPT';
}

export enum TradingStatus {
  TRADING = 'trading',
  NON_TRADING = 'non_trading',
  PRE_TRADING = 'pre_trading',
  POST_TRADING = 'post_trading'
}

export interface TradingTimeStatus {
  current_time: string;           // ISO timestamp
  current_date: string;          // YYYY-MM-DD
  is_trading_day: boolean;       // Is today a trading day (not weekend/holiday)
  is_trading_time: boolean;      // Is current time within trading hours
  status: TradingStatus;         // Current trading status
  ctp_trading: boolean;          // Is CTP currently in trading hours
  sopt_trading: boolean;         // Is SOPT currently in trading hours
  next_session_start?: string;   // ISO timestamp of next trading session start
  next_session_name?: string;    // Name of next trading session
  current_session_name?: string; // Name of current trading session if trading
  ctp_next_session?: string;     // ISO timestamp of CTP's next trading session start
  sopt_next_session?: string;    // ISO timestamp of SOPT's next trading session start
  sessions: TradingSession[];    // Available trading sessions
}

export interface TradingTimeConfig {
  enable_trading_time_check: boolean;
  force_gateway_connection: boolean;
  trading_time_buffer_minutes: number;
  ctp_trading_hours: string;     // Format: "08:45-11:45,13:15-15:15,20:45-02:45"
  sopt_trading_hours: string;    // Format: "09:15-11:45,12:45-15:15"
}