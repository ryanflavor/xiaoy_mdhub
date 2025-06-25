/**
 * Gateway Control Service
 * Handles API calls for gateway management and control operations
 */

import { 
  GatewayControlAction, 
  GatewayControlRequest, 
  GatewayControlResponse 
} from '@xiaoy-mdhub/shared-types';
import { ApiClient, ApiResponse } from './api-client';

export class GatewayService {
  private apiClient: ApiClient;

  constructor() {
    this.apiClient = new ApiClient();
  }

  /**
   * Start a gateway
   */
  async startGateway(gatewayId: string): Promise<ApiResponse<GatewayControlResponse>> {
    const request: GatewayControlRequest = {
      gateway_id: gatewayId,
      action: 'start'
    };

    return this.apiClient.post<GatewayControlResponse>(
      `/api/accounts/${gatewayId}/start`,
      request
    );
  }

  /**
   * Stop a gateway
   */
  async stopGateway(gatewayId: string): Promise<ApiResponse<GatewayControlResponse>> {
    const request: GatewayControlRequest = {
      gateway_id: gatewayId,
      action: 'stop'
    };

    return this.apiClient.post<GatewayControlResponse>(
      `/api/accounts/${gatewayId}/stop`,
      request
    );
  }

  /**
   * Restart a gateway
   */
  async restartGateway(gatewayId: string): Promise<ApiResponse<GatewayControlResponse>> {
    const request: GatewayControlRequest = {
      gateway_id: gatewayId,
      action: 'restart'
    };

    return this.apiClient.post<GatewayControlResponse>(
      `/api/accounts/${gatewayId}/restart`,
      request
    );
  }

  /**
   * Generic control action method
   */
  async controlGateway(
    action: GatewayControlAction, 
    gatewayId: string
  ): Promise<ApiResponse<GatewayControlResponse>> {
    switch (action) {
      case 'start':
        return this.startGateway(gatewayId);
      case 'stop':
        return this.stopGateway(gatewayId);
      case 'restart':
        return this.restartGateway(gatewayId);
      default:
        throw new Error(`Unsupported gateway action: ${action}`);
    }
  }
}

// Create and export a singleton instance
export const gatewayService = new GatewayService();