"use client"

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { GatewayControlDialog } from './gateway-control-dialog';
import { 
  GatewayControlAction, 
  ButtonState, 
  GatewayStatus 
} from '@xiaoy-mdhub/shared-types';
import { Play, Square, RotateCcw, Loader2, Check, X } from 'lucide-react';

interface GatewayControlsProps {
  gateway: GatewayStatus;
  onAction: (action: GatewayControlAction, gatewayId: string) => Promise<void>;
}

interface ControlButtonProps {
  action: GatewayControlAction;
  icon: React.ReactNode;
  label: string;
  disabled: boolean;
  state: ButtonState;
  variant?: 'default' | 'destructive' | 'outline' | 'secondary';
  tooltip?: string;
  onClick: () => void;
}

function ControlButton({
  action,
  icon,
  label,
  disabled,
  state,
  variant = 'outline',
  tooltip,
  onClick
}: ControlButtonProps) {
  // Determine visual feedback based on state
  const getIcon = () => {
    switch (state) {
      case 'loading':
        return <Loader2 className="h-3 w-3 animate-spin" />;
      case 'success':
        return <Check className="h-3 w-3 text-green-600" />;
      case 'error':
        return <X className="h-3 w-3 text-red-600" />;
      default:
        return icon;
    }
  };

  const getButtonVariant = () => {
    if (state === 'success') return 'default';
    if (state === 'error') return 'destructive';
    return variant;
  };

  const button = (
    <Button
      variant={getButtonVariant()}
      size="sm"
      disabled={disabled || state === 'loading'}
      onClick={onClick}
      className={`h-8 px-2 text-xs transition-all duration-200 ${
        state === 'loading' ? 'opacity-75' : ''
      } ${state === 'success' ? 'bg-green-600 hover:bg-green-700' : ''}`}
    >
      {getIcon()}
      <span className="ml-1">{label}</span>
    </Button>
  );

  if (tooltip && (disabled || state === 'loading')) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            {button}
          </TooltipTrigger>
          <TooltipContent>
            <p>{tooltip}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return button;
}

export function GatewayControls({ gateway, onAction }: GatewayControlsProps) {
  const [buttonStates, setButtonStates] = useState<Record<GatewayControlAction, ButtonState>>({
    start: 'idle',
    stop: 'idle',
    restart: 'idle'
  });
  
  const [dialogState, setDialogState] = useState<{
    open: boolean;
    action: GatewayControlAction | null;
  }>({
    open: false,
    action: null
  });

  const handleButtonClick = (action: GatewayControlAction) => {
    // Start action doesn't need confirmation
    if (action === 'start') {
      handleAction(action);
    } else {
      // Stop and restart require confirmation
      setDialogState({ open: true, action });
    }
  };

  const handleConfirmAction = () => {
    if (dialogState.action) {
      handleAction(dialogState.action);
    }
  };

  const handleAction = async (action: GatewayControlAction) => {
    setButtonStates(prev => ({ ...prev, [action]: 'loading' }));
    
    try {
      await onAction(action, gateway.gateway_id);
      setButtonStates(prev => ({ ...prev, [action]: 'success' }));
      
      // Reset to idle after showing success
      setTimeout(() => {
        setButtonStates(prev => ({ ...prev, [action]: 'idle' }));
      }, 2000);
    } catch (error) {
      console.error(`Gateway ${action} action failed for ${gateway.gateway_id}:`, error);
      setButtonStates(prev => ({ ...prev, [action]: 'error' }));
      
      // Reset to idle after showing error
      setTimeout(() => {
        setButtonStates(prev => ({ ...prev, [action]: 'idle' }));
      }, 5000);
    }
  };

  // Determine button availability based on gateway status
  const isRunning = gateway.current_status === 'HEALTHY' || gateway.connection_status === 'CONNECTED';
  const isStopped = gateway.current_status === 'DISCONNECTED' || gateway.connection_status === 'DISCONNECTED';
  const isRecovering = gateway.current_status === 'RECOVERING';

  const canStart = isStopped && !isRecovering;
  const canStop = isRunning && !isRecovering;
  const canRestart = (isRunning || isStopped) && !isRecovering;

  return (
    <>
      <div className="flex gap-1">
        <ControlButton
          action="start"
          icon={<Play className="h-3 w-3" />}
          label="Start"
          disabled={!canStart}
          state={buttonStates.start}
          variant="outline"
          tooltip={!canStart ? "Gateway is already running or in recovery mode" : undefined}
          onClick={() => handleButtonClick('start')}
        />
        
        <ControlButton
          action="stop"
          icon={<Square className="h-3 w-3" />}
          label="Stop"
          disabled={!canStop}
          state={buttonStates.stop}
          variant="destructive"
          tooltip={!canStop ? "Gateway is already stopped or in recovery mode" : undefined}
          onClick={() => handleButtonClick('stop')}
        />
        
        <ControlButton
          action="restart"
          icon={<RotateCcw className="h-3 w-3" />}
          label="Restart"
          disabled={!canRestart}
          state={buttonStates.restart}
          variant="secondary"
          tooltip={!canRestart ? "Gateway is in recovery mode" : undefined}
          onClick={() => handleButtonClick('restart')}
        />
      </div>

      {dialogState.action && (
        <GatewayControlDialog
          open={dialogState.open}
          onOpenChange={(open) => setDialogState({ open, action: null })}
          gateway={gateway}
          action={dialogState.action}
          onConfirm={handleConfirmAction}
          loading={dialogState.action ? buttonStates[dialogState.action] === 'loading' : false}
        />
      )}
    </>
  );
}