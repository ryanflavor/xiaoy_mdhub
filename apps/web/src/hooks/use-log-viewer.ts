"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { LogEntry, LogFilter, LogViewerConfig, LogViewerState, LogLevel } from '@xiaoy-mdhub/shared-types';
import { SystemLogMessage, WebSocketEventType, WebSocketState, isSystemLog } from '@xiaoy-mdhub/shared-types';
import { createWebSocketClient, WebSocketClient } from '@/services/websocket';

const DEFAULT_CONFIG: LogViewerConfig = {
  maxBufferSize: 1000,
  autoScrollToBottom: true,
  enableVirtualScrolling: true,
  refreshInterval: 100,
  debounceDelay: 300,
};

const DEFAULT_FILTER: LogFilter = {};

export function useLogViewer(config: Partial<LogViewerConfig> = {}) {
  const wsClient = useRef<WebSocketClient | null>(null);
  const configRef = useRef<LogViewerConfig>({ ...DEFAULT_CONFIG, ...config });
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  const [state, setState] = useState<LogViewerState>({
    logs: [],
    filteredLogs: [],
    filter: DEFAULT_FILTER,
    isConnected: false,
    isAutoScrollEnabled: true,
    isPaused: false,
    bufferSize: 0,
    totalLogCount: 0,
  });

  // Memoized filter function
  const filterLogs = useCallback((logs: LogEntry[], filter: LogFilter): LogEntry[] => {
    if (!filter || Object.keys(filter).length === 0) {
      return logs;
    }

    return logs.filter((log) => {
      // Level filter
      if (filter.level && filter.level !== 'ALL' && log.level !== filter.level) {
        return false;
      }

      // Module filter
      if (filter.module && filter.module !== 'ALL' && log.module !== filter.module) {
        return false;
      }

      // Gateway filter
      if (filter.gatewayId && filter.gatewayId !== 'ALL' && log.gatewayId !== filter.gatewayId) {
        return false;
      }

      // Text search filter
      if (filter.search) {
        const searchLower = filter.search.toLowerCase();
        const messageMatch = log.message.toLowerCase().includes(searchLower);
        const moduleMatch = log.module.toLowerCase().includes(searchLower);
        const gatewayMatch = log.gatewayId?.toLowerCase().includes(searchLower);
        
        if (!messageMatch && !moduleMatch && !gatewayMatch) {
          return false;
        }
      }

      // Date range filter
      if (filter.startDate && log.timestamp < filter.startDate) {
        return false;
      }
      if (filter.endDate && log.timestamp > filter.endDate) {
        return false;
      }

      return true;
    });
  }, []);

  // Apply filters with debouncing for search
  const applyFilters = useCallback((logs: LogEntry[], filter: LogFilter) => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    const applyFilteringLogic = () => {
      const filtered = filterLogs(logs, filter);
      setState(prev => ({
        ...prev,
        filteredLogs: filtered,
      }));
    };

    // Debounce search filter changes
    if (filter.search !== state.filter.search) {
      searchTimeoutRef.current = setTimeout(applyFilteringLogic, configRef.current.debounceDelay);
    } else {
      applyFilteringLogic();
    }
  }, [filterLogs, state.filter.search]);

  // Convert WebSocket message to LogEntry
  const convertToLogEntry = useCallback((message: SystemLogMessage): LogEntry => {
    return {
      id: `${message.timestamp}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(message.timestamp),
      level: message.level,
      message: message.message,
      module: message.source,
      gatewayId: message.metadata?.gateway_id,
      details: message.metadata,
      stackTrace: message.metadata?.stack_trace,
    };
  }, []);

  // Add new log entry with buffer management
  const addLogEntry = useCallback((entry: LogEntry) => {
    if (state.isPaused) {
      return;
    }

    setState(prev => {
      const newLogs = [...prev.logs, entry];
      
      // Apply buffer size limit
      const trimmedLogs = newLogs.length > configRef.current.maxBufferSize
        ? newLogs.slice(-configRef.current.maxBufferSize)
        : newLogs;

      const filteredLogs = filterLogs(trimmedLogs, prev.filter);

      return {
        ...prev,
        logs: trimmedLogs,
        filteredLogs,
        bufferSize: trimmedLogs.length,
        totalLogCount: prev.totalLogCount + 1,
      };
    });
  }, [state.isPaused, filterLogs]);

  // WebSocket message handler
  const handleWebSocketMessage = useCallback((message: any) => {
    if (isSystemLog(message)) {
      const logEntry = convertToLogEntry(message as SystemLogMessage);
      addLogEntry(logEntry);
    }
  }, [convertToLogEntry, addLogEntry]);

  // WebSocket state change handler
  const handleWebSocketStateChange = useCallback((wsState: WebSocketState) => {
    setState(prev => ({
      ...prev,
      isConnected: wsState === WebSocketState.CONNECTED,
    }));
  }, []);

  // Initialize WebSocket connection
  useEffect(() => {
    if (!wsClient.current) {
      wsClient.current = createWebSocketClient();
      
      // Subscribe to system log messages
      const unsubscribe = wsClient.current.on(WebSocketEventType.SYSTEM_LOG, handleWebSocketMessage);
      
      // Subscribe to state changes
      const unsubscribeState = wsClient.current.onStateChange(handleWebSocketStateChange);
      
      // Connect
      wsClient.current.connect();

      return () => {
        unsubscribe();
        unsubscribeState();
        if (wsClient.current) {
          wsClient.current.disconnect();
          wsClient.current = null;
        }
      };
    }
  }, [handleWebSocketMessage, handleWebSocketStateChange]);

  // Update filters and apply them
  const updateFilter = useCallback((newFilter: LogFilter) => {
    setState(prev => ({
      ...prev,
      filter: newFilter,
    }));
    
    applyFilters(state.logs, newFilter);
  }, [applyFilters, state.logs]);

  // Clear all logs
  const clearLogs = useCallback(() => {
    setState(prev => ({
      ...prev,
      logs: [],
      filteredLogs: [],
      bufferSize: 0,
    }));
  }, []);

  // Toggle pause/resume
  const togglePause = useCallback(() => {
    setState(prev => ({
      ...prev,
      isPaused: !prev.isPaused,
    }));
  }, []);

  // Toggle auto-scroll
  const toggleAutoScroll = useCallback(() => {
    setState(prev => ({
      ...prev,
      isAutoScrollEnabled: !prev.isAutoScrollEnabled,
    }));
  }, []);

  // Export logs
  const exportLogs = useCallback((format: 'json' | 'csv' | 'txt' = 'json') => {
    const logsToExport = state.filteredLogs.length > 0 ? state.filteredLogs : state.logs;
    
    switch (format) {
      case 'json':
        return JSON.stringify(logsToExport, null, 2);
      
      case 'csv':
        const headers = ['timestamp', 'level', 'module', 'gatewayId', 'message'];
        const csvRows = [
          headers.join(','),
          ...logsToExport.map(log => [
            log.timestamp.toISOString(),
            log.level,
            log.module,
            log.gatewayId || '',
            `"${log.message.replace(/"/g, '""')}"`,
          ].join(','))
        ];
        return csvRows.join('\n');
      
      case 'txt':
        return logsToExport.map(log => 
          `[${log.timestamp.toISOString()}] ${log.level} ${log.module}${log.gatewayId ? ` (${log.gatewayId})` : ''}: ${log.message}`
        ).join('\n');
      
      default:
        return JSON.stringify(logsToExport, null, 2);
    }
  }, [state.filteredLogs, state.logs]);

  // Get unique modules for filter options
  const availableModules = useMemo(() => {
    const modules = new Set(state.logs.map(log => log.module));
    return Array.from(modules).sort();
  }, [state.logs]);

  // Get unique gateways for filter options
  const availableGateways = useMemo(() => {
    const gateways = new Set(
      state.logs
        .map(log => log.gatewayId)
        .filter((id): id is string => Boolean(id))
    );
    return Array.from(gateways).sort();
  }, [state.logs]);

  // Get log statistics
  const logStats = useMemo(() => {
    const byLevel: Record<LogLevel, number> = {
      DEBUG: 0,
      INFO: 0,
      WARN: 0,
      ERROR: 0,
      CRITICAL: 0,
    };

    const byModule: Record<string, number> = {};

    state.filteredLogs.forEach(log => {
      byLevel[log.level] = (byLevel[log.level] || 0) + 1;
      byModule[log.module] = (byModule[log.module] || 0) + 1;
    });

    const timestamps = state.filteredLogs.map(log => log.timestamp);
    const timeRange = timestamps.length > 0 ? {
      start: new Date(Math.min(...timestamps.map(t => t.getTime()))),
      end: new Date(Math.max(...timestamps.map(t => t.getTime()))),
    } : {
      start: new Date(),
      end: new Date(),
    };

    return {
      total: state.filteredLogs.length,
      byLevel,
      byModule,
      timeRange,
    };
  }, [state.filteredLogs]);

  return {
    // State
    ...state,
    
    // Actions
    updateFilter,
    clearLogs,
    togglePause,
    toggleAutoScroll,
    exportLogs,
    
    // Computed data
    availableModules,
    availableGateways,
    logStats,
    
    // WebSocket control
    reconnect: () => wsClient.current?.connect(),
    disconnect: () => wsClient.current?.disconnect(),
  };
}