'use client';

import React, { useState, useEffect } from 'react';
import { Clock, AlertCircle, CheckCircle, XCircle, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TradingTimeStatus as TradingTimeStatusType } from '@xiaoy-mdhub/shared-types';
import { TradingTimeService } from '@/services/tradingTimeService';

interface TradingTimeStatusProps {
  className?: string;
  showDetails?: boolean;
}

export function TradingTimeStatus({ className = '', showDetails = false }: TradingTimeStatusProps) {
  const [status, setStatus] = useState<TradingTimeStatusType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update current time every second
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Fetch trading time status
  const fetchStatus = async () => {
    try {
      setError(null);
      const data = await TradingTimeService.getTradingTimeStatus();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取交易时间状态失败');
      console.error('Failed to fetch trading time status:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch status on mount and then every 30 seconds
  useEffect(() => {
    fetchStatus();
    
    const interval = setInterval(fetchStatus, 30000); // 30 seconds
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'trading':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'pre_trading':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'post_trading':
        return <Clock className="h-4 w-4 text-orange-500" />;
      case 'non_trading':
      default:
        return <XCircle className="h-4 w-4 text-red-500" />;
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'trading':
        return 'default' as const;
      case 'pre_trading':
        return 'secondary' as const;
      case 'post_trading':
        return 'outline' as const;
      case 'non_trading':
      default:
        return 'destructive' as const;
    }
  };

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="p-4">
          <div className="flex items-center space-x-2">
            <Clock className="h-4 w-4 animate-spin" />
            <span className="text-sm text-muted-foreground">加载交易时间状态...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="p-4">
          <div className="flex items-center space-x-2 p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!status) {
    return null;
  }

  const timeUntilNext = status.next_session_start 
    ? TradingTimeService.getTimeUntilNextSession(status.next_session_start)
    : null;

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center space-x-2">
          <Calendar className="h-5 w-5" />
          <span>交易时间状态</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Current Time */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="text-2xl font-mono font-bold">
              {currentTime.toLocaleTimeString('zh-CN', { hour12: false })}
            </div>
            <div className="text-sm text-muted-foreground">
              {TradingTimeService.formatDate(status.current_date)}
            </div>
          </div>
          <div className="text-right space-y-2">
            <div className="flex items-center space-x-2">
              {getStatusIcon(status.status)}
              <Badge variant={getStatusBadgeVariant(status.status)}>
                {TradingTimeService.getStatusText(status.status)}
              </Badge>
            </div>
            {!status.is_trading_day && (
              <div className="text-xs text-muted-foreground">非交易日</div>
            )}
          </div>
        </div>

        {/* Gateway Status */}
        <div className="grid grid-cols-2 gap-2">
          <div className="flex flex-col p-2 bg-muted/30 rounded space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">CTP</span>
              <Badge variant={status.ctp_trading ? 'default' : 'secondary'} className="text-xs">
                {status.ctp_trading ? '交易中' : '已关闭'}
              </Badge>
            </div>
            {!status.ctp_trading && status.ctp_next_session && (
              <div className="text-xs text-muted-foreground font-mono">
                下次: {TradingTimeService.formatTime(status.ctp_next_session).split(' ')[1]}
              </div>
            )}
          </div>
          <div className="flex flex-col p-2 bg-muted/30 rounded space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">SOPT</span>
              <Badge variant={status.sopt_trading ? 'default' : 'secondary'} className="text-xs">
                {status.sopt_trading ? '交易中' : '已关闭'}
              </Badge>
            </div>
            {!status.sopt_trading && status.sopt_next_session && (
              <div className="text-xs text-muted-foreground font-mono">
                下次: {TradingTimeService.formatTime(status.sopt_next_session).split(' ')[1]}
              </div>
            )}
          </div>
        </div>

        {/* Next Session Info */}
        {status.next_session_start && status.next_session_name && (
          <div className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="flex items-center space-x-2 mb-1">
              <Clock className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                下一交易时段
              </span>
            </div>
            <div className="text-sm text-blue-700 dark:text-blue-300">
              <div>{status.next_session_name}</div>
              <div className="font-mono">
                {TradingTimeService.formatTime(status.next_session_start)}
              </div>
              {timeUntilNext && (
                <div className="text-xs text-blue-600 dark:text-blue-400 mt-1">
                  {timeUntilNext}开始
                </div>
              )}
            </div>
          </div>
        )}

        {/* Current Session */}
        {status.current_session_name && (
          <div className="text-center p-2 bg-green-50 dark:bg-green-950/20 rounded border border-green-200 dark:border-green-800">
            <div className="text-sm font-medium text-green-900 dark:text-green-100">
              当前交易时段: {status.current_session_name}
            </div>
          </div>
        )}

        {/* Detailed Session Info (expandable) */}
        {showDetails && status.sessions && status.sessions.length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium text-muted-foreground">交易时段配置</div>
            {status.sessions.map((session: any, index: number) => (
              <div key={index} className="p-2 bg-muted/20 rounded text-xs space-y-1">
                <div className="font-medium">{session.name} ({session.market_type})</div>
                <div className="space-y-0.5">
                  {session.ranges.map((range: any, rangeIndex: number) => (
                    <div key={rangeIndex} className="text-muted-foreground font-mono">
                      {range.start} - {range.end}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}