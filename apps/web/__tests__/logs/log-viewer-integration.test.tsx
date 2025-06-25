import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { LogViewer } from '@/components/logs/log-viewer';

// Mock the useLogViewer hook
jest.mock('@/hooks/use-log-viewer', () => ({
  useLogViewer: jest.fn(() => ({
    logs: [],
    filteredLogs: [],
    filter: {},
    isConnected: false,
    isAutoScrollEnabled: true,
    isPaused: false,
    bufferSize: 0,
    totalLogCount: 0,
    updateFilter: jest.fn(),
    clearLogs: jest.fn(),
    togglePause: jest.fn(),
    toggleAutoScroll: jest.fn(),
    exportLogs: jest.fn(),
    availableModules: ['gateway_manager', 'websocket_manager'],
    availableGateways: ['ctp_main', 'sopt_backup'],
    logStats: {
      total: 0,
      byLevel: {
        DEBUG: 0,
        INFO: 0,
        WARN: 0,
        ERROR: 0,
        CRITICAL: 0,
      },
      byModule: {},
      timeRange: {
        start: new Date(),
        end: new Date(),
      },
    },
    reconnect: jest.fn(),
  })),
}));

// Mock next/dynamic for any lazy-loaded components
jest.mock('next/dynamic', () => ({
  __esModule: true,
  default: jest.fn((fn) => {
    const Component = fn();
    return Component;
  }),
}));

describe('LogViewer Integration', () => {
  it('renders log viewer with main components', () => {
    render(<LogViewer />);
    
    expect(screen.getByText('Log Filters')).toBeInTheDocument();
    expect(screen.getByText('System Logs')).toBeInTheDocument();
    expect(screen.getByText('Statistics')).toBeInTheDocument();
  });

  it('shows disconnected state initially', () => {
    render(<LogViewer />);
    
    expect(screen.getAllByText('Disconnected')).toHaveLength(2);
  });

  it('shows empty state when no logs are available', () => {
    render(<LogViewer />);
    
    expect(screen.getByText('No logs available')).toBeInTheDocument();
    expect(screen.getByText('Waiting for log messages...')).toBeInTheDocument();
  });

  it('displays log viewer controls', () => {
    render(<LogViewer />);
    
    expect(screen.getByText('Pause')).toBeInTheDocument(); // Since isPaused is false, shows "Pause"
    expect(screen.getByText('Auto-scroll')).toBeInTheDocument();
    expect(screen.getByText('JSON')).toBeInTheDocument();
    expect(screen.getByText('CSV')).toBeInTheDocument();
    expect(screen.getByText('Clear')).toBeInTheDocument();
  });
});

describe('LogViewer with Connected State', () => {
  beforeEach(() => {
    const { useLogViewer } = require('@/hooks/use-log-viewer');
    useLogViewer.mockReturnValue({
      logs: [],
      filteredLogs: [],
      filter: {},
      isConnected: true,
      isAutoScrollEnabled: true,
      isPaused: false,
      bufferSize: 0,
      totalLogCount: 0,
      updateFilter: jest.fn(),
      clearLogs: jest.fn(),
      togglePause: jest.fn(),
      toggleAutoScroll: jest.fn(),
      exportLogs: jest.fn(),
      availableModules: ['gateway_manager', 'websocket_manager'],
      availableGateways: ['ctp_main', 'sopt_backup'],
      logStats: {
        total: 0,
        byLevel: {
          DEBUG: 0,
          INFO: 0,
          WARN: 0,
          ERROR: 0,
          CRITICAL: 0,
        },
        byModule: {},
        timeRange: {
          start: new Date(),
          end: new Date(),
        },
      },
      reconnect: jest.fn(),
    });
  });

  it('shows connected state', () => {
    render(<LogViewer />);
    
    expect(screen.getAllByText('Connected')).toHaveLength(2);
    expect(screen.queryByLabelText('Reconnect')).not.toBeInTheDocument();
  });
});

describe('LogViewer with Log Data', () => {
  beforeEach(() => {
    const { useLogViewer } = require('@/hooks/use-log-viewer');
    useLogViewer.mockReturnValue({
      logs: [
        {
          id: 'log-1',
          timestamp: new Date('2024-01-01T12:00:00Z'),
          level: 'INFO',
          message: 'Test log message',
          module: 'gateway_manager',
          gatewayId: 'ctp_main',
        },
        {
          id: 'log-2',
          timestamp: new Date('2024-01-01T12:00:01Z'),
          level: 'ERROR',
          message: 'Error log message',
          module: 'websocket_manager',
        },
      ],
      filteredLogs: [
        {
          id: 'log-1',
          timestamp: new Date('2024-01-01T12:00:00Z'),
          level: 'INFO',
          message: 'Test log message',
          module: 'gateway_manager',
          gatewayId: 'ctp_main',
        },
        {
          id: 'log-2',
          timestamp: new Date('2024-01-01T12:00:01Z'),
          level: 'ERROR',
          message: 'Error log message',
          module: 'websocket_manager',
        },
      ],
      filter: {},
      isConnected: true,
      isAutoScrollEnabled: true,
      isPaused: false,
      bufferSize: 2,
      totalLogCount: 2,
      updateFilter: jest.fn(),
      clearLogs: jest.fn(),
      togglePause: jest.fn(),
      toggleAutoScroll: jest.fn(),
      exportLogs: jest.fn(() => 'exported data'),
      availableModules: ['gateway_manager', 'websocket_manager'],
      availableGateways: ['ctp_main', 'sopt_backup'],
      logStats: {
        total: 2,
        byLevel: {
          DEBUG: 0,
          INFO: 1,
          WARN: 0,
          ERROR: 1,
          CRITICAL: 0,
        },
        byModule: {
          gateway_manager: 1,
          websocket_manager: 1,
        },
        timeRange: {
          start: new Date('2024-01-01T12:00:00Z'),
          end: new Date('2024-01-01T12:00:01Z'),
        },
      },
      reconnect: jest.fn(),
    });
  });

  it('displays log entries when data is available', () => {
    render(<LogViewer />);
    
    expect(screen.getByText('Test log message')).toBeInTheDocument();
    expect(screen.getByText('Error log message')).toBeInTheDocument();
  });

  it('shows correct entry count', () => {
    render(<LogViewer />);
    
    expect(screen.getByText('2 entries')).toBeInTheDocument();
  });

  it('displays statistics correctly', () => {
    render(<LogViewer />);
    
    expect(screen.getByText('Total: 2')).toBeInTheDocument();
    expect(screen.getAllByText('Buffer: 2/1000')).toHaveLength(2);
  });

  it('shows status bar with correct information', () => {
    render(<LogViewer />);
    
    expect(screen.getByText('Total processed: 2')).toBeInTheDocument();
    expect(screen.getByText('Filtered: 2')).toBeInTheDocument();
    // Buffer information appears in multiple places, check for existence
    expect(screen.getAllByText(/Buffer: 2\/1000/)).toHaveLength(2);
  });
});