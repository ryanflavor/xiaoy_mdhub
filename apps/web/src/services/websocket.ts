/**
 * WebSocket client service for real-time communication with the backend
 */

import {
  WebSocketConfig,
  WebSocketState,
  AnyWebSocketMessage,
  WebSocketEventType,
  PingMessage,
  isPong,
} from '@xiaoy-mdhub/shared-types';

export type MessageHandler = (message: AnyWebSocketMessage) => void;
export type StateChangeHandler = (state: WebSocketState) => void;

/**
 * WebSocket client with automatic reconnection and message handling
 */
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private config: Required<WebSocketConfig>;
  private state: WebSocketState = WebSocketState.DISCONNECTED;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingTimer: NodeJS.Timeout | null = null;
  private pongTimer: NodeJS.Timeout | null = null;
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private stateChangeHandlers: Set<StateChangeHandler> = new Set();
  private clientId: string | null = null;

  constructor(config: WebSocketConfig) {
    this.config = {
      reconnect: true,
      reconnectInterval: 1000,
      maxReconnectAttempts: 10,
      pingInterval: 30000,
      pongTimeout: 10000,
      ...config,
    };
  }

  /**
   * Connect to the WebSocket server
   */
  connect(token?: string): void {
    if (this.state === WebSocketState.CONNECTED || this.state === WebSocketState.CONNECTING) {
      return;
    }

    this.setState(WebSocketState.CONNECTING);

    try {
      // Add token to URL if provided
      let wsUrl = this.config.url;
      if (token) {
        const separator = wsUrl.includes('?') ? '&' : '?';
        wsUrl = `${wsUrl}${separator}token=${encodeURIComponent(token)}`;
      }

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
      this.ws.onerror = this.handleError.bind(this);
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.setState(WebSocketState.ERROR);
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.clearTimers();
    this.reconnectAttempts = 0;

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.setState(WebSocketState.DISCONNECTED);
  }

  /**
   * Send a message to the server
   */
  send(message: any): void {
    if (this.state !== WebSocketState.CONNECTED || !this.ws) {
      console.warn('WebSocket not connected, cannot send message');
      return;
    }

    try {
      this.ws.send(JSON.stringify(message));
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
    }
  }

  /**
   * Subscribe to messages of a specific type
   */
  on(eventType: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(eventType)) {
      this.messageHandlers.set(eventType, new Set());
    }

    this.messageHandlers.get(eventType)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(eventType);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.messageHandlers.delete(eventType);
        }
      }
    };
  }

  /**
   * Subscribe to all messages
   */
  onAny(handler: MessageHandler): () => void {
    return this.on('*', handler);
  }

  /**
   * Subscribe to state changes
   */
  onStateChange(handler: StateChangeHandler): () => void {
    this.stateChangeHandlers.add(handler);
    return () => this.stateChangeHandlers.delete(handler);
  }

  /**
   * Get current connection state
   */
  getState(): WebSocketState {
    return this.state;
  }

  /**
   * Get client ID assigned by server
   */
  getClientId(): string | null {
    return this.clientId;
  }

  private handleOpen(): void {
    console.log('WebSocket connected');
    this.setState(WebSocketState.CONNECTED);
    this.reconnectAttempts = 0;
    this.startPingInterval();
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: AnyWebSocketMessage = JSON.parse(event.data);

      // Handle connection message
      if (message.event_type === WebSocketEventType.CONNECTION) {
        const connMsg = message as any;
        if (connMsg.client_id) {
          this.clientId = connMsg.client_id;
        }
      }

      // Handle pong messages
      if (isPong(message)) {
        this.handlePong();
        return;
      }

      // Dispatch to handlers
      this.dispatchMessage(message);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  private handleClose(event: CloseEvent): void {
    console.log('WebSocket closed:', event.code, event.reason);
    this.clearTimers();
    this.ws = null;
    this.clientId = null;

    if (event.code === 1008) {
      // Policy violation (e.g., unauthorized)
      this.setState(WebSocketState.ERROR);
      return;
    }

    this.setState(WebSocketState.DISCONNECTED);

    if (this.config.reconnect && this.reconnectAttempts < this.config.maxReconnectAttempts) {
      this.scheduleReconnect();
    }
  }

  private handleError(event: Event): void {
    console.error('WebSocket error:', event);
    this.setState(WebSocketState.ERROR);
  }

  private dispatchMessage(message: AnyWebSocketMessage): void {
    // Dispatch to specific handlers
    const eventType = message.event_type || message.type || 'unknown';
    const handlers = this.messageHandlers.get(eventType);
    if (handlers) {
      handlers.forEach((handler) => handler(message));
    }

    // Dispatch to wildcard handlers
    const wildcardHandlers = this.messageHandlers.get('*');
    if (wildcardHandlers) {
      wildcardHandlers.forEach((handler) => handler(message));
    }
  }

  private setState(state: WebSocketState): void {
    if (this.state === state) return;

    this.state = state;
    this.stateChangeHandlers.forEach((handler) => handler(state));
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;

    this.setState(WebSocketState.RECONNECTING);
    this.reconnectAttempts++;

    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      30000
    );

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private startPingInterval(): void {
    this.pingTimer = setInterval(() => {
      if (this.state === WebSocketState.CONNECTED && this.ws) {
        const ping: PingMessage = {
          type: 'ping',
          timestamp: new Date().toISOString(),
        };

        this.send(ping);
        this.startPongTimeout();
      }
    }, this.config.pingInterval);
  }

  private startPongTimeout(): void {
    this.pongTimer = setTimeout(() => {
      console.warn('Pong timeout - connection may be dead');
      if (this.ws) {
        this.ws.close(4000, 'Pong timeout');
      }
    }, this.config.pongTimeout);
  }

  private handlePong(): void {
    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
  }

  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }

    if (this.pongTimer) {
      clearTimeout(this.pongTimer);
      this.pongTimer = null;
    }
  }
}

/**
 * Create and configure a WebSocket client instance
 */
export function createWebSocketClient(token?: string): WebSocketClient {
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
  
  const client = new WebSocketClient({
    url: wsUrl,
    reconnect: true,
    reconnectInterval: 1000,
    maxReconnectAttempts: 10,
    pingInterval: 30000,
    pongTimeout: 10000,
  });

  if (token) {
    client.connect(token);
  }

  return client;
}