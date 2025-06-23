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
