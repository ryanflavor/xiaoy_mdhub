import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { LogEntry } from '@/components/logs/log-entry';
import { LogEntry as LogEntryType } from '@xiaoy-mdhub/shared-types';

const mockLogEntry: LogEntryType = {
  id: 'test-log-1',
  timestamp: new Date('2024-01-01T12:00:00.123Z'),
  level: 'INFO',
  message: 'Test log message',
  module: 'test-module',
  gatewayId: 'test-gateway',
  details: {
    user: 'test-user',
    action: 'test-action',
  },
  stackTrace: 'Error stack trace here',
};

describe('LogEntry', () => {
  it('renders basic log entry information', () => {
    render(<LogEntry entry={mockLogEntry} />);
    
    expect(screen.getByText('Test log message')).toBeInTheDocument();
    expect(screen.getByText('INFO')).toBeInTheDocument();
    expect(screen.getByText('test-module')).toBeInTheDocument();
    expect(screen.getByText('Gateway: test-gateway')).toBeInTheDocument();
  });

  it('formats timestamp correctly with milliseconds', () => {
    render(<LogEntry entry={mockLogEntry} />);
    
    // Should display time with milliseconds (format may vary by locale)
    expect(screen.getByText(/\.123/)).toBeInTheDocument();
  });

  it('applies correct styling for ERROR level logs', () => {
    const errorLog: LogEntryType = {
      ...mockLogEntry,
      level: 'ERROR',
      message: 'Error message',
    };
    
    const { container } = render(<LogEntry entry={errorLog} />);
    
    expect(screen.getByText('ERROR')).toBeInTheDocument();
    expect(container.querySelector('.bg-red-50')).toBeInTheDocument();
  });

  it('applies correct styling for CRITICAL level logs', () => {
    const criticalLog: LogEntryType = {
      ...mockLogEntry,
      level: 'CRITICAL',
      message: 'Critical error',
    };
    
    const { container } = render(<LogEntry entry={criticalLog} />);
    
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(container.querySelector('.bg-red-100')).toBeInTheDocument();
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  it('shows expand button when metadata is available', () => {
    render(<LogEntry entry={mockLogEntry} />);
    
    expect(screen.getByLabelText('Expand details')).toBeInTheDocument();
  });

  it('expands to show metadata when clicked', () => {
    render(<LogEntry entry={mockLogEntry} />);
    
    const expandButton = screen.getByLabelText('Expand details');
    fireEvent.click(expandButton);
    
    expect(screen.getByText('Metadata')).toBeInTheDocument();
    expect(screen.getByText('user:')).toBeInTheDocument();
    expect(screen.getByText('test-user')).toBeInTheDocument();
    expect(screen.getByText('action:')).toBeInTheDocument();
    expect(screen.getByText('test-action')).toBeInTheDocument();
  });

  it('shows stack trace when available', () => {
    render(<LogEntry entry={mockLogEntry} />);
    
    const expandButton = screen.getByLabelText('Expand details');
    fireEvent.click(expandButton);
    
    expect(screen.getByText('Stack Trace')).toBeInTheDocument();
    expect(screen.getByText('Error stack trace here')).toBeInTheDocument();
  });

  it('does not show expand button when no metadata or stack trace', () => {
    const simpleLog: LogEntryType = {
      ...mockLogEntry,
      details: undefined,
      stackTrace: undefined,
    };
    
    render(<LogEntry entry={simpleLog} />);
    
    expect(screen.queryByLabelText('Expand details')).not.toBeInTheDocument();
  });

  it('handles different log levels with appropriate badge variants', () => {
    const levels = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'] as const;
    
    levels.forEach((level) => {
      const log: LogEntryType = {
        ...mockLogEntry,
        level,
        message: `${level} message`,
      };
      
      const { container, unmount } = render(<LogEntry entry={log} />);
      
      expect(screen.getByText(level)).toBeInTheDocument();
      expect(screen.getByText(`${level} message`)).toBeInTheDocument();
      
      unmount();
    });
  });

  it('changes expand button icon when expanded', () => {
    render(<LogEntry entry={mockLogEntry} />);
    
    const expandButton = screen.getByLabelText('Expand details');
    
    // Initial state - should show ChevronRight
    expect(expandButton).toBeInTheDocument();
    
    fireEvent.click(expandButton);
    
    // After expansion - should show ChevronDown and change aria-label
    expect(screen.getByLabelText('Collapse details')).toBeInTheDocument();
  });
});