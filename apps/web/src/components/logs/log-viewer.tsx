"use client";

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useLogViewer } from '@/hooks/use-log-viewer';
import { LogEntry } from './log-entry';
import { LogFilterComponent } from './log-filter';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Play, 
  Pause, 
  ScrollText, 
  Download, 
  Trash2, 
  Wifi, 
  WifiOff, 
  RotateCcw,
  Activity,
  AlertTriangle,
  Info,
  Bug,
  AlertCircle,
  Zap
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface LogViewerProps {
  className?: string;
}

const ITEM_HEIGHT = 120; // Approximate height of each log entry

export function LogViewer({ className }: LogViewerProps) {
  const {
    logs,
    filteredLogs,
    filter,
    isConnected,
    isAutoScrollEnabled,
    isPaused,
    bufferSize,
    totalLogCount,
    updateFilter,
    clearLogs,
    togglePause,
    toggleAutoScroll,
    exportLogs,
    availableModules,
    availableGateways,
    logStats,
    reconnect,
  } = useLogViewer({
    maxBufferSize: 1000,
    autoScrollToBottom: true,
    debounceDelay: 300,
  });

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 50 });
  const [isUserScrolling, setIsUserScrolling] = useState(false);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (isAutoScrollEnabled && !isUserScrolling && scrollViewportRef.current) {
      const viewport = scrollViewportRef.current;
      viewport.scrollTop = viewport.scrollHeight;
    }
  }, [filteredLogs.length, isAutoScrollEnabled, isUserScrolling]);

  // Virtual scrolling calculation
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const viewport = event.currentTarget;
    const scrollTop = viewport.scrollTop;
    const viewportHeight = viewport.clientHeight;
    const isAtBottom = scrollTop + viewportHeight >= viewport.scrollHeight - 10;

    // Update user scrolling state
    setIsUserScrolling(!isAtBottom);

    // Calculate visible range for virtual scrolling
    const startIndex = Math.floor(scrollTop / ITEM_HEIGHT);
    const endIndex = Math.min(
      startIndex + Math.ceil(viewportHeight / ITEM_HEIGHT) + 5,
      filteredLogs.length
    );

    setVisibleRange({ start: startIndex, end: endIndex });
  }, [filteredLogs.length]);

  // Export handler
  const handleExport = useCallback((format: 'json' | 'csv' | 'txt') => {
    const content = exportLogs(format);
    const blob = new Blob([content], { 
      type: format === 'json' ? 'application/json' : 
           format === 'csv' ? 'text/csv' : 'text/plain' 
    });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `system-logs-${new Date().toISOString().split('T')[0]}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [exportLogs]);

  // Get connection status icon and color
  const getConnectionStatus = () => {
    if (isConnected) {
      return { icon: Wifi, color: 'text-green-600', text: 'Connected' };
    } else {
      return { icon: WifiOff, color: 'text-red-600', text: 'Disconnected' };
    }
  };

  const connectionStatus = getConnectionStatus();
  const ConnectionIcon = connectionStatus.icon;

  // Get log level icon
  const getLogLevelIcon = (level: string) => {
    switch (level) {
      case 'DEBUG': return Bug;
      case 'INFO': return Info;
      case 'WARN': return AlertTriangle;
      case 'ERROR': return AlertCircle;
      case 'CRITICAL': return Zap;
      default: return Activity;
    }
  };

  return (
    <div className={cn("flex gap-6", className)}>
      {/* Filter Sidebar */}
      <div className="w-80 flex-shrink-0">
        <LogFilterComponent
          filter={filter}
          onFilterChange={updateFilter}
          availableModules={availableModules}
          availableGateways={availableGateways}
        />
        
        {/* Log Statistics */}
        <Card className="mt-4">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Statistics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>Total: {logStats.total}</div>
              <div>Buffer: {bufferSize}/{1000}</div>
            </div>
            
            <Separator />
            
            <div className="space-y-2">
              <div className="text-xs font-medium text-muted-foreground">By Level</div>
              {Object.entries(logStats.byLevel).map(([level, count]) => {
                if (count === 0) return null;
                const IconComponent = getLogLevelIcon(level);
                return (
                  <div key={level} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1">
                      <IconComponent className="h-3 w-3" />
                      {level}
                    </div>
                    <Badge variant="outline" className="h-5 text-xs">
                      {count}
                    </Badge>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Log Viewer */}
      <div className="flex-1 min-w-0">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <ScrollText className="h-5 w-5" />
                System Logs
                <Badge variant="outline" className="ml-2">
                  {filteredLogs.length} entries
                </Badge>
              </CardTitle>
              
              {/* Connection Status */}
              <div className="flex items-center gap-2">
                <div className={cn("flex items-center gap-1 text-sm", connectionStatus.color)}>
                  <ConnectionIcon className="h-4 w-4" />
                  {connectionStatus.text}
                </div>
                {!isConnected && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={reconnect}
                    className="h-8"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
            
            {/* Controls */}
            <div className="flex items-center gap-2">
              <Button
                variant={isPaused ? "default" : "outline"}
                size="sm"
                onClick={togglePause}
                className="h-8"
              >
                {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                {isPaused ? 'Resume' : 'Pause'}
              </Button>
              
              <Button
                variant={isAutoScrollEnabled ? "default" : "outline"}
                size="sm"
                onClick={toggleAutoScroll}
                className="h-8"
              >
                <ScrollText className="h-4 w-4" />
                Auto-scroll
              </Button>
              
              <Separator orientation="vertical" className="h-6" />
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('json')}
                className="h-8"
              >
                <Download className="h-4 w-4" />
                JSON
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('csv')}
                className="h-8"
              >
                <Download className="h-4 w-4" />
                CSV
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={clearLogs}
                className="h-8"
              >
                <Trash2 className="h-4 w-4" />
                Clear
              </Button>
            </div>
          </CardHeader>
          
          <CardContent className="p-0">
            {filteredLogs.length === 0 ? (
              <div className="flex items-center justify-center h-96 text-muted-foreground">
                <div className="text-center">
                  <ScrollText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">No logs available</p>
                  <p className="text-sm">
                    {logs.length === 0 
                      ? 'Waiting for log messages...' 
                      : 'No logs match the current filter criteria'
                    }
                  </p>
                </div>
              </div>
            ) : (
              <ScrollArea 
                className="h-[600px]" 
                ref={scrollAreaRef}
              >
                <div 
                  ref={scrollViewportRef}
                  onScroll={handleScroll}
                  className="p-4 space-y-2"
                  style={{ 
                    height: filteredLogs.length * ITEM_HEIGHT,
                    position: 'relative'
                  }}
                >
                  {/* Virtual scrolling - only render visible items */}
                  {filteredLogs.slice(visibleRange.start, visibleRange.end).map((entry, index) => (
                    <div
                      key={entry.id}
                      style={{
                        position: 'absolute',
                        top: (visibleRange.start + index) * ITEM_HEIGHT,
                        width: '100%',
                        height: ITEM_HEIGHT,
                      }}
                    >
                      <LogEntry 
                        entry={entry}
                        className="h-full"
                      />
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>
        
        {/* Status Bar */}
        <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground bg-muted/30 px-4 py-2 rounded">
          <div className="flex items-center gap-4">
            <span>Total processed: {totalLogCount}</span>
            <span>Filtered: {filteredLogs.length}</span>
            <span>Buffer: {bufferSize}/1000</span>
          </div>
          
          <div className="flex items-center gap-4">
            {isPaused && (
              <Badge variant="outline" className="text-xs">
                PAUSED
              </Badge>
            )}
            {isUserScrolling && (
              <Badge variant="outline" className="text-xs">
                MANUAL SCROLL
              </Badge>
            )}
            <span className={connectionStatus.color}>
              {connectionStatus.text}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}