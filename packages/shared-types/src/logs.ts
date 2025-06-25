import { LogLevel } from "./common";

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: LogLevel;
  message: string;
  module: string;
  gatewayId?: string;
  details?: Record<string, any>;
  stackTrace?: string;
}

export interface LogFilter {
  level?: LogLevel | "ALL";
  module?: string | "ALL";
  gatewayId?: string | "ALL";
  search?: string;
  startDate?: Date;
  endDate?: Date;
}

export interface LogConfiguration {
  level: LogLevel;
  enableFileLogging: boolean;
  enableConsoleLogging: boolean;
  maxLogFiles: number;
  maxLogFileSize: number; // in MB
  logDirectory: string;
}

// Log viewer specific types

export interface LogViewerState {
  logs: LogEntry[];
  filteredLogs: LogEntry[];
  filter: LogFilter;
  isConnected: boolean;
  isAutoScrollEnabled: boolean;
  isPaused: boolean;
  bufferSize: number;
  totalLogCount: number;
}

export interface LogViewerConfig {
  maxBufferSize: number;
  autoScrollToBottom: boolean;
  enableVirtualScrolling: boolean;
  refreshInterval: number;
  debounceDelay: number;
}

export interface LogExportOptions {
  format: 'json' | 'csv' | 'txt';
  includeMetadata: boolean;
  dateRange?: {
    start: Date;
    end: Date;
  };
  filter?: LogFilter;
}

export interface LogStats {
  total: number;
  byLevel: Record<LogLevel, number>;
  byModule: Record<string, number>;
  timeRange: {
    start: Date;
    end: Date;
  };
}
