"use client"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { GatewayControlAction, GatewayStatus } from '@xiaoy-mdhub/shared-types';
import { AlertTriangle, Square, RotateCcw } from 'lucide-react';

interface GatewayControlDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  gateway: GatewayStatus;
  action: GatewayControlAction;
  onConfirm: () => void;
  loading?: boolean;
}

function getActionConfig(action: GatewayControlAction) {
  switch (action) {
    case 'stop':
      return {
        title: 'Stop Gateway',
        description: 'This will stop the gateway and disconnect all active connections. Market data will no longer be received from this gateway.',
        icon: <Square className="h-5 w-5 text-red-500" />,
        confirmText: 'Stop Gateway',
        confirmVariant: 'destructive' as const,
        severity: 'high' as const
      };
    case 'restart':
      return {
        title: 'Restart Gateway',
        description: 'This will stop and restart the gateway, temporarily interrupting market data flow. The gateway will attempt to reconnect automatically.',
        icon: <RotateCcw className="h-5 w-5 text-orange-500" />,
        confirmText: 'Restart Gateway',
        confirmVariant: 'default' as const,
        severity: 'medium' as const
      };
    case 'start':
      return {
        title: 'Start Gateway',
        description: 'This will start the gateway and initiate connection to the market data provider.',
        icon: <AlertTriangle className="h-5 w-5 text-blue-500" />,
        confirmText: 'Start Gateway',
        confirmVariant: 'default' as const,
        severity: 'low' as const
      };
  }
}

export function GatewayControlDialog({
  open,
  onOpenChange,
  gateway,
  action,
  onConfirm,
  loading = false
}: GatewayControlDialogProps) {
  const config = getActionConfig(action);

  const handleConfirm = () => {
    onConfirm();
    onOpenChange(false);
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-3">
            {config.icon}
            <AlertDialogTitle>{config.title}</AlertDialogTitle>
          </div>
          <AlertDialogDescription className="text-left">
            <div className="space-y-3">
              <p>{config.description}</p>
              
              <div className="bg-muted p-3 rounded-md">
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Gateway ID:</span>
                    <span className="text-muted-foreground">{gateway.gateway_id}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Type:</span>
                    <span className="text-muted-foreground uppercase">{gateway.gateway_type}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Current Status:</span>
                    <span className="text-muted-foreground">{gateway.current_status}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Priority:</span>
                    <span className="text-muted-foreground">{gateway.priority}</span>
                  </div>
                </div>
              </div>

              {config.severity === 'high' && (
                <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-950/30 rounded-md border border-red-200 dark:border-red-800">
                  <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <div className="text-sm">
                    <p className="font-medium text-red-700 dark:text-red-300">Warning</p>
                    <p className="text-red-600 dark:text-red-400">
                      This action will immediately stop market data flow. Ensure you have alternative data sources active.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={loading}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            className={config.confirmVariant === 'destructive' ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90' : ''}
            disabled={loading}
          >
            {loading ? 'Processing...' : config.confirmText}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}