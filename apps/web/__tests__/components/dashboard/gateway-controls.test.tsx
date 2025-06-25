/**
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { GatewayControls } from '@/components/dashboard/gateway-controls';
import { GatewayStatus, GatewayControlAction } from '@xiaoy-mdhub/shared-types';

// Mock the tooltip components
jest.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Tooltip: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TooltipContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// Mock the alert dialog components
jest.mock('@/components/dashboard/gateway-control-dialog', () => ({
  GatewayControlDialog: ({ open, onConfirm }: { open: boolean; onConfirm: () => void }) => 
    open ? (
      <div data-testid="control-dialog">
        <button onClick={onConfirm} data-testid="confirm-button">Confirm</button>
      </div>
    ) : null
}));

describe('GatewayControls', () => {
  const mockGateway: GatewayStatus = {
    gateway_id: 'test_gateway',
    gateway_type: 'ctp',
    current_status: 'HEALTHY',
    priority: 1,
    last_update: '2025-06-25T10:30:00Z',
    connection_status: 'CONNECTED',
  };

  const mockDisconnectedGateway: GatewayStatus = {
    ...mockGateway,
    current_status: 'DISCONNECTED',
    connection_status: 'DISCONNECTED',
  };

  const mockOnAction = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders all control buttons', () => {
    render(<GatewayControls gateway={mockGateway} onAction={mockOnAction} />);
    
    expect(screen.getAllByRole('button')).toHaveLength(3);
    expect(screen.getByText('Start')).toBeInTheDocument();
    expect(screen.getByText('Stop')).toBeInTheDocument();
    expect(screen.getByText('Restart')).toBeInTheDocument();
  });

  it('disables start button when gateway is running', () => {
    render(<GatewayControls gateway={mockGateway} onAction={mockOnAction} />);
    
    const buttons = screen.getAllByRole('button');
    const startButton = buttons.find(button => button.textContent?.includes('Start'));
    expect(startButton).toBeDisabled();
  });

  it('enables start button when gateway is disconnected', () => {
    render(<GatewayControls gateway={mockDisconnectedGateway} onAction={mockOnAction} />);
    
    const buttons = screen.getAllByRole('button');
    const startButton = buttons.find(button => button.textContent?.includes('Start'));
    expect(startButton).not.toBeDisabled();
  });

  it('calls onAction when start button is clicked', async () => {
    mockOnAction.mockResolvedValue(undefined);
    render(<GatewayControls gateway={mockDisconnectedGateway} onAction={mockOnAction} />);
    
    const buttons = screen.getAllByRole('button');
    const startButton = buttons.find(button => button.textContent?.includes('Start'));
    fireEvent.click(startButton!);
    
    await waitFor(() => {
      expect(mockOnAction).toHaveBeenCalledWith('start', 'test_gateway');
    });
  });

  it('shows confirmation dialog for stop action', () => {
    render(<GatewayControls gateway={mockGateway} onAction={mockOnAction} />);
    
    const buttons = screen.getAllByRole('button');
    const stopButton = buttons.find(button => button.textContent?.includes('Stop'));
    fireEvent.click(stopButton!);
    
    expect(screen.getByTestId('control-dialog')).toBeInTheDocument();
  });

  it('shows confirmation dialog for restart action', () => {
    render(<GatewayControls gateway={mockGateway} onAction={mockOnAction} />);
    
    const buttons = screen.getAllByRole('button');
    const restartButton = buttons.find(button => button.textContent?.includes('Restart'));
    fireEvent.click(restartButton!);
    
    expect(screen.getByTestId('control-dialog')).toBeInTheDocument();
  });

  it('executes action after confirmation', async () => {
    mockOnAction.mockResolvedValue(undefined);
    render(<GatewayControls gateway={mockGateway} onAction={mockOnAction} />);
    
    const buttons = screen.getAllByRole('button');
    const stopButton = buttons.find(button => button.textContent?.includes('Stop'));
    fireEvent.click(stopButton!);
    
    const confirmButton = screen.getByTestId('confirm-button');
    fireEvent.click(confirmButton);
    
    await waitFor(() => {
      expect(mockOnAction).toHaveBeenCalledWith('stop', 'test_gateway');
    });
  });

  it('handles action errors gracefully', async () => {
    const consoleError = jest.spyOn(console, 'error').mockImplementation();
    mockOnAction.mockRejectedValue(new Error('Network error'));
    
    render(<GatewayControls gateway={mockDisconnectedGateway} onAction={mockOnAction} />);
    
    const buttons = screen.getAllByRole('button');
    const startButton = buttons.find(button => button.textContent?.includes('Start'));
    fireEvent.click(startButton!);
    
    await waitFor(() => {
      expect(consoleError).toHaveBeenCalledWith(
        expect.stringContaining('Gateway start action failed'),
        expect.any(Error)
      );
    });

    consoleError.mockRestore();
  });

  it('shows loading state during action execution', async () => {
    let resolveAction: () => void;
    const actionPromise = new Promise<void>((resolve) => {
      resolveAction = resolve;
    });
    mockOnAction.mockReturnValue(actionPromise);
    
    render(<GatewayControls gateway={mockDisconnectedGateway} onAction={mockOnAction} />);
    
    const buttons = screen.getAllByRole('button');
    const startButton = buttons.find(button => button.textContent?.includes('Start'));
    fireEvent.click(startButton!);
    
    // Check if loading state is shown (button should be disabled)
    await waitFor(() => {
      expect(startButton).toBeDisabled();
    });
    
    // Resolve the action
    resolveAction!();
    
    await waitFor(() => {
      expect(startButton).not.toBeDisabled();
    });
  });
});