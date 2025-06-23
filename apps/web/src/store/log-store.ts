import { create } from "zustand";
import { devtools } from "zustand/middleware";

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: "DEBUG" | "INFO" | "WARN" | "ERROR";
  message: string;
  module: string;
  details?: Record<string, any>;
}

export interface LogState {
  logs: LogEntry[];
  filteredLogs: LogEntry[];
  filters: {
    level: LogEntry["level"] | "ALL";
    module: string | "ALL";
    search: string;
  };
  maxLogs: number;

  // Actions
  addLog: (log: Omit<LogEntry, "id">) => void;
  clearLogs: () => void;
  setFilters: (filters: Partial<LogState["filters"]>) => void;
  setMaxLogs: (maxLogs: number) => void;
}

export const useLogStore = create<LogState>()(
  devtools(
    (set, get) => ({
      // Initial state
      logs: [],
      filteredLogs: [],
      filters: {
        level: "ALL",
        module: "ALL",
        search: "",
      },
      maxLogs: 1000,

      // Actions
      addLog: (logData) =>
        set(
          (state) => {
            const newLog: LogEntry = {
              ...logData,
              id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            };

            const newLogs = [newLog, ...state.logs].slice(0, state.maxLogs);
            const filteredLogs = applyFilters(newLogs, state.filters);

            return {
              ...state,
              logs: newLogs,
              filteredLogs,
            };
          },
          false,
          "addLog",
        ),

      clearLogs: () =>
        set(
          (state) => ({ ...state, logs: [], filteredLogs: [] }),
          false,
          "clearLogs",
        ),

      setFilters: (newFilters) =>
        set(
          (state) => {
            const filters = { ...state.filters, ...newFilters };
            const filteredLogs = applyFilters(state.logs, filters);

            return {
              ...state,
              filters,
              filteredLogs,
            };
          },
          false,
          "setFilters",
        ),

      setMaxLogs: (maxLogs) =>
        set(
          (state) => {
            const logs = state.logs.slice(0, maxLogs);
            const filteredLogs = applyFilters(logs, state.filters);

            return {
              ...state,
              maxLogs,
              logs,
              filteredLogs,
            };
          },
          false,
          "setMaxLogs",
        ),
    }),
    {
      name: "log-store",
    },
  ),
);

// Helper function to apply filters
function applyFilters(
  logs: LogEntry[],
  filters: LogState["filters"],
): LogEntry[] {
  return logs.filter((log) => {
    // Level filter
    if (filters.level !== "ALL" && log.level !== filters.level) {
      return false;
    }

    // Module filter
    if (filters.module !== "ALL" && log.module !== filters.module) {
      return false;
    }

    // Search filter
    if (
      filters.search &&
      !log.message.toLowerCase().includes(filters.search.toLowerCase())
    ) {
      return false;
    }

    return true;
  });
}
