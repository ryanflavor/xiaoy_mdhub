/**
 * Simple tests for canary functionality in useDashboardData hook
 */

import { renderHook, act } from '@testing-library/react';
import { useDashboardData } from '@/hooks/use-dashboard-data';

// Mock gateway service with proper health data including canary config
const mockHealthData = {
  status: 'ok',
  gateways: [],
  canary_contracts: [],
  canary_config: {
    ctp_contracts: ['rb2601', 'au2512'],
    ctp_primary: 'rb2601',
    sopt_contracts: ['510050', '159915'],
    sopt_primary: '510050',
    heartbeat_timeout_seconds: 60
  }
};

// Mock fetch globally with proper response
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(mockHealthData),
  })
) as jest.Mock;

// Mock WebSocket service
const mockWebSocketClient = {
  connect: jest.fn(),
  disconnect: jest.fn(),
  onAny: jest.fn(() => jest.fn()),
  onStateChange: jest.fn(() => jest.fn()),
  getState: jest.fn(() => 'connected'),
  getClientId: jest.fn(() => 'test-client'),
};

jest.mock('@/services/websocket', () => ({
  createWebSocketClient: jest.fn(() => mockWebSocketClient),
  WebSocketClient: jest.fn(),
}));

jest.mock('@/services/gateway-service', () => ({
  getHealthStatus: jest.fn(() => Promise.resolve(mockHealthData)),
}));

describe('useDashboardData Canary Functionality', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize canary contracts from health config', async () => {
    const { result } = renderHook(() => useDashboardData());
    
    // Wait for initial data load
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Should have initial canary contracts from config
    expect(result.current.data.canary_contracts.length).toBeGreaterThan(0);
    
    // Check that contracts include those from config
    const contractSymbols = result.current.data.canary_contracts.map((c: any) => c.contract_symbol);
    expect(contractSymbols).toContain('rb2601');
    expect(contractSymbols).toContain('au2512');
    expect(contractSymbols).toContain('510050');
    expect(contractSymbols).toContain('159915');
  });

  it('should setup WebSocket to listen for messages', async () => {
    renderHook(() => useDashboardData());
    
    // Wait for WebSocket setup
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Verify WebSocket client was created and connected
    expect(mockWebSocketClient.connect).toHaveBeenCalled();
    expect(mockWebSocketClient.onAny).toHaveBeenCalled();
    expect(mockWebSocketClient.onStateChange).toHaveBeenCalled();
  });

  it('should have proper canary contract structure', async () => {
    const { result } = renderHook(() => useDashboardData());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Check canary contract structure
    const canaryContracts = result.current.data.canary_contracts;
    expect(canaryContracts.length).toBeGreaterThan(0);
    
    // Each contract should have the required fields
    canaryContracts.forEach((contract: any) => {
      expect(contract).toHaveProperty('contract_symbol');
      expect(contract).toHaveProperty('status');
      expect(contract).toHaveProperty('tick_count_1min');
      expect(contract).toHaveProperty('last_tick_time');
      expect(contract).toHaveProperty('threshold_seconds');
      
      // Status should be one of the valid values
      expect(['ACTIVE', 'STALE', 'INACTIVE']).toContain(contract.status);
    });
  });

  it('should handle loading and error states', () => {
    const { result } = renderHook(() => useDashboardData());
    
    // Initially should be loading
    expect(result.current.isLoading).toBe(true);
    expect(result.current.error).toBe(null);
    
    // Should have initial empty data structure
    expect(result.current.data).toHaveProperty('gateways');
    expect(result.current.data).toHaveProperty('canary_contracts');
    expect(result.current.data).toHaveProperty('system_health');
  });

  it('should provide refresh functionality', async () => {
    const { result } = renderHook(() => useDashboardData());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Should have refresh function
    expect(typeof result.current.refreshData).toBe('function');
    
    // Calling refresh should work without errors
    await act(async () => {
      await result.current.refreshData();
    });
  });
});