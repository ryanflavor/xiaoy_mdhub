"use client";

import React, { useState } from 'react';
import { LogEntry as LogEntryType, LogLevel } from '@xiaoy-mdhub/shared-types';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface LogEntryProps {
  entry: LogEntryType;
  className?: string;
}

const getLogLevelVariant = (level: LogLevel) => {
  switch (level) {
    case 'DEBUG':
      return { variant: 'outline' as const, className: 'text-muted-foreground' };
    case 'INFO':
      return { variant: 'secondary' as const, className: 'text-blue-600 dark:text-blue-400' };
    case 'WARN':
      return { variant: 'outline' as const, className: 'text-amber-600 dark:text-amber-400 border-amber-600' };
    case 'ERROR':
      return { variant: 'destructive' as const, className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' };
    case 'CRITICAL':
      return { variant: 'destructive' as const, className: 'bg-red-600 text-white animate-pulse font-bold' };
    default:
      return { variant: 'outline' as const, className: '' };
  }
};

const getLogEntryBackground = (level: LogLevel) => {
  switch (level) {
    case 'ERROR':
      return 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900';
    case 'CRITICAL':
      return 'bg-red-100 dark:bg-red-950/40 border-red-300 dark:border-red-800 border-2';
    case 'WARN':
      return 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900';
    default:
      return 'bg-card';
  }
};

const formatTimestamp = (timestamp: Date) => {
  const time = new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(timestamp);
  
  const ms = timestamp.getMilliseconds().toString().padStart(3, '0');
  return `${time}.${ms}`;
};

export function LogEntry({ entry, className }: LogEntryProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const levelConfig = getLogLevelVariant(entry.level);
  const backgroundClass = getLogEntryBackground(entry.level);
  
  const hasMetadata = entry.details && Object.keys(entry.details).length > 0;
  const hasStackTrace = Boolean(entry.stackTrace);
  const isExpandable = hasMetadata || hasStackTrace;

  return (
    <Card className={cn(backgroundClass, className)}>
      <CardContent className="p-3">
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 w-16 text-xs text-muted-foreground font-mono">
              {formatTimestamp(entry.timestamp)}
            </div>
            
            <div className="flex-shrink-0">
              <Badge 
                variant={levelConfig.variant}
                className={cn('min-w-[60px] justify-center', levelConfig.className)}
              >
                {entry.level}
              </Badge>
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-start gap-2">
                <div className="flex-1 min-w-0">
                  <p className={cn(
                    'text-sm break-words',
                    entry.level === 'ERROR' && 'font-medium text-red-900 dark:text-red-100',
                    entry.level === 'CRITICAL' && 'font-bold text-red-950 dark:text-red-50'
                  )}>
                    {entry.message}
                  </p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    <span className="font-mono">{entry.module}</span>
                    {entry.gatewayId && (
                      <>
                        <span>•</span>
                        <span>Gateway: {entry.gatewayId}</span>
                      </>
                    )}
                  </div>
                </div>
                
                {isExpandable && (
                  <CollapsibleTrigger 
                    className="flex-shrink-0 p-1 hover:bg-muted rounded"
                    aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </CollapsibleTrigger>
                )}
              </div>
            </div>
          </div>
          
          {isExpandable && (
            <CollapsibleContent className="mt-3 pl-19">
              <div className="space-y-3 p-3 bg-muted/50 rounded">
                {hasMetadata && (
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-2">Metadata</h4>
                    <div className="space-y-1">
                      {Object.entries(entry.details!).map(([key, value]) => (
                        <div key={key} className="flex gap-2 text-xs">
                          <span className="font-mono text-muted-foreground min-w-0 flex-shrink-0">
                            {key}:
                          </span>
                          <span className="font-mono break-all">
                            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {hasStackTrace && (
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground mb-2">Stack Trace</h4>
                    <pre className="text-xs font-mono bg-background p-2 rounded border overflow-x-auto whitespace-pre-wrap">
                      {entry.stackTrace}
                    </pre>
                  </div>
                )}
              </div>
            </CollapsibleContent>
          )}
        </Collapsible>
      </CardContent>
    </Card>
  );
}