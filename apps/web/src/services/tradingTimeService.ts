import { TradingTimeStatus, TradingTimeConfig } from '@xiaoy-mdhub/shared-types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export interface TradingTimeResponse {
  success: boolean;
  data: TradingTimeStatus;
}

export interface TradingTimeConfigResponse {
  success: boolean;
  data: TradingTimeConfig & {
    sessions: Array<{
      name: string;
      market_type: string;
      ranges: Array<{
        start: string;
        end: string;
        is_overnight?: boolean;
      }>;
    }>;
  };
}

export interface TradingTimeCheckResponse {
  success: boolean;
  data: {
    gateway_type: string;
    is_trading_time: boolean;
    current_time: string;
  };
}

export class TradingTimeService {
  /**
   * Get current trading time status
   */
  static async getTradingTimeStatus(): Promise<TradingTimeStatus> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/trading-time/status`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: TradingTimeResponse = await response.json();
      
      if (!result.success) {
        throw new Error('API returned unsuccessful response');
      }
      
      return result.data;
    } catch (error) {
      console.error('Failed to fetch trading time status:', error);
      throw new Error(`Failed to fetch trading time status: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Check if current time is trading time for specific gateway
   */
  static async isTrading(gatewayType: 'CTP' | 'SOPT' = 'CTP'): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/trading-time/is-trading-time?gateway_type=${gatewayType}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: TradingTimeCheckResponse = await response.json();
      
      if (!result.success) {
        throw new Error('API returned unsuccessful response');
      }
      
      return result.data.is_trading_time;
    } catch (error) {
      console.error('Failed to check trading time:', error);
      throw new Error(`Failed to check trading time: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Get trading time configuration
   */
  static async getTradingTimeConfig(): Promise<TradingTimeConfigResponse['data']> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/trading-time/config`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: TradingTimeConfigResponse = await response.json();
      
      if (!result.success) {
        throw new Error('API returned unsuccessful response');
      }
      
      return result.data;
    } catch (error) {
      console.error('Failed to fetch trading time config:', error);
      throw new Error(`Failed to fetch trading time config: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Format time for display
   */
  static formatTime(isoString: string): string {
    return new Date(isoString).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  }

  /**
   * Format date for display
   */
  static formatDate(isoString: string): string {
    return new Date(isoString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      weekday: 'long'
    });
  }

  /**
   * Get status color based on trading status
   */
  static getStatusColor(status: string): string {
    switch (status) {
      case 'trading':
        return 'text-green-500';
      case 'pre_trading':
        return 'text-yellow-500';
      case 'post_trading':
        return 'text-orange-500';
      case 'non_trading':
      default:
        return 'text-red-500';
    }
  }

  /**
   * Get status text in Chinese
   */
  static getStatusText(status: string): string {
    switch (status) {
      case 'trading':
        return '交易中';
      case 'pre_trading':
        return '盘前';
      case 'post_trading':
        return '盘后';
      case 'non_trading':
      default:
        return '非交易时间';
    }
  }

  /**
   * Get time until next session
   */
  static getTimeUntilNextSession(nextSessionStart: string | null): string | null {
    if (!nextSessionStart) return null;

    const now = new Date();
    const nextStart = new Date(nextSessionStart);
    const diffMs = nextStart.getTime() - now.getTime();

    if (diffMs <= 0) return null;

    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
      return `${hours}小时${minutes}分钟后`;
    } else {
      return `${minutes}分钟后`;
    }
  }
}