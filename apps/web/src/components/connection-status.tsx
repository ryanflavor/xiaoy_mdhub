'use client';

import dynamic from 'next/dynamic';
import { useConnectionStatus } from '@/hooks/use-connection-status';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';

function ConnectionStatusContent() {
  const { status, checkConnection, resetRetryCount } = useConnectionStatus();

  if (status.isOnline && status.apiConnected) {
    return null; // Don't show anything when everything is connected
  }

  const getStatusInfo = () => {
    if (!status.isOnline) {
      return {
        variant: 'destructive' as const,
        text: '离线',
        description: '网络连接已断开',
        showRetry: false,
      };
    }

    if (!status.apiConnected) {
      return {
        variant: 'destructive' as const,
        text: 'API 连接断开',
        description: `API 服务器无法访问 (重试 ${status.retryCount}/${5})`,
        showRetry: true,
      };
    }

    return {
      variant: 'secondary' as const,
      text: '连接中',
      description: '正在重新连接...',
      showRetry: false,
    };
  };

  const statusInfo = getStatusInfo();

  return (
    <div className="fixed top-4 right-4 z-50">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2 bg-white border rounded-lg px-3 py-2 shadow-lg">
              <div className={`w-2 h-2 rounded-full ${
                statusInfo.variant === 'destructive' ? 'bg-red-500' : 'bg-yellow-500'
              } animate-pulse`} />
              <Badge variant={statusInfo.variant} className="text-xs">
                {statusInfo.text}
              </Badge>
              {statusInfo.showRetry && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    resetRetryCount();
                    checkConnection();
                  }}
                  className="h-6 px-2 text-xs"
                >
                  重试
                </Button>
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p className="text-sm">{statusInfo.description}</p>
            {status.lastApiCheck && (
              <p className="text-xs text-gray-500 mt-1">
                上次检查: {status.lastApiCheck.toLocaleTimeString()}
              </p>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}

// Export as a dynamic component with no SSR
export const ConnectionStatus = dynamic(() => Promise.resolve(ConnectionStatusContent), {
  ssr: false,
});