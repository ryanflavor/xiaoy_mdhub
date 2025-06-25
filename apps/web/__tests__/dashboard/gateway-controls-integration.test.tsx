/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { GatewayStatusCard } from '@/components/dashboard/gateway-status-card';
import { GatewayStatus } from '@xiaoy-mdhub/shared-types';

// Mock the API service
const mockControlGateway = jest.fn();
jest.mock('@/services/api', () => ({
  gatewayService: {
    controlGateway: mockControlGateway,
  },
}));

// Mock the date-fns library
jest.mock('date-fns', () => ({
  formatDistanceToNow: jest.fn(() => '2 minutes ago'),
}));

// Mock the tooltip and dialog components
jest.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Tooltip: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock('@/components/dashboard/gateway-control-dialog', () => ({
  GatewayControlDialog: ({ open, onConfirm }: { open: boolean; onConfirm: () => void }) => 
    open ? (
      <div data-testid="control-dialog">
        <button onClick={onConfirm} data-testid="confirm-button">Confirm</button>
      </div>
    ) : null
}));

describe('Gateway Controls Integration', () => {
  const mockHealthyGateway: GatewayStatus = {
    gateway_id: 'ctp_main_account',
    gateway_type: 'ctp',
    current_status: 'HEALTHY',
    priority: 1,
    last_update: '2025-06-25T10:30:00Z',
    connection_status: 'CONNECTED',
    last_tick_time: '2025-06-25T10:29:50Z',
    canary_status: 'ACTIVE',
  };

  const mockDisconnectedGateway: GatewayStatus = {
    ...mockHealthyGateway,
    current_status: 'DISCONNECTED',
    connection_status: 'DISCONNECTED',
    canary_status: 'INACTIVE',
  };

  const mockOnAction = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockControlGateway.mockReset();
  });

  it('renders gateway status card with controls', () => {
    render(<GatewayStatusCard gateway={mockHealthyGateway} onAction={mockOnAction} />);
    
    // Check if gateway information is displayed
    expect(screen.getByText('ctp_main_account')).toBeInTheDocument();
    expect(screen.getByText('ctp')).toBeInTheDocument(); // CSS uppercase is not applied in JSDOM
    expect(screen.getByText('HEALTHY')).toBeInTheDocument();
    expect(screen.getByText('CONNECTED')).toBeInTheDocument();
    
    // Check if control buttons are present
    expect(screen.getByRole('button', { name: /^start$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^stop$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^restart$/i })).toBeInTheDocument();
  });

  it('handles successful gateway start action', async () => {
    mockOnAction.mockResolvedValue(undefined);
    render(<GatewayStatusCard gateway={mockDisconnectedGateway} onAction={mockOnAction} />);
    
    const startButton = screen.getByRole('button', { name: /^start$/i });
    fireEvent.click(startButton);
    
    await waitFor(() => {
      expect(mockOnAction).toHaveBeenCalledWith('start', 'ctp_main_account');
    });
  });

  it('handles gateway stop action with confirmation', async () => {
    mockOnAction.mockResolvedValue(undefined);
    render(<GatewayStatusCard gateway={mockHealthyGateway} onAction={mockOnAction} />);
    
    const stopButton = screen.getByRole('button', { name: /^stop$/i });
    fireEvent.click(stopButton);
    
    // Should show confirmation dialog
    expect(screen.getByTestId('control-dialog')).toBeInTheDocument();
    
    // Confirm the action
    const confirmButton = screen.getByTestId('confirm-button');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(mockOnAction).toHaveBeenCalledWith('stop', 'ctp_main_account');
    });
  });

  it('handles gateway restart action with confirmation', async () => {
    mockOnAction.mockResolvedValue(undefined);
    render(<GatewayStatusCard gateway={mockHealthyGateway} onAction={mockOnAction} />);
    
    const restartButton = screen.getByRole('button', { name: /^restart$/i });
    fireEvent.click(restartButton);
    
    // Should show confirmation dialog
    expect(screen.getByTestId('control-dialog')).toBeInTheDocument();
    
    // Confirm the action
    const confirmButton = screen.getByTestId('confirm-button');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(mockOnAction).toHaveBeenCalledWith('restart', 'ctp_main_account');
    });
  });

  it('handles API error during gateway control', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    mockOnAction.mockRejectedValue(new Error('Gateway control failed'));
    
    render(<GatewayStatusCard gateway={mockDisconnectedGateway} onAction={mockOnAction} />);
    
    const startButton = screen.getByRole('button', { name: /^start$/i });
    fireEvent.click(startButton);
    
    await waitFor(() => {
      expect(consoleError).toHaveBeenCalledWith(
        expect.stringContaining('Gateway start action failed'),
        expect.any(Error)
      );
    });

    consoleError.mockRestore();
  });

  it('correctly enables/disables buttons based on gateway status', () => {
    const { rerender } = render(
      <GatewayStatusCard gateway={mockHealthyGateway} onAction={mockOnAction} />
    );
    
    // When gateway is healthy/connected
    expect(screen.getByRole('button', { name: /^start$/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /^stop$/i })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: /^restart$/i })).not.toBeDisabled();
    
    // When gateway is disconnected
    rerender(<GatewayStatusCard gateway={mockDisconnectedGateway} onAction={mockOnAction} />);
    
    expect(screen.getByRole('button', { name: /^start$/i })).not.toBeDisabled();
    expect(screen.getByRole('button', { name: /^stop$/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /^restart$/i })).not.toBeDisabled();
  });

  it('shows appropriate button states during action execution', async () => {
    let resolveAction: () => void;
    const actionPromise = new Promise<void>((resolve) => {
      resolveAction = resolve;
    });
    mockOnAction.mockReturnValue(actionPromise);
    
    render(<GatewayStatusCard gateway={mockDisconnectedGateway} onAction={mockOnAction} />);
    
    const startButton = screen.getByRole('button', { name: /^start$/i });
    fireEvent.click(startButton);
    
    // Button should be disabled during loading
    await waitFor(() => {
      expect(startButton).toBeDisabled();
    });
    
    // Resolve the action
    resolveAction!();
    
    // Button should be enabled again after completion
    await waitFor(() => {
      expect(startButton).not.toBeDisabled();
    });
  });
});