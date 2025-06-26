/**
 * Tests for canary functionality in useDashboardData hook
 */

import { renderHook, act } from '@testing-library/react';
import { useDashboardData } from '@/hooks/use-dashboard-data';
import { WebSocketEventType } from '@xiaoy-mdhub/shared-types';
import type { CanaryTickUpdateMessage } from '@xiaoy-mdhub/shared-types';

// Mock fetch globally
global.fetch = jest.fn();

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

  it('should setup WebSocket to listen for canary messages', async () => {
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

  it('should update existing canary contract data instead of creating duplicates', async () => {
    const { result } = renderHook(() => useDashboardData());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    const firstUpdate: CanaryTickUpdateMessage = {
      event_type: WebSocketEventType.CANARY_TICK_UPDATE,
      timestamp: new Date().toISOString(),
      gateway_id: 'ctp_01',
      contract_symbol: 'rb2601',
      tick_count_1min: 30,
      last_tick_time: new Date().toISOString(),
      status: 'ACTIVE',
      threshold_seconds: 60
    };

    const secondUpdate: CanaryTickUpdateMessage = {
      event_type: WebSocketEventType.CANARY_TICK_UPDATE,
      timestamp: new Date().toISOString(),
      gateway_id: 'ctp_01',
      contract_symbol: 'rb2601',
      tick_count_1min: 45,
      last_tick_time: new Date().toISOString(),
      status: 'STALE',
      threshold_seconds: 60
    };

    act(() => {
      const mockHandleMessage = result.current.handleWebSocketMessage;
      if (mockHandleMessage) {
        mockHandleMessage(firstUpdate);
        mockHandleMessage(secondUpdate);
      }
    });

    // Should have only one rb2601 contract with updated data
    const rb2601Contracts = result.current.data.canary_contracts.filter(
      (c: any) => c.contract_symbol === 'rb2601'
    );
    
    expect(rb2601Contracts).toHaveLength(1);
    expect(rb2601Contracts[0]).toMatchObject({
      contract_symbol: 'rb2601',
      status: 'STALE',
      tick_count_1min: 45
    });
  });

  it('should handle multiple canary contracts correctly', async () => {
    const { result } = renderHook(() => useDashboardData());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    const rb2601Update: CanaryTickUpdateMessage = {
      event_type: WebSocketEventType.CANARY_TICK_UPDATE,
      timestamp: new Date().toISOString(),
      gateway_id: 'ctp_01',
      contract_symbol: 'rb2601',
      tick_count_1min: 30,
      last_tick_time: new Date().toISOString(),
      status: 'ACTIVE',
      threshold_seconds: 60
    };

    const au2512Update: CanaryTickUpdateMessage = {
      event_type: WebSocketEventType.CANARY_TICK_UPDATE,
      timestamp: new Date().toISOString(),
      gateway_id: 'ctp_01',
      contract_symbol: 'au2512',
      tick_count_1min: 15,
      last_tick_time: new Date().toISOString(),
      status: 'INACTIVE',
      threshold_seconds: 60
    };

    act(() => {
      const mockHandleMessage = result.current.handleWebSocketMessage;
      if (mockHandleMessage) {
        mockHandleMessage(rb2601Update);
        mockHandleMessage(au2512Update);
      }
    });

    // Should have both contracts
    expect(result.current.data.canary_contracts).toHaveLength(2);
    expect(result.current.data.canary_contracts).toContainEqual(
      expect.objectContaining({
        contract_symbol: 'rb2601',
        status: 'ACTIVE'
      })
    );
    expect(result.current.data.canary_contracts).toContainEqual(
      expect.objectContaining({
        contract_symbol: 'au2512',
        status: 'INACTIVE'
      })
    );
  });

  it('should initialize canary contracts from health config', async () => {
    const { result } = renderHook(() => useDashboardData());
    
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

  it('should handle canary status transitions correctly', async () => {
    const { result } = renderHook(() => useDashboardData());
    
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Test ACTIVE status
    const activeUpdate: CanaryTickUpdateMessage = {
      event_type: WebSocketEventType.CANARY_TICK_UPDATE,
      timestamp: new Date().toISOString(),
      gateway_id: 'ctp_01',
      contract_symbol: 'rb2601',
      tick_count_1min: 50,
      last_tick_time: new Date().toISOString(),
      status: 'ACTIVE',
      threshold_seconds: 60
    };

    act(() => {
      const mockHandleMessage = result.current.handleWebSocketMessage;
      if (mockHandleMessage) {
        mockHandleMessage(activeUpdate);
      }
    });

    let rb2601Contract = result.current.data.canary_contracts.find(
      (c: any) => c.contract_symbol === 'rb2601'
    );
    expect(rb2601Contract?.status).toBe('ACTIVE');

    // Test STALE status
    const staleUpdate: CanaryTickUpdateMessage = {
      ...activeUpdate,
      status: 'STALE',
      tick_count_1min: 20
    };

    act(() => {
      const mockHandleMessage = result.current.handleWebSocketMessage;
      if (mockHandleMessage) {
        mockHandleMessage(staleUpdate);
      }
    });

    rb2601Contract = result.current.data.canary_contracts.find(
      (c: any) => c.contract_symbol === 'rb2601'
    );
    expect(rb2601Contract?.status).toBe('STALE');

    // Test INACTIVE status
    const inactiveUpdate: CanaryTickUpdateMessage = {
      ...activeUpdate,
      status: 'INACTIVE',
      tick_count_1min: 0
    };

    act(() => {
      const mockHandleMessage = result.current.handleWebSocketMessage;
      if (mockHandleMessage) {
        mockHandleMessage(inactiveUpdate);
      }
    });

    rb2601Contract = result.current.data.canary_contracts.find(
      (c: any) => c.contract_symbol === 'rb2601'
    );
    expect(rb2601Contract?.status).toBe('INACTIVE');
  });
});