/**
 * Hook for monitoring API and WebSocket connection status
 */

import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '@/services/api-client';

export interface ConnectionStatus {
  isOnline: boolean;
  apiConnected: boolean;
  wsConnected: boolean;
  lastApiCheck: Date | null;
  lastWsMessage: Date | null;
  retryCount: number;
}

export interface UseConnectionStatusReturn {
  status: ConnectionStatus;
  checkConnection: () => Promise<void>;
  resetRetryCount: () => void;
}

const HEALTH_CHECK_INTERVAL = 30000; // 30 seconds
const MAX_RETRY_COUNT = 5;

export function useConnectionStatus(): UseConnectionStatusReturn {
  const [status, setStatus] = useState<ConnectionStatus>({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true, // Default to true on server
    apiConnected: false,
    wsConnected: false,
    lastApiCheck: null,
    lastWsMessage: null,
    retryCount: 0,
  });

  const checkApiConnection = useCallback(async () => {
    try {
      await apiClient.get('/health');
      setStatus(prev => ({
        ...prev,
        apiConnected: true,
        lastApiCheck: new Date(),
        retryCount: 0,
      }));
      return true;
    } catch (error) {
      setStatus(prev => ({
        ...prev,
        apiConnected: false,
        lastApiCheck: new Date(),
        retryCount: Math.min(prev.retryCount + 1, MAX_RETRY_COUNT),
      }));
      return false;
    }
  }, []);

  const checkConnection = useCallback(async () => {
    await checkApiConnection();
  }, [checkApiConnection]);

  const resetRetryCount = useCallback(() => {
    setStatus(prev => ({ ...prev, retryCount: 0 }));
  }, []);

  // Monitor online/offline status
  useEffect(() => {
    // Update initial online status on client side
    if (typeof navigator !== 'undefined') {
      setStatus(prev => ({ ...prev, isOnline: navigator.onLine }));
    }

    const handleOnline = () => {
      setStatus(prev => ({ ...prev, isOnline: true }));
      checkConnection();
    };

    const handleOffline = () => {
      setStatus(prev => ({ 
        ...prev, 
        isOnline: false,
        apiConnected: false,
        wsConnected: false,
      }));
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [checkConnection]);

  // Periodic health checks
  useEffect(() => {
    if (!status.isOnline) return;

    const interval = setInterval(() => {
      checkConnection();
    }, HEALTH_CHECK_INTERVAL);

    // Initial check
    checkConnection();

    return () => clearInterval(interval);
  }, [status.isOnline, checkConnection]);

  return {
    status,
    checkConnection,
    resetRetryCount,
  };
}